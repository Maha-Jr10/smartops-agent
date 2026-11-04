"""JWT authentication via Supabase.

Validates Bearer tokens issued by Supabase Auth, then fetches the caller's
role from the `profiles` table using the service-role key.

Supports both HS256 (legacy JWT secret) and RS256 (new asymmetric JWT keys).
The algorithm is read from the token header; RS256 tokens are verified against
Supabase's JWKS endpoint (/auth/v1/.well-known/jwks.json).
"""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.request
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


# ---------------------------------------------------------------------------
# JWKS cache for RS256 tokens (Supabase "new JWT" / asymmetric keys)
# ---------------------------------------------------------------------------
_JWKS_CACHE: list[dict[str, Any]] = []
_JWKS_CACHE_EXPIRES: float = 0.0
_JWKS_CACHE_TTL = 3600  # 1 hour


def _get_jwks(supabase_url: str) -> list[dict[str, Any]]:  # pragma: no cover
    global _JWKS_CACHE, _JWKS_CACHE_EXPIRES
    now = time.monotonic()
    if _JWKS_CACHE and now < _JWKS_CACHE_EXPIRES:
        return _JWKS_CACHE
    url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310  # nosec B310
        jwks: dict[str, Any] = json.loads(resp.read())
    _JWKS_CACHE = jwks.get("keys", [])
    _JWKS_CACHE_EXPIRES = now + _JWKS_CACHE_TTL
    return _JWKS_CACHE


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
        import jwt as pyjwt
        from jwt.algorithms import RSAAlgorithm
        from jwt.exceptions import ExpiredSignatureError, PyJWTError

        token = credentials.credentials
        alg = _jwt_alg(token)

        if alg == "RS256":
            keys = _get_jwks(settings.supabase_url)
            kid = _jwt_kid(token)
            jwk_dict: dict[str, Any] | None = next(
                (k for k in keys if kid is None or k.get("kid") == kid),
                keys[0] if keys else None,
            )
            if jwk_dict is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="JWKS unavailable. Try again later.",
                )
            # from_jwk returns RSAPrivateKey|RSAPublicKey; JWKS only has public keys
            rsa_public_key = RSAAlgorithm.from_jwk(jwk_dict)
            payload: dict[str, Any] = pyjwt.decode(
                token,
                rsa_public_key,  # type: ignore[arg-type]
                algorithms=["RS256"],
                audience="authenticated",
            )
        else:
            payload = pyjwt.decode(
                token,
                _get_jwt_secret(),
                algorithms=["HS256"],
                audience="authenticated",
            )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired."
        ) from exc
    except PyJWTError as exc:
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
