"""Outil draft_followup : génère un brouillon de relance (rien n'est envoyé)."""

from __future__ import annotations

import sqlite3

from smartops_agent.tools.models import (
    DraftFollowupInput,
    DraftFollowupOutput,
    ToneType,
    ToolError,
    ToolErrorCode,
)

_SUBJECTS: dict[ToneType, str] = {
    ToneType.neutral: "Suivi de votre dossier",
    ToneType.friendly: "Prenons un moment pour faire le point",
    ToneType.formal: "Objet : relance dossier en attente",
}

_OPENINGS: dict[ToneType, str] = {
    ToneType.neutral: "Bonjour {name},\n\nNous souhaitons faire le point sur votre dossier.",
    ToneType.friendly: (
        "Bonjour {name},\n\nJ'espère que vous allez bien ! Je voulais prendre de vos nouvelles."
    ),
    ToneType.formal: (
        "Madame, Monsieur {name},\n\nNous vous contactons dans le cadre du suivi de votre dossier."
    ),
}

_CLOSINGS: dict[ToneType, str] = {
    ToneType.neutral: "Cordialement,\nL'équipe Smartara",
    ToneType.friendly: "À très bientôt,\nL'équipe Smartara",
    ToneType.formal: (
        "Veuillez agréer, Madame, Monsieur, l'expression de nos salutations distinguées.\nSmartara"
    ),
}


def draft_followup(inp: DraftFollowupInput, db_path: str, role: str) -> DraftFollowupOutput:
    """Génère un brouillon de message pour un lead. Ne l'envoie pas."""
    if role not in ("commercial", "admin"):
        raise ToolError(ToolErrorCode.FORBIDDEN, "Rôle insuffisant pour rédiger des relances.")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT name, opted_out FROM leads WHERE id = ?", (inp.lead_id,)
        ).fetchone()
    finally:
        con.close()

    if not row:
        raise ToolError(ToolErrorCode.NOT_FOUND, f"Lead {inp.lead_id} introuvable.")

    if row["opted_out"]:
        raise ToolError(
            ToolErrorCode.OPTED_OUT, "Ce prospect a refusé d'être contacté (opted-out)."
        )

    name: str = row["name"]
    body = (
        _OPENINGS[inp.tone].format(name=name)
        + "\n\nNous sommes à votre disposition pour répondre à vos questions.\n\n"
        + _CLOSINGS[inp.tone]
    )
    return DraftFollowupOutput(subject=_SUBJECTS[inp.tone], body=body)
