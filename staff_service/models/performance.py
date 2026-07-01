"""models/performance.py — Staff performance flag for applause recognition."""
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class StaffPerformanceFlag(SQLModel, table=True):
    __tablename__ = "staff_performance_flags"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    staff_id: uuid.UUID = Field(nullable=False, index=True)
    org_id: uuid.UUID = Field(nullable=False, index=True)
    feedback_ref: str = Field(max_length=50, nullable=False)
    feedback_type: str = Field(max_length=20, default="applause", nullable=False)
    note: str = Field(nullable=False)
    flagged_by: str = Field(max_length=50, default="ai_conversation", nullable=False)
    flagged_at: datetime = Field(default_factory=lambda: datetime.utcnow(), nullable=False)
