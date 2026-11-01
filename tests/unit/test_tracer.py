"""Tests du tracer JSONL."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from smartops_agent.tracing.tracer import NullTracer, Tracer

pytestmark = pytest.mark.unit


def test_tracer_writes_jsonl(tmp_path: Path) -> None:
    t = Tracer(trace_dir=tmp_path, prompt_version="v1", model_id="mock")
    t.start(user_message="Bonjour", role="commercial", user_id="u1")
    t.llm_step(iteration=0, latency=0.5)
    t.finish(answer="Réponse", iterations=1)

    lines = (tmp_path / "traces.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["role"] == "commercial"
    assert data["iterations"] == 1
    assert data["answer"] == "Réponse"
    assert data["prompt_version"] == "v1"


def test_tracer_masks_pii(tmp_path: Path) -> None:
    t = Tracer(trace_dir=tmp_path)
    t.start(user_message="Contactez john@example.com", role="admin", user_id="u1")
    t.finish(answer="D'accord", iterations=1)
    data = json.loads((tmp_path / "traces.jsonl").read_text(encoding="utf-8").strip())
    assert "john@example.com" not in data["user_message"]
    assert "[EMAIL]" in data["user_message"]


def test_tracer_tool_call_recorded(tmp_path: Path) -> None:
    t = Tracer(trace_dir=tmp_path)
    t.start(user_message="test", role="commercial", user_id="u1")
    t.tool_call("search_crm", {"query": "Acme", "entity": "client"}, {"results": []}, 0.1)
    t.finish(answer="ok", iterations=1)
    data = json.loads((tmp_path / "traces.jsonl").read_text(encoding="utf-8").strip())
    assert any(s["type"] == "tool_call" for s in data["steps"])


def test_tracer_tool_error_recorded(tmp_path: Path) -> None:
    t = Tracer(trace_dir=tmp_path)
    t.start(user_message="test", role="commercial", user_id="u1")
    t.tool_error("search_crm", "NOT_FOUND")
    t.finish(answer="Rien trouvé", iterations=1, escalated=False)
    data = json.loads((tmp_path / "traces.jsonl").read_text(encoding="utf-8").strip())
    assert any(s["type"] == "tool_error" for s in data["steps"])


def test_null_tracer_does_not_write(tmp_path: Path) -> None:
    t = NullTracer()
    t.start(user_message="test", role="commercial", user_id="u1")
    t.finish(answer="ok", iterations=1)
    assert t._data["answer"] == "ok"


def test_tracer_escalated_flag(tmp_path: Path) -> None:
    t = Tracer(trace_dir=tmp_path)
    t.start(user_message="test", role="commercial", user_id="u1")
    t.finish(answer="escaladé", iterations=6, escalated=True)
    data = json.loads((tmp_path / "traces.jsonl").read_text(encoding="utf-8").strip())
    assert data["escalated"] is True
