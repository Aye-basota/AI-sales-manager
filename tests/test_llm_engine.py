from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.llm.engine import (
    DEFAULT_MODELS,
    FALLBACK_TEXT,
    LLMEngine,
    OPENROUTER_BASE_URL,
    _is_retryable_error,
    _provider_from_base_url,
)


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

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
        result = await engine.generate(
            messages=[{"role": "user", "content": "Hi"}],
            model="qwen-2.5-72b-instruct",
        )

    assert result["text"] == "Hello there"
    assert result["model"] == "qwen-2.5-72b-instruct"
    assert result["tokens_used"] == 21


def test_provider_resolution_and_retryable_error_helpers():
    assert _provider_from_base_url(None) == "openrouter"
    assert _provider_from_base_url("https://dashscope-intl.aliyuncs.com") == "dashscope"
    assert _provider_from_base_url("https://example.com") == "openrouter"
    assert LLMEngine(api_key="key", provider="DASHSCOPE").provider == "dashscope"
    assert _is_retryable_error(httpx.ConnectError("down")) is True
    assert _is_retryable_error(httpx.TimeoutException("slow")) is True
    assert _is_retryable_error(RuntimeError("bad")) is False


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

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
        result = await engine.generate([{"role": "user", "content": "Hi"}])

    _, kwargs = mock_client.post.call_args
    payload = kwargs["json"]
    assert payload["model"] == DEFAULT_MODELS[0]
    assert result["text"] == "Default model reply"


@pytest.mark.asyncio
async def test_generate_includes_max_tokens_and_openrouter_headers(engine):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Reply"}}],
        "usage": {},
    }
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client) as client_cls:
        await engine.generate([{"role": "user", "content": "Hi"}], max_tokens=77)

    assert mock_client.post.call_args.kwargs["json"]["max_tokens"] == 77
    headers = client_cls.call_args.kwargs["headers"]
    assert "HTTP-Referer" in headers
    assert "X-Title" in headers


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

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
        result = await engine.generate_with_fallback(
            [{"role": "user", "content": "Hi"}]
        )

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

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
        result = await engine.generate_with_fallback(
            [{"role": "user", "content": "Hi"}]
        )

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

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
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


@pytest.mark.asyncio
async def test_generate_response_with_guardrails_approved_first_try(engine):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Approved text"}}],
        "usage": {"total_tokens": 5},
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
        result = await engine.generate_response_with_guardrails(
            messages=[{"role": "user", "content": "Hi"}],
            last_messages=[],
        )

    assert result["text"] == "Approved text"
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_generate_response_with_guardrails_fallback_after_retries(engine):
    bad_response = MagicMock()
    bad_response.json.return_value = {
        "choices": [{"message": {"content": "Я бот"}}],
        "usage": {"total_tokens": 2},
    }
    bad_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = bad_response

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
        result = await engine.generate_response_with_guardrails(
            messages=[{"role": "user", "content": "Hi"}],
            last_messages=[],
            max_retries=1,
        )

    assert result["text"] == FALLBACK_TEXT
    assert result["model"] == "fallback"
    # initial + 1 retry = 2 calls
    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_generate_response_with_guardrails_approved_on_retry(engine):
    bad_response = MagicMock()
    bad_response.json.return_value = {
        "choices": [{"message": {"content": "**markdown**"}}],
        "usage": {"total_tokens": 2},
    }
    bad_response.raise_for_status = MagicMock()

    good_response = MagicMock()
    good_response.json.return_value = {
        "choices": [{"message": {"content": "Plain text reply"}}],
        "usage": {"total_tokens": 3},
    }
    good_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.side_effect = [bad_response, good_response]

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
        result = await engine.generate_response_with_guardrails(
            messages=[{"role": "user", "content": "Hi"}],
            last_messages=[],
            max_retries=1,
        )

    assert result["text"] == "Plain text reply"
    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_generate_with_fallback_retry_429_then_success(engine):
    fail_response = MagicMock()
    fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Rate limited",
        request=MagicMock(),
        response=MagicMock(status_code=429),
    )

    ok_response = MagicMock()
    ok_response.json.return_value = {
        "choices": [{"message": {"content": "Retry success"}}],
        "usage": {"total_tokens": 3},
    }
    ok_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.side_effect = [fail_response, ok_response]

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
        with patch("app.llm.engine.asyncio.sleep") as mock_sleep:
            result = await engine.generate_with_fallback(
                [{"role": "user", "content": "Hi"}]
            )

    assert result["text"] == "Retry success"
    assert mock_client.post.call_count == 2
    mock_sleep.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_generate_with_fallback_all_retryable_exhausted_returns_fallback(engine):
    fail_response = MagicMock()
    fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Gateway",
        request=MagicMock(),
        response=MagicMock(status_code=502),
    )

    mock_client = AsyncMock()
    # First model: 4 failures (1 initial + 3 retries)
    # Second model: 1 failure (no retries left)
    # Third model: 1 failure (no retries left)
    mock_client.post.side_effect = [fail_response] * 6

    with patch("app.llm.engine.httpx.AsyncClient", return_value=mock_client):
        with patch("app.llm.engine.asyncio.sleep") as mock_sleep:
            result = await engine.generate_with_fallback(
                [{"role": "user", "content": "Hi"}]
            )

    assert result["text"] == FALLBACK_TEXT
    assert result["model"] == "fallback"
    assert mock_client.post.call_count == 6
    assert mock_sleep.await_count == 3
    mock_sleep.assert_any_await(1)
    mock_sleep.assert_any_await(2)
    mock_sleep.assert_any_await(4)
