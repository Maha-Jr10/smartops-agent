"""Tests d'intégration de l'API /chat et /approvals."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import smartops_agent.api.app as app_mod
from smartops_agent.agent.llm_client import LLMResponse
from smartops_agent.api.app import create_app
from smartops_agent.api.auth import AuthUser, require_admin, require_auth
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
