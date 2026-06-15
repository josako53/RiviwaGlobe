# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/custom_fields.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/custom_fields.py
═══════════════════════════════════════════════════════════════════════════════
Per-org custom field definition management.

Routes
──────
  GET    /orgs/{org_id}/custom-fields                    List custom fields [member+]
  POST   /orgs/{org_id}/custom-fields                    Create field [admin+]
  PATCH  /orgs/{org_id}/custom-fields/{field_id}         Update field [admin+]
  DELETE /orgs/{org_id}/custom-fields/{field_id}         Deactivate field [admin+]
  POST   /orgs/{org_id}/custom-fields/apply-template     Import industry template [admin+]
  GET    /orgs/{org_id}/custom-fields/ai-context         AI service endpoint (X-Service-Key)

Notes
─────
  /ai-context is authenticated via X-Service-Key header (no JWT).
  It returns fields grouped by entity_type in a compact format for the AI service.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.deps import DbDep, PublisherDep
from core.config import settings
from core.dependencies import require_org_role
from db.session import get_async_session as get_db
from events.publisher import EventPublisher
from models.organisation import OrgMemberRole
from repositories.custom_field_repository import CustomFieldRepository
from schemas.industry import ApplyTemplateRequest, CreateCustomFieldRequest, UpdateCustomFieldRequest
from services.custom_field_service import CustomFieldService
from services.industry_service import IndustryService

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/orgs", tags=["Custom Fields"])

_SERVICE_KEY = getattr(settings, "INTERNAL_SERVICE_KEY", "change-me-in-env")


def _cf_svc(db, publisher: EventPublisher) -> CustomFieldService:
    return CustomFieldService(db=db, publisher=publisher)


def _ind_svc(db, publisher: EventPublisher) -> IndustryService:
    return IndustryService(db=db, publisher=publisher)


def _require_service_key(x_service_key: str = Header(..., alias="X-Service-Key")) -> None:
    if x_service_key != _SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service key."
        )


def _field_out(f) -> dict:
    return {
        "id":                     str(f.id),
        "org_id":                 str(f.org_id),
        "entity_type":            f.entity_type,
        "field_key":              f.field_key,
        "label":                  f.label,
        "label_sw":               f.label_sw,
        "field_type":             f.field_type,
        "options":                f.options,
        "placeholder":            f.placeholder,
        "help_text":              f.help_text,
        "is_required":            f.is_required,
        "is_visible_to_consumer": f.is_visible_to_consumer,
        "feedback_types":         f.feedback_types,
        "industry_template_key":  f.industry_template_key,
        "sort_order":             f.sort_order,
        "is_active":              f.is_active,
        "created_by_id":          str(f.created_by_id) if f.created_by_id else None,
        "created_at":             f.created_at.isoformat(),
        "updated_at":             f.updated_at.isoformat(),
    }


# ── List custom fields ────────────────────────────────────────────────────────

@router.get(
    "/{org_id}/custom-fields",
    summary="List custom field definitions for an org [member+]",
)
async def list_custom_fields(
    org_id:      uuid.UUID,
    db:          DbDep,
    publisher:   PublisherDep,
    entity_type: Optional[str] = Query(
        default=None, description="Filter by entity type e.g. 'feedback'"
    ),
    active_only: bool = Query(default=True, description="Return only active fields"),
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    items = await _cf_svc(db, publisher).list(
        org_id=org_id, entity_type=entity_type, active_only=active_only
    )
    return {"items": [_field_out(f) for f in items], "count": len(items)}


# ── Create custom field ───────────────────────────────────────────────────────

@router.post(
    "/{org_id}/custom-fields",
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom field definition [admin+]",
)
async def create_custom_field(
    org_id:    uuid.UUID,
    body:      CreateCustomFieldRequest,
    db:        DbDep,
    publisher: PublisherDep,
    member=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    field = await _cf_svc(db, publisher).create(
        org_id=org_id,
        data=body.model_dump(exclude_none=True),
        created_by_id=member.user_id,
    )
    return _field_out(field)


# ── Update custom field ───────────────────────────────────────────────────────

@router.patch(
    "/{org_id}/custom-fields/{field_id}",
    summary="Update a custom field definition [admin+]",
)
async def update_custom_field(
    org_id:   uuid.UUID,
    field_id: uuid.UUID,
    body:     UpdateCustomFieldRequest,
    db:       DbDep,
    publisher: PublisherDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    field = await _cf_svc(db, publisher).update(
        field_id=field_id,
        org_id=org_id,
        data=body.model_dump(exclude_unset=True),
    )
    return _field_out(field)


# ── Deactivate custom field ───────────────────────────────────────────────────

@router.delete(
    "/{org_id}/custom-fields/{field_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a custom field definition [admin+]",
)
async def deactivate_custom_field(
    org_id:   uuid.UUID,
    field_id: uuid.UUID,
    db:       DbDep,
    publisher: PublisherDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    return await _cf_svc(db, publisher).deactivate(field_id=field_id, org_id=org_id)


# ── Apply industry template ───────────────────────────────────────────────────

@router.post(
    "/{org_id}/custom-fields/apply-template",
    status_code=status.HTTP_201_CREATED,
    summary="Import industry field templates into org custom fields [admin+]",
)
async def apply_template(
    org_id:    uuid.UUID,
    body:      ApplyTemplateRequest,
    db:        DbDep,
    publisher: PublisherDep,
    member=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    created = await _ind_svc(db, publisher).apply_template_to_org(
        org_id=org_id,
        industry_id=body.industry_id,
        entity_type=body.entity_type,
        created_by_id=member.user_id,
    )
    return {
        "created": [_field_out(f) for f in created],
        "count":   len(created),
        "detail":  f"{len(created)} field(s) imported. Existing fields were skipped.",
    }


# ── AI context endpoint (X-Service-Key, no JWT) ───────────────────────────────

@router.get(
    "/{org_id}/custom-fields/ai-context",
    summary="[Internal] Active custom fields grouped by entity_type for AI service",
    dependencies=[Depends(_require_service_key)],
)
async def get_ai_context(
    org_id: uuid.UUID,
    db:     DbDep,
    publisher: PublisherDep,
) -> dict:
    """
    Returns all active custom field definitions for an org, grouped by entity_type.
    Used by the AI service to know which extra fields to collect during
    a feedback conversation.

    Response shape:
    {
      "feedback": [
        {
          "field_key": "patient_file_number",
          "label": "Patient File Number",
          "label_sw": "Nambari ya Faili la Mgonjwa",
          "field_type": "text",
          "is_required": true,
          "feedback_types": ["grievance"]
        },
        ...
      ],
      "stakeholder": [...],
      ...
    }
    """
    repo = CustomFieldRepository(db)
    fields = await repo.list_for_org(org_id=org_id, entity_type=None, active_only=True)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for f in fields:
        grouped[f.entity_type].append({
            "field_key":              f.field_key,
            "label":                  f.label,
            "label_sw":               f.label_sw,
            "field_type":             f.field_type,
            "is_required":            f.is_required,
            "is_visible_to_consumer": f.is_visible_to_consumer,
            "feedback_types":         f.feedback_types,
            "options":                f.options,
            "placeholder":            f.placeholder,
            "help_text":              f.help_text,
            "sort_order":             f.sort_order,
        })

    return dict(grouped)
