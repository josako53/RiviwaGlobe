from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import structlog
from aiokafka import AIOKafkaProducer

from core.config import settings

log = structlog.get_logger(__name__)

_producer_instance: Optional["ProductProducer"] = None
_lock = asyncio.Lock()


def _serialize(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Not serializable: {type(obj)}")


def _envelope(event_type: str, payload: Dict[str, Any]) -> bytes:
    return json.dumps({
        "event_type": event_type,
        "event_id": str(uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",
        "service": settings.SERVICE_NAME,
        "payload": payload,
    }, default=_serialize).encode()


class ProductProducer:
    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            acks="all",
            enable_idempotence=True,
            compression_type="zstd",
            linger_ms=5,
            request_timeout_ms=15_000,
        )
        await self._producer.start()
        log.info("product.kafka_producer.started")

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            log.info("product.kafka_producer.stopped")

    async def _send(self, event_type: str, payload: Dict[str, Any], key: str) -> None:
        if not self._producer:
            log.warning("product.kafka_producer.not_started", event_type=event_type)
            return
        try:
            await self._producer.send(
                settings.KAFKA_PRODUCT_TOPIC,
                value=_envelope(event_type, payload),
                key=key.encode(),
            )
        except Exception as exc:
            log.error("product.kafka_producer.send_error", event_type=event_type, error=str(exc))

    async def product_created(self, product: Any, org_id: UUID, created_by: str) -> None:
        await self._send("product.created", {
            "product_id": str(product.product_id),
            "rsin": product.rsin,
            "organisation_id": str(org_id),
            "product_type": product.product_type,
            "title": product.title,
            "brand": product.brand,
            "price": float(product.price),
            "currency": product.currency,
            "listing_status": product.listing_status,
            "created_by": created_by,
        }, key=str(org_id))

    async def product_updated(self, product: Any, org_id: UUID) -> None:
        await self._send("product.updated", {
            "product_id": str(product.product_id),
            "rsin": product.rsin,
            "organisation_id": str(org_id),
            "listing_status": product.listing_status,
            "updated_at": product.updated_at,
        }, key=str(org_id))

    async def product_published(self, product: Any, org_id: UUID) -> None:
        await self._send("product.published", {
            "product_id": str(product.product_id),
            "rsin": product.rsin,
            "organisation_id": str(org_id),
            "product_type": product.product_type,
            "title": product.title,
            "brand": product.brand,
            "price": float(product.price),
            "currency": product.currency,
            "published_at": product.published_at,
        }, key=str(org_id))

    async def product_deactivated(self, product: Any, org_id: UUID) -> None:
        await self._send("product.deactivated", {
            "product_id": str(product.product_id),
            "rsin": product.rsin,
            "organisation_id": str(org_id),
        }, key=str(org_id))


async def get_producer() -> ProductProducer:
    global _producer_instance
    async with _lock:
        if _producer_instance is None:
            _producer_instance = ProductProducer()
    return _producer_instance
