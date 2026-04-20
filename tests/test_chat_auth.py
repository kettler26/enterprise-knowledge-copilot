from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _bootstrap(tmp_path: Path):
    api_dir = Path(__file__).resolve().parents[1] / "apps" / "api"
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))

    os.environ["APP_DB_PATH"] = str(tmp_path / "test.db")
    os.environ["DUCKDB_PATH"] = str(tmp_path / "analytics.duckdb")
    os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "admin-test-token"
    os.environ["JWT_SECRET_KEY"] = "jwt-test-secret"
    os.environ.pop("API_KEYS", None)

    import importlib

    main = importlib.import_module("main")
    db = importlib.import_module("db")
    auth = importlib.import_module("auth")
    schemas = importlib.import_module("schemas")

    importlib.reload(db)
    importlib.reload(auth)
    importlib.reload(main)

    db.init_db()
    db.create_api_key_record(
        key_hash=auth.hash_api_key("sk_test_ok"),
        key_name="pytest",
        workspace_id="default",
        plan="starter",
    )
    return main, db, schemas


def test_chat_requires_api_key(tmp_path):
    main, _, _ = _bootstrap(tmp_path)
    client = TestClient(main.app)
    response = client.post("/chat", json={"workspace_id": "default", "message": "hello"})
    assert response.status_code == 401


def test_chat_workspace_scope_enforced(tmp_path, monkeypatch):
    main, _, schemas = _bootstrap(tmp_path)

    async def fake_workflow(_request):
        return schemas.ChatResponse(
            answer="ok",
            model="test-model",
            grounded=False,
            citations=[],
            trace_id="trace-123",
        )

    monkeypatch.setattr(main, "run_chat_workflow", fake_workflow)
    client = TestClient(main.app)
    response = client.post(
        "/chat",
        headers={"x-api-key": "sk_test_ok"},
        json={"workspace_id": "other", "message": "hello"},
    )
    assert response.status_code == 403


def test_chat_success_and_usage_increment(tmp_path, monkeypatch):
    main, db, schemas = _bootstrap(tmp_path)

    async def fake_workflow(_request):
        return schemas.ChatResponse(
            answer="ok",
            model="test-model",
            grounded=True,
            citations=[],
            trace_id="trace-1",
        )

    monkeypatch.setattr(main, "run_chat_workflow", fake_workflow)
    client = TestClient(main.app)
    response = client.post(
        "/chat",
        headers={"x-api-key": "sk_test_ok"},
        json={"workspace_id": "default", "message": "hello"},
    )
    assert response.status_code == 200
    usage = db.get_usage_summary("default")
    assert usage["chat_runs_month"] == 1


def test_chat_quota_enforced(tmp_path, monkeypatch):
    main, db, schemas = _bootstrap(tmp_path)
    import auth

    monkeypatch.setitem(auth.PLAN_LIMITS_CHAT_RUNS, "starter", 1)

    async def fake_workflow(_request):
        return schemas.ChatResponse(
            answer="ok",
            model="test-model",
            grounded=False,
            citations=[],
            trace_id="trace-q",
        )

    monkeypatch.setattr(main, "run_chat_workflow", fake_workflow)
    client = TestClient(main.app)

    first = client.post(
        "/chat",
        headers={"x-api-key": "sk_test_ok"},
        json={"workspace_id": "default", "message": "first"},
    )
    assert first.status_code == 200

    second = client.post(
        "/chat",
        headers={"x-api-key": "sk_test_ok"},
        json={"workspace_id": "default", "message": "second"},
    )
    assert second.status_code == 402


def test_chat_accepts_bearer_jwt(tmp_path, monkeypatch):
    main, _, schemas = _bootstrap(tmp_path)
    import auth

    token = auth.issue_jwt_token(
        subject="pytest-user",
        workspace_id="default",
        plan="starter",
        expires_minutes=30,
    )

    async def fake_workflow(_request):
        return schemas.ChatResponse(
            answer="jwt-ok",
            model="test-model",
            grounded=False,
            citations=[],
            trace_id="trace-jwt",
        )

    monkeypatch.setattr(main, "run_chat_workflow", fake_workflow)
    client = TestClient(main.app)
    response = client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"workspace_id": "default", "message": "hello"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "jwt-ok"
