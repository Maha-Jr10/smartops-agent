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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# pandas 3.x removed infer_dtype_from_object; patch it back for evidently legacy.
# pandas is an optional (mlops) dep — skip the patch when it isn't installed.
try:
    import pandas.core.dtypes.common as _pd_common

    if not hasattr(_pd_common, "infer_dtype_from_object"):

        def _infer_dtype_from_object(dtype: object) -> type:
            return dtype if isinstance(dtype, type) else object

        _pd_common.infer_dtype_from_object = _infer_dtype_from_object
except ModuleNotFoundError:
    pass

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


def _download_traces_from_supabase(traces_path: Path) -> bool:
    """Download traces JSONL from Supabase Storage if the local file is missing."""
    try:
        from smartops_agent.config import get_settings

        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return False
        from supabase import create_client

        client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key.get_secret_value(),
        )
        content: bytes = client.storage.from_("reports").download("traces/traces.jsonl")
        if not content:
            return False
        traces_path.parent.mkdir(parents=True, exist_ok=True)
        traces_path.write_bytes(content)
        log.info("Traces downloaded from Supabase Storage (%d bytes)", len(content))
        return True
    except Exception:
        log.debug("Could not download traces from Supabase Storage", exc_info=True)
        return False


def run_report(
    traces_path: Path = _TRACES_FILE,
    report_path: Path = _REPORT_FILE,
) -> bool:
    """Generate Evidently drift report. Returns True if report was written."""
    try:
        import pandas as pd
        from evidently.legacy.metric_preset import DataDriftPreset
        from evidently.legacy.pipeline.column_mapping import ColumnMapping
        from evidently.legacy.report import Report
    except ImportError as exc:
        log.error("Evidently ou pandas manquant : %s", exc)
        return False

    if not traces_path.exists():
        _download_traces_from_supabase(traces_path)

    traces = _load_traces(traces_path)
    if len(traces) < _MIN_ROWS:
        log.warning(
            "Pas assez de traces (%d < %d) pour generer un rapport de derive.",
            len(traces),
            _MIN_ROWS,
        )
        _store_monitoring_alert(
            drift_detected=False, drifted_columns=[], status="insufficient_data"
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

    # Detect whether drift was found before saving
    drift_detected = False
    drifted_cols: list[str] = []
    try:
        result_dict = report.as_dict()
        for m in result_dict.get("metrics", []):
            r = m.get("result", {})
            if "dataset_drift" in r:
                drift_detected = bool(r["dataset_drift"])
                by_col = r.get("drift_by_columns", {})
                drifted_cols = [c for c, v in by_col.items() if v.get("drift_detected")]
                break
    except Exception:
        log.debug("Could not parse Evidently drift result", exc_info=True)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(report_path))
    log.info("Rapport de derive genere : %s", report_path)
    _log_to_mlflow(
        report_path=report_path,
        trace_count=len(traces),
        reference_count=len(reference),
        current_count=len(current),
        drift_detected=drift_detected,
        drifted_columns=drifted_cols,
    )
    _upload_to_supabase(report_path)
    _store_monitoring_alert(drift_detected=drift_detected, drifted_columns=drifted_cols)
    return True


def _log_to_mlflow(
    report_path: Path,
    trace_count: int,
    reference_count: int,
    current_count: int,
    drift_detected: bool,
    drifted_columns: list[str],
) -> None:
    """Log the generated drift report and summary metrics to MLflow."""
    try:
        import mlflow
    except ImportError as exc:
        log.warning("MLflow manquant; rapport non journalise dans MLflow : %s", exc)
        return

    try:
        from smartops_agent.config import get_settings

        mlflow.set_tracking_uri(get_settings().mlflow_tracking_uri)
        mlflow.set_experiment("smartops-agent-monitoring")
        with mlflow.start_run(run_name="evidently-drift-report"):
            mlflow.log_params(
                {
                    "trace_count": trace_count,
                    "reference_count": reference_count,
                    "current_count": current_count,
                    "drifted_columns": ", ".join(drifted_columns) or "none",
                }
            )
            mlflow.log_metrics(
                {
                    "drift_detected": float(drift_detected),
                    "drifted_column_count": len(drifted_columns),
                }
            )
            mlflow.log_artifact(str(report_path), artifact_path="evidently")
    except Exception:
        log.exception("Echec de la journalisation du rapport Evidently dans MLflow")


def _upload_to_supabase(html_path: Path) -> bool:
    """Upload the HTML report to Supabase Storage bucket 'reports'."""
    try:
        from smartops_agent.config import get_settings

        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return False
        from supabase import create_client

        client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key.get_secret_value(),
        )
        with html_path.open("rb") as fh:
            content = fh.read()
        client.storage.from_("reports").upload(
            "monitoring/drift_report.html",
            content,
            {"contentType": "text/html", "upsert": "true"},  # type: ignore[arg-type]
        )
        log.info("Rapport uploade dans Supabase Storage : reports/monitoring/drift_report.html")
        return True
    except Exception:
        log.warning("Upload Supabase Storage echoue; rapport disponible localement.", exc_info=True)
        return False


def _store_monitoring_alert(
    drift_detected: bool,
    drifted_columns: list[str],
    status: str | None = None,
) -> None:
    """Persist the latest monitoring result to Supabase app_settings."""
    effective_status = status or ("drift_detected" if drift_detected else "ok")
    if effective_status == "drift_detected":
        message = f"Derive detectee dans : {', '.join(drifted_columns) or 'colonnes inconnues'}."
    elif effective_status == "insufficient_data":
        message = "Donnees insuffisantes. Injectez des donnees de demo ou attendez plus de traces."
    else:
        message = "Aucune derive significative detectee."

    alert: dict[str, Any] = {
        "status": effective_status,
        "last_run": datetime.now(UTC).isoformat(),
        "drifted_columns": drifted_columns,
        "message": message,
    }
    try:
        from smartops_agent.config import get_settings

        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return
        from supabase import create_client

        client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key.get_secret_value(),
        )
        client.table("app_settings").upsert(
            {"key": "monitoring_alert", "value": json.dumps(alert)}
        ).execute()
        log.debug("Monitoring alert stored: %s", effective_status)
    except Exception:
        log.debug("Could not store monitoring alert in Supabase", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ok = run_report()
    raise SystemExit(0 if ok else 1)
