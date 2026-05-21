"""
schemas/dimension_analytics.py
────────────────────────────────────────────────────────────────────────────
Response schemas for per-entity (product / service / branch / department)
analytics endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Summary ───────────────────────────────────────────────────────────────────

class GrievanceTypeStats(BaseModel):
    count:           int
    pct:             float = Field(description="% of all feedback for this entity")
    resolved:        int
    resolution_rate: float = Field(description="% of grievances resolved or closed")


class SuggestionTypeStats(BaseModel):
    count:               int
    pct:                 float
    implemented:         int
    implementation_rate: float = Field(description="% of suggestions marked ACTIONED / implemented")


class SimpleTypeStats(BaseModel):
    count: int
    pct:   float


class ByTypeBreakdown(BaseModel):
    grievance:  GrievanceTypeStats
    suggestion: SuggestionTypeStats
    applause:   SimpleTypeStats
    inquiry:    SimpleTypeStats


class QRScanStats(BaseModel):
    scan_count:   int
    authentic:    int
    already_used: int
    unrecognized: int


class DimensionSummaryResponse(BaseModel):
    """
    Full analytics summary for a single product / service / branch / department.

    by_type contains counts and percentages for each feedback type.
    suggestion.implementation_rate = % of suggestions marked ACTIONED.
    grievance.resolution_rate      = % of grievances resolved or closed.
    qr_scans is populated for products only.
    """
    product_id:            Optional[UUID]        = None
    service_id:            Optional[UUID]        = None
    branch_id:             Optional[UUID]        = None
    department_id:         Optional[UUID]        = None

    total:                 int
    by_type:               ByTypeBreakdown
    resolved:              int
    resolution_rate_pct:   float
    avg_resolution_hours:  float
    pending:               int
    acknowledged:          int
    in_review:             int
    overdue:               int
    qr_scans:              Optional[QRScanStats] = None


# ── Category distribution ─────────────────────────────────────────────────────

class CategoryItem(BaseModel):
    category_id:          Optional[UUID]
    category_name:        str
    category_slug:        str
    color_hex:            Optional[str]
    icon:                 Optional[str]
    count:                int
    pct:                  float = Field(description="% of total feedback for this entity")
    grievances:           int
    suggestions:          int
    applause:             int
    inquiries:            int
    resolved:             int
    avg_resolution_hours: float


class CategoryDistributionResponse(BaseModel):
    """
    Category breakdown for a product / service / branch / department.
    pct shows e.g. 'quality 89%, delivery 5%, customer care 6%'.
    Use category_id from here to call /feedback?category_id=... for the drill-down list.
    """
    product_id:         Optional[UUID] = None
    service_id:         Optional[UUID] = None
    branch_id:          Optional[UUID] = None
    department_id:      Optional[UUID] = None
    total_categorised:  int
    categories:         List[CategoryItem]


# ── AI Themes ─────────────────────────────────────────────────────────────────

class ThemeItem(BaseModel):
    name:  str   = Field(description="Short theme label e.g. 'Quality Issues'")
    count: int
    pct:   float


class AIThemesResponse(BaseModel):
    """
    AI-mined recurring themes from feedback text.
    Groq LLM reads up to `texts_analysed` feedback descriptions and extracts
    recurring patterns with their percentage share.
    """
    product_id:      Optional[UUID] = None
    service_id:      Optional[UUID] = None
    branch_id:       Optional[UUID] = None
    department_id:   Optional[UUID] = None
    texts_analysed:  int
    themes:          List[ThemeItem]
    powered_by:      Optional[str]  = None
    note:            Optional[str]  = None


# ── Feedback drill-down ───────────────────────────────────────────────────────

class FeedbackLocation(BaseModel):
    region: Optional[str]
    lga:    Optional[str]
    ward:   Optional[str]


class FeedbackCategory(BaseModel):
    id:   Optional[UUID]
    name: Optional[str]
    slug: Optional[str]


class FeedbackListItem(BaseModel):
    feedback_id:             UUID
    unique_ref:              Optional[str]
    feedback_type:           str
    status:                  str
    priority:                Optional[str]
    subject:                 Optional[str]
    description:             Optional[str]
    submitter_name:          Optional[str]
    is_anonymous:            bool
    location:                FeedbackLocation
    category:                FeedbackCategory
    channel:                 Optional[str]
    submitted_at:            Optional[str]
    resolved_at:             Optional[str]
    implemented_at:          Optional[str]
    target_resolution_date:  Optional[str]
    org_id:                  Optional[UUID]
    project_id:              Optional[UUID]
    department_id:           Optional[UUID]
    service_id:              Optional[UUID]
    product_id:              Optional[UUID]
    branch_id:               Optional[UUID]


class FeedbackDrillDownResponse(BaseModel):
    """
    Paginated list of individual feedback records for a product / service / branch / department.
    Filter by feedback_type to see grievances only, or by category_id to see one category.
    """
    product_id:    Optional[UUID] = None
    service_id:    Optional[UUID] = None
    branch_id:     Optional[UUID] = None
    department_id: Optional[UUID] = None
    total:         int
    page:          int
    size:          int
    items:         List[FeedbackListItem]
