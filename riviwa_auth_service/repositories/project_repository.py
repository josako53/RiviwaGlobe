"""
repositories/project_repository.py
═══════════════════════════════════════════════════════════════════════════════
DB access layer for the OrgProject execution hierarchy.

Covers
───────
  OrgProject, OrgProjectInCharge
  OrgProjectStage, OrgProjectStageInCharge
  OrgSubProject, OrgSubProjectInCharge

Design rules (identical to all repositories in this service)
──────────────────────────────────────────────────────────────
  · Pure DB access — zero business logic.
  · Returns None for not-found rows (callers convert to 404).
  · flush() only — commit is owned by the service layer.
  · Allowlists on all update() helpers to prevent arbitrary column writes.
  · WITH RECURSIVE CTE for unlimited-depth sub-project tree traversal.

Notable patterns
─────────────────
  get_subproject_tree()  — WITH RECURSIVE walks the unlimited-depth tree
                           starting from any sub-project, returning all
                           descendant IDs (including the root). Mirrors
                           get_branch_subtree() in org_extended_repository.

  slug_exists()          — fast existence check before INSERT to give a
                           cleaner error than a DB unique violation.

  code_exists_in_org()   — project codes are unique within an org (not globally).
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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

log = structlog.get_logger(__name__)

# ── Allowlisted fields for update helpers ─────────────────────────────────────

_PROJECT_UPDATABLE = frozenset({
    "name", "visibility", "category", "sector",
    "description", "background", "objectives", "expected_outcomes",
    "target_beneficiaries", "start_date", "end_date",
    "actual_start_date", "actual_end_date",
    "budget_amount", "currency_code", "funding_source",
    "country_code", "region", "primary_lga", "location_description",
    "cover_image_url", "document_urls",
    "accepts_grievances", "accepts_suggestions", "accepts_applause",
    "requires_grm", "status",
})

_STAGE_UPDATABLE = frozenset({
    "name", "stage_order", "description", "objectives", "deliverables",
    "start_date", "end_date", "actual_start_date", "actual_end_date",
    "accepts_grievances", "accepts_suggestions", "accepts_applause",
    "status",
})

_SUBPROJECT_UPDATABLE = frozenset({
    "name", "code", "description", "objectives", "activities",
    "expected_outputs", "start_date", "end_date",
    "actual_start_date", "actual_end_date",
    "budget_amount", "currency_code", "location",
    "display_order", "status", "address_id",
})


class ProjectRepository:
    """All DB operations for the OrgProject execution hierarchy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ═════════════════════════════════════════════════════════════════════════
    # OrgProject
    # ═════════════════════════════════════════════════════════════════════════

    async def slug_exists(self, slug: str) -> bool:
        """True if any OrgProject with this slug exists (global uniqueness)."""
        result = await self.db.execute(
            select(OrgProject.id).where(OrgProject.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    async def code_exists_in_org(
        self, org_id: uuid.UUID, code: str, exclude_id: Optional[uuid.UUID] = None
    ) -> bool:
        """True if this code is already taken within the organisation."""
        q = select(OrgProject.id).where(
            OrgProject.organisation_id == org_id,
            OrgProject.code == code,
            OrgProject.deleted_at == None,
        )
        if exclude_id:
            q = q.where(OrgProject.id != exclude_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none() is not None

    async def create_project(
        self,
        org_id:          uuid.UUID,
        data:            dict,
        created_by_id:   Optional[uuid.UUID] = None,
    ) -> OrgProject:
        project = OrgProject(
            organisation_id = org_id,
            created_by_id   = created_by_id,
            **{k: v for k, v in data.items() if k in _PROJECT_UPDATABLE | {"name","slug","code","branch_id","org_service_id","visibility"}},
        )
        self.db.add(project)
        await self.db.flush()
        return project

    async def get_project(
        self,
        project_id: uuid.UUID,
        org_id:     Optional[uuid.UUID] = None,
        *,
        load_relations: bool = False,
    ) -> Optional[OrgProject]:
        """Fetch a project. Pass org_id to scope to an organisation."""
        q = select(OrgProject).where(
            OrgProject.id == project_id,
            OrgProject.deleted_at == None,
        )
        if org_id:
            q = q.where(OrgProject.organisation_id == org_id)
        if load_relations:
            q = q.options(
                selectinload(OrgProject.in_charges),
                selectinload(OrgProject.stages).selectinload(OrgProjectStage.in_charges),
                selectinload(OrgProject.stages).selectinload(
                    OrgProjectStage.sub_projects
                ).selectinload(OrgSubProject.in_charges),
                selectinload(OrgProject.stages).selectinload(
                    OrgProjectStage.sub_projects
                ).selectinload(OrgSubProject.children),
            )
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_projects(
        self,
        org_id:   uuid.UUID,
        status:   Optional[str] = None,
        branch_id: Optional[uuid.UUID] = None,
        skip:     int = 0,
        limit:    int = 50,
    ) -> list[OrgProject]:
        q = select(OrgProject).where(
            OrgProject.organisation_id == org_id,
            OrgProject.deleted_at == None,
        )
        if status:
            q = q.where(OrgProject.status == status)
        if branch_id:
            q = q.where(OrgProject.branch_id == branch_id)
        q = q.order_by(OrgProject.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update_project(
        self, project: OrgProject, **fields
    ) -> OrgProject:
        safe = {k: v for k, v in fields.items() if k in _PROJECT_UPDATABLE}
        for k, v in safe.items():
            setattr(project, k, v)
        project.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return project

    async def set_project_status(
        self, project: OrgProject, new_status: ProjectStatus
    ) -> OrgProject:
        project.status = new_status
        if new_status == ProjectStatus.ACTIVE and not project.actual_start_date:
            from datetime import date
            project.actual_start_date = date.today()
        if new_status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
            from datetime import date
            project.actual_end_date = project.actual_end_date or date.today()
        project.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return project

    async def soft_delete_project(self, project: OrgProject) -> OrgProject:
        project.status = ProjectStatus.CANCELLED
        project.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return project

    # ═════════════════════════════════════════════════════════════════════════
    # OrgProjectInCharge
    # ═════════════════════════════════════════════════════════════════════════

    async def get_in_charge(
        self,
        project_id: uuid.UUID,
        user_id:    uuid.UUID,
        role_title: str,
    ) -> Optional[OrgProjectInCharge]:
        result = await self.db.execute(
            select(OrgProjectInCharge).where(
                OrgProjectInCharge.project_id  == project_id,
                OrgProjectInCharge.user_id     == user_id,
                OrgProjectInCharge.role_title  == role_title,
                OrgProjectInCharge.relieved_at == None,
            )
        )
        return result.scalar_one_or_none()

    async def list_in_charges(
        self, project_id: uuid.UUID, active_only: bool = True
    ) -> list[OrgProjectInCharge]:
        q = select(OrgProjectInCharge).where(
            OrgProjectInCharge.project_id == project_id
        )
        if active_only:
            q = q.where(OrgProjectInCharge.relieved_at == None)
        result = await self.db.execute(q.order_by(OrgProjectInCharge.is_lead.desc()))
        return list(result.scalars().all())

    async def create_in_charge(
        self, project_id: uuid.UUID, data: dict
    ) -> OrgProjectInCharge:
        inc = OrgProjectInCharge(project_id=project_id, **data)
        self.db.add(inc)
        await self.db.flush()
        return inc

    async def relieve_in_charge(
        self, inc: OrgProjectInCharge
    ) -> OrgProjectInCharge:
        inc.relieved_at = datetime.now(timezone.utc)
        await self.db.flush()
        return inc

    # ═════════════════════════════════════════════════════════════════════════
    # OrgProjectStage
    # ═════════════════════════════════════════════════════════════════════════

    async def stage_order_taken(
        self,
        project_id:   uuid.UUID,
        stage_order:  int,
        exclude_id:   Optional[uuid.UUID] = None,
    ) -> bool:
        """True if stage_order is already taken for this project."""
        q = select(OrgProjectStage.id).where(
            OrgProjectStage.project_id  == project_id,
            OrgProjectStage.stage_order == stage_order,
        )
        if exclude_id:
            q = q.where(OrgProjectStage.id != exclude_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none() is not None

    async def active_stage_exists(self, project_id: uuid.UUID) -> bool:
        """True if there is already an ACTIVE stage for this project."""
        result = await self.db.execute(
            select(OrgProjectStage.id).where(
                OrgProjectStage.project_id == project_id,
                OrgProjectStage.status     == StageStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_stage(
        self,
        stage_id:   uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        *,
        load_relations: bool = False,
    ) -> Optional[OrgProjectStage]:
        q = select(OrgProjectStage).where(OrgProjectStage.id == stage_id)
        if project_id:
            q = q.where(OrgProjectStage.project_id == project_id)
        if load_relations:
            q = q.options(
                selectinload(OrgProjectStage.in_charges),
                selectinload(OrgProjectStage.sub_projects).selectinload(OrgSubProject.in_charges),
                selectinload(OrgProjectStage.sub_projects).selectinload(OrgSubProject.children),
            )
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_stages(
        self, project_id: uuid.UUID, load_relations: bool = False
    ) -> list[OrgProjectStage]:
        q = select(OrgProjectStage).where(
            OrgProjectStage.project_id == project_id
        ).order_by(OrgProjectStage.stage_order)
        if load_relations:
            q = q.options(
                selectinload(OrgProjectStage.in_charges),
                selectinload(OrgProjectStage.sub_projects).selectinload(OrgSubProject.in_charges),
            )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create_stage(
        self, project_id: uuid.UUID, data: dict
    ) -> OrgProjectStage:
        stage = OrgProjectStage(project_id=project_id, **data)
        self.db.add(stage)
        await self.db.flush()
        return stage

    async def update_stage(
        self, stage: OrgProjectStage, **fields
    ) -> OrgProjectStage:
        safe = {k: v for k, v in fields.items() if k in _STAGE_UPDATABLE}
        for k, v in safe.items():
            setattr(stage, k, v)
        stage.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return stage

    async def set_stage_status(
        self, stage: OrgProjectStage, new_status: StageStatus
    ) -> OrgProjectStage:
        stage.status = new_status
        if new_status == StageStatus.ACTIVE and not stage.actual_start_date:
            from datetime import date
            stage.actual_start_date = date.today()
        if new_status == StageStatus.COMPLETED and not stage.actual_end_date:
            from datetime import date
            stage.actual_end_date = date.today()
        stage.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return stage

    # ═════════════════════════════════════════════════════════════════════════
    # OrgProjectStageInCharge
    # ═════════════════════════════════════════════════════════════════════════

    async def get_stage_in_charge(
        self,
        stage_id:   uuid.UUID,
        user_id:    uuid.UUID,
        role_title: str,
    ) -> Optional[OrgProjectStageInCharge]:
        result = await self.db.execute(
            select(OrgProjectStageInCharge).where(
                OrgProjectStageInCharge.stage_id   == stage_id,
                OrgProjectStageInCharge.user_id    == user_id,
                OrgProjectStageInCharge.role_title == role_title,
                OrgProjectStageInCharge.relieved_at == None,
            )
        )
        return result.scalar_one_or_none()

    async def list_stage_in_charges(
        self, stage_id: uuid.UUID, active_only: bool = True
    ) -> list[OrgProjectStageInCharge]:
        q = select(OrgProjectStageInCharge).where(
            OrgProjectStageInCharge.stage_id == stage_id
        )
        if active_only:
            q = q.where(OrgProjectStageInCharge.relieved_at == None)
        result = await self.db.execute(q.order_by(OrgProjectStageInCharge.is_lead.desc()))
        return list(result.scalars().all())

    async def create_stage_in_charge(
        self, stage_id: uuid.UUID, data: dict
    ) -> OrgProjectStageInCharge:
        inc = OrgProjectStageInCharge(stage_id=stage_id, **data)
        self.db.add(inc)
        await self.db.flush()
        return inc

    async def relieve_stage_in_charge(
        self, inc: OrgProjectStageInCharge
    ) -> OrgProjectStageInCharge:
        inc.relieved_at = datetime.now(timezone.utc)
        await self.db.flush()
        return inc

    # ═════════════════════════════════════════════════════════════════════════
    # OrgSubProject
    # ═════════════════════════════════════════════════════════════════════════

    async def get_subproject(
        self,
        subproject_id: uuid.UUID,
        project_id:    Optional[uuid.UUID] = None,
        *,
        load_relations: bool = False,
    ) -> Optional[OrgSubProject]:
        q = select(OrgSubProject).where(
            OrgSubProject.id         == subproject_id,
            OrgSubProject.deleted_at == None,
        )
        if project_id:
            q = q.where(OrgSubProject.project_id == project_id)
        if load_relations:
            q = q.options(
                selectinload(OrgSubProject.in_charges),
                selectinload(OrgSubProject.children),
            )
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_stage_subprojects(
        self,
        stage_id:    uuid.UUID,
        parent_only: bool = True,
        load_relations: bool = False,
    ) -> list[OrgSubProject]:
        """
        List sub-projects for a stage.
        parent_only=True → only top-level (no parent). False → all.
        """
        q = select(OrgSubProject).where(
            OrgSubProject.stage_id   == stage_id,
            OrgSubProject.deleted_at == None,
        )
        if parent_only:
            q = q.where(OrgSubProject.parent_subproject_id == None)
        if load_relations:
            q = q.options(
                selectinload(OrgSubProject.in_charges),
                selectinload(OrgSubProject.children).selectinload(OrgSubProject.in_charges),
            )
        q = q.order_by(OrgSubProject.display_order, OrgSubProject.created_at)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_subproject_tree(
        self, root_subproject_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """
        Traverse the unlimited-depth sub-project tree rooted at root_subproject_id.
        Returns ALL descendant IDs including the root.
        Uses PostgreSQL WITH RECURSIVE CTE — mirrors get_branch_subtree().
        """
        cte = text("""
            WITH RECURSIVE sub_tree AS (
                SELECT id
                FROM   org_sub_projects
                WHERE  id = :root_id
                  AND  deleted_at IS NULL
                UNION ALL
                SELECT sp.id
                FROM   org_sub_projects sp
                JOIN   sub_tree        st ON sp.parent_subproject_id = st.id
                WHERE  sp.deleted_at IS NULL
            )
            SELECT id FROM sub_tree
        """)
        result = await self.db.execute(cte, {"root_id": root_subproject_id})
        return [row[0] for row in result.all()]

    async def create_subproject(
        self,
        project_id: uuid.UUID,
        stage_id:   uuid.UUID,
        data:       dict,
    ) -> OrgSubProject:
        sp = OrgSubProject(
            project_id=project_id,
            stage_id=stage_id,
            **{k: v for k, v in data.items() if k in _SUBPROJECT_UPDATABLE | {"name","code","parent_subproject_id","display_order"}},
        )
        self.db.add(sp)
        await self.db.flush()
        return sp

    async def update_subproject(
        self, sp: OrgSubProject, **fields
    ) -> OrgSubProject:
        safe = {k: v for k, v in fields.items() if k in _SUBPROJECT_UPDATABLE}
        for k, v in safe.items():
            setattr(sp, k, v)
        sp.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return sp

    async def soft_delete_subproject(
        self, sp: OrgSubProject
    ) -> OrgSubProject:
        sp.status = SubProjectStatus.CANCELLED
        sp.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return sp

    # ═════════════════════════════════════════════════════════════════════════
    # OrgSubProjectInCharge
    # ═════════════════════════════════════════════════════════════════════════

    async def get_subproject_in_charge(
        self,
        subproject_id: uuid.UUID,
        user_id:       uuid.UUID,
        role_title:    str,
    ) -> Optional[OrgSubProjectInCharge]:
        result = await self.db.execute(
            select(OrgSubProjectInCharge).where(
                OrgSubProjectInCharge.subproject_id == subproject_id,
                OrgSubProjectInCharge.user_id       == user_id,
                OrgSubProjectInCharge.role_title    == role_title,
                OrgSubProjectInCharge.relieved_at   == None,
            )
        )
        return result.scalar_one_or_none()

    async def list_subproject_in_charges(
        self, subproject_id: uuid.UUID, active_only: bool = True
    ) -> list[OrgSubProjectInCharge]:
        q = select(OrgSubProjectInCharge).where(
            OrgSubProjectInCharge.subproject_id == subproject_id
        )
        if active_only:
            q = q.where(OrgSubProjectInCharge.relieved_at == None)
        result = await self.db.execute(q.order_by(OrgSubProjectInCharge.is_lead.desc()))
        return list(result.scalars().all())

    async def create_subproject_in_charge(
        self, subproject_id: uuid.UUID, data: dict
    ) -> OrgSubProjectInCharge:
        inc = OrgSubProjectInCharge(subproject_id=subproject_id, **data)
        self.db.add(inc)
        await self.db.flush()
        return inc

    async def relieve_subproject_in_charge(
        self, inc: OrgSubProjectInCharge
    ) -> OrgSubProjectInCharge:
        inc.relieved_at = datetime.now(timezone.utc)
        await self.db.flush()
        return inc
