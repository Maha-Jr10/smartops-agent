"""Background drift monitor - runs run_report() on a schedule via asyncio."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_INTERVAL_S = 6 * 3600  # 6 hours between runs
_FIRST_RUN_DELAY_S = 90  # wait 90s after startup so the app is fully ready


async def _monitor_loop(interval_s: float) -> None:
    await asyncio.sleep(_FIRST_RUN_DELAY_S)
    while True:
        try:
            await asyncio.to_thread(_run_now)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Background drift monitor run failed")
        await asyncio.sleep(interval_s)


def _run_now() -> None:
    from smartops_agent.monitoring.report import run_report

    traces_path = Path("reports/traces/traces.jsonl")
    log.info("Background drift monitor: running report (traces=%s)", traces_path)
    run_report(traces_path=traces_path)


def start_scheduler_task(
    interval_s: float = _DEFAULT_INTERVAL_S,
) -> asyncio.Task[None]:
    return asyncio.ensure_future(_monitor_loop(interval_s))
