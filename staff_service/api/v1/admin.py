"""api/v1/admin.py — Admin (JWT org-scoped) staff endpoints."""
from __future__ import annotations

import math
from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, UploadFile, File

from core.dependencies import AdminDep, DbDep, KafkaDep, ManagerDep, require_feature
from core.exceptions import BulkImportJobNotFoundError, FraudReportNotFoundError, StaffNotFoundError
from repositories.staff_verification_repository import StaffVerificationRepository
from repositories.staff_fraud_report_repository import StaffFraudReportRepository
from schemas.staff_fraud_report import (
    FraudReportAssignRequest,
    FraudReportListOut,
    FraudReportOut,
    FraudReportUpdate,
)
from schemas.staff_profile import (
    StaffProfileCreate,
    StaffProfileListOut,
    StaffProfileOut,
    StaffProfileUpdate,
    StaffProfileWithStats,
    SuspendRequest,
    TerminateRequest,
)
from schemas.staff_verification import VerificationEventOut, VerificationListOut
from services.bulk_import_service import BulkImportService
from services.fraud_report_service import FraudReportService
from services.staff_service import StaffService
from storage.minio_client import upload_staff_photo, upload_csv_file

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/staff/admin",
    tags=["Admin"],
    dependencies=[Depends(require_feature("staff_verification"))],
)


# ── Profiles ──────────────────────────────────────────────────────────────────

@router.post("/profiles", response_model=StaffProfileOut)
async def create_profile(
    body: StaffProfileCreate,
    db: DbDep,
    producer: KafkaDep,
    claims: ManagerDep,
) -> StaffProfileOut:
    org_id = UUID(claims.org_id) if claims.org_id else None
    if not org_id:
        from core.exceptions import ForbiddenError
        raise ForbiddenError(message="No active org in token")
    svc = StaffService(db, producer)
    profile = await svc.create_profile(org_id, body, created_by=claims.sub)
    return StaffProfileOut.model_validate(profile)


