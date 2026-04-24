"""schemas/analytics.py — Pydantic response schemas for analytics_service."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Generic ───────────────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    total: int
    page: int = 1
    page_size: int = 100


# ── Feedback: Time-to-Open ────────────────────────────────────────────────────

class TimeToOpenItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    priority: Optional[str] = None
    submitted_at: Optional[datetime] = None
    first_action_at: Optional[datetime] = None
    hours_to_open: Optional[float] = None


class TimeToOpenResponse(BaseModel):
    avg_hours: Optional[float] = None
    min_hours: Optional[float] = None
    max_hours: Optional[float] = None
    median_hours: Optional[float] = None
    sample_count: int = 0
    items: List[TimeToOpenItem] = Field(default_factory=list)


# ── Feedback: Unread ──────────────────────────────────────────────────────────

class UnreadFeedbackItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    feedback_type: Optional[str] = None
    priority: Optional[str] = None
    submitted_at: Optional[datetime] = None
    days_waiting: Optional[float] = None
    channel: Optional[str] = None
    issue_lga: Optional[str] = None
    submitter_name: Optional[str] = None
    service_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    category_def_id: Optional[UUID] = None


class UnreadFeedbackResponse(BaseModel):
    total: int = 0
    items: List[UnreadFeedbackItem] = Field(default_factory=list)


# ── Feedback: Overdue ─────────────────────────────────────────────────────────

class OverdueFeedbackItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    submitted_at: Optional[datetime] = None
    target_resolution_date: Optional[datetime] = None
    days_overdue: Optional[float] = None
    assigned_to_user_id: Optional[UUID] = None
    committee_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    category_def_id: Optional[UUID] = None


class OverdueFeedbackResponse(BaseModel):
    total: int = 0
    items: List[OverdueFeedbackItem] = Field(default_factory=list)


# ── Feedback: Not Processed ───────────────────────────────────────────────────

class NotProcessedFeedbackResponse(BaseModel):
    total: int = 0
    items: List[OverdueFeedbackItem] = Field(default_factory=list)


# ── Feedback: Processed Today ─────────────────────────────────────────────────

class ProcessedTodayItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    processed_at: Optional[datetime] = None


class ProcessedTodayResponse(BaseModel):
    total: int = 0
    items: List[ProcessedTodayItem] = Field(default_factory=list)


# ── Feedback: Resolved Today ──────────────────────────────────────────────────

class ResolvedTodayItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    feedback_type: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_hours: Optional[float] = None


class ResolvedTodayResponse(BaseModel):
    total: int = 0
    items: List[ResolvedTodayItem] = Field(default_factory=list)


# ── Grievances: Unresolved ────────────────────────────────────────────────────

class UnresolvedGrievanceItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    submitted_at: Optional[datetime] = None
    days_unresolved: Optional[float] = None
    assigned_to_user_id: Optional[UUID] = None
    committee_id: Optional[UUID] = None
    issue_lga: Optional[str] = None
    issue_ward: Optional[str] = None
    department_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    category_def_id: Optional[UUID] = None


class UnresolvedGrievancesResponse(BaseModel):
    total: int = 0
    items: List[UnresolvedGrievanceItem] = Field(default_factory=list)


# ── Grievances: SLA Status ────────────────────────────────────────────────────

class SLAByPriority(BaseModel):
    priority: str
    total: int = 0
    ack_met: int = 0
    ack_breached: int = 0
    res_met: int = 0
    res_breached: int = 0
    compliance_rate: Optional[float] = None


class SLAOverdueItem(BaseModel):
    feedback_id: UUID
    priority: Optional[str] = None
    status: Optional[str] = None
    submitted_at: Optional[datetime] = None
    ack_deadline: Optional[datetime] = None
    res_deadline: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    ack_sla_met: Optional[bool] = None
    res_sla_met: Optional[bool] = None
    days_unresolved: Optional[float] = None


class SLAStatusResponse(BaseModel):
    by_priority: List[SLAByPriority] = Field(default_factory=list)
    overdue_list: List[SLAOverdueItem] = Field(default_factory=list)
    total_breached: int = 0
    overall_compliance_rate: Optional[float] = None


# ── Grievances: Hotspots ──────────────────────────────────────────────────────

class HotspotAlertItem(BaseModel):
    id: Optional[UUID] = None
    location: str
    category: str
    count: int
    spike_factor: float
    baseline_avg: float
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    alert_status: str = "active"


class HotspotResponse(BaseModel):
    total: int = 0
    alerts: List[HotspotAlertItem] = Field(default_factory=list)


# ── Suggestions: Implementation Time ─────────────────────────────────────────

class SuggestionImplTimeItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    submitted_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None
    hours_to_implement: Optional[float] = None
    category: Optional[str] = None


class ImplementationTimeResponse(BaseModel):
    avg_hours: Optional[float] = None
    min_hours: Optional[float] = None
    max_hours: Optional[float] = None
    median_hours: Optional[float] = None
    sample_count: int = 0
    items: List[SuggestionImplTimeItem] = Field(default_factory=list)


# ── Suggestions: Frequency ────────────────────────────────────────────────────

class SuggestionFrequencyItem(BaseModel):
    category: Optional[str] = None
    priority: Optional[str] = None
    count: int = 0
    rate_per_day: Optional[float] = None


class SuggestionFrequencyResponse(BaseModel):
    period: str
    period_days: int
    total: int = 0
    items: List[SuggestionFrequencyItem] = Field(default_factory=list)


# ── Suggestions: By Location ──────────────────────────────────────────────────

class SuggestionLocationItem(BaseModel):
    region: Optional[str] = None
    lga: Optional[str] = None
    ward: Optional[str] = None
    count: int = 0
    implemented_count: int = 0
    implementation_rate: Optional[float] = None


class SuggestionLocationResponse(BaseModel):
    total: int = 0
    items: List[SuggestionLocationItem] = Field(default_factory=list)


# ── Suggestions: Unread ───────────────────────────────────────────────────────

class UnreadSuggestionItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    submitted_at: Optional[datetime] = None
    days_unread: Optional[float] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    issue_lga: Optional[str] = None


class UnreadSuggestionsResponse(BaseModel):
    total: int = 0
    items: List[UnreadSuggestionItem] = Field(default_factory=list)


# ── Suggestions: Implemented ──────────────────────────────────────────────────

class ImplementedSuggestionItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    category: Optional[str] = None
    submitted_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None
    hours_to_implement: Optional[float] = None


class ImplementedResponse(BaseModel):
    total: int = 0
    items: List[ImplementedSuggestionItem] = Field(default_factory=list)


# ── Staff: Committee Performance ──────────────────────────────────────────────

class CommitteePerformanceItem(BaseModel):
    committee_id: UUID
    committee_name: Optional[str] = None
    level: Optional[str] = None
    project_id: Optional[UUID] = None
    cases_assigned: int = 0
    cases_resolved: int = 0
    cases_overdue: int = 0
    avg_resolution_hours: Optional[float] = None
    resolution_rate: Optional[float] = None


class CommitteePerformanceResponse(BaseModel):
    total: int = 0
    items: List[CommitteePerformanceItem] = Field(default_factory=list)


# ── Staff: Last Logins ────────────────────────────────────────────────────────

class StaffLoginItem(BaseModel):
    user_id: UUID
    last_login_at: Optional[datetime] = None
    login_count_7d: int = 0
    platform: Optional[str] = None


class LastLoginsResponse(BaseModel):
    total: int = 0
    items: List[StaffLoginItem] = Field(default_factory=list)


# ── Staff: Unread Assigned ────────────────────────────────────────────────────

class UnreadAssignedItem(BaseModel):
    user_id: UUID
    assigned_count: int = 0
    unread_count: int = 0
    feedback_ids: List[UUID] = Field(default_factory=list)


class UnreadAssignedResponse(BaseModel):
    total: int = 0
    items: List[UnreadAssignedItem] = Field(default_factory=list)


# ── Staff: Login Not Read ─────────────────────────────────────────────────────

class LoginNotReadItem(BaseModel):
    user_id: UUID
    last_login_at: Optional[datetime] = None
    assigned_unread_count: int = 0
    feedback_ids: List[UUID] = Field(default_factory=list)


class LoginNotReadResponse(BaseModel):
    total: int = 0
    items: List[LoginNotReadItem] = Field(default_factory=list)


# ── AI Insights ───────────────────────────────────────────────────────────────

class AIInsightRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    project_id: Optional[UUID] = None
    org_id: Optional[UUID] = None
    context_type: str = Field(
        default="general",
        description=(
            "Project scope: general, grievances, suggestions, sla, committees, hotspots, staff, unresolved, inquiries. "
            "Org scope: org_general, org_grievances, org_suggestions, org_applause, org_inquiries. "
            "Platform scope: platform_general, platform_grievances, platform_suggestions, platform_applause, platform_inquiries."
        ),
    )
    scope: str = Field(default="project", description="project | org | platform")


class AIInsightResponse(BaseModel):
    answer: str
    context_used: Dict[str, Any] = Field(default_factory=dict)
    model: str = ""


# ── Breakdown: By Service / Product / Category Def ────────────────────────────

class FeedbackBreakdownItem(BaseModel):
    """One row in a service/product/category breakdown — counts per dimension value."""
    service_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    category_def_id: Optional[UUID] = None
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    total: int = 0
    grievances: int = 0
    suggestions: int = 0
    applause: int = 0
    inquiries: int = 0
    resolved: int = 0
    avg_resolution_hours: Optional[float] = None


class FeedbackBreakdownResponse(BaseModel):
    total_items: int = 0
    items: List[FeedbackBreakdownItem] = Field(default_factory=list)


# ── Organisation-level Analytics ──────────────────────────────────────────────

class OrgSummaryResponse(BaseModel):
    """High-level counts across all projects in the org."""
    org_id: Optional[UUID] = None
    total_feedback: int = 0
    total_grievances: int = 0
    total_suggestions: int = 0
    total_applause: int = 0
    total_inquiries: int = 0
    # By status
    submitted: int = 0
    acknowledged: int = 0
    in_review: int = 0
    escalated: int = 0
    resolved: int = 0
    closed: int = 0
    dismissed: int = 0
    # By priority (grievances)
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    # Resolution stats
    avg_resolution_hours: Optional[float] = None
    avg_days_unresolved: Optional[float] = None
    total_projects: int = 0


class OrgByProjectItem(BaseModel):
    project_id: UUID
    project_name: Optional[str] = None
    total: int = 0
    grievances: int = 0
    suggestions: int = 0
    applause: int = 0
    inquiries: int = 0
    unresolved: int = 0
    resolved: int = 0
    avg_resolution_hours: Optional[float] = None


class OrgByProjectResponse(BaseModel):
    total_items: int = 0
    items: List[OrgByProjectItem] = Field(default_factory=list)


class OrgByPeriodItem(BaseModel):
    period: str                        # e.g. "2026-04-01" / "2026-W14" / "2026-04"
    total: int = 0
    grievances: int = 0
    suggestions: int = 0
    applause: int = 0
    inquiries: int = 0


class OrgByPeriodResponse(BaseModel):
    granularity: str                   # day | week | month
    total_items: int = 0
    items: List[OrgByPeriodItem] = Field(default_factory=list)


class OrgByChannelItem(BaseModel):
    channel: str
    total: int = 0
    grievances: int = 0
    suggestions: int = 0
    applause: int = 0
    inquiries: int = 0


class OrgByChannelResponse(BaseModel):
    total_items: int = 0
    items: List[OrgByChannelItem] = Field(default_factory=list)


class OrgDimensionBreakdownItem(BaseModel):
    """Generic breakdown row for department/service/product (UUID dimension)."""
    dimension_id: Optional[UUID] = None
    total: int = 0
    grievances: int = 0
    suggestions: int = 0
    applause: int = 0
    inquiries: int = 0
    resolved: int = 0
    avg_resolution_hours: Optional[float] = None


class OrgDimensionBreakdownResponse(BaseModel):
    dimension: str                     # "department_id" | "service_id" | "product_id"
    total_items: int = 0
    items: List[OrgDimensionBreakdownItem] = Field(default_factory=list)


class OrgByLocationItem(BaseModel):
    lga: Optional[str] = None
    ward: Optional[str] = None
    total: int = 0
    unresolved: int = 0
    resolved: int = 0


class OrgByLocationResponse(BaseModel):
    total_items: int = 0
    items: List[OrgByLocationItem] = Field(default_factory=list)


# ── Org Grievance ─────────────────────────────────────────────────────────────

class OrgGrievanceSummaryResponse(BaseModel):
    total_grievances: int = 0
    unresolved: int = 0
    escalated: int = 0
    dismissed: int = 0
    resolved: int = 0
    closed: int = 0
    avg_resolution_hours: Optional[float] = None
    avg_days_unresolved: Optional[float] = None
    # Priority breakdown
    critical_unresolved: int = 0
    high_unresolved: int = 0
    medium_unresolved: int = 0
    low_unresolved: int = 0


class OrgGrievanceByLevelItem(BaseModel):
    level: str
    total: int = 0
    unresolved: int = 0
    resolved: int = 0


class OrgGrievanceByLevelResponse(BaseModel):
    total_items: int = 0
    items: List[OrgGrievanceByLevelItem] = Field(default_factory=list)


class OrgSLAByPriority(BaseModel):
    priority: str
    total: int = 0
    ack_met: int = 0
    ack_breached: int = 0
    res_met: int = 0
    res_breached: int = 0
    compliance_rate: Optional[float] = None


class OrgGrievanceSLAResponse(BaseModel):
    by_priority: List[OrgSLAByPriority] = Field(default_factory=list)
    total_breached: int = 0
    overall_compliance_rate: Optional[float] = None


# ── Org Suggestions ───────────────────────────────────────────────────────────

class OrgSuggestionSummaryResponse(BaseModel):
    total_suggestions: int = 0
    actioned: int = 0
    noted: int = 0
    pending: int = 0          # submitted + acknowledged
    dismissed: int = 0
    actioned_rate: Optional[float] = None
    avg_hours_to_implement: Optional[float] = None


class OrgSuggestionByProjectItem(BaseModel):
    project_id: UUID
    project_name: Optional[str] = None
    total: int = 0
    actioned: int = 0
    pending: int = 0
    implementation_rate: Optional[float] = None
    avg_hours_to_implement: Optional[float] = None


class OrgSuggestionByProjectResponse(BaseModel):
    total_items: int = 0
    items: List[OrgSuggestionByProjectItem] = Field(default_factory=list)


# ── Org Applause ──────────────────────────────────────────────────────────────

class OrgApplauseCategoryItem(BaseModel):
    category: Optional[str] = None
    category_def_id: Optional[UUID] = None
    category_name: Optional[str] = None
    count: int = 0


class OrgApplauseByProjectItem(BaseModel):
    project_id: UUID
    project_name: Optional[str] = None
    count: int = 0


class OrgAppIauseSummaryResponse(BaseModel):
    total_applause: int = 0
    this_month: int = 0
    last_month: int = 0
    mom_change: Optional[float] = None     # month-on-month % change
    top_categories: List[OrgApplauseCategoryItem] = Field(default_factory=list)
    by_project: List[OrgApplauseByProjectItem] = Field(default_factory=list)
    context_used: Dict[str, Any] = Field(default_factory=dict)
    model: str = ""


# ── Platform-level Analytics ──────────────────────────────────────────────────

class PlatformSummaryResponse(BaseModel):
    """Aggregated counts across ALL organisations and ALL projects."""
    total_orgs: int = 0
    total_projects: int = 0
    total_feedback: int = 0
    total_grievances: int = 0
    total_suggestions: int = 0
    total_applause: int = 0
    total_inquiries: int = 0
    submitted: int = 0
    acknowledged: int = 0
    in_review: int = 0
    escalated: int = 0
    resolved: int = 0
    closed: int = 0
    dismissed: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    avg_resolution_hours: Optional[float] = None
    avg_days_unresolved: Optional[float] = None


class PlatformByOrgItem(BaseModel):
    organisation_id: UUID
    org_name: Optional[str] = None
    total_projects: int = 0
    total: int = 0
    grievances: int = 0
    suggestions: int = 0
    applause: int = 0
    inquiries: int = 0
    unresolved: int = 0
    resolved: int = 0
    avg_resolution_hours: Optional[float] = None


class PlatformByOrgResponse(BaseModel):
    total_items: int = 0
    items: List[PlatformByOrgItem] = Field(default_factory=list)


class OrgApplauseByOrgItem(BaseModel):
    organisation_id: UUID
    count: int = 0


class PlatformApplauseSummaryResponse(BaseModel):
    total_applause: int = 0
    this_month: int = 0
    last_month: int = 0
    mom_change: Optional[float] = None
    top_categories: List[OrgApplauseCategoryItem] = Field(default_factory=list)
    by_org: List[OrgApplauseByOrgItem] = Field(default_factory=list)
    context_used: Dict[str, Any] = Field(default_factory=dict)
    model: str = ""


# ── Inquiry Analytics ──────────────────────────────────────────────────────────

class InquirySummaryResponse(BaseModel):
    """Summary of inquiries at project, org, or platform level."""
    total_inquiries: int = 0
    open_inquiries: int = 0          # status NOT IN resolved/closed/dismissed
    resolved: int = 0
    closed: int = 0
    dismissed: int = 0
    avg_response_hours: Optional[float] = None   # avg hours from submitted to resolved
    avg_days_open: Optional[float] = None        # avg days currently open (unresolved)
    critical_open: int = 0
    high_open: int = 0
    medium_open: int = 0
    low_open: int = 0


class InquiryUnreadItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    priority: Optional[str] = None
    submitted_at: Optional[datetime] = None
    days_waiting: Optional[float] = None
    channel: Optional[str] = None
    issue_lga: Optional[str] = None
    department_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    category_def_id: Optional[UUID] = None


class InquiryUnreadResponse(BaseModel):
    total: int = 0
    items: List[InquiryUnreadItem] = Field(default_factory=list)


class InquiryOverdueItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    submitted_at: Optional[datetime] = None
    target_resolution_date: Optional[datetime] = None
    days_overdue: Optional[float] = None
    assigned_to_user_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    category_def_id: Optional[UUID] = None


class InquiryOverdueResponse(BaseModel):
    total: int = 0
    items: List[InquiryOverdueItem] = Field(default_factory=list)


class InquiryByChannelItem(BaseModel):
    channel: str
    total: int = 0
    open_count: int = 0
    resolved: int = 0


class InquiryByChannelResponse(BaseModel):
    total_items: int = 0
    items: List[InquiryByChannelItem] = Field(default_factory=list)


class InquiryByCategoryItem(BaseModel):
    category_def_id: Optional[UUID] = None
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    total: int = 0
    open_count: int = 0
    resolved: int = 0
    avg_response_hours: Optional[float] = None


class InquiryByCategoryResponse(BaseModel):
    total_items: int = 0
    items: List[InquiryByCategoryItem] = Field(default_factory=list)


# ── Grievance Dashboard ──────────────────────────────────────────────────────

class GrievanceSummaryStats(BaseModel):
    total_grievances: int = 0
    resolved: int = 0
    closed: int = 0
    unresolved: int = 0
    escalated: int = 0
    dismissed: int = 0
    acknowledged_count: int = 0
    acknowledged_pct: Optional[float] = None
    resolved_on_time: int = 0
    resolved_late: int = 0
    resolved_on_time_pct: Optional[float] = None
    resolved_late_pct: Optional[float] = None
    avg_resolution_hours: Optional[float] = None
    avg_days_unresolved: Optional[float] = None


class GrievancePriorityBreakdownItem(BaseModel):
    priority: str
    total: int = 0
    unresolved: int = 0
    resolved: int = 0


class GrievanceDeptBreakdownItem(BaseModel):
    department_id: Optional[UUID] = None
    total: int = 0
    unresolved: int = 0
    resolved: int = 0
    avg_resolution_hours: Optional[float] = None


class GrievanceStageBreakdownItem(BaseModel):
    stage_id: Optional[UUID] = None
    stage_name: Optional[str] = None
    stage_order: Optional[int] = None
    total: int = 0
    unresolved: int = 0
    resolved: int = 0


class GrievanceProjectBreakdownItem(BaseModel):
    project_id: UUID
    project_name: Optional[str] = None
    total: int = 0
    unresolved: int = 0
    resolved: int = 0


class GrievanceOrgBreakdownItem(BaseModel):
    organisation_id: UUID
    org_name: Optional[str] = None
    total: int = 0
    unresolved: int = 0
    resolved: int = 0


class GrievanceDashboardOverdueItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    submitted_at: Optional[datetime] = None
    target_resolution_date: Optional[datetime] = None
    days_overdue: Optional[float] = None
    department_id: Optional[UUID] = None
    assigned_to_user_id: Optional[UUID] = None
    committee_id: Optional[UUID] = None
    issue_lga: Optional[str] = None


class GrievanceListItem(BaseModel):
    feedback_id: UUID
    unique_ref: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    submitted_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    target_resolution_date: Optional[datetime] = None
    days_unresolved: Optional[float] = None
    department_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    category_def_id: Optional[UUID] = None
    issue_lga: Optional[str] = None
    issue_ward: Optional[str] = None
    assigned_to_user_id: Optional[UUID] = None
    committee_id: Optional[UUID] = None
    stage_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class PaginatedGrievancesResponse(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 50
    items: List[GrievanceListItem] = Field(default_factory=list)


class GrievanceDashboardResponse(BaseModel):
    """Project-scope grievance dashboard."""
    summary: GrievanceSummaryStats = Field(default_factory=GrievanceSummaryStats)
    by_priority: List[GrievancePriorityBreakdownItem] = Field(default_factory=list)
    by_department: List[GrievanceDeptBreakdownItem] = Field(default_factory=list)
    by_stage: List[GrievanceStageBreakdownItem] = Field(default_factory=list)
    overdue: List[GrievanceDashboardOverdueItem] = Field(default_factory=list)
    grievances: PaginatedGrievancesResponse = Field(default_factory=PaginatedGrievancesResponse)


class OrgGrievanceDashboardResponse(BaseModel):
    """Org-scope grievance dashboard."""
    summary: GrievanceSummaryStats = Field(default_factory=GrievanceSummaryStats)
    by_priority: List[GrievancePriorityBreakdownItem] = Field(default_factory=list)
    by_department: List[GrievanceDeptBreakdownItem] = Field(default_factory=list)
    by_project: List[GrievanceProjectBreakdownItem] = Field(default_factory=list)
    overdue: List[GrievanceDashboardOverdueItem] = Field(default_factory=list)
    grievances: PaginatedGrievancesResponse = Field(default_factory=PaginatedGrievancesResponse)


class PlatformGrievanceDashboardResponse(BaseModel):
    """Platform-scope grievance dashboard."""
    summary: GrievanceSummaryStats = Field(default_factory=GrievanceSummaryStats)
    by_priority: List[GrievancePriorityBreakdownItem] = Field(default_factory=list)
    by_department: List[GrievanceDeptBreakdownItem] = Field(default_factory=list)
    by_org: List[GrievanceOrgBreakdownItem] = Field(default_factory=list)
    overdue: List[GrievanceDashboardOverdueItem] = Field(default_factory=list)
    grievances: PaginatedGrievancesResponse = Field(default_factory=PaginatedGrievancesResponse)


# ── Internal: SLA upsert ──────────────────────────────────────────────────────

class SLAStatusUpsert(BaseModel):
    feedback_id: UUID
    project_id: UUID
    feedback_type: str
    priority: str
    submitted_at: datetime
    ack_deadline: Optional[datetime] = None
    res_deadline: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    ack_sla_met: Optional[bool] = None
    res_sla_met: Optional[bool] = None
    ack_sla_breached: bool = False
    res_sla_breached: bool = False
    days_unresolved: Optional[float] = None


# ── Staff Login Record (internal) ─────────────────────────────────────────────

class StaffLoginCreate(BaseModel):
    user_id: UUID
    login_at: datetime
    ip_address: Optional[str] = None
    platform: Optional[str] = None

