from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from core.dependencies import AdminDep, DbDep, KafkaDep, RedisDep, StaffDep
from core.exceptions import (
    OrgNotFoundError, ServicePointNotFoundError, ServiceFlowNotFoundError,
    StaffCounterNotFoundError, SessionAlreadyOpenError, ForbiddenError,
)
from models.org_cache import OrgCache
from models.service_point import ServicePoint
from models.service_flow import ServiceFlow, FlowStep
from models.staff_counter import StaffCounter
from repositories.service_point_repository import ServicePointRepository
from repositories.service_flow_repository import ServiceFlowRepository
from repositories.staff_counter_repository import StaffCounterRepository
from repositories.urgency_request_repository import UrgencyRequestRepository
from schemas.service_flow import ServiceFlowCreate, ServiceFlowOut, ServiceFlowUpdate
from schemas.service_point import ServicePointCreate, ServicePointOut, ServicePointUpdate
from schemas.staff_counter import OpenSessionIn, SessionOut, StaffCounterCreate, StaffCounterOut, StaffCounterUpdate
from schemas.urgency_request import UrgencyReviewIn
from services.staff_session_service import StaffSessionService
from services.urgency_service import UrgencyService

admin_router = APIRouter(prefix="/waiting/admin", tags=["Admin"])


# ── Service Points ────────────────────────────────────────────────────────────

@admin_router.post("/service-points", response_model=ServicePointOut, status_code=201)
async def create_service_point(data: ServicePointCreate, db: DbDep, token: AdminDep):
    # Verify org exists
    result = await db.execute(select(OrgCache).where(OrgCache.org_id == data.org_id))
    if not result.scalar_one_or_none():
        raise OrgNotFoundError()
    if token.org_id and token.org_id != data.org_id:
        raise ForbiddenError()
    repo = ServicePointRepository(db)
    existing = await repo.get_by_org_and_code(data.org_id, data.code)
    if existing:
        raise ServicePointNotFoundError(f"Code '{data.code}' already exists in this org.")
    return await repo.create(data.model_dump())


@admin_router.get("/service-points", response_model=List[ServicePointOut])
async def list_service_points(
    org_id: uuid.UUID = Query(...), active_only: bool = Query(True), db: DbDep = ..., token: StaffDep = ...
):
    if token.org_id and token.org_id != org_id:
        raise ForbiddenError()
    return await ServicePointRepository(db).list_by_org(org_id, active_only)


@admin_router.get("/service-points/{point_id}", response_model=ServicePointOut)
async def get_service_point(point_id: uuid.UUID, db: DbDep, token: StaffDep):
    sp = await ServicePointRepository(db).get_by_id_or_404(point_id)
    if token.org_id and sp.org_id != token.org_id:
        raise ForbiddenError()
    return sp


@admin_router.patch("/service-points/{point_id}", response_model=ServicePointOut)
async def update_service_point(point_id: uuid.UUID, data: ServicePointUpdate, db: DbDep, token: AdminDep):
    repo = ServicePointRepository(db)
    sp = await repo.get_by_id_or_404(point_id)
    if token.org_id and sp.org_id != token.org_id:
        raise ForbiddenError()
    if data.is_active is False and sp.is_active:
        if await repo.has_active_tickets(point_id):
            raise ServicePointNotFoundError("Cannot deactivate: service point has active tickets.")
    return await repo.update(sp, data.model_dump(exclude_none=True))


# ── Service Flows ─────────────────────────────────────────────────────────────

@admin_router.post("/flows", response_model=ServiceFlowOut, status_code=201)
async def create_flow(data: ServiceFlowCreate, db: DbDep, token: AdminDep):
    if token.org_id and token.org_id != data.org_id:
        raise ForbiddenError()
    orders = sorted(s.step_order for s in data.steps)
    if orders != list(range(1, len(orders) + 1)):
        raise ServiceFlowNotFoundError("Step orders must be sequential starting at 1.")
    repo = ServiceFlowRepository(db)
    flow = await repo.create(
        {"org_id": data.org_id, "name": data.name, "description": data.description,
         "is_active": data.is_active, "is_default": data.is_default},
        [{"service_point_id": s.service_point_id, "step_order": s.step_order, "is_optional": s.is_optional}
         for s in data.steps],
    )
    return await repo.get_with_steps(flow.id)


