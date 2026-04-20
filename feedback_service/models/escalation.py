# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service  |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  models/escalation.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/escalation.py
═══════════════════════════════════════════════════════════════════════════════
Dynamic, per-organisation GRM escalation hierarchy.

Design rationale
────────────────
The original system hardcoded the TARURA/TANROADS chain:
  WARD → LGA_GRM_UNIT → COORDINATING_UNIT → TARURA_WBCU → TANROADS → WORLD_BANK

This is retained as a seeded system template (is_system_template=True) but
each organisation can now define its own hierarchy.  Examples:

  Road contractor:    Branch → District Engineer → Regional Manager → HQ
  NGO/CBO:            Field Officer → Programme Manager → Executive Director
  World Bank project: Ward GHC → LGA GRM Unit → Coordinating Unit → WBCU → World Bank

Hierarchy selection
────────────────────
  ProjectCache.escalation_path_id  → project-specific path
  if NULL  →  organisation default path (is_default=True, org_id match)
  if NULL  →  system template (is_system_template=True)

SLA configuration
──────────────────
  Each EscalationLevel defines:
    ack_sla_hours        — hours to acknowledge at this level
    resolution_sla_hours — hours to resolve at this level
    sla_overrides        — per-priority overrides (JSONB)
      {"critical": {"ack_hours": 4, "resolution_hours": 24},
       "high":     {"ack_hours": 8, "resolution_hours": 72}, ...}

  If a level has no SLA configured, the system falls back to the
  hardcoded priority-based defaults.

Auto-escalation
────────────────
  auto_escalate_on_breach=True causes the APScheduler job to auto-promote
  a feedback when its SLA is exceeded at this level.
  auto_escalate_after_hours adds a grace period after the breach.

Backward compatibility
───────────────────────
  grm_level_ref maps an EscalationLevel to the legacy GRMLevel enum value
  ("ward", "lga_grm_unit", etc.).  The Feedback model still stores current_level
  (GRMLevel) alongside current_level_id (EscalationLevel UUID) so that
  existing analytics queries and Spark jobs remain valid.
