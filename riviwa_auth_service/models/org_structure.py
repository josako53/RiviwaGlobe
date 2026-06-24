"""
models/org_structure.py — Org operating hours, leadership/GRAM, and geo boundaries.

Tables
──────
  org_operating_hours    Structured Mon-Sun hours at org or branch level.
  org_leadership_roles   Org chart, GRAM, in-charges, focal persons.
  org_geo_boundaries     Geographic territory polygons (GeoJSON) per org/branch.
"""
from __future__ import annotations

import uuid
from datetime import datetime, time
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, DateTime, Field, SQLModel, text


# ═════════════════════════════════════════════════════════════════════════════
# OrgOperatingHours
# ═════════════════════════════════════════════════════════════════════════════

class DayOfWeek(str, Enum):
    MONDAY    = "MONDAY"
    TUESDAY   = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY  = "THURSDAY"
    FRIDAY    = "FRIDAY"
    SATURDAY  = "SATURDAY"
    SUNDAY    = "SUNDAY"


class OrgOperatingHours(SQLModel, table=True):
    """
    Structured operating hours for an Organisation or Branch.
    Seven rows per entity = a full week schedule.

    Scope:
      org_id set + branch_id NULL  → org-wide default hours
      branch_id set + org_id NULL  → branch-specific hours (overrides org)

    UNIQUE on (org_id, branch_id, day_of_week) to prevent duplicate entries.

    Relationship wiring:
      OrgOperatingHours.organisation ←→ Organisation (FK)
      OrgOperatingHours.branch       ←→ OrgBranch (FK)
    """
    __tablename__ = "org_operating_hours"
    __table_args__ = (
        UniqueConstraint("org_id", "branch_id", "day_of_week",
                         name="uq_org_hours_scope_day"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    org_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=True, index=True,
        ),
        description="Set for org-wide hours; NULL for branch-specific rows",
    )
    branch_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_branches.id", ondelete="CASCADE"),
            nullable=True, index=True,
        ),
        description="Set for branch-specific hours; NULL for org-wide rows",
    )

    day_of_week: DayOfWeek = Field(
        sa_column=Column(
            SAEnum(DayOfWeek, name="day_of_week"),
            nullable=False, index=True,
        ),
    )

    is_open:    bool           = Field(default=True, nullable=False,
                                       description="False = closed all day (e.g. Sunday)")
    open_time:  Optional[time] = Field(
        default=None,
        sa_column=Column(Time, nullable=True),
        description="Opening time e.g. 08:30",
    )
    close_time: Optional[time] = Field(
        default=None,
        sa_column=Column(Time, nullable=True),
        description="Closing time e.g. 17:00",
    )
    break_start: Optional[time] = Field(
        default=None,
        sa_column=Column(Time, nullable=True),
        description="Lunch break start",
    )
    break_end: Optional[time] = Field(
        default=None,
        sa_column=Column(Time, nullable=True),
        description="Lunch break end",
    )
    timezone: str = Field(
        default="Africa/Dar_es_Salaam", max_length=60, nullable=False,
        description="IANA timezone for these hours e.g. 'Europe/Rome'",
    )
    notes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="'By appointment only', 'Public holidays excluded', etc.",
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )


# ═════════════════════════════════════════════════════════════════════════════
# OrgLeadershipRole — Org chart, GRAM, in-charges, focal persons
# ═════════════════════════════════════════════════════════════════════════════

class LeadershipScope(str, Enum):
    EXECUTIVE    = "EXECUTIVE"     # CEO, CFO, COO, Director General
    MANAGEMENT   = "MANAGEMENT"    # Department heads, senior managers
    INCHARGE     = "INCHARGE"      # Designated area in-charges (GRM, tech, ops)
    FOCAL_PERSON = "FOCAL_PERSON"  # GRM focal persons / designated contacts
    SPOKESPERSON = "SPOKESPERSON"  # Communications / public affairs
    TECHNICAL    = "TECHNICAL"     # Technical leads, chief engineers
    BOARD        = "BOARD"         # Board members, trustees, governors


