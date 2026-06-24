"""Add physically_verified, issue_gps_accuracy_m, poi_id to feedbacks

Revision ID: 8e9f0a1b2c3d
Revises: 7d8e9f0a1b2c
Create Date: 2026-06-24 20:00:00.000000+00:00

physically_verified — boolean flag set server-side when the submitter's GPS coordinate
falls inside the org branch geofence at submission time. NULL means no GPS was provided
(e.g. SMS channel). Enables trust-tiered routing: in-person complaints get faster SLAs.

issue_gps_accuracy_m — device-reported accuracy in metres. Allows the system to reject
or downgrade low-confidence GPS readings (e.g. >200m accuracy is effectively useless
for room-level resolution in a large building).

poi_id — soft UUID reference to auth_service OrgPointOfInterest. Resolved from GPS
coordinate at submission time. Enables AI wayfinding directions and staff dispatch.
No DB-level FK (cross-database soft link, same pattern as department_id/branch_id).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "8e9f0a1b2c3d"
down_revision = "7d8e9f0a1b2c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "feedbacks",
        sa.Column("issue_gps_accuracy_m", sa.Integer(), nullable=True),
    )
    op.add_column(
        "feedbacks",
        sa.Column("physically_verified", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "feedbacks",
        sa.Column("poi_id", sa.UUID(), nullable=True),
    )
    op.create_index("ix_feedbacks_physically_verified", "feedbacks", ["physically_verified"])
    op.create_index("ix_feedbacks_poi_id",              "feedbacks", ["poi_id"])


def downgrade() -> None:
    op.drop_index("ix_feedbacks_poi_id",              table_name="feedbacks")
    op.drop_index("ix_feedbacks_physically_verified", table_name="feedbacks")
    op.drop_column("feedbacks", "poi_id")
    op.drop_column("feedbacks", "physically_verified")
    op.drop_column("feedbacks", "issue_gps_accuracy_m")
