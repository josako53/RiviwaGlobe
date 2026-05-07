
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.staff_counter import StaffCounter


class PointType(str, Enum):
    DESK    = "DESK"
    COUNTER = "COUNTER"
    ROOM    = "ROOM"
    KIOSK   = "KIOSK"
    STAGE   = "STAGE"
    WARD    = "WARD"
    CASHIER = "CASHIER"


class ServicePoint(SQLModel, table=True):
    """Named location at which staff attend to queue tickets."""
    __tablename__ = "service_points"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_service_point_org_code"),
        Index("ix_sp_org_id",    "org_id"),
        Index("ix_sp_type",      "point_type"),
        Index("ix_sp_is_active", "is_active"),
    )

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    )
    org_id: uuid.UUID = Field(sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True))
    name: str = Field(sa_column=Column(String(200), nullable=False))
    code: str = Field(sa_column=Column(String(30), nullable=False, index=True))
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    point_type: str = Field(sa_column=Column(String(20), nullable=False, index=True))
    max_concurrent_staff: int = Field(default=1, sa_column=Column(Integer, nullable=False, default=1))
    avg_service_minutes: float = Field(default=5.0, sa_column=Column(Float, nullable=False, default=5.0))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True, index=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

    staff_counters: List["StaffCounter"] = Relationship(
        back_populates="service_point",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

