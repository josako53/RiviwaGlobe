"""
repositories/channel_repository.py
────────────────────────────────────────────────────────────────────────────
All database operations for ChannelSession.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.feedback import ChannelSession, FeedbackCategoryDef, CategoryStatus, Feedback
from sqlalchemy import or_


class ChannelRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[ChannelSession]:
        result = await self.db.execute(
            select(ChannelSession).where(ChannelSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        project_id: Optional[uuid.UUID] = None,
        status:     Optional[str]       = None,
        channel:    Optional[str]       = None,
        skip:  int = 0,
        limit: int = 50,
    ) -> list[ChannelSession]:
        q = select(ChannelSession)
        if project_id: q = q.where(ChannelSession.project_id == project_id)
        if status:     q = q.where(ChannelSession.status     == status)
        if channel:    q = q.where(ChannelSession.channel    == channel)
        q = q.offset(skip).limit(limit).order_by(ChannelSession.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create(self, session: ChannelSession) -> ChannelSession:
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def save(self, session: ChannelSession) -> None:
        self.db.add(session)

    async def count_feedback_for_project(self, project_id: uuid.UUID) -> int:
        return await self.db.scalar(
            select(func.count(Feedback.id)).where(Feedback.project_id == project_id)
        ) or 0

    async def list_active_categories(
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
