# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/organisations.py
# ───────────────────────────────────────────────────────────────────────────
"""
app/api/v1/organisations.py
═══════════════════════════════════════════════════════════════════════════════
Organisation lifecycle, membership, and invite endpoints.

Routes
──────
  Organisation CRUD
    POST   /api/v1/orgs                              Create organisation
    GET    /api/v1/orgs                               List / discover organisations (public)
    GET    /api/v1/orgs/{org_id}                     Get organisation
    PATCH  /api/v1/orgs/{org_id}                     Update organisation
    DELETE /api/v1/orgs/{org_id}                     Deactivate organisation (owner)

  Admin / platform operations
    POST   /api/v1/orgs/{org_id}/verify              Verify (platform admin)
    POST   /api/v1/orgs/{org_id}/suspend             Suspend (platform admin)
    POST   /api/v1/orgs/{org_id}/ban                 Ban (platform admin)

  Membership
    POST   /api/v1/orgs/{org_id}/members             Add member directly
    DELETE /api/v1/orgs/{org_id}/members/{user_id}   Remove member
    PATCH  /api/v1/orgs/{org_id}/members/{user_id}/role   Change member role
    POST   /api/v1/orgs/{org_id}/transfer-ownership  Transfer ownership

  Logo
    POST   /api/v1/orgs/{org_id}/logo                Upload organisation logo

  Invites
    POST   /api/v1/orgs/{org_id}/invites             Send invite
    POST   /api/v1/orgs/invites/{invite_id}/accept   Accept invite
    POST   /api/v1/orgs/invites/{invite_id}/decline  Decline invite
    DELETE /api/v1/orgs/{org_id}/invites/{invite_id} Cancel invite
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, UploadFile, status

from api.v1.deps import OrgServiceDep
from core.dependencies import (
    DbDep,
    get_org_context,
    require_active_user,
    require_org_role,
    require_platform_role,
    require_verified_user,
)
from models.organisation import (
    OrgMemberRole,
    OrgStatus,
    OrgType,
    Organisation,
    OrganisationInvite,
    OrganisationMember,
)
from models.user import User
from schemas.common import MessageResponse
from schemas.organisation import (
    AddMemberRequest,
    AdminStatusRequest,
    ChangeRoleRequest,
    CreateOrgRequest,
    InviteResponse,
    MemberResponse,
    OrgListResponse,
    OrgResponse,
    SendInviteRequest,
    TransferOwnershipRequest,
    UpdateOrgRequest,
)

router = APIRouter(prefix="/orgs", tags=["Organisations"])


# ─────────────────────────────────────────────────────────────────────────────
# Inline response schemas  (no separate schemas file exists yet)
# ─────────────────────────────────────────────────────────────────────────────


# Schemas are defined in schemas/organisation.py


# ─────────────────────────────────────────────────────────────────────────────
# Create organisation
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# List / discover organisations  (public)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=OrgListResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover organisations — public listing with search & filter",
)
async def list_orgs(
    svc:           OrgServiceDep,
    search:        Optional[str]     = Query(default=None,  description="Search by name or slug"),
    org_type:      Optional[OrgType] = Query(default=None,  description="Filter by org type"),
    verified_only: bool              = Query(default=True,  description="Only show verified orgs"),
    sort:          str               = Query(default="name", description="Sort by: name | created"),
    page:          int               = Query(default=1,     ge=1),
    limit:         int               = Query(default=20,    ge=1, le=100),
) -> OrgListResponse:
    """
    Public org discovery endpoint.

    No authentication required — anyone can browse verified, active organisations.
    Set `verified_only=false` to also include orgs awaiting verification (platform
    admin use).

    Supports full-text search across `display_name`, `legal_name`, and `slug`.
    """
    items, total = await svc.list_public(
        search=search,
        org_type=org_type,
        verified_only=verified_only,
        sort=sort,
        page=page,
        limit=limit,
    )
    pages = max(1, -(-total // limit))  # ceiling division
    return OrgListResponse(
        items=[OrgResponse.model_validate(o) for o in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post(
    "",
    response_model=OrgResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organisation",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Email not verified"},
        409: {"description": "Slug already taken"},
    },
)
async def create_org(
    body: CreateOrgRequest,
    svc:  OrgServiceDep,
    user: Annotated[User, Depends(require_verified_user)],
) -> OrgResponse:
    """
    Create a new organisation. The caller automatically becomes the **OWNER**.

    The organisation starts with status `PENDING_VERIFICATION` and must be
    approved by a platform admin via `POST /orgs/{org_id}/verify` before it
    can transact.

    Requires a **verified email** (`is_email_verified = true`).
    """
    org = await svc.create(
        created_by_id=user.id,
        legal_name=body.legal_name,
        display_name=body.display_name,
        slug=body.slug,
        org_type=body.org_type,
        description=body.description,
        logo_url=body.logo_url,
        website_url=body.website_url,
        support_email=body.support_email,
        support_phone=body.support_phone,
        country_code=body.country_code,
        timezone=body.timezone,
        registration_number=body.registration_number,
        tax_id=body.tax_id,
        max_members=body.max_members,
    )
    return OrgResponse.model_validate(org)


# ─────────────────────────────────────────────────────────────────────────────
# Get organisation
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{org_id}",
    response_model=OrgResponse,
    status_code=status.HTTP_200_OK,
    summary="Get organisation details",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Organisation not found"},
    },
)
async def get_org(
    org_id: uuid.UUID,
    svc:    OrgServiceDep,
    _user:  Annotated[User, Depends(require_active_user)],
) -> OrgResponse:
    """Return public details for an organisation."""
    org = await svc._get_or_404(org_id)
    return OrgResponse.model_validate(org)


# ─────────────────────────────────────────────────────────────────────────────
# Update organisation (ADMIN+)
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/{org_id}",
    response_model=OrgResponse,
    status_code=status.HTTP_200_OK,
    summary="Update organisation profile",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient org role (ADMIN required)"},
        404: {"description": "Organisation not found"},
        409: {"description": "Slug already taken"},
    },
)
async def update_org(
    org_id:     uuid.UUID,
    body:       UpdateOrgRequest,
    svc:        OrgServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.ADMIN))],
) -> OrgResponse:
    """
    Update organisation profile fields (PATCH semantics).

    Requires the caller to be on the **org dashboard** for this org and hold
    at least the `ADMIN` role.
    """
    org = await svc._get_or_404(org_id)
    updates = body.model_dump(exclude_none=True)
    updated_org = await svc.update(org=org, updates=updates)
    return OrgResponse.model_validate(updated_org)


# ─────────────────────────────────────────────────────────────────────────────
# Deactivate organisation (OWNER only)
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{org_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate (close) organisation",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Only the OWNER can close the organisation"},
        404: {"description": "Organisation not found"},
    },
)
async def deactivate_org(
    org_id:     uuid.UUID,
    svc:        OrgServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.OWNER))],
    reason:     Optional[str] = None,
) -> MessageResponse:
    """
    Owner-initiated closure of the organisation.

    Sets status to `DEACTIVATED`. This is reversible by a platform admin.
    Requires the caller to hold the `OWNER` role in this org.
    """
    org = await svc._get_or_404(org_id)
    await svc.deactivate(org=org, reason=reason)
    return MessageResponse(message=f"Organisation '{org.slug}' has been deactivated.")


# ─────────────────────────────────────────────────────────────────────────────
# Platform admin — verify / suspend / ban
# ─────────────────────────────────────────────────────────────────────────────

_admin_guard = Depends(require_platform_role("admin"))


@router.post(
    "/{org_id}/verify",
    response_model=OrgResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Verify organisation",
    dependencies=[_admin_guard],
)
async def verify_org(
    org_id: uuid.UUID,
    svc:    OrgServiceDep,
    user:   Annotated[User, Depends(require_active_user)],
) -> OrgResponse:
    """
    Approve a `PENDING_VERIFICATION` organisation.
    Transitions status → `ACTIVE`, sets `is_verified = true`.

    Requires `platform_role = admin` or `super_admin`.
    """
    org = await svc.verify(org_id=org_id, verified_by_id=user.id)
    return OrgResponse.model_validate(org)


@router.post(
    "/{org_id}/suspend",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Suspend organisation",
    dependencies=[_admin_guard],
)
async def suspend_org(
    org_id: uuid.UUID,
    body:   AdminStatusRequest,
    svc:    OrgServiceDep,
) -> MessageResponse:
    """Suspend the organisation. Requires `platform_role = admin`."""
    await svc.suspend(org_id=org_id, reason=body.reason)
    return MessageResponse(message=f"Organisation {org_id} has been suspended.")


@router.post(
    "/{org_id}/ban",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Ban organisation",
    dependencies=[_admin_guard],
)
async def ban_org(
    org_id: uuid.UUID,
    body:   AdminStatusRequest,
    svc:    OrgServiceDep,
) -> MessageResponse:
    """Permanently ban the organisation. Requires `platform_role = admin`."""
    await svc.ban(org_id=org_id, reason=body.reason)
    return MessageResponse(message=f"Organisation {org_id} has been banned.")


# ─────────────────────────────────────────────────────────────────────────────
# Membership — add / remove / change role / transfer ownership
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{org_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member directly (no invite)",
    responses={
        403: {"description": "ADMIN role required"},
        404: {"description": "User not found"},
        409: {"description": "User is already a member"},
    },
)
async def add_member(
    org_id:     uuid.UUID,
    body:       AddMemberRequest,
    svc:        OrgServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.ADMIN))],
) -> MemberResponse:
    """
    Add an existing platform user as a member without going through the
    invite flow.

    Requires `ADMIN` role or higher in the org. Cannot assign `OWNER` —
    use `POST /orgs/{org_id}/transfer-ownership` for that.
    """
    new_member = await svc.add_member_directly(
        org_id=org_id,
        user_id=body.user_id,
        org_role=body.org_role,
        added_by_id=membership.user_id,
    )
    return MemberResponse.model_validate(new_member)


@router.delete(
    "/{org_id}/members/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a member from the organisation",
    responses={
        403: {"description": "ADMIN role required / cannot remove OWNER"},
        404: {"description": "Member not found"},
    },
)
async def remove_member(
    org_id:     uuid.UUID,
    user_id:    uuid.UUID,
    svc:        OrgServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.ADMIN))],
    reason:     Optional[str] = None,
) -> MessageResponse:
    """
    Remove a member from the organisation.

    Cannot remove the `OWNER` — transfer ownership first.
    Requires `ADMIN` role or higher.
    """
    await svc.remove_member(
        org_id=org_id,
        user_id=user_id,
        removed_by_id=membership.user_id,
        reason=reason,
    )
    return MessageResponse(message=f"User {user_id} removed from organisation.")


@router.patch(
    "/{org_id}/members/{user_id}/role",
    response_model=MemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Change a member's role",
    responses={
        400: {"description": "Cannot assign OWNER role via this endpoint"},
        403: {"description": "ADMIN role required / cannot change OWNER's role"},
        404: {"description": "Member not found"},
    },
)
async def change_member_role(
    org_id:     uuid.UUID,
    user_id:    uuid.UUID,
    body:       ChangeRoleRequest,
    svc:        OrgServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.ADMIN))],
) -> MemberResponse:
    """
    Change the role of an existing member.

    Cannot assign `OWNER` via this endpoint — use `transfer-ownership`.
    Cannot change the existing `OWNER`'s role — transfer ownership first.
    Requires `ADMIN` role or higher.
    """
    updated = await svc.change_member_role(
        org_id=org_id,
        user_id=user_id,
        new_role=body.org_role,
        changed_by_id=membership.user_id,
    )
    return MemberResponse.model_validate(updated)


@router.post(
    "/{org_id}/transfer-ownership",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Transfer org ownership to another member",
    responses={
        403: {"description": "Only the current OWNER can transfer"},
        404: {"description": "New owner is not an active member"},
    },
)
async def transfer_ownership(
    org_id:     uuid.UUID,
    body:       TransferOwnershipRequest,
    svc:        OrgServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.OWNER))],
) -> MessageResponse:
    """
    Transfer the `OWNER` role to another active member.

    - The current owner is demoted to `ADMIN`.
    - The new owner is promoted to `OWNER`.

    Requires the caller to hold the `OWNER` role.
    The new owner must already be an active member of the organisation.
    """
    await svc.transfer_ownership(
        org_id=org_id,
        current_owner_id=membership.user_id,
        new_owner_id=body.new_owner_id,
    )
    return MessageResponse(
        message=f"Ownership transferred to user {body.new_owner_id}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Invites — send / accept / decline / cancel
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{org_id}/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send an organisation invite",
    responses={
        400: {"description": "Missing invited_email or invited_user_id"},
        403: {"description": "MANAGER role required"},
        409: {"description": "A pending invite already exists for this target"},
    },
)
async def send_invite(
    org_id:     uuid.UUID,
    body:       SendInviteRequest,
    svc:        OrgServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))],
) -> InviteResponse:
    """
    Invite someone to join the organisation.

    Supply either `invited_email` or `invited_user_id` (or both).

    - `invited_email` sends an invitation email to that address.
    - `invited_user_id` targets an existing platform user (used for in-app invitations).

    Cannot invite someone as `OWNER` — use `transfer-ownership`.
    Requires at least `MANAGER` role.
    """
    invite = await svc.send_invite(
        org_id=org_id,
        invited_by_id=membership.user_id,
        invited_role=body.invited_role,
        invited_email=body.invited_email,
        invited_user_id=body.invited_user_id,
        message=body.message,
    )
    return InviteResponse.model_validate(invite)


@router.post(
    "/invites/{invite_id}/accept",
    response_model=MemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept an organisation invite",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Invite not found or expired"},
        409: {"description": "Already a member of this organisation"},
    },
)
async def accept_invite(
    invite_id: uuid.UUID,
    svc:       OrgServiceDep,
    user:      Annotated[User, Depends(require_active_user)],
) -> MemberResponse:
    """
    Accept a pending organisation invite.

    The invite token is validated (must be `PENDING` and not expired).
    On success the caller becomes an active member with the role specified
    in the invite.

    Note: the `invite_id` here is used as the token identifier.
    In the full invite-link flow the raw token from the email is hashed
    and looked up — wire `token_hash` via `svc.accept_invite(token_hash, user.id)`.
    """
    # For token-based acceptance: hash the token received in the email link.
    # Endpoint shown here uses invite_id for in-app accept flows.
    from core.security import hash_token
    membership = await svc.accept_invite(
        token_hash=hash_token(str(invite_id)),
        user_id=user.id,
    )
    return MemberResponse.model_validate(membership)


@router.post(
    "/invites/{invite_id}/decline",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Decline an organisation invite",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Invite not found or expired"},
    },
)
async def decline_invite(
    invite_id: uuid.UUID,
    svc:       OrgServiceDep,
    user:      Annotated[User, Depends(require_active_user)],
) -> MessageResponse:
    """Decline a pending invite. The invite status is set to `DECLINED`."""
    from core.security import hash_token
    await svc.decline_invite(
        token_hash=hash_token(str(invite_id)),
        user_id=user.id,
    )
    return MessageResponse(message="Invite declined.")


@router.delete(
    "/{org_id}/invites/{invite_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a pending invite",
    responses={
        403: {"description": "MANAGER role required"},
        404: {"description": "Invite not found or already responded"},
    },
)
async def cancel_invite(
    org_id:     uuid.UUID,
    invite_id:  uuid.UUID,
    svc:        OrgServiceDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))],
) -> MessageResponse:
    """
    Cancel a pending invite before it is accepted or declined.

    Requires at least `MANAGER` role in the org.
    Only `PENDING` invites can be cancelled.
    """
    await svc.cancel_invite(
        invite_id=invite_id,
        cancelled_by_id=membership.user_id,
    )
    return MessageResponse(message=f"Invite {invite_id} cancelled.")


# ── Logo upload ────────────────────────────────────────────────────────────────

@router.post(
    "/{org_id}/logo",
    status_code=status.HTTP_200_OK,
    summary="Upload organisation logo",
    description=(
        "Upload a logo image for the organisation. "
        "Accepted formats: JPEG, PNG, WebP, SVG. Max 5 MB. "
        "The file is stored in MinIO and the URL is saved to Organisation.logo_url. "
        "A Kafka event is published so downstream services (feedback_service, "
        "stakeholder_service) can sync the new logo_url to their ProjectCache. "
        "Requires MANAGER role or higher."
    ),
    responses={
        200: {"description": "Logo uploaded — returns the new logo_url"},
        400: {"description": "Invalid file type or size exceeded"},
        403: {"description": "MANAGER role required"},
        404: {"description": "Organisation not found"},
    },
)
async def upload_org_logo(
    org_id:     uuid.UUID,
    file:       UploadFile,
    db:         DbDep,
    membership: Annotated[OrganisationMember, Depends(require_org_role(OrgMemberRole.MANAGER))],
) -> dict:
    """
    Upload an organisation logo.

    The upload flow:
      1. ImageService validates MIME type and size.
      2. File is stored at images/organisations/{org_id}/logo.{ext} in MinIO.
      3. Organisation.logo_url is updated in the DB.
      4. A Kafka org.events message is published so subscriber services can
         update their cached logo_url on any ProjectCache rows.
    """
    from core.config import settings as cfg
    from services.image_service import ImageService, ImageUploadError
    from sqlalchemy import select, update
    from models.organisation import Organisation
    from events.producer import EventProducer
    from events.topics import OrgEvents

    # Validate and store
    svc = ImageService(cfg)
    try:
        logo_url = await svc.upload(
            file=file,
            entity_type="organisations",
            entity_id=org_id,
            slot="logo",
        )
    except ImageUploadError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(exc))

    # Persist to DB
    await db.execute(
        update(Organisation)
        .where(Organisation.id == org_id)
        .values(logo_url=logo_url)
    )
    await db.commit()

    # Publish Kafka event so feedback_service / stakeholder_service can sync
    producer = EventProducer()
    await producer.publish(
        topic=OrgEvents.UPDATED,
        payload={
            "event":    OrgEvents.UPDATED,
            "org_id":   str(org_id),
            "logo_url": logo_url,
        },
    )

    return {"org_id": str(org_id), "logo_url": logo_url}
