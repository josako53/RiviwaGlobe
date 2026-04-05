"""
services/feedback_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for the full GRM lifecycle:
  submit → acknowledge → assign → escalate → resolve → appeal → close/dismiss.
Also handles: action logging, escalation request review (staff).
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    AppealError,
    EscalationError,
    FeedbackClosedError,
    FeedbackNotFoundError,
    ProjectNotFoundError,
    ProjectNotAcceptingFeedbackError,
    ResolutionError,
    ValidationError,
)
from events.producer import FeedbackProducer
from models.feedback import (
    ActionType,
    EscalationRequest,
    EscalationRequestStatus,
    Feedback,
    FeedbackAction,
    FeedbackAppeal,
    FeedbackCategory,
    FeedbackChannel,
    FeedbackEscalation,
    FeedbackPriority,
    FeedbackResolution,
    FeedbackStatus,
    FeedbackType,
    GRMLevel,
    ResponseMethod,
    SubmissionMethod,
)
from repositories.feedback_repository import FeedbackRepository

_PREFIX = {
    FeedbackType.GRIEVANCE:  "GRV",
    FeedbackType.SUGGESTION: "SGG",
    FeedbackType.APPLAUSE:   "APP",
}

_LEVEL_ORDER = [
    GRMLevel.WARD, GRMLevel.LGA_PIU, GRMLevel.PCU,
    GRMLevel.TARURA_WBCU, GRMLevel.TANROADS, GRMLevel.WORLD_BANK,
]


class FeedbackService:

    def __init__(self, db: AsyncSession, producer: FeedbackProducer) -> None:
        self.repo     = FeedbackRepository(db)
        self.producer = producer
        self.db       = db

    # ── Submit ────────────────────────────────────────────────────────────────

    async def submit(self, data: dict, token_sub: Optional[uuid.UUID] = None) -> Feedback:
        project_id = uuid.UUID(data["project_id"])
        project = await self.repo.get_project(project_id)
        if not project:
            raise ProjectNotFoundError()

        feedback_type = FeedbackType(data["feedback_type"])
        if not project.accepts_feedback_type(feedback_type.value):
            raise ProjectNotAcceptingFeedbackError(
                message=f"This project is not currently accepting {feedback_type.value} submissions."
            )

        count = await self.repo.count_for_project(project_id)
        unique_ref = f"{_PREFIX[feedback_type]}-{datetime.now().year}-{count + 1:04d}"
        active_stage = project.active_stage()
        is_anon = bool(data.get("is_anonymous", False))

        f = Feedback(
            unique_ref                   = unique_ref,
            project_id                   = project_id,
            stage_id                     = active_stage.id if active_stage else None,
            service_location_id          = uuid.UUID(data["service_location_id"]) if data.get("service_location_id") else None,
            feedback_type                = feedback_type,
            category                     = FeedbackCategory(data["category"]),
            status                       = FeedbackStatus.SUBMITTED,
            priority                     = FeedbackPriority(data.get("priority", "medium")),
            current_level                = GRMLevel.WARD,
            channel                      = FeedbackChannel(data["channel"]),
            is_anonymous                 = is_anon,
            submitted_by_user_id         = None if is_anon else (token_sub or (uuid.UUID(data["submitted_by_user_id"]) if data.get("submitted_by_user_id") else None)),
            submitted_by_stakeholder_id  = None if is_anon else (uuid.UUID(data["submitted_by_stakeholder_id"]) if data.get("submitted_by_stakeholder_id") else None),
            submitted_by_contact_id      = None if is_anon else (uuid.UUID(data["submitted_by_contact_id"]) if data.get("submitted_by_contact_id") else None),
            submitter_name               = None if is_anon else data.get("submitter_name"),
            submitter_phone              = None if is_anon else data.get("submitter_phone"),
            submitter_location_lga       = None if is_anon else data.get("submitter_location_lga"),
            submitter_location_ward      = None if is_anon else data.get("submitter_location_ward"),
            entered_by_user_id           = None if is_anon else (token_sub if data.get("officer_recorded") else None),
            stakeholder_engagement_id    = uuid.UUID(data["stakeholder_engagement_id"]) if data.get("stakeholder_engagement_id") else None,
            distribution_id              = uuid.UUID(data["distribution_id"]) if data.get("distribution_id") else None,
            subject                      = data["subject"],
            description                  = data["description"],
            media_urls                   = data.get("media_urls"),
            issue_location_description   = data.get("issue_location_description"),
            issue_lga                    = data.get("issue_lga"),
            issue_ward                   = data.get("issue_ward"),
            issue_gps_lat                = data.get("issue_gps_lat"),
            issue_gps_lng                = data.get("issue_gps_lng"),
            date_of_incident             = datetime.fromisoformat(data["date_of_incident"]) if data.get("date_of_incident") else None,
        )
        f = await self.repo.create(f)
        await self.db.commit()

        await self.producer.feedback_submitted(
            f.id, f.project_id, f.feedback_type.value, f.category.value,
            stakeholder_engagement_id=f.stakeholder_engagement_id,
            distribution_id=f.distribution_id,
        )
        return f

    async def submit_from_pap(
        self, data: dict, user_id: uuid.UUID
    ) -> Feedback:
        project_id = uuid.UUID(data["project_id"])
        project = await self.repo.get_project(project_id)
        if not project:
            raise ValidationError("Project not found or not active.")

        fb_type = FeedbackType(data["feedback_type"])
        if fb_type == FeedbackType.GRIEVANCE and not project.accepts_grievances:
            raise ValidationError("This project is not currently accepting grievances.")
        if fb_type == FeedbackType.SUGGESTION and not project.accepts_suggestions:
            raise ValidationError("This project is not currently accepting suggestions.")
        if fb_type == FeedbackType.APPLAUSE and not project.accepts_applause:
            raise ValidationError("This project is not currently accepting applause.")

        count     = await self.repo.count_for_project(project_id)
        prefix    = _PREFIX[fb_type]
        unique_ref = f"{prefix}-{datetime.now().year}-{count + 1:04d}"
        is_anon   = bool(data.get("is_anonymous", False))

        f = Feedback(
            unique_ref          = unique_ref,
            project_id          = project_id,
            feedback_type       = fb_type,
            category            = FeedbackCategory(data.get("category", "other")),
            status              = FeedbackStatus.SUBMITTED,
            priority            = FeedbackPriority.MEDIUM,
            current_level       = GRMLevel.WARD,
            channel             = FeedbackChannel(data.get("channel", "web_portal")),
            submission_method   = SubmissionMethod.SELF_SERVICE,
            is_anonymous        = is_anon,
            submitted_by_user_id = None if is_anon else user_id,
            subject             = data.get("subject") or data.get("description", "")[:100],
            description         = data["description"],
            issue_lga           = data.get("issue_lga"),
            issue_ward          = data.get("issue_ward"),
            submitter_name      = None if is_anon else data.get("submitter_name"),
            submitter_phone     = None if is_anon else data.get("submitter_phone"),
        )
        f = await self.repo.create(f)
        await self.db.commit()
        return f

    # ── Fetch ─────────────────────────────────────────────────────────────────

    async def get_or_404(self, feedback_id: uuid.UUID, load_relations=False) -> Feedback:
        f = await self.repo.get_by_id(feedback_id, load_relations=load_relations)
        if not f:
            raise FeedbackNotFoundError()
        return f

    async def get_with_history_or_404(self, feedback_id: uuid.UUID) -> Feedback:
        f = await self.repo.get_with_history(feedback_id)
        if not f:
            raise FeedbackNotFoundError()
        return f

    async def list(self, **filters) -> list[Feedback]:
        return await self.repo.list(**filters)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def acknowledge(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> Feedback:
        f = await self.get_or_404(feedback_id)
        self._assert_open(f)
        f.status          = FeedbackStatus.ACKNOWLEDGED
        f.priority        = FeedbackPriority(data.get("priority", f.priority.value))
        f.acknowledged_at = datetime.now(timezone.utc)
        if data.get("assigned_to_user_id"):
            f.assigned_to_user_id = uuid.UUID(data["assigned_to_user_id"])
        if data.get("target_resolution_date"):
            f.target_resolution_date = datetime.fromisoformat(data["target_resolution_date"])
        action = FeedbackAction(
            feedback_id=f.id, action_type=ActionType.ACKNOWLEDGEMENT,
            description=data.get("note", f"Feedback {f.unique_ref} acknowledged."),
            response_method=ResponseMethod(data["response_method"]) if data.get("response_method") else None,
            response_summary=data.get("response_summary"),
            is_internal=False, performed_by_user_id=by,
        )
        await self.repo.save(f)
        await self.repo.create_action(action)
        await self.db.commit()
        await self.producer.feedback_acknowledged(f.id, f.project_id, f.priority.value)
        return f

    async def assign(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> Feedback:
        f = await self.get_or_404(feedback_id)
        self._assert_open(f)
        if data.get("assigned_to_user_id"):
            f.assigned_to_user_id = uuid.UUID(data["assigned_to_user_id"])
        if data.get("assigned_committee_id"):
            f.assigned_committee_id = uuid.UUID(data["assigned_committee_id"])
        if f.status == FeedbackStatus.SUBMITTED:
            f.status = FeedbackStatus.IN_REVIEW
        action = FeedbackAction(
            feedback_id=f.id, action_type=ActionType.INTERNAL_REVIEW,
            description=data.get("note", "Feedback assigned."),
            is_internal=True, performed_by_user_id=by,
        )
        await self.repo.save(f)
        await self.repo.create_action(action)
        await self.db.commit()
        return f

    async def escalate(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> Feedback:
        f = await self.get_or_404(feedback_id)
        self._assert_open(f)
        if not f.can_escalate():
            raise EscalationError(message=f"Cannot escalate feedback with status '{f.status.value}'.")
        reason = data.get("reason", "").strip()
        if not reason:
            raise EscalationError(message="Escalation reason is required.")
        next_level = GRMLevel(data["to_level"]) if data.get("to_level") else f.next_grm_level()
        if not next_level:
            raise EscalationError(message="Feedback is already at the highest GRM level (World Bank).")
        from_level = f.current_level
        esc = FeedbackEscalation(
            feedback_id=f.id, from_level=from_level, to_level=next_level,
            reason=reason,
            escalated_to_committee_id=uuid.UUID(data["committee_id"]) if data.get("committee_id") else None,
            escalated_by_user_id=by,
        )
        f.current_level = next_level
        f.status        = FeedbackStatus.ESCALATED
        if esc.escalated_to_committee_id:
            f.assigned_committee_id = esc.escalated_to_committee_id
        await self.repo.save(f)
        await self.repo.create_escalation(esc)
        await self.repo.create_action(FeedbackAction(
            feedback_id=f.id, action_type=ActionType.ESCALATION_NOTE,
            description=f"Escalated from {from_level.value} to {next_level.value}: {reason}",
            is_internal=False, performed_by_user_id=by,
        ))
        await self.db.commit()
        await self.producer.feedback_escalated(f.id, f.project_id, from_level.value, next_level.value, reason)
        return f

    async def resolve(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> Feedback:
        f = await self.get_or_404(feedback_id)
        self._assert_open(f)
        if not f.can_resolve():
            raise ResolutionError(message=f"Cannot resolve feedback with status '{f.status.value}'.")
        summary = data.get("resolution_summary", "").strip()
        if not summary:
            raise ResolutionError(message="Resolution summary is required.")
        f.status      = FeedbackStatus.RESOLVED
        f.resolved_at = datetime.now(timezone.utc)
        resolution = FeedbackResolution(
            feedback_id=f.id, resolution_summary=summary,
            response_method=ResponseMethod(data.get("response_method", "in_person_meeting")),
            grievant_satisfied=data.get("grievant_satisfied"),
            grievant_response=data.get("grievant_response"),
            witness_name=data.get("witness_name"),
            resolved_by_user_id=by,
        )
        await self.repo.save(f)
        await self.repo.create_resolution(resolution)
        await self.repo.create_action(FeedbackAction(
            feedback_id=f.id, action_type=ActionType.RESPONSE,
            description=summary, response_method=resolution.response_method,
            response_summary=data.get("grievant_response"),
            is_internal=False, performed_by_user_id=by,
        ))
        await self.db.commit()
        await self.producer.feedback_resolved(f.id, f.project_id)
        return f

    async def appeal(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> Feedback:
        f = await self.get_or_404(feedback_id, load_relations=True)
        if not f.can_appeal():
            raise AppealError()
        grounds = data.get("appeal_grounds", "").strip()
        if not grounds:
            raise AppealError(message="Appeal grounds are required.")
        f.status = FeedbackStatus.APPEALED
        appeal = FeedbackAppeal(
            feedback_id=f.id, appeal_grounds=grounds,
            appeal_status="pending", filed_by_user_id=by,
        )
        if f.resolution:
            f.resolution.appeal_filed = True
            await self.repo.save_resolution(f.resolution)
        next_level = f.next_grm_level()
        if next_level:
            esc = FeedbackEscalation(
                feedback_id=f.id, from_level=f.current_level,
                to_level=next_level,
                reason=f"Appeal filed: {grounds}",
                escalated_by_user_id=by,
            )
            f.current_level = next_level
            await self.repo.create_escalation(esc)
        await self.repo.save(f)
        await self.repo.create_appeal(appeal)
        await self.repo.create_action(FeedbackAction(
            feedback_id=f.id, action_type=ActionType.APPEAL_REVIEW,
            description=f"Appeal filed: {grounds}",
            is_internal=False, performed_by_user_id=by,
        ))
        await self.db.commit()
        await self.producer.feedback_appealed(f.id, f.project_id, grounds)
        return f

    async def close(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> Feedback:
        f = await self.get_or_404(feedback_id)
        if f.status == FeedbackStatus.CLOSED:
            raise FeedbackClosedError()
        f.status    = FeedbackStatus.CLOSED
        f.closed_at = datetime.now(timezone.utc)
        await self.repo.save(f)
        await self.repo.create_action(FeedbackAction(
            feedback_id=f.id, action_type=ActionType.NOTE,
            description=data.get("note", "Feedback closed."),
            is_internal=True, performed_by_user_id=by,
        ))
        await self.db.commit()
        return f

    async def dismiss(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> Feedback:
        f = await self.get_or_404(feedback_id)
        self._assert_open(f)
        reason = data.get("reason", "").strip()
        if not reason:
            raise ValidationError(message="Dismissal reason is required.")
        f.status    = FeedbackStatus.DISMISSED
        f.closed_at = datetime.now(timezone.utc)
        await self.repo.save(f)
        await self.repo.create_action(FeedbackAction(
            feedback_id=f.id, action_type=ActionType.NOTE,
            description=f"Dismissed: {reason}",
            is_internal=True, performed_by_user_id=by,
        ))
        await self.db.commit()
        return f

    # ── Actions ───────────────────────────────────────────────────────────────

    async def log_action(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> FeedbackAction:
        f = await self.get_or_404(feedback_id)
        action_type = ActionType(data["action_type"])
        if action_type == ActionType.INVESTIGATION and f.status.value == "acknowledged":
            f.status = FeedbackStatus.IN_REVIEW
            await self.repo.save(f)
        action = FeedbackAction(
            feedback_id=feedback_id, action_type=action_type,
            description=data["description"],
            response_method=ResponseMethod(data["response_method"]) if data.get("response_method") else None,
            response_summary=data.get("response_summary"),
            is_internal=data.get("is_internal", False),
            performed_by_user_id=by,
        )
        action = await self.repo.create_action(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def list_actions(
        self, feedback_id: uuid.UUID
    ):
        await self.get_or_404(feedback_id)
        return await self.repo.list_actions(feedback_id)

    # ── PAP ───────────────────────────────────────────────────────────────────

    async def list_for_pap(
        self,
        user_id:        uuid.UUID,
        stakeholder_id: Optional[uuid.UUID] = None,
        **filters,
    ) -> list[Feedback]:
        return await self.repo.list_for_user(
            user_id=user_id, stakeholder_id=stakeholder_id, **filters
        )

    async def get_for_pap_or_404(
        self,
        feedback_id:    uuid.UUID,
        user_id:        uuid.UUID,
        stakeholder_id: Optional[uuid.UUID],
    ) -> Feedback:
        f = await self.repo.get_by_id(feedback_id, load_relations=True)
        if not f:
            raise FeedbackNotFoundError()
        owned = (
            f.submitted_by_user_id == user_id
            or (stakeholder_id and f.submitted_by_stakeholder_id == stakeholder_id)
        )
        if not owned:
            raise FeedbackNotFoundError()
        return f

    async def pap_add_comment(
        self, feedback_id: uuid.UUID, data: dict, user_id: uuid.UUID, stakeholder_id
    ) -> FeedbackAction:
        f = await self.get_for_pap_or_404(feedback_id, user_id, stakeholder_id)
        if f.status in (FeedbackStatus.CLOSED, FeedbackStatus.DISMISSED):
            raise FeedbackClosedError()
        comment = data.get("comment", "").strip()
        if not comment:
            raise ValidationError(message="comment is required.")
        action = FeedbackAction(
            feedback_id=feedback_id, action_type=ActionType.NOTE,
            description=f"PAP follow-up: {comment}", is_internal=False,
        )
        action = await self.repo.create_action(action)
        await self.db.commit()
        return action

    async def pap_appeal(
        self, feedback_id: uuid.UUID, data: dict, user_id: uuid.UUID, stakeholder_id
    ) -> tuple[Feedback, FeedbackAppeal]:
        f = await self.get_for_pap_or_404(feedback_id, user_id, stakeholder_id)
        if f.status != FeedbackStatus.RESOLVED:
            raise ValidationError(f"Current status: {f.status.value}. Appeal only allowed after resolution.")
        if f.appeal:
            raise ValidationError("An appeal has already been filed for this item.")
        grounds = data.get("appeal_grounds", "").strip()
        if not grounds:
            raise ValidationError("appeal_grounds is required.")
        appeal = FeedbackAppeal(
            feedback_id=feedback_id, appeal_grounds=grounds,
            appeal_status="pending", filed_by_user_id=user_id,
        )
        await self.repo.create_appeal(appeal)
        if f.resolution:
            f.resolution.appeal_filed = True
            f.resolution.grievant_satisfied = False
            await self.repo.save_resolution(f.resolution)
        f.status = FeedbackStatus.APPEALED
        current_idx = _LEVEL_ORDER.index(f.current_level) if f.current_level in _LEVEL_ORDER else 0
        next_level  = _LEVEL_ORDER[min(current_idx + 1, len(_LEVEL_ORDER) - 1)]
        esc = FeedbackEscalation(
            feedback_id=feedback_id, from_level=f.current_level,
            to_level=next_level, reason=f"PAP appeal filed: {grounds}",
            escalated_by_user_id=None,
        )
        await self.repo.create_escalation(esc)
        f.current_level = next_level
        await self.repo.save(f)
        await self.repo.create_action(FeedbackAction(
            feedback_id=feedback_id, action_type=ActionType.NOTE,
            description=f"PAP filed formal appeal. Grounds: {grounds}",
            is_internal=False,
        ))
        await self.db.commit()
        return f, appeal

    # ── Escalation requests ───────────────────────────────────────────────────

    async def request_escalation(
        self, feedback_id: uuid.UUID, data: dict,
        user_id: uuid.UUID, stakeholder_id: Optional[uuid.UUID]
    ) -> EscalationRequest:
        f = await self.get_for_pap_or_404(feedback_id, user_id, stakeholder_id)
        if f.status in (FeedbackStatus.CLOSED, FeedbackStatus.DISMISSED, FeedbackStatus.RESOLVED):
            raise ValidationError("Cannot request escalation on a closed or resolved item.")
        if f.current_level == GRMLevel.WORLD_BANK:
            raise ValidationError("Already at the highest GRM level (World Bank).")
        existing = await self.repo.get_pending_escalation_request(feedback_id)
        if existing:
            raise ValidationError("You already have a pending escalation request for this item.")
        reason = data.get("reason", "").strip()
        if not reason:
            raise ValidationError("reason is required.")
        er = EscalationRequest(
            feedback_id=feedback_id, requested_by_user_id=user_id,
            requested_by_stakeholder_id=stakeholder_id, reason=reason,
            requested_level=data.get("requested_level"),
            status=EscalationRequestStatus.PENDING,
        )
        er = await self.repo.create_escalation_request(er)
        await self.db.commit()
        return er

    async def list_escalation_requests(self, **filters):
        return await self.repo.list_escalation_requests(**filters)

    async def approve_escalation_request(
        self, request_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> EscalationRequest:
        er = await self.repo.get_escalation_request(request_id)
        if not er:
            raise ValidationError("Escalation request not found.")
        if er.status != EscalationRequestStatus.PENDING:
            raise ValidationError(f"Request is already {er.status.value}.")
        er.status              = EscalationRequestStatus.APPROVED
        er.reviewed_by_user_id = by
        er.reviewed_at         = datetime.now(timezone.utc)
        er.reviewer_notes      = data.get("notes", "Your escalation request has been approved.")
        await self.repo.save_escalation_request(er)
        await self.db.commit()
        return er

    async def reject_escalation_request(
        self, request_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> EscalationRequest:
        er = await self.repo.get_escalation_request(request_id)
        if not er:
            raise ValidationError("Escalation request not found.")
        if er.status != EscalationRequestStatus.PENDING:
            raise ValidationError(f"Request is already {er.status.value}.")
        notes = data.get("notes", "").strip()
        if not notes:
            raise ValidationError("reviewer_notes is required when rejecting.")
        er.status              = EscalationRequestStatus.REJECTED
        er.reviewed_by_user_id = by
        er.reviewed_at         = datetime.now(timezone.utc)
        er.reviewer_notes      = notes
        await self.repo.save_escalation_request(er)
        await self.db.commit()
        return er

    async def count_pending_escalation_requests(self, user_id: uuid.UUID) -> int:
        return await self.repo.count_pending_escalation_requests(user_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assert_open(self, f: Feedback) -> None:
        if not f.is_open():
            raise FeedbackClosedError()
