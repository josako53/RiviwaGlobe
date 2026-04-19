# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  events/consumer.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/consumer.py — feedback_service
═══════════════════════════════════════════════════════════════════════════════
CONSUMES:
  riviwa.org.events       → upsert ProjectCache (fb_projects / fb_project_stages)
  riviwa.stakeholder.events → concern.raised → auto-create Suggestion feedback
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from aiokafka import AIOKafkaConsumer
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from core.config import settings
from db.session import AsyncSessionLocal
from events.topics import (
    KafkaTopics,
    OrgProjectEvents,
    OrgProjectStageEvents,
    OrgServiceEvents,
    StakeholderEvents,
    UserEvents,
)
from models.project import ProjectCache, ProjectStageCache, ProjectStatus, StageStatus
from models.feedback import Feedback

log = structlog.get_logger(__name__)
_consumer_task: Optional[asyncio.Task] = None


# ─────────────────────────────────────────────────────────────────────────────
# ProjectCache handlers
# ─────────────────────────────────────────────────────────────────────────────

def _project_fields(payload: dict, status: ProjectStatus, now: datetime) -> dict:
    return {
        "organisation_id":     uuid.UUID(payload["organisation_id"]),
        "branch_id":           uuid.UUID(payload["branch_id"]) if payload.get("branch_id") else None,
        "name":                payload["name"],
        "slug":                payload["slug"],
        "status":              status,
        "category":            payload.get("category"),
        "sector":              payload.get("sector"),
        "description":         payload.get("description"),
        "country_code":        payload.get("country_code"),
        "region":              payload.get("region"),
        "primary_lga":         payload.get("primary_lga"),
        "accepts_grievances":  payload.get("accepts_grievances", True),
        "accepts_suggestions": payload.get("accepts_suggestions", True),
        "accepts_applause":    payload.get("accepts_applause", True),
        "cover_image_url":     payload.get("cover_image_url"),
        "org_logo_url":        payload.get("org_logo_url"),
        "synced_at":           now,
    }


async def _upsert_project(
    payload: dict, new_status: ProjectStatus, db: AsyncSession
) -> None:
    project_id = uuid.UUID(payload["id"])
    result     = await db.execute(select(ProjectCache).where(ProjectCache.id == project_id))
    existing   = result.scalar_one_or_none()
    now        = datetime.now(timezone.utc)
    fields     = _project_fields(payload, new_status, now)

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        db.add(existing)
        log.info("feedback.project.updated", project_id=str(project_id))
    else:
        db.add(ProjectCache(id=project_id, published_at=now, **fields))
        log.info("feedback.project.created", project_id=str(project_id))
    await db.commit()


async def _update_project_status(
    payload: dict, new_status: ProjectStatus, db: AsyncSession
) -> None:
    project_id = uuid.UUID(payload["id"])
    await db.execute(
        update(ProjectCache)
        .where(ProjectCache.id == project_id)
        .values(status=new_status, synced_at=datetime.now(timezone.utc))
    )
    await db.commit()
    log.info("feedback.project.status_changed",
             project_id=str(project_id), status=new_status.value)


# ─────────────────────────────────────────────────────────────────────────────
# ProjectStageCache handlers
# ─────────────────────────────────────────────────────────────────────────────

async def _upsert_stage(
    payload: dict, new_status: StageStatus, db: AsyncSession
) -> None:
    stage_id   = uuid.UUID(payload["stage_id"])
    project_id = uuid.UUID(payload["project_id"])
    result     = await db.execute(
        select(ProjectStageCache).where(ProjectStageCache.id == stage_id)
    )
    existing = result.scalar_one_or_none()
    now      = datetime.now(timezone.utc)
    fields   = {
        "project_id":          project_id,
        "name":                payload["name"],
        "stage_order":         payload["stage_order"],
        "status":              new_status,
        "description":         payload.get("description"),
        "accepts_grievances":  payload.get("accepts_grievances"),   # None = inherit
        "accepts_suggestions": payload.get("accepts_suggestions"),
        "accepts_applause":    payload.get("accepts_applause"),
        "synced_at":           now,
    }

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        db.add(existing)
        log.info("feedback.stage.updated", stage_id=str(stage_id), status=new_status.value)
    else:
        db.add(ProjectStageCache(id=stage_id, **fields))
        log.info("feedback.stage.created", stage_id=str(stage_id))
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# User event handlers
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_user_account_closed(payload: dict, db: AsyncSession) -> None:
    """
    user.suspended / user.banned / user.deactivated

    Nulls submitted_by_user_id on all non-anonymous feedbacks belonging to
    this user so their identity is no longer visible in the grievance log.
    Anonymous feedbacks are left untouched (they already have no identity).

    Note: we do NOT delete or close their feedbacks — the grievance records
    must remain for audit purposes. We only sever the identity link.
    """
    from models.feedback import Feedback
    user_id = uuid.UUID(payload["user_id"])
    result = await db.execute(
        update(Feedback)
        .where(
            Feedback.submitted_by_user_id == user_id,
            Feedback.is_anonymous == False,  # noqa: E712
        )
        .values(submitted_by_user_id=None)
    )
    await db.commit()
    log.info(
        "feedback.user.identity_severed",
        user_id=str(user_id),
        rows_updated=result.rowcount,
    )


