"""
events/consumer.py — ai_service Kafka consumer.

CONSUMES:
  riviwa.organisation.events → sync ProjectKnowledgeBase + Qdrant index
  riviwa.stakeholder.events  → sync StakeholderCache (incharge contacts)
  riviwa.feedback.events     → feedback.submitted → auto-classify project + category
"""
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog
from aiokafka import AIOKafkaConsumer

from core.config import settings
from db.session import AsyncSessionLocal
from events.topics import KafkaTopics, OrgProjectEvents, OrgProjectStageEvents, StakeholderEvents, FeedbackEvents
from repositories.conversation_repo import ProjectKBRepository, StakeholderCacheRepository
from services.rag_service import get_rag

log = structlog.get_logger(__name__)
_consumer_task: Optional[asyncio.Task] = None


# ── Project sync helpers ──────────────────────────────────────────────────────

async def _upsert_project(payload: dict, status: str) -> None:
    project_id = uuid.UUID(payload["id"])
    data = {
        "organisation_id":    uuid.UUID(payload["organisation_id"]),
        "name":               payload["name"],
        "slug":               payload.get("slug", ""),
        "description":        payload.get("description"),
        "sector":             payload.get("sector"),
        "category":           payload.get("category"),
        "code":               payload.get("code"),
        "background":         payload.get("background"),
        "objectives":         payload.get("objectives"),
        "expected_outcomes":  payload.get("expected_outcomes"),
        "target_beneficiaries": payload.get("target_beneficiaries"),
        "location_description": payload.get("location_description"),
        "funding_source":     payload.get("funding_source"),
        "branch_id":          uuid.UUID(payload["branch_id"]) if payload.get("branch_id") else None,
        "org_service_id":     uuid.UUID(payload["org_service_id"]) if payload.get("org_service_id") else None,
        "org_display_name":   payload.get("org_display_name"),
        "region":             payload.get("region"),
        "primary_lga":        payload.get("primary_lga"),
        "status":             status,
        "accepts_grievances":  payload.get("accepts_grievances", True),
        "accepts_suggestions": payload.get("accepts_suggestions", True),
        "accepts_applause":    payload.get("accepts_applause", True),
        "synced_at":          datetime.now(timezone.utc),
    }
    async with AsyncSessionLocal() as db:
        repo = ProjectKBRepository(db)
        kb   = await repo.upsert(project_id, data)
        await db.commit()

    # Build rich searchable text for embedding
    parts = [payload["name"]]
    for field in ("code", "sector", "category", "description", "background",
                  "objectives", "expected_outcomes", "target_beneficiaries",
                  "location_description", "funding_source", "region", "primary_lga",
                  "org_display_name"):
        val = payload.get(field, "")
        if val:
            parts.append(str(val)[:300])
    searchable = " ".join(p for p in parts if p).strip()

    # Rich Qdrant payload — everything the AI needs to explain its match
    qdrant_payload = {
        "name":               payload["name"],
        "code":               payload.get("code", ""),
        "sector":             payload.get("sector", ""),
        "category":           payload.get("category", ""),
        "description":        payload.get("description", ""),
        "objectives":         (payload.get("objectives") or "")[:300],
        "location_description": payload.get("location_description", ""),
        "funding_source":     payload.get("funding_source", ""),
        "region":             payload.get("region", ""),
        "primary_lga":        payload.get("primary_lga", ""),
        "org_display_name":   payload.get("org_display_name", ""),
        "organisation_id":    payload["organisation_id"],
        "branch_id":          payload.get("branch_id", ""),
        "status":             status,
    }

    rag = get_rag()
    ok  = rag.index_project(project_id, searchable, qdrant_payload)
    if ok:
        async with AsyncSessionLocal() as db:
            repo = ProjectKBRepository(db)
            await repo.mark_vector_indexed(project_id)
            await db.commit()

    log.info("ai.consumer.project_synced", project_id=str(project_id),
             name=payload["name"], status=status)


async def _update_project_status(payload: dict, status: str) -> None:
    await _upsert_project(payload, status)


async def _upsert_stage(payload: dict) -> None:
    """Update active_stage_name on the project KB record."""
    project_id = uuid.UUID(payload.get("project_id", ""))
    stage_name = payload.get("name", "")
    if not project_id:
        return
    async with AsyncSessionLocal() as db:
        repo = ProjectKBRepository(db)
        kb   = await repo.get_by_project_id(project_id)
        if kb:
            kb.active_stage_name = stage_name
            kb.synced_at         = datetime.now(timezone.utc)
            db.add(kb)
            await db.commit()
    log.info("ai.consumer.stage_synced", project_id=str(project_id), stage=stage_name)


# ── Stakeholder sync helpers ──────────────────────────────────────────────────

