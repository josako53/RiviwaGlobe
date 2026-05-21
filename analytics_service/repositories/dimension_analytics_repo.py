"""
repositories/dimension_analytics_repo.py
────────────────────────────────────────────────────────────────────────────
Analytics queries scoped to a single entity: product, service, branch, or
department.  All queries run against feedback_db using raw SQL.

Dimensions
──────────
  product    → feedbacks.product_id
  service    → feedbacks.service_id
  branch     → feedbacks.branch_id
  department → feedbacks.department_id
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

# Safe column map — never use user-supplied strings as column names directly
_DIM_COL: Dict[str, str] = {
    "product":    "product_id",
    "service":    "service_id",
    "branch":     "branch_id",
    "department": "department_id",
}


def _dim_col(dim: str) -> str:
    col = _DIM_COL.get(dim)
    if not col:
        raise ValueError(f"Unknown dimension '{dim}'. Valid: {list(_DIM_COL)}")
    return col


class DimensionAnalyticsRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _fetchall(self, sql: str, params: dict) -> List[Dict[str, Any]]:
        try:
            result = await self.db.execute(text(sql), params)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
        except Exception as exc:
            log.error("dim_analytics.query_failed", error=str(exc))
            return []

    async def _fetchone(self, sql: str, params: dict) -> Optional[Dict[str, Any]]:
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else None

    # ── Summary ───────────────────────────────────────────────────────────────

    async def get_summary(
        self,
        dim: str,
        dim_id: uuid.UUID,
        org_id:    Optional[uuid.UUID] = None,
        date_from: Optional[date]      = None,
        date_to:   Optional[date]      = None,
    ) -> Dict[str, Any]:
        """
        Full feedback summary for a single entity.
        Returns counts per type, percentages, resolution rate, avg hours,
        and suggestion implementation rate.
        """
        col = _dim_col(dim)
        params: Dict[str, Any] = {"dim_id": str(dim_id)}
        extra: List[str] = []

        if org_id:
            extra.append("f.org_id = :org_id")
            params["org_id"] = str(org_id)
        if date_from:
            extra.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            extra.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)

        where_extra = ("AND " + " AND ".join(extra)) if extra else ""

        row = await self._fetchone(f"""
            SELECT
                COUNT(*)                                                           AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')       AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')      AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')        AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')         AS inquiries,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))   AS resolved,
                COUNT(*) FILTER (
                    WHERE f.feedback_type::text = 'GRIEVANCE'
                      AND f.status::text IN ('RESOLVED','CLOSED')
                )                                                                   AS grievances_resolved,
                COUNT(*) FILTER (
                    WHERE f.feedback_type::text = 'SUGGESTION'
                      AND (f.implemented_at IS NOT NULL OR f.status::text = 'ACTIONED')
                )                                                                   AS suggestions_implemented,
                COUNT(*) FILTER (WHERE f.status::text = 'SUBMITTED')              AS pending,
                COUNT(*) FILTER (WHERE f.status::text = 'ACKNOWLEDGED')           AS acknowledged,
                COUNT(*) FILTER (WHERE f.status::text = 'IN_REVIEW')              AS in_review,
                COUNT(*) FILTER (
                    WHERE f.status::text IN ('ACKNOWLEDGED','IN_REVIEW')
                      AND f.target_resolution_date < NOW()
                )                                                                   AS overdue,
                ROUND(CAST(
                    AVG(CASE WHEN f.resolved_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                        ELSE NULL END
                    ) AS NUMERIC
                ), 2)                                                               AS avg_resolution_hours
            FROM feedbacks f
            WHERE f.{col} = :dim_id
              {where_extra}
        """, params) or {}

        total       = int(row.get("total", 0))
        grievances  = int(row.get("grievances", 0))
        suggestions = int(row.get("suggestions", 0))
        applause    = int(row.get("applause", 0))
        inquiries   = int(row.get("inquiries", 0))
        resolved    = int(row.get("resolved", 0))
        g_resolved  = int(row.get("grievances_resolved", 0))
        s_impl      = int(row.get("suggestions_implemented", 0))

        def pct(n: int) -> float:
            return round(n * 100 / total, 1) if total else 0.0

        return {
            "total": total,
            "by_type": {
                "grievance": {
                    "count": grievances,
                    "pct":   pct(grievances),
                    "resolved":      g_resolved,
                    "resolution_rate": round(g_resolved * 100 / grievances, 1) if grievances else 0.0,
                },
                "suggestion": {
                    "count": suggestions,
                    "pct":   pct(suggestions),
                    "implemented":       s_impl,
                    "implementation_rate": round(s_impl * 100 / suggestions, 1) if suggestions else 0.0,
                },
                "applause": {
                    "count": applause,
                    "pct":   pct(applause),
                },
                "inquiry": {
                    "count": inquiries,
                    "pct":   pct(inquiries),
                },
            },
            "resolved":             resolved,
            "resolution_rate_pct":  pct(resolved),
            "avg_resolution_hours": float(row.get("avg_resolution_hours") or 0),
            "pending":              int(row.get("pending", 0)),
            "acknowledged":         int(row.get("acknowledged", 0)),
            "in_review":            int(row.get("in_review", 0)),
            "overdue":              int(row.get("overdue", 0)),
        }

    # ── Category distribution ─────────────────────────────────────────────────

    async def get_category_distribution(
        self,
        dim: str,
        dim_id: uuid.UUID,
        org_id:        Optional[uuid.UUID] = None,
        feedback_type: Optional[str]       = None,
        date_from:     Optional[date]      = None,
        date_to:       Optional[date]      = None,
    ) -> List[Dict[str, Any]]:
        """
        Categories with counts and percentages for the given entity.
        Joins feedback_category_defs to return human-readable names.
        Includes an 'uncategorised' bucket for feedback with no category.
        """
        col = _dim_col(dim)
        params: Dict[str, Any] = {"dim_id": str(dim_id)}
        extra: List[str] = []

        if org_id:
            extra.append("f.org_id = :org_id")
            params["org_id"] = str(org_id)
        if feedback_type:
            extra.append("f.feedback_type::text = :ftype")
            params["ftype"] = feedback_type.upper()
        if date_from:
            extra.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            extra.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)

        where_extra = ("AND " + " AND ".join(extra)) if extra else ""

        rows = await self._fetchall(f"""
            SELECT
                f.category_def_id,
                COALESCE(cd.name, 'Uncategorised')  AS category_name,
                COALESCE(cd.slug, 'uncategorised')  AS category_slug,
                cd.color_hex,
                cd.icon,
                COUNT(*)                                                            AS total,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'GRIEVANCE')        AS grievances,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'SUGGESTION')       AS suggestions,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'APPLAUSE')         AS applause,
                COUNT(*) FILTER (WHERE f.feedback_type::text = 'INQUIRY')          AS inquiries,
                COUNT(*) FILTER (WHERE f.status::text IN ('RESOLVED','CLOSED'))    AS resolved,
                ROUND(CAST(
                    AVG(CASE WHEN f.resolved_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (f.resolved_at - f.submitted_at)) / 3600.0
                        ELSE NULL END
                    ) AS NUMERIC
                ), 2)                                                               AS avg_resolution_hours
            FROM feedbacks f
            LEFT JOIN feedback_category_defs cd ON cd.id = f.category_def_id
            WHERE f.{col} = :dim_id
              {where_extra}
            GROUP BY f.category_def_id, cd.name, cd.slug, cd.color_hex, cd.icon
            ORDER BY total DESC
        """, params)

        grand_total = sum(int(r.get("total", 0)) for r in rows)
        result = []
        for r in rows:
            cnt = int(r.get("total", 0))
            result.append({
                "category_id":   str(r["category_def_id"]) if r["category_def_id"] else None,
                "category_name": r["category_name"],
                "category_slug": r["category_slug"],
                "color_hex":     r.get("color_hex"),
                "icon":          r.get("icon"),
                "count":         cnt,
                "pct":           round(cnt * 100 / grand_total, 1) if grand_total else 0.0,
                "grievances":    int(r.get("grievances", 0)),
                "suggestions":   int(r.get("suggestions", 0)),
                "applause":      int(r.get("applause", 0)),
                "inquiries":     int(r.get("inquiries", 0)),
                "resolved":      int(r.get("resolved", 0)),
                "avg_resolution_hours": float(r.get("avg_resolution_hours") or 0),
            })
        return result

    # ── Feedback list (drill-down) ─────────────────────────────────────────────

    async def get_feedback_list(
        self,
        dim: str,
        dim_id: uuid.UUID,
        org_id:        Optional[uuid.UUID] = None,
        feedback_type: Optional[str]       = None,
        category_id:   Optional[uuid.UUID] = None,
        status:        Optional[str]       = None,
        date_from:     Optional[date]      = None,
        date_to:       Optional[date]      = None,
        page:          int                 = 1,
        size:          int                 = 20,
    ) -> Dict[str, Any]:
        """
        Paginated list of individual feedback records for the given entity.
        Used for drill-down when a user clicks a feedback type or category.
        """
        col = _dim_col(dim)
        params: Dict[str, Any] = {"dim_id": str(dim_id), "limit": size, "offset": (page - 1) * size}
        filters: List[str] = [f"f.{col} = :dim_id"]

        if org_id:
            filters.append("f.org_id = :org_id")
            params["org_id"] = str(org_id)
        if feedback_type:
            filters.append("f.feedback_type::text = :ftype")
            params["ftype"] = feedback_type.upper()
        if category_id:
            filters.append("f.category_def_id = :cat_id")
            params["cat_id"] = str(category_id)
        if status:
            filters.append("f.status::text = :status")
            params["status"] = status.upper()
        if date_from:
            filters.append("f.submitted_at >= :date_from")
            params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        if date_to:
            filters.append("f.submitted_at < :date_to")
            params["date_to"] = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)

        where = "WHERE " + " AND ".join(filters)

        count_row = await self._fetchone(f"""
            SELECT COUNT(*) AS total FROM feedbacks f {where}
        """, params)
        total = int((count_row or {}).get("total", 0))

        rows = await self._fetchall(f"""
            SELECT
                f.id,
                f.unique_ref,
                f.feedback_type::text   AS feedback_type,
                f.status::text          AS status,
                f.priority::text        AS priority,
                f.subject,
                f.description,
                f.submitter_name,
                f.submitter_phone,
                f.is_anonymous,
                f.issue_lga,
                f.issue_ward,
                f.issue_region,
                f.submitted_at,
                f.resolved_at,
                f.implemented_at,
                f.target_resolution_date,
                f.category_def_id,
                cd.name  AS category_name,
                cd.slug  AS category_slug,
                f.channel::text         AS channel,
                f.org_id,
                f.project_id,
                f.department_id,
                f.service_id,
                f.product_id,
                f.branch_id
            FROM feedbacks f
            LEFT JOIN feedback_category_defs cd ON cd.id = f.category_def_id
            {where}
            ORDER BY f.submitted_at DESC
            LIMIT :limit OFFSET :offset
        """, params)

        items = []
        for r in rows:
            items.append({
                "feedback_id":    str(r["id"]),
                "unique_ref":     r["unique_ref"],
                "feedback_type":  r["feedback_type"],
                "status":         r["status"],
                "priority":       r["priority"],
                "subject":        r["subject"],
                "description":    r["description"],
                "submitter_name": r["submitter_name"] if not r["is_anonymous"] else "Anonymous",
                "is_anonymous":   r["is_anonymous"],
                "location": {
                    "region": r["issue_region"],
                    "lga":    r["issue_lga"],
                    "ward":   r["issue_ward"],
                },
                "category": {
                    "id":   str(r["category_def_id"]) if r["category_def_id"] else None,
                    "name": r["category_name"],
                    "slug": r["category_slug"],
                },
                "channel":      r["channel"],
                "submitted_at": r["submitted_at"].isoformat() if r["submitted_at"] else None,
                "resolved_at":  r["resolved_at"].isoformat()  if r["resolved_at"]  else None,
                "implemented_at": r["implemented_at"].isoformat() if r["implemented_at"] else None,
                "target_resolution_date": r["target_resolution_date"].isoformat() if r["target_resolution_date"] else None,
                "org_id":        str(r["org_id"])        if r["org_id"]        else None,
                "project_id":    str(r["project_id"])    if r["project_id"]    else None,
                "department_id": str(r["department_id"]) if r["department_id"] else None,
                "service_id":    str(r["service_id"])    if r["service_id"]    else None,
                "product_id":    str(r["product_id"])    if r["product_id"]    else None,
                "branch_id":     str(r["branch_id"])     if r["branch_id"]     else None,
            })

        return {"total": total, "page": page, "size": size, "items": items}

    # ── Feedback texts for AI theme mining ───────────────────────────────────

    async def get_feedback_texts(
        self,
        dim: str,
        dim_id: uuid.UUID,
        limit: int = 100,
    ) -> List[str]:
        """
        Fetches recent feedback description texts (and transcriptions) for AI mining.
        """
        col = _dim_col(dim)
        rows = await self._fetchall(f"""
            SELECT
                COALESCE(
                    NULLIF(f.voice_note_transcription, ''),
                    NULLIF(f.description, '')
                ) AS text,
                f.feedback_type::text AS feedback_type
            FROM feedbacks f
            WHERE f.{col} = :dim_id
              AND (
                (f.description IS NOT NULL AND f.description != '')
                OR (f.voice_note_transcription IS NOT NULL AND f.voice_note_transcription != '')
              )
            ORDER BY f.submitted_at DESC
            LIMIT :limit
        """, {"dim_id": str(dim_id), "limit": limit})

        return [r["text"] for r in rows if r.get("text")]

    # ── QR scan counts ────────────────────────────────────────────────────────

    async def get_scan_counts(
        self,
        dim: str,
        dim_id: uuid.UUID,
    ) -> Dict[str, int]:
        """
        Returns QR scan counts for a product from verification_events.
        Only relevant for dim=product.
        Only works if verification_db is accessible (via analytics_db or cross-db view).
        Falls back to 0 gracefully.
        """
        if dim != "product":
            return {"scan_count": 0, "authentic": 0, "already_used": 0, "unrecognized": 0}
        try:
            row = await self._fetchone("""
                SELECT
                    COUNT(*)                                              AS scan_count,
                    COUNT(*) FILTER (WHERE result = 'AUTHENTIC')         AS authentic,
                    COUNT(*) FILTER (WHERE result = 'ALREADY_USED')      AS already_used,
                    COUNT(*) FILTER (WHERE result = 'UNRECOGNIZED')      AS unrecognized
                FROM verification_events
                WHERE product_id = :dim_id
            """, {"dim_id": str(dim_id)}) or {}
            return {
                "scan_count":   int(row.get("scan_count", 0)),
                "authentic":    int(row.get("authentic", 0)),
                "already_used": int(row.get("already_used", 0)),
                "unrecognized": int(row.get("unrecognized", 0)),
            }
        except Exception:
            return {"scan_count": 0, "authentic": 0, "already_used": 0, "unrecognized": 0}
