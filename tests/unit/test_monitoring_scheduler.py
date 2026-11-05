from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from smartops_agent.monitoring.scheduler import _monitor_loop, _run_now, start_scheduler_task

pytestmark = pytest.mark.unit


def test_run_now_calls_report_with_default_traces_path() -> None:
    with patch("smartops_agent.monitoring.report.run_report") as run_report:
        _run_now()

    run_report.assert_called_once_with(traces_path=Path("reports/traces/traces.jsonl"))


def test_monitor_loop_runs_and_propagates_cancellation() -> None:
    sleeps: list[float] = []
    runs: list[bool] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)
        if len(sleeps) == 2:
            raise asyncio.CancelledError

    async def fake_to_thread(func: Any) -> None:
        runs.append(True)
        func()

    with (
        patch("smartops_agent.monitoring.scheduler.asyncio.sleep", side_effect=fake_sleep),
        patch("smartops_agent.monitoring.scheduler.asyncio.to_thread", side_effect=fake_to_thread),
        patch("smartops_agent.monitoring.scheduler._run_now"),
        pytest.raises(asyncio.CancelledError),
    ):
        asyncio.run(_monitor_loop(interval_s=12))

    assert sleeps == [90, 12]
    assert runs == [True]


def test_monitor_loop_logs_report_failure_and_continues() -> None:
    sleeps = 0

    async def fake_sleep(_delay: float) -> None:
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            raise asyncio.CancelledError

    async def fake_to_thread(_func: Any) -> None:
        raise RuntimeError("report failed")

    with (
        patch("smartops_agent.monitoring.scheduler.asyncio.sleep", side_effect=fake_sleep),
        patch("smartops_agent.monitoring.scheduler.asyncio.to_thread", side_effect=fake_to_thread),
        patch("smartops_agent.monitoring.scheduler.log.exception") as log_exception,
        pytest.raises(asyncio.CancelledError),
    ):
        asyncio.run(_monitor_loop(interval_s=12))

    log_exception.assert_called_once_with("Background drift monitor run failed")


def test_start_scheduler_task_schedules_monitor_loop() -> None:
    with patch("smartops_agent.monitoring.scheduler.asyncio.ensure_future") as ensure_future:
        task = start_scheduler_task(interval_s=30)

    coroutine = ensure_future.call_args.args[0]
    assert coroutine.cr_code.co_name == "_monitor_loop"
    coroutine.close()
    ensure_future.assert_called_once()
    assert task is ensure_future.return_value
