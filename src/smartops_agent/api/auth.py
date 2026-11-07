"""JWT authentication via Supabase.

Validates Bearer tokens by calling Supabase's own /auth/v1/user endpoint.
This works for both HS256 (legacy) and RS256 (asymmetric) tokens without
any local JWT library handling.
"""

from __future__ import annotations

import base64
import json
import logging
import time

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


def _jwt_alg(token: str) -> str:
    """Read the algorithm from the JWT header without verifying the signature."""
    try:
        header_b64 = token.split(".")[0]
        padding = 4 - len(header_b64) % 4
        header = json.loads(base64.urlsafe_b64decode(header_b64 + "=" * padding))
        return str(header.get("alg", "HS256"))
    except Exception:
        return "HS256"


def _jwt_kid(token: str) -> str | None:
    """Read the key-id from the JWT header."""
    try:
        header_b64 = token.split(".")[0]
        padding = 4 - len(header_b64) % 4
        header = json.loads(base64.urlsafe_b64decode(header_b64 + "=" * padding))
        kid = header.get("kid")
        return str(kid) if kid is not None else None
    except Exception:
        return None


# TTL cache for granted roles only — denials and errors are never cached so
# a pending user who gets promoted gains access within _ROLE_CACHE_TTL seconds.
# Cache value: (role, crm_member_id, display_name, expires_at)
_ROLE_CACHE: dict[str, tuple[str, str | None, str, float]] = {}
_ROLE_CACHE_TTL = 300  # seconds


def _fetch_profile(user_id: str) -> tuple[str, str | None, str]:
    """Fetch role, crm_member_id, display_name from Supabase profiles. Fails closed."""
    from smartops_agent.config import get_settings

    s = get_settings()
    if not s.supabase_url or not s.supabase_service_role_key:
        return ROLE_COMMERCIAL, None, ""  # local dev without Supabase configured

    # Serve from cache when fresh (only allowed roles are ever cached)
    cached = _ROLE_CACHE.get(user_id)
    if cached:
        c_role, c_crm_id, c_display_name, expires_at = cached
        if time.monotonic() < expires_at:
            return c_role, c_crm_id, c_display_name
        _ROLE_CACHE.pop(user_id, None)

    # Fetch from Supabase — network/DB errors raise 503 (fail closed, not open)
    try:
        from supabase import create_client

        client = create_client(
            s.supabase_url,
            s.supabase_service_role_key.get_secret_value(),
        )
        resp = (
            client.table("profiles")
            .select("role,crm_member_id,display_name")
            .eq("id", user_id)
            .single()
            .execute()
        )
        data = resp.data if isinstance(resp.data, dict) else {}
        raw_role: str = str(data.get("role", "pending"))
        crm_member_id: str | None = data.get("crm_member_id") or None
        display_name: str = str(data.get("display_name") or "")
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
            detail=(
                "Bienvenue sur SmartOps Agent. Votre compte a bien ete cree et attend "
                "l'activation par un administrateur. Ceci est normal : l'acces au CRM "
                "interne (meme fictif) est reserve aux utilisateurs valides. Pour "
                "demander une activation, contactez muhammedjohn3@gmail.com en "
                "precisant l'email utilise a l'inscription."
            ),
        )

    # Cache only granted roles, not denials
    _ROLE_CACHE[user_id] = (
        raw_role,
        crm_member_id,
        display_name,
        time.monotonic() + _ROLE_CACHE_TTL,
    )
    return raw_role, crm_member_id, display_name


class AuthUser:
    def __init__(
        self,
        user_id: str,
        email: str,
        role: str,
        crm_member_id: str | None = None,
        display_name: str = "",
    ) -> None:
        self.user_id = user_id
        self.email = email
        self.role = role
        self.crm_member_id = crm_member_id  # CRM team member ID (tm_XXXXXXXX), if linked
        self.display_name = display_name

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
            return AuthUser(
                user_id="local",
                email="local@dev",
                role=ROLE_COMMERCIAL,
                crm_member_id=None,
                display_name="Dev",
            )
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

    token = credentials.credentials
    svc_key = (
        settings.supabase_service_role_key.get_secret_value()
        if settings.supabase_service_role_key
        else ""
    )

    try:
        from supabase import create_client
        from supabase_auth.errors import AuthApiError, AuthError

        client = create_client(settings.supabase_url, svc_key)
        resp = client.auth.get_user(token)
        user = resp.user if resp is not None else None
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
        user_id: str = str(user.id)
        email: str = user.email or ""
    except HTTPException:
        raise
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc.message}",
        ) from exc
    except AuthError as exc:
        log.warning("Auth service error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable.",
        ) from exc
    except Exception as exc:
        log.warning("Auth service unreachable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable.",
        ) from exc

    role, crm_member_id, display_name = _fetch_profile(user_id)
    return AuthUser(
        user_id=user_id,
        email=email,
        role=role,
        crm_member_id=crm_member_id,
        display_name=display_name,
    )


def require_admin(user: AuthUser = Depends(require_auth)) -> AuthUser:  # noqa: B008
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user
