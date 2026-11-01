"""Masquage des données personnelles (email, téléphone) dans les traces."""

from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(r"\+?[\d\s\-().]{7,20}")


def mask_pii(value: str) -> str:
    """Remplace emails et numéros de téléphone par des balises génériques."""
    value = _EMAIL_RE.sub("[EMAIL]", value)
    value = _PHONE_RE.sub("[PHONE]", value)
    return value


def mask_pii_in_dict(data: Any) -> Any:
    """Parcourt récursivement un objet et masque les PII dans toutes les chaînes."""
    if isinstance(data, str):
        return mask_pii(data)
    if isinstance(data, dict):
        return {k: mask_pii_in_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [mask_pii_in_dict(item) for item in data]
    return data
