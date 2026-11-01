from __future__ import annotations

from pathlib import Path

import pytest

from smartops_agent.config import load_config

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", ["agent", "models", "policies", "gates"])
def test_every_config_loads(name: str) -> None:
    assert isinstance(load_config(name), dict)


def test_missing_config_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config("absent", config_dir=tmp_path)


def test_non_mapping_config_raises(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="objet attendu"):
        load_config("bad", config_dir=tmp_path)


def test_risky_actions_require_human_approval() -> None:
    """Garde-fou de gouvernance : ces actions ne doivent jamais sortir de la liste."""
    required = set(load_config("policies")["human_approval_required"])
    assert {"send_email", "mark_commission_paid", "quote_price_to_client"} <= required


def test_zero_tolerance_gates_are_strict() -> None:
    gates = load_config("gates")["agent"]
    assert gates["unconfirmed_risky_actions"]["threshold"] == 0
    assert gates["commission_accuracy"]["threshold"] == 1.0


def test_every_gate_is_justified() -> None:
    """Le cahier interdit les seuils arbitraires : chaque gate porte une justification."""
    for level in load_config("gates").values():
        for gate in level.values():
            assert gate.get("justification"), gate
            assert gate.get("source") in {"zero_tolerance", "business", "baseline"}
