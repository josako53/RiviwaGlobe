from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ServicePointStats(BaseModel):
    service_point_id:    uuid.UUID
    service_point_name:  str
    point_type:          str
    waiting_count:       int
    attending_count:     int
    avg_wait_seconds:    Optional[float]
    avg_service_seconds: Optional[float]
    throughput_today:    int

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    org_id:                uuid.UUID
    generated_at:          datetime
    total_waiting:         int
    total_attending:       int
    total_completed_today: int
    service_points:        List[ServicePointStats]
