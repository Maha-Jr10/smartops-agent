"""Tests de get_invoice_status."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from smartops_agent.tools.get_invoice_status import get_invoice_status
from smartops_agent.tools.models import GetInvoiceStatusInput, ToolError, ToolErrorCode

pytestmark = pytest.mark.unit


@pytest.fixture
def db(tmp_path: Path) -> str:
    p = tmp_path / "inv.db"
    con = sqlite3.connect(p)
    con.executescript("""
        CREATE TABLE invoices (
            id TEXT PRIMARY KEY, project_id TEXT, amount REAL,
            currency TEXT, status TEXT, due_date TEXT
        );
    """)
    con.execute("INSERT INTO invoices VALUES ('inv1','pr1',5000,'MAD','paid','2026-03-01')")
    con.execute("INSERT INTO invoices VALUES ('inv2','pr1',2000,'MAD','unpaid','2026-04-01')")
    con.commit()
    con.close()
    return str(p)


def test_get_by_invoice_id(db: str) -> None:
    inp = GetInvoiceStatusInput(invoice_id="inv1")
    out = get_invoice_status(inp, db, role="commercial", user_id="u1")
    assert len(out.invoices) == 1
    assert out.invoices[0].status == "paid"
    assert out.invoices[0].currency == "MAD"


def test_get_by_project_id_returns_all(db: str) -> None:
    inp = GetInvoiceStatusInput(project_id="pr1")
    out = get_invoice_status(inp, db, role="admin", user_id="u1")
    assert len(out.invoices) == 2


def test_not_found(db: str) -> None:
    inp = GetInvoiceStatusInput(invoice_id="inv_missing")
    with pytest.raises(ToolError) as exc_info:
        get_invoice_status(inp, db, role="commercial", user_id="u1")
    assert exc_info.value.code == ToolErrorCode.NOT_FOUND


def test_delivery_forbidden(db: str) -> None:
    inp = GetInvoiceStatusInput(invoice_id="inv1")
    with pytest.raises(ToolError) as exc_info:
        get_invoice_status(inp, db, role="delivery", user_id="u1")
    assert exc_info.value.code == ToolErrorCode.FORBIDDEN


def test_input_requires_at_least_one_field() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GetInvoiceStatusInput()
