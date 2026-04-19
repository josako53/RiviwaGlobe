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

    # Backward compat
    grm_level_ref: Optional[str] = Field(
        default=None, max_length=30,
        description="Legacy GRMLevel enum value. Set to 'ward', 'lga_piu', etc. for backward compat.",
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


class EscalationPathUpdate(BaseModel):
    """Body for PATCH /escalation-paths/{path_id}."""
    name:        Optional[str]  = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    is_default:  Optional[bool] = None
    is_active:   Optional[bool] = None


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


class EscalationPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 uuid.UUID
    org_id:             Optional[uuid.UUID] = None
    project_id:         Optional[uuid.UUID] = None
    name:               str
    description:        Optional[str] = None
    is_default:         bool
    is_system_template: bool
    is_active:          bool
    created_by_user_id: Optional[uuid.UUID] = None
    created_at:         datetime
    updated_at:         datetime
    levels:             List[EscalationLevelResponse] = []


class EscalationPathListResponse(BaseModel):
    total:  int
    items:  List[EscalationPathResponse]
