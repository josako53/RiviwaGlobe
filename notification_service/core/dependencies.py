# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  core/dependencies.py
# ───────────────────────────────────────────────────────────────────────────
"""core/dependencies.py — FastAPI dependency providers."""
from __future__ import annotations

from typing import Annotated, AsyncGenerator, Optional

import httpx
import structlog
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import AsyncSessionLocal

log = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)


# ── Database session ──────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Service-to-service auth ───────────────────────────────────────────────────

def require_service_key(x_service_key: str = Header(..., alias="X-Service-Key")) -> None:
    """
    Guards internal dispatch endpoints.
    Called by riviwa_auth_service, feedback_service, stakeholder_service etc.
    to directly dispatch a notification without going through Kafka.
    """
    if x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service key.",
        )


ServiceKeyDep = Depends(require_service_key)


# ── Token claims (for notification preference endpoints) ──────────────────────

class TokenClaims:
    def __init__(self, sub: str, org_id: Optional[str] = None):
        self.sub    = sub
        self.org_id = org_id


def _get_token_claims(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> TokenClaims:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required.")
    try:
        payload = jwt.decode(creds.credentials, settings.AUTH_SECRET_KEY, algorithms=[settings.AUTH_ALGORITHM])
        return TokenClaims(sub=payload["sub"], org_id=payload.get("org_id"))
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


def get_current_token(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> TokenClaims:
    return _get_token_claims(creds)


# ── Subscription feature-gate ─────────────────────────────────────────────────

def require_feature(feature: str):
    """Subscription feature-gate. Verifies the org's active plan includes `feature`.
    Raises HTTP 402 if not on plan, 503 if subscription service unreachable.
    Usage: @router.post("/path", dependencies=[Depends(require_feature("flag"))])
    """
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
