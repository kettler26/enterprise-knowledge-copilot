from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source: str = Field(..., description="Document or system source name")
    snippet: str = Field(..., description="Short excerpt used for grounding")
    score: float = Field(..., ge=0.0, le=1.0, description="Retrieval confidence score")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    context: str | None = None
    workspace_id: str = Field(default="default")


class ChatResponse(BaseModel):
    answer: str
    model: str
    grounded: bool
    citations: list[Citation]
    trace_id: str


class IngestRequest(BaseModel):
    workspace_id: str = Field(default="default")
    source: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=20000)


class IngestResponse(BaseModel):
    document_id: int
    workspace_id: str
    source: str
    chunks_indexed: int = Field(default=0, description="Chunks stored in Qdrant (0 if embeddings unavailable)")


class ToolKbSearchRequest(BaseModel):
    workspace_id: str = Field(default="default")
    query: str = Field(..., min_length=1, max_length=4000)
    limit: int = Field(default=8, ge=1, le=50)


class ToolKbSearchResponse(BaseModel):
    workspace_id: str
    hits: list[dict[str, Any]]


class AdminCreateApiKeyRequest(BaseModel):
    key_name: str = Field(..., min_length=1, max_length=100)
    workspace_id: str = Field(..., min_length=1, max_length=100)
    plan: str = Field(default="starter", pattern="^(starter|growth|enterprise)$")


class AdminCreateApiKeyResponse(BaseModel):
    key_name: str
    workspace_id: str
    plan: str
    api_key: str


class AdminIssueJwtRequest(BaseModel):
    subject: str = Field(default="local-user")
    workspace_id: str = Field(..., min_length=1, max_length=100)
    plan: str = Field(default="starter", pattern="^(starter|growth|enterprise)$")
    expires_minutes: int = Field(default=60, ge=5, le=10080)


class AdminIssueJwtResponse(BaseModel):
    workspace_id: str
    plan: str
    expires_minutes: int
    access_token: str


class ConnectorImportResponse(BaseModel):
    workspace_id: str
    connector: str
    imported_documents: int
    indexed_chunks: int
