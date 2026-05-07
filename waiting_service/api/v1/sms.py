from __future__ import annotations

import re
from typing import Optional

import structlog
from fastapi import APIRouter, Form, Request
from sqlalchemy import select

from core.dependencies import DbDep, KafkaDep, RedisDep
from models.org_cache import OrgCache
from models.queue_ticket import TicketPriority, TicketChannel
from schemas.queue_ticket import JoinQueueIn
from services.queue_service import QueueService

log = structlog.get_logger(__name__)
sms_router = APIRouter(prefix="/waiting/sms", tags=["SMS"])

_STATUS_RE = re.compile(r"^STATUS\s+([A-Z0-9\-]+)$", re.IGNORECASE)
_JOIN_RE   = re.compile(r"^JOIN\s+([A-Z0-9_\-]+)(?:\s+(.+))?$", re.IGNORECASE)


@sms_router.post("/inbound")
async def handle_inbound_sms(
    request: Request,
    db:      DbDep,
    redis:   RedisDep,
    kafka:   KafkaDep,
    from_:   Optional[str] = Form(None, alias="from"),
    From:    Optional[str] = Form(None),
    text:    Optional[str] = Form(None),
    Body:    Optional[str] = Form(None),
):
    phone   = from_ or From or "unknown"
    message = (text or Body or "").strip()
    log.info("waiting.sms.inbound", phone=phone, message=message[:80])

    svc = QueueService(db, redis, kafka)

    m_status = _STATUS_RE.match(message)
    if m_status:
        from repositories.queue_ticket_repository import QueueTicketRepository
        ticket_number = m_status.group(1).upper()
        ticket = await QueueTicketRepository(db).get_by_ticket_number(ticket_number)
        if not ticket:
            reply = f"Ticket {ticket_number} not found."
        else:
            enriched = await svc.enrich_with_live_data(ticket)
            pos = enriched.get("position_in_queue")
            eta = enriched.get("eta_minutes")
            status = ticket.status.replace("_", " ").title()
            if pos and eta:
                reply = f"Ticket {ticket_number}: {status}. Position: {pos}. Est. wait: {round(eta)} min."
            else:
                reply = f"Ticket {ticket_number}: {status}."
        return {"message": reply}

    m_join = _JOIN_RE.match(message)
    if m_join:
        org_slug = m_join.group(1).upper()
        result = await db.execute(
            select(OrgCache).where(OrgCache.slug.ilike(org_slug), OrgCache.is_active == True)  # noqa: E712
        )
        org_cache = result.scalar_one_or_none()
        if not org_cache:
            return {"message": f"Organisation '{org_slug}' not found. Reply HELP for assistance."}

        from repositories.service_flow_repository import ServiceFlowRepository
        flows = await ServiceFlowRepository(db).list_by_org(org_cache.org_id, active_only=True)
        default_flow = next((f for f in flows if f.is_default), flows[0] if flows else None)
        if not default_flow:
            return {"message": "No active service flow found for this organisation."}

        try:
            ticket = await svc.join_queue(
                JoinQueueIn(
                    org_id=org_cache.org_id,
                    flow_id=default_flow.id,
                    phone_number=phone,
                    channel=TicketChannel.SMS,
                ),
                token=None,
            )
            enriched = await svc.enrich_with_live_data(ticket)
            pos = enriched.get("position_in_queue", "?")
            eta = enriched.get("eta_minutes")
            eta_str = f"Est. wait: {round(eta)} min." if eta else ""
            reply = (
                f"Joined! Ticket: {ticket.ticket_number}. Position: {pos}. {eta_str}"
                f" Reply STATUS {ticket.ticket_number} to check."
            )
        except Exception as exc:
            log.error("waiting.sms.join_failed", error=str(exc))
            reply = "Sorry, could not join the queue. Please visit the counter."
        return {"message": reply}

    reply = (
        "Riviwa Queue:\n"
        "  JOIN <ORG_CODE>  — join the queue\n"
        "  STATUS <TICKET>  — check your position\n"
        "Example: JOIN KNH"
    )
    return {"message": reply}
