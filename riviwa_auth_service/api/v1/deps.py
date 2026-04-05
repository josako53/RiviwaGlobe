"""
app/api/deps.py
═══════════════════════════════════════════════════════════════════════════════
FastAPI dependency providers for service-layer objects.

Changes from original
──────────────────────
  · get_user_service() now injects redis (required for password reset OTP flow)
  · get_oauth_service() added (new — wires OAuthService for social auth)
  · OAuthServiceDep added to Annotated alias set
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db, get_kafka, get_redis
from events.publisher import EventPublisher
from services.auth_service import AuthService
from services.id_verification_service import IDVerificationService
from services.oauth_service import OAuthService
from services.org_extended_service import OrgExtendedService
from services.organisation_service import OrganisationService
from services.registration_service import RegistrationService
from services.user_service import UserService
from workers.kafka_producer import KafkaEventProducer


# ─────────────────────────────────────────────────────────────────────────────
# EventPublisher
# ─────────────────────────────────────────────────────────────────────────────

async def get_publisher(
    producer: Annotated[KafkaEventProducer, Depends(get_kafka)],
) -> EventPublisher:
    """
    Construct an EventPublisher wrapping the shared Kafka singleton.
    Stateless wrapper — constructing one per request is intentional so
    tests can override get_publisher directly:

        app.dependency_overrides[get_publisher] = lambda: MockPublisher()
    """
    return EventPublisher(producer)


# ─────────────────────────────────────────────────────────────────────────────
# Service factories
# ─────────────────────────────────────────────────────────────────────────────

async def get_auth_service(
    db:        Annotated[AsyncSession,   Depends(get_db)],
    redis:     Annotated[Redis,          Depends(get_redis)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> AuthService:
    """
    AuthService — login (2-step OTP), logout, token refresh, org switch.
    Requires: DB session, Redis (OTP sessions, refresh tokens, JTI deny-list),
              EventPublisher.
    """
    return AuthService(db=db, redis=redis, publisher=publisher)


async def get_user_service(
    db:        Annotated[AsyncSession,   Depends(get_db)],
    redis:     Annotated[Redis,          Depends(get_redis)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> UserService:
    """
    UserService — email/phone verification, password management (including
    forgot-password OTP flow), profile updates, account status changes,
    OAuth linking.

    Redis is now injected to support the forgot-password OTP session
    (pwd_reset:<token> → JSON stored in Redis, TTL 10 min).
    """
    return UserService(db=db, publisher=publisher, redis=redis)


async def get_org_service(
    db:        Annotated[AsyncSession,   Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrganisationService:
    """
    OrganisationService — create/verify/update orgs, member management,
    invite lifecycle, ownership transfers, dashboard switching.
    """
    return OrganisationService(db=db, publisher=publisher)


async def get_org_extended_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrgExtendedService:
    """
    OrgExtendedService — locations, content, FAQs, branches, branch managers,
    services, service personnel, service locations, media, FAQs, policies.

    Does not need Redis or EventPublisher — extended org ops are
    content-management in nature with no async side-effects in this version.
    Add EventPublisher here when downstream consumers need to react to
    service status changes (e.g. search index rebuild).
    """
    return OrgExtendedService(db=db)


async def get_registration_service(
    db:        Annotated[AsyncSession,   Depends(get_db)],
    redis:     Annotated[Redis,          Depends(get_redis)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> RegistrationService:
    """
    RegistrationService — 3-step consumer registration pipeline.
    Uses Redis for multi-step session state (reg_otp:<token>, reg_cont:<token>).
    Publishes registration events via EventPublisher.
    """
    return RegistrationService(db=db, redis=redis, publisher=publisher)


async def get_id_verification_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IDVerificationService:
    """
    IDVerificationService — government ID verification lifecycle.
    Kafka singleton is fetched lazily inside process_webhook().
    """
    return IDVerificationService(db=db)


async def get_oauth_service(
    db:        Annotated[AsyncSession,   Depends(get_db)],
    redis:     Annotated[Redis,          Depends(get_redis)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OAuthService:
    """
    OAuthService — social login / registration via Google, Apple, Facebook.
    Requires: DB session (user upsert), Redis (refresh tokens),
              EventPublisher (user.registered_social, auth.login_success).
    """
    return OAuthService(db=db, redis=redis, publisher=publisher)


# ─────────────────────────────────────────────────────────────────────────────
# Annotated shorthand aliases
# ─────────────────────────────────────────────────────────────────────────────

AuthServiceDep         = Annotated[AuthService,           Depends(get_auth_service)]
UserServiceDep         = Annotated[UserService,           Depends(get_user_service)]
OrgServiceDep          = Annotated[OrganisationService,   Depends(get_org_service)]
OrgExtendedServiceDep  = Annotated[OrgExtendedService,    Depends(get_org_extended_service)]
RegistrationServiceDep = Annotated[RegistrationService,   Depends(get_registration_service)]
IDVerifyServiceDep     = Annotated[IDVerificationService, Depends(get_id_verification_service)]
OAuthServiceDep        = Annotated[OAuthService,          Depends(get_oauth_service)]
PublisherDep           = Annotated[EventPublisher,        Depends(get_publisher)]
