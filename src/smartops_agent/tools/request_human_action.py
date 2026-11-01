"""Outil request_human_action : seule voie vers une action à effet métier réel."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from smartops_agent.tools.models import (
    RequestHumanActionInput,
    RequestHumanActionOutput,
    ToolError,
    ToolErrorCode,
)

if TYPE_CHECKING:
    from smartops_agent.guardrails.approval_queue import ApprovalQueue


def request_human_action(
    inp: RequestHumanActionInput,
    allowed_actions: list[str],
    queue: ApprovalQueue,
) -> RequestHumanActionOutput:
    """Enregistre une demande dans la file d'attente pour validation humaine."""
    if inp.action not in allowed_actions:
        raise ToolError(
            ToolErrorCode.UNKNOWN_ACTION,
            f"Action inconnue : « {inp.action} ». "
            f"Actions autorisées : {', '.join(allowed_actions)}",
        )
    request_id = str(uuid.uuid4())
    queue.enqueue(request_id, inp.action, inp.reason, inp.payload)
    return RequestHumanActionOutput(request_id=request_id, status="pending")
