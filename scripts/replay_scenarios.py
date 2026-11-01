"""Replay scenarios as simulated traffic against the running API.

Usage:
    uv run python scripts/replay_scenarios.py [--url URL] [--scenarios PATH] [--delay SECS]

Reads data/scenarios/scenarios_v1.jsonl and sends each scenario to POST /chat.
Useful to populate traces for Evidently drift reports (make monitor).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_DEFAULT_URL = "http://localhost:8000"
_DEFAULT_SCENARIOS = Path("data/scenarios/scenarios_v1.jsonl")
_DEFAULT_DELAY = 0.1


def _load_scenarios(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def replay(url: str, scenarios_path: Path, delay: float) -> int:
    try:
        import urllib.request
    except ImportError:
        print("urllib not available", file=sys.stderr)
        return 1

    scenarios = _load_scenarios(scenarios_path)
    ok = 0
    errors = 0
    for sc in scenarios:
        payload = json.dumps(
            {
                "message": sc.get("input", ""),
                "role": sc.get("role", "commercial"),
                "user_id": f"replay-{sc.get('id', 'unknown')}",
            }
        ).encode()
        req = urllib.request.Request(  # noqa: S310
            f"{url}/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                resp.read()
                ok += 1
        except Exception as exc:
            errors += 1
            print(f"[ERROR] {sc.get('id')}: {exc}", file=sys.stderr)
        if delay > 0:
            time.sleep(delay)

    print(f"Replay done: {ok} ok, {errors} errors (total {len(scenarios)})")
    return 0 if errors == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay scenarios against the API.")
    parser.add_argument("--url", default=_DEFAULT_URL)
    parser.add_argument("--scenarios", type=Path, default=_DEFAULT_SCENARIOS)
    parser.add_argument("--delay", type=float, default=_DEFAULT_DELAY)
    args = parser.parse_args()
    sys.exit(replay(args.url, args.scenarios, args.delay))


if __name__ == "__main__":
    main()
