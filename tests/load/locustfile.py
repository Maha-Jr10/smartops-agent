"""Test de charge sur /health et /chat.

Usage (stub LLM, serveur local) :
    uv run locust -f tests/load/locustfile.py --headless -u 5 -r 1 -t 1m \
        --host http://localhost:8000
"""

from __future__ import annotations

import random

from locust import HttpUser, between, task

_MESSAGES = [
    "Cherche le client Diallo dans la base.",
    "Quel est le statut de la facture INV-001 ?",
    "Calcule la commission pour le projet Audit 2024.",
    "Donne-moi la liste des projets actifs.",
    "Quels sont les leads non contactes cette semaine ?",
]

_ROLES = ["commercial", "delivery", "admin"]


class AgentUser(HttpUser):
    wait_time = between(1, 3)

    @task(1)
    def health(self) -> None:
        self.client.get("/health")

    @task(9)
    def chat(self) -> None:
        self.client.post(
            "/chat",
            json={
                "message": random.choice(_MESSAGES),  # noqa: S311
                "role": random.choice(_ROLES),  # noqa: S311
                "user_id": "load-test-user",
            },
            timeout=30,
        )
