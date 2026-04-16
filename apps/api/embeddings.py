from __future__ import annotations

import logging
from typing import Any

import httpx

from settings import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL

logger = logging.getLogger(__name__)


def _parse_embedding(data: dict[str, Any]) -> list[float]:
    if "embedding" in data and isinstance(data["embedding"], list):
        return [float(x) for x in data["embedding"]]
    embeddings = data.get("embeddings")
    if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
        return [float(x) for x in embeddings[0]]
    raise ValueError("Unexpected embedding response shape")


def embed_text(text: str) -> list[float] | None:
    """
    Call Ollama embeddings API. Tries /api/embed then /api/embeddings.
    Returns None if the service is unavailable (caller can fall back).
    """
    text = text.strip()
    if not text:
        return None

    truncated = text if len(text) <= 8000 else text[:8000]

    with httpx.Client(timeout=120.0) as client:
        # Newer Ollama: POST /api/embed
        try:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": OLLAMA_EMBED_MODEL, "input": truncated},
            )
            if response.status_code == 404:
                raise httpx.HTTPStatusError("not found", request=response.request, response=response)
            response.raise_for_status()
            return _parse_embedding(response.json())
        except (httpx.HTTPError, ValueError) as first_error:
            logger.debug("embed /api/embed failed: %s", first_error)

        # Older Ollama: POST /api/embeddings
        try:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": OLLAMA_EMBED_MODEL, "prompt": truncated},
            )
            response.raise_for_status()
            return _parse_embedding(response.json())
        except httpx.HTTPError as exc:
            logger.warning("Ollama embeddings unavailable: %s", exc)
            return None
        except ValueError as exc:
            logger.warning("Bad embedding response: %s", exc)
            return None
