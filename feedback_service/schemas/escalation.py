# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service  |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  schemas/escalation.py
# ───────────────────────────────────────────────────────────────────────────
"""
schemas/escalation.py
Pydantic request/response schemas for the dynamic escalation path API.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Level schemas
# ─────────────────────────────────────────────────────────────────────────────

class SLAOverride(BaseModel):
    """Per-priority SLA configuration."""
    ack_hours:        Optional[int] = Field(default=None, ge=1, description="Hours to acknowledge. NULL = no SLA.")
    resolution_hours: Optional[int] = Field(default=None, ge=1, description="Hours to resolve. NULL = no SLA.")


class EscalationLevelCreate(BaseModel):
    """Body for adding a level to a path."""
    level_order: int = Field(..., ge=1, description="Position in the chain. 1 = entry point.")
    name:        str = Field(..., min_length=2, max_length=255, description="Display name, e.g. 'Ward GHC'.")
    code:        str = Field(..., min_length=2, max_length=50,  description="Slug unique within path, e.g. 'ward_ghc'.")
    description: Optional[str] = None

    is_final: bool = Field(
        default=False,
        description="True = no further escalation from this level.",
    )

    # SLA
    ack_sla_hours:        Optional[int] = Field(default=None, ge=1)
    resolution_sla_hours: Optional[int] = Field(default=None, ge=1)
    sla_overrides: Optional[Dict[str, SLAOverride]] = Field(
        default=None,
        description=(
            "Per-priority SLA overrides. Keys: 'critical', 'high', 'medium', 'low'. "
            "Overrides ack_sla_hours/resolution_sla_hours for that priority."
        ),
    )

    # Auto-escalation
    auto_escalate_on_breach:   bool         = False
    auto_escalate_after_hours: Optional[int] = Field(default=None, ge=0)

    # Notifications
    responsible_role: Optional[str] = Field(default=None, max_length=100)
    notify_emails:    Optional[List[str]] = None

    # Org structure link
    responsible_org_unit: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Soft links to org entities responsible at this level. "
            "Keys: department_id (UUID str), branch_id (UUID str), "
            "user_ids (list of UUID str), committee_id (UUID str)."
        ),
    )
    consumer_visible_name: Optional[str] = Field(
        default=None, max_length=255,
        description="Level name shown to the feedback submitter. Hides internal org structure terms.",
    )

    # Backward compat
    grm_level_ref: Optional[str] = Field(
        default=None, max_length=30,
        description="Legacy GRMLevel enum value. Set to 'ward', 'lga_grm_unit', 'coordinating_unit', etc. for backward compat.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "level_order": 1,
                "name": "Ward GRM Committee",
                "code": "ward_ghc",
                "description": "First point of contact — ward-level grievance handling.",
                "is_final": False,
                "sla_overrides": {
                    "critical": {"ack_hours": 24, "resolution_hours": 168},
                    "high":     {"ack_hours": 48, "resolution_hours": 336},
                    "medium":   {"ack_hours": 120, "resolution_hours": 720},
                    "low":      {"ack_hours": 240, "resolution_hours": None},
                },
                "auto_escalate_on_breach": False,
                "grm_level_ref": "ward",
            }
        }
    }


class EscalationLevelUpdate(BaseModel):
    """Body for PATCH .../levels/{level_id}. All fields optional."""
    name:                     Optional[str]  = Field(default=None, min_length=2, max_length=255)
    description:              Optional[str]  = None
    is_final:                 Optional[bool] = None
    ack_sla_hours:            Optional[int]  = Field(default=None, ge=1)
    resolution_sla_hours:     Optional[int]  = Field(default=None, ge=1)
    sla_overrides:            Optional[Dict[str, SLAOverride]] = None
    auto_escalate_on_breach:  Optional[bool] = None
    auto_escalate_after_hours: Optional[int] = Field(default=None, ge=0)
    responsible_role:         Optional[str]  = Field(default=None, max_length=100)
    notify_emails:            Optional[List[str]] = None
    responsible_org_unit:     Optional[Dict[str, Any]] = None
    consumer_visible_name:    Optional[str]  = Field(default=None, max_length=255)
    grm_level_ref:            Optional[str]  = Field(default=None, max_length=30)


class EscalationLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          uuid.UUID
    path_id:     uuid.UUID
    level_order: int
    name:        str
    code:        str
    description: Optional[str] = None
    is_final:    bool

    ack_sla_hours:             Optional[int] = None
    resolution_sla_hours:      Optional[int] = None
    sla_overrides:             Optional[Dict[str, Any]] = None
    auto_escalate_on_breach:   bool
    auto_escalate_after_hours: Optional[int] = None
    responsible_role:          Optional[str] = None
    notify_emails:             Optional[List[str]] = None
    responsible_org_unit:      Optional[Dict[str, Any]] = None
    consumer_visible_name:     Optional[str] = None
    grm_level_ref:             Optional[str] = None

    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Path schemas
# ─────────────────────────────────────────────────────────────────────────────

class EscalationPathCreate(BaseModel):
    """Body for POST /escalation-paths."""
    name:        str            = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    project_id:  Optional[uuid.UUID] = Field(
        default=None,
        description="If set, this path applies only to this project. NULL = org-wide.",
    )
    is_default:  bool = Field(
        default=False,
        description="Set as the org's default path. Clears the previous default.",
    )
    applies_to_feedback_types: Optional[List[str]] = Field(
        default=None,
        description="Feedback types this path handles: grievance, suggestion, applause, inquiry. NULL = all types.",
    )
    levels: Optional[List[EscalationLevelCreate]] = Field(
        default=None,
        description="Optionally define levels inline. Can also be added later via POST .../levels.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Road Construction GRM — Branch Level",
                "description": "Custom escalation hierarchy for branch-level road projects.",
                "is_default": True,
                "levels": [
                    {"level_order": 1, "name": "Branch GRM Officer",    "code": "branch_grm", "grm_level_ref": "ward"},
                    {"level_order": 2, "name": "District Engineer",     "code": "district_eng"},
                    {"level_order": 3, "name": "Regional Manager",      "code": "regional_mgr"},
                    {"level_order": 4, "name": "Headquarters (HQ GRM)", "code": "hq_grm", "is_final": True,
                     "grm_level_ref": "world_bank"},
                ],
            }
        }
    }


class EscalationPathClone(BaseModel):
    """Body for POST /escalation-paths/from-template."""
    template_id:    uuid.UUID = Field(..., description="UUID of the source path or system template to clone.")
    name:           str       = Field(..., min_length=2, max_length=255, description="Name for the new path.")
    set_as_default: bool      = Field(default=False, description="Make this the org's default escalation path.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Our TARURA GRM Chain (copy)",
                "set_as_default": True,
            }
        }
    }


class EscalationLevelReorder(BaseModel):
    """Body for POST /escalation-paths/{path_id}/levels/reorder."""
    ordered_level_ids: List[uuid.UUID] = Field(
        ...,
        description="All level IDs in the desired order. First item → level_order=1.",
    )

    @model_validator(mode="after")
    def check_non_empty(self) -> "EscalationLevelReorder":
        if not self.ordered_level_ids:
            raise ValueError("ordered_level_ids must not be empty.")
        return self


class EscalationPathUpdate(BaseModel):
    """Body for PATCH /escalation-paths/{path_id}."""
    name:        Optional[str]  = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    is_default:  Optional[bool] = None
    is_active:   Optional[bool] = None
    applies_to_feedback_types: Optional[List[str]] = None


class EscalationPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                         uuid.UUID
    org_id:                     Optional[uuid.UUID] = None
    project_id:                 Optional[uuid.UUID] = None
    name:                       str
    description:                Optional[str] = None
    is_default:                 bool
    is_system_template:         bool
    is_active:                  bool
    template_key:               Optional[str] = None
    applies_to_feedback_types:  Optional[List[str]] = None
    created_by_user_id:         Optional[uuid.UUID] = None
    created_at:                 datetime
    updated_at:                 datetime
    levels:                     List[EscalationLevelResponse] = []


class EscalationPathListResponse(BaseModel):
    total:  int
    items:  List[EscalationPathResponse]


# ─────────────────────────────────────────────────────────────────────────────
# Quick Setup Wizard schemas
# ─────────────────────────────────────────────────────────────────────────────

class LevelCustomization(BaseModel):
    """
    Override specific fields of a template level during quick setup.
    Only supplied fields are changed — unset fields keep the template defaults.
    """
    level_order: int = Field(..., ge=1, description="Which template level to customise (1-based).")
    name:                     Optional[str]  = Field(default=None, max_length=255, description="Override the level name.")
    consumer_visible_name:    Optional[str]  = Field(default=None, max_length=255, description="Name shown to submitters.")
    description:              Optional[str]  = None
    ack_sla_hours:            Optional[int]  = Field(default=None, ge=1)
    resolution_sla_hours:     Optional[int]  = Field(default=None, ge=1)
    auto_escalate_on_breach:  Optional[bool] = None
    auto_escalate_after_hours: Optional[int] = Field(default=None, ge=0)
    notify_emails:            Optional[List[str]] = None
    responsible_org_unit: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Link this level to your org structure. "
            "Keys: department_id, branch_id, user_ids (list), committee_id."
        ),
    )
    is_final: Optional[bool] = None


class EscalationQuickSetup(BaseModel):
    """
    One-call wizard: pick a template, name it, customise any levels, done.

    The system copies all levels from the chosen template, then applies your
    `level_customizations` on top. You only need to specify the fields you
    want to change — everything else keeps the template default.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Yas Tanzania Customer Escalation",
            "template_key": "CUSTOMER_SERVICE_3_LEVEL",
            "set_as_default": True,
            "applies_to_feedback_types": ["grievance"],
            "level_customizations": [
                {
                    "level_order": 1,
                    "name": "Customer Care",
                    "consumer_visible_name": "Customer Support Team",
                    "responsible_org_unit": {
                        "department_id": "afd5b4e2-10f5-4874-b1da-248a74091805"
                    },
                    "notify_emails": ["customercare@yas.co.tz"],
                    "resolution_sla_hours": 24
                },
                {
                    "level_order": 2,
                    "name": "CC Manager",
                    "responsible_org_unit": {
                        "user_ids": ["5183174a-bcad-4e68-bf06-700d1f1260dc"]
                    },
                    "notify_emails": ["cc.manager@yas.co.tz"],
                    "auto_escalate_on_breach": True
                },
                {
                    "level_order": 3,
                    "name": "CEO Office",
                    "consumer_visible_name": "Senior Leadership",
                    "notify_emails": ["ceo@yas.co.tz"],
                    "is_final": True
                }
            ]
        }
    })

    name: str = Field(..., min_length=2, max_length=255, description="Name for the new escalation path.")
    template_key: str = Field(
        ...,
        description=(
            "Which built-in template to start from. "
            "Use GET /escalation-paths/available-templates to see all options."
        ),
    )
    set_as_default: bool = Field(
        default=True,
        description="Make this the org's default escalation path. Clears the previous default.",
    )
    applies_to_feedback_types: Optional[List[str]] = Field(
        default=None,
        description="Restrict this path to specific feedback types. NULL = applies to all.",
    )
    level_customizations: Optional[List[LevelCustomization]] = Field(
        default=None,
        description=(
            "Per-level overrides applied on top of the template defaults. "
            "Match by level_order. Levels not listed keep the template values unchanged."
        ),
    )


class AvailableTemplateItem(BaseModel):
    """One entry from the template catalogue."""
    template_key:    str
    display_name:    str
    description:     str
    org_types_hint:  List[str]
    level_count:     int
