from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import TokenClaims
from core.exceptions import ForbiddenError
from waiting_redis.client import WaitingRedis
from repositories.analytics_repository import AnalyticsRepository
from schemas.analytics import DashboardOut, ServicePointStats

log = structlog.get_logger(__name__)


class AnalyticsService:

    def __init__(self, db: AsyncSession, redis: WaitingRedis) -> None:
        self.db    = db
        self.redis = redis
        self.repo  = AnalyticsRepository(db)

    async def get_dashboard(self, org_id: uuid.UUID, token: TokenClaims) -> DashboardOut:
        if token.org_id and token.org_id != org_id:
            raise ForbiddenError()

        raw_stats = await self.repo.get_service_point_stats(org_id)
        total_completed = await self.repo.get_total_completed_today(org_id)

        # Overlay live Redis queue depths
        live_depths = await self.redis.get_all_queue_depths()

        point_stats: List[ServicePointStats] = []
        total_waiting = 0
        total_attending = 0

        for s in raw_stats:
            # Prefer Redis depth for real-time accuracy, fallback to DB count
            point_id_str = str(s["service_point_id"])
            live_waiting = live_depths.get(point_id_str, s["waiting_count"])
            total_waiting   += live_waiting
            total_attending += s["attending_count"]

            point_stats.append(ServicePointStats(
                service_point_id=s["service_point_id"],
                service_point_name=s["service_point_name"],
                point_type=s["point_type"],
                waiting_count=live_waiting,
                attending_count=s["attending_count"],
                avg_wait_seconds=s["avg_wait_seconds"],
                avg_service_seconds=s["avg_service_seconds"],
                throughput_today=s["throughput_today"],
            ))

        return DashboardOut(
            org_id=org_id,
            generated_at=datetime.now(timezone.utc),
            total_waiting=total_waiting,
            total_attending=total_attending,
            total_completed_today=total_completed,
            service_points=point_stats,
        )
