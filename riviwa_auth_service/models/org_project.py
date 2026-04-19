# ───────────────────────────────────────────────────────────────────────────
# SERVICE   :  riviwa_auth_service
# PORT      :  Port: 8000
# DATABASE  :  DB: auth_db (5433)
# FILE      :  models/org_project.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/org_project.py
═══════════════════════════════════════════════════════════════════════════════
Project execution models — separate from OrgService (marketplace listings).

THE DISTINCTION
──────────────────────────────────────────────────────────────────────────────
  OrgService  (organisation_extended.py)
    → What the org LISTS and OFFERS on the Riviwa marketplace.
    → Has pricing, SKU, delivery mode, media, FAQs, policies.
    → Monitored via feedback_service (grievances, suggestions, applause).

  OrgProject  (this file)
    → What the org EXECUTES — construction, development programs, aid projects.
    → Has stages, sub-projects (infinitely nested), in-charges with duties.
    → Also monitored via feedback_service.
    → TARURA runs "Msimbazi Basin Development Project", "RISE", "TACTICS" etc.
    → Each is an OrgProject, not an OrgService.

HIERARCHY
──────────────────────────────────────────────────────────────────────────────

  Organisation (TARURA)
    └── OrgBranch (TARURA DSM Regional Office)         [existing]
          └── OrgProject ("Msimbazi Basin Dev Project")
                ├── OrgProjectInCharge (Project Director, Project Manager …)
                │
                ├── OrgProjectStage ("Preparation Stage")
                │     ├── OrgProjectStageInCharge (Stage Manager …)
                │     └── OrgSubProject ("Environmental Impact Assessment")
                │           ├── OrgSubProjectInCharge (EIA Lead, Field Officer …)
                │           └── OrgSubProject ("Baseline Survey")   ← nested
                │                 └── OrgSubProject ("Household Survey") ← deeper
                │
                ├── OrgProjectStage ("Construction Phase 1 — Lower Basin")
                │     ├── OrgProjectStageInCharge (Site Engineer …)
                │     ├── OrgSubProject ("River Dredging Works")
                │     │     └── OrgSubProjectInCharge (Contractor Lead, Site Supervisor …)
                │     └── OrgSubProject ("Jangwani Bridge Rehabilitation")
                │           └── OrgSubProjectInCharge (Bridge Engineer …)
                │
                └── OrgProjectStage ("Finalization and Handover")

SUB-PROJECT NESTING
──────────────────────────────────────────────────────────────────────────────
  OrgSubProject uses the same self-referential parent_subproject_id pattern
  as OrgBranch. Depth is unlimited — the application layer walks the tree
  using WITH RECURSIVE queries just like branch subtrees.

  At each level, in-charges (OrgSubProjectInCharge) can have distinct roles:
    - "Sub-project Coordinator"
    - "Field Engineer"
    - "Community Liaison Officer"
    - "Environmental Monitor"
  These are free-text role_title fields, not enums, to support any project type.

RELATIONSHIP WIRING
──────────────────────────────────────────────────────────────────────────────
  OrgProject.organisation      ←→  Organisation (existing model)
  OrgProject.branch            ←→  OrgBranch (existing model)
  OrgProject.stages            ←→  OrgProjectStage.project
  OrgProject.in_charges        ←→  OrgProjectInCharge.project
  OrgProjectStage.sub_projects ←→  OrgSubProject.stage
  OrgSubProject.children       ←→  OrgSubProject.parent  (self-ref)
  OrgSubProject.in_charges     ←→  OrgSubProjectInCharge.subproject
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Runtime imports — needed so SQLAlchemy mapper can resolve
# forward-reference strings like "Organisation" in Relationship().
# These are NOT circular: organisation.py and organisation_extended.py
# import OrgProject only under TYPE_CHECKING, so there is no import cycle.
from models.organisation import Organisation                      # noqa: F401
from models.organisation_extended import OrgBranch               # noqa: F401
from models.address import Address                                # noqa: F401

from sqlalchemy import CheckConstraint, Column, Date, DateTime, Enum as SAEnum, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.user import User



class ProjectStatus(str, Enum):
    """
    Lifecycle status of a project.

    PLANNING    → approved and being set up; no active work yet
    ACTIVE      → currently in execution
    PAUSED      → temporarily suspended (funding gap, political hold, etc.)
    COMPLETED   → all stages done and accepted
    CANCELLED   → terminated before completion
    """
    PLANNING   = "planning"
    ACTIVE     = "active"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"


