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
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.deps import DbDep, PublisherDep
from core.dependencies import require_active_user, require_org_role, require_platform_role
from events.publisher import EventPublisher
from models.industry import (
    GuideType,
    IndustryPolicyDocument,
    PlatformGuide,
    PolicyDocumentType,
)
from models.organisation import OrgMemberRole
from schemas.industry import (
    IndustryFieldTemplateOut,
    IndustryOut,
    OrgIndustryOut,
    SetOrgIndustriesRequest,
)
from services.industry_service import IndustryService

router = APIRouter(tags=["Industries"])

_admin_guard = Depends(require_platform_role("admin"))


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
    svc = _svc(db, publisher)
    await svc.set_org_industries(
        org_id=org_id,
        industry_ids=body.industry_ids,
        primary_id=body.primary_industry_id,
    )
    # Re-fetch with eager-loaded industry relationship to avoid lazy-load in async context
    rows = await svc.get_org_industries(org_id=org_id)
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
    svc = _svc(db, publisher)
    await svc.add_org_industry(org_id=org_id, industry_id=industry_id, is_primary=is_primary)
    # Re-fetch with eager-loaded relationship
    rows = await svc.get_org_industries(org_id=org_id)
    row = next((r for r in rows if str(r.industry_id) == str(industry_id)), rows[-1] if rows else None)
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


# ═════════════════════════════════════════════════════════════════════════════
# IndustryPolicyDocument — country laws, regulations, standards
# ═════════════════════════════════════════════════════════════════════════════

class CreatePolicyDocumentRequest(BaseModel):
    industry_id:       Optional[uuid.UUID] = None
    country_code:      Optional[str]       = None
    region:            Optional[str]       = None
    policy_type:       PolicyDocumentType
    title:             str
    slug:              str
    issuing_authority: Optional[str]       = None
    document_number:   Optional[str]       = None
    effective_date:    Optional[datetime]  = None
    expiry_date:       Optional[datetime]  = None
    content_md:        Optional[str]       = None
    file_url:          Optional[str]       = None
    version:           Optional[str]       = None
    language:          str                 = "en"
    is_public:         bool                = True


class UpdatePolicyDocumentRequest(BaseModel):
    country_code:      Optional[str]      = None
    region:            Optional[str]      = None
    policy_type:       Optional[PolicyDocumentType] = None
    title:             Optional[str]      = None
    issuing_authority: Optional[str]      = None
    document_number:   Optional[str]      = None
    effective_date:    Optional[datetime] = None
    expiry_date:       Optional[datetime] = None
    content_md:        Optional[str]      = None
    file_url:          Optional[str]      = None
    version:           Optional[str]      = None
    language:          Optional[str]      = None
    is_active:         Optional[bool]     = None
    is_public:         Optional[bool]     = None


def _policy_out(p) -> dict:
    return {
        "id":                str(p.id),
        "industry_id":       str(p.industry_id) if p.industry_id else None,
        "country_code":      p.country_code,
        "region":            p.region,
        "policy_type":       p.policy_type,
        "title":             p.title,
        "slug":              p.slug,
        "issuing_authority": p.issuing_authority,
        "document_number":   p.document_number,
        "effective_date":    p.effective_date.isoformat() if p.effective_date else None,
        "expiry_date":       p.expiry_date.isoformat() if p.expiry_date else None,
        "content_md":        p.content_md,
        "file_url":          p.file_url,
        "version":           p.version,
        "language":          p.language,
        "is_active":         p.is_active,
        "is_public":         p.is_public,
        "created_at":        p.created_at.isoformat(),
        "updated_at":        p.updated_at.isoformat(),
    }


