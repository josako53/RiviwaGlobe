"""
schemas/department.py
─────────────────────────────────────────────────────────────────────────────
Pydantic request / response schemas for OrgDepartment endpoints.
"""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateDepartment(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Human Resources",
            "code": "HR",
            "description": "Manages recruitment, payroll, and employee relations.",
            "branch_id": None,
            "sort_order": 0,
        }
    })

    name: str = Field(..., min_length=1, max_length=150,
                      description="Department display name e.g. 'Human Resources', 'Finance'")
    code: Optional[str] = Field(default=None, max_length=30,
                                description="Short code e.g. 'HR', 'FIN'. Optional.")
    description: Optional[str] = Field(default=None,
                                       description="Department mandate / responsibilities")
    branch_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Scope to a specific branch. Omit (null) for an org-wide department.",
    )
    sort_order: int = Field(default=0, description="Display order; lower = first")


class UpdateDepartment(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {"name": "People & Culture", "code": "PC", "sort_order": 1}
    })

    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    code: Optional[str] = Field(default=None, max_length=30)
    description: Optional[str] = Field(default=None)
    branch_id: Optional[uuid.UUID] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class DepartmentOut(BaseModel):
    id:          uuid.UUID
    org_id:      uuid.UUID
    branch_id:   Optional[uuid.UUID]
    name:        str
    code:        Optional[str]
    description: Optional[str]
    sort_order:  int
    is_active:   bool
    created_at:  str
    updated_at:  str

    model_config = ConfigDict(from_attributes=True)
