from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from aiokafka import AIOKafkaProducer

from core.config import settings
from events.topics import KafkaTopics, WaitingEventTypes

log = structlog.get_logger(__name__)

_producer: Optional["WaitingProducer"] = None
_producer_lock = asyncio.Lock()


class WaitingProducer:
    def __init__(self) -> None:
        self._p: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        self._p = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            compression_type="zstd",
            linger_ms=5,
            request_timeout_ms=15_000,
        )
        await self._p.start()
        log.info("waiting.producer.started")

    async def stop(self) -> None:
        if self._p:
            await self._p.stop()
            self._p = None

    def _envelope(self, event_type: str, payload: dict) -> dict:
        return {
            "event_type":     event_type,
            "event_id":       str(uuid.uuid4()),
            "occurred_at":    datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            "service":        settings.SERVICE_NAME,
            "payload":        payload,
        }

    async def _publish(self, topic: str, event_type: str, payload: dict, key: Optional[str] = None) -> None:
        if not self._p:
            log.warning("waiting.producer.not_started", event_type=event_type)
            return
        try:
            await self._p.send_and_wait(topic, value=self._envelope(event_type, payload), key=key)
            log.debug("waiting.producer.sent", topic=topic, event_type=event_type)
        except Exception as exc:
            log.error("waiting.producer.failed", topic=topic, event_type=event_type, error=str(exc))

    async def ticket_joined(self, ticket_id: uuid.UUID, org_id: uuid.UUID, ticket_number: str,
                            flow_id: uuid.UUID, channel: str, priority: int, service_point_name: str,
                            position: int, phone_number: Optional[str] = None) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.TICKET_JOINED, {
            "ticket_id": str(ticket_id), "org_id": str(org_id), "ticket_number": ticket_number,
            "flow_id": str(flow_id), "channel": channel, "priority": priority,
            "service_point_name": service_point_name, "position": position, "phone_number": phone_number,
        }, key=str(org_id))

    async def ticket_attending(self, ticket_id: uuid.UUID, org_id: uuid.UUID, ticket_number: str,
                                staff_counter_id: uuid.UUID, service_point_id: uuid.UUID,
                                staff_user_id: Optional[uuid.UUID] = None) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.TICKET_ATTENDING, {
            "ticket_id": str(ticket_id), "org_id": str(org_id), "ticket_number": ticket_number,
            "staff_counter_id": str(staff_counter_id), "service_point_id": str(service_point_id),
            "staff_user_id": str(staff_user_id) if staff_user_id else None,
        }, key=str(org_id))

    async def ticket_finished(self, ticket_id: uuid.UUID, org_id: uuid.UUID, ticket_number: str,
                               service_point_id: uuid.UUID, wait_secs: Optional[float],
                               service_secs: Optional[float], is_final: bool) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.TICKET_FINISHED, {
            "ticket_id": str(ticket_id), "org_id": str(org_id), "ticket_number": ticket_number,
            "service_point_id": str(service_point_id), "wait_secs": wait_secs,
            "service_secs": service_secs, "is_final": is_final,
        }, key=str(org_id))

    async def ticket_completed(self, ticket_id: uuid.UUID, org_id: uuid.UUID, ticket_number: str) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.TICKET_COMPLETED, {
            "ticket_id": str(ticket_id), "org_id": str(org_id), "ticket_number": ticket_number,
        }, key=str(org_id))

    async def ticket_cancelled(self, ticket_id: uuid.UUID, org_id: uuid.UUID,
                                ticket_number: str, reason: Optional[str] = None) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.TICKET_CANCELLED, {
            "ticket_id": str(ticket_id), "org_id": str(org_id),
            "ticket_number": ticket_number, "reason": reason,
        }, key=str(org_id))

    async def ticket_stage_advanced(self, ticket_id: uuid.UUID, org_id: uuid.UUID,
                                     ticket_number: str, next_point_name: str,
                                     current_step_order: int) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.TICKET_STAGE_ADVANCED, {
            "ticket_id": str(ticket_id), "org_id": str(org_id),
            "ticket_number": ticket_number, "next_point_name": next_point_name,
            "current_step_order": current_step_order,
        }, key=str(org_id))

    async def ticket_priority_changed(self, ticket_id: uuid.UUID, org_id: uuid.UUID,
                                       ticket_number: str, old_priority: int, new_priority: int,
                                       phone_number: Optional[str] = None,
                                       reason: Optional[str] = None) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.TICKET_PRIORITY_CHANGED, {
            "ticket_id": str(ticket_id), "org_id": str(org_id), "ticket_number": ticket_number,
            "old_priority": old_priority, "new_priority": new_priority,
            "phone_number": phone_number, "reason": reason,
        }, key=str(org_id))

    async def eta_alert_15min(self, ticket_id: uuid.UUID, ticket_number: str, org_id: uuid.UUID,
                               phone_number: Optional[str], service_point_name: str,
                               eta_minutes: float) -> None:
        # Notify to notification_service for SMS
        if phone_number:
            await self._publish(KafkaTopics.NOTIFICATIONS, WaitingEventTypes.ETA_ALERT_15MIN, {
                "notification_type": "waiting.eta_alert",
                "recipient_phone": phone_number,
                "org_id": str(org_id),
                "channels": ["sms"],
                "variables": {
                    "ticket_number": ticket_number,
                    "service_point_name": service_point_name,
                    "eta_minutes": str(int(round(eta_minutes))),
                },
            }, key=str(org_id))
        # Also emit internal observability event
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.ETA_ALERT_15MIN, {
            "ticket_id": str(ticket_id), "org_id": str(org_id), "ticket_number": ticket_number,
            "phone_number": phone_number, "service_point_name": service_point_name,
            "eta_minutes": eta_minutes,
        }, key=str(org_id))

    async def urgency_approved(self, ticket_id: uuid.UUID, request_id: uuid.UUID,
                                org_id: uuid.UUID, urgency_type: str, new_priority: int) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.URGENCY_APPROVED, {
            "ticket_id": str(ticket_id), "request_id": str(request_id),
            "org_id": str(org_id), "urgency_type": urgency_type, "new_priority": new_priority,
        }, key=str(org_id))

    async def urgency_rejected(self, ticket_id: uuid.UUID, request_id: uuid.UUID,
                                org_id: uuid.UUID, reviewer_notes: Optional[str]) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.URGENCY_REJECTED, {
            "ticket_id": str(ticket_id), "request_id": str(request_id),
            "org_id": str(org_id), "reviewer_notes": reviewer_notes,
        }, key=str(org_id))

    async def staff_session_opened(self, session_id: uuid.UUID, org_id: uuid.UUID,
                                    counter_id: uuid.UUID, service_point_id: uuid.UUID,
                                    staff_user_id: Optional[uuid.UUID] = None) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.STAFF_SESSION_OPENED, {
            "session_id": str(session_id), "org_id": str(org_id),
            "counter_id": str(counter_id), "service_point_id": str(service_point_id),
            "staff_user_id": str(staff_user_id) if staff_user_id else None,
        }, key=str(org_id))

    async def staff_session_closed(self, session_id: uuid.UUID, org_id: uuid.UUID,
                                    tickets_served: int, avg_service_seconds: float) -> None:
        await self._publish(KafkaTopics.WAITING_EVENTS, WaitingEventTypes.STAFF_SESSION_CLOSED, {
            "session_id": str(session_id), "org_id": str(org_id),
            "tickets_served": tickets_served, "avg_service_seconds": avg_service_seconds,
        }, key=str(org_id))


async def get_producer() -> WaitingProducer:
    global _producer
    if _producer is not None:
        return _producer
    async with _producer_lock:
        if _producer is None:
            _producer = WaitingProducer()
            await _producer.start()
    return _producer


async def close_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
