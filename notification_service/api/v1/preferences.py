# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  api/v1/preferences.py
# ───────────────────────────────────────────────────────────────────────────
"""api/v1/preferences.py — User notification preference management."""
from __future__ import annotations

import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.dependencies import DbDep
from repositories.notification_repository import NotificationRepository
from schemas.notification import (
    NotificationPreferenceItem,
    NotificationPreferenceRequest,
)

router = APIRouter(prefix="/notification-preferences", tags=["Notification Preferences"])

_bearer = HTTPBearer(auto_error=True)


def _user_id(creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)]) -> uuid.UUID:
    try:
        payload = jwt.decode(creds.credentials, settings.AUTH_SECRET_KEY, algorithms=[settings.AUTH_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


UserIdDep = Annotated[uuid.UUID, Depends(_user_id)]


@router.get(
    "",
    response_model=List[NotificationPreferenceItem],
    summary="Get all notification preferences for the current user",
    description=(
        "Returns every opt-out record for the user. "
        "If a (notification_type, channel) combination is not listed, "
        "the default is ENABLED — the user will receive that notification."
    ),
)
async def get_preferences(user_id: UserIdDep, db: DbDep) -> List[NotificationPreferenceItem]:
    repo  = NotificationRepository(db)
    prefs = await repo.get_preferences(user_id)
    return [NotificationPreferenceItem.model_validate(p.__dict__) for p in prefs]


@router.put(
    "",
    status_code=status.HTTP_200_OK,
    summary="Set a notification preference",
    description=(
        "Enable or disable a specific notification type on a specific channel. "
        "Set `enabled=false` to opt out. Set `enabled=true` to re-subscribe. "
        "Use wildcard types like `grm.*` to control all GRM notifications at once."
    ),
)
async def set_preference(
    body:    NotificationPreferenceRequest,
    user_id: UserIdDep,
    db:      DbDep,
) -> dict:
    repo = NotificationRepository(db)
    await repo.upsert_preference(
        user_id=user_id,
        notification_type=body.notification_type,
        channel=body.channel,
        enabled=body.enabled,
    )
    await db.commit()
    state = "enabled" if body.enabled else "disabled"
    return {
        "message": f"Preference {state} for {body.notification_type} on {body.channel}.",
        "notification_type": body.notification_type,
        "channel": body.channel,
        "enabled": body.enabled,
    }


@router.delete(
    "/{notification_type}/{channel}",
    status_code=status.HTTP_200_OK,
    summary="Reset a preference to default (remove opt-out)",
)
async def delete_preference(
    notification_type: str,
    channel:           str,
    user_id:           UserIdDep,
    db:                DbDep,
) -> dict:
    repo    = NotificationRepository(db)
    deleted = await repo.delete_preference(user_id, notification_type, channel)
    await db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Preference not found.")
    return {"message": "Preference reset to default (enabled)."}
