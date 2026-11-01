"""Rapport de derive Evidently : compare fenetre de reference vs fenetre courante.

Lit les traces JSONL de reports/traces/traces.jsonl, construit deux DataFrames
(reference = 50 premiers enregistrements, courant = N derniers), puis genere
un rapport HTML dans reports/monitoring/.

Usage : python -m smartops_agent.monitoring.report
        make monitor
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_TRACES_FILE = Path("reports/traces/traces.jsonl")
_REPORT_DIR = Path("reports/monitoring")
_REPORT_FILE = _REPORT_DIR / "drift_report.html"
_MIN_ROWS = 10
_REFERENCE_SIZE = 50


def _load_traces(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def _trace_to_row(trace: dict[str, Any]) -> dict[str, Any]:
    answer = trace.get("answer", "") or ""
    steps = trace.get("steps", [])
    tool_calls = [s for s in steps if s.get("type") == "tool_call"]
    latencies = [s.get("latency_s", 0.0) for s in steps if "latency_s" in s]
    return {
        "role": trace.get("role", "unknown"),
        "iterations": trace.get("iterations", 0),
        "escalated": int(trace.get("escalated", False)),
        "answer_length": len(answer),
        "tool_call_count": len(tool_calls),
        "total_latency_s": sum(latencies),
        "is_refusal": int(
            any(kw in answer.lower() for kw in ["interdit", "ne peux pas", "hors de mon"])
        ),
    }


def run_report(
    traces_path: Path = _TRACES_FILE,
    report_path: Path = _REPORT_FILE,
) -> bool:
    """Generate Evidently drift report. Returns True if report was written."""
    try:
        import pandas as pd
        from evidently import ColumnMapping
        from evidently.metric_preset import DataDriftPreset
        from evidently.report import Report
    except ImportError as exc:
        log.error("Evidently ou pandas manquant : %s", exc)
        return False

    traces = _load_traces(traces_path)
    if len(traces) < _MIN_ROWS:
        log.warning(
            "Pas assez de traces (%d < %d) pour generer un rapport de derive.",
            len(traces),
            _MIN_ROWS,
        )
        return False

    rows = [_trace_to_row(t) for t in traces]
    df = pd.DataFrame(rows)

    ref_size = min(_REFERENCE_SIZE, len(df) // 2)
    reference = df.iloc[:ref_size].reset_index(drop=True)
    current = df.iloc[ref_size:].reset_index(drop=True)

    if current.empty:
        log.warning("Fenetre courante vide apres decoupage.")
        return False

    column_mapping = ColumnMapping(
        target=None,
        numerical_features=["iterations", "answer_length", "tool_call_count", "total_latency_s"],
        categorical_features=["role", "escalated", "is_refusal"],
    )

    report = Report(metrics=[DataDriftPreset()])
    report.run(
        reference_data=reference,
        current_data=current,
        column_mapping=column_mapping,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(report_path))
    log.info("Rapport de derive genere : %s", report_path)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ok = run_report()
    raise SystemExit(0 if ok else 1)
