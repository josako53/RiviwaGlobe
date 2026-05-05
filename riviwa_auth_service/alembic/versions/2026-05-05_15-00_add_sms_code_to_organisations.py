"""add_sms_code_to_organisations

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-05-05 15:00:00.000000+00:00

Adds the `sms_code` column to the organisations table.

  sms_code  VARCHAR(10)  nullable  unique
  ─────────────────────────────────────────────
  Short prefix used in Riviwa unified SMS codes.
  One Riviwa number serves all organisations; the prefix disambiguates.
  Format: {SMS_CODE}-{SHORT_CODE}  e.g.  UTT-AB3X9KPJ, CRDB-XY7ZMNPQ
  Rules: 2–10 uppercase alphanumeric chars, globally unique, nullable.
  Examples: UTT, CRDB, NMB, CCBRT, TESLA, TARURA
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision      = "a1b2c3d4e5f6"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "organisations",
        sa.Column("sms_code", sa.String(10), nullable=True),
    )
    op.create_unique_constraint(
        "uq_organisations_sms_code", "organisations", ["sms_code"]
    )
    op.create_index(
        "ix_organisations_sms_code", "organisations", ["sms_code"]
    )


def downgrade() -> None:
    op.drop_index("ix_organisations_sms_code", table_name="organisations")
    op.drop_constraint("uq_organisations_sms_code", "organisations", type_="unique")
    op.drop_column("organisations", "sms_code")
