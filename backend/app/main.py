from __future__ import annotations

from typing import List
import time

from app.routers.candleRoute import router as candlesRoute
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from app.services.redis_client import redis_client
from app.services.candle_poller import CandlePoller
from fastapi.middleware.cors import CORSMiddleware
from app.models.candles import Candle
from app.services import finnhub_client
from app.services.candle_stream import stream_candles_to_websocket
import logging

logging.basicConfig(level=logging.DEBUG)
app = FastAPI(title="TradeMind API", version="0.1.0")
app.include_router(candlesRoute)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup() -> None:
    await finnhub_client.init_client()
    await redis_client.init_redis_client()
    CandlePoller.start_polling()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await finnhub_client.close_client()
    await redis_client.close_redis_client()
    CandlePoller.stop_polling()

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws/candles/{symbol}")
async def candles_ws(
    websocket: WebSocket,
    symbol: str,
    resolution: str = Query("1"), 
) -> None:
    
    await websocket.accept()
    try:
        await stream_candles_to_websocket(
            websocket=websocket,
            symbol=symbol,
            resolution=resolution,
        )
    except WebSocketDisconnect:
        print (f"Websocket disconnected for {symbol}")
    except Exception as e:
        print (f"Websocket error for {symbol}: {e}")
        await websocket.close(code=1011)  # 1011: Internal Error