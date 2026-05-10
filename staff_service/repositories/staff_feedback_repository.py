"""repositories/staff_feedback_repository.py — StaffFeedback DB ops."""
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import case, func, select
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
        """
        Analytics using Riviwa feedback vocabulary.
        Performance metric: applause_rate = applause / total * 100.
        """
        agg = await self.db.execute(
            select(
                func.count(StaffFeedback.id).label("total"),
                func.sum(case((StaffFeedback.feedback_type == "grievance", 1), else_=0)).label("grievances"),
                func.sum(case((StaffFeedback.feedback_type == "suggestion", 1), else_=0)).label("suggestions"),
                func.sum(case((StaffFeedback.feedback_type == "applause", 1), else_=0)).label("applause"),
                func.sum(case((StaffFeedback.feedback_type == "inquiry", 1), else_=0)).label("inquiries"),
            ).where(StaffFeedback.org_id == org_id)
        )
        row = agg.one()
        total = row.total or 0
        grievances = row.grievances or 0
        suggestions = row.suggestions or 0
        applause = row.applause or 0
        inquiries = row.inquiries or 0
        applause_rate = round(applause / total * 100, 1) if total else None

        # Per-staff breakdown — applause_rate is the performance metric
        by_staff_rows = await self.db.execute(
            select(
                StaffFeedback.staff_id,
                func.count(StaffFeedback.id).label("total"),
                func.sum(case((StaffFeedback.feedback_type == "grievance", 1), else_=0)).label("grievances"),
                func.sum(case((StaffFeedback.feedback_type == "suggestion", 1), else_=0)).label("suggestions"),
                func.sum(case((StaffFeedback.feedback_type == "applause", 1), else_=0)).label("applause"),
                func.sum(case((StaffFeedback.feedback_type == "inquiry", 1), else_=0)).label("inquiries"),
            ).where(StaffFeedback.org_id == org_id)
            .group_by(StaffFeedback.staff_id)
            .order_by(func.count(StaffFeedback.id).desc())
            .limit(20)
        )
        by_staff = []
        for r in by_staff_rows.all():
            t = r.total or 0
            a = r.applause or 0
            by_staff.append({
                "staff_id": str(r.staff_id),
                "total": t,
                "grievances": r.grievances or 0,
                "suggestions": r.suggestions or 0,
                "applause": a,
                "inquiries": r.inquiries or 0,
                "applause_rate": round(a / t * 100, 1) if t else None,
            })

        return {
            "total": total,
            "applause_rate": applause_rate,
            "by_type": {
                "grievance": grievances,
                "suggestion": suggestions,
                "applause": applause,
                "inquiry": inquiries,
            },
            "by_staff": by_staff,
        }
