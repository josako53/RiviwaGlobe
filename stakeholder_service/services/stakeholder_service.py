"""
services/stakeholder_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for stakeholder registration, contacts, project registration,
and engagement history.
Orchestrates repositories and Kafka. Owns all validation rules.

Address creation
────────────────
When a stakeholder is registered or updated with OSM/GPS address fields,
this service calls auth_service POST /api/v1/addresses to create an Address
record, then stores the returned UUID in Stakeholder.address_id and syncs
lga/ward to the Stakeholder row for fast geographic filtering.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

log = structlog.get_logger(__name__)

from core.exceptions import (
    DuplicateStakeholderProjectError,
    ContactNotFoundError,
    ProjectNotFoundError,
    StakeholderNotFoundError,
    ValidationError,
)
from events.producer import StakeholderProducer
from models.stakeholder import (
    AffectednessType,
    EntityType,
    ImportanceRating,
    PreferredChannel,
    Stakeholder,
    StakeholderCategory,
    StakeholderContact,
    StakeholderProject,
    StakeholderType,
)
from models.engagement import StakeholderEngagement
from repositories.stakeholder_repository import StakeholderRepository


class StakeholderService:

    def __init__(self, db: AsyncSession, producer: StakeholderProducer) -> None:
        self.repo     = StakeholderRepository(db)
        self.producer = producer
        self.db       = db

    # ── Address creation helper ───────────────────────────────────────────────

    async def _create_address_for_stakeholder(
        self,
        stakeholder_id: uuid.UUID,
        data: Dict[str, Any],
        jwt_token: Optional[str] = None,
    ) -> Optional[uuid.UUID]:
        """
        Call auth_service POST /api/v1/addresses to create an Address record
        for this stakeholder. Returns the new address UUID, or None on failure.

        Used during register and update when the caller provides OSM/GPS/address
        fields rather than an existing address_id.

        The JWT forwarded is the PIU staff member's token that originated the
        request — auth_service will accept it for address creation.
        """
        has_osm = data.get("osm_place_id") is not None
        has_gps = data.get("gps_latitude") is not None
        has_manual = any(data.get(f) for f in ("region", "district", "lga", "ward", "mtaa", "line1"))

        if not (has_osm or has_gps or has_manual):
            return None

        body: Dict[str, Any] = {
            "entity_type":  "stakeholder",
            "entity_id":    str(stakeholder_id),
            "address_type": "registered",
            "is_default":   True,
        }
        for field in (
            "osm_place_id", "display_name", "osm_id", "osm_type",
            "gps_latitude", "gps_longitude",
            "region", "district", "lga", "ward", "mtaa", "line1", "address_notes",
        ):
            if data.get(field) is not None:
                body[field] = data[field]

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY,
        }
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{settings.AUTH_SERVICE_URL}/api/v1/addresses",
                    json=body,
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()
                addr_id = uuid.UUID(result["id"])
                log.info(
                    "stakeholder.address.created_in_auth",
                    stakeholder_id=str(stakeholder_id),
                    address_id=str(addr_id),
                )
                return addr_id
        except Exception as exc:
            log.error(
                "stakeholder.address.creation_failed",
                stakeholder_id=str(stakeholder_id),
                error=str(exc),
                exc_info=exc,
            )
            return None

    # ── Register ──────────────────────────────────────────────────────────────

    async def register(
        self,
        data: dict,
        registered_by: uuid.UUID,
        jwt_token: Optional[str] = None,
    ) -> Stakeholder:
        """
        Register a new stakeholder.

        If data contains OSM/GPS/manual address fields (and no address_id),
        a new Address record is created in auth_service and the returned UUID
        is stored in Stakeholder.address_id. lga and ward are also denormalised
        from the request data for fast geographic filtering.
        """
        # Resolve address_id: existing UUID or create new
        address_id: Optional[uuid.UUID] = None
        if data.get("address_id"):
            address_id = uuid.UUID(str(data["address_id"]))

        s = await self.repo.create(
            stakeholder_type       = StakeholderType(data["stakeholder_type"]),
            entity_type            = EntityType(data["entity_type"]),
            category               = StakeholderCategory(data["category"]),
            affectedness           = AffectednessType(data.get("affectedness", "unknown")),
            importance_rating      = ImportanceRating(data.get("importance_rating", "medium")),
            preferred_channel      = PreferredChannel(data.get("preferred_channel", "public_meeting")),
            org_name               = data.get("org_name"),
            first_name             = data.get("first_name"),
            last_name              = data.get("last_name"),
            org_id                 = uuid.UUID(data["org_id"]) if data.get("org_id") else None,
            address_id             = address_id,
            lga                    = data.get("lga"),
            ward                   = data.get("ward"),
            language_preference    = data.get("language_preference", "sw"),
            needs_translation      = data.get("needs_translation", False),
            needs_transport        = data.get("needs_transport", False),
            needs_childcare        = data.get("needs_childcare", False),
            is_vulnerable          = data.get("is_vulnerable", False),
            vulnerable_group_types = data.get("vulnerable_group_types"),
            participation_barriers = data.get("participation_barriers"),
            notes                  = data.get("notes"),
            registered_by_user_id  = registered_by,
        )
        await self.db.commit()

        # If no explicit address_id but OSM/GPS fields provided, create address now
        if not address_id and (
            data.get("osm_place_id") or data.get("gps_latitude") or
            any(data.get(f) for f in ("region", "district", "lga", "ward", "mtaa", "line1"))
        ):
            new_addr_id = await self._create_address_for_stakeholder(s.id, data, jwt_token)
            if new_addr_id:
                await self.repo.update(s, {"address_id": new_addr_id})
                await self.db.commit()

        await self.producer.stakeholder_registered(s.id, s.entity_type.value, s.category.value)
        return s

    # ── Fetch ─────────────────────────────────────────────────────────────────

    async def get_or_404(self, stakeholder_id: uuid.UUID) -> Stakeholder:
        s = await self.repo.get_by_id(stakeholder_id)
        if not s:
            raise StakeholderNotFoundError()
        return s

    async def get_with_contacts_or_404(self, stakeholder_id: uuid.UUID) -> Stakeholder:
        s = await self.repo.get_by_id_with_contacts(stakeholder_id)
        if not s:
            raise StakeholderNotFoundError()
        return s

    async def list(
        self,
        stakeholder_type: Optional[str]              = None,
        category:         Optional[str]              = None,
        lga:              Optional[str]              = None,
        is_vulnerable:    Optional[bool]             = None,
        project_id:       Optional[uuid.UUID]        = None,
        importance:       Optional[ImportanceRating] = None,
        stage_id:         Optional[uuid.UUID]        = None,
        affectedness:     Optional[str]              = None,
        skip:             int                        = 0,
        limit:            int                        = 50,
    ) -> list[Stakeholder]:
        return await self.repo.list(
            stakeholder_type=stakeholder_type, category=category,
            lga=lga, is_vulnerable=is_vulnerable, project_id=project_id,
            importance=importance, stage_id=stage_id, affectedness=affectedness,
            skip=skip, limit=limit,
        )

    async def stakeholder_analysis(
        self,
        project_id:    uuid.UUID,
        stage_id:      Optional[uuid.UUID]       = None,
        importance:    Optional[ImportanceRating] = None,
        category:      Optional[str]             = None,
        affectedness:  Optional[str]             = None,
        is_vulnerable: Optional[bool]            = None,
        skip:          int                       = 0,
        limit:         int                       = 200,
    ) -> list[dict]:
        """Returns the full Annex 3 stakeholder analysis matrix."""
        return await self.repo.list_stakeholder_analysis(
            project_id=project_id, stage_id=stage_id, importance=importance,
            category=category, affectedness=affectedness, is_vulnerable=is_vulnerable,
            skip=skip, limit=limit,
        )

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(
        self,
        stakeholder_id: uuid.UUID,
        data: dict,
        jwt_token: Optional[str] = None,
    ) -> Stakeholder:
        s = await self.get_or_404(stakeholder_id)
        allowed = {
            "affectedness", "importance_rating", "org_name", "first_name", "last_name",
            "address_id", "lga", "ward", "language_preference", "preferred_channel",
            "needs_translation", "needs_transport", "needs_childcare", "is_vulnerable",
            "vulnerable_group_types", "participation_barriers", "notes",
            # ── Media ─────────────────────────────────────────────────────────
            "logo_url",
        }
        coercions = {
            "affectedness":    AffectednessType,
            "importance_rating": ImportanceRating,
            "preferred_channel": PreferredChannel,
        }
        fields = {}
        for field, value in data.items():
            if field in allowed and value is not None:
                fields[field] = coercions[field](value) if field in coercions else value

        # If OSM/GPS address fields provided (no explicit address_id), create address
        address_fields = ("osm_place_id", "gps_latitude", "gps_longitude",
                          "region", "district", "lga", "ward", "mtaa", "line1")
        needs_address_create = (
            not data.get("address_id")
            and any(data.get(f) for f in address_fields)
        )
        if needs_address_create:
            new_addr_id = await self._create_address_for_stakeholder(s.id, data, jwt_token)
            if new_addr_id:
                fields["address_id"] = new_addr_id
                # Sync denormalised location fields
                for f in ("lga", "ward"):
                    if data.get(f):
                        fields[f] = data[f]

        if fields:
            await self.repo.update(s, fields)
            await self.db.commit()
            await self.producer.stakeholder_updated(s.id, list(fields.keys()))

        return s

    # ── Soft delete ───────────────────────────────────────────────────────────

    async def delete(self, stakeholder_id: uuid.UUID) -> None:
        s = await self.get_or_404(stakeholder_id)
        await self.repo.soft_delete(s)
        await self.db.commit()

    # ── Project registration ──────────────────────────────────────────────────

    async def register_for_project(
        self, stakeholder_id: uuid.UUID, data: dict, registered_by: uuid.UUID
    ) -> StakeholderProject:
        await self.get_or_404(stakeholder_id)
        project_id = uuid.UUID(data["project_id"])

        if not await self.repo.get_project_cache(project_id):
            raise ProjectNotFoundError()
        if await self.repo.get_stakeholder_project(stakeholder_id, project_id):
            raise DuplicateStakeholderProjectError()

        sp = await self.repo.create_stakeholder_project(
            stakeholder_id        = stakeholder_id,
            project_id            = project_id,
            is_pap                = data.get("is_pap", False),
            affectedness          = AffectednessType(data["affectedness"]) if data.get("affectedness") else None,
            impact_description    = data.get("impact_description"),
            registered_by_user_id = registered_by,
        )
        await self.db.commit()
        return sp

    async def list_projects(self, stakeholder_id: uuid.UUID) -> list[StakeholderProject]:
        await self.get_or_404(stakeholder_id)
        return await self.repo.list_stakeholder_projects(stakeholder_id)

    # ── Engagement history ────────────────────────────────────────────────────

    async def engagement_history(
        self, stakeholder_id: uuid.UUID
    ) -> list[StakeholderEngagement]:
        await self.get_or_404(stakeholder_id)
        contact_ids = await self.repo.list_contact_ids_for_stakeholder(stakeholder_id)
        return await self.repo.list_engagements_for_contacts(contact_ids)

    # ── Contacts ──────────────────────────────────────────────────────────────

    async def add_contact(
        self, stakeholder_id: uuid.UUID, data: dict
    ) -> StakeholderContact:
        await self.get_or_404(stakeholder_id)
        c = await self.repo.create_contact(
            stakeholder_id                = stakeholder_id,
            full_name                     = data["full_name"],
            preferred_channel             = PreferredChannel(data.get("preferred_channel", "phone_call")),
            user_id                       = uuid.UUID(data["user_id"]) if data.get("user_id") else None,
            title                         = data.get("title"),
            role_in_org                   = data.get("role_in_org"),
            email                         = data.get("email"),
            phone                         = data.get("phone"),
            is_primary                    = data.get("is_primary", False),
            can_submit_feedback           = data.get("can_submit_feedback", True),
            can_receive_communications    = data.get("can_receive_communications", True),
            can_distribute_communications = data.get("can_distribute_communications", False),
            notes                         = data.get("notes"),
        )
        await self.db.commit()
        await self.producer.contact_added(stakeholder_id, c.id, c.is_primary)
        return c

    async def get_contact_or_404(
        self, contact_id: uuid.UUID, stakeholder_id: uuid.UUID
    ) -> StakeholderContact:
        c = await self.repo.get_contact_by_id(contact_id, stakeholder_id)
        if not c:
            raise ContactNotFoundError()
        return c

    async def list_contacts(
        self, stakeholder_id: uuid.UUID, active_only: bool = True
    ) -> list[StakeholderContact]:
        return await self.repo.list_contacts(stakeholder_id, active_only)

    async def update_contact(
        self, stakeholder_id: uuid.UUID, contact_id: uuid.UUID, data: dict
    ) -> StakeholderContact:
        c = await self.get_contact_or_404(contact_id, stakeholder_id)
        allowed = {
            "full_name", "title", "role_in_org", "email", "phone",
            "preferred_channel", "is_primary", "can_submit_feedback",
            "can_receive_communications", "can_distribute_communications",
            "notes", "user_id",
        }
        for field, value in data.items():
            if field in allowed and value is not None:
                if field == "preferred_channel":
                    value = PreferredChannel(value)
                if field == "user_id":
                    value = uuid.UUID(value)
                setattr(c, field, value)
        self.db.add(c)
        await self.db.commit()
        return c

    async def deactivate_contact(
        self, stakeholder_id: uuid.UUID, contact_id: uuid.UUID, reason: Optional[str]
    ) -> None:
        c = await self.get_contact_or_404(contact_id, stakeholder_id)
        await self.repo.deactivate_contact(c, reason)
        await self.db.commit()
