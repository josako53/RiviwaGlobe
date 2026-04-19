"""api/v1/feedback.py — HTTP orchestration only"""
from __future__ import annotations
import csv
import io
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Query, Request, UploadFile, status
from core.dependencies import DbDep, KafkaDep, StaffDep, GRMOfficerDep, GRMCoordinatorDep, OptTokenDep
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
async def submit_feedback(body: StaffSubmitFeedback, db: DbDep, kafka: KafkaDep, token: GRMOfficerDep) -> dict:
    """
    Submit a single feedback record. Staff can backdate by setting `submitted_at`
    for historical records (paper forms, past complaints).
    Requires org role manager/admin/owner or platform admin.
    """
    return feedback_out(await _svc(db, kafka).submit(body.model_dump(exclude_none=True), token_sub=token.sub))


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

@router.get("", summary="List feedback records [staff — org-scoped]")
async def list_feedback(
    db: DbDep, kafka: KafkaDep, token: StaffDep,
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
    # Platform admins see all orgs; org staff see only their org's feedback
    from core.dependencies import _is_platform_admin
    org_id = None if _is_platform_admin(token) else token.org_id
    items = await _svc(db, kafka).list(
        org_id=org_id,
        project_id=project_id, feedback_type=feedback_type, status=status_,
        priority=priority, current_level=current_level, category=category, lga=lga,
        is_anonymous=is_anonymous, submission_method=submission_method, channel=channel,
        submitted_by_stakeholder_id=submitted_by_stakeholder_id,
        assigned_committee_id=assigned_committee_id, skip=skip, limit=limit,
    )
    return {"items": [feedback_out(f) for f in items], "count": len(items)}

@router.get("/{feedback_id}", summary="Feedback detail with full history")
async def get_feedback(feedback_id: uuid.UUID, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    from core.dependencies import _is_platform_admin
    org_id = None if _is_platform_admin(token) else token.org_id
    f = await _svc(db, kafka).get_with_history_or_404(feedback_id, org_id=org_id)
    return {
        **feedback_out(f),
        "actions":     [action_out(a) for a in sorted(f.actions, key=lambda x: x.performed_at)],
        "escalations": [esc_out(e) for e in sorted(f.escalations, key=lambda x: x.escalated_at)],
        "resolution":  resolution_out(f.resolution) if f.resolution else None,
        "appeal":      appeal_out(f.appeal) if f.appeal else None,
    }

@router.patch("/{feedback_id}/acknowledge", summary="Acknowledge receipt [manager+]")
async def acknowledge_feedback(feedback_id: uuid.UUID, body: AcknowledgeFeedback, db: DbDep, kafka: KafkaDep, token: GRMOfficerDep) -> dict:
    from core.dependencies import _is_platform_admin
    org_id = None if _is_platform_admin(token) else token.org_id
    return feedback_out(await _svc(db, kafka).acknowledge(feedback_id, body.model_dump(exclude_none=True), by=token.sub, org_id=org_id))

@router.patch("/{feedback_id}/assign", summary="Assign to staff member or committee [manager+]")
async def assign_feedback(feedback_id: uuid.UUID, body: AssignFeedback, db: DbDep, kafka: KafkaDep, token: GRMOfficerDep) -> dict:
    from core.dependencies import _is_platform_admin
    org_id = None if _is_platform_admin(token) else token.org_id
    return feedback_out(await _svc(db, kafka).assign(feedback_id, body.model_dump(exclude_none=True), by=token.sub, org_id=org_id))

@router.post("/{feedback_id}/escalate", status_code=status.HTTP_200_OK, summary="Escalate to next GRM level [manager+]")
async def escalate_feedback(feedback_id: uuid.UUID, body: EscalateFeedback, db: DbDep, kafka: KafkaDep, token: GRMOfficerDep) -> dict:
    from core.dependencies import _is_platform_admin
    org_id = None if _is_platform_admin(token) else token.org_id
    return feedback_out(await _svc(db, kafka).escalate(feedback_id, body.model_dump(exclude_none=True), by=token.sub, org_id=org_id))

@router.post("/{feedback_id}/resolve", status_code=status.HTTP_200_OK, summary="Record resolution [manager+]")
async def resolve_feedback(feedback_id: uuid.UUID, body: ResolveFeedback, db: DbDep, kafka: KafkaDep, token: GRMOfficerDep) -> dict:
    from core.dependencies import _is_platform_admin
    org_id = None if _is_platform_admin(token) else token.org_id
    return feedback_out(await _svc(db, kafka).resolve(feedback_id, body.model_dump(exclude_none=True), by=token.sub, org_id=org_id))

@router.post("/{feedback_id}/appeal", status_code=status.HTTP_200_OK, summary="File appeal against resolution [manager+]")
async def file_appeal(feedback_id: uuid.UUID, body: AppealFeedback, db: DbDep, kafka: KafkaDep, token: GRMOfficerDep) -> dict:
    from core.dependencies import _is_platform_admin
    org_id = None if _is_platform_admin(token) else token.org_id
    return feedback_out(await _svc(db, kafka).appeal(feedback_id, body.model_dump(exclude_none=True), by=token.sub, org_id=org_id))

@router.patch("/{feedback_id}/close", summary="Close feedback [manager+]")
async def close_feedback(feedback_id: uuid.UUID, body: CloseFeedback, db: DbDep, kafka: KafkaDep, token: GRMOfficerDep) -> dict:
    from core.dependencies import _is_platform_admin
    org_id = None if _is_platform_admin(token) else token.org_id
    return feedback_out(await _svc(db, kafka).close(feedback_id, body.model_dump(exclude_none=True), by=token.sub, org_id=org_id))

@router.patch("/{feedback_id}/dismiss", summary="Dismiss feedback [admin/owner only]")
async def dismiss_feedback(feedback_id: uuid.UUID, body: DismissFeedback, db: DbDep, kafka: KafkaDep, token: GRMCoordinatorDep) -> dict:
    from core.dependencies import _is_platform_admin
    org_id = None if _is_platform_admin(token) else token.org_id
    return feedback_out(await _svc(db, kafka).dismiss(feedback_id, body.model_dump(exclude_none=True), by=token.sub, org_id=org_id))


# ── Internal AI enrichment endpoint ───────────────────────────────────────────
# Called by ai_service after classifying feedback with Ollama + RAG.
# Secured by X-Service-Key header — no JWT required.

@router.get(
    "/by-ref/{unique_ref}",
    status_code=status.HTTP_200_OK,
    summary="Look up feedback status by reference number (internal service only)",
    include_in_schema=False,
)
async def get_feedback_by_ref_internal(unique_ref: str, request: Request, db: DbDep, kafka: KafkaDep) -> dict:
    """Internal: no JWT. Used by ai_service for Consumer follow-up status queries."""
    from fastapi.responses import JSONResponse
    from core.config import settings
    from sqlmodel import select
    from models.feedback import Feedback

    service_key = request.headers.get("X-Service-Key", "")
    if service_key != settings.INTERNAL_SERVICE_KEY:
        return JSONResponse(status_code=403, content={"error": "FORBIDDEN", "message": "Invalid service key."})

    result = await db.execute(
        select(Feedback).where(Feedback.unique_ref == unique_ref.upper()).limit(1)
    )
    f = result.scalar_one_or_none()
    if not f:
        return JSONResponse(status_code=404, content={"error": "NOT_FOUND", "message": "Reference not found."})

    return {
        "id":          str(f.id),
        "unique_ref":  f.unique_ref,
        "status":      f.status.value if f.status else None,
        "feedback_type": f.feedback_type.value if f.feedback_type else None,
        "subject":     f.subject,
        "description": (f.description or "")[:150],
        "submitted_at": f.submitted_at.isoformat() if f.submitted_at else None,
        "resolved_at":  f.resolved_at.isoformat() if f.resolved_at else None,
    }


@router.get(
    "/{feedback_id}/for-ai",
    status_code=status.HTTP_200_OK,
    summary="Fetch feedback data for AI classification (internal service only)",
    include_in_schema=False,
)
async def get_feedback_for_ai(feedback_id: uuid.UUID, request: Request, db: DbDep, kafka: KafkaDep) -> dict:
    """
    Internal-only. Returns the fields ai_service needs to classify a feedback record.
    Requires X-Service-Key header — no JWT needed.
    """
    from fastapi.responses import JSONResponse
    from core.config import settings
    from sqlmodel import select
    from models.feedback import Feedback

    service_key = request.headers.get("X-Service-Key", "")
    if service_key != settings.INTERNAL_SERVICE_KEY:
        return JSONResponse(status_code=403, content={"error": "FORBIDDEN", "message": "Invalid service key."})

    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    f = result.scalar_one_or_none()
    if not f:
        return JSONResponse(status_code=404, content={"error": "NOT_FOUND", "message": "Feedback not found."})

    return {
        "id":                          str(f.id),
        "project_id":                  str(f.project_id) if f.project_id else None,
        "category_def_id":             str(f.category_def_id) if f.category_def_id else None,
        "feedback_type":               f.feedback_type.value if f.feedback_type else None,
        "category":                    f.category.value if f.category else None,
        "subject":                     f.subject,
        "description":                 f.description,
        "issue_location_description":  f.issue_location_description,
        "issue_region":                f.issue_region,
        "issue_district":              f.issue_district,
        "issue_lga":                   f.issue_lga,
        "issue_ward":                  f.issue_ward,
        "issue_mtaa":                  f.issue_mtaa,
        "submitted_at":                f.submitted_at.isoformat() if f.submitted_at else None,
    }


@router.patch(
    "/{feedback_id}/ai-enrich",
    status_code=status.HTTP_200_OK,
    summary="AI enrichment: set project_id and/or category_def_id (internal service only)",
    include_in_schema=False,  # hidden from public docs
)
async def ai_enrich_feedback(feedback_id: uuid.UUID, request: Request, db: DbDep, kafka: KafkaDep) -> dict:
    """
    Internal-only endpoint called by ai_service to backfill:
      - project_id  — when feedback was submitted without one
      - category_def_id — auto-classified by Ollama
    Requires X-Service-Key header matching INTERNAL_SERVICE_KEY.
    """
    from fastapi.responses import JSONResponse
    from core.config import settings
    from sqlmodel import select
    from models.feedback import Feedback, FeedbackAction, ActionType
    from datetime import datetime, timezone

    # Validate internal service key
    service_key = request.headers.get("X-Service-Key", "")
    if service_key != settings.INTERNAL_SERVICE_KEY:
        return JSONResponse(status_code=403, content={"error": "FORBIDDEN", "message": "Invalid service key."})

    body = await request.json()
    project_id_raw      = body.get("project_id")
    category_def_id_raw = body.get("category_def_id")
    note                = body.get("note", "Auto-enriched by AI service (Ollama classification)")

    if not project_id_raw and not category_def_id_raw:
        return {"enriched": False, "reason": "Nothing to update"}

    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    f = result.scalar_one_or_none()
    if not f:
        return JSONResponse(status_code=404, content={"error": "NOT_FOUND", "message": "Feedback not found."})

    changed = False
    if project_id_raw and not f.project_id:
        f.project_id = uuid.UUID(str(project_id_raw))
        changed = True
    if category_def_id_raw and not f.category_def_id:
        f.category_def_id = uuid.UUID(str(category_def_id_raw))
        changed = True

    if changed:
        action = FeedbackAction(
            feedback_id=f.id,
            action_type=ActionType.NOTE,
            description=note,
            is_internal=True,
            performed_at=datetime.now(timezone.utc),
        )
        db.add(f)
        db.add(action)
        await db.flush()

    return {"enriched": changed, "feedback_id": str(feedback_id)}
