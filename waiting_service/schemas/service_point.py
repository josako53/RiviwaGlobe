from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ServicePointCreate(BaseModel):
    org_id:               uuid.UUID
    name:                 str   = Field(..., max_length=200)
    code:                 str   = Field(..., max_length=30)
    description:          Optional[str] = None
    point_type:           str   = Field(..., description="DESK|COUNTER|ROOM|KIOSK|STAGE|WARD|CASHIER")
    max_concurrent_staff: int   = Field(default=1, ge=1, le=50)
    avg_service_minutes:  float = Field(default=5.0, gt=0)
    is_active:            bool  = True


class ServicePointUpdate(BaseModel):
    name:                 Optional[str]   = Field(default=None, max_length=200)
    code:                 Optional[str]   = Field(default=None, max_length=30)
    description:          Optional[str]   = None
    point_type:           Optional[str]   = None
    max_concurrent_staff: Optional[int]   = Field(default=None, ge=1, le=50)
    avg_service_minutes:  Optional[float] = Field(default=None, gt=0)
    is_active:            Optional[bool]  = None


class ServicePointOut(BaseModel):
    id:                   uuid.UUID
    org_id:               uuid.UUID
    name:                 str
    code:                 str
    description:          Optional[str]
    point_type:           str
    max_concurrent_staff: int
    avg_service_minutes:  float
    is_active:            bool
    created_at:           datetime
    updated_at:           datetime

    model_config = {"from_attributes": True}
