"""Quality gates: reads reports/eval/metrics.json and configs/gates.yaml.

Usage (via DVC): python -m smartops_agent.evaluation.gates
Exit code 0 = all gates passed.  Exit code 1 = one or more gates failed.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

from smartops_agent.config import PROJECT_ROOT

log = logging.getLogger(__name__)

GATES_CONFIG = PROJECT_ROOT / "configs" / "gates.yaml"
METRICS_FILE = PROJECT_ROOT / "reports" / "eval" / "metrics.json"
GATES_REPORT = PROJECT_ROOT / "reports" / "eval" / "gates.json"

_OPERATOR_FN = {
    "==": lambda v, t: v == t,
    ">=": lambda v, t: v >= t,
    "<=": lambda v, t: v <= t,
    ">": lambda v, t: v > t,
    "<": lambda v, t: v < t,
}


def _eval_gate(gate_id: str, gate_cfg: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    threshold = gate_cfg.get("threshold")
    if threshold is None:
        return {
            "id": gate_id,
            "status": "skipped",
            "reason": "threshold not set (baseline pending)",
        }

    operator = gate_cfg.get("operator", ">=")
    fn = _OPERATOR_FN.get(operator)
    if fn is None:
        return {"id": gate_id, "status": "error", "reason": f"unknown operator: {operator}"}

    value = metrics.get(gate_id)
    if value is None:
        return {
            "id": gate_id,
            "status": "error",
            "reason": f"metric '{gate_id}' not in metrics.json",
        }

    passed = fn(value, threshold)
    return {
        "id": gate_id,
        "status": "passed" if passed else "failed",
        "value": value,
        "threshold": threshold,
        "operator": operator,
        "justification": gate_cfg.get("justification", ""),
    }


def run_gates(
    gates_config: Path = GATES_CONFIG,
    metrics_file: Path = METRICS_FILE,
    gates_report: Path = GATES_REPORT,
) -> dict[str, Any]:
    with gates_config.open(encoding="utf-8") as fh:
        gates_cfg: dict[str, Any] = yaml.safe_load(fh)
    with metrics_file.open(encoding="utf-8") as fh:
        metrics: dict[str, Any] = json.load(fh)

    flat_metrics: dict[str, Any] = {k: v for k, v in metrics.items() if not isinstance(v, dict)}
    flat_metrics["llm_stub"] = metrics.get("llm_stub", False)

    results: list[dict[str, Any]] = []
    failed = 0

    agent_gates = gates_cfg.get("agent", {})
    for gate_id, gate_cfg in agent_gates.items():
        result = _eval_gate(gate_id, gate_cfg, flat_metrics)
        results.append(result)
        if result["status"] == "failed":
            failed += 1
            log.error(
                "GATE FAILED: %s = %s (expected %s %s)",
                gate_id,
                result.get("value"),
                gate_cfg.get("operator"),
                gate_cfg.get("threshold"),
            )
        elif result["status"] == "passed":
            log.info("gate passed: %s = %s", gate_id, result.get("value"))
        else:
            log.info("gate %s: %s", result["status"], gate_id)

    report: dict[str, Any] = {
        "gates_passed": failed == 0,
        "failed_count": failed,
        "results": results,
    }
    gates_report.parent.mkdir(parents=True, exist_ok=True)
    gates_report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Gates report: %d failed / %d evaluated", failed, len(results))
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = run_gates()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(0 if report["gates_passed"] else 1)
