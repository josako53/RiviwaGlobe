from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FlowStepIn(BaseModel):
    service_point_id: uuid.UUID
    step_order:       int  = Field(..., ge=1)
    is_optional:      bool = False


class FlowStepOut(BaseModel):
    id:               uuid.UUID
    flow_id:          uuid.UUID
    service_point_id: uuid.UUID
    step_order:       int
    is_optional:      bool

    model_config = {"from_attributes": True}


class ServiceFlowCreate(BaseModel):
    org_id:      uuid.UUID
    name:        str  = Field(..., max_length=200)
    description: Optional[str] = None
    is_active:   bool = True
    is_default:  bool = False
    steps:       List[FlowStepIn] = Field(..., min_length=1)


class ServiceFlowUpdate(BaseModel):
    name:        Optional[str]              = Field(default=None, max_length=200)
    description: Optional[str]              = None
    is_active:   Optional[bool]             = None
    is_default:  Optional[bool]             = None
    steps:       Optional[List[FlowStepIn]] = None


class ServiceFlowOut(BaseModel):
    id:          uuid.UUID
    org_id:      uuid.UUID
    name:        str
    description: Optional[str]
    is_active:   bool
    is_default:  bool
    created_at:  datetime
    updated_at:  datetime
    steps:       List[FlowStepOut] = []

    model_config = {"from_attributes": True}
