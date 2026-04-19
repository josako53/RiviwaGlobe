# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  stakeholder_service  |  Port: 8070  |  DB: stakeholder_db (5436)
# FILE     :  events/consumer.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/consumer.py — stakeholder_service
═══════════════════════════════════════════════════════════════════════════════
CONSUMES:
  riviwa.org.events
    OrgProject lifecycle   → upsert/update ProjectCache
    OrgProjectStage events → upsert/update ProjectStageCache
    user.deactivated       → null StakeholderContact.user_id

  riviwa.feedback.events
    feedback.submitted     → link feedback_ref_id to engagement + distribution

Payload field conventions (set by auth_service EventPublisher)
──────────────────────────────────────────────────────────────
  OrgProject events   → payload["id"]         = project UUID
  OrgProjectStage     → payload["stage_id"]   = stage UUID
                        payload["project_id"] = project UUID
  OrgService (legacy) → payload["org_service_id"] — IGNORED
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
    AddressEvents,
    KafkaTopics,
    OrgEvents,
    OrgProjectEvents,
    OrgProjectStageEvents,
    OrgServiceEvents,
    UserEvents,
    FeedbackEvents,
)
from models.project import ProjectCache, ProjectStageCache, ProjectStatus, StageStatus
from models.stakeholder import Stakeholder, StakeholderContact
from models.engagement import StakeholderEngagement
from models.communication import CommunicationDistribution

log = structlog.get_logger(__name__)
_consumer_task: Optional[asyncio.Task] = None


# ─────────────────────────────────────────────────────────────────────────────
# ProjectCache handlers
# ─────────────────────────────────────────────────────────────────────────────

