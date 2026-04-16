from contextlib import asynccontextmanager
import logging
import os
from typing import Any

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from analytics_duckdb import get_duckdb_metrics, init_analytics
from db import add_document, get_metrics_summary, init_db
from otel_setup import setup_otel_fastapi
from schemas import (
    ChatRequest,
    ChatResponse,
    IngestRequest,
    IngestResponse,
    ToolKbSearchRequest,
    ToolKbSearchResponse,
)
from vector_store import index_document, search_similar
from workflow import run_chat_workflow

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    init_analytics()
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
async def chat(request: ChatRequest) -> ChatResponse:
    return await run_chat_workflow(request)


@app.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest) -> IngestResponse:
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
    return IngestResponse(
        document_id=document_id,
        workspace_id=request.workspace_id,
        source=request.source,
        chunks_indexed=chunks_indexed,
    )


@app.get("/metrics/summary")
def metrics_summary(workspace_id: str = "default") -> dict[str, Any]:
    summary: dict[str, Any] = get_metrics_summary(workspace_id=workspace_id)
    summary["workspace_id"] = workspace_id
    summary.update(get_duckdb_metrics(workspace_id=workspace_id))
    return summary


@app.post("/tools/kb-search", response_model=ToolKbSearchResponse)
def tool_kb_search(payload: ToolKbSearchRequest) -> ToolKbSearchResponse:
    """
    HTTP tool surface for agents (or MCP bridges) — semantic search over the vector index.
    """
    hits = search_similar(workspace_id=payload.workspace_id, query=payload.query, limit=payload.limit)
    return ToolKbSearchResponse(workspace_id=payload.workspace_id, hits=hits)


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
    }


app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
