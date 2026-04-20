from contextlib import asynccontextmanager
import logging
import os
import secrets
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from analytics_duckdb import get_duckdb_metrics, init_analytics
from auth import (
    APIKeyContext,
    enforce_chat_run_quota,
    ensure_workspace_access,
    hash_api_key,
    issue_jwt_token,
    require_auth_context,
    seed_api_keys_from_env,
)
from db import (
    add_document,
    create_api_key_record,
    get_metrics_summary,
    get_usage_summary,
    init_db,
    log_usage_event,
)
from otel_setup import setup_otel_fastapi
from schemas import (
    AdminCreateApiKeyRequest,
    AdminCreateApiKeyResponse,
    AdminIssueJwtRequest,
    AdminIssueJwtResponse,
    ChatRequest,
    ChatResponse,
    ConnectorImportResponse,
    IngestRequest,
    IngestResponse,
    ToolKbSearchRequest,
    ToolKbSearchResponse,
)
from sync_jobs import sync_notion, sync_zendesk
from vector_store import search_similar
from workflow import run_chat_workflow

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    init_analytics()
    seed_api_keys_from_env()
    yield


app = FastAPI(title="SaaS Copilot API", version="0.1.0", lifespan=lifespan)
setup_otel_fastapi(app)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/")
def root() -> RedirectResponse:
    """Browser entry without Node: static UI under /ui/."""
    return RedirectResponse(url="/ui/")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    ctx: APIKeyContext = Depends(require_auth_context),
) -> ChatResponse:
    ensure_workspace_access(ctx, request.workspace_id)
    enforce_chat_run_quota(ctx)
    response = await run_chat_workflow(request)
    log_usage_event(
        workspace_id=request.workspace_id,
        event_type="chat_run",
        units=1,
        trace_id=response.trace_id,
    )
    return response


@app.post("/ingest", response_model=IngestResponse)
def ingest(
    request: IngestRequest,
    ctx: APIKeyContext = Depends(require_auth_context),
) -> IngestResponse:
    ensure_workspace_access(ctx, request.workspace_id)
    document_id = add_document(
        workspace_id=request.workspace_id,
        source=request.source,
        content=request.content,
    )
    chunks_indexed = 0
    try:
        chunks_indexed = index_document(
            workspace_id=request.workspace_id,
            source=request.source,
            document_id=document_id,
            content=request.content,
        )
    except Exception as exc:
        # SQLite ingest succeeded; vector index is best-effort (Ollama/Qdrant may be down).
        logger.warning("Vector indexing skipped: %s", exc)
        chunks_indexed = 0
    log_usage_event(
        workspace_id=request.workspace_id,
        event_type="ingest_chars",
        units=len(request.content),
        trace_id=None,
    )
    return IngestResponse(
        document_id=document_id,
        workspace_id=request.workspace_id,
        source=request.source,
        chunks_indexed=chunks_indexed,
    )


@app.get("/metrics/summary")
def metrics_summary(
    workspace_id: str = "default",
    ctx: APIKeyContext = Depends(require_auth_context),
) -> dict[str, Any]:
    ensure_workspace_access(ctx, workspace_id)
    summary: dict[str, Any] = get_metrics_summary(workspace_id=workspace_id)
    summary["workspace_id"] = workspace_id
    summary.update(get_duckdb_metrics(workspace_id=workspace_id))
    summary.update(get_usage_summary(workspace_id=workspace_id))
    summary["plan"] = ctx.plan
    return summary


@app.post("/tools/kb-search", response_model=ToolKbSearchResponse)
def tool_kb_search(
    payload: ToolKbSearchRequest,
    ctx: APIKeyContext = Depends(require_auth_context),
) -> ToolKbSearchResponse:
    """
    HTTP tool surface for agents (or MCP bridges) — semantic search over the vector index.
    """
    ensure_workspace_access(ctx, payload.workspace_id)
    hits = search_similar(workspace_id=payload.workspace_id, query=payload.query, limit=payload.limit)
    return ToolKbSearchResponse(workspace_id=payload.workspace_id, hits=hits)


