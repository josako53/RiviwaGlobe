# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  schemas/grievance_performance.py
# ───────────────────────────────────────────────────────────────────────────
"""
schemas/grievance_performance.py
────────────────────────────────────────────────────────────────────────────
Pydantic response schemas for the comprehensive grievance performance report.

GET /api/v1/reports/grievance-performance
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


# ── Dimensional breakdown rows ─────────────────────────────────────────────

class GrievanceCountsBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    total:        int
    submitted:    int
    acknowledged: int
    in_review:    int
    escalated:    int
    resolved:     int
    appealed:     int
    dismissed:    int
    closed:       int
    open:         int


class GrievanceRatesBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    resolution_rate_pct: float
    dismissal_rate_pct:  float
    appeal_rate_pct:     float
    open_rate_pct:       float


class SLAPriorityRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    priority:              str
    count:                 int
    ack_sla_hours:         int
    resolve_sla_hours:     Optional[int] = None
    ack_compliance_pct:    Optional[float] = None
    res_compliance_pct:    Optional[float] = None
    avg_ack_hours:         Optional[float] = None
    avg_resolve_hours:     Optional[float] = None


class EscalationRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    level:               str
    currently_at_level:  int
    passed_through:      int


class CategoryGrievanceRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    category:          str
    total:             int
    resolved:          int
    dismissed:         int
    open:              int
    resolution_rate:   float


class StakeholderGrievanceRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    stakeholder_id:      str
    count:               int


class StakeholderResolutionRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    stakeholder_id:           str
    resolved_count:           int
    avg_resolution_hours:     Optional[float] = None
    avg_resolution_days:      Optional[float] = None
    min_resolution_hours:     Optional[float] = None
    max_resolution_hours:     Optional[float] = None
    resolution_times_measured: int


class CategoryResolutionRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    category:                 str
    resolved_count:           int
    avg_resolution_hours:     Optional[float] = None
    min_resolution_hours:     Optional[float] = None
    max_resolution_hours:     Optional[float] = None
    resolution_times_measured: int


class ResolutionBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    total_resolved:           int
    with_timing_data:         int
    avg_resolution_hours:     Optional[float] = None
    avg_resolution_days:      Optional[float] = None
    min_resolution_hours:     Optional[float] = None
    max_resolution_hours:     Optional[float] = None
    by_stakeholder:           List[StakeholderResolutionRow] = []
    by_category:              List[CategoryResolutionRow]    = []


class GrievanceResponseTimesBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    avg_acknowledgement_hours: Optional[float] = None
    avg_resolution_hours:      Optional[float] = None
    avg_close_hours:           Optional[float] = None


class DayRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    date:  str
    count: int


class StageRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    stage_id: str
    count:    int


class SubProjectRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    subproject_id: str
    count:         int


class LocationBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    by_region:   List[Dict[str, Any]] = []
    by_district: List[Dict[str, Any]] = []
    by_lga:      List[Dict[str, Any]] = []
    by_ward:     List[Dict[str, Any]] = []
    by_mtaa:     List[Dict[str, Any]] = []


class GrievanceFiltersAppliedBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    stage_id:       Optional[str] = None
    subproject_id:  Optional[str] = None
    stakeholder_id: Optional[str] = None
    category:       Optional[str] = None
    region:         Optional[str] = None
    district:       Optional[str] = None
    lga:            Optional[str] = None
    ward:           Optional[str] = None
    mtaa:           Optional[str] = None
    channel:        Optional[str] = None
    status:         Optional[str] = None


# ── Top-level response ─────────────────────────────────────────────────────

class GrievancePerformanceResponse(BaseModel):
    """
    Comprehensive grievance performance report.

    Returned by GET /api/v1/reports/grievance-performance.

    Structure:
      counts              — volume by status
      rates               — resolution, dismissal, appeal, open rates
      response_times      — avg acknowledgement / resolution / close hours
      resolution          — resolution time stats per stakeholder, per category
      sla_by_priority     — SLA compliance per priority tier
      escalation_breakdown — where grievances sit in the GRM hierarchy
      by_location         — region / district / lga / ward / mtaa breakdown
      by_category         — volumes + resolution rate per category
      by_day              — daily submission trend
      by_stage            — volumes per project stage
      by_subproject       — volumes per sub-project
      by_stakeholder      — volumes per stakeholder
      by_channel          — volumes per intake channel
      by_priority         — volumes per priority
      by_level            — current GRM level distribution
      by_status           — full status distribution
    """
    model_config = ConfigDict(from_attributes=False)

    project_id:           Optional[str] = None
    date_range:           Dict[str, str]
    filters_applied:      GrievanceFiltersAppliedBlock
    counts:               GrievanceCountsBlock
    rates:                GrievanceRatesBlock
    response_times:       GrievanceResponseTimesBlock
    resolution:           ResolutionBlock
    sla_by_priority:      List[SLAPriorityRow]       = []
    escalation_breakdown: List[EscalationRow]         = []
    by_location:          LocationBlock
    by_category:          List[CategoryGrievanceRow]  = []
    by_day:               List[DayRow]                = []
    by_stage:             List[StageRow]              = []
    by_subproject:        List[SubProjectRow]         = []
    by_stakeholder:       List[StakeholderGrievanceRow] = []
    by_channel:           List[Dict[str, Any]]        = []
    by_priority:          List[Dict[str, Any]]        = []
    by_level:             List[Dict[str, Any]]        = []
    by_status:            List[Dict[str, Any]]        = []

    @classmethod
    def from_dict(cls, d: dict) -> "GrievancePerformanceResponse":
        c   = d["counts"]
        r   = d["rates"]
        rt  = d["response_times"]
        res = d["resolution"]
        loc = d["by_location"]
        fa  = d.get("filters_applied", {})

        return cls(
            project_id=d.get("project_id"),
            date_range=d["date_range"],
            filters_applied=GrievanceFiltersAppliedBlock(**fa),
            counts=GrievanceCountsBlock(**c),
            rates=GrievanceRatesBlock(**r),
            response_times=GrievanceResponseTimesBlock(**rt),
            resolution=ResolutionBlock(
                total_resolved            = res["total_resolved"],
                with_timing_data          = res["with_timing_data"],
                avg_resolution_hours      = res.get("avg_resolution_hours"),
                avg_resolution_days       = res.get("avg_resolution_days"),
                min_resolution_hours      = res.get("min_resolution_hours"),
                max_resolution_hours      = res.get("max_resolution_hours"),
                by_stakeholder=[
                    StakeholderResolutionRow(
                        stakeholder_id            = row["stakeholder_id"],
                        resolved_count            = row["resolved_count"],
                        avg_resolution_hours      = row.get("avg_resolution_hours"),
                        avg_resolution_days       = round(row["avg_resolution_hours"] / 24, 1)
                                                    if row.get("avg_resolution_hours") else None,
                        min_resolution_hours      = row.get("min_resolution_hours"),
                        max_resolution_hours      = row.get("max_resolution_hours"),
                        resolution_times_measured = row["resolution_times_measured"],
                    )
                    for row in res.get("by_stakeholder", [])
                ],
                by_category=[
                    CategoryResolutionRow(**row)
                    for row in res.get("by_category", [])
                ],
            ),
            sla_by_priority=[SLAPriorityRow(**row) for row in d.get("sla_by_priority", [])],
            escalation_breakdown=[EscalationRow(**row) for row in d.get("escalation_breakdown", [])],
            by_location=LocationBlock(**loc),
            by_category=[CategoryGrievanceRow(**row) for row in d.get("by_category", [])],
            by_day=[DayRow(**row) for row in d.get("by_day", [])],
            by_stage=[StageRow(**row) for row in d.get("by_stage", [])],
            by_subproject=[SubProjectRow(**row) for row in d.get("by_subproject", [])],
            by_stakeholder=[
                StakeholderGrievanceRow(stakeholder_id=row["stakeholder_id"], count=row["count"])
                for row in d.get("by_stakeholder", [])
            ],
            by_channel=d.get("by_channel", []),
            by_priority=d.get("by_priority", []),
            by_level=d.get("by_level", []),
            by_status=d.get("by_status", []),
        )
