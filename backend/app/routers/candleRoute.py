# app/routers/candles.py
from __future__ import annotations

from datetime import datetime, timezone, time, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException
from app.models.candles import Candle
from httpx import HTTPStatusError
from app.services.historical_provider import (
    Resolution,
    get_historical_candles,
)

US_EASTERN = ZoneInfo("America/New_York")
US_CENTRAL = ZoneInfo("America/Chicago")
US_MOUNTAINS = ZoneInfo("America/Denver")
US_WESTERN = ZoneInfo("America/Los_Angeles")
MARKET_OPEN = time(9, 30, tzinfo=US_EASTERN)
MARKET_CLOSE = time(16, 0, tzinfo=US_EASTERN)

def _intraday_anchor(now_ts: int, resolution: Resolution, minutes: Optional[int]) -> int:
    """
    Returns a 'to_ts' anchor in UTC seconds for intraday ranges.
    - If we are inside a weekday session (9:30–16:00 ET), return now_ts unchanged.
    - If we are before 9:30 ET, after 16:00 ET, or on a weekend, 
      return the last weekday’s 16:00 ET timestamp.
    For non-intraday resolutions or when minutes is None, just return now_ts.
    """
    if minutes is None or resolution not in ("1", "5", "15", "30", "60"):
        return now_ts
    now_utc = datetime.fromtimestamp(now_ts, tz=timezone.utc)
    now_et = now_utc.astimezone(US_EASTERN)
    dow = now_et.weekday()
    current_time = now_et.time()

    # Helper to find the previous weekday (skip weekends)

    def previous_weekday(d: datetime.date) -> datetime.date:
        d = d - timedelta(days=1)
        while d.weekday() > 4:
            d = d - timedelta(days=1)
        return d

    # Case 1: within regular session on a weekday
    if dow < 5 and MARKET_OPEN <= current_time <= MARKET_CLOSE:
        return now_ts
    
    # Determine which day’s close to use
    if dow >= 5: # weekend
        # go to frindays data
        last_day = now_et.date()
        while last_day.weekday() > 4:
            last_day = previous_weekday(last_day)
    elif current_time < MARKET_OPEN:
        # go to previous weekday’s close
        last_day = previous_weekday(now_et.date())
    else: # after today’s close
        last_day = now_et.date()

    anchor_et = datetime.combine(last_day, MARKET_CLOSE, tzinfo=US_EASTERN)
    return int(anchor_et.astimezone(timezone.utc).timestamp())

router = APIRouter(prefix="/candles", tags=["candles"])

@router.get("/history", response_model=List[Candle])
async def candles_history(
    symbol: str = Query(..., description="Symbol name"),
    resolution: Resolution = Query(
        "1",
        description="Intraday resolution (1, 5, 15, 30, 60, D)",

    ),
    minutes: Optional[int] = Query(
        None,
        ge=1,
        le = 60 *24*365,
        description = "Maximum allowed resolution for minute data",
    ),
    from_ts: Optional[int] = Query(
        None,
        ge=0, 
        description="Timestamp in seconds",
    ),
    to_ts: Optional[int] = Query(
        None,
        ge=0,
        description="Timestamp in seconds",
    ),
    provider: str = Query(
        "auto",
        description="Data provider"
    ),
):

    """
    Unified historical candles endpoint.

    You can:
    - Pass `minutes` for "last N minutes" (good for intraday charts).
    - Or pass `from_ts`[/`to_ts`] for explicit ranges (good for 1Y, 5Y, etc).

    The underlying provider is:
      - Finnhub for shorter intraday ranges (<= 1 year)
      - Yahoo Finance (via yfinance) fo
      """
    now = int(datetime.now(tz=timezone.utc).timestamp())

    if from_ts is None and minutes is None:
        minutes = 60*24

    if from_ts is None:
        to_ts_eff = to_ts if to_ts is not None else _intraday_anchor(now, resolution, minutes)
        from_ts_eff = to_ts_eff - minutes * 60
    else:
        from_ts_eff = from_ts
        to_ts_eff = to_ts if to_ts is not None else now

    if from_ts_eff >= to_ts_eff:
        raise HTTPException(status_code=400, detail="from_ts must be < to_ts")

    try:
        candles = await get_historical_candles(
            symbol=symbol,
            resolution=resolution,
            from_ts=from_ts_eff,
            to_ts=to_ts_eff,
            provider=provider,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPStatusError as e:
        status = e.response.status_code
        detail = e.response.text or "Upstream data provider error"
        raise HTTPException(status_code=status, detail=detail)


    if not candles:
        raise HTTPException(status_code=404, detail=f"No candles found for {symbol} in range {from_ts_eff}–{to_ts_eff} with provider={provider}")


    return candles
        