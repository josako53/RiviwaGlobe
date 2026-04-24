"""
repositories/feedback_analytics_repo.py
────────────────────────────────────────────────────────────────────────────
Read-only analytics repository that queries feedback_db directly using
raw SQL (text()) for complex analytics queries that are not possible via
standard SQLModel ORM (cross-service, read-only connection).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


class FeedbackAnalyticsRepository:
    """All methods are read-only analytics queries against feedback_db."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Internal helper ───────────────────────────────────────────────────────

    async def _fetchall(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(text(sql), params or {})
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    # ── Feedback: Time-to-Open ────────────────────────────────────────────────

    async def get_time_to_open(
        self,
        project_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Average/min/max/median hours from submitted_at to first feedback_action.performed_at,
        per feedback, for a given project.
        """
        where_clauses = ["f.project_id = :project_id"]
        params: Dict[str, Any] = {"project_id": str(project_id)}

        if date_from:
            where_clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            where_clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)

        where_sql = " AND ".join(where_clauses)
        sql = f"""
            SELECT
                f.id              AS feedback_id,
                f.unique_ref,
                f.priority,
                f.submitted_at,
                MIN(fa.performed_at) AS first_action_at,
                EXTRACT(EPOCH FROM (MIN(fa.performed_at) - f.submitted_at)) / 3600.0 AS hours_to_open
            FROM feedbacks f
            JOIN feedback_actions fa ON fa.feedback_id = f.id
            WHERE {where_sql}
            GROUP BY f.id, f.unique_ref, f.priority, f.submitted_at
            HAVING MIN(fa.performed_at) IS NOT NULL
            ORDER BY hours_to_open ASC
        """
        return await self._fetchall(sql, params)

    # ── Feedback: Unread ──────────────────────────────────────────────────────

    async def get_unread_grievances(
        self,
        project_id: uuid.UUID,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Feedbacks where status='submitted' AND feedback_type='grievance', ordered by submitted_at ASC.
        """
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra = ""
        if priority:
            extra = " AND f.priority = :priority"
            params["priority"] = priority.upper() if priority else priority

        sql = f"""
            SELECT
                f.id              AS feedback_id,
                f.unique_ref,
                f.feedback_type,
                f.priority,
                f.submitted_at,
                EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0 AS days_waiting,
                f.channel,
                f.issue_lga,
                NULL              AS submitter_name
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.status::text = 'SUBMITTED'
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
            ORDER BY f.submitted_at ASC
        """
        return await self._fetchall(sql, params)

    async def get_unread_all(
        self,
        project_id: uuid.UUID,
        priority: Optional[str] = None,
        feedback_type: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        service_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        category_def_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        All unread feedbacks (status='submitted') with optional filters.
        """
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses = []

        if priority:
            extra_clauses.append("f.priority::text = :priority")
            params["priority"] = priority.upper() if priority else priority
        if feedback_type:
            extra_clauses.append("f.feedback_type::text = :feedback_type")
            params["feedback_type"] = feedback_type.upper() if feedback_type else feedback_type
        if department_id:
            extra_clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if service_id:
            extra_clauses.append("f.service_id = :service_id")
            params["service_id"] = str(service_id)
        if product_id:
            extra_clauses.append("f.product_id = :product_id")
            params["product_id"] = str(product_id)
        if category_def_id:
            extra_clauses.append("f.category_def_id = :category_def_id")
            params["category_def_id"] = str(category_def_id)

        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.id              AS feedback_id,
                f.unique_ref,
                f.feedback_type::text,
                f.priority::text,
                f.submitted_at,
                EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0 AS days_waiting,
                f.channel::text,
                f.issue_lga,
                f.department_id,
                f.service_id,
                f.product_id,
                f.category_def_id,
                NULL              AS submitter_name
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.status::text = 'SUBMITTED'
              {extra}
            ORDER BY f.submitted_at ASC
        """
        return await self._fetchall(sql, params)

    # ── Feedback: Overdue ─────────────────────────────────────────────────────

    async def get_overdue(
        self,
        project_id: uuid.UUID,
        feedback_type: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        service_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        category_def_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        status IN ('acknowledged','in_review') AND target_resolution_date < NOW()
        """
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses = []
        if feedback_type:
            extra_clauses.append("f.feedback_type::text = :feedback_type")
            params["feedback_type"] = feedback_type.upper() if feedback_type else feedback_type
        if department_id:
            extra_clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if service_id:
            extra_clauses.append("f.service_id = :service_id")
            params["service_id"] = str(service_id)
        if product_id:
            extra_clauses.append("f.product_id = :product_id")
            params["product_id"] = str(product_id)
        if category_def_id:
            extra_clauses.append("f.category_def_id = :category_def_id")
            params["category_def_id"] = str(category_def_id)

        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.id                      AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.status::text,
                f.submitted_at,
                f.target_resolution_date,
                EXTRACT(EPOCH FROM (NOW() - f.target_resolution_date)) / 86400.0 AS days_overdue,
                f.assigned_to_user_id,
                f.assigned_committee_id   AS committee_id,
                f.department_id,
                f.service_id,
                f.product_id,
                f.category_def_id
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.status::text IN ('ACKNOWLEDGED', 'IN_REVIEW')
              AND f.target_resolution_date < NOW()
              {extra}
            ORDER BY f.target_resolution_date ASC
        """
        return await self._fetchall(sql, params)

    # ── Feedback: Read Not Processed ─────────────────────────────────────────

    async def get_read_not_processed(
        self,
        project_id: uuid.UUID,
        feedback_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        status IN ('acknowledged','in_review') — acknowledged but not yet resolved.
        """
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra = ""
        if feedback_type:
            extra = " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper() if feedback_type else feedback_type

        sql = f"""
            SELECT
                f.id                      AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.status::text,
                f.submitted_at,
                f.target_resolution_date,
                CASE
                    WHEN f.target_resolution_date IS NOT NULL AND f.target_resolution_date < NOW()
                    THEN EXTRACT(EPOCH FROM (NOW() - f.target_resolution_date)) / 86400.0
                    ELSE NULL
                END                       AS days_overdue,
                f.assigned_to_user_id,
                f.assigned_committee_id   AS committee_id
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.status::text IN ('ACKNOWLEDGED', 'IN_REVIEW')
              {extra}
            ORDER BY f.submitted_at ASC
        """
        return await self._fetchall(sql, params)

    # ── Feedback: Processed Today ─────────────────────────────────────────────

    async def get_processed_today(self, project_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Feedbacks where DATE(updated_at) = today AND status = 'in_review'.
        """
        sql = """
            SELECT
                f.id          AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.category::text,
                f.updated_at  AS processed_at
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.status::text = 'IN_REVIEW'
              AND DATE(f.updated_at AT TIME ZONE 'UTC') = CURRENT_DATE
            ORDER BY f.updated_at DESC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Feedback: Resolved Today ──────────────────────────────────────────────

    async def get_resolved_today(self, project_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Feedbacks where DATE(resolved_at) = today.
        """
        sql = """
            SELECT
                f.id          AS feedback_id,
                f.unique_ref,
                f.feedback_type::text,
                f.priority::text,
                f.category::text,
                f.resolved_at,
                EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0 AS resolution_hours
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND DATE(f.resolved_at AT TIME ZONE 'UTC') = CURRENT_DATE
            ORDER BY f.resolved_at DESC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Grievances: Unresolved ────────────────────────────────────────────────

    async def get_unresolved_grievances(
        self,
        project_id: uuid.UUID,
        min_days: Optional[float] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        service_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        category_def_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        feedback_type='grievance' AND status NOT IN ('resolved','closed','dismissed').
        days_unresolved = EXTRACT(EPOCH FROM now()-submitted_at)/86400
        """
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses: List[str] = []

        if min_days is not None:
            extra_clauses.append(
                "EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0 >= :min_days"
            )
            params["min_days"] = min_days
        if priority:
            extra_clauses.append("f.priority::text = :priority")
            params["priority"] = priority.upper() if priority else priority
        if status:
            extra_clauses.append("f.status::text = :status")
            params["status"] = status.upper() if status else status
        if department_id:
            extra_clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if service_id:
            extra_clauses.append("f.service_id = :service_id")
            params["service_id"] = str(service_id)
        if product_id:
            extra_clauses.append("f.product_id = :product_id")
            params["product_id"] = str(product_id)
        if category_def_id:
            extra_clauses.append("f.category_def_id = :category_def_id")
            params["category_def_id"] = str(category_def_id)

        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.id                      AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.category::text,
                f.status::text,
                f.submitted_at,
                EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0 AS days_unresolved,
                f.assigned_to_user_id,
                f.assigned_committee_id   AS committee_id,
                f.issue_lga,
                f.issue_ward,
                f.department_id,
                f.service_id,
                f.product_id,
                f.category_def_id
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'GRIEVANCE'
              AND f.status::text NOT IN ('RESOLVED', 'CLOSED', 'DISMISSED')
              {extra}
            ORDER BY f.submitted_at ASC
        """
        return await self._fetchall(sql, params)

    # ── Suggestions: Implementation Time ─────────────────────────────────────

    async def get_suggestion_implementation_time(
        self, project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Suggestions with status='actioned'.
        EXTRACT(EPOCH FROM resolved_at - submitted_at)/3600 as hours
        """
        sql = """
            SELECT
                f.id          AS feedback_id,
                f.unique_ref,
                f.submitted_at,
                f.resolved_at AS implemented_at,
                EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0 AS hours_to_implement,
                f.category
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'SUGGESTION'
              AND f.status::text = 'ACTIONED'
              AND f.resolved_at IS NOT NULL
            ORDER BY hours_to_implement ASC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Suggestions: Frequency ────────────────────────────────────────────────

    async def get_suggestion_frequency(
        self,
        project_id: uuid.UUID,
        period: str = "week",
    ) -> List[Dict[str, Any]]:
        """
        Count suggestions by category + priority for the current period (week/month/year).
        """
        period_map = {
            "week": ("7 days", 7),
            "month": ("30 days", 30),
            "year": ("365 days", 365),
        }
        interval, days = period_map.get(period, ("7 days", 7))

        sql = f"""
            SELECT
                f.category,
                f.priority,
                COUNT(*) AS count,
                ROUND(CAST(COUNT(*) AS NUMERIC) / {days}, 4) AS rate_per_day
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'SUGGESTION'
              AND f.submitted_at >= NOW() - INTERVAL '{interval}'
            GROUP BY f.category, f.priority
            ORDER BY count DESC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Suggestions: By Location ──────────────────────────────────────────────

    async def get_suggestion_by_location(
        self, project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        GROUP BY issue_region, issue_lga, issue_ward with counts and implementation rate.
        """
        sql = """
            SELECT
                f.issue_region                                            AS region,
                f.issue_lga                                               AS lga,
                f.issue_ward                                              AS ward,
                COUNT(*)                                                  AS count,
                COUNT(*) FILTER (WHERE f.status::text = 'ACTIONED')      AS implemented_count,
                CASE
                    WHEN COUNT(*) > 0
                    THEN ROUND(
                        CAST(COUNT(*) FILTER (WHERE f.status::text = 'ACTIONED') AS NUMERIC) /
                        CAST(COUNT(*) AS NUMERIC) * 100.0, 2
                    )
                    ELSE NULL
                END                                                       AS implementation_rate
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'SUGGESTION'
            GROUP BY f.issue_region, f.issue_lga, f.issue_ward
            ORDER BY count DESC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Suggestions: Unread ───────────────────────────────────────────────────

    async def get_unread_suggestions(
        self, project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        status='submitted' AND feedback_type='suggestion' with days_unread.
        """
        sql = """
            SELECT
                f.id          AS feedback_id,
                f.unique_ref,
                f.submitted_at,
                EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0 AS days_unread,
                f.priority,
                f.category,
                f.issue_lga
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.status::text = 'SUBMITTED'
              AND f.feedback_type::text = 'SUGGESTION'
            ORDER BY f.submitted_at ASC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Suggestions: Implemented Today ───────────────────────────────────────

    async def get_suggestions_implemented_today(
        self, project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        DATE(resolved_at) = today AND feedback_type='suggestion' AND status='actioned'.
        """
        sql = """
            SELECT
                f.id          AS feedback_id,
                f.unique_ref,
                f.category,
                f.submitted_at,
                f.resolved_at AS implemented_at,
                EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0 AS hours_to_implement
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'SUGGESTION'
              AND f.status::text = 'ACTIONED'
              AND DATE(f.resolved_at AT TIME ZONE 'UTC') = CURRENT_DATE
            ORDER BY f.resolved_at DESC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Suggestions: Implemented This Week ───────────────────────────────────

    async def get_suggestions_implemented_this_week(
        self, project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        DATE_TRUNC('week', resolved_at) = DATE_TRUNC('week', now()) AND status='actioned'.
        """
        sql = """
            SELECT
                f.id          AS feedback_id,
                f.unique_ref,
                f.category,
                f.submitted_at,
                f.resolved_at AS implemented_at,
                EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0 AS hours_to_implement
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'SUGGESTION'
              AND f.status::text = 'ACTIONED'
              AND DATE_TRUNC('week', f.resolved_at AT TIME ZONE 'UTC') =
                  DATE_TRUNC('week', NOW() AT TIME ZONE 'UTC')
            ORDER BY f.resolved_at DESC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Staff: Committee Performance ──────────────────────────────────────────

    async def get_committee_performance(
        self, project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        JOIN grm_committees + feedbacks GROUP BY committee_id:
        count assigned, resolved, overdue, avg resolution hours.
        """
        sql = """
            SELECT
                c.id                                          AS committee_id,
                c.name                                        AS committee_name,
                c.level,
                c.project_id,
                COUNT(f.id)                                   AS cases_assigned,
                COUNT(f.id) FILTER (
                    WHERE f.status::text IN ('RESOLVED', 'CLOSED')
                )                                             AS cases_resolved,
                COUNT(f.id) FILTER (
                    WHERE f.status::text IN ('ACKNOWLEDGED', 'IN_REVIEW')
                      AND f.target_resolution_date < NOW()
                )                                             AS cases_overdue,
                ROUND(
                    CAST(
                        AVG(
                            CASE
                                WHEN f.resolved_at IS NOT NULL
                                THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                                ELSE NULL
                            END
                        ) AS NUMERIC
                    ), 2
                )                                             AS avg_resolution_hours,
                CASE
                    WHEN COUNT(f.id) > 0
                    THEN ROUND(
                        CAST(
                            COUNT(f.id) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED')) AS NUMERIC
                        ) / CAST(COUNT(f.id) AS NUMERIC) * 100.0, 2
                    )
                    ELSE NULL
                END                                           AS resolution_rate
            FROM grm_committees c
            LEFT JOIN feedbacks f ON f.assigned_committee_id = c.id
            WHERE c.project_id = :project_id
              AND c.is_active = TRUE
            GROUP BY c.id, c.name, c.level, c.project_id
            ORDER BY cases_assigned DESC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Staff: Unread Assigned ────────────────────────────────────────────────

    async def get_staff_unread_assigned(
        self, project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Feedbacks assigned to an officer (assigned_to_user_id IS NOT NULL, status='submitted')
        with NO feedback_actions by that officer yet.
        """
        sql = """
            SELECT
                f.assigned_to_user_id  AS user_id,
                COUNT(f.id)            AS unread_count,
                ARRAY_AGG(f.id)        AS feedback_ids
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.assigned_to_user_id IS NOT NULL
              AND f.status::text = 'SUBMITTED'
              AND NOT EXISTS (
                  SELECT 1
                  FROM feedback_actions fa
                  WHERE fa.feedback_id = f.id
                    AND fa.performed_by_user_id = f.assigned_to_user_id
              )
            GROUP BY f.assigned_to_user_id
            ORDER BY unread_count DESC
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    async def get_all_assigned_per_officer(
        self, project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Total assigned feedbacks per officer for a project.
        """
        sql = """
            SELECT
                f.assigned_to_user_id AS user_id,
                COUNT(f.id)           AS assigned_count
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.assigned_to_user_id IS NOT NULL
            GROUP BY f.assigned_to_user_id
        """
        return await self._fetchall(sql, {"project_id": str(project_id)})

    # ── Breakdown: By Service ─────────────────────────────────────────────────

    async def get_breakdown_by_service(
        self,
        project_id: uuid.UUID,
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        GROUP BY service_id: count, resolved count, avg resolution hours.
        Only rows where service_id IS NOT NULL.
        """
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses: List[str] = []
        if feedback_type:
            extra_clauses.append("f.feedback_type::text = :feedback_type")
            params["feedback_type"] = feedback_type.upper()
        if date_from:
            extra_clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            extra_clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)

        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.service_id,
                COUNT(*)                                                          AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')      AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')     AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')       AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')        AS inquiries,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))  AS resolved,
                ROUND(CAST(
                    AVG(CASE WHEN f.resolved_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                        ELSE NULL END
                    ) AS NUMERIC
                ), 2)                                                             AS avg_resolution_hours
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.service_id IS NOT NULL
              {extra}
            GROUP BY f.service_id
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Breakdown: By Product ─────────────────────────────────────────────────

    async def get_breakdown_by_product(
        self,
        project_id: uuid.UUID,
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        GROUP BY product_id: count, resolved count, avg resolution hours.
        Only rows where product_id IS NOT NULL.
        """
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses: List[str] = []
        if feedback_type:
            extra_clauses.append("f.feedback_type::text = :feedback_type")
            params["feedback_type"] = feedback_type.upper()
        if date_from:
            extra_clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            extra_clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)

        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.product_id,
                COUNT(*)                                                          AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')      AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')     AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')       AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')        AS inquiries,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))  AS resolved,
                ROUND(CAST(
                    AVG(CASE WHEN f.resolved_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                        ELSE NULL END
                    ) AS NUMERIC
                ), 2)                                                             AS avg_resolution_hours
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.product_id IS NOT NULL
              {extra}
            GROUP BY f.product_id
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Breakdown: By Category Def ────────────────────────────────────────────

    async def get_breakdown_by_category_def(
        self,
        project_id: uuid.UUID,
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        GROUP BY category_def_id + category name/slug from feedback_category_defs.
        Includes rows with category_def_id IS NULL grouped as 'uncategorised'.
        """
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses: List[str] = []
        if feedback_type:
            extra_clauses.append("f.feedback_type::text = :feedback_type")
            params["feedback_type"] = feedback_type.upper()
        if date_from:
            extra_clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            extra_clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)

        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.category_def_id,
                cd.name                                                           AS category_name,
                cd.slug                                                           AS category_slug,
                COUNT(*)                                                          AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')      AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')     AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')       AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')        AS inquiries,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))  AS resolved,
                ROUND(CAST(
                    AVG(CASE WHEN f.resolved_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                        ELSE NULL END
                    ) AS NUMERIC
                ), 2)                                                             AS avg_resolution_hours
            FROM feedbacks f
            LEFT JOIN feedback_category_defs cd ON cd.id = f.category_def_id
            WHERE f.project_id = :project_id
              {extra}
            GROUP BY f.category_def_id, cd.name, cd.slug
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Org-level: Summary ───────────────────────────────────────────────────

    async def get_org_summary(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(*)                                                                    AS total_feedback,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')                AS total_grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')               AS total_suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')                 AS total_applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')                  AS total_inquiries,
                COUNT(*) FILTER (WHERE f.status::text = 'SUBMITTED')                       AS submitted,
                COUNT(*) FILTER (WHERE f.status::text = 'ACKNOWLEDGED')                    AS acknowledged,
                COUNT(*) FILTER (WHERE f.status::text = 'IN_REVIEW')                       AS in_review,
                COUNT(*) FILTER (WHERE f.status::text = 'ESCALATED')                       AS escalated,
                COUNT(*) FILTER (WHERE f.status::text = 'RESOLVED')                        AS resolved,
                COUNT(*) FILTER (WHERE f.status::text = 'CLOSED')                          AS closed,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                       AS dismissed,
                COUNT(*) FILTER (WHERE f.priority::text = 'CRITICAL')                      AS critical,
                COUNT(*) FILTER (WHERE f.priority::text = 'HIGH')                          AS high,
                COUNT(*) FILTER (WHERE f.priority::text = 'MEDIUM')                        AS medium,
                COUNT(*) FILTER (WHERE f.priority::text = 'LOW')                           AS low,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_days_unresolved,
                COUNT(DISTINCT f.project_id)                                                AS total_projects
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id {extra}
        """
        rows = await self._fetchall(sql, params)
        row = rows[0] if rows else {}
        row["org_id"] = str(org_id)
        return {k: (v if v is not None else (0 if isinstance(v, int) or k not in ("avg_resolution_hours","avg_days_unresolved","org_id") else v)) for k, v in row.items()}

    # ── Org-level: By Project ─────────────────────────────────────────────────

    async def get_org_by_project(
        self,
        org_id: uuid.UUID,
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        if feedback_type:
            extra += " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper()
        sql = f"""
            SELECT
                p.id                                                                        AS project_id,
                p.name                                                                      AS project_name,
                COUNT(f.id)                                                                 AS total,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')             AS grievances,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')            AS suggestions,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')              AS applause,
                COUNT(f.id) FILTER (
                    WHERE f.feedback_type::text = 'GRIEVANCE'
                      AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(f.id) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))         AS resolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours
            FROM fb_projects p
            LEFT JOIN feedbacks f ON f.project_id = p.id {extra.replace('AND f.', 'AND f.') if extra else ''}
            WHERE p.organisation_id = :org_id
            GROUP BY p.id, p.name
            ORDER BY total DESC
        """
        # Simpler approach — join then filter
        sql = f"""
            SELECT
                p.id                                                                        AS project_id,
                p.name                                                                      AS project_name,
                COUNT(f.id)                                                                 AS total,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')             AS grievances,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')            AS suggestions,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')              AS applause,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'INQUIRY')               AS inquiries,
                COUNT(f.id) FILTER (
                    WHERE f.feedback_type::text = 'GRIEVANCE'
                      AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(f.id) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))         AS resolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours
            FROM fb_projects p
            LEFT JOIN feedbacks f ON f.project_id = p.id
            WHERE p.organisation_id = :org_id {extra}
            GROUP BY p.id, p.name
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Org-level: By Period ──────────────────────────────────────────────────

    async def get_org_by_period(
        self,
        org_id: uuid.UUID,
        granularity: str = "day",
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        trunc_map = {"day": "day", "week": "week", "month": "month"}
        trunc = trunc_map.get(granularity, "day")
        fmt_map = {"day": "YYYY-MM-DD", "week": "IYYY-\"W\"IW", "month": "YYYY-MM"}
        fmt = fmt_map.get(granularity, "YYYY-MM-DD")

        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        if feedback_type:
            extra += " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper()

        sql = f"""
            SELECT
                TO_CHAR(DATE_TRUNC('{trunc}', f.submitted_at), '{fmt}') AS period,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')                AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')               AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')                 AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')                  AS inquiries
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id {extra}
            GROUP BY DATE_TRUNC('{trunc}', f.submitted_at)
            ORDER BY DATE_TRUNC('{trunc}', f.submitted_at) ASC
        """
        return await self._fetchall(sql, params)

    # ── Org-level: By Channel ─────────────────────────────────────────────────

    async def get_org_by_channel(
        self,
        org_id: uuid.UUID,
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        if feedback_type:
            extra += " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper()
        sql = f"""
            SELECT
                f.channel::text                                                             AS channel,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')                AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')               AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')                 AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')                  AS inquiries
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id {extra}
            GROUP BY f.channel
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Org-level: By Dimension (department/service/product) ─────────────────

    async def get_org_by_dimension(
        self,
        org_id: uuid.UUID,
        dimension: str,          # "department_id" | "service_id" | "product_id"
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        allowed = {"department_id", "service_id", "product_id"}
        if dimension not in allowed:
            return []
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        if feedback_type:
            extra += " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper()
        sql = f"""
            SELECT
                f.{dimension}                                                               AS dimension_id,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')                AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')               AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')                 AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')                  AS inquiries,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.{dimension} IS NOT NULL {extra}
            GROUP BY f.{dimension}
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Org-level: By Category Def ────────────────────────────────────────────

    async def get_org_by_category(
        self,
        org_id: uuid.UUID,
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        if feedback_type:
            extra += " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper()
        sql = f"""
            SELECT
                f.category_def_id,
                cd.name                                                                     AS category_name,
                cd.slug                                                                     AS category_slug,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')                AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')               AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')                 AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')                  AS inquiries,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            LEFT JOIN feedback_category_defs cd ON cd.id = f.category_def_id
            WHERE p.organisation_id = :org_id {extra}
            GROUP BY f.category_def_id, cd.name, cd.slug
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Org-level: By Location ────────────────────────────────────────────────

    async def get_org_by_location(
        self,
        org_id: uuid.UUID,
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        if feedback_type:
            extra += " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper()
        sql = f"""
            SELECT
                f.issue_lga                                                                 AS lga,
                f.issue_ward                                                                AS ward,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id {extra}
            GROUP BY f.issue_lga, f.issue_ward
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Org-level: Grievance Summary ──────────────────────────────────────────

    async def get_org_grievance_summary(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(*)                                                                    AS total_grievances,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text = 'ESCALATED')                       AS escalated,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                       AS dismissed,
                COUNT(*) FILTER (WHERE f.status::text = 'RESOLVED')                        AS resolved,
                COUNT(*) FILTER (WHERE f.status::text = 'CLOSED')                          AS closed,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_days_unresolved,
                COUNT(*) FILTER (
                    WHERE f.priority::text = 'CRITICAL'
                      AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS critical_unresolved,
                COUNT(*) FILTER (
                    WHERE f.priority::text = 'HIGH'
                      AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS high_unresolved,
                COUNT(*) FILTER (
                    WHERE f.priority::text = 'MEDIUM'
                      AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS medium_unresolved,
                COUNT(*) FILTER (
                    WHERE f.priority::text = 'LOW'
                      AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS low_unresolved
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'GRIEVANCE' {extra}
        """
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else {}

    # ── Org-level: Grievances By GRM Level ───────────────────────────────────

    async def get_org_grievances_by_level(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                f.current_level::text                                                       AS level,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'GRIEVANCE' {extra}
            GROUP BY f.current_level
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Org-level: Grievance SLA ──────────────────────────────────────────────

    async def get_org_grievance_sla(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        ACK_HOURS  = {"CRITICAL": 4,  "HIGH": 8,  "MEDIUM": 24, "LOW": 48}
        RES_HOURS  = {"CRITICAL": 72, "HIGH": 168, "MEDIUM": 336, "LOW": 720}
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                f.priority::text                                                            AS priority,
                f.acknowledged_at,
                f.resolved_at,
                f.submitted_at
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'GRIEVANCE' {extra}
        """
        rows = await self._fetchall(sql, params)

        buckets: Dict[str, Dict] = {}
        for r in rows:
            p = (r.get("priority") or "UNKNOWN").upper()
            if p not in buckets:
                buckets[p] = {"priority": p, "total": 0, "ack_met": 0, "ack_breached": 0, "res_met": 0, "res_breached": 0}
            b = buckets[p]
            b["total"] += 1
            ack_h = ACK_HOURS.get(p, 24)
            res_h = RES_HOURS.get(p, 336)
            sub = r.get("submitted_at")
            ack = r.get("acknowledged_at")
            res = r.get("resolved_at")
            if sub and ack:
                elapsed_h = (ack - sub).total_seconds() / 3600
                if elapsed_h <= ack_h: b["ack_met"] += 1
                else: b["ack_breached"] += 1
            if sub and res:
                elapsed_h = (res - sub).total_seconds() / 3600
                if elapsed_h <= res_h: b["res_met"] += 1
                else: b["res_breached"] += 1

        by_priority = []
        total_breached = 0
        total_res = 0
        total_res_met = 0
        for b in buckets.values():
            total_breached += b["res_breached"]
            total_res += b["res_met"] + b["res_breached"]
            total_res_met += b["res_met"]
            rate = round(b["res_met"] / (b["res_met"] + b["res_breached"]) * 100, 2) if (b["res_met"] + b["res_breached"]) > 0 else None
            by_priority.append({**b, "compliance_rate": rate})

        overall = round(total_res_met / total_res * 100, 2) if total_res > 0 else None
        return {"by_priority": by_priority, "total_breached": total_breached, "overall_compliance_rate": overall}

    # ── Org-level: Suggestion Summary ────────────────────────────────────────

    async def get_org_suggestion_summary(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(*)                                                                    AS total_suggestions,
                COUNT(*) FILTER (WHERE f.status::text = 'ACTIONED')                        AS actioned,
                COUNT(*) FILTER (WHERE f.status::text = 'NOTED')                           AS noted,
                COUNT(*) FILTER (WHERE f.status::text IN ('SUBMITTED','ACKNOWLEDGED'))      AS pending,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                       AS dismissed,
                ROUND(CAST(AVG(
                    CASE WHEN f.implemented_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.implemented_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_hours_to_implement
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'SUGGESTION' {extra}
        """
        rows = await self._fetchall(sql, params)
        row = dict(rows[0]) if rows else {}
        total = row.get("total_suggestions") or 0
        actioned = row.get("actioned") or 0
        row["actioned_rate"] = round(actioned / total * 100, 2) if total > 0 else None
        return row

    # ── Org-level: Suggestions By Project ────────────────────────────────────

    async def get_org_suggestions_by_project(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                p.id                                                                        AS project_id,
                p.name                                                                      AS project_name,
                COUNT(f.id)                                                                 AS total,
                COUNT(f.id) FILTER (WHERE f.status::text = 'ACTIONED')                     AS actioned,
                COUNT(f.id) FILTER (WHERE f.status::text IN ('SUBMITTED','ACKNOWLEDGED'))   AS pending,
                CASE WHEN COUNT(f.id) > 0
                     THEN ROUND(CAST(COUNT(f.id) FILTER (WHERE f.status::text = 'ACTIONED') AS NUMERIC)
                          / CAST(COUNT(f.id) AS NUMERIC) * 100.0, 2)
                     ELSE NULL END                                                          AS implementation_rate,
                ROUND(CAST(AVG(
                    CASE WHEN f.implemented_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.implemented_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_hours_to_implement
            FROM fb_projects p
            LEFT JOIN feedbacks f ON f.project_id = p.id
              AND f.feedback_type::text = 'SUGGESTION' {extra}
            WHERE p.organisation_id = :org_id
            GROUP BY p.id, p.name
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Org-level: Applause Summary ───────────────────────────────────────────

    async def get_org_applause_summary(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)

        # Total + month-on-month
        sql_counts = f"""
            SELECT
                COUNT(*)                                                                    AS total_applause,
                COUNT(*) FILTER (
                    WHERE DATE_TRUNC('month', f.submitted_at) = DATE_TRUNC('month', NOW())
                )                                                                           AS this_month,
                COUNT(*) FILTER (
                    WHERE DATE_TRUNC('month', f.submitted_at) =
                          DATE_TRUNC('month', NOW() - INTERVAL '1 month')
                )                                                                           AS last_month
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'APPLAUSE' {extra}
        """
        count_rows = await self._fetchall(sql_counts, params)
        counts = count_rows[0] if count_rows else {}

        # Top categories (category_def)
        sql_cats = f"""
            SELECT
                f.category_def_id,
                cd.name                                                                     AS category_name,
                f.category::text                                                            AS category,
                COUNT(*)                                                                    AS count
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            LEFT JOIN feedback_category_defs cd ON cd.id = f.category_def_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'APPLAUSE' {extra}
            GROUP BY f.category_def_id, cd.name, f.category
            ORDER BY count DESC
            LIMIT 10
        """
        cat_rows = await self._fetchall(sql_cats, params)

        # By project
        sql_proj = f"""
            SELECT
                p.id                                                                        AS project_id,
                p.name                                                                      AS project_name,
                COUNT(f.id)                                                                 AS count
            FROM fb_projects p
            LEFT JOIN feedbacks f ON f.project_id = p.id
              AND f.feedback_type::text = 'APPLAUSE' {extra}
            WHERE p.organisation_id = :org_id
            GROUP BY p.id, p.name
            ORDER BY count DESC
        """
        proj_rows = await self._fetchall(sql_proj, params)

        this_m  = int(counts.get("this_month") or 0)
        last_m  = int(counts.get("last_month") or 0)
        mom = round((this_m - last_m) / last_m * 100, 2) if last_m > 0 else None

        return {
            "total_applause": int(counts.get("total_applause") or 0),
            "this_month":     this_m,
            "last_month":     last_m,
            "mom_change":     mom,
            "top_categories": [
                {"category_def_id": r.get("category_def_id"), "category_name": r.get("category_name"), "category": r.get("category"), "count": int(r.get("count",0))}
                for r in cat_rows
            ],
            "by_project": [
                {"project_id": r["project_id"], "project_name": r.get("project_name"), "count": int(r.get("count",0))}
                for r in proj_rows
            ],
        }

    # ── Platform-level: Summary ─────────────────────────────────────────────

    async def get_platform_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(DISTINCT p.organisation_id)                                               AS total_orgs,
                COUNT(DISTINCT p.id)                                                            AS total_projects,
                COUNT(f.id)                                                                     AS total_feedback,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')                 AS total_grievances,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')                AS total_suggestions,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')                  AS total_applause,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'INQUIRY')                   AS total_inquiries,
                COUNT(f.id) FILTER (WHERE f.status::text = 'SUBMITTED')                        AS submitted,
                COUNT(f.id) FILTER (WHERE f.status::text = 'ACKNOWLEDGED')                     AS acknowledged,
                COUNT(f.id) FILTER (WHERE f.status::text = 'IN_REVIEW')                        AS in_review,
                COUNT(f.id) FILTER (WHERE f.status::text = 'ESCALATED')                        AS escalated,
                COUNT(f.id) FILTER (WHERE f.status::text = 'RESOLVED')                         AS resolved,
                COUNT(f.id) FILTER (WHERE f.status::text = 'CLOSED')                           AS closed,
                COUNT(f.id) FILTER (WHERE f.status::text = 'DISMISSED')                        AS dismissed,
                COUNT(f.id) FILTER (WHERE f.priority::text = 'CRITICAL')                       AS critical,
                COUNT(f.id) FILTER (WHERE f.priority::text = 'HIGH')                           AS high,
                COUNT(f.id) FILTER (WHERE f.priority::text = 'MEDIUM')                         AS medium,
                COUNT(f.id) FILTER (WHERE f.priority::text = 'LOW')                            AS low,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                               AS avg_resolution_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                               AS avg_days_unresolved
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE 1=1 {extra}
        """
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else {}

    # ── Platform-level: By Org ──────────────────────────────────────────────

    async def get_platform_by_org(
        self,
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        extra = self._org_date_clauses(params, date_from, date_to)
        if feedback_type:
            extra += " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper()
        sql = f"""
            SELECT
                p.organisation_id,
                MAX(p.org_display_name)                                                         AS org_name,
                COUNT(DISTINCT p.id)                                                            AS total_projects,
                COUNT(f.id)                                                                     AS total,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')                 AS grievances,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')                AS suggestions,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')                  AS applause,
                COUNT(f.id) FILTER (WHERE f.feedback_type::text = 'INQUIRY')                   AS inquiries,
                COUNT(f.id) FILTER (
                    WHERE f.feedback_type::text = 'GRIEVANCE'
                      AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                               AS unresolved,
                COUNT(f.id) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))             AS resolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                               AS avg_resolution_hours
            FROM fb_projects p
            LEFT JOIN feedbacks f ON f.project_id = p.id {extra}
            GROUP BY p.organisation_id
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Project/Org name resolution (for AI context enrichment) ───────────────

    async def get_project_profile(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """
        Returns human-readable project identity from fb_projects.
        Used to enrich AI context with names instead of raw UUIDs.
        """
        rows = await self._fetchall(
            """
            SELECT
                id, name, slug, status, category, sector, description,
                country_code, region, primary_lga,
                start_date, end_date,
                organisation_id, org_display_name,
                accepts_grievances, accepts_suggestions, accepts_applause
            FROM fb_projects
            WHERE id = :project_id
            """,
            {"project_id": str(project_id)},
        )
        return rows[0] if rows else {}

    async def get_org_name(self, org_id: uuid.UUID) -> Optional[str]:
        """
        Returns the cached org display_name from fb_projects.
        Returns None if no projects exist yet or name hasn't been synced.
        """
        rows = await self._fetchall(
            """
            SELECT org_display_name
            FROM fb_projects
            WHERE organisation_id = :org_id
              AND org_display_name IS NOT NULL
            LIMIT 1
            """,
            {"org_id": str(org_id)},
        )
        return rows[0]["org_display_name"] if rows else None

    # ── Platform-level: By Period ───────────────────────────────────────────

    async def get_platform_by_period(
        self,
        granularity: str = "day",
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        trunc_map = {"day": "day", "week": "week", "month": "month"}
        trunc = trunc_map.get(granularity, "day")
        fmt_map = {"day": "YYYY-MM-DD", "week": "IYYY-\"W\"IW", "month": "YYYY-MM"}
        fmt = fmt_map.get(granularity, "YYYY-MM-DD")

        params: Dict[str, Any] = {}
        extra = self._org_date_clauses(params, date_from, date_to)
        if feedback_type:
            extra += " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper()

        sql = f"""
            SELECT
                TO_CHAR(DATE_TRUNC('{trunc}', f.submitted_at), '{fmt}') AS period,
                COUNT(*)                                                                        AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')                    AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')                   AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')                     AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')                      AS inquiries
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE 1=1 {extra}
            GROUP BY DATE_TRUNC('{trunc}', f.submitted_at)
            ORDER BY DATE_TRUNC('{trunc}', f.submitted_at) ASC
        """
        return await self._fetchall(sql, params)

    # ── Platform-level: By Channel ──────────────────────────────────────────

    async def get_platform_by_channel(
        self,
        feedback_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        extra = self._org_date_clauses(params, date_from, date_to)
        if feedback_type:
            extra += " AND f.feedback_type::text = :feedback_type"
            params["feedback_type"] = feedback_type.upper()
        sql = f"""
            SELECT
                f.channel::text                                                                 AS channel,
                COUNT(*)                                                                        AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')                    AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')                   AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')                     AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')                      AS inquiries
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE 1=1 {extra}
            GROUP BY f.channel
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Platform-level: Grievance Summary ────────────────────────────────────

    async def get_platform_grievance_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(*)                                                                        AS total_grievances,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                               AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text = 'ESCALATED')                           AS escalated,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                           AS dismissed,
                COUNT(*) FILTER (WHERE f.status::text = 'RESOLVED')                            AS resolved,
                COUNT(*) FILTER (WHERE f.status::text = 'CLOSED')                              AS closed,
                COUNT(*) FILTER (WHERE f.priority::text = 'CRITICAL'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))               AS critical_unresolved,
                COUNT(*) FILTER (WHERE f.priority::text = 'HIGH'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))               AS high_unresolved,
                COUNT(*) FILTER (WHERE f.priority::text = 'MEDIUM'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))               AS medium_unresolved,
                COUNT(*) FILTER (WHERE f.priority::text = 'LOW'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))               AS low_unresolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                               AS avg_resolution_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                               AS avg_days_unresolved
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'GRIEVANCE' {extra}
        """
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else {}

    # ── Platform-level: Grievance SLA ────────────────────────────────────────

    async def get_platform_grievance_sla(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        """SLA compliance across all organisations — computed in Python same as org-level."""
        ACK_HOURS  = {"CRITICAL": 4,  "HIGH": 8,  "MEDIUM": 24, "LOW": 48}
        RES_HOURS  = {"CRITICAL": 72, "HIGH": 168, "MEDIUM": 336, "LOW": 720}
        params: Dict[str, Any] = {}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                f.priority::text                                                                AS priority,
                f.acknowledged_at,
                f.resolved_at,
                f.submitted_at
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'GRIEVANCE' {extra}
        """
        rows = await self._fetchall(sql, params)

        buckets: Dict[str, Dict] = {}
        for r in rows:
            p = (r.get("priority") or "UNKNOWN").upper()
            if p not in buckets:
                buckets[p] = {"priority": p, "total": 0, "ack_met": 0, "ack_breached": 0, "res_met": 0, "res_breached": 0}
            b = buckets[p]
            b["total"] += 1
            ack_h = ACK_HOURS.get(p, 24)
            res_h = RES_HOURS.get(p, 336)
            sub = r.get("submitted_at")
            ack = r.get("acknowledged_at")
            res = r.get("resolved_at")
            if sub and ack:
                elapsed_h = (ack - sub).total_seconds() / 3600
                if elapsed_h <= ack_h: b["ack_met"] += 1
                else: b["ack_breached"] += 1
            if sub and res:
                elapsed_h = (res - sub).total_seconds() / 3600
                if elapsed_h <= res_h: b["res_met"] += 1
                else: b["res_breached"] += 1

        by_priority = []
        total_breached = 0
        total_res = 0
        total_res_met = 0
        for b in buckets.values():
            total_breached += b["res_breached"]
            total_res += b["res_met"] + b["res_breached"]
            total_res_met += b["res_met"]
            rate = round(b["res_met"] / (b["res_met"] + b["res_breached"]) * 100, 2) if (b["res_met"] + b["res_breached"]) > 0 else None
            by_priority.append({**b, "compliance_rate": rate})

        overall = round(total_res_met / total_res * 100, 2) if total_res > 0 else None
        return {"by_priority": by_priority, "total_breached": total_breached, "overall_compliance_rate": overall}

    # ── Platform-level: Suggestion Summary ───────────────────────────────────

    async def get_platform_suggestion_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(*)                                                                        AS total_suggestions,
                COUNT(*) FILTER (WHERE f.status::text = 'ACTIONED')                            AS actioned,
                COUNT(*) FILTER (WHERE f.status::text = 'NOTED')                               AS noted,
                COUNT(*) FILTER (WHERE f.status::text IN ('SUBMITTED','ACKNOWLEDGED'))          AS pending,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                           AS dismissed,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL AND f.status::text = 'ACTIONED'
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                               AS avg_hours_to_implement
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'SUGGESTION' {extra}
        """
        rows = await self._fetchall(sql, params)
        row = dict(rows[0]) if rows else {}
        total = row.get("total_suggestions") or 0
        actioned = row.get("actioned") or 0
        row["actioned_rate"] = round(actioned / total * 100, 2) if total > 0 else None
        return row

    # ── Platform-level: Applause Summary ─────────────────────────────────────

    async def get_platform_applause_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        extra = self._org_date_clauses(params, date_from, date_to)

        sql_counts = f"""
            SELECT
                COUNT(*)                                                                        AS total_applause,
                COUNT(*) FILTER (
                    WHERE DATE_TRUNC('month', f.submitted_at) = DATE_TRUNC('month', NOW())
                )                                                                               AS this_month,
                COUNT(*) FILTER (
                    WHERE DATE_TRUNC('month', f.submitted_at) =
                          DATE_TRUNC('month', NOW() - INTERVAL '1 month')
                )                                                                               AS last_month
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'APPLAUSE' {extra}
        """
        count_rows = await self._fetchall(sql_counts, params)
        counts = count_rows[0] if count_rows else {}

        sql_cats = f"""
            SELECT
                f.category_def_id,
                cd.name                                                                         AS category_name,
                f.category::text                                                                AS category,
                COUNT(*)                                                                        AS count
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            LEFT JOIN feedback_category_defs cd ON cd.id = f.category_def_id
            WHERE f.feedback_type::text = 'APPLAUSE' {extra}
            GROUP BY f.category_def_id, cd.name, f.category
            ORDER BY count DESC
            LIMIT 10
        """
        cat_rows = await self._fetchall(sql_cats, params)

        sql_orgs = f"""
            SELECT
                p.organisation_id,
                COUNT(f.id)                                                                     AS count
            FROM fb_projects p
            LEFT JOIN feedbacks f ON f.project_id = p.id
              AND f.feedback_type::text = 'APPLAUSE' {extra}
            GROUP BY p.organisation_id
            ORDER BY count DESC
        """
        org_rows = await self._fetchall(sql_orgs, params)

        this_m = int(counts.get("this_month") or 0)
        last_m = int(counts.get("last_month") or 0)
        mom = round((this_m - last_m) / last_m * 100, 2) if last_m > 0 else None

        return {
            "total_applause": int(counts.get("total_applause") or 0),
            "this_month":     this_m,
            "last_month":     last_m,
            "mom_change":     mom,
            "top_categories": [
                {"category_def_id": r.get("category_def_id"), "category_name": r.get("category_name"), "category": r.get("category"), "count": int(r.get("count", 0))}
                for r in cat_rows
            ],
            "by_org": [
                {"organisation_id": r["organisation_id"], "count": int(r.get("count", 0))}
                for r in org_rows
            ],
        }

    # ── Inquiry: Project-level Summary ───────────────────────────────────────

    async def get_inquiry_summary(
        self,
        project_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses = []
        if date_from:
            extra_clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            extra_clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                COUNT(*)                                                                    AS total_inquiries,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS open_inquiries,
                COUNT(*) FILTER (WHERE f.status::text = 'RESOLVED')                        AS resolved,
                COUNT(*) FILTER (WHERE f.status::text = 'CLOSED')                          AS closed,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                       AS dismissed,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_response_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_days_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'CRITICAL'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS critical_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'HIGH'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS high_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'MEDIUM'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS medium_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'LOW'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS low_open
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'INQUIRY' {extra}
        """
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else {}

    async def get_inquiry_unread(
        self,
        project_id: uuid.UUID,
        priority: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        service_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        category_def_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses: List[str] = []
        if priority:
            extra_clauses.append("f.priority::text = :priority")
            params["priority"] = priority.upper()
        if department_id:
            extra_clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if service_id:
            extra_clauses.append("f.service_id = :service_id")
            params["service_id"] = str(service_id)
        if product_id:
            extra_clauses.append("f.product_id = :product_id")
            params["product_id"] = str(product_id)
        if category_def_id:
            extra_clauses.append("f.category_def_id = :category_def_id")
            params["category_def_id"] = str(category_def_id)
        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.id              AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.submitted_at,
                EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0 AS days_waiting,
                f.channel::text,
                f.issue_lga,
                f.department_id,
                f.service_id,
                f.product_id,
                f.category_def_id
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'INQUIRY'
              AND f.status::text = 'SUBMITTED'
              {extra}
            ORDER BY f.submitted_at ASC
        """
        return await self._fetchall(sql, params)

    async def get_inquiry_overdue(
        self,
        project_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        service_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        category_def_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses: List[str] = []
        if department_id:
            extra_clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if service_id:
            extra_clauses.append("f.service_id = :service_id")
            params["service_id"] = str(service_id)
        if product_id:
            extra_clauses.append("f.product_id = :product_id")
            params["product_id"] = str(product_id)
        if category_def_id:
            extra_clauses.append("f.category_def_id = :category_def_id")
            params["category_def_id"] = str(category_def_id)
        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.id                      AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.status::text,
                f.submitted_at,
                f.target_resolution_date,
                EXTRACT(EPOCH FROM (NOW() - f.target_resolution_date)) / 86400.0 AS days_overdue,
                f.assigned_to_user_id,
                f.department_id,
                f.service_id,
                f.product_id,
                f.category_def_id
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'INQUIRY'
              AND f.status::text IN ('ACKNOWLEDGED','IN_REVIEW')
              AND f.target_resolution_date < NOW()
              {extra}
            ORDER BY f.target_resolution_date ASC
        """
        return await self._fetchall(sql, params)

    async def get_inquiry_by_channel(
        self,
        project_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses: List[str] = []
        if date_from:
            extra_clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            extra_clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.channel::text                                                             AS channel,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS open_count,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'INQUIRY' {extra}
            GROUP BY f.channel
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    async def get_inquiry_by_category(
        self,
        project_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra_clauses: List[str] = []
        if date_from:
            extra_clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            extra_clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        extra = ("AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.category_def_id,
                cd.name                                                                     AS category_name,
                cd.slug                                                                     AS category_slug,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS open_count,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_response_hours
            FROM feedbacks f
            LEFT JOIN feedback_category_defs cd ON cd.id = f.category_def_id
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'INQUIRY' {extra}
            GROUP BY f.category_def_id, cd.name, cd.slug
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    # ── Inquiry: Org-level Summary ────────────────────────────────────────────

    async def get_org_inquiry_summary(
        self,
        org_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(*)                                                                    AS total_inquiries,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS open_inquiries,
                COUNT(*) FILTER (WHERE f.status::text = 'RESOLVED')                        AS resolved,
                COUNT(*) FILTER (WHERE f.status::text = 'CLOSED')                          AS closed,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                       AS dismissed,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_response_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_days_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'CRITICAL'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS critical_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'HIGH'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS high_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'MEDIUM'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS medium_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'LOW'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS low_open
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'INQUIRY' {extra}
        """
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else {}

    # ── Inquiry: Platform-level Summary ──────────────────────────────────────

    async def get_platform_inquiry_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        extra = self._org_date_clauses(params, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(*)                                                                    AS total_inquiries,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS open_inquiries,
                COUNT(*) FILTER (WHERE f.status::text = 'RESOLVED')                        AS resolved,
                COUNT(*) FILTER (WHERE f.status::text = 'CLOSED')                          AS closed,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                       AS dismissed,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_response_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_days_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'CRITICAL'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS critical_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'HIGH'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS high_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'MEDIUM'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS medium_open,
                COUNT(*) FILTER (WHERE f.priority::text = 'LOW'
                    AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED'))           AS low_open
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'INQUIRY' {extra}
        """
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else {}

    # ── Grievance Dashboard: Project scope ───────────────────────────────────

    def _proj_grievance_filters(
        self,
        params: Dict[str, Any],
        department_id: Optional[uuid.UUID],
        status: Optional[str],
        priority: Optional[str],
        date_from: Optional[date],
        date_to: Optional[date],
    ) -> str:
        clauses = []
        if department_id:
            clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if status:
            clauses.append("f.status::text = :status")
            params["status"] = status.upper()
        if priority:
            clauses.append("f.priority::text = :priority")
            params["priority"] = priority.upper()
        if date_from:
            clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        return (" AND " + " AND ".join(clauses)) if clauses else ""

    async def get_project_grievance_dashboard_summary(
        self,
        project_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra = self._proj_grievance_filters(params, department_id, status, priority, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(*)                                                                    AS total_grievances,
                COUNT(*) FILTER (WHERE f.status::text = 'RESOLVED')                        AS resolved,
                COUNT(*) FILTER (WHERE f.status::text = 'CLOSED')                          AS closed,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text = 'ESCALATED')                       AS escalated,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                       AS dismissed,
                COUNT(*) FILTER (WHERE f.acknowledged_at IS NOT NULL)                      AS acknowledged_count,
                COUNT(*) FILTER (
                    WHERE f.resolved_at IS NOT NULL
                      AND f.target_resolution_date IS NOT NULL
                      AND f.resolved_at <= f.target_resolution_date
                )                                                                           AS resolved_on_time,
                COUNT(*) FILTER (
                    WHERE f.resolved_at IS NOT NULL
                      AND f.target_resolution_date IS NOT NULL
                      AND f.resolved_at > f.target_resolution_date
                )                                                                           AS resolved_late,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_days_unresolved
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
        """
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else {}

    async def get_project_grievance_by_priority(
        self,
        project_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra = self._proj_grievance_filters(params, department_id, status, None, date_from, date_to)
        sql = f"""
            SELECT
                f.priority::text                                                            AS priority,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
            GROUP BY f.priority
            ORDER BY f.priority
        """
        return await self._fetchall(sql, params)

    async def get_project_grievance_by_dept(
        self,
        project_id: uuid.UUID,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra = self._proj_grievance_filters(params, None, status, priority, date_from, date_to)
        sql = f"""
            SELECT
                f.department_id,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
            GROUP BY f.department_id
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    async def get_project_grievance_by_stage(
        self,
        project_id: uuid.UUID,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra = self._proj_grievance_filters(params, None, status, priority, date_from, date_to)
        sql = f"""
            SELECT
                s.id                                                                        AS stage_id,
                s.name                                                                      AS stage_name,
                s.stage_order,
                COUNT(f.id)                                                                 AS total,
                COUNT(f.id) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(f.id) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))         AS resolved
            FROM fb_project_stages s
            LEFT JOIN feedbacks f ON f.stage_id = s.id
              AND f.feedback_type::text = 'GRIEVANCE' {extra}
            WHERE s.project_id = :project_id
            GROUP BY s.id, s.name, s.stage_order
            ORDER BY s.stage_order
        """
        return await self._fetchall(sql, params)

    async def get_project_grievance_overdue(
        self,
        project_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        priority: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"project_id": str(project_id), "limit": limit}
        extra_clauses = []
        if department_id:
            extra_clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if priority:
            extra_clauses.append("f.priority::text = :priority")
            params["priority"] = priority.upper()
        extra = (" AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.id                                                AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.status::text,
                f.submitted_at,
                f.target_resolution_date,
                EXTRACT(EPOCH FROM (NOW() - f.target_resolution_date)) / 86400.0
                                                                    AS days_overdue,
                f.department_id,
                f.assigned_to_user_id,
                f.assigned_committee_id                             AS committee_id,
                f.issue_lga
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'GRIEVANCE'
              AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
              AND f.target_resolution_date IS NOT NULL
              AND f.target_resolution_date < NOW()
              {extra}
            ORDER BY f.target_resolution_date ASC
            LIMIT :limit
        """
        return await self._fetchall(sql, params)

    async def get_project_grievance_list(
        self,
        project_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"project_id": str(project_id)}
        extra = self._proj_grievance_filters(params, department_id, status, priority, date_from, date_to)
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
        """
        count_rows = await self._fetchall(count_sql, params)
        total = int(count_rows[0]["total"]) if count_rows else 0

        offset = (page - 1) * page_size
        params["page_size"] = page_size
        params["offset"] = offset
        sql = f"""
            SELECT
                f.id                                                AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.status::text,
                f.category::text,
                f.submitted_at,
                f.resolved_at,
                f.acknowledged_at,
                f.target_resolution_date,
                EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                                                                    AS days_unresolved,
                f.department_id,
                f.service_id,
                f.product_id,
                f.category_def_id,
                f.issue_lga,
                f.issue_ward,
                f.assigned_to_user_id,
                f.assigned_committee_id                             AS committee_id,
                f.stage_id,
                f.project_id
            FROM feedbacks f
            WHERE f.project_id = :project_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
            ORDER BY f.submitted_at DESC
            LIMIT :page_size OFFSET :offset
        """
        items = await self._fetchall(sql, params)
        return {"total": total, "items": items}

    # ── Grievance Dashboard: Org scope ────────────────────────────────────────

    def _org_grievance_filters(
        self,
        params: Dict[str, Any],
        department_id: Optional[uuid.UUID],
        status: Optional[str],
        priority: Optional[str],
        date_from: Optional[date],
        date_to: Optional[date],
        project_id: Optional[uuid.UUID] = None,
    ) -> str:
        clauses = []
        if project_id:
            clauses.append("f.project_id = :filter_project_id")
            params["filter_project_id"] = str(project_id)
        if department_id:
            clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if status:
            clauses.append("f.status::text = :status")
            params["status"] = status.upper()
        if priority:
            clauses.append("f.priority::text = :priority")
            params["priority"] = priority.upper()
        if date_from:
            clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        return (" AND " + " AND ".join(clauses)) if clauses else ""

    async def get_org_grievance_dashboard_summary(
        self,
        org_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_grievance_filters(params, department_id, status, priority, date_from, date_to, project_id)
        sql = f"""
            SELECT
                COUNT(*)                                                                    AS total_grievances,
                COUNT(*) FILTER (WHERE f.status::text = 'RESOLVED')                        AS resolved,
                COUNT(*) FILTER (WHERE f.status::text = 'CLOSED')                          AS closed,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text = 'ESCALATED')                       AS escalated,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                       AS dismissed,
                COUNT(*) FILTER (WHERE f.acknowledged_at IS NOT NULL)                      AS acknowledged_count,
                COUNT(*) FILTER (
                    WHERE f.resolved_at IS NOT NULL
                      AND f.target_resolution_date IS NOT NULL
                      AND f.resolved_at <= f.target_resolution_date
                )                                                                           AS resolved_on_time,
                COUNT(*) FILTER (
                    WHERE f.resolved_at IS NOT NULL
                      AND f.target_resolution_date IS NOT NULL
                      AND f.resolved_at > f.target_resolution_date
                )                                                                           AS resolved_late,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_days_unresolved
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
        """
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else {}

    async def get_org_grievance_by_priority(
        self,
        org_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_grievance_filters(params, department_id, status, None, date_from, date_to, project_id)
        sql = f"""
            SELECT
                f.priority::text                                                            AS priority,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
            GROUP BY f.priority
            ORDER BY f.priority
        """
        return await self._fetchall(sql, params)

    async def get_org_grievance_by_dept(
        self,
        org_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_grievance_filters(params, None, status, priority, date_from, date_to, project_id)
        sql = f"""
            SELECT
                f.department_id,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
            GROUP BY f.department_id
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    async def get_org_grievance_by_project(
        self,
        org_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_grievance_filters(params, department_id, status, priority, date_from, date_to)
        sql = f"""
            SELECT
                p.id                                                                        AS project_id,
                p.name                                                                      AS project_name,
                COUNT(f.id)                                                                 AS total,
                COUNT(f.id) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(f.id) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))         AS resolved
            FROM fb_projects p
            LEFT JOIN feedbacks f ON f.project_id = p.id
              AND f.feedback_type::text = 'GRIEVANCE' {extra}
            WHERE p.organisation_id = :org_id
            GROUP BY p.id, p.name
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    async def get_org_grievance_overdue(
        self,
        org_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        priority: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"org_id": str(org_id), "limit": limit}
        extra_clauses = []
        if project_id:
            extra_clauses.append("f.project_id = :filter_project_id")
            params["filter_project_id"] = str(project_id)
        if department_id:
            extra_clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if priority:
            extra_clauses.append("f.priority::text = :priority")
            params["priority"] = priority.upper()
        extra = (" AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.id                                                AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.status::text,
                f.submitted_at,
                f.target_resolution_date,
                EXTRACT(EPOCH FROM (NOW() - f.target_resolution_date)) / 86400.0
                                                                    AS days_overdue,
                f.department_id,
                f.assigned_to_user_id,
                f.assigned_committee_id                             AS committee_id,
                f.issue_lga
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'GRIEVANCE'
              AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
              AND f.target_resolution_date IS NOT NULL
              AND f.target_resolution_date < NOW()
              {extra}
            ORDER BY f.target_resolution_date ASC
            LIMIT :limit
        """
        return await self._fetchall(sql, params)

    async def get_org_grievance_list(
        self,
        org_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"org_id": str(org_id)}
        extra = self._org_grievance_filters(params, department_id, status, priority, date_from, date_to, project_id)
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
        """
        count_rows = await self._fetchall(count_sql, params)
        total = int(count_rows[0]["total"]) if count_rows else 0

        offset = (page - 1) * page_size
        params["page_size"] = page_size
        params["offset"] = offset
        sql = f"""
            SELECT
                f.id                                                AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.status::text,
                f.category::text,
                f.submitted_at,
                f.resolved_at,
                f.acknowledged_at,
                f.target_resolution_date,
                EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                                                                    AS days_unresolved,
                f.department_id,
                f.service_id,
                f.product_id,
                f.category_def_id,
                f.issue_lga,
                f.issue_ward,
                f.assigned_to_user_id,
                f.assigned_committee_id                             AS committee_id,
                f.stage_id,
                f.project_id
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE p.organisation_id = :org_id
              AND f.feedback_type::text = 'GRIEVANCE'
              {extra}
            ORDER BY f.submitted_at DESC
            LIMIT :page_size OFFSET :offset
        """
        items = await self._fetchall(sql, params)
        return {"total": total, "items": items}

    # ── Grievance Dashboard: Platform scope ───────────────────────────────────

    def _platform_grievance_filters(
        self,
        params: Dict[str, Any],
        org_id: Optional[uuid.UUID],
        project_id: Optional[uuid.UUID],
        department_id: Optional[uuid.UUID],
        status: Optional[str],
        priority: Optional[str],
        date_from: Optional[date],
        date_to: Optional[date],
    ) -> str:
        clauses = []
        if org_id:
            clauses.append("p.organisation_id = :filter_org_id")
            params["filter_org_id"] = str(org_id)
        if project_id:
            clauses.append("f.project_id = :filter_project_id")
            params["filter_project_id"] = str(project_id)
        if department_id:
            clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if status:
            clauses.append("f.status::text = :status")
            params["status"] = status.upper()
        if priority:
            clauses.append("f.priority::text = :priority")
            params["priority"] = priority.upper()
        if date_from:
            clauses.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            clauses.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        return (" AND " + " AND ".join(clauses)) if clauses else ""

    async def get_platform_grievance_dashboard_summary(
        self,
        org_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        extra = self._platform_grievance_filters(params, org_id, project_id, department_id, status, priority, date_from, date_to)
        sql = f"""
            SELECT
                COUNT(*)                                                                    AS total_grievances,
                COUNT(*) FILTER (WHERE f.status::text = 'RESOLVED')                        AS resolved,
                COUNT(*) FILTER (WHERE f.status::text = 'CLOSED')                          AS closed,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text = 'ESCALATED')                       AS escalated,
                COUNT(*) FILTER (WHERE f.status::text = 'DISMISSED')                       AS dismissed,
                COUNT(*) FILTER (WHERE f.acknowledged_at IS NOT NULL)                      AS acknowledged_count,
                COUNT(*) FILTER (
                    WHERE f.resolved_at IS NOT NULL
                      AND f.target_resolution_date IS NOT NULL
                      AND f.resolved_at <= f.target_resolution_date
                )                                                                           AS resolved_on_time,
                COUNT(*) FILTER (
                    WHERE f.resolved_at IS NOT NULL
                      AND f.target_resolution_date IS NOT NULL
                      AND f.resolved_at > f.target_resolution_date
                )                                                                           AS resolved_late,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours,
                ROUND(CAST(AVG(
                    CASE WHEN f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                    THEN EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_days_unresolved
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'GRIEVANCE'
              {extra}
        """
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else {}

    async def get_platform_grievance_by_priority(
        self,
        org_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        extra = self._platform_grievance_filters(params, org_id, project_id, department_id, status, None, date_from, date_to)
        sql = f"""
            SELECT
                f.priority::text                                                            AS priority,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'GRIEVANCE'
              {extra}
            GROUP BY f.priority
            ORDER BY f.priority
        """
        return await self._fetchall(sql, params)

    async def get_platform_grievance_by_dept(
        self,
        org_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        extra = self._platform_grievance_filters(params, org_id, project_id, None, status, priority, date_from, date_to)
        sql = f"""
            SELECT
                f.department_id,
                COUNT(*)                                                                    AS total,
                COUNT(*) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))            AS resolved,
                ROUND(CAST(AVG(
                    CASE WHEN f.resolved_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                    ELSE NULL END
                ) AS NUMERIC), 2)                                                           AS avg_resolution_hours
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'GRIEVANCE'
              {extra}
            GROUP BY f.department_id
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    async def get_platform_grievance_by_org(
        self,
        project_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        extra = self._platform_grievance_filters(params, None, project_id, department_id, status, priority, date_from, date_to)
        sql = f"""
            SELECT
                p.organisation_id,
                MAX(p.org_display_name)                                                     AS org_name,
                COUNT(f.id)                                                                 AS total,
                COUNT(f.id) FILTER (
                    WHERE f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                           AS unresolved,
                COUNT(f.id) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))         AS resolved
            FROM fb_projects p
            LEFT JOIN feedbacks f ON f.project_id = p.id
              AND f.feedback_type::text = 'GRIEVANCE' {extra}
            GROUP BY p.organisation_id
            ORDER BY total DESC
        """
        return await self._fetchall(sql, params)

    async def get_platform_grievance_overdue(
        self,
        org_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        priority: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        extra_clauses = []
        if org_id:
            extra_clauses.append("p.organisation_id = :filter_org_id")
            params["filter_org_id"] = str(org_id)
        if project_id:
            extra_clauses.append("f.project_id = :filter_project_id")
            params["filter_project_id"] = str(project_id)
        if department_id:
            extra_clauses.append("f.department_id = :department_id")
            params["department_id"] = str(department_id)
        if priority:
            extra_clauses.append("f.priority::text = :priority")
            params["priority"] = priority.upper()
        extra = (" AND " + " AND ".join(extra_clauses)) if extra_clauses else ""
        sql = f"""
            SELECT
                f.id                                                AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.status::text,
                f.submitted_at,
                f.target_resolution_date,
                EXTRACT(EPOCH FROM (NOW() - f.target_resolution_date)) / 86400.0
                                                                    AS days_overdue,
                f.department_id,
                f.assigned_to_user_id,
                f.assigned_committee_id                             AS committee_id,
                f.issue_lga
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'GRIEVANCE'
              AND f.status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
              AND f.target_resolution_date IS NOT NULL
              AND f.target_resolution_date < NOW()
              {extra}
            ORDER BY f.target_resolution_date ASC
            LIMIT :limit
        """
        return await self._fetchall(sql, params)

    async def get_platform_grievance_list(
        self,
        org_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        extra = self._platform_grievance_filters(params, org_id, project_id, department_id, status, priority, date_from, date_to)
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'GRIEVANCE'
              {extra}
        """
        count_rows = await self._fetchall(count_sql, params)
        total = int(count_rows[0]["total"]) if count_rows else 0

        offset = (page - 1) * page_size
        params["page_size"] = page_size
        params["offset"] = offset
        sql = f"""
            SELECT
                f.id                                                AS feedback_id,
                f.unique_ref,
                f.priority::text,
                f.status::text,
                f.category::text,
                f.submitted_at,
                f.resolved_at,
                f.acknowledged_at,
                f.target_resolution_date,
                EXTRACT(EPOCH FROM (NOW() - f.submitted_at)) / 86400.0
                                                                    AS days_unresolved,
                f.department_id,
                f.service_id,
                f.product_id,
                f.category_def_id,
                f.issue_lga,
                f.issue_ward,
                f.assigned_to_user_id,
                f.assigned_committee_id                             AS committee_id,
                f.stage_id,
                f.project_id
            FROM feedbacks f
            JOIN fb_projects p ON p.id = f.project_id
            WHERE f.feedback_type::text = 'GRIEVANCE'
              {extra}
            ORDER BY f.submitted_at DESC
            LIMIT :page_size OFFSET :offset
        """
        items = await self._fetchall(sql, params)
        return {"total": total, "items": items}

    # ── Internal helper ───────────────────────────────────────────────────────

    def _org_date_clauses(
        self,
        params: Dict[str, Any],
        date_from: Optional[date],
        date_to: Optional[date],
    ) -> str:
        clauses = ""
        if date_from:
            clauses += " AND f.submitted_at >= :date_from"
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            clauses += " AND f.submitted_at < :date_to"
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        return clauses

    # ── Notification stats placeholder ───────────────────────────────────────

    async def get_notification_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Placeholder: notification_service does not expose its DB directly.
        Returns a dict with zero values — call notification_service API if needed.
        """
        log.info(
            "analytics.notification_stats.placeholder",
            user_id=str(user_id),
            note="notification_service DB is not accessible cross-service; returning zeros.",
        )
        return {
            "user_id": str(user_id),
            "unread_notifications": 0,
            "total_sent_7d": 0,
            "total_failed_7d": 0,
            "note": "Live data requires calling notification_service /api/v1/notifications endpoint.",
        }

    # ── Summary counts for AI context ────────────────────────────────────────

    async def get_summary_counts(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """
        Quick aggregate counts used to build AI insight context.
        """
        sql = """
            SELECT
                COUNT(*) FILTER (WHERE feedback_type::text='GRIEVANCE')                   AS total_grievances,
                COUNT(*) FILTER (WHERE feedback_type::text='SUGGESTION')                  AS total_suggestions,
                COUNT(*) FILTER (WHERE feedback_type::text='APPLAUSE')                    AS total_applause,
                COUNT(*) FILTER (WHERE feedback_type::text='INQUIRY')                     AS total_inquiries,
                COUNT(*) FILTER (WHERE status::text='SUBMITTED')                          AS unread_count,
                COUNT(*) FILTER (
                    WHERE status::text IN ('ACKNOWLEDGED','IN_REVIEW')
                      AND target_resolution_date IS NOT NULL
                      AND target_resolution_date < NOW()
                )                                                                         AS overdue_count,
                COUNT(*) FILTER (
                    WHERE feedback_type::text='GRIEVANCE'
                      AND status::text NOT IN ('RESOLVED','CLOSED','DISMISSED')
                )                                                                         AS unresolved_grievances,
                ROUND(CAST(
                    AVG(
                        CASE WHEN resolved_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (resolved_at - submitted_at)) / 3600.0
                        ELSE NULL END
                    ) AS NUMERIC
                ), 2)                                                                     AS avg_resolution_hours,
                MODE() WITHIN GROUP (ORDER BY category::text)                             AS top_category
            FROM feedbacks
            WHERE project_id = :project_id
        """
        rows = await self._fetchall(sql, {"project_id": str(project_id)})
        return rows[0] if rows else {}
