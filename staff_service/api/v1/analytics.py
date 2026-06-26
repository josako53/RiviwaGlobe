"""api/v1/analytics.py — Analytics (JWT org-scoped) endpoints."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from core.dependencies import DbDep, ManagerDep, require_feature
from core.exceptions import ForbiddenError
from models.staff_profile import StaffProfile
from repositories.staff_feedback_repository import StaffFeedbackRepository
from repositories.staff_fraud_report_repository import StaffFraudReportRepository
from repositories.staff_verification_repository import StaffVerificationRepository

router = APIRouter(
    prefix="/api/v1/staff/analytics",
    tags=["Analytics"],
    dependencies=[Depends(require_feature("staff_analytics"))],
)


@router.get("/overview")
async def analytics_overview(
    db: DbDep,
    claims: ManagerDep,
    org_id: Optional[UUID] = Query(default=None),
) -> dict:
    """Staff totals: active, suspended, terminated, on_leave, departments breakdown."""
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    effective_org_id = org_id if is_platform_admin and org_id else (
        UUID(claims.org_id) if claims.org_id else None
    )
    if not effective_org_id:
        raise ForbiddenError(message="org_id required")

    # Status counts
    status_rows = await db.execute(
        select(StaffProfile.status, func.count(StaffProfile.id).label("cnt"))
        .where(StaffProfile.org_id == effective_org_id)
        .group_by(StaffProfile.status)
    )
    by_status = {r.status: r.cnt for r in status_rows.all()}

    total = sum(by_status.values())
    active = by_status.get("ACTIVE", 0)
    suspended = by_status.get("SUSPENDED", 0)
    terminated = by_status.get("TERMINATED", 0)
    on_leave = by_status.get("ON_LEAVE", 0)

    # Department counts
    dept_rows = await db.execute(
        select(StaffProfile.department, func.count(StaffProfile.id).label("cnt"))
        .where(StaffProfile.org_id == effective_org_id, StaffProfile.status == "ACTIVE")
        .group_by(StaffProfile.department)
        .order_by(func.count(StaffProfile.id).desc())
    )
    departments = [
        {"department": r.department or "Unassigned", "count": r.cnt}
        for r in dept_rows.all()
    ]

    return {
        "org_id": str(effective_org_id),
        "total": total,
        "active": active,
        "suspended": suspended,
        "terminated": terminated,
        "on_leave": on_leave,
        "departments": departments,
    }


@router.get("/verifications")
async def analytics_verifications(
    db: DbDep,
    claims: ManagerDep,
    org_id: Optional[UUID] = Query(default=None),
) -> dict:
    """Verification stats: total, by_result, by_day (last 30 days)."""
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    effective_org_id = org_id if is_platform_admin and org_id else (
        UUID(claims.org_id) if claims.org_id else None
    )
    if not effective_org_id:
        raise ForbiddenError(message="org_id required")

    repo = StaffVerificationRepository(db)
    stats = await repo.stats_by_org(effective_org_id)
    stats["org_id"] = str(effective_org_id)
    return stats


@router.get("/feedback")
async def analytics_feedback(
    db: DbDep,
    claims: ManagerDep,
    org_id: Optional[UUID] = Query(default=None),
) -> dict:
    """Feedback stats: avg_rating, total, by_staff (top 10), by_rating."""
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    effective_org_id = org_id if is_platform_admin and org_id else (
        UUID(claims.org_id) if claims.org_id else None
    )
    if not effective_org_id:
        raise ForbiddenError(message="org_id required")

    repo = StaffFeedbackRepository(db)
    stats = await repo.stats_by_org(effective_org_id)
    stats["org_id"] = str(effective_org_id)
    return stats


@router.get("/fraud-reports")
async def analytics_fraud_reports(
    db: DbDep,
    claims: ManagerDep,
    org_id: Optional[UUID] = Query(default=None),
) -> dict:
    """Fraud report stats: total, by_status."""
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    effective_org_id = org_id if is_platform_admin and org_id else (
        UUID(claims.org_id) if claims.org_id else None
    )
    if not effective_org_id:
        raise ForbiddenError(message="org_id required")

    repo = StaffFraudReportRepository(db)
    stats = await repo.stats_by_org(effective_org_id)
    stats["org_id"] = str(effective_org_id)
    return stats
