from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from smartops_agent.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())