@router.get(
    "/industry-policies",
    summary="List industry policy documents and country laws (public)",
    dependencies=[Depends(require_active_user)],
)
async def list_policy_documents(
    db:           DbDep,
    country_code: Optional[str]  = Query(default=None, description="Filter by country code e.g. 'TZ'"),
    policy_type:  Optional[str]  = Query(default=None, description="Filter by type: CONSTITUTION|LAW|REGULATION|POLICY|STANDARD|GUIDELINE|DIRECTIVE|FRAMEWORK"),
    industry_id:  Optional[uuid.UUID] = Query(default=None, description="Filter by industry"),
    active_only:  bool           = Query(default=True),
) -> dict:
    q = select(IndustryPolicyDocument)
    filters = []
    if active_only:
        filters.append(IndustryPolicyDocument.is_active == True)  # noqa: E712
    if country_code:
        filters.append(IndustryPolicyDocument.country_code == country_code)
    if policy_type:
        filters.append(IndustryPolicyDocument.policy_type == policy_type)
    if industry_id:
        filters.append(IndustryPolicyDocument.industry_id == industry_id)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q)
    items = result.scalars().all()
    return {"items": [_policy_out(p) for p in items], "count": len(items)}


@router.get(
    "/industry-policies/{policy_id}",
    summary="Get a policy document by ID (public)",
    dependencies=[Depends(require_active_user)],
)
async def get_policy_document(policy_id: uuid.UUID, db: DbDep) -> dict:
    result = await db.execute(
        select(IndustryPolicyDocument).where(IndustryPolicyDocument.id == policy_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Policy document not found.")
    return _policy_out(p)


@router.post(
    "/industry-policies",
    status_code=status.HTTP_201_CREATED,
    summary="Create a policy document [platform admin]",
    dependencies=[_admin_guard],
)
async def create_policy_document(body: CreatePolicyDocumentRequest, db: DbDep) -> dict:
    doc = IndustryPolicyDocument(**body.model_dump(exclude_none=True))
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    await db.commit()
    return _policy_out(doc)


@router.patch(
    "/industry-policies/{policy_id}",
    summary="Update a policy document [platform admin]",
    dependencies=[_admin_guard],
)
async def update_policy_document(
    policy_id: uuid.UUID,
    body:      UpdatePolicyDocumentRequest,
    db:        DbDep,
) -> dict:
    result = await db.execute(
        select(IndustryPolicyDocument).where(IndustryPolicyDocument.id == policy_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Policy document not found.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.flush()
    await db.refresh(p)
    await db.commit()
    return _policy_out(p)


@router.delete(
    "/industry-policies/{policy_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a policy document [platform admin]",
    dependencies=[_admin_guard],
)
async def delete_policy_document(policy_id: uuid.UUID, db: DbDep) -> dict:
    result = await db.execute(
        select(IndustryPolicyDocument).where(IndustryPolicyDocument.id == policy_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Policy document not found.")
    await db.delete(p)
    await db.commit()
    return {"detail": "Policy document deleted."}


# ═════════════════════════════════════════════════════════════════════════════
# PlatformGuide — professional guides and assistance documents
# ═════════════════════════════════════════════════════════════════════════════

class CreatePlatformGuideRequest(BaseModel):
    industry_id:        Optional[uuid.UUID] = None
    title:              str
    slug:               str
    guide_type:         GuideType
    applicable_sectors: Optional[list]  = None
    target_audience:    Optional[str]   = None
    content_md:         Optional[str]   = None
    file_url:           Optional[str]   = None
    file_format:        Optional[str]   = None
    version:            Optional[str]   = None
    language:           str             = "en"
    source_standard:    Optional[str]   = None
    is_public:          bool            = True


class UpdatePlatformGuideRequest(BaseModel):
    title:              Optional[str]       = None
    guide_type:         Optional[GuideType] = None
    applicable_sectors: Optional[list]     = None
    target_audience:    Optional[str]      = None
    content_md:         Optional[str]      = None
    file_url:           Optional[str]      = None
    file_format:        Optional[str]      = None
    version:            Optional[str]      = None
    language:           Optional[str]      = None
    source_standard:    Optional[str]      = None
    is_public:          Optional[bool]     = None
    is_active:          Optional[bool]     = None


def _guide_out(g) -> dict:
    return {
        "id":                 str(g.id),
        "industry_id":        str(g.industry_id) if g.industry_id else None,
        "title":              g.title,
        "slug":               g.slug,
        "guide_type":         g.guide_type,
        "applicable_sectors": g.applicable_sectors,
        "target_audience":    g.target_audience,
        "content_md":         g.content_md,
        "file_url":           g.file_url,
        "file_format":        g.file_format,
        "version":            g.version,
        "language":           g.language,
        "source_standard":    g.source_standard,
        "is_public":          g.is_public,
        "is_active":          g.is_active,
        "created_at":         g.created_at.isoformat(),
        "updated_at":         g.updated_at.isoformat(),
    }


@router.get(
    "/platform-guides",
    summary="List professional guides and assistance documents (public)",
    dependencies=[Depends(require_active_user)],
)
async def list_platform_guides(
    db:          DbDep,
    guide_type:  Optional[str]      = Query(default=None, description="Filter by type: PROFESSIONAL_GUIDE|REFERENCE_MANUAL|STANDARD|BEST_PRACTICE|TRAINING_MATERIAL|CHECKLIST|TEMPLATE|FAQ"),
    industry_id: Optional[uuid.UUID] = Query(default=None, description="Filter by industry"),
    language:    Optional[str]       = Query(default=None, description="Filter by language e.g. 'en', 'sw'"),
    active_only: bool                = Query(default=True),
) -> dict:
    q = select(PlatformGuide)
    filters = []
    if active_only:
        filters.append(PlatformGuide.is_active == True)  # noqa: E712
    if guide_type:
        filters.append(PlatformGuide.guide_type == guide_type)
    if industry_id:
        filters.append(PlatformGuide.industry_id == industry_id)
    if language:
        filters.append(PlatformGuide.language == language)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q)
    items = result.scalars().all()
    return {"items": [_guide_out(g) for g in items], "count": len(items)}


@router.get(
    "/platform-guides/{guide_id}",
    summary="Get a platform guide by ID (public)",
    dependencies=[Depends(require_active_user)],
)
async def get_platform_guide(guide_id: uuid.UUID, db: DbDep) -> dict:
    result = await db.execute(
        select(PlatformGuide).where(PlatformGuide.id == guide_id)
    )
    g = result.scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Guide not found.")
    return _guide_out(g)


@router.post(
    "/platform-guides",
    status_code=status.HTTP_201_CREATED,
    summary="Create a platform guide [platform admin]",
    dependencies=[_admin_guard],
)
async def create_platform_guide(body: CreatePlatformGuideRequest, db: DbDep) -> dict:
    guide = PlatformGuide(**body.model_dump(exclude_none=True))
    db.add(guide)
    await db.flush()
    await db.refresh(guide)
    await db.commit()
    return _guide_out(guide)


@router.patch(
    "/platform-guides/{guide_id}",
    summary="Update a platform guide [platform admin]",
    dependencies=[_admin_guard],
)
async def update_platform_guide(
    guide_id: uuid.UUID,
    body:     UpdatePlatformGuideRequest,
    db:       DbDep,
) -> dict:
    result = await db.execute(
        select(PlatformGuide).where(PlatformGuide.id == guide_id)
    )
    g = result.scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Guide not found.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(g, k, v)
    await db.flush()
    await db.refresh(g)
    await db.commit()
    return _guide_out(g)


@router.delete(
    "/platform-guides/{guide_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a platform guide [platform admin]",
    dependencies=[_admin_guard],
)
async def delete_platform_guide(guide_id: uuid.UUID, db: DbDep) -> dict:
    result = await db.execute(
        select(PlatformGuide).where(PlatformGuide.id == guide_id)
    )
    g = result.scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Guide not found.")
    await db.delete(g)
    await db.commit()
    return {"detail": "Platform guide deleted."}
