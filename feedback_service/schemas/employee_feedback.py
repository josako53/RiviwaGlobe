"""schemas/employee_feedback.py — Request/response schemas for employee internal feedback."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

FeedbackType = Literal["grievance", "suggestion", "applause", "inquiry"]

EmployeeCategoryType = Literal[
    "working_conditions", "management", "culture", "compensation",
    "tools_resources", "communication", "career_growth", "safety",
    "team_dynamics", "leadership", "benefits", "other",
]


# ── Submission (any org member) ───────────────────────────────────────────────

class EmployeeFeedbackCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "feedback_type": "grievance",
            "category": "working_conditions",
            "subject": "No proper desk equipment in Mwanza branch",
            "description": "Staff in Mwanza are working on broken chairs and outdated computers. This affects our productivity and morale every day.",
            "is_anonymous": False,
            "branch_id": None,
            "department_id": None,
        }
    })

    feedback_type: FeedbackType = Field(..., description="grievance | suggestion | applause | inquiry")
    category: EmployeeCategoryType = Field(..., description="Area this feedback relates to")
    subject: Optional[str] = Field(default=None, max_length=500)
    description: str = Field(..., min_length=10, description="Detailed feedback — min 10 characters")
    is_anonymous: bool = Field(default=False, description="Hide your identity from org admins")
    department_id: Optional[uuid.UUID] = Field(default=None, description="Your department UUID")
    branch_id: Optional[uuid.UUID] = Field(default=None, description="Your branch UUID")


# ── Admin update (org admin only) ─────────────────────────────────────────────

class EmployeeFeedbackAdminUpdate(BaseModel):
    status: Optional[Literal["submitted", "acknowledged", "resolved", "closed"]] = None
    management_response: Optional[str] = Field(
        default=None,
        description="Official management response visible to the submitter",
    )


# ── Response ──────────────────────────────────────────────────────────────────

class EmployeeFeedbackResponse(BaseModel):
    id: uuid.UUID
    tracking_number: str
    org_id: uuid.UUID
    feedback_type: str
    category: str
    subject: Optional[str]
    description: str
    is_anonymous: bool
    employee_user_id: Optional[uuid.UUID]
    employee_name: Optional[str]
    department_id: Optional[uuid.UUID]
    branch_id: Optional[uuid.UUID]
    status: str
    management_response: Optional[str]
    responded_at: Optional[datetime]
    responded_by_user_id: Optional[uuid.UUID]
    submitted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeFeedbackListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[EmployeeFeedbackResponse]


class EmployeeFeedbackSubmitResponse(BaseModel):
    feedback_id: uuid.UUID
    tracking_number: str
    feedback_type: str
    status: str
    message: str
