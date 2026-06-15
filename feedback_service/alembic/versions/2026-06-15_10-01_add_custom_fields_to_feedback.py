"""Add custom_fields JSONB column to feedbacks table.

Revision ID: bf1c2d3e4f5a
Revises: 9e8d7c6b5a49
Create Date: 2026-06-15 10:01:00

WHY
───
Organisations have industry-specific data they need to capture alongside
standard feedback fields. For example, a hospital needs patient_file_number
and drug_batch_number; a telecom needs service_account_number and device_imei.

custom_fields is a free-form JSONB blob whose keys are OrgCustomFieldDefinition
field_key values. The auth_service defines which fields each org has; the
feedback_service stores the submitted values here without cross-DB FK constraints.

Example value:
  {"patient_file_number": "MNH-44521", "drug_batch_number": "AB123"}
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "bf1c2d3e4f5a"
down_revision = "9e8d7c6b5a49"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "feedbacks",
        sa.Column("custom_fields", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("feedbacks", "custom_fields")
