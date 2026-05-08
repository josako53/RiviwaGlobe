"""repositories/staff_profile_repository.py — StaffProfile and StaffIdSequence DB ops."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.staff_profile import StaffIdSequence, StaffProfile

log = structlog.get_logger(__name__)


class StaffProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Sequence / Code generation ────────────────────────────────────────────

    async def next_sequence(self, org_id: UUID) -> int:
        """
        Atomically increment the per-org sequence and return the new value.
        Uses raw SQL so the upsert is done in a single round-trip.
        """
        result = await self.db.execute(
            text(
                """
                INSERT INTO staff_id_sequences (org_id, last_value)
                VALUES (:org_id, 1)
                ON CONFLICT (org_id) DO UPDATE
                    SET last_value = staff_id_sequences.last_value + 1
                RETURNING last_value
                """
            ),
            {"org_id": str(org_id)},
        )
        return result.scalar_one()

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, profile: StaffProfile) -> StaffProfile:
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_by_id(self, profile_id: UUID) -> Optional[StaffProfile]:
        return await self.db.get(StaffProfile, profile_id)

    async def get_by_staff_code(self, org_id: UUID, staff_code: str) -> Optional[StaffProfile]:
        result = await self.db.execute(
            select(StaffProfile).where(
                StaffProfile.org_id == org_id,
                func.lower(StaffProfile.staff_code) == staff_code.strip().lower(),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code_any_org(self, code: str) -> Optional[StaffProfile]:
        """Look up by staff_code across all orgs (for public verify endpoint)."""
        result = await self.db.execute(
            select(StaffProfile).where(
                func.lower(StaffProfile.staff_code) == code.strip().lower(),
            ).order_by(StaffProfile.created_at.desc()).limit(1)
        )
        return result.scalars().first()

    async def get_by_badge_number(self, org_id: UUID, badge_number: str) -> Optional[StaffProfile]:
        result = await self.db.execute(
            select(StaffProfile).where(
                StaffProfile.org_id == org_id,
                StaffProfile.badge_number == badge_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, org_id: UUID, email: str) -> Optional[StaffProfile]:
        result = await self.db.execute(
            select(StaffProfile).where(
                StaffProfile.org_id == org_id,
                func.lower(StaffProfile.email) == email.lower(),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        org_id: UUID,
        department: Optional[str] = None,
        branch_id: Optional[UUID] = None,
        status: Optional[str] = None,
        position: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[StaffProfile], int]:
        q = select(StaffProfile).where(StaffProfile.org_id == org_id)
        if department:
            q = q.where(StaffProfile.department == department)
        if branch_id:
            q = q.where(StaffProfile.branch_id == branch_id)
        if status:
            q = q.where(StaffProfile.status == status.upper())
        if position:
            q = q.where(StaffProfile.position.ilike(f"%{position}%"))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(StaffProfile.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update(self, profile: StaffProfile, data: Dict[str, Any]) -> StaffProfile:
        for k, v in data.items():
            setattr(profile, k, v)
        profile.updated_at = dt.datetime.utcnow()
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def save(self, profile: StaffProfile) -> StaffProfile:
        profile.updated_at = dt.datetime.utcnow()
        self.db.add(profile)
        await self.db.flush()
        return profile

    # ── Feedback Stats ────────────────────────────────────────────────────────

    async def feedback_stats(self, staff_id: UUID) -> Dict[str, Any]:
        from models.staff_feedback import StaffFeedback
        result = await self.db.execute(
            select(
                func.count(StaffFeedback.id).label("count"),
                func.avg(StaffFeedback.rating).label("avg_rating"),
            ).where(StaffFeedback.staff_id == staff_id)
        )
        row = result.one()
        return {
            "feedback_count": row.count or 0,
            "avg_rating": float(row.avg_rating) if row.avg_rating else None,
        }
