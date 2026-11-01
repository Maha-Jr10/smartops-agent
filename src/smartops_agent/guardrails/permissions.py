"""Vérification des permissions par rôle (configs/policies.yaml)."""

from __future__ import annotations

from functools import lru_cache

from smartops_agent.config import load_config
from smartops_agent.tools.models import ToolError, ToolErrorCode


@lru_cache(maxsize=1)
def _policies() -> dict:  # type: ignore[type-arg]
    return load_config("policies")


def check_permission(tool_name: str, role: str) -> None:
    """Lève ToolError FORBIDDEN si le rôle n'est pas autorisé pour cet outil."""
    policies = _policies()
    tool_cfg = policies.get("tools", {}).get(tool_name)
    if tool_cfg is None:
        raise ToolError(ToolErrorCode.FORBIDDEN, f"Outil inconnu : {tool_name}")
    allowed: list[str] = tool_cfg.get("allowed_roles", [])
    if role not in allowed:
        raise ToolError(
            ToolErrorCode.FORBIDDEN,
            f"Le rôle « {role} » n'est pas autorisé à utiliser l'outil « {tool_name} ».",
        )


def is_own_only_scope(tool_name: str, role: str) -> bool:
    """Retourne True si ce rôle est limité à ses propres données pour cet outil."""
    policies = _policies()
    scope: dict[str, str] = policies.get("tools", {}).get(tool_name, {}).get("scope", {})
    if not scope:
        return False
    role_scope = scope.get(role, scope.get("default", "all"))
    return role_scope == "own_only"


def get_allowed_human_actions() -> list[str]:
    """Retourne la liste des actions qui requièrent une validation humaine."""
    return list(_policies().get("human_approval_required", []))
