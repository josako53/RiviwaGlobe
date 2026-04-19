# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  events/topics.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/topics.py
═══════════════════════════════════════════════════════════════════════════════
Kafka topic names and notification type constants used across all Riviwa
services.

The notification_service CONSUMES from:
  riviwa.notifications        — notification requests from all services

The notification_service PUBLISHES to:
  riviwa.notifications.events — delivery receipts (sent, failed, read)

NOTIFICATION TYPE NAMING CONVENTION
──────────────────────────────────────────────────────────────────────────────
  <domain>.<entity>.<event>

  Examples:
    auth.registration.otp_requested
    auth.login.otp_requested
    grm.feedback.submitted
    grm.feedback.acknowledged
    grm.feedback.assigned
    grm.feedback.escalated
    grm.feedback.resolved
    grm.feedback.closed
    grm.feedback.dismissed
    grm.feedback.appeal_filed
    grm.feedback.sla_breach_warning
    grm.escalation_request.received
    grm.escalation_request.approved
    grm.escalation_request.rejected
    project.activated
    project.stage.activated
    project.stage.completed
    project.checklist.item_due_soon
    project.checklist.item_overdue
    activity.reminder
    activity.conducted
    stakeholder.concern_auto_created
    payment.initiated
    payment.confirmed
    payment.failed
    system.welcome
    system.account_verified
    system.account_suspended
    system.account_banned
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations


class KafkaTopics:
    # Inbound — all services publish notification requests here
    NOTIFICATIONS         = "riviwa.notifications"
    # Outbound — notification_service publishes delivery receipts
    NOTIFICATION_EVENTS   = "riviwa.notifications.events"


class NotificationTypes:
    """
    All valid notification_type values used as template keys.
    Services publish using these constants — the notification_service
    looks up the matching template in the DB.
    """

    # ── Authentication ────────────────────────────────────────────────────────
    AUTH_REGISTRATION_OTP      = "auth.registration.otp_requested"
    AUTH_LOGIN_OTP             = "auth.login.otp_requested"
    AUTH_PASSWORD_RESET_OTP    = "auth.password_reset.otp_requested"
    AUTH_CHANNEL_LOGIN_OTP     = "auth.channel_login.otp_requested"
    AUTH_ACCOUNT_VERIFIED      = "system.account_verified"
    AUTH_ACCOUNT_SUSPENDED     = "system.account_suspended"
    AUTH_ACCOUNT_BANNED        = "system.account_banned"
    AUTH_ACCOUNT_REACTIVATED   = "system.account_reactivated"
    AUTH_WELCOME               = "system.welcome"
    AUTH_PASSWORD_CHANGED      = "auth.password.changed"
    AUTH_SOCIAL_PASSWORD_SET   = "auth.social.password_set"

    # ── GRM — Feedback ────────────────────────────────────────────────────────
    GRM_SUBMITTED              = "grm.feedback.submitted"
    GRM_ACKNOWLEDGED           = "grm.feedback.acknowledged"
    GRM_ASSIGNED               = "grm.feedback.assigned"
    GRM_ESCALATED              = "grm.feedback.escalated"
    GRM_RESOLVED               = "grm.feedback.resolved"
    GRM_CLOSED                 = "grm.feedback.closed"
    GRM_DISMISSED              = "grm.feedback.dismissed"
    GRM_APPEAL_FILED           = "grm.feedback.appeal_filed"
    GRM_APPEAL_RESOLVED        = "grm.feedback.appeal_resolved"
    GRM_SLA_BREACH_WARNING     = "grm.feedback.sla_breach_warning"
    GRM_COMMENT_ADDED          = "grm.feedback.comment_added"

    # ── GRM — Escalation requests (Consumer-initiated) ────────────────────────
    GRM_ESCALATION_REQUEST_RECEIVED  = "grm.escalation_request.received"
    GRM_ESCALATION_REQUEST_APPROVED  = "grm.escalation_request.approved"
    GRM_ESCALATION_REQUEST_REJECTED  = "grm.escalation_request.rejected"

    # ── Projects ──────────────────────────────────────────────────────────────
    PROJECT_ACTIVATED          = "project.activated"
    PROJECT_PAUSED             = "project.paused"
    PROJECT_RESUMED            = "project.resumed"
    PROJECT_COMPLETED          = "project.completed"
    PROJECT_STAGE_ACTIVATED    = "project.stage.activated"
    PROJECT_STAGE_COMPLETED    = "project.stage.completed"

    # ── Checklists ────────────────────────────────────────────────────────────
    CHECKLIST_ITEM_DUE_SOON    = "project.checklist.item_due_soon"
    CHECKLIST_ITEM_OVERDUE     = "project.checklist.item_overdue"
    CHECKLIST_ITEM_DONE        = "project.checklist.item_done"

    # ── Activities ────────────────────────────────────────────────────────────
    ACTIVITY_REMINDER          = "activity.reminder"
    ACTIVITY_CONDUCTED         = "activity.conducted"
    ACTIVITY_CANCELLED         = "activity.cancelled"

    # ── Stakeholders ──────────────────────────────────────────────────────────
    STAKEHOLDER_CONCERN_CREATED = "stakeholder.concern_auto_created"

    # ── Payments ──────────────────────────────────────────────────────────────
    PAYMENT_INITIATED          = "payment.initiated"
    PAYMENT_CONFIRMED          = "payment.confirmed"
    PAYMENT_FAILED             = "payment.failed"
    PAYMENT_REFUNDED           = "payment.refunded"

    # ── Organisations ─────────────────────────────────────────────────────────
    ORG_INVITE_RECEIVED        = "org.invite.received"
    ORG_INVITE_ACCEPTED        = "org.invite.accepted"
    ORG_MEMBER_ROLE_CHANGED    = "org.member.role_changed"
    ORG_OWNERSHIP_TRANSFERRED  = "org.ownership.transferred"


class NotificationChannel:
    """Channel identifiers used in notifications and preferences."""
    IN_APP    = "in_app"     # stored in DB, polled or SSE
    PUSH      = "push"       # FCM (Android) / APNs (iOS)
    SMS       = "sms"        # Africa's Talking / Twilio
    WHATSAPP  = "whatsapp"   # Meta Cloud API
    EMAIL     = "email"      # SendGrid / SMTP


class NotificationPriority:
    """
    Priority levels. Higher priority bypasses rate limits and
    may trigger fallback channels if primary channel fails.
    """
    CRITICAL = "critical"   # OTPs, security alerts — always sent immediately
    HIGH     = "high"       # SLA breaches, payment confirmed, GRM resolved
    MEDIUM   = "medium"     # Activity reminders, checklist due soon
    LOW      = "low"        # Informational, welcome messages


class DeliveryStatus:
    """Delivery status values for notification records."""
    PENDING   = "pending"    # created, not yet attempted
    SENT      = "sent"       # dispatched to provider
    DELIVERED = "delivered"  # provider confirmed delivery
    FAILED    = "failed"     # all retries exhausted
    SKIPPED   = "skipped"    # user preference or rate limit prevented send
    READ      = "read"       # in_app: user opened the notification
