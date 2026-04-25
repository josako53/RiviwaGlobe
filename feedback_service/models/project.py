# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  models/project.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/project.py
═══════════════════════════════════════════════════════════════════════════════
Local read-only cache of ProjectCache + ProjectStageCache from stakeholder_service
(originally sourced from auth_service OrgProject / OrgProjectStage).

The feedback_service maintains its own independent copy — same UUIDs, same
Kafka sync pattern, no HTTP dependency on other services at request time.

Additions specific to feedback_service:
  · ProjectCache carries accepts_grievances / accepts_suggestions / accepts_applause
    flags that gate what feedback types are allowed per project.
  · ProjectStageCache carries the same per-stage overrides — a project may
    accept grievances overall but disable applause during construction.
    Stage-level flags take precedence over project-level when the stage is ACTIVE.
═══════════════════════════════════════════════════════════════════════════════
"""
# from __future__ import annotations  # removed: breaks List[Model] SQLModel relationship annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, ForeignKey, Text, UniqueConstraint, text
from typing import List
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.feedback import Feedback


class ProjectStatus(str, Enum):
    PLANNING  = "planning"
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StageStatus(str, Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    SKIPPED   = "skipped"


class ProjectCache(SQLModel, table=True):
    """
    Read-only cache of OrgProject from auth_service.
    Updated via Kafka events on riviwa.org.events.
    The `id` is the same UUID as auth_service OrgProject.id.
    """
    __tablename__ = "fb_projects"

    id: uuid.UUID = Field(primary_key=True, nullable=False)

    organisation_id: uuid.UUID           = Field(nullable=False, index=True)
    branch_id:       Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    name:            str                 = Field(max_length=255, nullable=False, index=True)
    code:            Optional[str]       = Field(default=None, max_length=50, nullable=True)
    slug:            str                 = Field(max_length=255, nullable=False, index=True)
    status: ProjectStatus = Field(
        default=ProjectStatus.ACTIVE,
        sa_column=Column(SAEnum(ProjectStatus, name="fb_proj_status"), nullable=False, index=True),
    )
    category:    Optional[str] = Field(default=None, max_length=100, nullable=True, index=True)
    sector:      Optional[str] = Field(default=None, max_length=100, nullable=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    country_code: Optional[str] = Field(default=None, max_length=2,   nullable=True)
    region:       Optional[str] = Field(default=None, max_length=100, nullable=True)
    primary_lga:  Optional[str] = Field(default=None, max_length=100, nullable=True)
    start_date:   Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    end_date:     Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))

    # ── Media ─────────────────────────────────────────────────────────────────
    cover_image_url:  Optional[str] = Field(default=None, max_length=500, nullable=True)
    org_logo_url:     Optional[str] = Field(default=None, max_length=500, nullable=True)
    # Synced from org.created / org.updated events so analytics can resolve names
    org_display_name: Optional[str] = Field(default=None, max_length=255, nullable=True)

    # ── Feedback acceptance gates ─────────────────────────────────────────────
    # These mirror the flags on ProjectCache in stakeholder_service.
    # Stage-level flags (ProjectStageCache) override these when a stage is ACTIVE.
    accepts_grievances:  bool = Field(default=True,  nullable=False)
    accepts_suggestions: bool = Field(default=True,  nullable=False)
    accepts_applause:    bool = Field(default=True,   nullable=False)

    # ── Dynamic escalation path ────────────────────────────────────────────────
    # When set, feedback submitted to this project uses this specific escalation
    # hierarchy instead of the org default or system template.
    # Soft link — no FK constraint (escalation_paths lives in the same DB but
    # we keep this nullable/unvalidated so it can be set before the path exists).
    escalation_path_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "EscalationPath.id to use for this project. "
            "NULL = fall back to org default path or system template."
        ),
    )

    synced_at:    datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False))
    published_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at:   datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False))
    updated_at:   datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False))

    stages:   List["ProjectStageCache"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "ProjectStageCache.stage_order"},
    )
    feedbacks: List["Feedback"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all"},
    )

    def is_active(self) -> bool:
        return self.status == ProjectStatus.ACTIVE

    def active_stage(self) -> Optional["ProjectStageCache"]:
        """Returns the currently active stage if stages are loaded."""
        if not self.stages:
            return None
        for s in self.stages:
            if s.status == StageStatus.ACTIVE:
                return s
        return None

    def accepts_feedback_type(self, feedback_type: str) -> bool:
        """
        Check if this project accepts a given feedback type.
        If an active stage exists and has an explicit override, use that.
        Otherwise fall back to project-level flag.
        """
        stage = self.active_stage()
        if stage:
            if feedback_type == "grievance"  and stage.accepts_grievances  is not None:
                return stage.accepts_grievances
            if feedback_type == "suggestion" and stage.accepts_suggestions is not None:
                return stage.accepts_suggestions
            if feedback_type == "applause"   and stage.accepts_applause    is not None:
                return stage.accepts_applause
        # Project-level fallback
        if feedback_type == "grievance":  return self.accepts_grievances
        if feedback_type == "suggestion": return self.accepts_suggestions
        if feedback_type == "applause":   return self.accepts_applause
        return True

    def __repr__(self) -> str:
        return f"<ProjectCache {self.name!r} [{self.status}]>"


class ProjectStageCache(SQLModel, table=True):
    """Per-stage cache. Stage-level feedback flags override project-level when stage is ACTIVE."""
    __tablename__ = "fb_project_stages"
    __table_args__ = (UniqueConstraint("project_id", "stage_order", name="uq_fb_stage_order"),)

    id: uuid.UUID = Field(primary_key=True, nullable=False)
    project_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("fb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    name:        str = Field(max_length=255, nullable=False)
    stage_order: int = Field(nullable=False)
    status: StageStatus = Field(
        default=StageStatus.PENDING,
        sa_column=Column(SAEnum(StageStatus, name="fb_stage_status"), nullable=False, index=True),
    )
    description: Optional[str]  = Field(default=None, sa_column=Column(Text, nullable=True))
    start_date:  Optional[date]  = Field(default=None, sa_column=Column(Date, nullable=True))
    end_date:    Optional[date]  = Field(default=None, sa_column=Column(Date, nullable=True))

    # Nullable means "inherit from project" — explicit bool overrides project-level gate
    accepts_grievances:  Optional[bool] = Field(default=None, nullable=True)
    accepts_suggestions: Optional[bool] = Field(default=None, nullable=True)
    accepts_applause:    Optional[bool] = Field(default=None, nullable=True)

    synced_at:  datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False))

    project: ProjectCache = Relationship(back_populates="stages")

    def is_active(self) -> bool:
        return self.status == StageStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<ProjectStageCache {self.name!r} order={self.stage_order} [{self.status}]>"
