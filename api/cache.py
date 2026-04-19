"""Redis cache layer"""
import json
import redis.asyncio as redis
from api.config import REDIS_URL

_redis = None

async def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis

async def cache_get(key: str):
    r = await get_redis()
    val = await r.get(key)
    if val:
        return json.loads(val)
    return None

async def cache_set(key: str, value: dict, ttl: int = 3600):
    r = await get_redis()
    await r.set(key, json.dumps(value, default=str), ex=ttl)

async def rate_limit_check(ip: str, limit: int = 100, window: int = 60) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    r = await get_redis()
    key = f"rl:{ip}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window)
    return count <= limit
