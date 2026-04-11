"""api/v1/pap.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Query, status
from core.dependencies import DbDep, KafkaDep, PAPDep, StaffDep
from models.feedback import FeedbackStatus, GRMLevel, EscalationRequestStatus
from schemas.feedback import PAPSubmitFeedback
from schemas.lifecycle import PAPEscalationRequest, PAPAppeal, PAPComment, ApproveEscalation, RejectEscalation
from services.feedback_service import FeedbackService
from api.v1.serialisers import feedback_out, escalation_request_out

router = APIRouter(tags=["PAP Portal"])
def _svc(db, kafka=None): return FeedbackService(db=db, producer=kafka)

def _status_label(status: FeedbackStatus) -> str:
    labels = {
        FeedbackStatus.SUBMITTED:    "Received — awaiting acknowledgement",
        FeedbackStatus.ACKNOWLEDGED: "Acknowledged — under review",
        FeedbackStatus.IN_REVIEW:    "Under investigation",
        FeedbackStatus.ESCALATED:    "Escalated to higher authority",
        FeedbackStatus.RESOLVED:     "Resolution provided",
        FeedbackStatus.APPEALED:     "Appeal in progress",
        FeedbackStatus.ACTIONED:     "Actioned — implemented",
        FeedbackStatus.NOTED:        "Received and noted",
        FeedbackStatus.DISMISSED:    "Closed — assessed as outside scope",
        FeedbackStatus.CLOSED:       "Closed",
    }
    return labels.get(status, status.value)

def _tracking_view(f, now):
    public_actions = [
        {"id": str(a.id), "action_type": a.action_type.value,
         "description": a.description,
         "response_method": a.response_method.value if a.response_method else None,
         "response_summary": a.response_summary,
         "performed_at": a.performed_at.isoformat(), "performed_by": "PIU / GHC"}
        for a in (f.actions or []) if not a.is_internal
    ]
    esc_trail = [
        {"from_level": e.from_level.value, "to_level": e.to_level.value,
         "reason": e.reason, "escalated_at": e.escalated_at.isoformat()}
        for e in (f.escalations or [])
    ]
    resolution = None
    if f.resolution:
        r = f.resolution
        resolution = {"summary": r.resolution_summary, "response_method": r.response_method.value,
                      "resolved_at": r.resolved_at.isoformat(), "grievant_satisfied": r.grievant_satisfied,
                      "grievant_response": r.grievant_response, "appeal_filed": r.appeal_filed}
    appeal = None
    if f.appeal:
        ap = f.appeal
        appeal = {"grounds": ap.appeal_grounds, "status": ap.appeal_status,
                  "outcome": ap.appeal_outcome, "filed_at": ap.filed_at.isoformat(),
                  "court_referral": ap.court_referral_date.isoformat() if ap.court_referral_date else None}
    ers = [
        {"id": str(er.id), "reason": er.reason, "requested_level": er.requested_level,
         "status": er.status.value,
         "reviewer_notes": er.reviewer_notes if er.status == EscalationRequestStatus.REJECTED else None,
         "requested_at": er.requested_at.isoformat(),
         "reviewed_at": er.reviewed_at.isoformat() if er.reviewed_at else None}
        for er in (f.escalation_requests or [])
    ]
    has_pending_er = any(er.status == EscalationRequestStatus.PENDING for er in (f.escalation_requests or []))
    level_order = [GRMLevel.WARD, GRMLevel.LGA_PIU, GRMLevel.PCU, GRMLevel.TARURA_WBCU, GRMLevel.TANROADS, GRMLevel.WORLD_BANK]
    open_st = {FeedbackStatus.SUBMITTED, FeedbackStatus.ACKNOWLEDGED, FeedbackStatus.IN_REVIEW, FeedbackStatus.ESCALATED, FeedbackStatus.APPEALED}
    can_esc = (f.status not in (FeedbackStatus.CLOSED, FeedbackStatus.DISMISSED, FeedbackStatus.RESOLVED)
               and f.current_level != GRMLevel.WORLD_BANK and not has_pending_er)
    can_ap  = (f.status == FeedbackStatus.RESOLVED and f.resolution is not None
               and f.resolution.grievant_satisfied is not True and f.appeal is None)
    return {
        "id": str(f.id), "unique_ref": f.unique_ref, "feedback_type": f.feedback_type.value,
        "category": f.category.value, "subject": f.subject, "description": f.description,
        "channel": f.channel.value,
        "submission_method": f.submission_method.value if f.submission_method else None,
        "is_anonymous": f.is_anonymous, "project_id": str(f.project_id),
        "current_level": f.current_level.value if f.current_level else None,
        "priority": f.priority.value if f.priority else None,
        "status": f.status.value, "status_label": _status_label(f.status),
        "issue_location_description": f.issue_location_description,
        "issue_lga": f.issue_lga,
        "issue_ward": f.issue_ward,
        "issue_gps_lat": f.issue_gps_lat,
        "issue_gps_lng": f.issue_gps_lng,
        "submitted_at": f.submitted_at.isoformat(),
        "acknowledged_at": f.acknowledged_at.isoformat() if f.acknowledged_at else None,
        "target_resolution_date": f.target_resolution_date.isoformat() if f.target_resolution_date else None,
        "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
        "closed_at": f.closed_at.isoformat() if f.closed_at else None,
        "hours_open": round((now - f.submitted_at).total_seconds() / 3600, 1),
        "public_actions": public_actions, "escalation_trail": esc_trail,
        "resolution": resolution, "appeal": appeal, "escalation_requests": ers,
        "can_request_escalation": can_esc, "can_appeal": can_ap,
        "can_add_comment": f.status not in (FeedbackStatus.CLOSED, FeedbackStatus.DISMISSED),
    }

@router.get("/my/feedback", status_code=status.HTTP_200_OK, summary="List all my feedback submissions")
async def my_feedback_list(
    db: DbDep, kafka: KafkaDep, token: PAPDep,
    feedback_type: Optional[str] = Query(default=None),
    status_: Optional[str] = Query(default=None, alias="status"),
    project_id: Optional[uuid.UUID] = Query(default=None),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    stakeholder_id = getattr(token, "stakeholder_id", None)
    items = await _svc(db, kafka).list_for_pap(
        user_id=token.sub, stakeholder_id=stakeholder_id,
        feedback_type=feedback_type, status=status_, project_id=project_id,
        skip=skip, limit=limit,
    )
    return {
        "items": [{
            "id": str(f.id), "unique_ref": f.unique_ref,
            "feedback_type": f.feedback_type.value, "category": f.category.value,
            "subject": f.subject, "channel": f.channel.value, "status": f.status.value,
            "status_label": _status_label(f.status),
            "current_level": f.current_level.value if f.current_level else None,
            "priority": f.priority.value if f.priority else None,
            "submitted_at": f.submitted_at.isoformat(),
            "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
            "project_id": str(f.project_id),
        } for f in items],
        "count": len(items),
    }

@router.get("/my/feedback/summary", status_code=status.HTTP_200_OK, summary="My feedback summary — counts for the dashboard widget")
async def my_feedback_summary(db: DbDep, kafka: KafkaDep, token: PAPDep, project_id: Optional[uuid.UUID] = Query(default=None)) -> dict:
    stakeholder_id = getattr(token, "stakeholder_id", None)
    items = await _svc(db, kafka).list_for_pap(user_id=token.sub, stakeholder_id=stakeholder_id, project_id=project_id)
    open_st = {FeedbackStatus.SUBMITTED, FeedbackStatus.ACKNOWLEDGED, FeedbackStatus.IN_REVIEW, FeedbackStatus.ESCALATED, FeedbackStatus.APPEALED}
    by_type: dict = {}
    by_status: dict = {}
    for f in items:
        by_type[f.feedback_type.value]  = by_type.get(f.feedback_type.value, 0) + 1
        by_status[f.status.value]       = by_status.get(f.status.value, 0) + 1
    pending_ers = await _svc(db, kafka).count_pending_escalation_requests(token.sub)
    return {
        "total":    len(items),
        "open":     sum(1 for f in items if f.status in open_st),
        "resolved": sum(1 for f in items if f.status in (FeedbackStatus.RESOLVED, FeedbackStatus.ACTIONED, FeedbackStatus.NOTED)),
        "closed":   sum(1 for f in items if f.status == FeedbackStatus.CLOSED),
        "by_type":  [{"type": k, "count": v} for k, v in by_type.items()],
        "by_status": [{"status": k, "label": _status_label(FeedbackStatus(k)), "count": v} for k, v in sorted(by_status.items())],
        "pending_escalation_requests": pending_ers,
    }

@router.get("/my/feedback/{feedback_id}", status_code=status.HTTP_200_OK, summary="Track a specific submission — full handling history")
async def my_feedback_detail(feedback_id: uuid.UUID, db: DbDep, kafka: KafkaDep, token: PAPDep) -> dict:
    now = datetime.now(timezone.utc)
    stakeholder_id = getattr(token, "stakeholder_id", None)
    f = await _svc(db, kafka).get_for_pap_or_404(feedback_id, token.sub, stakeholder_id)
    return _tracking_view(f, now)

@router.post(
    "/my/feedback",
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new grievance, suggestion, or applause",
    description=(
        "PAP self-service submission. Channel is auto-set to web_portal.\n\n"
        "**project_id** is optional — the AI auto-detects it from `issue_lga` + `description`. "
        "**category** is optional — the AI classifies it from the description.\n\n"
        "If the project cannot be identified automatically, HTTP 422 is returned with "
        "`detail.candidate_projects` — a ranked list of matching projects for the frontend "
        "to present as a picker. Re-submit with the chosen `project_id` to complete the submission."
    ),
    responses={
        422: {
            "description": "Project could not be auto-identified. `detail.candidate_projects` contains a ranked list to show the user.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "We could not automatically identify the project for your location. Please select the correct project from the list below.",
                        "detail": {
                            "error_code": "PROJECT_UNIDENTIFIED",
                            "candidate_projects": [
                                {"project_id": "...", "name": "Dodoma Road Project", "region": "Dodoma", "lga": "Bahi", "score": 0.72}
                            ]
                        }
                    }
                }
            }
        }
    },
)
async def pap_submit_feedback(body: PAPSubmitFeedback, db: DbDep, kafka: KafkaDep, token: PAPDep) -> dict:
    data = body.model_dump(exclude_none=True)
    f = await _svc(db, kafka).submit_from_pap(data, user_id=token.sub, channel_override="web_portal")
    return {
        "feedback_id":    str(f.id),
        "tracking_number": f.unique_ref,
        "status":         f.status.value,
        "status_label":   _status_label(f.status),
        "feedback_type":  f.feedback_type.value,
        "ai_classified":  not bool(body.project_id),   # true when AI detected the project
        "message": (
            f"Your {f.feedback_type.value} has been submitted successfully. "
            f"Tracking number: {f.unique_ref}. "
            "You will be notified when the PIU acknowledges receipt."
        ),
    }

@router.post("/my/feedback/{feedback_id}/escalation-request", status_code=status.HTTP_201_CREATED, summary="Request PIU to escalate your grievance to a higher GRM level")
async def request_escalation(feedback_id: uuid.UUID, body: PAPEscalationRequest, db: DbDep, kafka: KafkaDep, token: PAPDep) -> dict:
    stakeholder_id = getattr(token, "stakeholder_id", None)
    er = await _svc(db, kafka).request_escalation(feedback_id, body.model_dump(exclude_none=True), user_id=token.sub, stakeholder_id=stakeholder_id)
    return {
        "id": str(er.id), "status": er.status.value,
        "message": ("Your escalation request has been submitted. "
                    "PIU will review it and either approve (and escalate your case) "
                    "or explain why escalation is not applicable at this stage."),
    }

@router.post("/my/feedback/{feedback_id}/appeal", status_code=status.HTTP_201_CREATED, summary="File a formal appeal against an unsatisfactory resolution")
async def pap_appeal(feedback_id: uuid.UUID, body: PAPAppeal, db: DbDep, kafka: KafkaDep, token: PAPDep) -> dict:
    stakeholder_id = getattr(token, "stakeholder_id", None)
    f, appeal = await _svc(db, kafka).pap_appeal(feedback_id, body.model_dump(exclude_none=True), user_id=token.sub, stakeholder_id=stakeholder_id)
    return {
        "appeal_id": str(appeal.id), "status": f.status.value,
        "now_at_level": f.current_level.value,
        "message": (f"Your appeal has been filed. Your case has been escalated to "
                    f"{f.current_level.value.replace('_', ' ').upper()} for review. "
                    "If you remain unsatisfied after the appeal outcome, you have "
                    "the right to seek resolution through the courts."),
    }

@router.post("/my/feedback/{feedback_id}/add-comment", status_code=status.HTTP_201_CREATED, summary="Add a follow-up comment to your submission")
async def pap_add_comment(feedback_id: uuid.UUID, body: PAPComment, db: DbDep, kafka: KafkaDep, token: PAPDep) -> dict:
    stakeholder_id = getattr(token, "stakeholder_id", None)
    action = await _svc(db, kafka).pap_add_comment(feedback_id, body.model_dump(exclude_none=True), user_id=token.sub, stakeholder_id=stakeholder_id)
    return {"message": "Your comment has been added and is visible to PIU staff.", "action_id": str(action.id)}

@router.get("/escalation-requests", status_code=status.HTTP_200_OK, summary="[Staff] List PAP escalation requests")
async def list_escalation_requests(
    db: DbDep, kafka: KafkaDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    status_: Optional[str] = Query(default="pending", alias="status"),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    items = await _svc(db, kafka).list_escalation_requests(status=status_, project_id=project_id, skip=skip, limit=limit)
    return {"items": [escalation_request_out(er) for er in items], "count": len(items)}

@router.post("/escalation-requests/{request_id}/approve", status_code=status.HTTP_200_OK, summary="[Staff] Approve a PAP escalation request")
async def approve_escalation_request(request_id: uuid.UUID, body: ApproveEscalation, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    er = await _svc(db, kafka).approve_escalation_request(request_id, body.model_dump(exclude_none=True), by=token.sub)
    return {"status": er.status.value, "message": "Escalation request approved.", "feedback_id": str(er.feedback_id)}

@router.post("/escalation-requests/{request_id}/reject", status_code=status.HTTP_200_OK, summary="[Staff] Reject a PAP escalation request with explanation")
async def reject_escalation_request(request_id: uuid.UUID, body: RejectEscalation, db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    er = await _svc(db, kafka).reject_escalation_request(request_id, body.model_dump(exclude_none=True), by=token.sub)
    return {"status": er.status.value, "message": "Escalation request rejected. The PAP has been notified."}
