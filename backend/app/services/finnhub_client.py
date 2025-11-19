from __future__ import annotations

import time
from typing import List
import httpx
from app.models.candles import Candle
from app.config import settings

BASE_URL = "https://finnhub.io/api/v1"

_client: httpx.AsyncClient | None = None

async def init_client() -> None:
    """
    Initialize a shared AsyncClient for HTTP calls.

    Called once on FastAPI startup.
    """
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=BASE_URL, timeout=10.0)

async def close_client() -> None:
    """
    Close the shared AsyncClient.

    Called once on FastAPI shutdown.
    """
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

async def get_stock_candles(
        symbol: str,
        resolution: str,
        from_ts: int,
        to_ts: int
) -> List[Candle]:
        """
    Call Finnhub's /stock/candle endpoint and return a list of Candle models.

    Docs for this endpoint: /stock/candle?symbol=AAPL&resolution=1&from=...&to=...
    """
        if _client is None:
             raise RuntimeError("Client not initialized")
        
        params = {
             "symbol": symbol.upper(),
             "resolution": resolution,
             "from": from_ts,
             "to": to_ts,
             "token": settings.finnhub_api_key,
        }

        r = await _client.get("/stock/candle", params=params)
        r.raise_for_status()
        data = r.json()

    # Finnhub returns s: "ok" | "no_data" | "error"
        status = data.get("s")
        if status != "ok":
             return []
        
        t_list = data["t"]
        o_list = data["o"]
        h_list = data["h"]
        l_list = data["l"]
        c_list = data["c"]
        v_list = data["v"]

        candles: List[Candle] = []
        for idx, ts in enumerate(t_list):
             candles.append(
                  Candle(
                       t=ts,
                       o=o_list[idx],
                       h=h_list[idx],
                       l=l_list[idx],
                       c=c_list[idx],
                       v=v_list[idx],
                  
                  )
             )
                
        return candles

async def get_recent_candles(
    symbol: str,
    resolution: str = "1",
    lookback_minutes = 120,
) -> List[Candle]:
     now = int(time.time())
     from_ts = now - (lookback_minutes * 60)
     return await get_stock_candles(symbol, resolution, from_ts, now)