def _project_from_payload(payload: dict, now: datetime) -> dict:
    """Extract canonical ProjectCache fields from an OrgProject event payload."""
    return {
        "name":                payload["name"],
        "slug":                payload["slug"],
        "organisation_id":     uuid.UUID(payload["organisation_id"]),
        "branch_id":           uuid.UUID(payload["branch_id"]) if payload.get("branch_id") else None,
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
    fields     = _project_from_payload(payload, now)
    fields["status"] = new_status

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        db.add(existing)
        log.info("stakeholder.project.updated", project_id=str(project_id), status=new_status)
    else:
        project = ProjectCache(id=project_id, published_at=now, **fields)
        db.add(project)
        log.info("stakeholder.project.created", project_id=str(project_id))
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
    log.info("stakeholder.project.status_changed",
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

    fields = {
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
        log.info("stakeholder.stage.updated", stage_id=str(stage_id), status=new_status.value)
    else:
        stage = ProjectStageCache(id=stage_id, **fields)
        db.add(stage)
        log.info("stakeholder.stage.created", stage_id=str(stage_id))
    await db.commit()


async def _update_stage_status(
    payload: dict, new_status: StageStatus, db: AsyncSession
) -> None:
    stage_id = uuid.UUID(payload["stage_id"])
    await db.execute(
        update(ProjectStageCache)
        .where(ProjectStageCache.id == stage_id)
        .values(status=new_status, synced_at=datetime.now(timezone.utc))
    )
    await db.commit()
    log.info("stakeholder.stage.status_changed",
             stage_id=str(stage_id), status=new_status.value)


# ─────────────────────────────────────────────────────────────────────────────
# User / feedback handlers
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_user_deactivated(payload: dict, db: AsyncSession) -> None:
    """user.suspended / user.banned / user.deactivated — sever platform link."""
    user_id = uuid.UUID(payload["user_id"])
    result = await db.execute(
        update(StakeholderContact)
        .where(StakeholderContact.user_id == user_id)
        .values(user_id=None)
    )
    await db.commit()
    log.info("stakeholder.contact.user_unlinked",
             user_id=str(user_id), rows_updated=result.rowcount)


async def _handle_user_registered(payload: dict, db: AsyncSession) -> None:
    """
    user.registered / user.registered_social

    When a new user registers on the platform, check if any StakeholderContact
    already exists with the same email or phone number. If found, link them by
    setting contact.user_id = new user's id.

    This handles the common case where a GRM Unit officer manually registered a Consumer
    as a StakeholderContact before the Consumer created their own platform account.
    """
    user_id = payload.get("user_id")
    email   = payload.get("email")
    phone   = payload.get("phone_number")

    if not user_id or (not email and not phone):
        return

    uid = uuid.UUID(user_id)

    # Match by email first, then phone — email is more reliable
    for field, value in [("email", email), ("phone", phone)]:
        if not value:
            continue
        result = await db.execute(
            select(StakeholderContact).where(
                getattr(StakeholderContact, field) == value,
                StakeholderContact.user_id.is_(None),
            )
        )
        contact = result.scalar_one_or_none()
        if contact:
            contact.user_id = uid
            db.add(contact)
            await db.commit()
            log.info(
                "stakeholder.contact.auto_linked",
                contact_id=str(contact.id),
                user_id=str(uid),
                matched_on=field,
            )
            return  # only link once

    log.debug("stakeholder.contact.no_match_for_new_user",
              user_id=user_id, email=email)


async def _handle_user_profile_updated(payload: dict, db: AsyncSession) -> None:
    """
    user.profile_updated

    If the user is linked to a StakeholderContact, sync the changed fields
    (full_name, email, phone) so the stakeholder register stays accurate.
    Only syncs fields present in changed_fields to avoid overwriting
    manually curated stakeholder data with stale values.
    """
    user_id        = payload.get("user_id")
    changed_fields = payload.get("changed_fields", [])

    if not user_id:
        return

    result = await db.execute(
        select(StakeholderContact).where(
            StakeholderContact.user_id == uuid.UUID(user_id)
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        return

    updated = False
    field_map = {
        "email":        ("email",     payload.get("email")),
        "phone_number": ("phone",     payload.get("phone_number")),
        "full_name":    ("full_name", payload.get("full_name")),
    }
    for auth_field, (contact_field, value) in field_map.items():
        if auth_field in changed_fields and value:
            setattr(contact, contact_field, value)
            updated = True

    if updated:
        db.add(contact)
        await db.commit()
        log.info(
            "stakeholder.contact.profile_synced",
            contact_id=str(contact.id),
            user_id=user_id,
            synced_fields=[f for f in changed_fields if f in field_map],
        )


async def _handle_user_reactivated(payload: dict, db: AsyncSession) -> None:
    """
    user.reactivated

    user_id was nulled on deactivation. We cannot automatically know which
    contact to re-link — log for operator awareness.
    """
    log.info(
        "stakeholder.contact.user_reactivated_no_restore",
        user_id=payload.get("user_id"),
        note="contact.user_id was nulled on deactivation and cannot be restored automatically",
    )


async def _handle_feedback_submitted(payload: dict, db: AsyncSession) -> None:
    feedback_id = uuid.UUID(payload["feedback_id"])
    if engagement_id_str := payload.get("stakeholder_engagement_id"):
        await db.execute(
            update(StakeholderEngagement)
            .where(StakeholderEngagement.id == uuid.UUID(engagement_id_str))
            .values(feedback_submitted=True, feedback_ref_id=feedback_id)
        )
        log.info("stakeholder.engagement.feedback_linked",
                 engagement_id=engagement_id_str, feedback_id=str(feedback_id))
    if dist_id_str := payload.get("distribution_id"):
        await db.execute(
            update(CommunicationDistribution)
            .where(CommunicationDistribution.id == uuid.UUID(dist_id_str))
            .values(feedback_ref_id=feedback_id)
        )
        log.info("stakeholder.distribution.feedback_linked",
                 distribution_id=dist_id_str, feedback_id=str(feedback_id))
    await db.commit()


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
    log.info("stakeholder.org_logo.synced", org_id=org_id, logo_url=logo_url)


async def _handle_address_deleted(payload: dict, db: AsyncSession) -> None:
    """
    address.deleted — published by auth_service when an Address record is removed.

    Nulls Stakeholder.address_id wherever it equals the deleted address UUID.
    Also clears lga and ward since those were denormalised from the deleted record.

    This maintains referential integrity for the cross-service soft link:
      Stakeholder.address_id → auth_service.addresses.id
    """
    address_id_str = payload.get("address_id")
    if not address_id_str:
        return

    address_id = uuid.UUID(address_id_str)
    result = await db.execute(
        update(Stakeholder)
        .where(Stakeholder.address_id == address_id)
        .values(address_id=None, lga=None, ward=None)
    )
    await db.commit()
    log.info(
        "stakeholder.address_link.nulled",
        address_id=address_id_str,
        rows_updated=result.rowcount,
    )


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
            UserEvents.DEACTIVATED,
            UserEvents.SUSPENDED,
            UserEvents.BANNED,
        ):
            await _handle_user_deactivated(payload, db)

        elif event_type in (
            UserEvents.REGISTERED,
            UserEvents.REGISTERED_SOCIAL,
        ):
            await _handle_user_registered(payload, db)

        elif event_type == UserEvents.PROFILE_UPDATED:
            await _handle_user_profile_updated(payload, db)

        elif event_type == UserEvents.REACTIVATED:
            await _handle_user_reactivated(payload, db)

        # ── Org events — sync logo_url to all project caches for this org ──────
        elif event_type == OrgEvents.UPDATED:
            if payload.get("logo_url"):
                await _handle_org_logo_updated(payload, db)
            else:
                log.debug("stakeholder.consumer.org_updated_no_logo",
                          org_id=payload.get("org_id"))

        elif event_type in (
            OrgServiceEvents.PUBLISHED, OrgServiceEvents.UPDATED,
            OrgServiceEvents.SUSPENDED, OrgServiceEvents.CLOSED,
        ):
            log.debug("stakeholder.consumer.org_service_ignored", event_type=event_type)

        # ── Address events ────────────────────────────────────────────────────
        elif event_type == AddressEvents.DELETED:
            await _handle_address_deleted(payload, db)

        elif event_type in (AddressEvents.CREATED, AddressEvents.UPDATED):
            log.debug("stakeholder.consumer.address_event_ignored",
                      event_type=event_type,
                      address_id=payload.get("address_id"))

        # ── Feedback events ───────────────────────────────────────────────────
        elif event_type == FeedbackEvents.SUBMITTED:
            await _handle_feedback_submitted(payload, db)

        else:
            log.debug("stakeholder.consumer.unknown_event", event_type=event_type)

    except Exception as exc:
        log.error("stakeholder.consumer.handler_failed",
                  event_type=event_type, error=str(exc), exc_info=exc)
        await db.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# Consumer loop
# ─────────────────────────────────────────────────────────────────────────────

async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        KafkaTopics.ORG_EVENTS,
        KafkaTopics.USER_EVENTS,
        KafkaTopics.FEEDBACK_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="stakeholder_service_group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    log.info("stakeholder.consumer.started")
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
        log.error("stakeholder.consumer.fatal", error=str(exc), exc_info=exc)
    finally:
        await consumer.stop()
        log.info("stakeholder.consumer.stopped")


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
