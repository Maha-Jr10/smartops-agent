"""Tests de la base CRM fictive : reproductibilité et pièges."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from smartops_agent.data.seed import SeedParams, seed_database

pytestmark = pytest.mark.unit


def _count(db_path: Path, table: str) -> int:
    con = sqlite3.connect(db_path)
    row = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
    con.close()
    return int(row[0])


def test_seed_is_deterministic(tmp_path: Path) -> None:
    p = SeedParams(random_seed=42)
    db1 = tmp_path / "a.db"
    db2 = tmp_path / "b.db"
    seed_database(db1, p)
    seed_database(db2, p)
    assert db1.read_bytes() == db2.read_bytes()


def test_row_counts(tmp_path: Path) -> None:
    p = SeedParams(random_seed=42, n_clients=30, n_leads=120, n_projects=40, n_invoices=60)
    db = tmp_path / "crm.db"
    seed_database(db, p)
    assert _count(db, "clients") == 30
    assert _count(db, "leads") == 120
    assert _count(db, "projects") == 40
    assert _count(db, "invoices") == 60


def test_similar_client_name_trap(tmp_path: Path) -> None:
    db = tmp_path / "crm.db"
    seed_database(db, SeedParams())
    con = sqlite3.connect(db)
    names = [r[0] for r in con.execute("SELECT name FROM clients").fetchall()]
    con.close()
    # Two names share a common prefix (trap)
    matching = [n for n in names if "Société Marocaine de Services" in n]
    assert len(matching) >= 2, "Piège : deux clients aux noms similaires attendus"


def test_opted_out_lead_exists(tmp_path: Path) -> None:
    db = tmp_path / "crm.db"
    seed_database(db, SeedParams())
    con = sqlite3.connect(db)
    n = con.execute("SELECT COUNT(*) FROM leads WHERE opted_out=1").fetchone()[0]
    con.close()
    assert n >= 1


def test_injection_trap_lead_exists(tmp_path: Path) -> None:
    db = tmp_path / "crm.db"
    seed_database(db, SeedParams())
    con = sqlite3.connect(db)
    row = con.execute("SELECT notes FROM leads WHERE notes LIKE '%IGNORE%'").fetchone()
    con.close()
    assert row is not None, "Piège d'injection de prompt attendu dans les notes d'un lead"


def test_unpaid_invoice_trap_exists(tmp_path: Path) -> None:
    db = tmp_path / "crm.db"
    seed_database(db, SeedParams())
    con = sqlite3.connect(db)
    n = con.execute("SELECT COUNT(*) FROM invoices WHERE status='unpaid'").fetchone()[0]
    con.close()
    assert n >= 1
