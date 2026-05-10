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
    AVAILABLE_TEMPLATES,
    SYSTEM_DEFAULT_SLA_OVERRIDES,
    SYSTEM_TEMPLATE_SEEDS,
)
from repositories.escalation_repository import EscalationRepository

log = structlog.get_logger(__name__)


class EscalationService:

    def __init__(self, db: AsyncSession) -> None:
        self.db   = db
        self.repo = EscalationRepository(db)

    # ── System template seeding ───────────────────────────────────────────────

    async def seed_system_template(self) -> None:
        """Backward-compat alias — calls seed_system_templates()."""
        await self.seed_system_templates()

    async def seed_system_templates(self) -> None:
        """
        Idempotent: create all built-in system templates if they don't already exist.
        Called from main.py lifespan startup.
        Checks by template_key so re-runs are safe after adding new templates.
        """
        for tmpl in SYSTEM_TEMPLATE_SEEDS:
            existing = await self.repo.get_system_template_by_key(tmpl["template_key"])
            if existing:
                log.debug("escalation.seed.already_exists", key=tmpl["template_key"], name=existing.name)
                continue

            path = EscalationPath(
                name               = tmpl["name"],
                description        = tmpl["description"],
                template_key       = tmpl["template_key"],
                is_system_template = True,
                is_default         = False,
                is_active          = True,
            )
            await self.repo.create_path(path)

            for lv_data in tmpl["levels"]:
                level = EscalationLevel(
                    path_id                   = path.id,
                    level_order               = lv_data["level_order"],
                    name                      = lv_data["name"],
                    code                      = lv_data["code"],
                    description               = lv_data.get("description"),
                    grm_level_ref             = lv_data.get("grm_level_ref"),
                    is_final                  = lv_data.get("is_final", False),
                    ack_sla_hours             = lv_data.get("ack_sla_hours"),
                    resolution_sla_hours      = lv_data.get("resolution_sla_hours"),
                    auto_escalate_on_breach   = lv_data.get("auto_escalate_on_breach", False),
                    auto_escalate_after_hours = lv_data.get("auto_escalate_after_hours"),
                    sla_overrides             = copy.deepcopy(lv_data.get("sla_overrides")),
                    consumer_visible_name     = lv_data.get("consumer_visible_name"),
                )
                await self.repo.create_level(level)

            await self.db.commit()
            log.info("escalation.seed.created", key=tmpl["template_key"], path_id=str(path.id))

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

    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Return the template catalogue (no DB call required)."""
        return [{"template_key": k, **v} for k, v in AVAILABLE_TEMPLATES.items()]

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
            org_id                     = org_id,
            project_id                 = uuid.UUID(data["project_id"]) if data.get("project_id") else None,
            name                       = data["name"],
            description                = data.get("description"),
            is_default                 = data.get("is_default", False),
            is_active                  = True,
            is_system_template         = False,
            applies_to_feedback_types  = data.get("applies_to_feedback_types"),
            created_by_user_id         = created_by,
        )
        await self.repo.create_path(path)

        for lv in data.get("levels", []):
            await self._create_level_for_path(path.id, lv)

        await self.db.commit()
        return await self.repo.get_path_with_levels(path.id)

    async def quick_setup(
        self,
        org_id: uuid.UUID,
        data: Dict[str, Any],
        created_by: uuid.UUID,
    ) -> EscalationPath:
        """
        Create a complete org escalation path from a built-in template in one call.

        Steps:
          1. Validate the template_key against AVAILABLE_TEMPLATES.
          2. Find the system template DB record with that key.
          3. Clone all its levels.
          4. Apply per-level customizations from data["level_customizations"].
          5. Set applies_to_feedback_types and is_default.
        """
        template_key = data["template_key"]
        if template_key not in AVAILABLE_TEMPLATES:
            raise ValidationError(
                f"Unknown template_key '{template_key}'. "
                f"Valid options: {', '.join(AVAILABLE_TEMPLATES.keys())}"
            )

        source = await self.repo.get_system_template_by_key(template_key)
        if not source:
            raise ValidationError(
                f"System template '{template_key}' has not been seeded yet. "
                "Please restart the service to seed templates."
            )

        if data.get("set_as_default", True):
            await self.repo.clear_org_default(org_id)

        path = EscalationPath(
            org_id                    = org_id,
            name                      = data["name"],
            description               = source.description,
            template_key              = template_key,
            is_default                = data.get("set_as_default", True),
            is_active                 = True,
            is_system_template        = False,
            applies_to_feedback_types = data.get("applies_to_feedback_types"),
            created_by_user_id        = created_by,
        )
        await self.repo.create_path(path)

        # Build customization lookup by level_order
        customizations: Dict[int, Dict[str, Any]] = {}
        for c in (data.get("level_customizations") or []):
            customizations[c["level_order"]] = c

        for src_level in source.sorted_levels():
            cust = customizations.get(src_level.level_order, {})
            level = EscalationLevel(
                path_id                   = path.id,
                level_order               = src_level.level_order,
                name                      = cust.get("name") or src_level.name,
                code                      = src_level.code,
                description               = cust.get("description") or src_level.description,
                consumer_visible_name     = cust.get("consumer_visible_name") or src_level.consumer_visible_name,
                grm_level_ref             = src_level.grm_level_ref,
                is_final                  = cust.get("is_final") if cust.get("is_final") is not None else src_level.is_final,
                ack_sla_hours             = cust.get("ack_sla_hours") or src_level.ack_sla_hours,
                resolution_sla_hours      = cust.get("resolution_sla_hours") or src_level.resolution_sla_hours,
                sla_overrides             = copy.deepcopy(src_level.sla_overrides),
                auto_escalate_on_breach   = cust.get("auto_escalate_on_breach") if cust.get("auto_escalate_on_breach") is not None else src_level.auto_escalate_on_breach,
                auto_escalate_after_hours = cust.get("auto_escalate_after_hours") if cust.get("auto_escalate_after_hours") is not None else src_level.auto_escalate_after_hours,
                responsible_role          = src_level.responsible_role,
                notify_emails             = copy.deepcopy(cust.get("notify_emails") or src_level.notify_emails),
                responsible_org_unit      = cust.get("responsible_org_unit"),
            )
            await self.repo.create_level(level)

        await self.db.commit()
        log.info(
            "escalation.quick_setup.created",
            template_key=template_key, path_id=str(path.id), org_id=str(org_id),
        )
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
