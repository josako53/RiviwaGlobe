"""Add boundary_polygon to org_locations

Revision ID: 9f0a1b2c3d4e
Revises: 6a7b8c9d0e1f
Create Date: 2026-06-25 10:00:00.000000+00:00

boundary_polygon replaces the circular geofence_radius_m as the primary method for
defining the operational area of an office or building. A single centre-point + radius
forms a circle, which almost never matches the real shape of a building or campus.

boundary_polygon is a JSONB array of ordered GPS coordinate points:
  [{"lat": -6.7900, "lng": 39.2060, "label": "north_west"},
   {"lat": -6.7900, "lng": 39.2110, "label": "north_east"},
   {"lat": -6.7950, "lng": 39.2110, "label": "south_east"},
   {"lat": -6.7950, "lng": 39.2060, "label": "south_west"}]

Minimum 4 points (N, S, E, W corners). Add more for L-shaped buildings, hospital
wings, campus perimeters, or any irregular boundary.

feedback_service uses the ray-casting point-in-polygon algorithm to evaluate whether
a submitter's GPS coordinate falls inside the polygon. geofence_radius_m remains as
a fallback for locations that have not yet been upgraded to polygon boundaries.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "9f0a1b2c3d4e"
down_revision = "6a7b8c9d0e1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "org_locations",
        sa.Column("boundary_polygon", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("org_locations", "boundary_polygon")
