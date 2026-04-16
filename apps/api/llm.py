from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from settings import OLLAMA_BASE_URL, OLLAMA_MODEL


async def generate_answer(prompt: str) -> str:
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM backend error: {exc}") from exc

    text = (data.get("response") or "").strip()
    if not text:
        raise HTTPException(status_code=502, detail="LLM returned an empty response.")
    return text
