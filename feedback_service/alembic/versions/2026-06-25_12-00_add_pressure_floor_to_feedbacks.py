"""Add pressure_hpa, floor_id, floor_confidence to feedbacks

Revision ID: b2c3d4e5f6a7
Revises: 8e9f0a1b2c3d
Create Date: 2026-06-25 12:00:00.000000+00:00

Barometric floor detection fields:

  pressure_hpa      — phone barometric pressure (hPa) captured at feedback submission.
                      Compared against org_floors.calibrated_pressure_hpa in auth_service
                      to determine which floor the submitter was on.

  floor_id          — soft UUID reference to auth_service OrgFloor.
                      Resolved at submission time from pressure_hpa.
                      NULL when no pressure submitted or building not calibrated.

  floor_confidence  — 'high' when pressure delta to matched floor < 1.5 hPa.
                      'low' when delta is 1.5–3.0 hPa (weather drift likely).
                      NULL when floor_id is NULL.

Together with poi_id (added in previous migration), these fields complete the
indoor location chain: branch → building → floor → zone → POI.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "g4h5i6j7k8l9"
down_revision = "8e9f0a1b2c3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("feedbacks", sa.Column("pressure_hpa", sa.Float(), nullable=True))
    op.add_column("feedbacks", sa.Column("floor_id", sa.UUID(), nullable=True))
    op.add_column("feedbacks", sa.Column("floor_confidence", sa.String(10), nullable=True))
    op.create_index("ix_feedbacks_floor_id", "feedbacks", ["floor_id"])


def downgrade() -> None:
    op.drop_index("ix_feedbacks_floor_id", table_name="feedbacks")
    op.drop_column("feedbacks", "floor_confidence")
    op.drop_column("feedbacks", "floor_id")
    op.drop_column("feedbacks", "pressure_hpa")
