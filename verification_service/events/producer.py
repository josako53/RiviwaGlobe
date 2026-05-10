"""events/producer.py — Kafka producer for verification_service."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import structlog
from aiokafka import AIOKafkaProducer

from core.config import settings
from events.topics import VERIFICATION_TOPIC, VerificationEvents

log = structlog.get_logger(__name__)

_producer_instance: Optional["VerificationProducer"] = None
_lock = asyncio.Lock()


def _serialize(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Not serializable: {type(obj)}")


def _envelope(event_type: str, payload: Dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "event_type":     event_type,
            "event_id":       str(uuid4()),
            "occurred_at":    datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            "service":        "verification_service",
            "payload":        payload,
        },
        default=_serialize,
    ).encode()


class VerificationProducer:
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
        log.info("verification.kafka_producer.started")

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            log.info("verification.kafka_producer.stopped")

    def _send_nowait(self, event_type: str, payload: Dict[str, Any], key: str) -> None:
        if not self._producer:
            log.warning("verification.kafka_producer.not_started", event_type=event_type)
            return
        try:
            asyncio.ensure_future(
                self._producer.send(
                    VERIFICATION_TOPIC,
                    value=_envelope(event_type, payload),
                    key=key.encode(),
                )
            )
        except Exception as exc:
            log.error("verification.kafka_producer.send_error", event_type=event_type, error=str(exc))

    def scanned(
        self,
        verification_event_id: UUID,
        short_code: str,
        result: str,
        organisation_id: Optional[UUID],
        product_id: Optional[UUID],
        qr_type: Optional[str],
        scanner_lat: Optional[float],
        scanner_lng: Optional[float],
    ) -> None:
        self._send_nowait(
            VerificationEvents.SCANNED,
            {
                "verification_event_id": str(verification_event_id),
                "short_code":           short_code,
                "result":               result,
                "organisation_id":      str(organisation_id) if organisation_id else None,
                "product_id":           str(product_id) if product_id else None,
                "qr_type":              qr_type,
                "scanner_lat":          scanner_lat,
                "scanner_lng":          scanner_lng,
            },
            key=str(organisation_id) if organisation_id else "unrecognized",
        )

    def fake_reported(
        self,
        report_id: UUID,
        verification_event_id: UUID,
        short_code: str,
        organisation_id: Optional[UUID],
        has_photo: bool,
        gps_lat: Optional[float],
        gps_lng: Optional[float],
    ) -> None:
        self._send_nowait(
            VerificationEvents.FAKE_REPORTED,
            {
                "report_id":              str(report_id),
                "verification_event_id": str(verification_event_id),
                "short_code":            short_code,
                "organisation_id":       str(organisation_id) if organisation_id else None,
                "has_photo":             has_photo,
                "gps_lat":               gps_lat,
                "gps_lng":               gps_lng,
            },
            key=str(organisation_id) if organisation_id else "unknown",
        )


async def get_producer() -> VerificationProducer:
    global _producer_instance
    async with _lock:
        if _producer_instance is None:
            _producer_instance = VerificationProducer()
    return _producer_instance
