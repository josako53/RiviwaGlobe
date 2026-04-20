"""add_org_departments

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-20 10:00:00.000000+00:00

Creates the org_departments table — named internal units (HR, Finance,
Customer Care, etc.) that belong to an organisation and optionally a branch.

Changes
────────
  · NEW TABLE  org_departments
      id                UUID        PK
      org_id            UUID        FK → organisations.id ON DELETE CASCADE
      branch_id         UUID        FK → org_branches.id  ON DELETE SET NULL  nullable
      name              VARCHAR(150) NOT NULL
      code              VARCHAR(30)  nullable
      description       TEXT         nullable
      sort_order        INTEGER      NOT NULL  DEFAULT 0
      is_active         BOOLEAN      NOT NULL  DEFAULT true
      created_by_id     UUID         nullable
      created_at        TIMESTAMPTZ  NOT NULL  DEFAULT now()
      updated_at        TIMESTAMPTZ  NOT NULL  DEFAULT now()

  · UNIQUE  (org_id, name)
  · INDEX   org_id, branch_id, is_active
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision      = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "org_departments",
        sa.Column("id",            sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id",        sa.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id",     sa.UUID(as_uuid=True), nullable=True),
        sa.Column("name",          sa.String(150),        nullable=False),
        sa.Column("code",          sa.String(30),         nullable=True),
        sa.Column("description",   sa.Text(),             nullable=True),
        sa.Column("sort_order",    sa.Integer(),          nullable=False, server_default="0"),
        sa.Column("is_active",     sa.Boolean(),          nullable=False, server_default="true"),
        sa.Column("created_by_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organisations.id"],
            ondelete="CASCADE",
            name="fk_org_departments_org",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["org_branches.id"],
            ondelete="SET NULL",
            name="fk_org_departments_branch",
        ),
        sa.UniqueConstraint("org_id", "name", name="uq_org_department_name"),
    )
    op.create_index("ix_org_departments_org_id",    "org_departments", ["org_id"])
    op.create_index("ix_org_departments_branch_id", "org_departments", ["branch_id"])
    op.create_index("ix_org_departments_is_active", "org_departments", ["is_active"])
    op.create_index("ix_org_departments_name",      "org_departments", ["name"])


def downgrade() -> None:
    op.drop_table("org_departments")
