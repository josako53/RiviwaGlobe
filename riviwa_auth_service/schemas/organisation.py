# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  schemas/organisation.py
# ───────────────────────────────────────────────────────────────────────────
"""
schemas/organisation.py
═══════════════════════════════════════════════════════════════════════════════
Pydantic v2 request and response schemas for the Organisation domain.

Covers:
  · OrgResponse          — full org details (read)
  · OrgListResponse      — paginated org discovery list
  · MemberResponse       — org member read
  · InviteResponse       — org invite read
  · CreateOrgRequest     — create org body
  · UpdateOrgRequest     — partial update body (all fields optional)
  · AddMemberRequest     — add member directly
  · ChangeRoleRequest    — change a member's role
  · TransferOwnershipRequest — transfer org ownership
  · SendInviteRequest    — send an email / user invite
  · AdminStatusRequest   — admin verify / suspend / ban (optional reason)

Import via the package root:

    from schemas import OrgResponse, CreateOrgRequest, ...
    # or directly:
    from schemas.organisation import OrgResponse
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from models.organisation import OrgMemberRole, OrgType


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class OrgResponse(BaseModel):
    """
    Public-safe organisation profile.
    Returned by GET /orgs, GET /orgs/{id}, and POST /orgs.
    """
    model_config = ConfigDict(from_attributes=True)

    id:                  uuid.UUID
    slug:                str
    legal_name:          str
    display_name:        str
    org_type:            str
    status:              str
    is_verified:         bool
    description:         Optional[str]      = None
    logo_url:            Optional[str]      = None
    website_url:         Optional[str]      = None
    support_email:       Optional[str]      = None
    support_phone:       Optional[str]      = None
    country_code:        Optional[str]      = None
    timezone:            Optional[str]      = None
    registration_number: Optional[str]      = None
    tax_id:              Optional[str]      = None
    max_members:         int
    created_at:          Optional[datetime] = None


class OrgListResponse(BaseModel):
    """
    Paginated org discovery list.  Returned by GET /orgs.
    """
    items: List[OrgResponse]
    total: int
    page:  int
    limit: int
    pages: int


class MemberResponse(BaseModel):
    """Organisation membership row — role, status, join date."""
    model_config = ConfigDict(from_attributes=True)

    user_id:         uuid.UUID
    organisation_id: uuid.UUID
    org_role:        str
    status:          str
    joined_at:       Optional[datetime] = None


class InviteResponse(BaseModel):
    """Pending / responded invite record."""
    model_config = ConfigDict(from_attributes=True)

    id:              uuid.UUID
    organisation_id: uuid.UUID
    invited_by_id:   uuid.UUID
    invited_email:   Optional[str]       = None
    invited_user_id: Optional[uuid.UUID] = None
    invited_role:    str
    status:          str
    expires_at:      Optional[datetime]  = None


# ─────────────────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    """Body for POST /orgs."""
    model_config = ConfigDict(str_strip_whitespace=True)

    legal_name:          str           = Field(min_length=2,  max_length=200)
    display_name:        str           = Field(min_length=2,  max_length=100)
    slug:                str           = Field(min_length=3,  max_length=80,
                                               pattern=r"^[a-z0-9-]+$")
    org_type:            OrgType
    description:         Optional[str] = Field(default=None, max_length=1000)
    logo_url:            Optional[str] = None
    website_url:         Optional[str] = None
    support_email:       Optional[str] = None
    support_phone:       Optional[str] = None
    country_code:        Optional[str] = Field(default=None, min_length=2, max_length=2)
    timezone:            Optional[str] = None
    registration_number: Optional[str] = None
    tax_id:              Optional[str] = None
    max_members:         int           = Field(default=0, ge=0)


class UpdateOrgRequest(BaseModel):
    """Body for PATCH /orgs/{org_id} — all fields optional."""
    model_config = ConfigDict(str_strip_whitespace=True)

    legal_name:          Optional[str] = None
    display_name:        Optional[str] = None
    slug:                Optional[str] = Field(default=None, pattern=r"^[a-z0-9-]+$")
    description:         Optional[str] = None
    logo_url:            Optional[str] = None
    website_url:         Optional[str] = None
    support_email:       Optional[str] = None
    support_phone:       Optional[str] = None
    country_code:        Optional[str] = Field(default=None, min_length=2, max_length=2)
    timezone:            Optional[str] = None
    registration_number: Optional[str] = None
    tax_id:              Optional[str] = None
    max_members:         Optional[int] = Field(default=None, ge=0)


class AddMemberRequest(BaseModel):
    """Body for POST /orgs/{org_id}/members."""
    user_id:  uuid.UUID
    org_role: OrgMemberRole


class ChangeRoleRequest(BaseModel):
    """Body for PATCH /orgs/{org_id}/members/{user_id}/role."""
    org_role: OrgMemberRole


class TransferOwnershipRequest(BaseModel):
    """Body for POST /orgs/{org_id}/transfer-ownership."""
    new_owner_id: uuid.UUID


class SendInviteRequest(BaseModel):
    """
    Body for POST /orgs/{org_id}/invites.
    Exactly one of invited_email or invited_user_id must be provided
    (validated in the service layer).
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    invited_role:    OrgMemberRole
    invited_email:   Optional[str]       = None
    invited_user_id: Optional[uuid.UUID] = None
    message:         Optional[str]       = Field(default=None, max_length=500)


class AdminStatusRequest(BaseModel):
    """
    Body for POST /orgs/{org_id}/verify|suspend|ban.
    Reason is optional for verify, recommended for suspend/ban.
    """
    reason: Optional[str] = Field(default=None, max_length=500)
