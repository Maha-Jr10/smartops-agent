from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from smartops_agent import __version__

pytestmark = pytest.mark.integration


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == __version__


def test_metrics_endpoint_exposes_prometheus(client: TestClient) -> None:
    response = client.get("/metrics/")
    assert response.status_code == 200
    assert "python_info" in response.text
