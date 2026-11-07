from __future__ import annotations

import json
import random
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smartops_agent.data.seed_traces import (
    _download_from_supabase,
    _make_trace,
    delete_traces,
    seed_traces,
    startup_replay,
    upload_traces,
)

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


def test_seed_traces_skips_write_when_enough_real_traces(tmp_path: Path) -> None:
    """Real traces are never overwritten when >= _MIN_REAL_ROWS already exist."""
    traces = tmp_path / "traces.jsonl"
    lines = [json.dumps({"role": "commercial"}) for _ in range(15)]
    traces.write_text("\n".join(lines) + "\n", encoding="utf-8")
    original = traces.read_text(encoding="utf-8")

    with (
        patch("smartops_agent.data.seed_traces._upload_to_supabase"),
        patch("smartops_agent.data.seed_traces._replay_metrics"),
    ):
        n = seed_traces(traces, n_reference=3, n_current=2)

    assert n == 5  # still returns total seed rows count
    assert traces.read_text(encoding="utf-8") == original  # file untouched


def test_upload_traces_delegates_to_upload(tmp_path: Path) -> None:
    traces = tmp_path / "t.jsonl"
    traces.write_text("{}", encoding="utf-8")
    with patch("smartops_agent.data.seed_traces._upload_to_supabase", return_value=True) as m:
        assert upload_traces(traces) is True
    m.assert_called_once_with(traces)


def test_startup_replay_no_file_no_supabase(tmp_path: Path) -> None:
    mock_settings = MagicMock()
    mock_settings.supabase_url = None
    mock_settings.supabase_service_role_key = None
    with patch("smartops_agent.config.get_settings", return_value=mock_settings):
        n = startup_replay(tmp_path / "missing.jsonl")
    assert n == 0


def test_startup_replay_reads_existing_file_and_replays(tmp_path: Path) -> None:
    traces = tmp_path / "traces.jsonl"
    rows = [{"role": "commercial", "steps": [], "iterations": 1, "escalated": False}] * 4
    traces.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    with patch("smartops_agent.data.seed_traces._replay_metrics") as mock_replay:
        n = startup_replay(traces)
    assert n == 4
    mock_replay.assert_called_once()
    replayed = mock_replay.call_args[0][0]
    assert len(replayed) == 4


def test_startup_replay_downloads_from_supabase_when_file_missing(
    tmp_path: Path,
) -> None:
    traces = tmp_path / "traces.jsonl"
    row = {"role": "admin", "steps": [], "iterations": 1, "escalated": False}

    def fake_download(path: Path) -> bool:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        return True

    with (
        patch(
            "smartops_agent.data.seed_traces._download_from_supabase",
            side_effect=fake_download,
        ),
        patch("smartops_agent.data.seed_traces._replay_metrics") as mock_replay,
    ):
        n = startup_replay(traces)

    assert n == 1
    mock_replay.assert_called_once()


def test_download_from_supabase_success(tmp_path: Path) -> None:
    traces = tmp_path / "traces.jsonl"
    content = b'{"role":"commercial"}\n'

    mock_settings = MagicMock()
    mock_settings.supabase_url = "https://fake.supabase.co"
    mock_key = MagicMock()
    mock_key.get_secret_value.return_value = "fake-key"
    mock_settings.supabase_service_role_key = mock_key

    mock_client = MagicMock()
    mock_client.storage.from_.return_value.download.return_value = content

    with (
        patch("smartops_agent.config.get_settings", return_value=mock_settings),
        patch("supabase.create_client", return_value=mock_client),
    ):
        result = _download_from_supabase(traces)

    assert result is True
    assert traces.read_bytes() == content


def test_download_from_supabase_no_credentials(tmp_path: Path) -> None:
    mock_settings = MagicMock()
    mock_settings.supabase_url = None
    mock_settings.supabase_service_role_key = None
    with patch("smartops_agent.config.get_settings", return_value=mock_settings):
        result = _download_from_supabase(tmp_path / "traces.jsonl")
    assert result is False