class StageStatus(str, Enum):
    """
    Lifecycle status of a project stage.

    PENDING    → not yet started (future stage)
    ACTIVE     → currently in progress
    COMPLETED  → stage deliverables accepted
    SKIPPED    → stage was removed from scope
    """
    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    SKIPPED   = "skipped"


class SubProjectStatus(str, Enum):
    PENDING    = "pending"
    ACTIVE     = "active"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"


class ProjectVisibility(str, Enum):
    """
    Controls who can see this project in the Riviwa platform.

    PUBLIC     → visible to all platform users and the general public
    ORG_ONLY   → visible only to org members (internal project tracking)
    PRIVATE    → visible only to in-charges (sensitive / classified projects)
    """
    PUBLIC   = "public"
    ORG_ONLY = "org_only"
    PRIVATE  = "private"



class OrgProject(SQLModel, table=True):
    """
    An execution project owned by an Organisation or one of its Branches.

    Examples:
      · TARURA's "Msimbazi Basin Development Project"
      · TARURA's "RISE" (Road Infrastructure for Socio-Economic Development)
      · TARURA's "TACTICS" (Tanzania Transport for Climate-resilient Infrastructure)
      · US Department of State / USAID's "Tanzania Infrastructure Program"
      · A hospital's "New Outpatient Wing Construction Project"

    Key design decisions:
      · branch_id is nullable — project may be owned by the org directly or
        delegated to a specific branch (e.g. TARURA DSM Regional Office).
      · org_service_id is nullable — set when this project is also listed as
        an OrgService on the marketplace (e.g. a consulting firm listing
        project management as a service AND running actual projects).
      · visibility controls who sees this project on the platform.
      · objectives, background, expected_outcomes are rich text fields.
      · budget_amount + currency_code are optional for public-facing display.

    Relationships:
      OrgProject.organisation  ← Organisation.projects (to be back-populated)
      OrgProject.branch        ← OrgBranch.projects (to be back-populated)
      OrgProject.in_charges    → OrgProjectInCharge (overall leadership)
      OrgProject.stages        → OrgProjectStage (ordered phases)
    """
    __tablename__ = "org_projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── Ownership ─────────────────────────────────────────────────────────────
    organisation_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    # Nullable: project may be run directly by org or delegated to a branch
    branch_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_branches.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description="OrgBranch running this project. Null if run directly by the organisation.",
    )
    # Optional link: if this project is also an OrgService marketplace listing
    org_service_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "auth_service OrgService.id — set when this project is also listed "
            "as a marketplace service (e.g. a consulting firm's deliverable). "
            "No FK constraint — soft link."
        ),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: str = Field(max_length=255, nullable=False, index=True)
    code: Optional[str] = Field(
        default=None,
        max_length=50,
        nullable=True,
        unique=True,
        index=True,
        description="Short internal project code e.g. 'MVDP', 'RISE', 'TACTICS'.",
    )
    slug: str = Field(
        max_length=255,
        unique=True,
        index=True,
        nullable=False,
        description="URL-safe unique identifier e.g. 'msimbazi-basin-development-project'.",
    )

    # ── Classification ────────────────────────────────────────────────────────
    status: ProjectStatus = Field(
        default=ProjectStatus.PLANNING,
        sa_column=Column(SAEnum(ProjectStatus, name="project_status"), nullable=False, index=True),
    )
    visibility: ProjectVisibility = Field(
        default=ProjectVisibility.PUBLIC,
        sa_column=Column(SAEnum(ProjectVisibility, name="project_visibility"), nullable=False),
    )
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        index=True,
        description="Free-text category e.g. 'Infrastructure', 'Road Rehabilitation', 'Flood Control'.",
    )
    sector: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description="Sector e.g. 'Transport', 'Water', 'Health', 'Education'.",
    )

    # ── Narrative ─────────────────────────────────────────────────────────────
    description:       Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    background:        Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Context and rationale for the project.",
    )
    objectives:        Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Project Development Objective (PDO) and key results.",
    )
    expected_outcomes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Measurable outcomes and deliverables expected at completion.",
    )
    target_beneficiaries: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Who directly and indirectly benefits from this project.",
    )

    # ── Timeline ──────────────────────────────────────────────────────────────
    start_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )
    end_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )
    actual_start_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
        description="Actual start date if different from planned.",
    )
    actual_end_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )

    # ── Budget ────────────────────────────────────────────────────────────────
    budget_amount:  Optional[float] = Field(default=None, nullable=True)
    currency_code:  Optional[str]   = Field(default=None, max_length=3, nullable=True)
    funding_source: Optional[str]   = Field(
        default=None,
        max_length=500,
        nullable=True,
        description="e.g. 'World Bank IDA Credit', 'Government of Tanzania', 'USAID'.",
    )

    # ── Location ──────────────────────────────────────────────────────────────
    country_code:  Optional[str] = Field(default=None, max_length=2,   nullable=True)
    region:        Optional[str] = Field(default=None, max_length=100, nullable=True)
    primary_lga:   Optional[str] = Field(default=None, max_length=100, nullable=True)
    location_description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Narrative description of the project area e.g. 'Lower Msimbazi Basin from Selander Bridge to Kawawa Bridge'.",
    )

    # ── Media / Documents ─────────────────────────────────────────────────────
    cover_image_url: Optional[str] = Field(default=None, max_length=1024, nullable=True)
    document_urls: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='{"urls": [{"label": "SEP", "url": "..."}]}',
    )

    # ── Feedback settings ─────────────────────────────────────────────────────
    # Controls what types of feedback are accepted for this project
    accepts_grievances:  bool = Field(default=True,  nullable=False)
    accepts_suggestions: bool = Field(default=True,  nullable=False)
    accepts_applause:    bool = Field(default=True,  nullable=False)
    requires_grm:        bool = Field(
        default=False,
        nullable=False,
        description=(
            "True = formal GRM escalation hierarchy (World Bank SEP style) applies. "
            "Automatically True for all feedback in this system per design decision, "
            "but this flag allows reporting queries to distinguish project types."
        ),
    )

    # ── Audit ────────────────────────────────────────────────────────────────
    created_by_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description="auth_service User.id who created this project.",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    organisation: Organisation = Relationship(
        back_populates="projects",
        sa_relationship_kwargs={"foreign_keys": "[OrgProject.organisation_id]"},
    )
    branch: OrgBranch = Relationship(
        back_populates="projects",
        sa_relationship_kwargs={"foreign_keys": "[OrgProject.branch_id]"},
    )
    in_charges: OrgProjectInCharge = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    stages: OrgProjectStage = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "OrgProjectStage.stage_order",
        },
    )
    progress_images: ProjectProgressImage = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ProjectProgressImage.display_order, ProjectProgressImage.created_at",
            "primaryjoin": "ProjectProgressImage.project_id == OrgProject.id",
        },
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_active(self) -> bool:
        return self.status == ProjectStatus.ACTIVE

    def is_accepting_feedback(self) -> bool:
        return self.status in (ProjectStatus.ACTIVE, ProjectStatus.PLANNING)

    def duration_days(self) -> Optional[int]:
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    def __repr__(self) -> str:
        return f"<OrgProject {self.name!r} [{self.status}]>"



