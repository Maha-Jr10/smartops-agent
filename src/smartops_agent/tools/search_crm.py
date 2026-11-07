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

    conditions: list[str] = []
    params: list[str] = []
    if inp.query:
        conditions.append("lower(name) LIKE ?")
        params.append(f"%{inp.query.lower()}%")
    if inp.status:
        conditions.append("lower(status) = ?")
        params.append(inp.status.lower())

    where = " AND ".join(conditions) if conditions else "1=1"
    # table comes from a fixed enum — no user input reaches the SQL identifier
    _sql = f"SELECT id, name, status FROM {table} WHERE {where}"  # noqa: S608  # nosec B608

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(_sql, params).fetchmany(10)
    finally:
        con.close()

    if not rows:
        desc = inp.query or inp.status or inp.entity.value
        raise ToolError(ToolErrorCode.NOT_FOUND, f"Aucun résultat pour « {desc} »")

    results = [CrmRecord(id=r["id"], name=r["name"], status=r["status"]) for r in rows]

    # AMBIGUOUS only when searching by name — not on listing queries (empty query)
    if inp.query and len(results) > 1:
        names = {r.name.lower() for r in results}
        if any(a != b and (a in b or b in a) for a in names for b in names):
            raise ToolError(
                ToolErrorCode.AMBIGUOUS,
                f"Plusieurs correspondances proches pour « {inp.query} » : "
                + ", ".join(r.name for r in results[:3]),
            )

    return SearchCrmOutput(results=results)
