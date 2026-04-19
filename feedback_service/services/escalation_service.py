# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service  |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  services/escalation_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/escalation_service.py
═══════════════════════════════════════════════════════════════════════════════
Business logic for managing dynamic GRM escalation hierarchies.

Responsibilities:
  · CRUD for EscalationPath and EscalationLevel
  · Clone-from-template (organisations copy a system template and customise it)
  · Resolve the correct path for a project/org at feedback submission time
  · Provide SLA hours for a given level + priority
  · Seed the system default template (called on startup)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import copy
import uuid
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ValidationError
from models.escalation import (
    EscalationLevel,
    EscalationPath,
    SYSTEM_DEFAULT_SLA_OVERRIDES,
    SYSTEM_TEMPLATE_SEED,
)
from repositories.escalation_repository import EscalationRepository

log = structlog.get_logger(__name__)


class EscalationService:

    def __init__(self, db: AsyncSession) -> None:
        self.db   = db
        self.repo = EscalationRepository(db)

    # ── System template seeding ───────────────────────────────────────────────

    async def seed_system_template(self) -> None:
        """
        Idempotent: create the TARURA/TANROADS system template if it doesn't exist.
        Called from main.py lifespan startup.
        """
        existing = await self.repo.get_system_template()
        if existing:
            log.debug("escalation.seed.already_exists", name=existing.name)
            return

        path = EscalationPath(
            name=SYSTEM_TEMPLATE_SEED["name"],
            description=SYSTEM_TEMPLATE_SEED["description"],
            is_system_template=True,
            is_default=False,
            is_active=True,
        )
        await self.repo.create_path(path)

        for lv_data in SYSTEM_TEMPLATE_SEED["levels"]:
            level = EscalationLevel(
                path_id               = path.id,
                level_order           = lv_data["level_order"],
                name                  = lv_data["name"],
                code                  = lv_data["code"],
                description           = lv_data.get("description"),
                grm_level_ref         = lv_data.get("grm_level_ref"),
                is_final              = lv_data.get("is_final", False),
                auto_escalate_on_breach = lv_data.get("auto_escalate_on_breach", False),
                sla_overrides         = copy.deepcopy(lv_data.get("sla_overrides")),
            )
            await self.repo.create_level(level)

        await self.db.commit()
        log.info("escalation.seed.created", template=path.name, path_id=str(path.id))

    # ── Path resolution ───────────────────────────────────────────────────────

    async def get_path_for_org_project(
        self,
        org_id: uuid.UUID,
        project_escalation_path_id: Optional[uuid.UUID],
    ) -> Optional[EscalationPath]:
        """
        Resolve the correct escalation path for a feedback submission.

        Priority:
          1. project.escalation_path_id  (project-specific override)
          2. org default path             (is_default=True, org_id=org_id)
          3. system template              (is_system_template=True)
        """
        return await self.repo.resolve_path_for_project(
            project_id=uuid.uuid4(),  # not used in lookup
            org_id=org_id,
            explicit_path_id=project_escalation_path_id,
        )

    # ── Path CRUD ─────────────────────────────────────────────────────────────

    async def list_paths(self, org_id: uuid.UUID) -> List[EscalationPath]:
        return await self.repo.list_paths_for_org(org_id)

    async def list_system_templates(self) -> List[EscalationPath]:
        return await self.repo.list_system_templates()

    async def get_path_or_404(self, path_id: uuid.UUID) -> EscalationPath:
        path = await self.repo.get_path_with_levels(path_id)
        if not path:
            raise NotFoundError(f"Escalation path {path_id} not found.")
        return path

    async def create_path(
        self,
        org_id: uuid.UUID,
        data: Dict[str, Any],
        created_by: uuid.UUID,
    ) -> EscalationPath:
        if data.get("is_default"):
            await self.repo.clear_org_default(org_id)

        path = EscalationPath(
            org_id             = org_id,
            project_id         = uuid.UUID(data["project_id"]) if data.get("project_id") else None,
            name               = data["name"],
            description        = data.get("description"),
            is_default         = data.get("is_default", False),
            is_active          = True,
            is_system_template = False,
            created_by_user_id = created_by,
        )
        await self.repo.create_path(path)

        # Create levels if provided inline
        for lv in data.get("levels", []):
            await self._create_level_for_path(path.id, lv)

        await self.db.commit()
        return await self.repo.get_path_with_levels(path.id)

    async def clone_from_template(
        self,
        template_id: uuid.UUID,
        org_id: uuid.UUID,
        name: str,
        created_by: uuid.UUID,
        set_as_default: bool = False,
    ) -> EscalationPath:
        """
        Clone a system template (or any other path) into a new editable path
        for the given org. All levels are deep-copied and fully editable.
        """
        source = await self.repo.get_path_with_levels(template_id)
        if not source:
            raise NotFoundError(f"Template path {template_id} not found.")

        if set_as_default:
            await self.repo.clear_org_default(org_id)

        new_path = EscalationPath(
            org_id             = org_id,
            name               = name,
            description        = source.description,
            is_default         = set_as_default,
            is_active          = True,
            is_system_template = False,
            created_by_user_id = created_by,
        )
        await self.repo.create_path(new_path)

        for src_level in source.sorted_levels():
            level = EscalationLevel(
                path_id                = new_path.id,
                level_order            = src_level.level_order,
                name                   = src_level.name,
                code                   = src_level.code,
                description            = src_level.description,
                grm_level_ref          = src_level.grm_level_ref,
                is_final               = src_level.is_final,
                ack_sla_hours          = src_level.ack_sla_hours,
                resolution_sla_hours   = src_level.resolution_sla_hours,
                sla_overrides          = copy.deepcopy(src_level.sla_overrides),
                auto_escalate_on_breach   = src_level.auto_escalate_on_breach,
                auto_escalate_after_hours = src_level.auto_escalate_after_hours,
                responsible_role       = src_level.responsible_role,
                notify_emails          = copy.deepcopy(src_level.notify_emails),
            )
            await self.repo.create_level(level)

        await self.db.commit()
        log.info("escalation.path.cloned",
                 source_id=str(template_id), new_path_id=str(new_path.id), org_id=str(org_id))
        return await self.repo.get_path_with_levels(new_path.id)

    async def update_path(
        self,
        path_id: uuid.UUID,
        data: Dict[str, Any],
        org_id: uuid.UUID,
    ) -> EscalationPath:
        path = await self.get_path_or_404(path_id)
        if path.is_system_template:
            raise ValidationError("System templates cannot be modified. Clone first.")
        if path.org_id != org_id:
            raise ValidationError("Path does not belong to this organisation.")

        if data.get("is_default") and not path.is_default:
            await self.repo.clear_org_default(org_id, exclude_id=path_id)

        for field in ("name", "description", "is_default", "is_active"):
            if field in data:
                setattr(path, field, data[field])

        await self.repo.save_path(path)
        await self.db.commit()
        return await self.repo.get_path_with_levels(path_id)

    async def delete_path(self, path_id: uuid.UUID, org_id: uuid.UUID) -> None:
        path = await self.get_path_or_404(path_id)
        if path.is_system_template:
            raise ValidationError("System templates cannot be deleted.")
        if path.org_id != org_id:
            raise ValidationError("Path does not belong to this organisation.")
        path.is_active = False
        await self.repo.save_path(path)
        await self.db.commit()

    # ── Level CRUD ────────────────────────────────────────────────────────────

    async def add_level(
        self,
        path_id: uuid.UUID,
        data: Dict[str, Any],
        org_id: uuid.UUID,
    ) -> EscalationLevel:
        path = await self.get_path_or_404(path_id)
        if path.is_system_template:
            raise ValidationError("System templates cannot be modified. Clone first.")
        if path.org_id != org_id:
            raise ValidationError("Path does not belong to this organisation.")

        level = await self._create_level_for_path(path_id, data)
        await self.db.commit()
        return level

    async def update_level(
        self,
        path_id: uuid.UUID,
        level_id: uuid.UUID,
        data: Dict[str, Any],
        org_id: uuid.UUID,
    ) -> EscalationLevel:
        path = await self.get_path_or_404(path_id)
        if path.is_system_template:
            raise ValidationError("System templates cannot be modified. Clone first.")
        if path.org_id != org_id:
            raise ValidationError("Path does not belong to this organisation.")

        level = await self.repo.get_level(level_id)
        if not level or level.path_id != path_id:
            raise NotFoundError(f"Level {level_id} not found in path {path_id}.")

        updatable = {
            "name", "description", "is_final",
            "ack_sla_hours", "resolution_sla_hours", "sla_overrides",
            "auto_escalate_on_breach", "auto_escalate_after_hours",
            "responsible_role", "notify_emails", "grm_level_ref",
        }
        for field in updatable:
            if field in data:
                setattr(level, field, data[field])

        await self.repo.save_level(level)
        await self.db.commit()
        return level

    async def remove_level(
        self,
        path_id: uuid.UUID,
        level_id: uuid.UUID,
        org_id: uuid.UUID,
    ) -> None:
        path = await self.get_path_or_404(path_id)
        if path.is_system_template:
            raise ValidationError("System templates cannot be modified. Clone first.")
        if path.org_id != org_id:
            raise ValidationError("Path does not belong to this organisation.")

        level = await self.repo.get_level(level_id)
        if not level or level.path_id != path_id:
            raise NotFoundError(f"Level {level_id} not found in path {path_id}.")

        await self.repo.delete_level(level)
        await self.db.commit()

    async def reorder_levels(
        self,
        path_id: uuid.UUID,
        ordered_level_ids: List[uuid.UUID],
        org_id: uuid.UUID,
    ) -> EscalationPath:
        path = await self.get_path_or_404(path_id)
        if path.is_system_template:
            raise ValidationError("System templates cannot be modified. Clone first.")
        if path.org_id != org_id:
            raise ValidationError("Path does not belong to this organisation.")

        await self.repo.reorder_levels(path_id, ordered_level_ids)
        await self.db.commit()
        return await self.repo.get_path_with_levels(path_id)

    # ── SLA resolution ────────────────────────────────────────────────────────

    def get_sla_for_level(
        self,
        level: EscalationLevel,
        priority: str,
    ) -> tuple[Optional[int], Optional[int]]:
        """
        Return (ack_hours, resolution_hours) for a level + priority combination.

        Falls back to SYSTEM_DEFAULT_SLA_OVERRIDES if the level has no config.
        """
        ack, res = level.get_sla_hours(priority)
        if ack is None and res is None:
            # Fall back to system defaults
            pkey = (priority or "medium").lower()
            defaults = SYSTEM_DEFAULT_SLA_OVERRIDES.get(pkey, {})
            ack = defaults.get("ack_hours")
            res = defaults.get("resolution_hours")
        return ack, res

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _create_level_for_path(
        self,
        path_id: uuid.UUID,
        data: Dict[str, Any],
    ) -> EscalationLevel:
        level = EscalationLevel(
            path_id                   = path_id,
            level_order               = data["level_order"],
            name                      = data["name"],
            code                      = data["code"],
            description               = data.get("description"),
            grm_level_ref             = data.get("grm_level_ref"),
            is_final                  = data.get("is_final", False),
            ack_sla_hours             = data.get("ack_sla_hours"),
            resolution_sla_hours      = data.get("resolution_sla_hours"),
            sla_overrides             = data.get("sla_overrides"),
            auto_escalate_on_breach   = data.get("auto_escalate_on_breach", False),
            auto_escalate_after_hours = data.get("auto_escalate_after_hours"),
            responsible_role          = data.get("responsible_role"),
            notify_emails             = data.get("notify_emails"),
        )
        await self.repo.create_level(level)
        return level