async def _handle_user_registered(payload: dict, db: AsyncSession) -> None:
    """
    user.registered / user.registered_social

    No local user table in feedback_service — nothing to upsert.
    Logged for observability so we can trace when a user first appeared.
    """
    log.info(
        "feedback.user.registered",
        user_id=payload.get("user_id"),
        method=payload.get("method", "unknown"),
    )


async def _handle_user_reactivated(payload: dict, db: AsyncSession) -> None:
    """
    user.reactivated

    We cannot automatically restore submitted_by_user_id because it was
    nulled when the account was deactivated — we don't know which feedbacks
    belonged to this user after the null. Log for operator awareness.
    """
    log.info(
        "feedback.user.reactivated_no_restore",
        user_id=payload.get("user_id"),
        note="submitted_by_user_id was nulled on deactivation and cannot be restored automatically",
    )




async def _handle_concern_raised(payload: dict, db: AsyncSession) -> None:
    """
    When stakeholder_service publishes engagement.concern.raised or
    communication.concerns.pending, auto-create a SUGGESTION feedback so
    the GRM Unit can track it without manually entering it.
    """
    from models.feedback import (
        Feedback, FeedbackType, FeedbackStatus, FeedbackPriority,
        FeedbackCategory, FeedbackChannel, GRMLevel,
    )
    from events.producer import get_producer
    from sqlalchemy import func

    project_id = payload.get("project_id")
    if not project_id:
        return
    pid = uuid.UUID(project_id)

    proj_result = await db.execute(
        select(ProjectCache).where(ProjectCache.id == pid)
    )
    if not proj_result.scalar_one_or_none():
        log.warning("feedback.concern.project_not_found", project_id=project_id)
        return

    # Generate unique ref: SGG-YYYY-NNNN scoped to the project
    count = await db.scalar(
        select(func.count(Feedback.id)).where(Feedback.project_id == pid)
    ) or 0
    unique_ref = f"SGG-{datetime.now().year}-{count + 1:04d}"

    f = Feedback(
        unique_ref                  = unique_ref,
        project_id                  = pid,
        feedback_type               = FeedbackType.SUGGESTION,
        category                    = FeedbackCategory.ENGAGEMENT,
        status                      = FeedbackStatus.SUBMITTED,
        priority                    = FeedbackPriority.LOW,
        current_level               = GRMLevel.WARD,
        channel                     = FeedbackChannel.PUBLIC_MEETING,
        is_anonymous                = False,
        submitted_by_stakeholder_id = uuid.UUID(payload["stakeholder_id"]) if payload.get("stakeholder_id") else None,
        submitted_by_contact_id     = uuid.UUID(payload["contact_id"])     if payload.get("contact_id")     else None,
        stakeholder_engagement_id   = uuid.UUID(payload["activity_id"])    if payload.get("activity_id")    else None,
        distribution_id             = uuid.UUID(payload["distribution_id"]) if payload.get("distribution_id") else None,
        subject                     = "Concern raised during consultation",
        description                 = payload.get("concerns") or payload.get("concerns_raised_after") or "Concern raised — see consultation record.",
    )
    db.add(f)
    await db.flush()
    await db.refresh(f)
    await db.commit()

    producer = await get_producer()
    await producer.feedback_submitted(
        f.id, f.project_id,
        f.feedback_type.value,
        f.category.value,
        stakeholder_engagement_id=f.stakeholder_engagement_id,
        distribution_id=f.distribution_id,
    )
    log.info("feedback.auto_created_from_concern",
             feedback_id=str(f.id), unique_ref=unique_ref)


