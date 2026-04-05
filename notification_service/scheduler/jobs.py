# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  scheduler/jobs.py
# ───────────────────────────────────────────────────────────────────────────
"""
scheduler/jobs.py
═══════════════════════════════════════════════════════════════════════════════
APScheduler configuration for reminder and maintenance jobs.

Jobs:
  ┌──────────────────────────────────────────────────────┬──────────────────┐
  │ Job                                                  │ Interval         │
  ├──────────────────────────────────────────────────────┼──────────────────┤
  │ dispatch_scheduled_notifications                     │ Every 1 minute   │
  │   → Sends notifications whose scheduled_at is due    │                  │
  ├──────────────────────────────────────────────────────┼──────────────────┤
  │ retry_failed_deliveries                              │ Every 5 minutes  │
  │   → Re-attempts failed deliveries with backoff       │                  │
  ├──────────────────────────────────────────────────────┼──────────────────┤
  │ prune_stale_devices                                  │ Daily at 02:00   │
  │   → Removes push tokens inactive for 90+ days        │                  │
  └──────────────────────────────────────────────────────┴──────────────────┘

The scheduler is started in main.py lifespan and stopped on shutdown.
Note: APScheduler runs in the same process as FastAPI.  Jobs share the
asyncio event loop.  Each job creates its own DB session.
"""
from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from db.session import AsyncSessionLocal
from services.delivery_service import DeliveryService

log = structlog.get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


# ── Job functions ─────────────────────────────────────────────────────────────

async def _job_dispatch_scheduled() -> None:
    """Dispatch any scheduled notifications that are now due."""
    async with AsyncSessionLocal() as db:
        svc = DeliveryService(db)
        count = await svc.dispatch_scheduled()
        if count:
            log.info("scheduler.job.dispatch_scheduled", dispatched=count)


async def _job_retry_failed() -> None:
    """Re-attempt failed deliveries within retry policy."""
    async with AsyncSessionLocal() as db:
        svc = DeliveryService(db)
        count = await svc.retry_failed_deliveries()
        if count:
            log.info("scheduler.job.retry_failed", retried=count)


async def _job_prune_stale_devices() -> None:
    """Mark push devices inactive if last_active_at > 90 days ago."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import update
    from models.notification import NotificationDevice

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(NotificationDevice)
            .where(
                NotificationDevice.is_active      == True,
                NotificationDevice.last_active_at <= cutoff,
            )
            .values(is_active=False)
        )
        await db.commit()
        pruned = result.rowcount
        if pruned:
            log.info("scheduler.job.prune_stale_devices", pruned=pruned)


async def _job_prune_old_notifications() -> None:
    """
    Archive read in_app notifications older than 90 days.
    Keeps the notifications table lean.
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import delete, and_
    from models.notification import NotificationDelivery, Notification, ChannelEnum, DeliveryStatusEnum

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    async with AsyncSessionLocal() as db:
        # Delete deliveries for old read in_app notifications
        result = await db.execute(
            delete(NotificationDelivery).where(
                NotificationDelivery.channel == ChannelEnum.IN_APP,
                NotificationDelivery.status  == DeliveryStatusEnum.READ,
                NotificationDelivery.read_at <= cutoff,
            )
        )
        await db.commit()
        pruned = result.rowcount
        if pruned:
            log.info("scheduler.job.prune_old_notifications", pruned=pruned)


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")

    # Dispatch scheduled notifications every 1 minute
    _scheduler.add_job(
        _job_dispatch_scheduled,
        trigger=IntervalTrigger(minutes=1),
        id="dispatch_scheduled",
        name="Dispatch due scheduled notifications",
        max_instances=1,
        misfire_grace_time=30,
    )

    # Retry failed deliveries every 5 minutes
    _scheduler.add_job(
        _job_retry_failed,
        trigger=IntervalTrigger(minutes=5),
        id="retry_failed",
        name="Retry failed notification deliveries",
        max_instances=1,
        misfire_grace_time=60,
    )

    # Prune stale push devices daily at 02:00 UTC
    _scheduler.add_job(
        _job_prune_stale_devices,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="prune_stale_devices",
        name="Prune inactive push device tokens",
        max_instances=1,
    )

    # Prune old read in-app notifications daily at 03:00 UTC
    _scheduler.add_job(
        _job_prune_old_notifications,
        trigger=CronTrigger(hour=3, minute=0, timezone="UTC"),
        id="prune_old_notifications",
        name="Prune read in-app notifications older than 90 days",
        max_instances=1,
    )

    return _scheduler


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler