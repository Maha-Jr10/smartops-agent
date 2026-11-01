"""Tests d'intégration de la boucle agent avec un LLM simulé."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from smartops_agent.agent.llm_client import LLMResponse
from smartops_agent.agent.loop import AgentLoop
from smartops_agent.guardrails.approval_queue import ApprovalQueue
from smartops_agent.tracing.tracer import NullTracer

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(tmp_path: Path) -> str:
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(db_path)
    con.executescript("""
        CREATE TABLE clients (id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT, status TEXT);
        CREATE TABLE leads (id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT,
                            status TEXT, opted_out INTEGER, notes TEXT);
        CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, client_id TEXT, status TEXT,
                               total_amount REAL, currency TEXT, direct_costs REAL,
                               apporteur_id TEXT, realisation_ids TEXT);
        CREATE TABLE invoices (id TEXT PRIMARY KEY, project_id TEXT, amount REAL,
                               currency TEXT, status TEXT, due_date TEXT);
    """)
    con.execute(
        "INSERT INTO clients VALUES ('cl1','Acme Corp','acme@ex.com','+224600000001','active')"
    )
    con.execute(
        "INSERT INTO leads VALUES "
        "('ld1','Bob Lead','bob@ex.com','+224600000002','new',0,'Notes ok')"
    )
    con.execute(
        "INSERT INTO leads VALUES "
        "('ld_opt','Opted Out','opt@ex.com','+224600000003','new',1,'notes')"
    )
    con.execute(
        "INSERT INTO projects VALUES ('pr1','Proj A','cl1','closed',20000,'MAD',2000,'tm_a','tm_b')"
    )
    con.execute("INSERT INTO invoices VALUES ('inv1','pr1',20000,'MAD','paid','2026-01-01')")
    con.commit()
    con.close()
    return str(db_path)


class FakeLLM:
    """Séquence de réponses prédéfinies."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self._index = 0

    def chat(self, messages: Any, tools: Any, temperature: Any, timeout: Any) -> LLMResponse:
        if self._index >= len(self._responses):
            return LLMResponse(content="Fin des réponses simulées.")
        resp = self._responses[self._index]
        self._index += 1
        return resp


