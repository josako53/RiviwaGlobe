"""
repositories/category_repository.py
────────────────────────────────────────────────────────────────────────────
All database operations for FeedbackCategoryDef.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.feedback import (
    CategorySource,
    CategoryStatus,
    Feedback,
    FeedbackCategoryDef,
    FeedbackStatus,
)


class CategoryRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, cat_id: uuid.UUID) -> Optional[FeedbackCategoryDef]:
        result = await self.db.execute(
            select(FeedbackCategoryDef).where(FeedbackCategoryDef.id == cat_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(
        self, slug: str, project_id: Optional[uuid.UUID] = None
    ) -> Optional[FeedbackCategoryDef]:
        result = await self.db.execute(
            select(FeedbackCategoryDef).where(
                FeedbackCategoryDef.slug == slug,
                FeedbackCategoryDef.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        project_id:     Optional[uuid.UUID] = None,
        source:         Optional[str]       = None,
        status:         Optional[str]       = None,
        include_global: bool                = True,
        skip:  int = 0,
        limit: int = 100,
    ) -> list[FeedbackCategoryDef]:
        q = select(FeedbackCategoryDef)
        if project_id and include_global:
            q = q.where(or_(
                FeedbackCategoryDef.project_id == project_id,
                FeedbackCategoryDef.project_id.is_(None),
            ))
        elif project_id:
            q = q.where(FeedbackCategoryDef.project_id == project_id)
        else:
            q = q.where(FeedbackCategoryDef.project_id.is_(None))
        if source:
            q = q.where(FeedbackCategoryDef.source == source)
        if status:
            q = q.where(FeedbackCategoryDef.status == status)
        else:
            q = q.where(FeedbackCategoryDef.status == CategoryStatus.ACTIVE)
        result = await self.db.execute(
            q.order_by(FeedbackCategoryDef.display_order, FeedbackCategoryDef.name)
             .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def list_active_for_project(
        self, project_id: uuid.UUID
    ) -> list[FeedbackCategoryDef]:
        result = await self.db.execute(
            select(FeedbackCategoryDef).where(
                FeedbackCategoryDef.status == CategoryStatus.ACTIVE,
                or_(
                    FeedbackCategoryDef.project_id == project_id,
                    FeedbackCategoryDef.project_id.is_(None),
                ),
            ).order_by(FeedbackCategoryDef.display_order)
        )
        return list(result.scalars().all())

    async def create(self, cat: FeedbackCategoryDef) -> FeedbackCategoryDef:
        self.db.add(cat)
        await self.db.flush()
        await self.db.refresh(cat)
        return cat

    async def save(self, cat: FeedbackCategoryDef) -> None:
        self.db.add(cat)

    # ── Feedback counts for rate analytics ───────────────────────────────────

    async def count_feedback(
        self,
        category_id: uuid.UUID,
        from_dt,
        to_dt,
        project_id:                  Optional[uuid.UUID] = None,
        stage_id:                    Optional[uuid.UUID] = None,
        feedback_type:               Optional[str]       = None,
        status:                      Optional[str]       = None,
        priority:                    Optional[str]       = None,
        current_level:               Optional[str]       = None,
        lga:                         Optional[str]       = None,
        ward:                        Optional[str]       = None,
        is_anonymous:                Optional[bool]      = None,
        open_only:                   bool                = False,
        submitted_by_stakeholder_id: Optional[uuid.UUID] = None,
        assigned_committee_id:       Optional[uuid.UUID] = None,
        assigned_to_user_id:         Optional[uuid.UUID] = None,
    ) -> int:
        q = self._build_rate_query(
            category_id, from_dt, to_dt,
            project_id=project_id, stage_id=stage_id, feedback_type=feedback_type,
            status=status, priority=priority, current_level=current_level,
            lga=lga, ward=ward, is_anonymous=is_anonymous, open_only=open_only,
            submitted_by_stakeholder_id=submitted_by_stakeholder_id,
            assigned_committee_id=assigned_committee_id,
            assigned_to_user_id=assigned_to_user_id,
        )
        count_q = select(func.count()).select_from(q.subquery())
        return await self.db.scalar(count_q) or 0

    async def list_feedback_for_rate(
        self,
        category_id: uuid.UUID,
        from_dt,
        to_dt,
        **filters,
    ) -> list[Feedback]:
        q = self._build_rate_query(category_id, from_dt, to_dt, **filters)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    def _build_rate_query(
        self,
        category_id: uuid.UUID,
        from_dt,
        to_dt,
        project_id=None, stage_id=None, feedback_type=None, status=None,
        priority=None, current_level=None, lga=None, ward=None,
        is_anonymous=None, open_only=False,
        submitted_by_stakeholder_id=None, assigned_committee_id=None,
        assigned_to_user_id=None,
    ):
        q = select(Feedback).where(
            Feedback.category_def_id == category_id,
            Feedback.submitted_at   >= from_dt,
            Feedback.submitted_at   <= to_dt,
        )
        if project_id:                  q = q.where(Feedback.project_id                   == project_id)
        if stage_id:                    q = q.where(Feedback.stage_id                     == stage_id)
        if feedback_type:               q = q.where(Feedback.feedback_type                == feedback_type)
        if status:                      q = q.where(Feedback.status                       == status)
        if priority:                    q = q.where(Feedback.priority                     == priority)
        if current_level:               q = q.where(Feedback.current_level                == current_level)
        if lga:                         q = q.where(Feedback.issue_lga.ilike(f"%{lga}%"))
        if ward:                        q = q.where(Feedback.issue_ward.ilike(f"%{ward}%"))
        if is_anonymous is not None:    q = q.where(Feedback.is_anonymous                 == is_anonymous)
        if submitted_by_stakeholder_id: q = q.where(Feedback.submitted_by_stakeholder_id  == submitted_by_stakeholder_id)
        if assigned_committee_id:       q = q.where(Feedback.assigned_committee_id        == assigned_committee_id)
        if assigned_to_user_id:         q = q.where(Feedback.assigned_to_user_id          == assigned_to_user_id)
        if open_only:
            q = q.where(Feedback.status.not_in([
                FeedbackStatus.CLOSED, FeedbackStatus.DISMISSED, FeedbackStatus.RESOLVED,
            ]))
        return q

    async def count_feedback_in_category_for_project(
        self,
        category_id: uuid.UUID,
        project_id:  uuid.UUID,
        from_dt,
        to_dt,
        feedback_type: Optional[str] = None,
    ) -> int:
        q = select(func.count(Feedback.id)).where(
            Feedback.category_def_id == category_id,
            Feedback.project_id      == project_id,
            Feedback.submitted_at   >= from_dt,
            Feedback.submitted_at   <= to_dt,
        )
        if feedback_type:
            q = q.where(Feedback.feedback_type == feedback_type)
        return await self.db.scalar(q) or 0

    async def count_open_feedback_in_category_for_project(
        self,
        category_id: uuid.UUID,
        project_id:  uuid.UUID,
        from_dt,
        to_dt,
        feedback_type: Optional[str] = None,
    ) -> int:
        q = select(func.count(Feedback.id)).where(
            Feedback.category_def_id == category_id,
            Feedback.project_id      == project_id,
            Feedback.submitted_at   >= from_dt,
            Feedback.submitted_at   <= to_dt,
            Feedback.status.not_in([
                FeedbackStatus.CLOSED, FeedbackStatus.DISMISSED, FeedbackStatus.RESOLVED,
            ]),
        )
        if feedback_type:
            q = q.where(Feedback.feedback_type == feedback_type)
        return await self.db.scalar(q) or 0

    async def retag_feedback_from_category(
        self, category_id: uuid.UUID
    ) -> None:
        """Clear category_def_id on feedback pointing at a rejected category."""
        fb_result = await self.db.execute(
            select(Feedback).where(Feedback.category_def_id == category_id)
        )
        for fb in fb_result.scalars().all():
            fb.category_def_id = None
            self.db.add(fb)
