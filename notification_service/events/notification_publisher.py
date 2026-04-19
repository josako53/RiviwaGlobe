# ───────────────────────────────────────────────────────────────────────────
# SHARED UTILITY  (copy into each service that sends notifications)
# FILE     :  events/notification_publisher.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/notification_publisher.py
═══════════════════════════════════════════════════════════════════════════════
Shared helper that any Riviwa service uses to publish notification requests
to the notification_service via Kafka.

DESIGN PRINCIPLE — notification_service is ignorant of business logic:
  · The SOURCE service (auth, feedback, stakeholder, payment) owns the
    decision of WHAT to notify about, WHO to notify, and with WHAT data.
  · This publisher just wraps the Kafka publish call with a typed interface.
  · The notification_service only handles HOW to deliver it.

USAGE in each source service:
  from events.notification_publisher import NotificationPublisher

  publisher = NotificationPublisher(kafka_producer)

  # Immediately dispatched
  await publisher.send(
      notification_type  = NotificationTypes.GRM_ACKNOWLEDGED,
      recipient_user_id  = str(consumer_user_id),
      recipient_phone    = "+255712345678",
      language           = "sw",
      variables          = {
          "feedback_ref":  "GRV-2025-0041",
          "project_name":  "Msimbazi Flood Control",
          "ack_note":      "Your complaint has been received.",
      },
      preferred_channels = ["push", "sms"],
      priority           = "high",
      idempotency_key    = f"feedback:{feedback_id}:acknowledged:{date.today()}",
      source_service     = "feedback_service",
      source_entity_id   = str(feedback_id),
  )

  # Reminder — scheduled for future delivery (e.g. checklist item due)
  await publisher.send(
      notification_type  = NotificationTypes.CHECKLIST_ITEM_DUE_SOON,
      recipient_user_id  = str(assigned_user_id),
      language           = "en",
      variables          = {
          "item_title":    "Submit Environmental Impact Assessment",
          "due_date":      "2025-06-30",
          "project_name":  "Msimbazi Flood Control",
      },
      preferred_channels = ["push", "in_app"],
      priority           = "medium",
      idempotency_key    = f"checklist:{item_id}:due_soon:{date.today()}",
      source_service     = "riviwa_auth_service",
      source_entity_id   = str(item_id),
      scheduled_at       = reminder_datetime,   # datetime object
  )

NOTIFICATION TYPE CONSTANTS
  Import from notification_service.events.topics.NotificationTypes or
  duplicate the constants in each service's own topics.py.

CHANNEL OPTIONS:
  "in_app"   — stored in DB, polled by app (always available, no credentials needed)
  "push"     — FCM / APNs (requires device registration)
  "sms"      — Africa's Talking / Twilio (requires phone number)
  "whatsapp" — Meta Cloud API (requires phone number + pre-approved template)
  "email"    — SendGrid / SMTP (requires email address)

PRIORITY LEVELS:
  "critical" — OTPs, security alerts. Bypasses user preferences. Always sent.
  "high"     — SLA breaches, payment confirmed, feedback resolved.
  "medium"   — Reminders, checklist due soon. Sent to push + in_app.
  "low"      — Informational. in_app only.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

log = structlog.get_logger(__name__)

# The notification Kafka topic — same across all services
NOTIFICATIONS_TOPIC = "riviwa.notifications"


