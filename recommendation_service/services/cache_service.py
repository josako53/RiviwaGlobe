"""services/cache_service.py — Redis caching layer."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import structlog
from redis.asyncio import Redis

from core.config import settings

log = structlog.get_logger(__name__)

_redis: Optional[Redis] = None


async def init_redis() -> None:
    global _redis
    _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    await _redis.ping()
    log.info("redis.connected", url=settings.REDIS_URL)


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def _cache_key(prefix: str, entity_id: str, params: dict | None = None) -> str:
    key = f"rec:{prefix}:{entity_id}"
    if params:
        param_str = json.dumps(params, sort_keys=True)
        h = hashlib.md5(param_str.encode()).hexdigest()[:8]
        key = f"{key}:{h}"
    return key


async def get_cached(prefix: str, entity_id: str, params: dict | None = None) -> Optional[dict]:
    if not _redis:
        return None
    key = _cache_key(prefix, entity_id, params)
    try:
        raw = await _redis.get(key)
        if raw:
            return json.loads(raw)
    except Exception as exc:
        log.warning("cache.get_failed", key=key, error=str(exc))
    return None


async def set_cached(
    prefix: str,
    entity_id: str,
    data: Any,
    params: dict | None = None,
    ttl: int | None = None,
) -> None:
    if not _redis:
        return
    key = _cache_key(prefix, entity_id, params)
    ttl = ttl or settings.CACHE_TTL_RECOMMENDATIONS
    try:
        await _redis.setex(key, ttl, json.dumps(data, default=str))
    except Exception as exc:
        log.warning("cache.set_failed", key=key, error=str(exc))


async def invalidate(prefix: str, entity_id: str) -> None:
    if not _redis:
        return
    pattern = f"rec:{prefix}:{entity_id}*"
    try:
        keys = []
        async for key in _redis.scan_iter(match=pattern, count=100):
            keys.append(key)
        if keys:
            await _redis.delete(*keys)
            log.debug("cache.invalidated", pattern=pattern, count=len(keys))
    except Exception as exc:
        log.warning("cache.invalidate_failed", pattern=pattern, error=str(exc))


def is_redis_available() -> bool:
    return _redis is not None