═══════════════════════════════════════════════════════════════════════════════
"""
# NOTE: do NOT add `from __future__ import annotations` here.
# It stringifies all annotations at import time, which breaks SQLModel's
# List["Model"] relationship resolution (same issue as models/feedback.py).

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.project import ProjectCache


# ─────────────────────────────────────────────────────────────────────────────
# Default SLA values (mirrors the old hardcoded report_service constants)
# Used as the system template seed and as fallback when a level has no SLA set.
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_DEFAULT_SLA_OVERRIDES: Dict[str, Dict] = {
    "critical": {"ack_hours": 24,  "resolution_hours": 168},
    "high":     {"ack_hours": 48,  "resolution_hours": 336},
    "medium":   {"ack_hours": 120, "resolution_hours": 720},
    "low":      {"ack_hours": 240, "resolution_hours": None},
}

# System template seed — the TARURA/TANROADS chain becomes a DB record
SYSTEM_TEMPLATE_SEED = {
    "name": "TARURA / TANROADS GRM (Tanzania Default)",
    "description": (
        "Default GRM escalation hierarchy for TARURA and TANROADS infrastructure "
        "programmes in Tanzania. Matches the World Bank SEP escalation chain."
    ),
    "levels": [
        {
            "level_order": 1, "name": "Ward GRM Committee", "code": "ward",
            "description": "Ward-level Grievance Handling Committee (GHC). First point of contact.",
            "grm_level_ref": "ward", "is_final": False,
            "auto_escalate_on_breach": False,
            "sla_overrides": SYSTEM_DEFAULT_SLA_OVERRIDES,
        },
        {
            "level_order": 2, "name": "LGA GRM Unit", "code": "lga_grm_unit",
            "description": "Local Government Authority — GRM Unit.",
            "grm_level_ref": "lga_grm_unit", "is_final": False,
            "auto_escalate_on_breach": False,
            "sla_overrides": SYSTEM_DEFAULT_SLA_OVERRIDES,
        },
        {
            "level_order": 3, "name": "Coordinating Unit", "code": "coordinating_unit",
            "description": "Coordinating Unit — central coordination level.",
            "grm_level_ref": "coordinating_unit", "is_final": False,
            "auto_escalate_on_breach": False,
            "sla_overrides": SYSTEM_DEFAULT_SLA_OVERRIDES,
        },
        {
            "level_order": 4, "name": "TARURA World Bank Coordinating Unit", "code": "tarura_wbcu",
            "description": "TARURA WBCU — national programme oversight.",
            "grm_level_ref": "tarura_wbcu", "is_final": False,
            "auto_escalate_on_breach": False,
            "sla_overrides": SYSTEM_DEFAULT_SLA_OVERRIDES,
        },
        {
            "level_order": 5, "name": "TANROADS", "code": "tanroads",
            "description": "TANROADS — for road and bridge-specific escalations.",
            "grm_level_ref": "tanroads", "is_final": False,
            "auto_escalate_on_breach": False,
            "sla_overrides": SYSTEM_DEFAULT_SLA_OVERRIDES,
        },
        {
            "level_order": 6, "name": "World Bank", "code": "world_bank",
            "description": "Final escalation level. No further escalation possible.",
            "grm_level_ref": "world_bank", "is_final": True,
            "auto_escalate_on_breach": False,
            "sla_overrides": SYSTEM_DEFAULT_SLA_OVERRIDES,
        },
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# EscalationPath
# ─────────────────────────────────────────────────────────────────────────────

class EscalationPath(SQLModel, table=True):
    """
    An organisation's GRM escalation hierarchy.

    One org may have multiple paths (e.g. one per project type).
    Exactly one path per org should have is_default=True.

    System templates (is_system_template=True) have org_id=NULL.
    They are read-only — the UI/API prevents modification.
    Orgs can clone a template via the /escalation-paths/from-template endpoint
    to get an editable copy.

    Hierarchy resolution at feedback submission:
      1. ProjectCache.escalation_path_id   (project-specific)
      2. org default path (org_id match, is_default=True)
      3. system template  (is_system_template=True)
    """
    __tablename__ = "escalation_paths"
    __table_args__ = (
        # Partial unique index: at most one default path per org.
        # Use Index (not UniqueConstraint) because partial indexes require postgresql_where.
        Index(
            "uq_escalation_path_org_default",
            "org_id", "is_default",
            unique=True,
            postgresql_where=text("is_default = true"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # NULL for system templates
    org_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="Soft link to auth_service Organisation.id. NULL for system templates.",
    )
    # Soft link to ProjectCache — path applies only to this project when set
    project_id: Optional[uuid.UUID] = Field(
        sa_column=Column(ForeignKey("fb_projects.id", ondelete="SET NULL"), nullable=True, index=True),
        description="When set, this path applies only to this project. NULL = org-wide.",
    )

    name:        str            = Field(max_length=255, nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    is_default:         bool = Field(default=False, nullable=False, index=True,
                                     description="One true per org. Used when no project-specific path is set.")
    is_system_template: bool = Field(default=False, nullable=False, index=True,
                                     description="Read-only built-in template. Cannot be edited or deleted.")
    is_active:          bool = Field(default=True, nullable=False, index=True)

    created_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id who created this path.",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"),
            onupdate=text("now()"), nullable=False,
        )
    )

    # Relationships
    levels:  List["EscalationLevel"] = Relationship(
        back_populates="path",
        sa_relationship_kwargs={"order_by": "EscalationLevel.level_order", "cascade": "all, delete-orphan"},
    )
    project: Optional["ProjectCache"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[EscalationPath.project_id]"}
    )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def sorted_levels(self) -> List["EscalationLevel"]:
        """Return levels sorted by level_order (ascending)."""
        return sorted(self.levels, key=lambda l: l.level_order)

    def first_level(self) -> Optional["EscalationLevel"]:
        levels = self.sorted_levels()
        return levels[0] if levels else None

    def next_level(self, current_level_id: uuid.UUID) -> Optional["EscalationLevel"]:
        """Return the level immediately after current_level_id, or None if at the end."""
        levels = self.sorted_levels()
        for i, lv in enumerate(levels):
            if lv.id == current_level_id:
                return levels[i + 1] if i + 1 < len(levels) else None
        return None

    def get_level_by_id(self, level_id: uuid.UUID) -> Optional["EscalationLevel"]:
        return next((l for l in self.levels if l.id == level_id), None)

    def __repr__(self) -> str:
        return f"<EscalationPath {self.name!r} org={self.org_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# EscalationLevel
# ─────────────────────────────────────────────────────────────────────────────

class EscalationLevel(SQLModel, table=True):
    """
    One step in an EscalationPath.

    Levels are ordered by level_order (1 = entry point, N = final).
    The is_final flag marks the last level from which no further
    escalation is possible (typically "World Bank" or "CEO").

    SLA resolution order for a given feedback:
      1. sla_overrides[priority]["ack_hours" / "resolution_hours"]
      2. ack_sla_hours / resolution_sla_hours (level-wide defaults)
      3. System hardcoded defaults (report_service._ACK_SLA_H)

    grm_level_ref
    ─────────────
    Maps this dynamic level back to the legacy GRMLevel enum for backward
    compatibility with existing analytics queries and Spark streaming jobs.
    Set to None for org-specific levels that have no GRM equivalent.
    """
    __tablename__ = "escalation_levels"
    __table_args__ = (
        UniqueConstraint("path_id", "level_order", name="uq_escalation_level_order"),
        UniqueConstraint("path_id", "code",        name="uq_escalation_level_code"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    path_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("escalation_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    )

    level_order: int = Field(
        sa_column=Column(Integer, nullable=False),
        description="1-based ordering. Level 1 is the entry point (e.g. Ward).",
    )

    # Display
    name: str = Field(max_length=255, nullable=False,
                      description="Human-readable level name, e.g. 'Ward GHC', 'Branch Manager'.")
    code: str = Field(max_length=50, nullable=False,
                      description="Slug unique within the path, e.g. 'ward_ghc', 'branch_manager'.")
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    is_final: bool = Field(
        default=False, nullable=False,
        description="True for the last level. No further escalation is possible from here.",
    )

    # ── SLA configuration ─────────────────────────────────────────────────────
    ack_sla_hours: Optional[int] = Field(
        default=None, nullable=True,
        description="Hours to acknowledge at this level. NULL = use priority default.",
    )
    resolution_sla_hours: Optional[int] = Field(
        default=None, nullable=True,
        description="Hours to resolve at this level. NULL = use priority default.",
    )
    # Per-priority overrides: {"critical": {"ack_hours": 4, "resolution_hours": 24}, ...}
    sla_overrides: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description=(
            "Priority-specific SLA overrides. Keys: 'critical', 'high', 'medium', 'low'. "
            "Values: {'ack_hours': int|null, 'resolution_hours': int|null}. "
            "Overrides ack_sla_hours/resolution_sla_hours for the matching priority."
        ),
    )

    # ── Auto-escalation ────────────────────────────────────────────────────────
    auto_escalate_on_breach: bool = Field(
        default=False, nullable=False,
        description="If True, the APScheduler job auto-escalates on SLA breach.",
    )
    auto_escalate_after_hours: Optional[int] = Field(
        default=None, nullable=True,
        description=(
            "Additional grace hours after SLA breach before auto-escalation fires. "
            "NULL means escalate immediately when breach is detected."
        ),
    )

    # ── Responsible role / notifications ─────────────────────────────────────
    responsible_role: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Role tag for notifications, e.g. 'ward_officer', 'regional_manager'.",
    )
    # JSONB list of email addresses notified when a feedback reaches this level
    notify_emails: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="List of email addresses to notify when feedback reaches this level.",
    )

    # ── Backward compatibility ─────────────────────────────────────────────────
    grm_level_ref: Optional[str] = Field(
        default=None, max_length=30, nullable=True, index=True,
        description=(
            "Maps to the legacy GRMLevel enum value (e.g. 'ward', 'lga_grm_unit', 'coordinating_unit', 'world_bank'). "
            "NULL for org-specific levels with no legacy equivalent. "
            "Used to keep Feedback.current_level (GRMLevel) in sync for analytics."
        ),
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"),
            onupdate=text("now()"), nullable=False,
        )
    )

    # Relationships
    path: EscalationPath = Relationship(back_populates="levels")

    # ── SLA helpers ───────────────────────────────────────────────────────────

    def get_sla_hours(self, priority: str) -> tuple[Optional[int], Optional[int]]:
        """
        Return (ack_hours, resolution_hours) for the given priority string.

        Resolution order:
          1. sla_overrides[priority]
          2. ack_sla_hours / resolution_sla_hours (level-wide)
          3. (None, None) — caller falls back to system defaults
        """
        pkey = (priority or "medium").lower()
        if self.sla_overrides and pkey in self.sla_overrides:
            ov = self.sla_overrides[pkey]
            return ov.get("ack_hours"), ov.get("resolution_hours")
        return self.ack_sla_hours, self.resolution_sla_hours

    def __repr__(self) -> str:
        return f"<EscalationLevel [{self.level_order}] {self.name!r} path={self.path_id}>"
