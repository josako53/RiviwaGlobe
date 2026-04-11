"""add_cover_image_org_logo_to_fb_projects

Revision ID: a1b2c3d4e5f6
Revises: 83411431c615
Create Date: 2026-04-11 00:00:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '83411431c615'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('fb_projects', sa.Column('cover_image_url', sa.String(length=500), nullable=True))
    op.add_column('fb_projects', sa.Column('org_logo_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('fb_projects', 'org_logo_url')
    op.drop_column('fb_projects', 'cover_image_url')
