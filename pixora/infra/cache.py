"""Redis caching + rate limiting + session management.

Falls back to in-memory dict when Redis is not configured.
Set PIXORA_REDIS_URL=redis://localhost:6379/0 to enable.
"""
from __future__ import annotations
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_redis_client = None
_redis_checked = False
_memory_cache: dict[str, tuple[Any, float]] = {}


async def get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client

    from pixora.config.settings import settings
    if not settings.redis_url:
        _redis_checked = True
        return None

    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await _redis_client.ping()
        logger.info("Redis connected: %s", settings.redis_url)
    except Exception as exc:
        logger.info("Redis unavailable: %s — using in-memory cache", exc)
        _redis_client = None
    _redis_checked = True
    return _redis_client


async def cache_get(key: str) -> Any | None:
    r = await get_redis()
    if r:
        try:
            val = await r.get(f"pixora:{key}")
            return json.loads(val) if val else None
        except Exception:
            pass

    entry = _memory_cache.get(key)
    if entry:
        val, expiry = entry
        if expiry == 0 or time.time() < expiry:
            return val
        del _memory_cache[key]
    return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    r = await get_redis()
    if r:
        try:
            await r.setex(f"pixora:{key}", ttl, json.dumps(value, default=str))
            return
        except Exception:
            pass

    expiry = time.time() + ttl if ttl > 0 else 0
    _memory_cache[key] = (value, expiry)

    if len(_memory_cache) > 1000:
        oldest = next(iter(_memory_cache))
        del _memory_cache[oldest]


async def cache_delete(key: str) -> None:
    r = await get_redis()
    if r:
        try:
            await r.delete(f"pixora:{key}")
        except Exception:
            pass
    _memory_cache.pop(key, None)


async def rate_limit_check(key: str, limit: int, window: int = 60) -> tuple[bool, int]:
    r = await get_redis()
    rk = f"pixora:rl:{key}"

    if r:
        try:
            pipe = r.pipeline()
            pipe.incr(rk)
            pipe.expire(rk, window)
            results = await pipe.execute()
            count = results[0]
            return count <= limit, limit - count
        except Exception:
            pass

    now = time.time()
    entry = _memory_cache.get(f"rl:{key}")
    if entry:
        count, window_start = entry
        if now - window_start > window:
            _memory_cache[f"rl:{key}"] = (1, now)
            return True, limit - 1
        count += 1
        _memory_cache[f"rl:{key}"] = (count, window_start)
        return count <= limit, limit - count
    else:
        _memory_cache[f"rl:{key}"] = (1, now)
        return True, limit - 1
