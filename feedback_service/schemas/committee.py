"""schemas/committee.py — Pydantic schemas for GRM committee management."""
from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateCommittee(BaseModel):
    """
    Create a Grievance Handling Committee (GHC).
    Each GHC operates at a specific GRM level and handles grievances
    for a project within its jurisdiction (LGA/ward).
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Kariakoo Ward GHC",
            "level": "ward",
            "project_id": "71274571-a3c0-4372-8a68-23880e02a578",
            "lga": "Ilala",
            "description": "Ward-level Grievance Handling Committee for Kariakoo area under Msimbazi project",
        }
    })

    name: str = Field(
        ..., min_length=3, max_length=255,
        description="Committee name (e.g. 'Kariakoo Ward GHC', 'Ilala LGA GRM Unit Committee')",
    )
    level: str = Field(
        ...,
        description=(
            "GRM escalation level this committee handles. "
            "ward = Level 1 (community). "
            "lga_grm_unit = Level 2 (LGA GRM Unit). "
            "coordinating_unit = Level 3 (Coordinating Unit). "
            "tarura_wbcu = Level 4 (TARURA World Bank Unit). "
            "tanroads = Level 5 (road/bridge-specific)."
        ),
        json_schema_extra={"enum": ["ward", "lga_grm_unit", "coordinating_unit", "tarura_wbcu", "tanroads"]},
    )
    project_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Project this committee handles grievances for. Null = cross-project committee.",
    )
    lga: Optional[str] = Field(
        default=None, max_length=100,
        description="LGA jurisdiction (e.g. 'Ilala', 'Kinondoni'). Required for ward and lga_piu levels.",
    )
    org_sub_project_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Sub-project scope — if this GHC only handles a specific sub-project.",
    )
    description: Optional[str] = Field(
        default=None, max_length=500,
        description="Description of the committee's scope and responsibilities.",
    )
    stakeholder_ids: Optional[List[uuid.UUID]] = Field(
        default=None,
        description="Stakeholder group UUIDs this committee covers (from stakeholder_service).",
    )


class UpdateCommittee(BaseModel):
    """Update an existing GHC. Only include fields to change."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Kariakoo Ward GHC - Phase 2",
            "description": "Updated scope for Phase 2 construction",
            "is_active": True,
        }
    })

    name: Optional[str] = Field(default=None, min_length=3, max_length=255, description="New committee name")
    lga: Optional[str] = Field(default=None, max_length=100, description="Updated LGA jurisdiction")
    description: Optional[str] = Field(default=None, max_length=500, description="Updated description")
    is_active: Optional[bool] = Field(default=None, description="Set false to deactivate the committee")
    org_sub_project_id: Optional[uuid.UUID] = Field(default=None, description="Updated sub-project scope")
    stakeholder_ids: Optional[List[uuid.UUID]] = Field(default=None, description="Replace covered stakeholder groups")


class AddCommitteeMember(BaseModel):
    """Add a member to a GHC."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "7caa7de5-a260-43f8-9da1-30bc907be8ef",
            "role": "chairperson",
        }
    })

    user_id: uuid.UUID = Field(
        ...,
        description="Riviwa User ID of the person to add to this committee.",
    )
    role: str = Field(
        default="member",
        description=(
            "Role within the committee. "
            "chairperson = leads the committee. "
            "secretary = records minutes and coordinates. "
            "member = regular committee member."
        ),
        json_schema_extra={"enum": ["chairperson", "secretary", "member"]},
    )
