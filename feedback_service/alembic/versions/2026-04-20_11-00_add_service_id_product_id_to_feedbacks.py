"""add_service_id_product_id_to_feedbacks

Revision ID: a1b2c3d4e5f6
Revises:     f3a4b5c6d7e8
Create Date: 2026-04-20 11:00:00

Changes
───────
  · feedbacks.service_id   UUID nullable indexed  — soft link to auth_service OrgService.id
  · feedbacks.product_id   UUID nullable indexed  — soft link to auth_service OrgService.id (service_type=PRODUCT)

Both are cross-database soft links — no FK constraints.
Enables filtering: GET /feedback?service_id=...&product_id=...&category_def_id=...
"""
from alembic import op
import sqlalchemy as sa

revision      = "a1b2c3d4e5f6"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column("feedbacks", sa.Column("service_id", sa.UUID(as_uuid=True), nullable=True))
    op.add_column("feedbacks", sa.Column("product_id", sa.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_feedbacks_service_id", "feedbacks", ["service_id"])
    op.create_index("ix_feedbacks_product_id", "feedbacks", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_feedbacks_product_id", table_name="feedbacks")
    op.drop_index("ix_feedbacks_service_id",  table_name="feedbacks")
    op.drop_column("feedbacks", "product_id")
    op.drop_column("feedbacks", "service_id")
