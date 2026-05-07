from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from core.dependencies import DbDep, RedisDep, StaffDep
from schemas.analytics import DashboardOut
from services.analytics_service import AnalyticsService

analytics_router = APIRouter(prefix="/waiting/analytics", tags=["Analytics"])


@analytics_router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(
    org_id: uuid.UUID = Query(...),
    db:     DbDep     = ...,
    redis:  RedisDep  = ...,
    token:  StaffDep  = ...,
):
    return await AnalyticsService(db, redis).get_dashboard(org_id, token)
