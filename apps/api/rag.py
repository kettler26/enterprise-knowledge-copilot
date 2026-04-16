from __future__ import annotations

import re

from db import search_documents
from schemas import Citation
from settings import (
    RAG_MAX_CITATIONS,
    RAG_MAX_KEYWORD,
    RAG_MAX_VECTOR,
    RAG_MIN_VECTOR_SCORE,
)
from vector_store import search_similar

_SUFFIX_RE = re.compile(r"\s*\((vector|keyword)\)\s*$", re.IGNORECASE)


def _normalize_source_key(source: str) -> str:
    base = _SUFFIX_RE.sub("", source.strip()).strip().lower()
    return base or source.strip().lower()


def _trim_snippet(text: str, limit: int = 280) -> str:
    text = text.strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def build_citations(message: str, context: str | None, workspace_id: str) -> list[Citation]:
    """
    Priority: inline context (if any) → vector (Qdrant) if score passes threshold →
    else keyword (SQLite). Deduplicate by base source name. Hard cap on total citations.
    """
    citations: list[Citation] = []

    if context:
        citations.append(
            Citation(
                source="inline_context",
                snippet=_trim_snippet(context, 240),
                score=0.88,
            )
        )

    remaining = max(0, RAG_MAX_CITATIONS - len(citations))

    vector_hits = search_similar(workspace_id=workspace_id, query=message, limit=24)
    vector_hits.sort(key=lambda hit: float(hit["score"]), reverse=True)

    filtered_vectors = [hit for hit in vector_hits if float(hit["score"]) >= RAG_MIN_VECTOR_SCORE]

    used_keys: set[str] = set()
    for c in citations:
        used_keys.add(_normalize_source_key(c.source))

    vector_added = 0
    for hit in filtered_vectors:
        if remaining <= 0 or vector_added >= RAG_MAX_VECTOR:
            break
        raw_source = str(hit["source"])
        key = _normalize_source_key(raw_source)
        if key in used_keys:
            continue
        used_keys.add(key)
        citations.append(
            Citation(
                source=f"{raw_source} (vector)",
                snippet=_trim_snippet(str(hit["text"])),
                score=float(hit["score"]),
            )
        )
        vector_added += 1
        remaining -= 1

    # Keyword fallback only when nothing from vector search cleared the quality bar
    if vector_added == 0 and remaining > 0:
        for idx, row in enumerate(search_documents(workspace_id=workspace_id, query=message, limit=8)):
            if remaining <= 0 or idx >= RAG_MAX_KEYWORD:
                break
            raw_source = str(row["source"])
            key = _normalize_source_key(raw_source)
            if key in used_keys:
                continue
            used_keys.add(key)
            citations.append(
                Citation(
                    source=f"{raw_source} (keyword)",
                    snippet=_trim_snippet(str(row["content"]), 240),
                    score=max(0.42, 0.68 - (idx * 0.06)),
                )
            )
            remaining -= 1

    return citations[: RAG_MAX_CITATIONS]
