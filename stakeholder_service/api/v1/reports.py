"""api/v1/reports.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Query
from core.dependencies import DbDep, KafkaDep, StaffDep
from services.communication_service import CommunicationService

router = APIRouter(prefix="/reports", tags=["Reports"])

def _svc(db, kafka): return CommunicationService(db=db, producer=kafka)

@router.get("/engagement-summary", summary="Activity counts by stage and LGA for a project")
async def engagement_summary(db: DbDep, kafka: KafkaDep, _: StaffDep, project_id: uuid.UUID = Query(...)) -> dict:
    return await _svc(db, kafka).engagement_summary(project_id)

@router.get("/stakeholder-reach", summary="Stakeholder counts by category and vulnerability")
async def stakeholder_reach(db: DbDep, kafka: KafkaDep, _: StaffDep, project_id: uuid.UUID = Query(...)) -> dict:
    return await _svc(db, kafka).stakeholder_reach(project_id)

@router.get("/pending-distributions", summary="Communications requiring distribution that haven't been logged yet")
async def pending_distributions(db: DbDep, kafka: KafkaDep, _: StaffDep, project_id: uuid.UUID = Query(...)) -> dict:
    return await _svc(db, kafka).pending_distributions(project_id)

@router.get("/pending-concerns", summary="Distribution records with unresolved concerns")
async def pending_concerns(db: DbDep, kafka: KafkaDep, _: StaffDep, project_id: uuid.UUID = Query(...)) -> dict:
    return await _svc(db, kafka).pending_concerns(project_id)