class OrgLeadershipRole(SQLModel, table=True):
    """
    Formal org-level leadership structure: org chart, GRAM, in-charges.

    Self-referential via parent_role_id to model hierarchy:

      Director General (level=1, scope=EXECUTIVE)
        ├── CFO (level=2, scope=EXECUTIVE, parent=DG)
        │    └── Finance Manager (level=3, scope=MANAGEMENT, parent=CFO)
        ├── Head of GRM (level=2, scope=INCHARGE, parent=DG)
        │    └── GRM Focal Person – Dar Branch (level=3, scope=FOCAL_PERSON)
        └── Chief Engineer (level=2, scope=TECHNICAL, parent=DG)

    branch_id: when set, this role is scoped to a specific branch;
               NULL means org-wide role (e.g. the CEO is org-wide).

    user_id: links to a registered platform user if the person has an account.
             Can be NULL for external persons or board members without logins.

    Relationship wiring:
      OrgLeadershipRole.org_id       → organisations.id (CASCADE)
      OrgLeadershipRole.branch_id    → org_branches.id (SET NULL)
      OrgLeadershipRole.user_id      → users.id (SET NULL)
      OrgLeadershipRole.parent_role_id → org_leadership_roles.id (SET NULL)
    """
    __tablename__ = "org_leadership_roles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    org_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
    )
    branch_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_branches.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
        description="NULL = org-wide role; set = branch-scoped role",
    )
    user_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
        description="Registered platform user (optional)",
    )

    # Person details (always required even if user_id is set)
    full_name: str       = Field(max_length=200, nullable=False)
    photo_url: Optional[str] = Field(default=None, max_length=1024, nullable=True)

    # Role definition
    role_title: str           = Field(max_length=200, nullable=False,
                                      description="e.g. 'Chief Executive Officer'")
    scope: LeadershipScope    = Field(
        default=LeadershipScope.MANAGEMENT,
        sa_column=Column(SAEnum(LeadershipScope, name="leadership_scope"),
                         nullable=False, index=True),
    )
    duties: Optional[str]     = Field(default=None,
                                      sa_column=Column(Text, nullable=True),
                                      description="Responsibilities and duties")
    department: Optional[str] = Field(default=None, max_length=200, nullable=True)

    # Contact information
    phone: Optional[str] = Field(default=None, max_length=30,  nullable=True)
    email: Optional[str] = Field(default=None, max_length=255, nullable=True)

    # Hierarchy
    parent_role_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_leadership_roles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        description="Who this person reports to (NULL = top of hierarchy)",
    )
    level:      int = Field(default=1, sa_column=Column(Integer, nullable=False),
                            description="1=top (CEO/DG), 2=direct reports, …")
    sort_order: int = Field(default=0, sa_column=Column(Integer, nullable=False))

    # Visibility & status
    is_public: bool = Field(default=True,  nullable=False,
                            description="Show on public org profile")
    is_active: bool = Field(default=True,  nullable=False)

    # Tenure
    started_on: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    ended_on: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="NULL = still serving",
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )


# ═════════════════════════════════════════════════════════════════════════════
# OrgGeoBoundary — GeoJSON territory polygons
# ═════════════════════════════════════════════════════════════════════════════

class GeoBoundaryType(str, Enum):
    SERVICE_AREA  = "SERVICE_AREA"   # Where the org/branch delivers services
    JURISDICTION  = "JURISDICTION"   # Legal / administrative jurisdiction
    DELIVERY_ZONE = "DELIVERY_ZONE"  # Physical delivery coverage
    CATCHMENT     = "CATCHMENT"      # Catchment area (clinic/school)
    MONITORING    = "MONITORING"     # Project impact / monitoring zone
    OPERATIONAL   = "OPERATIONAL"    # General operational territory


class OrgGeoBoundary(SQLModel, table=True):
    """
    Geographic territory boundary for an Organisation or Branch.

    Stores GeoJSON Polygon / MultiPolygon objects for:
      - Service delivery areas    ("we deliver within these coordinates")
      - Administrative boundaries ("this office serves Kinondoni District")
      - Catchment areas           ("this clinic serves patients from this region")
      - Project monitoring zones  ("project impact area: GeoJSON polygon")

    geojson: standard GeoJSON geometry:
      {"type": "Polygon", "coordinates": [[[lng, lat], [lng, lat], ...]]}
      or MultiPolygon for non-contiguous territories.

    bbox_* fields enable fast bounding-box pre-filtering before expensive
    polygon containment checks.

    Relationship wiring:
      OrgGeoBoundary.org_id    → organisations.id (CASCADE)
      OrgGeoBoundary.branch_id → org_branches.id (CASCADE)
    """
    __tablename__ = "org_geo_boundaries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    org_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=True, index=True,
        ),
    )
    branch_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_branches.id", ondelete="CASCADE"),
            nullable=True, index=True,
        ),
    )

    boundary_type: GeoBoundaryType = Field(
        sa_column=Column(SAEnum(GeoBoundaryType, name="geo_boundary_type"),
                         nullable=False, index=True),
    )
    name:        str           = Field(max_length=300, nullable=False)
    description: Optional[str] = Field(default=None,
                                       sa_column=Column(Text, nullable=True))

    # GeoJSON stored as JSONB — Polygon or MultiPolygon geometry object
    geojson: dict = Field(
        sa_column=Column(JSONB, nullable=False),
        description="GeoJSON Polygon or MultiPolygon: {type, coordinates}",
    )

    # Bounding box for fast pre-filter (decimal degrees)
    bbox_min_lat: Optional[float] = Field(
        default=None, sa_column=Column(Float, nullable=True))
    bbox_max_lat: Optional[float] = Field(
        default=None, sa_column=Column(Float, nullable=True))
    bbox_min_lng: Optional[float] = Field(
        default=None, sa_column=Column(Float, nullable=True))
    bbox_max_lng: Optional[float] = Field(
        default=None, sa_column=Column(Float, nullable=True))

    is_active: bool = Field(default=True, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )
