# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  models/notification.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/notification.py
═══════════════════════════════════════════════════════════════════════════════
All database models for the notification_service.

TABLES
──────────────────────────────────────────────────────────────────────────────
  notification_templates   — Jinja2 templates per type × channel × language
  notifications            — every dispatched (or scheduled) notification
  notification_deliveries  — one row per channel attempt per notification
  notification_preferences — per-user opt-in/out per type × channel
  notification_devices     — push token registry (FCM / APNs)

DESIGN PRINCIPLES
──────────────────────────────────────────────────────────────────────────────
  · The notification_service is IGNORANT of business logic.
    It knows templates, channels, preferences, and delivery state.
    It does NOT know what "feedback acknowledged" means for the business.

  · recipient_user_id is nullable → supports notifications to non-registered
    phone numbers or emails (e.g. OTPs before account creation).

  · idempotency_key prevents duplicate notifications when the same event
    is published multiple times (at-least-once Kafka delivery).

  · scheduled_at enables reminders: the consumer stores the notification
    as PENDING_SCHEDULED and the APScheduler job dispatches it later.

  · Soft deletes are NOT used — notifications are time-series data and
    old records are archived/pruned by a background job, not soft-deleted.
═══════════════════════════════════════════════════════════════════════════════
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text
from sqlmodel import Field, Relationship, SQLModel


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class ChannelEnum(str, Enum):
    IN_APP   = "in_app"
    PUSH     = "push"
    SMS      = "sms"
    WHATSAPP = "whatsapp"
    EMAIL    = "email"


class PriorityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class NotificationStatus(str, Enum):
    """Overall notification lifecycle status."""
    PENDING_SCHEDULED = "pending_scheduled"  # waiting for scheduled_at
    PROCESSING        = "processing"         # being dispatched now
    PARTIALLY_SENT    = "partially_sent"     # some channels sent, some failed
    SENT              = "sent"               # all requested channels sent
    FAILED            = "failed"             # all channels failed
    CANCELLED         = "cancelled"          # cancelled before dispatch


class DeliveryStatusEnum(str, Enum):
    """Per-channel delivery attempt status."""
    PENDING   = "pending"
    SENT      = "sent"
    DELIVERED = "delivered"
    FAILED    = "failed"
    SKIPPED   = "skipped"
    READ      = "read"


class PushPlatform(str, Enum):
    FCM  = "fcm"    # Firebase Cloud Messaging — Android + web
    APNS = "apns"   # Apple Push Notification service — iOS


# ─────────────────────────────────────────────────────────────────────────────
# NotificationTemplate
# ─────────────────────────────────────────────────────────────────────────────

class NotificationTemplate(SQLModel, table=True):
    """
    Jinja2 message templates — one row per (notification_type, channel, language).

    notification_type examples:
      "grm.feedback.acknowledged"
      "project.checklist.item_due_soon"
      "auth.login.otp_requested"

    The template engine renders subject_template and body_template with the
    variables dict from the notification request.  Channel-specific fields:
      · subject_template — used by email only
      · title_template   — used by push (notification title)
      · body_template    — all channels (message body / email HTML)

    is_active = False → template is disabled; delivery is SKIPPED for this
    channel but continues on other channels.
    """
    __tablename__ = "notification_templates"
    __table_args__ = (
        UniqueConstraint(
            "notification_type", "channel", "language",
            name="uq_template_type_channel_lang",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── Identity ──────────────────────────────────────────────────────────────
    notification_type: str = Field(
        max_length=120, nullable=False, index=True,
        description="Dot-notation type key e.g. 'grm.feedback.acknowledged'.",
    )
    channel: ChannelEnum = Field(
        sa_column=Column(SAEnum(ChannelEnum, name="notif_channel", create_type=False), nullable=False, index=True),
    )
    language: str = Field(
        max_length=5, default="en", nullable=False, index=True,
        description="ISO 639-1 language code. 'sw' for Swahili, 'en' for English.",
    )

    # ── Templates (Jinja2 syntax) ─────────────────────────────────────────────
    title_template: Optional[str] = Field(
        default=None, max_length=300, nullable=True,
        description="Push notification title. Supports Jinja2 variables.",
    )
    subject_template: Optional[str] = Field(
        default=None, max_length=300, nullable=True,
        description="Email subject line. Supports Jinja2 variables.",
    )
    body_template: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Message body. Jinja2 template. HTML allowed for email.",
    )

    # ── Config ────────────────────────────────────────────────────────────────
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )

    def __repr__(self) -> str:
        return f"<NotificationTemplate {self.notification_type}:{self.channel}:{self.language}>"


