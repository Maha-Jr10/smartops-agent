"""Generate deterministic fake JSONL traces for Evidently drift demo.

Reference batch (n_reference rows): fast, few tool calls.
Current batch  (n_current rows):   slower, more tool calls → triggers drift.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_ROLES = ["commercial", "commercial", "delivery", "admin"]
_STORAGE_PATH = "traces/traces.jsonl"
_MIN_REAL_ROWS = 10  # don't overwrite if we already have this many real traces

_SHORT_ANSWERS = [
    "Voici les informations sur le client Diallo.",
    "La commission de ce projet est de 5 300 GMD.",
    "Le lead a été contacté avec succès.",
    "Projet Refonte portail #3 : statut actif.",
    "Facture inv_a2b3c4 : montant 45 000 MAD, en attente.",
    "Aucun projet en retard pour ce client.",
    "Le taux de commission est de 8 % pour cet apporteur.",
]

_LONG_ANSWERS = [
    (
        "Voici le résumé complet du portefeuille client pour ce trimestre. "
        "Les projets actifs totalisent 320 000 GMD répartis sur 7 clients distincts. "
        "Trois factures restent impayées au-delà de 30 jours. "
        "Je recommande une relance prioritaire pour les projets "
        "Refonte portail #3 et Migration cloud #7."
    ),
    (
        "Après analyse des données disponibles, j'ai identifié une anomalie dans les commissions "
        "versées au cours des 60 derniers jours. Le montant total versé dépasse le seuil autorisé "
        "de 15 %. Une validation humaine est requise avant toute action supplémentaire."
    ),
    (
        "Le projet Audit sécurité #12 est actuellement bloqué en attente d'approbation. "
        "L'équipe delivery signale un retard de 2 semaines dû à des dépendances externes. "
        "Je recommande de contacter l'équipe pour débloquer la situation dès que possible."
    ),
    (
        "Résultat de la recherche : 4 leads qualifiés correspondent à vos critères. "
        "Deux d'entre eux ont exprimé un intérêt fort lors des derniers échanges. "
        "Je vous suggère de planifier des appels de qualification dans les 48 prochaines heures."
    ),
]


def _make_trace(rng: random.Random, is_reference: bool) -> dict[str, Any]:
    role = rng.choice(_ROLES)
    if is_reference:
        n_tools = rng.randint(1, 2)
        latencies = [round(rng.uniform(0.3, 0.9), 3) for _ in range(n_tools + 1)]
        answer = rng.choice(_SHORT_ANSWERS)
        iterations = rng.randint(1, 2)
        escalated = rng.random() < 0.04
    else:
        n_tools = rng.randint(2, 5)
        latencies = [round(rng.uniform(0.9, 2.8), 3) for _ in range(n_tools + 1)]
        answer = rng.choice(_LONG_ANSWERS if rng.random() < 0.65 else _SHORT_ANSWERS)
        iterations = rng.randint(2, 5)
        escalated = rng.random() < 0.14

    steps = []
    for i, lat in enumerate(latencies):
        step_type = "tool_call" if i < n_tools else "llm_call"
        steps.append({"type": step_type, "latency_s": lat})

    return {
        "role": role,
        "iterations": iterations,
        "escalated": escalated,
        "answer": answer,
        "steps": steps,
    }


def _replay_metrics(rows: list[dict[str, Any]]) -> None:
    """Increment Prometheus counters so Grafana shows activity from seed data."""
    try:
        from smartops_agent.monitoring.metrics import (
            chat_latency_seconds,
            chat_requests_total,
            escalations_total,
            iterations_total,
            tool_calls_total,
        )
    except Exception:
        log.debug("Prometheus metrics unavailable; skipping replay", exc_info=True)
        return

    for row in rows:
        role = row.get("role", "commercial")
        chat_requests_total.labels(role=role, status="ok").inc()
        iters = row.get("iterations", 1)
        iterations_total.observe(iters)
        total_latency = sum(s.get("latency_s", 0.0) for s in row.get("steps", []))
        chat_latency_seconds.observe(total_latency)
        for step in row.get("steps", []):
            if step.get("type") == "tool_call":
                tool_calls_total.labels(tool="seed", status="ok").inc()
        if row.get("escalated"):
            escalations_total.labels(reason="seed").inc()


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                count += 1
    return count


def _upload_to_supabase(traces_path: Path) -> bool:
    """Persist the traces JSONL to Supabase Storage so it survives redeploys."""
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
        with traces_path.open("rb") as fh:
            content = fh.read()
        client.storage.from_("reports").upload(
            _STORAGE_PATH,
            content,
            {"contentType": "application/x-ndjson", "upsert": "true"},  # type: ignore[arg-type]
        )
        log.info("Seed traces uploaded to Supabase Storage: reports/%s", _STORAGE_PATH)
        return True
    except Exception:
        log.debug("Could not upload seed traces to Supabase Storage", exc_info=True)
        return False


def _delete_from_supabase() -> bool:
    """Remove the persisted traces from Supabase Storage."""
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
        client.storage.from_("reports").remove([_STORAGE_PATH])
        log.info("Seed traces removed from Supabase Storage")
        return True
    except Exception:
        log.debug("Could not remove seed traces from Supabase Storage", exc_info=True)
        return False


def upload_traces(
    traces_path: Path = Path("reports/traces/traces.jsonl"),
) -> bool:
    """Upload current traces file to Supabase Storage (called by scheduler)."""
    return _upload_to_supabase(traces_path)


def seed_traces(
    traces_path: Path = Path("reports/traces/traces.jsonl"),
    n_reference: int = 60,
    n_current: int = 100,
    random_seed: int = 42,
) -> int:
    """Seed demo traces if not enough real data exists; always replay Prometheus metrics.

    When >= _MIN_REAL_ROWS real traces already exist the file is left untouched so
    production data is never overwritten.  Metrics are replayed regardless so
    Grafana shows activity immediately after injection.
    """
    rng = random.Random(random_seed)  # noqa: S311  # nosec B311

    rows: list[dict[str, Any]] = []
    for _ in range(n_reference):
        rows.append(_make_trace(rng, is_reference=True))
    for _ in range(n_current):
        rows.append(_make_trace(rng, is_reference=False))

    existing = _count_lines(traces_path)
    if existing < _MIN_REAL_ROWS:
        traces_path.parent.mkdir(parents=True, exist_ok=True)
        with traces_path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        _upload_to_supabase(traces_path)
        log.info("Seed traces written (%d rows)", len(rows))
    else:
        log.info(
            "Skipping seed write: %d real traces exist; replaying metrics only",
            existing,
        )

    _replay_metrics(rows)
    return len(rows)


def delete_traces(
    traces_path: Path = Path("reports/traces/traces.jsonl"),
) -> bool:
    """Delete the local traces file and remove from Supabase Storage."""
    deleted_local = False
    if traces_path.exists():
        traces_path.unlink()
        deleted_local = True
    _delete_from_supabase()
    return deleted_local
