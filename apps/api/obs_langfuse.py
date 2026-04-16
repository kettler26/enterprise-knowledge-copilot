from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _client() -> Any | None:
    if not (
        os.getenv("LANGFUSE_PUBLIC_KEY")
        and os.getenv("LANGFUSE_SECRET_KEY")
    ):
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except Exception as exc:
        logger.warning("Langfuse init failed: %s", exc)
        return None


def trace_chat_turn(
    trace_id: str,
    workspace_id: str,
    message: str,
    prompt: str,
    answer: str,
    model: str,
    citation_count: int,
) -> None:
    """Best-effort Langfuse trace (SDK API varies by major version)."""
    lf = _client()
    if lf is None:
        return
    try:
        trace_builder = getattr(lf, "trace", None)
        if callable(trace_builder):
            trace = trace_builder(
                id=trace_id,
                name="saas-copilot-chat",
                metadata={"workspace_id": workspace_id},
                input={"message": message},
                output={"answer": answer},
            )
            gen = getattr(trace, "generation", None)
            if callable(gen):
                gen(
                    name="ollama-completion",
                    model=model,
                    input=prompt,
                    output=answer,
                    metadata={"citation_count": citation_count},
                )
        flush = getattr(lf, "flush", None)
        if callable(flush):
            flush()
    except Exception as exc:
        logger.debug("Langfuse trace skipped: %s", exc)