# ─────────────────────────────────────────────────────────────────────────────
# Org logo sync handler
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_org_logo_updated(payload: dict, db: AsyncSession) -> None:
    """
    When an organisation uploads a new logo, update org_logo_url on every
    ProjectCache row that belongs to that organisation.
    Called when org.events carries a logo_url field.
    """
    org_id   = payload.get("org_id")
    logo_url = payload.get("logo_url")
    if not org_id or not logo_url:
        return
    await db.execute(
        update(ProjectCache)
        .where(ProjectCache.organisation_id == uuid.UUID(org_id))
        .values(org_logo_url=logo_url, synced_at=datetime.now(timezone.utc))
    )
    await db.commit()
    log.info("feedback.org_logo.synced", org_id=org_id, logo_url=logo_url)


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────────────

async def _dispatch(event_type: str, payload: dict, db: AsyncSession) -> None:
    try:
        # ── OrgProject lifecycle ──────────────────────────────────────────────
        if event_type == OrgProjectEvents.PUBLISHED:
            await _upsert_project(payload, ProjectStatus.ACTIVE, db)

        elif event_type == OrgProjectEvents.UPDATED:
            await _upsert_project(
                payload,
                ProjectStatus(payload.get("status", "active")),
                db,
            )
        elif event_type == OrgProjectEvents.PAUSED:
            await _update_project_status(payload, ProjectStatus.PAUSED, db)

        elif event_type == OrgProjectEvents.RESUMED:
            await _update_project_status(payload, ProjectStatus.ACTIVE, db)

        elif event_type == OrgProjectEvents.COMPLETED:
            await _update_project_status(payload, ProjectStatus.COMPLETED, db)

        elif event_type == OrgProjectEvents.CANCELLED:
            await _update_project_status(payload, ProjectStatus.CANCELLED, db)

        # ── OrgProjectStage lifecycle ─────────────────────────────────────────
        elif event_type == OrgProjectStageEvents.ACTIVATED:
            await _upsert_stage(payload, StageStatus.ACTIVE, db)

        elif event_type == OrgProjectStageEvents.COMPLETED:
            await _upsert_stage(payload, StageStatus.COMPLETED, db)

        elif event_type == OrgProjectStageEvents.SKIPPED:
            await _upsert_stage(payload, StageStatus.SKIPPED, db)

        # ── User events ───────────────────────────────────────────────────────
        elif event_type in (
            UserEvents.SUSPENDED,
            UserEvents.BANNED,
            UserEvents.DEACTIVATED,
        ):
            await _handle_user_account_closed(payload, db)

        elif event_type in (
            UserEvents.REGISTERED,
            UserEvents.REGISTERED_SOCIAL,
        ):
            await _handle_user_registered(payload, db)

        elif event_type == UserEvents.REACTIVATED:
            await _handle_user_reactivated(payload, db)

        elif event_type == UserEvents.PROFILE_UPDATED:
            # feedback_service does not cache user profile — nothing to sync
            log.debug("feedback.consumer.user_profile_update_ignored",
                      user_id=payload.get("user_id"))

        # ── Org events — sync logo_url to all project caches for this org ──────
        elif event_type == OrgEvents.UPDATED:
            # Only act on this event if it carries a logo_url change.
            # Full org profile changes are not cached in feedback_service.
            if payload.get("logo_url"):
                await _handle_org_logo_updated(payload, db)
            else:
                log.debug("feedback.consumer.org_updated_no_logo", org_id=payload.get("org_id"))

        elif event_type in (
            OrgServiceEvents.PUBLISHED, OrgServiceEvents.UPDATED,
            OrgServiceEvents.SUSPENDED, OrgServiceEvents.CLOSED,
        ):
            log.debug("feedback.consumer.org_service_ignored", event_type=event_type)

        # ── Stakeholder concern events ────────────────────────────────────────
        elif event_type in (
            StakeholderEvents.CONCERN_RAISED,
            StakeholderEvents.COMM_CONCERNS_PENDING,
        ):
            await _handle_concern_raised(payload, db)

        else:
            log.debug("feedback.consumer.unknown_event", event_type=event_type)

    except Exception as exc:
        log.error("feedback.consumer.handler_failed",
                  event_type=event_type, error=str(exc), exc_info=exc)
        await db.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# Consumer loop
# ─────────────────────────────────────────────────────────────────────────────

async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        KafkaTopics.ORG_EVENTS,
        KafkaTopics.USER_EVENTS,
        KafkaTopics.STAKEHOLDER_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="feedback_service_group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    log.info("feedback.consumer.started")
    try:
        async for msg in consumer:
            envelope   = msg.value
            event_type = envelope.get("event_type", "")
            payload    = envelope.get("payload", {})
            async with AsyncSessionLocal() as db:
                await _dispatch(event_type, payload, db)
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        log.error("feedback.consumer.fatal", error=str(exc), exc_info=exc)
    finally:
        await consumer.stop()
        log.info("feedback.consumer.stopped")


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
