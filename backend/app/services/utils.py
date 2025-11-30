from __future__ import annotations
from typing import List, Dict, Any
import time
from app.models.candles import Candle



# In memory cache per process
CACHE_TTL_SECONDS = 60 
CACHE_MAX_ENTRIES = 500

# Rate Limiting / guardrails
RATE_LIMIT_PER_MINUTE = 50  # Finnhub free tier limit
RATE_LIMIT_WINDOW_SECONDS = 60.0

class RateLimitError(Exception):
    pass


# key: (symbol, resolution, from_ts, to_ts, provider)
_cache_store: Dict[tuple, Dict[str, Any]] = {}

# key: provider, value: list of request timestamps
_rate_limit_state: Dict[str, List[float]] = {}

def _cache_get(key: tuple) -> List[Candle] | None:
    """Return cached candles if present and not expired."""
    entry = _cache_store.get(key)
    if not entry:
        return None
    now = time.time()
    if now >= entry["expires_at"]:
        _cache_store.pop(key, None)
        return None
    return entry["candles"]

def _cache_set(key: tuple, candles: List[Candle]) -> None:
    """Store candles in cache."""
    if len(_cache_store) >= CACHE_MAX_ENTRIES:
        # Evict the oldest entry
        _cache_store.pop(next(iter(_cache_store)), None)
    _cache_store[key] = {
        "candles": candles,
        "expires_at": time.time() + CACHE_TTL_SECONDS,
    }

def _rate_limit_check(provider: str) -> None:
    """Check and update rate limit state for the given provider."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _rate_limit_state.get(provider, [])
    # Remove timestamps outside the window
    timestamps = [ts for ts in timestamps if ts >= window_start]
    if len(timestamps) >= RATE_LIMIT_PER_MINUTE:
        raise RateLimitError(f"Rate limit exceeded for provider {provider}")
    timestamps.append(now)
    _rate_limit_state[provider] = timestamps

