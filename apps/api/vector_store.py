from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from chunking import chunk_text
from embeddings import embed_text
from settings import CHUNK_MAX_CHARS, CHUNK_OVERLAP, QDRANT_COLLECTION, QDRANT_URL

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None
_collection_dim: int | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client


def _existing_vector_size(client: QdrantClient) -> int | None:
    try:
        info = client.get_collection(QDRANT_COLLECTION)
        params = getattr(info, "config", None)
        if not params or not getattr(params, "params", None):
            return None
        vectors = getattr(params.params, "vectors", None)
        if vectors is None:
            return None
        if isinstance(vectors, dict):
            first = next(iter(vectors.values()), None)
            if first is not None:
                return int(getattr(first, "size", None) or 0) or None
        return int(getattr(vectors, "size", None) or 0) or None
    except Exception:
        return None


def _ensure_collection(dim: int) -> None:
    global _collection_dim
    client = get_client()
    names = {c.name for c in client.get_collections().collections}
    if QDRANT_COLLECTION not in names:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        _collection_dim = dim
        logger.info("Created Qdrant collection %s dim=%s", QDRANT_COLLECTION, dim)
        return

    existing = _existing_vector_size(client)
    if existing is not None:
        _collection_dim = existing
        if existing != dim:
            logger.warning(
                "Qdrant collection expects dim=%s but embedding dim=%s; align OLLAMA_EMBED_MODEL or recreate collection",
                existing,
                dim,
            )
    else:
        _collection_dim = dim


def index_document(workspace_id: str, source: str, document_id: int, content: str) -> int:
    """Chunk, embed, upsert. Returns number of points indexed (0 if vector path skipped)."""
    chunks = chunk_text(content, max_chars=CHUNK_MAX_CHARS, overlap=CHUNK_OVERLAP)
    if not chunks:
        return 0

    client = get_client()
    points: list[PointStruct] = []

    for idx, chunk in enumerate(chunks):
        vector = embed_text(chunk)
        if not vector:
            logger.warning("No embedding for document %s chunk %s; skipping vector index", document_id, idx)
            continue
        _ensure_collection(len(vector))
        if _collection_dim is not None and len(vector) != _collection_dim:
            logger.warning("Embedding dim mismatch; skipping chunk")
            continue

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "workspace_id": workspace_id,
                    "source": source,
                    "document_id": document_id,
                    "chunk_index": idx,
                    "text": chunk[:8000],
                },
            )
        )

    if points:
        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return len(points)


def search_similar(workspace_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return list of {source, text, score} from vector search, or empty if unavailable."""
    try:
        client = get_client()
        if QDRANT_COLLECTION not in {c.name for c in client.get_collections().collections}:
            return []
    except Exception as exc:
        logger.warning("Qdrant unavailable (vector search skipped): %s", exc)
        return []

    vector = embed_text(query)
    if not vector:
        return []

    try:
        _ensure_collection(len(vector))
    except Exception as exc:
        logger.warning("Qdrant ensure collection failed: %s", exc)
        return []

    try:
        hits = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vector,
            query_filter=Filter(must=[FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))]),
            limit=limit,
        )
    except Exception as exc:
        logger.warning("Qdrant search failed: %s", exc)
        return []

    results: list[dict[str, Any]] = []
    for hit in hits:
        payload = hit.payload or {}
        text = str(payload.get("text", "")).strip()
        source = str(payload.get("source", "unknown"))
        score = float(hit.score) if hit.score is not None else 0.0
        # Cosine similarity in Qdrant is typically in [0, 1] for COSINE distance config
        norm = max(0.0, min(1.0, score))
        if text:
            results.append({"source": source, "text": text, "score": norm})
    return results
