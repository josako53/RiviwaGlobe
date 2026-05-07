
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.service_point import ServicePoint


class ServiceFlow(SQLModel, table=True):
    """Ordered sequence of service points a customer passes through."""
    __tablename__ = "service_flows"
    __table_args__ = (
        Index("ix_sf_org_id",     "org_id"),
        Index("ix_sf_is_active",  "is_active"),
        Index("ix_sf_is_default", "is_default"),
    )

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    )
    org_id: uuid.UUID = Field(sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True))
    name: str = Field(sa_column=Column(String(200), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True, index=True))
    is_default: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, default=False, index=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

    steps: List["FlowStep"] = Relationship(
        back_populates="flow",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "FlowStep.step_order"},
    )


class FlowStep(SQLModel, table=True):
    """One step in a ServiceFlow, pointing to the ServicePoint and its position."""
    __tablename__ = "flow_steps"
    __table_args__ = (
        UniqueConstraint("flow_id", "step_order", name="uq_flow_step_order"),
        Index("ix_fstep_flow_id",          "flow_id"),
        Index("ix_fstep_service_point_id", "service_point_id"),
    )

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    )
    flow_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("service_flows.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
    )
    service_point_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("service_points.id", ondelete="RESTRICT"),
            nullable=False, index=True,
        )
    )
    step_order: int = Field(sa_column=Column(Integer, nullable=False))
    is_optional: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, default=False))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

    flow: "ServiceFlow" = Relationship(back_populates="steps")
    service_point: "ServicePoint" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[FlowStep.service_point_id]"}
    )

