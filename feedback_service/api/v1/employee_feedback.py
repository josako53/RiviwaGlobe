"""
api/v1/employee_feedback.py — Employee internal feedback endpoints.

Submission paths
─────────────────
  POST  /my/employee-feedback           Any authenticated org member
  GET   /my/employee-feedback           Own submissions only

Admin paths (manager/admin/owner)
──────────────────────────────────
  GET   /employee-feedback              List all for org (filterable)
  GET   /employee-feedback/{id}         Detail
  PATCH /employee-feedback/{id}         Respond / change status
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query, status

from core.dependencies import (
    ConsumerDep,
    DbDep,
    GRMOfficerDep,
)
from core.exceptions import ForbiddenError
from schemas.employee_feedback import (
    EmployeeFeedbackAdminUpdate,
    EmployeeFeedbackCreate,
    EmployeeFeedbackListResponse,
    EmployeeFeedbackResponse,
    EmployeeFeedbackSubmitResponse,
)
from services.employee_feedback_service import EmployeeFeedbackService

router = APIRouter(tags=["Employee Feedback"])


def _svc(db: DbDep) -> EmployeeFeedbackService:
    return EmployeeFeedbackService(db)


# ── Consumer / Employee self-service ─────────────────────────────────────────

@router.post(
    "/my/employee-feedback",
    status_code=status.HTTP_201_CREATED,
    response_model=EmployeeFeedbackSubmitResponse,
    summary="Submit internal employee feedback about your organisation",
)
async def submit_employee_feedback(
    body: EmployeeFeedbackCreate,
    db: DbDep,
    token: ConsumerDep,
) -> EmployeeFeedbackSubmitResponse:
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation to submit employee feedback.")
    return await _svc(db).submit(
        body=body,
        employee_user_id=token.sub,
        employee_name=None,  # resolved by auth_service; not carried in JWT
        org_id=token.org_id,
    )


@router.get(
    "/my/employee-feedback",
    response_model=EmployeeFeedbackListResponse,
    summary="List your own employee feedback submissions",
)
async def list_my_employee_feedback(
    db: DbDep,
    token: ConsumerDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> EmployeeFeedbackListResponse:
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation.")
    return await _svc(db).my_feedback(
        employee_user_id=token.sub,
        org_id=token.org_id,
        skip=skip,
        limit=limit,
    )


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get(
    "/employee-feedback",
    response_model=EmployeeFeedbackListResponse,
    summary="[Admin] List all employee feedback for the organisation",
)
async def admin_list_employee_feedback(
    db: DbDep,
    token: GRMOfficerDep,
    org_id: Optional[uuid.UUID] = Query(
        default=None,
        description="Override — platform admins only. Omit to use JWT org.",
    ),
    feedback_type: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    is_anonymous: Optional[bool] = Query(default=None),
    branch_id: Optional[uuid.UUID] = Query(default=None),
    department_id: Optional[uuid.UUID] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> EmployeeFeedbackListResponse:
    from core.dependencies import _is_platform_admin
    effective_org = org_id if (org_id and _is_platform_admin(token)) else token.org_id
    if not effective_org:
        raise ForbiddenError(message="Switch to an active organisation.")
    return await _svc(db).admin_list(
        org_id=effective_org,
        feedback_type=feedback_type,
        category=category,
        status=status_filter,
        is_anonymous=is_anonymous,
        branch_id=branch_id,
        department_id=department_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/employee-feedback/{ef_id}",
    response_model=EmployeeFeedbackResponse,
    summary="[Admin] Get employee feedback detail",
)
async def admin_get_employee_feedback(
    ef_id: uuid.UUID,
    db: DbDep,
    token: GRMOfficerDep,
) -> EmployeeFeedbackResponse:
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation.")
    return await _svc(db).admin_get(ef_id=ef_id, org_id=token.org_id)


@router.patch(
    "/employee-feedback/{ef_id}",
    response_model=EmployeeFeedbackResponse,
    summary="[Admin] Respond to or update status of employee feedback",
)
async def admin_update_employee_feedback(
    ef_id: uuid.UUID,
    body: EmployeeFeedbackAdminUpdate,
    db: DbDep,
    token: GRMOfficerDep,
) -> EmployeeFeedbackResponse:
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation.")
    return await _svc(db).admin_update(
        ef_id=ef_id,
        org_id=token.org_id,
        body=body,
        responder_user_id=token.sub,
    )