@router.get("/profiles", response_model=StaffProfileListOut)
async def list_profiles(
    db: DbDep,
    producer: KafkaDep,
    claims: ManagerDep,
    org_id: Optional[UUID] = Query(default=None),
    department: Optional[str] = Query(default=None),
    branch_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    position: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> StaffProfileListOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    effective_org_id = org_id if is_platform_admin and org_id else (
        UUID(claims.org_id) if claims.org_id else None
    )
    if not effective_org_id:
        from core.exceptions import ForbiddenError
        raise ForbiddenError(message="org_id required")
    svc = StaffService(db, producer)
    items, total = await svc.list_profiles(
        effective_org_id, department, branch_id, status, position, page, size
    )
    pages = math.ceil(total / size) if size else 0
    return StaffProfileListOut(
        items=[StaffProfileOut.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/profiles/{profile_id}", response_model=StaffProfileWithStats)
async def get_profile(
    profile_id: UUID,
    db: DbDep,
    producer: KafkaDep,
    claims: ManagerDep,
) -> StaffProfileWithStats:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    svc = StaffService(db, producer)
    result = await svc.get_profile_with_stats(profile_id, org_id, is_platform_admin)
    profile = result["profile"]
    out = StaffProfileWithStats.model_validate(profile)
    out = out.model_copy(update={
        "feedback_count": result.get("feedback_count", 0),
        "avg_rating": result.get("avg_rating"),
    })
    return out


@router.patch("/profiles/{profile_id}", response_model=StaffProfileOut)
async def update_profile(
    profile_id: UUID,
    body: StaffProfileUpdate,
    db: DbDep,
    producer: KafkaDep,
    claims: ManagerDep,
) -> StaffProfileOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    svc = StaffService(db, producer)
    profile = await svc.update_profile(profile_id, org_id, body, is_platform_admin)
    return StaffProfileOut.model_validate(profile)


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: UUID,
    db: DbDep,
    producer: KafkaDep,
    claims: AdminDep,
) -> None:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    svc = StaffService(db, producer)
    await svc.soft_delete(profile_id, org_id, is_platform_admin=is_platform_admin)


@router.post("/profiles/{profile_id}/photo", response_model=StaffProfileOut)
async def upload_photo(
    profile_id: UUID,
    db: DbDep,
    producer: KafkaDep,
    claims: ManagerDep,
    photo: UploadFile = File(...),
) -> StaffProfileOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    data = await photo.read()
    content_type = photo.content_type or "image/jpeg"
    filename = photo.filename or "photo.jpg"
    key, url = upload_staff_photo(org_id, profile_id, filename, data, content_type)
    svc = StaffService(db, producer)
    profile = await svc.set_photo(profile_id, org_id, key, url, is_platform_admin)
    return StaffProfileOut.model_validate(profile)


@router.post("/profiles/{profile_id}/suspend", response_model=StaffProfileOut)
async def suspend_profile(
    profile_id: UUID,
    body: SuspendRequest,
    db: DbDep,
    producer: KafkaDep,
    claims: AdminDep,
) -> StaffProfileOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    svc = StaffService(db, producer)
    profile = await svc.suspend(profile_id, org_id, body.reason, is_platform_admin)
    return StaffProfileOut.model_validate(profile)


@router.post("/profiles/{profile_id}/reinstate", response_model=StaffProfileOut)
async def reinstate_profile(
    profile_id: UUID,
    db: DbDep,
    producer: KafkaDep,
    claims: AdminDep,
) -> StaffProfileOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    svc = StaffService(db, producer)
    profile = await svc.reinstate(profile_id, org_id, is_platform_admin)
    return StaffProfileOut.model_validate(profile)


@router.post("/profiles/{profile_id}/terminate", response_model=StaffProfileOut)
async def terminate_profile(
    profile_id: UUID,
    body: TerminateRequest,
    db: DbDep,
    producer: KafkaDep,
    claims: AdminDep,
) -> StaffProfileOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    svc = StaffService(db, producer)
    profile = await svc.terminate(profile_id, org_id, body.reason, is_platform_admin)
    return StaffProfileOut.model_validate(profile)


@router.post("/profiles/{profile_id}/verify", response_model=StaffProfileOut)
async def verify_profile(
    profile_id: UUID,
    db: DbDep,
    producer: KafkaDep,
    claims: AdminDep,
) -> StaffProfileOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    svc = StaffService(db, producer)
    profile = await svc.verify_profile(profile_id, org_id, is_platform_admin)
    return StaffProfileOut.model_validate(profile)


# ── Bulk Import ───────────────────────────────────────────────────────────────

@router.post("/bulk-import", dependencies=[Depends(require_feature("bulk_staff_import"))])
async def bulk_import(
    db: DbDep,
    producer: KafkaDep,
    claims: AdminDep,
    file: UploadFile = File(...),
) -> dict:
    org_id = UUID(claims.org_id) if claims.org_id else None
    if not org_id:
        from core.exceptions import ForbiddenError
        raise ForbiddenError(message="No active org in token")
    imported_by = UUID(claims.sub) if claims.sub else None
    csv_bytes = await file.read()
    filename = file.filename or "import.csv"
    svc = BulkImportService()
    # Upload CSV to MinIO first
    from uuid import uuid4
    job_id_tmp = uuid4()
    file_key = upload_csv_file(org_id, job_id_tmp, filename, csv_bytes)
    job = await svc.start_import(org_id, imported_by, filename, file_key, csv_bytes)
    return {
        "job_id": str(job.id),
        "status": job.status,
        "message": "Import job started. Check /bulk-import/{job_id} for progress.",
    }


@router.get("/bulk-import/{job_id}")
async def get_bulk_import_job(
    job_id: UUID,
    claims: AdminDep,
) -> dict:
    svc = BulkImportService()
    job = await svc.get_job(job_id)
    return {
        "id": str(job.id),
        "org_id": str(job.org_id),
        "status": job.status,
        "total_rows": job.total_rows,
        "successful_rows": job.successful_rows,
        "failed_rows": job.failed_rows,
        "errors": job.errors or [],
        "original_filename": job.original_filename,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


# ── Fraud Reports ─────────────────────────────────────────────────────────────

@router.get("/fraud-reports", response_model=FraudReportListOut)
async def list_fraud_reports(
    db: DbDep,
    producer: KafkaDep,
    claims: ManagerDep,
    org_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> FraudReportListOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    effective_org_id = org_id if is_platform_admin and org_id else (
        UUID(claims.org_id) if claims.org_id else None
    )
    if not effective_org_id:
        from core.exceptions import ForbiddenError
        raise ForbiddenError(message="org_id required")
    svc = FraudReportService(db, producer)
    items, total = await svc.list_reports(effective_org_id, status, page, size)
    pages = math.ceil(total / size) if size else 0
    return FraudReportListOut(
        items=[FraudReportOut.model_validate(r) for r in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/fraud-reports/{report_id}", response_model=FraudReportOut)
async def get_fraud_report(
    report_id: UUID,
    db: DbDep,
    producer: KafkaDep,
    claims: ManagerDep,
) -> FraudReportOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else None
    svc = FraudReportService(db, producer)
    report = await svc.get_report(report_id, org_id, is_platform_admin)
    return FraudReportOut.model_validate(report)


@router.patch("/fraud-reports/{report_id}", response_model=FraudReportOut)
async def update_fraud_report(
    report_id: UUID,
    body: FraudReportUpdate,
    db: DbDep,
    producer: KafkaDep,
    claims: AdminDep,
) -> FraudReportOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    svc = FraudReportService(db, producer)
    updates = body.model_dump(exclude_unset=True)
    report = await svc.update_report(report_id, org_id, updates, is_platform_admin)
    return FraudReportOut.model_validate(report)


@router.post("/fraud-reports/{report_id}/assign", response_model=FraudReportOut)
async def assign_fraud_report(
    report_id: UUID,
    body: FraudReportAssignRequest,
    db: DbDep,
    producer: KafkaDep,
    claims: AdminDep,
) -> FraudReportOut:
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    org_id = UUID(claims.org_id) if claims.org_id else UUID("00000000-0000-0000-0000-000000000000")
    svc = FraudReportService(db, producer)
    report = await svc.assign_agent(
        report_id, org_id, body.agent_user_id, body.notes, is_platform_admin
    )
    return FraudReportOut.model_validate(report)


# ── Verifications ─────────────────────────────────────────────────────────────

@router.get("/verifications", response_model=VerificationListOut)
async def list_verifications(
    db: DbDep,
    claims: ManagerDep,
    org_id: Optional[UUID] = Query(default=None),
    result: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> VerificationListOut:
    import datetime as dt
    is_platform_admin = claims.platform_role in ("super_admin", "admin")
    effective_org_id = org_id if is_platform_admin and org_id else (
        UUID(claims.org_id) if claims.org_id else None
    )
    if not effective_org_id:
        from core.exceptions import ForbiddenError
        raise ForbiddenError(message="org_id required")

    from_dt = dt.datetime.fromisoformat(from_date) if from_date else None
    to_dt = dt.datetime.fromisoformat(to_date) if to_date else None

    repo = StaffVerificationRepository(db)
    items, total = await repo.list_by_org(effective_org_id, result, from_dt, to_dt, page, size)
    pages = math.ceil(total / size) if size else 0
    return VerificationListOut(
        items=[VerificationEventOut.model_validate(e) for e in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )
