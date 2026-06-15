"""
schemas/industry.py
─────────────────────────────────────────────────────────────────────────────
Pydantic request / response schemas for industry and custom field endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Industry ──────────────────────────────────────────────────────────────────

class IndustryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          uuid.UUID
    name:        str
    slug:        str
    description: Optional[str] = None
    icon_url:    Optional[str] = None
    parent_id:   Optional[uuid.UUID] = None
    sort_order:  int
    is_active:   bool


# ── OrganisationIndustry ──────────────────────────────────────────────────────

class OrgIndustryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          uuid.UUID
    org_id:      uuid.UUID
    industry_id: uuid.UUID
    is_primary:  bool
    industry:    Optional[IndustryOut] = None
    created_at:  datetime


class SetOrgIndustriesRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "industry_ids": ["<uuid-healthcare>", "<uuid-pharmacy>"],
            "primary_industry_id": "<uuid-healthcare>",
        }
    })

    industry_ids: List[uuid.UUID] = Field(
        ..., description="Full replacement list of industry UUIDs for this org"
    )
    primary_industry_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Which industry is the org's primary (marked is_primary=True)",
    )


# ── OrgCustomFieldDefinition ──────────────────────────────────────────────────

class CustomFieldDefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                      uuid.UUID
    org_id:                  uuid.UUID
    entity_type:             str
    field_key:               str
    label:                   str
    label_sw:                Optional[str] = None
    field_type:              str
    options:                 Optional[Any] = None
    placeholder:             Optional[str] = None
    help_text:               Optional[str] = None
    is_required:             bool
    is_visible_to_consumer:  bool
    feedback_types:          Optional[Any] = None
    industry_template_key:   Optional[str] = None
    sort_order:              int
    is_active:               bool
    created_by_id:           Optional[uuid.UUID] = None
    created_at:              datetime
    updated_at:              datetime


class CreateCustomFieldRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "entity_type": "feedback",
            "field_key": "patient_file_number",
            "label": "Patient File Number",
            "label_sw": "Nambari ya Faili la Mgonjwa",
            "field_type": "text",
            "is_required": True,
            "is_visible_to_consumer": True,
            "feedback_types": ["grievance", "inquiry"],
            "sort_order": 1,
        }
    })

    entity_type:             str = Field(..., max_length=30)
    field_key:               str = Field(..., max_length=100)
    label:                   str = Field(..., max_length=200)
    label_sw:                Optional[str] = Field(default=None, max_length=200)
    field_type:              str = Field(default="text", max_length=20)
    options:                 Optional[Any] = Field(default=None)
    placeholder:             Optional[str] = Field(default=None, max_length=300)
    help_text:               Optional[str] = Field(default=None, max_length=500)
    is_required:             bool = Field(default=False)
    is_visible_to_consumer:  bool = Field(default=True)
    feedback_types:          Optional[Any] = Field(default=None)
    sort_order:              int = Field(default=0)


class UpdateCustomFieldRequest(BaseModel):
    label:                   Optional[str] = Field(default=None, max_length=200)
    label_sw:                Optional[str] = Field(default=None, max_length=200)
    field_type:              Optional[str] = Field(default=None, max_length=20)
    options:                 Optional[Any] = Field(default=None)
    placeholder:             Optional[str] = Field(default=None, max_length=300)
    help_text:               Optional[str] = Field(default=None, max_length=500)
    is_required:             Optional[bool] = Field(default=None)
    is_visible_to_consumer:  Optional[bool] = Field(default=None)
    feedback_types:          Optional[Any] = Field(default=None)
    sort_order:              Optional[int] = Field(default=None)
    is_active:               Optional[bool] = Field(default=None)


class ApplyTemplateRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "industry_id": "<uuid-healthcare>",
            "entity_type": "feedback",
        }
    })

    industry_id: uuid.UUID = Field(..., description="Industry whose templates to import")
    entity_type: Optional[str] = Field(
        default=None,
        description="Filter to a specific entity type (e.g. 'feedback'). Null = import all.",
    )


# ── IndustryFieldTemplate ─────────────────────────────────────────────────────

class IndustryFieldTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     uuid.UUID
    industry_id:            uuid.UUID
    entity_type:            str
    field_key:              str
    label:                  str
    label_sw:               Optional[str] = None
    field_type:             str
    is_required:            bool
    is_visible_to_consumer: bool
    feedback_types:         Optional[Any] = None
    source_standard:        Optional[str] = None
    sort_order:             int
