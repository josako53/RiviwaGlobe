"""
workers/kafka_producer.py
──────────────────────────────────────────────────────────────────
Async Kafka producer singleton.
Publishes domain events (user.registered, fraud.signals, etc.)
for downstream services to consume.

Delivery guarantee
──────────────────────────────────────────────────────────────────
  acks="all" + enable_idempotence=True + retries=5 gives
  at-least-once delivery with duplicate-free retries (exactly-once
  per producer session).  Consumers must still be idempotent on the
  event ID / (topic, partition, offset) tuple.

Production tuning applied
──────────────────────────────────────────────────────────────────
  enable_idempotence=True   — deduplicates retried batches
  compression_type="lz4"   — ~60% bandwidth reduction, low CPU cost
  linger_ms=5               — micro-batch window; reduces round-trips
                              without meaningful latency impact for
                              registration-path events
  request_timeout_ms=15000  — broker must ACK within 15 s or the
                              send raises; prevents silent hangs
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import structlog
from aiokafka import AIOKafkaProducer

from core.config import settings

log = structlog.get_logger(__name__)

_producer: Optional["KafkaEventProducer"] = None
_producer_lock = asyncio.Lock()


class KafkaEventProducer:
    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            # ── Delivery guarantees ──────────────────────────────────────────
            acks="all",                  # all in-sync replicas must ACK
            enable_idempotence=True,     # deduplicates retried batches (required
            retry_backoff_ms=200,
            # ── Performance ──────────────────────────────────────────────────
            compression_type="zstd",      # ~60% bandwidth, low CPU overhead
            linger_ms=5,                 # micro-batch window (ms)
            # ── Reliability ──────────────────────────────────────────────────
            request_timeout_ms=15_000,   # fail loudly instead of hanging
        )
        await self._producer.start()
        log.info("kafka_producer.started", servers=settings.KAFKA_BOOTSTRAP_SERVERS)

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None
            log.info("kafka_producer.stopped")

    async def publish(
        self,
        topic: str,
        value: dict[str, Any],
        key:   Optional[str] = None,
    ) -> None:
        if not self._producer:
            log.warning("kafka_producer.not_started — skipping publish", topic=topic)
            return
        try:
            await self._producer.send_and_wait(topic, value=value, key=key)
            log.debug("kafka_producer.published", topic=topic, key=key)
        except Exception as exc:
            log.error("kafka_producer.publish_failed", topic=topic, error=str(exc))
            raise


async def get_kafka_producer() -> KafkaEventProducer:
    """
    Return the module-level KafkaEventProducer singleton.

    The asyncio.Lock() prevents a race where two coroutines both find
    _producer is None and each create their own instance; without it
    the second producer is started and then orphaned (never stopped),
    leaking a TCP connection to the broker.
    """
    global _producer
    if _producer is not None:
        return _producer
    async with _producer_lock:
        # Re-check inside the lock: another coroutine may have initialised
        # _producer while we were waiting to acquire it.
        if _producer is None:
            _producer = KafkaEventProducer()
            await _producer.start()
    return _producer


async def close_kafka_producer() -> None:
    """
    Gracefully stop the producer.  Call from the FastAPI lifespan shutdown
    handler to flush any buffered messages before the process exits.
    """
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
