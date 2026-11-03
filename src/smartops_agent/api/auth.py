"""JWT authentication via Supabase.

Validates Bearer tokens issued by Supabase Auth, then fetches the caller's
role from the `profiles` table using the service-role key.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

log = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------
ROLE_ADMIN = "admin"
ROLE_COMMERCIAL = "commercial"
ROLE_DELIVERY = "delivery"
ALLOWED_ROLES = {ROLE_ADMIN, ROLE_COMMERCIAL, ROLE_DELIVERY}


def _get_jwt_secret() -> str:
    from smartops_agent.config import get_settings

    s = get_settings()
    secret = s.supabase_jwt_secret.get_secret_value() if s.supabase_jwt_secret else ""
    if not secret:
        raise RuntimeError("SUPABASE_JWT_SECRET is not configured.")
    return secret


# TTL cache for granted roles only — denials and errors are never cached so
# a pending user who gets promoted gains access within _ROLE_CACHE_TTL seconds.
_ROLE_CACHE: dict[str, tuple[str, float]] = {}
_ROLE_CACHE_TTL = 300  # seconds


def _fetch_role(user_id: str) -> str:
    """Fetch role from Supabase profiles table. Fails closed on errors."""
    from smartops_agent.config import get_settings

    s = get_settings()
    if not s.supabase_url or not s.supabase_service_role_key:
        return ROLE_COMMERCIAL  # local dev without Supabase configured

    # Serve from cache when fresh (only allowed roles are ever cached)
    cached = _ROLE_CACHE.get(user_id)
    if cached:
        role, expires_at = cached
        if time.monotonic() < expires_at:
            return role
        _ROLE_CACHE.pop(user_id, None)

    # Fetch from Supabase — network/DB errors raise 503 (fail closed, not open)
    try:
        from supabase import create_client

        client = create_client(
            s.supabase_url,
            s.supabase_service_role_key.get_secret_value(),
        )
        resp = client.table("profiles").select("role").eq("id", user_id).single().execute()
        data = resp.data if isinstance(resp.data, dict) else {}
        raw_role: str = str(data.get("role", "pending"))
    except Exception as exc:
        log.warning("Role lookup failed for %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Role lookup failed. Try again later.",
        ) from exc

    # Validate OUTSIDE the try so 403 is never swallowed by the except above
    if raw_role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte est en attente d'activation par un administrateur.",
        )

    # Cache only granted roles, not denials
    _ROLE_CACHE[user_id] = (raw_role, time.monotonic() + _ROLE_CACHE_TTL)
    return raw_role


class AuthUser:
    def __init__(self, user_id: str, email: str, role: str) -> None:
        self.user_id = user_id
        self.email = email
        self.role = role

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
) -> AuthUser:
    """FastAPI dependency — validates Supabase JWT and returns the caller."""
    from smartops_agent.config import get_settings

    settings = get_settings()

    # No Supabase: dev/local gets a restricted fallback; anything else is a misconfiguration
    if not settings.supabase_url:
        if settings.app_env in ("dev", "local"):
            return AuthUser(user_id="local", email="local@dev", role=ROLE_COMMERCIAL)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured. Set SUPABASE_URL.",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        from jose import ExpiredSignatureError, JWTError, jwt  # type: ignore[import-untyped]

        payload: dict[str, Any] = jwt.decode(
            credentials.credentials,
            _get_jwt_secret(),
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired."
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}"
        ) from exc

    user_id: str = payload.get("sub", "")
    email: str = payload.get("email", "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub.")

    role = _fetch_role(user_id)
    return AuthUser(user_id=user_id, email=email, role=role)


def require_admin(user: AuthUser = Depends(require_auth)) -> AuthUser:  # noqa: B008
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user
