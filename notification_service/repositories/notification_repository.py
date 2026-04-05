# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  repositories/notification_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""
repositories/notification_repository.py
────────────────────────────────────────────────────────────────────────────
All DB read/write operations for the notification_service.

Covers:
  · Notification inbox queries (unread count, paginated list)
  · Mark-as-read for in_app deliveries
  · Preference CRUD
  · Device (push token) registration and management
  · Template CRUD (admin)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.notification import (
    ChannelEnum,
    DeliveryStatusEnum,
    Notification,
    NotificationDelivery,
    NotificationDevice,
    NotificationPreference,
    NotificationStatus,
    NotificationTemplate,
    PushPlatform,
)


class NotificationRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Inbox ─────────────────────────────────────────────────────────────────

    async def list_inbox(
        self,
        user_id:      uuid.UUID,
        unread_only:  bool = False,
        skip:         int  = 0,
        limit:        int  = 30,
    ) -> list[Notification]:
        """
        Return the user's notification inbox (in_app channel deliveries).
        Ordered by created_at descending.
        """
        q = (
            select(Notification)
            .join(
                NotificationDelivery,
                and_(
                    NotificationDelivery.notification_id == Notification.id,
                    NotificationDelivery.channel == ChannelEnum.IN_APP,
                )
            )
            .where(
                Notification.recipient_user_id == user_id,
                NotificationDelivery.status.in_([
                    DeliveryStatusEnum.SENT,
                    DeliveryStatusEnum.DELIVERED,
                    DeliveryStatusEnum.READ,
                ]),
            )
            .options(selectinload(Notification.deliveries))
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if unread_only:
            q = q.where(NotificationDelivery.read_at.is_(None))

        result = await self.db.execute(q)
        return list(result.scalars().unique().all())

    async def unread_count(self, user_id: uuid.UUID) -> int:
        """Count of in_app notifications the user hasn't read yet."""
        q = (
            select(func.count(NotificationDelivery.id))
            .join(Notification, Notification.id == NotificationDelivery.notification_id)
            .where(
                Notification.recipient_user_id == user_id,
                NotificationDelivery.channel   == ChannelEnum.IN_APP,
                NotificationDelivery.status.in_([
                    DeliveryStatusEnum.SENT,
                    DeliveryStatusEnum.DELIVERED,
                ]),
                NotificationDelivery.read_at.is_(None),
            )
        )
        return await self.db.scalar(q) or 0

    async def mark_delivery_read(
        self,
        delivery_id: uuid.UUID,
        user_id:     uuid.UUID,
    ) -> Optional[NotificationDelivery]:
        """
        Mark one in_app delivery as read.
        Verifies the delivery belongs to the user before updating.
        """
        q = (
            select(NotificationDelivery)
            .join(Notification, Notification.id == NotificationDelivery.notification_id)
            .where(
                NotificationDelivery.id      == delivery_id,
                NotificationDelivery.channel == ChannelEnum.IN_APP,
                Notification.recipient_user_id == user_id,
            )
        )
        delivery = (await self.db.execute(q)).scalar_one_or_none()
        if not delivery:
            return None
        delivery.read_at = datetime.now(timezone.utc)
        delivery.status  = DeliveryStatusEnum.READ
        self.db.add(delivery)
        return delivery

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """
        Mark ALL unread in_app notifications for a user as read.
        Returns the count of updated rows.
        """
        now = datetime.now(timezone.utc)
        # Fetch delivery IDs belonging to this user
        q = (
            select(NotificationDelivery.id)
            .join(Notification, Notification.id == NotificationDelivery.notification_id)
            .where(
                Notification.recipient_user_id == user_id,
                NotificationDelivery.channel   == ChannelEnum.IN_APP,
                NotificationDelivery.read_at.is_(None),
                NotificationDelivery.status.in_([
                    DeliveryStatusEnum.SENT,
                    DeliveryStatusEnum.DELIVERED,
                ]),
            )
        )
        ids = list((await self.db.execute(q)).scalars().all())
        if not ids:
            return 0

        await self.db.execute(
            update(NotificationDelivery)
            .where(NotificationDelivery.id.in_(ids))
            .values(read_at=now, status=DeliveryStatusEnum.READ)
        )
        return len(ids)

    # ── Preferences ───────────────────────────────────────────────────────────

    async def get_preferences(self, user_id: uuid.UUID) -> list[NotificationPreference]:
        q = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        ).order_by(
            NotificationPreference.notification_type,
            NotificationPreference.channel,
        )
        return list((await self.db.execute(q)).scalars().all())

    async def upsert_preference(
        self,
        user_id:           uuid.UUID,
        notification_type: str,
        channel:           str,
        enabled:           bool,
    ) -> NotificationPreference:
        """
        Create or update a preference row.
        If enabled=True and a row exists, it is updated.
        If enabled=False, the row is created/updated (opt-out record).
        """
        q = select(NotificationPreference).where(
            NotificationPreference.user_id           == user_id,
            NotificationPreference.notification_type == notification_type,
            NotificationPreference.channel           == ChannelEnum(channel),
        )
        pref = (await self.db.execute(q)).scalar_one_or_none()
        if pref:
            pref.enabled = enabled
        else:
            pref = NotificationPreference(
                user_id           = user_id,
                notification_type = notification_type,
                channel           = ChannelEnum(channel),
                enabled           = enabled,
            )
        self.db.add(pref)
        return pref

    async def delete_preference(
        self,
        user_id:           uuid.UUID,
        notification_type: str,
        channel:           str,
    ) -> bool:
        q = select(NotificationPreference).where(
            NotificationPreference.user_id           == user_id,
            NotificationPreference.notification_type == notification_type,
            NotificationPreference.channel           == ChannelEnum(channel),
        )
        pref = (await self.db.execute(q)).scalar_one_or_none()
        if not pref:
            return False
        await self.db.delete(pref)
        return True

    # ── Devices (push tokens) ─────────────────────────────────────────────────

    async def get_devices(self, user_id: uuid.UUID) -> list[NotificationDevice]:
        q = select(NotificationDevice).where(
            NotificationDevice.user_id   == user_id,
            NotificationDevice.is_active == True,
        )
        return list((await self.db.execute(q)).scalars().all())

    async def register_device(
        self,
        user_id:     uuid.UUID,
        platform:    str,
        push_token:  str,
        device_name: Optional[str] = None,
        app_version: Optional[str] = None,
    ) -> NotificationDevice:
        """
        Register a push token. If the token already exists for this user,
        update last_active_at and ensure is_active=True.
        If the token exists for a DIFFERENT user (device transferred),
        deactivate the old record and create a new one.
        """
        # Check if token already exists
        existing_q = select(NotificationDevice).where(
            NotificationDevice.push_token == push_token
        )
        existing = (await self.db.execute(existing_q)).scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing:
            if existing.user_id == user_id:
                # Same user — refresh
                existing.is_active      = True
                existing.last_active_at = now
                existing.platform       = PushPlatform(platform)
                if device_name:
                    existing.device_name = device_name
                if app_version:
                    existing.app_version = app_version
                self.db.add(existing)
                return existing
            else:
                # Different user (device transfer) — deactivate old
                existing.is_active = False
                self.db.add(existing)

        device = NotificationDevice(
            user_id       = user_id,
            platform      = PushPlatform(platform),
            push_token    = push_token,
            device_name   = device_name,
            app_version   = app_version,
            is_active     = True,
            last_active_at = now,
        )
        self.db.add(device)
        return device

    async def deregister_device(self, device_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        q = select(NotificationDevice).where(
            NotificationDevice.id      == device_id,
            NotificationDevice.user_id == user_id,
        )
        device = (await self.db.execute(q)).scalar_one_or_none()
        if not device:
            return False
        device.is_active = False
        self.db.add(device)
        return True

    async def update_device_token(
        self,
        device_id:   uuid.UUID,
        user_id:     uuid.UUID,
        new_token:   str,
        app_version: Optional[str] = None,
    ) -> Optional[NotificationDevice]:
        """
        FCM/APNs tokens rotate periodically. Client must call this
        when the platform issues a new token.
        """
        q = select(NotificationDevice).where(
            NotificationDevice.id      == device_id,
            NotificationDevice.user_id == user_id,
        )
        device = (await self.db.execute(q)).scalar_one_or_none()
        if not device:
            return None
        device.push_token     = new_token
        device.last_active_at = datetime.now(timezone.utc)
        if app_version:
            device.app_version = app_version
        self.db.add(device)
        return device

    # ── Templates (admin) ─────────────────────────────────────────────────────

    async def list_templates(
        self,
        notification_type: Optional[str] = None,
        channel:           Optional[str] = None,
        language:          Optional[str] = None,
    ) -> list[NotificationTemplate]:
        q = select(NotificationTemplate)
        if notification_type:
            q = q.where(NotificationTemplate.notification_type == notification_type)
        if channel:
            q = q.where(NotificationTemplate.channel == ChannelEnum(channel))
        if language:
            q = q.where(NotificationTemplate.language == language)
        q = q.order_by(
            NotificationTemplate.notification_type,
            NotificationTemplate.channel,
            NotificationTemplate.language,
        )
        return list((await self.db.execute(q)).scalars().all())

    async def get_template(self, template_id: uuid.UUID) -> Optional[NotificationTemplate]:
        return await self.db.get(NotificationTemplate, template_id)

    async def upsert_template(self, data: dict) -> NotificationTemplate:
        """Create or replace a template. Match on (notification_type, channel, language)."""
        q = select(NotificationTemplate).where(
            NotificationTemplate.notification_type == data["notification_type"],
            NotificationTemplate.channel           == ChannelEnum(data["channel"]),
            NotificationTemplate.language          == data["language"],
        )
        tmpl = (await self.db.execute(q)).scalar_one_or_none()
        if tmpl:
            for k in ("title_template", "subject_template", "body_template", "is_active"):
                if k in data:
                    setattr(tmpl, k, data[k])
        else:
            tmpl = NotificationTemplate(**data)
            if "channel" in data:
                tmpl.channel = ChannelEnum(data["channel"])
        self.db.add(tmpl)
        return tmpl

    async def delete_template(self, template_id: uuid.UUID) -> bool:
        tmpl = await self.db.get(NotificationTemplate, template_id)
        if not tmpl:
            return False
        await self.db.delete(tmpl)
        return True

    # ── Delivery DLR update (provider webhook callback) ───────────────────────

    async def update_delivery_status(
        self,
        provider_message_id: str,
        new_status:          str,
        delivered_at:        Optional[datetime] = None,
        failure_reason:      Optional[str]      = None,
    ) -> Optional[NotificationDelivery]:
        """
        Called by webhook handlers when a DLR (delivery receipt) arrives
        from Africa's Talking, Twilio, SendGrid, or FCM.
        """
        q = select(NotificationDelivery).where(
            NotificationDelivery.provider_message_id == provider_message_id
        )
        delivery = (await self.db.execute(q)).scalar_one_or_none()
        if not delivery:
            return None
        delivery.status = DeliveryStatusEnum(new_status)
        if delivered_at:
            delivery.delivered_at = delivered_at
        if failure_reason:
            delivery.failure_reason = failure_reason
        self.db.add(delivery)
        return delivery
