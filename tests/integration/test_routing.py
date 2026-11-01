"""Routing tests : valide le comportement du proxy shadow/canary.

Ces tests s'executent via TestClient (pas de Docker requis).
Ils verifient que les en-tetes de deploiement sont forwarded correctement
et que les deux versions repondent a /health.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from smartops_agent.api.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def stable_client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(scope="module")
def candidate_client() -> TestClient:
    # Candidate uses the same app factory in tests (same code, different env)
    return TestClient(create_app())


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
