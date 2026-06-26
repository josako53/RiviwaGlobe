"""Add CONSTITUTION value to policy_document_type enum

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-26 18:00:00.000000+00:00
"""
from __future__ import annotations

from alembic import op

revision      = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.execute("ALTER TYPE policy_document_type ADD VALUE IF NOT EXISTS 'CONSTITUTION'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    # To roll back: recreate the enum without CONSTITUTION and cast the column.
    op.execute("""
        ALTER TABLE industry_policy_documents
            ALTER COLUMN policy_type TYPE VARCHAR(50);
        DROP TYPE policy_document_type;
        CREATE TYPE policy_document_type AS ENUM (
            'LAW', 'REGULATION', 'POLICY', 'STANDARD',
            'GUIDELINE', 'DIRECTIVE', 'FRAMEWORK'
        );
        ALTER TABLE industry_policy_documents
            ALTER COLUMN policy_type TYPE policy_document_type
                USING policy_type::policy_document_type;
    """)
