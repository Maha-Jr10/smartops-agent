"""Interface unique vers Groq et Ollama (ADR 0001 : boucle écrite par nous)."""

from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from smartops_agent.config import get_settings


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
    if provider == "groq":
        key = settings.groq_api_key
        api_key = key.get_secret_value() if key else ""
        return GroqClient(model_id=model_id, api_key=api_key)
    if provider == "ollama":
        return OllamaClient(model_id=model_id, base_url=settings.ollama_base_url)
    raise ValueError(f"Fournisseur LLM inconnu : {provider}")
