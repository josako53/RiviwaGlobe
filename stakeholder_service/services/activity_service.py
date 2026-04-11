"""
services/activity_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for engagement activities and attendance logging.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ActivityNotFoundError, ContactNotFoundError, ProjectNotFoundError
from events.producer import StakeholderProducer
from models.engagement import (
    ActivityStatus,
    ActivityType,
    AttendanceStatus,
    EngagementActivity,
    EngagementStage,
    StakeholderEngagement,
)
from repositories.activity_repository import ActivityRepository
from repositories.stakeholder_repository import StakeholderRepository


class ActivityService:

    def __init__(self, db: AsyncSession, producer: StakeholderProducer) -> None:
        self.repo     = ActivityRepository(db)
        self.stk_repo = StakeholderRepository(db)
        self.producer = producer
        self.db       = db

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(self, data: dict, conducted_by: uuid.UUID) -> EngagementActivity:
        project_id = uuid.UUID(data["project_id"])
        if not await self.stk_repo.get_project_cache(project_id):
            raise ProjectNotFoundError()

        a = await self.repo.create(
            project_id           = project_id,
            stage                = EngagementStage(data["stage"]),
            activity_type        = ActivityType(data["activity_type"]),
            title                = data["title"],
            conducted_by_user_id = conducted_by,
            description          = data.get("description"),
            agenda               = data.get("agenda"),
            venue                = data.get("venue"),
            lga                  = data.get("lga"),
            ward                 = data.get("ward"),
            gps_lat              = data.get("gps_lat"),
            gps_lng              = data.get("gps_lng"),
            virtual_platform     = data.get("virtual_platform"),
            virtual_url          = data.get("virtual_url"),
            virtual_meeting_id   = data.get("virtual_meeting_id"),
            scheduled_at         = datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None,
            expected_count       = data.get("expected_count"),
            languages_used       = data.get("languages_used"),
            # Previously missing fields — now passed through
            stage_id             = uuid.UUID(data["stage_id"]) if data.get("stage_id") else None,
            subproject_id        = uuid.UUID(data["subproject_id"]) if data.get("subproject_id") else None,
            duration_hours       = data.get("duration_hours"),
            female_count         = data.get("female_count"),
            vulnerable_count     = data.get("vulnerable_count"),
        )
        await self.db.commit()
        await self.db.refresh(a)
        return a

    # ── Fetch ─────────────────────────────────────────────────────────────────

    async def get_or_404(self, activity_id: uuid.UUID) -> EngagementActivity:
        a = await self.repo.get_by_id(activity_id)
        if not a:
            raise ActivityNotFoundError()
        return a

    async def get_with_attendances_or_404(
        self, activity_id: uuid.UUID
    ) -> EngagementActivity:
        a = await self.repo.get_by_id_with_attendances(activity_id)
        if not a:
            raise ActivityNotFoundError()
        return a

    async def list(
        self,
        project_id: Optional[uuid.UUID] = None,
        stage:      Optional[str]       = None,
        status:     Optional[str]       = None,
        lga:        Optional[str]       = None,
        skip:       int                 = 0,
        limit:      int                 = 50,
    ) -> list[EngagementActivity]:
        return await self.repo.list(
            project_id=project_id, stage=stage,
            status=status, lga=lga,
            skip=skip, limit=limit,
        )

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(self, activity_id: uuid.UUID, data: dict) -> EngagementActivity:
        a = await self.get_or_404(activity_id)
        allowed = {
            "title", "description", "agenda", "venue", "lga", "ward",
            "virtual_platform", "virtual_url", "virtual_meeting_id",
            "scheduled_at", "expected_count", "languages_used", "minutes_url",
            "photos_urls", "summary_of_issues", "summary_of_responses",
            "action_items", "actual_count", "female_count", "vulnerable_count",
            "cancelled_reason", "duration_hours",
            # stage_id and subproject_id can be updated before activity is conducted
            "stage_id", "subproject_id",
        }
        for field, value in data.items():
            if field in allowed and value is not None:
                if field == "scheduled_at":
                    value = datetime.fromisoformat(value)
                setattr(a, field, value)

        if new_status := data.get("status"):
            a.status = ActivityStatus(new_status)
            if a.status == ActivityStatus.CONDUCTED and not a.conducted_at:
                from datetime import timezone
                a.conducted_at = datetime.now(timezone.utc)
                await self._increment_consultation_counts(a)
                await self.producer.activity_conducted(
                    a.id, a.project_id, a.stage.value, a.actual_count
                )

        await self.repo.save(a)
        await self.db.commit()
        await self.db.refresh(a)
        return a

    async def _increment_consultation_counts(self, a: EngagementActivity) -> None:
        """Increment consultation_count on StakeholderProject for every attendee."""
        engagements = await self.repo.list_engagements_for_activity(a.id)
        for eng in engagements:
            contact = await self.stk_repo.get_contact_by_id(eng.contact_id)
            if contact:
                await self.stk_repo.increment_consultation_count(
                    contact.stakeholder_id, a.project_id
                )

    # ── Attendance ────────────────────────────────────────────────────────────

    async def log_attendance(
        self, activity_id: uuid.UUID, data: dict, logged_by: uuid.UUID
    ) -> StakeholderEngagement:
        a          = await self.get_or_404(activity_id)
        contact_id = uuid.UUID(data["contact_id"])
        contact    = await self.stk_repo.get_contact_by_id(contact_id)
        if not contact:
            raise ContactNotFoundError()

        e = await self.repo.create_engagement(
            contact_id        = contact_id,
            activity_id       = activity_id,
            logged_by_user_id = logged_by,
            attendance_status = AttendanceStatus(data.get("attendance_status", "attended")),
            proxy_name        = data.get("proxy_name"),
            concerns_raised   = data.get("concerns_raised"),
            response_given    = data.get("response_given"),
            notes             = data.get("notes"),
        )
        await self.db.commit()

        if e.concerns_raised:
            await self.producer.concern_raised(
                activity_id    = activity_id,
                contact_id     = contact_id,
                stakeholder_id = contact.stakeholder_id,
                project_id     = a.project_id,
                concerns       = e.concerns_raised,
            )
        return e

    async def update_attendance(
        self, activity_id: uuid.UUID, engagement_id: uuid.UUID, data: dict
    ) -> StakeholderEngagement:
        e = await self.repo.get_engagement_by_id(engagement_id, activity_id)
        if not e:
            raise ActivityNotFoundError()

        old_concerns = e.concerns_raised
        for field in ("concerns_raised", "response_given", "notes", "attendance_status", "proxy_name"):
            if field in data and data[field] is not None:
                setattr(e, field, data[field])

        await self.repo.save_engagement(e)
        await self.db.commit()

        if e.concerns_raised and not old_concerns:
            contact = await self.stk_repo.get_contact_by_id(e.contact_id)
            activity = await self.get_or_404(activity_id)
            if contact:
                await self.producer.concern_raised(
                    activity_id, e.contact_id,
                    contact.stakeholder_id, activity.project_id,
                    e.concerns_raised,
                )
        return e

    async def delete_attendance(
        self, activity_id: uuid.UUID, engagement_id: uuid.UUID
    ) -> None:
        """Hard delete an attendance record."""
        deleted = await self.repo.delete_engagement(engagement_id, activity_id)
        if not deleted:
            raise ActivityNotFoundError()
        await self.db.commit()

    async def bulk_log_attendance(
        self, activity_id: uuid.UUID, records: list[dict], logged_by: uuid.UUID
    ) -> list[StakeholderEngagement]:
        """
        Log attendance for multiple contacts in one request.
        Validates all contact_ids exist before inserting.
        Publishes concern_raised events for any concerns captured.
        """
        await self.get_or_404(activity_id)

        # Validate all contact_ids up front
        for rec in records:
            contact = await self.stk_repo.get_contact_by_id(uuid.UUID(rec["contact_id"]))
            if not contact:
                raise ContactNotFoundError()

        engagements = await self.repo.bulk_create_engagements(activity_id, records, logged_by)
        await self.db.commit()

        # Publish concern events
        activity = await self.get_or_404(activity_id)
        for eng in engagements:
            if eng.concerns_raised:
                contact = await self.stk_repo.get_contact_by_id(eng.contact_id)
                if contact:
                    await self.producer.concern_raised(
                        activity_id, eng.contact_id,
                        contact.stakeholder_id, activity.project_id,
                        eng.concerns_raised,
                    )
        return engagements

    async def cancel(self, activity_id: uuid.UUID, reason: Optional[str] = None) -> EngagementActivity:
        """Mark activity as CANCELLED."""
        a = await self.get_or_404(activity_id)
        if a.status == ActivityStatus.CONDUCTED:
            raise ValueError("A conducted activity cannot be cancelled.")
        a.status = ActivityStatus.CANCELLED
        if reason:
            a.cancelled_reason = reason
        await self.repo.save(a)
        await self.db.commit()
        return a

    # ── Media ─────────────────────────────────────────────────────────────────

    async def upload_media(
        self,
        activity_id:         uuid.UUID,
        file,                            # FastAPI UploadFile
        title:               str,
        media_type:          str,
        description:         Optional[str]       = None,
        uploaded_by_user_id: Optional[uuid.UUID] = None,
        settings=None,
    ) -> "ActivityMedia":
        """
        Upload a file (photo, PDF minutes, presentation, document) and
        attach it to an engagement activity.

        Stores the file in MinIO at:
          activities/{activity_id}/media/{media_id}.{ext}

        Returns the ActivityMedia row.
        """
        from models.engagement import ActivityMedia, MediaType
        from services.image_service import ImageService, ImageUploadError

        await self.get_or_404(activity_id)

        # Validate media_type
        valid_types = {e.value for e in MediaType}
        if media_type not in valid_types:
            raise ValueError(f"media_type must be one of {sorted(valid_types)}, got '{media_type}'.")

        # Determine storage slot label
        slot_map = {
            "minutes":      "minutes",
            "photo":        "photo",
            "presentation": "presentation",
            "document":     "document",
            "other":        "file",
        }
        slot = slot_map.get(media_type, "file")

        # Store file — ImageService validates MIME type and size
        image_svc = ImageService(settings)
        media_id  = __import__("uuid").uuid4()

        # Override allowed types for documents (ImageService defaults to image only)
        # We patch settings for PDF/DOCX uploads
        import types
        doc_settings = types.SimpleNamespace(
            **{k: getattr(settings, k) for k in dir(settings) if not k.startswith('_') and not callable(getattr(settings, k))}
        )
        if media_type in ("minutes", "presentation", "document", "other"):
            doc_settings.IMAGE_ALLOWED_TYPES = (
                "application/pdf,application/vnd.ms-powerpoint,"
                "application/vnd.openxmlformats-officedocument.presentationml.presentation,"
                "application/msword,"
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
                "application/vnd.ms-excel,"
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
                "image/jpeg,image/png,image/webp"
            )

        svc_inst = ImageService(doc_settings)
        try:
            file_url = await svc_inst.upload(
                file=file,
                entity_type=f"activities/{activity_id}/media",
                entity_id=media_id,
                slot=slot,
            )
        except ImageUploadError:
            raise

        # Capture file metadata from the UploadFile
        file_name  = getattr(file, "filename", None)
        mime_type  = getattr(file, "content_type", None)

        media = ActivityMedia(
            id                  = media_id,
            activity_id         = activity_id,
            media_type          = MediaType(media_type),
            file_url            = file_url,
            file_name           = file_name,
            mime_type           = mime_type,
            title               = title.strip(),
            description         = description,
            uploaded_by_user_id = uploaded_by_user_id,
        )
        media = await self.repo.create_media(media)
        await self.db.commit()
        return media

    async def list_media(
        self,
        activity_id: uuid.UUID,
        media_type:  Optional[str] = None,
    ) -> list["ActivityMedia"]:
        return await self.repo.list_media(activity_id, media_type)

    async def delete_media(
        self,
        activity_id: uuid.UUID,
        media_id:    uuid.UUID,
    ) -> None:
        """Soft-delete the media record. File in object storage is never deleted."""
        media = await self.repo.get_media_by_id(media_id, activity_id)
        if not media:
            raise ActivityNotFoundError()
        await self.repo.soft_delete_media(media)
        await self.db.commit()
