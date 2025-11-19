from __future__ import annotations
from app.models.candles import Candle
from typing import List, Literal
import yfinance as yf
from httpx import HTTPStatusError
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
) -> List[Candle]:
    """
    Wraps the existing Finnhub REST call and normalizes to a list of
    {t, o, h, l, c, v} dicts.
    """

    candles = await finnhub_get_stock_candles(symbol, resolution, from_ts, to_ts)
    return candles

def _fetch_yahoo_candles_sync(
    symbol: str,
    resolution: Resolution,
    from_ts: int,
    to_ts: int,
) -> List[Candle]:
    """
    Blocking Yahoo Finance fetch. We will call this via asyncio.to_thread
    so it doesn't block the event loop.
    """
    start_dt_ucc = _unix_to_datetime(from_ts)
    end_dt_ucc = _unix_to_datetime(to_ts)
    start = start_dt_ucc.replace(tzinfo=None)
    end = end_dt_ucc.replace(tzinfo=None)

    # Map our resolution to yfinance interval strings
    interval_map = {
        "1": "1m",
        "5": "5m",
        "15": "15m",
        "30": "30m",
        "60": "1h",
        "D": "D",
        "W": "W",
        "M": "M",
    }
    interval = interval_map.get(resolution, "1d")

    print (f"[YAHOO] symbol={symbol}, start={start}, end={end}, interval={interval}")

    df = yf.download(
        symbol, 
        start=start,
        end=end,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )

    if df is None or df.empty:
        print(f"[YAHOO] Empty DataFrame fpr {symbol}, interval: {interval}, start: {start}, end: {end}")
        return []
    
    # df index is Timestamp, columns are: Open, High, Low, Close, Adj Close, Volume
    candles: List[Candle] = []
    for ts, row in df.dropna(subset=["Open", "High", "Low", "Close"]).iterrows():
        ts_dt = ts.to_pydatetime()
        candles.append(
            {
                "t": int(ts_dt.replace(tzinfo=timezone.utc).timestamp()),
                "o": float(row["Open"]),
                "h": float(row["High"]),
                "l": float(row["Low"]),
                "c": float(row["Close"]),
                "v": float(row.get("Volume", 0.0)),
            }
        )
    print (f"[YAHOO] Returning {len(candles)} candles for {symbol}, interval: {interval}, start: {start}, end: {end}")
    return candles

async def _fetch_yahoo_candles(
    symbol: str,
    resolution: Resolution,
    from_ts: int,
    to_ts: int,
) -> List[Candle]:
    return await asyncio.to_thread(
        _fetch_yahoo_candles_sync, symbol, resolution, from_ts, to_ts
    )

async def get_historical_candles(
    symbol: str, 
    resolution: Resolution,
    from_ts: int,
    to_ts: int,
    provider: str = "auto"
) -> List[Candle]:
    """
    Unified entry point for historical candles.

    - provider="auto": choose Finnhub for near-term intraday, Yahoo for
      long-range or higher timeframe.
    - provider="finnhub" or "yahoo": force a specific provider.
    """
    provider_norm = (provider or "auto").lower()
    if provider_norm == "auto":
        range_seconds = max(to_ts - from_ts, 0)
        one_year_seconds = 365 * 24 * 60 * 60
        
        if resolution in ("1", "5", "15", "30", "60") and range_seconds <= one_year_seconds:
            provider_to_use = "finnhub"
        else:
            provider_to_use = "yahoo"
    elif provider_norm in ("finnhub", "yahoo"):
        provider_to_use = provider_norm
    else:
        raise ValueError(f"Invalid provider: {provider_norm}")
    
    if provider_to_use == "finnhub":
        try:
            return await _fetch_finnhub_candles(symbol, resolution, from_ts, to_ts)
        except HTTPStatusError as e:
            # If auto-selected Finnhub and it fails (403/401/429/etc)
            if provider_norm == "auto":
                print(f"[FINNHUB] HTTP error {e.response.status_code}, falling back to Yahoo")
                return await(_fetch_yahoo_candles(symbol, resolution, from_ts, to_ts))
            raise
    elif provider_to_use == "yahoo":
        return await _fetch_yahoo_candles(symbol, resolution, from_ts, to_ts)