async def _upsert_stakeholder(payload: dict) -> None:
    stakeholder_id = uuid.UUID(payload["id"])
    # Determine if this stakeholder is the project incharge
    # (typically identified by role: "piu_officer", "project_coordinator", "incharge", etc.)
    role       = (payload.get("role") or "").lower()
    is_incharge = any(kw in role for kw in ("incharge", "coordinator", "piu", "officer", "director"))
    data = {
        "organisation_id": uuid.UUID(payload["organisation_id"]) if payload.get("organisation_id") else None,
        "project_id":      uuid.UUID(payload["project_id"]) if payload.get("project_id") else None,
        "name":            payload.get("name", ""),
        "phone":           payload.get("phone"),
        "email":           payload.get("email"),
        "role":            payload.get("role"),
        "is_incharge":     is_incharge,
        "lga":             payload.get("lga"),
        "synced_at":       datetime.now(timezone.utc),
    }
    async with AsyncSessionLocal() as db:
        repo = StakeholderCacheRepository(db)
        await repo.upsert(stakeholder_id, data)
        await db.commit()
    log.info("ai.consumer.stakeholder_synced", stakeholder_id=str(stakeholder_id),
             name=payload.get("name"), is_incharge=is_incharge)


# ── Feedback auto-classification ──────────────────────────────────────────────

_INTERNAL_HEADERS = {
    "X-Service-Key": settings.INTERNAL_SERVICE_KEY,
    "X-Service-Name": "ai_service",
}


async def _classify_submitted_feedback(payload: dict) -> None:
    """
    Triggered by feedback.submitted event.
    Fetches full feedback data, then classifies project_id + category_def_id if missing.
    Runs in the background so it doesn't block the consumer loop.
    """
    feedback_id = payload.get("feedback_id")
    if not feedback_id:
        return

    # Check if enrichment is even needed based on event payload
    project_id      = payload.get("project_id")
    # category_def_id is not in the event payload — fetch full record to check
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Use the internal endpoint — no JWT required, only X-Service-Key
            r = await client.get(
                f"{settings.FEEDBACK_SERVICE_URL}/api/v1/feedback/{feedback_id}/for-ai",
                headers=_INTERNAL_HEADERS,
            )
            if r.status_code != 200:
                log.warning("ai.consumer.feedback_fetch_failed",
                            feedback_id=feedback_id, status=r.status_code)
                return
            feedback_data = r.json()
    except Exception as exc:
        log.error("ai.consumer.feedback_fetch_error", feedback_id=feedback_id, error=str(exc))
        return

    # Skip if both fields already set
    if feedback_data.get("project_id") and feedback_data.get("category_def_id"):
        log.debug("ai.consumer.skip_classification", feedback_id=feedback_id,
                  reason="project_id and category_def_id already set")
        return

    from services.classification_service import ClassificationService
    svc = ClassificationService()
    enriched = await svc.classify_and_enrich(feedback_data)
    log.info("ai.consumer.classification_done", feedback_id=feedback_id, enriched=enriched)


# ── Consumer loop ─────────────────────────────────────────────────────────────

async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        KafkaTopics.ORG_EVENTS,
        KafkaTopics.STAKEHOLDER_EVENTS,
        KafkaTopics.FEEDBACK_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="ai_service_group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    log.info("ai.consumer.started")
    try:
        async for msg in consumer:
            try:
                envelope   = msg.value
                event_type = envelope.get("event_type", "")
                payload    = envelope.get("payload", {})

                # ── Organisation events ───────────────────────────────────────
                if event_type == OrgProjectEvents.PUBLISHED:
                    await _upsert_project(payload, "active")
                elif event_type == OrgProjectEvents.UPDATED:
                    await _upsert_project(payload, payload.get("status", "active"))
                elif event_type == OrgProjectEvents.PAUSED:
                    await _update_project_status(payload, "paused")
                elif event_type == OrgProjectEvents.RESUMED:
                    await _update_project_status(payload, "active")
                elif event_type == OrgProjectEvents.COMPLETED:
                    await _update_project_status(payload, "completed")
                elif event_type == OrgProjectEvents.CANCELLED:
                    await _update_project_status(payload, "cancelled")
                elif event_type == OrgProjectStageEvents.ACTIVATED:
                    await _upsert_stage(payload)

                # ── Stakeholder events ────────────────────────────────────────
                elif event_type in (
                    StakeholderEvents.CREATED,
                    StakeholderEvents.UPDATED,
                    StakeholderEvents.ENGAGEMENT_CREATED,
                ):
                    if payload.get("id"):
                        await _upsert_stakeholder(payload)

                # ── Feedback events ───────────────────────────────────────────
                elif event_type == FeedbackEvents.SUBMITTED:
                    # Run classification in a background task so it doesn't
                    # block the consumer loop (Ollama can be slow)
                    asyncio.create_task(_classify_submitted_feedback(payload))

            except Exception as exc:
                log.error("ai.consumer.message_error", error=str(exc), exc_info=exc)

    except asyncio.CancelledError:
        pass
    finally:
        await consumer.stop()
        log.info("ai.consumer.stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
