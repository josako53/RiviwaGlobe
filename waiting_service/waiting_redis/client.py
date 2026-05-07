from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

import structlog
from redis.asyncio import Redis

log = structlog.get_logger(__name__)

_PRIORITY_RANK: dict[str, int] = {"URGENT": 0, "HIGH": 1, "NORMAL": 2}


class WaitingRedis:
    """
    Async Redis wrapper for the waiting queue service.

    Key patterns:
      wq:{service_point_id}   — sorted set: FIFO+priority queue per service point
      eta:{ticket_id}         — string: computed ETA in minutes (TTL 120s)
      eta_alerted:{ticket_id} — string: sentinel, set when 15-min alert was sent
    """

    def __init__(self, redis_url: str) -> None:
        self._url = redis_url
        self._client: Optional[Redis] = None

    async def connect(self) -> None:
        self._client = Redis.from_url(self._url, encoding="utf-8", decode_responses=True)
        await self._client.ping()
        log.info("waiting.redis.connected", url=self._url)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _queue_key(self, service_point_id: UUID) -> str:
        return f"wq:{service_point_id}"

    def _eta_key(self, ticket_id: UUID) -> str:
        return f"eta:{ticket_id}"

    def _alert_key(self, ticket_id: UUID) -> str:
        return f"eta_alerted:{ticket_id}"

    def _score(self, priority: str, created_at: datetime) -> float:
        """
        Priority-aware FIFO score: priority_rank * 1e12 + epoch_microseconds.
        URGENT(0) < HIGH(1) < NORMAL(2), lower score = dequeued first.
        Within the same priority, earlier created_at = lower score = served first.
        """
        rank = _PRIORITY_RANK.get(priority.upper(), 2)
        epoch_us = int(created_at.timestamp() * 1_000_000)
        return float(rank * 1_000_000_000_000 + epoch_us)

    # ── Queue sorted-set helpers ──────────────────────────────────────────────

    async def zadd_ticket(
        self, service_point_id: UUID, ticket_id: UUID, priority: str, created_at: datetime
    ) -> None:
        score = self._score(priority, created_at)
        await self._client.zadd(self._queue_key(service_point_id), {str(ticket_id): score})

    async def zrem_ticket(self, service_point_id: UUID, ticket_id: UUID) -> None:
        await self._client.zrem(self._queue_key(service_point_id), str(ticket_id))

    async def zrank_ticket(self, service_point_id: UUID, ticket_id: UUID) -> Optional[int]:
        return await self._client.zrank(self._queue_key(service_point_id), str(ticket_id))

    async def zcard_queue(self, service_point_id: UUID) -> int:
        return await self._client.zcard(self._queue_key(service_point_id))

    async def get_all_queue_depths(self) -> dict[str, int]:
        depths: dict[str, int] = {}
        async for key in self._client.scan_iter("wq:*"):
            point_id_str = key[len("wq:"):]
            depths[point_id_str] = await self._client.zcard(key)
        return depths

    # ── ETA helpers ───────────────────────────────────────────────────────────

    async def set_eta(self, ticket_id: UUID, eta_minutes: float, ttl_seconds: int = 120) -> None:
        await self._client.setex(self._eta_key(ticket_id), ttl_seconds, str(eta_minutes))

    async def get_eta(self, ticket_id: UUID) -> Optional[float]:
        raw = await self._client.get(self._eta_key(ticket_id))
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    async def del_eta(self, ticket_id: UUID) -> None:
        await self._client.delete(self._eta_key(ticket_id))

    # ── Alert dedup ───────────────────────────────────────────────────────────

    async def mark_alerted(self, ticket_id: UUID, ttl_seconds: int = 600) -> None:
        await self._client.set(self._alert_key(ticket_id), "1", nx=True, ex=ttl_seconds)

    async def is_alerted(self, ticket_id: UUID) -> bool:
        return bool(await self._client.exists(self._alert_key(ticket_id)))

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception as exc:
            log.error("waiting.redis.ping_failed", error=str(exc))
            return False


# ── Singleton ─────────────────────────────────────────────────────────────────

_redis: Optional[WaitingRedis] = None
_redis_lock: asyncio.Lock = asyncio.Lock()


async def init_redis(redis_url: str) -> WaitingRedis:
    global _redis
    async with _redis_lock:
        if _redis is None:
            instance = WaitingRedis(redis_url)
            await instance.connect()
            _redis = instance
    return _redis


async def get_redis_client() -> WaitingRedis:
    if _redis is None:
        raise RuntimeError("WaitingRedis not initialised. Call init_redis() at startup.")
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