# ─────────────────────────────────────────────────────────────────────────────
# Notification
# ─────────────────────────────────────────────────────────────────────────────

class Notification(SQLModel, table=True):
    """
    One record per notification dispatch request.

    A notification may be delivered across multiple channels (push + SMS).
    Each channel attempt is recorded as a NotificationDelivery row.

    recipient_user_id is nullable — supports:
      · Pre-registration OTPs (user doesn't have an account yet)
      · Bulk announcements to phone numbers from stakeholder lists
      · Any notification to a contact who is not a Riviwa user

    idempotency_key prevents re-processing the same notification twice.
    The consumer checks this key before inserting.  If the key already exists,
    the message is acknowledged but not processed again.

    scheduled_at = null   → dispatch immediately
    scheduled_at = future → APScheduler dispatches at that time (reminder)
    """
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_notification_idempotency"),
        Index("ix_notifications_user_unread",
              "recipient_user_id", "status",
              postgresql_where=text("status != 'SENT'::notif_status")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── Recipient ─────────────────────────────────────────────────────────────
    recipient_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="auth_service User.id. Null for pre-registration or anonymous.",
    )
    recipient_phone:  Optional[str] = Field(default=None, max_length=20,  nullable=True)
    recipient_email:  Optional[str] = Field(default=None, max_length=320, nullable=True)

    # ── Content ───────────────────────────────────────────────────────────────
    notification_type: str = Field(
        max_length=120, nullable=False, index=True,
        description="Template key — must match a NotificationTemplate row.",
    )
    variables: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Template rendering variables supplied by the originating service.",
    )
    language: str = Field(max_length=5, default="en", nullable=False)

    # ── Routing ───────────────────────────────────────────────────────────────
    requested_channels: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description=(
            'JSONB array of channel names requested by originating service. '
            'Format: {"channels": ["push", "sms"]}. '
            'Final channels are determined after preference checking.'
        ),
    )
    priority: PriorityEnum = Field(
        default=PriorityEnum.MEDIUM,
        sa_column=Column(SAEnum(PriorityEnum, name="notif_priority"), nullable=False, index=True),
    )

    # ── Scheduling ────────────────────────────────────────────────────────────
    scheduled_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
        description="Null = dispatch immediately. Future = reminder, dispatched by APScheduler.",
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status: NotificationStatus = Field(
        default=NotificationStatus.PENDING_SCHEDULED,
        sa_column=Column(SAEnum(NotificationStatus, name="notif_status"), nullable=False, index=True),
    )

    # ── Idempotency ───────────────────────────────────────────────────────────
    idempotency_key: Optional[str] = Field(
        default=None, max_length=255, nullable=True, index=True,
        description=(
            "Unique key supplied by originating service to prevent duplicate sends. "
            "Format convention: 'domain:entity_id:event:date' "
            "e.g. 'feedback:uuid:acknowledged:2025-06-15'"
        ),
    )

    # ── Source context ────────────────────────────────────────────────────────
    source_service: Optional[str] = Field(
        default=None, max_length=60, nullable=True,
        description="Which service published this notification request.",
    )
    source_entity_id: Optional[str] = Field(
        default=None, max_length=36, nullable=True,
        description="ID of the entity that triggered this notification.",
    )
    extra_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
        description="Arbitrary extra context from the originating service.",
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    dispatched_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    deliveries: List["NotificationDelivery"] = Relationship(back_populates="notification")

    def get_requested_channels(self) -> list[str]:
        if not self.requested_channels:
            return []
        return self.requested_channels.get("channels", [])

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} → user={self.recipient_user_id} [{self.status}]>"


# ─────────────────────────────────────────────────────────────────────────────
# NotificationDelivery
# ─────────────────────────────────────────────────────────────────────────────

