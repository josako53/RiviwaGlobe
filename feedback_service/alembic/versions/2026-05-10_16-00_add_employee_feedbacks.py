"""Add employee_feedbacks table — staff internal feedback about their own org.

Revision ID: f1a2b3c4d5e6
Revises: e9f0a1b2c3d4
Create Date: 2026-05-10 16:00:00

WHY
───
Employees need a dedicated channel to leave structured feedback about their
own organisation (working conditions, management, culture, etc.). This is
distinct from:
  1. Consumer GRM feedback (feedbacks table) — external citizens about services/projects
  2. Staff post-verification ratings (staff_feedbacks) — customers rating staff

The org_id column is always populated (required at submission). employee_user_id
is NULL for anonymous submissions. This allows org admins to see aggregate
patterns without identifying individuals when anonymity is requested.
"""
from alembic import op
import sqlalchemy as sa

revision      = "f1a2b3c4d5e6"
down_revision = "e9f0a1b2c3d4"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "employee_feedbacks",
        sa.Column("id",                    sa.UUID(),     nullable=False, primary_key=True),
        sa.Column("tracking_number",       sa.String(20), nullable=False, unique=True),
        sa.Column("org_id",                sa.UUID(),     nullable=False),
        sa.Column("feedback_type",         sa.String(20), nullable=False),
        sa.Column("category",              sa.String(40), nullable=False),
        sa.Column("subject",               sa.String(500), nullable=True),
        sa.Column("description",           sa.Text(),     nullable=False),
        sa.Column("is_anonymous",          sa.Boolean(),  nullable=False, server_default="false"),
        sa.Column("employee_user_id",      sa.UUID(),     nullable=True),
        sa.Column("employee_name",         sa.String(255), nullable=True),
        sa.Column("department_id",         sa.UUID(),     nullable=True),
        sa.Column("branch_id",             sa.UUID(),     nullable=True),
        sa.Column("status",                sa.String(20), nullable=False, server_default="submitted"),
        sa.Column("management_response",   sa.Text(),     nullable=True),
        sa.Column("responded_at",          sa.DateTime(), nullable=True),
        sa.Column("responded_by_user_id",  sa.UUID(),     nullable=True),
        sa.Column("submitted_at",          sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",            sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_employee_feedbacks_org_id",          "employee_feedbacks", ["org_id"])
    op.create_index("ix_employee_feedbacks_feedback_type",   "employee_feedbacks", ["feedback_type"])
    op.create_index("ix_employee_feedbacks_category",        "employee_feedbacks", ["category"])
    op.create_index("ix_employee_feedbacks_status",          "employee_feedbacks", ["status"])
    op.create_index("ix_employee_feedbacks_is_anonymous",    "employee_feedbacks", ["is_anonymous"])
    op.create_index("ix_employee_feedbacks_employee_user_id","employee_feedbacks", ["employee_user_id"])
    op.create_index("ix_employee_feedbacks_department_id",   "employee_feedbacks", ["department_id"])
    op.create_index("ix_employee_feedbacks_branch_id",       "employee_feedbacks", ["branch_id"])
    op.create_index("ix_employee_feedbacks_tracking_number", "employee_feedbacks", ["tracking_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_employee_feedbacks_tracking_number",  table_name="employee_feedbacks")
    op.drop_index("ix_employee_feedbacks_branch_id",        table_name="employee_feedbacks")
    op.drop_index("ix_employee_feedbacks_department_id",    table_name="employee_feedbacks")
    op.drop_index("ix_employee_feedbacks_employee_user_id", table_name="employee_feedbacks")
    op.drop_index("ix_employee_feedbacks_is_anonymous",     table_name="employee_feedbacks")
    op.drop_index("ix_employee_feedbacks_status",           table_name="employee_feedbacks")
    op.drop_index("ix_employee_feedbacks_category",         table_name="employee_feedbacks")
    op.drop_index("ix_employee_feedbacks_feedback_type",    table_name="employee_feedbacks")
    op.drop_index("ix_employee_feedbacks_org_id",           table_name="employee_feedbacks")
    op.drop_table("employee_feedbacks")
