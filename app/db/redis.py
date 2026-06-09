"""Redis connection helper."""

import json
import logging
from typing import Any

import redis.asyncio as aioredis
from app.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return a shared async Redis client, creating it on first call."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            _settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def close_redis() -> None:
    """Close the shared Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None


async def cache_conversation_context(
    redis: aioredis.Redis,
    conversation_id: Any,
    messages: list[Any],
    facts: dict[str, Any],
    ttl: int = 86400,
) -> None:
    """Cache conversation context in Redis."""
    key = f"conv:{conversation_id}:context"
    payload = {
        "messages": [
            {
                "id": str(getattr(m, "id", "")),
                "direction": getattr(m, "direction", ""),
                "content": getattr(m, "content", ""),
                "sent_at": getattr(m, "sent_at", None).isoformat()
                if getattr(m, "sent_at", None)
                else None,
                "message_type": getattr(m, "message_type", "text"),
                "intent_classification": getattr(m, "intent_classification", None),
                "llm_model": getattr(m, "llm_model", None),
                "tokens_used": getattr(m, "tokens_used", None),
                "typing_delay_ms": getattr(m, "typing_delay_ms", None),
            }
            for m in messages
        ],
        "facts": facts or {},
    }
    try:
        await redis.setex(key, ttl, json.dumps(payload))
    except Exception as exc:
        logger.warning("Failed to cache conversation context: %s", exc)


async def get_cached_conversation_context(
    redis: aioredis.Redis,
    conversation_id: Any,
) -> dict[str, Any] | None:
    """Retrieve cached conversation context from Redis."""
    key = f"conv:{conversation_id}:context"
    try:
        data = await redis.get(key)
        if data:
            return json.loads(data)
    except Exception as exc:
        logger.warning("Failed to get cached conversation context: %s", exc)
    return None


async def invalidate_conversation_cache(
    redis: aioredis.Redis,
    conversation_id: Any,
) -> None:
    """Remove cached conversation context from Redis."""
    key = f"conv:{conversation_id}:context"
    try:
        await redis.delete(key)
    except Exception as exc:
        logger.warning("Failed to invalidate conversation cache: %s", exc)
