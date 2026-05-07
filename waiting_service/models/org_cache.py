
import uuid
from datetime import datetime

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class OrgCache(SQLModel, table=True):
    """Denormalised org snapshot synced via Kafka organisation events."""
    __tablename__ = "org_cache"

    org_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    )
    name: str = Field(sa_column=Column(String(300), nullable=False))
    slug: str = Field(default=None, sa_column=Column(String(200), nullable=True))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))
    synced_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

