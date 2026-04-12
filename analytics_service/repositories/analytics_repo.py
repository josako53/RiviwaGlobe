"""
repositories/analytics_repo.py
────────────────────────────────────────────────────────────────────────────
Repository for analytics_db (own database). Reads and writes pre-computed
analytics tables: StaffLogin, FeedbackSLAStatus, HotspotAlert,
CommitteePerformance, FeedbackMLScore, GeneratedReport.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.analytics import (
    CommitteePerformance,
    FeedbackMLScore,
    FeedbackSLAStatus,
    GeneratedReport,
    HotspotAlert,
    StaffLogin,
)

log = structlog.get_logger(__name__)


class AnalyticsRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── StaffLogin ────────────────────────────────────────────────────────────

    async def upsert_staff_login(
        self,
        user_id: uuid.UUID,
        login_at: datetime,
        ip_address: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> StaffLogin:
        record = StaffLogin(
            user_id=user_id,
            login_at=login_at,
            ip_address=ip_address,
            platform=platform,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        log.info("analytics.staff_login.recorded", user_id=str(user_id))
        return record

    async def get_staff_logins(
        self,
        user_ids: Optional[List[uuid.UUID]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[StaffLogin]:
        q = select(StaffLogin)
        if user_ids:
            q = q.where(StaffLogin.user_id.in_(user_ids))
        if date_from:
            q = q.where(StaffLogin.login_at >= date_from)
        if date_to:
            q = q.where(StaffLogin.login_at <= date_to)
        q = q.order_by(StaffLogin.login_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_last_login_per_user(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns last login and login count in last 7 days per user.
        Uses raw SQL for window function efficiency.
        """
        params: Dict[str, Any] = {}
        where_clauses = []

        if date_from:
            where_clauses.append("login_at >= :date_from")
            params["date_from"] = date_from
        if date_to:
            where_clauses.append("login_at <= :date_to")
            params["date_to"] = date_to

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        sql = f"""
            SELECT
                user_id,
                MAX(login_at)                                    AS last_login_at,
                COUNT(*) FILTER (
                    WHERE login_at >= NOW() - INTERVAL '7 days'
                )                                                AS login_count_7d,
                (ARRAY_AGG(platform ORDER BY login_at DESC))[1]  AS platform
            FROM staff_logins
            {where_sql}
            GROUP BY user_id
            ORDER BY last_login_at DESC
        """
        result = await self.db.execute(text(sql), params)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def get_logins_today_user_ids(self) -> List[uuid.UUID]:
        """Return user_ids of staff who logged in today."""
        sql = """
            SELECT DISTINCT user_id
            FROM staff_logins
            WHERE DATE(login_at AT TIME ZONE 'UTC') = CURRENT_DATE
        """
        result = await self.db.execute(text(sql))
        rows = result.fetchall()
        return [r[0] for r in rows]

    # ── FeedbackSLAStatus ─────────────────────────────────────────────────────

    async def upsert_sla_status(self, data: Dict[str, Any]) -> FeedbackSLAStatus:
        """
        Upsert a FeedbackSLAStatus record by feedback_id (primary key).
        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE.
        """
        stmt = (
            pg_insert(FeedbackSLAStatus)
            .values(**data)
            .on_conflict_do_update(
                index_elements=["feedback_id"],
                set_={k: v for k, v in data.items() if k != "feedback_id"},
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

        result = await self.db.execute(
            select(FeedbackSLAStatus).where(
                FeedbackSLAStatus.feedback_id == data["feedback_id"]
            )
        )
        return result.scalar_one()

    async def get_sla_status(
        self,
        project_id: uuid.UUID,
        breached_only: bool = False,
    ) -> List[FeedbackSLAStatus]:
        q = select(FeedbackSLAStatus).where(FeedbackSLAStatus.project_id == project_id)
        if breached_only:
            q = q.where(
                (FeedbackSLAStatus.ack_sla_breached == True)  # noqa: E712
                | (FeedbackSLAStatus.res_sla_breached == True)  # noqa: E712
            )
        q = q.order_by(FeedbackSLAStatus.submitted_at.asc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # ── HotspotAlert ──────────────────────────────────────────────────────────

    async def get_hotspot_alerts(
        self,
        project_id: uuid.UUID,
        status: str = "active",
    ) -> List[HotspotAlert]:
        q = (
            select(HotspotAlert)
            .where(HotspotAlert.project_id == project_id)
            .where(HotspotAlert.alert_status == status)
            .order_by(HotspotAlert.spike_factor.desc())
        )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create_hotspot_alert(self, data: Dict[str, Any]) -> HotspotAlert:
        alert = HotspotAlert(**data)
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)
        return alert

    async def resolve_hotspot_alert(self, alert_id: uuid.UUID) -> Optional[HotspotAlert]:
        result = await self.db.execute(
            select(HotspotAlert).where(HotspotAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        if alert:
            alert.alert_status = "resolved"
            self.db.add(alert)
            await self.db.flush()
        return alert

    # ── CommitteePerformance ──────────────────────────────────────────────────

    async def get_committee_performance_precomputed(
        self,
        project_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[CommitteePerformance]:
        q = select(CommitteePerformance).where(
            CommitteePerformance.project_id == project_id
        )
        if date_from:
            q = q.where(CommitteePerformance.computed_date >= date_from)
        if date_to:
            q = q.where(CommitteePerformance.computed_date <= date_to)
        q = q.order_by(CommitteePerformance.computed_date.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def upsert_committee_performance(
        self, data: Dict[str, Any]
    ) -> CommitteePerformance:
        stmt = (
            pg_insert(CommitteePerformance)
            .values(**data)
            .on_conflict_do_update(
                index_elements=["id"],
                set_={k: v for k, v in data.items() if k != "id"},
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()
        result = await self.db.execute(
            select(CommitteePerformance).where(
                CommitteePerformance.id == data["id"]
            )
        )
        return result.scalar_one()

    # ── FeedbackMLScore ───────────────────────────────────────────────────────

    async def get_ml_score(
        self, feedback_id: uuid.UUID
    ) -> Optional[FeedbackMLScore]:
        result = await self.db.execute(
            select(FeedbackMLScore).where(
                FeedbackMLScore.feedback_id == feedback_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert_ml_score(self, data: Dict[str, Any]) -> FeedbackMLScore:
        stmt = (
            pg_insert(FeedbackMLScore)
            .values(**data)
            .on_conflict_do_update(
                index_elements=["feedback_id"],
                set_={k: v for k, v in data.items() if k != "feedback_id"},
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()
        result = await self.db.execute(
            select(FeedbackMLScore).where(
                FeedbackMLScore.feedback_id == data["feedback_id"]
            )
        )
        return result.scalar_one()

    # ── GeneratedReport ───────────────────────────────────────────────────────

    async def get_generated_report(
        self,
        project_id: uuid.UUID,
        report_type: str,
    ) -> Optional[GeneratedReport]:
        """Return the most recent GeneratedReport of the given type for a project."""
        result = await self.db.execute(
            select(GeneratedReport)
            .where(GeneratedReport.project_id == project_id)
            .where(GeneratedReport.report_type == report_type)
            .order_by(GeneratedReport.generated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_generated_report(self, data: Dict[str, Any]) -> GeneratedReport:
        report = GeneratedReport(**data)
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def list_generated_reports(
        self,
        project_id: uuid.UUID,
        report_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[GeneratedReport]:
        q = (
            select(GeneratedReport)
            .where(GeneratedReport.project_id == project_id)
            .order_by(GeneratedReport.generated_at.desc())
            .limit(limit)
        )
        if report_type:
            q = q.where(GeneratedReport.report_type == report_type)
        result = await self.db.execute(q)
        return list(result.scalars().all())
