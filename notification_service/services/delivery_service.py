# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  services/delivery_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/delivery_service.py
═══════════════════════════════════════════════════════════════════════════════
Core notification orchestration engine.

Responsibilities:
  1. Accept a notification request dict (from Kafka or HTTP dispatch)
  2. Check idempotency — skip if already processed
  3. Create the Notification DB row
  4. Resolve which channels to use (requested channels ∩ user preferences)
  5. Load push tokens from NotificationDevice table
  6. For each channel: render template → call channel.send() → record delivery
  7. Handle retry state for failed deliveries
  8. Publish delivery events back to Kafka

CHANNEL RESOLUTION RULES
──────────────────────────────────────────────────────────────────────────────
  1. Start with requested_channels from the notification request
  2. If no channels requested, use DEFAULT_CHANNELS_BY_PRIORITY
  3. Remove channels where the user has opted out (NotificationPreference)
  4. CRITICAL priority always bypasses preference checks — always sent
  5. Rate limit check (per user, per notification_type, per hour)
     — CRITICAL bypasses rate limiting
  6. Deliver to remaining channels

DEFAULT CHANNELS BY PRIORITY
──────────────────────────────────────────────────────────────────────────────
  critical → push + sms (both simultaneously)
  high     → push + sms (both simultaneously)
  medium   → push (then in_app as fallback if no push token)
  low      → in_app only
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from channels.base import BaseChannel, ChannelPayload
from channels.email_channel import EmailChannel
from channels.in_app import InAppChannel
from channels.push import PushChannel
from channels.sms import SMSChannel
from channels.whatsapp import WhatsAppChannel
from core.config import settings
from events.topics import (
    NotificationChannel, NotificationPriority, DeliveryStatus,
    NotificationTypes,
)
from models.notification import (
    ChannelEnum, DeliveryStatusEnum, Notification, NotificationDelivery,
    NotificationDevice, NotificationPreference, NotificationStatus, PriorityEnum,
)
from services.template_service import TemplateService

log = structlog.get_logger(__name__)

# ── Channel registry ──────────────────────────────────────────────────────────
_CHANNELS: dict[str, BaseChannel] = {
    NotificationChannel.IN_APP:   InAppChannel(),
    NotificationChannel.PUSH:     PushChannel(),
    NotificationChannel.SMS:      SMSChannel(),
    NotificationChannel.WHATSAPP: WhatsAppChannel(),
    NotificationChannel.EMAIL:    EmailChannel(),
}

# Default channel sets when the caller doesn't specify
_DEFAULT_CHANNELS: dict[str, list[str]] = {
    NotificationPriority.CRITICAL: [NotificationChannel.PUSH, NotificationChannel.SMS],
    NotificationPriority.HIGH:     [NotificationChannel.PUSH, NotificationChannel.SMS],
    NotificationPriority.MEDIUM:   [NotificationChannel.PUSH, NotificationChannel.IN_APP],
    NotificationPriority.LOW:      [NotificationChannel.IN_APP],
}


