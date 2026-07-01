"""waiting_service/api/v1/internal.py — service-to-service internal endpoints."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select

from core.config import settings
from core.dependencies import DbDep
from models.service_flow import ServiceFlow

internal_router = APIRouter(prefix="/waiting/internal", tags=["Internal"])


def _require_service_key(x_service_key: Optional[str] = Header(default=None)) -> None:
    if x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Invalid service key.")


@internal_router.get(
    "/{org_id}/default-flow",
    dependencies=[Depends(_require_service_key)],
    summary="[Internal] Default service flow for an org",
)
async def get_default_flow(org_id: uuid.UUID, db: DbDep) -> dict:
    """
    Return the default (or first active) service flow for an org.
    Used by the AI service to get a flow_id before calling POST /waiting/join.
    Returns {flow_id: null, flow_name: null} when no active flow exists.
    """
    result = await db.execute(
        select(ServiceFlow)
        .where(ServiceFlow.org_id == org_id, ServiceFlow.is_active == True)  # noqa: E712
        .order_by(ServiceFlow.is_default.desc(), ServiceFlow.name)
        .limit(1)
    )
    flow = result.scalar_one_or_none()
    if not flow:
        return {"flow_id": None, "flow_name": None}
    return {
        "flow_id": str(flow.id),
        "flow_name": flow.name,
    }
