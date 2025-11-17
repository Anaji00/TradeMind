from __future__ import annotations

from typing import Optional
import asyncio

from fastapi import WebSocket
from app.models.candles import Candle
from app.services.finnhub_client import get_recent_candles
from app.services.pattern_detector import classify_candle

async def stream_candles_to_websocket(
    websocket: WebSocket,
    symbol: str,
    resolution: str = "1",
    lookback_minutes: int = 120,
    poll_interval_seconds: int = 5,
) -> None:
    """
    Continuously poll Finnhub for recent candles and push new ones
    to the client as JSON.

    This is per-WebSocket connection: simple and easy to reason about.
    Later you can centralize polling if you have many clients.
    """
    last_ts = Optional[int] = None
    while True:
        candles = await get_recent_candles(
            symbol=symbol,
            resolution=resolution,
            lookback_minutes=lookback_minutes,
        )
        if candles:
            latest: Candle = candles[-1]
            previous: Optional[Candle] = candles[-2] if len(candles) >= 2 else None

            if last_ts is None or latest.t != last_ts:
                patterns = classify_candle(latest, previous)

                await websocket.send_json(
                    {
                        "type": "candle",
                        "symbol": symbol,
                        "resolution": resolution,
                        "candle": latest.model_dump(),
                        "patterns": patterns,
                    }
                )

                last_ts = latest.t

        await asyncio.sleep(poll_interval_seconds)