"""api/v1/public.py — Public (unauthenticated) staff endpoints."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Form, Request, UploadFile, File

from core.dependencies import DbDep, KafkaDep
from core.exceptions import StaffNotFoundError, VerificationEventNotFoundError
from repositories.staff_feedback_repository import StaffFeedbackRepository
from repositories.staff_verification_repository import StaffVerificationRepository
from schemas.staff_feedback import StaffFeedbackCreate, StaffFeedbackOut
from schemas.staff_verification import VerifyRequest, VerifyResponse
from services.fraud_report_service import FraudReportService
from services.verification_service import VerificationService
from models.staff_feedback import StaffFeedback
from storage.minio_client import upload_fraud_photo

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/staff", tags=["Public"])


@router.post("/verify", response_model=VerifyResponse)
async def verify_staff(
    body: VerifyRequest,
    request: Request,
    db: DbDep,
    producer: KafkaDep,
) -> VerifyResponse:
    """
    Look up a staff member by their staff code.
    Returns verification result along with public staff info on a valid match.
    """
    scanner_ip = request.client.host if request.client else None
    svc = VerificationService(db, producer)
    return await svc.verify(
        code=body.code,
        scanner_lat=body.scanner_lat,
        scanner_lng=body.scanner_lng,
        scanner_ip=scanner_ip,
        user_agent=body.user_agent,
    )


@router.post("/report-fraud")
async def report_fraud(
    db: DbDep,
    producer: KafkaDep,
    verification_event_id: Optional[UUID] = Form(default=None),
    reporter_name: Optional[str] = Form(default=None),
    reporter_phone: Optional[str] = Form(default=None),
    reporter_email: Optional[str] = Form(default=None),
    claimed_staff_name: Optional[str] = Form(default=None),
    claimed_staff_id: Optional[str] = Form(default=None),
    description: str = Form(...),
    photos: Optional[List[UploadFile]] = File(default=None),
) -> dict:
    """
    Submit a fraud report about a staff impersonator.
    Accepts multipart/form-data. Photos are optional.
    """
    # Resolve org_id from verification event if provided
    org_id: Optional[UUID] = None
    if verification_event_id:
        v_repo = StaffVerificationRepository(db)
        event = await v_repo.get_by_id(verification_event_id)
        if event:
            org_id = event.org_id

    photo_keys: list = []
    photo_urls: list = []

    if photos:
        for photo in photos:
            if photo.filename:
                data = await photo.read()
                content_type = photo.content_type or "image/jpeg"
                rid = verification_event_id or UUID("00000000-0000-0000-0000-000000000000")
                oid = org_id or UUID("00000000-0000-0000-0000-000000000000")
                key, url = upload_fraud_photo(oid, rid, photo.filename, data, content_type)
                photo_keys.append(key)
                photo_urls.append(url)

    svc = FraudReportService(db, producer)
    report = await svc.submit_report(
        org_id=org_id,
        verification_event_id=verification_event_id,
        reporter_name=reporter_name,
        reporter_phone=reporter_phone,
        reporter_email=reporter_email,
        claimed_staff_name=claimed_staff_name,
        claimed_staff_id=claimed_staff_id,
        description=description,
        photo_keys=photo_keys or None,
        photo_urls=photo_urls or None,
    )

    return {
        "report_id": str(report.id),
        "status": report.status,
        "message": "Fraud report submitted. Thank you for helping keep your community safe.",
    }


@router.post("/feedback", response_model=StaffFeedbackOut)
async def submit_feedback(
    body: StaffFeedbackCreate,
    db: DbDep,
) -> StaffFeedback:
    """Submit feedback about a staff member after a successful verification."""
    # Validate verification event exists and is VALID
    v_repo = StaffVerificationRepository(db)
    event = await v_repo.get_by_id(body.verification_event_id)
    if not event:
        raise VerificationEventNotFoundError()
    if not event.staff_id:
        raise StaffNotFoundError(message="Cannot submit feedback: no staff associated with this verification.")

    feedback = StaffFeedback(
        verification_event_id=body.verification_event_id,
        staff_id=event.staff_id,
        org_id=event.org_id,
        feedback_type=body.feedback_type,
        comment=body.comment,
        service_type=body.service_type,
        location_description=body.location_description,
        location_lat=body.location_lat,
        location_lng=body.location_lng,
        is_anonymous=body.is_anonymous,
        submitter_name=None if body.is_anonymous else body.submitter_name,
        submitter_phone=None if body.is_anonymous else body.submitter_phone,
    )
    fb_repo = StaffFeedbackRepository(db)
    feedback = await fb_repo.create(feedback)
    log.info("staff.feedback.submitted", feedback_id=str(feedback.id), staff_id=str(feedback.staff_id))
    return feedback
