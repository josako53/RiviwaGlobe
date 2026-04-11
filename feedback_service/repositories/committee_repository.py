"""
repositories/committee_repository.py
────────────────────────────────────────────────────────────────────────────
All database operations for GrievanceCommittee and GrievanceCommitteeMember.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.feedback import (
    CommitteeRole,
    GrievanceCommittee,
    GrievanceCommitteeMember,
)


class CommitteeRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, committee_id: uuid.UUID) -> Optional[GrievanceCommittee]:
        result = await self.db.execute(
            select(GrievanceCommittee).where(GrievanceCommittee.id == committee_id)
        )
        return result.scalar_one_or_none()

    async def create(self, committee: GrievanceCommittee) -> GrievanceCommittee:
        self.db.add(committee)
        await self.db.flush()
        await self.db.refresh(committee)
        return committee

    async def save(self, committee: GrievanceCommittee) -> None:
        self.db.add(committee)

    async def list(
        self,
        project_id:         Optional[uuid.UUID] = None,
        level:              Optional[str]        = None,
        lga:                Optional[str]        = None,
        org_sub_project_id: Optional[uuid.UUID]  = None,
        stakeholder_id:     Optional[uuid.UUID]  = None,
        active_only:        bool                 = True,
    ) -> list[GrievanceCommittee]:
        q = select(GrievanceCommittee)
        if project_id:         q = q.where(GrievanceCommittee.project_id         == project_id)
        if level:              q = q.where(GrievanceCommittee.level              == level)
        if lga:                q = q.where(GrievanceCommittee.lga.ilike(f"%{lga}%"))
        if org_sub_project_id: q = q.where(GrievanceCommittee.org_sub_project_id == org_sub_project_id)
        if active_only:        q = q.where(GrievanceCommittee.is_active.is_(True))
        if stakeholder_id:
            # JSONB contains check
            q = q.where(
                GrievanceCommittee.stakeholder_ids[
                    "stakeholder_ids"
                ].as_string().contains(str(stakeholder_id))
            )
        result = await self.db.execute(
            q.order_by(GrievanceCommittee.level, GrievanceCommittee.name)
        )
        return list(result.scalars().all())

    # ── Members ───────────────────────────────────────────────────────────────

    async def get_active_member(
        self, committee_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[GrievanceCommitteeMember]:
        result = await self.db.execute(
            select(GrievanceCommitteeMember).where(
                GrievanceCommitteeMember.committee_id == committee_id,
                GrievanceCommitteeMember.user_id      == user_id,
                GrievanceCommitteeMember.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_any_member(
        self, committee_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[GrievanceCommitteeMember]:
        """Return an existing member row regardless of is_active status."""
        result = await self.db.execute(
            select(GrievanceCommitteeMember).where(
                GrievanceCommitteeMember.committee_id == committee_id,
                GrievanceCommitteeMember.user_id      == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_member(
        self,
        committee_id: uuid.UUID,
        user_id:      uuid.UUID,
        role:         CommitteeRole = CommitteeRole.MEMBER,
    ) -> GrievanceCommitteeMember:
        # Reactivate an existing row rather than inserting (unique constraint on committee_id+user_id)
        existing = await self.get_any_member(committee_id, user_id)
        if existing:
            existing.is_active = True
            existing.role      = role
            existing.left_at   = None
            self.db.add(existing)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        m = GrievanceCommitteeMember(
            committee_id = committee_id,
            user_id      = user_id,
            role         = role,
        )
        self.db.add(m)
        await self.db.flush()
        await self.db.refresh(m)
        return m

    async def deactivate_member(self, m: GrievanceCommitteeMember) -> None:
        m.is_active = False
        m.left_at   = datetime.now(timezone.utc)
        self.db.add(m)
