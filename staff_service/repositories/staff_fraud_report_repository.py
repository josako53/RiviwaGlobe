"""repositories/staff_fraud_report_repository.py — StaffFraudReport DB ops."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.staff_fraud_report import StaffFraudReport


class StaffFraudReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, report: StaffFraudReport) -> StaffFraudReport:
        self.db.add(report)
        await self.db.flush()
        return report

    async def get_by_id(self, report_id: UUID) -> Optional[StaffFraudReport]:
        return await self.db.get(StaffFraudReport, report_id)

    async def list_by_org(
        self,
        org_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[StaffFraudReport], int]:
        q = select(StaffFraudReport).where(StaffFraudReport.org_id == org_id)
        if status:
            q = q.where(StaffFraudReport.status == status.upper())

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(StaffFraudReport.created_at.desc()).offset((page - 1) * size).limit(size)
        rows = (await self.db.execute(q)).scalars().all()
        return rows, total

    async def update(self, report: StaffFraudReport, data: Dict[str, Any]) -> StaffFraudReport:
        import datetime as dt
        for k, v in data.items():
            setattr(report, k, v)
        report.updated_at = dt.datetime.utcnow()
        self.db.add(report)
        await self.db.flush()
        return report

    async def stats_by_org(self, org_id: UUID) -> dict:
        result = await self.db.execute(
            select(
                StaffFraudReport.status,
                func.count(StaffFraudReport.id).label("cnt"),
            ).where(
                StaffFraudReport.org_id == org_id
            ).group_by(StaffFraudReport.status)
        )
        rows = result.all()
        by_status = {r.status: r.cnt for r in rows}
        total = sum(by_status.values())
        return {"total": total, "by_status": by_status}
