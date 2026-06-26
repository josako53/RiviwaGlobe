# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  core/dependencies.py
# ───────────────────────────────────────────────────────────────────────────
"""core/dependencies.py — FastAPI dependency providers."""
from __future__ import annotations

import httpx
import structlog
from dataclasses import dataclass
from typing import Annotated, AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import AsyncSessionLocal

log = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TokenClaims:
    sub:    str
    org_id: Optional[str] = None


def _decode_token(raw: str) -> TokenClaims:
    try:
        payload = jwt.decode(raw, settings.AUTH_SECRET_KEY, algorithms=[settings.AUTH_ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return TokenClaims(sub=payload.get("sub", ""), org_id=payload.get("org_id"))


async def get_current_token(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> TokenClaims:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required.")
    return _decode_token(creds.credentials)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


DbDep = Annotated[AsyncSession, Depends(get_db)]


def require_service_key(
    x_service_key: str = Header(..., alias="X-Service-Key"),
) -> None:
    """
    Guards internal endpoints called service-to-service.
    Every other Riviwa service (auth, feedback, notification, etc.) uses this
    header when asking for a user's language or posting a detected language.
    """
    if x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service key.",
        )


ServiceKeyDep = Depends(require_service_key)


def require_feature(feature: str):
    """Subscription feature-gate. Verifies the org's active plan includes `feature`.
    Raises HTTP 402 if not on plan, 503 if subscription service unreachable.
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
