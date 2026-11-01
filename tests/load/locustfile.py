"""Test de charge. Pour l'instant sur /health ; la route de l'agent sera ajoutée en phase 1."""

from locust import HttpUser, between, task


class AgentUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def health(self) -> None:
        self.client.get("/health")
