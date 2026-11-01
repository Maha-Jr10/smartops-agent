"""Outil search_crm : recherche dans la base CRM fictive."""

from __future__ import annotations

import sqlite3

from smartops_agent.tools.models import (
    CrmRecord,
    EntityType,
    SearchCrmInput,
    SearchCrmOutput,
    ToolError,
    ToolErrorCode,
)

_TABLE_MAP = {
    EntityType.client: "clients",
    EntityType.lead: "leads",
    EntityType.project: "projects",
}


def search_crm(inp: SearchCrmInput, db_path: str) -> SearchCrmOutput:
    """Recherche dans la table correspondant à l'entité, retourne au plus 10 fiches."""
    table = _TABLE_MAP[inp.entity]
    query_lower = inp.query.lower()

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        # table comes from a fixed enum -- no user input reaches the SQL identifier
        _sql = f"SELECT id, name, status FROM {table} WHERE lower(name) LIKE ?"  # noqa: S608  # nosec B608
        rows = con.execute(_sql, (f"%{query_lower}%",)).fetchmany(10)
    finally:
        con.close()

    if not rows:
        raise ToolError(ToolErrorCode.NOT_FOUND, f"Aucun résultat pour « {inp.query} »")

    results = [CrmRecord(id=r["id"], name=r["name"], status=r["status"]) for r in rows]

    # AMBIGUOUS si plusieurs enregistrements partagent un nom très proche
    if len(results) > 1:
        names = {r.name.lower() for r in results}
        if any(a != b and (a in b or b in a) for a in names for b in names):
            raise ToolError(
                ToolErrorCode.AMBIGUOUS,
                f"Plusieurs correspondances proches pour « {inp.query} » : "
                + ", ".join(r.name for r in results[:3]),
            )

    return SearchCrmOutput(results=results)
