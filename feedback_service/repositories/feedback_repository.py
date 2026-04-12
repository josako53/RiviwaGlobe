"""
repositories/feedback_repository.py
────────────────────────────────────────────────────────────────────────────
All database operations for Feedback, FeedbackAction, FeedbackEscalation,
FeedbackResolution, FeedbackAppeal, EscalationRequest.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.feedback import (
    EscalationRequest,
    EscalationRequestStatus,
    Feedback,
    FeedbackAction,
    FeedbackAppeal,
    FeedbackEscalation,
    FeedbackResolution,
    FeedbackStatus,
)
from models.project import ProjectCache


class FeedbackRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── ProjectCache ──────────────────────────────────────────────────────────

    async def get_project(self, project_id: uuid.UUID) -> Optional[ProjectCache]:
        result = await self.db.execute(
            select(ProjectCache)
            .options(selectinload(ProjectCache.stages))
            .where(ProjectCache.id == project_id)
        )
        return result.scalar_one_or_none()

    # ── Feedback ──────────────────────────────────────────────────────────────

    async def create(self, feedback: Feedback) -> Feedback:
        self.db.add(feedback)
        await self.db.flush()
        await self.db.refresh(feedback)
        return feedback

    async def get_by_id(
        self,
        feedback_id: uuid.UUID,
        load_relations: bool = False,
        org_id: Optional[uuid.UUID] = None,
    ) -> Optional[Feedback]:
        q = select(Feedback).where(Feedback.id == feedback_id)
        if org_id:
            q = q.join(ProjectCache, Feedback.project_id == ProjectCache.id).where(
                ProjectCache.organisation_id == org_id
            )
        if load_relations:
            q = q.options(
                selectinload(Feedback.actions),
                selectinload(Feedback.escalations),
                selectinload(Feedback.resolution),
                selectinload(Feedback.appeal),
                selectinload(Feedback.escalation_requests),
            )
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_with_history(
        self,
        feedback_id: uuid.UUID,
        org_id: Optional[uuid.UUID] = None,
    ) -> Optional[Feedback]:
        q = (
            select(Feedback)
            .options(
                selectinload(Feedback.actions),
                selectinload(Feedback.escalations),
                selectinload(Feedback.resolution),
                selectinload(Feedback.appeal),
            )
            .where(Feedback.id == feedback_id)
        )
        if org_id:
            q = q.join(ProjectCache, Feedback.project_id == ProjectCache.id).where(
                ProjectCache.organisation_id == org_id
            )
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list(
        self,
        org_id:                      Optional[uuid.UUID] = None,
        project_id:                  Optional[uuid.UUID] = None,
        feedback_type:               Optional[str]       = None,
        status:                      Optional[str]       = None,
        priority:                    Optional[str]       = None,
        current_level:               Optional[str]       = None,
        category:                    Optional[str]       = None,
        # ── Tanzania location filters (Annex 5/6 admin hierarchy) ─────────────
        region:                      Optional[str]       = None,
        district:                    Optional[str]       = None,
        lga:                         Optional[str]       = None,
        ward:                        Optional[str]       = None,
        mtaa:                        Optional[str]       = None,
        # ── Other filters ─────────────────────────────────────────────────────
        is_anonymous:                Optional[bool]      = None,
        submission_method:           Optional[str]       = None,
        channel:                     Optional[str]       = None,
        submitted_by_stakeholder_id: Optional[uuid.UUID] = None,
        assigned_committee_id:       Optional[uuid.UUID] = None,
        skip:  int = 0,
        limit: int = 50,
    ) -> list[Feedback]:
        q = select(Feedback)
        if org_id:
            q = q.join(ProjectCache, Feedback.project_id == ProjectCache.id).where(
                ProjectCache.organisation_id == org_id
            )
        if project_id:                  q = q.where(Feedback.project_id                   == project_id)
        if feedback_type:               q = q.where(Feedback.feedback_type                == feedback_type)
        if status:                      q = q.where(Feedback.status                       == status)
        if priority:                    q = q.where(Feedback.priority                     == priority)
        if current_level:               q = q.where(Feedback.current_level                == current_level)
        if category:                    q = q.where(Feedback.category                     == category)
        # Location filters — partial match (ilike) for flexibility
        if region:                      q = q.where(Feedback.issue_region.ilike(f"%{region}%"))
        if district:                    q = q.where(Feedback.issue_district.ilike(f"%{district}%"))
        if lga:                         q = q.where(Feedback.issue_lga.ilike(f"%{lga}%"))
        if ward:                        q = q.where(Feedback.issue_ward.ilike(f"%{ward}%"))
        if mtaa:                        q = q.where(Feedback.issue_mtaa.ilike(f"%{mtaa}%"))
        if is_anonymous is not None:    q = q.where(Feedback.is_anonymous                 == is_anonymous)
        if submission_method:           q = q.where(Feedback.submission_method            == submission_method)
        if channel:                     q = q.where(Feedback.channel                      == channel)
        if submitted_by_stakeholder_id: q = q.where(Feedback.submitted_by_stakeholder_id == submitted_by_stakeholder_id)
        if assigned_committee_id:       q = q.where(Feedback.assigned_committee_id        == assigned_committee_id)
        q = q.offset(skip).limit(limit).order_by(Feedback.submitted_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def list_for_user(
        self,
        user_id:        uuid.UUID,
        stakeholder_id: Optional[uuid.UUID] = None,
        feedback_type:  Optional[str]       = None,
        status:         Optional[str]       = None,
        project_id:     Optional[uuid.UUID] = None,
        skip:  int = 0,
        limit: int = 50,
    ) -> list[Feedback]:
        conditions = [Feedback.submitted_by_user_id == user_id]
        if stakeholder_id:
            conditions.append(Feedback.submitted_by_stakeholder_id == stakeholder_id)
        q = select(Feedback).where(or_(*conditions))
        if feedback_type: q = q.where(Feedback.feedback_type == feedback_type)
        if status:        q = q.where(Feedback.status        == status)
        if project_id:    q = q.where(Feedback.project_id    == project_id)
        q = q.order_by(Feedback.submitted_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def count_for_project(self, project_id: uuid.UUID) -> int:
        return await self.db.scalar(
            select(func.count(Feedback.id)).where(Feedback.project_id == project_id)
        ) or 0

    async def count_total(self) -> int:
        return await self.db.scalar(select(func.count(Feedback.id))) or 0

    async def count_by_type(self, feedback_type) -> int:
        """Global count of all feedback of a given type."""
        return await self.db.scalar(
            select(func.count(Feedback.id)).where(Feedback.feedback_type == feedback_type)
        ) or 0

    async def next_ref_sequence(self, prefix: str, year: int) -> int:
        """
        Return the next unique sequence number for a ref like GRV-2026-NNNN.

        Uses an atomic INSERT … ON CONFLICT DO UPDATE … RETURNING on the
        feedback_ref_sequences table.  PostgreSQL processes this as a single
        statement — two concurrent calls on the same (prefix, year) can never
        receive the same number, regardless of load.

        Why not MAX()?  Under concurrent load two transactions can both read
        the same MAX value and both attempt to insert the same ref, causing a
        UniqueViolationError.  The atomic upsert eliminates the race entirely.
        """
        from sqlalchemy import text as _text
        result = await self.db.execute(
            _text("""
                INSERT INTO feedback_ref_sequences (prefix, year, last_value)
                VALUES (:prefix, :year, 1)
                ON CONFLICT (prefix, year)
                DO UPDATE SET last_value = feedback_ref_sequences.last_value + 1
                RETURNING last_value
            """),
            {"prefix": prefix, "year": year},
        )
        return result.scalar()

    async def save(self, f: Feedback) -> None:
        self.db.add(f)

    # ── Actions ───────────────────────────────────────────────────────────────

    async def create_action(self, action: FeedbackAction) -> FeedbackAction:
        self.db.add(action)
        await self.db.flush()
        await self.db.refresh(action)
        return action

    async def list_actions(self, feedback_id: uuid.UUID) -> list[FeedbackAction]:
        result = await self.db.execute(
            select(FeedbackAction)
            .where(FeedbackAction.feedback_id == feedback_id)
            .order_by(FeedbackAction.performed_at)
        )
        return list(result.scalars().all())

    # ── Escalations ───────────────────────────────────────────────────────────

    async def create_escalation(self, esc: FeedbackEscalation) -> FeedbackEscalation:
        self.db.add(esc)
        return esc

    # ── Resolution ────────────────────────────────────────────────────────────

    async def create_resolution(self, resolution: FeedbackResolution) -> FeedbackResolution:
        self.db.add(resolution)
        return resolution

    async def save_resolution(self, r: FeedbackResolution) -> None:
        self.db.add(r)

    # ── Appeal ────────────────────────────────────────────────────────────────

    async def create_appeal(self, appeal: FeedbackAppeal) -> FeedbackAppeal:
        self.db.add(appeal)
        return appeal

    # ── Escalation requests ───────────────────────────────────────────────────

    async def get_pending_escalation_request(
        self, feedback_id: uuid.UUID
    ) -> Optional[EscalationRequest]:
        result = await self.db.execute(
            select(EscalationRequest).where(
                EscalationRequest.feedback_id == feedback_id,
                EscalationRequest.status == EscalationRequestStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def create_escalation_request(
        self, er: EscalationRequest
    ) -> EscalationRequest:
        self.db.add(er)
        await self.db.flush()
        await self.db.refresh(er)
        return er

    async def get_escalation_request(
        self, request_id: uuid.UUID
    ) -> Optional[EscalationRequest]:
        result = await self.db.execute(
            select(EscalationRequest).where(EscalationRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def list_escalation_requests(
        self,
        status:     Optional[str]       = "pending",
        project_id: Optional[uuid.UUID] = None,
        skip:  int = 0,
        limit: int = 50,
    ) -> list[EscalationRequest]:
        q = select(EscalationRequest)
        if status:
            q = q.where(EscalationRequest.status == status)
        if project_id:
            q = q.join(Feedback, EscalationRequest.feedback_id == Feedback.id) \
                 .where(Feedback.project_id == project_id)
        q = q.order_by(EscalationRequest.requested_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def count_pending_escalation_requests(
        self, user_id: uuid.UUID
    ) -> int:
        return await self.db.scalar(
            select(func.count(EscalationRequest.id)).where(
                EscalationRequest.requested_by_user_id == user_id,
                EscalationRequest.status == EscalationRequestStatus.PENDING,
            )
        ) or 0

    async def save_escalation_request(self, er: EscalationRequest) -> None:
        self.db.add(er)
