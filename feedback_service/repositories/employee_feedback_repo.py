"""repositories/employee_feedback_repo.py — CRUD for EmployeeFeedback."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.employee_feedback import EmployeeFeedback

log = structlog.get_logger(__name__)


class EmployeeFeedbackRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_tracking_number(self) -> str:
        year = datetime.utcnow().year
        result = await self.db.execute(
            select(func.count(EmployeeFeedback.id)).where(
                func.extract("year", EmployeeFeedback.submitted_at) == year
            )
        )
        count = (result.scalar() or 0) + 1
        return f"EF-{year}-{count:04d}"

    async def create(self, ef: EmployeeFeedback) -> EmployeeFeedback:
        self.db.add(ef)
        await self.db.flush()
        await self.db.refresh(ef)
        return ef

    async def get_by_id(
        self,
        ef_id: uuid.UUID,
        org_id: Optional[uuid.UUID] = None,
    ) -> Optional[EmployeeFeedback]:
        q = select(EmployeeFeedback).where(EmployeeFeedback.id == ef_id)
        if org_id:
            q = q.where(EmployeeFeedback.org_id == org_id)
        result = await self.db.execute(q)
        return result.scalars().first()

    async def list_for_org(
        self,
        org_id: uuid.UUID,
        feedback_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        is_anonymous: Optional[bool] = None,
        branch_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, List[EmployeeFeedback]]:
        q = select(EmployeeFeedback).where(EmployeeFeedback.org_id == org_id)
        if feedback_type:
            q = q.where(EmployeeFeedback.feedback_type == feedback_type)
        if category:
            q = q.where(EmployeeFeedback.category == category)
        if status:
            q = q.where(EmployeeFeedback.status == status)
        if is_anonymous is not None:
            q = q.where(EmployeeFeedback.is_anonymous == is_anonymous)
        if branch_id:
            q = q.where(EmployeeFeedback.branch_id == branch_id)
        if department_id:
            q = q.where(EmployeeFeedback.department_id == department_id)

        count_q = select(func.count()).select_from(q.subquery())
        total_result = await self.db.execute(count_q)
        total = total_result.scalar() or 0

        q = q.order_by(EmployeeFeedback.submitted_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return total, list(result.scalars().all())

    async def list_for_employee(
        self,
        employee_user_id: uuid.UUID,
        org_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, List[EmployeeFeedback]]:
        q = select(EmployeeFeedback).where(
            EmployeeFeedback.employee_user_id == employee_user_id,
            EmployeeFeedback.org_id == org_id,
        )
        count_q = select(func.count()).select_from(q.subquery())
        total_result = await self.db.execute(count_q)
        total = total_result.scalar() or 0

        q = q.order_by(EmployeeFeedback.submitted_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return total, list(result.scalars().all())

    async def save(self, ef: EmployeeFeedback) -> EmployeeFeedback:
        self.db.add(ef)
        await self.db.flush()
        await self.db.refresh(ef)
        return ef
