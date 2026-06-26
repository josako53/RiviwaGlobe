from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

import httpx
import structlog
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import ForbiddenError, UnauthorisedError
from db.session import get_async_session
from events.producer import WaitingProducer, get_producer
from waiting_redis.client import WaitingRedis, get_redis_client

log = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub:           uuid.UUID
    jti:           uuid.UUID
    exp:           int
    org_id:        Optional[uuid.UUID]
    org_role:      Optional[str]
    platform_role: Optional[str]


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async for session in get_async_session():
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_redis() -> WaitingRedis:
    return await get_redis_client()


RedisDep = Annotated[WaitingRedis, Depends(get_redis)]


async def get_kafka() -> WaitingProducer:
    return await get_producer()


KafkaDep = Annotated[WaitingProducer, Depends(get_kafka)]


def _decode_token(raw: str) -> TokenClaims:
    if not settings.AUTH_SECRET_KEY:
        raise UnauthorisedError("Auth secret key is not configured.")
    try:
        claims = jwt.decode(raw, settings.AUTH_SECRET_KEY, algorithms=[settings.AUTH_ALGORITHM])
    except ExpiredSignatureError:
        raise UnauthorisedError("Access token has expired.")
    except JWTError as exc:
        raise UnauthorisedError(f"Invalid token: {exc}")
    try:
        return TokenClaims(
            sub=uuid.UUID(claims["sub"]),
            jti=uuid.UUID(claims["jti"]),
            exp=int(claims["exp"]),
            org_id=uuid.UUID(claims["org_id"]) if claims.get("org_id") else None,
            org_role=(claims.get("org_role") or "").lower() or None,
            platform_role=claims.get("platform_role"),
        )
    except (KeyError, ValueError) as exc:
        raise UnauthorisedError(f"Malformed token payload: {exc}")


async def get_current_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> TokenClaims:
    if not credentials or not credentials.credentials:
        raise UnauthorisedError("A Bearer token is required.")
    return _decode_token(credentials.credentials)


async def get_optional_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[TokenClaims]:
    if not credentials or not credentials.credentials:
        return None
    try:
        return _decode_token(credentials.credentials)
    except UnauthorisedError:
        return None


OptTokenDep = Annotated[Optional[TokenClaims], Depends(get_optional_token)]

_STAFF_ORG_ROLES   = {"member", "manager", "admin", "owner"}
_ADMIN_ORG_ROLES   = {"manager", "admin", "owner"}
_PLATFORM_ADMIN    = {"admin", "super_admin"}


async def require_staff(token: TokenClaims = Depends(get_current_token)) -> TokenClaims:
    if token.platform_role in _PLATFORM_ADMIN:
        return token
    if token.org_role and token.org_role in _STAFF_ORG_ROLES:
        return token
    raise ForbiddenError("This endpoint requires an active organisation membership.")


StaffDep = Annotated[TokenClaims, Depends(require_staff)]


async def require_queue_admin(token: TokenClaims = Depends(get_current_token)) -> TokenClaims:
    if token.platform_role in _PLATFORM_ADMIN:
        return token
    if token.org_role and token.org_role in _ADMIN_ORG_ROLES:
        return token
    raise ForbiddenError("This action requires at least a 'manager' organisation role.")


AdminDep = Annotated[TokenClaims, Depends(require_queue_admin)]


def require_feature(feature: str):
    """Subscription feature-gate. Raises HTTP 402 if not on plan, 503 if unreachable."""
    async def _gate(token: Annotated[TokenClaims, Depends(get_current_token)]) -> None:
        if not token.org_id:
            raise HTTPException(
                status_code=403,
                detail={"error": "NO_ACTIVE_ORG",
                        "message": "Switch to an active organisation to use this feature."},
            )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/subscriptions/internal/feature-check",
                    params={"org_id": str(token.org_id), "feature": feature},
                    headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
                )
        except Exception as exc:
            log.warning("subscription.check.unavailable", feature=feature, error=str(exc))
            raise HTTPException(
                status_code=503,
                detail={"error": "SUBSCRIPTION_CHECK_FAILED",
                        "message": "Unable to verify subscription. Please try again."},
            )
        if resp.status_code != 200 or not resp.json().get("has_access"):
            raise HTTPException(
                status_code=402,
                detail={"error": "FEATURE_NOT_AVAILABLE", "feature": feature,
                        "message": f"Your current plan does not include '{feature}'. "
                                    "Upgrade your subscription to access this feature."},
            )
    return _gate
