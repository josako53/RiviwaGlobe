"""
core/dependencies.py
═══════════════════════════════════════════════════════════════════════════════
All FastAPI dependency injection providers.

Authentication, authorisation, and resource resolution all live here so that
endpoint functions stay thin and fully testable via dependency overrides.

Dependency graph
────────────────
  get_db                   → AsyncSession          (one per request, auto-closed)
  get_redis                → Redis                 (shared pool singleton)
  get_kafka                → KafkaEventProducer    (shared singleton)
  get_current_token        → TokenClaims           (decoded + deny-list checked)
  get_current_user         → User                  (loaded from DB, any status)
                                                    ★ FIX: uses get_by_id_with_roles
                                                      so platform_roles + role are
                                                      eager-loaded — no MissingGreenlet
  require_active_user      → User                  (ACTIVE + not locked)
  require_verified_user    → User                  (active + email verified)
  get_optional_user        → User | None           (public endpoints)
  get_org_context          → OrganisationMember    (validates org dashboard)
  require_org_role(r)      → OrganisationMember    (minimum role guard factory)
  require_platform_role(r) → User                  (platform staff guard factory)
  get_client_ip            → str
  get_user_agent           → str | None

MissingGreenlet fix — single-line change in get_current_user
─────────────────────────────────────────────────────────────
  BEFORE:  user = await repo.get_by_id(token.sub)
  AFTER:   user = await repo.get_by_id_with_roles(token.sub)

  get_by_id_with_roles uses selectinload on BOTH relationship hops:
      User.platform_roles  →  list[UserRole]    (hop 1)
      UserRole.role        →  Role              (hop 2)

  Without hop 2, any call to user.get_platform_role_names() (e.g. inside
  AuthService._get_platform_role called from switch_org) accesses `ur.role`
  which triggers a synchronous lazy-load inside an async context:
      MissingGreenlet: greenlet_spawn has not been called …

  selectinload fires a second async SELECT … WHERE id IN (…) — no lazy IO.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    AccessTokenRevokedError,
    AccountBannedError,
    AccountDeactivatedError,
    AccountLockedError,
    AccountSuspendedError,
    EmailNotVerifiedError,
    ForbiddenError,
    InsufficientOrgRoleError,
    InsufficientPlatformRoleError,
    OrgMembershipRequiredError,
    OrgNotActiveError,
    OrgNotFoundError,
    UnauthorisedError,
    UserNotFoundError,
)
from core.logging import bind_user_to_context
from core.security import decode_access_token
from db.session import get_async_session, get_redis_client
from models.organisation import OrgMemberRole, OrgStatus
from models.user import AccountStatus, User
from repositories.organisation_repository import OrganisationRepository
from repositories.user_repository import UserRepository
from workers.kafka_producer import KafkaEventProducer
from workers.kafka_producer import get_kafka_producer as _kafka_singleton

log = structlog.get_logger(__name__)

# Bearer extractor — auto_error=False so we can return None for optional auth
_bearer = HTTPBearer(auto_error=False)


# ─────────────────────────────────────────────────────────────────────────────
# Token claims dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class TokenClaims:
    """
    Typed, immutable representation of a verified JWT payload.
    Returned by get_current_token and threaded through the dependency chain.
    """
    sub:           uuid.UUID
    jti:           uuid.UUID
    iat:           int           # issued-at (present in every JWT we issue)
    exp:           int
    org_id:        Optional[uuid.UUID]
    org_role:      Optional[str]
    platform_role: Optional[str]


# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure dependencies
# ─────────────────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:                 # type: ignore[misc]
    """
    Yield a SQLAlchemy AsyncSession for the current request.

    Commits on clean exit, rolls back on any exception.
    Session is always closed at request teardown regardless of outcome.
    Session factory is defined in db.session using settings.ASYNC_DATABASE_URL.
    """
    async for session in get_async_session():
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_redis() -> Redis:
    """
    Return the shared async Redis client (connection pool singleton).

    The pool is initialised at application startup (lifespan event).
    Do NOT close this client inside a request handler.
    """
    return await get_redis_client()


async def get_kafka() -> KafkaEventProducer:
    """Return the shared Kafka producer singleton (started in lifespan)."""
    return await _kafka_singleton()


# ─────────────────────────────────────────────────────────────────────────────
# Token extraction → decoding → deny-list check
# ─────────────────────────────────────────────────────────────────────────────

async def get_current_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    redis: Redis = Depends(get_redis),
) -> TokenClaims:
    """
    Extract, decode, and fully validate the Bearer access token.

    Steps
    ─────
    1. Extract Authorization: Bearer <token> header.
    2. Decode + verify JWT signature and expiry.
    3. Check JTI against the Redis deny-list (set on logout/rotation).
    4. Return typed TokenClaims.

    Raises
    ──────
        UnauthorisedError          no / malformed / missing token
        AccessTokenExpiredError    exp claim is in the past
        AccessTokenRevokedError    JTI found on deny-list
    """
    if not credentials or not credentials.credentials:
        raise UnauthorisedError("A Bearer token is required.")

    # Decodes + verifies signature and expiry; raises on failure
    claims = decode_access_token(credentials.credentials)

    token = TokenClaims(
        sub=uuid.UUID(claims["sub"]),
        jti=uuid.UUID(claims["jti"]),
        iat=int(claims["iat"]),
        exp=int(claims["exp"]),
        org_id=uuid.UUID(claims["org_id"]) if claims.get("org_id") else None,
        org_role=claims.get("org_role"),
        platform_role=claims.get("platform_role"),
    )

    # Deny-list check — O(1) Redis GET.
    # Key set on logout: "jti_deny:<jti>"  TTL = remaining token seconds.
    deny_key = f"jti_deny:{token.jti}"
    if await redis.exists(deny_key):
        log.warning("auth.jti_revoked", jti=str(token.jti))
        raise AccessTokenRevokedError()

    return token


# ─────────────────────────────────────────────────────────────────────────────
# User resolution
# ─────────────────────────────────────────────────────────────────────────────

async def get_current_user(
    token: TokenClaims  = Depends(get_current_token),
    db:    AsyncSession = Depends(get_db),
) -> User:
    """
    Load the User row for the authenticated token subject.

    ★ MissingGreenlet fix: uses get_by_id_with_roles instead of get_by_id.

    get_by_id_with_roles eager-loads two relationship hops via selectinload:
        User.platform_roles  →  list[UserRole]   (junction rows)
        UserRole.role        →  Role             (the actual Role object)

    This prevents MissingGreenlet when any code downstream calls
    user.get_platform_role_names() — which iterates `ur.role` on each
    UserRole junction row.  Without this eager load, SQLAlchemy attempts a
    synchronous lazy-load inside the async event loop and raises:
        MissingGreenlet: greenlet_spawn has not been called …

    Returns the User regardless of account status.
    Use require_active_user or require_verified_user for status-gated routes.

    Raises UserNotFoundError if the user no longer exists in the database.
    Binds user_id (and org_id when present) into the structlog context so
    every subsequent log call in this request carries identity fields.
    """
    repo = UserRepository(db)
    # ★ THE FIX — was: repo.get_by_id(token.sub)
    user = await repo.get_by_id_with_roles(token.sub)
    if not user:
        log.warning("auth.user_not_found", user_id=str(token.sub))
        raise UserNotFoundError()

    # Enrich per-request log context with resolved identity
    bind_user_to_context(
        user_id=str(user.id),
        org_id=str(token.org_id) if token.org_id else None,
    )
    return user


async def require_active_user(user: User = Depends(get_current_user)) -> User:
    """
    Assert the authenticated user's account is ACTIVE and not temporarily locked.

    Status → Exception mapping
    ──────────────────────────
        SUSPENDED   → AccountSuspendedError
        BANNED      → AccountBannedError
        DEACTIVATED → AccountDeactivatedError
        ACTIVE + is_locked() → AccountLockedError
        Any other non-ACTIVE status → ForbiddenError
    """
    if user.status == AccountStatus.ACTIVE:
        if user.is_locked():
            raise AccountLockedError()
        return user

    _status_exc_map = {
        AccountStatus.SUSPENDED:   AccountSuspendedError,
        AccountStatus.BANNED:      AccountBannedError,
        AccountStatus.DEACTIVATED: AccountDeactivatedError,
    }
    exc_class = _status_exc_map.get(user.status, ForbiddenError)
    raise exc_class()


async def require_active_user_or_channel(
    user: User = Depends(get_current_user),
) -> User:
    """
    Like require_active_user but also allows CHANNEL_REGISTERED accounts.

    Used exclusively for POST /auth/channel/set-password — the endpoint
    that upgrades a channel-registered PAP to a full ACTIVE account.
    A CHANNEL_REGISTERED user has:
      · phone_verified = True  (proven by initiating the conversation)
      · hashed_password = None (not yet set)
      · valid JWT issued at channel registration or after OTP login

    After successfully setting a password, their status becomes ACTIVE
    and this dependency is no longer needed for subsequent requests.
    """
    if user.status in (AccountStatus.ACTIVE, AccountStatus.CHANNEL_REGISTERED):
        if user.status == AccountStatus.ACTIVE and user.is_locked():
            raise AccountLockedError()
        return user

    _status_exc_map = {
        AccountStatus.SUSPENDED:   AccountSuspendedError,
        AccountStatus.BANNED:      AccountBannedError,
        AccountStatus.DEACTIVATED: AccountDeactivatedError,
    }
    exc_class = _status_exc_map.get(user.status, ForbiddenError)
    raise exc_class()


async def require_verified_user(
    user: User = Depends(require_active_user),
) -> User:
    """
    Assert the user is ACTIVE and has a verified email address.

    Required for actions such as:
        · Creating an organisation
        · Sending org invites
        · Accessing billing features
    """
    if not user.is_email_verified:
        raise EmailNotVerifiedError()
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db:    AsyncSession = Depends(get_db),
    redis: Redis        = Depends(get_redis),
) -> Optional[User]:
    """
    Return the authenticated User if a valid Bearer token is present, else None.

    Used on public endpoints that personalise responses for logged-in users
    without requiring authentication (e.g. public org profile pages).
    Never raises an authentication error.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        token = await get_current_token(credentials, redis)
        return await get_current_user(token, db)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Org dashboard context
