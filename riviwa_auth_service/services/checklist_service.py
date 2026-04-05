# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  services/checklist_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/checklist_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for project / stage / sub-project checklists.

Key behaviours
──────────────
· create_item()     — validates entity_type, coerces due_date/completion_date
                      from ISO strings, enforces title not blank.
· update_item()     — when status → DONE, auto-sets completion_date to today
                      if not provided. When status → SKIPPED or BLOCKED,
                      skip_reason is required.
· mark_done()       — convenience shortcut: status → DONE + optional note.
· bulk_reorder()    — reorders items by updating display_order in one tx.
· progress()        — returns {total, done, in_progress, pending, skipped,
                      blocked, percent_complete} for progress bars.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.org_project import ChecklistEntityType, ChecklistItemStatus, ProjectChecklistItem
from repositories.checklist_repository import ChecklistRepository

_VALID_ENTITY_TYPES = {e.value for e in ChecklistEntityType}
_VALID_STATUSES     = {e.value for e in ChecklistItemStatus}


class ChecklistService:

    def __init__(self, db: AsyncSession) -> None:
        self.db   = db
        self.repo = ChecklistRepository(db)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _validate_entity_type(self, entity_type: str) -> None:
        if entity_type not in _VALID_ENTITY_TYPES:
            raise ValueError(
                f"entity_type must be one of {sorted(_VALID_ENTITY_TYPES)}, "
                f"got '{entity_type}'."
            )

    def _validate_status(self, status: str) -> None:
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_VALID_STATUSES)}, "
                f"got '{status}'."
            )

    @staticmethod
    def _parse_date(value: str | date | None) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            raise ValueError(
                f"Invalid date format: {value!r}. Use ISO 8601 e.g. '2025-06-15'."
            )

    @staticmethod
    def _serialise(item: ProjectChecklistItem) -> dict:
        return {
            "id":                       str(item.id),
            "entity_type":              item.entity_type,
            "entity_id":                str(item.entity_id),
            "title":                    item.title,
            "description":              item.description,
            "category":                 item.category,
            "status":                   item.status,
            "due_date":                 item.due_date.isoformat() if item.due_date else None,
            "completion_date":          item.completion_date.isoformat() if item.completion_date else None,
            "assigned_to_user_id":      str(item.assigned_to_user_id) if item.assigned_to_user_id else None,
            "completion_note":          item.completion_note,
            "completion_evidence_url":  item.completion_evidence_url,
            "skip_reason":              item.skip_reason,
            "display_order":            item.display_order,
            "created_by_user_id":       str(item.created_by_user_id) if item.created_by_user_id else None,
            "updated_by_user_id":       str(item.updated_by_user_id) if item.updated_by_user_id else None,
            "created_at":               item.created_at.isoformat(),
            "updated_at":               item.updated_at.isoformat(),
        }

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_item(
        self,
        entity_type:              str,
        entity_id:                uuid.UUID,
        data:                     dict,
        created_by_user_id:       Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Create a new checklist item attached to a project, stage, or subproject.

        Required fields in data: title
        Optional: description, category, due_date, assigned_to_user_id,
                  display_order
        """
        self._validate_entity_type(entity_type)

        title = (data.get("title") or "").strip()
        if not title:
            raise ValueError("title is required and must not be blank.")

        item = ProjectChecklistItem(
            entity_type             = entity_type,
            entity_id               = entity_id,
            title                   = title,
            description             = data.get("description"),
            category                = data.get("category"),
            status                  = ChecklistItemStatus.PENDING,
            due_date                = self._parse_date(data.get("due_date")),
            assigned_to_user_id     = uuid.UUID(str(data["assigned_to_user_id"])) if data.get("assigned_to_user_id") else None,
            display_order           = int(data.get("display_order", 0)),
            created_by_user_id      = created_by_user_id,
        )

        item = await self.repo.create(item)
        await self.db.commit()
        return self._serialise(item)

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_item(
        self,
        item_id:     uuid.UUID,
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> dict:
        item = await self.repo.get_by_id(item_id, entity_type, entity_id)
        if not item:
            raise ValueError(f"Checklist item {item_id} not found.")
        return self._serialise(item)

    async def list_items(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
        status:      Optional[str]       = None,
        category:    Optional[str]       = None,
        assigned_to: Optional[uuid.UUID] = None,
        skip:        int  = 0,
        limit:       int  = 100,
    ) -> dict:
        """
        Return paginated checklist for the entity plus a full progress summary.
        """
        self._validate_entity_type(entity_type)

        items        = await self.repo.list(
            entity_type, entity_id, status, category, assigned_to, skip, limit
        )
        total        = await self.repo.count(entity_type, entity_id)
        status_map   = await self.repo.status_counts(entity_type, entity_id)

        done_count = status_map.get("done", 0)
        # Exclude skipped from denominator — only count actionable items
        actionable = total - status_map.get("skipped", 0) - status_map.get("blocked", 0)
        pct = round((done_count / actionable * 100) if actionable > 0 else 0, 1)

        return {
            "entity_type":   entity_type,
            "entity_id":     str(entity_id),
            "total":         total,
            "returned":      len(items),
            "progress": {
                "total":            total,
                "done":             status_map.get("done", 0),
                "in_progress":      status_map.get("in_progress", 0),
                "pending":          status_map.get("pending", 0),
                "skipped":          status_map.get("skipped", 0),
                "blocked":          status_map.get("blocked", 0),
                "percent_complete": pct,
            },
            "items": [self._serialise(i) for i in items],
        }

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_item(
        self,
        item_id:            uuid.UUID,
        entity_type:        str,
        entity_id:          uuid.UUID,
        data:               dict,
        updated_by_user_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Update any field on a checklist item.

        Auto-behaviours:
          · status → DONE:    completion_date set to today if not provided.
          · status → SKIPPED or BLOCKED: skip_reason becomes required.
          · title: stripped, must not be blank if provided.
        """
        item = await self.repo.get_by_id(item_id, entity_type, entity_id)
        if not item:
            raise ValueError(f"Checklist item {item_id} not found.")

        clean: dict = {"updated_by_user_id": updated_by_user_id}

        # Title
        if "title" in data and data["title"] is not None:
            t = data["title"].strip()
            if not t:
                raise ValueError("title must not be blank.")
            clean["title"] = t

        # Status transition logic
        if "status" in data and data["status"] is not None:
            new_status = data["status"]
            self._validate_status(new_status)
            clean["status"] = new_status

            if new_status == ChecklistItemStatus.DONE:
                # Auto-set completion_date to today if not provided
                clean["completion_date"] = self._parse_date(
                    data.get("completion_date")
                ) or date.today()

            if new_status in (ChecklistItemStatus.SKIPPED, ChecklistItemStatus.BLOCKED):
                reason = data.get("skip_reason") or item.skip_reason
                if not reason:
                    raise ValueError(
                        f"skip_reason is required when setting status to '{new_status}'."
                    )

        # Remaining fields
        passthrough = {
            "description", "category", "assigned_to_user_id",
            "completion_note", "completion_evidence_url",
            "skip_reason", "display_order",
        }
        for field in passthrough:
            if field in data and data[field] is not None:
                if field == "assigned_to_user_id":
                    clean[field] = uuid.UUID(str(data[field]))
                else:
                    clean[field] = data[field]

        # Date fields
        for date_field in ("due_date", "completion_date"):
            if date_field in data and date_field not in clean:
                clean[date_field] = self._parse_date(data[date_field])

        item = await self.repo.update(item, clean)
        await self.db.commit()
        return self._serialise(item)

    # ── Convenience: mark done ────────────────────────────────────────────────

    async def mark_done(
        self,
        item_id:            uuid.UUID,
        entity_type:        str,
        entity_id:          uuid.UUID,
        completion_note:    Optional[str]      = None,
        evidence_url:       Optional[str]      = None,
        completion_date:    Optional[date]     = None,
        updated_by_user_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Shortcut: set status to DONE with optional note and evidence URL.
        Prevents a double PATCH from the client.
        """
        return await self.update_item(
            item_id=item_id,
            entity_type=entity_type,
            entity_id=entity_id,
            data={
                "status":                   ChecklistItemStatus.DONE,
                "completion_note":          completion_note,
                "completion_evidence_url":  evidence_url,
                "completion_date":          completion_date.isoformat() if completion_date else None,
            },
            updated_by_user_id=updated_by_user_id,
        )

    # ── Reorder ───────────────────────────────────────────────────────────────

    async def reorder(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
        order:       list[dict],  # [{"id": "uuid", "display_order": int}]
    ) -> dict:
        """
        Bulk update display_order for items in one transaction.
        Useful for drag-and-drop reordering in the UI.

        order = [
            {"id": "uuid1", "display_order": 0},
            {"id": "uuid2", "display_order": 1},
            ...
        ]
        """
        self._validate_entity_type(entity_type)
        await self.repo.bulk_reorder(entity_type, entity_id, order)
        await self.db.commit()
        items = await self.repo.list(entity_type, entity_id)
        return {
            "entity_type": entity_type,
            "entity_id":   str(entity_id),
            "items":       [self._serialise(i) for i in items],
        }

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_item(
        self,
        item_id:     uuid.UUID,
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> None:
        item = await self.repo.get_by_id(item_id, entity_type, entity_id)
        if not item:
            raise ValueError(f"Checklist item {item_id} not found.")
        await self.repo.soft_delete(item)
        await self.db.commit()

    # ── Progress (standalone) ─────────────────────────────────────────────────

    async def progress(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> dict:
        """
        Return a lightweight progress summary without the full item list.
        Used for dashboard cards and stage completion gates.
        """
        self._validate_entity_type(entity_type)
        total      = await self.repo.count(entity_type, entity_id)
        status_map = await self.repo.status_counts(entity_type, entity_id)

        done_count = status_map.get("done", 0)
        actionable = total - status_map.get("skipped", 0) - status_map.get("blocked", 0)
        pct = round((done_count / actionable * 100) if actionable > 0 else 0, 1)

        return {
            "entity_type":      entity_type,
            "entity_id":        str(entity_id),
            "total":            total,
            "done":             status_map.get("done", 0),
            "in_progress":      status_map.get("in_progress", 0),
            "pending":          status_map.get("pending", 0),
            "skipped":          status_map.get("skipped", 0),
            "blocked":          status_map.get("blocked", 0),
            "percent_complete": pct,
        }

    # ── Performance reporting ─────────────────────────────────────────────────

    async def performance_report_by_project(
        self,
        org_id:      uuid.UUID,
        project_id:  uuid.UUID,
        entity_type: Optional[str] = None,   # filter to "project"|"stage"|"subproject"
        status_filter: Optional[str] = None, # filter rows by entity_status
    ) -> dict:
        """
        Full performance breakdown for one project.

        Returns one row per entity (project + each stage + each sub-project)
        with checklist stats, location, and overdue count.

        Optionally filter to a specific entity_type or entity_status.
        """
        rows = await self.repo.performance_by_project(org_id, project_id)

        if entity_type:
            rows = [r for r in rows if r["entity_type"] == entity_type]
        if status_filter:
            rows = [r for r in rows if r["entity_status"] == status_filter]

        # Roll up totals across all returned rows for a project-level summary
        total = done = overdue = 0
        for r in rows:
            total   += r["total"]
            done    += r["done"]
            overdue += r["overdue"]

        actionable = sum(
            r["total"] - r["skipped"] - r["blocked"] for r in rows
        )
        overall_pct = round((done / actionable * 100) if actionable > 0 else 0.0, 1)

        return {
            "project_id":       str(project_id),
            "summary": {
                "total_items":       total,
                "done_items":        done,
                "overdue_items":     overdue,
                "percent_complete":  overall_pct,
            },
            "rows": rows,
        }

    async def performance_report_by_org(
        self,
        org_id:        uuid.UUID,
        status_filter: Optional[str] = None,  # filter by project_status
        region:        Optional[str] = None,
        lga:           Optional[str] = None,
    ) -> dict:
        """
        High-level performance view across all projects in an organisation.

        Returns one summary row per project — aggregates all checklists
        (project + stages + subprojects) into a single row.

        Optionally filter by project_status, region, or lga.
        """
        rows = await self.repo.performance_by_org(org_id)

        if status_filter:
            rows = [r for r in rows if r["project_status"] == status_filter]
        if region:
            rows = [r for r in rows
                    if (r.get("project_region") or "").lower() == region.lower()]
        if lga:
            rows = [r for r in rows
                    if (r.get("project_lga") or "").lower() == lga.lower()]

        # Org-wide totals
        total = done = overdue = 0
        for r in rows:
            total   += r["total"]
            done    += r["done"]
            overdue += r["overdue"]

        actionable = sum(
            r["total"] - r["skipped"] - r["blocked"] for r in rows
        )
        overall_pct = round((done / actionable * 100) if actionable > 0 else 0.0, 1)

        return {
            "org_id": str(org_id),
            "summary": {
                "total_projects":     len(rows),
                "total_items":        total,
                "done_items":         done,
                "overdue_items":      overdue,
                "percent_complete":   overall_pct,
            },
            "rows": rows,
        }

    async def performance_report_by_stage(
        self,
        stage_id:      uuid.UUID,
        entity_type:   Optional[str] = None,  # "stage" | "subproject"
        status_filter: Optional[str] = None,
    ) -> dict:
        """
        Performance breakdown for one stage — the stage itself and all
        its sub-projects, each with their own checklist stats.

        Optionally filter to only sub-project rows, or by status.
        """
        rows = await self.repo.performance_by_stage(stage_id)

        if entity_type:
            rows = [r for r in rows if r["entity_type"] == entity_type]
        if status_filter:
            rows = [r for r in rows if r["entity_status"] == status_filter]

        total = done = overdue = 0
        for r in rows:
            total   += r["total"]
            done    += r["done"]
            overdue += r["overdue"]

        actionable = sum(r["total"] - r["skipped"] - r["blocked"] for r in rows)
        pct = round((done / actionable * 100) if actionable > 0 else 0.0, 1)

        # Extract stage context from first row
        stage_ctx = {}
        if rows:
            r0 = rows[0]
            stage_ctx = {
                "stage_name":        r0.get("stage_name") or r0.get("entity_name"),
                "stage_order":       r0.get("stage_order"),
                "stage_start_date":  r0.get("stage_start_date"),
                "stage_end_date":    r0.get("stage_end_date"),
                "project_id":        r0.get("project_id"),
                "project_name":      r0.get("project_name"),
                "project_region":    r0.get("project_region"),
                "project_lga":       r0.get("project_lga"),
            }

        return {
            "stage_id": str(stage_id),
            **stage_ctx,
            "summary": {
                "total_items":      total,
                "done_items":       done,
                "overdue_items":    overdue,
                "percent_complete": pct,
            },
            "rows": rows,
        }

    async def performance_report_by_subproject(
        self,
        subproject_id: uuid.UUID,
    ) -> dict:
        """
        Single performance row for one sub-project with all context
        (stage, project, location, dates, budget, checklist stats).
        """
        row = await self.repo.performance_by_subproject(subproject_id)
        if not row:
            raise ValueError(f"Sub-project {subproject_id} not found.")
        return row
