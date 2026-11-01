"""Tests des garde-fous : permissions, PII, file d'approbation."""

from __future__ import annotations

import pytest

from smartops_agent.guardrails.approval_queue import ApprovalQueue
from smartops_agent.guardrails.permissions import (
    check_permission,
    get_allowed_human_actions,
    is_own_only_scope,
)
from smartops_agent.guardrails.pii import mask_pii, mask_pii_in_dict
from smartops_agent.tools.models import ToolError, ToolErrorCode

pytestmark = pytest.mark.unit


# --- Permissions ---


def test_commercial_can_search_crm() -> None:
    check_permission("search_crm", "commercial")  # should not raise


def test_delivery_cannot_get_invoice() -> None:
    with pytest.raises(ToolError) as exc_info:
        check_permission("get_invoice_status", "delivery")
    assert exc_info.value.code == ToolErrorCode.FORBIDDEN


def test_all_roles_can_request_human_action() -> None:
    for role in ("commercial", "delivery", "admin"):
        check_permission("request_human_action", role)


def test_calculate_commission_own_only_for_non_admin() -> None:
    assert is_own_only_scope("calculate_commission", "commercial") is True
    assert is_own_only_scope("calculate_commission", "delivery") is True
    assert is_own_only_scope("calculate_commission", "admin") is False


def test_risky_actions_in_policy() -> None:
    actions = get_allowed_human_actions()
    assert "send_email" in actions
    assert "mark_commission_paid" in actions
    assert "delete_record" in actions


# --- PII masking ---


def test_email_masked() -> None:
    result = mask_pii("Contact: john.doe@example.com pour plus d'info")
    assert "[EMAIL]" in result
    assert "john.doe@example.com" not in result


def test_phone_masked() -> None:
    result = mask_pii("Appelez-nous au +224612345678")
    assert "[PHONE]" in result


def test_mask_pii_in_nested_dict() -> None:
    data = {
        "name": "Alice",
        "email": "alice@example.com",
        "contacts": [{"phone": "+224698765432"}],
    }
    masked = mask_pii_in_dict(data)
    assert "[EMAIL]" in masked["email"]
    assert "[PHONE]" in masked["contacts"][0]["phone"]
    assert masked["name"] == "Alice"


# --- ApprovalQueue ---


def test_queue_enqueue_and_get() -> None:
    q = ApprovalQueue()
    q.enqueue("req1", "send_email", "Relance client", {"to": "x@y.com"})
    items = q.get_all()
    assert len(items) == 1
    assert items[0]["status"] == "pending"
    assert items[0]["action"] == "send_email"


def test_queue_approve() -> None:
    q = ApprovalQueue()
    q.enqueue("req2", "mark_commission_paid", "Paiement validé", {})
    ok = q.approve("req2", "approved", "OK")
    assert ok is True
    item = q.get("req2")
    assert item is not None
    assert item["status"] == "approved"


def test_queue_approve_nonexistent_returns_false() -> None:
    q = ApprovalQueue()
    assert q.approve("nonexistent", "approved") is False
