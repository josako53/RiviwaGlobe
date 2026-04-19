# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/addresses.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/addresses.py
═══════════════════════════════════════════════════════════════════════════════
Address management endpoints.

Route inventory
────────────────
  OSM / Nominatim (public — no auth)
    GET  /addresses/search              Search Nominatim for address suggestions
    GET  /addresses/reverse             Reverse-geocode GPS coordinates

  Address CRUD (requires JWT)
    POST   /addresses                   Create address (OSM, GPS, or manual)
    GET    /addresses/{entity_type}/{entity_id}   List addresses for an entity
    GET    /addresses/{address_id}      Get single address
    PATCH  /addresses/{address_id}      Update address fields
    DELETE /addresses/{address_id}      Delete address
    POST   /addresses/{address_id}/set-default    Set as default

Notes
──────
  · Search and reverse are proxied from the frontend so the Nominatim
    User-Agent can be set server-side (required by ToS).
  · All write endpoints require a valid JWT. Ownership checks (does the
    calling user own entity_id?) are enforced by the service layer.
  · For "select from existing" use cases, GET /addresses/{entity_type}/{entity_id}
    returns all saved addresses; the client renders them as a picklist.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Annotated, List, Optional

import structlog
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db, get_kafka, require_active_user
from events.publisher import EventPublisher
from models.user import User
from schemas.address import (
    AddressCreateRequest,
    AddressListResponse,
    AddressResponse,
    AddressUpdateRequest,
    NominatimResult,
)
from services.address_service import AddressService, nominatim_reverse, nominatim_search
from workers.kafka_producer import KafkaEventProducer

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/addresses", tags=["Addresses"])

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep          = Annotated[AsyncSession,        Depends(get_db)]
CurrentUserDep = Annotated[User,               Depends(require_active_user)]
ProducerDep    = Annotated[KafkaEventProducer, Depends(get_kafka)]


def get_address_service(db: DbDep, producer: ProducerDep) -> AddressService:
    publisher = EventPublisher(producer)
    return AddressService(db=db, publisher=publisher)

AddressServiceDep = Annotated[AddressService, Depends(get_address_service)]


# ─────────────────────────────────────────────────────────────────────────────
# OSM / Nominatim proxy (no auth required)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=List[NominatimResult],
    summary="Search for addresses (Nominatim / OSM)",
    description=(
        "Proxy to Nominatim /search. Returns up to `limit` address suggestions "
        "matching `q`. Use `countrycodes=TZ` to bias results to Tanzania. "
        "The frontend renders these as an autocomplete dropdown. "
        "When the user selects one, pass its `place_id` in POST /addresses."
    ),
)
async def search_addresses(
    q: str = Query(..., min_length=2, description="Free-text address query"),
    countrycodes: Optional[str] = Query(
        default="TZ",
        description="Comma-separated ISO 3166-1 alpha-2 codes to restrict results e.g. 'TZ,KE'.",
    ),
    limit: int = Query(default=8, ge=1, le=20, description="Max results to return"),
) -> List[NominatimResult]:
    return await nominatim_search(q, countrycodes=countrycodes, limit=limit)


@router.get(
    "/reverse",
    response_model=Optional[NominatimResult],
    summary="Reverse-geocode GPS coordinates (Nominatim / OSM)",
    description=(
        "Proxy to Nominatim /reverse. Given a latitude and longitude, returns "
        "the best matching address. Returns null if Nominatim has no result. "
        "The frontend shows this as a confirmation card when a user drops a map pin."
    ),
)
async def reverse_geocode(
    lat: float = Query(..., ge=-90.0,   le=90.0,   description="Decimal degrees latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Decimal degrees longitude"),
) -> Optional[NominatimResult]:
    return await nominatim_reverse(lat, lon)


# ─────────────────────────────────────────────────────────────────────────────
# Address CRUD (JWT required)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create address",
    description=(
        "Create a new address for any entity (user, org_subproject, stakeholder).\n\n"
        "**GPS coordinates are always the precise ground truth.** "
        "When provided they are stored exactly as sent — Nominatim's own centroid is never used.\n\n"
        "**Four modes:**\n\n"
        "1. **OSM + GPS** — set `osm_place_id` AND `gps_latitude`/`gps_longitude`. "
        "Nominatim fills the text fields (display_name, ward, region…); "
        "your GPS pin is the exact stored location.\n\n"
        "2. **OSM only** — set `osm_place_id`, no GPS. "
        "All fields including coordinates come from Nominatim.\n\n"
        "3. **GPS only** — set `gps_latitude` + `gps_longitude`, no `osm_place_id`. "
        "Nominatim /reverse fills text fields; your GPS is the exact location.\n\n"
        "4. **Manual** — omit both. Fill all fields directly.\n\n"
        "If the entity has no existing address, this one is auto-set as default."
    ),
)
async def create_address(
    body: AddressCreateRequest,
    svc:  AddressServiceDep,
    _:    CurrentUserDep,
) -> AddressResponse:
    address = await svc.create(body)
    return AddressService.to_response(address)


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=AddressListResponse,
    summary="List addresses for an entity",
    description=(
        "Return all saved addresses for the given entity. "
        "Use this to populate a 'select existing address' picklist. "
        "Results are ordered: default first, then by creation time."
    ),
)
async def list_addresses(
    entity_type: str,
    entity_id:   uuid.UUID,
    svc:         AddressServiceDep,
    _:           CurrentUserDep,
) -> AddressListResponse:
    addresses = await svc.list_by_entity(entity_type, entity_id)
    items = [AddressService.to_response(a) for a in addresses]
    return AddressListResponse(total=len(items), addresses=items)


@router.get(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Get a single address",
)
async def get_address(
    address_id: uuid.UUID,
    svc:        AddressServiceDep,
    _:          CurrentUserDep,
) -> AddressResponse:
    address = await svc.get_by_id(address_id)
    return AddressService.to_response(address)


@router.patch(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Update address fields",
    description=(
        "Partial update — only the fields you include are changed. "
        "Setting `is_default=true` automatically clears is_default on all other "
        "addresses for the same entity."
    ),
)
async def update_address(
    address_id: uuid.UUID,
    body:       AddressUpdateRequest,
    svc:        AddressServiceDep,
    _:          CurrentUserDep,
) -> AddressResponse:
    address = await svc.update(address_id, body)
    return AddressService.to_response(address)


@router.post(
    "/{address_id}/set-default",
    response_model=AddressResponse,
    summary="Set address as default",
    description="Marks this address as the default for its entity, clearing the previous default.",
)
async def set_default(
    address_id: uuid.UUID,
    svc:        AddressServiceDep,
    _:          CurrentUserDep,
) -> AddressResponse:
    address = await svc.set_default(address_id)
    return AddressService.to_response(address)


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete address",
)
async def delete_address(
    address_id: uuid.UUID,
    svc:        AddressServiceDep,
    _:          CurrentUserDep,
) -> None:
    await svc.delete(address_id)
