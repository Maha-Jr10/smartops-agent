"""Tests du client LLM (hors appels réseau)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
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


def test_openrouter_rate_limit_raises_readable_error() -> None:
    from smartops_agent.agent.llm_client import OpenRouterClient

    client = OpenRouterClient(model_id="test/model", api_key="fake-key")
    mock_response = MagicMock()
    mock_response.status_code = 429
    http_err = httpx.HTTPStatusError("429", request=MagicMock(), response=mock_response)

    with patch("httpx.Client") as mock_client_cls:
        mock_http = mock_client_cls.return_value.__enter__.return_value
        mock_http.post.return_value.raise_for_status.side_effect = http_err
        with pytest.raises(RuntimeError, match="Quota OpenRouter"):
            client.chat(messages=[{"role": "user", "content": "test"}], tools=[])


def test_openrouter_http_error_raises_readable_error() -> None:
    from smartops_agent.agent.llm_client import OpenRouterClient

    client = OpenRouterClient(model_id="test/model", api_key="fake-key")
    mock_response = MagicMock()
    mock_response.status_code = 503
    http_err = httpx.HTTPStatusError("503", request=MagicMock(), response=mock_response)

    with patch("httpx.Client") as mock_client_cls:
        mock_http = mock_client_cls.return_value.__enter__.return_value
        mock_http.post.return_value.raise_for_status.side_effect = http_err
        with pytest.raises(RuntimeError, match="503"):
            client.chat(messages=[{"role": "user", "content": "test"}], tools=[])
