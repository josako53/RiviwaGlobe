# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  services/project_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/project_service.py
═══════════════════════════════════════════════════════════════════════════════
Business logic for the OrgProject execution hierarchy.

Layer responsibilities
───────────────────────
  1. Validate business rules (no DB calls where possible — use the
     repository for existence checks).
  2. Delegate DB mutations to ProjectRepository (flush only).
  3. Commit via the injected AsyncSession.
  4. Publish Kafka lifecycle events via the optional EventPublisher.

Business rules enforced here
──────────────────────────────
  Projects
    · Slug must be globally unique across all OrgProject rows.
    · Code (if provided) must be unique within the organisation.
    · Project must belong to the requesting organisation.
    · Only PLANNING projects can be activated (PLANNING → ACTIVE).
    · Only ACTIVE projects can be paused (ACTIVE → PAUSED).
    · Only PAUSED projects can be resumed (PAUSED → ACTIVE).
    · Only ACTIVE or PAUSED projects can be marked completed.

  Stages
    · stage_order must be unique within a project.
    · Only one stage can be ACTIVE at a time per project.
    · Stages can only be activated/completed in order
      (stage N cannot be activated while stage N-1 is still PENDING).
    · Completing a stage does NOT auto-activate the next — the user does
      that explicitly so they can review deliverables first.

  In-charges
    · UNIQUE (project_id, user_id, role_title) — duplicate role raises ConflictError.
    · A user can hold multiple distinct roles on the same project/stage/subproject.
    · Relieving re-assigns relieved_at, does not delete the row.

  Sub-projects
    · parent_subproject_id must belong to the same stage if provided.
    · Slug is not required on sub-projects (only OrgProject requires it).
    · Soft-delete cascades to in-charges (set relieved_at) but NOT to children
      (children become orphaned top-level sub-projects per the SET NULL FK).

  Kafka publishing
    · All status changes publish events synchronously after commit.
    · Project and stage ACTIVATED events are the most critical — downstream
      services use them to sync ProjectCache and ProjectStageCache.
    · publisher is optional (None in seed/test contexts).
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    ConflictError,
    NotFoundError,
    OrgNotFoundError,
    ValidationError,
)
from models.org_project import (
    OrgProject,
    OrgProjectInCharge,
    OrgProjectStage,
    OrgProjectStageInCharge,
    OrgSubProject,
    OrgSubProjectInCharge,
    ProjectStatus,
    StageStatus,
    SubProjectStatus,
)
from models.organisation import Organisation, OrgStatus
from repositories.organisation_repository import OrganisationRepository
from repositories.project_repository import ProjectRepository

log = structlog.get_logger(__name__)