class OrgProjectInCharge(SQLModel, table=True):
    """
    A person responsible for the overall project.

    Multiple in-charges per project with different roles:
      · "Project Director" — executive accountability
      · "Project Manager" — day-to-day management
      · "Technical Lead" — technical oversight
      · "Financial Controller" — budget and procurement
      · "Environmental and Social Specialist" — safeguards
      · "Community Liaison Officer" — stakeholder relations

    `user_id` references auth_service User. The person must have a platform
    account to be assigned as an in-charge (they log in to manage the project).

    UNIQUE (project_id, user_id, role_title) — a person can hold multiple
    roles on the same project (e.g. both Technical Lead and Deputy PM),
    but not the same role twice.
    """
    __tablename__ = "org_project_in_charges"

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", "role_title", name="uq_project_incharge_role"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    project_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("org_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    # auth_service User.id — must have a platform account
    user_id: uuid.UUID = Field(nullable=False, index=True)

    role_title: str = Field(
        max_length=200,
        nullable=False,
        description="e.g. 'Project Director', 'Project Manager', 'Technical Lead'.",
    )
    duties: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Detailed description of responsibilities and authority.",
    )
    is_lead: bool = Field(
        default=False,
        nullable=False,
        description="True for the single primary in-charge (project lead).",
    )
    assigned_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    relieved_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When this person was relieved of this role (null = still active).",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    project: OrgProject = Relationship(back_populates="in_charges")

    def is_active(self) -> bool:
        return self.relieved_at is None

    def __repr__(self) -> str:
        return f"<OrgProjectInCharge user={self.user_id} role={self.role_title!r}>"



