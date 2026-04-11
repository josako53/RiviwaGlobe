# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  api/v1/notifications.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/notifications.py
═══════════════════════════════════════════════════════════════════════════════
Public REST endpoints for the notification inbox.

Consumed by the mobile app and web frontend to:
  · Display the notification bell / badge count
  · Show the notification feed
  · Mark individual or all notifications as read
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.dependencies import DbDep
from repositories.notification_repository import NotificationRepository
from schemas.notification import (
    NotificationInboxItem,
    NotificationInboxResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notification Inbox"])

_bearer = HTTPBearer(auto_error=True)


def _user_id_from_token(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> uuid.UUID:
    """Decode the Bearer JWT and extract the user_id (sub claim)."""
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
        )
        return uuid.UUID(payload["sub"])
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


UserIdDep = Annotated[uuid.UUID, Depends(_user_id_from_token)]


# ─────────────────────────────────────────────────────────────────────────────
# Inbox
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=NotificationInboxResponse,
    summary="Get notification inbox",
    description=(
        "Returns the user's in-app notification feed, ordered newest first. "
        "Filter to `unread_only=true` for the notification tray. "
        "The response includes `unread_count` so the client can update the "
        "badge in a single request."
    ),
)
async def get_inbox(
    user_id:     UserIdDep,
    db:          DbDep,
    unread_only: bool = Query(default=False, description="Return only unread notifications"),
    skip:        int  = Query(default=0,  ge=0),
    limit:       int  = Query(default=30, ge=1, le=100),
) -> NotificationInboxResponse:
    repo  = NotificationRepository(db)
    items = await repo.list_inbox(user_id, unread_only=unread_only, skip=skip, limit=limit)
    unread = await repo.unread_count(user_id)

    return NotificationInboxResponse(
        unread_count=unread,
        returned=len(items),
        items=[
            NotificationInboxItem.from_notification(n)
            for n in items
        ],
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count (for badge)",
    description=(
        "Lightweight endpoint for the notification bell badge. "
        "Returns only the unread count — no item list."
    ),
)
async def unread_count(user_id: UserIdDep, db: DbDep) -> UnreadCountResponse:
    repo = NotificationRepository(db)
    count = await repo.unread_count(user_id)
    return UnreadCountResponse(unread_count=count)


# ─────────────────────────────────────────────────────────────────────────────
# Mark as read
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/deliveries/{delivery_id}/read",
    status_code=status.HTTP_200_OK,
    summary="Mark a single notification as read",
    description=(
        "Call this when the user taps a notification in the feed. "
        "Sets read_at timestamp and changes status to READ. "
        "Idempotent — calling twice has no side-effects."
    ),
)
async def mark_read(
    delivery_id: uuid.UUID,
    user_id:     UserIdDep,
    db:          DbDep,
) -> dict:
    repo = NotificationRepository(db)
    delivery = await repo.mark_delivery_read(delivery_id, user_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Notification delivery not found.")
    await db.commit()
    return {"message": "Marked as read.", "delivery_id": str(delivery_id)}


@router.post(
    "/mark-all-read",
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
    description=(
        "Marks every unread in-app notification for the user as read. "
        "Call when the user opens the notification tray and views all items."
    ),
)
async def mark_all_read(user_id: UserIdDep, db: DbDep) -> dict:
    repo  = NotificationRepository(db)
    count = await repo.mark_all_read(user_id)
    await db.commit()
    return {"message": f"{count} notification(s) marked as read.", "count": count}
