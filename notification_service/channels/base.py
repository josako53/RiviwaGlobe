# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  channels/base.py
# ───────────────────────────────────────────────────────────────────────────
"""
channels/base.py
═══════════════════════════════════════════════════════════════════════════════
Abstract base class for all notification delivery channels.

Every channel implementation must:
  1. Implement send() — the core dispatch method
  2. Return a ChannelResult indicating success/failure + provider message ID
  3. Be stateless — no session/DB access inside channels; that is done by
     DeliveryService which wraps each channel call

Channel implementations:
  · InAppChannel     — writes to notification_deliveries (no external provider)
  · PushChannel      — FCM (Android/Web) and APNs (iOS) via firebase-admin
  · SMSChannel       — Africa's Talking primary, Twilio fallback
  · WhatsAppChannel  — Meta Cloud API
  · EmailChannel     — SendGrid primary, SMTP fallback
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChannelResult:
    """
    Returned by every channel's send() method.

    success = True  → message accepted by the provider (not yet delivered)
    success = False → provider rejected the message or a network error occurred
    provider_message_id → provider-assigned ID for DLR correlation
    failure_reason → human-readable reason for failure (for audit trail)
    should_retry → False for permanent failures (invalid number, unsubscribed)
    """
    success:             bool
    provider_message_id: Optional[str] = None
    failure_reason:      Optional[str] = None
    should_retry:        bool          = True

    @classmethod
    def ok(cls, provider_message_id: Optional[str] = None) -> "ChannelResult":
        return cls(success=True, provider_message_id=provider_message_id)

    @classmethod
    def fail(cls, reason: str, should_retry: bool = True) -> "ChannelResult":
        return cls(success=False, failure_reason=reason, should_retry=should_retry)

    @classmethod
    def permanent_fail(cls, reason: str) -> "ChannelResult":
        """For failures that should NOT be retried: unsubscribed, invalid token, etc."""
        return cls(success=False, failure_reason=reason, should_retry=False)


@dataclass
class ChannelPayload:
    """
    All the information a channel needs to send a message.
    Assembled by DeliveryService before calling channel.send().
    """
    recipient_user_id:    Optional[str]       # may be null for pre-reg OTPs
    recipient_phone:      Optional[str]       # E.164 format
    recipient_email:      Optional[str]
    push_tokens:          list[str] = field(default_factory=list)  # FCM/APNs tokens
    rendered_title:       Optional[str] = None
    rendered_subject:     Optional[str] = None
    rendered_body:        str = ""
    notification_type:    str = ""
    priority:             str = "medium"
    language:             str = "en"


class BaseChannel(ABC):
    """
    Abstract base class for all notification channels.

    Channel implementations are STATELESS — they receive a ChannelPayload,
    call the external provider API, and return a ChannelResult.
    No database access. No business logic.
    """

    channel_name: str = "base"

    @abstractmethod
    async def send(self, payload: ChannelPayload) -> ChannelResult:
        """
        Dispatch the message to the external provider.
        Returns ChannelResult immediately — provider delivery is async.
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Returns True if this channel has the required provider credentials
        configured in settings. Used at startup to log which channels are active.
        """
        ...
