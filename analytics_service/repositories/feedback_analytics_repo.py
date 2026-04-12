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
    ) -> List[Dict[str, Any]]:
        """
        status IN ('acknowledged','in_review') AND target_resolution_date < NOW()
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
                EXTRACT(EPOCH FROM (NOW() - f.target_resolution_date)) / 86400.0 AS days_overdue,
                f.assigned_to_user_id,
                f.assigned_committee_id   AS committee_id
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
                f.issue_ward
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
