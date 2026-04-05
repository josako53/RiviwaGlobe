"""
repositories/report_repository.py
────────────────────────────────────────────────────────────────────────────
Read-only aggregate queries for the reports endpoints.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.engagement import ActivityStatus, EngagementActivity
from models.stakeholder import Stakeholder, StakeholderProject


class ReportRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def activity_counts_by_stage(
        self, project_id: uuid.UUID
    ) -> list[tuple]:
        result = await self.db.execute(
            select(
                EngagementActivity.stage,
                EngagementActivity.status,
                func.count(EngagementActivity.id),
            )
            .where(EngagementActivity.project_id == project_id)
            .group_by(EngagementActivity.stage, EngagementActivity.status)
        )
        return result.all()

    async def activity_counts_by_lga(
        self, project_id: uuid.UUID
    ) -> list[tuple]:
        result = await self.db.execute(
            select(EngagementActivity.lga, func.count(EngagementActivity.id))
            .where(
                EngagementActivity.project_id == project_id,
                EngagementActivity.lga.is_not(None),
            )
            .group_by(EngagementActivity.lga)
        )
        return result.all()

    async def attendance_totals(
        self, project_id: uuid.UUID
    ) -> tuple[int, int, int]:
        """Returns (total, female, vulnerable) attendance for conducted activities."""
        result = await self.db.execute(
            select(
                func.sum(EngagementActivity.actual_count),
                func.sum(EngagementActivity.female_count),
                func.sum(EngagementActivity.vulnerable_count),
            )
            .where(
                EngagementActivity.project_id == project_id,
                EngagementActivity.status == ActivityStatus.CONDUCTED,
            )
        )
        row = result.one()
        return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)

    async def stakeholder_ids_for_project(
        self, project_id: uuid.UUID
    ) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(StakeholderProject.stakeholder_id).where(
                StakeholderProject.project_id == project_id
            )
        )
        return [r[0] for r in result.all()]

    async def stakeholder_counts_by_category(
        self, stakeholder_ids: list[uuid.UUID]
    ) -> list[tuple]:
        result = await self.db.execute(
            select(Stakeholder.category, func.count(Stakeholder.id))
            .where(Stakeholder.id.in_(stakeholder_ids))
            .group_by(Stakeholder.category)
        )
        return result.all()

    async def stakeholder_counts_by_entity_type(
        self, stakeholder_ids: list[uuid.UUID]
    ) -> list[tuple]:
        result = await self.db.execute(
            select(Stakeholder.entity_type, func.count(Stakeholder.id))
            .where(Stakeholder.id.in_(stakeholder_ids))
            .group_by(Stakeholder.entity_type)
        )
        return result.all()

    async def vulnerable_count(self, stakeholder_ids: list[uuid.UUID]) -> int:
        return await self.db.scalar(
            select(func.count(Stakeholder.id)).where(
                Stakeholder.id.in_(stakeholder_ids),
                Stakeholder.is_vulnerable.is_(True),
            )
        ) or 0

    async def pap_count(self, project_id: uuid.UUID) -> int:
        return await self.db.scalar(
            select(func.count(StakeholderProject.id)).where(
                StakeholderProject.project_id == project_id,
                StakeholderProject.is_pap.is_(True),
            )
        ) or 0
