"""Redis connection helper."""

import redis.asyncio as aioredis
from app.config import get_settings

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
