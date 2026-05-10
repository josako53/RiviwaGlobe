"""
repositories/employee_feedback_analytics_repo.py
─────────────────────────────────────────────────────────────────────────────
Read-only analytics against the employee_feedbacks table in feedback_db.
Uses the same raw-SQL pattern as FeedbackAnalyticsRepository.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


class EmployeeFeedbackAnalyticsRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _fetchone(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(text(sql), params or {})
        row = result.mappings().first()
        return dict(row) if row else None

    async def _fetchall(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(text(sql), params or {})
        return [dict(r) for r in result.mappings().all()]

    def _date_params(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
    ) -> tuple[list[str], Dict[str, Any]]:
        clauses: list[str] = []
        params: Dict[str, Any] = {}
        if date_from:
            clauses.append("ef.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            clauses.append("ef.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        return clauses, params

    # ── Employee feedback: summary ────────────────────────────────────────────

    async def get_summary(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        date_clauses, params = self._date_params(date_from, date_to)
        params["org_id"] = str(org_id)
        where = " AND ".join(["ef.org_id = :org_id"] + date_clauses)
        row = await self._fetchone(f"""
            SELECT
                COUNT(*)                                                          AS total,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'grievance')            AS grievances,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'suggestion')           AS suggestions,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'applause')             AS applause,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'inquiry')              AS inquiries,
                COUNT(*) FILTER (WHERE ef.is_anonymous = true)                    AS anonymous_count,
                COUNT(*) FILTER (WHERE ef.status = 'submitted')                   AS pending,
                COUNT(*) FILTER (WHERE ef.status = 'acknowledged')                AS acknowledged,
                COUNT(*) FILTER (WHERE ef.status = 'resolved')                    AS resolved,
                COUNT(*) FILTER (WHERE ef.status = 'closed')                      AS closed,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE ef.feedback_type = 'applause')
                    / NULLIF(COUNT(*), 0), 1
                )                                                                  AS applause_rate
            FROM employee_feedbacks ef
            WHERE {where}
        """, params)
        return row or {}

    # ── By category ───────────────────────────────────────────────────────────

    async def get_by_category(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        date_clauses, params = self._date_params(date_from, date_to)
        params["org_id"] = str(org_id)
        where = " AND ".join(["ef.org_id = :org_id"] + date_clauses)
        return await self._fetchall(f"""
            SELECT
                ef.category,
                COUNT(*)                                                       AS total,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'grievance')         AS grievances,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'suggestion')        AS suggestions,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'applause')          AS applause,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'inquiry')           AS inquiries,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE ef.feedback_type = 'applause')
                    / NULLIF(COUNT(*), 0), 1
                )                                                               AS applause_rate
            FROM employee_feedbacks ef
            WHERE {where}
            GROUP BY ef.category
            ORDER BY total DESC
        """, params)

    # ── By department ────────────────────────────────────────────────────────

    async def get_by_department(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        date_clauses, params = self._date_params(date_from, date_to)
        params["org_id"] = str(org_id)
        where = " AND ".join(["ef.org_id = :org_id"] + date_clauses)
        return await self._fetchall(f"""
            SELECT
                ef.department_id,
                ef.branch_id,
                COUNT(*)                                                       AS total,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'grievance')         AS grievances,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'suggestion')        AS suggestions,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'applause')          AS applause,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'inquiry')           AS inquiries,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE ef.feedback_type = 'applause')
                    / NULLIF(COUNT(*), 0), 1
                )                                                               AS applause_rate
            FROM employee_feedbacks ef
            WHERE {where}
            GROUP BY ef.department_id, ef.branch_id
            ORDER BY total DESC
        """, params)

    # ── Trend over time ───────────────────────────────────────────────────────

    async def get_trend(
        self,
        org_id: uuid.UUID,
        granularity: str = "day",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        trunc_map = {"hour": "hour", "day": "day", "week": "week", "month": "month"}
        trunc = trunc_map.get(granularity, "day")
        date_clauses, params = self._date_params(date_from, date_to)
        params["org_id"] = str(org_id)
        where = " AND ".join(["ef.org_id = :org_id"] + date_clauses)
        return await self._fetchall(f"""
            SELECT
                DATE_TRUNC('{trunc}', ef.submitted_at) AS period,
                COUNT(*)                                                       AS total,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'grievance')         AS grievances,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'suggestion')        AS suggestions,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'applause')          AS applause,
                COUNT(*) FILTER (WHERE ef.feedback_type = 'inquiry')           AS inquiries
            FROM employee_feedbacks ef
            WHERE {where}
            GROUP BY 1
            ORDER BY 1
        """, params)

    # ── Consumer feedback summary (for combined view) ─────────────────────────

    async def get_consumer_summary(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Consumer/GRM feedback summary from the feedbacks table."""
        date_clauses, params = self._date_params(date_from, date_to)
        params["org_id"] = str(org_id)
        where = " AND ".join(["f.org_id = :org_id"] + date_clauses)
        row = await self._fetchone(f"""
            SELECT
                COUNT(*)                                                           AS total,
                COUNT(*) FILTER (WHERE f.feedback_type = 'GRIEVANCE')             AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type = 'SUGGESTION')            AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type = 'APPLAUSE')              AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type = 'INQUIRY')               AS inquiries,
                COUNT(*) FILTER (WHERE f.status IN ('RESOLVED','ACTIONED','NOTED','DISMISSED','CLOSED'))
                                                                                   AS resolved,
                COUNT(*) FILTER (WHERE f.status IN ('SUBMITTED','ACKNOWLEDGED','IN_REVIEW','ESCALATED','APPEALED'))
                                                                                   AS open_count,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE f.feedback_type = 'APPLAUSE')
                    / NULLIF(COUNT(*), 0), 1
                )                                                                   AS applause_rate,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE f.status IN ('RESOLVED','ACTIONED','NOTED','DISMISSED','CLOSED'))
                    / NULLIF(COUNT(*), 0), 1
                )                                                                   AS resolution_rate,
                ROUND(
                    EXTRACT(EPOCH FROM AVG(
                        f.resolved_at - f.submitted_at
                    )) / 3600.0, 1
                )                                                                   AS avg_resolution_hours
            FROM feedbacks f
            WHERE {where}
        """, params)
        return row or {}

    # ── Combined performance ──────────────────────────────────────────────────

    async def get_combined_performance(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        consumer = await self.get_consumer_summary(org_id, date_from, date_to)
        employee = await self.get_summary(org_id, date_from, date_to)
        by_category = await self.get_by_category(org_id, date_from, date_to)

        c_total     = int(consumer.get("total") or 0)
        c_applause  = int(consumer.get("applause") or 0)
        e_total     = int(employee.get("total") or 0)
        e_applause  = int(employee.get("applause") or 0)

        combined_total   = c_total + e_total
        combined_applause = c_applause + e_applause
        combined_rate    = (
            round(100.0 * combined_applause / combined_total, 1)
            if combined_total > 0 else 0.0
        )

        if combined_rate >= 70:
            health = "excellent"
        elif combined_rate >= 50:
            health = "good"
        elif combined_rate >= 30:
            health = "fair"
        else:
            health = "needs_improvement"

        return {
            "org_id": str(org_id),
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "consumer": consumer,
            "employee": {
                **employee,
                "by_category": by_category,
            },
            "combined": {
                "total": combined_total,
                "applause": combined_applause,
                "applause_rate": combined_rate,
                "health_score": health,
            },
        }
