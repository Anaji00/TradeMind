from __future__ import annotations

import json
import asyncio

from fastapi import WebSocket
from app.services.redis_client import redis_client
from app.services.candle_poller import CandlePoller


async def stream_candles_to_websocket(
        websocket: WebSocket,
        symbol: str,
        resolution: str = "1",
    ) -> None:
    """
    Connects the client WebSocket to the Redis Pub/Sub channel
    for live candle updates for the given symbol and resolution.
    """
    symbol = symbol.upper()

    # Register symbol for polling
    CandlePoller.subscribe(symbol)

    if redis_client is None:
        await websocket.send_json({"error": "Data Stream Unavailable, check Redis config."})
        await websocket.close(code=1011)
        return
    
    pubsub = None
    try:
        # 2. Open a dedicated PubSub connection and subscribe to the channel
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(CandlePoller.REDIS_CHANNEL)

        # 3. Listen for messages and forward relevant ones to the WebSocket
        while websocket.client_state.name == "CONNECTED":
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)

            if message and message.get('data'):
                try:
                    data = json.loads(message['data'].decode('utf-8'))

                    if data.get("symbol") == symbol:
                        await websocket.send_json(data)
                except Exception as e:
                    print(f"Error processing PubSub message for {symbol}: {e}")

    except asyncio.CancelledError:
        pass  # Normal on disconnect
    except Exception as e:
        print(f"Error in stream_candles_to_websocket for {symbol}: {e}")
        await websocket.close(code=1011)
    finally:
        # Cleanup
        if pubsub:
            await pubsub.unsubscribe(CandlePoller.REDIS_CHANNEL)
            await pubsub.close()

        CandlePoller.unsubscribe(symbol)

        