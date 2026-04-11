"""
repositories/stakeholder_repository.py
────────────────────────────────────────────────────────────────────────────
All database operations for Stakeholder, StakeholderContact,
StakeholderProject, and StakeholderEngagement.

No business logic here — pure query construction and DB I/O.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.engagement import StakeholderEngagement
from models.project import ProjectCache
from models.stakeholder import (
    AffectednessType,
    EntityType,
    ImportanceRating,
    PreferredChannel,
    Stakeholder,
    StakeholderCategory,
    StakeholderContact,
    StakeholderProject,
    StakeholderStageEngagement,
    StakeholderType,
)


class StakeholderRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Stakeholder ───────────────────────────────────────────────────────────

    async def create(
        self,
        stakeholder_type:       StakeholderType,
        entity_type:            EntityType,
        category:               StakeholderCategory,
        affectedness:           AffectednessType,
        importance_rating:      ImportanceRating,
        preferred_channel:      PreferredChannel,
        registered_by_user_id:  uuid.UUID,
        org_name:               Optional[str]       = None,
        first_name:             Optional[str]       = None,
        last_name:              Optional[str]       = None,
        org_id:                 Optional[uuid.UUID] = None,
        address_id:             Optional[uuid.UUID] = None,
        lga:                    Optional[str]       = None,
        ward:                   Optional[str]       = None,
        language_preference:    str                 = "sw",
        needs_translation:      bool                = False,
        needs_transport:        bool                = False,
        needs_childcare:        bool                = False,
        is_vulnerable:          bool                = False,
        vulnerable_group_types: Optional[dict]      = None,
        participation_barriers: Optional[dict]      = None,
        notes:                  Optional[str]       = None,
    ) -> Stakeholder:
        s = Stakeholder(
            stakeholder_type       = stakeholder_type,
            entity_type            = entity_type,
            category               = category,
            affectedness           = affectedness,
            importance_rating      = importance_rating,
            preferred_channel      = preferred_channel,
            org_name               = org_name,
            first_name             = first_name,
            last_name              = last_name,
            org_id                 = org_id,
            address_id             = address_id,
            lga                    = lga,
            ward                   = ward,
            language_preference    = language_preference,
            needs_translation      = needs_translation,
            needs_transport        = needs_transport,
            needs_childcare        = needs_childcare,
            is_vulnerable          = is_vulnerable,
            vulnerable_group_types = vulnerable_group_types,
            participation_barriers = participation_barriers,
            notes                  = notes,
            registered_by_user_id  = registered_by_user_id,
        )
        self.db.add(s)
        await self.db.flush()
        await self.db.refresh(s)
        return s

    async def get_by_id(self, stakeholder_id: uuid.UUID) -> Optional[Stakeholder]:
        result = await self.db.execute(
            select(Stakeholder).where(
                Stakeholder.id == stakeholder_id,
                Stakeholder.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_contacts(self, stakeholder_id: uuid.UUID) -> Optional[Stakeholder]:
        result = await self.db.execute(
            select(Stakeholder)
            .options(selectinload(Stakeholder.contacts))
            .where(
                Stakeholder.id == stakeholder_id,
                Stakeholder.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        stakeholder_type: Optional[str]            = None,
        category:         Optional[str]            = None,
        lga:              Optional[str]            = None,
        is_vulnerable:    Optional[bool]           = None,
        project_id:       Optional[uuid.UUID]      = None,
        importance:       Optional[ImportanceRating] = None,
        stage_id:         Optional[uuid.UUID]      = None,
        affectedness:     Optional[str]            = None,
        skip:             int                      = 0,
        limit:            int                      = 50,
    ) -> list[Stakeholder]:
        q = select(Stakeholder).where(Stakeholder.deleted_at.is_(None))

        if stakeholder_type:
            q = q.where(Stakeholder.stakeholder_type == stakeholder_type)
        if category:
            q = q.where(Stakeholder.category == category)
        if lga:
            q = q.where(Stakeholder.lga.ilike(f"%{lga}%"))
        if is_vulnerable is not None:
            q = q.where(Stakeholder.is_vulnerable == is_vulnerable)
        if affectedness:
            q = q.where(Stakeholder.affectedness == affectedness)

        # ── Stage / importance filters require join to StakeholderStageEngagement ──
        if stage_id or importance:
            q = q.join(
                StakeholderStageEngagement,
                StakeholderStageEngagement.stakeholder_id == Stakeholder.id,
            )
            if stage_id:
                q = q.where(StakeholderStageEngagement.stage_id == stage_id)
            if importance:
                q = q.where(StakeholderStageEngagement.importance == importance)

        elif project_id:
            # project_id without stage → join via StakeholderProject
            q = q.join(
                StakeholderProject,
                StakeholderProject.stakeholder_id == Stakeholder.id,
            ).where(StakeholderProject.project_id == project_id)

        if project_id and (stage_id or importance):
            # also filter stage engagements to this project
            q = q.where(StakeholderStageEngagement.project_id == project_id)

        q = q.distinct().offset(skip).limit(limit).order_by(Stakeholder.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # ── Stakeholder Analysis (Annex 3 / SEP format) ───────────────────────────

    async def list_stakeholder_analysis(
        self,
        project_id:   uuid.UUID,
        stage_id:     Optional[uuid.UUID]       = None,
        importance:   Optional[ImportanceRating] = None,
        category:     Optional[str]             = None,
        affectedness: Optional[str]             = None,
        is_vulnerable: Optional[bool]           = None,
        skip:         int                       = 0,
        limit:        int                       = 200,
    ) -> list[dict]:
        """
        Returns the full Annex 3 stakeholder analysis matrix for a project,
        one row per (stakeholder × stage) combination.

        Filters: project_id (required), stage_id, importance, category,
                 affectedness, is_vulnerable.

        Output fields per row:
          stakeholder_id, display_name, category, stakeholder_type,
          affectedness, is_vulnerable, stage_id, stage_name, stage_order,
          importance, importance_justification,
          role_in_stage  (Why Important),
          interests       (Interest),
          potential_risks (Risks),
          preferred_engagement_approach (How to Engage),
          engagement_frequency          (When to Engage),
          permitted_activities
        """
        from models.project import ProjectStageCache

        q = (
            select(Stakeholder, StakeholderStageEngagement, ProjectStageCache)
            .join(
                StakeholderStageEngagement,
                StakeholderStageEngagement.stakeholder_id == Stakeholder.id,
            )
            .join(
                ProjectStageCache,
                ProjectStageCache.id == StakeholderStageEngagement.stage_id,
            )
            .where(
                Stakeholder.deleted_at.is_(None),
                StakeholderStageEngagement.project_id == project_id,
            )
        )

        if stage_id:
            q = q.where(StakeholderStageEngagement.stage_id == stage_id)
        if importance:
            q = q.where(StakeholderStageEngagement.importance == importance)
        if category:
            q = q.where(Stakeholder.category == category)
        if affectedness:
            q = q.where(Stakeholder.affectedness == affectedness)
        if is_vulnerable is not None:
            q = q.where(Stakeholder.is_vulnerable == is_vulnerable)

        q = q.order_by(
            ProjectStageCache.stage_order,
            StakeholderStageEngagement.importance,
            Stakeholder.created_at,
        ).offset(skip).limit(limit)

        result = await self.db.execute(q)
        rows = []
        for stakeholder, sse, stage in result.all():
            rows.append({
                # ── Who ────────────────────────────────────────────────────
                "stakeholder_id":          str(stakeholder.id),
                "display_name":            stakeholder.display_name,
                "category":                stakeholder.category,
                "stakeholder_type":        stakeholder.stakeholder_type,
                "affectedness":            stakeholder.affectedness,
                "lga":                     stakeholder.lga,
                "ward":                    stakeholder.ward,
                "is_vulnerable":           stakeholder.is_vulnerable,
                "vulnerable_group_types":  stakeholder.vulnerable_group_types,
                # ── Stage ──────────────────────────────────────────────────
                "stage_id":                str(stage.id),
                "stage_name":              stage.name,
                "stage_order":             stage.stage_order,
                # ── Annex 3 fields ─────────────────────────────────────────
                "importance":              sse.importance,                    # How important
                "importance_justification":sse.importance_justification,
                "why_important":           sse.engagement_role,               # Why Important  (role_in_stage)
                "interests":               sse.interests,                     # Interest
                "potential_risks":         sse.potential_risks,               # Risks
                "how_to_engage":           sse.engagement_approach,           # How to Engage
                "when_to_engage":          sse.engagement_frequency,          # When to Engage
                "permitted_activities":    sse.allowed_activities,            # JSONB {activities:[...]}
                "notify_on_stage_milestone": sse.notify_on_stage_milestone,
                "preferred_notification_channel": sse.notify_channel,
                "stage_engagement_id":     str(sse.id),
            })
        return rows

    async def update(self, s: Stakeholder, fields: dict) -> Stakeholder:
        """Apply a dict of allowed field values to the stakeholder."""
        for field, value in fields.items():
            setattr(s, field, value)
        self.db.add(s)
        return s

    async def soft_delete(self, s: Stakeholder) -> None:
        s.deleted_at = datetime.now(timezone.utc)
        self.db.add(s)

    # ── Project registration ──────────────────────────────────────────────────

    async def get_project_cache(self, project_id: uuid.UUID) -> Optional[ProjectCache]:
        result = await self.db.execute(
            select(ProjectCache).where(ProjectCache.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_stakeholder_project(
        self, stakeholder_id: uuid.UUID, project_id: uuid.UUID
    ) -> Optional[StakeholderProject]:
        result = await self.db.execute(
            select(StakeholderProject).where(
                StakeholderProject.stakeholder_id == stakeholder_id,
                StakeholderProject.project_id     == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_stakeholder_project(
        self,
        stakeholder_id:        uuid.UUID,
        project_id:            uuid.UUID,
        is_pap:                bool                = False,
        affectedness:          Optional[AffectednessType] = None,
        impact_description:    Optional[str]       = None,
        registered_by_user_id: Optional[uuid.UUID] = None,
    ) -> StakeholderProject:
        sp = StakeholderProject(
            stakeholder_id        = stakeholder_id,
            project_id            = project_id,
            is_pap                = is_pap,
            affectedness          = affectedness,
            impact_description    = impact_description,
            registered_by_user_id = registered_by_user_id,
        )
        self.db.add(sp)
        await self.db.flush()
        await self.db.refresh(sp)
        return sp

    async def list_stakeholder_projects(
        self, stakeholder_id: uuid.UUID
    ) -> list[StakeholderProject]:
        result = await self.db.execute(
            select(StakeholderProject)
            .where(StakeholderProject.stakeholder_id == stakeholder_id)
            .order_by(StakeholderProject.registered_at.desc())
        )
        return list(result.scalars().all())

    async def increment_consultation_count(
        self, stakeholder_id: uuid.UUID, project_id: uuid.UUID
    ) -> None:
        await self.db.execute(
            update(StakeholderProject)
            .where(
                StakeholderProject.stakeholder_id == stakeholder_id,
                StakeholderProject.project_id     == project_id,
            )
            .values(consultation_count=StakeholderProject.consultation_count + 1)
            .execution_options(synchronize_session=False)
        )

    # ── Contacts ──────────────────────────────────────────────────────────────

    async def create_contact(
        self,
        stakeholder_id:               uuid.UUID,
        full_name:                    str,
        preferred_channel:            PreferredChannel,
        user_id:                      Optional[uuid.UUID] = None,
        title:                        Optional[str]       = None,
        role_in_org:                  Optional[str]       = None,
        email:                        Optional[str]       = None,
        phone:                        Optional[str]       = None,
        is_primary:                   bool                = False,
        can_submit_feedback:          bool                = True,
        can_receive_communications:   bool                = True,
        can_distribute_communications: bool               = False,
        notes:                        Optional[str]       = None,
    ) -> StakeholderContact:
        c = StakeholderContact(
            stakeholder_id                = stakeholder_id,
            user_id                       = user_id,
            full_name                     = full_name,
            title                         = title,
            role_in_org                   = role_in_org,
            email                         = email,
            phone                         = phone,
            preferred_channel             = preferred_channel,
            is_primary                    = is_primary,
            can_submit_feedback           = can_submit_feedback,
            can_receive_communications    = can_receive_communications,
            can_distribute_communications = can_distribute_communications,
            notes                         = notes,
        )
        self.db.add(c)
        await self.db.flush()
        await self.db.refresh(c)
        return c

    async def get_contact_by_id(
        self, contact_id: uuid.UUID, stakeholder_id: Optional[uuid.UUID] = None
    ) -> Optional[StakeholderContact]:
        q = select(StakeholderContact).where(StakeholderContact.id == contact_id)
        if stakeholder_id:
            q = q.where(StakeholderContact.stakeholder_id == stakeholder_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_contacts(
        self, stakeholder_id: uuid.UUID, active_only: bool = True
    ) -> list[StakeholderContact]:
        q = select(StakeholderContact).where(
            StakeholderContact.stakeholder_id == stakeholder_id
        )
        if active_only:
            q = q.where(StakeholderContact.is_active.is_(True))
        result = await self.db.execute(
            q.order_by(StakeholderContact.is_primary.desc())
        )
        return list(result.scalars().all())

    async def deactivate_contact(
        self, c: StakeholderContact, reason: Optional[str] = None
    ) -> None:
        c.is_active           = False
        c.deactivated_at      = datetime.now(timezone.utc)
        c.deactivation_reason = reason
        self.db.add(c)

    async def list_contact_ids_for_stakeholder(
        self, stakeholder_id: uuid.UUID
    ) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(StakeholderContact.id).where(
                StakeholderContact.stakeholder_id == stakeholder_id
            )
        )
        return [r[0] for r in result.all()]

    # ── Engagements ───────────────────────────────────────────────────────────

    async def list_engagements_for_contacts(
        self, contact_ids: list[uuid.UUID]
    ) -> list[StakeholderEngagement]:
        if not contact_ids:
            return []
        result = await self.db.execute(
            select(StakeholderEngagement)
            .where(StakeholderEngagement.contact_id.in_(contact_ids))
            .order_by(StakeholderEngagement.created_at.desc())
        )
        return list(result.scalars().all())
