"""models/employee_feedback.py — Employee internal org-feedback model."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class EmployeeCategory(str, Enum):
    WORKING_CONDITIONS = "working_conditions"
    MANAGEMENT         = "management"
    CULTURE            = "culture"
    COMPENSATION       = "compensation"
    TOOLS_RESOURCES    = "tools_resources"
    COMMUNICATION      = "communication"
    CAREER_GROWTH      = "career_growth"
    SAFETY             = "safety"
    TEAM_DYNAMICS      = "team_dynamics"
    LEADERSHIP         = "leadership"
    BENEFITS           = "benefits"
    OTHER              = "other"


class EFStatus(str, Enum):
    SUBMITTED    = "submitted"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED     = "resolved"
    CLOSED       = "closed"


class EmployeeFeedback(SQLModel, table=True):
    """
    Feedback submitted BY employees ABOUT their own organisation.
    Separate from consumer GRM feedback (feedbacks table) and
    from staff post-verification ratings (staff_feedbacks table).
    """
    __tablename__ = "employee_feedbacks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tracking_number: str = Field(max_length=20, unique=True, index=True)  # EF-2026-0001

    # Always org-scoped — resolved from JWT at submission
    org_id: uuid.UUID = Field(index=True)

    # Classification
    feedback_type: str = Field(max_length=20, index=True)  # grievance|suggestion|applause|inquiry
    category: str = Field(max_length=40, index=True)        # EmployeeCategory value

    # Content
    subject: Optional[str] = Field(default=None, max_length=500)
    description: str = Field(sa_column=Column("description", Text, nullable=False))

    # Submitter identity
    is_anonymous: bool = Field(default=False, index=True)
    employee_user_id: Optional[uuid.UUID] = Field(default=None, index=True)  # null when anonymous
    employee_name: Optional[str] = Field(default=None, max_length=255)

    # Org sub-scope (optional context)
    department_id: Optional[uuid.UUID] = Field(default=None, index=True)
    branch_id: Optional[uuid.UUID] = Field(default=None, index=True)

    # Lifecycle
    status: str = Field(default=EFStatus.SUBMITTED, index=True)
    management_response: Optional[str] = Field(
        default=None,
        sa_column=Column("management_response", Text),
    )
    responded_at: Optional[datetime] = Field(default=None)
    responded_by_user_id: Optional[uuid.UUID] = Field(default=None)

    # Timestamps
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
