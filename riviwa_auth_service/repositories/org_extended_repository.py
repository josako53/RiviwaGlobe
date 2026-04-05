"""
repositories/org_extended_repository.py
═══════════════════════════════════════════════════════════════════════════════
All DB operations for the 12 extended organisation tables:

  OrgLocation, OrgContent, OrgFAQ,
  OrgBranch, OrgBranchManager,
  OrgService, OrgServicePersonnel, OrgBranchService,
  OrgServiceLocation, OrgServiceMedia, OrgServiceFAQ, OrgServicePolicy

Design rules (identical to all other repositories in this service)
───────────────────────────────────────────────────────────────────
  · Pure DB access — zero business logic.
  · Returns None for not-found rows.
  · flush() only — commit is owned by the service layer.
  · Targeted UPDATE statements via SQLAlchemy update() for performance.
  · WITH RECURSIVE CTE for branch tree traversal (PostgreSQL only).
  · Allowlists on all generic update() helpers to prevent arbitrary column
    writes.

Notable patterns
────────────────
  get_branch_subtree()   — WITH RECURSIVE walks the unlimited-depth tree
                           starting from any branch, returning all descendant
                           branch IDs (including the root). Used to scope
                           service-location monitoring queries.

  upsert_content()       — OrgContent is 1-to-1 with Organisation. INSERT on
                           first call, UPDATE on subsequent calls. Returns the
                           current row either way.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.organisation_extended import (
    BranchStatus,
    OrgBranch,
    OrgBranchManager,
    OrgBranchService,
    OrgContent,
    OrgFAQ,
    OrgLocation,
    OrgService,
    OrgServiceFAQ,
    OrgServiceLocation,
    OrgServiceMedia,
    OrgServicePersonnel,
    OrgServicePolicy,
    OrgServiceStatus,
    ServicePersonnelRole,
)

log = structlog.get_logger(__name__)

# ── Allowlisted columns for generic update helpers ────────────────────────────

_LOCATION_UPDATABLE = frozenset({
    "location_type", "label", "line1", "line2", "city", "state",
    "postal_code", "country_code", "region", "latitude", "longitude",
    "is_primary",
})
_CONTENT_UPDATABLE = frozenset({
    "vision", "mission", "objectives", "global_policy",
    "terms_of_use", "privacy_policy",
})
_FAQ_UPDATABLE = frozenset({
    "question", "answer", "display_order", "is_published",
})
_BRANCH_UPDATABLE = frozenset({
    "name", "code", "description", "branch_type", "status",
    "phone", "email", "opened_on", "closed_at",
})
_SERVICE_UPDATABLE = frozenset({
    "title", "slug", "service_type", "status", "delivery_mode",
    "product_format", "inherits_location", "summary", "description",
    "category", "subcategory", "tags", "base_price", "currency_code",
    "price_is_negotiable", "delivery_time_days", "revisions_included",
    "sku", "stock_quantity", "is_featured", "published_at", "deleted_at",
})
_SERVICE_LOCATION_UPDATABLE = frozenset({
    "status", "is_virtual", "virtual_platform", "virtual_url",
    "operating_hours", "capacity", "notes", "contact_phone",
    "contact_email", "started_on", "ended_on",
})
_SERVICE_POLICY_UPDATABLE = frozenset({
    "policy_type", "title", "content", "version",
    "effective_date", "is_active",
})


class OrgExtendedRepository:
    """
    Single repository covering all 12 extended organisation tables.

    Instantiated once per request by the service layer.  All methods
    flush but never commit — the service layer owns the transaction.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ══════════════════════════════════════════════════════════════════════════
    # OrgLocation
    # ══════════════════════════════════════════════════════════════════════════

    async def create_location(
        self,
        organisation_id: uuid.UUID,
        data: dict,
    ) -> OrgLocation:
        """INSERT a new OrgLocation row and flush."""
        loc = OrgLocation(organisation_id=organisation_id, **data)
        self.db.add(loc)
        await self.db.flush()
        await self.db.refresh(loc)
        log.debug("org_location.created", org_id=str(organisation_id))
        return loc

    async def get_location(self, location_id: uuid.UUID) -> Optional[OrgLocation]:
        result = await self.db.execute(
            select(OrgLocation).where(OrgLocation.id == location_id)
        )
        return result.scalar_one_or_none()

    async def list_org_locations(self, organisation_id: uuid.UUID) -> list[OrgLocation]:
        """All locations for an org, ordered: primary first, then by city."""
        result = await self.db.execute(
            select(OrgLocation)
            .where(OrgLocation.organisation_id == organisation_id)
            .order_by(OrgLocation.is_primary.desc(), OrgLocation.city)
        )
        return list(result.scalars().all())

    async def list_branch_locations(self, branch_id: uuid.UUID) -> list[OrgLocation]:
        result = await self.db.execute(
            select(OrgLocation)
            .where(OrgLocation.branch_id == branch_id)
            .order_by(OrgLocation.is_primary.desc(), OrgLocation.city)
        )
        return list(result.scalars().all())

    async def update_location(
        self, location: OrgLocation, **fields
    ) -> OrgLocation:
        safe = {k: v for k, v in fields.items() if k in _LOCATION_UPDATABLE}
        for k, v in safe.items():
            setattr(location, k, v)
        await self.db.flush()
        return location

    async def delete_location(self, location: OrgLocation) -> None:
        await self.db.delete(location)
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgContent  (1-to-1 with Organisation)
    # ══════════════════════════════════════════════════════════════════════════

    async def get_content(self, org_id: uuid.UUID) -> Optional[OrgContent]:
        result = await self.db.execute(
            select(OrgContent).where(OrgContent.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def upsert_content(self, org_id: uuid.UUID, **fields) -> OrgContent:
        """
        Create or update the OrgContent row for this organisation.
        OrgContent is 1-to-1: the UNIQUE constraint on org_id prevents
        duplicate rows.  On first call a new row is created; on subsequent
        calls the existing row is updated.
        """
        safe   = {k: v for k, v in fields.items() if k in _CONTENT_UPDATABLE}
        content = await self.get_content(org_id)

        if content:
            for k, v in safe.items():
                setattr(content, k, v)
            content.updated_at = datetime.now(timezone.utc)
        else:
            content = OrgContent(org_id=org_id, **safe)
            self.db.add(content)

        await self.db.flush()
        await self.db.refresh(content)
        log.debug("org_content.upserted", org_id=str(org_id))
        return content

    # ══════════════════════════════════════════════════════════════════════════
    # OrgFAQ
    # ══════════════════════════════════════════════════════════════════════════

    async def create_faq(self, org_id: uuid.UUID, data: dict) -> OrgFAQ:
        faq = OrgFAQ(org_id=org_id, **data)
        self.db.add(faq)
        await self.db.flush()
        await self.db.refresh(faq)
        return faq

    async def get_faq(self, faq_id: uuid.UUID) -> Optional[OrgFAQ]:
        result = await self.db.execute(
            select(OrgFAQ).where(OrgFAQ.id == faq_id)
        )
        return result.scalar_one_or_none()

    async def list_org_faqs(
        self, org_id: uuid.UUID, *, published_only: bool = False
    ) -> list[OrgFAQ]:
        q = select(OrgFAQ).where(OrgFAQ.org_id == org_id)
        if published_only:
            q = q.where(OrgFAQ.is_published == True)  # noqa: E712
        result = await self.db.execute(q.order_by(OrgFAQ.display_order))
        return list(result.scalars().all())

    async def update_faq(self, faq: OrgFAQ, **fields) -> OrgFAQ:
        safe = {k: v for k, v in fields.items() if k in _FAQ_UPDATABLE}
        for k, v in safe.items():
            setattr(faq, k, v)
        await self.db.flush()
        return faq

    async def delete_faq(self, faq: OrgFAQ) -> None:
        await self.db.delete(faq)
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgBranch
    # ══════════════════════════════════════════════════════════════════════════

    async def create_branch(
        self,
        organisation_id: uuid.UUID,
        data: dict,
    ) -> OrgBranch:
        """INSERT a new OrgBranch and flush."""
        branch = OrgBranch(organisation_id=organisation_id, **data)
        self.db.add(branch)
        await self.db.flush()
        await self.db.refresh(branch)
        log.debug(
            "org_branch.created",
            org_id=str(organisation_id),
            branch_id=str(branch.id),
            name=branch.name,
        )
        return branch

    async def get_branch(self, branch_id: uuid.UUID) -> Optional[OrgBranch]:
        result = await self.db.execute(
            select(OrgBranch).where(OrgBranch.id == branch_id)
        )
        return result.scalar_one_or_none()

    async def get_branch_by_code(
        self, organisation_id: uuid.UUID, code: str
    ) -> Optional[OrgBranch]:
        result = await self.db.execute(
            select(OrgBranch).where(
                and_(
                    OrgBranch.organisation_id == organisation_id,
                    OrgBranch.code == code,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_top_level_branches(
        self, organisation_id: uuid.UUID
    ) -> list[OrgBranch]:
        """Direct children of the Organisation (parent_branch_id IS NULL)."""
        result = await self.db.execute(
            select(OrgBranch)
            .where(
                and_(
                    OrgBranch.organisation_id == organisation_id,
                    OrgBranch.parent_branch_id == None,  # noqa: E711
                )
            )
            .order_by(OrgBranch.name)
        )
        return list(result.scalars().all())

    async def list_child_branches(self, parent_branch_id: uuid.UUID) -> list[OrgBranch]:
        """Direct children of a branch (one level only)."""
        result = await self.db.execute(
            select(OrgBranch)
            .where(OrgBranch.parent_branch_id == parent_branch_id)
            .order_by(OrgBranch.name)
        )
        return list(result.scalars().all())

    async def get_branch_subtree(self, root_branch_id: uuid.UUID) -> list[uuid.UUID]:
        """
        Return all branch IDs in the subtree rooted at root_branch_id
        (including the root itself), using a PostgreSQL WITH RECURSIVE CTE.

        Used by service-location monitoring queries to scope results to a
        branch manager's span of control:

          Ambassador of Rome sees all locations where services are run
          by Embassy of Rome, Visa Section, Cultural Affairs, etc.

        Returns a flat list of UUIDs — callers pass this to
        get_service_locations_for_branches() or similar.
        """
        cte_sql = text("""
            WITH RECURSIVE subtree AS (
                SELECT id FROM org_branches WHERE id = :root_id
                UNION ALL
                SELECT b.id FROM org_branches b
                  JOIN subtree ON b.parent_branch_id = subtree.id
            )
            SELECT id FROM subtree
        """)
        result = await self.db.execute(cte_sql, {"root_id": root_branch_id})
        return [row[0] for row in result.fetchall()]

    async def update_branch(self, branch: OrgBranch, **fields) -> OrgBranch:
        safe = {k: v for k, v in fields.items() if k in _BRANCH_UPDATABLE}
        for k, v in safe.items():
            setattr(branch, k, v)
        branch.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return branch

    async def close_branch(self, branch: OrgBranch) -> OrgBranch:
        """Set status=CLOSED and stamp closed_at."""
        branch.status    = BranchStatus.CLOSED
        branch.closed_at = datetime.now(timezone.utc)
        branch.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return branch

    async def delete_branch(self, branch: OrgBranch) -> None:
        """
        Hard delete a branch.

        CASCADE: OrgBranchManager, OrgBranchService rows are deleted.
        SET NULL: OrgLocation.branch_id, OrgServiceLocation.branch_id,
                  OrgBranch.parent_branch_id (children survive as orphans).
        """
        await self.db.delete(branch)
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgBranchManager
    # ══════════════════════════════════════════════════════════════════════════

    async def add_branch_manager(
        self,
        branch_id:       uuid.UUID,
        user_id:         uuid.UUID,
        manager_title:   str             = "Branch Manager",
        is_primary:      bool            = False,
        appointed_by_id: Optional[uuid.UUID] = None,
    ) -> OrgBranchManager:
        manager = OrgBranchManager(
            branch_id=branch_id,
            user_id=user_id,
            manager_title=manager_title,
            is_primary=is_primary,
            appointed_by_id=appointed_by_id,
        )
        self.db.add(manager)
        await self.db.flush()
        await self.db.refresh(manager)
        log.debug(
            "org_branch_manager.added",
            branch_id=str(branch_id),
            user_id=str(user_id),
        )
        return manager

    async def get_branch_manager(
        self, branch_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[OrgBranchManager]:
        result = await self.db.execute(
            select(OrgBranchManager).where(
                and_(
                    OrgBranchManager.branch_id == branch_id,
                    OrgBranchManager.user_id   == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_branch_managers(
        self, branch_id: uuid.UUID
    ) -> list[OrgBranchManager]:
        result = await self.db.execute(
            select(OrgBranchManager)
            .where(OrgBranchManager.branch_id == branch_id)
            .order_by(OrgBranchManager.is_primary.desc(), OrgBranchManager.appointed_at)
        )
        return list(result.scalars().all())

    async def remove_branch_manager(self, manager: OrgBranchManager) -> None:
        await self.db.delete(manager)
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgService
    # ══════════════════════════════════════════════════════════════════════════

    async def create_service(
        self, organisation_id: uuid.UUID, data: dict
    ) -> OrgService:
        svc = OrgService(organisation_id=organisation_id, **data)
        self.db.add(svc)
        await self.db.flush()
        await self.db.refresh(svc)
        log.debug(
            "org_service.created",
            org_id=str(organisation_id),
            service_id=str(svc.id),
            slug=svc.slug,
        )
        return svc

    async def get_service(self, service_id: uuid.UUID) -> Optional[OrgService]:
        result = await self.db.execute(
            select(OrgService).where(OrgService.id == service_id)
        )
        return result.scalar_one_or_none()

    async def get_service_by_slug(self, slug: str) -> Optional[OrgService]:
        result = await self.db.execute(
            select(OrgService).where(OrgService.slug == slug)
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        result = await self.db.execute(
            select(OrgService.id).where(OrgService.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    async def list_org_services(
        self,
        organisation_id: uuid.UUID,
        *,
        status:           Optional[OrgServiceStatus] = None,
        active_only:      bool = False,
    ) -> list[OrgService]:
        """All services for an org. Optional status filter; active_only shortcut."""
        q = select(OrgService).where(
            and_(
                OrgService.organisation_id == organisation_id,
                OrgService.deleted_at == None,   # noqa: E711
            )
        )
        if active_only:
            q = q.where(OrgService.status == OrgServiceStatus.ACTIVE)
        elif status:
            q = q.where(OrgService.status == status)
        result = await self.db.execute(q.order_by(OrgService.title))
        return list(result.scalars().all())

    async def list_branch_services(
        self,
        branch_id: uuid.UUID,
        *,
        active_only: bool = False,
    ) -> list[OrgService]:
        """Services directly owned by a specific branch (not inherited)."""
        q = select(OrgService).where(
            and_(
                OrgService.branch_id  == branch_id,
                OrgService.deleted_at == None,  # noqa: E711
            )
        )
        if active_only:
            q = q.where(OrgService.status == OrgServiceStatus.ACTIVE)
        result = await self.db.execute(q.order_by(OrgService.title))
        return list(result.scalars().all())

    async def update_service(self, service: OrgService, **fields) -> OrgService:
        safe = {k: v for k, v in fields.items() if k in _SERVICE_UPDATABLE}
        for k, v in safe.items():
            setattr(service, k, v)
        service.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return service

    async def soft_delete_service(self, service: OrgService) -> OrgService:
        service.status     = OrgServiceStatus.ARCHIVED
        service.deleted_at = datetime.now(timezone.utc)
        service.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return service

    async def increment_view_count(self, service_id: uuid.UUID) -> None:
        """Atomic increment — avoids read-modify-write race."""
        await self.db.execute(
            update(OrgService)
            .where(OrgService.id == service_id)
            .values(view_count=OrgService.view_count + 1)
        )
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServicePersonnel
    # ══════════════════════════════════════════════════════════════════════════

    async def add_service_personnel(
        self,
        service_id:       uuid.UUID,
        user_id:          uuid.UUID,
        personnel_role:   ServicePersonnelRole,
        personnel_title:  Optional[str]       = None,
        is_primary:       bool                = False,
        appointed_by_id:  Optional[uuid.UUID] = None,
    ) -> OrgServicePersonnel:
        """
        Assign a User to an OrgService in a named role.
        UNIQUE (service_id, user_id, personnel_role) — caller should check
        first using get_service_personnel().
        """
        personnel = OrgServicePersonnel(
            service_id=service_id,
            user_id=user_id,
            personnel_role=personnel_role,
            personnel_title=personnel_title,
            is_primary=is_primary,
            appointed_by_id=appointed_by_id,
        )
        self.db.add(personnel)
        await self.db.flush()
        await self.db.refresh(personnel)
        log.debug(
            "org_service_personnel.added",
            service_id=str(service_id),
            user_id=str(user_id),
            role=personnel_role.value,
        )
        return personnel

    async def get_service_personnel(
        self,
        service_id:     uuid.UUID,
        user_id:        uuid.UUID,
        personnel_role: ServicePersonnelRole,
    ) -> Optional[OrgServicePersonnel]:
        result = await self.db.execute(
            select(OrgServicePersonnel).where(
                and_(
                    OrgServicePersonnel.service_id      == service_id,
                    OrgServicePersonnel.user_id         == user_id,
                    OrgServicePersonnel.personnel_role  == personnel_role,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_service_personnel(
        self, service_id: uuid.UUID
    ) -> list[OrgServicePersonnel]:
        result = await self.db.execute(
            select(OrgServicePersonnel)
            .where(OrgServicePersonnel.service_id == service_id)
            .order_by(
                OrgServicePersonnel.personnel_role,
                OrgServicePersonnel.is_primary.desc(),
            )
        )
        return list(result.scalars().all())

    async def remove_service_personnel(self, personnel: OrgServicePersonnel) -> None:
        await self.db.delete(personnel)
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgBranchService  (junction: which services a branch offers)
    # ══════════════════════════════════════════════════════════════════════════

    async def link_branch_service(
        self,
        branch_id:  uuid.UUID,
        service_id: uuid.UUID,
        inherited:  bool = True,
    ) -> OrgBranchService:
        """Add a service to a branch's offerings. UNIQUE (branch_id, service_id)."""
        link = OrgBranchService(
            branch_id=branch_id,
            service_id=service_id,
            inherited=inherited,
        )
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def get_branch_service_link(
        self, branch_id: uuid.UUID, service_id: uuid.UUID
    ) -> Optional[OrgBranchService]:
        result = await self.db.execute(
            select(OrgBranchService).where(
                and_(
                    OrgBranchService.branch_id  == branch_id,
                    OrgBranchService.service_id == service_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_branch_service_links(
        self, branch_id: uuid.UUID
    ) -> list[OrgBranchService]:
        result = await self.db.execute(
            select(OrgBranchService)
            .where(OrgBranchService.branch_id == branch_id)
            .order_by(OrgBranchService.created_at)
        )
        return list(result.scalars().all())

    async def unlink_branch_service(self, link: OrgBranchService) -> None:
        await self.db.delete(link)
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServiceLocation  (the key monitoring table)
    # ══════════════════════════════════════════════════════════════════════════

    async def create_service_location(self, data: dict) -> OrgServiceLocation:
        """INSERT a deployment row. UNIQUE (service_id, branch_id, location_id)."""
        sl = OrgServiceLocation(**data)
        self.db.add(sl)
        await self.db.flush()
        await self.db.refresh(sl)
        log.debug(
            "org_service_location.created",
            service_id=str(data.get("service_id")),
            branch_id=str(data.get("branch_id")),
        )
        return sl

    async def get_service_location(
        self, service_location_id: uuid.UUID
    ) -> Optional[OrgServiceLocation]:
        result = await self.db.execute(
            select(OrgServiceLocation).where(
                OrgServiceLocation.id == service_location_id
            )
        )
        return result.scalar_one_or_none()

    async def list_service_locations(
        self, service_id: uuid.UUID
    ) -> list[OrgServiceLocation]:
        """All deployment rows for a service, ordered by status then city."""
        result = await self.db.execute(
            select(OrgServiceLocation)
            .where(OrgServiceLocation.service_id == service_id)
            .order_by(OrgServiceLocation.status, OrgServiceLocation.id)
        )
        return list(result.scalars().all())

    async def list_service_locations_for_branches(
        self,
        service_id:  uuid.UUID,
        branch_ids:  list[uuid.UUID],
    ) -> list[OrgServiceLocation]:
        """
        All deployment rows for a service scoped to a set of branch IDs.

        Combine with get_branch_subtree() to scope a manager's view to their
        span of control:

            subtree = await repo.get_branch_subtree(ambassador_branch_id)
            locations = await repo.list_service_locations_for_branches(
                service_id, subtree
            )
        """
        if not branch_ids:
            return []
        result = await self.db.execute(
            select(OrgServiceLocation).where(
                and_(
                    OrgServiceLocation.service_id == service_id,
                    OrgServiceLocation.branch_id.in_(branch_ids),
                )
            ).order_by(OrgServiceLocation.status, OrgServiceLocation.id)
        )
        return list(result.scalars().all())

    async def update_service_location(
        self, sl: OrgServiceLocation, **fields
    ) -> OrgServiceLocation:
        safe = {k: v for k, v in fields.items() if k in _SERVICE_LOCATION_UPDATABLE}
        for k, v in safe.items():
            setattr(sl, k, v)
        sl.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return sl

    async def delete_service_location(self, sl: OrgServiceLocation) -> None:
        await self.db.delete(sl)
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServiceMedia
    # ══════════════════════════════════════════════════════════════════════════

    async def add_service_media(
        self, service_id: uuid.UUID, data: dict
    ) -> OrgServiceMedia:
        media = OrgServiceMedia(service_id=service_id, **data)
        self.db.add(media)
        await self.db.flush()
        await self.db.refresh(media)
        return media

    async def get_service_media(
        self, media_id: uuid.UUID
    ) -> Optional[OrgServiceMedia]:
        result = await self.db.execute(
            select(OrgServiceMedia).where(OrgServiceMedia.id == media_id)
        )
        return result.scalar_one_or_none()

    async def list_service_media(
        self, service_id: uuid.UUID
    ) -> list[OrgServiceMedia]:
        """Ordered: cover first, then by display_order."""
        result = await self.db.execute(
            select(OrgServiceMedia)
            .where(OrgServiceMedia.service_id == service_id)
            .order_by(
                OrgServiceMedia.is_cover.desc(),
                OrgServiceMedia.display_order,
            )
        )
        return list(result.scalars().all())

    async def set_cover_media(
        self, service_id: uuid.UUID, media_id: uuid.UUID
    ) -> None:
        """
        Set one media item as the cover, clearing is_cover on all others.
        Two targeted UPDATEs: clear all, then set the chosen one.
        """
        await self.db.execute(
            update(OrgServiceMedia)
            .where(OrgServiceMedia.service_id == service_id)
            .values(is_cover=False)
        )
        await self.db.execute(
            update(OrgServiceMedia)
            .where(OrgServiceMedia.id == media_id)
            .values(is_cover=True)
        )
        await self.db.flush()

    async def delete_service_media(self, media: OrgServiceMedia) -> None:
        await self.db.delete(media)
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServiceFAQ
    # ══════════════════════════════════════════════════════════════════════════

    async def create_service_faq(
        self, service_id: uuid.UUID, data: dict
    ) -> OrgServiceFAQ:
        faq = OrgServiceFAQ(service_id=service_id, **data)
        self.db.add(faq)
        await self.db.flush()
        await self.db.refresh(faq)
        return faq

    async def get_service_faq(self, faq_id: uuid.UUID) -> Optional[OrgServiceFAQ]:
        result = await self.db.execute(
            select(OrgServiceFAQ).where(OrgServiceFAQ.id == faq_id)
        )
        return result.scalar_one_or_none()

    async def list_service_faqs(
        self,
        service_id:    uuid.UUID,
        *,
        published_only: bool = False,
    ) -> list[OrgServiceFAQ]:
        q = select(OrgServiceFAQ).where(OrgServiceFAQ.service_id == service_id)
        if published_only:
            q = q.where(OrgServiceFAQ.is_published == True)  # noqa: E712
        result = await self.db.execute(q.order_by(OrgServiceFAQ.display_order))
        return list(result.scalars().all())

    async def update_service_faq(
        self, faq: OrgServiceFAQ, **fields
    ) -> OrgServiceFAQ:
        safe = {k: v for k, v in fields.items() if k in _FAQ_UPDATABLE}
        for k, v in safe.items():
            setattr(faq, k, v)
        faq.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return faq

    async def delete_service_faq(self, faq: OrgServiceFAQ) -> None:
        await self.db.delete(faq)
        await self.db.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServicePolicy
    # ══════════════════════════════════════════════════════════════════════════

    async def create_service_policy(
        self, service_id: uuid.UUID, data: dict
    ) -> OrgServicePolicy:
        """
        Insert a new policy version.
        The caller should call deactivate_previous_policy_version() first
        when replacing an existing version (version history pattern).
        """
        policy = OrgServicePolicy(service_id=service_id, **data)
        self.db.add(policy)
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def get_service_policy(
        self, policy_id: uuid.UUID
    ) -> Optional[OrgServicePolicy]:
        result = await self.db.execute(
            select(OrgServicePolicy).where(OrgServicePolicy.id == policy_id)
        )
        return result.scalar_one_or_none()

    async def list_service_policies(
        self,
        service_id:   uuid.UUID,
        *,
        active_only:  bool            = True,
        policy_type:  Optional[str]   = None,
    ) -> list[OrgServicePolicy]:
        q = select(OrgServicePolicy).where(
            OrgServicePolicy.service_id == service_id
        )
        if active_only:
            q = q.where(OrgServicePolicy.is_active == True)  # noqa: E712
        if policy_type:
            q = q.where(OrgServicePolicy.policy_type == policy_type)
        result = await self.db.execute(
            q.order_by(OrgServicePolicy.policy_type, OrgServicePolicy.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate_previous_policy_version(
        self, service_id: uuid.UUID, policy_type: str
    ) -> int:
        """
        Set is_active=False on all existing active rows for this
        (service_id, policy_type) pair before inserting a new version.
        Returns the count of rows deactivated.
        """
        result = await self.db.execute(
            update(OrgServicePolicy)
            .where(
                and_(
                    OrgServicePolicy.service_id  == service_id,
                    OrgServicePolicy.policy_type == policy_type,
                    OrgServicePolicy.is_active   == True,   # noqa: E712
                )
            )
            .values(is_active=False)
        )
        await self.db.flush()
        return result.rowcount

    async def update_service_policy(
        self, policy: OrgServicePolicy, **fields
    ) -> OrgServicePolicy:
        safe = {k: v for k, v in fields.items() if k in _SERVICE_POLICY_UPDATABLE}
        for k, v in safe.items():
            setattr(policy, k, v)
        policy.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return policy

    async def delete_service_policy(self, policy: OrgServicePolicy) -> None:
        await self.db.delete(policy)
        await self.db.flush()
