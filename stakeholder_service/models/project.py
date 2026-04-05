# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  stakeholder_service  |  Port: 8070  |  DB: stakeholder_db (5436)
# FILE     :  models/project.py
# ───────────────────────────────────────────────────────────────────────────
"""
models/project.py - Local read-only caches of OrgProject and OrgProjectStage from auth_service.
"""
from __future__ import annotations
import uuid
from datetime import datetime, date
from enum import Enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, ForeignKey, Text, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.stakeholder import StakeholderProject, StakeholderStageEngagement
    from models.engagement import EngagementActivity
    from models.communication import CommunicationRecord, FocalPerson

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
    """Read-only local cache of OrgProject from auth_service. Never written by API callers."""
    __tablename__ = "projects"

    id: uuid.UUID = Field(primary_key=True, nullable=False,
                          description="Same UUID as auth_service OrgProject.id.")
    organisation_id: uuid.UUID        = Field(nullable=False, index=True)
    branch_id:       Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    name:            str              = Field(max_length=255, nullable=False, index=True)
    code:            Optional[str]    = Field(default=None, max_length=50, nullable=True, index=True)
    slug:            str              = Field(max_length=255, nullable=False, index=True)
    status: ProjectStatus = Field(
        default=ProjectStatus.ACTIVE,
        sa_column=Column(SAEnum(ProjectStatus, name="proj_status_cache"), nullable=False, index=True)
    )
    category:    Optional[str] = Field(default=None, max_length=100, nullable=True, index=True)
    sector:      Optional[str] = Field(default=None, max_length=100, nullable=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    country_code: Optional[str] = Field(default=None, max_length=2,   nullable=True)
    region:       Optional[str] = Field(default=None, max_length=100, nullable=True)
    primary_lga:  Optional[str] = Field(default=None, max_length=100, nullable=True)
    start_date:   Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    end_date:     Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    accepts_grievances:  bool = Field(default=True, nullable=False)
    accepts_suggestions: bool = Field(default=True, nullable=False)
    accepts_applause:    bool = Field(default=True, nullable=False)
    synced_at:    datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False))
    published_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at:   datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False))
    updated_at:   datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False))

    stages:               ProjectStageCache   = Relationship(back_populates="project",       sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "ProjectStageCache.stage_order"})
    stakeholder_projects: StakeholderProject  = Relationship(back_populates="project",       sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    activities:           EngagementActivity  = Relationship(back_populates="project",       sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    communications:       CommunicationRecord = Relationship(back_populates="project",       sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    focal_persons:        FocalPerson         = Relationship(back_populates="project",       sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    def is_active(self) -> bool: return self.status == ProjectStatus.ACTIVE
    def is_accepting_stakeholders(self) -> bool: return self.status in (ProjectStatus.PLANNING, ProjectStatus.ACTIVE)
    def __repr__(self) -> str: return f"<ProjectCache {self.name!r} [{self.status}]>"


class ProjectStageCache(SQLModel, table=True):
    """Read-only local cache of OrgProjectStage. Critical for stage-scoped stakeholder engagement."""
    __tablename__ = "project_stages"
    __table_args__ = (UniqueConstraint("project_id", "stage_order", name="uq_cached_stage_order"),)

    id: uuid.UUID = Field(primary_key=True, nullable=False,
                          description="Same UUID as auth_service OrgProjectStage.id.")
    project_id: uuid.UUID = Field(sa_column=Column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True))
    name:        str         = Field(max_length=255, nullable=False)
    stage_order: int         = Field(nullable=False)
    status: StageStatus = Field(
        default=StageStatus.PENDING,
        sa_column=Column(SAEnum(StageStatus, name="stage_status_cache"), nullable=False, index=True)
    )
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    objectives:  Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    start_date:  Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    end_date:    Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    accepts_grievances:  Optional[bool] = Field(default=None, nullable=True)
    accepts_suggestions: Optional[bool] = Field(default=None, nullable=True)
    accepts_applause:    Optional[bool] = Field(default=None, nullable=True)
    synced_at:  datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False))

    project:          ProjectCache                  = Relationship(back_populates="stages")
    stage_engagements: StakeholderStageEngagement       = Relationship(back_populates="stage", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    def is_active(self) -> bool: return self.status == StageStatus.ACTIVE
    def __repr__(self) -> str: return f"<ProjectStageCache {self.name!r} order={self.stage_order} [{self.status}]>"
