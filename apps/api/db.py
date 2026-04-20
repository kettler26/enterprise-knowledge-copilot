from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.getenv("APP_DB_PATH", os.path.join(os.getcwd(), "copilot.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                trace_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                message TEXT NOT NULL,
                answer TEXT NOT NULL,
                model TEXT NOT NULL,
                grounded INTEGER NOT NULL,
                citation_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT NOT NULL UNIQUE,
                key_name TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                plan TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                units INTEGER NOT NULL,
                trace_id TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS connector_sync_state (
                connector TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                cursor TEXT,
                last_success_at TEXT,
                PRIMARY KEY (connector, workspace_id)
            )
            """
        )


def log_run(
    trace_id: str,
    workspace_id: str,
    message: str,
    answer: str,
    model: str,
    grounded: bool,
    citation_count: int,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO runs (trace_id, workspace_id, message, answer, model, grounded, citation_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (trace_id, workspace_id, message, answer, model, int(grounded), citation_count, created_at),
        )


def add_document(workspace_id: str, source: str, content: str) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (workspace_id, source, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (workspace_id, source, content, created_at),
        )
        return int(cursor.lastrowid)


def search_documents(workspace_id: str, query: str, limit: int = 3) -> list[sqlite3.Row]:
    terms = [term.strip().lower() for term in query.split() if term.strip()]
    if not terms:
        terms = [query.lower()]
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, source, content
            FROM documents
            WHERE workspace_id = ?
            ORDER BY id DESC
            LIMIT 100
            """,
            (workspace_id,),
        ).fetchall()
    ranked: list[tuple[int, sqlite3.Row]] = []
    for row in rows:
        body = row["content"].lower()
        score = sum(1 for t in terms if t in body)
        if score > 0:
            ranked.append((score, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in ranked[:limit]]


def get_metrics_summary(workspace_id: str) -> dict[str, int]:
    with _connect() as conn:
        totals = conn.execute(
            """
            SELECT
              COUNT(*) AS total_runs,
              COALESCE(SUM(grounded), 0) AS grounded_runs,
              COALESCE(SUM(citation_count), 0) AS total_citations
            FROM runs
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()
        docs = conn.execute(
            """
            SELECT COUNT(*) AS total_documents
            FROM documents
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()

    return {
        "total_runs": int(totals["total_runs"]),
        "grounded_runs": int(totals["grounded_runs"]),
        "total_citations": int(totals["total_citations"]),
        "total_documents": int(docs["total_documents"]),
    }


def create_api_key_record(
    key_hash: str,
    key_name: str,
    workspace_id: str,
    plan: str,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO api_keys (key_hash, key_name, workspace_id, plan, active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (key_hash, key_name, workspace_id, plan, created_at),
        )


def get_api_key_record(key_hash: str) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute(
            """
            SELECT key_name, workspace_id, plan, active
            FROM api_keys
            WHERE key_hash = ?
            LIMIT 1
            """,
            (key_hash,),
        ).fetchone()


def log_usage_event(
    workspace_id: str,
    event_type: str,
    units: int,
    trace_id: str | None = None,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO usage_events (workspace_id, event_type, units, trace_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (workspace_id, event_type, units, trace_id, created_at),
        )


def get_monthly_usage(workspace_id: str, event_type: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(units), 0) AS total
            FROM usage_events
            WHERE workspace_id = ?
              AND event_type = ?
              AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            """,
            (workspace_id, event_type),
        ).fetchone()
    return int((row or {"total": 0})["total"])


def get_usage_summary(workspace_id: str) -> dict[str, Any]:
    return {
        "chat_runs_month": get_monthly_usage(workspace_id, "chat_run"),
        "ingest_chars_month": get_monthly_usage(workspace_id, "ingest_chars"),
    }


def get_connector_cursor(connector: str, workspace_id: str) -> str | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT cursor
            FROM connector_sync_state
            WHERE connector = ? AND workspace_id = ?
            LIMIT 1
            """,
            (connector, workspace_id),
        ).fetchone()
    if row is None:
        return None
    return row["cursor"]


def set_connector_cursor(connector: str, workspace_id: str, cursor: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO connector_sync_state (connector, workspace_id, cursor, last_success_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(connector, workspace_id)
            DO UPDATE SET cursor = excluded.cursor, last_success_at = excluded.last_success_at
            """,
            (connector, workspace_id, cursor, now),
        )
