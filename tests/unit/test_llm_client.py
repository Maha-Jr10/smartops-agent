"""Tests du client LLM (hors appels réseau)."""

from __future__ import annotations

import pytest

from smartops_agent.agent.llm_client import LLMResponse, build_llm_client

pytestmark = pytest.mark.unit


def test_llm_response_has_tool_calls() -> None:
    r = LLMResponse(
        content=None,
        tool_calls=[{"id": "1", "name": "search_crm", "arguments": {}}],
    )
    assert r.has_tool_calls is True


def test_llm_response_no_tool_calls() -> None:
    r = LLMResponse(content="Bonjour", tool_calls=[])
    assert r.has_tool_calls is False


def test_build_llm_client_groq_returns_groq_client() -> None:
    from smartops_agent.agent.llm_client import GroqClient

    client = build_llm_client("groq", "llama-3.3-70b-versatile")
    assert isinstance(client, GroqClient)


def test_build_llm_client_ollama_returns_ollama_client() -> None:
    from smartops_agent.agent.llm_client import OllamaClient

    client = build_llm_client("ollama", "qwen2.5:7b")
    assert isinstance(client, OllamaClient)


def test_build_llm_client_unknown_provider_raises() -> None:
    with pytest.raises(ValueError, match="inconnu"):
        build_llm_client("unknown_provider", "some-model")
