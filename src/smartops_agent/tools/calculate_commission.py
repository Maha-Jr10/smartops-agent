"""Outil calculate_commission : calcul déterministe en code (ADR 0002).

Règles (jamais calculées par le LLM) :
  base = total_projet - coûts_directs
  apporteur : 20 % de base
  réalisation : 40 % de base, partagés si plusieurs réalisateurs
  même personne (apporteur ET réalisateur) : 60 % de base
  l'entreprise conserve au moins 40 % (= commissions ≤ 60 % de base)
"""

from __future__ import annotations

import sqlite3

from smartops_agent.tools.models import (
    CalculateCommissionInput,
    CalculateCommissionOutput,
    CommissionDetail,
    ToolError,
    ToolErrorCode,
)

APPORTEUR_RATE = 0.20
REALISATION_RATE = 0.40
COMBINED_RATE = 0.60  # apporteur + réalisateur, même personne
MAX_COMMISSION_RATE = 0.60  # l'entreprise garde au moins 40 %


def calculate_commission(
    inp: CalculateCommissionInput,
    db_path: str,
    role: str,
    user_id: str,
) -> CalculateCommissionOutput:
    """Calcule la commission de person_id sur project_id."""
    # Vérification d'accès : on ne peut voir que sa propre commission sauf admin
    if role != "admin" and user_id != inp.person_id:
        raise ToolError(
            ToolErrorCode.FORBIDDEN, "Vous ne pouvez consulter que vos propres commissions."
        )

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        proj_row = con.execute(
            "SELECT total_amount, currency, direct_costs, apporteur_id, realisation_ids "
            "FROM projects WHERE id = ?",
            (inp.project_id,),
        ).fetchone()
        if not proj_row:
            raise ToolError(ToolErrorCode.NOT_FOUND, "Projet introuvable.")

        # Vérifier qu'au moins une facture est payée (ADR 0002)
        paid = con.execute(
            "SELECT COUNT(*) FROM invoices WHERE project_id = ? AND status = 'paid'",
            (inp.project_id,),
        ).fetchone()[0]
    finally:
        con.close()

    if paid == 0:
        raise ToolError(
            ToolErrorCode.CLIENT_NOT_PAID,
            "Aucune commission calculée tant que le client n'a pas payé.",
        )

    total: float = proj_row["total_amount"]
    costs: float = proj_row["direct_costs"]
    currency: str = proj_row["currency"]
    apporteur_id: str | None = proj_row["apporteur_id"]
    realisation_ids: list[str] = [r for r in proj_row["realisation_ids"].split(",") if r]

    base = total - costs
    if base <= 0:
        base = 0.0

    is_apporteur = apporteur_id == inp.person_id
    is_realisateur = inp.person_id in realisation_ids
    n_real = len(realisation_ids) if realisation_ids else 1

    if is_apporteur and is_realisateur:
        commission = base * COMBINED_RATE
        rule = "apporteur+réalisation (même personne) : 60 %"
        apporteur_share = base * APPORTEUR_RATE
        real_share = base * REALISATION_RATE / n_real
    elif is_apporteur:
        commission = base * APPORTEUR_RATE
        rule = "apporteur : 20 %"
        apporteur_share = commission
        real_share = 0.0
    elif is_realisateur:
        real_share = base * REALISATION_RATE / n_real
        commission = real_share
        rule = f"réalisation : 40 % partagés entre {n_real} réalisateur(s)"
        apporteur_share = 0.0
    else:
        raise ToolError(
            ToolErrorCode.NOT_FOUND,
            "Cette personne n'est ni apporteur ni réalisateur de ce projet.",
        )

    # Garde : l'entreprise conserve au moins 40 %
    max_commission = base * MAX_COMMISSION_RATE
    if commission > max_commission:
        commission = max_commission
        rule += " (plafonné à 60 % de la base)"

    breakdown = (
        f"base={base:.2f} {currency} "
        f"(total={total:.2f} - coûts={costs:.2f}), "
        f"commission={commission:.2f} {currency}"
    )

    detail = CommissionDetail(
        base=round(base, 2),
        apporteur_share=round(apporteur_share, 2),
        realisation_share=round(real_share, 2),
        total=round(commission, 2),
        currency=currency,
        rule_applied=rule,
        breakdown=breakdown,
    )
    return CalculateCommissionOutput(commission=detail)
