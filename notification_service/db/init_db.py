# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  db/init_db.py
# ───────────────────────────────────────────────────────────────────────────
"""
db/init_db.py
════════════════════════════════════════════════════════════════════════════
Database initialisation for notification_service.

Called once at startup from main.py lifespan.

What it does:
  1. Retries connection up to max_retries times with exponential backoff.
     Handles the race condition where the DB container is "healthy" in Docker
     but still initialising its filesystem.
  2. Creates all SQLModel tables via metadata.create_all.
     In production this is a no-op because Alembic already created the tables.
     In development (ENVIRONMENT=development/staging) it creates tables when
     there are no Alembic version files.
  3. Seeds default notification templates on first boot.

Seeds
─────
  Default templates are seeded for all notification types across all channels.
  The seed is idempotent — skipped if the template already exists.
  Templates can be customised via PUT /api/v1/templates (admin endpoint).
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
from typing import Optional

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel

from db.session import engine, AsyncSessionLocal

# Import ALL models so SQLModel.metadata knows about every table
from models.notification import (           # noqa: F401 — must be imported for metadata
    NotificationTemplate,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationDevice,
)

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Seed data — default templates
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_TEMPLATES = [
    # ── Authentication ────────────────────────────────────────────────────────
    {
        "notification_type": "auth.registration.otp_requested",
        "channel": "sms", "language": "en",
        "body_template": "Your Riviwa verification code is {{ otp_code }}. Valid for {{ expires_minutes }} minutes. Do not share this code.",
    },
    {
        "notification_type": "auth.registration.otp_requested",
        "channel": "sms", "language": "sw",
        "body_template": "Nambari yako ya uthibitishaji wa Riviwa ni {{ otp_code }}. Inaisha baada ya dakika {{ expires_minutes }}. Usishiriki nambari hii.",
    },
    {
        "notification_type": "auth.registration.otp_requested",
        "channel": "email", "language": "en",
        "subject_template": "Your Riviwa verification code",
        "body_template": "<p>Your verification code is: <strong>{{ otp_code }}</strong></p><p>Valid for {{ expires_minutes }} minutes.</p>",
    },
    {
        "notification_type": "auth.login.otp_requested",
        "channel": "sms", "language": "en",
        "body_template": "Your Riviwa login code is {{ otp_code }}. Valid for {{ expires_minutes }} minutes.",
    },
    {
        "notification_type": "auth.login.otp_requested",
        "channel": "sms", "language": "sw",
        "body_template": "Nambari yako ya kuingia Riviwa ni {{ otp_code }}. Inaisha baada ya dakika {{ expires_minutes }}.",
    },
    {
        "notification_type": "auth.password_reset.otp_requested",
        "channel": "sms", "language": "en",
        "body_template": "Your Riviwa password reset code is {{ otp_code }}. Valid for {{ expires_minutes }} minutes.",
    },
    {
        "notification_type": "system.welcome",
        "channel": "in_app", "language": "en",
        "title_template": "Welcome to Riviwa",
        "body_template": "Welcome, {{ display_name }}! Your account is ready. You can now submit feedback, track projects, and stay informed.",
    },
    {
        "notification_type": "system.account_suspended",
        "channel": "in_app", "language": "en",
        "title_template": "Account Suspended",
        "body_template": "Your account has been suspended.{% if reason %} Reason: {{ reason }}.{% endif %} Contact support if you believe this is an error.",
    },
    {
        "notification_type": "system.account_banned",
        "channel": "in_app", "language": "en",
        "title_template": "Account Banned",
        "body_template": "Your account has been permanently banned.{% if reason %} Reason: {{ reason }}.{% endif %}",
    },
    {
        "notification_type": "system.account_reactivated",
        "channel": "in_app", "language": "en",
        "title_template": "Account Reactivated",
        "body_template": "Your account has been reactivated. Welcome back!",
    },
    # ── GRM Feedback ──────────────────────────────────────────────────────────
    {
        "notification_type": "grm.feedback.submitted",
        "channel": "sms", "language": "sw",
        "body_template": "Malalamiko/Maoni yako yamepokewa. Nambari ya kumbukumbu: {{ feedback_ref }}. Mradi: {{ project_name }}. Tutawasiliana nawe hivi karibuni.",
    },
    {
        "notification_type": "grm.feedback.submitted",
        "channel": "sms", "language": "en",
        "body_template": "Your feedback has been received. Reference: {{ feedback_ref }}. Project: {{ project_name }}. We will follow up shortly.",
    },
    {
        "notification_type": "grm.feedback.submitted",
        "channel": "in_app", "language": "en",
        "title_template": "Feedback Received",
        "body_template": "Your {{ feedback_type }} ({{ feedback_ref }}) has been received and is being reviewed.",
    },
    {
        "notification_type": "grm.feedback.acknowledged",
        "channel": "sms", "language": "sw",
        "body_template": "Malalamiko yako ({{ feedback_ref }}) yamekiriwa. Tarehe ya kutatuliwa: {{ target_resolution_date }}.",
    },
    {
        "notification_type": "grm.feedback.acknowledged",
        "channel": "sms", "language": "en",
        "body_template": "Your feedback ({{ feedback_ref }}) has been acknowledged. Target resolution: {{ target_resolution_date }}.",
    },
    {
        "notification_type": "grm.feedback.acknowledged",
        "channel": "in_app", "language": "en",
        "title_template": "Feedback Acknowledged",
        "body_template": "Your submission {{ feedback_ref }} has been acknowledged by the project team. Target resolution: {{ target_resolution_date }}.",
    },
    {
        "notification_type": "grm.feedback.resolved",
        "channel": "sms", "language": "sw",
        "body_template": "Malalamiko yako ({{ feedback_ref }}) yametatuliwa. {{ resolution_summary }}",
    },
    {
        "notification_type": "grm.feedback.resolved",
        "channel": "sms", "language": "en",
        "body_template": "Your feedback ({{ feedback_ref }}) has been resolved. {{ resolution_summary }}",
    },
    {
        "notification_type": "grm.feedback.resolved",
        "channel": "in_app", "language": "en",
        "title_template": "Feedback Resolved",
        "body_template": "Your submission {{ feedback_ref }} has been resolved. {{ resolution_summary }}",
    },
    {
        "notification_type": "grm.feedback.sla_breach_warning",
        "channel": "push", "language": "en",
        "title_template": "SLA Breach Warning",
        "body_template": "{{ feedback_ref }} ({{ priority }} priority) is {{ hours_overdue }}h past its SLA. Project: {{ project_name }}.",
    },
    {
        "notification_type": "grm.feedback.sla_breach_warning",
        "channel": "in_app", "language": "en",
        "title_template": "SLA Breach — Action Required",
        "body_template": "Grievance {{ feedback_ref }} is {{ hours_overdue }} hours past its target resolution date. Immediate action required.",
    },
    # ── Projects ──────────────────────────────────────────────────────────────
    {
        "notification_type": "project.activated",
        "channel": "push", "language": "en",
        "title_template": "Project Activated",
        "body_template": "{{ project_name }} ({{ project_code }}) is now active. Stakeholder engagement and feedback collection have begun.",
    },
    {
        "notification_type": "project.activated",
        "channel": "in_app", "language": "en",
        "title_template": "Project Now Active",
        "body_template": "{{ project_name }} ({{ project_code }}) has been activated and is now open for feedback.",
    },
    # ── Checklists ────────────────────────────────────────────────────────────
    {
        "notification_type": "project.checklist.item_due_soon",
        "channel": "push", "language": "en",
        "title_template": "Checklist Item Due Soon",
        "body_template": "\"{{ item_title }}\" is due in {{ days_remaining }} day(s) ({{ due_date }}). Entity: {{ entity_name }}.",
    },
    {
        "notification_type": "project.checklist.item_due_soon",
        "channel": "in_app", "language": "en",
        "title_template": "Checklist Item Due in {{ days_remaining }} Day(s)",
        "body_template": "\"{{ item_title }}\" must be completed by {{ due_date }}.",
    },
    {
        "notification_type": "project.checklist.item_overdue",
        "channel": "push", "language": "en",
        "title_template": "Checklist Item Overdue",
        "body_template": "\"{{ item_title }}\" was due {{ due_date }} and is now {{ days_overdue }} day(s) overdue.",
    },
    {
        "notification_type": "project.checklist.item_overdue",
        "channel": "in_app", "language": "en",
        "title_template": "Overdue: {{ item_title }}",
        "body_template": "\"{{ item_title }}\" is {{ days_overdue }} day(s) overdue. Due date was {{ due_date }}.",
    },
    # ── Activities ────────────────────────────────────────────────────────────
    {
        "notification_type": "activity.reminder",
        "channel": "push", "language": "en",
        "title_template": "Meeting Tomorrow",
        "body_template": "Reminder: {{ activity_title }} at {{ venue }} on {{ scheduled_at }}.",
    },
    {
        "notification_type": "activity.reminder",
        "channel": "in_app", "language": "en",
        "title_template": "Activity Reminder",
        "body_template": "{{ activity_title }} is scheduled for {{ scheduled_at }} at {{ venue }}.",
    },
    # ── Payments ──────────────────────────────────────────────────────────────
    {
        "notification_type": "payment.confirmed",
        "channel": "sms", "language": "en",
        "body_template": "Payment confirmed: {{ currency }} {{ amount }} for {{ description }}. Thank you.",
    },
    {
        "notification_type": "payment.confirmed",
        "channel": "in_app", "language": "en",
        "title_template": "Payment Confirmed",
        "body_template": "Your payment of {{ currency }} {{ amount }} for {{ description }} has been confirmed.",
    },
    {
        "notification_type": "payment.failed",
        "channel": "sms", "language": "en",
        "body_template": "Payment failed: {{ currency }} {{ amount }}. Reason: {{ reason }}. Please try again.",
    },
    {
        "notification_type": "payment.failed",
        "channel": "in_app", "language": "en",
        "title_template": "Payment Failed",
        "body_template": "Your payment of {{ currency }} {{ amount }} failed. Reason: {{ reason }}.",
    },
    # ── Organisations ─────────────────────────────────────────────────────────
    {
        "notification_type": "org.invite.received",
        "channel": "email", "language": "en",
        "subject_template": "You've been invited to join {{ org_name }} on Riviwa",
        "body_template": "<p>{{ inviter_name }} has invited you to join <strong>{{ org_name }}</strong> as <strong>{{ role }}</strong>.</p><p>Log in to Riviwa to accept or decline.</p>",
    },
]


async def seed_default_templates() -> None:
    """
    Idempotent: seeds default notification templates on first boot.
    Skips any template whose (notification_type, channel, language) already exists.
    """
    from models.notification import ChannelEnum
    from sqlmodel import select

    async with AsyncSessionLocal() as db:
        seeded = 0
        for tmpl_data in _DEFAULT_TEMPLATES:
            existing = await db.execute(
                select(NotificationTemplate).where(
                    NotificationTemplate.notification_type == tmpl_data["notification_type"],
                    NotificationTemplate.channel           == ChannelEnum(tmpl_data["channel"]),
                    NotificationTemplate.language          == tmpl_data["language"],
                )
            )
            if existing.scalar_one_or_none():
                continue
            tmpl = NotificationTemplate(
                notification_type = tmpl_data["notification_type"],
                channel           = ChannelEnum(tmpl_data["channel"]),
                language          = tmpl_data["language"],
                title_template    = tmpl_data.get("title_template"),
                subject_template  = tmpl_data.get("subject_template"),
                body_template     = tmpl_data["body_template"],
                is_active         = True,
            )
            db.add(tmpl)
            seeded += 1
        await db.commit()
    log.info("notification.templates.seeded", count=seeded)


# ─────────────────────────────────────────────────────────────────────────────
# Main init function
# ─────────────────────────────────────────────────────────────────────────────

async def init_db(
    max_retries:    int   = 5,
    initial_delay:  float = 2.0,
    backoff_factor: float = 2.0,
) -> None:
    """
    Create all tables and seed default data.

    Retries up to max_retries times with exponential backoff to handle the
    race condition where the DB container is healthy but still initialising.

    In production Alembic migrations (run via entrypoint.sh) create the tables
    before this function runs, so create_all is a no-op. In development/staging
    it creates tables when there are no Alembic migration files.
    """
    delay    = initial_delay
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            log.info("notification.db.tables_ready")
            await seed_default_templates()
            return
        except (SQLAlchemyError, OSError) as exc:
            last_exc = exc
            log.warning(
                "notification.db.init.retry",
                attempt       = attempt,
                max_retries   = max_retries,
                delay_seconds = delay,
                error         = str(exc),
            )
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= backoff_factor

    raise RuntimeError(
        f"notification_service: database unreachable after {max_retries} attempts."
    ) from last_exc
