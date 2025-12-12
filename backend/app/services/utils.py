from __future__ import annotations
from typing import List, Any
import asyncio
import time
import json
import redis.asyncio as redis
from app.services.redis_client import redis_client
from app.models.candles import Candle



# In memory cache per process
CACHE_TTL_SECONDS = 60 
RATE_LIMIT_PER_MINUTE = 50  # Finnhub free tier limit
RATE_LIMIT_WINDOW_SECONDS = 60.0

class RateLimitError(Exception):
    pass


# key: (symbol, resolution, from_ts, to_ts, provider)
async def _cache_key(key: tuple) -> str:
    """Generates a consistent, hashable, and readable cache key string."""
    return f"candle:{':'.join(map(str, key))}"

async def _cache_get(key: tuple) -> List[Candle] | None:
    """Return cached candles if present, relying on Redis TTL for expiry."""
    if redis_client is None: return None
    key_str = await _cache_key(key)
    cached_data = await redis_client.get(key_str)
    if cached_data:
        try:
            data = json.loads(cached_data)
            return [Candle(**item) for item in data]
        except exception as e:
            print(f"Error deserializing cached data for key {key_str}: {e}")
            return None
    return None

async def _cache_set(key: tuple, candles: List[Candle]) -> None:
    """Cache Candles with a TTL"""
    if redis_client is None: return None
    key_str = await _cache_key(key)
    data_to_cache = [c.model_dump() for c in candles]
    await redis_client.set(
        key_str,
        json.dumps(data_to_cache),
        ex=CACHE_TTL_SECONDS
    )


async def _rate_limit_check(provider: str) -> None:
    """
    Check and update rate limit state using a Redis-based sliding window log.
    This is process-safe and highly concurrent.
    """
    if redis_client is None:
        raise RateLimitError("Redis client not initialized for rate limiting.")
    
    key = f"rl:{provider}"
    now_ms = int(time.time() * 1000)
    window_start_ms = now_ms - int(RATE_LIMIT_WINDOW_SECONDS * 1000)

    pipe = redis_client.pipeline()

    # Remove timestamps outside the current window
    pipe.zremrangebyscore(key, 0, window_start_ms)

    # Add the current timestamp
    pipe.zadd(key, {str(now_ms): now_ms})
    # Get the current count of timestamps in the window
    pipe.zcard(key)
    # Set expiration for the key to avoid stale data
    pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS + 5)

    _, _, count, _ = await pipe.execute()

    if count > RATE_LIMIT_PER_MINUTE:
        await redis_client.zrem(key, now_ms)
        raise RateLimitError(
            f"Rate limit of {RATE_LIMIT_PER_MINUTE} exceeded for provider {provider}: {count} requests in the last minute."
        )