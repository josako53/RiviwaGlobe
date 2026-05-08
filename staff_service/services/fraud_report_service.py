"""services/fraud_report_service.py — Fraud report business logic."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import FraudReportNotFoundError, ForbiddenError
from events.producer import StaffProducer
from models.staff_fraud_report import StaffFraudReport
from repositories.staff_fraud_report_repository import StaffFraudReportRepository

log = structlog.get_logger(__name__)


class FraudReportService:
    def __init__(self, db: AsyncSession, producer: StaffProducer) -> None:
        self.db = db
        self.repo = StaffFraudReportRepository(db)
        self.producer = producer

    async def submit_report(
        self,
        org_id: Optional[UUID],
        verification_event_id: Optional[UUID],
        reporter_name: Optional[str],
        reporter_phone: Optional[str],
        reporter_email: Optional[str],
        claimed_staff_name: Optional[str],
        claimed_staff_id: Optional[str],
        description: str,
        photo_keys: Optional[List[str]] = None,
        photo_urls: Optional[List[str]] = None,
    ) -> StaffFraudReport:
        report = StaffFraudReport(
            org_id=org_id,
            verification_event_id=verification_event_id,
            reporter_name=reporter_name,
            reporter_phone=reporter_phone,
            reporter_email=reporter_email,
            claimed_staff_name=claimed_staff_name,
            claimed_staff_id=claimed_staff_id,
            description=description,
            photo_keys=photo_keys,
            photo_urls=photo_urls,
            status="SUBMITTED",
        )
        report = await self.repo.create(report)
        self.producer.fraud_report_submitted(report.id, org_id)
        log.info("staff.fraud_report.submitted", report_id=str(report.id))
        return report

    async def get_report(
        self, report_id: UUID, org_id: Optional[UUID] = None, is_platform_admin: bool = False
    ) -> StaffFraudReport:
        report = await self.repo.get_by_id(report_id)
        if not report:
            raise FraudReportNotFoundError()
        if not is_platform_admin and org_id and report.org_id != org_id:
            raise ForbiddenError()
        return report

    async def list_reports(
        self,
        org_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[StaffFraudReport], int]:
        return await self.repo.list_by_org(org_id, status, page, size)

    async def update_report(
        self,
        report_id: UUID,
        org_id: UUID,
        updates: Dict[str, Any],
        is_platform_admin: bool = False,
    ) -> StaffFraudReport:
        report = await self.repo.get_by_id(report_id)
        if not report:
            raise FraudReportNotFoundError()
        if not is_platform_admin and report.org_id != org_id:
            raise ForbiddenError()
        if "status" in updates and updates["status"]:
            updates["status"] = updates["status"].upper()
        return await self.repo.update(report, updates)

    async def assign_agent(
        self,
        report_id: UUID,
        org_id: UUID,
        agent_user_id: UUID,
        notes: Optional[str],
        is_platform_admin: bool = False,
    ) -> StaffFraudReport:
        report = await self.repo.get_by_id(report_id)
        if not report:
            raise FraudReportNotFoundError()
        if not is_platform_admin and report.org_id != org_id:
            raise ForbiddenError()
        updates: Dict[str, Any] = {
            "assigned_agent_id": agent_user_id,
            "status": "UNDER_INVESTIGATION",
        }
        if notes:
            updates["resolution_notes"] = notes
        return await self.repo.update(report, updates)