# ─────────────────────────────────────────────────────────────────────────────

async def get_org_context(
    user:  User         = Depends(require_active_user),
    token: TokenClaims  = Depends(get_current_token),
    db:    AsyncSession = Depends(get_db),
):
    """
    Resolve and validate the user's current org dashboard context.

    Validates in order:
        1. token.org_id is not None  (user has switched to an org dashboard)
        2. The Organisation exists
        3. The Organisation status is ACTIVE
        4. The user has an ACTIVE OrganisationMember row for this org

    Returns the OrganisationMember row (carries org_role, joined_at, etc.).

    Raises
    ──────
        OrgMembershipRequiredError   no org_id in token (personal view)
        OrgNotFoundError             organisation does not exist
        OrgNotActiveError            organisation is not in ACTIVE status
        OrgMembershipRequiredError   user has no active membership in this org
    """
    if token.org_id is None:
        raise OrgMembershipRequiredError(
            "This endpoint requires an active org dashboard. "
            "Switch via POST /api/v1/auth/switch-org first."
        )

    org_repo = OrganisationRepository(db)
    org = await org_repo.get_by_id(token.org_id)
    if not org:
        raise OrgNotFoundError()
    if org.status != OrgStatus.ACTIVE:
        raise OrgNotActiveError()

    membership = await org_repo.get_active_member(token.org_id, user.id)
    if not membership:
        log.warning(
            "auth.no_active_membership",
            user_id=str(user.id),
            org_id=str(token.org_id),
        )
        raise OrgMembershipRequiredError()

    return membership


