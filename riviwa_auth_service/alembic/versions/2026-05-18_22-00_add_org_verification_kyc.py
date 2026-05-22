"""Add organisation payment/KYC verification and KYC submission tables

Revision ID: b7c8d9e0f1a2
Revises: c7d8e9f0a1b2
Create Date: 2026-05-18 22:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7c8d9e0f1a2'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── New columns on organisations ─────────────────────────────────────────
    op.add_column('organisations', sa.Column('is_payment_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('organisations', sa.Column('payment_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('organisations', sa.Column('is_kyc_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('organisations', sa.Column('kyc_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('organisations', sa.Column('kyc_verified_by_id', sa.UUID(), nullable=True))
    op.add_column('organisations', sa.Column('kyc_rejection_reason', sa.String(512), nullable=True))

    op.create_index('ix_organisations_is_payment_verified', 'organisations', ['is_payment_verified'])
    op.create_index('ix_organisations_is_kyc_verified', 'organisations', ['is_kyc_verified'])

    # ── org_kyc_submissions ──────────────────────────────────────────────────
    op.create_table(
        'org_kyc_submissions',
        sa.Column('id',              sa.UUID(),          primary_key=True),
        sa.Column('org_id',          sa.UUID(),          nullable=False,  index=True),
        sa.Column('submitted_by_id', sa.UUID(),          nullable=False),
        sa.Column('status',          sa.String(32),      nullable=False,  server_default='pending'),
        sa.Column('business_type',   sa.String(64),      nullable=True),
        sa.Column('reg_number',      sa.String(100),     nullable=True),
        sa.Column('tax_id',          sa.String(100),     nullable=True),
        sa.Column('notes_for_admin', sa.Text(),          nullable=True),
        sa.Column('admin_notes',     sa.Text(),          nullable=True),
        sa.Column('rejection_reason',sa.String(512),     nullable=True),
        sa.Column('reviewed_by_id',  sa.UUID(),          nullable=True),
        sa.Column('submitted_at',    sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('reviewed_at',     sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at',      sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_org_kyc_submissions_status', 'org_kyc_submissions', ['status'])

    # ── org_kyc_documents ────────────────────────────────────────────────────
    op.create_table(
        'org_kyc_documents',
        sa.Column('id',              sa.UUID(),          primary_key=True),
        sa.Column('org_id',          sa.UUID(),          nullable=False,  index=True),
        sa.Column('submission_id',   sa.UUID(),          nullable=False,  index=True),
        sa.Column('document_type',   sa.String(64),      nullable=False),
        sa.Column('file_url',        sa.String(512),     nullable=False),
        sa.Column('file_name',       sa.String(255),     nullable=True),
        sa.Column('file_size_bytes', sa.Integer(),       nullable=True),
        sa.Column('uploaded_by_id',  sa.UUID(),          nullable=False),
        sa.Column('is_verified',     sa.Boolean(),       nullable=False, server_default='false'),
        sa.Column('uploaded_at',     sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['submission_id'], ['org_kyc_submissions.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    op.drop_table('org_kyc_documents')
    op.drop_table('org_kyc_submissions')
    op.drop_index('ix_organisations_is_kyc_verified', 'organisations')
    op.drop_index('ix_organisations_is_payment_verified', 'organisations')
    op.drop_column('organisations', 'kyc_rejection_reason')
    op.drop_column('organisations', 'kyc_verified_by_id')
    op.drop_column('organisations', 'kyc_verified_at')
    op.drop_column('organisations', 'is_kyc_verified')
    op.drop_column('organisations', 'payment_verified_at')
    op.drop_column('organisations', 'is_payment_verified')
