"""Tests d'intégration de l'API /chat et /approvals."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import smartops_agent.api.app as app_mod
from smartops_agent.agent.llm_client import AVAILABLE_MODELS, LLMResponse
from smartops_agent.api.app import create_app
from smartops_agent.api.auth import AuthUser, require_admin, require_auth
from smartops_agent.config import Settings
from smartops_agent.guardrails.approval_queue import ApprovalQueue

pytestmark = pytest.mark.integration


class FakeLLM:
    def __init__(self, response: LLMResponse) -> None:
        self._response = response

    def chat(self, messages: Any, tools: Any, temperature: Any, timeout: Any) -> LLMResponse:
        return self._response


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    p = tmp_path / "crm.db"
    con = sqlite3.connect(p)
    con.executescript("""
        CREATE TABLE clients (id TEXT PRIMARY KEY, name TEXT,
            email TEXT, phone TEXT, status TEXT);
        CREATE TABLE leads (id TEXT PRIMARY KEY, name TEXT,
            email TEXT, phone TEXT, status TEXT, opted_out INTEGER, notes TEXT);
        CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, client_id TEXT,
            status TEXT, total_amount REAL, currency TEXT, direct_costs REAL,
            apporteur_id TEXT, realisation_ids TEXT);
        CREATE TABLE invoices (id TEXT PRIMARY KEY, project_id TEXT, amount REAL,
            currency TEXT, status TEXT, due_date TEXT);
    """)
    con.commit()
    con.close()
    return str(p)


@pytest.fixture
def queue() -> ApprovalQueue:
    return ApprovalQueue()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM(LLMResponse(content="Réponse simulée."))


_TEST_ADMIN = AuthUser(user_id="test-admin", email="admin@test.local", role="admin")


def _stub_auth() -> AuthUser:
    return _TEST_ADMIN


@pytest.fixture
def app_client(
    db_path: str,
    queue: ApprovalQueue,
    fake_llm: FakeLLM,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    # Reset rate-limit state with proper defaultdicts
    monkeypatch.setattr(app_mod, "_rate_windows", defaultdict(list))
    monkeypatch.setattr(app_mod, "_daily_llm_count", defaultdict(int))

    from smartops_agent.agent import llm_client as llm_mod

    monkeypatch.setattr(llm_mod, "build_llm_client", lambda p, m: fake_llm)

    app = create_app(db_path=db_path, queue=queue)
    # Bypass Supabase auth in integration tests — use a fixed admin identity
    app.dependency_overrides[require_auth] = _stub_auth
    app.dependency_overrides[require_admin] = _stub_auth
    return TestClient(app)


def test_chat_returns_200(app_client: TestClient) -> None:
    resp = app_client.post(
        "/chat", json={"message": "Bonjour", "role": "commercial", "user_id": "u1"}
    )
    assert resp.status_code == 200
    assert "answer" in resp.json()


def test_approvals_list_empty(app_client: TestClient) -> None:
    resp = app_client.get("/approvals")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_approvals_decision(app_client: TestClient, queue: ApprovalQueue) -> None:
    queue.enqueue("req_test", "send_email", "relance", {"to": "x@y.com"})
    resp = app_client.post("/approvals/req_test", json={"decision": "approved", "comment": "OK"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_approvals_decision_not_found(app_client: TestClient) -> None:
    resp = app_client.post("/approvals/nonexistent", json={"decision": "approved"})
    assert resp.status_code == 404


def test_approvals_invalid_decision(app_client: TestClient, queue: ApprovalQueue) -> None:
    queue.enqueue("req_bad", "send_email", "test", {})
    resp = app_client.post("/approvals/req_bad", json={"decision": "maybe"})
    assert resp.status_code == 422


def test_rate_limit_triggers_429(
    db_path: str, queue: ApprovalQueue, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Fill up the rate-limit window for the TestClient's IP ('testclient')
    import time

    full_window: dict[str, list[float]] = defaultdict(list)
    full_window["testclient"] = [time.time()] * 100
    monkeypatch.setattr(app_mod, "_rate_windows", full_window)
    monkeypatch.setattr(app_mod, "_daily_llm_count", defaultdict(int))

    from smartops_agent.agent import llm_client as llm_mod

    monkeypatch.setattr(
        llm_mod,
        "build_llm_client",
        lambda p, m: FakeLLM(LLMResponse(content="ok")),
    )
    app = create_app(db_path=db_path, queue=queue)
    app.dependency_overrides[require_auth] = _stub_auth
    app.dependency_overrides[require_admin] = _stub_auth
    client = TestClient(app)
    resp = client.post("/chat", json={"message": "hi", "role": "commercial", "user_id": "u1"})
    assert resp.status_code == 429


def test_admin_seed_and_monitoring_endpoints(
    tmp_path: Path, queue: ApprovalQueue, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(supabase_url="", supabase_service_role_key=None)
    monkeypatch.setattr(app_mod, "get_settings", lambda: settings)
    app = create_app(db_path=str(tmp_path / "crm.db"), queue=queue)
    app.dependency_overrides[require_auth] = _stub_auth
    app.dependency_overrides[require_admin] = _stub_auth

    import smartops_agent.data.seed_traces as seed_mod
    import smartops_agent.monitoring.report as report_mod

    monkeypatch.setattr(seed_mod, "seed_traces", lambda: 160)
    monkeypatch.setattr(report_mod, "run_report", lambda: True)
    monkeypatch.setattr(seed_mod, "delete_traces", lambda: True)

    client = TestClient(app)
    seeded = client.post("/admin/seed-data")
    deleted = client.delete("/admin/seed-data")
    status = client.get("/monitoring/status")

    assert seeded.status_code == 200
    assert seeded.json() == {"seeded_traces": 160, "report": "generated"}
    assert deleted.status_code == 200
    assert deleted.json() == {"traces_deleted": True, "supabase_cleaned": False}
    assert status.status_code == 200
    assert status.json()["status"] == "never_run"


def test_admin_settings_and_drift_fallback(
    tmp_path: Path, queue: ApprovalQueue, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(supabase_url="", supabase_service_role_key=None)
    monkeypatch.setattr(app_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(app_mod, "get_effective_groq_key", lambda: "abcdefgh1234wxyz")
    monkeypatch.setattr(app_mod, "get_effective_openrouter_key", lambda: "")
    monkeypatch.setattr(app_mod, "get_effective_model_id", lambda: "test-model")
    monkeypatch.setattr(Path, "exists", lambda _path: False)

    app = create_app(db_path=str(tmp_path / "crm.db"), queue=queue)
    app.dependency_overrides[require_auth] = _stub_auth
    app.dependency_overrides[require_admin] = _stub_auth
    client = TestClient(app)

    groq_key = client.get("/settings/groq-key")
    openrouter_key = client.get("/settings/openrouter-key")
    model = client.get("/settings/model")
    groq_update = client.put("/settings/groq-key", json={"api_key": "test-key"})
    openrouter_update = client.put("/settings/openrouter-key", json={"api_key": "test-key"})
    invalid_model = client.put("/settings/model", json={"model_id": "unknown-model"})
    valid_model = client.put(
        "/settings/model",
        json={"model_id": AVAILABLE_MODELS[0]["id"]},
    )
    drift_report = client.get("/report/drift")

    assert groq_key.json() == {"has_key": "true", "masked": "abcdefgh…wxyz", "source": "env"}
    assert openrouter_key.json() == {"has_key": "false", "masked": ""}
    assert model.json()["current"] == "test-model"
    assert groq_update.status_code == 503
    assert openrouter_update.status_code == 503
    assert invalid_model.status_code == 422
    assert valid_model.status_code == 503
    assert drift_report.status_code == 200
    assert "Rapport non disponible" in drift_report.text


def test_admin_settings_update_with_supabase(
    tmp_path: Path, queue: ApprovalQueue, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        supabase_url="https://test.supabase.co",
        supabase_service_role_key="test-service-key",
    )
    monkeypatch.setattr(app_mod, "get_settings", lambda: settings)
    supabase_client = MagicMock()
    query = supabase_client.table.return_value.select.return_value
    query.eq.return_value.single.return_value.execute.return_value.data = {"value": "stored-key"}

    import supabase

    monkeypatch.setattr(supabase, "create_client", lambda *_args: supabase_client)
    app = create_app(db_path=str(tmp_path / "crm.db"), queue=queue)
    app.dependency_overrides[require_auth] = _stub_auth
    app.dependency_overrides[require_admin] = _stub_auth
    client = TestClient(app)

    groq_key = client.get("/settings/groq-key")
    groq_update = client.put("/settings/groq-key", json={"api_key": "new-groq-key"})
    openrouter_update = client.put(
        "/settings/openrouter-key", json={"api_key": "new-openrouter-key"}
    )
    model_id = AVAILABLE_MODELS[0]["id"]
    model_update = client.put("/settings/model", json={"model_id": model_id})

    assert groq_key.json()["source"] == "override"
    assert groq_update.json() == {"status": "updated"}
    assert openrouter_update.json() == {"status": "updated"}
    assert model_update.json() == {"status": "updated", "model_id": model_id}
    assert supabase_client.table.return_value.upsert.call_count == 3
