# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/industries.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/industries.py
═══════════════════════════════════════════════════════════════════════════════
Industry taxonomy and org-industry association endpoints.

Routes
──────
  GET    /industries                                  List all active industries (public)
  GET    /industries/{industry_id}/field-templates    List field templates for an industry
  GET    /orgs/{org_id}/industries                    List org's industries [member+]
  PUT    /orgs/{org_id}/industries                    Set org's industries (replace) [admin+]
  POST   /orgs/{org_id}/industries/{industry_id}      Add single industry to org [admin+]
  DELETE /orgs/{org_id}/industries/{industry_id}      Remove industry from org [admin+]
═══════════════════════════════════════════════════════════════════════════════
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from api.v1.deps import DbDep, PublisherDep
from core.dependencies import require_org_role
from events.publisher import EventPublisher
from models.organisation import OrgMemberRole
from schemas.industry import (
    IndustryFieldTemplateOut,
    IndustryOut,
    OrgIndustryOut,
    SetOrgIndustriesRequest,
)
from services.industry_service import IndustryService

router = APIRouter(tags=["Industries"])


def _svc(db, publisher: EventPublisher) -> IndustryService:
    return IndustryService(db=db, publisher=publisher)


def _industry_out(ind) -> dict:
    return {
        "id":          str(ind.id),
        "name":        ind.name,
        "slug":        ind.slug,
        "description": ind.description,
        "icon_url":    ind.icon_url,
        "parent_id":   str(ind.parent_id) if ind.parent_id else None,
        "sort_order":  ind.sort_order,
        "is_active":   ind.is_active,
    }


def _org_industry_out(row) -> dict:
    return {
        "id":          str(row.id),
        "org_id":      str(row.org_id),
        "industry_id": str(row.industry_id),
        "is_primary":  row.is_primary,
        "created_at":  row.created_at.isoformat(),
        "industry":    _industry_out(row.industry) if row.industry else None,
    }


def _template_out(tmpl) -> dict:
    return {
        "id":                     str(tmpl.id),
        "industry_id":            str(tmpl.industry_id),
        "entity_type":            tmpl.entity_type,
        "field_key":              tmpl.field_key,
        "label":                  tmpl.label,
        "label_sw":               tmpl.label_sw,
        "field_type":             tmpl.field_type,
        "is_required":            tmpl.is_required,
        "is_visible_to_consumer": tmpl.is_visible_to_consumer,
        "feedback_types":         tmpl.feedback_types,
        "source_standard":        tmpl.source_standard,
        "sort_order":             tmpl.sort_order,
    }


# ── Public: list all industries ───────────────────────────────────────────────

@router.get(
    "/industries",
    summary="List all active industries (public)",
)
async def list_industries(
    db:        DbDep,
    publisher: PublisherDep,
    active_only: bool = Query(default=True, description="Return only active industries"),
) -> dict:
    items = await _svc(db, publisher).list_industries(active_only=active_only)
    return {"items": [_industry_out(i) for i in items], "count": len(items)}


# ── Public: list field templates for an industry ──────────────────────────────

@router.get(
    "/industries/{industry_id}/field-templates",
    summary="List field templates for an industry",
)
async def list_field_templates(
    industry_id: uuid.UUID,
    db:          DbDep,
    publisher:   PublisherDep,
    entity_type: Optional[str] = Query(
        default=None,
        description="Filter by entity type e.g. 'feedback', 'stakeholder'",
    ),
) -> dict:
    items = await _svc(db, publisher).get_field_templates(
        industry_id=industry_id, entity_type=entity_type
    )
    return {"items": [_template_out(t) for t in items], "count": len(items)}


# ── Org industries: list ──────────────────────────────────────────────────────

@router.get(
    "/orgs/{org_id}/industries",
    summary="List org's industries [member+]",
)
async def list_org_industries(
    org_id:    uuid.UUID,
    db:        DbDep,
    publisher: PublisherDep,
    _=Depends(require_org_role(OrgMemberRole.MEMBER)),
) -> dict:
    rows = await _svc(db, publisher).get_org_industries(org_id=org_id)
    return {"items": [_org_industry_out(r) for r in rows], "count": len(rows)}


# ── Org industries: set (replace all) ────────────────────────────────────────

@router.put(
    "/orgs/{org_id}/industries",
    summary="Replace org's industries [admin+]",
)
async def set_org_industries(
    org_id:    uuid.UUID,
    body:      SetOrgIndustriesRequest,
    db:        DbDep,
    publisher: PublisherDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    rows = await _svc(db, publisher).set_org_industries(
        org_id=org_id,
        industry_ids=body.industry_ids,
        primary_id=body.primary_industry_id,
    )
    return {"items": [_org_industry_out(r) for r in rows], "count": len(rows)}


# ── Org industries: add single ────────────────────────────────────────────────

@router.post(
    "/orgs/{org_id}/industries/{industry_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add a single industry to org [admin+]",
)
async def add_org_industry(
    org_id:      uuid.UUID,
    industry_id: uuid.UUID,
    db:          DbDep,
    publisher:   PublisherDep,
    is_primary:  bool = Query(default=False, description="Mark as primary industry"),
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    row = await _svc(db, publisher).add_org_industry(
        org_id=org_id, industry_id=industry_id, is_primary=is_primary
    )
    return _org_industry_out(row)


# ── Org industries: remove single ─────────────────────────────────────────────

@router.delete(
    "/orgs/{org_id}/industries/{industry_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove an industry from org [admin+]",
)
async def remove_org_industry(
    org_id:      uuid.UUID,
    industry_id: uuid.UUID,
    db:          DbDep,
    publisher:   PublisherDep,
    _=Depends(require_org_role(OrgMemberRole.ADMIN)),
) -> dict:
    await _svc(db, publisher).remove_org_industry(org_id=org_id, industry_id=industry_id)
    return {"detail": "Industry removed from organisation."}
