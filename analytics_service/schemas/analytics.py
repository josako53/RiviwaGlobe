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
    project_id: UUID
    context_type: str = Field(
        default="general",
        description=(
            "One of: general, grievances, suggestions, sla, committees, "
            "hotspots, staff, unresolved"
        ),
    )


class AIInsightResponse(BaseModel):
    answer: str
    context_used: Dict[str, Any] = Field(default_factory=dict)
    model: str


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
