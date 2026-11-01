"""Outil get_invoice_status : statut de paiement d'une facture ou d'un projet."""

from __future__ import annotations

import sqlite3

from smartops_agent.tools.models import (
    GetInvoiceStatusInput,
    GetInvoiceStatusOutput,
    InvoiceRecord,
    ToolError,
    ToolErrorCode,
)


def get_invoice_status(
    inp: GetInvoiceStatusInput,
    db_path: str,
    role: str,
    user_id: str,
) -> GetInvoiceStatusOutput:
    """Retourne les factures correspondantes après vérification du rôle."""
    if role not in ("commercial", "admin"):
        raise ToolError(ToolErrorCode.FORBIDDEN, "Rôle insuffisant pour consulter les factures.")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        _base = "SELECT id, project_id, amount, currency, status, due_date FROM invoices"
        if inp.invoice_id:
            rows = con.execute(f"{_base} WHERE id = ?", (inp.invoice_id,)).fetchall()
        else:
            rows = con.execute(f"{_base} WHERE project_id = ?", (inp.project_id,)).fetchall()
    finally:
        con.close()

    if not rows:
        raise ToolError(ToolErrorCode.NOT_FOUND, "Facture introuvable.")

    invoices = [
        InvoiceRecord(
            id=r["id"],
            amount=r["amount"],
            currency=r["currency"],
            status=r["status"],
            due_date=r["due_date"],
        )
        for r in rows
    ]
    return GetInvoiceStatusOutput(invoices=invoices)
