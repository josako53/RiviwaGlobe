"""
models/department.py
═══════════════════════════════════════════════════════════════════════════════
OrgDepartment — named internal units within an organisation.

Examples:  HR, Finance, Customer Care, Legal, Engineering, Operations.

SCOPING
═══════════════════════════════════════════════════════════════════════════════

  org_id    (required)   — which organisation this department belongs to
  branch_id (optional)   — narrow scope to a specific branch / regional office
                           NULL = org-wide department (all branches can use it)
                           SET  = department exists only within that branch

UNIQUENESS
  (org_id, name) — department name must be unique within an organisation.
  This prevents "HR" appearing twice under the same org, whether it is
  org-wide or branch-scoped.

RELATIONSHIPS
  Organisation  ←→  OrgDepartment.org      (Organisation.departments)
  OrgBranch     ←→  OrgDepartment.branch   (nullable; OrgBranch.departments)

FEEDBACK LINK
  feedback_service.feedbacks.department_id is a soft UUID reference to
  OrgDepartment.id. There is no DB-level FK because the two tables live in
  different databases (auth_db vs feedback_db). The feedback service stores
  the UUID; the auth service resolves it for display.
═══════════════════════════════════════════════════════════════════════════════
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.organisation import Organisation
    from models.organisation_extended import OrgBranch


class OrgDepartment(SQLModel, table=True):
    """
    A named internal department or functional unit within an organisation.

    Can be org-wide (branch_id=NULL) or scoped to a specific branch
    (branch_id=<id>). All branches may reference an org-wide department;
    branch-scoped departments are visible only within that branch context.

    Feedback records reference this table via a soft UUID column
    (feedback_service.feedbacks.department_id) to indicate which department
    a grievance, suggestion, or applause is directed at or handled by.
    """
    __tablename__ = "org_departments"
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_org_department_name"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # ── Ownership ─────────────────────────────────────────────────────────────
    org_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # Optional branch scope.  NULL = org-wide (shared across all branches).
    branch_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_branches.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: str = Field(
        max_length=150,
        nullable=False,
        index=True,
        description="Department display name e.g. 'Human Resources', 'Finance', 'Customer Care'",
    )
    code: Optional[str] = Field(
        default=None,
        max_length=30,
        nullable=True,
        index=True,
        description="Short internal code e.g. 'HR', 'FIN', 'CS'. Optional; set by the org.",
    )
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Optional longer description of the department's mandate or responsibilities.",
    )

    # ── Ordering & status ─────────────────────────────────────────────────────
    sort_order: int = Field(
        default=0,
        nullable=False,
        description="Display order in lists; lower values appear first.",
    )
    is_active: bool = Field(
        default=True,
        nullable=False,
        index=True,
        description="Soft-delete: False = deactivated; excluded from active lists.",
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description="User who created this department (auth_service User.id).",
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    org:    "Organisation" = Relationship(back_populates="departments")
    branch: "OrgBranch"   = Relationship(back_populates="departments")

    def __repr__(self) -> str:
        scope = f"branch={self.branch_id}" if self.branch_id else "org-wide"
        return f"<OrgDepartment {self.name!r} org={self.org_id} {scope}>"
