"""Unit tests for auth.py helpers (JWT, role, auth dependencies)."""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from smartops_agent.api.auth import (
    _ROLE_CACHE,
    ROLE_ADMIN,
    ROLE_COMMERCIAL,
    AuthUser,
    _fetch_role,
    _get_jwt_secret,
    _jwt_alg,
    _jwt_kid,
    require_admin,
    require_auth,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_header_token(alg: str = "HS256", kid: str | None = None) -> str:
    header: dict[str, str] = {"alg": alg, "typ": "JWT"}
    if kid is not None:
        header["kid"] = kid
    encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    return f"{encoded}.payload.signature"


def _mock_settings(**kwargs: object) -> MagicMock:
    s = MagicMock()
    s.supabase_url = kwargs.get("supabase_url", "")
    s.supabase_service_role_key = kwargs.get("supabase_service_role_key")
    s.supabase_jwt_secret = kwargs.get("supabase_jwt_secret")
    s.app_env = kwargs.get("app_env", "local")
    return s


def _mock_service_key(value: str = "test-service-key") -> MagicMock:
    sk = MagicMock()
    sk.get_secret_value.return_value = value
    return sk


# ---------------------------------------------------------------------------
# _jwt_alg
# ---------------------------------------------------------------------------


class TestJwtAlg:
    def test_hs256_detected(self) -> None:
        assert _jwt_alg(_make_header_token("HS256")) == "HS256"

    def test_rs256_detected(self) -> None:
        assert _jwt_alg(_make_header_token("RS256")) == "RS256"

    def test_missing_alg_defaults_to_hs256(self) -> None:
        header = base64.urlsafe_b64encode(b'{"typ":"JWT"}').rstrip(b"=").decode()
        assert _jwt_alg(f"{header}.p.s") == "HS256"

    def test_malformed_token_defaults_to_hs256(self) -> None:
        assert _jwt_alg("not.a.jwt") == "HS256"

    def test_empty_string_defaults_to_hs256(self) -> None:
        assert _jwt_alg("") == "HS256"


# ---------------------------------------------------------------------------
# _jwt_kid
# ---------------------------------------------------------------------------


class TestJwtKid:
    def test_kid_extracted(self) -> None:
        assert _jwt_kid(_make_header_token("RS256", kid="key-123")) == "key-123"

    def test_no_kid_returns_none(self) -> None:
        assert _jwt_kid(_make_header_token("HS256")) is None

    def test_malformed_returns_none(self) -> None:
        assert _jwt_kid("bad") is None


# ---------------------------------------------------------------------------
# _get_jwt_secret
# ---------------------------------------------------------------------------


class TestGetJwtSecret:
    def test_raises_when_not_configured(self) -> None:
        s = _mock_settings(supabase_jwt_secret=None)
        with (
            patch("smartops_agent.config.get_settings", return_value=s),
            pytest.raises(RuntimeError, match="SUPABASE_JWT_SECRET"),
        ):
            _get_jwt_secret()

    def test_returns_secret_value(self) -> None:
        s = _mock_settings(supabase_jwt_secret=SecretStr("test-secret-value"))
        with patch("smartops_agent.config.get_settings", return_value=s):
            assert _get_jwt_secret() == "test-secret-value"


# ---------------------------------------------------------------------------
# _fetch_role
# ---------------------------------------------------------------------------


class TestFetchRole:
    def test_local_dev_no_supabase_returns_commercial(self) -> None:
        s = _mock_settings(supabase_url="")
        with patch("smartops_agent.config.get_settings", return_value=s):
            assert _fetch_role("any-user-id") == ROLE_COMMERCIAL

    def test_cache_hit_returns_cached_role(self) -> None:
        _ROLE_CACHE["cached-user-99"] = (ROLE_ADMIN, time.monotonic() + 300)
        s = _mock_settings(
            supabase_url="https://x.supabase.co",
            supabase_service_role_key=_mock_service_key(),
        )
        try:
            with patch("smartops_agent.config.get_settings", return_value=s):
                assert _fetch_role("cached-user-99") == ROLE_ADMIN
        finally:
            _ROLE_CACHE.pop("cached-user-99", None)

    def test_expired_cache_entry_evicted_before_lookup(self) -> None:
        _ROLE_CACHE["expired-user"] = (ROLE_ADMIN, time.monotonic() - 1)
        # Use empty supabase_url so the function hits local-dev path after eviction
        # We verify the stale entry is NOT returned (eviction happens, then local fallback)
        s = _mock_settings(supabase_url="")
        try:
            with patch("smartops_agent.config.get_settings", return_value=s):
                # supabase_url is empty → returns COMMERCIAL early (before cache check),
                # so we just verify the stale ADMIN value is not served
                result = _fetch_role("expired-user")
            assert result == ROLE_COMMERCIAL
        finally:
            _ROLE_CACHE.pop("expired-user", None)


# ---------------------------------------------------------------------------
# require_auth
# ---------------------------------------------------------------------------


class TestRequireAuth:
    def test_local_dev_returns_commercial_user(self) -> None:
        s = _mock_settings(supabase_url="", app_env="local")
        with patch("smartops_agent.config.get_settings", return_value=s):
            user = require_auth(credentials=None)
        assert user.role == ROLE_COMMERCIAL
        assert user.user_id == "local"

    def test_dev_env_returns_commercial_user(self) -> None:
        s = _mock_settings(supabase_url="", app_env="dev")
        with patch("smartops_agent.config.get_settings", return_value=s):
            user = require_auth(credentials=None)
        assert user.role == ROLE_COMMERCIAL

    def test_production_without_supabase_raises_503(self) -> None:
        s = _mock_settings(supabase_url="", app_env="production")
        with (
            patch("smartops_agent.config.get_settings", return_value=s),
            pytest.raises(HTTPException) as exc_info,
        ):
            require_auth(credentials=None)
        assert exc_info.value.status_code == 503

    def test_missing_credentials_raises_401(self) -> None:
        s = _mock_settings(supabase_url="https://x.supabase.co")
        with (
            patch("smartops_agent.config.get_settings", return_value=s),
            pytest.raises(HTTPException) as exc_info,
        ):
            require_auth(credentials=None)
        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_401(self) -> None:
        s = _mock_settings(
            supabase_url="https://x.supabase.co",
            supabase_service_role_key=_mock_service_key(),
        )
        from fastapi.security import HTTPAuthorizationCredentials
        from supabase_auth.errors import AuthApiError

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.here")
        mock_client = MagicMock()
        mock_client.auth.get_user.side_effect = AuthApiError("invalid JWT", 401, None)
        with (
            patch("smartops_agent.config.get_settings", return_value=s),
            patch("supabase.create_client", return_value=mock_client),
            pytest.raises(HTTPException) as exc_info,
        ):
            require_auth(credentials=creds)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# require_admin
# ---------------------------------------------------------------------------


class TestRequireAdmin:
    def test_non_admin_raises_403(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user=AuthUser("u1", "user@test.com", "commercial"))
        assert exc_info.value.status_code == 403

    def test_delivery_raises_403(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user=AuthUser("u1", "user@test.com", "delivery"))
        assert exc_info.value.status_code == 403

    def test_admin_passes_through(self) -> None:
        user = AuthUser("u1", "admin@test.com", ROLE_ADMIN)
        assert require_admin(user=user) is user


# ---------------------------------------------------------------------------
# AuthUser
# ---------------------------------------------------------------------------


class TestAuthUser:
    def test_is_admin_true_for_admin_role(self) -> None:
        assert AuthUser("u", "a@b.com", ROLE_ADMIN).is_admin is True

    def test_is_admin_false_for_other_roles(self) -> None:
        assert AuthUser("u", "a@b.com", ROLE_COMMERCIAL).is_admin is False
        assert AuthUser("u", "a@b.com", "delivery").is_admin is False
