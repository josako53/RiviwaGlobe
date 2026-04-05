"""
services/org_extended_service.py
═══════════════════════════════════════════════════════════════════════════════
Business logic for the 12 extended organisation tables.

Each public method:
  1. Validates business rules
  2. Delegates DB writes to OrgExtendedRepository (flush only)
  3. Commits via the injected AsyncSession

Notable business rules enforced here
──────────────────────────────────────
  · A branch can only be created under an ACTIVE organisation.
  · A branch code must be unique within the organisation.
  · Service slugs are globally unique (cross-org).
  · OrgContent is 1-to-1: upsert semantics.
  · Service PRODUCT type with delivery_mode=PHYSICAL should have
    product_format set (warned, not enforced at DB level).
  · Personnel assignments are unique per (service, user, role);
    the same user can hold different roles on the same service.
  · When creating a new policy version, the previous active version of the
    same policy_type is deactivated atomically before inserting.
  · Branch tree traversal (get_branch_subtree) is delegated to the
    repository which executes the WITH RECURSIVE CTE.

No Kafka events are published from this service layer — the extended org
functionality is additive/content-management in nature. Add event publishing
here if downstream consumers need to react (e.g. a search index rebuild on
service status change).
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
    ForbiddenError,
    NotFoundError,
    OrgNotFoundError,
    ValidationError,
)
from models.organisation import Organisation, OrgStatus
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
    OrgServiceType,
    ProductFormat,
    ServiceDeliveryMode,
    ServicePersonnelRole,
)
from repositories.org_extended_repository import OrgExtendedRepository
from repositories.organisation_repository import OrganisationRepository

log = structlog.get_logger(__name__)


class OrgExtendedService:

    def __init__(self, db: AsyncSession) -> None:
        self.db      = db
        self.repo    = OrgExtendedRepository(db)
        self.org_repo = OrganisationRepository(db)

    # ══════════════════════════════════════════════════════════════════════════
    # OrgLocation
    # ══════════════════════════════════════════════════════════════════════════

    async def add_location(
        self,
        org_id: uuid.UUID,
        data:   dict,
    ) -> OrgLocation:
        """
        Add a physical address to an organisation (or one of its branches).

        If data contains branch_id, the location is scoped to that branch.
        Setting is_primary=True on a new location does NOT automatically
        clear is_primary on other locations — call set_primary_location() to
        do that atomically.
        """
        org = await self._get_org_or_404(org_id)

        if data.get("branch_id"):
            await self._get_branch_or_404(data["branch_id"], expected_org_id=org_id)

        location = await self.repo.create_location(org_id, data)
        await self.db.commit()
        log.info("org_location.added", org_id=str(org_id), location_id=str(location.id))
        return location

    async def update_location(
        self,
        org_id:      uuid.UUID,
        location_id: uuid.UUID,
        **fields,
    ) -> OrgLocation:
        location = await self._get_location_or_404(location_id, expected_org_id=org_id)
        location = await self.repo.update_location(location, **fields)
        await self.db.commit()
        return location

    async def delete_location(
        self, org_id: uuid.UUID, location_id: uuid.UUID
    ) -> None:
        location = await self._get_location_or_404(location_id, expected_org_id=org_id)
        await self.repo.delete_location(location)
        await self.db.commit()
        log.info("org_location.deleted", location_id=str(location_id))

    async def list_locations(self, org_id: uuid.UUID) -> list[OrgLocation]:
        return await self.repo.list_org_locations(org_id)

    async def list_branch_locations(self, branch_id: uuid.UUID) -> list[OrgLocation]:
        await self._get_branch_or_404(branch_id)
        return await self.repo.list_branch_locations(branch_id)

    # ══════════════════════════════════════════════════════════════════════════
    # OrgContent  (1-to-1 upsert)
    # ══════════════════════════════════════════════════════════════════════════

    async def upsert_content(
        self, org_id: uuid.UUID, **fields
    ) -> OrgContent:
        """
        Create or update the long-form content profile for an organisation.
        Accepts: vision, mission, objectives, global_policy, terms_of_use,
                 privacy_policy.
        """
        await self._get_org_or_404(org_id)
        content = await self.repo.upsert_content(org_id, **fields)
        await self.db.commit()
        log.info("org_content.upserted", org_id=str(org_id))
        return content

    async def get_content(self, org_id: uuid.UUID) -> Optional[OrgContent]:
        return await self.repo.get_content(org_id)

    # ══════════════════════════════════════════════════════════════════════════
    # OrgFAQ
    # ══════════════════════════════════════════════════════════════════════════

    async def add_faq(
        self, org_id: uuid.UUID, question: str, answer: str,
        display_order: int = 0, is_published: bool = True,
    ) -> OrgFAQ:
        await self._get_org_or_404(org_id)
        faq = await self.repo.create_faq(
            org_id,
            {"question": question, "answer": answer,
             "display_order": display_order, "is_published": is_published},
        )
        await self.db.commit()
        return faq

    async def update_faq(
        self, org_id: uuid.UUID, faq_id: uuid.UUID, **fields
    ) -> OrgFAQ:
        faq = await self._get_org_faq_or_404(faq_id, expected_org_id=org_id)
        faq = await self.repo.update_faq(faq, **fields)
        await self.db.commit()
        return faq

    async def delete_faq(self, org_id: uuid.UUID, faq_id: uuid.UUID) -> None:
        faq = await self._get_org_faq_or_404(faq_id, expected_org_id=org_id)
        await self.repo.delete_faq(faq)
        await self.db.commit()

    async def list_faqs(
        self, org_id: uuid.UUID, *, published_only: bool = False
    ) -> list[OrgFAQ]:
        return await self.repo.list_org_faqs(org_id, published_only=published_only)

    # ══════════════════════════════════════════════════════════════════════════
    # OrgBranch
    # ══════════════════════════════════════════════════════════════════════════

    async def create_branch(
        self,
        org_id:   uuid.UUID,
        name:     str,
        data:     dict,
    ) -> OrgBranch:
        """
        Create a new branch (or sub-branch) under this organisation.

        Rules:
          · Organisation must be ACTIVE.
          · If parent_branch_id is set, the parent must belong to the same org.
          · If code is set, it must be unique within this org.
        """
        org = await self._get_org_or_404(org_id)
        if org.status != OrgStatus.ACTIVE:
            raise ValidationError(
                "Cannot add a branch to an organisation that is not ACTIVE."
            )

        parent_id = data.get("parent_branch_id")
        if parent_id:
            await self._get_branch_or_404(parent_id, expected_org_id=org_id)

        if data.get("code"):
            existing = await self.repo.get_branch_by_code(org_id, data["code"])
            if existing:
                raise ConflictError(
                    f"A branch with code '{data['code']}' already exists in this organisation."
                )

        branch = await self.repo.create_branch(org_id, {"name": name, **data})
        await self.db.commit()
        log.info(
            "org_branch.created",
            org_id=str(org_id),
            branch_id=str(branch.id),
            name=name,
        )
        return branch

    async def update_branch(
        self, org_id: uuid.UUID, branch_id: uuid.UUID, **fields
    ) -> OrgBranch:
        branch = await self._get_branch_or_404(branch_id, expected_org_id=org_id)

        # Code uniqueness check on change
        if "code" in fields and fields["code"] != branch.code:
            existing = await self.repo.get_branch_by_code(org_id, fields["code"])
            if existing:
                raise ConflictError(
                    f"A branch with code '{fields['code']}' already exists."
                )

        branch = await self.repo.update_branch(branch, **fields)
        await self.db.commit()
        return branch

    async def close_branch(
        self, org_id: uuid.UUID, branch_id: uuid.UUID
    ) -> OrgBranch:
        """Close a branch. Its children survive as orphaned branches (SET NULL)."""
        branch = await self._get_branch_or_404(branch_id, expected_org_id=org_id)
        if branch.status == BranchStatus.CLOSED:
            raise ValidationError("Branch is already closed.")
        branch = await self.repo.close_branch(branch)
        await self.db.commit()
        log.info("org_branch.closed", branch_id=str(branch_id))
        return branch

    async def delete_branch(
        self, org_id: uuid.UUID, branch_id: uuid.UUID
    ) -> None:
        branch = await self._get_branch_or_404(branch_id, expected_org_id=org_id)
        await self.repo.delete_branch(branch)
        await self.db.commit()
        log.info("org_branch.deleted", branch_id=str(branch_id))

    async def get_branch_tree(
        self, org_id: uuid.UUID, branch_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """
        Return all branch IDs in the subtree rooted at branch_id
        (including branch_id itself). Uses WITH RECURSIVE CTE.
        Scoped to org for safety.
        """
        await self._get_branch_or_404(branch_id, expected_org_id=org_id)
        return await self.repo.get_branch_subtree(branch_id)

    async def list_top_level_branches(
        self, org_id: uuid.UUID
    ) -> list[OrgBranch]:
        await self._get_org_or_404(org_id)
        return await self.repo.list_top_level_branches(org_id)

    async def list_child_branches(
        self, org_id: uuid.UUID, branch_id: uuid.UUID
    ) -> list[OrgBranch]:
        await self._get_branch_or_404(branch_id, expected_org_id=org_id)
        return await self.repo.list_child_branches(branch_id)

    # ══════════════════════════════════════════════════════════════════════════
    # OrgBranchManager
    # ══════════════════════════════════════════════════════════════════════════

    async def add_branch_manager(
        self,
        org_id:          uuid.UUID,
        branch_id:       uuid.UUID,
        user_id:         uuid.UUID,
        manager_title:   str             = "Branch Manager",
        is_primary:      bool            = False,
        appointed_by_id: Optional[uuid.UUID] = None,
    ) -> OrgBranchManager:
        await self._get_branch_or_404(branch_id, expected_org_id=org_id)

        existing = await self.repo.get_branch_manager(branch_id, user_id)
        if existing:
            raise ConflictError("This user is already a manager of this branch.")

        manager = await self.repo.add_branch_manager(
            branch_id, user_id, manager_title, is_primary, appointed_by_id
        )
        await self.db.commit()
        log.info(
            "org_branch_manager.added",
            branch_id=str(branch_id),
            user_id=str(user_id),
        )
        return manager

    async def remove_branch_manager(
        self,
        org_id:    uuid.UUID,
        branch_id: uuid.UUID,
        user_id:   uuid.UUID,
    ) -> None:
        await self._get_branch_or_404(branch_id, expected_org_id=org_id)
        manager = await self.repo.get_branch_manager(branch_id, user_id)
        if not manager:
            raise NotFoundError("Manager assignment not found.")
        await self.repo.remove_branch_manager(manager)
        await self.db.commit()
        log.info(
            "org_branch_manager.removed",
            branch_id=str(branch_id),
            user_id=str(user_id),
        )

    async def list_branch_managers(
        self, org_id: uuid.UUID, branch_id: uuid.UUID
    ) -> list[OrgBranchManager]:
        await self._get_branch_or_404(branch_id, expected_org_id=org_id)
        return await self.repo.list_branch_managers(branch_id)

    # ══════════════════════════════════════════════════════════════════════════
    # OrgService
    # ══════════════════════════════════════════════════════════════════════════

    async def create_service(
        self,
        org_id: uuid.UUID,
        data:   dict,
    ) -> OrgService:
        """
        Create a new service/product/program listing.

        Rules:
          · Org must be ACTIVE.
          · slug must be globally unique.
          · If branch_id is set, it must belong to this org.
          · PRODUCT type with delivery_mode=PHYSICAL should have product_format
            set (logged as a warning; not a hard error).
        """
        org = await self._get_org_or_404(org_id)
        if org.status != OrgStatus.ACTIVE:
            raise ValidationError(
                "Cannot create a service for an organisation that is not ACTIVE."
            )

        if data.get("branch_id"):
            await self._get_branch_or_404(data["branch_id"], expected_org_id=org_id)

        slug = data.get("slug")
        if not slug:
            raise ValidationError("slug is required.")
        if await self.repo.slug_exists(slug):
            raise ConflictError(f"A service with slug '{slug}' already exists.")

        # Advisory check: PRODUCT + PHYSICAL should have product_format
        if (
            data.get("service_type") == OrgServiceType.PRODUCT
            and data.get("delivery_mode") == ServiceDeliveryMode.PHYSICAL
            and not data.get("product_format")
        ):
            log.warning(
                "org_service.create.missing_product_format",
                org_id=str(org_id),
                slug=slug,
            )

        service = await self.repo.create_service(org_id, data)
        await self.db.commit()
        log.info(
            "org_service.created",
            org_id=str(org_id),
            service_id=str(service.id),
            slug=slug,
        )
        return service

    async def update_service(
        self, org_id: uuid.UUID, service_id: uuid.UUID, **fields
    ) -> OrgService:
        service = await self._get_service_or_404(service_id, expected_org_id=org_id)

        if "slug" in fields and fields["slug"] != service.slug:
            if await self.repo.slug_exists(fields["slug"]):
                raise ConflictError(
                    f"A service with slug '{fields['slug']}' already exists."
                )

        service = await self.repo.update_service(service, **fields)
        await self.db.commit()
        return service

    async def publish_service(
        self, org_id: uuid.UUID, service_id: uuid.UUID
    ) -> OrgService:
        """Transition DRAFT → ACTIVE and stamp published_at."""
        service = await self._get_service_or_404(service_id, expected_org_id=org_id)
        if service.status == OrgServiceStatus.ACTIVE:
            raise ValidationError("Service is already published.")
        service = await self.repo.update_service(
            service,
            status=OrgServiceStatus.ACTIVE,
            published_at=datetime.now(timezone.utc),
        )
        await self.db.commit()
        log.info("org_service.published", service_id=str(service_id))
        return service

    async def archive_service(
        self, org_id: uuid.UUID, service_id: uuid.UUID
    ) -> OrgService:
        service = await self._get_service_or_404(service_id, expected_org_id=org_id)
        service = await self.repo.soft_delete_service(service)
        await self.db.commit()
        log.info("org_service.archived", service_id=str(service_id))
        return service

    async def list_org_services(
        self,
        org_id:       uuid.UUID,
        *,
        status:       Optional[OrgServiceStatus] = None,
        active_only:  bool = False,
    ) -> list[OrgService]:
        return await self.repo.list_org_services(
            org_id, status=status, active_only=active_only
        )

    async def get_service(self, service_id: uuid.UUID) -> OrgService:
        service = await self.repo.get_service(service_id)
        if not service:
            raise NotFoundError("Service not found.")
        return service

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServicePersonnel
    # ══════════════════════════════════════════════════════════════════════════

    async def assign_service_personnel(
        self,
        org_id:          uuid.UUID,
        service_id:      uuid.UUID,
        user_id:         uuid.UUID,
        personnel_role:  ServicePersonnelRole,
        personnel_title: Optional[str]       = None,
        is_primary:      bool                = False,
        appointed_by_id: Optional[uuid.UUID] = None,
    ) -> OrgServicePersonnel:
        """
        Assign a user to a service in a named role.
        UNIQUE (service_id, user_id, personnel_role) — a user can hold
        multiple different roles on the same service (two separate rows),
        but cannot hold the same role twice.
        """
        await self._get_service_or_404(service_id, expected_org_id=org_id)

        existing = await self.repo.get_service_personnel(
            service_id, user_id, personnel_role
        )
        if existing:
            raise ConflictError(
                f"This user already holds the '{personnel_role.value}' role "
                "on this service."
            )

        personnel = await self.repo.add_service_personnel(
            service_id, user_id, personnel_role,
            personnel_title, is_primary, appointed_by_id,
        )
        await self.db.commit()
        return personnel

    async def remove_service_personnel(
        self,
        org_id:         uuid.UUID,
        service_id:     uuid.UUID,
        user_id:        uuid.UUID,
        personnel_role: ServicePersonnelRole,
    ) -> None:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        personnel = await self.repo.get_service_personnel(
            service_id, user_id, personnel_role
        )
        if not personnel:
            raise NotFoundError("Personnel assignment not found.")
        await self.repo.remove_service_personnel(personnel)
        await self.db.commit()

    async def list_service_personnel(
        self, service_id: uuid.UUID
    ) -> list[OrgServicePersonnel]:
        return await self.repo.list_service_personnel(service_id)

    # ══════════════════════════════════════════════════════════════════════════
    # OrgBranchService  (branch ↔ service junction)
    # ══════════════════════════════════════════════════════════════════════════

    async def link_branch_service(
        self,
        org_id:     uuid.UUID,
        branch_id:  uuid.UUID,
        service_id: uuid.UUID,
        inherited:  bool = True,
    ) -> OrgBranchService:
        """Register that a branch offers this service."""
        await self._get_branch_or_404(branch_id, expected_org_id=org_id)
        await self._get_service_or_404(service_id, expected_org_id=org_id)

        existing = await self.repo.get_branch_service_link(branch_id, service_id)
        if existing:
            raise ConflictError("This service is already linked to this branch.")

        link = await self.repo.link_branch_service(branch_id, service_id, inherited)
        await self.db.commit()
        return link

    async def unlink_branch_service(
        self,
        org_id:     uuid.UUID,
        branch_id:  uuid.UUID,
        service_id: uuid.UUID,
    ) -> None:
        await self._get_branch_or_404(branch_id, expected_org_id=org_id)
        link = await self.repo.get_branch_service_link(branch_id, service_id)
        if not link:
            raise NotFoundError("Branch-service link not found.")
        await self.repo.unlink_branch_service(link)
        await self.db.commit()

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServiceLocation  (the monitoring table)
    # ══════════════════════════════════════════════════════════════════════════

    async def add_service_location(
        self,
        org_id:     uuid.UUID,
        service_id: uuid.UUID,
        data:       dict,
    ) -> OrgServiceLocation:
        """
        Pin a service to an address and branch.

        Rules:
          · service must belong to this org.
          · branch_id (if set) must belong to this org.
          · For virtual deployments (is_virtual=True), location_id must be None.
          · For physical deployments (is_virtual=False), location_id should be set.
        """
        await self._get_service_or_404(service_id, expected_org_id=org_id)

        if data.get("branch_id"):
            await self._get_branch_or_404(data["branch_id"], expected_org_id=org_id)

        if not data.get("is_virtual") and not data.get("location_id"):
            log.warning(
                "org_service_location.physical_without_location",
                service_id=str(service_id),
            )

        if data.get("is_virtual") and data.get("location_id"):
            raise ValidationError(
                "Virtual deployments must have location_id=None. "
                "location_id is only used for physical deployments."
            )

        sl = await self.repo.create_service_location(
            {"service_id": service_id, **data}
        )
        await self.db.commit()
        return sl

    async def update_service_location(
        self,
        org_id:              uuid.UUID,
        service_id:          uuid.UUID,
        service_location_id: uuid.UUID,
        **fields,
    ) -> OrgServiceLocation:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        sl = await self.repo.get_service_location(service_location_id)
        if not sl or sl.service_id != service_id:
            raise NotFoundError("Service location not found.")
        sl = await self.repo.update_service_location(sl, **fields)
        await self.db.commit()
        return sl

    async def delete_service_location(
        self,
        org_id:              uuid.UUID,
        service_id:          uuid.UUID,
        service_location_id: uuid.UUID,
    ) -> None:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        sl = await self.repo.get_service_location(service_location_id)
        if not sl or sl.service_id != service_id:
            raise NotFoundError("Service location not found.")
        await self.repo.delete_service_location(sl)
        await self.db.commit()

    async def list_service_locations(
        self, service_id: uuid.UUID
    ) -> list[OrgServiceLocation]:
        return await self.repo.list_service_locations(service_id)

    async def list_service_locations_for_branch_tree(
        self,
        org_id:     uuid.UUID,
        service_id: uuid.UUID,
        branch_id:  uuid.UUID,
    ) -> list[OrgServiceLocation]:
        """
        Return all service deployment rows visible to a manager of branch_id
        (their branch and all descendant branches).

        This is the core monitoring query: a branch manager can see all
        addresses where a service is running within their span of control.
        """
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        await self._get_branch_or_404(branch_id, expected_org_id=org_id)

        subtree = await self.repo.get_branch_subtree(branch_id)
        return await self.repo.list_service_locations_for_branches(
            service_id, subtree
        )

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServiceMedia
    # ══════════════════════════════════════════════════════════════════════════

    async def add_service_media(
        self, org_id: uuid.UUID, service_id: uuid.UUID, data: dict
    ) -> OrgServiceMedia:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        media = await self.repo.add_service_media(service_id, data)
        await self.db.commit()
        return media

    async def set_cover_media(
        self, org_id: uuid.UUID, service_id: uuid.UUID, media_id: uuid.UUID
    ) -> None:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        media = await self.repo.get_service_media(media_id)
        if not media or media.service_id != service_id:
            raise NotFoundError("Media item not found on this service.")
        await self.repo.set_cover_media(service_id, media_id)
        await self.db.commit()

    async def delete_service_media(
        self, org_id: uuid.UUID, service_id: uuid.UUID, media_id: uuid.UUID
    ) -> None:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        media = await self.repo.get_service_media(media_id)
        if not media or media.service_id != service_id:
            raise NotFoundError("Media item not found.")
        await self.repo.delete_service_media(media)
        await self.db.commit()

    async def list_service_media(self, service_id: uuid.UUID) -> list[OrgServiceMedia]:
        return await self.repo.list_service_media(service_id)

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServiceFAQ
    # ══════════════════════════════════════════════════════════════════════════

    async def add_service_faq(
        self,
        org_id:     uuid.UUID,
        service_id: uuid.UUID,
        question:   str,
        answer:     str,
        display_order: int  = 0,
        is_published:  bool = True,
    ) -> OrgServiceFAQ:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        faq = await self.repo.create_service_faq(
            service_id,
            {"question": question, "answer": answer,
             "display_order": display_order, "is_published": is_published},
        )
        await self.db.commit()
        return faq

    async def update_service_faq(
        self,
        org_id:     uuid.UUID,
        service_id: uuid.UUID,
        faq_id:     uuid.UUID,
        **fields,
    ) -> OrgServiceFAQ:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        faq = await self.repo.get_service_faq(faq_id)
        if not faq or faq.service_id != service_id:
            raise NotFoundError("Service FAQ not found.")
        faq = await self.repo.update_service_faq(faq, **fields)
        await self.db.commit()
        return faq

    async def delete_service_faq(
        self, org_id: uuid.UUID, service_id: uuid.UUID, faq_id: uuid.UUID
    ) -> None:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        faq = await self.repo.get_service_faq(faq_id)
        if not faq or faq.service_id != service_id:
            raise NotFoundError("Service FAQ not found.")
        await self.repo.delete_service_faq(faq)
        await self.db.commit()

    async def list_service_faqs(
        self,
        service_id:    uuid.UUID,
        *,
        published_only: bool = False,
    ) -> list[OrgServiceFAQ]:
        return await self.repo.list_service_faqs(
            service_id, published_only=published_only
        )

    # ══════════════════════════════════════════════════════════════════════════
    # OrgServicePolicy
    # ══════════════════════════════════════════════════════════════════════════

    async def create_service_policy(
        self,
        org_id:     uuid.UUID,
        service_id: uuid.UUID,
        data:       dict,
    ) -> OrgServicePolicy:
        """
        Create a new policy version for a service.

        If a previous active version of the same policy_type exists, it is
        deactivated atomically (version history pattern: old version kept as
        audit log, new version becomes the active one).
        """
        await self._get_service_or_404(service_id, expected_org_id=org_id)

        policy_type = data.get("policy_type")
        if not policy_type:
            raise ValidationError("policy_type is required.")

        # Deactivate previous version of this policy_type for this service
        deactivated = await self.repo.deactivate_previous_policy_version(
            service_id, policy_type
        )
        if deactivated:
            log.info(
                "org_service_policy.previous_version_deactivated",
                service_id=str(service_id),
                policy_type=policy_type,
                count=deactivated,
            )

        policy = await self.repo.create_service_policy(service_id, data)
        await self.db.commit()
        return policy

    async def update_service_policy(
        self,
        org_id:     uuid.UUID,
        service_id: uuid.UUID,
        policy_id:  uuid.UUID,
        **fields,
    ) -> OrgServicePolicy:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        policy = await self.repo.get_service_policy(policy_id)
        if not policy or policy.service_id != service_id:
            raise NotFoundError("Service policy not found.")
        policy = await self.repo.update_service_policy(policy, **fields)
        await self.db.commit()
        return policy

    async def delete_service_policy(
        self, org_id: uuid.UUID, service_id: uuid.UUID, policy_id: uuid.UUID
    ) -> None:
        await self._get_service_or_404(service_id, expected_org_id=org_id)
        policy = await self.repo.get_service_policy(policy_id)
        if not policy or policy.service_id != service_id:
            raise NotFoundError("Service policy not found.")
        await self.repo.delete_service_policy(policy)
        await self.db.commit()

    async def list_service_policies(
        self,
        service_id:  uuid.UUID,
        *,
        active_only: bool          = True,
        policy_type: Optional[str] = None,
    ) -> list[OrgServicePolicy]:
        return await self.repo.list_service_policies(
            service_id, active_only=active_only, policy_type=policy_type
        )

    # ══════════════════════════════════════════════════════════════════════════
    # Internal helpers
    # ══════════════════════════════════════════════════════════════════════════

    async def _get_org_or_404(self, org_id: uuid.UUID) -> Organisation:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise OrgNotFoundError()
        return org

    async def _get_branch_or_404(
        self,
        branch_id:         uuid.UUID,
        expected_org_id:   Optional[uuid.UUID] = None,
    ) -> OrgBranch:
        branch = await self.repo.get_branch(branch_id)
        if not branch:
            raise NotFoundError("Branch not found.")
        if expected_org_id and branch.organisation_id != expected_org_id:
            raise ForbiddenError("Branch does not belong to this organisation.")
        return branch

    async def _get_service_or_404(
        self,
        service_id:       uuid.UUID,
        expected_org_id:  Optional[uuid.UUID] = None,
    ) -> OrgService:
        service = await self.repo.get_service(service_id)
        if not service or service.deleted_at is not None:
            raise NotFoundError("Service not found.")
        if expected_org_id and service.organisation_id != expected_org_id:
            raise ForbiddenError("Service does not belong to this organisation.")
        return service

    async def _get_location_or_404(
        self,
        location_id:     uuid.UUID,
        expected_org_id: Optional[uuid.UUID] = None,
    ) -> OrgLocation:
        location = await self.repo.get_location(location_id)
        if not location:
            raise NotFoundError("Location not found.")
        if expected_org_id and location.organisation_id != expected_org_id:
            raise ForbiddenError("Location does not belong to this organisation.")
        return location

    async def _get_org_faq_or_404(
        self,
        faq_id:          uuid.UUID,
        expected_org_id: Optional[uuid.UUID] = None,
    ) -> OrgFAQ:
        faq = await self.repo.get_faq(faq_id)
        if not faq:
            raise NotFoundError("FAQ not found.")
        if expected_org_id and faq.org_id != expected_org_id:
            raise ForbiddenError("FAQ does not belong to this organisation.")
        return faq
