"""Interface unique vers Groq, OpenRouter et Ollama (ADR 0001 : boucle écrite par nous)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol

import httpx

from smartops_agent.config import get_settings

log = logging.getLogger(__name__)

# Models shown in the admin settings dropdown (OpenRouter free tier).
AVAILABLE_MODELS: list[dict[str, str]] = [
    {"id": "nvidia/nemotron-3.5-lightning:free", "label": "Nemotron 3.5 Lightning (recommandé)"},
    {"id": "google/gemma-4-31b-it:free", "label": "Gemma 4 31B"},
    {"id": "google/gemma-4-26b-a4b-it:free", "label": "Gemma 4 26B"},
    {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "label": "Nemotron Ultra 550B"},
    {"id": "xingchen-agi/xing4.0-29b-a4b:free", "label": "Xing 4.0 29B"},
]

# Keep alias so existing imports from app.py stay valid.
FREE_GROQ_MODELS = AVAILABLE_MODELS

_KEY_CACHE_TTL = 60  # seconds — changes visible within 1 minute

# ---------------------------------------------------------------------------
# Dynamic Groq API key (admin can override via /settings/groq-key)
# ---------------------------------------------------------------------------

_groq_key_cache: tuple[str, float] | None = None


def _fetch_groq_key() -> str:
    """Read from Supabase app_settings first, fall back to env var."""
    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        try:
            from supabase import create_client

            client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key.get_secret_value(),
            )
            resp = (
                client.table("app_settings")
                .select("value")
                .eq("key", "groq_api_key")
                .single()
                .execute()
            )
            if isinstance(resp.data, dict):
                val = resp.data.get("value", "")
                if val:
                    return str(val)
        except Exception:
            log.debug("Supabase app_settings unavailable; falling back to env key", exc_info=True)
    key = settings.groq_api_key
    return key.get_secret_value() if key else ""


def get_effective_groq_key() -> str:
    """Return the active Groq API key (cached for _KEY_CACHE_TTL seconds)."""
    global _groq_key_cache
    now = time.monotonic()
    if _groq_key_cache and now < _groq_key_cache[1]:
        return _groq_key_cache[0]
    key = _fetch_groq_key()
    _groq_key_cache = (key, now + _KEY_CACHE_TTL)
    return key


def invalidate_groq_key_cache() -> None:
    global _groq_key_cache
    _groq_key_cache = None


# ---------------------------------------------------------------------------
# Dynamic OpenRouter API key (admin can override via /settings/openrouter-key)
# ---------------------------------------------------------------------------

_openrouter_key_cache: tuple[str, float] | None = None


def _fetch_openrouter_key() -> str:
    """Read from Supabase app_settings first, fall back to env var."""
    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        try:
            from supabase import create_client

            client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key.get_secret_value(),
            )
            resp = (
                client.table("app_settings")
                .select("value")
                .eq("key", "openrouter_api_key")
                .single()
                .execute()
            )
            if isinstance(resp.data, dict):
                val = resp.data.get("value", "")
                if val:
                    return str(val)
        except Exception:
            log.debug("Supabase app_settings unavailable; falling back to env key", exc_info=True)
    key = settings.openrouter_api_key
    return key.get_secret_value() if key else ""


def get_effective_openrouter_key() -> str:
    """Return the active OpenRouter API key (cached for _KEY_CACHE_TTL seconds)."""
    global _openrouter_key_cache
    now = time.monotonic()
    if _openrouter_key_cache and now < _openrouter_key_cache[1]:
        return _openrouter_key_cache[0]
    key = _fetch_openrouter_key()
    _openrouter_key_cache = (key, now + _KEY_CACHE_TTL)
    return key


def invalidate_openrouter_key_cache() -> None:
    global _openrouter_key_cache
    _openrouter_key_cache = None


# ---------------------------------------------------------------------------
# Dynamic model selection (admin can override via /settings/model)
# ---------------------------------------------------------------------------

_model_cache: tuple[str, float] | None = None
_MODEL_CACHE_TTL = 60  # seconds


def _fetch_model_id() -> str:
    """Read active model from Supabase app_settings, fall back to config default."""
    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        try:
            from supabase import create_client

            client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key.get_secret_value(),
            )
            resp = (
                client.table("app_settings")
                .select("value")
                .eq("key", "active_model_id")
                .single()
                .execute()
            )
            if isinstance(resp.data, dict):
                val = resp.data.get("value", "")
                valid_ids = {m["id"] for m in AVAILABLE_MODELS}
                if val and val in valid_ids:
                    return str(val)
                if val:
                    log.warning(
                        "Stored model_id %r not in AVAILABLE_MODELS; using config default", val
                    )
        except Exception:
            log.debug("Could not fetch active_model_id from Supabase", exc_info=True)
    from smartops_agent.config import load_config

    models_cfg = load_config("models")
    default_name = str(models_cfg.get("default", "openrouter-large"))
    return str(models_cfg["models"][default_name]["model_id"])


def get_effective_model_id() -> str:
    """Return the active model ID (cached for _MODEL_CACHE_TTL seconds)."""
    global _model_cache
    now = time.monotonic()
    if _model_cache and now < _model_cache[1]:
        return _model_cache[0]
    model_id = _fetch_model_id()
    _model_cache = (model_id, now + _MODEL_CACHE_TTL)
    return model_id


def invalidate_model_cache() -> None:
    global _model_cache
    _model_cache = None


class LLMResponse:
    def __init__(
        self,
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
        finish_reason: str = "stop",
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls or []
        self.finish_reason = finish_reason

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class LLMClient(Protocol):
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float,
        timeout: float,
    ) -> LLMResponse: ...


class GroqClient:
    def __init__(self, model_id: str, api_key: str) -> None:
        self._model = model_id
        self._api_key = api_key

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.0,
        timeout: float = 20.0,
    ) -> LLMResponse:
        import groq

        client = groq.Groq(api_key=self._api_key)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "timeout": timeout,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                )
        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
        )


class OpenRouterClient:
    _BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model_id: str, api_key: str) -> None:
        self._model = model_id
        self._api_key = api_key

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.0,
        timeout: float = 30.0,
    ) -> LLMResponse:
        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY n'est pas configuré.")
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        with httpx.Client(timeout=timeout) as client:
            r = client.post(
                self._BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://smartopsagent.netlify.app",
                },
            )
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                if code == 429:
                    raise RuntimeError(
                        "Quota OpenRouter épuisé. Réessayez dans quelques minutes "
                        "ou changez de modèle via /settings/model."
                    ) from exc
                raise RuntimeError(f"Erreur HTTP {code} du fournisseur LLM.") from exc
        data = r.json()
        choice = data["choices"][0]
        msg = choice["message"]
        tool_calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            tool_calls.append(
                {
                    "id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "arguments": json.loads(fn.get("arguments", "{}")),
                }
            )
        return LLMResponse(
            content=msg.get("content"),
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason") or "stop",
        )


class OllamaClient:
    def __init__(self, model_id: str, base_url: str) -> None:
        self._model = model_id
        self._base_url = base_url.rstrip("/")

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.0,
        timeout: float = 20.0,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools
        with httpx.Client(timeout=timeout) as client:
            r = client.post(f"{self._base_url}/api/chat", json=payload)
            r.raise_for_status()
        data = r.json()
        msg = data.get("message", {})
        tool_calls = []
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            tool_calls.append(
                {
                    "id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "arguments": fn.get("arguments", {}),
                }
            )
        return LLMResponse(
            content=msg.get("content"),
            tool_calls=tool_calls,
            finish_reason="stop" if not tool_calls else "tool_calls",
        )


def build_llm_client(provider: str, model_id: str) -> LLMClient:
    settings = get_settings()
    effective_model = get_effective_model_id()
    if provider == "openrouter":
        return OpenRouterClient(model_id=effective_model, api_key=get_effective_openrouter_key())
    if provider == "groq":
        return GroqClient(model_id=effective_model, api_key=get_effective_groq_key())
    if provider == "ollama":
        return OllamaClient(model_id=model_id, base_url=settings.ollama_base_url)
    raise ValueError(f"Fournisseur LLM inconnu : {provider}")
