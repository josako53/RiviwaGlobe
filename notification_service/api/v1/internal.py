# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  api/v1/internal.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/internal.py
═══════════════════════════════════════════════════════════════════════════════
Internal HTTP dispatch endpoint — an alternative to Kafka for services that
need synchronous dispatch confirmation (e.g. OTP flows where the caller must
know the notification was accepted before returning its own response).

ALL other services can call POST /internal/dispatch with the same payload
format as the Kafka notification request.

Security: requires X-Service-Key header (shared internal secret).
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status

from core.dependencies import DbDep, ServiceKeyDep
from schemas.notification import (
    NotificationDispatchRequest,
    NotificationDispatchResponse,
)
from services.delivery_service import DeliveryService

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post(
    "/dispatch",
    response_model=NotificationDispatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="[Internal] Dispatch a notification (HTTP alternative to Kafka)",
    description=(
        "Called by other Riviwa services via service-to-service HTTP when "
        "synchronous confirmation is needed (e.g. OTP flows). "
        "Requires X-Service-Key header. "
        "Idempotent — duplicate requests with the same idempotency_key return "
        "the existing notification_id without re-sending."
    ),
    dependencies=[ServiceKeyDep],
)
async def dispatch(
    body: NotificationDispatchRequest,
    db:   DbDep,
) -> NotificationDispatchResponse:
    svc = DeliveryService(db)
    notif_id = await svc.process_request(body.model_dump(mode="python"))
    return NotificationDispatchResponse(
        notification_id=notif_id,
        accepted=True,
    )


@router.post(
    "/dispatch/batch",
    status_code=status.HTTP_202_ACCEPTED,
    summary="[Internal] Dispatch multiple notifications in one request",
    description=(
        "Batch dispatch for bulk notifications (e.g. project activation "
        "notifying all org members). Each request is processed independently "
        "with its own idempotency key."
    ),
    dependencies=[ServiceKeyDep],
)
async def dispatch_batch(
    body: List[NotificationDispatchRequest],
    db:   DbDep,
) -> dict:
    svc     = DeliveryService(db)
    results = []
    for req in body:
        notif_id = await svc.process_request(req.model_dump(mode="python"))
        results.append({"notification_id": str(notif_id) if notif_id else None})
    return {"accepted": len(results), "results": results}
