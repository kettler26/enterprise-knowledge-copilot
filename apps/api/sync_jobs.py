from __future__ import annotations

import logging
from dataclasses import dataclass

from connectors import fetch_notion_pages, fetch_zendesk_tickets
from db import add_document, get_connector_cursor, set_connector_cursor
from vector_store import index_document

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    connector: str
    workspace_id: str
    imported_documents: int
    indexed_chunks: int
    cursor_before: str | None
    cursor_after: str | None


def _index_best_effort(workspace_id: str, source: str, doc_id: int, content: str) -> int:
    try:
        return index_document(
            workspace_id=workspace_id,
            source=source,
            document_id=doc_id,
            content=content,
        )
    except Exception as exc:
        logger.warning("Vector indexing skipped for %s: %s", source, exc)
        return 0


def sync_notion(workspace_id: str, limit: int = 5) -> SyncResult:
    before = get_connector_cursor("notion", workspace_id)
    pages, after = fetch_notion_pages(limit=limit, since_cursor=before)
    imported = 0
    indexed = 0
    for page in pages:
        doc_id = add_document(workspace_id=workspace_id, source=page["source"], content=page["content"])
        imported += 1
        indexed += _index_best_effort(workspace_id, page["source"], doc_id, page["content"])
    set_connector_cursor("notion", workspace_id, after)
    return SyncResult(
        connector="notion",
        workspace_id=workspace_id,
        imported_documents=imported,
        indexed_chunks=indexed,
        cursor_before=before,
        cursor_after=after,
    )


def sync_zendesk(workspace_id: str, limit: int = 10) -> SyncResult:
    before = get_connector_cursor("zendesk", workspace_id)
    tickets, after = fetch_zendesk_tickets(limit=limit, since_cursor=before)
    imported = 0
    indexed = 0
    for ticket in tickets:
        doc_id = add_document(workspace_id=workspace_id, source=ticket["source"], content=ticket["content"])
        imported += 1
        indexed += _index_best_effort(workspace_id, ticket["source"], doc_id, ticket["content"])
    set_connector_cursor("zendesk", workspace_id, after)
    return SyncResult(
        connector="zendesk",
        workspace_id=workspace_id,
        imported_documents=imported,
        indexed_chunks=indexed,
        cursor_before=before,
        cursor_after=after,
    )