class NotificationDelivery(SQLModel, table=True):
    """
    One row per channel attempt for a Notification.

    Tracks whether the message was actually sent to the provider,
    provider-level delivery confirmation, and failure details.

    retry_count is incremented on each attempt.  Max retries is
    controlled by config (default: 3).

    provider_message_id links to the external provider's message ID
    for delivery status callbacks (e.g. Africa's Talking DLR).

    read_at is populated for in_app channel when the user opens the notification.
    """
    __tablename__ = "notification_deliveries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    notification_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("notifications.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    channel: ChannelEnum = Field(
        sa_column=Column(SAEnum(ChannelEnum, name="notif_channel", create_type=False), nullable=False)
    )

    # ── Rendered content (stored for audit) ──────────────────────────────────
    rendered_title: Optional[str] = Field(default=None, max_length=300, nullable=True)
    rendered_subject: Optional[str] = Field(default=None, max_length=300, nullable=True)
    rendered_body: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    # ── Delivery state ────────────────────────────────────────────────────────
    status: DeliveryStatusEnum = Field(
        default=DeliveryStatusEnum.PENDING,
        sa_column=Column(SAEnum(DeliveryStatusEnum, name="delivery_status"), nullable=False, index=True),
    )
    retry_count: int = Field(default=0, nullable=False)
    next_retry_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    failure_reason: Optional[str] = Field(
        default=None, max_length=500, nullable=True,
    )

    # ── Provider response ─────────────────────────────────────────────────────
    provider_name: Optional[str] = Field(
        default=None, max_length=60, nullable=True,
        description="e.g. 'africas_talking', 'twilio', 'fcm', 'sendgrid', 'meta_cloud'",
    )
    provider_message_id: Optional[str] = Field(
        default=None, max_length=255, nullable=True,
        description="Provider's message ID for delivery receipt correlation.",
    )

    # ── In-app read tracking ──────────────────────────────────────────────────
    read_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Populated when the user opens the in_app notification.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    sent_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    delivered_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    notification: Notification = Relationship(back_populates="deliveries")

    def __repr__(self) -> str:
        return f"<NotificationDelivery {self.channel} [{self.status}] retries={self.retry_count}>"


# ─────────────────────────────────────────────────────────────────────────────
# NotificationPreference
# ─────────────────────────────────────────────────────────────────────────────

class NotificationPreference(SQLModel, table=True):
    """
    Per-user opt-in / opt-out per notification_type × channel.

    CRITICAL priority notifications IGNORE preferences — they are always sent.

    If no preference row exists for a (user_id, notification_type, channel)
    combination, the DEFAULT is to send (opt-in by default).

    To disable a channel: set enabled = False.
    To enable a previously disabled channel: set enabled = True.

    notification_type can also be a domain prefix for bulk control:
      "grm.*"         → all GRM notifications
      "project.*"     → all project notifications
    """
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "notification_type", "channel",
            name="uq_preference_user_type_channel",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    user_id: uuid.UUID = Field(nullable=False, index=True)
    notification_type: str = Field(
        max_length=120, nullable=False,
        description=(
            "Exact notification type OR a wildcard domain prefix ending in .* "
            "e.g. 'grm.feedback.acknowledged' or 'grm.*'"
        ),
    )
    channel: ChannelEnum = Field(
        sa_column=Column(SAEnum(ChannelEnum, name="notif_channel", create_type=False), nullable=False)
    )
    enabled: bool = Field(default=True, nullable=False)
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )

    def __repr__(self) -> str:
        state = "ON" if self.enabled else "OFF"
        return f"<NotificationPreference {self.user_id} {self.notification_type}:{self.channel} {state}>"


# ─────────────────────────────────────────────────────────────────────────────
# NotificationDevice (push token registry)
# ─────────────────────────────────────────────────────────────────────────────

class NotificationDevice(SQLModel, table=True):
    """
    Push token registry — one row per device per user.

    A user can have multiple devices (phone + tablet + web).
    Tokens are rotated by FCM/APNs; the client must update the token
    via PATCH /api/v1/devices/{device_id}/token when it changes.

    Stale tokens (is_active = False or last_active_at > 90 days ago)
    are pruned by a periodic background job.
    """
    __tablename__ = "notification_devices"
    __table_args__ = (
        UniqueConstraint("push_token", name="uq_device_push_token"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    user_id: uuid.UUID = Field(nullable=False, index=True)
    platform: PushPlatform = Field(
        sa_column=Column(SAEnum(PushPlatform, name="push_platform"), nullable=False)
    )
    push_token: str = Field(max_length=512, nullable=False, index=True)
    device_name: Optional[str] = Field(default=None, max_length=100, nullable=True)
    app_version:  Optional[str] = Field(default=None, max_length=30, nullable=True)
    is_active: bool = Field(default=True, nullable=False)
    registered_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    last_active_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    def __repr__(self) -> str:
        return f"<NotificationDevice {self.user_id} {self.platform} active={self.is_active}>"