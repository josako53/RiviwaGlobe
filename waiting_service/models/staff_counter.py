
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.service_point import ServicePoint
    from models.staff_session import StaffSession


class StaffCounter(SQLModel, table=True):
    """Individual desk within a ServicePoint. Serves one ticket at a time."""
    __tablename__ = "staff_counters"
    __table_args__ = (
        UniqueConstraint("service_point_id", "code", name="uq_sc_point_code"),
        Index("ix_sc_org_id",            "org_id"),
        Index("ix_sc_service_point_id",  "service_point_id"),
        Index("ix_sc_user_id",           "user_id"),
        Index("ix_sc_is_active",         "is_active"),
        Index("ix_sc_current_ticket_id", "current_ticket_id"),
    )

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    )
    org_id: uuid.UUID = Field(sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True))
    service_point_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("service_points.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
    )
    name: str = Field(sa_column=Column(String(150), nullable=False))
    code: str = Field(sa_column=Column(String(20), nullable=False))
    user_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), nullable=True, index=True)
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True, index=True))
    current_ticket_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("queue_tickets.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

    service_point: "ServicePoint" = Relationship(back_populates="staff_counters")
    sessions: List["StaffSession"] = Relationship(
        back_populates="counter",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @property
    def is_available(self) -> bool:
        return self.current_ticket_id is None and self.is_active

