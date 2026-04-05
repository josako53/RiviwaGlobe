# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  schemas/suggestion_performance.py
# ───────────────────────────────────────────────────────────────────────────
"""
schemas/suggestion_performance.py
────────────────────────────────────────────────────────────────────────────
Pydantic response schemas for the suggestion performance report.

GET /api/v1/reports/suggestion-performance
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


# ── Dimensional breakdown rows ─────────────────────────────────────────────

class LocationRow(BaseModel):
    """Count of suggestions for a single location value."""
    model_config = ConfigDict(from_attributes=False)
    label:  str
    count:  int


class CategoryBreakdownRow(BaseModel):
    """Suggestion counts + action rate per category."""
    model_config = ConfigDict(from_attributes=False)
    category:    str
    total:       int
    actioned:    int
    noted:       int
    open:        int
    dismissed:   int
    action_rate: float   # % of terminal items that were actioned


class DayRow(BaseModel):
    """Submission count per calendar day — for trend charts."""
    model_config = ConfigDict(from_attributes=False)
    date:  str   # "YYYY-MM-DD"
    count: int


class StageRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    stage_id: str
    count:    int


class SubProjectRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    subproject_id: str
    count:         int


class StakeholderVolumeRow(BaseModel):
    """How many suggestions a given stakeholder has submitted."""
    model_config = ConfigDict(from_attributes=False)
    stakeholder_id: str
    count:          int


# ── Implementation time rows ───────────────────────────────────────────────

class StakeholderImplementationRow(BaseModel):
    """
    Per-stakeholder: how many suggestions were actioned and the average
    time (in hours) it took the PIU to implement (submitted → resolved_at).
    """
    model_config = ConfigDict(from_attributes=False)
    stakeholder_id:                str
    actioned_count:                int
    avg_implementation_hours:      Optional[float] = None
    avg_implementation_days:       Optional[float] = None
    min_implementation_hours:      Optional[float] = None
    max_implementation_hours:      Optional[float] = None
    implementation_times_measured: int


class CategoryImplementationRow(BaseModel):
    """Per-category average implementation time for actioned suggestions."""
    model_config = ConfigDict(from_attributes=False)
    category:                      str
    actioned_count:                int
    avg_implementation_hours:      Optional[float] = None
    min_implementation_hours:      Optional[float] = None
    max_implementation_hours:      Optional[float] = None
    implementation_times_measured: int


class ImplementationBlock(BaseModel):
    """
    Full implementation performance block for actioned suggestions.

    'implementation' measures the time between a suggestion being
    submitted and the PIU marking it as ACTIONED (resolved_at).

    by_stakeholder — which stakeholders' suggestions get implemented
                     fastest / slowest.
    by_category    — which types of suggestions get implemented fastest.
    """
    model_config = ConfigDict(from_attributes=False)
    total_actioned:               int
    with_timing_data:             int
    avg_implementation_hours:     Optional[float] = None
    avg_implementation_days:      Optional[float] = None
    min_implementation_hours:     Optional[float] = None
    max_implementation_hours:     Optional[float] = None
    by_stakeholder:               List[StakeholderImplementationRow] = []
    by_category:                  List[CategoryImplementationRow]    = []


# ── Rates ──────────────────────────────────────────────────────────────────

class SuggestionRatesBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    action_rate_pct:    float   # % of terminal items that were actioned
    noted_rate_pct:     float   # % noted (received but not implemented)
    dismissal_rate_pct: float   # % dismissed (out of scope / duplicate)
    open_rate_pct:      float   # % still open


class ResponseTimesBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    avg_acknowledgement_hours: Optional[float] = None
    avg_resolution_hours:      Optional[float] = None
    avg_close_hours:           Optional[float] = None


# ── Location block ─────────────────────────────────────────────────────────

class LocationBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    by_region:   List[Dict[str, Any]] = []
    by_district: List[Dict[str, Any]] = []
    by_lga:      List[Dict[str, Any]] = []
    by_ward:     List[Dict[str, Any]] = []
    by_mtaa:     List[Dict[str, Any]] = []


# ── Counts ─────────────────────────────────────────────────────────────────

class SuggestionCountsBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)
    total:        int
    submitted:    int
    acknowledged: int
    in_review:    int
    actioned:     int
    noted:        int
    dismissed:    int
    closed:       int
    open:         int


# ── Filters applied block ──────────────────────────────────────────────────

class FiltersAppliedBlock(BaseModel):
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

class SuggestionPerformanceResponse(BaseModel):
    """
    Comprehensive suggestion performance report.

    Returned by GET /api/v1/reports/suggestion-performance.

    Structure:
      counts          — volume by status
      rates           — action_rate, noted_rate, dismissal_rate, open_rate
      response_times  — avg acknowledgement / resolution / close hours
      implementation  — avg time to implement, per-stakeholder, per-category
      by_location     — region / district / lga / ward / mtaa breakdown
      by_category     — volumes + action rate per category
      by_day          — daily submission trend
      by_stage        — volumes per project stage
      by_subproject   — volumes per sub-project
      by_stakeholder  — volumes per stakeholder (who submits most)
      by_channel      — volumes per intake channel
      by_status       — full status distribution
    """
    model_config = ConfigDict(from_attributes=False)

    project_id:      Optional[str] = None
    date_range:      Dict[str, str]
    filters_applied: FiltersAppliedBlock
    counts:          SuggestionCountsBlock
    rates:           SuggestionRatesBlock
    response_times:  ResponseTimesBlock
    implementation:  ImplementationBlock
    by_location:     LocationBlock
    by_category:     List[CategoryBreakdownRow]    = []
    by_day:          List[DayRow]                  = []
    by_stage:        List[StageRow]                = []
    by_subproject:   List[SubProjectRow]           = []
    by_stakeholder:  List[StakeholderVolumeRow]    = []
    by_channel:      List[Dict[str, Any]]          = []
    by_status:       List[Dict[str, Any]]          = []

    @classmethod
    def from_dict(cls, d: dict) -> "SuggestionPerformanceResponse":
        c = d["counts"]
        r = d["rates"]
        rt = d["response_times"]
        impl = d["implementation"]
        loc  = d["by_location"]
        fa   = d.get("filters_applied", {})

        return cls(
            project_id=d.get("project_id"),
            date_range=d["date_range"],
            filters_applied=FiltersAppliedBlock(**fa),
            counts=SuggestionCountsBlock(**c),
            rates=SuggestionRatesBlock(**r),
            response_times=ResponseTimesBlock(**rt),
            implementation=ImplementationBlock(
                total_actioned               = impl["total_actioned"],
                with_timing_data             = impl["with_timing_data"],
                avg_implementation_hours     = impl.get("avg_implementation_hours"),
                avg_implementation_days      = impl.get("avg_implementation_days"),
                min_implementation_hours     = impl.get("min_implementation_hours"),
                max_implementation_hours     = impl.get("max_implementation_hours"),
                by_stakeholder = [
                    StakeholderImplementationRow(
                        stakeholder_id                = row["stakeholder_id"],
                        actioned_count                = row["actioned_count"],
                        avg_implementation_hours      = row.get("avg_implementation_hours"),
                        avg_implementation_days       = round(row["avg_implementation_hours"] / 24, 1)
                                                        if row.get("avg_implementation_hours") else None,
                        min_implementation_hours      = row.get("min_implementation_hours"),
                        max_implementation_hours      = row.get("max_implementation_hours"),
                        implementation_times_measured = row["implementation_times_measured"],
                    )
                    for row in impl.get("by_stakeholder", [])
                ],
                by_category = [
                    CategoryImplementationRow(**row)
                    for row in impl.get("by_category", [])
                ],
            ),
            by_location=LocationBlock(**loc),
            by_category=[CategoryBreakdownRow(**row) for row in d.get("by_category", [])],
            by_day=[DayRow(**row) for row in d.get("by_day", [])],
            by_stage=[StageRow(**row) for row in d.get("by_stage", [])],
            by_subproject=[SubProjectRow(**row) for row in d.get("by_subproject", [])],
            by_stakeholder=[
                StakeholderVolumeRow(stakeholder_id=row["stakeholder_id"], count=row["count"])
                for row in d.get("by_stakeholder", [])
            ],
            by_channel=d.get("by_channel", []),
            by_status=d.get("by_status", []),
        )
