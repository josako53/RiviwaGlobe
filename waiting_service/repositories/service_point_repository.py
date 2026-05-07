from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ServicePointNotFoundError
from models.queue_ticket import QueueTicket, TicketStatus
from models.service_point import ServicePoint

log = structlog.get_logger(__name__)


class ServicePointRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> ServicePoint:
        point = ServicePoint(**data)
        self.db.add(point)
        await self.db.flush()
        await self.db.refresh(point)
        return point

    async def get_by_id(self, point_id: uuid.UUID) -> Optional[ServicePoint]:
        result = await self.db.execute(select(ServicePoint).where(ServicePoint.id == point_id))
        return result.scalar_one_or_none()

    async def get_by_id_or_404(self, point_id: uuid.UUID) -> ServicePoint:
        point = await self.get_by_id(point_id)
        if point is None:
            raise ServicePointNotFoundError(f"Service point {point_id} not found.")
        return point

    async def get_by_org_and_code(self, org_id: uuid.UUID, code: str) -> Optional[ServicePoint]:
        result = await self.db.execute(
            select(ServicePoint).where(ServicePoint.org_id == org_id, ServicePoint.code == code)
        )
        return result.scalar_one_or_none()

    async def list_by_org(self, org_id: uuid.UUID, active_only: bool = True) -> List[ServicePoint]:
        q = select(ServicePoint).where(ServicePoint.org_id == org_id)
        if active_only:
            q = q.where(ServicePoint.is_active == True)  # noqa: E712
        result = await self.db.execute(q.order_by(ServicePoint.name))
        return list(result.scalars().all())

    async def update(self, point: ServicePoint, data: dict) -> ServicePoint:
        for k, v in data.items():
            setattr(point, k, v)
        self.db.add(point)
        await self.db.flush()
        await self.db.refresh(point)
        return point

    async def has_active_tickets(self, point_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(QueueTicket.id).where(
                QueueTicket.current_service_point_id == point_id,
                QueueTicket.status.in_([TicketStatus.WAITING, TicketStatus.ATTENDING]),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
