from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from core.dependencies import DbDep, KafkaDep, RedisDep, StaffDep
from core.exceptions import NoTicketsWaitingError
from services.queue_service import QueueService

staff_router = APIRouter(prefix="/waiting/staff", tags=["Staff"])


class CallNextIn(BaseModel):
    service_point_id: uuid.UUID
    staff_counter_id: Optional[uuid.UUID] = None  # auto-resolved from session if omitted


class FinishIn(BaseModel):
    staff_counter_id: Optional[uuid.UUID] = None  # auto-resolved from ticket if omitted
    notes:            Optional[str] = None


class SetPriorityIn(BaseModel):
    priority: str
    reason:   Optional[str] = None


@staff_router.post("/call-next")
async def call_next(body: CallNextIn, db: DbDep, redis: RedisDep, kafka: KafkaDep, token: StaffDep):
    svc = QueueService(db, redis, kafka)
    try:
        ticket, stage = await svc.call_next(body.service_point_id, body.staff_counter_id, token)
        enriched = await svc.enrich_with_live_data(ticket)
        return {"ticket": enriched, "stage": stage, "message": f"Now serving {ticket.ticket_number}"}
    except NoTicketsWaitingError:
        return {"ticket": None, "stage": None, "message": "No tickets waiting."}


@staff_router.post("/ticket/{ticket_id}/finish")
async def finish_attending(
    ticket_id: uuid.UUID, body: FinishIn, db: DbDep, redis: RedisDep, kafka: KafkaDep, token: StaffDep
):
    svc = QueueService(db, redis, kafka)
    result = await svc.finish(ticket_id, body.staff_counter_id, body.notes, token)
    enriched = await svc.enrich_with_live_data(result.ticket)
    return {
        "is_final": result.is_final,
        "ticket": enriched,
        "next_point": result.next_point,
        "message": "Completed." if result.is_final else f"Advanced to: {getattr(result.next_point, 'name', 'next stage')}",
    }


@staff_router.post("/ticket/{ticket_id}/priority")
async def set_priority(
    ticket_id: uuid.UUID, body: SetPriorityIn, db: DbDep, redis: RedisDep, kafka: KafkaDep, token: StaffDep
):
    svc = QueueService(db, redis, kafka)
    ticket = await svc.set_priority(ticket_id, body.priority, body.reason, token)
    return await svc.enrich_with_live_data(ticket)


@staff_router.get("/queue/{service_point_id}")
async def view_queue(
    service_point_id: uuid.UUID, db: DbDep, redis: RedisDep, kafka: KafkaDep, token: StaffDep
):
    from repositories.queue_ticket_repository import QueueTicketRepository
    from repositories.service_point_repository import ServicePointRepository
    from models.queue_ticket import TicketStatus

    svc  = QueueService(db, redis, kafka)
    repo = QueueTicketRepository(db)
    sp   = await ServicePointRepository(db).get_by_id_or_404(service_point_id)
    waiting   = await repo.get_tickets_in_queue(service_point_id)
    attending = (await repo.list_by_org(sp.org_id, TicketStatus.ATTENDING, service_point_id, 0, 100))[0]

    return {
        "service_point": sp,
        "waiting": [await svc.enrich_with_live_data(t) for t in waiting],
        "attending": [await svc.enrich_with_live_data(t) for t in attending],
    }
