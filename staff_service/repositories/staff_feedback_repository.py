"""repositories/staff_feedback_repository.py — StaffFeedback DB ops."""
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.staff_feedback import StaffFeedback


class StaffFeedbackRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, feedback: StaffFeedback) -> StaffFeedback:
        self.db.add(feedback)
        await self.db.flush()
        return feedback

    async def get_by_id(self, feedback_id: UUID) -> Optional[StaffFeedback]:
        return await self.db.get(StaffFeedback, feedback_id)

    async def list_by_org(
        self,
        org_id: UUID,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[StaffFeedback], int]:
        q = select(StaffFeedback).where(StaffFeedback.org_id == org_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(StaffFeedback.created_at.desc()).offset((page - 1) * size).limit(size)
        rows = (await self.db.execute(q)).scalars().all()
        return rows, total

    async def stats_by_org(self, org_id: UUID) -> dict:
        """Analytics: avg_rating, total, by_staff (top 10), by_rating."""
        agg = await self.db.execute(
            select(
                func.count(StaffFeedback.id).label("total"),
                func.avg(StaffFeedback.rating).label("avg_rating"),
            ).where(StaffFeedback.org_id == org_id)
        )
        row = agg.one()
        total = row.total or 0
        avg_rating = float(row.avg_rating) if row.avg_rating else None

        # by_staff top 10
        by_staff_rows = await self.db.execute(
            select(
                StaffFeedback.staff_id,
                func.count(StaffFeedback.id).label("cnt"),
                func.avg(StaffFeedback.rating).label("avg"),
            ).where(StaffFeedback.org_id == org_id)
            .group_by(StaffFeedback.staff_id)
            .order_by(func.count(StaffFeedback.id).desc())
            .limit(10)
        )
        by_staff = [
            {"staff_id": str(r.staff_id), "feedback_count": r.cnt, "avg_rating": float(r.avg) if r.avg else None}
            for r in by_staff_rows.all()
        ]

        # by_rating 1-5
        by_rating_rows = await self.db.execute(
            select(
                StaffFeedback.rating,
                func.count(StaffFeedback.id).label("cnt"),
            ).where(StaffFeedback.org_id == org_id)
            .group_by(StaffFeedback.rating)
            .order_by(StaffFeedback.rating)
        )
        by_rating = {r.rating: r.cnt for r in by_rating_rows.all()}

        return {
            "total": total,
            "avg_rating": avg_rating,
            "by_staff": by_staff,
            "by_rating": by_rating,
        }
