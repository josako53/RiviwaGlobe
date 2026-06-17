"""events/producer.py — Kafka producer for subscription_service."""
from __future__ import annotations

import asyncio, json, uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from aiokafka import AIOKafkaProducer

from core.config import settings

log = structlog.get_logger(__name__)

SUBSCRIPTION_TOPIC = "riviwa.subscription.events"
_producer: Optional[AIOKafkaProducer] = None
_lock = asyncio.Lock()


def _serialize(obj: Any) -> Any:
    if isinstance(obj, (datetime,)):    return obj.isoformat()
    if isinstance(obj, uuid.UUID):      return str(obj)
    from decimal import Decimal
    if isinstance(obj, Decimal):        return str(obj)
    raise TypeError(f"Not serializable: {type(obj)}")


def _envelope(event_type: str, payload: Dict[str, Any]) -> bytes:
    return json.dumps({
        "event_type": event_type, "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0", "service": "subscription_service",
        "payload": payload,
    }, default=_serialize).encode()


async def get_producer() -> Optional[AIOKafkaProducer]:
    global _producer
    async with _lock:
        if _producer is None:
            p = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                acks="all", enable_idempotence=True,
                compression_type="zstd", linger_ms=5,
            )
            try:
                await p.start()
                _producer = p
                log.info("subscription.kafka_producer.started")
            except Exception as exc:
                log.warning("subscription.kafka_producer.start_failed", error=str(exc))
                return None
    return _producer


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


def _fire(event_type: str, payload: Dict[str, Any], key: str) -> None:
    async def _send():
        try:
            p = await get_producer()
            if p is None:
                log.warning("subscription.kafka.unavailable", event_type=event_type)
                return
            await p.send(SUBSCRIPTION_TOPIC, value=_envelope(event_type, payload), key=key.encode())
        except Exception as exc:
            log.error("subscription.kafka.publish_failed", event_type=event_type, error=str(exc))
    asyncio.ensure_future(_send())


def publish_subscribed(org_id: str, plan_slug: str, billing_cycle: str, subscription_id: str) -> None:
    _fire("subscription.subscribed", {"org_id": org_id, "plan": plan_slug,
          "billing_cycle": billing_cycle, "subscription_id": subscription_id}, key=org_id)


def publish_upgraded(org_id: str, from_plan: str, to_plan: str) -> None:
    _fire("subscription.upgraded", {"org_id": org_id, "from_plan": from_plan, "to_plan": to_plan}, key=org_id)


def publish_downgraded(org_id: str, from_plan: str, to_plan: str) -> None:
    _fire("subscription.downgraded", {"org_id": org_id, "from_plan": from_plan, "to_plan": to_plan}, key=org_id)


def publish_cancelled(org_id: str, reason: Optional[str]) -> None:
    _fire("subscription.cancelled", {"org_id": org_id, "reason": reason}, key=org_id)


def publish_payment_succeeded(org_id: str, invoice_number: str, amount_usd: str) -> None:
    _fire("subscription.payment_succeeded", {"org_id": org_id, "invoice_number": invoice_number,
          "amount_usd": amount_usd}, key=org_id)


def publish_payment_failed(org_id: str, invoice_number: str) -> None:
    _fire("subscription.payment_failed", {"org_id": org_id, "invoice_number": invoice_number}, key=org_id)
