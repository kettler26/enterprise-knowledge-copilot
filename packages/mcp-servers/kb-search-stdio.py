from __future__ import annotations

import json
import os
import sys

import httpx

API_BASE_URL = os.getenv("COPILOT_API_BASE_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("COPILOT_API_KEY", "")


def _send(payload: dict) -> dict:
    workspace_id = str(payload.get("workspace_id") or "default")
    query = str(payload.get("query") or "").strip()
    limit = int(payload.get("limit") or 8)
    if not query:
        return {"ok": False, "error": "query required"}

    response = httpx.post(
        f"{API_BASE_URL}/tools/kb-search",
        headers={"Content-Type": "application/json", "x-api-key": API_KEY},
        json={"workspace_id": workspace_id, "query": query, "limit": limit},
        timeout=30.0,
    )
    if response.status_code >= 400:
        return {"ok": False, "error": response.text, "status_code": response.status_code}
    return {"ok": True, "result": response.json()}


def main() -> int:
    """
    Tiny stdio wrapper for MCP-style usage.
    Reads JSON lines from stdin:
      {"workspace_id":"default","query":"refund policy","limit":5}
    Writes one JSON response line to stdout.
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            out = _send(payload)
        except Exception as exc:
            out = {"ok": False, "error": str(exc)}
        sys.stdout.write(json.dumps(out, ensure_ascii=True) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