@app.post("/admin/api-keys", response_model=AdminCreateApiKeyResponse)
def create_api_key(
    payload: AdminCreateApiKeyRequest,
    x_admin_token: str | None = Header(default=None),
) -> AdminCreateApiKeyResponse:
    expected = os.getenv("ADMIN_BOOTSTRAP_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_BOOTSTRAP_TOKEN is not configured.")
    if x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token.")

    raw_key = "sk_live_" + secrets.token_urlsafe(24)
    create_api_key_record(
        key_hash=hash_api_key(raw_key),
        key_name=payload.key_name,
        workspace_id=payload.workspace_id,
        plan=payload.plan,
    )
    return AdminCreateApiKeyResponse(
        key_name=payload.key_name,
        workspace_id=payload.workspace_id,
        plan=payload.plan,
        api_key=raw_key,
    )


@app.post("/admin/jwt", response_model=AdminIssueJwtResponse)
def issue_jwt(
    payload: AdminIssueJwtRequest,
    x_admin_token: str | None = Header(default=None),
) -> AdminIssueJwtResponse:
    expected = os.getenv("ADMIN_BOOTSTRAP_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_BOOTSTRAP_TOKEN is not configured.")
    if x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token.")

    access_token = issue_jwt_token(
        subject=payload.subject,
        workspace_id=payload.workspace_id,
        plan=payload.plan,
        expires_minutes=payload.expires_minutes,
    )
    return AdminIssueJwtResponse(
        workspace_id=payload.workspace_id,
        plan=payload.plan,
        expires_minutes=payload.expires_minutes,
        access_token=access_token,
    )


@app.get("/connectors/notion/test")
def notion_connector_test(_ctx: APIKeyContext = Depends(require_auth_context)) -> dict[str, Any]:
    return {"connector": "notion", "status": "stub", "message": "Configure Notion token + sync worker next."}


@app.get("/connectors/zendesk/test")
def zendesk_connector_test(_ctx: APIKeyContext = Depends(require_auth_context)) -> dict[str, Any]:
    return {"connector": "zendesk", "status": "stub", "message": "Configure Zendesk token + sync worker next."}


@app.post("/connectors/notion/import", response_model=ConnectorImportResponse)
def notion_connector_import(
    workspace_id: str = "default",
    limit: int = 5,
    ctx: APIKeyContext = Depends(require_auth_context),
) -> ConnectorImportResponse:
    ensure_workspace_access(ctx, workspace_id)
    result = sync_notion(workspace_id=workspace_id, limit=limit)
    return ConnectorImportResponse(
        workspace_id=workspace_id,
        connector="notion",
        imported_documents=result.imported_documents,
        indexed_chunks=result.indexed_chunks,
    )


@app.post("/connectors/zendesk/import", response_model=ConnectorImportResponse)
def zendesk_connector_import(
    workspace_id: str = "default",
    limit: int = 10,
    ctx: APIKeyContext = Depends(require_auth_context),
) -> ConnectorImportResponse:
    ensure_workspace_access(ctx, workspace_id)
    result = sync_zendesk(workspace_id=workspace_id, limit=limit)
    return ConnectorImportResponse(
        workspace_id=workspace_id,
        connector="zendesk",
        imported_documents=result.imported_documents,
        indexed_chunks=result.indexed_chunks,
    )


@app.get("/capabilities")
def capabilities() -> dict[str, Any]:
    """Runtime feature flags for operators and integration tests."""
    return {
        "api": "saas-copilot",
        "sqlite": True,
        "duckdb_analytics": True,
        "qdrant_vector": True,
        "ollama_llm": True,
        "langgraph": True,
        "langfuse_tracing": bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")),
        "otel_otlp": bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")),
        "static_ui": True,
        "http_tool_kb_search": True,
        "api_key_auth": True,
        "jwt_auth": True,
        "usage_metering": True,
        "plan_enforcement": True,
        "connector_notion_import": True,
        "connector_zendesk_import": True,
    }


app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
