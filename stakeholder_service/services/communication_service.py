"""
services/communication_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for communication records, distributions, focal persons,
and report aggregation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    CommunicationNotFoundError,
    FocalPersonNotFoundError,
    ProjectNotFoundError,
)
from events.producer import StakeholderProducer
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
from repositories.communication_repository import CommunicationRepository
from repositories.report_repository import ReportRepository


class CommunicationService:

    def __init__(self, db: AsyncSession, producer: StakeholderProducer) -> None:
        self.repo        = CommunicationRepository(db)
        self.report_repo = ReportRepository(db)
        self.producer    = producer
        self.db          = db

    # ── Communications ────────────────────────────────────────────────────────

    async def log_communication(
        self, data: dict, sent_by: uuid.UUID
    ) -> CommunicationRecord:
        project_id = uuid.UUID(data["project_id"])
        if not await self.repo.get_project_cache(project_id):
            raise ProjectNotFoundError()

        c = await self.repo.create_communication(
            project_id             = project_id,
            channel                = CommChannel(data["channel"]),
            direction              = CommDirection(data["direction"]),
            purpose                = CommPurpose(data["purpose"]),
            subject                = data["subject"],
            sent_by_user_id        = sent_by,
            stakeholder_id         = uuid.UUID(data["stakeholder_id"]) if data.get("stakeholder_id") else None,
            contact_id             = uuid.UUID(data["contact_id"]) if data.get("contact_id") else None,
            content_summary        = data.get("content_summary"),
            document_urls          = data.get("document_urls"),
            in_response_to_id      = uuid.UUID(data["in_response_to_id"]) if data.get("in_response_to_id") else None,
            distribution_required  = data.get("distribution_required", False),
            distribution_deadline  = datetime.fromisoformat(data["distribution_deadline"]) if data.get("distribution_deadline") else None,
            notes                  = data.get("notes"),
        )
        await self.db.commit()
        return c

    async def get_communication_or_404(self, comm_id: uuid.UUID) -> CommunicationRecord:
        c = await self.repo.get_communication_by_id(comm_id)
        if not c:
            raise CommunicationNotFoundError()
        return c

    async def get_communication_with_distributions(
        self, comm_id: uuid.UUID
    ) -> tuple[CommunicationRecord, list[CommunicationDistribution]]:
        c = await self.get_communication_or_404(comm_id)
        distributions = await self.repo.list_distributions_for_comm(comm_id)
        return c, distributions

    async def list_communications(
        self,
        project_id:     Optional[uuid.UUID] = None,
        stakeholder_id: Optional[uuid.UUID] = None,
        direction:      Optional[str]       = None,
        channel:        Optional[str]       = None,
        skip:           int                 = 0,
        limit:          int                 = 50,
    ) -> list[CommunicationRecord]:
        return await self.repo.list_communications(
            project_id=project_id, stakeholder_id=stakeholder_id,
            direction=direction, channel=channel, skip=skip, limit=limit,
        )

    # ── Distributions ─────────────────────────────────────────────────────────

    async def log_distribution(
        self, comm_id: uuid.UUID, data: dict, logged_by: uuid.UUID
    ) -> CommunicationDistribution:
        c = await self.get_communication_or_404(comm_id)
        d = await self.repo.create_distribution(
            communication_id      = comm_id,
            contact_id            = uuid.UUID(data["contact_id"]),
            distribution_method   = DistributionMethod(data["distribution_method"]),
            logged_by_user_id     = logged_by,
            distributed_to_count  = data.get("distributed_to_count"),
            distribution_notes    = data.get("distribution_notes"),
            distributed_at        = datetime.fromisoformat(data["distributed_at"]) if data.get("distributed_at") else None,
            concerns_raised_after = data.get("concerns_raised_after"),
        )
        await self.db.commit()
        if d.concerns_raised_after:
            await self.producer.comm_concerns_pending(
                d.id, comm_id, d.contact_id, c.project_id, d.concerns_raised_after
            )
        return d

    async def update_distribution(
        self, comm_id: uuid.UUID, dist_id: uuid.UUID,
        data: dict, updated_by: uuid.UUID,
    ) -> CommunicationDistribution:
        d = await self.repo.get_distribution_by_id(dist_id, comm_id)
        if not d:
            raise CommunicationNotFoundError()

        for field in ("distribution_notes", "concerns_raised_after", "distributed_to_count"):
            if field in data and data[field] is not None:
                setattr(d, field, data[field])

        if "feedback_ref_id" in data and data["feedback_ref_id"]:
            d.feedback_ref_id = uuid.UUID(data["feedback_ref_id"])

        if data.get("acknowledge"):
            d.acknowledged_at         = datetime.now(timezone.utc)
            d.acknowledged_by_user_id = updated_by

        await self.repo.save_distribution(d)
        await self.db.commit()
        return d

    # ── Focal persons ─────────────────────────────────────────────────────────

    async def create_focal_person(self, data: dict) -> FocalPerson:
        project_id = uuid.UUID(data["project_id"])
        if not await self.repo.get_project_cache(project_id):
            raise ProjectNotFoundError()

        fp = await self.repo.create_focal_person(
            project_id        = project_id,
            org_type          = FocalPersonOrgType(data["org_type"]),
            organization_name = data["organization_name"],
            title             = data.get("title"),
            full_name         = data.get("full_name"),
            phone             = data.get("phone"),
            email             = data.get("email"),
            address           = data.get("address"),
            user_id           = uuid.UUID(data["user_id"]) if data.get("user_id") else None,
            lga               = data.get("lga"),
            subproject        = data.get("subproject"),
            notes             = data.get("notes"),
        )
        await self.db.commit()
        return fp

    async def get_focal_person_or_404(self, fp_id: uuid.UUID) -> FocalPerson:
        fp = await self.repo.get_focal_person_by_id(fp_id)
        if not fp:
            raise FocalPersonNotFoundError()
        return fp

    async def list_focal_persons(
        self,
        project_id:  Optional[uuid.UUID] = None,
        org_type:    Optional[str]       = None,
        active_only: bool                = True,
    ) -> list[FocalPerson]:
        return await self.repo.list_focal_persons(
            project_id=project_id, org_type=org_type, active_only=active_only
        )

    async def update_focal_person(
        self, fp_id: uuid.UUID, data: dict
    ) -> FocalPerson:
        fp = await self.get_focal_person_or_404(fp_id)
        for field in ("title", "full_name", "phone", "email", "address",
                      "lga", "subproject", "notes", "is_active"):
            if field in data and data[field] is not None:
                setattr(fp, field, data[field])
        if "user_id" in data:
            fp.user_id = uuid.UUID(data["user_id"]) if data["user_id"] else None
        await self.repo.save_focal_person(fp)
        await self.db.commit()
        return fp

    # ── Reports ───────────────────────────────────────────────────────────────

    async def engagement_summary(self, project_id: uuid.UUID) -> dict:
        by_stage  = await self.report_repo.activity_counts_by_stage(project_id)
        by_lga    = await self.report_repo.activity_counts_by_lga(project_id)
        total, female, vuln = await self.report_repo.attendance_totals(project_id)
        return {
            "project_id": str(project_id),
            "by_stage":   [{"stage": r[0], "status": r[1], "count": r[2]} for r in by_stage],
            "by_lga":     [{"lga": r[0], "count": r[1]} for r in by_lga],
            "total_attendance":            total,
            "total_female_attendance":     female,
            "total_vulnerable_attendance": vuln,
        }

    async def stakeholder_reach(self, project_id: uuid.UUID) -> dict:
        stakeholder_ids = await self.report_repo.stakeholder_ids_for_project(project_id)
        if not stakeholder_ids:
            return {"project_id": str(project_id), "total": 0, "pap_count": 0,
                    "by_category": [], "vulnerable_count": 0, "by_entity_type": []}
        by_cat   = await self.report_repo.stakeholder_counts_by_category(stakeholder_ids)
        by_type  = await self.report_repo.stakeholder_counts_by_entity_type(stakeholder_ids)
        vuln_cnt = await self.report_repo.vulnerable_count(stakeholder_ids)
        pap_cnt  = await self.report_repo.pap_count(project_id)
        return {
            "project_id":     str(project_id),
            "total":          len(stakeholder_ids),
            "pap_count":      pap_cnt,
            "vulnerable_count": vuln_cnt,
            "by_category":    [{"category": r[0], "count": r[1]} for r in by_cat],
            "by_entity_type": [{"entity_type": r[0], "count": r[1]} for r in by_type],
        }

    async def pending_distributions(self, project_id: uuid.UUID) -> dict:
        comms = await self.repo.list_comms_requiring_distribution(project_id)
        pending = []
        for c in comms:
            if await self.repo.distribution_count_for_comm(c.id) == 0:
                pending.append({
                    "communication_id": str(c.id),
                    "subject":          c.subject,
                    "sent_at":          c.sent_at.isoformat() if c.sent_at else None,
                    "deadline":         c.distribution_deadline.isoformat() if c.distribution_deadline else None,
                    "stakeholder_id":   str(c.stakeholder_id) if c.stakeholder_id else None,
                    "contact_id":       str(c.contact_id) if c.contact_id else None,
                })
        return {"project_id": str(project_id), "pending_count": len(pending), "items": pending}

    async def pending_concerns(self, project_id: uuid.UUID) -> dict:
        comm_ids = await self.repo.list_comm_ids_for_project(project_id)
        items = await self.repo.list_pending_concern_distributions(comm_ids)
        return {
            "project_id":    str(project_id),
            "pending_count": len(items),
            "items": [
                {
                    "distribution_id":  str(d.id),
                    "communication_id": str(d.communication_id),
                    "contact_id":       str(d.contact_id),
                    "concerns":         d.concerns_raised_after,
                    "distributed_at":   d.distributed_at.isoformat() if d.distributed_at else None,
                }
                for d in items
            ],
        }
