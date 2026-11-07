"""File de validation humaine en mémoire (thread-safe, persistée en JSON pour l'API)."""

from __future__ import annotations

import threading
import time
from typing import Any


class ApprovalQueue:
    """Stocke les demandes d'actions à effet métier en attente de validation humaine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, dict[str, Any]] = {}

    def enqueue(
        self,
        request_id: str,
        action: str,
        reason: str,
        payload: dict[str, Any],
        requested_by: str = "",
        role: str = "",
    ) -> None:
        with self._lock:
            self._items[request_id] = {
                "id": request_id,
                "action": action,
                "reason": reason,
                "payload": payload,
                "status": "pending",
                "requested_by": requested_by,
                "role": role,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

    def get_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._items.values())

    def get(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._items.get(request_id)

    def approve(self, request_id: str, decision: str, comment: str = "") -> bool:
        """Enregistre la décision (approved | rejected). Retourne False si non trouvé."""
        with self._lock:
            item = self._items.get(request_id)
            if item is None:
                return False
            item["status"] = decision
            item["comment"] = comment
            return True


# Instance globale — remplacée par injection de dépendance dans les tests
_queue = ApprovalQueue()


def get_queue() -> ApprovalQueue:
    return _queue
