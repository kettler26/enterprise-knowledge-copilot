from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import httpx


def _headers_notion() -> dict[str, str]:
    token = os.getenv("NOTION_API_TOKEN", "").strip()
    if not token:
        raise ValueError("NOTION_API_TOKEN is missing.")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": os.getenv("NOTION_VERSION", "2022-06-28"),
        "Content-Type": "application/json",
    }


def _extract_notion_text(page_obj: dict[str, Any]) -> str:
    props = page_obj.get("properties", {})
    lines: list[str] = []
    title = ""
    for _, value in props.items():
        if value.get("type") == "title":
            title = "".join([item.get("plain_text", "") for item in value.get("title", [])]).strip()
            if title:
                lines.append(f"Title: {title}")
            break
    return "\n".join(lines) or f"Notion page {page_obj.get('id', '')}"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _with_retries(request_fn, attempts: int = 3, base_sleep_s: float = 0.4):
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return request_fn()
        except Exception as exc:  # noqa: PERF203
            last_exc = exc
            if i + 1 >= attempts:
                break
            time.sleep(base_sleep_s * (2**i))
    assert last_exc is not None
    raise last_exc


def fetch_notion_pages(limit: int = 5, since_cursor: str | None = None) -> tuple[list[dict[str, str]], str | None]:
    """
    Read-only fetch of recently searchable Notion pages.
    Returns list of {"source": "...", "content": "..."}.
    """
    url = "https://api.notion.com/v1/search"
    payload = {
        "page_size": max(1, min(limit, 20)),
        "filter": {"value": "page", "property": "object"},
        "sort": {"direction": "descending", "timestamp": "last_edited_time"},
    }
    with httpx.Client(timeout=30.0) as client:
        def _do():
            response = client.post(url, headers=_headers_notion(), json=payload)
            response.raise_for_status()
            return response.json()
        data = _with_retries(_do)
    pages: list[dict[str, str]] = []
    max_cursor_dt = _parse_dt(since_cursor)
    for page in data.get("results", []):
        last_edited = page.get("last_edited_time")
        dt = _parse_dt(last_edited)
        if since_cursor and dt and max_cursor_dt and dt <= max_cursor_dt:
            continue
        page_id = page.get("id", "unknown")
        title_text = _extract_notion_text(page)
        pages.append(
            {
                "source": f"notion:{page_id}",
                "content": title_text,
            }
        )
        if dt and (max_cursor_dt is None or dt > max_cursor_dt):
            max_cursor_dt = dt
    new_cursor = max_cursor_dt.isoformat() if max_cursor_dt else since_cursor
    return pages, new_cursor


def _zendesk_auth_headers() -> dict[str, str]:
    token = os.getenv("ZENDESK_API_TOKEN", "").strip()
    email = os.getenv("ZENDESK_EMAIL", "").strip()
    if not token or not email:
        raise ValueError("ZENDESK_API_TOKEN or ZENDESK_EMAIL is missing.")
    import base64

    raw = f"{email}/token:{token}".encode("utf-8")
    return {
        "Authorization": f"Basic {base64.b64encode(raw).decode('ascii')}",
        "Content-Type": "application/json",
    }


def fetch_zendesk_tickets(limit: int = 10, since_cursor: str | None = None) -> tuple[list[dict[str, str]], str | None]:
    """
    Read-only fetch of Zendesk tickets.
    Requires ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_API_TOKEN.
    """
    subdomain = os.getenv("ZENDESK_SUBDOMAIN", "").strip()
    if not subdomain:
        raise ValueError("ZENDESK_SUBDOMAIN is missing.")
    url = f"https://{subdomain}.zendesk.com/api/v2/tickets.json"
    with httpx.Client(timeout=30.0) as client:
        def _do():
            response = client.get(url, headers=_zendesk_auth_headers(), params={"per_page": max(1, min(limit, 100))})
            response.raise_for_status()
            return response.json()
        data = _with_retries(_do)
    tickets: list[dict[str, str]] = []
    max_cursor_dt = _parse_dt(since_cursor)
    for ticket in data.get("tickets", []):
        updated_at = ticket.get("updated_at")
        dt = _parse_dt(updated_at)
        if since_cursor and dt and max_cursor_dt and dt <= max_cursor_dt:
            continue
        tid = ticket.get("id", "unknown")
        subject = str(ticket.get("subject") or "").strip()
        description = str(ticket.get("description") or "").strip()
        status = str(ticket.get("status") or "").strip()
        priority = str(ticket.get("priority") or "").strip()
        content = (
            f"Ticket #{tid}\n"
            f"Subject: {subject}\n"
            f"Status: {status}\n"
            f"Priority: {priority}\n\n"
            f"Description:\n{description}"
        ).strip()
        tickets.append({"source": f"zendesk:{tid}", "content": content})
        if dt and (max_cursor_dt is None or dt > max_cursor_dt):
            max_cursor_dt = dt
    new_cursor = max_cursor_dt.isoformat() if max_cursor_dt else since_cursor
    return tickets, new_cursor
