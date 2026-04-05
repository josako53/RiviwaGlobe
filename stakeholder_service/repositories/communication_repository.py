"""
repositories/communication_repository.py
────────────────────────────────────────────────────────────────────────────
All database operations for CommunicationRecord, CommunicationDistribution,
and FocalPerson.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.communication import (
    CommChannel,
    CommDirection,
    CommPurpose,
    CommunicationDistribution,
    CommunicationRecord,
    DistributionMethod,
    FocalPerson,
    FocalPersonOrgType,
)
from models.project import ProjectCache


class CommunicationRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── ProjectCache lookup ───────────────────────────────────────────────────

    async def get_project_cache(self, project_id: uuid.UUID) -> Optional[ProjectCache]:
        result = await self.db.execute(
            select(ProjectCache).where(ProjectCache.id == project_id)
        )
        return result.scalar_one_or_none()

    # ── CommunicationRecord ───────────────────────────────────────────────────

    async def create_communication(
        self,
        project_id:            uuid.UUID,
        channel:               CommChannel,
        direction:             CommDirection,
        purpose:               CommPurpose,
        subject:               str,
        sent_by_user_id:       uuid.UUID,
        stakeholder_id:        Optional[uuid.UUID] = None,
        contact_id:            Optional[uuid.UUID] = None,
        content_summary:       Optional[str]       = None,
        document_urls:         Optional[dict]      = None,
        in_response_to_id:     Optional[uuid.UUID] = None,
        distribution_required: bool                = False,
        distribution_deadline: Optional[datetime]  = None,
        notes:                 Optional[str]       = None,
    ) -> CommunicationRecord:
        now = datetime.now(timezone.utc)
        c = CommunicationRecord(
            project_id             = project_id,
            stakeholder_id         = stakeholder_id,
            contact_id             = contact_id,
            channel                = channel,
            direction              = direction,
            purpose                = purpose,
            subject                = subject,
            content_summary        = content_summary,
            document_urls          = document_urls,
            in_response_to_id      = in_response_to_id,
            distribution_required  = distribution_required,
            distribution_deadline  = distribution_deadline,
            sent_by_user_id        = sent_by_user_id,
            sent_at                = now if direction == CommDirection.OUTGOING else None,
            received_at            = now if direction == CommDirection.INCOMING else None,
            notes                  = notes,
        )
        self.db.add(c)
        await self.db.flush()
        await self.db.refresh(c)
        return c

    async def get_communication_by_id(
        self, comm_id: uuid.UUID
    ) -> Optional[CommunicationRecord]:
        result = await self.db.execute(
            select(CommunicationRecord).where(CommunicationRecord.id == comm_id)
        )
        return result.scalar_one_or_none()

    async def list_communications(
        self,
        project_id:     Optional[uuid.UUID] = None,
        stakeholder_id: Optional[uuid.UUID] = None,
        direction:      Optional[str]       = None,
        channel:        Optional[str]       = None,
        skip:           int                 = 0,
        limit:          int                 = 50,
    ) -> list[CommunicationRecord]:
        q = select(CommunicationRecord)
        if project_id:     q = q.where(CommunicationRecord.project_id     == project_id)
        if stakeholder_id: q = q.where(CommunicationRecord.stakeholder_id == stakeholder_id)
        if direction:      q = q.where(CommunicationRecord.direction       == direction)
        if channel:        q = q.where(CommunicationRecord.channel         == channel)
        q = q.offset(skip).limit(limit).order_by(CommunicationRecord.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def list_distributions_for_comm(
        self, comm_id: uuid.UUID
    ) -> list[CommunicationDistribution]:
        result = await self.db.execute(
            select(CommunicationDistribution).where(
                CommunicationDistribution.communication_id == comm_id
            )
        )
        return list(result.scalars().all())

    async def distribution_count_for_comm(self, comm_id: uuid.UUID) -> int:
        return await self.db.scalar(
            select(func.count(CommunicationDistribution.id)).where(
                CommunicationDistribution.communication_id == comm_id
            )
        ) or 0

    # ── CommunicationDistribution ─────────────────────────────────────────────

    async def create_distribution(
        self,
        communication_id:     uuid.UUID,
        contact_id:           uuid.UUID,
        distribution_method:  DistributionMethod,
        logged_by_user_id:    uuid.UUID,
        distributed_to_count: Optional[int]      = None,
        distribution_notes:   Optional[str]      = None,
        distributed_at:       Optional[datetime] = None,
        concerns_raised_after: Optional[str]     = None,
    ) -> CommunicationDistribution:
        d = CommunicationDistribution(
            communication_id     = communication_id,
            contact_id           = contact_id,
            distributed_to_count = distributed_to_count,
            distribution_method  = distribution_method,
            distribution_notes   = distribution_notes,
            distributed_at       = distributed_at or datetime.now(timezone.utc),
            concerns_raised_after = concerns_raised_after,
            logged_by_user_id    = logged_by_user_id,
        )
        self.db.add(d)
        await self.db.flush()
        await self.db.refresh(d)
        return d

    async def get_distribution_by_id(
        self, dist_id: uuid.UUID, comm_id: Optional[uuid.UUID] = None
    ) -> Optional[CommunicationDistribution]:
        q = select(CommunicationDistribution).where(
            CommunicationDistribution.id == dist_id
        )
        if comm_id:
            q = q.where(CommunicationDistribution.communication_id == comm_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def save_distribution(self, d: CommunicationDistribution) -> None:
        self.db.add(d)

    # ── Report queries ────────────────────────────────────────────────────────

    async def list_comm_ids_for_project(
        self, project_id: uuid.UUID
    ) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(CommunicationRecord.id).where(
                CommunicationRecord.project_id == project_id
            )
        )
        return [r[0] for r in result.all()]

    async def list_comms_requiring_distribution(
        self, project_id: uuid.UUID
    ) -> list[CommunicationRecord]:
        result = await self.db.execute(
            select(CommunicationRecord).where(
                CommunicationRecord.project_id            == project_id,
                CommunicationRecord.distribution_required == True,
            )
        )
        return list(result.scalars().all())

    async def list_pending_concern_distributions(
        self, comm_ids: list[uuid.UUID]
    ) -> list[CommunicationDistribution]:
        if not comm_ids:
            return []
        result = await self.db.execute(
            select(CommunicationDistribution).where(
                CommunicationDistribution.communication_id.in_(comm_ids),
                CommunicationDistribution.concerns_raised_after.is_not(None),
                CommunicationDistribution.feedback_ref_id.is_(None),
            )
        )
        return list(result.scalars().all())

    # ── FocalPerson ───────────────────────────────────────────────────────────

    async def create_focal_person(
        self,
        project_id:        uuid.UUID,
        org_type:          FocalPersonOrgType,
        organization_name: str,
        title:             Optional[str]       = None,
        full_name:         Optional[str]       = None,
        phone:             Optional[str]       = None,
        email:             Optional[str]       = None,
        address:           Optional[str]       = None,
        user_id:           Optional[uuid.UUID] = None,
        lga:               Optional[str]       = None,
        subproject:        Optional[str]       = None,
        notes:             Optional[str]       = None,
    ) -> FocalPerson:
        fp = FocalPerson(
            project_id        = project_id,
            org_type          = org_type,
            organization_name = organization_name,
            title             = title,
            full_name         = full_name,
            phone             = phone,
            email             = email,
            address           = address,
            user_id           = user_id,
            lga               = lga,
            subproject        = subproject,
            notes             = notes,
        )
        self.db.add(fp)
        await self.db.flush()
        await self.db.refresh(fp)
        return fp

    async def get_focal_person_by_id(
        self, fp_id: uuid.UUID
    ) -> Optional[FocalPerson]:
        result = await self.db.execute(
            select(FocalPerson).where(FocalPerson.id == fp_id)
        )
        return result.scalar_one_or_none()

    async def list_focal_persons(
        self,
        project_id:  Optional[uuid.UUID] = None,
        org_type:    Optional[str]       = None,
        active_only: bool                = True,
    ) -> list[FocalPerson]:
        q = select(FocalPerson)
        if project_id:  q = q.where(FocalPerson.project_id == project_id)
        if org_type:    q = q.where(FocalPerson.org_type   == org_type)
        if active_only: q = q.where(FocalPerson.is_active.is_(True))
        result = await self.db.execute(q.order_by(FocalPerson.organization_name))
        return list(result.scalars().all())

    async def save_focal_person(self, fp: FocalPerson) -> None:
        self.db.add(fp)
