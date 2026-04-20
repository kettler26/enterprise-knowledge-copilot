from __future__ import annotations

import os
import sys
import time
from pathlib import Path


def _api_path() -> str:
    root = Path(__file__).resolve().parents[1]
    return str(root / "apps" / "api")


sys.path.insert(0, _api_path())

from db import init_db  # noqa: E402
from sync_jobs import sync_notion, sync_zendesk  # noqa: E402


def _parse_list(env_name: str, default: str) -> list[str]:
    raw = os.getenv(env_name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def run_once(workspaces: list[str], connectors: list[str]) -> None:
    for workspace in workspaces:
        if "notion" in connectors:
            result = sync_notion(workspace_id=workspace, limit=int(os.getenv("NOTION_SYNC_LIMIT", "10")))
            print(
                f"[scheduler] notion workspace={workspace} imported={result.imported_documents} "
                f"indexed={result.indexed_chunks} cursor_after={result.cursor_after}"
            )
        if "zendesk" in connectors:
            result = sync_zendesk(workspace_id=workspace, limit=int(os.getenv("ZENDESK_SYNC_LIMIT", "20")))
            print(
                f"[scheduler] zendesk workspace={workspace} imported={result.imported_documents} "
                f"indexed={result.indexed_chunks} cursor_after={result.cursor_after}"
            )


def main() -> int:
    init_db()
    workspaces = _parse_list("CONNECTOR_SYNC_WORKSPACES", "default")
    connectors = _parse_list("CONNECTOR_SYNC_CONNECTORS", "notion,zendesk")
    interval = int(os.getenv("CONNECTOR_SYNC_INTERVAL_SECONDS", "300"))

    print(
        f"[scheduler] start workspaces={workspaces} connectors={connectors} interval_s={interval}",
        flush=True,
    )
    while True:
        try:
            run_once(workspaces=workspaces, connectors=connectors)
        except Exception as exc:
            print(f"[scheduler] sync cycle failed: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
