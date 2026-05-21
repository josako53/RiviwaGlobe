"""Add made_in, how_to_use, org_product_custom_field_defs, product_documents

Revision ID: b2c3d4e5f6a7
Revises: a1f2e3d4c5b6
Create Date: 2026-05-18 00:00:00.000000+00:00

Changes:
  - products: add made_in (VARCHAR 150), how_to_use (TEXT)
  - product_attributes: add custom_field_def_id (UUID nullable)
  - NEW TABLE: org_product_custom_field_defs
  - NEW TABLE: product_documents
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1f2e3d4c5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── products: new columns ─────────────────────────────────────────────────
    op.add_column("products", sa.Column("made_in",    sa.String(150), nullable=True))
    op.add_column("products", sa.Column("how_to_use", sa.Text(),      nullable=True))

    # ── product_attributes: link to custom field def ──────────────────────────
    op.add_column("product_attributes",
        sa.Column("custom_field_def_id", sa.UUID(), nullable=True, index=True))

    # ── org_product_custom_field_defs ─────────────────────────────────────────
    op.create_table(
        "org_product_custom_field_defs",
        sa.Column("id",          sa.UUID(),    primary_key=True),
        sa.Column("org_id",      sa.UUID(),    nullable=False,  index=True),
        sa.Column("field_name",  sa.String(200), nullable=False),
        sa.Column("field_label", sa.String(200), nullable=False),
        sa.Column("field_type",  sa.String(20),  nullable=False, server_default="text"),
        sa.Column("options",     sa.JSON(),     nullable=True),
        sa.Column("placeholder", sa.String(300), nullable=True),
        sa.Column("help_text",   sa.String(500), nullable=True),
        sa.Column("is_required", sa.Boolean(),  nullable=False, server_default="false"),
        sa.Column("max_length",  sa.Integer(),  nullable=True),
        sa.Column("applies_to_product_types", sa.JSON(), nullable=True),
        sa.Column("group",       sa.String(100), nullable=True),
        sa.Column("position",    sa.Integer(),  nullable=False, server_default="0"),
        sa.Column("unit",        sa.String(50),  nullable=True),
        sa.Column("is_active",   sa.Boolean(),  nullable=False, server_default="true"),
        sa.Column("created_by",  sa.UUID(),     nullable=True),
        sa.Column("created_at",  sa.DateTime(), nullable=False),
        sa.Column("updated_at",  sa.DateTime(), nullable=False),
    )
    op.create_index("ix_org_custom_field_defs_org_id",
                    "org_product_custom_field_defs", ["org_id"])
    op.create_index("ix_org_custom_field_defs_field_name",
                    "org_product_custom_field_defs", ["org_id", "field_name"])

    # ── product_documents ─────────────────────────────────────────────────────
    op.create_table(
        "product_documents",
        sa.Column("id",             sa.UUID(),     primary_key=True),
        sa.Column("product_id",     sa.UUID(),     nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"], ondelete="CASCADE"),
        sa.Column("title",          sa.String(300), nullable=False),
        sa.Column("document_type",  sa.String(30),  nullable=False, server_default="OTHER",  index=True),
        sa.Column("file_format",    sa.String(10),  nullable=False, server_default="PDF"),
        sa.Column("file_url",       sa.String(1000), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(),  nullable=True),
        sa.Column("content_md",     sa.Text(),      nullable=True),
        sa.Column("version",        sa.String(50),  nullable=True),
        sa.Column("language",       sa.String(10),  nullable=False, server_default="en"),
        sa.Column("description",    sa.String(500), nullable=True),
        sa.Column("is_public",      sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("uploaded_by",    sa.UUID(),      nullable=True),
        sa.Column("created_at",     sa.DateTime(),  nullable=False),
        sa.Column("updated_at",     sa.DateTime(),  nullable=False),
    )
    op.create_index("ix_product_documents_product_id",
                    "product_documents", ["product_id"])


def downgrade() -> None:
    op.drop_table("product_documents")
    op.drop_index("ix_org_custom_field_defs_field_name", "org_product_custom_field_defs")
    op.drop_index("ix_org_custom_field_defs_org_id", "org_product_custom_field_defs")
    op.drop_table("org_product_custom_field_defs")
    op.drop_column("product_attributes", "custom_field_def_id")
    op.drop_column("products", "how_to_use")
    op.drop_column("products", "made_in")
