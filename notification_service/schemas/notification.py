# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  schemas/notification.py
# ───────────────────────────────────────────────────────────────────────────
"""schemas/notification.py — Pydantic request/response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Dispatch (internal HTTP endpoint, same payload as Kafka) ─────────────────

class NotificationDispatchRequest(BaseModel):
    """
    Body for POST /api/v1/internal/dispatch
    (called by other services directly via HTTP as an alternative to Kafka).

    The format is identical to the Kafka envelope so services can switch
    between Kafka and HTTP dispatch without changing their code.
    """
    notification_type:     str
    recipient_user_id:     Optional[uuid.UUID] = None
    recipient_phone:       Optional[str]       = None
    recipient_email:       Optional[str]       = None
    recipient_push_tokens: List[str]           = Field(default_factory=list)
    language:              str                 = "en"
    variables:             Dict[str, Any]      = Field(default_factory=dict)
    preferred_channels:    List[str]           = Field(default_factory=list)
    priority:              str                 = "medium"
    idempotency_key:       Optional[str]       = None
    scheduled_at:          Optional[datetime]  = None
    source_service:        Optional[str]       = None
    source_entity_id:      Optional[str]       = None
    metadata:              Dict[str, Any]      = Field(default_factory=dict)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        valid = {"critical", "high", "medium", "low"}
        if v not in valid:
            raise ValueError(f"priority must be one of {sorted(valid)}")
        return v

    @field_validator("preferred_channels")
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        valid = {"in_app", "push", "sms", "whatsapp", "email"}
        for ch in v:
            if ch not in valid:
                raise ValueError(f"Invalid channel '{ch}'. Must be one of {sorted(valid)}")
        return v


class NotificationDispatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    notification_id: uuid.UUID
    status:          str


# ── In-app notification list (mobile / web polling) ──────────────────────────

class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    id:                   uuid.UUID
    channel:              str
    status:               str
    rendered_title:       Optional[str]
    rendered_body:        Optional[str]
    read_at:              Optional[datetime]
    sent_at:              Optional[datetime]
    provider_message_id:  Optional[str]

    @classmethod
    def from_orm(cls, d) -> "DeliveryResponse":
        return cls(
            id=d.id, channel=d.channel.value, status=d.status.value,
            rendered_title=d.rendered_title, rendered_body=d.rendered_body,
            read_at=d.read_at, sent_at=d.sent_at,
            provider_message_id=d.provider_message_id,
        )


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    id:                uuid.UUID
    notification_type: str
    priority:          str
    status:            str
    language:          str
    scheduled_at:      Optional[datetime]
    created_at:        datetime
    dispatched_at:     Optional[datetime]
    deliveries:        List[DeliveryResponse] = []

    @classmethod
    def from_orm(cls, n) -> "NotificationResponse":
        return cls(
            id=n.id, notification_type=n.notification_type,
            priority=n.priority.value, status=n.status.value,
            language=n.language, scheduled_at=n.scheduled_at,
            created_at=n.created_at, dispatched_at=n.dispatched_at,
            deliveries=[DeliveryResponse.from_orm(d) for d in (n.deliveries or [])],
        )


class NotificationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    total:    int
    unread:   int
    returned: int
    items:    List[NotificationResponse] = []


# ── Preferences ───────────────────────────────────────────────────────────────

class SetPreferenceRequest(BaseModel):
    """
    Upsert a single notification preference.
    Call once per (notification_type, channel) pair.
    """
    notification_type: str = Field(
        description="Exact type or wildcard prefix ending in .* e.g. 'grm.*'"
    )
    channel:  str  = Field(description="in_app | push | sms | whatsapp | email")
    enabled:  bool

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        valid = {"in_app", "push", "sms", "whatsapp", "email"}
        if v not in valid:
            raise ValueError(f"channel must be one of {sorted(valid)}")
        return v


class BulkSetPreferencesRequest(BaseModel):
    preferences: List[SetPreferenceRequest]


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    id:                uuid.UUID
    user_id:           uuid.UUID
    notification_type: str
    channel:           str
    enabled:           bool
    updated_at:        datetime

    @classmethod
    def from_orm(cls, p) -> "PreferenceResponse":
        return cls(
            id=p.id, user_id=p.user_id, notification_type=p.notification_type,
            channel=p.channel.value, enabled=p.enabled, updated_at=p.updated_at,
        )


class PreferenceListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    user_id:     uuid.UUID
    preferences: List[PreferenceResponse] = []


# ── Device (push token) registration ─────────────────────────────────────────

class RegisterDeviceRequest(BaseModel):
    platform:    str = Field(description="fcm | apns")
    push_token:  str = Field(max_length=512)
    device_name: Optional[str] = None
    app_version: Optional[str] = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in ("fcm", "apns"):
            raise ValueError("platform must be 'fcm' or 'apns'")
        return v


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    id:          uuid.UUID
    platform:    str
    device_name: Optional[str]
    is_active:   bool
    registered_at: datetime

    @classmethod
    def from_orm(cls, d) -> "DeviceResponse":
        return cls(
            id=d.id, platform=d.platform.value,
            device_name=d.device_name, is_active=d.is_active,
            registered_at=d.registered_at,
        )


# ── Templates (admin management) ─────────────────────────────────────────────

class CreateTemplateRequest(BaseModel):
    notification_type: str = Field(max_length=120)
    channel:           str = Field(description="in_app | push | sms | whatsapp | email")
    language:          str = Field(max_length=5, default="en")
    title_template:    Optional[str] = Field(default=None, max_length=300)
    subject_template:  Optional[str] = Field(default=None, max_length=300)
    body_template:     str
    is_active:         bool = True


class UpdateTemplateRequest(BaseModel):
    title_template:   Optional[str] = Field(default=None, max_length=300)
    subject_template: Optional[str] = Field(default=None, max_length=300)
    body_template:    Optional[str] = None
    is_active:        Optional[bool] = None


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    id:                uuid.UUID
    notification_type: str
    channel:           str
    language:          str
    title_template:    Optional[str]
    subject_template:  Optional[str]
    body_template:     str
    is_active:         bool
    updated_at:        datetime

    @classmethod
    def from_orm(cls, t) -> "TemplateResponse":
        return cls(
            id=t.id, notification_type=t.notification_type,
            channel=t.channel.value, language=t.language,
            title_template=t.title_template, subject_template=t.subject_template,
            body_template=t.body_template, is_active=t.is_active,
            updated_at=t.updated_at,
        )


# ── Additional schemas for new API endpoints ──────────────────────────────────

class NotificationDispatchResponse(BaseModel):  # noqa: F811 (redefine with accepted field)
    model_config = ConfigDict(from_attributes=False)
    notification_id: Optional[uuid.UUID] = None
    accepted: bool = True


class NotificationInboxItem(BaseModel):
    """Single item in the notification inbox feed."""
    model_config = ConfigDict(from_attributes=False)

    delivery_id:       uuid.UUID
    notification_id:   uuid.UUID
    notification_type: str
    priority:          str
    rendered_title:    Optional[str]   = None
    rendered_body:     Optional[str]   = None
    read_at:           Optional[datetime] = None
    created_at:        datetime
    is_read:           bool

    @classmethod
    def from_notification(cls, n) -> "NotificationInboxItem":
        # Find the in_app delivery for this notification
        in_app_delivery = next(
            (d for d in (n.deliveries or []) if d.channel.value == "in_app"),
            None,
        )
        return cls(
            delivery_id       = in_app_delivery.id if in_app_delivery else n.id,
            notification_id   = n.id,
            notification_type = n.notification_type,
            priority          = n.priority.value,
            rendered_title    = in_app_delivery.rendered_title if in_app_delivery else None,
            rendered_body     = in_app_delivery.rendered_body if in_app_delivery else None,
            read_at           = in_app_delivery.read_at if in_app_delivery else None,
            created_at        = n.created_at,
            is_read           = in_app_delivery.read_at is not None if in_app_delivery else False,
        )


class NotificationInboxResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    unread_count: int
    returned:     int
    items:        List[NotificationInboxItem] = []


class UnreadCountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    unread_count: int


class NotificationPreferenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                uuid.UUID
    user_id:           uuid.UUID
    notification_type: str
    channel:           str
    enabled:           bool
    updated_at:        datetime


class NotificationPreferenceRequest(BaseModel):
    notification_type: str = Field(
        description="Exact type or wildcard prefix e.g. 'grm.*', 'grm.feedback.acknowledged'"
    )
    channel: str = Field(description="in_app | push | sms | whatsapp | email")
    enabled: bool

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        valid = {"in_app", "push", "sms", "whatsapp", "email"}
        if v not in valid:
            raise ValueError(f"channel must be one of {sorted(valid)}")
        return v


class DeviceRegisterRequest(BaseModel):
    platform:    str = Field(description="fcm | apns")
    push_token:  str = Field(max_length=512)
    device_name: Optional[str] = None
    app_version: Optional[str] = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in ("fcm", "apns"):
            raise ValueError("platform must be 'fcm' or 'apns'")
        return v


class DeviceTokenUpdateRequest(BaseModel):
    push_token:  str = Field(max_length=512)
    app_version: Optional[str] = None


class TemplateRequest(BaseModel):
    notification_type: str = Field(max_length=120)
    channel:           str = Field(description="in_app | push | sms | whatsapp | email")
    language:          str = Field(max_length=5, default="en")
    title_template:    Optional[str] = Field(default=None, max_length=300)
    subject_template:  Optional[str] = Field(default=None, max_length=300)
    body_template:     str
    is_active:         bool = True
