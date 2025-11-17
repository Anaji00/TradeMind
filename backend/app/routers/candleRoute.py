# app/routers/candles.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException

from app.models.candles import Candle

from app.services.historical_provider import (
    Resolution,
    get_historical_candles,
)

router = APIRouter(prefix="/candles", tags=["candles"])

@router.get("/hisotry", response_model=List[Candle])
async def candles_history(
    symbol: str = Query(..., description="Symbol name"),
    resolution: Resolution = Query(
        "1",
        description="Intraday resolution (1, 5, 15, 30, 60, D)",

    ),
    minutes: {int} = Query(
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
        to_ts_eff = to_ts if to_ts is not None else now
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

    if not candles:
        raise HTTPException(status_code=404, detail="No candles found")

    return candles
        