"""
repositories/activity_repository.py
────────────────────────────────────────────────────────────────────────────
All database operations for EngagementActivity and StakeholderEngagement.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.engagement import (
    ActivityMedia,
    ActivityStatus,
    ActivityType,
    AttendanceStatus,
    EngagementActivity,
    EngagementStage,
    MediaType,
    StakeholderEngagement,
)
from models.stakeholder import StakeholderContact


class ActivityRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        project_id:           uuid.UUID,
        stage:                EngagementStage,
        activity_type:        ActivityType,
        title:                str,
        conducted_by_user_id: uuid.UUID,
        description:          Optional[str]       = None,
        agenda:               Optional[str]       = None,
        venue:                Optional[str]       = None,
        lga:                  Optional[str]       = None,
        ward:                 Optional[str]       = None,
        gps_lat:              Optional[float]     = None,
        gps_lng:              Optional[float]     = None,
        virtual_platform:     Optional[str]       = None,
        virtual_url:          Optional[str]       = None,
        virtual_meeting_id:   Optional[str]       = None,
        scheduled_at:         Optional[datetime]  = None,
        expected_count:       Optional[int]       = None,
        languages_used:       Optional[dict]      = None,
        # Previously missing fields
        stage_id:             Optional[uuid.UUID] = None,
        subproject_id:        Optional[uuid.UUID] = None,
        duration_hours:       Optional[float]     = None,
        female_count:         Optional[int]       = None,
        vulnerable_count:     Optional[int]       = None,
    ) -> EngagementActivity:
        a = EngagementActivity(
            project_id           = project_id,
            stage_id             = stage_id,
            subproject_id        = subproject_id,
            stage                = stage,
            activity_type        = activity_type,
            status               = ActivityStatus.PLANNED,
            title                = title,
            description          = description,
            agenda               = agenda,
            venue                = venue,
            lga                  = lga,
            ward                 = ward,
            gps_lat              = gps_lat,
            gps_lng              = gps_lng,
            virtual_platform     = virtual_platform,
            virtual_url          = virtual_url,
            virtual_meeting_id   = virtual_meeting_id,
            scheduled_at         = scheduled_at,
            expected_count       = expected_count,
            female_count         = female_count,
            vulnerable_count     = vulnerable_count,
            duration_hours       = duration_hours,
            languages_used       = languages_used,
            conducted_by_user_id = conducted_by_user_id,
        )
        self.db.add(a)
        await self.db.flush()
        await self.db.refresh(a)
        return a

    async def get_by_id(self, activity_id: uuid.UUID) -> Optional[EngagementActivity]:
        result = await self.db.execute(
            select(EngagementActivity).where(EngagementActivity.id == activity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_attendances(
        self, activity_id: uuid.UUID
    ) -> Optional[EngagementActivity]:
        result = await self.db.execute(
            select(EngagementActivity)
            .options(selectinload(EngagementActivity.attendances))
            .where(EngagementActivity.id == activity_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        project_id: Optional[uuid.UUID] = None,
        stage:      Optional[str]       = None,
        status:     Optional[str]       = None,
        lga:        Optional[str]       = None,
        skip:       int                 = 0,
        limit:      int                 = 50,
    ) -> list[EngagementActivity]:
        q = select(EngagementActivity)
        if project_id: q = q.where(EngagementActivity.project_id == project_id)
        if stage:      q = q.where(EngagementActivity.stage == stage)
        if status:     q = q.where(EngagementActivity.status == status)
        if lga:        q = q.where(EngagementActivity.lga.ilike(f"%{lga}%"))
        q = q.offset(skip).limit(limit).order_by(EngagementActivity.scheduled_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def save(self, a: EngagementActivity) -> None:
        self.db.add(a)

    # ── Engagements (attendances) ─────────────────────────────────────────────

    async def create_engagement(
        self,
        contact_id:        uuid.UUID,
        activity_id:       uuid.UUID,
        logged_by_user_id: uuid.UUID,
        attendance_status: AttendanceStatus = AttendanceStatus.ATTENDED,
        proxy_name:        Optional[str]    = None,
        concerns_raised:   Optional[str]    = None,
        response_given:    Optional[str]    = None,
        notes:             Optional[str]    = None,
    ) -> StakeholderEngagement:
        e = StakeholderEngagement(
            contact_id        = contact_id,
            activity_id       = activity_id,
            attendance_status = attendance_status,
            proxy_name        = proxy_name,
            concerns_raised   = concerns_raised,
            response_given    = response_given,
            notes             = notes,
            logged_by_user_id = logged_by_user_id,
        )
        self.db.add(e)
        await self.db.flush()
        await self.db.refresh(e)
        return e

    async def get_engagement_by_id(
        self, engagement_id: uuid.UUID, activity_id: Optional[uuid.UUID] = None
    ) -> Optional[StakeholderEngagement]:
        q = select(StakeholderEngagement).where(StakeholderEngagement.id == engagement_id)
        if activity_id:
            q = q.where(StakeholderEngagement.activity_id == activity_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_engagements_for_activity(
        self, activity_id: uuid.UUID
    ) -> list[StakeholderEngagement]:
        result = await self.db.execute(
            select(StakeholderEngagement).where(
                StakeholderEngagement.activity_id == activity_id
            )
        )
        return list(result.scalars().all())

    async def save_engagement(self, e: StakeholderEngagement) -> None:
        self.db.add(e)

    async def delete_engagement(self, engagement_id: uuid.UUID, activity_id: uuid.UUID) -> bool:
        """Hard delete an attendance record. Returns True if found and deleted."""
        e = await self.get_engagement_by_id(engagement_id, activity_id)
        if not e:
            return False
        await self.db.delete(e)
        return True

    async def bulk_create_engagements(
        self,
        activity_id:   uuid.UUID,
        records:       list[dict],
        logged_by_uid: uuid.UUID,
    ) -> list[StakeholderEngagement]:
        """
        Create multiple StakeholderEngagement rows in one transaction.
        Skips duplicate (contact_id, activity_id) pairs silently.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        results = []
        for rec in records:
            contact_id = uuid.UUID(rec["contact_id"])
            e = StakeholderEngagement(
                contact_id        = contact_id,
                activity_id       = activity_id,
                attendance_status = AttendanceStatus(rec.get("attendance_status", "attended")),
                proxy_name        = rec.get("proxy_name"),
                concerns_raised   = rec.get("concerns_raised"),
                response_given    = rec.get("response_given"),
                notes             = rec.get("notes"),
                logged_by_user_id = logged_by_uid,
            )
            self.db.add(e)
            results.append(e)
        await self.db.flush()
        return results

    # ── Activity Media ────────────────────────────────────────────────────────

    async def create_media(self, media: ActivityMedia) -> ActivityMedia:
        self.db.add(media)
        await self.db.flush()
        await self.db.refresh(media)
        return media

    async def list_media(
        self,
        activity_id:     uuid.UUID,
        media_type:      Optional[str] = None,
        include_deleted: bool          = False,
    ) -> list[ActivityMedia]:
        from sqlalchemy import select
        q = select(ActivityMedia).where(ActivityMedia.activity_id == activity_id)
        if not include_deleted:
            q = q.where(ActivityMedia.deleted_at.is_(None))
        if media_type:
            q = q.where(ActivityMedia.media_type == media_type)
        q = q.order_by(ActivityMedia.media_type, ActivityMedia.uploaded_at)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_media_by_id(
        self, media_id: uuid.UUID, activity_id: Optional[uuid.UUID] = None
    ) -> Optional[ActivityMedia]:
        from sqlalchemy import select
        q = select(ActivityMedia).where(
            ActivityMedia.id == media_id,
            ActivityMedia.deleted_at.is_(None),
        )
        if activity_id:
            q = q.where(ActivityMedia.activity_id == activity_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def soft_delete_media(self, media: ActivityMedia) -> None:
        from datetime import datetime, timezone
        media.deleted_at = datetime.now(timezone.utc)
        self.db.add(media)
