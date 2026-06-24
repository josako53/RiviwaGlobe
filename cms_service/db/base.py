"""
db/base.py — Single import point for Alembic autogenerate.
All CMS models must be imported here so Alembic can discover them.
"""
from sqlmodel import SQLModel

Base = SQLModel

from models.post import (          # noqa: F401, E402
    OrgPost,
    OrgPostCategory,
    OrgPostCategoryLink,
    OrgPostRevision,
)
