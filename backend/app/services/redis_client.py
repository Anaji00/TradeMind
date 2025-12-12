import redis.asyncio as redis
from typing import Optional
from app.config import settings

redis_client = Optional[redis.Redis] = None

async def init_redit_client() -> None:
    global redis_client
    redis_client = redis.Redis(host = "6379", db = 0)
    print ("Redis client initialized")
    try:
        await redis_client.ping()
        print("Connected to Redis server successfully.")
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis server: {e}")

async def close_redis_client() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        print("Redis client connection closed.")


