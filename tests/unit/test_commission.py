"""Tests exhaustifs des règles calculate_commission (ADR 0002 : gate 100 %)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from smartops_agent.tools.calculate_commission import (
    APPORTEUR_RATE,
    COMBINED_RATE,
    MAX_COMMISSION_RATE,
    REALISATION_RATE,
    calculate_commission,
)
from smartops_agent.tools.models import CalculateCommissionInput, ToolError, ToolErrorCode

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path: Path) -> str:
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(db_path)
    con.executescript("""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT,
            client_id TEXT,
            status TEXT,
            total_amount REAL,
            currency TEXT,
            direct_costs REAL,
            apporteur_id TEXT,
            realisation_ids TEXT
        );
        CREATE TABLE invoices (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            amount REAL,
            currency TEXT,
            status TEXT,
            due_date TEXT
        );
    """)
    # Project with apporteur=p1, realisation=p2
    con.execute(
        "INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)",
        ("pr_a", "Test", "cl_1", "closed", 10000.0, "MAD", 1000.0, "p1", "p2"),
    )
    # Project with both apporteur and realisation = p1
    con.execute(
        "INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)",
        ("pr_b", "Combo", "cl_1", "closed", 10000.0, "MAD", 1000.0, "p1", "p1"),
    )
    # Project with two realisateurs
    con.execute(
        "INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)",
        ("pr_c", "Shared", "cl_1", "closed", 10000.0, "MAD", 1000.0, "p1", "p2,p3"),
    )
    # Unpaid project
    con.execute(
        "INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)",
        ("pr_unpaid", "Unpaid", "cl_1", "active", 10000.0, "MAD", 1000.0, "p1", "p2"),
    )
    # Paid invoice for pr_a, pr_b, pr_c
    con.execute(
        "INSERT INTO invoices VALUES (?,?,?,?,?,?)",
        ("inv1", "pr_a", 10000, "MAD", "paid", "2026-01-01"),
    )
    con.execute(
        "INSERT INTO invoices VALUES (?,?,?,?,?,?)",
        ("inv2", "pr_b", 10000, "MAD", "paid", "2026-01-01"),
    )
    con.execute(
        "INSERT INTO invoices VALUES (?,?,?,?,?,?)",
        ("inv3", "pr_c", 10000, "MAD", "paid", "2026-01-01"),
    )
    con.commit()
    con.close()
    return str(db_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_apporteur_gets_20_percent(db: str) -> None:
    inp = CalculateCommissionInput(project_id="pr_a", person_id="p1")
    out = calculate_commission(inp, db, role="admin", user_id="p1")
    base = 10000.0 - 1000.0
    assert out.commission.total == pytest.approx(base * APPORTEUR_RATE)
    assert out.commission.currency == "MAD"


def test_realisateur_gets_40_percent(db: str) -> None:
    inp = CalculateCommissionInput(project_id="pr_a", person_id="p2")
    out = calculate_commission(inp, db, role="admin", user_id="p2")
    base = 10000.0 - 1000.0
    assert out.commission.total == pytest.approx(base * REALISATION_RATE)


def test_combined_gets_60_percent(db: str) -> None:
    inp = CalculateCommissionInput(project_id="pr_b", person_id="p1")
    out = calculate_commission(inp, db, role="admin", user_id="p1")
    base = 10000.0 - 1000.0
    assert out.commission.total == pytest.approx(base * COMBINED_RATE)


def test_shared_realisation_splits_40_percent(db: str) -> None:
    base = 10000.0 - 1000.0
    expected_each = base * REALISATION_RATE / 2
    for person in ("p2", "p3"):
        inp = CalculateCommissionInput(project_id="pr_c", person_id=person)
        out = calculate_commission(inp, db, role="admin", user_id=person)
        assert out.commission.total == pytest.approx(expected_each)


def test_company_keeps_at_least_40_percent(db: str) -> None:
    """Invariant : les commissions ne dépassent jamais 60 % de la base."""
    inp = CalculateCommissionInput(project_id="pr_b", person_id="p1")
    out = calculate_commission(inp, db, role="admin", user_id="p1")
    base = 10000.0 - 1000.0
    assert out.commission.total <= base * MAX_COMMISSION_RATE + 0.01


def test_client_not_paid_blocks_commission(db: str) -> None:
    inp = CalculateCommissionInput(project_id="pr_unpaid", person_id="p1")
    with pytest.raises(ToolError) as exc_info:
        calculate_commission(inp, db, role="admin", user_id="p1")
    assert exc_info.value.code == ToolErrorCode.CLIENT_NOT_PAID


def test_forbidden_for_other_person(db: str) -> None:
    inp = CalculateCommissionInput(project_id="pr_a", person_id="p1")
    with pytest.raises(ToolError) as exc_info:
        calculate_commission(inp, db, role="commercial", user_id="p99")
    assert exc_info.value.code == ToolErrorCode.FORBIDDEN


def test_not_found_when_not_involved(db: str) -> None:
    inp = CalculateCommissionInput(project_id="pr_a", person_id="p99")
    with pytest.raises(ToolError) as exc_info:
        calculate_commission(inp, db, role="admin", user_id="p99")
    assert exc_info.value.code == ToolErrorCode.NOT_FOUND


def test_not_found_project(db: str) -> None:
    inp = CalculateCommissionInput(project_id="pr_missing", person_id="p1")
    with pytest.raises(ToolError) as exc_info:
        calculate_commission(inp, db, role="admin", user_id="p1")
    assert exc_info.value.code == ToolErrorCode.NOT_FOUND
