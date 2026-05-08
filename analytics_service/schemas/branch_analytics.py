"""schemas/branch_analytics.py — Response schemas for branch analytics endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Branch summary (all branches in an org) ───────────────────────────────────

class BranchSummaryItem(BaseModel):
    branch_id:            UUID
    total:                int             = 0
    grievances:           int             = 0
    suggestions:          int             = 0
    applause:             int             = 0
    inquiries:            int             = 0
    resolved:             int             = 0
    open_count:           int             = 0
    escalated:            int             = 0
    dismissed:            int             = 0
    overdue:              int             = 0
    avg_resolution_hours: Optional[float] = None
    resolution_rate:      Optional[float] = None
    escalation_rate:      Optional[float] = None


class BranchSummaryResponse(BaseModel):
    org_id:         UUID
    date_from:      Optional[str] = None
    date_to:        Optional[str] = None
    feedback_type:  Optional[str] = None
    total_branches: int
    items:          List[BranchSummaryItem]


# ── Branch performance ranking ────────────────────────────────────────────────

class BranchPerformanceItem(BaseModel):
    rank:                 int
    branch_id:            UUID
    total:                int             = 0
    grievances:           int             = 0
    suggestions:          int             = 0
    applause:             int             = 0
    inquiries:            int             = 0
    resolved:             int             = 0
    open_count:           int             = 0
    escalated:            int             = 0
    overdue:              int             = 0
    avg_resolution_hours: Optional[float] = None
    resolution_rate:      Optional[float] = None
    escalation_rate:      Optional[float] = None


class BranchPerformanceResponse(BaseModel):
    org_id:         UUID
    date_from:      Optional[str] = None
    date_to:        Optional[str] = None
    total_branches: int
    items:          List[BranchPerformanceItem]


# ── Branch trend (multi-branch over time) ────────────────────────────────────

class BranchTrendItem(BaseModel):
    branch_id:   UUID
    period:      Optional[datetime] = None
    total:       int = 0
    grievances:  int = 0
    suggestions: int = 0
    applause:    int = 0
    inquiries:   int = 0
    resolved:    int = 0


class BranchTrendResponse(BaseModel):
    org_id:      UUID
    granularity: str
    date_from:   Optional[str] = None
    date_to:     Optional[str] = None
    items:       List[BranchTrendItem]


# ── Single-branch detail ──────────────────────────────────────────────────────

class BranchDeptItem(BaseModel):
    department_id:        Optional[UUID]  = None
    total:                int             = 0
    grievances:           int             = 0
    applause:             int             = 0
    resolved:             int             = 0
    avg_resolution_hours: Optional[float] = None


class BranchCategoryItem(BaseModel):
    category_def_id: Optional[UUID] = None
    category:        Optional[str]  = None
    total:           int            = 0
    grievances:      int            = 0
    resolved:        int            = 0


class BranchServiceItem(BaseModel):
    service_id: Optional[UUID] = None
    total:      int            = 0
    grievances: int            = 0
    resolved:   int            = 0


class BranchDayItem(BaseModel):
    period:      Optional[datetime] = None
    total:       int = 0
    grievances:  int = 0
    suggestions: int = 0
    applause:    int = 0
    inquiries:   int = 0


class BranchDetailResponse(BaseModel):
    org_id:               UUID
    branch_id:            UUID
    date_from:            Optional[str]  = None
    date_to:              Optional[str]  = None
    # Totals
    total:                int             = 0
    grievances:           int             = 0
    suggestions:          int             = 0
    applause:             int             = 0
    inquiries:            int             = 0
    resolved:             int             = 0
    open_count:           int             = 0
    escalated:            int             = 0
    dismissed:            int             = 0
    overdue:              int             = 0
    critical_open:        int             = 0
    high_open:            int             = 0
    avg_resolution_hours: Optional[float] = None
    resolution_rate:      Optional[float] = None
    escalation_rate:      Optional[float] = None
    # Breakdowns
    by_department: List[BranchDeptItem]     = Field(default_factory=list)
    by_category:   List[BranchCategoryItem] = Field(default_factory=list)
    by_service:    List[BranchServiceItem]  = Field(default_factory=list)
    trend:         List[BranchDayItem]      = Field(default_factory=list)
