"""events/consumer.py — Analytics Kafka consumer for riviwa.verification.events."""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from aiokafka import AIOKafkaConsumer
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.config import settings
from db.session import AnalyticsSessionLocal
from models.verification import VerificationFakeReportLog, VerificationScanLog

log = structlog.get_logger(__name__)

VERIFICATION_TOPIC = "riviwa.verification.events"

_consumer_task: Optional[asyncio.Task] = None
_RETRY_DELAYS = [2, 4, 8, 16, 30, 60]


def _parse_dt(raw: Optional[str]) -> datetime:
    if not raw:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except Exception:
        return datetime.now(timezone.utc).replace(tzinfo=None)


async def _handle_scanned(payload: dict, occurred_at: str) -> None:
    raw_id = payload.get("verification_event_id")
    if not raw_id:
        return

    org_raw = payload.get("organisation_id")
    prod_raw = payload.get("product_id")

    row = {
        "id":          uuid.UUID(raw_id),
        "short_code":  payload.get("short_code", ""),
        "result":      payload.get("result", "UNRECOGNIZED"),
        "org_id":      uuid.UUID(org_raw)  if org_raw  else None,
        "product_id":  uuid.UUID(prod_raw) if prod_raw else None,
        "qr_type":     payload.get("qr_type"),
        "scanner_lat": payload.get("scanner_lat"),
        "scanner_lng": payload.get("scanner_lng"),
        "scanned_at":  _parse_dt(occurred_at),
    }

    stmt = (
        pg_insert(VerificationScanLog)
        .values(**row)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    async with AnalyticsSessionLocal() as db:
        await db.execute(stmt)
        await db.commit()

    log.info("analytics.verification.scanned",
             result=row["result"],
             org_id=str(row["org_id"]) if row["org_id"] else None,
             id=str(row["id"]))


async def _handle_fake_reported(payload: dict, occurred_at: str) -> None:
    raw_id  = payload.get("report_id")
    raw_vid = payload.get("verification_event_id")
    if not raw_id or not raw_vid:
        return

    org_raw = payload.get("organisation_id")

    row = {
        "id":                    uuid.UUID(raw_id),
        "verification_event_id": uuid.UUID(raw_vid),
        "short_code":            payload.get("short_code", ""),
        "org_id":                uuid.UUID(org_raw) if org_raw else None,
        "has_photo":             bool(payload.get("has_photo", False)),
        "gps_lat":               payload.get("gps_lat"),
        "gps_lng":               payload.get("gps_lng"),
        "reported_at":           _parse_dt(occurred_at),
    }

    stmt = (
        pg_insert(VerificationFakeReportLog)
        .values(**row)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    async with AnalyticsSessionLocal() as db:
        await db.execute(stmt)
        await db.commit()

    log.info("analytics.verification.fake_reported",
             org_id=str(row["org_id"]) if row["org_id"] else None,
             id=str(row["id"]))


async def _handle_event(msg: dict) -> None:
    event_type = msg.get("event_type", "")
    payload    = msg.get("payload", {})
    occurred   = msg.get("occurred_at", "")

    if event_type == "verification.scanned":
        await _handle_scanned(payload, occurred)
    elif event_type == "verification.fake_reported":
        await _handle_fake_reported(payload, occurred)


async def _consume_loop() -> None:
    attempt = 0
    while True:
        consumer = AIOKafkaConsumer(
            VERIFICATION_TOPIC,
            bootstrap_servers       = settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id                = settings.KAFKA_VERIFICATION_CONSUMER_GROUP,
            auto_offset_reset       = "earliest",
            enable_auto_commit      = True,
            value_deserializer      = lambda v: json.loads(v.decode("utf-8")),
            retry_backoff_ms        = 1000,
            connections_max_idle_ms = 30_000,
            request_timeout_ms      = 15_000,
        )
        try:
            await consumer.start()
            attempt = 0
            log.info("analytics.verification_consumer.started", topic=VERIFICATION_TOPIC)
            async for msg in consumer:
                try:
                    await _handle_event(msg.value)
                except Exception as exc:
                    log.error("analytics.verification_consumer.handle_error",
                              error=str(exc), exc_info=exc, offset=msg.offset)
        except asyncio.CancelledError:
            log.info("analytics.verification_consumer.cancelled")
            break
        except Exception as exc:
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            log.warning("analytics.verification_consumer.error",
                        error=str(exc), retry_in=delay, attempt=attempt)
            attempt += 1
            await asyncio.sleep(delay)
        finally:
            try:
                await consumer.stop()
            except Exception:
                pass


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop(), name="verification_events_consumer")
    log.info("analytics.verification_consumer.task_created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
    log.info("analytics.verification_consumer.task_stopped")
