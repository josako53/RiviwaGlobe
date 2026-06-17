"""events/producer.py — Kafka producer for staff_service."""
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

_producer_instance: Optional["StaffProducer"] = None
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
            "event_type": event_type,
            "event_id": str(uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            "service": settings.SERVICE_NAME,
            "payload": payload,
        },
        default=_serialize,
    ).encode()


class StaffProducer:
    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        p = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            acks="all",
            enable_idempotence=True,
            compression_type="zstd",
            linger_ms=5,
            request_timeout_ms=15_000,
        )
        try:
            await p.start()
            self._producer = p
            log.info("staff.kafka_producer.started")
        except Exception as exc:
            log.warning("staff.kafka_producer.start_failed", error=str(exc))

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            log.info("staff.kafka_producer.stopped")

    def _send_nowait(self, event_type: str, payload: Dict[str, Any], key: str) -> None:
        """Fire-and-forget: schedule send but do not await."""
        if not self._producer:
            log.warning("staff.kafka_producer.not_started", event_type=event_type)
            return
        try:
            asyncio.ensure_future(
                self._producer.send(
                    settings.KAFKA_STAFF_TOPIC,
                    value=_envelope(event_type, payload),
                    key=key.encode(),
                )
            )
        except Exception as exc:
            log.error("staff.kafka_producer.send_error", event_type=event_type, error=str(exc))

    # ── Event methods ─────────────────────────────────────────────────────────

    def profile_created(self, staff_id: UUID, org_id: UUID, staff_code: str, created_by: Optional[str]) -> None:
        self._send_nowait("staff.profile.created", {
            "staff_id": str(staff_id),
            "org_id": str(org_id),
            "staff_code": staff_code,
            "created_by": created_by,
        }, key=str(org_id))

    def profile_updated(self, staff_id: UUID, org_id: UUID) -> None:
        self._send_nowait("staff.profile.updated", {
            "staff_id": str(staff_id),
            "org_id": str(org_id),
        }, key=str(org_id))

    def profile_suspended(self, staff_id: UUID, org_id: UUID, reason: str) -> None:
        self._send_nowait("staff.profile.suspended", {
            "staff_id": str(staff_id),
            "org_id": str(org_id),
            "reason": reason,
        }, key=str(org_id))

    def profile_terminated(self, staff_id: UUID, org_id: UUID, reason: str) -> None:
        self._send_nowait("staff.profile.terminated", {
            "staff_id": str(staff_id),
            "org_id": str(org_id),
            "reason": reason,
        }, key=str(org_id))

    def staff_verified(self, staff_id: UUID, org_id: UUID, verification_event_id: UUID) -> None:
        self._send_nowait("staff.verified", {
            "staff_id": str(staff_id),
            "org_id": str(org_id),
            "verification_event_id": str(verification_event_id),
        }, key=str(org_id))

    def fraud_report_submitted(self, report_id: UUID, org_id: Optional[UUID]) -> None:
        self._send_nowait("staff.fraud_report.submitted", {
            "report_id": str(report_id),
            "org_id": str(org_id) if org_id else None,
        }, key=str(org_id) if org_id else "unknown")


async def get_producer() -> StaffProducer:
    global _producer_instance
    async with _lock:
        if _producer_instance is None:
            _producer_instance = StaffProducer()
    return _producer_instance
