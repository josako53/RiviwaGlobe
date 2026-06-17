"""api/v1/reports.py — Fake report management for admins and field agents."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import JWTDep
from db.session import get_async_session
from models.verification import AgentAssignment, FakeSuspectReport, FieldAgent

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/verify/reports", tags=["Verification — Reports"])


def _report_out(r: FakeSuspectReport) -> dict:
    out = {
        "id": str(r.id), "verification_event_id": str(r.verification_event_id),
        "short_code_scanned": r.short_code_scanned, "status": r.status,
        "reporter_phone": r.reporter_phone, "reporter_name": r.reporter_name,
        "description": r.description, "photo_url": r.photo_url,
        "gps_lat": float(r.gps_lat) if r.gps_lat else None,
        "gps_lng": float(r.gps_lng) if r.gps_lng else None,
        "location_description": r.location_description,
        "organisation_id": str(r.organisation_id) if r.organisation_id else None,
        "assigned_agent_id": str(r.assigned_agent_id) if r.assigned_agent_id else None,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
        "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        "resolution_notes": r.resolution_notes,
    }
    if r.ai_analysis:
        verdict = r.ai_analysis.get("ai_verdict", {})
        out["ai_analysis"] = {
            "verdict":            verdict.get("verdict"),
            "confidence":         verdict.get("confidence"),
            "suspected_brand":    verdict.get("suspected_brand"),
            "suspected_product":  verdict.get("suspected_product"),
            "clip_similarity":    r.ai_analysis.get("clip_similarity"),
            "counterfeit_indicators": verdict.get("counterfeit_indicators", []),
            "reasoning":          verdict.get("reasoning"),
            "recommended_action": verdict.get("recommended_action"),
        }
    return out


@router.get("", status_code=200)
async def list_reports(
    organisation_id: Optional[uuid.UUID] = Query(default=None),
    report_status: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
    _claims = JWTDep,
) -> dict:
    caller_org_id = uuid.UUID(_claims["org_id"]) if _claims.get("org_id") else None
    if caller_org_id is None:
        raise HTTPException(status_code=403, detail={"error": "NO_ORG_CONTEXT"})
    # Always scope to the caller's org; ignore any requested organisation_id
    effective_org_id = caller_org_id
    q = select(FakeSuspectReport).where(FakeSuspectReport.organisation_id == effective_org_id)
    if report_status:
        q = q.where(FakeSuspectReport.status == report_status.upper())
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.order_by(FakeSuspectReport.created_at.desc()).offset((page-1)*size).limit(size))).scalars().all()
    return {"total": total, "page": page, "size": size, "items": [_report_out(r) for r in items]}


@router.get("/{report_id}", status_code=200)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _claims = JWTDep,
) -> dict:
    caller_org_id = uuid.UUID(_claims["org_id"]) if _claims.get("org_id") else None
    if caller_org_id is None:
        raise HTTPException(status_code=403, detail={"error": "NO_ORG_CONTEXT"})
    r = await db.get(FakeSuspectReport, report_id)
    if not r:
        raise HTTPException(status_code=404, detail={"error": "REPORT_NOT_FOUND"})
    if r.organisation_id != caller_org_id:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN"})
    assignments = (await db.execute(
        select(AgentAssignment).where(AgentAssignment.fake_report_id == report_id).order_by(AgentAssignment.assigned_at.desc())
    )).scalars().all()
    out = _report_out(r)
    out["assignment_history"] = [
        {"agent_id": str(a.agent_id), "assigned_at": a.assigned_at.isoformat(),
         "completed_at": a.completed_at.isoformat() if a.completed_at else None, "notes": a.notes}
        for a in assignments
    ]
    return out


@router.patch("/{report_id}", status_code=200)
async def update_report(
    report_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    _claims = JWTDep,
) -> dict:
    caller_org_id = uuid.UUID(_claims["org_id"]) if _claims.get("org_id") else None
    if caller_org_id is None:
        raise HTTPException(status_code=403, detail={"error": "NO_ORG_CONTEXT"})
    r = await db.get(FakeSuspectReport, report_id)
    if not r:
        raise HTTPException(status_code=404, detail={"error": "REPORT_NOT_FOUND"})
    if r.organisation_id != caller_org_id:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN"})
    if "status" in body:
        r.status = body["status"].upper()
        if r.status in ("RESOLVED", "CONFIRMED_FAKE", "DISMISSED"):
            r.resolved_at = datetime.utcnow()
    if "resolution_notes" in body:
        r.resolution_notes = body["resolution_notes"]
    r.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(r)
    return _report_out(r)


@router.post("/{report_id}/assign", status_code=200)
async def assign_agent(
    report_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    claims = JWTDep,
) -> dict:
    """Assign a field agent to investigate a fake report."""
    caller_org_id = uuid.UUID(claims["org_id"]) if claims.get("org_id") else None
    if caller_org_id is None:
        raise HTTPException(status_code=403, detail={"error": "NO_ORG_CONTEXT"})
    r = await db.get(FakeSuspectReport, report_id)
    if not r:
        raise HTTPException(status_code=404, detail={"error": "REPORT_NOT_FOUND"})
    if r.organisation_id != caller_org_id:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN"})
    agent_id = uuid.UUID(body["agent_id"])
    agent = await db.get(FieldAgent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail={"error": "AGENT_NOT_FOUND"})
    if agent.organisation_id != caller_org_id:
        raise HTTPException(status_code=403, detail={"error": "AGENT_ORG_MISMATCH"})

    r.assigned_agent_id = agent_id
    r.status = "UNDER_INVESTIGATION"
    r.updated_at = datetime.utcnow()
    agent.assignment_count += 1

    assignment = AgentAssignment(
        fake_report_id=report_id, agent_id=agent_id,
        assigned_by=uuid.UUID(claims["sub"]) if claims.get("sub") else uuid.uuid4(),
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    log.info("fake_report.assigned", report_id=str(report_id), agent_id=str(agent_id))
    return {
        "assignment_id": str(assignment.id), "agent_id": str(agent_id),
        "agent_name": agent.name, "assigned_at": assignment.assigned_at.isoformat(),
        "report_status": r.status,
    }


@router.get("/agents/list", status_code=200)
async def list_agents(
    organisation_id: Optional[uuid.UUID] = Query(default=None),
    is_active: Optional[bool] = Query(default=True),
    db: AsyncSession = Depends(get_async_session),
    _claims = JWTDep,
) -> dict:
    caller_org_id = uuid.UUID(_claims["org_id"]) if _claims.get("org_id") else None
    if caller_org_id is None:
        raise HTTPException(status_code=403, detail={"error": "NO_ORG_CONTEXT"})
    # Always scope to the caller's org
    q = select(FieldAgent).where(FieldAgent.organisation_id == caller_org_id)
    if is_active is not None:
        q = q.where(FieldAgent.is_active == is_active)
    items = (await db.execute(q.order_by(FieldAgent.name))).scalars().all()
    return {"total": len(items), "items": [
        {"id": str(a.id), "user_id": str(a.user_id), "name": a.name,
         "phone": a.phone, "email": a.email, "is_active": a.is_active,
         "assignment_count": a.assignment_count}
        for a in items
    ]}


@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    _claims = JWTDep,
) -> dict:
    caller_org_id = uuid.UUID(_claims["org_id"]) if _claims.get("org_id") else None
    if caller_org_id is None:
        raise HTTPException(status_code=403, detail={"error": "NO_ORG_CONTEXT"})
    agent = FieldAgent(
        user_id=uuid.UUID(body["user_id"]),
        organisation_id=caller_org_id,  # always taken from JWT, body value ignored
        name=body["name"], phone=body.get("phone"), email=body.get("email"),
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return {"id": str(agent.id), "name": agent.name, "organisation_id": str(agent.organisation_id)}
