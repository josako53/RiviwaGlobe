from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from core.config import settings
from events.producer import WaitingProducer
from models.org_cache import OrgCache
from waiting_redis.client import WaitingRedis

log = structlog.get_logger(__name__)


async def recalculate_etas(db_factory: Callable, redis: WaitingRedis, producer: WaitingProducer) -> None:
    """
    For each active service point: compute ETA per ticket from queue position × avg_service_minutes.
    Store in Redis. If ETA ≤ threshold and not yet alerted, send ETA notification.
    """
    threshold = settings.ETA_ALERT_THRESHOLD_MINUTES
    try:
        async with db_factory() as db:
            from repositories.service_point_repository import ServicePointRepository
            from repositories.queue_ticket_repository import QueueTicketRepository
            from models.queue_ticket import TicketStatus

            result = await db.execute(
                select(OrgCache).where(OrgCache.is_active == True)  # noqa: E712
            )
            orgs = list(result.scalars().all())

            for org in orgs:
                sp_repo = ServicePointRepository(db)
                ticket_repo = QueueTicketRepository(db)
                service_points = await sp_repo.list_by_org(org.org_id, active_only=True)

                for sp in service_points:
                    # Get ordered waiting tickets from DB (same order as Redis)
                    waiting = await ticket_repo.get_tickets_in_queue(sp.id)
                    if not waiting:
                        continue
                    avg_minutes = sp.avg_service_minutes or 5.0

                    for position_0, ticket in enumerate(waiting):
                        position = position_0 + 1
                        eta = position * avg_minutes
                        await redis.set_eta(ticket.id, eta, ttl_seconds=120)

                        if eta <= threshold and ticket.phone_number:
                            alerted = await redis.is_alerted(ticket.id)
                            if not alerted:
                                await redis.mark_alerted(ticket.id, ttl_seconds=600)
                                await producer.eta_alert_15min(
                                    ticket_id=ticket.id,
                                    ticket_number=ticket.ticket_number,
                                    org_id=ticket.org_id,
                                    phone_number=ticket.phone_number,
                                    service_point_name=sp.name,
                                    eta_minutes=eta,
                                )
                                log.info("waiting.scheduler.eta_alert_sent",
                                         ticket=ticket.ticket_number, eta=eta)
    except Exception as exc:
        log.error("waiting.scheduler.eta_job_failed", error=str(exc), exc_info=exc)


async def prune_stale_sessions(db_factory: Callable) -> None:
    """Close StaffSessions open for more than 24 hours (guards against crash-left sessions)."""
    try:
        async with db_factory() as db:
            from models.staff_session import StaffSession
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            result = await db.execute(
                select(StaffSession).where(
                    StaffSession.is_active == True,  # noqa: E712
                    StaffSession.opened_at <= cutoff,
                )
            )
            stale = list(result.scalars().all())
            now = datetime.now(timezone.utc)
            for session in stale:
                session.is_active = False
                session.closed_at = now
                db.add(session)
                log.warning("waiting.scheduler.stale_session_closed",
                            session_id=str(session.id), counter_id=str(session.staff_counter_id))
            if stale:
                await db.commit()
                log.info("waiting.scheduler.stale_sessions_pruned", count=len(stale))
    except Exception as exc:
        log.error("waiting.scheduler.prune_job_failed", error=str(exc), exc_info=exc)


def create_scheduler(db_factory: Callable, redis: WaitingRedis, producer: WaitingProducer) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        recalculate_etas,
        trigger=IntervalTrigger(seconds=settings.SCHEDULER_ETA_INTERVAL_SECONDS),
        kwargs={"db_factory": db_factory, "redis": redis, "producer": producer},
        id="recalculate_etas",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=15,
    )

    scheduler.add_job(
        prune_stale_sessions,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        kwargs={"db_factory": db_factory},
        id="prune_stale_sessions",
        max_instances=1,
        coalesce=True,
    )

    return scheduler
