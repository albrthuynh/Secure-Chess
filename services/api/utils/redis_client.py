"""
This file initializes the Redis client to get set up for implementing the rate limiting
"""

from redis.asyncio import Redis
from typing import Optional
import os

# Global client instance
_redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    global _redis_client

    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("redis_url is not found")

        _redis_client = Redis.from_url(
            redis_url, encoding="utf-8", decode_responses=True, max_connections=10
        )

        if _redis_client is None:
            raise ValueError("_redis_client was not initialized properly")

        print(await _redis_client.ping())

    return _redis_client


async def close_redis_connection():
    global _redis_client

    if _redis_client is None:
        raise ValueError("Redis client is not initialized")

    await _redis_client.aclose()
    _redis_client = None
