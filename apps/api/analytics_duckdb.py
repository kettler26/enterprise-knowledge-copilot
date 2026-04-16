from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DUCKDB_PATH = os.getenv("DUCKDB_PATH", os.path.join(os.getcwd(), "analytics.duckdb"))

_conn = None


def _get():
    global _conn
    if _conn is None:
        import duckdb

        _conn = duckdb.connect(DUCKDB_PATH)
    return _conn


def init_analytics() -> None:
    try:
        con = _get()
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS runs_analytics (
              trace_id VARCHAR PRIMARY KEY,
              workspace_id VARCHAR NOT NULL,
              created_at TIMESTAMP NOT NULL,
              grounded BOOLEAN NOT NULL,
              citation_count INTEGER NOT NULL,
              model VARCHAR NOT NULL,
              message_len INTEGER NOT NULL,
              answer_len INTEGER NOT NULL
            )
            """
        )
    except Exception as exc:
        logger.warning("DuckDB analytics disabled: %s", exc)


def append_run_analytics(
    trace_id: str,
    workspace_id: str,
    message: str,
    answer: str,
    model: str,
    grounded: bool,
    citation_count: int,
) -> None:
    try:
        con = _get()
        created_at = datetime.now(timezone.utc)
        con.execute(
            """
            INSERT OR REPLACE INTO runs_analytics
            (trace_id, workspace_id, created_at, grounded, citation_count, model, message_len, answer_len)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trace_id,
                workspace_id,
                created_at,
                grounded,
                citation_count,
                model,
                len(message or ""),
                len(answer or ""),
            ],
        )
    except Exception as exc:
        logger.debug("DuckDB append skipped: %s", exc)


def get_duckdb_metrics(workspace_id: str) -> dict[str, float | int]:
    """Rolling 7-day aggregates for dashboards."""
    try:
        con = _get()
        row = con.execute(
            """
            SELECT
              COUNT(*)::INTEGER AS runs_7d,
              AVG(citation_count)::DOUBLE AS avg_citations,
              AVG(CASE WHEN grounded THEN 1.0 ELSE 0.0 END)::DOUBLE AS grounded_rate
            FROM runs_analytics
            WHERE workspace_id = ?
              AND created_at >= (CURRENT_TIMESTAMP - INTERVAL '7 days')
            """,
            [workspace_id],
        ).fetchone()
        if not row:
            return {"runs_7d": 0, "avg_citations_7d": 0.0, "grounded_rate_7d": 0.0}
        return {
            "runs_7d": int(row[0] or 0),
            "avg_citations_7d": float(row[1] or 0.0),
            "grounded_rate_7d": float(row[2] or 0.0),
        }
    except Exception as exc:
        logger.debug("DuckDB metrics skipped: %s", exc)
        return {"runs_7d": 0, "avg_citations_7d": 0.0, "grounded_rate_7d": 0.0}
