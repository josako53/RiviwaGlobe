from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from core.dependencies import AdminDep, DbDep, KafkaDep, OptTokenDep, RedisDep, StaffDep
from schemas.queue_ticket import JoinQueueIn, TicketStatusOut
from schemas.urgency_request import UrgencyRequestIn, UrgencyRequestOut
from services.queue_service import QueueService
from services.urgency_service import UrgencyService

queue_router = APIRouter(prefix="/waiting", tags=["Queue"])


class NoShowIn(BaseModel):
    staff_counter_id: uuid.UUID


@queue_router.post("/join", status_code=201)
async def join_queue(data: JoinQueueIn, db: DbDep, redis: RedisDep, kafka: KafkaDep, token: OptTokenDep):
    svc = QueueService(db, redis, kafka)
    ticket = await svc.join_queue(data, token)
    enriched = await svc.enrich_with_live_data(ticket)
    return enriched


@queue_router.get("/ticket/{ticket_id}/status")
async def get_ticket_status(
    ticket_id: uuid.UUID, db: DbDep, redis: RedisDep, kafka: KafkaDep, token: OptTokenDep
):
    svc = QueueService(db, redis, kafka)
    ticket = await svc.get_ticket_status(ticket_id)
    return await svc.enrich_with_live_data(ticket)


@queue_router.post("/ticket/{ticket_id}/urgency", status_code=201)
async def submit_urgency(
    ticket_id: uuid.UUID, data: UrgencyRequestIn,
    db: DbDep, redis: RedisDep, kafka: KafkaDep, token: OptTokenDep
):
    return await UrgencyService(db, redis, kafka).submit_request(ticket_id, data, token)


@queue_router.post("/ticket/{ticket_id}/cancel")
async def cancel_ticket(
    ticket_id: uuid.UUID, db: DbDep, redis: RedisDep, kafka: KafkaDep, token: StaffDep
):
    svc = QueueService(db, redis, kafka)
    ticket = await svc.cancel_ticket(ticket_id, token)
    return await svc.enrich_with_live_data(ticket)


@queue_router.post("/ticket/{ticket_id}/no-show")
async def mark_no_show(
    ticket_id: uuid.UUID, body: NoShowIn,
    db: DbDep, redis: RedisDep, kafka: KafkaDep, token: StaffDep
):
    svc = QueueService(db, redis, kafka)
    ticket = await svc.mark_no_show(ticket_id, body.staff_counter_id, token)
    return await svc.enrich_with_live_data(ticket)
