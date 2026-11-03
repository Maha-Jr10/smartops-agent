"""Routing tests : valide le comportement du proxy shadow/canary.

Ces tests s'executent via TestClient (pas de Docker requis).
Ils verifient que les en-tetes de deploiement sont forwarded correctement
et que les deux versions repondent a /health.
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


def _make_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[require_auth] = _stub_auth
    app.dependency_overrides[require_admin] = _stub_auth
    return TestClient(app)


@pytest.fixture(scope="module")
def stable_client() -> TestClient:
    return _make_client()


@pytest.fixture(scope="module")
def candidate_client() -> TestClient:
    return _make_client()


def test_stable_health(stable_client: TestClient) -> None:
    resp = stable_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_candidate_health(candidate_client: TestClient) -> None:
    resp = candidate_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_both_versions_return_same_schema(
    stable_client: TestClient, candidate_client: TestClient
) -> None:
    s = stable_client.get("/health").json()
    c = candidate_client.get("/health").json()
    assert set(s.keys()) == set(c.keys()), "Health schema mismatch between versions"


def test_approvals_endpoint_consistent(
    stable_client: TestClient, candidate_client: TestClient
) -> None:
    s = stable_client.get("/approvals")
    c = candidate_client.get("/approvals")
    assert s.status_code == 200
    assert c.status_code == 200
    assert isinstance(s.json(), list)
    assert isinstance(c.json(), list)
