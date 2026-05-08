"""
repositories/waiting_analytics_repo.py
────────────────────────────────────────────────────────────────────────────
Read-only analytics repository that queries waiting_db for queue, staff
session, and wait-time analytics used in cross-service staff performance views.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


class WaitingAnalyticsRepository:
    """Read-only analytics against waiting_db."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _fetchone(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(text(sql), params or {})
        row = result.mappings().first()
        return dict(row) if row else None

    async def _fetchall(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(text(sql), params or {})
        return [dict(r) for r in result.mappings().all()]

    # ── Per-staff performance aggregation ────────────────────────────────────

    async def get_staff_performance(
        self,
        org_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        service_point_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Per-staff aggregate: tickets served, avg/min/max wait time, avg service time,
        and the duty window (first_attended_at → last_finished_at).
        """
        extra = (
            " AND qts.service_point_id = :sp_id"
            if service_point_id else ""
        )
        params: Dict[str, Any] = {
            "org_id":    str(org_id),
            "date_from": date_from,
            "date_to":   date_to,
        }
        if service_point_id:
            params["sp_id"] = str(service_point_id)

        sql = f"""
            SELECT
                qts.assigned_staff_user_id                        AS staff_user_id,
                sp.id                                              AS service_point_id,
                sp.name                                            AS service_point_name,
                sp.point_type,
                COUNT(*)                                           AS tickets_served,
                AVG(qts.wait_duration_seconds)                     AS avg_wait_seconds,
                AVG(qts.service_duration_seconds)                  AS avg_service_seconds,
                MIN(qts.wait_duration_seconds)                     AS min_wait_seconds,
                MAX(qts.wait_duration_seconds)                     AS max_wait_seconds,
                MIN(qts.attending_started_at)                      AS first_attended_at,
                MAX(qts.finished_at)                               AS last_finished_at
            FROM queue_ticket_stages qts
            JOIN queue_tickets  qt ON qt.id = qts.ticket_id
            JOIN service_points sp ON sp.id = qts.service_point_id
            WHERE qt.org_id = :org_id
              AND qts.status = 'FINISHED'
              AND qts.assigned_staff_user_id IS NOT NULL
              AND qts.finished_at >= :date_from
              AND qts.finished_at <= :date_to
              {extra}
            GROUP BY qts.assigned_staff_user_id, sp.id, sp.name, sp.point_type
            ORDER BY tickets_served DESC
        """
        return await self._fetchall(sql, params)

    # ── Staff duty sessions ───────────────────────────────────────────────────

    async def get_staff_duty_sessions(
        self,
        org_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        is_active: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        All staff sessions in the period with counter + service point details.
        """
        active_clause = " AND ss.is_active = :is_active" if is_active is not None else ""
        params: Dict[str, Any] = {
            "org_id":    str(org_id),
            "date_from": date_from,
            "date_to":   date_to,
        }
        if is_active is not None:
            params["is_active"] = is_active

        sql = f"""
            SELECT
                ss.id                   AS session_id,
                ss.staff_user_id,
                ss.staff_counter_id,
                sc.name                 AS counter_name,
                sc.code                 AS counter_code,
                ss.service_point_id,
                sp.name                 AS service_point_name,
                sp.point_type,
                ss.opened_at,
                ss.closed_at,
                ss.is_active,
                ss.tickets_served,
                ss.avg_service_seconds
            FROM staff_sessions   ss
            JOIN service_points   sp ON sp.id = ss.service_point_id
            JOIN staff_counters   sc ON sc.id = ss.staff_counter_id
            WHERE ss.org_id = :org_id
              AND ss.opened_at >= :date_from
              AND ss.opened_at <= :date_to
              {active_clause}
            ORDER BY ss.opened_at DESC
        """
        return await self._fetchall(sql, params)

    # ── Wait time bucketed by period ─────────────────────────────────────────

    async def get_wait_time_by_period(
        self,
        org_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        granularity: str = "hour",
    ) -> List[Dict[str, Any]]:
        """
        Queue wait/service times bucketed by hour, day, or week.
        granularity must be validated to 'hour'|'day'|'week' before calling.
        """
        trunc = granularity if granularity in ("hour", "day", "week") else "hour"
        sql = f"""
            SELECT
                date_trunc('{trunc}', qts.finished_at) AS period,
                COUNT(*)                               AS tickets_served,
                AVG(qts.wait_duration_seconds)         AS avg_wait_seconds,
                AVG(qts.service_duration_seconds)      AS avg_service_seconds,
                MIN(qts.wait_duration_seconds)         AS min_wait_seconds,
                MAX(qts.wait_duration_seconds)         AS max_wait_seconds
            FROM queue_ticket_stages qts
            JOIN queue_tickets qt ON qt.id = qts.ticket_id
            WHERE qt.org_id = :org_id
              AND qts.status = 'FINISHED'
              AND qts.finished_at >= :date_from
              AND qts.finished_at <= :date_to
            GROUP BY period
            ORDER BY period
        """
        return await self._fetchall(sql, {
            "org_id":    str(org_id),
            "date_from": date_from,
            "date_to":   date_to,
        })

    # ── Wait time per service point ───────────────────────────────────────────

    async def get_wait_by_service_point(
        self,
        org_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> List[Dict[str, Any]]:
        """Wait and service time stats grouped by service point."""
        sql = """
            SELECT
                sp.id                              AS service_point_id,
                sp.name                            AS service_point_name,
                sp.point_type,
                COUNT(*)                           AS tickets_served,
                AVG(qts.wait_duration_seconds)     AS avg_wait_seconds,
                AVG(qts.service_duration_seconds)  AS avg_service_seconds,
                MAX(qts.wait_duration_seconds)     AS max_wait_seconds,
                MIN(qts.wait_duration_seconds)     AS min_wait_seconds
            FROM queue_ticket_stages qts
            JOIN queue_tickets  qt ON qt.id  = qts.ticket_id
            JOIN service_points sp ON sp.id  = qts.service_point_id
            WHERE qt.org_id = :org_id
              AND qts.status = 'FINISHED'
              AND qts.finished_at >= :date_from
              AND qts.finished_at <= :date_to
            GROUP BY sp.id, sp.name, sp.point_type
            ORDER BY avg_wait_seconds DESC NULLS LAST
        """
        return await self._fetchall(sql, {
            "org_id":    str(org_id),
            "date_from": date_from,
            "date_to":   date_to,
        })
