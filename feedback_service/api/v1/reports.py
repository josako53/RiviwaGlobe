# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  api/v1/reports.py
# ───────────────────────────────────────────────────────────────────────────
"""api/v1/reports.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Query
from core.dependencies import DbDep, StaffDep
from core.exporters import export_response
from schemas.applause_performance import ApplausePerformanceResponse
from schemas.grievance_performance import GrievancePerformanceResponse
from schemas.suggestion_performance import SuggestionPerformanceResponse
from services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])
_FMT = Query(default="json", description="json | pdf | xlsx | csv")
def _svc(db): return ReportService(db=db)

@router.get("/performance", summary="Overall performance dashboard — all types · exportable")
async def performance_dashboard(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    stage_id:   Optional[uuid.UUID] = Query(default=None),
    from_date:  Optional[str]       = Query(default=None),
    to_date:    Optional[str]       = Query(default=None),
        region:   Optional[str] = Query(default=None, description="Filter by issue region (partial match) e.g. 'Dar es Salaam'"),
    district: Optional[str] = Query(default=None, description="Filter by issue district (partial match) e.g. 'Ilala'"),
    lga:      Optional[str] = Query(default=None, description="Filter by issue LGA / municipal council (partial match)"),
    ward:     Optional[str] = Query(default=None, description="Filter by issue ward (partial match) e.g. 'Jangwani'"),
    mtaa:     Optional[str] = Query(default=None, description="Filter by issue Mtaa / cell (partial match)"),
    priority:          Optional[str] = Query(default=None),
    channel:           Optional[str] = Query(default=None),
    submission_method: Optional[str] = Query(default=None),
    format: str = _FMT,
):
    result = await _svc(db).performance(
        project_id=project_id, from_date=from_date, to_date=to_date,
        stage_id=stage_id, region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        priority=priority, channel=channel, submission_method=submission_method,
    )
    return export_response(result, format=format, filename="performance-report", title="Riviwa — Feedback Performance Report")

@router.get("/grievances", summary="Grievance performance page · exportable")
async def grievance_performance(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    stage_id:   Optional[uuid.UUID] = Query(default=None),
    from_date:  Optional[str]       = Query(default=None),
    to_date:    Optional[str]       = Query(default=None),
        region:   Optional[str] = Query(default=None, description="Filter by issue region (partial match) e.g. 'Dar es Salaam'"),
    district: Optional[str] = Query(default=None, description="Filter by issue district (partial match) e.g. 'Ilala'"),
    lga:      Optional[str] = Query(default=None, description="Filter by issue LGA / municipal council (partial match)"),
    ward:     Optional[str] = Query(default=None, description="Filter by issue ward (partial match) e.g. 'Jangwani'"),
    mtaa:     Optional[str] = Query(default=None, description="Filter by issue Mtaa / cell (partial match)"),
    priority:          Optional[str] = Query(default=None),
    channel:           Optional[str] = Query(default=None),
    submission_method: Optional[str] = Query(default=None),
    status_:           Optional[str] = Query(default=None, alias="status"),
    time_unit:         str           = Query(default="hours", description="Time unit for all timing outputs: seconds | minutes | hours | days | custom"),
    custom_seconds:    int           = Query(default=3600, description="Divisor when time_unit=custom e.g. 1800 = 30-min periods"),
    format: str = _FMT,
):
    result = await _svc(db).grievances(
        project_id=project_id, from_date=from_date, to_date=to_date,
        stage_id=stage_id, region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        priority=priority, channel=channel,
        submission_method=submission_method, status=status_,
        time_unit=time_unit, custom_seconds=custom_seconds,
    )
    return export_response(result, format=format, filename="grievances-report", title="Riviwa — Grievance Performance Report")

@router.get(
    "/grievance-performance",
    response_model=GrievancePerformanceResponse,
    summary="Comprehensive grievance performance report",
    description=(
        "Full grievance analytics in a single request.\n\n"
        "**Covers:**\n"
        "- **Volume** by status (total, submitted, acknowledged, in_review, escalated, resolved, appealed, dismissed, closed, open)\n"
        "- **Rates** — resolution rate, dismissal rate, appeal rate, open rate\n"
        "- **Response times** — avg acknowledgement, resolution, close hours\n"
        "- **SLA compliance** — per priority tier (critical/high/medium/low)\n"
        "- **Escalation breakdown** — distribution across GRM levels\n"
        "- **Resolution tracking** — avg time from submission → resolved, min/max, per stakeholder, per category\n"
        "- **Location breakdown** — by region, district, LGA, ward, mtaa\n"
        "- **Category breakdown** — volumes + resolution rate per category\n"
        "- **Daily trend** — submission count per calendar day\n"
        "- **Stage breakdown** — grievances per project stage\n"
        "- **Sub-project breakdown** — grievances per sub-project\n"
        "- **Stakeholder breakdown** — who submits the most grievances\n"
        "- **Channel breakdown** — intake channel distribution\n\n"
        "Filter by any combination of stage, sub-project, stakeholder, "
        "category, location, channel, or status."
    ),
)
async def grievance_performance_report(
    db: DbDep,
    _: StaffDep,
    project_id:     Optional[uuid.UUID] = Query(default=None, description="Filter to a specific project."),
    stage_id:       Optional[uuid.UUID] = Query(default=None, description="Filter to a specific project stage."),
    subproject_id:  Optional[uuid.UUID] = Query(default=None, description="Filter to a specific sub-project."),
    stakeholder_id: Optional[uuid.UUID] = Query(default=None, description="Filter to a specific stakeholder."),
    category:       Optional[str]       = Query(default=None, description="Filter by category slug e.g. 'compensation'."),
    from_date:      Optional[str]       = Query(default=None, description="Start date ISO 8601 e.g. '2025-01-01'."),
    to_date:        Optional[str]       = Query(default=None, description="End date ISO 8601 e.g. '2025-12-31'."),
    region:         Optional[str]       = Query(default=None, description="Filter by issue region (partial match)."),
    district:       Optional[str]       = Query(default=None, description="Filter by issue district (partial match)."),
    lga:            Optional[str]       = Query(default=None, description="Filter by issue LGA (partial match)."),
    ward:           Optional[str]       = Query(default=None, description="Filter by issue ward (partial match)."),
    mtaa:           Optional[str]       = Query(default=None, description="Filter by issue mtaa (partial match)."),
    channel:        Optional[str]       = Query(default=None, description="Filter by intake channel."),
    submission_method: Optional[str]    = Query(default=None),
    status:         Optional[str]       = Query(default=None, description="submitted | acknowledged | in_review | escalated | resolved | appealed | dismissed | closed"),
    time_unit:      str                 = Query(default="hours", description="Primary time unit: seconds | minutes | hours | days | custom"),
    custom_seconds: int                 = Query(default=3600, description="Divisor when time_unit=custom e.g. 1800 = 30-min periods"),
) -> GrievancePerformanceResponse:
    result = await _svc(db).grievance_performance(
        project_id=project_id,
        from_date=from_date,
        to_date=to_date,
        stage_id=stage_id,
        subproject_id=subproject_id,
        stakeholder_id=stakeholder_id,
        category=category,
        region=region,
        district=district,
        lga=lga,
        ward=ward,
        mtaa=mtaa,
        channel=channel,
        submission_method=submission_method,
        status=status,
        time_unit=time_unit,
        custom_seconds=custom_seconds,
    )
    return GrievancePerformanceResponse.from_dict(result)


@router.get("/suggestions", summary="Suggestion performance page · exportable")
async def suggestion_performance(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    stage_id:   Optional[uuid.UUID] = Query(default=None),
    from_date:  Optional[str]       = Query(default=None),
    to_date:    Optional[str]       = Query(default=None),
        region:   Optional[str] = Query(default=None, description="Filter by issue region (partial match) e.g. 'Dar es Salaam'"),
    district: Optional[str] = Query(default=None, description="Filter by issue district (partial match) e.g. 'Ilala'"),
    lga:      Optional[str] = Query(default=None, description="Filter by issue LGA / municipal council (partial match)"),
    ward:     Optional[str] = Query(default=None, description="Filter by issue ward (partial match) e.g. 'Jangwani'"),
    mtaa:     Optional[str] = Query(default=None, description="Filter by issue Mtaa / cell (partial match)"),
    channel:           Optional[str] = Query(default=None),
    submission_method: Optional[str] = Query(default=None),
    status_:           Optional[str] = Query(default=None, alias="status"),
    time_unit:         str           = Query(default="hours", description="Time unit for all timing outputs: seconds | minutes | hours | days | custom"),
    custom_seconds:    int           = Query(default=3600, description="Divisor when time_unit=custom e.g. 1800 = 30-min periods"),
    format: str = _FMT,
):
    result = await _svc(db).suggestions(
        project_id=project_id, from_date=from_date, to_date=to_date,
        stage_id=stage_id, region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        channel=channel, submission_method=submission_method, status=status_,
        time_unit=time_unit, custom_seconds=custom_seconds,
    )
    return export_response(result, format=format, filename="suggestions-report", title="Riviwa — Suggestion Performance Report")

@router.get(
    "/suggestion-performance",
    response_model=SuggestionPerformanceResponse,
    summary="Comprehensive suggestion performance report",
    description=(
        "Full suggestion analytics in a single request.\n\n"
        "Covers:\n"
        "- **Volume** by status (total, actioned, noted, open, dismissed)\n"
        "- **Rates** — action rate, noted rate, dismissal rate, open rate\n"
        "- **Response times** — avg acknowledgement, resolution, close hours\n"
        "- **Implementation tracking** — avg time from submission → ACTIONED "
        "(in hours and days), min/max, per stakeholder, per category\n"
        "- **Location breakdown** — by region, district, LGA, ward, mtaa\n"
        "- **Category breakdown** — volumes + action rate per category\n"
        "- **Daily trend** — submission count per calendar day\n"
        "- **Stage breakdown** — suggestions per project stage\n"
        "- **Sub-project breakdown** — suggestions per sub-project\n"
        "- **Stakeholder breakdown** — who submits the most suggestions\n"
        "- **Channel breakdown** — intake channel distribution\n\n"
        "Filter by any combination of stage, sub-project, stakeholder, "
        "category, location, channel, or status."
    ),
)
async def suggestion_performance_report(
    db: DbDep,
    _: StaffDep,
    project_id:     Optional[uuid.UUID] = Query(default=None, description="Filter to a specific project."),
    stage_id:       Optional[uuid.UUID] = Query(default=None, description="Filter to a specific project stage."),
    subproject_id:  Optional[uuid.UUID] = Query(default=None, description="Filter to a specific sub-project."),
    stakeholder_id: Optional[uuid.UUID] = Query(default=None, description="Filter to a specific stakeholder."),
    category:       Optional[str]       = Query(default=None, description="Filter by category value e.g. 'design', 'safety'."),
    from_date:      Optional[str]       = Query(default=None, description="Start date ISO 8601 e.g. '2025-01-01'."),
    to_date:        Optional[str]       = Query(default=None, description="End date ISO 8601 e.g. '2025-12-31'."),
    region:         Optional[str]       = Query(default=None, description="Filter by issue region (partial match)."),
    district:       Optional[str]       = Query(default=None, description="Filter by issue district (partial match)."),
    lga:            Optional[str]       = Query(default=None, description="Filter by issue LGA (partial match)."),
    ward:           Optional[str]       = Query(default=None, description="Filter by issue ward (partial match)."),
    mtaa:           Optional[str]       = Query(default=None, description="Filter by issue mtaa (partial match)."),
    channel:        Optional[str]       = Query(default=None, description="Filter by intake channel."),
    submission_method: Optional[str]    = Query(default=None),
    status:         Optional[str]       = Query(default=None, description="actioned | noted | submitted | acknowledged | in_review | dismissed | closed"),
    time_unit:      str                 = Query(default="hours", description="Primary time unit: seconds | minutes | hours | days | custom"),
    custom_seconds: int                 = Query(default=3600, description="Divisor when time_unit=custom e.g. 1800 = 30-min periods"),
) -> SuggestionPerformanceResponse:
    result = await _svc(db).suggestion_performance(
        project_id=project_id,
        from_date=from_date,
        to_date=to_date,
        stage_id=stage_id,
        subproject_id=subproject_id,
        stakeholder_id=stakeholder_id,
        category=category,
        region=region,
        district=district,
        lga=lga,
        ward=ward,
        mtaa=mtaa,
        channel=channel,
        submission_method=submission_method,
        status=status,
        time_unit=time_unit,
        custom_seconds=custom_seconds,
    )
    return SuggestionPerformanceResponse.from_dict(result)


@router.get(
    "/suggestions/detailed",
    summary="Detailed suggestion performance — rate, category, location, stakeholder, implementation time",
    description=(
        "Extended suggestion analytics covering:\n\n"
        "- **Daily rate**: submission count per day across the period\n"
        "- **By category**: count + action rate per feedback category\n"
        "- **By location**: grouped by region / district / LGA / ward / mtaa\n"
        "- **By stakeholder**: top submitters with their avg implementation time\n"
        "- **By stage**: submissions per project stage\n"
        "- **By sub-project**: submissions per work package\n"
        "- **Implementation time**: avg / min / max / median hours from submission "
        "to ACTIONED for implemented suggestions; per-suggestion log\n\n"
        "Filter by project, stage, subproject, stakeholder, category, location, "
        "or date range to drill into any dimension."
    ),
)
async def suggestion_performance_detailed(
    db: DbDep, _: StaffDep,
    project_id:     Optional[uuid.UUID] = Query(default=None),
    stage_id:       Optional[uuid.UUID] = Query(default=None),
    subproject_id:  Optional[uuid.UUID] = Query(default=None, description="Filter to a specific sub-project (work package)"),
    stakeholder_id: Optional[uuid.UUID] = Query(default=None, description="Filter to suggestions from a specific stakeholder"),
    from_date:  Optional[str] = Query(default=None, description="ISO date e.g. '2025-01-01'"),
    to_date:    Optional[str] = Query(default=None),
    category:   Optional[str] = Query(default=None, description="Partial match on category name"),
    region:     Optional[str] = Query(default=None, description="Filter by issue region"),
    district:   Optional[str] = Query(default=None, description="Filter by issue district"),
    lga:        Optional[str] = Query(default=None, description="Filter by issue LGA"),
    ward:       Optional[str] = Query(default=None, description="Filter by issue ward"),
    mtaa:       Optional[str] = Query(default=None, description="Filter by issue mtaa / cell"),
    group_location_by: str = Query(
        default="lga",
        description="Geographic grouping for by_location breakdown: region | district | lga | ward | mtaa",
    ),
    format: str = _FMT,
):
    result = await _svc(db).suggestion_performance_detailed(
        project_id=project_id,
        from_date=from_date,
        to_date=to_date,
        stage_id=stage_id,
        subproject_id=subproject_id,
        stakeholder_id=stakeholder_id,
        category=category,
        region=region,
        district=district,
        lga=lga,
        ward=ward,
        mtaa=mtaa,
        group_location_by=group_location_by,
    )
    return export_response(
        result, format=format,
        filename="suggestion-performance-detailed",
        title="Riviwa — Suggestion Performance (Detailed)",
    )


@router.get("/applause", summary="Applause performance page · exportable")
async def applause_performance(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    stage_id:   Optional[uuid.UUID] = Query(default=None),
    from_date:  Optional[str]       = Query(default=None),
    to_date:    Optional[str]       = Query(default=None),
        region:   Optional[str] = Query(default=None, description="Filter by issue region (partial match) e.g. 'Dar es Salaam'"),
    district: Optional[str] = Query(default=None, description="Filter by issue district (partial match) e.g. 'Ilala'"),
    lga:      Optional[str] = Query(default=None, description="Filter by issue LGA / municipal council (partial match)"),
    ward:     Optional[str] = Query(default=None, description="Filter by issue ward (partial match) e.g. 'Jangwani'"),
    mtaa:     Optional[str] = Query(default=None, description="Filter by issue Mtaa / cell (partial match)"),
    channel:           Optional[str] = Query(default=None),
    submission_method: Optional[str] = Query(default=None),
    format: str = _FMT,
):
    result = await _svc(db).applause(
        project_id=project_id, from_date=from_date, to_date=to_date,
        stage_id=stage_id, region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        channel=channel, submission_method=submission_method,
    )
    return export_response(result, format=format, filename="applause-report", title="Riviwa — Applause Performance Report")

@router.get(
    "/applause-performance",
    response_model=ApplausePerformanceResponse,
    summary="Comprehensive applause performance report with flexible time units",
    description=(
        "Full applause analytics in a single request.\n\n"
        "**Time unit control** — set `time_unit` to express all timing outputs in:\n"
        "- `seconds` — e.g. avg_ack = 172800 (2 days in seconds)\n"
        "- `minutes` — e.g. avg_ack = 2880\n"
        "- `hours`   — e.g. avg_ack = 48.0 (default)\n"
        "- `days`    — e.g. avg_ack = 2.0\n"
        "- `custom`  — divide by `custom_seconds` (e.g. 1800 = per 30-minute periods)\n\n"
        "The response ALWAYS includes timing in all four standard units simultaneously "
        "(`acknowledgement_time_all_units`) so the client never needs to recalculate.\n\n"
        "**Covers:**\n"
        "- Volume counts and rates (acknowledgement rate, open rate, close rate)\n"
        "- Acknowledgement time stats (avg, min, max, median) in the requested unit\n"
        "- Per-item acknowledgement detail with all four unit conversions\n"
        "- Location breakdown: region → district → LGA → ward → mtaa\n"
        "- Category breakdown: count + ack rate + avg ack time per category\n"
        "- Daily submission trend\n"
        "- By project stage and sub-project\n"
        "- Per-stakeholder: volume + ack timing in the requested unit\n"
        "- By intake channel\n\n"
        "**Filter by any combination of:** stage, sub-project, stakeholder, "
        "category, location, channel, status, date range."
    ),
)
async def applause_performance_report(
    db: DbDep,
    _: StaffDep,
    project_id:      Optional[uuid.UUID] = Query(default=None,  description="Scope to one project."),
    stage_id:        Optional[uuid.UUID] = Query(default=None,  description="Filter to a specific project stage."),
    subproject_id:   Optional[uuid.UUID] = Query(default=None,  description="Filter to a specific sub-project."),
    stakeholder_id:  Optional[uuid.UUID] = Query(default=None,  description="Filter to a specific stakeholder."),
    category:        Optional[str]       = Query(default=None,  description="Filter by category value."),
    from_date:       Optional[str]       = Query(default=None,  description="Start date ISO 8601 e.g. '2025-01-01'."),
    to_date:         Optional[str]       = Query(default=None,  description="End date ISO 8601 e.g. '2025-12-31'."),
    region:          Optional[str]       = Query(default=None,  description="Filter by issue region (partial match)."),
    district:        Optional[str]       = Query(default=None,  description="Filter by issue district (partial match)."),
    lga:             Optional[str]       = Query(default=None,  description="Filter by issue LGA (partial match)."),
    ward:            Optional[str]       = Query(default=None,  description="Filter by issue ward (partial match)."),
    mtaa:            Optional[str]       = Query(default=None,  description="Filter by issue mtaa (partial match)."),
    channel:         Optional[str]       = Query(default=None,  description="Filter by intake channel."),
    submission_method: Optional[str]     = Query(default=None),
    status:          Optional[str]       = Query(default=None,  description="submitted | acknowledged | in_review | open | closed"),
    time_unit:       str                 = Query(default="hours",description="Primary time unit for timing outputs: seconds | minutes | hours | days | custom"),
    custom_seconds:  int                 = Query(default=3600,  description="Divisor used when time_unit=custom. E.g. 1800 = 30-minute periods."),
) -> ApplausePerformanceResponse:
    result = await _svc(db).applause_performance(
        project_id=project_id,
        from_date=from_date,
        to_date=to_date,
        stage_id=stage_id,
        subproject_id=subproject_id,
        stakeholder_id=stakeholder_id,
        category=category,
        region=region,
        district=district,
        lga=lga,
        ward=ward,
        mtaa=mtaa,
        channel=channel,
        submission_method=submission_method,
        status=status,
        time_unit=time_unit,
        custom_seconds=custom_seconds,
    )
    return ApplausePerformanceResponse.from_dict(result)


@router.get("/channels", summary="Breakdown by intake channel and submission method · exportable")
async def channel_analytics(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    feedback_type: Optional[str] = Query(default=None),
    format: str = _FMT,
):
    result = await _svc(db).channels(project_id=project_id, from_date=from_date, to_date=to_date, feedback_type=feedback_type)
    return export_response(result, format=format, filename="channels-report", title="Riviwa — Channel Analytics Report")

@router.get("/grievance-log", summary="Full grievance log (SEP Annex 5/6 format) · exportable")
async def grievance_log(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    from_date:  Optional[str]       = Query(default=None),
    to_date:    Optional[str]       = Query(default=None),
        region:   Optional[str] = Query(default=None, description="Filter by issue region (partial match) e.g. 'Dar es Salaam'"),
    district: Optional[str] = Query(default=None, description="Filter by issue district (partial match) e.g. 'Ilala'"),
    lga:      Optional[str] = Query(default=None, description="Filter by issue LGA / municipal council (partial match)"),
    ward:     Optional[str] = Query(default=None, description="Filter by issue ward (partial match) e.g. 'Jangwani'"),
    mtaa:     Optional[str] = Query(default=None, description="Filter by issue Mtaa / cell (partial match)"),
    priority: Optional[str] = Query(default=None),
    channel:  Optional[str] = Query(default=None),
    status_:  Optional[str] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500),
    format: str = _FMT,
):
    result = await _svc(db).grievance_log(
        project_id=project_id, from_date=from_date, to_date=to_date,
        region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        priority=priority, channel=channel, status=status_, skip=skip, limit=limit,
    )
    return export_response(result, format=format, filename="grievance-log", title="Riviwa — Grievance Log (SEP Format)")

@router.get("/suggestion-log", summary="Full suggestion log · exportable")
async def suggestion_log(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    from_date:  Optional[str]       = Query(default=None),
    to_date:    Optional[str]       = Query(default=None),
        region:   Optional[str] = Query(default=None, description="Filter by issue region (partial match) e.g. 'Dar es Salaam'"),
    district: Optional[str] = Query(default=None, description="Filter by issue district (partial match) e.g. 'Ilala'"),
    lga:      Optional[str] = Query(default=None, description="Filter by issue LGA / municipal council (partial match)"),
    ward:     Optional[str] = Query(default=None, description="Filter by issue ward (partial match) e.g. 'Jangwani'"),
    mtaa:     Optional[str] = Query(default=None, description="Filter by issue Mtaa / cell (partial match)"),
    channel: Optional[str] = Query(default=None),
    status_: Optional[str] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500),
    format: str = _FMT,
):
    result = await _svc(db).suggestion_log(
        project_id=project_id, from_date=from_date, to_date=to_date,
        region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        channel=channel, status=status_, skip=skip, limit=limit,
    )
    return export_response(result, format=format, filename="suggestion-log", title="Riviwa — Suggestion Log")

@router.get("/applause-log", summary="Full applause log · exportable")
async def applause_log(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    from_date:  Optional[str]       = Query(default=None),
    to_date:    Optional[str]       = Query(default=None),
        region:   Optional[str] = Query(default=None, description="Filter by issue region (partial match) e.g. 'Dar es Salaam'"),
    district: Optional[str] = Query(default=None, description="Filter by issue district (partial match) e.g. 'Ilala'"),
    lga:      Optional[str] = Query(default=None, description="Filter by issue LGA / municipal council (partial match)"),
    ward:     Optional[str] = Query(default=None, description="Filter by issue ward (partial match) e.g. 'Jangwani'"),
    mtaa:     Optional[str] = Query(default=None, description="Filter by issue Mtaa / cell (partial match)"),
    channel: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500),
    format: str = _FMT,
):
    result = await _svc(db).applause_log(
        project_id=project_id, from_date=from_date, to_date=to_date,
        region=region, district=district, lga=lga, ward=ward, mtaa=mtaa,
        channel=channel, skip=skip, limit=limit,
    )
    return export_response(result, format=format, filename="applause-log", title="Riviwa — Applause Log")

@router.get("/summary", summary="Count summary · exportable")
async def feedback_summary(db: DbDep, _: StaffDep, project_id: uuid.UUID = Query(...), format: str = _FMT):
    result = await _svc(db).summary(project_id)
    return export_response(result, format=format, filename="summary-report", title="Riviwa — Feedback Summary")

@router.get("/overdue", summary="Grievances past target resolution date · exportable")
async def overdue_grievances(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    format: str = _FMT,
):
    result = await _svc(db).overdue(project_id=project_id, priority=priority)
    return export_response(result, format=format, filename="overdue-report", title="Riviwa — Overdue Grievances")
