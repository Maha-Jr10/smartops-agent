from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from smartops_agent.data.seed_traces import _make_trace, delete_traces, seed_traces

pytestmark = pytest.mark.unit


def test_make_trace_creates_tool_and_llm_steps() -> None:
    for is_reference in (True, False):
        trace = _make_trace(random.Random(42), is_reference=is_reference)  # noqa: S311

        assert trace["role"] in {"commercial", "delivery", "admin"}
        assert trace["steps"][-1]["type"] == "llm_call"
        assert all(step["type"] == "tool_call" for step in trace["steps"][:-1])
        assert len(trace["steps"]) >= 2


def test_seed_traces_is_deterministic_and_writes_jsonl(tmp_path: Path) -> None:
    first = tmp_path / "first" / "traces.jsonl"
    second = tmp_path / "second" / "traces.jsonl"

    assert seed_traces(first, n_reference=3, n_current=2) == 5
    assert seed_traces(second, n_reference=3, n_current=2) == 5
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    assert len([json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]) == 5


def test_delete_traces_reports_whether_file_existed(tmp_path: Path) -> None:
    traces = tmp_path / "traces.jsonl"

    assert delete_traces(traces) is False
    traces.write_text("{}", encoding="utf-8")
    assert delete_traces(traces) is True
    assert not traces.exists()
