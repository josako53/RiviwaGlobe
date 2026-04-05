"""
app/api/v1/org_extended.py
═══════════════════════════════════════════════════════════════════════════════
Extended organisation capability endpoints.

All routes sit under /api/v1/orgs/{org_id}/... and are guarded by
require_org_role(MANAGER) or higher unless noted.

Route inventory
────────────────
  Locations
    POST   /orgs/{org_id}/locations
    GET    /orgs/{org_id}/locations
    PATCH  /orgs/{org_id}/locations/{location_id}
    DELETE /orgs/{org_id}/locations/{location_id}
    GET    /orgs/{org_id}/branches/{branch_id}/locations

  Content (1-to-1)
    GET    /orgs/{org_id}/content
    PUT    /orgs/{org_id}/content

  Org-level FAQs
    POST   /orgs/{org_id}/faqs
    GET    /orgs/{org_id}/faqs
    PATCH  /orgs/{org_id}/faqs/{faq_id}
    DELETE /orgs/{org_id}/faqs/{faq_id}

  Branches
    POST   /orgs/{org_id}/branches
    GET    /orgs/{org_id}/branches                (top-level)
    GET    /orgs/{org_id}/branches/{branch_id}/children
    PATCH  /orgs/{org_id}/branches/{branch_id}
    POST   /orgs/{org_id}/branches/{branch_id}/close
    DELETE /orgs/{org_id}/branches/{branch_id}
    GET    /orgs/{org_id}/branches/{branch_id}/tree   (subtree IDs)

  Branch managers
    POST   /orgs/{org_id}/branches/{branch_id}/managers
    GET    /orgs/{org_id}/branches/{branch_id}/managers
    DELETE /orgs/{org_id}/branches/{branch_id}/managers/{user_id}

  Services
    POST   /orgs/{org_id}/services
    GET    /orgs/{org_id}/services
    GET    /orgs/{org_id}/services/{service_id}
    PATCH  /orgs/{org_id}/services/{service_id}
    POST   /orgs/{org_id}/services/{service_id}/publish
    POST   /orgs/{org_id}/services/{service_id}/archive
    POST   /orgs/{org_id}/branches/{branch_id}/services/{service_id}/link
    DELETE /orgs/{org_id}/branches/{branch_id}/services/{service_id}/link

  Service personnel
    POST   /orgs/{org_id}/services/{service_id}/personnel
    GET    /orgs/{org_id}/services/{service_id}/personnel
    DELETE /orgs/{org_id}/services/{service_id}/personnel/{user_id}/{role}

  Service locations (monitoring table)
    POST   /orgs/{org_id}/services/{service_id}/locations
    GET    /orgs/{org_id}/services/{service_id}/locations
    PATCH  /orgs/{org_id}/services/{service_id}/locations/{sl_id}
    DELETE /orgs/{org_id}/services/{service_id}/locations/{sl_id}
    GET    /orgs/{org_id}/services/{service_id}/locations/tree/{branch_id}

  Service media
    POST   /orgs/{org_id}/services/{service_id}/media
    GET    /orgs/{org_id}/services/{service_id}/media
    POST   /orgs/{org_id}/services/{service_id}/media/{media_id}/set-cover
    DELETE /orgs/{org_id}/services/{service_id}/media/{media_id}

  Service FAQs
    POST   /orgs/{org_id}/services/{service_id}/faqs
    GET    /orgs/{org_id}/services/{service_id}/faqs
    PATCH  /orgs/{org_id}/services/{service_id}/faqs/{faq_id}
    DELETE /orgs/{org_id}/services/{service_id}/faqs/{faq_id}

  Service policies
    POST   /orgs/{org_id}/services/{service_id}/policies
    GET    /orgs/{org_id}/services/{service_id}/policies
    PATCH  /orgs/{org_id}/services/{service_id}/policies/{policy_id}
    DELETE /orgs/{org_id}/services/{service_id}/policies/{policy_id}
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field

from api.v1.deps import OrgExtendedServiceDep
from core.dependencies import require_active_user, require_org_role, require_platform_role
from models.organisation import OrganisationMember
from models.organisation_extended import (
    BranchStatus,
    OrgLocationType,
    OrgMediaType,
    OrgServiceStatus,
    OrgServiceType,
    ProductFormat,
    ServiceDeliveryMode,
    ServiceLocationStatus,
    ServicePersonnelRole,
)
from models.user import User
from schemas.common import MessageResponse

router = APIRouter(prefix="/orgs", tags=["Orgs — Extended"])


# ─────────────────────────────────────────────────────────────────────────────
# Inline response schemas
# ─────────────────────────────────────────────────────────────────────────────

class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              uuid.UUID
    organisation_id: uuid.UUID
    branch_id:       Optional[uuid.UUID] = None
    location_type:   str
    label:           Optional[str]       = None
    line1:           str
    line2:           Optional[str]       = None
    city:            str
    state:           Optional[str]       = None
    postal_code:     Optional[str]       = None
    country_code:    str
    region:          Optional[str]       = None
    latitude:        Optional[float]     = None
    longitude:       Optional[float]     = None
    is_primary:      bool


class ContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    org_id:         uuid.UUID
    vision:         Optional[str] = None
    mission:        Optional[str] = None
    objectives:     Optional[str] = None
    global_policy:  Optional[str] = None
    terms_of_use:   Optional[str] = None
    privacy_policy: Optional[str] = None
    updated_at:     datetime


class FAQResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:            uuid.UUID
    question:      str
    answer:        str
    display_order: int
    is_published:  bool


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    organisation_id:  uuid.UUID
    parent_branch_id: Optional[uuid.UUID] = None
    name:             str
    code:             Optional[str]       = None
    description:      Optional[str]       = None
    branch_type:      Optional[str]       = None
    status:           str
    phone:            Optional[str]       = None
    email:            Optional[str]       = None
    opened_on:        Optional[datetime]  = None
    closed_at:        Optional[datetime]  = None


class BranchManagerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              uuid.UUID
    branch_id:       uuid.UUID
    user_id:         uuid.UUID
    manager_title:   Optional[str] = None
    is_primary:      bool
    appointed_at:    datetime


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    organisation_id:     uuid.UUID
    branch_id:           Optional[uuid.UUID] = None
    title:               str
    slug:                str
    service_type:        str
    status:              str
    delivery_mode:       str
    product_format:      Optional[str]       = None
    inherits_location:   bool
    summary:             Optional[str]       = None
    category:            Optional[str]       = None
    subcategory:         Optional[str]       = None
    tags:                Optional[str]       = None
    base_price:          float
    currency_code:       str
    price_is_negotiable: bool
    delivery_time_days:  Optional[int]       = None
    is_featured:         bool
    view_count:          int
    published_at:        Optional[datetime]  = None


class ServicePersonnelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              uuid.UUID
    service_id:      uuid.UUID
    user_id:         uuid.UUID
    personnel_role:  str
    personnel_title: Optional[str] = None
    is_primary:      bool
    appointed_at:    datetime


class ServiceLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    service_id:       uuid.UUID
    branch_id:        Optional[uuid.UUID] = None
    location_id:      Optional[uuid.UUID] = None
    status:           str
    is_virtual:       bool
    virtual_platform: Optional[str]       = None
    virtual_url:      Optional[str]       = None
    operating_hours:  Optional[str]       = None
    capacity:         Optional[int]       = None
    contact_phone:    Optional[str]       = None
    contact_email:    Optional[str]       = None
    started_on:       Optional[datetime]  = None
    ended_on:         Optional[datetime]  = None


class ServiceMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:            uuid.UUID
    service_id:    uuid.UUID
    media_type:    str
    media_url:     Optional[str] = None
    storage_key:   Optional[str] = None
    alt_text:      Optional[str] = None
    caption:       Optional[str] = None
    is_cover:      bool
    display_order: int


class ServicePolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    service_id:     uuid.UUID
    policy_type:    str
    title:          str
    content:        str
    version:        str
    effective_date: Optional[datetime] = None
    is_active:      bool
    created_at:     datetime


# ─────────────────────────────────────────────────────────────────────────────
# Request bodies
# ─────────────────────────────────────────────────────────────────────────────

class CreateLocationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    location_type: OrgLocationType         = OrgLocationType.HEADQUARTERS
    branch_id:     Optional[uuid.UUID]     = None
    label:         Optional[str]           = Field(default=None, max_length=100)
    line1:         str                     = Field(min_length=1, max_length=200)
    line2:         Optional[str]           = Field(default=None, max_length=200)
    city:          str                     = Field(min_length=1, max_length=100)
    state:         Optional[str]           = Field(default=None, max_length=100)
    postal_code:   Optional[str]           = Field(default=None, max_length=20)
    country_code:  str                     = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    region:        Optional[str]           = Field(default=None, max_length=150)
    latitude:      Optional[float]         = None
    longitude:     Optional[float]         = None
    is_primary:    bool                    = False


class UpdateLocationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    location_type: Optional[OrgLocationType] = None
    label:         Optional[str]             = Field(default=None, max_length=100)
    line1:         Optional[str]             = Field(default=None, max_length=200)
    line2:         Optional[str]             = None
    city:          Optional[str]             = Field(default=None, max_length=100)
    state:         Optional[str]             = None
    postal_code:   Optional[str]             = None
    country_code:  Optional[str]             = Field(default=None, min_length=2, max_length=2)
    region:        Optional[str]             = None
    latitude:      Optional[float]           = None
    longitude:     Optional[float]           = None
    is_primary:    Optional[bool]            = None


class UpsertContentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    vision:         Optional[str] = None
    mission:        Optional[str] = None
    objectives:     Optional[str] = None
    global_policy:  Optional[str] = None
    terms_of_use:   Optional[str] = None
    privacy_policy: Optional[str] = None


class CreateFAQRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question:      str  = Field(min_length=1)
    answer:        str  = Field(min_length=1)
    display_order: int  = 0
    is_published:  bool = True


class UpdateFAQRequest(BaseModel):
    question:      Optional[str]  = None
    answer:        Optional[str]  = None
    display_order: Optional[int]  = None
    is_published:  Optional[bool] = None


class CreateBranchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name:             str                      = Field(min_length=1, max_length=255)
    code:             Optional[str]            = Field(default=None, max_length=50)
    description:      Optional[str]            = None
    branch_type:      Optional[str]            = Field(default=None, max_length=100)
    parent_branch_id: Optional[uuid.UUID]      = None
    status:           BranchStatus             = BranchStatus.ACTIVE
    phone:            Optional[str]            = Field(default=None, max_length=20)
    email:            Optional[str]            = Field(default=None, max_length=255)
    opened_on:        Optional[datetime]       = None


class UpdateBranchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name:         Optional[str]          = Field(default=None, max_length=255)
    code:         Optional[str]          = Field(default=None, max_length=50)
    description:  Optional[str]          = None
    branch_type:  Optional[str]          = None
    status:       Optional[BranchStatus] = None
    phone:        Optional[str]          = None
    email:        Optional[str]          = None


class AddBranchManagerRequest(BaseModel):
    user_id:       uuid.UUID
    manager_title: str  = Field(default="Branch Manager", max_length=100)
    is_primary:    bool = False


class CreateServiceRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title:               str                     = Field(min_length=1, max_length=255)
    slug:                str                     = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    service_type:        OrgServiceType
    delivery_mode:       ServiceDeliveryMode      = ServiceDeliveryMode.PHYSICAL
    product_format:      Optional[ProductFormat]  = None
    branch_id:           Optional[uuid.UUID]      = None
    inherits_location:   bool                     = True
    summary:             Optional[str]            = Field(default=None, max_length=500)
    description:         Optional[str]            = None
    category:            Optional[str]            = Field(default=None, max_length=100)
    subcategory:         Optional[str]            = Field(default=None, max_length=100)
    tags:                Optional[str]            = Field(default=None, max_length=500)
    base_price:          float                    = Field(default=0.0, ge=0)
    currency_code:       str                      = Field(default="USD", min_length=3, max_length=3)
    price_is_negotiable: bool                     = False
    delivery_time_days:  Optional[int]            = Field(default=None, ge=0)
    revisions_included:  Optional[int]            = Field(default=None, ge=0)
    sku:                 Optional[str]            = Field(default=None, max_length=100)
    stock_quantity:      Optional[int]            = None
    is_featured:         bool                     = False


class UpdateServiceRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title:               Optional[str]                   = Field(default=None, max_length=255)
    slug:                Optional[str]                   = Field(default=None, pattern=r"^[a-z0-9-]+$")
    status:              Optional[OrgServiceStatus]       = None
    delivery_mode:       Optional[ServiceDeliveryMode]   = None
    product_format:      Optional[ProductFormat]         = None
    inherits_location:   Optional[bool]                  = None
    summary:             Optional[str]                   = None
    description:         Optional[str]                   = None
    category:            Optional[str]                   = None
    subcategory:         Optional[str]                   = None
    tags:                Optional[str]                   = None
    base_price:          Optional[float]                 = Field(default=None, ge=0)
    currency_code:       Optional[str]                   = None
    price_is_negotiable: Optional[bool]                  = None
    delivery_time_days:  Optional[int]                   = None
    sku:                 Optional[str]                   = None
    stock_quantity:      Optional[int]                   = None
    is_featured:         Optional[bool]                  = None


class AssignPersonnelRequest(BaseModel):
    user_id:         uuid.UUID
    personnel_role:  ServicePersonnelRole
    personnel_title: Optional[str]           = Field(default=None, max_length=100)
    is_primary:      bool                    = False


class CreateServiceLocationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    branch_id:        Optional[uuid.UUID]          = None
    location_id:      Optional[uuid.UUID]          = None
    status:           ServiceLocationStatus         = ServiceLocationStatus.ACTIVE
    is_virtual:       bool                          = False
    virtual_platform: Optional[str]                = Field(default=None, max_length=100)
    virtual_url:      Optional[str]                = Field(default=None, max_length=1024)
    operating_hours:  Optional[str]                = Field(default=None, max_length=500)
    capacity:         Optional[int]                = None
    notes:            Optional[str]                = None
    contact_phone:    Optional[str]                = Field(default=None, max_length=20)
    contact_email:    Optional[str]                = Field(default=None, max_length=255)
    started_on:       Optional[datetime]           = None


class UpdateServiceLocationRequest(BaseModel):
    status:           Optional[ServiceLocationStatus] = None
    virtual_platform: Optional[str]                  = None
    virtual_url:      Optional[str]                  = None
    operating_hours:  Optional[str]                  = None
    capacity:         Optional[int]                  = None
    notes:            Optional[str]                  = None
    contact_phone:    Optional[str]                  = None
    contact_email:    Optional[str]                  = None
    started_on:       Optional[datetime]             = None
    ended_on:         Optional[datetime]             = None


class AddServiceMediaRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    media_type:    OrgMediaType
    media_url:     Optional[str] = Field(default=None, max_length=1024)
    storage_key:   Optional[str] = Field(default=None, max_length=512)
    alt_text:      Optional[str] = Field(default=None, max_length=255)
    caption:       Optional[str] = Field(default=None, max_length=500)
    is_cover:      bool          = False
    display_order: int           = 0


class CreatePolicyRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    policy_type:    str      = Field(min_length=1, max_length=50)
    title:          str      = Field(min_length=1, max_length=200)
    content:        str      = Field(min_length=1)
    version:        str      = Field(default="1.0", max_length=20)
    effective_date: Optional[datetime] = None


class UpdatePolicyRequest(BaseModel):
    title:          Optional[str]      = Field(default=None, max_length=200)
    content:        Optional[str]      = None
    version:        Optional[str]      = Field(default=None, max_length=20)
    effective_date: Optional[datetime] = None
    is_active:      Optional[bool]     = None


# ─────────────────────────────────────────────────────────────────────────────
# Auth guard shorthands
# ─────────────────────────────────────────────────────────────────────────────

_manager_guard = Depends(require_org_role(
    __import__("models.organisation", fromlist=["OrgMemberRole"]).OrgMemberRole.MANAGER
))
_admin_guard = Depends(require_org_role(
    __import__("models.organisation", fromlist=["OrgMemberRole"]).OrgMemberRole.ADMIN
))
_owner_guard = Depends(require_org_role(
    __import__("models.organisation", fromlist=["OrgMemberRole"]).OrgMemberRole.OWNER
))
_platform_admin_guard = Depends(require_platform_role("admin"))


# ═════════════════════════════════════════════════════════════════════════════
# Locations
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a physical location to this organisation",
    dependencies=[_admin_guard],
)
async def add_location(
    org_id: uuid.UUID,
    body:   CreateLocationRequest,
    svc:    OrgExtendedServiceDep,
) -> LocationResponse:
    """Register a physical address for the organisation or one of its branches."""
    data = body.model_dump(exclude_none=True)
    location = await svc.add_location(org_id, data)
    return LocationResponse.model_validate(location)


@router.get(
    "/{org_id}/locations",
    response_model=list[LocationResponse],
    status_code=status.HTTP_200_OK,
    summary="List all locations for this organisation",
    dependencies=[Depends(require_active_user)],
)
async def list_locations(
    org_id: uuid.UUID,
    svc:    OrgExtendedServiceDep,
) -> list[LocationResponse]:
    locations = await svc.list_locations(org_id)
    return [LocationResponse.model_validate(loc) for loc in locations]


@router.patch(
    "/{org_id}/locations/{location_id}",
    response_model=LocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a location",
    dependencies=[_admin_guard],
)
async def update_location(
    org_id:      uuid.UUID,
    location_id: uuid.UUID,
    body:        UpdateLocationRequest,
    svc:         OrgExtendedServiceDep,
) -> LocationResponse:
    fields = body.model_dump(exclude_none=True)
    loc = await svc.update_location(org_id, location_id, **fields)
    return LocationResponse.model_validate(loc)


@router.delete(
    "/{org_id}/locations/{location_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a location",
    dependencies=[_admin_guard],
)
async def delete_location(
    org_id:      uuid.UUID,
    location_id: uuid.UUID,
    svc:         OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.delete_location(org_id, location_id)
    return MessageResponse(message="Location deleted.")


@router.get(
    "/{org_id}/branches/{branch_id}/locations",
    response_model=list[LocationResponse],
    status_code=status.HTTP_200_OK,
    summary="List locations for a specific branch",
    dependencies=[Depends(require_active_user)],
)
async def list_branch_locations(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    svc:       OrgExtendedServiceDep,
) -> list[LocationResponse]:
    locations = await svc.list_branch_locations(branch_id)
    return [LocationResponse.model_validate(loc) for loc in locations]


# ═════════════════════════════════════════════════════════════════════════════
# Content  (1-to-1 upsert)
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{org_id}/content",
    response_model=Optional[ContentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get organisation content profile",
    dependencies=[Depends(require_active_user)],
)
async def get_content(
    org_id: uuid.UUID,
    svc:    OrgExtendedServiceDep,
) -> Optional[ContentResponse]:
    """Returns null if no content profile has been created yet."""
    content = await svc.get_content(org_id)
    return ContentResponse.model_validate(content) if content else None


@router.put(
    "/{org_id}/content",
    response_model=ContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update organisation content profile",
    dependencies=[_admin_guard],
)
async def upsert_content(
    org_id: uuid.UUID,
    body:   UpsertContentRequest,
    svc:    OrgExtendedServiceDep,
) -> ContentResponse:
    """
    Idempotent upsert: creates the content row if it does not exist,
    updates it if it does. Partial updates are supported (null fields
    are ignored; supply only the fields you want to change).
    """
    fields = body.model_dump(exclude_none=True)
    content = await svc.upsert_content(org_id, **fields)
    return ContentResponse.model_validate(content)


# ═════════════════════════════════════════════════════════════════════════════
# Org-level FAQs
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/faqs",
    response_model=FAQResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an FAQ to this organisation's profile",
    dependencies=[_manager_guard],
)
async def add_org_faq(
    org_id: uuid.UUID,
    body:   CreateFAQRequest,
    svc:    OrgExtendedServiceDep,
) -> FAQResponse:
    faq = await svc.add_faq(
        org_id,
        question=body.question,
        answer=body.answer,
        display_order=body.display_order,
        is_published=body.is_published,
    )
    return FAQResponse.model_validate(faq)


@router.get(
    "/{org_id}/faqs",
    response_model=list[FAQResponse],
    status_code=status.HTTP_200_OK,
    summary="List FAQs for this organisation",
    dependencies=[Depends(require_active_user)],
)
async def list_org_faqs(
    org_id:         uuid.UUID,
    svc:            OrgExtendedServiceDep,
    published_only: bool = Query(default=True),
) -> list[FAQResponse]:
    faqs = await svc.list_faqs(org_id, published_only=published_only)
    return [FAQResponse.model_validate(f) for f in faqs]


@router.patch(
    "/{org_id}/faqs/{faq_id}",
    response_model=FAQResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an org FAQ",
    dependencies=[_manager_guard],
)
async def update_org_faq(
    org_id: uuid.UUID,
    faq_id: uuid.UUID,
    body:   UpdateFAQRequest,
    svc:    OrgExtendedServiceDep,
) -> FAQResponse:
    fields = body.model_dump(exclude_none=True)
    faq = await svc.update_faq(org_id, faq_id, **fields)
    return FAQResponse.model_validate(faq)


@router.delete(
    "/{org_id}/faqs/{faq_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete an org FAQ",
    dependencies=[_manager_guard],
)
async def delete_org_faq(
    org_id: uuid.UUID,
    faq_id: uuid.UUID,
    svc:    OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.delete_faq(org_id, faq_id)
    return MessageResponse(message="FAQ deleted.")


# ═════════════════════════════════════════════════════════════════════════════
# Branches
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/branches",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a branch or sub-branch",
    dependencies=[_admin_guard],
)
async def create_branch(
    org_id: uuid.UUID,
    body:   CreateBranchRequest,
    svc:    OrgExtendedServiceDep,
) -> BranchResponse:
    """
    Creates a branch under the organisation, or a sub-branch under an
    existing branch (set `parent_branch_id`). Supports unlimited depth.
    Requires ADMIN role.
    """
    data = body.model_dump(exclude={"name"}, exclude_none=True)
    branch = await svc.create_branch(org_id, body.name, data)
    return BranchResponse.model_validate(branch)


@router.get(
    "/{org_id}/branches",
    response_model=list[BranchResponse],
    status_code=status.HTTP_200_OK,
    summary="List top-level branches (direct children of the org)",
    dependencies=[Depends(require_active_user)],
)
async def list_top_level_branches(
    org_id: uuid.UUID,
    svc:    OrgExtendedServiceDep,
) -> list[BranchResponse]:
    branches = await svc.list_top_level_branches(org_id)
    return [BranchResponse.model_validate(b) for b in branches]


@router.get(
    "/{org_id}/branches/{branch_id}/children",
    response_model=list[BranchResponse],
    status_code=status.HTTP_200_OK,
    summary="List direct children of a branch",
    dependencies=[Depends(require_active_user)],
)
async def list_child_branches(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    svc:       OrgExtendedServiceDep,
) -> list[BranchResponse]:
    branches = await svc.list_child_branches(org_id, branch_id)
    return [BranchResponse.model_validate(b) for b in branches]


@router.get(
    "/{org_id}/branches/{branch_id}/tree",
    response_model=list[uuid.UUID],
    status_code=status.HTTP_200_OK,
    summary="Get all branch IDs in the subtree (WITH RECURSIVE)",
    dependencies=[Depends(require_active_user)],
)
async def get_branch_tree(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    svc:       OrgExtendedServiceDep,
) -> list[uuid.UUID]:
    """
    Returns all branch IDs in the subtree rooted at `branch_id`,
    including the root itself. Uses a PostgreSQL WITH RECURSIVE CTE.

    Useful for building full org tree UIs and for scoping monitoring queries
    to a branch manager's span of control.
    """
    return await svc.get_branch_tree(org_id, branch_id)


@router.patch(
    "/{org_id}/branches/{branch_id}",
    response_model=BranchResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a branch",
    dependencies=[_admin_guard],
)
async def update_branch(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    body:      UpdateBranchRequest,
    svc:       OrgExtendedServiceDep,
) -> BranchResponse:
    fields = body.model_dump(exclude_none=True)
    branch = await svc.update_branch(org_id, branch_id, **fields)
    return BranchResponse.model_validate(branch)


@router.post(
    "/{org_id}/branches/{branch_id}/close",
    response_model=BranchResponse,
    status_code=status.HTTP_200_OK,
    summary="Close a branch",
    dependencies=[_admin_guard],
)
async def close_branch(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    svc:       OrgExtendedServiceDep,
) -> BranchResponse:
    """
    Sets status=CLOSED and stamps closed_at. Child branches are unaffected
    (their parent_branch_id is SET NULL — they become orphaned top-level
    branches of the org).
    """
    branch = await svc.close_branch(org_id, branch_id)
    return BranchResponse.model_validate(branch)


@router.delete(
    "/{org_id}/branches/{branch_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a branch",
    dependencies=[_owner_guard],
)
async def delete_branch(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    svc:       OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.delete_branch(org_id, branch_id)
    return MessageResponse(message=f"Branch {branch_id} deleted.")


# ═════════════════════════════════════════════════════════════════════════════
# Branch managers
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/branches/{branch_id}/managers",
    response_model=BranchManagerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a manager to a branch",
    dependencies=[_admin_guard],
)
async def add_branch_manager(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    body:      AddBranchManagerRequest,
    svc:       OrgExtendedServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(
        __import__("models.organisation", fromlist=["OrgMemberRole"]).OrgMemberRole.ADMIN
    ))],
) -> BranchManagerResponse:
    manager = await svc.add_branch_manager(
        org_id, branch_id, body.user_id,
        manager_title=body.manager_title,
        is_primary=body.is_primary,
        appointed_by_id=membership.user_id,
    )
    return BranchManagerResponse.model_validate(manager)


@router.get(
    "/{org_id}/branches/{branch_id}/managers",
    response_model=list[BranchManagerResponse],
    status_code=status.HTTP_200_OK,
    summary="List managers of a branch",
    dependencies=[Depends(require_active_user)],
)
async def list_branch_managers(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    svc:       OrgExtendedServiceDep,
) -> list[BranchManagerResponse]:
    managers = await svc.list_branch_managers(org_id, branch_id)
    return [BranchManagerResponse.model_validate(m) for m in managers]


@router.delete(
    "/{org_id}/branches/{branch_id}/managers/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a manager from a branch",
    dependencies=[_admin_guard],
)
async def remove_branch_manager(
    org_id:    uuid.UUID,
    branch_id: uuid.UUID,
    user_id:   uuid.UUID,
    svc:       OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.remove_branch_manager(org_id, branch_id, user_id)
    return MessageResponse(message="Manager removed.")


# ═════════════════════════════════════════════════════════════════════════════
# Services
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a service / product / program listing",
    dependencies=[_manager_guard],
)
async def create_service(
    org_id: uuid.UUID,
    body:   CreateServiceRequest,
    svc:    OrgExtendedServiceDep,
) -> ServiceResponse:
    """
    Create a new listing. `service_type` controls the semantics:
    - SERVICE — freelance-style deliverable (Fiverr model)
    - PRODUCT — physical or digital goods (marketplace model)
    - PROGRAM — government/NGO assistance program

    `slug` must be globally unique (lowercase letters, numbers, hyphens).
    Starts in DRAFT status — call `/publish` when ready.
    """
    data = body.model_dump(exclude_none=True)
    service = await svc.create_service(org_id, data)
    return ServiceResponse.model_validate(service)


@router.get(
    "/{org_id}/services",
    response_model=list[ServiceResponse],
    status_code=status.HTTP_200_OK,
    summary="List services for this organisation",
    dependencies=[Depends(require_active_user)],
)
async def list_org_services(
    org_id:      uuid.UUID,
    svc:         OrgExtendedServiceDep,
    active_only: bool = Query(default=False),
    svc_status:  Optional[OrgServiceStatus] = Query(default=None, alias="status"),
) -> list[ServiceResponse]:
    services = await svc.list_org_services(
        org_id, status=svc_status, active_only=active_only
    )
    return [ServiceResponse.model_validate(s) for s in services]


@router.get(
    "/{org_id}/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a service",
    dependencies=[Depends(require_active_user)],
)
async def get_service(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> ServiceResponse:
    service = await svc.get_service(service_id)
    return ServiceResponse.model_validate(service)


@router.patch(
    "/{org_id}/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a service",
    dependencies=[_manager_guard],
)
async def update_service(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    body:       UpdateServiceRequest,
    svc:        OrgExtendedServiceDep,
) -> ServiceResponse:
    fields = body.model_dump(exclude_none=True)
    service = await svc.update_service(org_id, service_id, **fields)
    return ServiceResponse.model_validate(service)


@router.post(
    "/{org_id}/services/{service_id}/publish",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Publish a service (DRAFT → ACTIVE)",
    dependencies=[_manager_guard],
)
async def publish_service(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> ServiceResponse:
    service = await svc.publish_service(org_id, service_id)
    return ServiceResponse.model_validate(service)


@router.post(
    "/{org_id}/services/{service_id}/archive",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive a service (soft-delete)",
    dependencies=[_admin_guard],
)
async def archive_service(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> ServiceResponse:
    service = await svc.archive_service(org_id, service_id)
    return ServiceResponse.model_validate(service)


@router.post(
    "/{org_id}/branches/{branch_id}/services/{service_id}/link",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link a service to a branch's offering",
    dependencies=[_manager_guard],
)
async def link_branch_service(
    org_id:     uuid.UUID,
    branch_id:  uuid.UUID,
    service_id: uuid.UUID,
    svc:        OrgExtendedServiceDep,
    inherited:  bool = Query(default=True),
) -> MessageResponse:
    await svc.link_branch_service(org_id, branch_id, service_id, inherited)
    return MessageResponse(message="Service linked to branch.")


@router.delete(
    "/{org_id}/branches/{branch_id}/services/{service_id}/link",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Unlink a service from a branch",
    dependencies=[_manager_guard],
)
async def unlink_branch_service(
    org_id:     uuid.UUID,
    branch_id:  uuid.UUID,
    service_id: uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.unlink_branch_service(org_id, branch_id, service_id)
    return MessageResponse(message="Service unlinked from branch.")


# ═════════════════════════════════════════════════════════════════════════════
# Service personnel
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/services/{service_id}/personnel",
    response_model=ServicePersonnelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a user to a service in a named role",
    dependencies=[_admin_guard],
)
async def assign_service_personnel(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    body:       AssignPersonnelRequest,
    svc:        OrgExtendedServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(
        __import__("models.organisation", fromlist=["OrgMemberRole"]).OrgMemberRole.ADMIN
    ))],
) -> ServicePersonnelResponse:
    """
    Assign a user as LEADER, SUPERVISOR, or COORDINATOR on this service.

    A user can hold multiple different roles on the same service
    (two separate rows). The same role cannot be assigned twice
    (UNIQUE on service_id, user_id, personnel_role).
    """
    personnel = await svc.assign_service_personnel(
        org_id, service_id, body.user_id, body.personnel_role,
        body.personnel_title, body.is_primary,
        appointed_by_id=membership.user_id,
    )
    return ServicePersonnelResponse.model_validate(personnel)


@router.get(
    "/{org_id}/services/{service_id}/personnel",
    response_model=list[ServicePersonnelResponse],
    status_code=status.HTTP_200_OK,
    summary="List personnel assigned to a service",
    dependencies=[Depends(require_active_user)],
)
async def list_service_personnel(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> list[ServicePersonnelResponse]:
    personnel = await svc.list_service_personnel(service_id)
    return [ServicePersonnelResponse.model_validate(p) for p in personnel]


@router.delete(
    "/{org_id}/services/{service_id}/personnel/{user_id}/{role}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a personnel assignment",
    dependencies=[_admin_guard],
)
async def remove_service_personnel(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    user_id:    uuid.UUID,
    role:       ServicePersonnelRole,
    svc:        OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.remove_service_personnel(org_id, service_id, user_id, role)
    return MessageResponse(message="Personnel assignment removed.")


# ═════════════════════════════════════════════════════════════════════════════
# Service locations  (the monitoring table)
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/services/{service_id}/locations",
    response_model=ServiceLocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pin a service to a deployment address",
    dependencies=[_manager_guard],
)
async def add_service_location(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    body:       CreateServiceLocationRequest,
    svc:        OrgExtendedServiceDep,
) -> ServiceLocationResponse:
    """
    Register where a service is deployed.
    For virtual deployments set `is_virtual=True` and `location_id=null`.
    For physical deployments set `location_id` to an existing OrgLocation.
    HYBRID services have one row of each type.
    """
    data = body.model_dump(exclude_none=True)
    sl = await svc.add_service_location(org_id, service_id, data)
    return ServiceLocationResponse.model_validate(sl)


@router.get(
    "/{org_id}/services/{service_id}/locations",
    response_model=list[ServiceLocationResponse],
    status_code=status.HTTP_200_OK,
    summary="List all deployment locations for a service",
    dependencies=[Depends(require_active_user)],
)
async def list_service_locations(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> list[ServiceLocationResponse]:
    sls = await svc.list_service_locations(service_id)
    return [ServiceLocationResponse.model_validate(sl) for sl in sls]


@router.get(
    "/{org_id}/services/{service_id}/locations/tree/{branch_id}",
    response_model=list[ServiceLocationResponse],
    status_code=status.HTTP_200_OK,
    summary="List service deployments visible from a branch (full subtree)",
    dependencies=[Depends(require_active_user)],
)
async def list_service_locations_for_branch_tree(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    branch_id:  uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> list[ServiceLocationResponse]:
    """
    Returns all deployment rows for the service that are operated by
    `branch_id` or any of its descendants (WITH RECURSIVE subtree walk).

    An Ambassador of Rome passes their branch_id to see all visa processing
    locations in the Embassy of Rome tree.
    A Secretary of State passes the Department of State branch_id to see
    all locations across all embassies worldwide.
    """
    sls = await svc.list_service_locations_for_branch_tree(
        org_id, service_id, branch_id
    )
    return [ServiceLocationResponse.model_validate(sl) for sl in sls]


@router.patch(
    "/{org_id}/services/{service_id}/locations/{sl_id}",
    response_model=ServiceLocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a service deployment location",
    dependencies=[_manager_guard],
)
async def update_service_location(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    sl_id:      uuid.UUID,
    body:       UpdateServiceLocationRequest,
    svc:        OrgExtendedServiceDep,
) -> ServiceLocationResponse:
    fields = body.model_dump(exclude_none=True)
    sl = await svc.update_service_location(org_id, service_id, sl_id, **fields)
    return ServiceLocationResponse.model_validate(sl)


@router.delete(
    "/{org_id}/services/{service_id}/locations/{sl_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a service deployment location",
    dependencies=[_admin_guard],
)
async def delete_service_location(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    sl_id:      uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.delete_service_location(org_id, service_id, sl_id)
    return MessageResponse(message="Service location removed.")


# ═════════════════════════════════════════════════════════════════════════════
# Service media
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/services/{service_id}/media",
    response_model=ServiceMediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a media asset to a service listing",
    dependencies=[_manager_guard],
)
async def add_service_media(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    body:       AddServiceMediaRequest,
    svc:        OrgExtendedServiceDep,
) -> ServiceMediaResponse:
    """
    Upload metadata for an image, video, or document attached to a service.
    The actual file upload happens separately via a pre-signed S3 URL.
    Pass the resulting CDN URL as `media_url`.
    """
    data = body.model_dump(exclude_none=True)
    media = await svc.add_service_media(org_id, service_id, data)
    return ServiceMediaResponse.model_validate(media)


@router.get(
    "/{org_id}/services/{service_id}/media",
    response_model=list[ServiceMediaResponse],
    status_code=status.HTTP_200_OK,
    summary="List media for a service",
    dependencies=[Depends(require_active_user)],
)
async def list_service_media(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> list[ServiceMediaResponse]:
    media = await svc.list_service_media(service_id)
    return [ServiceMediaResponse.model_validate(m) for m in media]


@router.post(
    "/{org_id}/services/{service_id}/media/{media_id}/set-cover",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Set a media item as the service cover image",
    dependencies=[_manager_guard],
)
async def set_cover_media(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    media_id:   uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> MessageResponse:
    """Clears is_cover on all other media for this service, then sets it on this item."""
    await svc.set_cover_media(org_id, service_id, media_id)
    return MessageResponse(message="Cover image updated.")


@router.delete(
    "/{org_id}/services/{service_id}/media/{media_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a service media asset",
    dependencies=[_manager_guard],
)
async def delete_service_media(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    media_id:   uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.delete_service_media(org_id, service_id, media_id)
    return MessageResponse(message="Media deleted.")


# ═════════════════════════════════════════════════════════════════════════════
# Service FAQs
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/services/{service_id}/faqs",
    response_model=FAQResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an FAQ to a service listing",
    dependencies=[_manager_guard],
)
async def add_service_faq(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    body:       CreateFAQRequest,
    svc:        OrgExtendedServiceDep,
) -> FAQResponse:
    faq = await svc.add_service_faq(
        org_id, service_id,
        question=body.question, answer=body.answer,
        display_order=body.display_order, is_published=body.is_published,
    )
    return FAQResponse.model_validate(faq)


@router.get(
    "/{org_id}/services/{service_id}/faqs",
    response_model=list[FAQResponse],
    status_code=status.HTTP_200_OK,
    summary="List FAQs for a service",
    dependencies=[Depends(require_active_user)],
)
async def list_service_faqs(
    org_id:         uuid.UUID,
    service_id:     uuid.UUID,
    svc:            OrgExtendedServiceDep,
    published_only: bool = Query(default=True),
) -> list[FAQResponse]:
    faqs = await svc.list_service_faqs(service_id, published_only=published_only)
    return [FAQResponse.model_validate(f) for f in faqs]


@router.patch(
    "/{org_id}/services/{service_id}/faqs/{faq_id}",
    response_model=FAQResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a service FAQ",
    dependencies=[_manager_guard],
)
async def update_service_faq(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    faq_id:     uuid.UUID,
    body:       UpdateFAQRequest,
    svc:        OrgExtendedServiceDep,
) -> FAQResponse:
    fields = body.model_dump(exclude_none=True)
    faq = await svc.update_service_faq(org_id, service_id, faq_id, **fields)
    return FAQResponse.model_validate(faq)


@router.delete(
    "/{org_id}/services/{service_id}/faqs/{faq_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a service FAQ",
    dependencies=[_manager_guard],
)
async def delete_service_faq(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    faq_id:     uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.delete_service_faq(org_id, service_id, faq_id)
    return MessageResponse(message="Service FAQ deleted.")


# ═════════════════════════════════════════════════════════════════════════════
# Service policies
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{org_id}/services/{service_id}/policies",
    response_model=ServicePolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a policy version for a service",
    dependencies=[_admin_guard],
)
async def create_service_policy(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    body:       CreatePolicyRequest,
    svc:        OrgExtendedServiceDep,
) -> ServicePolicyResponse:
    """
    Adds a new policy version. If an active version of the same `policy_type`
    already exists, it is deactivated automatically (version history pattern:
    old versions are retained as an audit log).

    Common `policy_type` values: `refund`, `terms_of_use`, `delivery`,
    `eligibility`, `copyright`, `privacy`.
    """
    data = body.model_dump(exclude_none=True)
    policy = await svc.create_service_policy(org_id, service_id, data)
    return ServicePolicyResponse.model_validate(policy)


@router.get(
    "/{org_id}/services/{service_id}/policies",
    response_model=list[ServicePolicyResponse],
    status_code=status.HTTP_200_OK,
    summary="List policies for a service",
    dependencies=[Depends(require_active_user)],
)
async def list_service_policies(
    org_id:      uuid.UUID,
    service_id:  uuid.UUID,
    svc:         OrgExtendedServiceDep,
    active_only: bool          = Query(default=True),
    policy_type: Optional[str] = Query(default=None),
) -> list[ServicePolicyResponse]:
    """
    Returns active policy versions by default. Pass `active_only=false`
    to see the full version history. Filter by `policy_type` to retrieve
    a specific policy (e.g. `?policy_type=refund`).
    """
    policies = await svc.list_service_policies(
        service_id, active_only=active_only, policy_type=policy_type
    )
    return [ServicePolicyResponse.model_validate(p) for p in policies]


@router.patch(
    "/{org_id}/services/{service_id}/policies/{policy_id}",
    response_model=ServicePolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a service policy",
    dependencies=[_admin_guard],
)
async def update_service_policy(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    policy_id:  uuid.UUID,
    body:       UpdatePolicyRequest,
    svc:        OrgExtendedServiceDep,
) -> ServicePolicyResponse:
    fields = body.model_dump(exclude_none=True)
    policy = await svc.update_service_policy(org_id, service_id, policy_id, **fields)
    return ServicePolicyResponse.model_validate(policy)


@router.delete(
    "/{org_id}/services/{service_id}/policies/{policy_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a service policy",
    dependencies=[_admin_guard],
)
async def delete_service_policy(
    org_id:     uuid.UUID,
    service_id: uuid.UUID,
    policy_id:  uuid.UUID,
    svc:        OrgExtendedServiceDep,
) -> MessageResponse:
    await svc.delete_service_policy(org_id, service_id, policy_id)
    return MessageResponse(message="Policy deleted.")
