from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Header, HTTPException

from db import create_api_key_record, get_api_key_record, get_monthly_usage

try:
    from jose import JWTError, jwt
except Exception:  # pragma: no cover - import fallback in environments without deps
    JWTError = Exception
    jwt = None

PLAN_LIMITS_CHAT_RUNS = {
    "starter": 2000,
    "growth": 20000,
    "enterprise": None,
}


@dataclass
class APIKeyContext:
    key_name: str
    workspace_id: str
    plan: str
    auth_type: str = "api_key"
    subject: str = "api_key"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def seed_api_keys_from_env() -> None:
    """
    API_KEYS format:
    API_KEYS=sk_live_123:default:starter,sk_live_456:acme:growth
    """
    raw = os.getenv("API_KEYS", "").strip()
    if not raw:
        return
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [p.strip() for p in chunk.split(":")]
        if len(parts) != 3:
            continue
        raw_key, workspace_id, plan = parts
        create_api_key_record(
            key_hash=hash_api_key(raw_key),
            key_name=f"seed-{workspace_id}",
            workspace_id=workspace_id,
            plan=plan,
        )


def require_api_key(x_api_key: str | None = Header(default=None)) -> APIKeyContext:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key. Pass header `x-api-key`.")
    row = get_api_key_record(hash_api_key(x_api_key))
    if row is None or not int(row["active"]):
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")
    return APIKeyContext(
        key_name=str(row["key_name"]),
        workspace_id=str(row["workspace_id"]),
        plan=str(row["plan"]),
    )


def _decode_bearer_token(token: str) -> dict[str, Any]:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    algo = os.getenv("JWT_ALGORITHM", "HS256")
    if not secret:
        raise HTTPException(status_code=503, detail="JWT_SECRET_KEY is not configured.")
    if jwt is None:
        raise HTTPException(status_code=503, detail="JWT library unavailable.")
    try:
        payload = jwt.decode(token, secret, algorithms=[algo])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid bearer token: {exc}") from exc
    return payload


def issue_jwt_token(subject: str, workspace_id: str, plan: str, expires_minutes: int = 60) -> str:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    algo = os.getenv("JWT_ALGORITHM", "HS256")
    if not secret:
        raise HTTPException(status_code=503, detail="JWT_SECRET_KEY is not configured.")
    if jwt is None:
        raise HTTPException(status_code=503, detail="JWT library unavailable.")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "workspace_id": workspace_id,
        "plan": plan,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=algo)


def require_auth_context(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> APIKeyContext:
    if x_api_key:
        return require_api_key(x_api_key=x_api_key)
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = _decode_bearer_token(token)
        workspace_id = str(payload.get("workspace_id") or "")
        plan = str(payload.get("plan") or "starter")
        subject = str(payload.get("sub") or "jwt-user")
        if not workspace_id:
            raise HTTPException(status_code=401, detail="Bearer token missing workspace_id.")
        return APIKeyContext(
            key_name=f"jwt:{subject}",
            workspace_id=workspace_id,
            plan=plan,
            auth_type="jwt",
            subject=subject,
        )
    raise HTTPException(status_code=401, detail="Missing credentials. Use x-api-key or Authorization: Bearer.")


def ensure_workspace_access(ctx: APIKeyContext, workspace_id: str) -> None:
    if ctx.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail=f"{ctx.auth_type} credentials cannot access this workspace.")


def enforce_chat_run_quota(ctx: APIKeyContext) -> None:
    plan = ctx.plan.lower()
    max_runs = PLAN_LIMITS_CHAT_RUNS.get(plan)
    if max_runs is None:
        return
    used = get_monthly_usage(ctx.workspace_id, "chat_run")
    if used >= max_runs:
        raise HTTPException(
            status_code=402,
            detail=f"Plan quota exceeded for chat runs this month ({used}/{max_runs}).",
        )
