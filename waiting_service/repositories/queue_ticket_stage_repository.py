from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.queue_ticket_stage import QueueTicketStage, StageStatus

log = structlog.get_logger(__name__)


class QueueTicketStageRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> QueueTicketStage:
        stage = QueueTicketStage(**data)
        self.db.add(stage)
        await self.db.flush()
        await self.db.refresh(stage)
        return stage

    async def update(self, stage: QueueTicketStage, data: dict) -> QueueTicketStage:
        for k, v in data.items():
            setattr(stage, k, v)
        self.db.add(stage)
        await self.db.flush()
        await self.db.refresh(stage)
        return stage

    async def get_by_id(self, stage_id: uuid.UUID) -> Optional[QueueTicketStage]:
        result = await self.db.execute(
            select(QueueTicketStage).where(QueueTicketStage.id == stage_id)
        )
        return result.scalar_one_or_none()

    async def get_active_stage(self, ticket_id: uuid.UUID) -> Optional[QueueTicketStage]:
        result = await self.db.execute(
            select(QueueTicketStage).where(
                QueueTicketStage.ticket_id == ticket_id,
                QueueTicketStage.status.in_([StageStatus.WAITING, StageStatus.ATTENDING]),
            ).order_by(QueueTicketStage.step_order.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_ticket(self, ticket_id: uuid.UUID) -> List[QueueTicketStage]:
        result = await self.db.execute(
            select(QueueTicketStage).where(QueueTicketStage.ticket_id == ticket_id)
            .order_by(QueueTicketStage.step_order.asc())
        )
        return list(result.scalars().all())

    async def get_avg_service_seconds_for_point(
        self, service_point_id: uuid.UUID, last_n_days: int = 7
    ) -> Optional[float]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=last_n_days)
        result = await self.db.execute(
            select(func.avg(QueueTicketStage.service_duration_seconds)).where(
                QueueTicketStage.service_point_id == service_point_id,
                QueueTicketStage.status == StageStatus.FINISHED,
                QueueTicketStage.finished_at >= cutoff,
                QueueTicketStage.service_duration_seconds.is_not(None),
            )
        )
        avg = result.scalar_one_or_none()
        return float(avg) if avg is not None else None

    async def get_avg_wait_seconds_for_point(
        self, service_point_id: uuid.UUID, last_n_days: int = 7
    ) -> Optional[float]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=last_n_days)
        result = await self.db.execute(
            select(func.avg(QueueTicketStage.wait_duration_seconds)).where(
                QueueTicketStage.service_point_id == service_point_id,
                QueueTicketStage.status == StageStatus.FINISHED,
                QueueTicketStage.finished_at >= cutoff,
                QueueTicketStage.wait_duration_seconds.is_not(None),
            )
        )
        avg = result.scalar_one_or_none()
        return float(avg) if avg is not None else None

    async def count_served_today(self, service_point_id: uuid.UUID) -> int:
        today = datetime.now(timezone.utc).date()
        result = await self.db.scalar(
            select(func.count(QueueTicketStage.id)).where(
                QueueTicketStage.service_point_id == service_point_id,
                QueueTicketStage.status == StageStatus.FINISHED,
                func.date(QueueTicketStage.finished_at) == today,
            )
        ) or 0
        return result
