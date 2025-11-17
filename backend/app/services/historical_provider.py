from __future__ import annotations
from app.models.candles import Candle
from typing import List, Literal, Dict
import yfinance as yf
import asyncio
from datetime import datetime, timezone

from .finnhub_client import get_stock_candles as finnhub_get_stock_candles

Resolution = Literal["1", "5", "15", "30", "60", "D", "W", "M"]


def _unix_to_datetime(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz = timezone.utc)


async def _fetch_finnhub_candles(
    symbol: str,
    resolution: Resolution,
    from_ts: int,
    to_ts: int,
) -> List[Dict]:
    """
    Wraps the existing Finnhub REST call and normalizes to a list of
    {t, o, h, l, c, v} dicts.
    """
    candles_list: List[Candle] = await finnhub_get_stock_candles(symbol, resolution, from_ts, to_ts)    
    candles: List[Dict] = []
    for c in candles_list:
        candles.append({
            "t": c.t,
            "o": c.o,
            "h": c.h,
            "l": c.l,
            "c": c.c,
            "v": c.v,
            })
        return candles

def _fetch_yahoo_candles_sync(
    symbol: str,
    resolution: Resolution,
    from_ts: int,
    to_ts: int,
) -> List[Dict]:
    """
    Blocking Yahoo Finance fetch. We will call this via asyncio.to_thread
    so it doesn't block the event loop.
    """
    start = _unix_to_datetime(from_ts)
    end = _unix_to_datetime(to_ts)

    # Map our resolution to yfinance interval strings
    interval_map = {
        "1": "1m",
        "5": "5m",
        "15": "15m",
        "30": "30m",
        "60": "1h",
        "D": "1d",
        "W": "1wk",
        "M": "1mo",
    }
    interval = interval_map.get(resolution, "1h")

    df = yf.download(
        symbol, 
        start=start,
        end=end,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )

    if df.empty:
        return []
    
    # df index is Timestamp, columns are: Open, High, Low, Close, Adj Close, Volume
    candles: List[Dict] = []
    for ts, row in df.dropna().iterrows():
        candles.append(
            {
                "t": int(ts.to_pydatetime().replace(tzinfo=timezone.utc).timestamp()),
                "o": float(row["Open"]),
                "h": float(row["High"]),
                "l": float(row["Low"]),
                "c": float(row["Close"]),
                "v": float(row.get("Volume", 0.0)),
            }
        )
    return candles

async def _fetch_yahoo_candles(
    symbol: str,
    resolution: Resolution,
    from_ts: int,
    to_ts: int,
) -> List[Dict]:
    return await asyncio.to_thread(
        _fetch_yahoo_candles_sync, symbol, resolution, from_ts, to_ts
    )

async def get_historical_candles(
    symbol: str, 
    resolution: Resolution,
    from_ts: int,
    to_ts: int,
    provider: str = "auto"
) -> List[Dict]:
    """
    Unified entry point for historical candles.

    - provider="auto": choose Finnhub for near-term intraday, Yahoo for
      long-range or higher timeframe.
    - provider="finnhub" or "yahoo": force a specific provider.
    """
    if provider == "auto":
        range_seconds = to_ts - from_ts
        one_year_seconds = 365 * 24 * 60 * 60
        if resolution in ("1", "5", "15", "30", "60") and range_seconds < one_year_seconds:
            provider = "finnhub"
        else:
            provider = "yahoo"
    else:
        provider_to_use = provider


    if provider_to_use == "finnhub":
        return await _fetch_finnhub_candles(symbol, resolution, from_ts, to_ts)
    elif provider_to_use == "yahoo":
        return await _fetch_yahoo_candles(symbol, resolution, from_ts, to_ts)
    else:
        raise ValueError(f"Unknown provider: {provider}")