class ProjectService:

    def __init__(
        self,
        db:        AsyncSession,
        publisher: object | None = None,
    ) -> None:
        self.db        = db
        self.repo      = ProjectRepository(db)
        self.org_repo  = OrganisationRepository(db)
        self.publisher = publisher

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_org_or_404(self, org_id: uuid.UUID) -> Organisation:
        org = await self.org_repo.get_by_id(org_id)
        if not org or org.status not in (OrgStatus.ACTIVE, OrgStatus.VERIFIED):
            raise OrgNotFoundError()
        return org

    async def _get_project_or_404(
        self,
        project_id: uuid.UUID,
        org_id:     uuid.UUID,
        *,
        load_relations: bool = False,
    ) -> OrgProject:
        project = await self.repo.get_project(
            project_id, org_id, load_relations=load_relations
        )
        if not project:
            raise NotFoundError(
                message="Project not found or does not belong to this organisation."
            )
        return project

    async def _get_stage_or_404(
        self,
        stage_id:   uuid.UUID,
        project_id: uuid.UUID,
        *,
        load_relations: bool = False,
    ) -> OrgProjectStage:
        stage = await self.repo.get_stage(
            stage_id, project_id, load_relations=load_relations
        )
        if not stage:
            raise NotFoundError(message="Stage not found.")
        return stage

    async def _get_subproject_or_404(
        self,
        subproject_id: uuid.UUID,
        project_id:    uuid.UUID,
        *,
        load_relations: bool = False,
    ) -> OrgSubProject:
        sp = await self.repo.get_subproject(
            subproject_id, project_id, load_relations=load_relations
        )
        if not sp:
            raise NotFoundError(message="Sub-project not found.")
        return sp

    async def _publish(self, coro) -> None:
        """Fire-and-forget: never abort a request due to Kafka failure."""
        if not self.publisher:
            return
        try:
            await coro
        except Exception as exc:
            log.error("project_service.publish_failed", error=str(exc))

    # ═════════════════════════════════════════════════════════════════════════
    # OrgProject
    # ═════════════════════════════════════════════════════════════════════════

    async def create_project(
        self,
        org_id:        uuid.UUID,
        data:          dict,
        created_by_id: Optional[uuid.UUID] = None,
    ) -> OrgProject:
        """
        Create a new execution project in PLANNING status.

        Rules:
          · Org must be ACTIVE or VERIFIED.
          · slug must be globally unique.
          · code (if provided) must be unique within the org.
          · branch_id (if provided) must belong to this org.
        """
        await self._get_org_or_404(org_id)

        slug = data.get("slug", "").strip()
        if not slug:
            raise ValidationError("slug is required.")
        if await self.repo.slug_exists(slug):
            raise ConflictError(
                f"A project with slug '{slug}' already exists."
            )

        if code := data.get("code"):
            if await self.repo.code_exists_in_org(org_id, code):
                raise ConflictError(
                    f"Project code '{code}' is already used in this organisation."
                )

        project = await self.repo.create_project(org_id, data, created_by_id)
        await self.db.commit()

        log.info(
            "project.created",
            project_id=str(project.id),
            org_id=str(org_id),
            slug=slug,
        )
        return project

    async def list_projects(
        self,
        org_id:    uuid.UUID,
        status:    Optional[str] = None,
        branch_id: Optional[uuid.UUID] = None,
        skip:      int = 0,
        limit:     int = 50,
    ) -> list[OrgProject]:
        await self._get_org_or_404(org_id)
        return await self.repo.list_projects(org_id, status, branch_id, skip, limit)

    async def get_project(
        self, org_id: uuid.UUID, project_id: uuid.UUID
    ) -> OrgProject:
        await self._get_org_or_404(org_id)
        return await self._get_project_or_404(
            project_id, org_id, load_relations=True
        )

    async def update_project(
        self, org_id: uuid.UUID, project_id: uuid.UUID, **fields
    ) -> OrgProject:
        await self._get_org_or_404(org_id)
        project = await self._get_project_or_404(project_id, org_id)

        if (new_slug := fields.get("slug")) and new_slug != project.slug:
            if await self.repo.slug_exists(new_slug):
                raise ConflictError(
                    f"A project with slug '{new_slug}' already exists."
                )
        if (new_code := fields.get("code")) and new_code != project.code:
            if await self.repo.code_exists_in_org(org_id, new_code, exclude_id=project_id):
                raise ConflictError(
                    f"Project code '{new_code}' is already used in this organisation."
                )

        changed = list(fields.keys())
        project = await self.repo.update_project(project, **fields)
        await self.db.commit()

        # Publish update event when project is ACTIVE or when a media field
        # changes — downstream services need to sync cover_image_url even for
        # projects that aren't active yet (e.g. PLANNING status preview).
        media_changed = bool({"cover_image_url", "org_logo_url"} & set(changed))
        if project.status == ProjectStatus.ACTIVE or media_changed:
            await self._publish(
                self.publisher.org_project_updated(project, changed)
            )
        return project

    async def activate_project(
        self, org_id: uuid.UUID, project_id: uuid.UUID
    ) -> OrgProject:
        """PLANNING → ACTIVE. Publishes org_project.published."""
        project = await self._get_project_or_404(project_id, org_id)

        if project.status != ProjectStatus.PLANNING:
            raise ValidationError(
                f"Cannot activate project with status '{project.status.value}'. "
                "Only PLANNING projects can be activated."
            )

        project = await self.repo.set_project_status(project, ProjectStatus.ACTIVE)
        await self.db.commit()
        log.info("project.activated", project_id=str(project_id))

        await self._publish(self.publisher.org_project_published(project))
        return project

    async def pause_project(
        self, org_id: uuid.UUID, project_id: uuid.UUID
    ) -> OrgProject:
        """ACTIVE → PAUSED."""
        project = await self._get_project_or_404(project_id, org_id)

        if project.status != ProjectStatus.ACTIVE:
            raise ValidationError(
                "Only ACTIVE projects can be paused."
            )

        project = await self.repo.set_project_status(project, ProjectStatus.PAUSED)
        await self.db.commit()

        await self._publish(self.publisher.org_project_paused(project))
        return project

    async def resume_project(
        self, org_id: uuid.UUID, project_id: uuid.UUID
    ) -> OrgProject:
        """PAUSED → ACTIVE."""
        project = await self._get_project_or_404(project_id, org_id)

        if project.status != ProjectStatus.PAUSED:
            raise ValidationError("Only PAUSED projects can be resumed.")

        project = await self.repo.set_project_status(project, ProjectStatus.ACTIVE)
        await self.db.commit()

        await self._publish(self.publisher.org_project_resumed(project))
        return project

    async def complete_project(
        self, org_id: uuid.UUID, project_id: uuid.UUID
    ) -> OrgProject:
        project = await self._get_project_or_404(project_id, org_id)

        if project.status not in (ProjectStatus.ACTIVE, ProjectStatus.PAUSED):
            raise ValidationError(
                "Only ACTIVE or PAUSED projects can be marked as completed."
            )

        project = await self.repo.set_project_status(project, ProjectStatus.COMPLETED)
        await self.db.commit()

        await self._publish(self.publisher.org_project_completed(project))
        return project

    async def cancel_project(
        self, org_id: uuid.UUID, project_id: uuid.UUID
    ) -> OrgProject:
        """Soft-delete — status → CANCELLED, deleted_at set."""
        project = await self._get_project_or_404(project_id, org_id)
        project = await self.repo.soft_delete_project(project)
        await self.db.commit()

        await self._publish(self.publisher.org_project_cancelled(project))
        return project

    # ═════════════════════════════════════════════════════════════════════════
    # OrgProjectInCharge
    # ═════════════════════════════════════════════════════════════════════════

    async def assign_in_charge(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        data:       dict,
    ) -> OrgProjectInCharge:
        await self._get_project_or_404(project_id, org_id)

        existing = await self.repo.get_in_charge(
            project_id, data["user_id"], data["role_title"]
        )
        if existing:
            raise ConflictError(
                f"User already holds role '{data['role_title']}' on this project."
            )

        inc = await self.repo.create_in_charge(project_id, data)
        await self.db.commit()
        return inc

    async def list_in_charges(
        self, org_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[OrgProjectInCharge]:
        await self._get_project_or_404(project_id, org_id)
        return await self.repo.list_in_charges(project_id)

    async def relieve_in_charge(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        user_id:    uuid.UUID,
        role_title: str,
    ) -> OrgProjectInCharge:
        await self._get_project_or_404(project_id, org_id)
        inc = await self.repo.get_in_charge(project_id, user_id, role_title)
        if not inc:
            raise NotFoundError("In-charge assignment not found.")
        inc = await self.repo.relieve_in_charge(inc)
        await self.db.commit()
        return inc

    # ═════════════════════════════════════════════════════════════════════════
    # OrgProjectStage
    # ═════════════════════════════════════════════════════════════════════════

    async def add_stage(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        data:       dict,
    ) -> OrgProjectStage:
        await self._get_project_or_404(project_id, org_id)

        if await self.repo.stage_order_taken(project_id, data["stage_order"]):
            raise ConflictError(
                f"Stage order {data['stage_order']} is already taken. "
                "Choose a different stage_order or update the existing stage."
            )

        stage = await self.repo.create_stage(project_id, data)
        await self.db.commit()
        return stage

    async def list_stages(
        self, org_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[OrgProjectStage]:
        await self._get_project_or_404(project_id, org_id)
        return await self.repo.list_stages(project_id, load_relations=True)

    async def get_stage(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
    ) -> OrgProjectStage:
        await self._get_project_or_404(project_id, org_id)
        return await self._get_stage_or_404(stage_id, project_id, load_relations=True)

    async def update_stage(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
        **fields,
    ) -> OrgProjectStage:
        await self._get_project_or_404(project_id, org_id)
        stage = await self._get_stage_or_404(stage_id, project_id)

        if (new_order := fields.get("stage_order")) and new_order != stage.stage_order:
            if await self.repo.stage_order_taken(project_id, new_order, exclude_id=stage_id):
                raise ConflictError(
                    f"Stage order {new_order} is already taken."
                )

        stage = await self.repo.update_stage(stage, **fields)
        await self.db.commit()
        return stage

    async def activate_stage(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
    ) -> OrgProjectStage:
        """
        PENDING → ACTIVE.
        Business rule: only one stage can be ACTIVE at a time.
        The project must itself be ACTIVE before a stage can be activated.
        Publishes org_project_stage.activated — critical for downstream cache sync.
        """
        project = await self._get_project_or_404(project_id, org_id)

        if project.status != ProjectStatus.ACTIVE:
            raise ValidationError(
                "The project must be ACTIVE before a stage can be activated."
            )
        if await self.repo.active_stage_exists(project_id):
            raise ConflictError(
                "Another stage is currently ACTIVE. Complete or skip it first."
            )

        stage = await self._get_stage_or_404(stage_id, project_id)

        if stage.status != StageStatus.PENDING:
            raise ValidationError(
                f"Cannot activate a stage with status '{stage.status.value}'. "
                "Only PENDING stages can be activated."
            )

        stage = await self.repo.set_stage_status(stage, StageStatus.ACTIVE)
        await self.db.commit()
        log.info("stage.activated", stage_id=str(stage_id), project_id=str(project_id))

        await self._publish(self.publisher.org_project_stage_activated(stage, project))
        return stage

    async def complete_stage(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
    ) -> OrgProjectStage:
        """ACTIVE → COMPLETED. Publishes org_project_stage.completed."""
        project = await self._get_project_or_404(project_id, org_id)
        stage   = await self._get_stage_or_404(stage_id, project_id)

        if stage.status != StageStatus.ACTIVE:
            raise ValidationError(
                "Only ACTIVE stages can be marked as completed."
            )

        stage = await self.repo.set_stage_status(stage, StageStatus.COMPLETED)
        await self.db.commit()

        await self._publish(self.publisher.org_project_stage_completed(stage, project))
        return stage

    async def skip_stage(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
    ) -> OrgProjectStage:
        """Mark a PENDING stage as SKIPPED (removed from scope)."""
        project = await self._get_project_or_404(project_id, org_id)
        stage   = await self._get_stage_or_404(stage_id, project_id)

        if stage.status != StageStatus.PENDING:
            raise ValidationError("Only PENDING stages can be skipped.")

        stage = await self.repo.set_stage_status(stage, StageStatus.SKIPPED)
        await self.db.commit()

        await self._publish(self.publisher.org_project_stage_skipped(stage, project))
        return stage

    # ═════════════════════════════════════════════════════════════════════════
    # OrgProjectStageInCharge
    # ═════════════════════════════════════════════════════════════════════════

    async def assign_stage_in_charge(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
        data:       dict,
    ) -> OrgProjectStageInCharge:
        await self._get_project_or_404(project_id, org_id)
        await self._get_stage_or_404(stage_id, project_id)

        existing = await self.repo.get_stage_in_charge(
            stage_id, data["user_id"], data["role_title"]
        )
        if existing:
            raise ConflictError(
                f"User already holds role '{data['role_title']}' on this stage."
            )

        inc = await self.repo.create_stage_in_charge(stage_id, data)
        await self.db.commit()
        return inc

    async def list_stage_in_charges(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
    ) -> list[OrgProjectStageInCharge]:
        await self._get_project_or_404(project_id, org_id)
        await self._get_stage_or_404(stage_id, project_id)
        return await self.repo.list_stage_in_charges(stage_id)

    async def relieve_stage_in_charge(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
        user_id:    uuid.UUID,
        role_title: str,
    ) -> OrgProjectStageInCharge:
        await self._get_project_or_404(project_id, org_id)
        await self._get_stage_or_404(stage_id, project_id)
        inc = await self.repo.get_stage_in_charge(stage_id, user_id, role_title)
        if not inc:
            raise NotFoundError("Stage in-charge assignment not found.")
        inc = await self.repo.relieve_stage_in_charge(inc)
        await self.db.commit()
        return inc

    # ═════════════════════════════════════════════════════════════════════════
    # OrgSubProject
    # ═════════════════════════════════════════════════════════════════════════

    async def add_subproject(
        self,
        org_id:     uuid.UUID,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
        data:       dict,
    ) -> OrgSubProject:
        await self._get_project_or_404(project_id, org_id)
        await self._get_stage_or_404(stage_id, project_id)

        # Validate parent belongs to same stage
        if parent_id := data.get("parent_subproject_id"):
            parent = await self.repo.get_subproject(parent_id, project_id)
            if not parent or parent.stage_id != stage_id:
                raise ValidationError(
                    "parent_subproject_id must belong to the same stage."
                )

        sp = await self.repo.create_subproject(project_id, stage_id, data)
        await self.db.commit()
        return sp

    async def list_subprojects(
        self,
        org_id:      uuid.UUID,
        project_id:  uuid.UUID,
        stage_id:    uuid.UUID,
        parent_only: bool = True,
    ) -> list[OrgSubProject]:
        await self._get_project_or_404(project_id, org_id)
        await self._get_stage_or_404(stage_id, project_id)
        return await self.repo.list_stage_subprojects(
            stage_id, parent_only, load_relations=True
        )

    async def get_subproject(
        self,
        org_id:        uuid.UUID,
        project_id:    uuid.UUID,
        subproject_id: uuid.UUID,
    ) -> OrgSubProject:
        await self._get_project_or_404(project_id, org_id)
        return await self._get_subproject_or_404(
            subproject_id, project_id, load_relations=True
        )

    async def get_subproject_tree(
        self,
        org_id:        uuid.UUID,
        project_id:    uuid.UUID,
        subproject_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        await self._get_project_or_404(project_id, org_id)
        await self._get_subproject_or_404(subproject_id, project_id)
        return await self.repo.get_subproject_tree(subproject_id)

    async def update_subproject(
        self,
        org_id:        uuid.UUID,
        project_id:    uuid.UUID,
        subproject_id: uuid.UUID,
        **fields,
    ) -> OrgSubProject:
        await self._get_project_or_404(project_id, org_id)
        sp = await self._get_subproject_or_404(subproject_id, project_id)
        sp = await self.repo.update_subproject(sp, **fields)
        await self.db.commit()
        return sp

    async def delete_subproject(
        self,
        org_id:        uuid.UUID,
        project_id:    uuid.UUID,
        subproject_id: uuid.UUID,
    ) -> OrgSubProject:
        await self._get_project_or_404(project_id, org_id)
        sp = await self._get_subproject_or_404(subproject_id, project_id)
        sp = await self.repo.soft_delete_subproject(sp)
        await self.db.commit()
        return sp

    # ═════════════════════════════════════════════════════════════════════════
    # OrgSubProjectInCharge
    # ═════════════════════════════════════════════════════════════════════════

    async def assign_subproject_in_charge(
        self,
        org_id:        uuid.UUID,
        project_id:    uuid.UUID,
        subproject_id: uuid.UUID,
        data:          dict,
    ) -> OrgSubProjectInCharge:
        await self._get_project_or_404(project_id, org_id)
        await self._get_subproject_or_404(subproject_id, project_id)

        existing = await self.repo.get_subproject_in_charge(
            subproject_id, data["user_id"], data["role_title"]
        )
        if existing:
            raise ConflictError(
                f"User already holds role '{data['role_title']}' on this sub-project."
            )

        inc = await self.repo.create_subproject_in_charge(subproject_id, data)
        await self.db.commit()
        return inc

    async def list_subproject_in_charges(
        self,
        org_id:        uuid.UUID,
        project_id:    uuid.UUID,
        subproject_id: uuid.UUID,
    ) -> list[OrgSubProjectInCharge]:
        await self._get_project_or_404(project_id, org_id)
        await self._get_subproject_or_404(subproject_id, project_id)
        return await self.repo.list_subproject_in_charges(subproject_id)

    async def relieve_subproject_in_charge(
        self,
        org_id:        uuid.UUID,
        project_id:    uuid.UUID,
        subproject_id: uuid.UUID,
        user_id:       uuid.UUID,
        role_title:    str,
    ) -> OrgSubProjectInCharge:
        await self._get_project_or_404(project_id, org_id)
        await self._get_subproject_or_404(subproject_id, project_id)
        inc = await self.repo.get_subproject_in_charge(subproject_id, user_id, role_title)
        if not inc:
            raise NotFoundError("Sub-project in-charge assignment not found.")
        inc = await self.repo.relieve_subproject_in_charge(inc)
        await self.db.commit()
        return inc
