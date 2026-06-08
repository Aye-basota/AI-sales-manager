import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.llm.engine import DEFAULT_MODELS, LLMEngine, OPENROUTER_BASE_URL


@pytest.fixture
def engine():
    return LLMEngine(api_key="test-key", base_url=OPENROUTER_BASE_URL)


@pytest.mark.asyncio
async def test_generate_success(engine):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "qwen-2.5-72b-instruct",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello there"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 9, "completion_tokens": 12, "total_tokens": 21},
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.is_closed = False

    with patch.object(engine, "client", mock_client):
        result = await engine.generate(
            messages=[{"role": "user", "content": "Hi"}],
            model="qwen-2.5-72b-instruct",
        )

    assert result["text"] == "Hello there"
    assert result["model"] == "qwen-2.5-72b-instruct"
    assert result["tokens_used"] == 21


@pytest.mark.asyncio
async def test_generate_uses_default_model(engine):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": " Default model reply "}}],
        "usage": {},
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch.object(engine, "client", mock_client):
        result = await engine.generate([{"role": "user", "content": "Hi"}])

    _, kwargs = mock_client.post.call_args
    payload = kwargs["json"]
    assert payload["model"] == DEFAULT_MODELS[0]
    assert result["text"] == "Default model reply"


@pytest.mark.asyncio
async def test_generate_with_fallback_primary_succeeds(engine):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Primary ok"}}],
        "usage": {"total_tokens": 5},
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch.object(engine, "client", mock_client):
        result = await engine.generate_with_fallback([{"role": "user", "content": "Hi"}])

    assert result["text"] == "Primary ok"
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_generate_with_fallback_retries_on_failure(engine):
    fail_response = MagicMock()
    fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )

    ok_response = MagicMock()
    ok_response.json.return_value = {
        "choices": [{"message": {"content": "Fallback ok"}}],
        "usage": {"total_tokens": 3},
    }
    ok_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.side_effect = [fail_response, ok_response]

    with patch.object(engine, "client", mock_client):
        result = await engine.generate_with_fallback([{"role": "user", "content": "Hi"}])

    assert result["text"] == "Fallback ok"
    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_generate_with_fallback_all_fail(engine):
    fail_response = MagicMock()
    fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )

    mock_client = AsyncMock()
    mock_client.post.return_value = fail_response

    with patch.object(engine, "client", mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await engine.generate_with_fallback([{"role": "user", "content": "Hi"}])

    assert mock_client.post.call_count == len(DEFAULT_MODELS)


@pytest.mark.asyncio
async def test_close_client(engine):
    mock_client = AsyncMock()
    mock_client.is_closed = False
    engine._client = mock_client

    await engine.close()
    mock_client.aclose.assert_awaited_once()
