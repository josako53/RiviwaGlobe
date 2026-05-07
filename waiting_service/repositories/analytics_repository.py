from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.queue_ticket import QueueTicket, TicketStatus
from models.queue_ticket_stage import QueueTicketStage, StageStatus
from models.service_point import ServicePoint

log = structlog.get_logger(__name__)


class AnalyticsRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_service_point_stats(self, org_id: uuid.UUID) -> List[dict]:
        sp_result = await self.db.execute(
            select(ServicePoint).where(
                ServicePoint.org_id == org_id,
                ServicePoint.is_active == True,  # noqa: E712
            )
        )
        service_points = list(sp_result.scalars().all())

        now = datetime.now(timezone.utc)
        today = now.date()
        seven_days_ago = now - timedelta(days=7)

        stats = []
        for sp in service_points:
            waiting_count = await self.db.scalar(
                select(func.count(QueueTicket.id)).where(
                    QueueTicket.current_service_point_id == sp.id,
                    QueueTicket.status == TicketStatus.WAITING,
                )
            ) or 0

            attending_count = await self.db.scalar(
                select(func.count(QueueTicket.id)).where(
                    QueueTicket.current_service_point_id == sp.id,
                    QueueTicket.status == TicketStatus.ATTENDING,
                )
            ) or 0

            avg_wait_raw = await self.db.scalar(
                select(func.avg(QueueTicketStage.wait_duration_seconds)).where(
                    QueueTicketStage.service_point_id == sp.id,
                    QueueTicketStage.status == StageStatus.FINISHED,
                    QueueTicketStage.finished_at >= seven_days_ago,
                    QueueTicketStage.wait_duration_seconds.is_not(None),
                )
            )

            avg_svc_raw = await self.db.scalar(
                select(func.avg(QueueTicketStage.service_duration_seconds)).where(
                    QueueTicketStage.service_point_id == sp.id,
                    QueueTicketStage.status == StageStatus.FINISHED,
                    QueueTicketStage.finished_at >= seven_days_ago,
                    QueueTicketStage.service_duration_seconds.is_not(None),
                )
            )

            throughput_today = await self.db.scalar(
                select(func.count(QueueTicketStage.id)).where(
                    QueueTicketStage.service_point_id == sp.id,
                    QueueTicketStage.status == StageStatus.FINISHED,
                    func.date(QueueTicketStage.finished_at) == today,
                )
            ) or 0

            stats.append({
                "service_point_id":    sp.id,
                "service_point_name":  sp.name,
                "point_type":          sp.point_type,
                "waiting_count":       waiting_count,
                "attending_count":     attending_count,
                "avg_wait_seconds":    float(avg_wait_raw) if avg_wait_raw is not None else None,
                "avg_service_seconds": float(avg_svc_raw) if avg_svc_raw is not None else None,
                "throughput_today":    throughput_today,
            })

        return stats

    async def get_total_completed_today(self, org_id: uuid.UUID) -> int:
        today = datetime.now(timezone.utc).date()
        return await self.db.scalar(
            select(func.count(QueueTicket.id)).where(
                QueueTicket.org_id == org_id,
                QueueTicket.status == TicketStatus.COMPLETED,
                func.date(QueueTicket.completed_at) == today,
            )
        ) or 0
