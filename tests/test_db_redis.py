import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.db.redis import (
    cache_conversation_context,
    get_cached_conversation_context,
    invalidate_conversation_cache,
)


@pytest.mark.asyncio
async def test_cache_conversation_context():
    redis = AsyncMock()
    messages = [SimpleNamespace(direction="outbound", content="Hello")]
    facts = {"budget": "10k"}
    await cache_conversation_context(redis, "conv-1", messages, facts, ttl=60)
    redis.setex.assert_awaited_once()
    key, ttl, value = redis.setex.call_args.args
    assert key == "conv:conv-1:context"
    assert ttl == 60
    data = json.loads(value)
    assert data["messages"][0]["direction"] == "outbound"
    assert data["messages"][0]["content"] == "Hello"
    assert data["facts"] == facts


@pytest.mark.asyncio
async def test_get_cached_conversation_context_hit():
    redis = AsyncMock()
    redis.get = AsyncMock(
        return_value='{"messages": [{"direction": "inbound", "content": "Hi"}], "facts": {"city": "Moscow"}}'
    )
    result = await get_cached_conversation_context(redis, "conv-1")
    assert result is not None
    assert result["messages"][0]["content"] == "Hi"
    assert result["facts"]["city"] == "Moscow"


@pytest.mark.asyncio
async def test_get_cached_conversation_context_miss():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    result = await get_cached_conversation_context(redis, "conv-1")
    assert result is None


@pytest.mark.asyncio
async def test_invalidate_conversation_cache():
    redis = AsyncMock()
    await invalidate_conversation_cache(redis, "conv-1")
    redis.delete.assert_awaited_once_with("conv:conv-1:context")
