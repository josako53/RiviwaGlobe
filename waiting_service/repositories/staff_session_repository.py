from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import StaffSessionNotFoundError
from models.staff_session import StaffSession

log = structlog.get_logger(__name__)


class StaffSessionRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> StaffSession:
        session = StaffSession(**data)
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[StaffSession]:
        result = await self.db.execute(select(StaffSession).where(StaffSession.id == session_id))
        return result.scalar_one_or_none()

    async def get_active_for_counter(self, counter_id: uuid.UUID) -> Optional[StaffSession]:
        result = await self.db.execute(
            select(StaffSession).where(
                StaffSession.staff_counter_id == counter_id,
                StaffSession.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_active_for_staff(self, staff_user_id: uuid.UUID) -> Optional[StaffSession]:
        result = await self.db.execute(
            select(StaffSession).where(
                StaffSession.staff_user_id == staff_user_id,
                StaffSession.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def close(self, session: StaffSession, closed_at: datetime) -> StaffSession:
        session.closed_at = closed_at
        session.is_active = False
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def update_stats(self, session: StaffSession, service_seconds: float) -> StaffSession:
        session.tickets_served = (session.tickets_served or 0) + 1
        n = session.tickets_served
        old_avg = session.avg_service_seconds or 0.0
        session.avg_service_seconds = (old_avg * (n - 1) + service_seconds) / n
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def list_by_org(
        self, org_id: uuid.UUID, is_active: Optional[bool], skip: int, limit: int
    ) -> List[StaffSession]:
        q = select(StaffSession).where(StaffSession.org_id == org_id)
        if is_active is not None:
            q = q.where(StaffSession.is_active == is_active)
        result = await self.db.execute(q.order_by(StaffSession.opened_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all())
