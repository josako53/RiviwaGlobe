"""services/employee_feedback_service.py — Business logic for employee internal feedback."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ForbiddenError, NotFoundError
from models.employee_feedback import EmployeeFeedback, EFStatus
from repositories.employee_feedback_repo import EmployeeFeedbackRepository
from schemas.employee_feedback import (
    EmployeeFeedbackAdminUpdate,
    EmployeeFeedbackCreate,
    EmployeeFeedbackListResponse,
    EmployeeFeedbackResponse,
    EmployeeFeedbackSubmitResponse,
)

log = structlog.get_logger(__name__)

_VALID_TYPES = {"grievance", "suggestion", "applause", "inquiry"}
_VALID_CATEGORIES = {
    "working_conditions", "management", "culture", "compensation",
    "tools_resources", "communication", "career_growth", "safety",
    "team_dynamics", "leadership", "benefits", "other",
}
_VALID_STATUSES = {s.value for s in EFStatus}


def _to_response(ef: EmployeeFeedback) -> EmployeeFeedbackResponse:
    return EmployeeFeedbackResponse.model_validate(ef)


class EmployeeFeedbackService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = EmployeeFeedbackRepository(db)

    async def submit(
        self,
        body: EmployeeFeedbackCreate,
        employee_user_id: uuid.UUID,
        employee_name: Optional[str],
        org_id: uuid.UUID,
    ) -> EmployeeFeedbackSubmitResponse:
        tracking = await self.repo.next_tracking_number()

        ef = EmployeeFeedback(
            tracking_number=tracking,
            org_id=org_id,
            feedback_type=body.feedback_type,
            category=body.category,
            subject=body.subject,
            description=body.description,
            is_anonymous=body.is_anonymous,
            employee_user_id=None if body.is_anonymous else employee_user_id,
            employee_name=None if body.is_anonymous else employee_name,
            department_id=body.department_id,
            branch_id=body.branch_id,
            status=EFStatus.SUBMITTED,
        )
        ef = await self.repo.create(ef)
        log.info("employee_feedback.submitted", tracking=tracking, type=body.feedback_type, org=str(org_id))

        return EmployeeFeedbackSubmitResponse(
            feedback_id=ef.id,
            tracking_number=ef.tracking_number,
            feedback_type=ef.feedback_type,
            status=ef.status,
            message="Your feedback has been submitted. Thank you for helping improve our organisation.",
        )

    async def my_feedback(
        self,
        employee_user_id: uuid.UUID,
        org_id: uuid.UUID,
        skip: int,
        limit: int,
    ) -> EmployeeFeedbackListResponse:
        total, items = await self.repo.list_for_employee(employee_user_id, org_id, skip, limit)
        return EmployeeFeedbackListResponse(
            total=total, skip=skip, limit=limit,
            items=[_to_response(i) for i in items],
        )

    async def admin_list(
        self,
        org_id: uuid.UUID,
        feedback_type: Optional[str],
        category: Optional[str],
        status: Optional[str],
        is_anonymous: Optional[bool],
        branch_id: Optional[uuid.UUID],
        department_id: Optional[uuid.UUID],
        skip: int,
        limit: int,
    ) -> EmployeeFeedbackListResponse:
        total, items = await self.repo.list_for_org(
            org_id=org_id,
            feedback_type=feedback_type,
            category=category,
            status=status,
            is_anonymous=is_anonymous,
            branch_id=branch_id,
            department_id=department_id,
            skip=skip,
            limit=limit,
        )
        return EmployeeFeedbackListResponse(
            total=total, skip=skip, limit=limit,
            items=[_to_response(i) for i in items],
        )

    async def admin_get(self, ef_id: uuid.UUID, org_id: uuid.UUID) -> EmployeeFeedbackResponse:
        ef = await self.repo.get_by_id(ef_id, org_id)
        if not ef:
            raise NotFoundError(message="Employee feedback not found.")
        return _to_response(ef)

    async def admin_update(
        self,
        ef_id: uuid.UUID,
        org_id: uuid.UUID,
        body: EmployeeFeedbackAdminUpdate,
        responder_user_id: uuid.UUID,
    ) -> EmployeeFeedbackResponse:
        ef = await self.repo.get_by_id(ef_id, org_id)
        if not ef:
            raise NotFoundError(message="Employee feedback not found.")

        if body.status and body.status in _VALID_STATUSES:
            ef.status = body.status
        if body.management_response is not None:
            ef.management_response = body.management_response
            ef.responded_at = datetime.utcnow()
            ef.responded_by_user_id = responder_user_id
            if ef.status == EFStatus.SUBMITTED:
                ef.status = EFStatus.ACKNOWLEDGED

        ef.updated_at = datetime.utcnow()
        ef = await self.repo.save(ef)
        log.info("employee_feedback.updated", id=str(ef_id), status=ef.status)
        return _to_response(ef)
