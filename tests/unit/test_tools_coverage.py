"""Tests pour les chemins non couverts de draft_followup, search_crm, request_human_action."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from smartops_agent.guardrails.approval_queue import ApprovalQueue
from smartops_agent.tools.draft_followup import draft_followup
from smartops_agent.tools.models import (
    DraftFollowupInput,
    EntityType,
    RequestHumanActionInput,
    SearchCrmInput,
    ToneType,
    ToolError,
    ToolErrorCode,
)
from smartops_agent.tools.request_human_action import request_human_action
from smartops_agent.tools.search_crm import search_crm

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path: Path) -> str:
    p = tmp_path / "crm.db"
    con = sqlite3.connect(p)
    con.executescript("""
        CREATE TABLE leads (
            id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT,
            opted_out INTEGER DEFAULT 0
        );
        CREATE TABLE clients (
            id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT
        );
    """)
    con.execute("INSERT INTO leads VALUES ('l1', 'Alice Martin', 'prospect', 0)")
    con.execute("INSERT INTO leads VALUES ('l2', 'Bob Dupont', 'prospect', 1)")
    con.execute("INSERT INTO clients VALUES ('c1', 'Acme', 'active')")
    con.execute("INSERT INTO clients VALUES ('c2', 'Acme Corp', 'active')")
    con.commit()
    con.close()
    return str(p)


# ---------------------------------------------------------------------------
# draft_followup
# ---------------------------------------------------------------------------


def test_draft_followup_forbidden_role(db: str) -> None:
    inp = DraftFollowupInput(lead_id="l1", tone=ToneType.neutral)
    with pytest.raises(ToolError) as exc_info:
        draft_followup(inp, db, role="delivery")
    assert exc_info.value.code == ToolErrorCode.FORBIDDEN


def test_draft_followup_lead_not_found(db: str) -> None:
    inp = DraftFollowupInput(lead_id="unknown", tone=ToneType.neutral)
    with pytest.raises(ToolError) as exc_info:
        draft_followup(inp, db, role="commercial")
    assert exc_info.value.code == ToolErrorCode.NOT_FOUND


def test_draft_followup_opted_out(db: str) -> None:
    inp = DraftFollowupInput(lead_id="l2", tone=ToneType.neutral)
    with pytest.raises(ToolError) as exc_info:
        draft_followup(inp, db, role="commercial")
    assert exc_info.value.code == ToolErrorCode.OPTED_OUT


def test_draft_followup_success_neutral(db: str) -> None:
    inp = DraftFollowupInput(lead_id="l1", tone=ToneType.neutral)
    out = draft_followup(inp, db, role="commercial")
    assert "Suivi" in out.subject
    assert "Alice Martin" in out.body


def test_draft_followup_success_friendly(db: str) -> None:
    inp = DraftFollowupInput(lead_id="l1", tone=ToneType.friendly)
    out = draft_followup(inp, db, role="admin")
    assert "bientôt" in out.body or "bientot" in out.body.lower() or "bien" in out.body


def test_draft_followup_success_formal(db: str) -> None:
    inp = DraftFollowupInput(lead_id="l1", tone=ToneType.formal)
    out = draft_followup(inp, db, role="commercial")
    assert "distinguées" in out.body or "distinguees" in out.body.lower() or "Madame" in out.body


# ---------------------------------------------------------------------------
# search_crm - AMBIGUOUS path (lines 44-46)
# ---------------------------------------------------------------------------


def test_search_crm_ambiguous_names(db: str) -> None:
    # "Acme" matches both "Acme Corp" and "Acme Ltd" - one name contains the other substring
    inp = SearchCrmInput(entity=EntityType.client, query="Acme")
    with pytest.raises(ToolError) as exc_info:
        search_crm(inp, db)
    assert exc_info.value.code == ToolErrorCode.AMBIGUOUS


# ---------------------------------------------------------------------------
# request_human_action - unknown action (line 26)
# ---------------------------------------------------------------------------


def test_request_human_action_unknown(tmp_path: Path) -> None:
    queue = ApprovalQueue()
    inp = RequestHumanActionInput(
        action="wire_transfer",
        reason="test",
        payload={"amount": 1000},
    )
    with pytest.raises(ToolError) as exc_info:
        request_human_action(inp, allowed_actions=["send_email"], queue=queue)
    assert exc_info.value.code == ToolErrorCode.UNKNOWN_ACTION