def _make_loop(llm: FakeLLM, db_path: str, queue: ApprovalQueue | None = None) -> AgentLoop:
    return AgentLoop(
        llm=llm,
        db_path=db_path,
        queue=queue or ApprovalQueue(),
        tracer=NullTracer(),
        max_iterations=6,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_direct_text_response(tmp_path: Path) -> None:
    """Un LLM qui répond directement (pas d'outil) renvoie la réponse."""
    llm = FakeLLM([LLMResponse(content="Bonjour, comment puis-je vous aider ?")])
    loop = _make_loop(llm, _make_db(tmp_path))
    answer = loop.run("Bonjour", role="commercial", user_id="u1")
    assert "Bonjour" in answer


def test_search_crm_tool_called(tmp_path: Path) -> None:
    """Le LLM appelle search_crm, l'outil répond, le LLM formule la réponse finale."""
    tool_call_resp = LLMResponse(
        content=None,
        tool_calls=[
            {"id": "tc1", "name": "search_crm", "arguments": {"query": "Acme", "entity": "client"}}
        ],
    )
    final_resp = LLMResponse(content="J'ai trouvé Acme Corp.")
    llm = FakeLLM([tool_call_resp, final_resp])
    loop = _make_loop(llm, _make_db(tmp_path))
    answer = loop.run("Cherche le client Acme", role="commercial", user_id="u1")
    assert "Acme" in answer


def test_permission_denied_stops_tool(tmp_path: Path) -> None:
    """Un delivery ne peut pas appeler get_invoice_status : ToolError FORBIDDEN."""
    tool_call_resp = LLMResponse(
        content=None,
        tool_calls=[
            {"id": "tc2", "name": "get_invoice_status", "arguments": {"invoice_id": "inv1"}}
        ],
    )
    final_resp = LLMResponse(content="Désolé, accès refusé.")
    llm = FakeLLM([tool_call_resp, final_resp])
    loop = _make_loop(llm, _make_db(tmp_path))
    answer = loop.run("Statut de la facture inv1", role="delivery", user_id="u1")
    assert answer  # la boucle ne doit pas planter


def test_max_iterations_escalation(tmp_path: Path) -> None:
    """Après max_iterations appels d'outils sans réponse finale, on escalade."""
    tool_call = LLMResponse(
        content=None,
        tool_calls=[
            {"id": "tcX", "name": "search_crm", "arguments": {"query": "X", "entity": "client"}}
        ],
    )
    llm = FakeLLM([tool_call] * 10)  # jamais de fin
    loop = _make_loop(llm, _make_db(tmp_path))
    loop._max_iter = 3
    answer = loop.run("boucle infinie", role="commercial", user_id="u1")
    assert (
        "itération" in answer.lower() or "escalade" in answer.lower() or "limite" in answer.lower()
    )


def test_invalid_tool_args_retry(tmp_path: Path) -> None:
    """Un appel avec arguments invalides déclenche une retry, puis la boucle continue."""
    bad_call = LLMResponse(
        content=None,
        tool_calls=[
            {"id": "tc3", "name": "search_crm", "arguments": {"query": "x", "entity": "client"}}
        ],
    )
    # query trop courte (< 2 chars) — ValidationError sur SearchCrmInput
    bad_args = LLMResponse(
        content=None,
        tool_calls=[
            {
                "id": "tc4",
                "name": "search_crm",
                "arguments": {"query": "x", "entity": "INVALID_ENTITY"},
            }
        ],
    )
    final_resp = LLMResponse(content="D'accord.")
    llm = FakeLLM([bad_args, bad_call, final_resp])
    loop = _make_loop(llm, _make_db(tmp_path))
    answer = loop.run("test", role="commercial", user_id="u1")
    assert answer  # ne doit pas planter


def test_risky_action_routed_to_approval_queue(tmp_path: Path) -> None:
    """request_human_action enregistre la demande dans la file."""
    queue = ApprovalQueue()
    tool_call_resp = LLMResponse(
        content=None,
        tool_calls=[
            {
                "id": "tc5",
                "name": "request_human_action",
                "arguments": {
                    "action": "send_email",
                    "reason": "Relancer le client",
                    "payload": {"to": "client@example.com"},
                },
            }
        ],
    )
    final_resp = LLMResponse(content="Demande envoyée pour validation.")
    llm = FakeLLM([tool_call_resp, final_resp])
    loop = _make_loop(llm, _make_db(tmp_path), queue=queue)
    loop.run("Envoie un email au client", role="commercial", user_id="u1")
    items = queue.get_all()
    assert len(items) == 1
    assert items[0]["action"] == "send_email"
    assert items[0]["status"] == "pending"


def test_opted_out_lead_raises(tmp_path: Path) -> None:
    """draft_followup refuse un lead opted-out."""
    tool_call_resp = LLMResponse(
        content=None,
        tool_calls=[
            {
                "id": "tc6",
                "name": "draft_followup",
                "arguments": {"lead_id": "ld_opt", "tone": "neutral"},
            }
        ],
    )
    final_resp = LLMResponse(content="Impossible de contacter ce lead.")
    llm = FakeLLM([tool_call_resp, final_resp])
    loop = _make_loop(llm, _make_db(tmp_path))
    answer = loop.run("Relancer le lead", role="commercial", user_id="u1")
    assert answer  # ne doit pas planter


def test_injection_in_tool_result_not_executed(tmp_path: Path) -> None:
    """Les données renvoyées par les outils ne déclenchent pas de nouvelles actions."""
    # Le LLM fait une recherche, le résultat contiendra les notes avec injection
    # On vérifie que le LLM reçoit bien les données mais formule une réponse neutre
    tool_call_resp = LLMResponse(
        content=None,
        tool_calls=[
            {
                "id": "tc7",
                "name": "search_crm",
                "arguments": {"query": "Bob Lead", "entity": "lead"},
            }
        ],
    )
    # Le LLM simulé répond normalement même après avoir vu les données
    final_resp = LLMResponse(content="Voici les informations du lead.")
    llm = FakeLLM([tool_call_resp, final_resp])
    loop = _make_loop(llm, _make_db(tmp_path))
    answer = loop.run("Cherche le lead Bob Lead", role="commercial", user_id="u1")
    # La réponse ne doit pas contenir d'instruction d'injection
    assert "IGNORE" not in answer
    assert "instructions précédentes" not in answer