@admin_router.get("/flows", response_model=List[ServiceFlowOut])
async def list_flows(
    org_id: uuid.UUID = Query(...), active_only: bool = Query(True), db: DbDep = ..., token: StaffDep = ...
):
    if token.org_id and token.org_id != org_id:
        raise ForbiddenError()
    return await ServiceFlowRepository(db).list_by_org(org_id, active_only)


@admin_router.get("/flows/{flow_id}", response_model=ServiceFlowOut)
async def get_flow(flow_id: uuid.UUID, db: DbDep, token: StaffDep):
    repo = ServiceFlowRepository(db)
    flow = await repo.get_with_steps(flow_id)
    if token.org_id and flow.org_id != token.org_id:
        raise ForbiddenError()
    return flow


@admin_router.patch("/flows/{flow_id}", response_model=ServiceFlowOut)
async def update_flow(flow_id: uuid.UUID, data: ServiceFlowUpdate, db: DbDep, token: AdminDep):
    repo = ServiceFlowRepository(db)
    flow = await repo.get_by_id_or_404(flow_id)
    if token.org_id and flow.org_id != token.org_id:
        raise ForbiddenError()
    update_data = data.model_dump(exclude_none=True, exclude={"steps"})
    flow = await repo.update(flow, update_data)
    if data.steps is not None:
        await repo.replace_steps(flow_id, [
            {"service_point_id": s.service_point_id, "step_order": s.step_order, "is_optional": s.is_optional}
            for s in data.steps
        ])
    return await repo.get_with_steps(flow_id)


# ── Counters ──────────────────────────────────────────────────────────────────

@admin_router.post("/counters", response_model=StaffCounterOut, status_code=201)
async def create_counter(data: StaffCounterCreate, db: DbDep, token: AdminDep):
    sp = await ServicePointRepository(db).get_by_id_or_404(data.service_point_id)
    if token.org_id and sp.org_id != token.org_id:
        raise ForbiddenError()
    return await StaffCounterRepository(db).create({
        "org_id": sp.org_id, "service_point_id": data.service_point_id,
        "name": data.name, "code": data.code, "user_id": data.user_id,
    })


@admin_router.get("/counters", response_model=List[StaffCounterOut])
async def list_counters(
    service_point_id: uuid.UUID = Query(...), active_only: bool = Query(True),
    db: DbDep = ..., token: StaffDep = ...
):
    return await StaffCounterRepository(db).list_by_service_point(service_point_id, active_only)


@admin_router.patch("/counters/{counter_id}", response_model=StaffCounterOut)
async def update_counter(counter_id: uuid.UUID, data: StaffCounterUpdate, db: DbDep, token: AdminDep):
    repo = StaffCounterRepository(db)
    counter = await repo.get_by_id_or_404(counter_id)
    if token.org_id and counter.org_id != token.org_id:
        raise ForbiddenError()
    return await repo.update(counter, data.model_dump(exclude_none=True))


@admin_router.post("/counters/{counter_id}/session/open", response_model=SessionOut, status_code=201)
async def open_session(counter_id: uuid.UUID, db: DbDep, kafka: KafkaDep, token: StaffDep):
    return await StaffSessionService(db, kafka).open_session(OpenSessionIn(staff_counter_id=counter_id), token)


@admin_router.post("/counters/{counter_id}/session/close", response_model=SessionOut)
async def close_session(counter_id: uuid.UUID, db: DbDep, kafka: KafkaDep, token: StaffDep):
    return await StaffSessionService(db, kafka).close_session(counter_id, token)


# ── Urgency ───────────────────────────────────────────────────────────────────

@admin_router.get("/urgency-requests")
async def list_pending(
    org_id: uuid.UUID = Query(...), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: DbDep = ..., redis: RedisDep = ..., kafka: KafkaDep = ..., token: AdminDep = ...
):
    return await UrgencyService(db, redis, kafka).list_pending(org_id, token, skip, limit)


@admin_router.post("/urgency-requests/{request_id}/review")
async def review_urgency(
    request_id: uuid.UUID, data: UrgencyReviewIn,
    db: DbDep, redis: RedisDep, kafka: KafkaDep, token: AdminDep
):
    return await UrgencyService(db, redis, kafka).review(request_id, data, token)
