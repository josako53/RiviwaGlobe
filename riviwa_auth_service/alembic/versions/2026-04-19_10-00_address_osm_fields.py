"""address_osm_fields

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-04-19 10:00:00.000000+00:00

Adds OSM / Nominatim metadata columns to the addresses table and makes
line1 nullable to support GPS-only and OSM-sourced addresses that derive
their display string from Nominatim's display_name.

Changes
────────
  · addresses.line1              VARCHAR(200) NOT NULL → nullable
  · addresses.source             VARCHAR(10)  NOT NULL DEFAULT 'manual'  (new)
  · addresses.osm_id             BIGINT       nullable                   (new)
  · addresses.osm_type           VARCHAR(10)  nullable                   (new)
  · addresses.place_id           BIGINT       nullable, indexed           (new)
  · addresses.display_name       TEXT         nullable                   (new)
  · addresses.place_rank         INTEGER      nullable                   (new)
  · addresses.place_type         VARCHAR(100) nullable                   (new)
  · addresses.address_class      VARCHAR(50)  nullable                   (new)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision      = "e1f2a3b4c5d6"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # Make line1 nullable (existing rows are unaffected — they have values)
    op.alter_column(
        "addresses", "line1",
        existing_type=sa.String(200),
        nullable=True,
    )

    # Add source column (default 'manual' covers all pre-existing rows)
    op.add_column(
        "addresses",
        sa.Column("source", sa.String(10), nullable=False, server_default="manual"),
    )

    # Add OSM metadata columns
    op.add_column("addresses", sa.Column("osm_id",        sa.BigInteger, nullable=True))
    op.add_column("addresses", sa.Column("osm_type",      sa.String(10), nullable=True))
    op.add_column("addresses", sa.Column("place_id",      sa.BigInteger, nullable=True))
    op.add_column("addresses", sa.Column("display_name",  sa.Text,       nullable=True))
    op.add_column("addresses", sa.Column("place_rank",    sa.Integer,    nullable=True))
    op.add_column("addresses", sa.Column("place_type",    sa.String(100),nullable=True))
    op.add_column("addresses", sa.Column("address_class", sa.String(50), nullable=True))

    # Index place_id for deduplication queries
    op.create_index("ix_addresses_place_id", "addresses", ["place_id"])


def downgrade() -> None:
    op.drop_index("ix_addresses_place_id", table_name="addresses")
    op.drop_column("addresses", "address_class")
    op.drop_column("addresses", "place_type")
    op.drop_column("addresses", "place_rank")
    op.drop_column("addresses", "display_name")
    op.drop_column("addresses", "place_id")
    op.drop_column("addresses", "osm_type")
    op.drop_column("addresses", "osm_id")
    op.drop_column("addresses", "source")

    # Restore line1 to NOT NULL (safe only if all rows have line1 set)
    op.alter_column(
        "addresses", "line1",
        existing_type=sa.String(200),
        nullable=False,
    )
