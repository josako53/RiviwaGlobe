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

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


def _to_uuid(v) -> uuid.UUID:
    """Accept both uuid.UUID objects (from Pydantic) and plain strings."""
    return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))


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
from repositories.category_repository import CategoryRepository

_PREFIX = {
    FeedbackType.GRIEVANCE:  "GRV",
    FeedbackType.SUGGESTION: "SGG",
    FeedbackType.APPLAUSE:   "APP",
    FeedbackType.INQUIRY:    "INQ",
}


def _category_slug(val: str | None) -> str:
    """Normalise a category string to a slug (enum value → slug are identical in our system)."""
    if not val:
        return "other"
    return val.lower().replace("_", "-")


def _safe_category(val: str | None) -> FeedbackCategory:
    try:
        return FeedbackCategory(val or "other")
    except ValueError:
        return FeedbackCategory.OTHER

_LEVEL_ORDER = [
    GRMLevel.WARD, GRMLevel.LGA_GRM_UNIT, GRMLevel.COORDINATING_UNIT,
    GRMLevel.TARURA_WBCU, GRMLevel.TANROADS, GRMLevel.WORLD_BANK,
]


async def _resolve_branch_id(department_id: uuid.UUID) -> uuid.UUID | None:
    """
    Call auth_service GET /internal/departments/{dept_id} to resolve the
    branch_id for a department. Returns None if unreachable or no branch set.
    Never raises — branch_id is optional analytics metadata.
    """
    import httpx
    from core.config import settings

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/internal/departments/{department_id}",
                headers={
                    "X-Service-Key":  settings.INTERNAL_SERVICE_KEY,
                    "X-Service-Name": "feedback_service",
                },
            )
            if r.status_code == 200:
                raw = r.json().get("branch_id")
                return uuid.UUID(raw) if raw else None
            log.warning("feedback.branch_resolve_failed", dept=str(department_id), status=r.status_code)
            return None
    except Exception as exc:
        log.warning("feedback.branch_resolve_unreachable", dept=str(department_id), error=str(exc))
        return None


async def _classify_via_ai_service(data: dict) -> dict | None:
    """
    Call ai_service POST /api/v1/ai/internal/classify to auto-detect
    project_id and category for a Consumer submission.

    Returns the classification dict, or None if ai_service is unreachable.
    Never raises — caller must handle None gracefully.
    """
    import httpx
    from core.config import settings

    payload = {
        "feedback_type":              data.get("feedback_type", "grievance"),
        "description":                data.get("description", ""),
        "issue_location_description": data.get("issue_location_description"),
        "issue_lga":                  data.get("issue_lga"),
        "issue_ward":                 data.get("issue_ward"),
        "issue_region":               data.get("issue_region"),
        "project_id":                 str(data["project_id"]) if data.get("project_id") else None,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{settings.AI_SERVICE_URL}/api/v1/ai/internal/classify",
                json=payload,
                headers={
                    "X-Service-Key":  settings.INTERNAL_SERVICE_KEY,
                    "X-Service-Name": "feedback_service",
                },
            )
            if r.status_code == 200:
                return r.json()
            log.warning("feedback.ai_classify_failed", status=r.status_code, body=r.text[:200])
            return None
    except Exception as exc:
        log.warning("feedback.ai_classify_unreachable", error=str(exc))
        return None


async def _fetch_candidate_projects(data: dict) -> list:
    """
    When AI cannot identify a single project, fetch the top candidate projects
    from ai_service so the frontend can present a picker.
    Falls back to empty list if ai_service is unreachable.
    """
    import httpx
    from core.config import settings

    payload = {
        "feedback_type":              data.get("feedback_type", "grievance"),
        "description":                data.get("description", ""),
        "issue_location_description": data.get("issue_location_description"),
        "issue_lga":                  data.get("issue_lga"),
        "issue_ward":                 data.get("issue_ward"),
        "issue_region":               data.get("issue_region"),
        "top_k":                      5,   # ask for top 5 candidates
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{settings.AI_SERVICE_URL}/api/v1/ai/internal/candidate-projects",
                json=payload,
                headers={
                    "X-Service-Key":  settings.INTERNAL_SERVICE_KEY,
                    "X-Service-Name": "feedback_service",
                },
            )
            if r.status_code == 200:
                return r.json().get("projects", [])
    except Exception as exc:
        log.warning("feedback.candidate_projects_failed", error=str(exc))
    return []


