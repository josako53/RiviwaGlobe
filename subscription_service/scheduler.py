"""scheduler.py — APScheduler jobs for subscription reminders and dunning."""
from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from db.session import AsyncSessionLocal

log = structlog.get_logger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def _job_renewal_reminders() -> None:
    """
    Daily at 08:00 UTC.
    Send renewal reminder emails/in-app notifications to org owners
    whose subscription renews in exactly 7, 3, or 1 days.
    Industry standard: 7d ahead (planning), 3d (urgency), 1d (final).
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from models.subscription import Plan, Subscription, SubscriptionStatus
    import services.notification_client as notif

    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        for days in (7, 3, 1):
            window_start = now + timedelta(days=days) - timedelta(hours=12)
            window_end   = now + timedelta(days=days) + timedelta(hours=12)
            rows = (await db.execute(
                select(Subscription, Plan)
                .join(Plan, Plan.id == Subscription.plan_id)
                .where(
                    Subscription.status.in_([SubscriptionStatus.ACTIVE.value]),
                    Subscription.current_period_end >= window_start,
                    Subscription.current_period_end <= window_end,
                    Subscription.cancel_at_period_end == False,
                )
            )).all()
            for sub, plan in rows:
                notif.notify_renewal_reminder(
                    org_id=str(sub.org_id),
                    plan_name=plan.display_name,
                    days_left=days,
                    renewal_date=sub.current_period_end.strftime("%Y-%m-%d"),
                    amount_usd=str(sub.effective_monthly_usd),
                    billing_cycle=sub.billing_cycle,
                )
                log.info("scheduler.renewal_reminder_sent",
                         org_id=str(sub.org_id), days=days)


async def _job_trial_ending_reminders() -> None:
    """
    Daily at 08:00 UTC.
    Remind trial orgs whose trial ends in 7 or 3 days to subscribe.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from models.subscription import Plan, Subscription, SubscriptionStatus
    import services.notification_client as notif

    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        for days in (7, 3):
            window_start = now + timedelta(days=days) - timedelta(hours=12)
            window_end   = now + timedelta(days=days) + timedelta(hours=12)
            rows = (await db.execute(
                select(Subscription, Plan)
                .join(Plan, Plan.id == Subscription.plan_id)
                .where(
                    Subscription.status == SubscriptionStatus.TRIALING.value,
                    Subscription.trial_end >= window_start,
                    Subscription.trial_end <= window_end,
                )
            )).all()
            for sub, plan in rows:
                notif.notify_trial_ending(
                    org_id=str(sub.org_id),
                    plan_name=plan.display_name,
                    days_left=days,
                    trial_end_date=sub.trial_end.strftime("%Y-%m-%d"),
                    price_usd=str(plan.monthly_price_usd),
                    billing_cycle="monthly",
                )
                log.info("scheduler.trial_ending_reminder_sent",
                         org_id=str(sub.org_id), days=days)


async def _job_past_due_check() -> None:
    """
    Daily at 09:00 UTC.
    Mark subscriptions whose period_end has passed (without renewal) as PAST_DUE
    and send a past-due alert to the org owner.
    """
    from datetime import datetime
    from sqlalchemy import select
    from models.subscription import Plan, Subscription, SubscriptionStatus
    import services.notification_client as notif

    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Subscription, Plan)
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.current_period_end < now,
                Subscription.cancel_at_period_end == False,
            )
        )).all()
        for sub, plan in rows:
            sub.status = SubscriptionStatus.PAST_DUE.value
            notif.notify_past_due(org_id=str(sub.org_id), plan_name=plan.display_name)
            log.warning("scheduler.subscription_marked_past_due",
                        org_id=str(sub.org_id), plan=plan.slug)
        if rows:
            await db.commit()


def create_scheduler() -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")

    _scheduler.add_job(
        _job_renewal_reminders,
        trigger=CronTrigger(hour=8, minute=0, timezone="UTC"),
        id="renewal_reminders",
        name="Send renewal reminder notifications (7d/3d/1d)",
        max_instances=1,
    )

    _scheduler.add_job(
        _job_trial_ending_reminders,
        trigger=CronTrigger(hour=8, minute=5, timezone="UTC"),
        id="trial_ending_reminders",
        name="Send trial ending reminder notifications (7d/3d)",
        max_instances=1,
    )

    _scheduler.add_job(
        _job_past_due_check,
        trigger=CronTrigger(hour=9, minute=0, timezone="UTC"),
        id="past_due_check",
        name="Mark expired active subscriptions as past_due",
        max_instances=1,
    )

    return _scheduler


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler
