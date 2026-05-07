from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import StaffCounterNotFoundError
from models.staff_counter import StaffCounter

log = structlog.get_logger(__name__)


class StaffCounterRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> StaffCounter:
        counter = StaffCounter(**data)
        self.db.add(counter)
        await self.db.flush()
        await self.db.refresh(counter)
        return counter

    async def get_by_id(self, counter_id: uuid.UUID) -> Optional[StaffCounter]:
        result = await self.db.execute(select(StaffCounter).where(StaffCounter.id == counter_id))
        return result.scalar_one_or_none()

    async def get_by_id_or_404(self, counter_id: uuid.UUID) -> StaffCounter:
        counter = await self.get_by_id(counter_id)
        if counter is None:
            raise StaffCounterNotFoundError(f"Staff counter {counter_id} not found.")
        return counter

    async def list_by_service_point(self, service_point_id: uuid.UUID, active_only: bool = True) -> List[StaffCounter]:
        q = select(StaffCounter).where(StaffCounter.service_point_id == service_point_id)
        if active_only:
            q = q.where(StaffCounter.is_active == True)  # noqa: E712
        result = await self.db.execute(q.order_by(StaffCounter.code))
        return list(result.scalars().all())

    async def list_available_for_point(self, service_point_id: uuid.UUID) -> List[StaffCounter]:
        result = await self.db.execute(
            select(StaffCounter).where(
                StaffCounter.service_point_id == service_point_id,
                StaffCounter.is_active == True,          # noqa: E712
                StaffCounter.current_ticket_id == None,  # noqa: E711
            ).order_by(StaffCounter.code)
        )
        return list(result.scalars().all())

    async def assign_ticket(self, counter_id: uuid.UUID, ticket_id: uuid.UUID) -> StaffCounter:
        counter = await self.get_by_id_or_404(counter_id)
        counter.current_ticket_id = ticket_id
        self.db.add(counter)
        await self.db.flush()
        await self.db.refresh(counter)
        return counter

    async def release_ticket(self, counter_id: uuid.UUID) -> StaffCounter:
        counter = await self.get_by_id_or_404(counter_id)
        counter.current_ticket_id = None
        self.db.add(counter)
        await self.db.flush()
        await self.db.refresh(counter)
        return counter

    async def update(self, counter: StaffCounter, data: dict) -> StaffCounter:
        for k, v in data.items():
            setattr(counter, k, v)
        self.db.add(counter)
        await self.db.flush()
        await self.db.refresh(counter)
        return counter

    async def get_counter_serving_ticket(self, ticket_id: uuid.UUID) -> Optional[StaffCounter]:
        result = await self.db.execute(
            select(StaffCounter).where(StaffCounter.current_ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()