class FeedbackService:

    def __init__(self, db: AsyncSession, producer: FeedbackProducer) -> None:
        self.repo      = FeedbackRepository(db)
        self.cat_repo  = CategoryRepository(db)
        self.producer  = producer
        self.db        = db

    # ── Submit ────────────────────────────────────────────────────────────────

    def _to_uuid(self, val) -> Optional[uuid.UUID]:
        """Safely convert a value to UUID — handles str, UUID, or None."""
        if val is None:
            return None
        if isinstance(val, uuid.UUID):
            return val
        return uuid.UUID(str(val))

    async def submit(self, data: dict, token_sub: Optional[uuid.UUID] = None) -> Feedback:
        project_id = self._to_uuid(data.get("project_id"))
        project = None
        active_stage = None

        if project_id:
            project = await self.repo.get_project(project_id)
            if not project:
                raise ProjectNotFoundError()
            feedback_type = FeedbackType(data["feedback_type"])
            if not project.accepts_feedback_type(feedback_type.value):
                raise ProjectNotAcceptingFeedbackError(
                    message=f"This project is not currently accepting {feedback_type.value} submissions."
                )
            active_stage = project.active_stage()
        else:
            feedback_type = FeedbackType(data["feedback_type"])

        # Use MAX of existing sequence numbers so gaps/deletions never cause duplicates
        _year = datetime.now().year
        _seq  = await self.repo.next_ref_sequence(_PREFIX[feedback_type], _year)
        unique_ref = f"{_PREFIX[feedback_type]}-{_year}-{_seq:04d}"
        is_anon = bool(data.get("is_anonymous", False))

        f = Feedback(
            unique_ref                   = unique_ref,
            project_id                   = project_id,
            stage_id                     = active_stage.id if active_stage else None,
            subproject_id                = self._to_uuid(data.get("subproject_id")),
            department_id                = self._to_uuid(data.get("department_id")),
            branch_id                    = self._to_uuid(data.get("branch_id")),
            service_location_id          = self._to_uuid(data.get("service_location_id")),
            service_id                   = self._to_uuid(data.get("service_id")),
            product_id                   = self._to_uuid(data.get("product_id")),
            feedback_type                = feedback_type,
            category                     = _safe_category(data.get("category")),
            status                       = FeedbackStatus.SUBMITTED,
            priority                     = FeedbackPriority(data.get("priority", "medium")),
            current_level                = GRMLevel.WARD,
            channel                      = FeedbackChannel(data["channel"]),
            is_anonymous                 = is_anon,
            submitted_by_user_id         = None if is_anon else (token_sub or self._to_uuid(data.get("submitted_by_user_id"))),
            submitted_by_stakeholder_id  = None if is_anon else self._to_uuid(data.get("submitted_by_stakeholder_id")),
            submitted_by_contact_id      = None if is_anon else self._to_uuid(data.get("submitted_by_contact_id")),
            submitter_name               = None if is_anon else data.get("submitter_name"),
            submitter_phone              = None if is_anon else data.get("submitter_phone"),
            submitter_location_region    = None if is_anon else data.get("submitter_location_region"),
            submitter_location_district  = None if is_anon else data.get("submitter_location_district"),
            submitter_location_lga       = None if is_anon else data.get("submitter_location_lga"),
            submitter_location_ward      = None if is_anon else data.get("submitter_location_ward"),
            submitter_location_street    = None if is_anon else data.get("submitter_location_street"),
            entered_by_user_id           = None if is_anon else (token_sub if data.get("officer_recorded") else None),
            stakeholder_engagement_id    = self._to_uuid(data.get("stakeholder_engagement_id")),
            distribution_id              = self._to_uuid(data.get("distribution_id")),
            subject                      = data["subject"],
            description                  = data["description"],
            media_urls                   = data.get("media_urls"),
            internal_notes               = data.get("internal_notes"),
            issue_location_description   = data.get("issue_location_description"),
            issue_region                 = data.get("issue_region"),
            issue_district               = data.get("issue_district"),
            issue_lga                    = data.get("issue_lga"),
            issue_ward                   = data.get("issue_ward"),
            issue_mtaa                   = data.get("issue_mtaa"),
            issue_gps_lat                = float(data["issue_gps_lat"]) if data.get("issue_gps_lat") else None,
            issue_gps_lng                = float(data["issue_gps_lng"]) if data.get("issue_gps_lng") else None,
            date_of_incident             = datetime.fromisoformat(data["date_of_incident"]) if data.get("date_of_incident") else None,
        )
        # Backdate support: staff can set submitted_at for historical records
        if data.get("submitted_at"):
            f.submitted_at = datetime.fromisoformat(data["submitted_at"]).replace(tzinfo=timezone.utc) if not datetime.fromisoformat(data["submitted_at"]).tzinfo else datetime.fromisoformat(data["submitted_at"])
        f = await self.repo.create(f)

        # Resolve branch_id from department when not explicitly provided
        if f.department_id and not f.branch_id:
            f.branch_id = await _resolve_branch_id(f.department_id)

        # Auto-link to dynamic FeedbackCategoryDef by slug
        slug = _category_slug(data.get("category"))
        cat_def = (
            await self.cat_repo.get_by_slug(slug, project_id) or
            await self.cat_repo.get_by_slug(slug, None)
        )
        if cat_def:
            f.category_def_id = cat_def.id

        await self.db.commit()

        await self.producer.feedback_submitted(
            f.id, f.project_id, f.feedback_type.value, f.category.value,
            stakeholder_engagement_id=f.stakeholder_engagement_id,
            distribution_id=f.distribution_id,
        )

        # Notify Consumer that submission was received
        if not f.is_anonymous:
            try:
                project = await self.repo.get_project(f.project_id)
                await self.producer.notifications.grm_feedback_submitted(
                    feedback_id      = str(f.id),
                    consumer_user_id = str(f.submitted_by_user_id) if f.submitted_by_user_id else None,
                    consumer_phone   = f.submitter_phone,
                    feedback_ref     = f.unique_ref,
                    project_name     = project.name if project else "the project",
                    feedback_type    = f.feedback_type.value,
                    language         = "sw",
                )
            except Exception as _exc:
                log.warning("feedback.submit_notification_failed", error=str(_exc))

        return f

    # ── Bulk Submit (CSV/Excel) ──────────────────────────────────────────────

    async def bulk_submit(
        self, rows: list[dict], token_sub: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Import multiple feedback records from parsed CSV/Excel rows.
        Each row is validated and submitted independently — failures on one
        row do not block others. Returns summary with per-row errors.
        """
        created = 0
        skipped = 0
        errors = []

        for i, row in enumerate(rows, start=1):
            try:
                # Normalise keys to lowercase/underscore
                data = {k.strip().lower().replace(" ", "_"): v.strip() if isinstance(v, str) else v for k, v in row.items() if v}
                # Map common CSV column aliases
                _aliases = {
                    "type": "feedback_type", "feedback type": "feedback_type",
                    "phone": "submitter_phone", "name": "submitter_name",
                    "lga": "issue_lga", "ward": "issue_ward",
                    "date": "date_of_incident", "incident_date": "date_of_incident",
                    "submission_date": "submitted_at", "received_date": "submitted_at",
                    "received_at": "submitted_at",
                    "gps_lat": "issue_gps_lat", "gps_lng": "issue_gps_lng",
                    "lat": "issue_gps_lat", "lng": "issue_gps_lng",
                    "latitude": "issue_gps_lat", "longitude": "issue_gps_lng",
                    "anonymous": "is_anonymous",
                }
                for alias, canonical in _aliases.items():
                    if alias in data and canonical not in data:
                        data[canonical] = data.pop(alias)

                # Validate required fields
                for req in ("project_id", "feedback_type", "category", "subject", "description"):
                    if not data.get(req):
                        raise ValueError(f"Missing required field: {req}")

                # Defaults for bulk
                data.setdefault("channel", "paper_form")
                data.setdefault("priority", "medium")
                data.setdefault("officer_recorded", True)
                if isinstance(data.get("is_anonymous"), str):
                    data["is_anonymous"] = data["is_anonymous"].lower() in ("true", "yes", "1")

                await self.submit(data, token_sub=token_sub)
                created += 1
            except Exception as exc:
                skipped += 1
                errors.append({"row": i, "error": str(exc), "data": {k: str(v)[:100] for k, v in row.items()}})
                log.warning("feedback.bulk.row_failed", row=i, error=str(exc))

        await self.db.commit()
        return {"total_rows": len(rows), "created": created, "skipped": skipped, "errors": errors}

    async def submit_from_consumer(
        self, data: dict, user_id: uuid.UUID, channel_override: str = "web_portal",
    ) -> Feedback:
        project_id = self._to_uuid(data.get("project_id"))

        # ── AI auto-classification: fill missing project_id and/or category ──
        # Only call AI when project_id is missing (need project identification)
        # or category is missing AND project_id was not explicitly provided by Consumer.
        # Skip AI entirely when Consumer already picked a project — avoids 15s timeout.
        if not project_id or (not data.get("category") and not data.get("project_id")):
            ai_result = await _classify_via_ai_service(data)
            if ai_result:
                if not project_id and ai_result.get("project_id"):
                    project_id = self._to_uuid(ai_result["project_id"])
                    data["project_id"] = ai_result["project_id"]
                if not data.get("category") and ai_result.get("category_slug"):
                    data["category"] = ai_result["category_slug"].replace("-", "_")
                if not data.get("category_def_id") and ai_result.get("category_def_id"):
                    data["category_def_id"] = ai_result["category_def_id"]

        # If AI couldn't identify the project, continue with project_id=None
        # (the feedback will be submitted without a project and can be enriched later)

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

        prefix = _PREFIX[fb_type]
        _year  = datetime.now().year
        _seq   = await self.repo.next_ref_sequence(prefix, _year)
        unique_ref = f"{prefix}-{_year}-{_seq:04d}"
        is_anon   = bool(data.get("is_anonymous", False))

        f = Feedback(
            unique_ref          = unique_ref,
            project_id          = project_id,
            feedback_type       = fb_type,
            category            = _safe_category(data.get("category")),
            status              = FeedbackStatus.SUBMITTED,
            priority            = FeedbackPriority.MEDIUM,
            current_level       = GRMLevel.WARD,
            channel             = FeedbackChannel(channel_override),
            submission_method   = SubmissionMethod.SELF_SERVICE,
            is_anonymous        = is_anon,
            submitted_by_user_id = None if is_anon else user_id,
            subject             = data.get("subject") or data.get("description", "")[:100],
            description         = data["description"],
            issue_location_description = data.get("issue_location_description"),
            issue_lga           = data.get("issue_lga"),
            issue_ward          = data.get("issue_ward"),
            issue_gps_lat       = float(data["issue_gps_lat"]) if data.get("issue_gps_lat") else None,
            issue_gps_lng       = float(data["issue_gps_lng"]) if data.get("issue_gps_lng") else None,
            date_of_incident    = datetime.fromisoformat(data["date_of_incident"]) if data.get("date_of_incident") else None,
            submitter_name      = None if is_anon else data.get("submitter_name"),
            submitter_phone     = None if is_anon else data.get("submitter_phone"),
            media_urls          = data.get("media_urls"),
        )
        f = await self.repo.create(f)

        # Auto-link category_def_id: prefer AI pre-resolved ID, else slug lookup
        if data.get("category_def_id"):
            try:
                f.category_def_id = uuid.UUID(str(data["category_def_id"]))
            except (ValueError, AttributeError):
                pass
        if not f.category_def_id:
            slug = _category_slug(data.get("category"))
            cat_def = (
                await self.cat_repo.get_by_slug(slug, project_id) or
                await self.cat_repo.get_by_slug(slug, None)
            )
            if cat_def:
                f.category_def_id = cat_def.id

        await self.db.commit()

        # Notify Consumer (self-service portal submission)
        if not f.is_anonymous:
            try:
                project = await self.repo.get_project(f.project_id)
                await self.producer.notifications.grm_feedback_submitted(
                    feedback_id      = str(f.id),
                    consumer_user_id = str(user_id),
                    consumer_phone   = f.submitter_phone,
                    feedback_ref     = f.unique_ref,
                    project_name     = project.name if project else "the project",
                    feedback_type    = f.feedback_type.value,
                    language         = "sw",
                )
            except Exception as _exc:
                log.warning("feedback.consumer_submit_notification_failed", error=str(_exc))

        return f

    # ── Fetch ─────────────────────────────────────────────────────────────────

    async def get_or_404(
        self, feedback_id: uuid.UUID, load_relations=False, org_id: Optional[uuid.UUID] = None
    ) -> Feedback:
        f = await self.repo.get_by_id(feedback_id, load_relations=load_relations, org_id=org_id)
        if not f:
            raise FeedbackNotFoundError()
        return f

    async def get_with_history_or_404(
        self, feedback_id: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Feedback:
        f = await self.repo.get_with_history(feedback_id, org_id=org_id)
        if not f:
            raise FeedbackNotFoundError()
        return f

    async def list(self, org_id: Optional[uuid.UUID] = None, **filters) -> list[Feedback]:
        return await self.repo.list(org_id=org_id, **filters)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def acknowledge(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Feedback:
        f = await self.get_or_404(feedback_id, org_id=org_id)
        self._assert_open(f)
        f.status          = FeedbackStatus.ACKNOWLEDGED
        f.priority        = FeedbackPriority(data.get("priority", f.priority.value))
        f.acknowledged_at = datetime.now(timezone.utc)
        if data.get("assigned_to_user_id"):
            f.assigned_to_user_id = _to_uuid(data["assigned_to_user_id"])
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

        # Notify Consumer that their submission has been acknowledged
        if not f.is_anonymous:
            try:
                project  = await self.repo.get_project(f.project_id)
                trd      = f.target_resolution_date.strftime("%d %b %Y") if f.target_resolution_date else None
                await self.producer.notifications.grm_feedback_acknowledged(
                    feedback_id            = str(f.id),
                    consumer_user_id       = str(f.submitted_by_user_id) if f.submitted_by_user_id else None,
                    consumer_phone         = f.submitter_phone,
                    feedback_ref           = f.unique_ref,
                    project_name           = project.name if project else "the project",
                    target_resolution_date = trd,
                    language               = "sw",
                )
            except Exception as _exc:
                log.warning("feedback.acknowledge_notification_failed", error=str(_exc))

        return f

    async def assign(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Feedback:
        f = await self.get_or_404(feedback_id, org_id=org_id)
        self._assert_open(f)
        if data.get("assigned_to_user_id"):
            f.assigned_to_user_id = _to_uuid(data["assigned_to_user_id"])
        if data.get("assigned_committee_id"):
            f.assigned_committee_id = _to_uuid(data["assigned_committee_id"])
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
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Feedback:
        f = await self.get_or_404(feedback_id, org_id=org_id)
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
            escalated_to_committee_id=_to_uuid(data["committee_id"]) if data.get("committee_id") else None,
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
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Feedback:
        f = await self.get_or_404(feedback_id, org_id=org_id)
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

        # Notify Consumer that their submission has been resolved
        if not f.is_anonymous:
            try:
                project = await self.repo.get_project(f.project_id)
                await self.producer.notifications.grm_feedback_resolved(
                    feedback_id        = str(f.id),
                    consumer_user_id   = str(f.submitted_by_user_id) if f.submitted_by_user_id else None,
                    consumer_phone     = f.submitter_phone,
                    feedback_ref       = f.unique_ref,
                    project_name       = project.name if project else "the project",
                    resolution_summary = summary,
                    language           = "sw",
                )
            except Exception as _exc:
                log.warning("feedback.resolve_notification_failed", error=str(_exc))

        return f

    async def appeal(
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Feedback:
        f = await self.get_or_404(feedback_id, load_relations=True, org_id=org_id)
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
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Feedback:
        f = await self.get_or_404(feedback_id, org_id=org_id)
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
        self, feedback_id: uuid.UUID, data: dict, by: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Feedback:
        f = await self.get_or_404(feedback_id, org_id=org_id)
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

    # ── Consumer ──────────────────────────────────────────────────────────────

    async def list_for_consumer(
        self,
        user_id:        uuid.UUID,
        stakeholder_id: Optional[uuid.UUID] = None,
        **filters,
    ) -> list[Feedback]:
        return await self.repo.list_for_user(
            user_id=user_id, stakeholder_id=stakeholder_id, **filters
        )

    async def get_for_consumer_or_404(
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

    async def consumer_add_comment(
        self, feedback_id: uuid.UUID, data: dict, user_id: uuid.UUID, stakeholder_id
    ) -> FeedbackAction:
        f = await self.get_for_consumer_or_404(feedback_id, user_id, stakeholder_id)
        if f.status in (FeedbackStatus.CLOSED, FeedbackStatus.DISMISSED):
            raise FeedbackClosedError()
        comment = data.get("comment", "").strip()
        if not comment:
            raise ValidationError(message="comment is required.")
        action = FeedbackAction(
            feedback_id=feedback_id, action_type=ActionType.NOTE,
            description=f"Consumer follow-up: {comment}", is_internal=False,
        )
        action = await self.repo.create_action(action)
        await self.db.commit()
        return action

    async def consumer_appeal(
        self, feedback_id: uuid.UUID, data: dict, user_id: uuid.UUID, stakeholder_id
    ) -> tuple[Feedback, FeedbackAppeal]:
        f = await self.get_for_consumer_or_404(feedback_id, user_id, stakeholder_id)
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
            to_level=next_level, reason=f"Consumer appeal filed: {grounds}",
            escalated_by_user_id=None,
        )
        await self.repo.create_escalation(esc)
        f.current_level = next_level
        await self.repo.save(f)
        await self.repo.create_action(FeedbackAction(
            feedback_id=feedback_id, action_type=ActionType.NOTE,
            description=f"Consumer filed formal appeal. Grounds: {grounds}",
            is_internal=False,
        ))
        await self.db.commit()
        return f, appeal

    # ── Escalation requests ───────────────────────────────────────────────────

    async def request_escalation(
        self, feedback_id: uuid.UUID, data: dict,
        user_id: uuid.UUID, stakeholder_id: Optional[uuid.UUID]
    ) -> EscalationRequest:
        f = await self.get_for_consumer_or_404(feedback_id, user_id, stakeholder_id)
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
