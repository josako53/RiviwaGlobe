"""api/v1/feedback.py — HTTP orchestration only"""
from __future__ import annotations
import csv
import io
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Query, UploadFile, status
from core.dependencies import DbDep, KafkaDep, StaffDep, OptTokenDep
from schemas.feedback import BulkUploadResult, StaffSubmitFeedback
from schemas.lifecycle import (
    AcknowledgeFeedback, AssignFeedback, EscalateFeedback,
    ResolveFeedback, AppealFeedback, CloseFeedback, DismissFeedback, LogAction,
)
from services.feedback_service import FeedbackService
from api.v1.serialisers import feedback_out, action_out, esc_out, resolution_out, appeal_out

router = APIRouter(prefix="/feedback", tags=["Feedback"])
def _svc(db, kafka): return FeedbackService(db=db, producer=kafka)

@router.post("", status_code=status.HTTP_201_CREATED, summary="Submit feedback (grievance / suggestion / applause)")
async def submit_feedback(body: StaffSubmitFeedback, db: DbDep, kafka: KafkaDep, token: OptTokenDep) -> dict:
    """
    Submit a single feedback record. Staff can backdate by setting `submitted_at`
    for historical records (paper forms, past complaints).
    """
    return feedback_out(await _svc(db, kafka).submit(body.model_dump(exclude_none=True), token_sub=token.sub if token else None))


@router.post(
    "/bulk-upload",
    status_code=status.HTTP_200_OK,
    response_model=BulkUploadResult,
    summary="Bulk import feedback from CSV file",
    description=(
        "Upload a CSV file to import multiple feedback records at once. "
        "Each row becomes a separate feedback submission. Failed rows are skipped "
        "and reported in the response — successful rows are not affected.\n\n"
        "**CSV columns** (header row required):\n"
        "- `project_id` (required) — UUID of the project\n"
        "- `feedback_type` (required) — grievance | suggestion | applause\n"
        "- `category` (required) — compensation, construction_impact, safety, design, quality, other, etc.\n"
        "- `subject` (required) — short summary\n"
        "- `description` (required) — detailed description\n"
        "- `channel` — paper_form (default), in_person, email, public_meeting, notice_box, sms, other\n"
        "- `priority` — critical, high, medium (default), low\n"
        "- `submitter_name` — name of the person (blank for anonymous)\n"
        "- `submitter_phone` — phone number (E.164)\n"
        "- `is_anonymous` — true/false (default: false)\n"
        "- `issue_lga` — LGA where the issue occurred\n"
        "- `issue_ward` — ward where the issue occurred\n"
        "- `issue_gps_lat` / `issue_gps_lng` — GPS coordinates\n"
        "- `date_of_incident` — YYYY-MM-DD when the issue happened\n"
        "- `submitted_at` — YYYY-MM-DD for backdating (defaults to today)\n\n"
        "**Supported formats**: CSV (UTF-8, comma-separated). Max 1000 rows per upload."
    ),
    tags=["Feedback", "Bulk Import"],
)
async def bulk_upload_feedback(
    file: UploadFile = File(..., description="CSV file (UTF-8, max 1000 rows)"),
    db: DbDep = None,
    kafka: KafkaDep = None,
    token: StaffDep = None,
) -> BulkUploadResult:
    content = await file.read()

    # Try UTF-8, fall back to latin-1
    try:
        text = content.decode("utf-8-sig")  # handles BOM
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if len(rows) > 1000:
        return BulkUploadResult(
            total_rows=len(rows), created=0, skipped=len(rows),
            errors=[{"row": 0, "error": f"Too many rows ({len(rows)}). Maximum is 1000 per upload."}],
        )

    if not rows:
        return BulkUploadResult(
            total_rows=0, created=0, skipped=0,
            errors=[{"row": 0, "error": "CSV file is empty or has no data rows."}],
        )

    result = await _svc(db, kafka).bulk_submit(rows, token_sub=token.sub)
    return BulkUploadResult(**result)

@router.get("", summary="List feedback records [staff]")
async def list_feedback(
    db: DbDep, kafka: KafkaDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    feedback_type: Optional[str] = Query(default=None),
    status_: Optional[str] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    current_level: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    lga: Optional[str] = Query(default=None),
    is_anonymous: Optional[bool] = Query(default=None),
    submission_method: Optional[str] = Query(default=None),
    channel: Optional[str] = Query(default=None),
    submitted_by_stakeholder_id: Optional[uuid.UUID] = Query(default=None),
    assigned_committee_id: Optional[uuid.UUID] = Query(default=None),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    items = await _svc(db, kafka).list(
        project_id=project_id, feedback_type=feedback_type, status=status_,
        priority=priority, current_level=current_level, category=category, lga=lga,
        is_anonymous=is_anonymous, submission_method=submission_method, channel=channel,
        submitted_by_stakeholder_id=submitted_by_stakeholder_id,
        assigned_committee_id=assigned_committee_id, skip=skip, limit=limit,
    )
    return {"items": [feedback_out(f) for f in items], "count": len(items)}

@router.get("/{feedback_id}", summary="Feedback detail with full history")
async def get_feedback(feedback_id: uuid.UUID, db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    f = await _svc(db, kafka).get_with_history_or_404(feedback_id)
    return {
        **feedback_out(f),
        "actions":     [action_out(a) for a in sorted(f.actions, key=lambda x: x.performed_at)],
        "escalations": [esc_out(e) for e in sorted(f.escalations, key=lambda x: x.escalated_at)],
        "resolution":  resolution_out(f.resolution) if f.resolution else None,
        "appeal":      appeal_out(f.appeal) if f.appeal else None,
    }

@router.patch("/{feedback_id}/acknowledge", summary="Acknowledge receipt")
async def acknowledge_feedback(feedback_id: uuid.UUID, body: AcknowledgeFeedback, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).acknowledge(feedback_id, body.model_dump(exclude_none=True), by=token.sub))

@router.patch("/{feedback_id}/assign", summary="Assign to staff member or committee")
async def assign_feedback(feedback_id: uuid.UUID, body: AssignFeedback, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).assign(feedback_id, body.model_dump(exclude_none=True), by=token.sub))

@router.post("/{feedback_id}/escalate", status_code=status.HTTP_200_OK, summary="Escalate to next GRM level")
async def escalate_feedback(feedback_id: uuid.UUID, body: EscalateFeedback, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).escalate(feedback_id, body.model_dump(exclude_none=True), by=token.sub))

@router.post("/{feedback_id}/resolve", status_code=status.HTTP_200_OK, summary="Record resolution")
async def resolve_feedback(feedback_id: uuid.UUID, body: ResolveFeedback, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).resolve(feedback_id, body.model_dump(exclude_none=True), by=token.sub))

@router.post("/{feedback_id}/appeal", status_code=status.HTTP_200_OK, summary="File appeal against resolution")
async def file_appeal(feedback_id: uuid.UUID, body: AppealFeedback, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).appeal(feedback_id, body.model_dump(exclude_none=True), by=token.sub))

@router.patch("/{feedback_id}/close", summary="Close feedback [final state]")
async def close_feedback(feedback_id: uuid.UUID, body: CloseFeedback, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).close(feedback_id, body.model_dump(exclude_none=True), by=token.sub))

@router.patch("/{feedback_id}/dismiss", summary="Dismiss feedback")
async def dismiss_feedback(feedback_id: uuid.UUID, body: DismissFeedback, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return feedback_out(await _svc(db, kafka).dismiss(feedback_id, body.model_dump(exclude_none=True), by=token.sub))
