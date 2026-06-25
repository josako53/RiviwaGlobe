"""Add org_buildings, org_floors, org_zones, org_points_of_interest

Revision ID: a1b2c3d4e5f6
Revises: 9f0a1b2c3d4e
Create Date: 2026-06-25 12:00:00.000000+00:00

Building structure hierarchy for indoor location, floor detection, and AI wayfinding:

  OrgBranch (existing)
    └── OrgBuilding   — named building within a campus (Block A, Terminal 1)
          └── OrgFloor  — floor with barometric pressure calibration
                └── OrgZone  — named area (Cardiology Wing, Maternity Ward)
                      └── OrgPointOfInterest  — specific desk, counter, room,
                                               nurse station, emergency point

Floor detection uses barometric pressure (hPa) measured on each floor at onboarding
time and compared to the user's phone barometer at submission. Accuracy: ±1 floor.

POI resolution uses Haversine nearest-point on the resolved floor.
Emergency routing: is_emergency_point flag + nearest_emergency_poi_id enables
AI to direct a user in distress to the closest help point.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "f3a4b5c6d7e8"
down_revision = "9f0a1b2c3d4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── org_buildings ──────────────────────────────────────────────────────────
    op.create_table(
        "org_buildings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lng", sa.Float(), nullable=True),
        sa.Column("boundary_polygon", JSONB(), nullable=True),
        sa.Column("ground_altitude_m", sa.Float(), nullable=True),
        sa.Column("ground_reference_hpa", sa.Float(), nullable=True),
        sa.Column("reference_taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reference_station_id", sa.String(100), nullable=True),
        sa.Column("total_floors", sa.Integer(), nullable=True),
        sa.Column("accessibility_notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["org_branches.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_org_buildings_organisation_id", "org_buildings", ["organisation_id"])
    op.create_index("ix_org_buildings_branch_id", "org_buildings", ["branch_id"])

    # ── org_floors ─────────────────────────────────────────────────────────────
    op.create_table(
        "org_floors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("building_id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("floor_number", sa.Integer(), nullable=False),
        sa.Column("floor_name", sa.String(200), nullable=False),
        sa.Column("calibrated_pressure_hpa", sa.Float(), nullable=True),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("floor_height_m", sa.Float(), nullable=True),
        sa.Column("ceiling_height_m", sa.Float(), nullable=True),
        sa.Column("floor_plan_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["building_id"], ["org_buildings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("building_id", "floor_number", name="uq_org_floors_building_floor"),
    )
    op.create_index("ix_org_floors_building_id", "org_floors", ["building_id"])
    op.create_index("ix_org_floors_organisation_id", "org_floors", ["organisation_id"])

    # ── org_zones ──────────────────────────────────────────────────────────────
    op.create_table(
        "org_zones",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("floor_id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("zone_type", sa.String(50), nullable=False),
        sa.Column("boundary_polygon", JSONB(), nullable=True),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["floor_id"], ["org_floors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_org_zones_floor_id", "org_zones", ["floor_id"])
    op.create_index("ix_org_zones_organisation_id", "org_zones", ["organisation_id"])
    op.create_index("ix_org_zones_department_id", "org_zones", ["department_id"])

    # ── org_points_of_interest ─────────────────────────────────────────────────
    op.create_table(
        "org_points_of_interest",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("floor_id", sa.UUID(), nullable=False),
        sa.Column("zone_id", sa.UUID(), nullable=True),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("code", sa.String(100), nullable=True),
        sa.Column("poi_type", sa.String(50), nullable=False),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lng", sa.Float(), nullable=True),
        sa.Column("gps_accuracy_radius_m", sa.Integer(), nullable=True),
        sa.Column("boundary_polygon", JSONB(), nullable=True),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("service_id", sa.UUID(), nullable=True),
        sa.Column("staff_assigned_user_id", sa.UUID(), nullable=True),
        sa.Column("is_emergency_point", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("nearest_emergency_poi_id", sa.UUID(), nullable=True),
        sa.Column("connections_to", JSONB(), nullable=True),
        sa.Column("qr_code_id", sa.UUID(), nullable=True),
        sa.Column("accessibility_notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["floor_id"], ["org_floors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["org_zones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_org_poi_floor_id", "org_points_of_interest", ["floor_id"])
    op.create_index("ix_org_poi_zone_id", "org_points_of_interest", ["zone_id"])
    op.create_index("ix_org_poi_organisation_id", "org_points_of_interest", ["organisation_id"])
    op.create_index("ix_org_poi_is_emergency", "org_points_of_interest", ["is_emergency_point"])


def downgrade() -> None:
    op.drop_table("org_points_of_interest")
    op.drop_table("org_zones")
    op.drop_table("org_floors")
    op.drop_table("org_buildings")
