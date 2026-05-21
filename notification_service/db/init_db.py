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
    # ── Subscriptions ─────────────────────────────────────────────────────────
    # Trial started
    {
        "notification_type": "subscription.trial_started",
        "channel": "email", "language": "en",
        "subject_template": "Your {{ trial_days }}-day free trial of Riviwa {{ plan_name }} has started",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Your <strong>{{ trial_days }}-day free trial</strong> of the <strong>{{ plan_name }}</strong> plan "
            "has started for <strong>{{ org_name }}</strong>.</p>"
            "<p>Your trial ends on <strong>{{ trial_end_date }}</strong>. After that, you'll need to subscribe "
            "to keep access to your features.</p>"
            "<p>Explore everything included in your plan and subscribe before the trial ends to avoid interruption.</p>"
        ),
    },
    {
        "notification_type": "subscription.trial_started",
        "channel": "in_app", "language": "en",
        "title_template": "{{ trial_days }}-day free trial started",
        "body_template": "Your {{ trial_days }}-day free trial of {{ plan_name }} has started. Trial ends {{ trial_end_date }}.",
    },
    # Trial ending soon (7d / 3d)
    {
        "notification_type": "subscription.trial_ending_soon",
        "channel": "email", "language": "en",
        "subject_template": "Your Riviwa trial ends in {{ days_left }} day(s) — subscribe now to keep access",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Your free trial of <strong>{{ plan_name }}</strong> for <strong>{{ org_name }}</strong> "
            "ends in <strong>{{ days_left }} day(s)</strong> on {{ trial_end_date }}.</p>"
            "<p>Subscribe now to keep uninterrupted access to all your features, data, and team settings.</p>"
            "<p><strong>Current plan:</strong> {{ plan_name }} — {{ billing_cycle }} at ${{ price_usd }}/month</p>"
        ),
    },
    {
        "notification_type": "subscription.trial_ending_soon",
        "channel": "in_app", "language": "en",
        "title_template": "Trial ending in {{ days_left }} day(s)",
        "body_template": "Your {{ plan_name }} trial ends in {{ days_left }} day(s) on {{ trial_end_date }}. Subscribe to keep access.",
    },
    # Subscribed
    {
        "notification_type": "subscription.subscribed",
        "channel": "email", "language": "en",
        "subject_template": "Welcome to Riviwa {{ plan_name }} — subscription confirmed",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Thank you for subscribing! <strong>{{ org_name }}</strong> is now on the "
            "<strong>{{ plan_name }}</strong> plan.</p>"
            "<ul>"
            "<li><strong>Plan:</strong> {{ plan_name }}</li>"
            "<li><strong>Billing:</strong> {{ billing_cycle }} at ${{ price_usd }}/month</li>"
            "<li><strong>Next renewal:</strong> {{ next_renewal_date }}</li>"
            "<li><strong>Invoice:</strong> {{ invoice_number }}</li>"
            "</ul>"
            "<p>Your full feature set is now active. Thank you for choosing Riviwa.</p>"
        ),
    },
    {
        "notification_type": "subscription.subscribed",
        "channel": "in_app", "language": "en",
        "title_template": "Subscribed to {{ plan_name }}",
        "body_template": "{{ org_name }} is now on {{ plan_name }} ({{ billing_cycle }}). Next renewal: {{ next_renewal_date }}.",
    },
    # Payment receipt
    {
        "notification_type": "subscription.payment_receipt",
        "channel": "email", "language": "en",
        "subject_template": "Payment receipt — {{ invoice_number }} — ${{ amount_usd }}",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>We received your payment. Here is your receipt:</p>"
            "<table style='border-collapse:collapse;width:100%'>"
            "<tr><td><strong>Invoice</strong></td><td>{{ invoice_number }}</td></tr>"
            "<tr><td><strong>Plan</strong></td><td>{{ plan_name }} ({{ billing_cycle }})</td></tr>"
            "<tr><td><strong>Amount paid</strong></td><td>${{ amount_usd }}</td></tr>"
            "<tr><td><strong>Period</strong></td><td>{{ period_start }} to {{ period_end }}</td></tr>"
            "<tr><td><strong>Organisation</strong></td><td>{{ org_name }}</td></tr>"
            "</table>"
            "<p>Your next renewal is on <strong>{{ next_renewal_date }}</strong>.</p>"
        ),
    },
    {
        "notification_type": "subscription.payment_receipt",
        "channel": "in_app", "language": "en",
        "title_template": "Payment received — {{ invoice_number }}",
        "body_template": "Payment of ${{ amount_usd }} for {{ plan_name }} received. Invoice: {{ invoice_number }}.",
    },
    # Renewal reminder (7d / 3d / 1d)
    {
        "notification_type": "subscription.renewal_reminder",
        "channel": "email", "language": "en",
        "subject_template": "Reminder: Your Riviwa {{ plan_name }} subscription renews in {{ days_left }} day(s)",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Your <strong>{{ plan_name }}</strong> subscription for <strong>{{ org_name }}</strong> "
            "will automatically renew in <strong>{{ days_left }} day(s)</strong> on {{ renewal_date }}.</p>"
            "<ul>"
            "<li><strong>Plan:</strong> {{ plan_name }}</li>"
            "<li><strong>Amount:</strong> ${{ amount_usd }}/{{ billing_cycle }}</li>"
            "<li><strong>Renewal date:</strong> {{ renewal_date }}</li>"
            "</ul>"
            "<p>No action needed if you wish to continue. To cancel before renewal, visit your billing settings.</p>"
        ),
    },
    {
        "notification_type": "subscription.renewal_reminder",
        "channel": "in_app", "language": "en",
        "title_template": "Renewal in {{ days_left }} day(s)",
        "body_template": "{{ plan_name }} renews on {{ renewal_date }} for ${{ amount_usd }}. No action needed to continue.",
    },
    # Renewed
    {
        "notification_type": "subscription.renewed",
        "channel": "email", "language": "en",
        "subject_template": "Riviwa {{ plan_name }} subscription renewed successfully",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Your <strong>{{ plan_name }}</strong> subscription for <strong>{{ org_name }}</strong> "
            "has been renewed successfully.</p>"
            "<ul>"
            "<li><strong>Invoice:</strong> {{ invoice_number }}</li>"
            "<li><strong>Amount:</strong> ${{ amount_usd }}</li>"
            "<li><strong>Next renewal:</strong> {{ next_renewal_date }}</li>"
            "</ul>"
            "<p>Thank you for staying with Riviwa.</p>"
        ),
    },
    {
        "notification_type": "subscription.renewed",
        "channel": "in_app", "language": "en",
        "title_template": "Subscription renewed",
        "body_template": "{{ plan_name }} renewed. Next renewal: {{ next_renewal_date }}. Invoice: {{ invoice_number }}.",
    },
    # Upgraded
    {
        "notification_type": "subscription.upgraded",
        "channel": "email", "language": "en",
        "subject_template": "Plan upgraded to Riviwa {{ new_plan }} — extra features now active",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p><strong>{{ org_name }}</strong> has been upgraded from <strong>{{ old_plan }}</strong> "
            "to <strong>{{ new_plan }}</strong>.</p>"
            "<p>All {{ new_plan }} features are now active. Your next renewal reflects the new price.</p>"
        ),
    },
    {
        "notification_type": "subscription.upgraded",
        "channel": "in_app", "language": "en",
        "title_template": "Upgraded to {{ new_plan }}",
        "body_template": "{{ org_name }} upgraded from {{ old_plan }} to {{ new_plan }}. New features are now active.",
    },
    # Downgraded
    {
        "notification_type": "subscription.downgraded",
        "channel": "email", "language": "en",
        "subject_template": "Plan change to Riviwa {{ new_plan }} scheduled",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Your plan change from <strong>{{ old_plan }}</strong> to <strong>{{ new_plan }}</strong> "
            "has been scheduled. The change takes effect at your next renewal on "
            "<strong>{{ effective_date }}</strong>.</p>"
            "<p>Until then, you retain full access to your current {{ old_plan }} features.</p>"
        ),
    },
    {
        "notification_type": "subscription.downgraded",
        "channel": "in_app", "language": "en",
        "title_template": "Plan change scheduled",
        "body_template": "Downgrade from {{ old_plan }} to {{ new_plan }} takes effect {{ effective_date }}.",
    },
    # Cancelled
    {
        "notification_type": "subscription.cancelled",
        "channel": "email", "language": "en",
        "subject_template": "Riviwa subscription cancelled — access ends {{ access_end_date }}",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Your <strong>{{ plan_name }}</strong> subscription for <strong>{{ org_name }}</strong> "
            "has been cancelled.</p>"
            "<p>You will retain access until <strong>{{ access_end_date }}</strong>. "
            "After that date, your account will move to the free tier.</p>"
            "<p>We're sorry to see you go. If you change your mind, you can resubscribe at any time.</p>"
        ),
    },
    {
        "notification_type": "subscription.cancelled",
        "channel": "in_app", "language": "en",
        "title_template": "Subscription cancelled",
        "body_template": "{{ plan_name }} cancelled. Access continues until {{ access_end_date }}.",
    },
    # Paused
    {
        "notification_type": "subscription.paused",
        "channel": "email", "language": "en",
        "subject_template": "Riviwa subscription paused — resumes {{ resume_date }}",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Your <strong>{{ plan_name }}</strong> subscription for <strong>{{ org_name }}</strong> "
            "has been paused for {{ pause_months }} month(s).</p>"
            "<p>Billing is paused and your subscription will automatically resume on "
            "<strong>{{ resume_date }}</strong>.</p>"
        ),
    },
    {
        "notification_type": "subscription.paused",
        "channel": "in_app", "language": "en",
        "title_template": "Subscription paused",
        "body_template": "{{ plan_name }} paused for {{ pause_months }} month(s). Resumes {{ resume_date }}.",
    },
    # Resumed
    {
        "notification_type": "subscription.resumed",
        "channel": "email", "language": "en",
        "subject_template": "Riviwa subscription resumed — {{ plan_name }} is active again",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Your <strong>{{ plan_name }}</strong> subscription for <strong>{{ org_name }}</strong> "
            "has been resumed. All features are active and billing resumes normally.</p>"
        ),
    },
    {
        "notification_type": "subscription.resumed",
        "channel": "in_app", "language": "en",
        "title_template": "Subscription resumed",
        "body_template": "{{ plan_name }} is active again. Billing resumes on {{ next_renewal_date }}.",
    },
    # Payment failed
    {
        "notification_type": "subscription.payment_failed",
        "channel": "email", "language": "en",
        "subject_template": "ACTION REQUIRED: Riviwa subscription payment failed — {{ invoice_number }}",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p><strong>We could not process your payment</strong> for the <strong>{{ plan_name }}</strong> "
            "subscription of <strong>{{ org_name }}</strong>.</p>"
            "<ul>"
            "<li><strong>Invoice:</strong> {{ invoice_number }}</li>"
            "<li><strong>Amount:</strong> ${{ amount_usd }}</li>"
            "<li><strong>Reason:</strong> {{ failure_reason }}</li>"
            "</ul>"
            "<p>Please update your payment method to avoid service interruption. "
            "We will retry automatically in 3 days.</p>"
        ),
    },
    {
        "notification_type": "subscription.payment_failed",
        "channel": "in_app", "language": "en",
        "title_template": "Payment failed — action required",
        "body_template": "Payment of ${{ amount_usd }} for {{ plan_name }} failed. Update your payment method to avoid interruption.",
    },
    # Past due
    {
        "notification_type": "subscription.past_due",
        "channel": "email", "language": "en",
        "subject_template": "URGENT: Riviwa subscription past due — service at risk",
        "body_template": (
            "<p>Hi {{ owner_name }},</p>"
            "<p>Your <strong>{{ plan_name }}</strong> subscription for <strong>{{ org_name }}</strong> "
            "is now <strong>past due</strong>. We have been unable to collect payment.</p>"
            "<p>Please update your payment method immediately to restore full service. "
            "Your account will be downgraded if payment is not received within 7 days.</p>"
        ),
    },
    {
        "notification_type": "subscription.past_due",
        "channel": "in_app", "language": "en",
        "title_template": "Subscription past due — urgent",
        "body_template": "{{ plan_name }} is past due. Update your payment method to avoid service interruption.",
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
