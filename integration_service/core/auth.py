"""
core/auth.py — Request authentication for integration_service.

Three auth methods accepted:
  1. API Key       — rwi_live_xxx  in X-API-Key header
  2. Bearer token  — JWT access token in Authorization: Bearer header
  3. Client creds  — client_id + client_secret in request body (OAuth2 token endpoint only)

IP allowlist and rate limiting checks are applied after auth succeeds.
"""
from __future__ import annotations

import hashlib
import time
from typing import Optional
import uuid

import jwt
import redis.asyncio as aioredis
import structlog
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import verify_api_key
from db.session import get_async_session
from models.integration import ApiKey, IntegrationClient, OAuthToken

log = structlog.get_logger(__name__)


class AuthContext:
    """Result of a successful auth check."""
    def __init__(
        self,
        client: IntegrationClient,
        scopes: list[str],
        user_id: Optional[uuid.UUID] = None,
        auth_method: str = "api_key",
    ):
        self.client      = client
        self.scopes      = scopes
        self.user_id     = user_id
        self.auth_method = auth_method
        # Derived from client — every request is org-scoped
        self.org_id: Optional[uuid.UUID] = client.organisation_id

    def require_scope(self, scope: str) -> None:
        if scope not in self.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "INSUFFICIENT_SCOPE", "required": scope},
            )

    def require_org(self) -> uuid.UUID:
        """Raise 403 if the client has no organisation_id bound."""
        if not self.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "CLIENT_NOT_ORG_BOUND",
                    "message": "This client is not bound to an organisation. "
                               "Set organisation_id when registering the client.",
                },
            )
        return self.org_id

    def validate_org(self, requested_org_id: Optional[uuid.UUID]) -> uuid.UUID:
        """
        Ensure requested_org_id (if provided) matches the client's bound org.
        Falls back to the client's org if None. Raises 403 on mismatch.
        """
        bound = self.require_org()
        if requested_org_id and requested_org_id != bound:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ORG_MISMATCH",
                    "message": "Requested org_id does not match the client's bound organisation.",
                },
            )
        return bound


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def _check_rate_limit(redis: aioredis.Redis, client: IntegrationClient) -> None:
    """Sliding window rate limit check. Raises 429 if exceeded."""
    now     = int(time.time())
    min_key = f"rl:min:{client.id}:{now // 60}"
    day_key = f"rl:day:{client.id}:{now // 86400}"

    pipe = redis.pipeline()
    pipe.incr(min_key)
    pipe.expire(min_key, 120)
    pipe.incr(day_key)
    pipe.expire(day_key, 172800)
    results = await pipe.execute()

    if results[0] > client.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "RATE_LIMIT_EXCEEDED", "window": "minute"},
        )
    if results[2] > client.rate_limit_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "RATE_LIMIT_EXCEEDED", "window": "day"},
        )


def _check_ip_allowlist(client: IntegrationClient, request: Request) -> None:
    if not client.allowed_ips:
        return
    client_ip = request.client.host if request.client else ""
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    ip = forwarded or client_ip
    if ip not in client.allowed_ips:
        log.warning("integration.ip_blocked", client_id=str(client.id), ip=ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "IP_NOT_ALLOWED"},
        )


async def _auth_by_api_key(
    api_key_header: str,
    db: AsyncSession,
) -> AuthContext:
    key_hash = hashlib.sha256(api_key_header.encode()).hexdigest()
    result = await db.execute(
        select(ApiKey)
        .join(IntegrationClient, ApiKey.client_id == IntegrationClient.id)
        .where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True,
            ApiKey.revoked_at.is_(None),
            IntegrationClient.is_active == True,
        )
    )
    row = result.scalars().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"error": "INVALID_API_KEY"})
    if row.expires_at and row.expires_at.timestamp() < time.time():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"error": "API_KEY_EXPIRED"})

    client = await db.get(IntegrationClient, row.client_id)
    return AuthContext(client=client, scopes=row.scopes, auth_method="api_key")


async def _auth_by_bearer(
    token: str,
    db: AsyncSession,
) -> AuthContext:
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"error": "TOKEN_EXPIRED"})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"error": "INVALID_TOKEN"})

    jti = payload.get("jti")
    result = await db.execute(
        select(OAuthToken)
        .join(IntegrationClient, OAuthToken.client_id == IntegrationClient.id)
        .where(
            OAuthToken.jti == jti,
            OAuthToken.revoked_at.is_(None),
            IntegrationClient.is_active == True,
        )
    )
    token_row = result.scalars().first()
    if not token_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"error": "TOKEN_REVOKED_OR_UNKNOWN"})

    client  = await db.get(IntegrationClient, token_row.client_id)
    user_id = uuid.UUID(payload["user_id"]) if payload.get("user_id") else None
    return AuthContext(client=client, scopes=token_row.scopes,
                       user_id=user_id, auth_method="bearer")


async def require_integration_auth(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_async_session),
) -> AuthContext:
    """
    FastAPI dependency — authenticates any integration request.
    Checks API key or Bearer token, then IP allowlist + rate limit.
    """
    ctx: Optional[AuthContext] = None

    if x_api_key:
        ctx = await _auth_by_api_key(x_api_key, db)
    elif authorization and authorization.lower().startswith("bearer "):
        ctx = await _auth_by_bearer(authorization[7:], db)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "MISSING_CREDENTIALS",
                    "message": "Provide X-API-Key header or Authorization: Bearer <token>"},
        )

    _check_ip_allowlist(ctx.client, request)

    try:
        redis = await _get_redis()
        await _check_rate_limit(redis, ctx.client)
    except HTTPException:
        raise
    except Exception as exc:
        log.warning("integration.rate_limit_check_failed", error=str(exc))

    return ctx


# Shorthand dependency
IntegrationAuthDep = Depends(require_integration_auth)
