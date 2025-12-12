from __future__ import annotations
from typing import Optional, Set, Dict
import asyncio
import time
import json


from app.services.redis_client import redis_client
from app.services.pattern_detector import classify_candle
from app.services.finnhub_client import get_recent_candles

class CandlePoller:
    """
    Manages a single, centralized polling loop for all subscribed symbols, 
    publishing results to Redis Pub/Sub.
    """

    _symbols_to_poll: Set[str] = set()
    _last_ts: Dict[str, int] = {}
    POLL_INTERVAL_SECONDS: int = 5
    LOOKBACK_MINUTES: int = 120
    RESOLUTION: str = "1"

    REDIS_CHANNEL = "live_candles"

    _polling_task: Optional[asyncio.Task] = None

    @classmethod
    def start_polling(cls):
        """Start the background polling task."""
        if cls._polling_task is None or cls._polling_task.done():
            cls._polling_task = asyncio.create_task(cls._polling_loop())
            print("CandlePoller: Background polling started.")

    @classmethod
    def stop_polling(cls):
        if cls._polling_task and not cls._polling_task.done():
            cls._polling_task.cancel()
            cls._polling_task = None
            print("CandlePoller: Background polling stopped.")

    @classmethod
    def subscribe(cls, symbol: str) -> None:
        """Add a symbol and ensure the polling loop is running."""
        symbol = symbol.upper()
        if symbol not in cls._symbols_to_poll:
            cls._symbols_to_poll.add(symbol)
            cls.start_polling()
            print(f"CandlePoller: Subscribed to {symbol}.")

    @classmethod
    def unsubscribe(cls, symbol: str) -> None:
        """Remove a symbol from polling."""
        symbol = symbol.upper()
        cls._symbols_to_poll.discard(symbol)
        cls._last_ts.pop(symbol, None)
        print(f"CandlePoller: Unsubscribed from {symbol}.")

    @classmethod
    async def _polling_loop(cls):
        """Main polling Logic."""
        while cls._symbols_to_poll:
            start_time = time.time()

            # Create polling tasks for all subscribed symbols concurrently
            tasks = [cls._poll_symbol(symbol) for symbol in list(cls._symbols_to_poll)]
            await asyncio.gather(*tasks)

            # Wait for the remainder of the interval
            elapsed = time.time() - start_time
            sleep_time = max(0, cls.POLL_INTERVAL_SECONDS - elapsed)
            await asyncio.sleep(sleep_time)

        # If all symbols are unsubscribed, stop the background task gracefully
        cls.stop_polling()

    @classmethod
    async def _poll_symbol(cls, symbol: str) -> None:
        """Polls Finnhub for a single symbol and broadcasts new data."""
        try:
            candles = await get_recent_candles(
                symbol=symbol,
                resolution=cls.RESOLUTION,
                lookback_minutes=cls.LOOKBACK_MINUTES,
            )
            if not candles:
                return
            
            latest = candles[-1]
            previous = candles[-2] if len(candles) >= 2 else None
            last_ts = cls._last_ts.get(symbol)

            # Check if this candle is new or an update to the current candle
            if last_ts is None or latest.t >= last_ts:
                patterns = classify_candle(latest, previous)
                message = {
                    "type": "candle",
                    "symbol": symbol,
                    "resolution": cls.RESOLUTION,
                    "candle": latest.model_dump(),
                    "patterns": patterns,
                }
                if redis_client:
                    await redis_client.publish(cls.REDIS_CHANNEL, json.dumps(message))
                    print(f"CandlePoller: Published candle for {symbol} at {latest.t}.")
                
                cls._last_ts[symbol] = latest.t
        except Exception as e:
            print(f"CandlePoller: Error polling {symbol}: {e}")
            cls.unsubscribe(symbol)