class OrgProjectStage(SQLModel, table=True):
    """
    A named phase or stage within a project.

    Stages are ordered (stage_order) and have their own timeline, objectives,
    in-charges, and sub-projects. They represent the major phases of project
    execution e.g.:
      1. Preparation Stage
      2. Feasibility and Design
      3. Construction Phase 1 — Lower Basin
      4. Construction Phase 2 — Upper Basin
      5. Finalization and Handover
      6. Operation and Maintenance

    Stakeholders are engaged PER STAGE — a stakeholder's importance, goals,
    interests, and allowed activities can differ between stages. This is
    tracked in the stakeholder_service's StakeholderStageEngagement table.

    UNIQUE (project_id, stage_order) — no two stages at the same position.
    """
    __tablename__ = "org_project_stages"

    __table_args__ = (
        UniqueConstraint("project_id", "stage_order", name="uq_project_stage_order"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    project_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("org_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: str = Field(
        max_length=255,
        nullable=False,
        description="e.g. 'Preparation Stage', 'Construction Phase 1'.",
    )
    stage_order: int = Field(
        nullable=False,
        description="1-based ordering. Stages are displayed in ascending order.",
    )
    status: StageStatus = Field(
        default=StageStatus.PENDING,
        sa_column=Column(SAEnum(StageStatus, name="stage_status"), nullable=False, index=True),
    )

    # ── Narrative ─────────────────────────────────────────────────────────────
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    objectives:  Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="What this stage must achieve before the next stage begins.",
    )
    deliverables: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Tangible outputs expected at the end of this stage.",
    )

    # ── Timeline ──────────────────────────────────────────────────────────────
    start_date: Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    end_date:   Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    actual_start_date: Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    actual_end_date:   Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))

    # ── Feedback settings (can differ from project-level defaults) ─────────────
    # Null = inherit from OrgProject. Non-null = override for this stage.
    accepts_grievances:  Optional[bool] = Field(default=None, nullable=True)
    accepts_suggestions: Optional[bool] = Field(default=None, nullable=True)
    accepts_applause:    Optional[bool] = Field(default=None, nullable=True)

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    project: OrgProject = Relationship(back_populates="stages")

    in_charges: OrgProjectStageInCharge = Relationship(
        back_populates="stage",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    sub_projects: OrgSubProject = Relationship(
        back_populates="stage",
        sa_relationship_kwargs={
            "primaryjoin": "OrgSubProject.stage_id == OrgProjectStage.id",
            "cascade": "all, delete-orphan",
        },
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_active(self) -> bool:
        return self.status == StageStatus.ACTIVE

    def duration_days(self) -> Optional[int]:
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    def __repr__(self) -> str:
        return f"<OrgProjectStage {self.name!r} order={self.stage_order} [{self.status}]>"



class OrgProjectStageInCharge(SQLModel, table=True):
    """
    A person responsible for a specific project stage.

    The stage in-charge may be different from the overall project in-charge.
    Example:
      · Project Manager (OrgProjectInCharge) oversees the whole project.
      · "Dredging Works Supervisor" (OrgProjectStageInCharge) only for
        "Construction Phase 1".
      · "Community Engagement Officer" only for "Preparation Stage".

    UNIQUE (stage_id, user_id, role_title).
    """
    __tablename__ = "org_project_stage_in_charges"

    __table_args__ = (
        UniqueConstraint("stage_id", "user_id", "role_title", name="uq_stage_incharge_role"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    stage_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("org_project_stages.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    user_id:    uuid.UUID       = Field(nullable=False, index=True)
    role_title: str             = Field(max_length=200, nullable=False)
    duties:     Optional[str]  = Field(default=None, sa_column=Column(Text, nullable=True))
    is_lead:    bool           = Field(default=False, nullable=False)
    assigned_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    relieved_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    stage: OrgProjectStage = Relationship(back_populates="in_charges")

    def is_active(self) -> bool:
        return self.relieved_at is None

    def __repr__(self) -> str:
        return f"<OrgProjectStageInCharge user={self.user_id} role={self.role_title!r}>"



class OrgSubProject(SQLModel, table=True):
    """
    A work package or sub-project within a stage, with unlimited nesting depth.

    Uses the same self-referential pattern as OrgBranch (parent_subproject_id).
    Depth is unlimited — query with WITH RECURSIVE on parent_subproject_id.

    EXAMPLE TREE:
      Stage: "Construction Phase 1"
        └── OrgSubProject: "Flood Control Works"                 (depth 1)
              ├── OrgSubProject: "River Dredging"                (depth 2)
              │     ├── OrgSubProject: "Upstream Dredging"       (depth 3)
              │     └── OrgSubProject: "Downstream Dredging"     (depth 3)
              └── OrgSubProject: "Terrace Construction"          (depth 2)
                    ├── OrgSubProject: "Lower Terrace"           (depth 3)
                    └── OrgSubProject: "Upper Terrace"           (depth 3)

    The project_id is denormalised (redundant — can be derived via stage.project_id)
    but is stored directly for efficient querying: "give me all sub-projects
    for project X regardless of stage or depth" requires no recursive join.

    `activities` is a JSONB list of planned work activities:
      [
        {"name": "Site clearing", "description": "...", "start_date": "2025-01-15"},
        {"name": "Excavation",    "description": "...", "start_date": "2025-02-01"}
      ]
    This is intentionally simple — a more complex activity tracking system
    would use a separate table.
    """
    __tablename__ = "org_sub_projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── Parent references ──────────────────────────────────────────────────────
    project_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("org_projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        description="Denormalised project reference for efficient cross-stage queries.",
    )
    stage_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("org_project_stages.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        description="The stage this sub-project belongs to.",
    )
    # Self-referential — null for top-level sub-projects within the stage
    parent_subproject_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_sub_projects.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description=(
            "Parent sub-project. Null for top-level sub-projects directly under a stage. "
            "SET NULL on parent delete — children become top-level orphans (same as OrgBranch)."
        ),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name:        str           = Field(max_length=255, nullable=False, index=True)
    code:        Optional[str] = Field(
        default=None, max_length=50, nullable=True,
        description="Short internal code e.g. 'SP-001', 'RD-001'.",
    )
    status: SubProjectStatus = Field(
        default=SubProjectStatus.PENDING,
        sa_column=Column(SAEnum(SubProjectStatus, name="sub_project_status"), nullable=False, index=True),
    )
    display_order: int = Field(
        default=0,
        nullable=False,
        description="For ordering sibling sub-projects within the same parent.",
    )

    # ── Narrative ─────────────────────────────────────────────────────────────
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    objectives:  Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    activities: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description=(
            'JSONB array of planned activities. '
            'Example: {"activities": [{"name": "Site clearing", "start_date": "2025-01-15", "description": "..."}]}'
        ),
    )
    expected_outputs: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Tangible outputs/deliverables of this sub-project.",
    )

    # ── Timeline ──────────────────────────────────────────────────────────────
    start_date: Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    end_date:   Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    actual_start_date: Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    actual_end_date:   Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))

    # ── Budget ────────────────────────────────────────────────────────────────
    budget_amount:  Optional[float] = Field(default=None, nullable=True)
    currency_code:  Optional[str]   = Field(default=None, max_length=3, nullable=True)

    # ── Address ───────────────────────────────────────────────────────────────
    # Sub-projects often operate at a different site from the parent project.
    # The full address (including Tanzania hierarchy fields and GPS) is stored
    # in the shared Address table. This FK allows ON DELETE SET NULL so the
    # sub-project record is preserved even if the address is removed.
    #
    # Create the Address row first (entity_type="org_subproject",
    # entity_id=<this subproject's id>), then set address_id here.
    #
    # Multiple addresses per sub-project are possible via the Address table
    # (query: SELECT * FROM addresses WHERE entity_type='org_subproject'
    #          AND entity_id = :subproject_id).
    # address_id here points to the PRIMARY (is_default=True) address.
    address_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("addresses.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description=(
            "FK to addresses.id (primary / default site address). "
            "Multiple addresses for the same sub-project can be queried "
            "via Address.entity_type='org_subproject' AND entity_id=<this id>."
        ),
    )

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )
    deleted_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    stage: OrgProjectStage = Relationship(
        back_populates="sub_projects",
        sa_relationship_kwargs={"foreign_keys": "[OrgSubProject.stage_id]"},
    )
    # Self-referential: parent and children
    parent: OrgSubProject = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "foreign_keys": "[OrgSubProject.parent_subproject_id]",
            "remote_side": "OrgSubProject.id",
        },
    )
    children: OrgSubProject = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "foreign_keys": "[OrgSubProject.parent_subproject_id]",
        },
    )
    in_charges: OrgSubProjectInCharge = Relationship(
        back_populates="subproject",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    progress_images: ProjectProgressImage = Relationship(
        back_populates="subproject",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ProjectProgressImage.display_order, ProjectProgressImage.created_at",
            "primaryjoin": "ProjectProgressImage.subproject_id == OrgSubProject.id",
        },
    )
    # All addresses for this sub-project (entity_type="org_subproject")
    # address_id points to the primary one; others queried via entity_id.
    addresses: Address = Relationship(
        back_populates="subproject",
        sa_relationship_kwargs={
            "foreign_keys": "[Address.subproject_id]",
            "cascade": "all, delete-orphan",
        },
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_top_level(self) -> bool:
        """True when this sub-project has no parent (directly under a stage)."""
        return self.parent_subproject_id is None

    def is_active(self) -> bool:
        return self.status == SubProjectStatus.ACTIVE

    def __repr__(self) -> str:
        return (
            f"<OrgSubProject {self.name!r} "
            f"stage={self.stage_id} "
            f"parent={self.parent_subproject_id} "
            f"[{self.status}]>"
        )



class OrgSubProjectInCharge(SQLModel, table=True):
    """
    A person responsible for a specific sub-project with a defined role and duties.

    Different sub-projects need very different expertise:
      · "River Dredging": Site Engineer, Plant Operator, Safety Officer
      · "Community Survey": Survey Lead, Data Collector, Translator
      · "EIA Baseline": Environmental Scientist, Biodiversity Specialist
      · "RAP Implementation": Social Welfare Officer, Land Valuer

    Role titles and duties are free-text to support any project domain.

    UNIQUE (subproject_id, user_id, role_title).
    """
    __tablename__ = "org_sub_project_in_charges"

    __table_args__ = (
        UniqueConstraint("subproject_id", "user_id", "role_title", name="uq_subproject_incharge_role"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    subproject_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("org_sub_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    user_id:    uuid.UUID      = Field(nullable=False, index=True)
    role_title: str            = Field(
        max_length=200,
        nullable=False,
        description=(
            "e.g. 'Site Engineer', 'Safety Officer', 'Community Liaison', "
            "'Survey Lead', 'Environmental Monitor', 'Plant Operator'."
        ),
    )
    duties: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Detailed description of this person's responsibilities on this sub-project.",
    )
    is_lead: bool = Field(
        default=False,
        nullable=False,
        description="True for the primary in-charge of this sub-project.",
    )
    assigned_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    relieved_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    subproject: OrgSubProject = Relationship(back_populates="in_charges")

    def is_active(self) -> bool:
        return self.relieved_at is None

    def __repr__(self) -> str:
        return (
            f"<OrgSubProjectInCharge "
            f"user={self.user_id} "
            f"role={self.role_title!r} "
            f"subproject={self.subproject_id}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Project / Sub-project Progress Images
# ─────────────────────────────────────────────────────────────────────────────

class ImagePhase(str, Enum):
    """
    Phase of the project at the time the image was captured.

    Used for before/during/after progress tracking. A gallery filtered by
    phase gives the GRM Unit and World Bank a visual evidence trail showing what
    the site looked like before works began, during construction, and after
    completion.
    """
    BEFORE  = "before"   # Pre-construction / baseline condition
    DURING  = "during"   # Works in progress
    AFTER   = "after"    # Completed works / post-construction
    OTHER   = "other"    # Site visits, community meetings, milestone events


# ─────────────────────────────────────────────────────────────────────────────
# Project Progress Images
# ─────────────────────────────────────────────────────────────────────────────

class ProgressImagePhase(str, Enum):
    """
    Lifecycle phase the image documents.

    BEFORE — site/condition before work started.
    DURING — work in progress.
    AFTER  — completed work / final state.

    Used to build before/after comparison galleries and to populate
    World Bank progress reporting photo documentation requirements.
    """
    BEFORE = "before"
    DURING = "during"
    AFTER  = "after"


class ProjectProgressImage(SQLModel, table=True):
    """
    A titled, described progress image for an OrgProject or OrgSubProject.

    Exactly one of project_id or subproject_id must be set.
    A DB CHECK constraint enforces this.

    Storage paths
    ─────────────
      Project-level:    images/projects/{project_id}/progress/{id}.{ext}
      SubProject-level: images/subprojects/{subproject_id}/progress/{id}.{ext}

    Before / during / after comparisons
    ────────────────────────────────────
    Filter by phase to build comparison galleries:
      phase=BEFORE → original site conditions
      phase=DURING → construction progress
      phase=AFTER  → completed works

    GPS coordinates
    ───────────────
    gps_lat / gps_lng allow all images to be mapped to a GIS layer showing
    spatial progress across the project corridor.
    """
    __tablename__ = "project_progress_images"
    __table_args__ = (
        # Exactly one of project_id or subproject_id must be set
        CheckConstraint(
            "(project_id IS NOT NULL)::int + (subproject_id IS NOT NULL)::int = 1",
            name="chk_progress_image_one_parent",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, nullable=False
    )

    # ── Parent — exactly one must be set ──────────────────────────────────
    project_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_projects.id", ondelete="CASCADE"),
            nullable=True, index=True,
        ),
        description="Set for project-level images. Null for subproject images.",
    )
    subproject_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_sub_projects.id", ondelete="CASCADE"),
            nullable=True, index=True,
        ),
        description="Set for sub-project images. Null for project-level images.",
    )

    # ── Image ─────────────────────────────────────────────────────────────
    image_url: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Permanent URL in MinIO/S3.",
    )

    # ── Documentation ─────────────────────────────────────────────────────
    title: str = Field(
        max_length=255, nullable=False,
        description=(
            "Short descriptive title. "
            "e.g. 'Jangwani Bridge — before dredging'"
        ),
    )
    description: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description=(
            "Longer narrative: what the image shows, work completed, "
            "observations, or context for reviewers and World Bank reporting."
        ),
    )
    phase: ProgressImagePhase = Field(
        default=ProgressImagePhase.DURING,
        sa_column=Column(
            SAEnum(ProgressImagePhase, name="progress_image_phase"),
            nullable=False, index=True,
        ),
        description="BEFORE / DURING / AFTER — drives comparison gallery grouping.",
    )

    # ── When and where ────────────────────────────────────────────────────
    taken_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description=(
            "When the photo was taken (may differ from upload date — "
            "e.g. photo taken on site then uploaded at the office)."
        ),
    )
    location_description: Optional[str] = Field(
        default=None, max_length=500, nullable=True,
        description=(
            "Human-readable location. "
            "e.g. 'Upstream of Jangwani Bridge, left bank, Chainage 1+250'"
        ),
    )
    gps_lat: Optional[float] = Field(
        default=None, nullable=True,
        description="Decimal degrees latitude at the photo location.",
    )
    gps_lng: Optional[float] = Field(
        default=None, nullable=True,
        description="Decimal degrees longitude at the photo location.",
    )

    # ── Gallery ordering ──────────────────────────────────────────────────
    display_order: int = Field(
        default=0, nullable=False,
        description=(
            "Controls gallery display sequence within the same parent + phase. "
            "Lower numbers appear first. Default 0 = ordered by taken_at."
        ),
    )

    # ── Authorship ────────────────────────────────────────────────────────
    uploaded_by_user_id: Optional[uuid.UUID] = Field(
        default=None, nullable=True,
        description="auth_service User.id of the uploader.",
    )

    # ── Audit ─────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"),
            onupdate=text("now()"), nullable=False,
        )
    )

    # ── Relationships ──────────────────────────────────────────────────────
    project:    OrgProject    = Relationship(back_populates="progress_images")
    subproject: OrgSubProject = Relationship(back_populates="progress_images")

    def __repr__(self) -> str:
        parent = (
            f"project={self.project_id}"
            if self.project_id
            else f"subproject={self.subproject_id}"
        )
        return (
            f"<ProjectProgressImage {parent} "
            f"phase={self.phase.value} title={self.title!r}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Project Checklist
# ─────────────────────────────────────────────────────────────────────────────

class ChecklistEntityType(str, Enum):
    """Entity this checklist item is attached to."""
    PROJECT    = "project"
    STAGE      = "stage"
    SUBPROJECT = "subproject"


class ChecklistItemStatus(str, Enum):
    """
    Lifecycle status of a single checklist item.

    PENDING     → not yet started (default)
    IN_PROGRESS → work has started but not complete
    DONE        → completed; completion_date is set
    SKIPPED     → deliberately excluded from scope; skip_reason captured
    BLOCKED     → cannot proceed; reason captured in notes
    """
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    DONE        = "done"
    SKIPPED     = "skipped"
    BLOCKED     = "blocked"


class ProjectChecklistItem(SQLModel, table=True):
    """
    A single actionable checklist item attached to a project, stage,
    or sub-project.

    Design decisions
    ────────────────
    · One table covers all three entity levels via (entity_type, entity_id).
      Keeps queries, repositories, and API consistent.
    · entity_type = "project"    → OrgProject.id
    · entity_type = "stage"      → OrgProjectStage.id
    · entity_type = "subproject" → OrgSubProject.id
    · title is required — every item needs an actionable label.
    · description provides additional context and acceptance criteria.
    · assigned_to_user_id allows workload tracking per team member.
    · completion_note captures what was done and any observations.
    · completion_evidence_url links to supporting photo/doc in MinIO/S3.
    · Soft-delete via deleted_at — checklist history is preserved for audit.
    · display_order enables drag-and-drop reordering per entity.

    Usage examples
    ──────────────
    Stage "Design & Engineering" checklist:
      ☐  Conduct topographic survey
      ☐  Submit Environmental Impact Assessment
      ☐  Obtain works permit from TANROADS
      ✓  Approve contractor selection

    Sub-project "River Dredging" checklist:
      ☐  Mobilise equipment to site (KM 24+300)
      ☐  Clear vegetation from river banks
      ☐  Dredge main channel to -3.0m datum
      ☐  Dispose spoil at approved dumping site
    """
    __tablename__ = "project_checklist_items"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, nullable=False
    )

    # ── Entity link ───────────────────────────────────────────────────────────
    entity_type: str = Field(
        max_length=20,
        nullable=False,
        index=True,
        description="'project' | 'stage' | 'subproject'",
    )
    entity_id: uuid.UUID = Field(
        nullable=False,
        index=True,
        description=(
            "OrgProject.id, OrgProjectStage.id, or OrgSubProject.id "
            "depending on entity_type."
        ),
    )

    # ── Content ───────────────────────────────────────────────────────────────
    title: str = Field(
        max_length=500,
        nullable=False,
        description=(
            "Short actionable label. Required. "
            "e.g. 'Submit Environmental Impact Assessment' or "
            "'Obtain works permit from TANROADS'."
        ),
    )
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Additional context, acceptance criteria, or instructions "
            "for this item."
        ),
    )
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description=(
            "Optional grouping label e.g. 'Permits', 'Site Preparation', "
            "'Community Engagement', 'Financial'. Free-form text."
        ),
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status: ChecklistItemStatus = Field(
        default=ChecklistItemStatus.PENDING,
        sa_column=Column(
            SAEnum(ChecklistItemStatus, name="checklist_item_status"),
            nullable=False,
            index=True,
        ),
    )

    # ── Scheduling ────────────────────────────────────────────────────────────
    due_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
        description="Target completion date for this item.",
    )
    completion_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
        description="Actual date this item was marked DONE.",
    )

    # ── Assignment ────────────────────────────────────────────────────────────
    assigned_to_user_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description="auth_service User.id responsible for completing this item.",
    )

    # ── Completion evidence ────────────────────────────────────────────────────
    completion_note: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "What was done, observations, or outcome notes. "
            "Required when marking an item DONE — provides the evidence trail."
        ),
    )
    completion_evidence_url: Optional[str] = Field(
        default=None,
        max_length=1024,
        nullable=True,
        description=(
            "URL to supporting evidence (photo, signed permit, report) "
            "in MinIO/S3. Stored via the existing ImageService upload flow."
        ),
    )

    # ── Skip / block ──────────────────────────────────────────────────────────
    skip_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        nullable=True,
        description="Why this item was skipped or blocked. Required when status = SKIPPED or BLOCKED.",
    )

    # ── Ordering ──────────────────────────────────────────────────────────────
    display_order: int = Field(
        default=0,
        nullable=False,
        description="Manual ordering within the entity's checklist. Lower = shown first.",
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by_user_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description="User who created this checklist item.",
    )
    updated_by_user_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description="User who last updated this checklist item.",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Soft-delete timestamp. Deleted items are hidden but preserved for audit.",
    )

    # ── Computed helpers ──────────────────────────────────────────────────────

    def is_done(self) -> bool:
        return self.status == ChecklistItemStatus.DONE

    def is_visible(self) -> bool:
        return self.deleted_at is None

    def __repr__(self) -> str:
        return (
            f"<ProjectChecklistItem {self.entity_type}/{self.entity_id} "
            f"[{self.status}] {self.title!r}>"
        )
