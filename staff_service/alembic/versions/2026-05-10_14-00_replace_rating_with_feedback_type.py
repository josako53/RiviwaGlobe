"""Replace rating (int 1-5) with feedback_type (grievance|suggestion|applause|inquiry).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-10 14:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old integer rating column
    op.drop_index("ix_staff_feedbacks_rating", table_name="staff_feedbacks", if_exists=True)
    op.drop_column("staff_feedbacks", "rating")

    # Add feedback_type string column with index
    op.add_column(
        "staff_feedbacks",
        sa.Column("feedback_type", sa.String(20), nullable=False, server_default="applause"),
    )
    op.create_index("ix_staff_feedbacks_feedback_type", "staff_feedbacks", ["feedback_type"])

    # Remove the server_default now that existing rows are handled
    op.alter_column("staff_feedbacks", "feedback_type", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_staff_feedbacks_feedback_type", table_name="staff_feedbacks")
    op.drop_column("staff_feedbacks", "feedback_type")
    op.add_column(
        "staff_feedbacks",
        sa.Column("rating", sa.Integer(), nullable=False, server_default="3"),
    )
    op.alter_column("staff_feedbacks", "rating", server_default=None)
