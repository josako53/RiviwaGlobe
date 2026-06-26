"""Add branch content, service objective, industry policy documents, platform guides

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-26 10:00:00.000000+00:00

Changes
───────
  org_branch_content       NEW — 1:1 with org_branches: mission, vision,
                            objectives, functionalities, strategic_focus.
  org_services.objective   NEW COLUMN — explicit objective statement.
  industry_policy_documents NEW — country laws, regulations, standards,
                            guidelines, directives, frameworks.
  platform_guides          NEW — professional guides and assistance documents
                            for GRM focal persons, org admins, auditors.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision      = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    policy_document_type = sa.Enum(
        "LAW", "REGULATION", "POLICY", "STANDARD", "GUIDELINE", "DIRECTIVE", "FRAMEWORK",
        name="policy_document_type",
    )
    guide_type = sa.Enum(
        "PROFESSIONAL_GUIDE", "REFERENCE_MANUAL", "STANDARD", "BEST_PRACTICE",
        "TRAINING_MATERIAL", "CHECKLIST", "TEMPLATE", "FAQ",
        name="guide_type",
    )
    policy_document_type.create(op.get_bind(), checkfirst=True)
    guide_type.create(op.get_bind(), checkfirst=True)

    # ── 1. org_branch_content (1:1 with org_branches) ─────────────────────────
    op.create_table(
        "org_branch_content",
        sa.Column("id",              sa.UUID(as_uuid=True),  primary_key=True),
        sa.Column("branch_id",       sa.UUID(as_uuid=True),  nullable=False, unique=True),
        sa.Column("org_id",          sa.UUID(as_uuid=True),  nullable=False),
        sa.Column("mission",         sa.Text(),               nullable=True),
        sa.Column("vision",          sa.Text(),               nullable=True),
        sa.Column("objectives",      sa.Text(),               nullable=True),
        sa.Column("functionalities", JSONB(),                 nullable=True),
        sa.Column("strategic_focus", sa.String(500),          nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["org_branches.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organisations.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_org_branch_content_branch_id", "org_branch_content", ["branch_id"])
    op.create_index("ix_org_branch_content_org_id",    "org_branch_content", ["org_id"])

    # ── 2. org_services.objective (new column) ─────────────────────────────────
    op.add_column(
        "org_services",
        sa.Column("objective", sa.Text(), nullable=True),
    )

    # ── 3. industry_policy_documents ──────────────────────────────────────────
    op.create_table(
        "industry_policy_documents",
        sa.Column("id",                sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("industry_id",       sa.UUID(as_uuid=True), nullable=True),
        sa.Column("country_code",      sa.String(3),          nullable=True),
        sa.Column("region",            sa.String(100),        nullable=True),
        sa.Column(
            "policy_type",
            sa.Enum(
                "LAW", "REGULATION", "POLICY", "STANDARD",
                "GUIDELINE", "DIRECTIVE", "FRAMEWORK",
                name="policy_document_type", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title",             sa.String(500),        nullable=False),
        sa.Column("slug",              sa.String(200),        nullable=False, unique=True),
        sa.Column("issuing_authority", sa.String(300),        nullable=True),
        sa.Column("document_number",   sa.String(100),        nullable=True),
        sa.Column("effective_date",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_md",        sa.Text(),             nullable=True),
        sa.Column("file_url",          sa.String(1024),       nullable=True),
        sa.Column("version",           sa.String(50),         nullable=True),
        sa.Column("language",          sa.String(10),         nullable=False, server_default="en"),
        sa.Column("is_active",         sa.Boolean(),          nullable=False, server_default="true"),
        sa.Column("is_public",         sa.Boolean(),          nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["industry_id"], ["industries.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_ind_policy_docs_industry_id",   "industry_policy_documents", ["industry_id"])
    op.create_index("ix_ind_policy_docs_country_code",  "industry_policy_documents", ["country_code"])
    op.create_index("ix_ind_policy_docs_policy_type",   "industry_policy_documents", ["policy_type"])
    op.create_index("ix_ind_policy_docs_slug",          "industry_policy_documents", ["slug"])

    # ── 4. platform_guides ────────────────────────────────────────────────────
    op.create_table(
        "platform_guides",
        sa.Column("id",                 sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("industry_id",        sa.UUID(as_uuid=True), nullable=True),
        sa.Column("title",              sa.String(500),        nullable=False),
        sa.Column("slug",               sa.String(200),        nullable=False, unique=True),
        sa.Column(
            "guide_type",
            sa.Enum(
                "PROFESSIONAL_GUIDE", "REFERENCE_MANUAL", "STANDARD", "BEST_PRACTICE",
                "TRAINING_MATERIAL", "CHECKLIST", "TEMPLATE", "FAQ",
                name="guide_type", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("applicable_sectors", JSONB(),               nullable=True),
        sa.Column("target_audience",    sa.String(200),        nullable=True),
        sa.Column("content_md",         sa.Text(),             nullable=True),
        sa.Column("file_url",           sa.String(1024),       nullable=True),
        sa.Column("file_format",        sa.String(20),         nullable=True),
        sa.Column("version",            sa.String(50),         nullable=True),
        sa.Column("language",           sa.String(10),         nullable=False, server_default="en"),
        sa.Column("source_standard",    sa.String(300),        nullable=True),
        sa.Column("is_public",          sa.Boolean(),          nullable=False, server_default="true"),
        sa.Column("is_active",          sa.Boolean(),          nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["industry_id"], ["industries.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_platform_guides_industry_id", "platform_guides", ["industry_id"])
    op.create_index("ix_platform_guides_guide_type",  "platform_guides", ["guide_type"])
    op.create_index("ix_platform_guides_slug",        "platform_guides", ["slug"])


def downgrade() -> None:
    op.drop_table("platform_guides")
    op.drop_table("industry_policy_documents")
    op.drop_column("org_services", "objective")
    op.drop_table("org_branch_content")

    sa.Enum(name="guide_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="policy_document_type").drop(op.get_bind(), checkfirst=True)
