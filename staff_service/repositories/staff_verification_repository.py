"""repositories/staff_verification_repository.py — StaffVerificationEvent DB ops."""
from __future__ import annotations

import datetime as dt
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.staff_verification import StaffVerificationEvent


class StaffVerificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, event: StaffVerificationEvent) -> StaffVerificationEvent:
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_by_id(self, event_id: UUID) -> Optional[StaffVerificationEvent]:
        return await self.db.get(StaffVerificationEvent, event_id)

    async def list_by_org(
        self,
        org_id: UUID,
        result: Optional[str] = None,
        from_date: Optional[dt.datetime] = None,
        to_date: Optional[dt.datetime] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[StaffVerificationEvent], int]:
        q = select(StaffVerificationEvent).where(StaffVerificationEvent.org_id == org_id)
        if result:
            q = q.where(StaffVerificationEvent.result == result.upper())
        if from_date:
            q = q.where(StaffVerificationEvent.verified_at >= from_date)
        if to_date:
            q = q.where(StaffVerificationEvent.verified_at <= to_date)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(StaffVerificationEvent.verified_at.desc()).offset((page - 1) * size).limit(size)
        rows = (await self.db.execute(q)).scalars().all()
        return rows, total

    async def stats_by_org(self, org_id: UUID) -> dict:
        """Count verifications by result for analytics."""
        result = await self.db.execute(
            select(
                StaffVerificationEvent.result,
                func.count(StaffVerificationEvent.id).label("cnt"),
            ).where(
                StaffVerificationEvent.org_id == org_id
            ).group_by(StaffVerificationEvent.result)
        )
        rows = result.all()
        by_result = {r.result: r.cnt for r in rows}
        total = sum(by_result.values())

        # By day (last 30 days)
        cutoff = dt.datetime.utcnow() - dt.timedelta(days=30)
        daily = await self.db.execute(
            select(
                func.date_trunc("day", StaffVerificationEvent.verified_at).label("day"),
                func.count(StaffVerificationEvent.id).label("cnt"),
            ).where(
                StaffVerificationEvent.org_id == org_id,
                StaffVerificationEvent.verified_at >= cutoff,
            ).group_by("day").order_by("day")
        )
        by_day = [
            {"date": str(r.day.date()), "count": r.cnt}
            for r in daily.all()
        ]
        return {"total": total, "by_result": by_result, "by_day": by_day}
