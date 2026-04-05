"""events/producer.py — payment_service"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from aiokafka import AIOKafkaProducer

from core.config import settings
from events.topics import KafkaTopics, PaymentEvents
from models.payment import Payment

log = structlog.get_logger(__name__)

_producer: Optional[AIOKafkaProducer] = None


async def get_producer() -> Optional["PaymentProducer"]:
    return PaymentProducer(await _get_kafka())


async def _get_kafka() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode(),
            key_serializer=lambda k: k.encode() if k else None,
        )
        await _producer.start()
    return _producer


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


class PaymentProducer:
    def __init__(self, kafka: AIOKafkaProducer) -> None:
        self._kafka = kafka

    async def _publish(self, event_type: str, key: str, payload: dict) -> None:
        try:
            envelope = {
                "event_type": event_type,
                "payload":    payload,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
            await self._kafka.send_and_wait(
                KafkaTopics.PAYMENT_EVENTS,
                key=key,
                value=envelope,
            )
            log.info("payment.event.published", event=event_type, key=key)
        except Exception as exc:
            log.error("payment.event.publish_failed", event=event_type, error=str(exc))

    async def payment_initiated(self, payment: Payment, provider: str) -> None:
        await self._publish(
            PaymentEvents.INITIATED,
            key=str(payment.id),
            payload={
                "payment_id":    str(payment.id),
                "provider":      provider,
                "amount":        payment.amount,
                "currency":      payment.currency.value,
                "payment_type":  payment.payment_type.value,
                "payer_user_id": str(payment.payer_user_id) if payment.payer_user_id else None,
                "org_id":        str(payment.org_id)        if payment.org_id        else None,
                "project_id":    str(payment.project_id)    if payment.project_id    else None,
                "reference_id":  str(payment.reference_id)  if payment.reference_id  else None,
                "reference_type": payment.reference_type,
            },
        )

    async def payment_completed(self, payment_id: uuid.UUID, provider: str, amount: float) -> None:
        await self._publish(
            PaymentEvents.COMPLETED,
            key=str(payment_id),
            payload={
                "payment_id": str(payment_id),
                "provider":   provider,
                "amount":     amount,
            },
        )

    async def payment_failed(self, payment_id: uuid.UUID, reason: str) -> None:
        await self._publish(
            PaymentEvents.FAILED,
            key=str(payment_id),
            payload={"payment_id": str(payment_id), "reason": reason},
        )

    async def payment_refunded(self, payment_id: uuid.UUID, amount: float) -> None:
        await self._publish(
            PaymentEvents.REFUNDED,
            key=str(payment_id),
            payload={"payment_id": str(payment_id), "amount": amount},
        )
