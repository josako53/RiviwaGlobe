# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  repositories/report_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""
repositories/report_repository.py
────────────────────────────────────────────────────────────────────────────
Read-only aggregate queries for all performance reports.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.feedback import (
    Feedback,
    FeedbackStatus,
    FeedbackType,
)


class ReportRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _base(
        self,
        project_id: Optional[uuid.UUID] = None,
        from_dt=None,
        to_dt=None,
        region:   Optional[str] = None,
        district: Optional[str] = None,
        lga:      Optional[str] = None,
        ward:     Optional[str] = None,
        mtaa:     Optional[str] = None,
    ):
        """Base query with date range and Tanzania admin hierarchy location filters."""
        q = select(Feedback)
        if project_id: q = q.where(Feedback.project_id    == project_id)
        if from_dt:    q = q.where(Feedback.submitted_at  >= from_dt)
        if to_dt:      q = q.where(Feedback.submitted_at  <= to_dt)
        # Location filters — partial match for flexible querying
        if region:   q = q.where(Feedback.issue_region.ilike(f"%{region}%"))
        if district: q = q.where(Feedback.issue_district.ilike(f"%{district}%"))
        if lga:      q = q.where(Feedback.issue_lga.ilike(f"%{lga}%"))
        if ward:     q = q.where(Feedback.issue_ward.ilike(f"%{ward}%"))
        if mtaa:     q = q.where(Feedback.issue_mtaa.ilike(f"%{mtaa}%"))
        return q

    async def list_all_for_project(
        self,
        project_id: Optional[uuid.UUID] = None,
        from_dt:    Optional[datetime]  = None,
        to_dt:      Optional[datetime]  = None,
        region:     Optional[str]       = None,
        district:   Optional[str]       = None,
        lga:        Optional[str]       = None,
        ward:       Optional[str]       = None,
        mtaa:       Optional[str]       = None,
    ) -> list[Feedback]:
        result = await self.db.execute(
            self._base(project_id, from_dt, to_dt, region=region,
                       district=district, lga=lga, ward=ward, mtaa=mtaa)
            .order_by(Feedback.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def counts_by_type_and_status(
        self,
        project_id: Optional[uuid.UUID] = None,
        from_dt:    Optional[datetime]  = None,
        to_dt:      Optional[datetime]  = None,
    ) -> tuple[list, list]:
        q = select(Feedback.feedback_type, func.count(Feedback.id))
        if project_id: q = q.where(Feedback.project_id == project_id)
        if from_dt:    q = q.where(Feedback.submitted_at >= from_dt)
        if to_dt:      q = q.where(Feedback.submitted_at <= to_dt)
        by_type = await self.db.execute(q.group_by(Feedback.feedback_type))

        q2 = select(Feedback.feedback_type, Feedback.status, func.count(Feedback.id))
        if project_id: q2 = q2.where(Feedback.project_id == project_id)
        if from_dt:    q2 = q2.where(Feedback.submitted_at >= from_dt)
        if to_dt:      q2 = q2.where(Feedback.submitted_at <= to_dt)
        by_status = await self.db.execute(
            q2.group_by(Feedback.feedback_type, Feedback.status)
        )
        return list(by_type.all()), list(by_status.all())

    async def count_open(
        self,
        project_id:    Optional[uuid.UUID] = None,
        feedback_type: Optional[str]       = None,
        from_dt:       Optional[datetime]  = None,
        to_dt:         Optional[datetime]  = None,
    ) -> int:
        open_statuses = [
            FeedbackStatus.SUBMITTED, FeedbackStatus.ACKNOWLEDGED,
            FeedbackStatus.IN_REVIEW, FeedbackStatus.ESCALATED, FeedbackStatus.APPEALED,
        ]
        q = select(func.count(Feedback.id)).where(Feedback.status.in_(open_statuses))
        if project_id:    q = q.where(Feedback.project_id    == project_id)
        if feedback_type: q = q.where(Feedback.feedback_type == feedback_type)
        if from_dt:       q = q.where(Feedback.submitted_at  >= from_dt)
        if to_dt:         q = q.where(Feedback.submitted_at  <= to_dt)
        return await self.db.scalar(q) or 0

    async def list_grievances(
        self,
        project_id: Optional[uuid.UUID] = None,
        from_dt:    Optional[datetime]  = None,
        to_dt:      Optional[datetime]  = None,
        region:     Optional[str]       = None,
        district:   Optional[str]       = None,
        lga:        Optional[str]       = None,
        ward:       Optional[str]       = None,
        mtaa:       Optional[str]       = None,
    ) -> list[Feedback]:
        result = await self.db.execute(
            self._base(project_id, from_dt, to_dt, region=region,
                       district=district, lga=lga, ward=ward, mtaa=mtaa)
            .where(Feedback.feedback_type == FeedbackType.GRIEVANCE)
            .order_by(Feedback.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def list_suggestions(
        self,
        project_id: Optional[uuid.UUID] = None,
        from_dt:    Optional[datetime]  = None,
        to_dt:      Optional[datetime]  = None,
        region:     Optional[str]       = None,
        district:   Optional[str]       = None,
        lga:        Optional[str]       = None,
        ward:       Optional[str]       = None,
        mtaa:       Optional[str]       = None,
    ) -> list[Feedback]:
        result = await self.db.execute(
            self._base(project_id, from_dt, to_dt, region=region,
                       district=district, lga=lga, ward=ward, mtaa=mtaa)
            .where(Feedback.feedback_type == FeedbackType.SUGGESTION)
            .order_by(Feedback.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def list_applause(
        self,
        project_id: Optional[uuid.UUID] = None,
        from_dt:    Optional[datetime]  = None,
        to_dt:      Optional[datetime]  = None,
        region:     Optional[str]       = None,
        district:   Optional[str]       = None,
        lga:        Optional[str]       = None,
        ward:       Optional[str]       = None,
        mtaa:       Optional[str]       = None,
    ) -> list[Feedback]:
        result = await self.db.execute(
            self._base(project_id, from_dt, to_dt, region=region,
                       district=district, lga=lga, ward=ward, mtaa=mtaa)
            .where(Feedback.feedback_type == FeedbackType.APPLAUSE)
            .order_by(Feedback.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def list_overdue(
        self,
        project_id: Optional[uuid.UUID] = None,
        as_of:      Optional[datetime]  = None,
    ) -> list[Feedback]:
        from datetime import timezone
        now = as_of or datetime.now(timezone.utc)
        closed = [FeedbackStatus.CLOSED, FeedbackStatus.DISMISSED, FeedbackStatus.RESOLVED]
        q = select(Feedback).where(
            Feedback.target_resolution_date <= now,
            Feedback.status.not_in(closed),
        )
        if project_id:
            q = q.where(Feedback.project_id == project_id)
        result = await self.db.execute(q.order_by(Feedback.target_resolution_date))
        return list(result.scalars().all())

    # ── Suggestion performance queries ────────────────────────────────────────

    async def suggestion_daily_rate(
        self,
        project_id: Optional[uuid.UUID],
        from_dt:    datetime,
        to_dt:      datetime,
        subproject_id: Optional[uuid.UUID] = None,
        stage_id:      Optional[uuid.UUID] = None,
        lga:           Optional[str]       = None,
        region:        Optional[str]       = None,
        district:      Optional[str]       = None,
        ward:          Optional[str]       = None,
        category:      Optional[str]       = None,
    ) -> list[dict]:
        """
        Count of suggestions submitted per calendar day in the date range.
        Returns [{date: "2025-06-15", count: 4, actioned: 2, noted: 1}, ...]
        """
        from sqlalchemy import cast, Date as SADate, case
        q = (
            select(
                cast(Feedback.submitted_at, SADate).label("day"),
                func.count(Feedback.id).label("total"),
                func.count(
                    case((Feedback.status == FeedbackStatus.ACTIONED, Feedback.id))
                ).label("actioned"),
                func.count(
                    case((Feedback.status == FeedbackStatus.NOTED, Feedback.id))
                ).label("noted"),
            )
            .where(
                Feedback.feedback_type == FeedbackType.SUGGESTION,
                Feedback.submitted_at  >= from_dt,
                Feedback.submitted_at  <= to_dt,
            )
            .group_by("day")
            .order_by("day")
        )
        if project_id:    q = q.where(Feedback.project_id    == project_id)
        if subproject_id: q = q.where(Feedback.subproject_id == subproject_id)
        if stage_id:      q = q.where(Feedback.stage_id      == stage_id)
        if lga:           q = q.where(Feedback.issue_lga.ilike(f"%{lga}%"))
        if region:        q = q.where(Feedback.issue_region.ilike(f"%{region}%"))
        if district:      q = q.where(Feedback.issue_district.ilike(f"%{district}%"))
        if ward:          q = q.where(Feedback.issue_ward.ilike(f"%{ward}%"))
        rows = await self.db.execute(q)
        return [
            {"date": str(r.day), "total": r.total, "actioned": r.actioned, "noted": r.noted}
            for r in rows.all()
        ]

    async def suggestion_by_category(
        self,
        project_id:    Optional[uuid.UUID],
        from_dt:       datetime,
        to_dt:         datetime,
        subproject_id: Optional[uuid.UUID] = None,
        stage_id:      Optional[uuid.UUID] = None,
        lga:           Optional[str]       = None,
        region:        Optional[str]       = None,
    ) -> list[dict]:
        """
        Count of suggestions per category (legacy enum + dynamic category_def_id).
        Returns [{category: "...", total: 12, actioned: 8, action_rate: 66.7}, ...]
        """
        from sqlalchemy import case
        q = (
            select(
                Feedback.category.label("cat"),
                func.count(Feedback.id).label("total"),
                func.count(
                    case((Feedback.status == FeedbackStatus.ACTIONED, Feedback.id))
                ).label("actioned"),
                func.count(
                    case((Feedback.status == FeedbackStatus.NOTED, Feedback.id))
                ).label("noted"),
            )
            .where(
                Feedback.feedback_type == FeedbackType.SUGGESTION,
                Feedback.submitted_at  >= from_dt,
                Feedback.submitted_at  <= to_dt,
            )
            .group_by(Feedback.category)
            .order_by(func.count(Feedback.id).desc())
        )
        if project_id:    q = q.where(Feedback.project_id    == project_id)
        if subproject_id: q = q.where(Feedback.subproject_id == subproject_id)
        if stage_id:      q = q.where(Feedback.stage_id      == stage_id)
        if lga:           q = q.where(Feedback.issue_lga.ilike(f"%{lga}%"))
        if region:        q = q.where(Feedback.issue_region.ilike(f"%{region}%"))
        rows = await self.db.execute(q)
        return [
            {
                "category":    str(r.cat),
                "total":       r.total,
                "actioned":    r.actioned,
                "noted":       r.noted,
                "action_rate": round(r.actioned / r.total * 100, 1) if r.total else 0.0,
            }
            for r in rows.all()
        ]

    async def suggestion_by_location(
        self,
        project_id:    Optional[uuid.UUID],
        from_dt:       datetime,
        to_dt:         datetime,
        group_by:      str = "lga",   # "region" | "district" | "lga" | "ward" | "mtaa"
        subproject_id: Optional[uuid.UUID] = None,
        stage_id:      Optional[uuid.UUID] = None,
    ) -> list[dict]:
        """
        Suggestion rate grouped by a geographic level.
        group_by: region | district | lga | ward | mtaa
        """
        from sqlalchemy import case
        col_map = {
            "region":   Feedback.issue_region,
            "district": Feedback.issue_district,
            "lga":      Feedback.issue_lga,
            "ward":     Feedback.issue_ward,
            "mtaa":     Feedback.issue_mtaa,
        }
        geo_col = col_map.get(group_by, Feedback.issue_lga)

        q = (
            select(
                geo_col.label("location"),
                func.count(Feedback.id).label("total"),
                func.count(
                    case((Feedback.status == FeedbackStatus.ACTIONED, Feedback.id))
                ).label("actioned"),
                func.count(
                    case((Feedback.implemented_at.isnot(None), Feedback.id))
                ).label("implemented"),
            )
            .where(
                Feedback.feedback_type == FeedbackType.SUGGESTION,
                Feedback.submitted_at  >= from_dt,
                Feedback.submitted_at  <= to_dt,
                geo_col.isnot(None),
            )
            .group_by(geo_col)
            .order_by(func.count(Feedback.id).desc())
        )
        if project_id:    q = q.where(Feedback.project_id    == project_id)
        if subproject_id: q = q.where(Feedback.subproject_id == subproject_id)
        if stage_id:      q = q.where(Feedback.stage_id      == stage_id)
        rows = await self.db.execute(q)
        return [
            {
                group_by:       r.location or "unknown",
                "total":        r.total,
                "actioned":     r.actioned,
                "implemented":  r.implemented,
                "action_rate":  round(r.actioned / r.total * 100, 1) if r.total else 0.0,
            }
            for r in rows.all()
        ]

    async def suggestion_by_stakeholder(
        self,
        project_id:    Optional[uuid.UUID],
        from_dt:       datetime,
        to_dt:         datetime,
        subproject_id: Optional[uuid.UUID] = None,
        stage_id:      Optional[uuid.UUID] = None,
        top_n:         int = 20,
    ) -> list[dict]:
        """
        Suggestions per stakeholder (submitted_by_stakeholder_id).
        Returns top_n stakeholders by submission count with:
          total, actioned, avg_implement_hours
        """
        from sqlalchemy import case
        q = (
            select(
                Feedback.submitted_by_stakeholder_id.label("stakeholder_id"),
                func.count(Feedback.id).label("total"),
                func.count(
                    case((Feedback.status == FeedbackStatus.ACTIONED, Feedback.id))
                ).label("actioned"),
                func.avg(
                    case((
                        Feedback.implemented_at.isnot(None),
                        func.extract("epoch", Feedback.implemented_at - Feedback.submitted_at) / 3600
                    ))
                ).label("avg_implement_hours"),
            )
            .where(
                Feedback.feedback_type == FeedbackType.SUGGESTION,
                Feedback.submitted_at  >= from_dt,
                Feedback.submitted_at  <= to_dt,
                Feedback.submitted_by_stakeholder_id.isnot(None),
            )
            .group_by(Feedback.submitted_by_stakeholder_id)
            .order_by(func.count(Feedback.id).desc())
            .limit(top_n)
        )
        if project_id:    q = q.where(Feedback.project_id    == project_id)
        if subproject_id: q = q.where(Feedback.subproject_id == subproject_id)
        if stage_id:      q = q.where(Feedback.stage_id      == stage_id)
        rows = await self.db.execute(q)
        return [
            {
                "stakeholder_id":      str(r.stakeholder_id),
                "total":               r.total,
                "actioned":            r.actioned,
                "action_rate":         round(r.actioned / r.total * 100, 1) if r.total else 0.0,
                "avg_implement_hours": round(float(r.avg_implement_hours), 1) if r.avg_implement_hours else None,
            }
            for r in rows.all()
        ]

    async def suggestion_implementation_times(
        self,
        project_id:    Optional[uuid.UUID],
        from_dt:       datetime,
        to_dt:         datetime,
        subproject_id: Optional[uuid.UUID] = None,
        stage_id:      Optional[uuid.UUID] = None,
        stakeholder_id: Optional[uuid.UUID] = None,
        category:      Optional[str]        = None,
        lga:           Optional[str]        = None,
        region:        Optional[str]        = None,
    ) -> dict:
        """
        Implementation timing analytics for implemented (ACTIONED) suggestions:
          avg_hours, min_hours, max_hours, median_hours,
          plus per-suggestion breakdown for the log table.
        """
        from sqlalchemy import case, text as sa_text
        q = (
            select(
                Feedback.id,
                Feedback.unique_ref,
                Feedback.subject,
                Feedback.category,
                Feedback.submitted_by_stakeholder_id,
                Feedback.issue_lga,
                Feedback.issue_region,
                Feedback.issue_ward,
                Feedback.stage_id,
                Feedback.subproject_id,
                Feedback.submitted_at,
                Feedback.implemented_at,
                (
                    func.extract("epoch", Feedback.implemented_at - Feedback.submitted_at) / 3600
                ).label("implement_hours"),
            )
            .where(
                Feedback.feedback_type    == FeedbackType.SUGGESTION,
                Feedback.status           == FeedbackStatus.ACTIONED,
                Feedback.implemented_at.isnot(None),
                Feedback.submitted_at     >= from_dt,
                Feedback.submitted_at     <= to_dt,
            )
            .order_by(Feedback.implemented_at.desc())
        )
        if project_id:      q = q.where(Feedback.project_id    == project_id)
        if subproject_id:   q = q.where(Feedback.subproject_id == subproject_id)
        if stage_id:        q = q.where(Feedback.stage_id      == stage_id)
        if stakeholder_id:  q = q.where(Feedback.submitted_by_stakeholder_id == stakeholder_id)
        if category:        q = q.where(Feedback.category.cast(str).ilike(f"%{category}%"))
        if lga:             q = q.where(Feedback.issue_lga.ilike(f"%{lga}%"))
        if region:          q = q.where(Feedback.issue_region.ilike(f"%{region}%"))

        rows = await self.db.execute(q)
        results = rows.all()

        if not results:
            return {
                "total_implemented": 0,
                "avg_hours": None, "min_hours": None,
                "max_hours": None, "median_hours": None,
                "items": [],
            }

        hours = [float(r.implement_hours) for r in results if r.implement_hours is not None]
        items = [
            {
                "unique_ref":      r.unique_ref,
                "subject":         r.subject,
                "category":        str(r.category) if r.category else None,
                "stakeholder_id":  str(r.submitted_by_stakeholder_id) if r.submitted_by_stakeholder_id else None,
                "stage_id":        str(r.stage_id) if r.stage_id else None,
                "subproject_id":   str(r.subproject_id) if r.subproject_id else None,
                "issue_lga":       r.issue_lga,
                "issue_region":    r.issue_region,
                "issue_ward":      r.issue_ward,
                "submitted_at":    r.submitted_at.isoformat(),
                "implemented_at":  r.implemented_at.isoformat() if r.implemented_at else None,
                "implement_hours": round(float(r.implement_hours), 1) if r.implement_hours else None,
            }
            for r in results
        ]

        sorted_hours = sorted(hours)
        n = len(sorted_hours)
        median = round(
            (sorted_hours[n//2 - 1] + sorted_hours[n//2]) / 2
            if n % 2 == 0 else sorted_hours[n//2], 1
        )

        return {
            "total_implemented": len(results),
            "avg_hours":    round(sum(hours) / len(hours), 1) if hours else None,
            "min_hours":    round(min(hours), 1) if hours else None,
            "max_hours":    round(max(hours), 1) if hours else None,
            "median_hours": median,
            "items":        items,
        }

    # ── Applause analytics ────────────────────────────────────────────────────

    async def applause_daily_rate(
        self,
        project_id:     uuid.UUID,
        from_dt:        datetime,
        to_dt:          datetime,
        stage_id:       Optional[uuid.UUID] = None,
        subproject_id:  Optional[uuid.UUID] = None,
        region:         Optional[str]       = None,
        district:       Optional[str]       = None,
        lga:            Optional[str]       = None,
        ward:           Optional[str]       = None,
        mtaa:           Optional[str]       = None,
    ) -> list[dict]:
        """
        Count of applause submissions per calendar day.
        Returns [{"date": "YYYY-MM-DD", "count": N}, ...] ordered chronologically.
        """
        from sqlalchemy import func, cast
        from sqlalchemy.types import Date
        q = (
            select(
                cast(Feedback.submitted_at, Date).label("day"),
                func.count(Feedback.id).label("count"),
            )
            .where(
                Feedback.feedback_type == FeedbackType.APPLAUSE,
                Feedback.submitted_at  >= from_dt,
                Feedback.submitted_at  <= to_dt,
            )
            .group_by("day")
            .order_by("day")
        )
        if project_id:     q = q.where(Feedback.project_id == project_id)
        if stage_id:       q = q.where(Feedback.stage_id   == stage_id)
        if subproject_id:  q = q.where(Feedback.subproject_id == subproject_id)
        if region:         q = q.where(Feedback.issue_region.ilike(f"%{region}%"))
        if district:       q = q.where(Feedback.issue_district.ilike(f"%{district}%"))
        if lga:            q = q.where(Feedback.issue_lga.ilike(f"%{lga}%"))
        if ward:           q = q.where(Feedback.issue_ward.ilike(f"%{ward}%"))
        if mtaa:           q = q.where(Feedback.issue_mtaa.ilike(f"%{mtaa}%"))
        rows = await self.db.execute(q)
        return [{"date": str(r.day), "count": r.count} for r in rows.all()]

    async def applause_by_category(
        self,
        project_id:    Optional[uuid.UUID] = None,
        from_dt:       Optional[datetime]  = None,
        to_dt:         Optional[datetime]  = None,
        stage_id:      Optional[uuid.UUID] = None,
        subproject_id: Optional[uuid.UUID] = None,
        region:        Optional[str]       = None,
        district:      Optional[str]       = None,
        lga:           Optional[str]       = None,
        ward:          Optional[str]       = None,
        mtaa:          Optional[str]       = None,
    ) -> list[dict]:
        """
        Count of applause per category.
        Returns [{"category": str, "count": N, "ack_count": N, "avg_ack_hours": float}, ...]
        """
        q = (
            self._base(project_id, from_dt, to_dt,
                       region=region, district=district, lga=lga, ward=ward, mtaa=mtaa)
            .where(Feedback.feedback_type == FeedbackType.APPLAUSE)
        )
        if stage_id:      q = q.where(Feedback.stage_id      == stage_id)
        if subproject_id: q = q.where(Feedback.subproject_id == subproject_id)
        rows = list((await self.db.execute(q)).scalars().all())

        cats: dict = {}
        for f in rows:
            key = f.category.value if f.category else "uncategorised"
            if key not in cats:
                cats[key] = {"category": key, "count": 0, "ack_count": 0, "ack_hours": []}
            cats[key]["count"] += 1
            if f.acknowledged_at:
                cats[key]["ack_count"] += 1
                h = (f.acknowledged_at - f.submitted_at).total_seconds() / 3600
                cats[key]["ack_hours"].append(h)

        result = []
        for key, d in cats.items():
            hrs = d["ack_hours"]
            result.append({
                "category":       key,
                "count":          d["count"],
                "ack_count":      d["ack_count"],
                "ack_rate_pct":   round(d["ack_count"] / d["count"] * 100, 1) if d["count"] else 0.0,
                "avg_ack_hours":  round(sum(hrs) / len(hrs), 2) if hrs else None,
            })
        return sorted(result, key=lambda x: -x["count"])

    async def applause_by_stakeholder(
        self,
        project_id:    Optional[uuid.UUID] = None,
        from_dt:       Optional[datetime]  = None,
        to_dt:         Optional[datetime]  = None,
        stage_id:      Optional[uuid.UUID] = None,
        subproject_id: Optional[uuid.UUID] = None,
        region:        Optional[str]       = None,
        district:      Optional[str]       = None,
        lga:           Optional[str]       = None,
        ward:          Optional[str]       = None,
        mtaa:          Optional[str]       = None,
    ) -> list[dict]:
        """
        Per-stakeholder: how many applause they submitted + avg time to acknowledgement.
        """
        q = (
            self._base(project_id, from_dt, to_dt,
                       region=region, district=district, lga=lga, ward=ward, mtaa=mtaa)
            .where(Feedback.feedback_type == FeedbackType.APPLAUSE)
        )
        if stage_id:      q = q.where(Feedback.stage_id      == stage_id)
        if subproject_id: q = q.where(Feedback.subproject_id == subproject_id)
        rows = list((await self.db.execute(q)).scalars().all())

        stk: dict = {}
        for f in rows:
            sid = str(f.submitted_by_stakeholder_id) if f.submitted_by_stakeholder_id else "anonymous"
            if sid not in stk:
                stk[sid] = {"stakeholder_id": sid, "count": 0, "ack_hours": []}
            stk[sid]["count"] += 1
            if f.acknowledged_at:
                h = (f.acknowledged_at - f.submitted_at).total_seconds() / 3600
                stk[sid]["ack_hours"].append(h)

        result = []
        for sid, d in stk.items():
            hrs = d["ack_hours"]
            result.append({
                "stakeholder_id":     sid,
                "count":              d["count"],
                "acked_count":        len(hrs),
                "avg_ack_hours":      round(sum(hrs) / len(hrs), 2) if hrs else None,
                "min_ack_hours":      round(min(hrs), 2) if hrs else None,
                "max_ack_hours":      round(max(hrs), 2) if hrs else None,
            })
        return sorted(result, key=lambda x: -x["count"])

    async def applause_acknowledgement_times(
        self,
        project_id:    Optional[uuid.UUID] = None,
        from_dt:       Optional[datetime]  = None,
        to_dt:         Optional[datetime]  = None,
        stage_id:      Optional[uuid.UUID] = None,
        subproject_id: Optional[uuid.UUID] = None,
        stakeholder_id:Optional[uuid.UUID] = None,
        category:      Optional[str]       = None,
        region:        Optional[str]       = None,
        district:      Optional[str]       = None,
        lga:           Optional[str]       = None,
        ward:          Optional[str]       = None,
        mtaa:          Optional[str]       = None,
    ) -> dict:
        """
        Detailed acknowledgement time stats for applause items that have been acknowledged.
        Returns overall stats + per-item list with individual timings.
        """
        q = (
            self._base(project_id, from_dt, to_dt,
                       region=region, district=district, lga=lga, ward=ward, mtaa=mtaa)
            .where(
                Feedback.feedback_type     == FeedbackType.APPLAUSE,
                Feedback.acknowledged_at.isnot(None),
            )
        )
        if stage_id:       q = q.where(Feedback.stage_id      == stage_id)
        if subproject_id:  q = q.where(Feedback.subproject_id == subproject_id)
        if stakeholder_id: q = q.where(Feedback.submitted_by_stakeholder_id == stakeholder_id)
        if category:       q = q.where(Feedback.category.cast(str).ilike(f"%{category}%"))

        rows = list((await self.db.execute(q)).scalars().all())
        if not rows:
            return {
                "total_acknowledged": 0,
                "avg_seconds": None, "avg_minutes": None,
                "avg_hours": None,   "avg_days": None,
                "min_seconds": None, "max_seconds": None,
                "median_hours": None,
                "items": [],
            }

        seconds_list = [
            (f.acknowledged_at - f.submitted_at).total_seconds()
            for f in rows
        ]
        sorted_s = sorted(seconds_list)
        n = len(sorted_s)
        median_s = (
            (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2
            if n % 2 == 0 else sorted_s[n // 2]
        )
        avg_s = sum(seconds_list) / len(seconds_list)

        items = [
            {
                "unique_ref":     f.unique_ref,
                "subject":        f.subject,
                "category":       f.category.value if f.category else None,
                "stakeholder_id": str(f.submitted_by_stakeholder_id) if f.submitted_by_stakeholder_id else None,
                "stage_id":       str(f.stage_id) if f.stage_id else None,
                "subproject_id":  str(f.subproject_id) if hasattr(f, "subproject_id") and f.subproject_id else None,
                "issue_lga":      f.issue_lga,
                "issue_region":   f.issue_region,
                "issue_ward":     f.issue_ward,
                "submitted_at":   f.submitted_at.isoformat(),
                "acknowledged_at":f.acknowledged_at.isoformat(),
                "ack_seconds":    round((f.acknowledged_at - f.submitted_at).total_seconds(), 0),
                "ack_minutes":    round((f.acknowledged_at - f.submitted_at).total_seconds() / 60, 2),
                "ack_hours":      round((f.acknowledged_at - f.submitted_at).total_seconds() / 3600, 2),
                "ack_days":       round((f.acknowledged_at - f.submitted_at).total_seconds() / 86400, 3),
            }
            for f in rows
        ]

        return {
            "total_acknowledged": len(rows),
            "avg_seconds":  round(avg_s, 0),
            "avg_minutes":  round(avg_s / 60, 2),
            "avg_hours":    round(avg_s / 3600, 2),
            "avg_days":     round(avg_s / 86400, 3),
            "min_seconds":  round(min(seconds_list), 0),
            "max_seconds":  round(max(seconds_list), 0),
            "median_hours": round(median_s / 3600, 2),
            "items": items,
        }
