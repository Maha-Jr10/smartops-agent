"""Generate deterministic fake JSONL traces for Evidently drift demo.

Reference batch (n_reference rows): fast, few tool calls.
Current batch  (n_current rows):   slower, more tool calls → triggers drift.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

_ROLES = ["commercial", "commercial", "delivery", "admin"]

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


def seed_traces(
    traces_path: Path = Path("reports/traces/traces.jsonl"),
    n_reference: int = 60,
    n_current: int = 100,
    random_seed: int = 42,
) -> int:
    """Write seed traces; return total rows written."""
    rng = random.Random(random_seed)  # noqa: S311  # nosec B311
    traces_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for _ in range(n_reference):
        rows.append(_make_trace(rng, is_reference=True))
    for _ in range(n_current):
        rows.append(_make_trace(rng, is_reference=False))

    with traces_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(rows)


def delete_traces(
    traces_path: Path = Path("reports/traces/traces.jsonl"),
) -> bool:
    """Delete the traces file. Returns True if the file existed."""
    if traces_path.exists():
        traces_path.unlink()
        return True
    return False
