# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  repositories/checklist_repository.py
# ───────────────────────────────────────────────────────────────────────────
"""
repositories/checklist_repository.py
────────────────────────────────────────────────────────────────────────────
All DB operations for ProjectChecklistItem.

entity_type values:
  "project"    → OrgProject.id
  "stage"      → OrgProjectStage.id
  "subproject" → OrgSubProject.id
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from datetime import date

from sqlalchemy import String, case, cast, func, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.org_project import (
    ChecklistItemStatus,
    OrgProject,
    OrgProjectStage,
    OrgSubProject,
    ProjectChecklistItem,
)


class ChecklistRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(self, item: ProjectChecklistItem) -> ProjectChecklistItem:
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        item_id:     uuid.UUID,
        entity_type: Optional[str]       = None,
        entity_id:   Optional[uuid.UUID] = None,
    ) -> Optional[ProjectChecklistItem]:
        q = select(ProjectChecklistItem).where(
            ProjectChecklistItem.id == item_id,
            ProjectChecklistItem.deleted_at.is_(None),
        )
        if entity_type:
            q = q.where(ProjectChecklistItem.entity_type == entity_type)
        if entity_id:
            q = q.where(ProjectChecklistItem.entity_id == entity_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list(
        self,
        entity_type:     str,
        entity_id:       uuid.UUID,
        status:          Optional[str]  = None,
        category:        Optional[str]  = None,
        assigned_to:     Optional[uuid.UUID] = None,
        skip:            int  = 0,
        limit:           int  = 100,
        include_deleted: bool = False,
    ) -> list[ProjectChecklistItem]:
        q = (
            select(ProjectChecklistItem)
            .where(
                ProjectChecklistItem.entity_type == entity_type,
                ProjectChecklistItem.entity_id   == entity_id,
            )
            .order_by(
                ProjectChecklistItem.display_order,
                ProjectChecklistItem.created_at,
            )
        )
        if not include_deleted:
            q = q.where(ProjectChecklistItem.deleted_at.is_(None))
        if status:
            q = q.where(ProjectChecklistItem.status == status)
        if category:
            q = q.where(ProjectChecklistItem.category.ilike(f"%{category}%"))
        if assigned_to:
            q = q.where(ProjectChecklistItem.assigned_to_user_id == assigned_to)
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def count(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
        status:      Optional[str] = None,
    ) -> int:
        q = select(func.count(ProjectChecklistItem.id)).where(
            ProjectChecklistItem.entity_type == entity_type,
            ProjectChecklistItem.entity_id   == entity_id,
            ProjectChecklistItem.deleted_at.is_(None),
        )
        if status:
            q = q.where(ProjectChecklistItem.status == status)
        return await self.db.scalar(q) or 0

    async def status_counts(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> dict[str, int]:
        """
        Return {status_value: count} for all non-deleted items.
        Used to compute the progress summary (e.g. 8/12 done).
        """
        q = (
            select(ProjectChecklistItem.status, func.count(ProjectChecklistItem.id))
            .where(
                ProjectChecklistItem.entity_type == entity_type,
                ProjectChecklistItem.entity_id   == entity_id,
                ProjectChecklistItem.deleted_at.is_(None),
            )
            .group_by(ProjectChecklistItem.status)
        )
        rows = await self.db.execute(q)
        return {str(status): count for status, count in rows.all()}

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(
        self,
        item:   ProjectChecklistItem,
        fields: dict,
    ) -> ProjectChecklistItem:
        _allowed = {
            "title", "description", "category", "status",
            "due_date", "completion_date", "assigned_to_user_id",
            "completion_note", "completion_evidence_url",
            "skip_reason", "display_order", "updated_by_user_id",
        }
        for k, v in fields.items():
            if k in _allowed:
                setattr(item, k, v)
        self.db.add(item)
        return item

    async def bulk_reorder(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
        order:       list[dict],  # [{"id": uuid, "display_order": int}]
    ) -> None:
        """
        Update display_order for multiple items in one go.
        order = [{"id": "uuid-str", "display_order": 0}, ...]
        """
        for entry in order:
            item = await self.get_by_id(
                uuid.UUID(str(entry["id"])), entity_type, entity_id
            )
            if item:
                item.display_order = int(entry["display_order"])
                self.db.add(item)

    # ── Soft delete ───────────────────────────────────────────────────────────

    async def soft_delete(self, item: ProjectChecklistItem) -> None:
        item.deleted_at = datetime.now(timezone.utc)
        self.db.add(item)

    # ── Performance reporting ─────────────────────────────────────────────────

    async def overdue_count(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> int:
        """
        Items that are overdue: due_date < today AND status not in (done, skipped).
        """
        today = date.today()
        q = select(func.count(ProjectChecklistItem.id)).where(
            ProjectChecklistItem.entity_type == entity_type,
            ProjectChecklistItem.entity_id   == entity_id,
            ProjectChecklistItem.deleted_at.is_(None),
            ProjectChecklistItem.due_date < today,
            ProjectChecklistItem.status.notin_(
                [ChecklistItemStatus.DONE, ChecklistItemStatus.SKIPPED]
            ),
        )
        return await self.db.scalar(q) or 0

    async def performance_by_project(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
    ) -> list[dict]:
        """
        Returns one performance row per entity (project + each stage +
        each subproject) for a given project.

        Each row contains:
          entity_type, entity_id, entity_name, entity_status, entity_code,
          project_id, project_name, project_slug, project_status,
          project_region, project_lga, project_country_code,
          stage_id, stage_name, stage_order,
          total, done, in_progress, pending, skipped, blocked,
          overdue, percent_complete
        """
        today = date.today()
        rows = []

        # ── Project-level row ─────────────────────────────────────────────────
        proj = await self.db.get(OrgProject, project_id)
        if not proj:
            return rows

        sc = await self._entity_stats(today, "project", project_id)
        rows.append({
            "entity_type":         "project",
            "entity_id":           str(project_id),
            "entity_name":         proj.name,
            "entity_status":       str(proj.status),
            "entity_code":         proj.code,
            "project_id":          str(project_id),
            "project_name":        proj.name,
            "project_slug":        proj.slug,
            "project_status":      str(proj.status),
            "project_region":      proj.region,
            "project_lga":         proj.primary_lga,
            "project_country_code":proj.country_code,
            "project_location_description": proj.location_description,
            "stage_id":            None,
            "stage_name":          None,
            "stage_order":         None,
            **sc,
        })

        # ── Stage rows ────────────────────────────────────────────────────────
        stages_q = (
            select(OrgProjectStage)
            .where(
                OrgProjectStage.project_id == project_id,
                OrgProjectStage.deleted_at.is_(None) if hasattr(OrgProjectStage, "deleted_at") else text("1=1"),
            )
            .order_by(OrgProjectStage.stage_order)
        )
        stage_rows = list((await self.db.execute(stages_q)).scalars().all())

        for stage in stage_rows:
            sc = await self._entity_stats(today, "stage", stage.id)
            rows.append({
                "entity_type":         "stage",
                "entity_id":           str(stage.id),
                "entity_name":         stage.name,
                "entity_status":       str(stage.status),
                "entity_code":         None,
                "project_id":          str(project_id),
                "project_name":        proj.name,
                "project_slug":        proj.slug,
                "project_status":      str(proj.status),
                "project_region":      proj.region,
                "project_lga":         proj.primary_lga,
                "project_country_code":proj.country_code,
                "project_location_description": proj.location_description,
                "stage_id":            str(stage.id),
                "stage_name":          stage.name,
                "stage_order":         stage.stage_order,
                **sc,
            })

            # ── Sub-project rows (belonging to this stage) ────────────────────
            sp_q = (
                select(OrgSubProject)
                .where(
                    OrgSubProject.stage_id == stage.id,
                    OrgSubProject.deleted_at.is_(None),
                )
                .order_by(OrgSubProject.display_order, OrgSubProject.name)
            )
            subprojects = list((await self.db.execute(sp_q)).scalars().all())

            for sp in subprojects:
                sc = await self._entity_stats(today, "subproject", sp.id)
                rows.append({
                    "entity_type":         "subproject",
                    "entity_id":           str(sp.id),
                    "entity_name":         sp.name,
                    "entity_status":       str(sp.status),
                    "entity_code":         sp.code,
                    "project_id":          str(project_id),
                    "project_name":        proj.name,
                    "project_slug":        proj.slug,
                    "project_status":      str(proj.status),
                    "project_region":      proj.region,
                    "project_lga":         proj.primary_lga,
                    "project_country_code":proj.country_code,
                    "project_location_description": proj.location_description,
                    "stage_id":            str(stage.id),
                    "stage_name":          stage.name,
                    "stage_order":         stage.stage_order,
                    **sc,
                })

        return rows

    async def performance_by_org(
        self,
        org_id: uuid.UUID,
    ) -> list[dict]:
        """
        Returns one summary row per project for an organisation.
        Aggregates all checklist items across all entity levels (project +
        stages + subprojects) into a single row per project.
        """
        today = date.today()

        proj_q = select(OrgProject).where(
            OrgProject.organisation_id == org_id,
            OrgProject.deleted_at.is_(None),
        ).order_by(OrgProject.name)
        projects = list((await self.db.execute(proj_q)).scalars().all())

        rows = []
        for proj in projects:
            # Gather entity_ids for all entities in this project
            entity_ids: list[tuple[str, uuid.UUID]] = [("project", proj.id)]

            stages_q = select(OrgProjectStage.id).where(
                OrgProjectStage.project_id == proj.id
            )
            stage_ids = list((await self.db.execute(stages_q)).scalars().all())
            entity_ids += [("stage", sid) for sid in stage_ids]

            sp_q = select(OrgSubProject.id).where(
                OrgSubProject.project_id == proj.id,
                OrgSubProject.deleted_at.is_(None),
            )
            sp_ids = list((await self.db.execute(sp_q)).scalars().all())
            entity_ids += [("subproject", spid) for spid in sp_ids]

            # Aggregate stats across all entities
            total = done = in_progress = pending = skipped = blocked = overdue = 0
            for et, eid in entity_ids:
                sc = await self._entity_stats(today, et, eid)
                total       += sc["total"]
                done        += sc["done"]
                in_progress += sc["in_progress"]
                pending     += sc["pending"]
                skipped     += sc["skipped"]
                blocked     += sc["blocked"]
                overdue     += sc["overdue"]

            actionable = total - skipped - blocked
            pct = round((done / actionable * 100) if actionable > 0 else 0.0, 1)

            rows.append({
                "project_id":          str(proj.id),
                "project_name":        proj.name,
                "project_slug":        proj.slug,
                "project_status":      str(proj.status),
                "project_code":        proj.code,
                "project_region":      proj.region,
                "project_lga":         proj.primary_lga,
                "project_country_code":proj.country_code,
                "project_location_description": proj.location_description,
                "project_start_date":  proj.start_date.isoformat() if proj.start_date else None,
                "project_end_date":    proj.end_date.isoformat() if proj.end_date else None,
                "total":               total,
                "done":                done,
                "in_progress":         in_progress,
                "pending":             pending,
                "skipped":             skipped,
                "blocked":             blocked,
                "overdue":             overdue,
                "percent_complete":    pct,
            })

        return rows

    async def _entity_stats(
        self,
        today:       "date",
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> dict:
        """Internal: compute checklist counts for one entity."""
        status_map = await self.status_counts(entity_type, entity_id)
        total       = sum(status_map.values())
        done        = status_map.get("done", 0)
        in_progress = status_map.get("in_progress", 0)
        pending     = status_map.get("pending", 0)
        skipped     = status_map.get("skipped", 0)
        blocked     = status_map.get("blocked", 0)
        overdue     = await self.overdue_count(entity_type, entity_id)
        actionable  = total - skipped - blocked
        pct         = round((done / actionable * 100) if actionable > 0 else 0.0, 1)
        return {
            "total":            total,
            "done":             done,
            "in_progress":      in_progress,
            "pending":          pending,
            "skipped":          skipped,
            "blocked":          blocked,
            "overdue":          overdue,
            "percent_complete": pct,
        }
    async def performance_by_stage(
        self,
        stage_id: uuid.UUID,
    ) -> list[dict]:
        """
        One row per entity for a single stage:
          · The stage itself
          · Each sub-project belonging to the stage (any depth)

        Returns parent project context (name, region, lga) on every row.
        """
        today = date.today()

        stage = await self.db.get(OrgProjectStage, stage_id)
        if not stage:
            return []

        # Load parent project for location context
        proj = await self.db.get(OrgProject, stage.project_id)

        rows = []

        # Stage row
        sc = await self._entity_stats(today, "stage", stage_id)
        rows.append({
            "entity_type":         "stage",
            "entity_id":           str(stage.id),
            "entity_name":         stage.name,
            "entity_status":       str(stage.status),
            "entity_code":         None,
            "stage_order":         stage.stage_order,
            "stage_start_date":    stage.start_date.isoformat() if stage.start_date else None,
            "stage_end_date":      stage.end_date.isoformat() if stage.end_date else None,
            "stage_actual_start_date": stage.actual_start_date.isoformat() if stage.actual_start_date else None,
            "stage_actual_end_date":   stage.actual_end_date.isoformat() if stage.actual_end_date else None,
            "stage_objectives":    stage.objectives,
            "stage_deliverables":  stage.deliverables,
            "project_id":          str(stage.project_id),
            "project_name":        proj.name if proj else None,
            "project_slug":        proj.slug if proj else None,
            "project_status":      str(proj.status) if proj else None,
            "project_region":      proj.region if proj else None,
            "project_lga":         proj.primary_lga if proj else None,
            "project_country_code":proj.country_code if proj else None,
            "project_location_description": proj.location_description if proj else None,
            "parent_subproject_id": None,
            **sc,
        })

        # Sub-project rows
        sp_q = (
            select(OrgSubProject)
            .where(
                OrgSubProject.stage_id == stage_id,
                OrgSubProject.deleted_at.is_(None),
            )
            .order_by(OrgSubProject.display_order, OrgSubProject.name)
        )
        subprojects = list((await self.db.execute(sp_q)).scalars().all())

        for sp in subprojects:
            sc = await self._entity_stats(today, "subproject", sp.id)
            rows.append({
                "entity_type":         "subproject",
                "entity_id":           str(sp.id),
                "entity_name":         sp.name,
                "entity_status":       str(sp.status),
                "entity_code":         sp.code,
                "stage_order":         stage.stage_order,
                "stage_start_date":    stage.start_date.isoformat() if stage.start_date else None,
                "stage_end_date":      stage.end_date.isoformat() if stage.end_date else None,
                "stage_actual_start_date": stage.actual_start_date.isoformat() if stage.actual_start_date else None,
                "stage_actual_end_date":   stage.actual_end_date.isoformat() if stage.actual_end_date else None,
                "stage_objectives":    None,
                "stage_deliverables":  None,
                "project_id":          str(stage.project_id),
                "project_name":        proj.name if proj else None,
                "project_slug":        proj.slug if proj else None,
                "project_status":      str(proj.status) if proj else None,
                "project_region":      proj.region if proj else None,
                "project_lga":         proj.primary_lga if proj else None,
                "project_country_code":proj.country_code if proj else None,
                "project_location_description": proj.location_description if proj else None,
                "parent_subproject_id": str(sp.parent_subproject_id) if sp.parent_subproject_id else None,
                "subproject_start_date":       sp.start_date.isoformat() if sp.start_date else None,
                "subproject_end_date":         sp.end_date.isoformat() if sp.end_date else None,
                "subproject_actual_start_date":sp.actual_start_date.isoformat() if sp.actual_start_date else None,
                "subproject_actual_end_date":  sp.actual_end_date.isoformat() if sp.actual_end_date else None,
                "subproject_objectives":       sp.objectives,
                "subproject_expected_outputs": sp.expected_outputs,
                "subproject_budget_amount":    sp.budget_amount,
                "subproject_currency_code":    sp.currency_code,
                **sc,
            })

        return rows

    async def performance_by_subproject(
        self,
        subproject_id: uuid.UUID,
    ) -> dict:
        """
        Single performance row for one sub-project, with full context:
        parent project name/location, stage name/order, and own dates/budget.
        """
        today = date.today()

        sp = await self.db.get(OrgSubProject, subproject_id)
        if not sp:
            return {}

        stage = await self.db.get(OrgProjectStage, sp.stage_id)
        proj  = await self.db.get(OrgProject, sp.project_id)
        sc    = await self._entity_stats(today, "subproject", subproject_id)

        return {
            "entity_type":          "subproject",
            "entity_id":            str(sp.id),
            "entity_name":          sp.name,
            "entity_status":        str(sp.status),
            "entity_code":          sp.code,
            "parent_subproject_id": str(sp.parent_subproject_id) if sp.parent_subproject_id else None,
            "display_order":        sp.display_order,
            # Sub-project timeline & budget
            "subproject_start_date":        sp.start_date.isoformat() if sp.start_date else None,
            "subproject_end_date":          sp.end_date.isoformat() if sp.end_date else None,
            "subproject_actual_start_date": sp.actual_start_date.isoformat() if sp.actual_start_date else None,
            "subproject_actual_end_date":   sp.actual_end_date.isoformat() if sp.actual_end_date else None,
            "subproject_objectives":        sp.objectives,
            "subproject_expected_outputs":  sp.expected_outputs,
            "subproject_budget_amount":     sp.budget_amount,
            "subproject_currency_code":     sp.currency_code,
            # Stage context
            "stage_id":          str(stage.id) if stage else None,
            "stage_name":        stage.name if stage else None,
            "stage_order":       stage.stage_order if stage else None,
            "stage_status":      str(stage.status) if stage else None,
            "stage_start_date":  stage.start_date.isoformat() if stage and stage.start_date else None,
            "stage_end_date":    stage.end_date.isoformat() if stage and stage.end_date else None,
            # Project context
            "project_id":           str(sp.project_id),
            "project_name":         proj.name if proj else None,
            "project_slug":         proj.slug if proj else None,
            "project_status":       str(proj.status) if proj else None,
            "project_region":       proj.region if proj else None,
            "project_lga":          proj.primary_lga if proj else None,
            "project_country_code": proj.country_code if proj else None,
            "project_location_description": proj.location_description if proj else None,
            **sc,
        }