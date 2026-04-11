# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  schemas/project.py
# ───────────────────────────────────────────────────────────────────────────
"""
schemas/project.py
═══════════════════════════════════════════════════════════════════════════════
Pydantic schemas for the OrgProject execution hierarchy.

Schema pairs follow the same "trinity" pattern used throughout this service:
  Create*Request   → body accepted on POST
  Update*Request   → body accepted on PATCH (all fields Optional)
  *Response        → data returned to the client (from_attributes=True)

Resources covered
──────────────────
  OrgProject             — top-level execution project (Msimbazi, RISE, TACTICS…)
  OrgProjectInCharge     — people responsible for the overall project
  OrgProjectStage        — ordered phases within a project
  OrgProjectStageInCharge — people responsible for a specific stage
  OrgSubProject          — work packages (unlimited nesting depth)
  OrgSubProjectInCharge  — people responsible for a sub-project

Kafka payload schemas
──────────────────────
  ProjectPublishedEvent  — published on riviwa.org.events when a project goes ACTIVE
  StageActivatedEvent    — published when a stage transitions to ACTIVE
  StageCompletedEvent    — published when a stage is marked COMPLETED
  ProjectPausedEvent     — published when project is paused
  ProjectCompletedEvent  — published when project is completed
  ProjectCancelledEvent  — published when project is cancelled

These Kafka payloads are kept as plain Pydantic models so downstream services
(stakeholder_service, feedback_service) can import this file from a shared
location in future. For now they are defined here and used by the service layer
to build the JSON payload before publishing.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Shared primitive
# ─────────────────────────────────────────────────────────────────────────────

class AddressEmbed(BaseModel):
    """
    Embedded address block — returned inline on any resource that carries
    an address_id FK.  The full Address row is fetched and serialised here
    so the client doesn't need a second request.
    """
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id:             uuid.UUID
    address_type:   str
    label:          Optional[str] = None
    line1:          str
    line2:          Optional[str] = None
    city:           Optional[str] = None
    state:          Optional[str] = None
    postal_code:    Optional[str] = None
    country_code:   str
    region:         Optional[str] = None
    district:       Optional[str] = None
    lga:            Optional[str] = None
    ward:           Optional[str] = None
    mtaa:           Optional[str] = None
    gps_latitude:   Optional[float] = None
    gps_longitude:  Optional[float] = None
    address_notes:  Optional[str] = None
    is_default:     bool = False


# ─────────────────────────────────────────────────────────────────────────────
# OrgSubProjectInCharge
# ─────────────────────────────────────────────────────────────────────────────

class CreateSubProjectInChargeRequest(BaseModel):
    user_id:    uuid.UUID
    role_title: str = Field(max_length=200)
    duties:     Optional[str] = None
    is_lead:    bool = False


class SubProjectInChargeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id:            uuid.UUID
    subproject_id: uuid.UUID
    user_id:       uuid.UUID
    role_title:    str
    duties:        Optional[str] = None
    is_lead:       bool
    assigned_at:   datetime
    relieved_at:   Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# OrgSubProject
# ─────────────────────────────────────────────────────────────────────────────

class CreateSubProjectRequest(BaseModel):
    name:                 str = Field(max_length=255)
    code:                 Optional[str] = Field(default=None, max_length=50)
    parent_subproject_id: Optional[uuid.UUID] = None
    description:          Optional[str] = None
    objectives:           Optional[str] = None
    activities:           Optional[Dict[str, Any]] = None
    expected_outputs:     Optional[str] = None
    start_date:           Optional[date] = None
    end_date:             Optional[date] = None
    budget_amount:        Optional[float] = None
    currency_code:        Optional[str] = Field(default=None, max_length=3)
    location:             Optional[str] = None
    display_order:        int = 0


class UpdateSubProjectRequest(BaseModel):
    name:             Optional[str] = Field(default=None, max_length=255)
    code:             Optional[str] = Field(default=None, max_length=50)
    description:      Optional[str] = None
    objectives:       Optional[str] = None
    activities:       Optional[Dict[str, Any]] = None
    expected_outputs: Optional[str] = None
    start_date:       Optional[date] = None
    end_date:         Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date:   Optional[date] = None
    budget_amount:    Optional[float] = None
    currency_code:    Optional[str] = Field(default=None, max_length=3)
    location:         Optional[str] = None
    display_order:    Optional[int] = None
    status:           Optional[str] = None
    # Address — provide address_id to link an existing Address row
    address_id:       Optional[uuid.UUID] = None


class SubProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id:                   uuid.UUID
    project_id:           uuid.UUID
    stage_id:             uuid.UUID
    parent_subproject_id: Optional[uuid.UUID] = None
    name:                 str
    code:                 Optional[str] = None
    status:               str
    display_order:        int
    description:          Optional[str] = None
    objectives:           Optional[str] = None
    activities:           Optional[Dict[str, Any]] = None
    expected_outputs:     Optional[str] = None
    start_date:           Optional[date] = None
    end_date:             Optional[date] = None
    actual_start_date:    Optional[date] = None
    actual_end_date:      Optional[date] = None
    budget_amount:        Optional[float] = None
    currency_code:        Optional[str] = None
    address_id:           Optional[uuid.UUID] = None
    in_charges:           List[SubProjectInChargeResponse] = []
    children:             List["SubProjectResponse"] = []
    created_at:           datetime
    updated_at:           datetime


SubProjectResponse.model_rebuild()


# ─────────────────────────────────────────────────────────────────────────────
# OrgProjectStageInCharge
# ─────────────────────────────────────────────────────────────────────────────

class CreateStageInChargeRequest(BaseModel):
    user_id:    uuid.UUID
    role_title: str = Field(max_length=200)
    duties:     Optional[str] = None
    is_lead:    bool = False


class StageInChargeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id:          uuid.UUID
    stage_id:    uuid.UUID
    user_id:     uuid.UUID
    role_title:  str
    duties:      Optional[str] = None
    is_lead:     bool
    assigned_at: datetime
    relieved_at: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# OrgProjectStage
# ─────────────────────────────────────────────────────────────────────────────

class CreateStageRequest(BaseModel):
    name:                str = Field(max_length=255)
    stage_order:         int = Field(ge=1, description="1-based position. Determines sequence.")
    description:         Optional[str] = None
    objectives:          Optional[str] = None
    deliverables:        Optional[str] = None
    start_date:          Optional[date] = None
    end_date:            Optional[date] = None
    # Per-stage feedback gates (null = inherit from project)
    accepts_grievances:  Optional[bool] = None
    accepts_suggestions: Optional[bool] = None
    accepts_applause:    Optional[bool] = None


class UpdateStageRequest(BaseModel):
    name:                Optional[str] = Field(default=None, max_length=255)
    stage_order:         Optional[int] = Field(default=None, ge=1)
    description:         Optional[str] = None
    objectives:          Optional[str] = None
    deliverables:        Optional[str] = None
    start_date:          Optional[date] = None
    end_date:            Optional[date] = None
    actual_start_date:   Optional[date] = None
    actual_end_date:     Optional[date] = None
    accepts_grievances:  Optional[bool] = None
    accepts_suggestions: Optional[bool] = None
    accepts_applause:    Optional[bool] = None


class StageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id:                  uuid.UUID
    project_id:          uuid.UUID
    name:                str
    stage_order:         int
    status:              str
    description:         Optional[str] = None
    objectives:          Optional[str] = None
    deliverables:        Optional[str] = None
    start_date:          Optional[date] = None
    end_date:            Optional[date] = None
    actual_start_date:   Optional[date] = None
    actual_end_date:     Optional[date] = None
    accepts_grievances:  Optional[bool] = None
    accepts_suggestions: Optional[bool] = None
    accepts_applause:    Optional[bool] = None
    in_charges:          List[StageInChargeResponse] = []
    sub_projects:        List[SubProjectResponse] = []
    created_at:          datetime

    @field_validator("in_charges", "sub_projects", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return v if v is not None else []
    updated_at:          datetime


# ─────────────────────────────────────────────────────────────────────────────
# OrgProjectInCharge
# ─────────────────────────────────────────────────────────────────────────────

class CreateProjectInChargeRequest(BaseModel):
    user_id:    uuid.UUID
    role_title: str = Field(max_length=200)
    duties:     Optional[str] = None
    is_lead:    bool = False


class ProjectInChargeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id:          uuid.UUID
    project_id:  uuid.UUID
    user_id:     uuid.UUID
    role_title:  str
    duties:      Optional[str] = None
    is_lead:     bool
    assigned_at: datetime
    relieved_at: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# OrgProject
# ─────────────────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    """Fields required/accepted when creating a new execution project."""

    name:       str = Field(max_length=255)
    code:       Optional[str] = Field(
        default=None, max_length=50,
        description="Short internal code e.g. 'MVDP', 'RISE', 'TACTICS'. Must be globally unique.",
    )
    slug:       str = Field(
        max_length=255,
        description="URL-safe unique identifier. Must be globally unique.",
    )
    # Optionally scoped to a specific branch
    branch_id:  Optional[uuid.UUID] = None
    # Optional link to an OrgService marketplace listing
    org_service_id: Optional[uuid.UUID] = None

    # Classification
    visibility: str = Field(default="public", description="public | org_only | private")
    category:   Optional[str] = Field(default=None, max_length=100)
    sector:     Optional[str] = Field(default=None, max_length=100)

    # Narrative
    description:           Optional[str] = None
    background:            Optional[str] = None
    objectives:            Optional[str] = None
    expected_outcomes:     Optional[str] = None
    target_beneficiaries:  Optional[str] = None

    # Timeline
    start_date: Optional[date] = None
    end_date:   Optional[date] = None

    # Budget
    budget_amount:  Optional[float] = None
    currency_code:  Optional[str] = Field(default=None, max_length=3)
    funding_source: Optional[str] = Field(default=None, max_length=500)

    # Location
    country_code:         Optional[str] = Field(default=None, max_length=2)
    region:               Optional[str] = Field(default=None, max_length=100)
    primary_lga:          Optional[str] = Field(default=None, max_length=100)
    location_description: Optional[str] = None

    # Media
    cover_image_url: Optional[str] = None
    document_urls:   Optional[Dict[str, Any]] = None

    # Feedback settings
    accepts_grievances:  bool = True
    accepts_suggestions: bool = True
    accepts_applause:    bool = True
    requires_grm:        bool = False


class UpdateProjectRequest(BaseModel):
    """All fields optional — PATCH semantics."""
    name:                  Optional[str] = Field(default=None, max_length=255)
    visibility:            Optional[str] = None
    category:              Optional[str] = Field(default=None, max_length=100)
    sector:                Optional[str] = Field(default=None, max_length=100)
    description:           Optional[str] = None
    background:            Optional[str] = None
    objectives:            Optional[str] = None
    expected_outcomes:     Optional[str] = None
    target_beneficiaries:  Optional[str] = None
    start_date:            Optional[date] = None
    end_date:              Optional[date] = None
    actual_start_date:     Optional[date] = None
    actual_end_date:       Optional[date] = None
    budget_amount:         Optional[float] = None
    currency_code:         Optional[str] = Field(default=None, max_length=3)
    funding_source:        Optional[str] = None
    country_code:          Optional[str] = Field(default=None, max_length=2)
    region:                Optional[str] = None
    primary_lga:           Optional[str] = None
    location_description:  Optional[str] = None
    cover_image_url:       Optional[str] = None
    document_urls:         Optional[Dict[str, Any]] = None
    accepts_grievances:    Optional[bool] = None
    accepts_suggestions:   Optional[bool] = None
    accepts_applause:      Optional[bool] = None
    requires_grm:          Optional[bool] = None


class ProjectSummaryResponse(BaseModel):
    """
    Lightweight project card — used in list responses and downstream
    service ProjectCache sync payloads.
    """
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id:                uuid.UUID
    organisation_id:   uuid.UUID
    branch_id:         Optional[uuid.UUID] = None
    org_service_id:    Optional[uuid.UUID] = None
    name:              str
    code:              Optional[str] = None
    slug:              str
    status:            str
    visibility:        str
    category:          Optional[str] = None
    sector:            Optional[str] = None
    country_code:      Optional[str] = None
    region:            Optional[str] = None
    primary_lga:       Optional[str] = None
    start_date:        Optional[date] = None
    end_date:          Optional[date] = None
    budget_amount:     Optional[float] = None
    currency_code:     Optional[str] = None
    funding_source:    Optional[str] = None
    accepts_grievances:  bool
    accepts_suggestions: bool
    accepts_applause:    bool
    requires_grm:        bool
    cover_image_url:   Optional[str] = None
    created_at:        datetime
    updated_at:        datetime


class ProjectDetailResponse(ProjectSummaryResponse):
    """
    Full project detail — includes stages (with sub-projects) and in-charges.
    Returned on GET /orgs/{org_id}/projects/{project_id}.
    """
    description:          Optional[str] = None
    background:           Optional[str] = None
    objectives:           Optional[str] = None
    expected_outcomes:    Optional[str] = None
    target_beneficiaries: Optional[str] = None
    location_description: Optional[str] = None
    document_urls:        Optional[Dict[str, Any]] = None
    actual_start_date:    Optional[date] = None
    actual_end_date:      Optional[date] = None
    deleted_at:           Optional[datetime] = None
    in_charges:           List[ProjectInChargeResponse] = []
    stages:               List[StageResponse] = []

    @field_validator("in_charges", "stages", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return v if v is not None else []


# ─────────────────────────────────────────────────────────────────────────────
# Project / Sub-project Progress Images
# ─────────────────────────────────────────────────────────────────────────────

class UploadProgressImageRequest(BaseModel):
    """
    Metadata submitted alongside the image file (as multipart/form-data fields).

    The file itself is passed as the `file` parameter (UploadFile).
    These fields are form fields — not JSON body — because multipart requests
    mix file bytes with text fields.

    Notes
    ─────
    · `title` is required — it is the progress note that makes the image
      useful in reports and World Bank supervision documents.
    · `phase` must be one of: before | during | after | other.
    · `captured_at` is the ISO 8601 datetime when the photo was taken.
      If omitted, the upload timestamp is used for ordering.
    · `display_order` controls manual ordering within a phase gallery (0 = first).
    """
    title:                str            = Field(
        max_length=300,
        description="Short descriptive title. Required. "
                    "e.g. 'Jangwani Bridge North Abutment — Before Works'.",
    )
    phase:                str            = Field(
        default="during",
        description="Progress phase: before | during | after | other.",
    )
    description:          Optional[str]  = Field(
        default=None,
        description="Detailed description of what is shown. "
                    "Used in progress reports and supervision mission documents.",
    )
    display_order:        int            = Field(
        default=0,
        description="Manual ordering within the phase gallery. Lower = shown first.",
    )
    location_description: Optional[str]  = Field(
        default=None, max_length=300,
        description="Where the photo was taken. "
                    "e.g. 'Chalinze–Segera Road KM 24+300'.",
    )
    gps_lat:              Optional[float] = Field(
        default=None,
        description="GPS latitude in decimal degrees.",
    )
    gps_lng:              Optional[float] = Field(
        default=None,
        description="GPS longitude in decimal degrees.",
    )
    captured_at:          Optional[str]  = Field(
        default=None,
        description="ISO 8601 datetime when the photo was taken. "
                    "May differ from upload time (e.g. field photo uploaded later).",
    )


class UpdateProgressImageRequest(BaseModel):
    """
    PATCH body for updating image metadata.

    All fields optional. Cannot replace the image file — delete the record
    and re-upload to change the image itself.
    """
    title:                Optional[str]   = Field(default=None, max_length=300)
    phase:                Optional[str]   = Field(
        default=None,
        description="before | during | after | other",
    )
    description:          Optional[str]   = None
    display_order:        Optional[int]   = None
    location_description: Optional[str]   = Field(default=None, max_length=300)
    gps_lat:              Optional[float] = None
    gps_lng:              Optional[float] = None
    captured_at:          Optional[str]   = Field(
        default=None,
        description="ISO 8601 datetime. Pass null to clear.",
    )


class ProgressImageResponse(BaseModel):
    """
    Single progress image record — returned on upload, GET, and PATCH.

    `phase_counts` is NOT included here — it is part of the list response
    (ProgressImageListResponse) to avoid the overhead on single-item fetches.
    """
    model_config = ConfigDict(from_attributes=False)

    id:                   uuid.UUID
    entity_type:          str             # "project" | "subproject"
    entity_id:            uuid.UUID
    image_url:            str
    thumbnail_url:        Optional[str]   = None
    phase:                str             # before | during | after | other
    title:                str
    description:          Optional[str]   = None
    display_order:        int
    location_description: Optional[str]   = None
    gps_lat:              Optional[float] = None
    gps_lng:              Optional[float] = None
    captured_at:          Optional[datetime] = None
    uploaded_at:          datetime
    uploaded_by_user_id:  Optional[uuid.UUID] = None

    @classmethod
    def from_dict(cls, d: dict) -> "ProgressImageResponse":
        """Construct from the dict returned by ProjectImageService."""
        return cls(
            id=uuid.UUID(d["id"]),
            entity_type=d["entity_type"],
            entity_id=uuid.UUID(d["entity_id"]),
            image_url=d["image_url"],
            thumbnail_url=d.get("thumbnail_url"),
            phase=d["phase"],
            title=d["title"],
            description=d.get("description"),
            display_order=d["display_order"],
            location_description=d.get("location_description"),
            gps_lat=d.get("gps_lat"),
            gps_lng=d.get("gps_lng"),
            captured_at=datetime.fromisoformat(d["captured_at"]) if d.get("captured_at") else None,
            uploaded_at=datetime.fromisoformat(d["uploaded_at"]),
            uploaded_by_user_id=uuid.UUID(d["uploaded_by_user_id"]) if d.get("uploaded_by_user_id") else None,
        )


class ProgressImageListResponse(BaseModel):
    """
    Paginated gallery response.

    `phase_counts` gives the count per phase so the client can render
    "Before (3) | During (12) | After (5)" tab headers in one request.
    """
    model_config = ConfigDict(from_attributes=False)

    entity_type:  str
    entity_id:    uuid.UUID
    phase_filter: Optional[str]                  = None
    total:        int
    returned:     int
    phase_counts: Dict[str, int]                 = {}
    items:        List[ProgressImageResponse]    = []

    @classmethod
    def from_dict(cls, d: dict) -> "ProgressImageListResponse":
        return cls(
            entity_type=d["entity_type"],
            entity_id=uuid.UUID(d["entity_id"]),
            phase_filter=d.get("phase_filter"),
            total=d["total"],
            returned=d["returned"],
            phase_counts=d.get("phase_counts", {}),
            items=[ProgressImageResponse.from_dict(i) for i in d["items"]],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Project / Stage / Sub-project Checklist
# ─────────────────────────────────────────────────────────────────────────────

_CHECKLIST_ENTITY_TYPES = {"project", "stage", "subproject"}
_CHECKLIST_STATUSES     = {"pending", "in_progress", "done", "skipped", "blocked"}


class CreateChecklistItemRequest(BaseModel):
    """
    Body for POST .../checklist — add an item to a project, stage,
    or sub-project checklist.

    Only `title` is required.  All other fields are optional but recommended
    for meaningful progress tracking and World Bank reporting.
    """
    title: str = Field(
        max_length=500,
        description=(
            "Short actionable label. Required. "
            "e.g. 'Submit Environmental Impact Assessment' or "
            "'Obtain works permit from TANROADS'."
        ),
    )
    description: Optional[str] = Field(
        default=None,
        description=(
            "Additional context, acceptance criteria, or step-by-step "
            "instructions for completing this item."
        ),
    )
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description=(
            "Optional grouping label for filtering and display. "
            "e.g. 'Permits', 'Site Preparation', 'Community Engagement'."
        ),
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Target completion date. ISO 8601 format: '2025-06-15'.",
    )
    assigned_to_user_id: Optional[uuid.UUID] = Field(
        default=None,
        description="User responsible for completing this item.",
    )
    display_order: int = Field(
        default=0,
        description="Manual ordering within the checklist. Lower = shown first.",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank.")
        return v


class UpdateChecklistItemRequest(BaseModel):
    """
    Body for PATCH .../checklist/{item_id} — all fields optional.

    Status transition rules (enforced by the service):
      · status → DONE:    completion_date is auto-set to today if not provided.
      · status → SKIPPED: skip_reason becomes required.
      · status → BLOCKED: skip_reason becomes required.
    """
    title:       Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    category:    Optional[str] = Field(default=None, max_length=100)
    status:      Optional[str] = Field(
        default=None,
        description="pending | in_progress | done | skipped | blocked",
    )
    due_date:         Optional[str] = Field(
        default=None, description="ISO 8601 date e.g. '2025-06-15'. Pass null to clear.")
    completion_date:  Optional[str] = Field(
        default=None, description="ISO 8601 date. Auto-set to today when status → done.")
    assigned_to_user_id: Optional[uuid.UUID] = None
    completion_note:          Optional[str] = Field(
        default=None,
        description="What was done / outcome notes. Strongly recommended when marking DONE.",
    )
    completion_evidence_url:  Optional[str] = Field(
        default=None, max_length=1024,
        description="URL to supporting evidence (photo, signed permit, report) in MinIO/S3.",
    )
    skip_reason: Optional[str] = Field(
        default=None, max_length=500,
        description="Required when status = 'skipped' or 'blocked'.",
    )
    display_order: Optional[int] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in _CHECKLIST_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_CHECKLIST_STATUSES)}, got '{v}'."
            )
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("title must not be blank.")
        return v


class MarkDoneRequest(BaseModel):
    """
    Body for POST .../checklist/{item_id}/done — convenience endpoint.
    Sets status to DONE in one call without a full PATCH body.
    """
    completion_note:         Optional[str] = Field(
        default=None,
        description="What was accomplished. Strongly recommended for audit trail.",
    )
    completion_evidence_url: Optional[str] = Field(
        default=None, max_length=1024,
        description="URL to supporting evidence file in MinIO/S3.",
    )
    completion_date: Optional[str] = Field(
        default=None,
        description="ISO 8601 date. Defaults to today if not provided.",
    )


class ReorderChecklistRequest(BaseModel):
    """
    Body for PUT .../checklist/reorder — update display_order for multiple
    items in one request. Designed for drag-and-drop UI reordering.
    """
    order: List[Dict[str, Any]] = Field(
        description=(
            'List of {"id": "uuid", "display_order": int} entries. '
            "All items in the list will have their display_order updated atomically."
        ),
        min_length=1,
    )


class ChecklistProgressResponse(BaseModel):
    """
    Lightweight progress summary — used in dashboard cards and stage
    completion gates without fetching the full item list.
    """
    model_config = ConfigDict(from_attributes=False)

    entity_type:      str
    entity_id:        uuid.UUID
    total:            int
    done:             int
    in_progress:      int
    pending:          int
    skipped:          int
    blocked:          int
    percent_complete: float  # 0.0–100.0, skipped items excluded from denominator

    @classmethod
    def from_dict(cls, d: dict) -> "ChecklistProgressResponse":
        return cls(
            entity_type=d["entity_type"],
            entity_id=uuid.UUID(d["entity_id"]),
            total=d["total"],
            done=d["done"],
            in_progress=d["in_progress"],
            pending=d["pending"],
            skipped=d["skipped"],
            blocked=d["blocked"],
            percent_complete=d["percent_complete"],
        )


class ChecklistItemResponse(BaseModel):
    """Serialised ProjectChecklistItem row."""
    model_config = ConfigDict(from_attributes=False)

    id:                      uuid.UUID
    entity_type:             str
    entity_id:               uuid.UUID
    title:                   str
    description:             Optional[str]      = None
    category:                Optional[str]      = None
    status:                  str
    due_date:                Optional[date]     = None
    completion_date:         Optional[date]     = None
    assigned_to_user_id:     Optional[uuid.UUID] = None
    completion_note:         Optional[str]      = None
    completion_evidence_url: Optional[str]      = None
    skip_reason:             Optional[str]      = None
    display_order:           int
    created_by_user_id:      Optional[uuid.UUID] = None
    updated_by_user_id:      Optional[uuid.UUID] = None
    created_at:              datetime
    updated_at:              datetime

    @classmethod
    def from_dict(cls, d: dict) -> "ChecklistItemResponse":
        return cls(
            id=uuid.UUID(d["id"]),
            entity_type=d["entity_type"],
            entity_id=uuid.UUID(d["entity_id"]),
            title=d["title"],
            description=d.get("description"),
            category=d.get("category"),
            status=d["status"],
            due_date=date.fromisoformat(d["due_date"]) if d.get("due_date") else None,
            completion_date=date.fromisoformat(d["completion_date"]) if d.get("completion_date") else None,
            assigned_to_user_id=uuid.UUID(d["assigned_to_user_id"]) if d.get("assigned_to_user_id") else None,
            completion_note=d.get("completion_note"),
            completion_evidence_url=d.get("completion_evidence_url"),
            skip_reason=d.get("skip_reason"),
            display_order=d["display_order"],
            created_by_user_id=uuid.UUID(d["created_by_user_id"]) if d.get("created_by_user_id") else None,
            updated_by_user_id=uuid.UUID(d["updated_by_user_id"]) if d.get("updated_by_user_id") else None,
            created_at=datetime.fromisoformat(d["created_at"]),
            updated_at=datetime.fromisoformat(d["updated_at"]),
        )


class ChecklistListResponse(BaseModel):
    """
    Paginated checklist response — includes full progress summary
    so the client can render progress bars from a single request.
    """
    model_config = ConfigDict(from_attributes=False)

    entity_type:  str
    entity_id:    uuid.UUID
    total:        int
    returned:     int
    progress:     ChecklistProgressResponse
    items:        List[ChecklistItemResponse] = []

    @classmethod
    def from_dict(cls, d: dict) -> "ChecklistListResponse":
        return cls(
            entity_type=d["entity_type"],
            entity_id=uuid.UUID(d["entity_id"]),
            total=d["total"],
            returned=d["returned"],
            progress=ChecklistProgressResponse.from_dict({
                **d["progress"],
                "entity_type": d["entity_type"],
                "entity_id":   d["entity_id"],
            }),
            items=[ChecklistItemResponse.from_dict(i) for i in d["items"]],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Checklist Performance Reports
# ─────────────────────────────────────────────────────────────────────────────

class ChecklistStatsBlock(BaseModel):
    """
    Reusable checklist statistics block embedded in performance rows.
    Included in every performance row and in summary blocks.
    """
    model_config = ConfigDict(from_attributes=False)

    total:            int
    done:             int
    in_progress:      int
    pending:          int
    skipped:          int
    blocked:          int
    overdue:          int   # due_date < today AND status not done/skipped
    percent_complete: float  # excludes skipped+blocked from denominator


class ChecklistPerformanceRow(BaseModel):
    """
    A single row in the project-level performance report.
    One row per entity (project, stage, or subproject).

    Provides full context — entity name, status, project location,
    stage context — alongside the checklist stats block.
    """
    model_config = ConfigDict(from_attributes=False)

    # Entity identity
    entity_type:   str            # "project" | "stage" | "subproject"
    entity_id:     uuid.UUID
    entity_name:   str
    entity_status: str            # project/stage/subproject status value
    entity_code:   Optional[str] = None   # project code or subproject code

    # Project context (always present — provides location)
    project_id:          uuid.UUID
    project_name:        str
    project_slug:        str
    project_status:      str
    project_region:      Optional[str] = None
    project_lga:         Optional[str] = None
    project_country_code: Optional[str] = None
    project_location_description: Optional[str] = None

    # Stage context (present for stage and subproject rows)
    stage_id:    Optional[uuid.UUID] = None
    stage_name:  Optional[str]       = None
    stage_order: Optional[int]       = None

    # Checklist statistics
    total:            int
    done:             int
    in_progress:      int
    pending:          int
    skipped:          int
    blocked:          int
    overdue:          int
    percent_complete: float

    @classmethod
    def from_dict(cls, d: dict) -> "ChecklistPerformanceRow":
        return cls(
            entity_type   = d["entity_type"],
            entity_id     = uuid.UUID(d["entity_id"]),
            entity_name   = d["entity_name"],
            entity_status = d["entity_status"],
            entity_code   = d.get("entity_code"),
            project_id    = uuid.UUID(d["project_id"]),
            project_name  = d["project_name"],
            project_slug  = d["project_slug"],
            project_status= d["project_status"],
            project_region= d.get("project_region"),
            project_lga   = d.get("project_lga"),
            project_country_code = d.get("project_country_code"),
            project_location_description = d.get("project_location_description"),
            stage_id    = uuid.UUID(d["stage_id"])  if d.get("stage_id")   else None,
            stage_name  = d.get("stage_name"),
            stage_order = d.get("stage_order"),
            total           = d["total"],
            done            = d["done"],
            in_progress     = d["in_progress"],
            pending         = d["pending"],
            skipped         = d["skipped"],
            blocked         = d["blocked"],
            overdue         = d["overdue"],
            percent_complete= d["percent_complete"],
        )


class ChecklistSummaryBlock(BaseModel):
    """Rolled-up totals across all rows in a performance report."""
    model_config = ConfigDict(from_attributes=False)

    total_items:      int
    done_items:       int
    overdue_items:    int
    percent_complete: float


class ChecklistPerformanceReport(BaseModel):
    """
    Full performance report for one project.

    Contains one row per entity (project + stages + sub-projects) so the
    client can render a hierarchical breakdown — overall project progress
    at the top, then each stage, then each sub-project within that stage.

    `summary` gives the aggregate across all rows for a top-level progress bar.
    `rows` is ordered: project row first, then stages in order,
    then sub-projects within each stage.
    """
    model_config = ConfigDict(from_attributes=False)

    project_id: uuid.UUID
    summary:    ChecklistSummaryBlock
    rows:       List[ChecklistPerformanceRow] = []

    @classmethod
    def from_dict(cls, d: dict) -> "ChecklistPerformanceReport":
        s = d["summary"]
        return cls(
            project_id = uuid.UUID(d["project_id"]),
            summary    = ChecklistSummaryBlock(
                total_items      = s["total_items"],
                done_items       = s["done_items"],
                overdue_items    = s["overdue_items"],
                percent_complete = s["percent_complete"],
            ),
            rows = [ChecklistPerformanceRow.from_dict(r) for r in d["rows"]],
        )


class OrgChecklistPerformanceRow(BaseModel):
    """
    One summary row per project in the organisation-level performance report.
    Aggregates all checklists (project + stages + subprojects) per project.
    """
    model_config = ConfigDict(from_attributes=False)

    project_id:           uuid.UUID
    project_name:         str
    project_slug:         str
    project_status:       str
    project_code:         Optional[str]  = None
    project_region:       Optional[str]  = None
    project_lga:          Optional[str]  = None
    project_country_code: Optional[str]  = None
    project_location_description: Optional[str] = None
    project_start_date:   Optional[date] = None
    project_end_date:     Optional[date] = None

    # Aggregated checklist stats (all entity levels combined)
    total:            int
    done:             int
    in_progress:      int
    pending:          int
    skipped:          int
    blocked:          int
    overdue:          int
    percent_complete: float

    @classmethod
    def from_dict(cls, d: dict) -> "OrgChecklistPerformanceRow":
        return cls(
            project_id    = uuid.UUID(d["project_id"]),
            project_name  = d["project_name"],
            project_slug  = d["project_slug"],
            project_status= d["project_status"],
            project_code  = d.get("project_code"),
            project_region= d.get("project_region"),
            project_lga   = d.get("project_lga"),
            project_country_code = d.get("project_country_code"),
            project_location_description = d.get("project_location_description"),
            project_start_date = date.fromisoformat(d["project_start_date"]) if d.get("project_start_date") else None,
            project_end_date   = date.fromisoformat(d["project_end_date"])   if d.get("project_end_date")   else None,
            total           = d["total"],
            done            = d["done"],
            in_progress     = d["in_progress"],
            pending         = d["pending"],
            skipped         = d["skipped"],
            blocked         = d["blocked"],
            overdue         = d["overdue"],
            percent_complete= d["percent_complete"],
        )


class OrgChecklistSummaryBlock(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    total_projects:   int
    total_items:      int
    done_items:       int
    overdue_items:    int
    percent_complete: float


class OrgChecklistPerformanceReport(BaseModel):
    """
    Organisation-level checklist performance report.

    One row per project. Useful for a portfolio dashboard showing
    which projects are on track, behind, or blocked.
    """
    model_config = ConfigDict(from_attributes=False)

    org_id:  uuid.UUID
    summary: OrgChecklistSummaryBlock
    rows:    List[OrgChecklistPerformanceRow] = []

    @classmethod
    def from_dict(cls, d: dict) -> "OrgChecklistPerformanceReport":
        s = d["summary"]
        return cls(
            org_id  = uuid.UUID(d["org_id"]),
            summary = OrgChecklistSummaryBlock(
                total_projects   = s["total_projects"],
                total_items      = s["total_items"],
                done_items       = s["done_items"],
                overdue_items    = s["overdue_items"],
                percent_complete = s["percent_complete"],
            ),
            rows = [OrgChecklistPerformanceRow.from_dict(r) for r in d["rows"]],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Stage-level Performance Report schemas
# ─────────────────────────────────────────────────────────────────────────────

class StageChecklistPerformanceRow(BaseModel):
    """
    One row in the stage-level performance report.
    First row is the stage itself; subsequent rows are its sub-projects.

    Sub-project rows carry full sub-project context (dates, budget, objectives)
    so no further requests are needed to render a complete breakdown.
    """
    model_config = ConfigDict(from_attributes=False)

    # Entity identity
    entity_type:   str            # "stage" | "subproject"
    entity_id:     uuid.UUID
    entity_name:   str
    entity_status: str
    entity_code:   Optional[str] = None

    # Stage context (always present)
    stage_order:              Optional[int]  = None
    stage_start_date:         Optional[date] = None
    stage_end_date:           Optional[date] = None
    stage_actual_start_date:  Optional[date] = None
    stage_actual_end_date:    Optional[date] = None
    stage_objectives:         Optional[str]  = None
    stage_deliverables:       Optional[str]  = None   # stage only

    # Sub-project extra fields (present on subproject rows only)
    parent_subproject_id:         Optional[uuid.UUID] = None
    subproject_start_date:        Optional[date] = None
    subproject_end_date:          Optional[date] = None
    subproject_actual_start_date: Optional[date] = None
    subproject_actual_end_date:   Optional[date] = None
    subproject_objectives:        Optional[str]  = None
    subproject_expected_outputs:  Optional[str]  = None
    subproject_budget_amount:     Optional[float] = None
    subproject_currency_code:     Optional[str]   = None

    # Project context (location, name — always present)
    project_id:          uuid.UUID
    project_name:        Optional[str] = None
    project_slug:        Optional[str] = None
    project_status:      Optional[str] = None
    project_region:      Optional[str] = None
    project_lga:         Optional[str] = None
    project_country_code: Optional[str] = None
    project_location_description: Optional[str] = None

    # Checklist statistics
    total:            int
    done:             int
    in_progress:      int
    pending:          int
    skipped:          int
    blocked:          int
    overdue:          int
    percent_complete: float

    @classmethod
    def from_dict(cls, d: dict) -> "StageChecklistPerformanceRow":
        def _d(key): return date.fromisoformat(d[key]) if d.get(key) else None
        return cls(
            entity_type   = d["entity_type"],
            entity_id     = uuid.UUID(d["entity_id"]),
            entity_name   = d["entity_name"],
            entity_status = d["entity_status"],
            entity_code   = d.get("entity_code"),
            stage_order   = d.get("stage_order"),
            stage_start_date        = _d("stage_start_date"),
            stage_end_date          = _d("stage_end_date"),
            stage_actual_start_date = _d("stage_actual_start_date"),
            stage_actual_end_date   = _d("stage_actual_end_date"),
            stage_objectives   = d.get("stage_objectives"),
            stage_deliverables = d.get("stage_deliverables"),
            parent_subproject_id = uuid.UUID(d["parent_subproject_id"]) if d.get("parent_subproject_id") else None,
            subproject_start_date        = _d("subproject_start_date"),
            subproject_end_date          = _d("subproject_end_date"),
            subproject_actual_start_date = _d("subproject_actual_start_date"),
            subproject_actual_end_date   = _d("subproject_actual_end_date"),
            subproject_objectives        = d.get("subproject_objectives"),
            subproject_expected_outputs  = d.get("subproject_expected_outputs"),
            subproject_budget_amount     = d.get("subproject_budget_amount"),
            subproject_currency_code     = d.get("subproject_currency_code"),
            project_id    = uuid.UUID(d["project_id"]),
            project_name  = d.get("project_name"),
            project_slug  = d.get("project_slug"),
            project_status= d.get("project_status"),
            project_region= d.get("project_region"),
            project_lga   = d.get("project_lga"),
            project_country_code = d.get("project_country_code"),
            project_location_description = d.get("project_location_description"),
            total            = d["total"],
            done             = d["done"],
            in_progress      = d["in_progress"],
            pending          = d["pending"],
            skipped          = d["skipped"],
            blocked          = d["blocked"],
            overdue          = d["overdue"],
            percent_complete = d["percent_complete"],
        )


class StageSummaryBlock(BaseModel):
    """Stage context + aggregate checklist stats."""
    model_config = ConfigDict(from_attributes=False)

    stage_id:          uuid.UUID
    stage_name:        Optional[str] = None
    stage_order:       Optional[int] = None
    stage_start_date:  Optional[date] = None
    stage_end_date:    Optional[date] = None
    project_id:        Optional[uuid.UUID] = None
    project_name:      Optional[str] = None
    project_region:    Optional[str] = None
    project_lga:       Optional[str] = None
    total_items:       int
    done_items:        int
    overdue_items:     int
    percent_complete:  float


class StageChecklistPerformanceReport(BaseModel):
    """
    Checklist performance for a single stage.

    `summary` — aggregate counts for the whole stage (all entities combined).
    `rows`    — first row is the stage itself, then one row per sub-project.

    Filter params in the API allow restricting rows to only sub-projects,
    or to a specific status.
    """
    model_config = ConfigDict(from_attributes=False)

    stage_id: uuid.UUID
    summary:  StageSummaryBlock
    rows:     List[StageChecklistPerformanceRow] = []

    @classmethod
    def from_dict(cls, d: dict) -> "StageChecklistPerformanceReport":
        s = d["summary"]
        return cls(
            stage_id = uuid.UUID(d["stage_id"]),
            summary  = StageSummaryBlock(
                stage_id        = uuid.UUID(d["stage_id"]),
                stage_name      = d.get("stage_name"),
                stage_order     = d.get("stage_order"),
                stage_start_date= date.fromisoformat(d["stage_start_date"]) if d.get("stage_start_date") else None,
                stage_end_date  = date.fromisoformat(d["stage_end_date"]) if d.get("stage_end_date") else None,
                project_id      = uuid.UUID(d["project_id"]) if d.get("project_id") else None,
                project_name    = d.get("project_name"),
                project_region  = d.get("project_region"),
                project_lga     = d.get("project_lga"),
                total_items     = s["total_items"],
                done_items      = s["done_items"],
                overdue_items   = s["overdue_items"],
                percent_complete= s["percent_complete"],
            ),
            rows = [StageChecklistPerformanceRow.from_dict(r) for r in d["rows"]],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Sub-project-level Performance Report schema
# ─────────────────────────────────────────────────────────────────────────────

class SubProjectChecklistPerformanceReport(BaseModel):
    """
    Checklist performance for a single sub-project.

    A single-entity report — no row list, just the sub-project itself
    with full context: stage, parent project, location, dates, budget,
    and checklist stats.

    Use when you need to drill down into one work package specifically.
    """
    model_config = ConfigDict(from_attributes=False)

    # Sub-project identity
    entity_type:   str   = "subproject"
    entity_id:     uuid.UUID
    entity_name:   str
    entity_status: str
    entity_code:   Optional[str]  = None
    display_order: Optional[int]  = None
    parent_subproject_id: Optional[uuid.UUID] = None

    # Sub-project timeline & scope
    subproject_start_date:        Optional[date] = None
    subproject_end_date:          Optional[date] = None
    subproject_actual_start_date: Optional[date] = None
    subproject_actual_end_date:   Optional[date] = None
    subproject_objectives:        Optional[str]  = None
    subproject_expected_outputs:  Optional[str]  = None
    subproject_budget_amount:     Optional[float] = None
    subproject_currency_code:     Optional[str]   = None

    # Stage context
    stage_id:         Optional[uuid.UUID] = None
    stage_name:       Optional[str]  = None
    stage_order:      Optional[int]  = None
    stage_status:     Optional[str]  = None
    stage_start_date: Optional[date] = None
    stage_end_date:   Optional[date] = None

    # Project context (location)
    project_id:          uuid.UUID
    project_name:        Optional[str] = None
    project_slug:        Optional[str] = None
    project_status:      Optional[str] = None
    project_region:      Optional[str] = None
    project_lga:         Optional[str] = None
    project_country_code: Optional[str] = None
    project_location_description: Optional[str] = None

    # Checklist statistics
    total:            int
    done:             int
    in_progress:      int
    pending:          int
    skipped:          int
    blocked:          int
    overdue:          int
    percent_complete: float

    @classmethod
    def from_dict(cls, d: dict) -> "SubProjectChecklistPerformanceReport":
        def _d(key): return date.fromisoformat(d[key]) if d.get(key) else None
        return cls(
            entity_id     = uuid.UUID(d["entity_id"]),
            entity_name   = d["entity_name"],
            entity_status = d["entity_status"],
            entity_code   = d.get("entity_code"),
            display_order = d.get("display_order"),
            parent_subproject_id = uuid.UUID(d["parent_subproject_id"]) if d.get("parent_subproject_id") else None,
            subproject_start_date        = _d("subproject_start_date"),
            subproject_end_date          = _d("subproject_end_date"),
            subproject_actual_start_date = _d("subproject_actual_start_date"),
            subproject_actual_end_date   = _d("subproject_actual_end_date"),
            subproject_objectives        = d.get("subproject_objectives"),
            subproject_expected_outputs  = d.get("subproject_expected_outputs"),
            subproject_budget_amount     = d.get("subproject_budget_amount"),
            subproject_currency_code     = d.get("subproject_currency_code"),
            stage_id         = uuid.UUID(d["stage_id"]) if d.get("stage_id") else None,
            stage_name       = d.get("stage_name"),
            stage_order      = d.get("stage_order"),
            stage_status     = d.get("stage_status"),
            stage_start_date = _d("stage_start_date"),
            stage_end_date   = _d("stage_end_date"),
            project_id    = uuid.UUID(d["project_id"]),
            project_name  = d.get("project_name"),
            project_slug  = d.get("project_slug"),
            project_status= d.get("project_status"),
            project_region= d.get("project_region"),
            project_lga   = d.get("project_lga"),
            project_country_code = d.get("project_country_code"),
            project_location_description = d.get("project_location_description"),
            total            = d["total"],
            done             = d["done"],
            in_progress      = d["in_progress"],
            pending          = d["pending"],
            skipped          = d["skipped"],
            blocked          = d["blocked"],
            overdue          = d["overdue"],
            percent_complete = d["percent_complete"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Kafka event payload schemas
# ─────────────────────────────────────────────────────────────────────────────

class ProjectEventPayload(BaseModel):
    """
    Standard payload published on riviwa.org.events for any project lifecycle
    event. Downstream services (stakeholder_service, feedback_service) use
    these fields to upsert / update their local ProjectCache.

    Field mapping to ProjectCache:
      id               → ProjectCache.id
      organisation_id  → ProjectCache.organisation_id
      branch_id        → ProjectCache.branch_id
      name / slug      → mirrored
      status           → ProjectCache.status
      category / sector → mirrored
      country_code / region / primary_lga → mirrored
      accepts_*        → ProjectCache.accepts_grievances/suggestions/applause
    """
    model_config = ConfigDict(frozen=True)

    id:                  str  # UUID as string — safe across service boundaries
    organisation_id:     str
    branch_id:           Optional[str] = None
    org_service_id:      Optional[str] = None
    name:                str
    slug:                str
    status:              str
    category:            Optional[str] = None
    sector:              Optional[str] = None
    description:         Optional[str] = None
    country_code:        Optional[str] = None
    region:              Optional[str] = None
    primary_lga:         Optional[str] = None
    start_date:          Optional[str] = None  # ISO date string
    end_date:            Optional[str] = None
    accepts_grievances:  bool
    accepts_suggestions: bool
    accepts_applause:    bool
    requires_grm:        bool
    # ── Media — synced to ProjectCache in downstream services ──────────────
    cover_image_url:     Optional[str] = None
    org_logo_url:        Optional[str] = None


class StageEventPayload(BaseModel):
    """
    Payload published when a project stage changes status.
    Downstream services update their ProjectStageCache on receipt.

    Field mapping to ProjectStageCache:
      stage_id    → ProjectStageCache.id
      project_id  → ProjectStageCache.project_id
      name        → mirrored
      stage_order → mirrored
      status      → ProjectStageCache.status
      accepts_*   → stage-level override flags (null = inherit from project)
    """
    model_config = ConfigDict(frozen=True)

    stage_id:            str   # OrgProjectStage.id as string
    project_id:          str
    organisation_id:     str
    name:                str
    stage_order:         int
    status:              str
    description:         Optional[str] = None
    start_date:          Optional[str] = None
    end_date:            Optional[str] = None
    accepts_grievances:  Optional[bool] = None
    accepts_suggestions: Optional[bool] = None
    accepts_applause:    Optional[bool] = None
