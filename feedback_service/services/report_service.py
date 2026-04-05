"""
services/report_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for all 10 performance + log reports.
All computation happens here; API layer only calls one method and exports.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.feedback import (
    FeedbackPriority, FeedbackStatus, FeedbackType, GRMLevel, SubmissionMethod,
)
from repositories.report_repository import ReportRepository

_ACK_SLA_H = {
    FeedbackPriority.CRITICAL: 24,
    FeedbackPriority.HIGH:     48,
    FeedbackPriority.MEDIUM:  120,
    FeedbackPriority.LOW:     240,
}
_RES_SLA_H = {
    FeedbackPriority.CRITICAL: 168,
    FeedbackPriority.HIGH:     336,
    FeedbackPriority.MEDIUM:   720,
    FeedbackPriority.LOW:      None,
}
_OPEN_ST = {
    FeedbackStatus.SUBMITTED, FeedbackStatus.ACKNOWLEDGED,
    FeedbackStatus.IN_REVIEW, FeedbackStatus.ESCALATED, FeedbackStatus.APPEALED,
}
_TERM_ST = {
    FeedbackStatus.RESOLVED, FeedbackStatus.CLOSED,
    FeedbackStatus.DISMISSED, FeedbackStatus.ACTIONED, FeedbackStatus.NOTED,
}


class ReportService:

    def __init__(self, db: AsyncSession) -> None:
        self.repo = ReportRepository(db)

    # ── Date range helper ─────────────────────────────────────────────────────

    def _dr(self, from_date, to_date, default_days=30):
        now     = datetime.now(timezone.utc)
        from_dt = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc) if from_date \
                  else now - timedelta(days=default_days)
        to_dt   = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc) if to_date else now
        return from_dt, to_dt, now

    # ── Stat helpers (pure Python — no DB calls) ──────────────────────────────

    def _avg_h(self, items, start_field, end_field):
        deltas = [
            (getattr(f, end_field) - getattr(f, start_field)).total_seconds() / 3600
            for f in items
            if getattr(f, start_field) and getattr(f, end_field)
        ]
        return round(sum(deltas) / len(deltas), 1) if deltas else None

    def _res_rate(self, items):
        terminal = [f for f in items if f.status in _TERM_ST]
        if not terminal:
            return 0.0
        resolved = [f for f in terminal if f.status in (
            FeedbackStatus.RESOLVED, FeedbackStatus.ACTIONED, FeedbackStatus.NOTED
        )]
        return round(len(resolved) / len(terminal) * 100, 1)

    def _by_status(self, items):
        c = {}
        for f in items:
            c[f.status.value] = c.get(f.status.value, 0) + 1
        return [{"status": k, "count": v} for k, v in sorted(c.items())]

    def _by_priority(self, items):
        c = {}
        for f in items:
            p = f.priority.value if f.priority else "unknown"
            c[p] = c.get(p, 0) + 1
        return [{"priority": k, "count": v} for k, v in c.items()]

    def _by_channel(self, items):
        c = {}
        for f in items:
            c[f.channel.value] = c.get(f.channel.value, 0) + 1
        return [{"channel": k, "count": v} for k, v in sorted(c.items())]

    def _by_method(self, items):
        c = {}
        for f in items:
            m = f.submission_method.value if f.submission_method else "unknown"
            c[m] = c.get(m, 0) + 1
        return [{"method": k, "count": v} for k, v in sorted(c.items())]

    def _by_level(self, items):
        c = {}
        for f in items:
            lv = f.current_level.value if f.current_level else "unknown"
            c[lv] = c.get(lv, 0) + 1
        return [{"level": k, "count": v} for k, v in sorted(c.items())]

    def _by_lga(self, items):
        c = {}
        for f in items:
            c[f.issue_lga or "unknown"] = c.get(f.issue_lga or "unknown", 0) + 1
        return sorted([{"lga": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _by_region(self, items):
        c = {}
        for f in items:
            c[f.issue_region or "unknown"] = c.get(f.issue_region or "unknown", 0) + 1
        return sorted([{"region": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _by_district(self, items):
        c = {}
        for f in items:
            c[f.issue_district or "unknown"] = c.get(f.issue_district or "unknown", 0) + 1
        return sorted([{"district": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _by_ward(self, items):
        c = {}
        for f in items:
            c[f.issue_ward or "unknown"] = c.get(f.issue_ward or "unknown", 0) + 1
        return sorted([{"ward": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _by_mtaa(self, items):
        c = {}
        for f in items:
            c[f.issue_mtaa or "unknown"] = c.get(f.issue_mtaa or "unknown", 0) + 1
        return sorted([{"mtaa": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _breach(self, f, now):
        ack_s = _ACK_SLA_H.get(f.priority)
        res_s = _RES_SLA_H.get(f.priority)
        ack_b = (f.acknowledged_at is None and ack_s is not None and
                 (now - f.submitted_at).total_seconds() > ack_s * 3600)
        res_b = (f.resolved_at is None and res_s is not None and
                 f.status not in _TERM_ST and
                 (now - f.submitted_at).total_seconds() > res_s * 3600)
        return ack_b, res_b

    def _log_row(self, f, now):
        ab, rb = self._breach(f, now)
        return {
            "unique_ref":        f.unique_ref,
            "feedback_type":     f.feedback_type.value,
            "category":          f.category.value,
            "subject":           f.subject,
            "channel":           f.channel.value,
            "submission_method": f.submission_method.value if f.submission_method else None,
            "priority":          f.priority.value if f.priority else None,
            "current_level":     f.current_level.value if f.current_level else None,
            "status":            f.status.value,
            "is_anonymous":      f.is_anonymous,
            "submitter_name":    f.submitter_name if not f.is_anonymous else "Anonymous",
            # ── Submitter location ─────────────────────────────────────────
            "submitter_region":   f.submitter_location_region,
            "submitter_district": f.submitter_location_district,
            "submitter_lga":      f.submitter_location_lga,
            "submitter_ward":     f.submitter_location_ward,
            "submitter_street":   f.submitter_location_street,
            # ── Issue location (Tanzania admin hierarchy) ───────────────────
            "issue_region":   f.issue_region,
            "issue_district": f.issue_district,
            "issue_lga":      f.issue_lga,
            "issue_ward":     f.issue_ward,
            "issue_mtaa":     f.issue_mtaa,
            "issue_gps":      {"lat": f.issue_gps_lat, "lng": f.issue_gps_lng}
                              if f.issue_gps_lat and f.issue_gps_lng else None,
            "assigned_to":       str(f.assigned_to_user_id) if f.assigned_to_user_id else None,
            "submitted_at":      f.submitted_at.isoformat(),
            "acknowledged_at":   f.acknowledged_at.isoformat() if f.acknowledged_at else None,
            "resolved_at":       f.resolved_at.isoformat() if f.resolved_at else None,
            "closed_at":         f.closed_at.isoformat() if f.closed_at else None,
            "target_resolution": f.target_resolution_date.isoformat() if f.target_resolution_date else None,
            "hours_open":        round((now - f.submitted_at).total_seconds() / 3600, 1),
            "ack_sla_breached":  ab,
            "resolve_sla_breached": rb,
        }

    # ── Reports ───────────────────────────────────────────────────────────────

    async def performance(
        self, project_id=None, from_date=None, to_date=None,
        stage_id=None,
        region=None, district=None, lga=None, ward=None, mtaa=None,
        priority=None, channel=None, submission_method=None,
    ) -> dict:
        from_dt, to_dt, now = self._dr(from_date, to_date)
        all_items = await self.repo.list_all_for_project(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )
        # Apply post-DB filters (stage_id, priority, channel, submission_method)
        all_items = self._filter(all_items, stage_id=stage_id,
                                 priority=priority, channel=channel,
                                 submission_method=submission_method)
        gr = [f for f in all_items if f.feedback_type == FeedbackType.GRIEVANCE]
        sg = [f for f in all_items if f.feedback_type == FeedbackType.SUGGESTION]
        ap = [f for f in all_items if f.feedback_type == FeedbackType.APPLAUSE]

        def _ts(items, ftype):
            return {
                "type": ftype, "total": len(items),
                "open":      sum(1 for f in items if f.status in _OPEN_ST),
                "resolved":  sum(1 for f in items if f.status in (FeedbackStatus.RESOLVED, FeedbackStatus.ACTIONED, FeedbackStatus.NOTED)),
                "dismissed": sum(1 for f in items if f.status == FeedbackStatus.DISMISSED),
                "closed":    sum(1 for f in items if f.status == FeedbackStatus.CLOSED),
                "resolution_rate":   self._res_rate(items),
                "avg_ack_hours":     self._avg_h(items, "submitted_at", "acknowledged_at"),
                "avg_resolve_hours": self._avg_h(items, "submitted_at", "resolved_at"),
            }

        acked   = [f for f in all_items if f.acknowledged_at]
        ack_met = sum(1 for f in acked if f.priority and
                      (f.acknowledged_at - f.submitted_at).total_seconds() / 3600 <= _ACK_SLA_H[f.priority])
        res_el  = [f for f in all_items if f.priority and _RES_SLA_H.get(f.priority) and f.resolved_at]
        res_met = sum(1 for f in res_el if
                      (f.resolved_at - f.submitted_at).total_seconds() / 3600 <= _RES_SLA_H[f.priority])
        breaches = sum(1 for f in all_items if any(self._breach(f, now)))

        return {
            "project_id": str(project_id) if project_id else None,
            "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "totals": {
                "all":      len(all_items),
                "open":     sum(1 for f in all_items if f.status in _OPEN_ST),
                "resolved": sum(1 for f in all_items if f.status in (FeedbackStatus.RESOLVED, FeedbackStatus.ACTIONED, FeedbackStatus.NOTED)),
                "dismissed": sum(1 for f in all_items if f.status == FeedbackStatus.DISMISSED),
                "closed":   sum(1 for f in all_items if f.status == FeedbackStatus.CLOSED),
            },
            "by_type":           [_ts(gr, "grievance"), _ts(sg, "suggestion"), _ts(ap, "applause")],
            "resolution_rate":   self._res_rate(all_items),
            "avg_ack_hours":     self._avg_h(all_items, "submitted_at", "acknowledged_at"),
            "avg_resolve_hours": self._avg_h(all_items, "submitted_at", "resolved_at"),
            "sla_compliance": {
                "acknowledgement_pct": round(ack_met / len(acked) * 100, 1) if acked else None,
                "resolution_pct":      round(res_met / len(res_el) * 100, 1) if res_el else None,
            },
            "sla_breach_count":     breaches,
            "by_status":            self._by_status(all_items),
            "by_priority":          self._by_priority(all_items),
            "by_channel":           self._by_channel(all_items),
            "by_submission_method": self._by_method(all_items),
            "by_level":             self._by_level(gr),
            "by_lga":               self._by_lga(all_items),
            "by_region":            self._by_region(all_items),
            "by_district":          self._by_district(all_items),
            "by_ward":              self._by_ward(all_items),
        }

    async def grievances(
        self, project_id=None, from_date=None, to_date=None,
        stage_id=None,
        region=None, district=None, lga=None, ward=None, mtaa=None,
        priority=None, channel=None, submission_method=None, status=None,
        time_unit: str = "hours",
        custom_seconds: int = 3600,
    ) -> dict:
        from_dt, to_dt, now = self._dr(from_date, to_date)
        items = await self.repo.list_grievances(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )
        items = self._filter(items, stage_id=stage_id,
                             priority=priority, channel=channel,
                             submission_method=submission_method, status=status)
        terminal = [f for f in items if f.status in _TERM_ST]
        resolved = [f for f in items if f.status == FeedbackStatus.RESOLVED]

        sla_by_priority = []
        for pv in FeedbackPriority:
            pi = [f for f in items if f.priority == pv]
            if not pi:
                continue
            acked   = [f for f in pi if f.acknowledged_at]
            ack_met = sum(1 for f in acked if
                          (f.acknowledged_at - f.submitted_at).total_seconds() / 3600 <= _ACK_SLA_H[pv])
            res_p   = [f for f in pi if f.resolved_at]
            res_sla = _RES_SLA_H[pv]
            res_met = sum(1 for f in res_p if res_sla and
                          (f.resolved_at - f.submitted_at).total_seconds() / 3600 <= res_sla)
            sla_by_priority.append({
                "priority": pv.value, "count": len(pi),
                "ack_sla_hours": _ACK_SLA_H[pv], "resolve_sla_hours": res_sla,
                "ack_compliance_pct": round(ack_met / len(acked) * 100, 1) if acked else None,
                "res_compliance_pct": round(res_met / len(res_p) * 100, 1) if res_p else None,
                "avg_ack_hours":     self._avg_h(pi, "submitted_at", "acknowledged_at"),
                "avg_resolve_hours": self._avg_h(pi, "submitted_at", "resolved_at"),
            })

        escalation_breakdown = []
        for level in GRMLevel:
            at = [f for f in items if f.current_level == level]
            pt = [f for f in items if f.status == FeedbackStatus.ESCALATED and f.current_level == level]
            if at or pt:
                escalation_breakdown.append({
                    "level": level.value,
                    "currently_at_level": len(at),
                    "passed_through": len(pt),
                })

        breaches = [
            {
                "unique_ref":      f.unique_ref,
                "priority":        f.priority.value if f.priority else None,
                "status":          f.status.value,
                "submitted_at":    f.submitted_at.isoformat(),
                "ack_breached":    self._breach(f, now)[0],
                "resolve_breached": self._breach(f, now)[1],
                "hours_open":      round((now - f.submitted_at).total_seconds() / 3600, 1),
            }
            for f in items if any(self._breach(f, now))
        ][:20]

        return {
            "project_id": str(project_id) if project_id else None,
            "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "counts": {
                "total":        len(items),
                "submitted":    sum(1 for f in items if f.status == FeedbackStatus.SUBMITTED),
                "acknowledged": sum(1 for f in items if f.status == FeedbackStatus.ACKNOWLEDGED),
                "in_review":    sum(1 for f in items if f.status == FeedbackStatus.IN_REVIEW),
                "escalated":    sum(1 for f in items if f.status == FeedbackStatus.ESCALATED),
                "resolved":     sum(1 for f in items if f.status == FeedbackStatus.RESOLVED),
                "appealed":     sum(1 for f in items if f.status == FeedbackStatus.APPEALED),
                "dismissed":    sum(1 for f in items if f.status == FeedbackStatus.DISMISSED),
                "closed":       sum(1 for f in items if f.status == FeedbackStatus.CLOSED),
                "open":         sum(1 for f in items if f.status in _OPEN_ST),
            },
            "resolution_rate":   self._res_rate(items),
            "appeal_rate":       round(sum(1 for f in items if f.status == FeedbackStatus.APPEALED) / len(resolved) * 100, 1) if resolved else 0.0,
            "dismissal_rate":    round(sum(1 for f in items if f.status == FeedbackStatus.DISMISSED) / len(terminal) * 100, 1) if terminal else 0.0,
            "avg_ack_hours":     self._avg_h(items, "submitted_at", "acknowledged_at"),
            "avg_resolve_hours": self._avg_h(items, "submitted_at", "resolved_at"),
            "avg_close_hours":   self._avg_h(items, "submitted_at", "closed_at"),
            "time_unit":         time_unit,
            "custom_seconds":    custom_seconds if time_unit == "custom" else None,
            "timing": {
                "acknowledgement": self._timing_stats_multi(items, "submitted_at", "acknowledged_at", time_unit, custom_seconds),
                "resolution":       self._timing_stats_multi(items, "submitted_at", "resolved_at",     time_unit, custom_seconds),
                "close":            self._timing_stats_multi(items, "submitted_at", "closed_at",        time_unit, custom_seconds),
            },
            "sla_by_priority":   sla_by_priority,
            "sla_breach_count":  len(breaches),
            "by_status":         self._by_status(items),
            "by_priority":       self._by_priority(items),
            "by_level":          self._by_level(items),
            "by_channel":        self._by_channel(items),
            "by_submission_method": self._by_method(items),
            "by_lga":            self._by_lga(items),
            "by_region":         self._by_region(items),
            "by_district":       self._by_district(items),
            "by_ward":           self._by_ward(items),
            "escalation_breakdown": escalation_breakdown,
            "recent_breaches":   breaches,
        }

    async def suggestions(
        self, project_id=None, from_date=None, to_date=None,
        stage_id=None,
        region=None, district=None, lga=None, ward=None, mtaa=None,
        channel=None, submission_method=None, status=None,
        time_unit: str = "hours",
        custom_seconds: int = 3600,
    ) -> dict:
        from_dt, to_dt, _ = self._dr(from_date, to_date)
        items = await self.repo.list_suggestions(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )
        items = self._filter(items, stage_id=stage_id,
                             channel=channel, submission_method=submission_method,
                             status=status)
        terminal = [f for f in items if f.status in _TERM_ST]
        actioned = [f for f in items if f.status == FeedbackStatus.ACTIONED]
        noted    = [f for f in items if f.status == FeedbackStatus.NOTED]
        return {
            "project_id": str(project_id) if project_id else None,
            "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "counts": {
                "total":        len(items),
                "submitted":    sum(1 for f in items if f.status == FeedbackStatus.SUBMITTED),
                "acknowledged": sum(1 for f in items if f.status == FeedbackStatus.ACKNOWLEDGED),
                "in_review":    sum(1 for f in items if f.status == FeedbackStatus.IN_REVIEW),
                "actioned":     len(actioned),
                "noted":        len(noted),
                "dismissed":    sum(1 for f in items if f.status == FeedbackStatus.DISMISSED),
                "closed":       sum(1 for f in items if f.status == FeedbackStatus.CLOSED),
                "open":         sum(1 for f in items if f.status in _OPEN_ST),
            },
            "action_rate":    round(len(actioned) / len(terminal) * 100, 1) if terminal else 0.0,
            "noted_rate":     round(len(noted) / len(terminal) * 100, 1) if terminal else 0.0,
            "dismissal_rate": round(sum(1 for f in items if f.status == FeedbackStatus.DISMISSED) / len(terminal) * 100, 1) if terminal else 0.0,
            "avg_ack_hours":     self._avg_h(items, "submitted_at", "acknowledged_at"),
            "avg_resolve_hours": self._avg_h(items, "submitted_at", "resolved_at"),
            "time_unit":         time_unit,
            "custom_seconds":    custom_seconds if time_unit == "custom" else None,
            "timing": {
                "acknowledgement": self._timing_stats_multi(items, "submitted_at", "acknowledged_at", time_unit, custom_seconds),
                "resolution":       self._timing_stats_multi(items, "submitted_at", "resolved_at",     time_unit, custom_seconds),
            },
            "by_status":  self._by_status(items),
            "by_channel": self._by_channel(items),
            "by_submission_method": self._by_method(items),
            "by_lga":     self._by_lga(items),
            "by_region":  self._by_region(items),
            "by_district": self._by_district(items),
            "by_ward":    self._by_ward(items),
        }

    # ── Suggestion performance helpers ───────────────────────────────────────

    def _by_category(self, items) -> list:
        """Group by category_def name or category enum value."""
        c = {}
        for f in items:
            key = f.category.value if f.category else "uncategorised"
            if key not in c:
                c[key] = {"category": key, "total": 0, "actioned": 0, "noted": 0,
                          "open": 0, "dismissed": 0}
            c[key]["total"] += 1
            if f.status == FeedbackStatus.ACTIONED:
                c[key]["actioned"] += 1
            elif f.status == FeedbackStatus.NOTED:
                c[key]["noted"] += 1
            elif f.status in _OPEN_ST:
                c[key]["open"] += 1
            elif f.status == FeedbackStatus.DISMISSED:
                c[key]["dismissed"] += 1
        # Add action_rate per category
        for row in c.values():
            terminal = row["actioned"] + row["noted"] + row["dismissed"]
            row["action_rate"] = round(row["actioned"] / terminal * 100, 1) if terminal else 0.0
        return sorted(c.values(), key=lambda x: -x["total"])

    def _by_stage(self, items) -> list:
        c = {}
        for f in items:
            key = str(f.stage_id) if f.stage_id else "no_stage"
            c[key] = c.get(key, 0) + 1
        return sorted([{"stage_id": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _by_subproject(self, items) -> list:
        c = {}
        for f in items:
            key = str(f.subproject_id) if hasattr(f, "subproject_id") and f.subproject_id else "no_subproject"
            c[key] = c.get(key, 0) + 1
        return sorted([{"subproject_id": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _by_stakeholder(self, items) -> list:
        c = {}
        for f in items:
            key = str(f.submitted_by_stakeholder_id) if f.submitted_by_stakeholder_id else "anonymous_or_direct"
            c[key] = c.get(key, 0) + 1
        return sorted([{"stakeholder_id": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _by_day(self, items) -> list:
        c = {}
        for f in items:
            day = f.submitted_at.strftime("%Y-%m-%d") if f.submitted_at else "unknown"
            c[day] = c.get(day, 0) + 1
        return [{"date": k, "count": v} for k, v in sorted(c.items())]

    def _implementation_time_hours(self, f) -> float | None:
        """
        Time from submitted_at → resolved_at for ACTIONED suggestions.
        resolved_at is set when the PIU records the resolution (marks as ACTIONED).
        """
        if f.submitted_at and f.resolved_at:
            return round((f.resolved_at - f.submitted_at).total_seconds() / 3600, 2)
        return None

    def _stakeholder_implementation_stats(self, actioned_items) -> list:
        """
        Per-stakeholder: count of actioned suggestions + average implementation time.
        """
        stk: dict = {}
        for f in actioned_items:
            sid = str(f.submitted_by_stakeholder_id) if f.submitted_by_stakeholder_id else "anonymous"
            if sid not in stk:
                stk[sid] = {"stakeholder_id": sid, "actioned_count": 0, "impl_hours": []}
            stk[sid]["actioned_count"] += 1
            h = self._implementation_time_hours(f)
            if h is not None:
                stk[sid]["impl_hours"].append(h)

        rows = []
        for sid, d in stk.items():
            hrs = d["impl_hours"]
            rows.append({
                "stakeholder_id":          sid,
                "actioned_count":          d["actioned_count"],
                "avg_implementation_hours": round(sum(hrs) / len(hrs), 1) if hrs else None,
                "min_implementation_hours": round(min(hrs), 1) if hrs else None,
                "max_implementation_hours": round(max(hrs), 1) if hrs else None,
                "implementation_times_measured": len(hrs),
            })
        return sorted(rows, key=lambda x: -x["actioned_count"])

    def _category_implementation_stats(self, actioned_items) -> list:
        """Per-category implementation time stats for ACTIONED suggestions."""
        cats: dict = {}
        for f in actioned_items:
            key = f.category.value if f.category else "uncategorised"
            if key not in cats:
                cats[key] = {"category": key, "actioned_count": 0, "impl_hours": []}
            cats[key]["actioned_count"] += 1
            h = self._implementation_time_hours(f)
            if h is not None:
                cats[key]["impl_hours"].append(h)

        rows = []
        for cat, d in cats.items():
            hrs = d["impl_hours"]
            rows.append({
                "category":                   cat,
                "actioned_count":             d["actioned_count"],
                "avg_implementation_hours":   round(sum(hrs) / len(hrs), 1) if hrs else None,
                "min_implementation_hours":   round(min(hrs), 1) if hrs else None,
                "max_implementation_hours":   round(max(hrs), 1) if hrs else None,
                "implementation_times_measured": len(hrs),
            })
        return sorted(rows, key=lambda x: -x["actioned_count"])

    async def suggestion_performance(
        self,
        project_id=None,
        from_date=None,
        to_date=None,
        stage_id=None,
        subproject_id=None,
        stakeholder_id=None,
        category=None,
        region=None,
        district=None,
        lga=None,
        ward=None,
        mtaa=None,
        channel=None,
        submission_method=None,
        status=None,
        time_unit: str = "hours",
        custom_seconds: int = 3600,
    ) -> dict:
        """
        Comprehensive suggestion performance report.

        Covers:
          · Rate of suggestions by location (region, district, lga, ward, mtaa)
          · Rate by category (most/least submitted, most/least implemented)
          · Rate by day (submission trend)
          · Rate by stage and sub-project
          · Rate by stakeholder (who submits most)
          · Implementation tracking: time from submitted → actioned per suggestion
          · Average implementation time per stakeholder
          · Average implementation time per category
          · Overall action_rate, noted_rate, dismissal_rate
          · Pending (open) suggestions count
        """
        from_dt, to_dt, now = self._dr(from_date, to_date)

        items = await self.repo.list_suggestions(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )

        # Apply in-memory filters
        if stage_id:
            items = [f for f in items if str(f.stage_id) == str(stage_id)]
        if subproject_id:
            items = [f for f in items
                     if hasattr(f, "subproject_id") and str(getattr(f, "subproject_id", "")) == str(subproject_id)]
        if stakeholder_id:
            items = [f for f in items
                     if str(f.submitted_by_stakeholder_id or "") == str(stakeholder_id)]
        if category:
            items = [f for f in items if (f.category.value if f.category else "") == category]
        if channel:
            items = [f for f in items if f.channel.value == channel]
        if submission_method:
            items = [f for f in items if (f.submission_method.value if f.submission_method else "") == submission_method]
        if status:
            items = [f for f in items if f.status.value == status]

        total    = len(items)
        actioned = [f for f in items if f.status == FeedbackStatus.ACTIONED]
        noted    = [f for f in items if f.status == FeedbackStatus.NOTED]
        open_s   = [f for f in items if f.status in _OPEN_ST]
        dismissed = [f for f in items if f.status == FeedbackStatus.DISMISSED]
        terminal = [f for f in items if f.status in _TERM_ST]

        # Implementation time stats across all actioned suggestions
        impl_hours = [h for f in actioned if (h := self._implementation_time_hours(f)) is not None]
        avg_impl_h = round(sum(impl_hours) / len(impl_hours), 1) if impl_hours else None
        min_impl_h = round(min(impl_hours), 1) if impl_hours else None
        max_impl_h = round(max(impl_hours), 1) if impl_hours else None

        return {
            "project_id":  str(project_id) if project_id else None,
            "date_range":  {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "filters_applied": {
                "stage_id":        str(stage_id) if stage_id else None,
                "subproject_id":   str(subproject_id) if subproject_id else None,
                "stakeholder_id":  str(stakeholder_id) if stakeholder_id else None,
                "category":        category,
                "region":          region,
                "district":        district,
                "lga":             lga,
                "ward":            ward,
                "mtaa":            mtaa,
                "channel":         channel,
                "status":          status,
            },

            # ── Volume counts ───────────────────────────────────────────────
            "counts": {
                "total":        total,
                "submitted":    sum(1 for f in items if f.status == FeedbackStatus.SUBMITTED),
                "acknowledged": sum(1 for f in items if f.status == FeedbackStatus.ACKNOWLEDGED),
                "in_review":    sum(1 for f in items if f.status == FeedbackStatus.IN_REVIEW),
                "actioned":     len(actioned),
                "noted":        len(noted),
                "dismissed":    len(dismissed),
                "closed":       sum(1 for f in items if f.status == FeedbackStatus.CLOSED),
                "open":         len(open_s),
            },

            # ── Rates ───────────────────────────────────────────────────────
            "rates": {
                "action_rate_pct":    round(len(actioned) / len(terminal) * 100, 1) if terminal else 0.0,
                "noted_rate_pct":     round(len(noted) / len(terminal) * 100, 1) if terminal else 0.0,
                "dismissal_rate_pct": round(len(dismissed) / len(terminal) * 100, 1) if terminal else 0.0,
                "open_rate_pct":      round(len(open_s) / total * 100, 1) if total else 0.0,
            },

            # ── Response times — primary unit + all standard units ────────
            "time_unit":     time_unit,
            "custom_seconds": custom_seconds if time_unit == "custom" else None,
            "response_times": {
                "avg_acknowledgement_hours": self._avg_h(items, "submitted_at", "acknowledged_at"),
                "avg_resolution_hours":      self._avg_h(items, "submitted_at", "resolved_at"),
                "avg_close_hours":           self._avg_h(items, "submitted_at", "closed_at"),
            },
            "timing": {
                "acknowledgement": self._timing_stats_multi(items, "submitted_at", "acknowledged_at", time_unit, custom_seconds),
                "resolution":      self._timing_stats_multi(items, "submitted_at", "resolved_at",     time_unit, custom_seconds),
                "close":           self._timing_stats_multi(items, "submitted_at", "closed_at",        time_unit, custom_seconds),
            },

            # ── Implementation (ACTIONED suggestions only) ──────────────────
            "implementation": {
                "total_actioned":             len(actioned),
                "with_timing_data":           len(impl_hours),
                "avg_implementation_hours":   avg_impl_h,
                "avg_implementation_days":    round(avg_impl_h / 24, 1) if avg_impl_h else None,
                "min_implementation_hours":   min_impl_h,
                "max_implementation_hours":   max_impl_h,
                # Timing in requested unit
                "timing": self._timing_stats_multi(actioned, "submitted_at", "resolved_at", time_unit, custom_seconds),
                "by_stakeholder": self._stakeholder_implementation_stats(actioned),
                "by_category":    self._category_implementation_stats(actioned),
            },

            # ── Dimensional breakdowns ───────────────────────────────────────
            "by_location": {
                "by_region":   self._by_region(items),
                "by_district": self._by_district(items),
                "by_lga":      self._by_lga(items),
                "by_ward":     self._by_ward(items),
                "by_mtaa":     self._by_mtaa(items),
            },
            "by_category":    self._by_category(items),
            "by_day":         self._by_day(items),
            "by_stage":       self._by_stage(items),
            "by_subproject":  self._by_subproject(items),
            "by_stakeholder": self._by_stakeholder(items),
            "by_channel":     self._by_channel(items),
            "by_status":      self._by_status(items),
        }

    async def suggestion_performance_detailed(
        self,
        project_id=None,
        from_date=None,
        to_date=None,
        stage_id=None,
        subproject_id=None,
        stakeholder_id=None,
        category=None,
        region=None,
        district=None,
        lga=None,
        ward=None,
        mtaa=None,
        group_location_by: str = "lga",
    ) -> dict:
        """
        Extended suggestion performance report.

        Adds on top of the base suggestions() method:
          · daily_rate:         submissions per day in the period
          · by_category:        count + action_rate per category
          · by_location:        grouped by region/district/lga/ward/mtaa
          · by_stakeholder:     top submitters with avg implementation time
          · by_stage:           count per stage
          · by_subproject:      count per sub-project
          · implementation_time: avg/min/max/median hours to implement
        """
        from_dt, to_dt, now = self._dr(from_date, to_date)

        # Base items for in-memory stats
        items = await self.repo.list_suggestions(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )
        if stage_id:
            items = [f for f in items if str(f.stage_id) == str(stage_id)]
        if subproject_id:
            items = [f for f in items if str(getattr(f, "subproject_id", None)) == str(subproject_id)]
        if stakeholder_id:
            items = [f for f in items if str(f.submitted_by_stakeholder_id) == str(stakeholder_id)]
        if category:
            items = [f for f in items if f.category and category.lower() in f.category.value.lower()]

        terminal = [f for f in items if f.status in _TERM_ST]
        actioned  = [f for f in items if f.status == FeedbackStatus.ACTIONED]
        noted     = [f for f in items if f.status == FeedbackStatus.NOTED]

        # DB queries for aggregates
        import uuid as _uuid
        pid = _uuid.UUID(str(project_id)) if project_id else None
        sid = _uuid.UUID(str(stage_id)) if stage_id else None
        spid = _uuid.UUID(str(subproject_id)) if subproject_id else None
        skid = _uuid.UUID(str(stakeholder_id)) if stakeholder_id else None

        daily          = await self.repo.suggestion_daily_rate(pid, from_dt, to_dt, spid, sid, lga, region, district, ward, category)
        by_category    = await self.repo.suggestion_by_category(pid, from_dt, to_dt, spid, sid, lga, region)
        by_location    = await self.repo.suggestion_by_location(pid, from_dt, to_dt, group_location_by, spid, sid)
        by_stakeholder = await self.repo.suggestion_by_stakeholder(pid, from_dt, to_dt, spid, sid)
        impl_times     = await self.repo.suggestion_implementation_times(pid, from_dt, to_dt, spid, sid, skid, category, lga, region)

        # Stage breakdown from in-memory items
        by_stage = {}
        for f in items:
            k = str(f.stage_id) if f.stage_id else "no_stage"
            by_stage[k] = by_stage.get(k, 0) + 1

        # Sub-project breakdown
        by_sp = {}
        for f in items:
            k = str(getattr(f, "subproject_id", None) or "no_subproject")
            by_sp[k] = by_sp.get(k, 0) + 1

        # Daily average rate
        total_days = max((to_dt - from_dt).days, 1)
        avg_per_day = round(len(items) / total_days, 2)

        return {
            "project_id":   str(project_id) if project_id else None,
            "stage_id":     str(stage_id) if stage_id else None,
            "subproject_id":str(subproject_id) if subproject_id else None,
            "stakeholder_id":str(stakeholder_id) if stakeholder_id else None,
            "date_range":   {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "summary": {
                "total":              len(items),
                "actioned":           len(actioned),
                "noted":              len(noted),
                "open":               sum(1 for f in items if f.status in _OPEN_ST),
                "dismissed":          sum(1 for f in items if f.status == FeedbackStatus.DISMISSED),
                "action_rate":        round(len(actioned) / len(terminal) * 100, 1) if terminal else 0.0,
                "noted_rate":         round(len(noted) / len(terminal) * 100, 1) if terminal else 0.0,
                "avg_per_day":        avg_per_day,
                "avg_ack_hours":      self._avg_h(items, "submitted_at", "acknowledged_at"),
                "avg_resolve_hours":  self._avg_h(items, "submitted_at", "resolved_at"),
                "avg_implement_hours":impl_times.get("avg_hours"),
                "min_implement_hours":impl_times.get("min_hours"),
                "max_implement_hours":impl_times.get("max_hours"),
                "median_implement_hours": impl_times.get("median_hours"),
                "total_implemented":  impl_times.get("total_implemented", 0),
            },
            "daily_rate":    daily,
            "by_category":   by_category,
            "by_location":   by_location,
            "by_stakeholder":by_stakeholder,
            "by_stage":      [{"stage_id": k, "count": v} for k, v in by_stage.items()],
            "by_subproject": [{"subproject_id": k, "count": v} for k, v in by_sp.items()],
            "implementation_time": impl_times,
        }

    async def applause(
        self, project_id=None, from_date=None, to_date=None,
        stage_id=None,
        region=None, district=None, lga=None, ward=None, mtaa=None,
        channel=None, submission_method=None,
    ) -> dict:
        from_dt, to_dt, _ = self._dr(from_date, to_date)
        items = await self.repo.list_applause(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )
        items = self._filter(items, stage_id=stage_id,
                             channel=channel, submission_method=submission_method)
        total = len(items)
        acked = sum(1 for f in items if f.acknowledged_at)
        return {
            "project_id": str(project_id) if project_id else None,
            "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "counts": {
                "total":        total,
                "acknowledged": acked,
                "closed":       sum(1 for f in items if f.status == FeedbackStatus.CLOSED),
                "open":         sum(1 for f in items if f.status in _OPEN_ST),
            },
            "acknowledgement_rate": round(acked / total * 100, 1) if total else 0.0,
            "avg_ack_hours":        self._avg_h(items, "submitted_at", "acknowledged_at"),
            "by_channel":           self._by_channel(items),
            "by_submission_method": self._by_method(items),
            "by_lga":               self._by_lga(items),
            "by_region":            self._by_region(items),
            "by_district":          self._by_district(items),
            "by_ward":              self._by_ward(items),
        }

    # ── Applause time conversion helpers ─────────────────────────────────────

    def _convert_time(self, seconds, unit, custom_seconds=3600):
        """Convert a seconds value to the requested time unit."""
        if seconds is None:
            return None
        d = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}.get(unit, custom_seconds)
        return round(seconds / d, 3)

    def _ack_stats_in_unit(self, items, unit, custom_seconds=3600):
        """
        Acknowledgement time statistics in the given unit across a list of items.
        unit: "seconds" | "minutes" | "hours" | "days" | "custom"
        custom_seconds: divisor when unit = "custom" (e.g. 1800 = per half-hour)
        """
        d = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}.get(unit, custom_seconds)
        values = [
            round((f.acknowledged_at - f.submitted_at).total_seconds() / d, 3)
            for f in items
            if f.submitted_at and f.acknowledged_at
        ]
        if not values:
            return {"unit": unit, "count_with_data": 0,
                    "avg": None, "min": None, "max": None, "median": None}
        sv = sorted(values)
        n  = len(sv)
        median = round(
            (sv[n // 2 - 1] + sv[n // 2]) / 2 if n % 2 == 0 else sv[n // 2], 3
        )
        return {
            "unit":            unit,
            "count_with_data": n,
            "avg":    round(sum(values) / n, 3),
            "min":    round(sv[0], 3),
            "max":    round(sv[-1], 3),
            "median": median,
        }

    def _applause_by_stage(self, items):
        c = {}
        for f in items:
            key = str(f.stage_id) if f.stage_id else "no_stage"
            c[key] = c.get(key, 0) + 1
        return sorted([{"stage_id": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _applause_by_subproject(self, items):
        c = {}
        for f in items:
            sp = getattr(f, "subproject_id", None)
            key = str(sp) if sp else "no_subproject"
            c[key] = c.get(key, 0) + 1
        return sorted([{"subproject_id": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _applause_by_stakeholder(self, items):
        c = {}
        for f in items:
            key = str(f.submitted_by_stakeholder_id) if f.submitted_by_stakeholder_id else "anonymous"
            c[key] = c.get(key, 0) + 1
        return sorted([{"stakeholder_id": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])

    def _timing_in_unit(self, seconds, unit, custom_divisor=3600):
        """Convert a raw seconds value to the requested unit."""
        if seconds is None:
            return None
        d = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}.get(unit, custom_divisor)
        return round(seconds / d, 3)

    def _timing_stats_multi(self, items, start_field, end_field, unit, custom_divisor=3600):
        """
        Compute timing stats (avg/min/max/median) between two datetime fields
        for a list of feedback items, expressed in the given unit.

        Returns a dict with:
          unit, count_with_data, avg, min, max, median
        Plus the same stats in all four standard units (seconds/minutes/hours/days)
        under 'all_units'.
        """
        divs = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}
        d    = divs.get(unit, custom_divisor)

        # Collect raw seconds between start and end
        raw = [
            (getattr(f, end_field) - getattr(f, start_field)).total_seconds()
            for f in items
            if getattr(f, start_field) and getattr(f, end_field)
        ]
        if not raw:
            empty = {"unit": unit, "count_with_data": 0,
                     "avg": None, "min": None, "max": None, "median": None}
            return {
                **empty,
                "all_units": {u: {"unit": u, "count_with_data": 0,
                                  "avg": None, "min": None,
                                  "max": None, "median": None}
                              for u in divs},
            }

        def _stats(div, u):
            vals = sorted([round(s / div, 3) for s in raw])
            n = len(vals)
            med = round(
                (vals[n//2 - 1] + vals[n//2]) / 2 if n % 2 == 0 else vals[n//2], 3
            )
            return {
                "unit":            u,
                "count_with_data": n,
                "avg":    round(sum(vals) / n, 3),
                "min":    vals[0],
                "max":    vals[-1],
                "median": med,
            }

        primary = _stats(d, unit)
        return {
            **primary,
            "all_units": {u: _stats(dv, u) for u, dv in divs.items()},
        }

    def _applause_by_category(self, items):
        cats = {}
        for f in items:
            key = f.category.value if f.category else "uncategorised"
            if key not in cats:
                cats[key] = {"category": key, "count": 0, "acked": 0, "ack_seconds": []}
            cats[key]["count"] += 1
            if f.acknowledged_at:
                cats[key]["acked"] += 1
                cats[key]["ack_seconds"].append(
                    (f.acknowledged_at - f.submitted_at).total_seconds()
                )
        result = []
        for cat, d in cats.items():
            hrs = [s / 3600 for s in d["ack_seconds"]]
            result.append({
                "category":        cat,
                "count":           d["count"],
                "acked":           d["acked"],
                "ack_rate_pct":    round(d["acked"] / d["count"] * 100, 1) if d["count"] else 0.0,
                "avg_ack_hours":   round(sum(hrs) / len(hrs), 2) if hrs else None,
            })
        return sorted(result, key=lambda x: -x["count"])

    def _applause_stakeholder_ack_stats(self, items, unit, custom_seconds=3600):
        """Per-stakeholder acknowledgement time stats in the requested unit."""
        d_map = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}
        div   = d_map.get(unit, custom_seconds)
        stk   = {}
        for f in items:
            sid = str(f.submitted_by_stakeholder_id) if f.submitted_by_stakeholder_id else "anonymous"
            if sid not in stk:
                stk[sid] = {"stakeholder_id": sid, "count": 0, "values": []}
            stk[sid]["count"] += 1
            if f.acknowledged_at:
                stk[sid]["values"].append(
                    round((f.acknowledged_at - f.submitted_at).total_seconds() / div, 3)
                )
        result = []
        for sid, d in stk.items():
            vs = d["values"]
            result.append({
                "stakeholder_id":         sid,
                "total_submitted":        d["count"],
                "acked_count":            len(vs),
                f"avg_ack_{unit}":        round(sum(vs) / len(vs), 3) if vs else None,
                f"min_ack_{unit}":        round(min(vs), 3) if vs else None,
                f"max_ack_{unit}":        round(max(vs), 3) if vs else None,
                "ack_times_measured":     len(vs),
            })
        return sorted(result, key=lambda x: -x["total_submitted"])

    async def applause_performance(
        self,
        project_id=None,
        from_date=None,
        to_date=None,
        stage_id=None,
        subproject_id=None,
        stakeholder_id=None,
        category=None,
        region=None,
        district=None,
        lga=None,
        ward=None,
        mtaa=None,
        channel=None,
        submission_method=None,
        status=None,
        time_unit: str = "hours",
        custom_seconds: int = 3600,
    ) -> dict:
        """
        Comprehensive applause performance report.

        time_unit controls all timing outputs: "seconds" | "minutes" | "hours" | "days" | "custom"
        custom_seconds: divisor used only when time_unit = "custom" (e.g. 1800 = 30-min periods).

        Covers:
          · Volume counts (total, acknowledged, open, closed)
          · Acknowledgement rate and timing in the requested time_unit
          · All timing stats (avg, min, max, median) in the requested unit
          · All timing stats also provided in seconds, minutes, hours, days simultaneously
          · By location (region → district → lga → ward → mtaa)
          · By category (count + ack_rate + avg ack time per category)
          · By day (daily submission trend)
          · By stage (count per project stage)
          · By sub-project (count per work package)
          · By stakeholder (volume + ack time per stakeholder)
          · By channel
        """
        from_dt, to_dt, now = self._dr(from_date, to_date)

        items = await self.repo.list_applause(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )

        # In-memory filters
        if stage_id:       items = [f for f in items if str(f.stage_id or "") == str(stage_id)]
        if subproject_id:  items = [f for f in items if str(getattr(f, "subproject_id", "") or "") == str(subproject_id)]
        if stakeholder_id: items = [f for f in items if str(f.submitted_by_stakeholder_id or "") == str(stakeholder_id)]
        if category:       items = [f for f in items if (f.category.value if f.category else "") == category]
        if channel:        items = [f for f in items if f.channel.value == channel]
        if submission_method: items = [f for f in items if (f.submission_method.value if f.submission_method else "") == submission_method]
        if status:         items = [f for f in items if f.status.value == status]

        total  = len(items)
        acked  = [f for f in items if f.acknowledged_at]
        open_s = [f for f in items if f.status in _OPEN_ST]
        closed = [f for f in items if f.status == FeedbackStatus.CLOSED]

        # Acknowledgement time — primary unit
        ack_stats = self._ack_stats_in_unit(items, time_unit, custom_seconds)

        # Always also return all standard units for convenience
        all_units = {
            u: self._ack_stats_in_unit(items, u)
            for u in ("seconds", "minutes", "hours", "days")
        }

        # Per-item ack times for the detail log
        ack_items = []
        for f in acked:
            raw_s = (f.acknowledged_at - f.submitted_at).total_seconds()
            div   = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}.get(time_unit, custom_seconds)
            ack_items.append({
                "unique_ref":         f.unique_ref,
                "subject":            f.subject,
                "category":           f.category.value if f.category else None,
                "stakeholder_id":     str(f.submitted_by_stakeholder_id) if f.submitted_by_stakeholder_id else None,
                "stage_id":           str(f.stage_id) if f.stage_id else None,
                "subproject_id":      str(getattr(f, "subproject_id", None) or "") or None,
                "issue_region":       f.issue_region,
                "issue_lga":          f.issue_lga,
                "issue_ward":         f.issue_ward,
                "submitted_at":       f.submitted_at.isoformat(),
                "acknowledged_at":    f.acknowledged_at.isoformat(),
                f"ack_{time_unit}":   round(raw_s / div, 3),
                "ack_seconds":        round(raw_s, 0),
                "ack_minutes":        round(raw_s / 60, 2),
                "ack_hours":          round(raw_s / 3600, 2),
                "ack_days":           round(raw_s / 86400, 3),
            })

        return {
            "project_id":     str(project_id) if project_id else None,
            "date_range":     {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "time_unit":      time_unit,
            "custom_seconds": custom_seconds if time_unit == "custom" else None,
            "filters_applied": {
                "stage_id":        str(stage_id) if stage_id else None,
                "subproject_id":   str(subproject_id) if subproject_id else None,
                "stakeholder_id":  str(stakeholder_id) if stakeholder_id else None,
                "category":        category,
                "region":          region, "district": district,
                "lga":             lga, "ward": ward, "mtaa": mtaa,
                "channel":         channel, "status": status,
            },
            "counts": {
                "total":        total,
                "acknowledged": len(acked),
                "open":         len(open_s),
                "closed":       len(closed),
                "submitted":    sum(1 for f in items if f.status == FeedbackStatus.SUBMITTED),
                "in_review":    sum(1 for f in items if f.status == FeedbackStatus.IN_REVIEW),
            },
            "rates": {
                "acknowledgement_rate_pct": round(len(acked) / total * 100, 1) if total else 0.0,
                "open_rate_pct":            round(len(open_s) / total * 100, 1) if total else 0.0,
                "close_rate_pct":           round(len(closed) / total * 100, 1) if total else 0.0,
            },
            # Primary unit stats
            "acknowledgement_time": ack_stats,
            # All standard unit stats simultaneously
            "acknowledgement_time_all_units": all_units,
            # Per-item detail
            "acknowledgement_detail": ack_items,
            # Dimensional breakdowns
            "by_location": {
                "by_region":   self._by_region(items),
                "by_district": self._by_district(items),
                "by_lga":      self._by_lga(items),
                "by_ward":     self._by_ward(items),
                "by_mtaa":     self._by_mtaa(items),
            },
            "by_category":    self._applause_by_category(items),
            "by_day":         self._by_day(items),
            "by_stage":       self._applause_by_stage(items),
            "by_subproject":  self._applause_by_subproject(items),
            "by_stakeholder": self._applause_stakeholder_ack_stats(items, time_unit, custom_seconds),
            "by_channel":     self._by_channel(items),
            "by_status":      self._by_status(items),
        }

    async def channels(self, project_id=None, from_date=None, to_date=None, feedback_type=None) -> dict:
        from_dt, to_dt, _ = self._dr(from_date, to_date)
        items = await self.repo.list_all_for_project(project_id, from_dt, to_dt)
        if feedback_type:
            items = [f for f in items if f.feedback_type.value == feedback_type]
        breakdown: dict = {}
        meth_bkd: dict  = {}
        for f in items:
            ch = f.channel.value
            ft = f.feedback_type.value
            if ch not in breakdown:
                breakdown[ch] = {"channel": ch, "grievance": 0, "suggestion": 0, "applause": 0, "total": 0}
            breakdown[ch][ft] = breakdown[ch].get(ft, 0) + 1
            breakdown[ch]["total"] += 1
            m = f.submission_method.value if f.submission_method else "unknown"
            if m not in meth_bkd:
                meth_bkd[m] = {"method": m, "grievance": 0, "suggestion": 0, "applause": 0, "total": 0}
            meth_bkd[m][ft] = meth_bkd[m].get(ft, 0) + 1
            meth_bkd[m]["total"] += 1
        ai = [f for f in items if f.submission_method == SubmissionMethod.AI_CONVERSATION]
        return {
            "project_id": str(project_id) if project_id else None,
            "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "total":      len(items),
            "by_channel": sorted(breakdown.values(), key=lambda x: -x["total"]),
            "by_submission_method": sorted(meth_bkd.values(), key=lambda x: -x["total"]),
            "ai_conversation": {
                "total":      len(ai),
                "grievance":  sum(1 for f in ai if f.feedback_type == FeedbackType.GRIEVANCE),
                "suggestion": sum(1 for f in ai if f.feedback_type == FeedbackType.SUGGESTION),
                "applause":   sum(1 for f in ai if f.feedback_type == FeedbackType.APPLAUSE),
            },
        }

    async def grievance_log(
        self, project_id=None, from_date=None, to_date=None,
        region=None, district=None, lga=None, ward=None, mtaa=None,
        priority=None, channel=None, status=None,
        skip=0, limit=100,
    ) -> dict:
        from_dt, to_dt, now = self._dr(from_date, to_date, default_days=90)
        items = await self.repo.list_grievances(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )
        items = self._filter(items, priority=priority, channel=channel, status=status)
        paginated = items[skip:skip + limit]
        return {
            "project_id": str(project_id) if project_id else None,
            "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "total": len(items), "returned": len(paginated),
            "items": [self._log_row(f, now) for f in paginated],
        }

    async def suggestion_log(
        self, project_id=None, from_date=None, to_date=None,
        region=None, district=None, lga=None, ward=None, mtaa=None,
        channel=None, status=None, skip=0, limit=100,
    ) -> dict:
        from_dt, to_dt, now = self._dr(from_date, to_date, default_days=90)
        items = await self.repo.list_suggestions(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )
        items = self._filter(items, channel=channel, status=status)
        paginated = items[skip:skip + limit]
        return {
            "project_id": str(project_id) if project_id else None,
            "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "total": len(items), "returned": len(paginated),
            "items": [self._log_row(f, now) for f in paginated],
        }

    async def applause_log(
        self, project_id=None, from_date=None, to_date=None,
        region=None, district=None, lga=None, ward=None, mtaa=None,
        channel=None, skip=0, limit=100,
    ) -> dict:
        from_dt, to_dt, now = self._dr(from_date, to_date, default_days=90)
        items = await self.repo.list_applause(
            project_id, from_dt, to_dt,
            region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        )
        items = self._filter(items, channel=channel)
        paginated = items[skip:skip + limit]
        return {
            "project_id": str(project_id) if project_id else None,
            "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "total": len(items), "returned": len(paginated),
            "items": [self._log_row(f, now) for f in paginated],
        }

    async def summary(self, project_id: uuid.UUID) -> dict:
        by_type, by_status = await self.repo.counts_by_type_and_status(project_id)
        open_count = await self.repo.count_open(project_id)
        return {
            "project_id": str(project_id),
            "open_count": open_count,
            "by_type":   [{"type": r[0], "count": r[1]} for r in by_type],
            "by_status": [{"type": r[0], "status": r[1], "count": r[2]} for r in by_status],
        }

    async def overdue(self, project_id=None, priority=None) -> dict:
        now   = datetime.now(timezone.utc)
        items = await self.repo.list_overdue(project_id, now)
        if priority:
            items = [f for f in items if f.priority and f.priority.value == priority]
        return {
            "overdue_count": len(items),
            "items": [
                {
                    "unique_ref":      f.unique_ref,
                    "project_id":      str(f.project_id),
                    "subject":         f.subject,
                    "priority":        f.priority.value if f.priority else None,
                    "current_level":   f.current_level.value if f.current_level else None,
                    "status":          f.status.value,
                    "channel":         f.channel.value,
                    "target_resolution": f.target_resolution_date.isoformat(),
                    "days_overdue":    (now - f.target_resolution_date).days,
                    "assigned_to":     str(f.assigned_to_user_id) if f.assigned_to_user_id else None,
                }
                for f in items
            ],
        }

    # ── Filter helper (pure Python) ───────────────────────────────────────────

    def _filter(
        self, items,
        stage_id=None,
        # ── Tanzania admin hierarchy location filters ─────────────────────────
        region=None, district=None, lga=None, ward=None, mtaa=None,
        # ── Other filters ─────────────────────────────────────────────────────
        priority=None, channel=None, submission_method=None, status=None, **_
    ):
        """
        Pure-Python filter applied after DB fetch.
        All location filters use case-insensitive partial matching — consistent
        with the ilike() used in the repository layer.
        """
        if stage_id:          items = [f for f in items if str(f.stage_id) == str(stage_id)]
        if region:            items = [f for f in items if f.issue_region   and region.lower()   in f.issue_region.lower()]
        if district:          items = [f for f in items if f.issue_district and district.lower() in f.issue_district.lower()]
        if lga:               items = [f for f in items if f.issue_lga      and lga.lower()      in f.issue_lga.lower()]
        if ward:              items = [f for f in items if f.issue_ward     and ward.lower()     in f.issue_ward.lower()]
        if mtaa:              items = [f for f in items if f.issue_mtaa     and mtaa.lower()     in f.issue_mtaa.lower()]
        if priority:          items = [f for f in items if f.priority         and f.priority.value         == priority]
        if channel:           items = [f for f in items if f.channel          and f.channel.value          == channel]
        if submission_method: items = [f for f in items if f.submission_method and f.submission_method.value == submission_method]
        if status:            items = [f for f in items if f.status.value == status]
        return items
