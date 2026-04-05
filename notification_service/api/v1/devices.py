# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  api/v1/devices.py
# ───────────────────────────────────────────────────────────────────────────
"""api/v1/devices.py — Push notification device (token) registration."""
from __future__ import annotations

import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, Header, HTTPException, status

from core.dependencies import DbDep
from repositories.notification_repository import NotificationRepository
from schemas.notification import DeviceRegisterRequest, DeviceResponse, DeviceTokenUpdateRequest

router = APIRouter(prefix="/devices", tags=["Push Devices"])


def _user_id(x_user_id: str = Header(..., alias="X-User-Id")) -> uuid.UUID:
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id header.")


UserIdDep = Annotated[uuid.UUID, Depends(_user_id)]


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a push notification device token",
    description=(
        "Call this on app launch (or when the platform issues a new token). "
        "Handles: new device registration, token refresh, and device transfer "
        "(same token registered under a new user). "
        "Platform: `fcm` (Android/Web) or `apns` (iOS)."
    ),
)
async def register_device(
    body:    DeviceRegisterRequest,
    user_id: UserIdDep,
    db:      DbDep,
) -> DeviceResponse:
    repo   = NotificationRepository(db)
    device = await repo.register_device(
        user_id     = user_id,
        platform    = body.platform,
        push_token  = body.push_token,
        device_name = body.device_name,
        app_version = body.app_version,
    )
    await db.commit()
    await db.refresh(device)
    return DeviceResponse.model_validate(device.__dict__)


@router.get(
    "",
    response_model=List[DeviceResponse],
    summary="List registered devices for the current user",
)
async def list_devices(user_id: UserIdDep, db: DbDep) -> List[DeviceResponse]:
    repo    = NotificationRepository(db)
    devices = await repo.get_devices(user_id)
    return [DeviceResponse.model_validate(d.__dict__) for d in devices]


@router.patch(
    "/{device_id}/token",
    response_model=DeviceResponse,
    summary="Update push token for a device",
    description=(
        "Called when FCM/APNs issues a new token for an existing device. "
        "The old token is replaced. "
    ),
)
async def update_device_token(
    device_id: uuid.UUID,
    body:      DeviceTokenUpdateRequest,
    user_id:   UserIdDep,
    db:        DbDep,
) -> DeviceResponse:
    repo   = NotificationRepository(db)
    device = await repo.update_device_token(
        device_id   = device_id,
        user_id     = user_id,
        new_token   = body.push_token,
        app_version = body.app_version,
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")
    await db.commit()
    return DeviceResponse.model_validate(device.__dict__)


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_200_OK,
    summary="Deregister a push device (logout / uninstall)",
    description="Call on logout or uninstall to stop push notifications to this device.",
)
async def deregister_device(device_id: uuid.UUID, user_id: UserIdDep, db: DbDep) -> dict:
    repo    = NotificationRepository(db)
    success = await repo.deregister_device(device_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found.")
    await db.commit()
    return {"message": "Device deregistered. Push notifications will no longer be sent to this device."}
