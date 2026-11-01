"""Unit tests for evaluation/gates.py and evaluation/run.py (pure functions only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from smartops_agent.evaluation.gates import _eval_gate, run_gates
from smartops_agent.evaluation.run import (
    _check_scenario,
    _infer_outcome,
    _load_scenarios,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _eval_gate
# ---------------------------------------------------------------------------


def test_eval_gate_skipped_when_no_threshold() -> None:
    result = _eval_gate("my_metric", {"operator": ">="}, {"my_metric": 0.9})
    assert result["status"] == "skipped"


def test_eval_gate_passed() -> None:
    result = _eval_gate("score", {"operator": ">=", "threshold": 0.8}, {"score": 0.9})
    assert result["status"] == "passed"
    assert result["value"] == 0.9


def test_eval_gate_failed() -> None:
    result = _eval_gate("score", {"operator": ">=", "threshold": 0.8}, {"score": 0.5})
    assert result["status"] == "failed"


def test_eval_gate_error_unknown_operator() -> None:
    result = _eval_gate("score", {"operator": "??", "threshold": 0.5}, {"score": 0.5})
    assert result["status"] == "error"
    assert "unknown operator" in result["reason"]


def test_eval_gate_error_missing_metric() -> None:
    result = _eval_gate("missing_metric", {"operator": ">=", "threshold": 0.5}, {})
    assert result["status"] == "error"


def test_eval_gate_less_than_operator() -> None:
    result = _eval_gate("error_rate", {"operator": "<=", "threshold": 0.1}, {"error_rate": 0.05})
    assert result["status"] == "passed"


def test_eval_gate_equal_operator() -> None:
    result = _eval_gate("val", {"operator": "==", "threshold": 1.0}, {"val": 1.0})
    assert result["status"] == "passed"


# ---------------------------------------------------------------------------
# run_gates (with temp files)
# ---------------------------------------------------------------------------


def test_run_gates_all_passed(tmp_path: Path) -> None:
    gates_cfg = tmp_path / "gates.yaml"
    metrics_file = tmp_path / "metrics.json"
    gates_report = tmp_path / "gates.json"

    gates_cfg.write_text(
        yaml.dump({"agent": {"score": {"operator": ">=", "threshold": 0.7}}}),
        encoding="utf-8",
    )
    metrics_file.write_text(json.dumps({"score": 0.9}), encoding="utf-8")

    report = run_gates(gates_cfg, metrics_file, gates_report)

    assert report["gates_passed"] is True
    assert report["failed_count"] == 0
    assert gates_report.exists()


def test_run_gates_one_failed(tmp_path: Path) -> None:
    gates_cfg = tmp_path / "gates.yaml"
    metrics_file = tmp_path / "metrics.json"
    gates_report = tmp_path / "gates.json"

    gates_cfg.write_text(
        yaml.dump({"agent": {"score": {"operator": ">=", "threshold": 0.9}}}),
        encoding="utf-8",
    )
    metrics_file.write_text(json.dumps({"score": 0.5}), encoding="utf-8")

    report = run_gates(gates_cfg, metrics_file, gates_report)

    assert report["gates_passed"] is False
    assert report["failed_count"] == 1


def test_run_gates_skipped_null_threshold(tmp_path: Path) -> None:
    gates_cfg = tmp_path / "gates.yaml"
    metrics_file = tmp_path / "metrics.json"
    gates_report = tmp_path / "gates.json"

    gates_cfg.write_text(
        yaml.dump({"agent": {"score": {"operator": ">=", "threshold": None}}}),
        encoding="utf-8",
    )
    metrics_file.write_text(json.dumps({"score": 0.9}), encoding="utf-8")

    report = run_gates(gates_cfg, metrics_file, gates_report)

    assert report["gates_passed"] is True
    assert report["results"][0]["status"] == "skipped"


# ---------------------------------------------------------------------------
# _infer_outcome
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("Je ne peux pas faire cela, interdit.", "refuse"),
        ("Il faut une validation humaine pour cette action.", "escalate"),
        ("Quel projet voulez-vous consulter ?", "ask_clarification"),
        ("Voici les résultats pour Diallo : ...", "answer"),
        ("Cette demande est hors de mon périmètre.", "refuse"),
        ("Transmis à l'équipe pour approbation.", "escalate"),
    ],
)
def test_infer_outcome(answer: str, expected: str) -> None:
    assert _infer_outcome(answer) == expected


def test_infer_outcome_ask_clarification_before_refuse() -> None:
    # "lequel" triggers ask_clarification, not refuse
    answer = "Lequel de vos projets ? impossible de deviner."
    assert _infer_outcome(answer) == "ask_clarification"


# ---------------------------------------------------------------------------
# _check_scenario
# ---------------------------------------------------------------------------


def _make_scenario(**kwargs: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "id": "TST-001",
        "category": "nominal",
        "role": "commercial",
        "input": "test",
        "expected_tools": [],
        "expected_outcome": "answer",
        "checks": {},
    }
    defaults.update(kwargs)
    return defaults


def test_check_scenario_pass_no_checks() -> None:
    sc = _make_scenario(expected_outcome="answer")
    result = _check_scenario(sc, "Voici la réponse.", [])
    assert result["passed"] is True


def test_check_scenario_fail_contains_any_missing() -> None:
    sc = _make_scenario(checks={"contains_any": ["Diallo", "trouvé"]})
    result = _check_scenario(sc, "Je n'ai rien trouvé.", [])
    # "trouvé" IS in the answer — should pass
    assert result["passed"] is True


def test_check_scenario_fail_contains_any_no_match() -> None:
    sc = _make_scenario(checks={"contains_any": ["Diallo"]})
    result = _check_scenario(sc, "Aucun résultat.", [])
    assert result["passed"] is False
    assert result["details"]["contains_any"] is False


def test_check_scenario_fail_not_contains_violation() -> None:
    sc = _make_scenario(checks={"not_contains": ["secret"]})
    result = _check_scenario(sc, "Voici le secret de la commission.", [])
    assert result["passed"] is False
    assert result["details"]["not_contains"] is False


def test_check_scenario_tool_ok_when_tool_called() -> None:
    sc = _make_scenario(expected_tools=["search_crm"])
    result = _check_scenario(sc, "Résultat trouvé.", ["search_crm"])
    assert result["tool_ok"] is True


def test_check_scenario_tool_not_ok_when_tool_missing() -> None:
    sc = _make_scenario(expected_tools=["search_crm"])
    result = _check_scenario(sc, "Résultat trouvé.", [])
    assert result["tool_ok"] is False


def test_check_scenario_outcome_mismatch_fails() -> None:
    sc = _make_scenario(expected_outcome="refuse")
    result = _check_scenario(sc, "Voici la réponse.", [])
    # inferred = "answer", expected = "refuse" → mismatch
    assert result["passed"] is False
    assert result["details"]["outcome_match"] is False


# ---------------------------------------------------------------------------
# _load_scenarios
# ---------------------------------------------------------------------------


def test_load_scenarios_valid(tmp_path: Path) -> None:
    f = tmp_path / "scenarios.jsonl"
    rows = [
        {"id": "A-001", "category": "nominal"},
        {"id": "A-002", "category": "error"},
    ]
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    loaded = _load_scenarios(f)
    assert len(loaded) == 2
    assert loaded[0]["id"] == "A-001"


def test_load_scenarios_skips_blank_lines(tmp_path: Path) -> None:
    f = tmp_path / "scenarios.jsonl"
    f.write_text('{"id": "X-001"}\n\n{"id": "X-002"}\n', encoding="utf-8")
    loaded = _load_scenarios(f)
    assert len(loaded) == 2