class NotificationPublisher:
    """
    Thin wrapper over a Kafka producer that formats and publishes
    notification requests to the notification_service.

    Works with any producer that implements:
        async def send_and_wait(topic, value, key) -> None
    OR the pattern used by aiokafka's AIOKafkaProducer.

    Pass the raw AIOKafkaProducer or the service's producer wrapper.
    The publisher uses the producer's underlying send mechanism.
    """

    def __init__(self, producer: Any, service_name: str = "unknown_service") -> None:
        self._producer    = producer
        self._service     = service_name

    async def send(
        self,
        notification_type:   str,
        *,
        recipient_user_id:   Optional[str]      = None,
        recipient_phone:     Optional[str]       = None,
        recipient_email:     Optional[str]       = None,
        recipient_push_tokens: List[str]         = None,
        language:            str                 = "en",
        variables:           Dict[str, Any]      = None,
        preferred_channels:  List[str]           = None,
        priority:            str                 = "medium",
        idempotency_key:     Optional[str]       = None,
        scheduled_at:        Optional[datetime]  = None,
        source_entity_id:    Optional[str]       = None,
        metadata:            Dict[str, Any]      = None,
    ) -> None:
        """
        Publish one notification request to the riviwa.notifications Kafka topic.

        Args:
            notification_type:     Template lookup key (e.g. "grm.feedback.acknowledged")
            recipient_user_id:     auth_service User.id (str or uuid). Null for pre-reg OTPs.
            recipient_phone:       E.164 phone number. Required for sms / whatsapp channels.
            recipient_email:       Email address. Required for email channel.
            recipient_push_tokens: FCM/APNs tokens. If omitted, notification_service
                                   loads them from the NotificationDevice table.
            language:              ISO 639-1 code. "sw" for Swahili, "en" for English.
            variables:             Jinja2 template rendering variables.
            preferred_channels:    Which channels to use. If empty, notification_service
                                   applies defaults based on priority.
            priority:              "critical" | "high" | "medium" | "low"
            idempotency_key:       Prevents duplicate sends on Kafka replay.
                                   Recommended format: "<domain>:<id>:<event>:<date>"
                                   e.g. "feedback:uuid:acknowledged:2025-06-15"
            scheduled_at:          Future datetime → stored as PENDING_SCHEDULED,
                                   APScheduler fires at that time (reminder).
                                   None → dispatch immediately.
            source_entity_id:      ID of the entity that triggered this notification
                                   (feedback_id, project_id, etc.).
            metadata:              Arbitrary extra context for debugging / audit.
        """
        payload = {
            "notification_type":     notification_type,
            "recipient_user_id":     str(recipient_user_id) if recipient_user_id else None,
            "recipient_phone":       recipient_phone,
            "recipient_email":       recipient_email,
            "recipient_push_tokens": recipient_push_tokens or [],
            "language":              language,
            "variables":             variables or {},
            "preferred_channels":    preferred_channels or [],
            "priority":              priority,
            "idempotency_key":       idempotency_key,
            "scheduled_at":          scheduled_at.isoformat() if scheduled_at else None,
            "source_service":        self._service,
            "source_entity_id":      str(source_entity_id) if source_entity_id else None,
            "metadata":              metadata or {},
        }

        # Partition key: recipient_user_id for ordering, else notification_type
        key = str(recipient_user_id) if recipient_user_id else notification_type

        try:
            # Support both raw AIOKafkaProducer and wrapped producers
            if hasattr(self._producer, "send_and_wait"):
                import json
                await self._producer.send_and_wait(
                    NOTIFICATIONS_TOPIC,
                    value=json.dumps(payload, default=str).encode("utf-8"),
                    key=key.encode("utf-8"),
                )
            elif hasattr(self._producer, "publish"):
                # Some services wrap with a .publish(topic, value, key) method
                await self._producer.publish(
                    topic=NOTIFICATIONS_TOPIC,
                    value=payload,
                    key=key,
                )
            else:
                log.error("notification_publisher.unsupported_producer",
                          producer_type=type(self._producer).__name__)
                return

            log.debug(
                "notification.published",
                notification_type=notification_type,
                priority=priority,
                recipient_user_id=str(recipient_user_id) if recipient_user_id else None,
                channels=preferred_channels,
                scheduled=scheduled_at.isoformat() if scheduled_at else "immediate",
            )

        except Exception as exc:
            # Fire-and-forget — never block the caller on notification failure
            log.error(
                "notification_publisher.failed",
                notification_type=notification_type,
                error=str(exc),
            )

    # ── Typed convenience methods ─────────────────────────────────────────────
    # These mirror common notification scenarios. Each source service can
    # call these instead of building the dict manually.

    # ── Authentication ────────────────────────────────────────────────────────

    async def auth_registration_otp(
        self,
        recipient_phone: Optional[str],
        recipient_email: Optional[str],
        otp_code:        str,
        language:        str = "en",
        idempotency_key: Optional[str] = None,
    ) -> None:
        channel = ["sms"] if recipient_phone else ["email"]
        await self.send(
            notification_type  = "auth.registration.otp_requested",
            recipient_phone    = recipient_phone,
            recipient_email    = recipient_email,
            language           = language,
            variables          = {"otp_code": otp_code, "expires_minutes": 10},
            preferred_channels = channel,
            priority           = "critical",
            idempotency_key    = idempotency_key,
        )

    async def auth_login_otp(
        self,
        recipient_user_id: str,
        recipient_phone:   Optional[str],
        recipient_email:   Optional[str],
        otp_code:          str,
        language:          str = "en",
        idempotency_key:   Optional[str] = None,
    ) -> None:
        channel = ["sms"] if recipient_phone else ["email"]
        await self.send(
            notification_type  = "auth.login.otp_requested",
            recipient_user_id  = recipient_user_id,
            recipient_phone    = recipient_phone,
            recipient_email    = recipient_email,
            language           = language,
            variables          = {"otp_code": otp_code, "expires_minutes": 5},
            preferred_channels = channel,
            priority           = "critical",
            idempotency_key    = idempotency_key,
        )

    async def auth_password_reset_otp(
        self,
        recipient_phone: Optional[str],
        recipient_email: Optional[str],
        otp_code:        str,
        language:        str = "en",
        idempotency_key: Optional[str] = None,
    ) -> None:
        channel = ["sms"] if recipient_phone else ["email"]
        await self.send(
            notification_type  = "auth.password_reset.otp_requested",
            recipient_phone    = recipient_phone,
            recipient_email    = recipient_email,
            language           = language,
            variables          = {"otp_code": otp_code, "expires_minutes": 10},
            preferred_channels = channel,
            priority           = "critical",
            idempotency_key    = idempotency_key,
        )

    async def auth_welcome(
        self,
        recipient_user_id: str,
        display_name:      str,
        language:          str = "en",
    ) -> None:
        await self.send(
            notification_type  = "system.welcome",
            recipient_user_id  = recipient_user_id,
            language           = language,
            variables          = {"display_name": display_name},
            preferred_channels = ["push", "in_app"],
            priority           = "low",
            idempotency_key    = f"auth:{recipient_user_id}:welcome",
        )

    async def account_status_changed(
        self,
        recipient_user_id: str,
        notification_type: str,        # "system.account_suspended" etc.
        reason:            Optional[str] = None,
        language:          str = "en",
    ) -> None:
        await self.send(
            notification_type  = notification_type,
            recipient_user_id  = recipient_user_id,
            language           = language,
            variables          = {"reason": reason or ""},
            preferred_channels = ["push", "sms", "email", "in_app"],
            priority           = "high",
            idempotency_key    = f"auth:{recipient_user_id}:{notification_type}",
        )

    # ── GRM Feedback ──────────────────────────────────────────────────────────

    async def grm_feedback_submitted(
        self,
        feedback_id:       str,
        consumer_user_id:  Optional[str],
        consumer_phone:    Optional[str],
        feedback_ref:      str,
        project_name:      str,
        feedback_type:     str,
        language:          str = "sw",
    ) -> None:
        """Notify Consumer that their feedback was received."""
        await self.send(
            notification_type  = "grm.feedback.submitted",
            recipient_user_id  = consumer_user_id,
            recipient_phone    = consumer_phone,
            language           = language,
            variables          = {
                "feedback_ref":   feedback_ref,
                "project_name":   project_name,
                "feedback_type":  feedback_type,
            },
            preferred_channels = ["sms", "push", "in_app"],
            priority           = "medium",
            idempotency_key    = f"feedback:{feedback_id}:submitted",
            source_entity_id   = feedback_id,
        )

    async def grm_feedback_acknowledged(
        self,
        feedback_id:            str,
        consumer_user_id:       Optional[str],
        consumer_phone:         Optional[str],
        feedback_ref:           str,
        project_name:           str,
        target_resolution_date: Optional[str],
        language:               str = "sw",
    ) -> None:
        await self.send(
            notification_type  = "grm.feedback.acknowledged",
            recipient_user_id  = consumer_user_id,
            recipient_phone    = consumer_phone,
            language           = language,
            variables          = {
                "feedback_ref":           feedback_ref,
                "project_name":           project_name,
                "target_resolution_date": target_resolution_date or "",
            },
            preferred_channels = ["sms", "push", "in_app"],
            priority           = "high",
            idempotency_key    = f"feedback:{feedback_id}:acknowledged",
            source_entity_id   = feedback_id,
        )

    async def grm_feedback_resolved(
        self,
        feedback_id:        str,
        consumer_user_id:   Optional[str],
        consumer_phone:     Optional[str],
        feedback_ref:       str,
        project_name:       str,
        resolution_summary: str,
        language:           str = "sw",
    ) -> None:
        await self.send(
            notification_type  = "grm.feedback.resolved",
            recipient_user_id  = consumer_user_id,
            recipient_phone    = consumer_phone,
            language           = language,
            variables          = {
                "feedback_ref":       feedback_ref,
                "project_name":       project_name,
                "resolution_summary": resolution_summary,
            },
            preferred_channels = ["sms", "push", "in_app"],
            priority           = "high",
            idempotency_key    = f"feedback:{feedback_id}:resolved",
            source_entity_id   = feedback_id,
        )

    async def grm_sla_breach_warning(
        self,
        feedback_id:      str,
        assigned_user_id: str,
        feedback_ref:     str,
        project_name:     str,
        priority_level:   str,
        hours_overdue:    float,
        language:         str = "en",
    ) -> None:
        """
        Alert GRM Unit staff when a grievance is approaching or past its SLA.
        Scheduled by feedback_service's background job.
        """
        await self.send(
            notification_type  = "grm.feedback.sla_breach_warning",
            recipient_user_id  = assigned_user_id,
            language           = language,
            variables          = {
                "feedback_ref":  feedback_ref,
                "project_name":  project_name,
                "priority":      priority_level,
                "hours_overdue": str(round(hours_overdue, 1)),
            },
            preferred_channels = ["push", "in_app"],
            priority           = "high",
            idempotency_key    = f"feedback:{feedback_id}:sla_breach:{round(hours_overdue)}h",
            source_entity_id   = feedback_id,
        )

    # ── Projects ──────────────────────────────────────────────────────────────

    async def project_activated(
        self,
        project_id:     str,
        org_member_ids: list,          # list of user_id strings to notify
        project_name:   str,
        project_code:   str,
        language:       str = "en",
    ) -> None:
        """Notify all org members when a project is activated."""
        for user_id in org_member_ids:
            await self.send(
                notification_type  = "project.activated",
                recipient_user_id  = user_id,
                language           = language,
                variables          = {
                    "project_name": project_name,
                    "project_code": project_code,
                },
                preferred_channels = ["push", "in_app"],
                priority           = "medium",
                idempotency_key    = f"project:{project_id}:activated:{user_id}",
                source_entity_id   = project_id,
            )

    # ── Checklists ────────────────────────────────────────────────────────────

    async def checklist_item_due_soon(
        self,
        item_id:        str,
        assigned_user_id: str,
        item_title:     str,
        due_date:       str,
        entity_name:    str,      # project / stage / sub-project name
        days_remaining: int,
        scheduled_at:   Optional[datetime] = None,
        language:       str = "en",
    ) -> None:
        """
        Send a reminder that a checklist item is due soon.
        If scheduled_at is provided, the notification will be held until that time.
        """
        await self.send(
            notification_type  = "project.checklist.item_due_soon",
            recipient_user_id  = assigned_user_id,
            language           = language,
            variables          = {
                "item_title":     item_title,
                "due_date":       due_date,
                "entity_name":    entity_name,
                "days_remaining": str(days_remaining),
            },
            preferred_channels = ["push", "in_app"],
            priority           = "medium",
            idempotency_key    = f"checklist:{item_id}:due_soon:{due_date}",
            source_entity_id   = item_id,
            scheduled_at       = scheduled_at,
        )

    async def checklist_item_overdue(
        self,
        item_id:          str,
        assigned_user_id: str,
        item_title:       str,
        due_date:         str,
        entity_name:      str,
        days_overdue:     int,
        language:         str = "en",
    ) -> None:
        await self.send(
            notification_type  = "project.checklist.item_overdue",
            recipient_user_id  = assigned_user_id,
            language           = language,
            variables          = {
                "item_title":   item_title,
                "due_date":     due_date,
                "entity_name":  entity_name,
                "days_overdue": str(days_overdue),
            },
            preferred_channels = ["push", "sms", "in_app"],
            priority           = "high",
            idempotency_key    = f"checklist:{item_id}:overdue:{due_date}",
            source_entity_id   = item_id,
        )

    # ── Engagement activities ─────────────────────────────────────────────────

    async def activity_reminder(
        self,
        activity_id:    str,
        recipient_ids:  list,         # staff user_ids
        activity_title: str,
        venue:          str,
        scheduled_at:   datetime,     # actual meeting time (used as scheduled_at too)
        language:       str = "en",
    ) -> None:
        """
        Schedule a reminder for an upcoming engagement activity.
        The reminder fires 24 hours before the scheduled meeting time.
        """
        from datetime import timedelta
        reminder_time = scheduled_at - timedelta(hours=24)
        for user_id in recipient_ids:
            await self.send(
                notification_type  = "activity.reminder",
                recipient_user_id  = user_id,
                language           = language,
                variables          = {
                    "activity_title": activity_title,
                    "venue":          venue,
                    "scheduled_at":   scheduled_at.strftime("%d %b %Y %H:%M"),
                },
                preferred_channels = ["push", "in_app"],
                priority           = "medium",
                idempotency_key    = f"activity:{activity_id}:reminder:{user_id}",
                source_entity_id   = activity_id,
                scheduled_at       = reminder_time if reminder_time > datetime.now(timezone.utc) else None,
            )

    # ── Payments ──────────────────────────────────────────────────────────────

    async def payment_confirmed(
        self,
        payment_id:       str,
        recipient_user_id: str,
        recipient_phone:  Optional[str],
        amount:           float,
        currency:         str,
        description:      str,
        language:         str = "en",
    ) -> None:
        await self.send(
            notification_type  = "payment.confirmed",
            recipient_user_id  = recipient_user_id,
            recipient_phone    = recipient_phone,
            language           = language,
            variables          = {
                "amount":      f"{amount:,.0f}",
                "currency":    currency,
                "description": description,
            },
            preferred_channels = ["sms", "push", "in_app"],
            priority           = "high",
            idempotency_key    = f"payment:{payment_id}:confirmed",
            source_entity_id   = payment_id,
        )

    async def payment_failed(
        self,
        payment_id:        str,
        recipient_user_id: str,
        recipient_phone:   Optional[str],
        amount:            float,
        currency:          str,
        reason:            str,
        language:          str = "en",
    ) -> None:
        await self.send(
            notification_type  = "payment.failed",
            recipient_user_id  = recipient_user_id,
            recipient_phone    = recipient_phone,
            language           = language,
            variables          = {
                "amount":   f"{amount:,.0f}",
                "currency": currency,
                "reason":   reason,
            },
            preferred_channels = ["sms", "push", "in_app"],
            priority           = "high",
            idempotency_key    = f"payment:{payment_id}:failed",
            source_entity_id   = payment_id,
        )

    # ── Organisation ──────────────────────────────────────────────────────────

    async def org_invite_received(
        self,
        invite_id:        str,
        recipient_email:  str,
        org_name:         str,
        role:             str,
        inviter_name:     str,
        language:         str = "en",
    ) -> None:
        await self.send(
            notification_type  = "org.invite.received",
            recipient_email    = recipient_email,
            language           = language,
            variables          = {
                "org_name":     org_name,
                "role":         role,
                "inviter_name": inviter_name,
            },
            preferred_channels = ["email"],
            priority           = "medium",
            idempotency_key    = f"org_invite:{invite_id}:received",
            source_entity_id   = invite_id,
        )
