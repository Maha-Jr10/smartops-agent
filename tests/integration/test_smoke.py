"""Smoke tests : verifie que l'API demarre et repond correctement.

Ces tests s'executent en integration (LLM simule) via le TestClient FastAPI.
Ils ne necessitent pas Docker.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from smartops_agent.api.app import create_app
from smartops_agent.api.auth import AuthUser, require_admin, require_auth

pytestmark = pytest.mark.integration

_STUB_USER = AuthUser(user_id="test-admin", email="admin@test.local", role="admin")


def _stub_auth() -> AuthUser:
    return _STUB_USER


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[require_auth] = _stub_auth
    app.dependency_overrides[require_admin] = _stub_auth
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_health_returns_version(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    from smartops_agent import __version__

    assert resp.json()["version"] == __version__


def test_approvals_list_empty(client: TestClient) -> None:
    resp = client.get("/approvals")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_metrics_endpoint_exists(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert b"smartops" in resp.content or b"python_gc" in resp.content


def test_invalid_approval_decision(client: TestClient) -> None:
    resp = client.post(
        "/approvals/nonexistent-id",
        json={"decision": "invalid-value"},
    )
    assert resp.status_code == 422
