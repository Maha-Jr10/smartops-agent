"""Tests du module monitoring.report."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smartops_agent.monitoring.report import (
    _load_traces,
    _trace_to_row,
    _upload_to_supabase,
    run_report,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _load_traces
# ---------------------------------------------------------------------------


def test_load_traces_missing_file(tmp_path: Path) -> None:
    result = _load_traces(tmp_path / "nonexistent.jsonl")
    assert result == []


def test_load_traces_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "traces.jsonl"
    p.write_text("", encoding="utf-8")
    assert _load_traces(p) == []


def test_load_traces_valid_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "traces.jsonl"
    p.write_text(
        json.dumps({"role": "commercial", "answer": "ok"})
        + "\n"
        + json.dumps({"role": "admin", "answer": "yes"})
        + "\n",
        encoding="utf-8",
    )
    rows = _load_traces(p)
    assert len(rows) == 2
    assert rows[0]["role"] == "commercial"
    assert rows[1]["role"] == "admin"


def test_load_traces_skips_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "traces.jsonl"
    p.write_text(
        json.dumps({"role": "commercial"})
        + "\n"
        + "not-valid-json\n"
        + json.dumps({"role": "admin"})
        + "\n",
        encoding="utf-8",
    )
    rows = _load_traces(p)
    assert len(rows) == 2


def test_load_traces_skips_blank_lines(tmp_path: Path) -> None:
    p = tmp_path / "traces.jsonl"
    p.write_text(
        "\n" + json.dumps({"role": "commercial"}) + "\n" + "   \n",
        encoding="utf-8",
    )
    rows = _load_traces(p)
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# _trace_to_row
# ---------------------------------------------------------------------------


def test_trace_to_row_minimal() -> None:
    row = _trace_to_row({})
    assert row["role"] == "unknown"
    assert row["iterations"] == 0
    assert row["escalated"] == 0
    assert row["answer_length"] == 0
    assert row["tool_call_count"] == 0
    assert row["total_latency_s"] == 0
    assert row["is_refusal"] == 0


def test_trace_to_row_full() -> None:
    trace = {
        "role": "commercial",
        "iterations": 3,
        "escalated": True,
        "answer": "Voici la réponse",
        "steps": [
            {"type": "tool_call", "latency_s": 0.5},
            {"type": "llm", "latency_s": 1.2},
            {"type": "tool_call", "latency_s": 0.3},
        ],
    }
    row = _trace_to_row(trace)
    assert row["role"] == "commercial"
    assert row["iterations"] == 3
    assert row["escalated"] == 1
    assert row["answer_length"] == len("Voici la réponse")
    assert row["tool_call_count"] == 2
    assert abs(row["total_latency_s"] - 2.0) < 1e-9
    assert row["is_refusal"] == 0


def test_trace_to_row_refusal_keywords() -> None:
    for keyword in ["interdit", "ne peux pas", "hors de mon"]:
        row = _trace_to_row({"answer": f"Cela est {keyword} ici"})
        assert row["is_refusal"] == 1, f"Expected refusal for keyword '{keyword}'"


def test_trace_to_row_none_answer() -> None:
    row = _trace_to_row({"answer": None})
    assert row["answer_length"] == 0
    assert row["is_refusal"] == 0


# ---------------------------------------------------------------------------
# run_report
# ---------------------------------------------------------------------------


def _make_traces_file(path: Path, n: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(n):
        lines.append(
            json.dumps(
                {
                    "role": "commercial" if i % 2 == 0 else "admin",
                    "iterations": 1,
                    "escalated": False,
                    "answer": "Réponse test",
                    "steps": [{"type": "tool_call", "latency_s": 0.1}],
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_run_report_too_few_traces(tmp_path: Path) -> None:
    traces = tmp_path / "traces.jsonl"
    report = tmp_path / "report.html"
    _make_traces_file(traces, 5)
    result = run_report(traces_path=traces, report_path=report)
    assert result is False
    assert not report.exists()


def _mock_evidently_modules() -> dict[str, MagicMock]:
    """Return sys.modules patches for evidently legacy imports."""
    mock_report_instance = MagicMock()

    mod_report = MagicMock()
    mod_report.Report = MagicMock(return_value=mock_report_instance)

    mod_preset = MagicMock()
    mod_preset.DataDriftPreset = MagicMock()

    mod_cm = MagicMock()
    mod_cm.ColumnMapping = MagicMock()

    return {
        "evidently": MagicMock(),
        "evidently.legacy": MagicMock(),
        "evidently.legacy.report": mod_report,
        "evidently.legacy.metric_preset": mod_preset,
        "evidently.legacy.pipeline": MagicMock(),
        "evidently.legacy.pipeline.column_mapping": mod_cm,
        "_mock_report_instance": mock_report_instance,  # for assertions
    }


def _mock_pandas_module() -> MagicMock:
    """Return a sys.modules mock for pandas (not installed in CI's dev group)."""
    mock_current = MagicMock()
    mock_current.empty = False
    mock_slice = MagicMock()
    mock_slice.reset_index.return_value = mock_current
    mock_df_instance = MagicMock()
    mock_df_instance.iloc.__getitem__.return_value = mock_slice
    mock_pd = MagicMock()
    mock_pd.DataFrame.return_value = mock_df_instance
    return mock_pd


def test_run_report_success(tmp_path: Path) -> None:
    traces = tmp_path / "traces.jsonl"
    report = tmp_path / "report.html"
    _make_traces_file(traces, 20)

    mocks = _mock_evidently_modules()
    mock_report_instance = mocks.pop("_mock_report_instance")
    sys_mods = {**mocks, "pandas": _mock_pandas_module()}

    with (
        patch.dict("sys.modules", sys_mods),
        patch("smartops_agent.monitoring.report._upload_to_supabase", return_value=False),
    ):
        result = run_report(traces_path=traces, report_path=report)

    assert result is True
    mock_report_instance.save_html.assert_called_once()


def test_run_report_missing_evidently_returns_false(tmp_path: Path) -> None:
    traces = tmp_path / "traces.jsonl"
    report = tmp_path / "report.html"
    _make_traces_file(traces, 20)

    # Remove evidently from sys.modules so the import raises ImportError
    with patch.dict(
        "sys.modules",
        {"evidently.legacy.report": None},
    ):
        result = run_report(traces_path=traces, report_path=report)

    assert result is False


# ---------------------------------------------------------------------------
# _upload_to_supabase
# ---------------------------------------------------------------------------


def test_upload_to_supabase_no_credentials(tmp_path: Path) -> None:
    html = tmp_path / "report.html"
    html.write_text("<html/>", encoding="utf-8")

    mock_settings = MagicMock()
    mock_settings.supabase_url = None
    mock_settings.supabase_service_role_key = None

    with patch("smartops_agent.config.get_settings", return_value=mock_settings):
        result = _upload_to_supabase(html)

    assert result is False


def test_upload_to_supabase_success(tmp_path: Path) -> None:
    html = tmp_path / "report.html"
    html.write_text("<html>drift</html>", encoding="utf-8")

    mock_settings = MagicMock()
    mock_settings.supabase_url = "https://fake.supabase.co"
    mock_key = MagicMock()
    mock_key.get_secret_value.return_value = "fake-service-key"
    mock_settings.supabase_service_role_key = mock_key

    mock_client = MagicMock()

    with (
        patch("smartops_agent.config.get_settings", return_value=mock_settings),
        patch("supabase.create_client", return_value=mock_client),
    ):
        result = _upload_to_supabase(html)

    assert result is True
    mock_client.storage.from_.assert_called_once_with("reports")


def test_upload_to_supabase_exception_returns_false(tmp_path: Path) -> None:
    html = tmp_path / "report.html"
    html.write_text("<html/>", encoding="utf-8")

    mock_settings = MagicMock()
    mock_settings.supabase_url = "https://fake.supabase.co"
    mock_key = MagicMock()
    mock_key.get_secret_value.return_value = "fake-key"
    mock_settings.supabase_service_role_key = mock_key

    with (
        patch("smartops_agent.config.get_settings", return_value=mock_settings),
        patch("supabase.create_client", side_effect=RuntimeError("conn error")),
    ):
        result = _upload_to_supabase(html)

    assert result is False
