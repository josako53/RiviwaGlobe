# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  schemas/applause_performance.py
# ───────────────────────────────────────────────────────────────────────────
"""
schemas/applause_performance.py
────────────────────────────────────────────────────────────────────────────
Pydantic response schemas for the applause performance report.

GET /api/v1/reports/applause-performance
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


# ── Time unit stats block ──────────────────────────────────────────────────

class AckTimeStats(BaseModel):
    """
    Acknowledgement time statistics in a single time unit.

    `unit` tells the client which unit all numeric values are expressed in.
    E.g. if unit = "hours", avg = 2.5 means 2.5 hours.
    """
    model_config = ConfigDict(from_attributes=False)

    unit:            str              # "seconds" | "minutes" | "hours" | "days" | "custom"
    count_with_data: int              # items that have both submitted_at and acknowledged_at
    avg:             Optional[float] = None
    min:             Optional[float] = None
    max:             Optional[float] = None
    median:          Optional[float] = None


class AckTimeAllUnits(BaseModel):
    """
    Acknowledgement time stats expressed in all four standard units simultaneously.
    The client can pick whichever unit is most useful for display without
    making additional requests.
    """
    model_config = ConfigDict(from_attributes=False)

    seconds: AckTimeStats
    minutes: AckTimeStats
    hours:   AckTimeStats
    days:    AckTimeStats


# ── Per-item detail row ────────────────────────────────────────────────────

class ApplauseAckDetailRow(BaseModel):
    """
    One row in the per-item acknowledgement detail list.
    Every acknowledged applause item appears here with its timing in all units.
    """
    model_config = ConfigDict(from_attributes=False)

    unique_ref:       str
    subject:          str
    category:         Optional[str]  = None
    stakeholder_id:   Optional[str]  = None
    stage_id:         Optional[str]  = None
    subproject_id:    Optional[str]  = None
    issue_region:     Optional[str]  = None
    issue_lga:        Optional[str]  = None
    issue_ward:       Optional[str]  = None
    submitted_at:     str
    acknowledged_at:  str
    ack_seconds:      float
    ack_minutes:      float
    ack_hours:        float
    ack_days:         float
    # Dynamic field — also present as ack_{time_unit} in the raw dict
    # (included in extra fields via model_config extra="allow")
    model_config = ConfigDict(from_attributes=False, extra="allow")


# ── Dimensional breakdown rows ─────────────────────────────────────────────

class AppCategoryRow(BaseModel):
    """Applause count + acknowledgement rate per category."""
    model_config = ConfigDict(from_attributes=False)

    category:      str
    count:         int
    acked:         int
    ack_rate_pct:  float
    avg_ack_hours: Optional[float] = None


class AppDayRow(BaseModel):
    """Submission count per calendar day — for trend charts."""
    model_config = ConfigDict(from_attributes=False)

    date:  str    # "YYYY-MM-DD"
    count: int


class AppStageRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    stage_id: str
    count:    int


class AppSubProjectRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    subproject_id: str
    count:         int


class AppStakeholderRow(BaseModel):
    """
    Per-stakeholder: volume + acknowledgement timing in the requested unit.
    Dynamic field names (avg_ack_{unit}, min_ack_{unit}, max_ack_{unit})
    are included via extra="allow".
    """
    model_config = ConfigDict(from_attributes=False, extra="allow")

    stakeholder_id:       str
    total_submitted:      int
    acked_count:          int
    ack_times_measured:   int


# ── Rates and counts ───────────────────────────────────────────────────────

class ApplauseCountsBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    total:        int
    acknowledged: int
    open:         int
    closed:       int
    submitted:    int
    in_review:    int


class ApplauseRatesBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    acknowledgement_rate_pct: float
    open_rate_pct:            float
    close_rate_pct:           float


# ── Location block ─────────────────────────────────────────────────────────

class AppLocationBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    by_region:   List[Dict[str, Any]] = []
    by_district: List[Dict[str, Any]] = []
    by_lga:      List[Dict[str, Any]] = []
    by_ward:     List[Dict[str, Any]] = []
    by_mtaa:     List[Dict[str, Any]] = []


# ── Filters applied ────────────────────────────────────────────────────────

class AppFiltersApplied(BaseModel):
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

class ApplausePerformanceResponse(BaseModel):
    """
    Comprehensive applause performance report.

    Returned by GET /api/v1/reports/applause-performance.

    Key design: all acknowledgement timing is returned in BOTH the
    requested `time_unit` AND all four standard units simultaneously
    (seconds, minutes, hours, days) — so the client never needs to
    convert or make extra requests.

    Structure:
      counts                        — total, acknowledged, open, closed
      rates                         — acknowledgement rate, open rate, close rate
      acknowledgement_time          — stats in the requested time_unit
      acknowledgement_time_all_units — stats in all four standard units
      acknowledgement_detail        — per-item list with individual timings
      by_location                   — region / district / lga / ward / mtaa
      by_category                   — count + ack_rate + avg ack time per category
      by_day                        — daily submission trend
      by_stage                      — count per project stage
      by_subproject                 — count per sub-project / work package
      by_stakeholder                — volume + ack timing per stakeholder
      by_channel                    — intake channel breakdown
      by_status                     — full status distribution
    """
    model_config = ConfigDict(from_attributes=False)

    project_id:      Optional[str] = None
    date_range:      Dict[str, str]
    time_unit:       str            # the primary time unit used in the report
    custom_seconds:  Optional[int] = None   # only set when time_unit = "custom"
    filters_applied: AppFiltersApplied

    counts: ApplauseCountsBlock
    rates:  ApplauseRatesBlock

    acknowledgement_time:            AckTimeStats
    acknowledgement_time_all_units:  AckTimeAllUnits
    acknowledgement_detail:          List[Dict[str, Any]] = []

    by_location:    AppLocationBlock
    by_category:    List[AppCategoryRow]     = []
    by_day:         List[AppDayRow]          = []
    by_stage:       List[AppStageRow]        = []
    by_subproject:  List[AppSubProjectRow]   = []
    by_stakeholder: List[Dict[str, Any]]     = []
    by_channel:     List[Dict[str, Any]]     = []
    by_status:      List[Dict[str, Any]]     = []

    @classmethod
    def from_dict(cls, d: dict) -> "ApplausePerformanceResponse":
        au = d.get("acknowledgement_time_all_units", {})
        return cls(
            project_id=d.get("project_id"),
            date_range=d["date_range"],
            time_unit=d["time_unit"],
            custom_seconds=d.get("custom_seconds"),
            filters_applied=AppFiltersApplied(**d.get("filters_applied", {})),
            counts=ApplauseCountsBlock(**d["counts"]),
            rates=ApplauseRatesBlock(**d["rates"]),
            acknowledgement_time=AckTimeStats(**d["acknowledgement_time"]),
            acknowledgement_time_all_units=AckTimeAllUnits(
                seconds=AckTimeStats(**au.get("seconds", {"unit": "seconds", "count_with_data": 0})),
                minutes=AckTimeStats(**au.get("minutes", {"unit": "minutes", "count_with_data": 0})),
                hours=AckTimeStats(**au.get("hours",   {"unit": "hours",   "count_with_data": 0})),
                days=AckTimeStats(**au.get("days",     {"unit": "days",    "count_with_data": 0})),
            ),
            acknowledgement_detail=d.get("acknowledgement_detail", []),
            by_location=AppLocationBlock(**d.get("by_location", {})),
            by_category=[AppCategoryRow(**r) for r in d.get("by_category", [])],
            by_day=[AppDayRow(**r) for r in d.get("by_day", [])],
            by_stage=[AppStageRow(**r) for r in d.get("by_stage", [])],
            by_subproject=[AppSubProjectRow(**r) for r in d.get("by_subproject", [])],
            by_stakeholder=d.get("by_stakeholder", []),
            by_channel=d.get("by_channel", []),
            by_status=d.get("by_status", []),
        )
