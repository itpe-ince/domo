"""Unit tests for LLMGatewayClient — C-1 ai-artist-interview-generation.

Tests:
  1. Mock mode when LLM_GATEWAY_API_KEY is empty
  2. Mock response contains expected markdown structure
  3. Real API path calls correct endpoint with correct payload (httpx mocked)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── Test 1: Mock mode when API key not configured ───────────────────────────


@pytest.mark.asyncio
async def test_llm_gateway_mock_mode_no_key():
    """When LLM_GATEWAY_API_KEY is empty, is_mock is True."""
    with patch("app.services.llm_gateway.get_settings") as mock_settings:
        settings = MagicMock()
        settings.llm_gateway_api_key = ""
        settings.llm_gateway_url = "https://llm.example.com/v1"
        settings.llm_model_name = "gemma4-e4b"
        mock_settings.return_value = settings

        from app.services.llm_gateway import LLMGatewayClient

        client = LLMGatewayClient()
        assert client.is_mock is True


# ─── Test 2: Mock response contains expected markdown structure ───────────────


@pytest.mark.asyncio
async def test_llm_gateway_mock_response_content():
    """Mock response returns a dict with content/model/usage_tokens keys."""
    with patch("app.services.llm_gateway.get_settings") as mock_settings:
        settings = MagicMock()
        settings.llm_gateway_api_key = ""
        settings.llm_gateway_url = "https://llm.example.com/v1"
        settings.llm_model_name = "gemma4-e4b"
        mock_settings.return_value = settings

        from app.services.llm_gateway import LLMGatewayClient

        client = LLMGatewayClient()
        result = await client.generate_interview("Test prompt")

    assert "content" in result
    assert "model" in result
    assert "usage_tokens" in result
    assert result["model"] == "mock-gateway"
    assert result["usage_tokens"] == 0
    # Mock content should be a non-empty markdown string
    assert len(result["content"]) > 50
    assert "##" in result["content"] or "#" in result["content"]


# ─── Test 3: Real API path calls correct endpoint ────────────────────────────


@pytest.mark.asyncio
async def test_llm_gateway_real_api_call():
    """When API key is set, calls the LLM gateway with correct payload."""
    import httpx

    mock_response_data = {
        "choices": [{"message": {"content": "## 인터뷰\n\nQ: ...\nA: ..."}}],
        "model": "gemma4-e4b",
        "usage": {"total_tokens": 512},
    }

    with patch("app.services.llm_gateway.get_settings") as mock_settings:
        settings = MagicMock()
        settings.llm_gateway_api_key = "gw-test-key"
        settings.llm_gateway_url = "https://llm.example.com/v1"
        settings.llm_model_name = "gemma4-e4b"
        mock_settings.return_value = settings

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = mock_response_data

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.llm_gateway.httpx.AsyncClient", return_value=mock_client):
            from app.services.llm_gateway import LLMGatewayClient

            client = LLMGatewayClient()
            assert client.is_mock is False

            result = await client.generate_interview("Artist prompt here")

    assert result["content"] == "## 인터뷰\n\nQ: ...\nA: ..."
    assert result["model"] == "gemma4-e4b"
    assert result["usage_tokens"] == 512

    # Verify correct endpoint was called
    call_args = mock_client.post.call_args
    assert "/chat/completions" in call_args[0][0]
    payload = call_args[1]["json"]
    assert payload["model"] == "gemma4-e4b"
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert payload["messages"][1]["content"] == "Artist prompt here"
