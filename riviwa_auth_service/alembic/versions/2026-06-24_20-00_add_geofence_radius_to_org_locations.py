"""Add geofence_radius_m to org_locations

Revision ID: 6a7b8c9d0e1f
Revises: 5b1ce6f16a16
Create Date: 2026-06-24 20:00:00.000000+00:00

geofence_radius_m defines the circular boundary (in metres) around a branch location's
GPS coordinates that Riviwa considers "on premises". When a feedback submitter's GPS
coordinate falls within this radius, feedback_service sets physically_verified=true on
the feedback record, enabling trust-tiered routing and priority SLAs for in-person
complaints without exposing the raw GPS to counter staff.

A NULL value means no geofence is configured for that location — physically_verified
will remain NULL for submissions at that branch regardless of GPS availability.

Typical values: 50m (single-building campus), 200m (hospital complex),
500m (university campus), 100m (office building).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "6a7b8c9d0e1f"
down_revision = "5b1ce6f16a16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "org_locations",
        sa.Column("geofence_radius_m", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("org_locations", "geofence_radius_m")
