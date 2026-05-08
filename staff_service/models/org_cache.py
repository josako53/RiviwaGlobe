"""models/org_cache.py — Local cache of organisation records."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class OrgCache(SQLModel, table=True):
    __tablename__ = "org_cache"

    org_id: UUID = Field(primary_key=True)
    name: str = Field(max_length=300)
    slug: Optional[str] = Field(default=None, max_length=200)
    is_active: bool = Field(default=True)
    synced_at: datetime = Field(default_factory=datetime.utcnow)