class DeliveryService:

    def __init__(self, db: AsyncSession) -> None:
        self.db       = db
        self.template = TemplateService(db)

    # ── Main entry point ──────────────────────────────────────────────────────

    async def process_request(self, request: dict) -> Optional[uuid.UUID]:
        """
        Process one notification request.

        request format (published by originating services to riviwa.notifications):
        {
          "notification_type": "grm.feedback.acknowledged",
          "recipient_user_id": "uuid|null",
          "recipient_phone":   "+255...|null",
          "recipient_email":   "...|null",
          "recipient_push_tokens": ["token1", ...],  # optional, override DB lookup
          "language":          "sw|en",
          "variables":         { ... },
          "preferred_channels": ["push", "sms"],
          "priority":          "critical|high|medium|low",
          "idempotency_key":   "...",
          "scheduled_at":      "ISO datetime|null",
          "source_service":    "feedback_service",
          "source_entity_id":  "uuid",
          "metadata":          { ... }
        }

        Returns the notification UUID or None if skipped (idempotency).
        """
        idempotency_key = request.get("idempotency_key")

        # ── Idempotency check ─────────────────────────────────────────────────
        if idempotency_key:
            existing = await self._find_by_idempotency(idempotency_key)
            if existing:
                log.debug("notification.idempotent_skip",
                          idempotency_key=idempotency_key,
                          existing_id=str(existing.id))
                return existing.id

        # ── Build Notification row ────────────────────────────────────────────
        priority_str  = request.get("priority", NotificationPriority.MEDIUM)
        requested_chs = request.get("preferred_channels") or []
        scheduled_at_raw = request.get("scheduled_at")
        if scheduled_at_raw is None:
            scheduled_at = None
        elif isinstance(scheduled_at_raw, datetime):
            scheduled_at = scheduled_at_raw
        else:
            scheduled_at = datetime.fromisoformat(str(scheduled_at_raw))

        notification = Notification(
            recipient_user_id  = uuid.UUID(str(request["recipient_user_id"])) if request.get("recipient_user_id") else None,
            recipient_phone    = request.get("recipient_phone"),
            recipient_email    = request.get("recipient_email"),
            notification_type  = request["notification_type"],
            variables          = request.get("variables") or {},
            language           = request.get("language", "en"),
            requested_channels = {"channels": requested_chs} if requested_chs else None,
            priority           = PriorityEnum(priority_str),
            scheduled_at       = scheduled_at,
            status             = (
                NotificationStatus.PENDING_SCHEDULED
                if scheduled_at else NotificationStatus.PROCESSING
            ),
            idempotency_key   = idempotency_key,
            source_service    = request.get("source_service"),
            source_entity_id  = str(request["source_entity_id"]) if request.get("source_entity_id") else None,
            extra_data        = request.get("metadata"),
        )
        self.db.add(notification)
        await self.db.flush()

        # ── If scheduled for future, save and return — scheduler will dispatch ─
        if scheduled_at and scheduled_at > datetime.now(timezone.utc):
            await self.db.commit()
            log.info("notification.scheduled",
                     id=str(notification.id),
                     scheduled_at=scheduled_at.isoformat(),
                     notification_type=notification.notification_type)
            return notification.id

        # ── Dispatch immediately ──────────────────────────────────────────────
        return await self._dispatch(
            notification=notification,
            priority_str=priority_str,
            requested_chs=requested_chs,
            push_tokens_override=request.get("recipient_push_tokens", []),
        )

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def _dispatch(
        self,
        notification:        Notification,
        priority_str:        str,
        requested_chs:       list[str],
        push_tokens_override: list[str],
    ) -> uuid.UUID:
        """Resolve channels, render templates, send to each channel."""

        # Determine channels to use
        channels = await self._resolve_channels(
            user_id       = notification.recipient_user_id,
            requested_chs = requested_chs,
            priority      = priority_str,
            notif_type    = notification.notification_type,
        )

        # Load push tokens
        push_tokens = push_tokens_override or []
        if NotificationChannel.PUSH in channels and notification.recipient_user_id and not push_tokens:
            push_tokens = await self._load_push_tokens(notification.recipient_user_id)
            if not push_tokens and NotificationChannel.PUSH in channels:
                # Fall back to in_app if no push tokens
                channels = [
                    c if c != NotificationChannel.PUSH else NotificationChannel.IN_APP
                    for c in channels
                ]
                channels = list(dict.fromkeys(channels))  # dedup

        # Variables for rendering
        variables = dict(notification.variables or {})

        all_sent = True
        for ch_name in channels:
            delivery = await self._deliver_to_channel(
                notification  = notification,
                channel_name  = ch_name,
                variables     = variables,
                push_tokens   = push_tokens,
            )
            if delivery.status not in (
                DeliveryStatusEnum.SENT,
                DeliveryStatusEnum.DELIVERED,
                DeliveryStatusEnum.SKIPPED,
            ):
                all_sent = False

        # Update notification status
        if all_sent:
            notification.status = NotificationStatus.SENT
        else:
            notification.status = NotificationStatus.PARTIALLY_SENT

        notification.dispatched_at = datetime.now(timezone.utc)
        self.db.add(notification)
        await self.db.commit()

        log.info("notification.dispatched",
                 id=str(notification.id),
                 notification_type=notification.notification_type,
                 channels=channels,
                 status=notification.status)

        return notification.id

    async def _deliver_to_channel(
        self,
        notification: Notification,
        channel_name: str,
        variables:    dict,
        push_tokens:  list[str],
    ) -> NotificationDelivery:
        """Render template, call channel, record delivery."""

        # Create delivery record
        delivery = NotificationDelivery(
            notification_id = notification.id,
            channel         = ChannelEnum(channel_name),
            status          = DeliveryStatusEnum.PENDING,
        )
        self.db.add(delivery)
        await self.db.flush()

        # ── Render template ───────────────────────────────────────────────────
        rendered = await self.template.render(
            notification_type = notification.notification_type,
            channel           = channel_name,
            language          = notification.language,
            variables         = variables,
        )

        if rendered is None:
            delivery.status         = DeliveryStatusEnum.SKIPPED
            delivery.failure_reason = f"No active template for {notification.notification_type}:{channel_name}:{notification.language}"
            self.db.add(delivery)
            return delivery

        delivery.rendered_title   = rendered.title
        delivery.rendered_subject = rendered.subject
        delivery.rendered_body    = rendered.body

        # ── Build channel payload ─────────────────────────────────────────────
        payload = ChannelPayload(
            recipient_user_id = str(notification.recipient_user_id) if notification.recipient_user_id else None,
            recipient_phone   = notification.recipient_phone,
            recipient_email   = notification.recipient_email,
            push_tokens       = push_tokens,
            rendered_title    = rendered.title,
            rendered_subject  = rendered.subject,
            rendered_body     = rendered.body,
            notification_type = notification.notification_type,
            priority          = notification.priority.value,
            language          = notification.language,
        )

        # ── Call channel ──────────────────────────────────────────────────────
        channel = _CHANNELS.get(channel_name)
        if not channel or not channel.is_configured():
            delivery.status         = DeliveryStatusEnum.SKIPPED
            delivery.failure_reason = f"Channel {channel_name} not configured"
            self.db.add(delivery)
            return delivery

        result = await channel.send(payload)

        # ── Record result ─────────────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        if result.success:
            delivery.status              = DeliveryStatusEnum.SENT
            delivery.sent_at             = now
            delivery.provider_name       = channel_name
            delivery.provider_message_id = result.provider_message_id
        elif not result.should_retry:
            delivery.status         = DeliveryStatusEnum.FAILED
            delivery.failure_reason = result.failure_reason
        else:
            delivery.status         = DeliveryStatusEnum.FAILED
            delivery.failure_reason = result.failure_reason
            delivery.retry_count    = 0
            # next retry after base delay
            from datetime import timedelta
            delivery.next_retry_at  = now + timedelta(seconds=settings.RETRY_BASE_DELAY_SEC)

        self.db.add(delivery)
        return delivery

    # ── Channel resolution ────────────────────────────────────────────────────

    async def _resolve_channels(
        self,
        user_id:       Optional[uuid.UUID],
        requested_chs: list[str],
        priority:      str,
        notif_type:    str,
    ) -> list[str]:
        """
        Determine the final list of channels to use.

        Logic:
          1. Start with requested or defaults
          2. Skip if user has opted out (CRITICAL bypasses this)
        """
        # Step 1: channel candidates
        channels = list(requested_chs) if requested_chs else list(
            _DEFAULT_CHANNELS.get(priority, _DEFAULT_CHANNELS[NotificationPriority.MEDIUM])
        )

        # Step 2: preference filtering (CRITICAL bypasses)
        if priority != NotificationPriority.CRITICAL and user_id:
            channels = await self._apply_preferences(user_id, notif_type, channels)

        return channels

    async def _apply_preferences(
        self,
        user_id:    uuid.UUID,
        notif_type: str,
        channels:   list[str],
    ) -> list[str]:
        """Remove channels the user has disabled."""
        # Query preferences for this user + notification type
        q = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.enabled == False,  # only disabled rows
        )
        rows = list((await self.db.execute(q)).scalars().all())

        disabled_channels: set[str] = set()
        for pref in rows:
            pref_type = pref.notification_type
            # Exact match OR wildcard prefix (e.g. "grm.*" matches "grm.feedback.acknowledged")
            if pref_type == notif_type or (
                pref_type.endswith(".*") and notif_type.startswith(pref_type[:-2])
            ):
                disabled_channels.add(pref.channel.value)

        filtered = [c for c in channels if c not in disabled_channels]
        # Always keep at least in_app if all channels were disabled
        if not filtered:
            filtered = [NotificationChannel.IN_APP]
        return filtered

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _find_by_idempotency(self, key: str) -> Optional[Notification]:
        q = select(Notification).where(Notification.idempotency_key == key)
        return (await self.db.execute(q)).scalar_one_or_none()

    async def _load_push_tokens(self, user_id: uuid.UUID) -> list[str]:
        q = select(NotificationDevice.push_token).where(
            NotificationDevice.user_id   == user_id,
            NotificationDevice.is_active == True,
        )
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows)

    # ── Retry failed deliveries (called by scheduler) ─────────────────────────

    async def retry_failed_deliveries(self) -> int:
        """
        Re-attempt failed deliveries that are past their next_retry_at time
        and have not exceeded max retries.  Called periodically by APScheduler.
        Returns count of retried deliveries.
        """
        from sqlalchemy import and_
        now = datetime.now(timezone.utc)

        q = select(NotificationDelivery).where(
            and_(
                NotificationDelivery.status        == DeliveryStatusEnum.FAILED,
                NotificationDelivery.retry_count   <  settings.MAX_RETRIES,
                NotificationDelivery.next_retry_at <= now,
            )
        )
        deliveries = list((await self.db.execute(q)).scalars().all())
        retried = 0

        for delivery in deliveries:
            # Re-load the parent notification for context
            notification = await self.db.get(Notification, delivery.notification_id)
            if not notification:
                continue

            push_tokens = await self._load_push_tokens(notification.recipient_user_id) \
                if notification.recipient_user_id else []

            delivery.retry_count += 1
            new_delivery = await self._deliver_to_channel(
                notification  = notification,
                channel_name  = delivery.channel.value,
                variables     = dict(notification.variables or {}),
                push_tokens   = push_tokens,
            )
            # If still failing, schedule next retry with backoff
            if new_delivery.status == DeliveryStatusEnum.FAILED and delivery.retry_count < settings.MAX_RETRIES:
                from datetime import timedelta
                delay = settings.RETRY_BASE_DELAY_SEC * (settings.RETRY_BACKOFF_FACTOR ** delivery.retry_count)
                delivery.next_retry_at = now + timedelta(seconds=delay)
            elif new_delivery.status == DeliveryStatusEnum.FAILED:
                # Max retries exhausted
                delivery.status         = DeliveryStatusEnum.FAILED
                delivery.failure_reason = f"Max retries ({settings.MAX_RETRIES}) exhausted. Last: {delivery.failure_reason}"

            self.db.add(delivery)
            retried += 1

        await self.db.commit()
        return retried

    # ── Dispatch scheduled notifications (called by APScheduler) ─────────────

    async def dispatch_scheduled(self) -> int:
        """
        Dispatch notifications whose scheduled_at is in the past.
        Called every minute by APScheduler.
        """
        now = datetime.now(timezone.utc)
        q = select(Notification).where(
            Notification.status       == NotificationStatus.PENDING_SCHEDULED,
            Notification.scheduled_at <= now,
        )
        due = list((await self.db.execute(q)).scalars().all())

        dispatched = 0
        for notif in due:
            requested_chs = notif.get_requested_channels()
            notif.status  = NotificationStatus.PROCESSING
            self.db.add(notif)
            await self._dispatch(
                notification         = notif,
                priority_str         = notif.priority.value,
                requested_chs        = requested_chs,
                push_tokens_override = [],
            )
            dispatched += 1

        log.info("scheduler.scheduled_dispatched", count=dispatched)
        return dispatched
