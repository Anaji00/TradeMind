from __future__ import annotations
from app.models.candles import Candle, CandleWithTA
from typing import List, Literal, Dict
import yfinance as yf
from httpx import HTTPStatusError
import asyncio
from datetime import datetime, timezone
import pandas as pd
import time
import logging
from .ta_calculator import calculate_ta_indicators
from .utils import _cache_get, _cache_set, _rate_limit_check, RateLimitError
from .finnhub_client import get_stock_candles as finnhub_get_stock_candles

logger = logging.getLogger(__name__)

Resolution = Literal["1", "5", "15", "30", "60", "D", "W", "M"]

INTRADAY_RESOLUTION = ("1", "5", "15", "30", "60")
ONE_DAY_SECONDS = 60 * 60 * 24
THIRTY_DAYS_SECONDS = ONE_DAY_SECONDS * 30
ONE_YEAR_SECONDS = ONE_DAY_SECONDS * 365



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
    Blocking Yahoo Finance fetch. Runs in a thread via asyncio.to_thread.

    Handles both:
      - normal columns:  'Open','High','Low','Close','Volume'
      - MultiIndex:      ('Adj Close','AAPL'), ('Open','AAPL'), ...
    """
    start_dt_utc = _unix_to_datetime(from_ts)
    end_dt_utc = _unix_to_datetime(to_ts)
    start = start_dt_utc
    end = end_dt_utc

    # Map our resolution to yfinance interval strings
    interval_map = {
        "1": "1m",
        "5": "5m",
        "15": "15m",
        "30": "30m",
        "60": "60m",
        "D": "1d",
        "W": "1wk",
        "M": "1mo",
    }
    interval = interval_map.get(resolution, "1d")

    logger.debug(f"[YAHOO] symbol={symbol}, start={start}, end={end}, interval={interval}")
    try:
        df = yf.download(
            symbol, 
            start=start,
            end=end,
            interval=interval,
            progress=False,
            auto_adjust=False,
        )
    except Exception as e:
        logger.error(
            f"[YAHOO] Exception while downloading data for {symbol}: {e!r} "
            f"(interval={interval}, start={start}, end={end})"
        )
        return []

    if df is None or df.empty:
        logger.warning(
            f"[YAHOO] Empty DataFrame for {symbol}, "
            f"interval: {interval}, start: {start}, end: {end}"
        )        
        return []
    
    # normalize columns 
    sym = symbol.upper()
    # Case A: MultiIndex columns like ('Adj Close','AAPL'), names ['Price','Ticker']
    if isinstance(df.columns, pd.MultiIndex):
        logger.debug(f"[YAHOO] MultiIndex columns for {symbol} {df.columns}")
        names = list(df.columns.names)

        if "Ticker" in names:
            ticker_level = names.index("Ticker")
            df = df.xs(sym, axis = 1, level = ticker_level)
            # Now df.columns should be Index(['Adj Close','Close','High','Low','Open','Volume'], name='Price')
        else:
            # Fallback: find a level that contains our symbol
            used_level = None
            for lvl in range(df.columns.nlevels):
                if sym in df.columns.get_level_values(lvl):
                    used_level = lvl
                    df = df.xs(sym, axis = 1, level = lvl)
                    break
            logger.debug(f"[YAHOO] Used MultiIndex level {used_level} for ticker {sym}")
    # At this point for AAPL we expect columns like:
    # Index(['Adj Close','Close','High','Low','Open','Volume'], name='Price')

    required_columns = ["Open", "High", "Low", "Close"]
    if not all(col in df.columns for col in required_columns):
        logger.error(f"[YAHOO] Missing required columns for {symbol}, got {df.columns}")
        return []
    
    # Sample logs with human-readable times
    try:
        logger.debug(f"[YAHOO] Printing sample OHLC rows with times:")
        for ts, row in df[required_columns].head(5).iterrows():
            ts_dt = ts.to_pydatetime().replace(tzinfo=timezone.utc)
            # Format just date+time using format string
            ts_str = ts_dt.strftime("%Y-%m-%d %H:%M")
            logger.debug(
                f"  time={ts_str} | "
                f"open={row['Open']:.2f}, "
                f"high={row['High']:.2f}, "
                f"low={row['Low']:.2f}, "
                f"close={row['Close']:.2f}"
            )
    except Exception as e:
        logger.warning(f"[YAHOO] Error printing sample OHLC rows: {e}")
        
    candles: List[Candle] = []
    for ts, row in df.dropna(subset=required_columns).iterrows():
        ts_dt = ts.to_pydatetime()
        candles.append(
            Candle(
                t = int(ts_dt.replace(tzinfo=timezone.utc).timestamp()),
                o = float(row["Open"]),
                h = float(row["High"]),
                l = float(row["Low"]),
                c = float(row["Close"]),
                v = float(row.get("Volume", 0.0)),
            )
        )
    logger.debug(f"[YAHOO] Returning {len(candles)} candles for {symbol}, interval: {interval}, start: {start}, end: {end}")
    for c in candles[:3]:
        dt = datetime.fromtimestamp(c.t, tz=timezone.utc)
        dt_str = dt.strftime("%Y-%m-%d %H:%M")
        logger.debug(
            f"[YAHOO] sample candle: time = {dt_str}, "
            f"open={c.o:.2f}, high={c.h:.2f}, low={c.l:.2f}, close={c.c:.2f}, vol={c.v:.0f}"
        )
    
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
    provider: str = "auto",
    indicators: List[str] = []
) -> List[CandleWithTA]:
    """
    Unified entry point for historical candles.

    - provider="auto": choose Finnhub for near-term intraday, Yahoo for
      long-range or higher timeframe.
    - provider="finnhub" or "yahoo": force a specific provider.

    Also enforces guardrails for very fine resolutions (e.g., 1-minute)
    so we don't ask providers for impossible / overly heavy ranges.
    """
    provider_norm = (provider or "auto").lower()
    range_seconds = max(to_ts - from_ts, 0)
    symbol_upper = symbol.upper()

    raw_candles: List[Candle] = []

# 2. FIX: CONSOLIDATE GUARDRAILS HERE (Remove duplication from later blocks)
    if resolution == "1":
        # Yahoo/Auto 30-day limit
        if provider_norm in ("auto", "yahoo") and range_seconds > THIRTY_DAYS_SECONDS:
            raise ValueError(
                "1-minute candles are only supported within the last 30 days "
                "due to Yahoo Finance limitations. Please request a shorter "
                "range or use a higher timeframe (5, 15, 60, or D)."
            )
        # Finnhub/Auto 1-year limit
        elif provider_norm in ("auto", "finnhub") and range_seconds > ONE_YEAR_SECONDS:
            raise ValueError(
                "Finnhub does not support longer ranges than 1 year. "
                "Please request a shorter range."
            )
        
    

    
    # ---------- Provider selection ----------
    if provider_norm == "auto":
        if resolution in INTRADAY_RESOLUTION and range_seconds <= ONE_YEAR_SECONDS:
            provider_to_use = "finnhub"
        else:
            provider_to_use = "yahoo"
    elif provider_norm in ("finnhub", "yahoo"):
        provider_to_use = provider_norm
    else:
        raise ValueError(f"Invalid provider: {provider_norm}")
    
    cache_key = (symbol_upper, resolution, from_ts, to_ts, provider_to_use, tuple(sorted(indicators)))

    # ---------- Check cache ----------
    cached = await _cache_get(cache_key)
    if cached is not None:
        logger.info(
            f"[CACHE] Hit for {symbol_upper}, res={resolution}, "
            f"from={from_ts}, to={to_ts}, provider={provider_to_use}"
        )
        return cached
    
    #--------- Rate limit check ----------
    try:
        await _rate_limit_check(provider_to_use)
    except RateLimitError as e:
        # Re-raise the specific error so the router can handle it.
        # This allows returning a 429 status code.
        raise e
    
    if provider_to_use == "finnhub":
        try:
            raw_candles = await _fetch_finnhub_candles(symbol_upper, resolution, from_ts, to_ts)
        except HTTPStatusError as e:
            status = e.response.status_code
            text = e.response.text
            # If auto-selected Finnhub and it fails, fall back to Yahoo
            if provider_norm == "auto":
                logger.warning(
                    f"[FINNHUB] HTTP error {status} for {symbol_upper}, "
                    f"resolution={resolution}, range={range_seconds}s; "
                    "falling back to Yahoo."
                )
                try:
                    await _rate_limit_check("yahoo")
                    raw_candles = await _fetch_yahoo_candles(symbol, resolution, from_ts, to_ts)
                    provider_to_use = "yahoo"
                except Exception as e2:
                    raise ValueError(
                        f"Finnhub HTTP error {status}: {text}; "
                        f"Yahoo fallback also failed: {e2}"
                    ) from e2
            
            # User explicitly asked for Finnhub, so bubble up the error as a ValueError
            raise ValueError(f"Finnhub HTTP {status} for {symbol_upper}: {text}") from e

    elif provider_to_use == "yahoo":
        # -- Guardrails for Yahoo --
        try:
            raw_candles = await _fetch_yahoo_candles(symbol_upper, resolution, from_ts, to_ts)
        except Exception as e:
            raise ValueError(f"Yahoo Finance error for {symbol_upper}: {e}") from e
    if not raw_candles:
        logger.warning(f"No candles returned for {symbol_upper}, res={resolution}, {provider}")
        return []
    

    # ---------------------------------------------------------------------
    # COMMON PROCESSING BLOCK (TA, Caching)
    # ---------------------------------------------------------------------

    if indicators:
        ta_candles = calculate_ta_indicators(raw_candles, indicators)
        logger.info(f"Calculated {len(indicators)} indicators for {len(ta_candles)} candles" )
    else:
        ta_candles = [
            CandleWithTA(**c.model_dump()) for c in raw_candles
        ]

# Set cache with the augmented (TA-calculated) candles
    # Use the potentially updated provider_to_use (in case of Finnhub fallback)
    final_cache_key = (symbol_upper, resolution, from_ts, to_ts, provider_to_use, tuple(sorted(indicators)))
    await _cache_set(final_cache_key, ta_candles)
    return ta_candles
