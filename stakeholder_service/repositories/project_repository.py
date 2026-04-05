"""
repositories/project_repository.py
────────────────────────────────────────────────────────────────────────────
All database operations for ProjectCache reads and aggregate counts.
Projects are read-only in stakeholder_service — they are synced from
auth_service via Kafka and never mutated here.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.communication import CommunicationRecord, FocalPerson
from models.engagement import ActivityStatus, EngagementActivity
from models.project import ProjectCache, ProjectStatus
from models.stakeholder import StakeholderProject


class ProjectRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, project_id: uuid.UUID) -> Optional[ProjectCache]:
        result = await self.db.execute(
            select(ProjectCache).where(ProjectCache.id == project_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        status: Optional[ProjectStatus] = None,
        org_id: Optional[uuid.UUID]     = None,
        lga:    Optional[str]           = None,
        skip:   int                     = 0,
        limit:  int                     = 50,
    ) -> list[ProjectCache]:
        q = select(ProjectCache)
        if status: q = q.where(ProjectCache.status == status)
        if org_id: q = q.where(ProjectCache.organisation_id == org_id)
        if lga:    q = q.where(ProjectCache.primary_lga.ilike(f"%{lga}%"))
        q = q.offset(skip).limit(limit).order_by(ProjectCache.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def engagement_counts(self, project_id: uuid.UUID) -> dict:
        """Return all engagement-related counts for a project in one method."""
        stakeholder_count = await self.db.scalar(
            select(func.count(StakeholderProject.id))
            .where(StakeholderProject.project_id == project_id)
        ) or 0

        activity_count = await self.db.scalar(
            select(func.count(EngagementActivity.id))
            .where(EngagementActivity.project_id == project_id)
        ) or 0

        conducted_count = await self.db.scalar(
            select(func.count(EngagementActivity.id))
            .where(
                EngagementActivity.project_id == project_id,
                EngagementActivity.status == ActivityStatus.CONDUCTED,
            )
        ) or 0

        comm_count = await self.db.scalar(
            select(func.count(CommunicationRecord.id))
            .where(CommunicationRecord.project_id == project_id)
        ) or 0

        focal_count = await self.db.scalar(
            select(func.count(FocalPerson.id))
            .where(
                FocalPerson.project_id == project_id,
                FocalPerson.is_active.is_(True),
            )
        ) or 0

        return {
            "stakeholders":         int(stakeholder_count),
            "activities_total":     int(activity_count),
            "activities_conducted": int(conducted_count),
            "communications":       int(comm_count),
            "focal_persons":        int(focal_count),
        }