# ─────────────────────────────────────────────────────────────────────────────
# Role guard factories
# ─────────────────────────────────────────────────────────────────────────────

# Org member role strength (weakest → strongest)
_ORG_ROLE_STRENGTH: dict[OrgMemberRole, int] = {
    OrgMemberRole.MEMBER:  1,
    OrgMemberRole.MANAGER: 2,
    OrgMemberRole.ADMIN:   3,
    OrgMemberRole.OWNER:   4,
}

# Platform staff role strength (weakest → strongest)
_PLATFORM_ROLE_STRENGTH: dict[str, int] = {
    "moderator":   1,
    "admin":       2,
    "super_admin": 3,
}


def require_org_role(minimum_role: OrgMemberRole):
    """
    Dependency factory — assert the calling user holds at least *minimum_role*
    in the currently active org dashboard.

    Role hierarchy (weakest → strongest):
        MEMBER < MANAGER < ADMIN < OWNER

    Usage
    ─────
        @router.delete("/members/{uid}")
        async def kick(
            member = Depends(require_org_role(OrgMemberRole.ADMIN)),
        ):
            ...
    """
    async def _guard(membership=Depends(get_org_context)):
        user_strength = _ORG_ROLE_STRENGTH.get(membership.org_role, 0)
        need_strength = _ORG_ROLE_STRENGTH[minimum_role]
        if user_strength < need_strength:
            raise InsufficientOrgRoleError(
                f"This action requires at least the '{minimum_role.value}' role "
                f"in this organisation."
            )
        return membership

    return _guard


def require_platform_role(minimum_role: str):
    """
    Dependency factory — assert the calling user holds at least *minimum_role*
    as a platform staff role.

    Platform roles are always-on (not context-switched like org roles).
    The JWT platform_role claim carries the highest granted role name.
    Checking the JWT claim (not DB) is intentional — it avoids a DB round-trip
    and is safe because the token is re-issued on every role change.

    Role hierarchy (weakest → strongest):
        moderator < admin < super_admin

    Usage
    ─────
        @router.get("/admin/users")
        async def list_users(
            _ = Depends(require_platform_role("admin")),
        ):
            ...
    """
    async def _guard(
        user:  User        = Depends(require_active_user),
        token: TokenClaims = Depends(get_current_token),
    ) -> User:
        user_strength = _PLATFORM_ROLE_STRENGTH.get(token.platform_role or "", 0)
        need_strength = _PLATFORM_ROLE_STRENGTH.get(minimum_role, 0)
        if user_strength < need_strength:
            raise InsufficientPlatformRoleError(
                f"This action requires platform role '{minimum_role}' or higher."
            )
        return user

    return _guard


# ─────────────────────────────────────────────────────────────────────────────
# Request metadata
# ─────────────────────────────────────────────────────────────────────────────

def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP address.

    When settings.TRUST_PROXY is True, reads the leftmost value from the
    X-Forwarded-For header (set by nginx / AWS ALB / Cloudflare).
    Falls back to the direct connection peer address.
    Always returns a non-None string.
    """
    if settings.TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return (request.client.host if request.client else None) or "0.0.0.0"


def get_user_agent(request: Request) -> Optional[str]:
    """Return the User-Agent header value, or None if absent."""
    return request.headers.get("User-Agent")