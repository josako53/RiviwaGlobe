"""
models/organisation_extended.py
═══════════════════════════════════════════════════════════════════════════════
Extended Organisation capabilities — layered on top of organisation.py without
modifying the core file beyond adding back-populate hooks.

NEW TABLES (13)
═══════════════════════════════════════════════════════════════════════════════
  org_locations           — physical addresses for an Org or Branch
  org_content             — vision / mission / objectives / policy / T&C
                            (1-to-1 with Organisation)
  org_faqs                — FAQ items on the Organisation's public profile page
  org_branches            — sub-entities with UNLIMITED depth via self-ref FK:
                            Dept of Justice → DoJ for Children → Sub-branch …
  org_branch_managers     — M2M: Users who manage/direct a Branch
  org_services            — service / product / program listing
                            · delivery_mode: PHYSICAL | VIRTUAL | HYBRID
                            · product_format (products only): PHYSICAL | DIGITAL | BOTH
  org_service_personnel   — M2M: Users who lead/supervise/coordinate a service
                            · LEADER     for SERVICE/PROGRAM oversight
                            · SUPERVISOR for PRODUCT quality/fulfilment
                            · COORDINATOR for day-to-day operations
  org_branch_services     — M2M: which services a Branch offers (inherited or own)
  org_service_locations   — WHERE a service operates
                            · is_virtual=False → specific OrgLocation (physical)
                            · is_virtual=True  → no location needed; inherits
                              branch/org address; carries virtual_platform/url
  org_service_media       — images / videos / docs per service listing
  org_service_faqs        — FAQ items per service listing
  org_service_policies    — policy & T&C text blocks per service listing

═══════════════════════════════════════════════════════════════════════════════
FULL RELATIONSHIP MAP
═══════════════════════════════════════════════════════════════════════════════

  Organisation (existing)
    │
    ├── OrgLocation           (organisation_id → organisations.id)
    │     branch_id nullable → if set, belongs to that branch.
    │
    ├── OrgContent            (org_id UNIQUE → organisations.id)  [1-to-1]
    │
    ├── OrgFAQ                (org_id → organisations.id)
    │
    ├── OrgBranch             (organisation_id → organisations.id)
    │     UNLIMITED DEPTH — self-referential parent_branch_id (SET NULL on delete)
    │
    │       US Government (org)
    │         └── Department of State          L1
    │               └── Embassy of Rome        L2
    │                     └── Visa Section     L3
    │         └── Department of Justice        L1
    │               ├── DoJ for Children       L2
    │               │     └── Sub-branch …    L3
    │               ├── DoJ for Students       L2
    │               ├── DoJ for Women          L2
    │               └── DoJ for Refugees       L2
    │
    │   ├── OrgBranchManager  (branch_id, user_id)
    │   └── OrgBranchService  (branch_id, service_id)
    │
    └── OrgService            (organisation_id → organisations.id)
          service_type:    SERVICE | PRODUCT | PROGRAM
          delivery_mode:   PHYSICAL | VIRTUAL | HYBRID
          product_format:  PHYSICAL | DIGITAL | BOTH  (products only)
          │
          ├── OrgServicePersonnel   ← NEW — who leads / supervises this service
          │     (service_id → org_services.id, user_id → users.id)
          │     personnel_role: LEADER | SUPERVISOR | COORDINATOR
          │     personnel_title: free-text "Programme Director", "QA Lead" …
          │
          │   LEADER roles:
          │     · OrgService(type=PROGRAM, slug="visa-processing")
          │         → OrgServicePersonnel(user=Alice, role=LEADER,
          │                               title="Visa Programme Director")
          │         → OrgServicePersonnel(user=Bob,   role=COORDINATOR,
          │                               title="Operations Coordinator")
          │
          │   SUPERVISOR roles (products):
          │     · OrgService(type=PRODUCT, slug="laptop-model-x")
          │         → OrgServicePersonnel(user=Carol, role=SUPERVISOR,
          │                               title="Product Quality Supervisor")
          │
          ├── OrgServiceLocation    ← MONITORING TABLE — where it operates
          │     (service_id, branch_id, location_id)
          │     is_virtual = False → physical deployment at location_id
          │     is_virtual = True  → virtual; location_id = NULL;
          │                          inherits branch/org address for display;
          │                          virtual_platform + virtual_url carry access info
          │
          │   VIRTUAL EXAMPLE:
          │     "Online Legal Aid" (delivery_mode=VIRTUAL)
          │       OrgServiceLocation(branch=DoJ for Refugees,
          │                          location_id=NULL, is_virtual=True,
          │                          virtual_platform="Zoom",
          │                          virtual_url="https://zoom.us/j/12345")
          │     → Inherits branch's registered address for display purposes.
          │
          │   HYBRID EXAMPLE:
          │     "Visa Processing Program" (delivery_mode=HYBRID)
          │       OrgServiceLocation(branch=Embassy Rome, location=Via Veneto,
          │                          is_virtual=False, status=ACTIVE)
          │       OrgServiceLocation(branch=Embassy Rome, location=NULL,
          │                          is_virtual=True, virtual_platform="Portal",
          │                          virtual_url="https://visaapply.state.gov")
          │
          ├── OrgServiceMedia   (service_id)
          ├── OrgServiceFAQ     (service_id)
          └── OrgServicePolicy  (service_id)

═══════════════════════════════════════════════════════════════════════════════
DELIVERY MODE & LOCATION INHERITANCE RULES
═══════════════════════════════════════════════════════════════════════════════

  delivery_mode = PHYSICAL
    · Must have ≥ 1 OrgServiceLocation with is_virtual=False.
    · If none exist, service layer falls back to branch's primary OrgLocation,
      then to org headquarters. (Enforcement in service layer, not DB.)

  delivery_mode = VIRTUAL
    · OrgServiceLocation rows have is_virtual=True and location_id=NULL.
    · virtual_platform + virtual_url carry access details.
    · For display, service layer reads branch → org address chain.

  delivery_mode = HYBRID
    · Mix of physical (is_virtual=False) and virtual (is_virtual=True) rows.

  PRODUCT physical/digital:
    product_format = PHYSICAL → requires shipping address logic in order service.
    product_format = DIGITAL  → download link / access code; no address needed.
    product_format = BOTH     → buyer selects edition at purchase time.

═══════════════════════════════════════════════════════════════════════════════
PERSONNEL OVERSIGHT RULES
═══════════════════════════════════════════════════════════════════════════════

  SERVICE / PROGRAM:
    LEADER      → strategic ownership of the programme; accountable for KPIs.
    COORDINATOR → day-to-day scheduling, client liaison, reporting.

  PRODUCT:
    SUPERVISOR  → quality assurance, fulfilment oversight, returns/complaints.
    COORDINATOR → inventory coordination, supplier liaison.

  Any service_type can have any personnel_role; the above are recommendations.
  Enforced by convention in the service layer (not at DB level) to allow
  flexibility across org types (Government, Business, NGO, etc.).

  UNIQUE (service_id, user_id, personnel_role):
    A user cannot hold the same role twice on the same service.
    They can hold LEADER + COORDINATOR simultaneously (two rows).

═══════════════════════════════════════════════════════════════════════════════
DESIGN DECISIONS
═══════════════════════════════════════════════════════════════════════════════

1.  UNLIMITED BRANCH DEPTH — self-ref parent_branch_id, SET NULL on delete.
    PostgreSQL WITH RECURSIVE CTE for tree traversal.

2.  OrgServicePersonnel (new) — dedicated personnel table rather than adding
    FK columns to OrgService, because a service can have multiple leaders,
    multiple supervisors, and multiple coordinators simultaneously.
    Unique on (service_id, user_id, personnel_role) lets one user hold
    different roles on the same service.

3.  VIRTUAL vs PHYSICAL in OrgServiceLocation — is_virtual flag on the
    deployment row (not on the service) allows HYBRID services to have
    some physical and some virtual deployments from the same OrgService record.
    location_id is NULL for virtual rows; branch address is inherited in the
    service layer for display / monitoring purposes.

4.  product_format on OrgService — only consulted when service_type=PRODUCT.
    PHYSICAL products imply shipping address requirements in the order service.
    DIGITAL products imply download/access-code fulfilment.

5.  CASCADE CHAINS (unchanged from prior version, extended for new tables):
    OrgService deleted → OrgServicePersonnel CASCADE (new)
    User deleted       → OrgServicePersonnel CASCADE (new)
═══════════════════════════════════════════════════════════════════════════════
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ForeignKey, Column,
    DateTime,
    Enum as SAEnum,
    Text,
    UniqueConstraint,
    text,
)
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.organisation import Organisation
    from models.user import User
    from models.org_project import OrgProject
    from models.department import OrgDepartment


# ═════════════════════════════════════════════════════════════════════════════
# Enums
# ═════════════════════════════════════════════════════════════════════════════

class OrgLocationType(str, Enum):
    HEADQUARTERS = "headquarters"
    BRANCH       = "branch"
    WAREHOUSE    = "warehouse"
    MAILING      = "mailing"
    OTHER        = "other"


class OrgServiceType(str, Enum):
    SERVICE = "service"   # deliverable skill / consultation (Fiverr-style)
    PRODUCT = "product"   # physical or digital good          (Amazon-style)
    PROGRAM = "program"   # assistance / grant program        (Gov / NGO-style)


class OrgServiceStatus(str, Enum):
    DRAFT    = "draft"
    ACTIVE   = "active"
    PAUSED   = "paused"
    ARCHIVED = "archived"


class OrgMediaType(str, Enum):
    IMAGE    = "image"
    VIDEO    = "video"
    DOCUMENT = "document"


class BranchStatus(str, Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"
    CLOSED    = "closed"


class ServiceLocationStatus(str, Enum):
    """Operational status of a service/program at a specific address."""
    ACTIVE    = "active"     # running normally
    SUSPENDED = "suspended"  # temporarily halted at this location
    CLOSED    = "closed"     # permanently discontinued here
    PLANNED   = "planned"    # announced but not yet operating


class ServiceDeliveryMode(str, Enum):
    """
    How a service/program is delivered to its recipients.

    PHYSICAL → in-person only; requires a registered OrgLocation.
               If no explicit OrgServiceLocation exists, the service inherits
               the operating branch location (or org HQ if branch has none).
    VIRTUAL  → fully remote (online meeting, phone, portal, email).
               No OrgLocation needed. virtual_platform / virtual_url carry
               the access details on OrgServiceLocation.
    HYBRID   → both in-person and virtual modes are offered simultaneously.
    """
    PHYSICAL = "physical"
    VIRTUAL  = "virtual"
    HYBRID   = "hybrid"


class ProductFormat(str, Enum):
    """
    Physical vs digital nature of a PRODUCT-type listing.
    Only meaningful when OrgService.service_type == OrgServiceType.PRODUCT.

    PHYSICAL → tangible item; requires shipping / pickup address.
    DIGITAL  → downloadable / streamable; no physical delivery.
    BOTH     → the same product sold in physical and digital editions.
    """
    PHYSICAL = "physical"
    DIGITAL  = "digital"
    BOTH     = "both"


class ServicePersonnelRole(str, Enum):
    """
    The role a User plays in relation to a specific OrgService.

    LEADER      → programme lead / service owner; strategic oversight.
                  Applicable to any service_type, especially SERVICE + PROGRAM.
    SUPERVISOR  → quality / fulfilment supervisor.
                  Applicable primarily to PRODUCT type.
    COORDINATOR → day-to-day operational coordination across all types.
    """
    LEADER      = "leader"
    SUPERVISOR  = "supervisor"
    COORDINATOR = "coordinator"


# ═════════════════════════════════════════════════════════════════════════════
# OrgLocation
# ═════════════════════════════════════════════════════════════════════════════

class OrgLocation(SQLModel, table=True):
    """
    A physical address registered against an Organisation or one of its Branches.

    branch_id = NULL  → address belongs to the Organisation itself
    branch_id = <id>  → address belongs to that specific Branch

    OrgServiceLocation.location_id references rows here to pin a service to
    a precise, pre-registered address.

    Relationship wiring:
      OrgLocation.organisation      ←→  Organisation.locations
      OrgLocation.branch            ←→  OrgBranch.locations
      OrgLocation.service_locations ←→  OrgServiceLocation.location
    """
    __tablename__ = "org_locations"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    organisation_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)
    branch_id: Optional[uuid.UUID] = Field(
    default=None,
    sa_column=Column(
        ForeignKey("org_branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    ),
)
    location_type: OrgLocationType = Field(
        default=OrgLocationType.HEADQUARTERS,
        sa_column=Column(
            SAEnum(OrgLocationType, name="org_location_type"),
            nullable=False,
            index=True,
        ),
    )

    label:        Optional[str] = Field(default=None, max_length=100, nullable=True,
                                        description="Human label e.g. 'Rome HQ', 'North Wing'")
    line1:        str           = Field(max_length=200, nullable=False)
    line2:        Optional[str] = Field(default=None, max_length=200, nullable=True)
    city:         str           = Field(max_length=100, nullable=False)
    state:        Optional[str] = Field(default=None, max_length=100, nullable=True)
    postal_code:  Optional[str] = Field(default=None, max_length=20,  nullable=True)
    country_code: str           = Field(max_length=2,  nullable=False)
    region:       Optional[str] = Field(default=None, max_length=150, nullable=True,
                                        description="Named region e.g. 'Lazio', 'Northern Italy'")
    latitude:     Optional[float] = Field(default=None, nullable=True)
    longitude:    Optional[float] = Field(default=None, nullable=True)
    is_primary:   bool            = Field(default=False, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )

    organisation:      "Organisation"   = Relationship(back_populates="locations")
    branch:            "OrgBranch"      = Relationship(back_populates="locations")
    service_locations: "OrgServiceLocation" = Relationship(
        back_populates="location",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


# ═════════════════════════════════════════════════════════════════════════════
# OrgContent
# ═════════════════════════════════════════════════════════════════════════════

class OrgContent(SQLModel, table=True):
    """
    One row per Organisation (1-to-1 enforced by UNIQUE on org_id).
    All long-form profile text: vision, mission, objectives, policies.

    Relationship wiring:
      OrgContent.organisation  ←→  Organisation.content
    """
    __tablename__ = "org_content"
    __table_args__ = (UniqueConstraint("org_id", name="uq_org_content_org"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    org_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    vision:         Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    mission:        Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    objectives:     Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    global_policy:  Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    terms_of_use:   Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    privacy_policy: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )

    organisation: "Organisation" = Relationship(back_populates="content")


# ═════════════════════════════════════════════════════════════════════════════
# OrgFAQ
# ═════════════════════════════════════════════════════════════════════════════

class OrgFAQ(SQLModel, table=True):
    """
    FAQ items on an Organisation's public profile page.
    For service-specific FAQs see OrgServiceFAQ.

    Relationship wiring:
      OrgFAQ.organisation  ←→  Organisation.faqs
    """
    __tablename__ = "org_faqs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    org_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    question:      str  = Field(sa_column=Column(Text, nullable=False))
    answer:        str  = Field(sa_column=Column(Text, nullable=False))
    display_order: int  = Field(default=0,    nullable=False)
    is_published:  bool = Field(default=True, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )

    organisation: "Organisation" = Relationship(back_populates="faqs")


# ═════════════════════════════════════════════════════════════════════════════
# OrgBranch  — UNLIMITED depth self-referential tree
# ═════════════════════════════════════════════════════════════════════════════

class OrgBranch(SQLModel, table=True):
    """
    A branch, department, division, embassy, clinic or any named sub-entity.

    UNLIMITED DEPTH via self-referential parent_branch_id:

      US Government (org)
        └── Department of Justice        L1  parent_branch_id=NULL
              ├── DoJ for Children       L2  parent_branch_id=<DoJ id>
              │     └── Child Welfare    L3  parent_branch_id=<DoJ Children id>
              ├── DoJ for Students       L2
              ├── DoJ for Women          L2
              └── DoJ for Refugees       L2
                    └── Asylum Processing L3

      US Government (org)
        └── Department of State          L1
              ├── Embassy of Rome        L2
              │     ├── Visa Section     L3
              │     └── Cultural Affairs L3
              └── Embassy of Paris       L2

    parent_branch_id = NULL  → direct child of the Organisation (level 1)
    parent_branch_id = <id>  → child of another OrgBranch (unlimited levels)

    PARENT DELETE BEHAVIOUR: SET NULL — children survive as org-level branches.

    SERVICES: A branch can have its own services (OrgService.branch_id=this),
    inherit parent org services (OrgBranchService.inherited=True), or both.

    SERVICE LOCATIONS: OrgServiceLocation.branch_id records which branch
    runs a service at each specific address — enables ancestor monitoring.

    Relationship wiring:
      OrgBranch.organisation      ←→  Organisation.branches
      OrgBranch.parent_branch     ←→  OrgBranch.child_branches  (self-ref)
      OrgBranch.managers          ←→  OrgBranchManager.branch
      OrgBranch.locations         ←→  OrgLocation.branch
      OrgBranch.branch_services   ←→  OrgBranchService.branch
      OrgBranch.services          ←→  OrgService.branch
      OrgBranch.service_locations ←→  OrgServiceLocation.branch
    """
    __tablename__ = "org_branches"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    organisation_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)
    # SET NULL: children survive parent branch deletion
    parent_branch_id: Optional[uuid.UUID] = Field(
    default=None,
    sa_column=Column(
        ForeignKey("org_branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    ),
)

    name: str = Field(
        max_length=255, nullable=False,
        description="Display name e.g. 'Embassy of Rome', 'DoJ for Refugees'",
    )
    code: Optional[str] = Field(
        default=None, max_length=50, nullable=True, index=True,
        description="Internal code e.g. 'US-IT-ROME-001', 'DOJ-REF'",
    )
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    branch_type: Optional[str] = Field(
        default=None, max_length=100, nullable=True,
        description="Free-text: 'department', 'embassy', 'clinic', 'division' etc.",
    )

    status: BranchStatus = Field(
        default=BranchStatus.ACTIVE,
        sa_column=Column(SAEnum(BranchStatus, name="branch_status"),
                         nullable=False, index=True),
    )

    phone: Optional[str] = Field(default=None, max_length=20,  nullable=True)
    email: Optional[str] = Field(default=None, max_length=255, nullable=True)

    opened_on: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )
    closed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    organisation: "Organisation" = Relationship(back_populates="branches")

    parent_branch: "OrgBranch" = Relationship(
        back_populates="child_branches",
        sa_relationship_kwargs={
            "foreign_keys": "[OrgBranch.parent_branch_id]",
            "remote_side": "OrgBranch.id",
        },
    )
    child_branches: "OrgBranch" = Relationship(
        back_populates="parent_branch",
        sa_relationship_kwargs={"foreign_keys": "[OrgBranch.parent_branch_id]"},
    )

    managers: "OrgBranchManager" = Relationship(
        back_populates="branch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    locations: "OrgLocation" = Relationship(back_populates="branch")
    branch_services: "OrgBranchService" = Relationship(
        back_populates="branch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    services: "OrgService" = Relationship(back_populates="branch")

    # Projects delegated to this branch (e.g. "TARURA DSM" runs "Msimbazi Project")
    projects: "OrgProject" = Relationship(
        back_populates="branch",
        sa_relationship_kwargs={"foreign_keys": "[OrgProject.branch_id]"},
    )
    service_locations: "OrgServiceLocation" = Relationship(
        back_populates="branch"
    )
    # Departments scoped to this specific branch
    departments: "OrgDepartment" = Relationship(back_populates="branch")

    def is_active(self) -> bool:
        return self.status == BranchStatus.ACTIVE

    def __repr__(self) -> str:
        return (
            f"<OrgBranch {self.name!r} "
            f"org={self.organisation_id} parent={self.parent_branch_id} [{self.status}]>"
        )


# ═════════════════════════════════════════════════════════════════════════════
# OrgBranchManager
# ═════════════════════════════════════════════════════════════════════════════

class OrgBranchManager(SQLModel, table=True):
    """
    Associates a User as a manager / director / leader of an OrgBranch.

    A branch can have multiple managers. A user can manage multiple branches.
    manager_title is free-text: "Ambassador", "Branch Director",
    "Head of Department", "Deputy Chief of Mission" etc.

    UNIQUE  (branch_id, user_id).

    Relationship wiring:
      OrgBranchManager.branch  ←→  OrgBranch.managers
      OrgBranchManager.user    ←→  User.managed_branches
    """
    __tablename__ = "org_branch_managers"
    __table_args__ = (UniqueConstraint("branch_id", "user_id", name="uq_branch_manager"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    branch_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("org_branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)
    user_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    manager_title: Optional[str] = Field(
        default="Branch Manager", max_length=100, nullable=True,
        description="'Ambassador', 'Branch Director', 'Head of Department' etc.",
    )
    is_primary: bool = Field(
        default=False, nullable=False,
        description="True for the lead manager when a branch has multiple",
    )
    appointed_by_id: Optional[uuid.UUID] = Field(default=None, nullable=True)
    appointed_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    branch: "OrgBranch" = Relationship(back_populates="managers")
    user:   "User"      = Relationship(back_populates="managed_branches")

    def __repr__(self) -> str:
        return (
            f"<OrgBranchManager branch={self.branch_id} "
            f"user={self.user_id} title={self.manager_title!r}>"
        )


# ═════════════════════════════════════════════════════════════════════════════
# OrgService
# ═════════════════════════════════════════════════════════════════════════════

class OrgService(SQLModel, table=True):
    """
    A service / product / program listing owned by an Organisation or Branch.

    branch_id = NULL  → org-level listing (visible across all branches)
    branch_id = <id>  → scoped to and created by that specific branch

    SERVICE LOCATIONS (OrgServiceLocation)
    ─────────────────────────────────────────────────────────────────────────
    One OrgService → many OrgServiceLocation rows.
    Each row pins the service to a specific address and records which branch
    operates it there. This enables hierarchical monitoring:

      "Visa Processing Program" (single OrgService)
        → Via Veneto 121, Rome       operated by: Embassy of Rome
        → Piazza Repubblica 47, Rome operated by: Visa Section Rome
        → 4 Av Gabriel, Paris        operated by: Embassy of Paris

    Any ancestor manager queries their branch subtree
    (WITH RECURSIVE on parent_branch_id) + filter by service_id to see
    all deployment addresses across all child branches.

    Relationship wiring:
      OrgService.organisation      ←→  Organisation.services
      OrgService.branch            ←→  OrgBranch.services
      OrgService.personnel         ←→  OrgServicePersonnel.service
      OrgService.service_locations ←→  OrgServiceLocation.service
      OrgService.branch_links      ←→  OrgBranchService.service
      OrgService.media             ←→  OrgServiceMedia.service
      OrgService.faqs              ←→  OrgServiceFAQ.service
      OrgService.policies          ←→  OrgServicePolicy.service
    """
    __tablename__ = "org_services"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    organisation_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)
    branch_id: Optional[uuid.UUID] = Field(
    default=None,
    sa_column=Column(
        ForeignKey("org_branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    ),
)

    title: str = Field(max_length=255, nullable=False, index=True)
    slug:  str = Field(max_length=255, unique=True, index=True, nullable=False,
                       description="URL-safe unique handle e.g. 'us-visa-processing'")

    service_type: OrgServiceType = Field(
        sa_column=Column(SAEnum(OrgServiceType, name="org_service_type"),
                         nullable=False, index=True),
    )
    status: OrgServiceStatus = Field(
        default=OrgServiceStatus.DRAFT,
        sa_column=Column(SAEnum(OrgServiceStatus, name="org_service_status"),
                         nullable=False, index=True),
    )

    # ── Delivery mode ─────────────────────────────────────────────────────────
    # Controls how this service/program/product reaches its recipients.
    # Applies to all service_types. For PRODUCT, also see product_format below.
    delivery_mode: ServiceDeliveryMode = Field(
        default=ServiceDeliveryMode.PHYSICAL,
        sa_column=Column(
            SAEnum(ServiceDeliveryMode, name="service_delivery_mode"),
            nullable=False,
            index=True,
        ),
        description=(
            "PHYSICAL = in-person/shipped. "
            "VIRTUAL = remote/online only. "
            "HYBRID = both modes offered."
        ),
    )

    # ── Product format (PRODUCT type only) ────────────────────────────────────
    # NULL for SERVICE and PROGRAM types; set for PRODUCT.
    product_format: Optional[ProductFormat] = Field(
        default=None,
        sa_column=Column(
            SAEnum(ProductFormat, name="product_format"),
            nullable=True,
            index=True,
        ),
        description=(
            "PRODUCT only. "
            "PHYSICAL = shipped item. "
            "DIGITAL = download/access. "
            "BOTH = physical + digital editions."
        ),
    )

    # ── Location inheritance flag ─────────────────────────────────────────────
    # When True (and delivery_mode is VIRTUAL or no OrgServiceLocation rows
    # exist), the service layer inherits the branch's primary OrgLocation
    # (or org HQ) for display / monitoring purposes.
    # When False, the service only appears at explicitly registered
    # OrgServiceLocation rows.
    inherits_location: bool = Field(
        default=True,
        nullable=False,
        description=(
            "True = falls back to branch/org primary address when no explicit "
            "physical OrgServiceLocation exists. "
            "False = only shown at explicitly registered locations."
        ),
    )

    summary:     Optional[str] = Field(default=None, max_length=500, nullable=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    category:    Optional[str] = Field(default=None, max_length=100, nullable=True, index=True)
    subcategory: Optional[str] = Field(default=None, max_length=100, nullable=True)
    tags:        Optional[str] = Field(default=None, max_length=500, nullable=True,
                                       description="Comma-separated tags e.g. 'visa,consular,travel'")

    base_price:          float = Field(default=0.0,   nullable=False)
    currency_code:       str   = Field(default="USD", max_length=3, nullable=False)
    price_is_negotiable: bool  = Field(default=False, nullable=False)

    delivery_time_days: Optional[int] = Field(default=None, nullable=True)
    revisions_included: Optional[int] = Field(default=None, nullable=True)

    sku:            Optional[str] = Field(default=None, max_length=100, nullable=True, index=True)
    stock_quantity: Optional[int] = Field(default=None, nullable=True)

    is_featured: bool = Field(default=False, nullable=False)
    view_count:  int  = Field(default=0,     nullable=False)

    published_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )
    deleted_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    organisation:      "Organisation"       = Relationship(back_populates="services")
    branch:            "OrgBranch"          = Relationship(back_populates="services")
    personnel:         "OrgServicePersonnel"    = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    service_locations: "OrgServiceLocation"     = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    branch_links: "OrgBranchService" = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    media:    "OrgServiceMedia"   = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    faqs:     "OrgServiceFAQ"     = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    policies: "OrgServicePolicy"  = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def is_active(self) -> bool:
        return self.status == OrgServiceStatus.ACTIVE

    def is_free(self) -> bool:
        return self.base_price == 0.0

    def is_virtual(self) -> bool:
        return self.delivery_mode == ServiceDeliveryMode.VIRTUAL

    def __repr__(self) -> str:
        return f"<OrgService {self.slug!r} type={self.service_type} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# OrgServicePersonnel  — who leads / supervises / coordinates a service
# ═════════════════════════════════════════════════════════════════════════════

class OrgServicePersonnel(SQLModel, table=True):
    """
    Associates a User with an OrgService in a named oversight role.

    ROLE SEMANTICS
    ─────────────────────────────────────────────────────────────────────────
    LEADER
      · Programme lead / service owner. Accountable for KPIs and outcomes.
      · Applicable to any service_type; most common for SERVICE + PROGRAM.
      · Example: "Visa Programme Director" overseeing Visa Processing Program.

    SUPERVISOR
      · Quality assurance / fulfilment supervisor.
      · Primarily for PRODUCT listings: quality checks, returns, complaints.
      · Example: "Product Quality Supervisor" for a physical product line.

    COORDINATOR
      · Day-to-day operational coordination.
      · Applicable to all service_types.
      · Example: "Operations Coordinator" scheduling appointments for a program.

    MULTIPLE ROLES — one user can hold different roles on the same service
    ─────────────────────────────────────────────────────────────────────────
    UNIQUE on (service_id, user_id, personnel_role):
      Alice can be both LEADER and COORDINATOR on "Visa Processing" (two rows).
      Alice cannot be LEADER twice on the same service (enforced by UNIQUE).

    `personnel_title` is free-text for display:
      "Programme Director", "Quality Assurance Lead", "Deputy Coordinator" etc.

    Relationship wiring:
      OrgServicePersonnel.service  ←→  OrgService.personnel
      OrgServicePersonnel.user     ←→  User.service_roles
    """
    __tablename__ = "org_service_personnel"

    __table_args__ = (
        UniqueConstraint(
            "service_id", "user_id", "personnel_role",
            name="uq_service_personnel_role",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # CASCADE: deleting the Service removes all its personnel assignments
    service_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("org_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)
    # CASCADE: deleting the User removes their service role assignments
    user_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    personnel_role: ServicePersonnelRole = Field(
        sa_column=Column(
            SAEnum(ServicePersonnelRole, name="service_personnel_role"),
            nullable=False,
            index=True,
        ),
        description="LEADER | SUPERVISOR | COORDINATOR",
    )
    personnel_title: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description=(
            "Display title e.g. 'Programme Director', "
            "'Product Quality Supervisor', 'Deputy Coordinator'"
        ),
    )
    is_primary: bool = Field(
        default=False,
        nullable=False,
        description="True for the principal person in this role when multiples exist",
    )

    # Who made this appointment (null for seed / initial setup)
    appointed_by_id: Optional[uuid.UUID] = Field(default=None, nullable=True)
    appointed_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    service: "OrgService" = Relationship(back_populates="personnel")
    user:    "User"       = Relationship(back_populates="service_roles")

    def __repr__(self) -> str:
        return (
            f"<OrgServicePersonnel service={self.service_id} "
            f"user={self.user_id} role={self.personnel_role} "
            f"title={self.personnel_title!r}>"
        )


# ═════════════════════════════════════════════════════════════════════════════
# OrgServiceLocation  — WHERE a service operates (address + branch + status)
# ═════════════════════════════════════════════════════════════════════════════

class OrgServiceLocation(SQLModel, table=True):
    """
    Pins an OrgService to a specific OrgLocation (address) and records which
    OrgBranch is responsible for running it there.

    THIS IS THE KEY MONITORING TABLE.
    ─────────────────────────────────────────────────────────────────────────
    One row = "this service/program is deployed at this exact address,
               operated by this branch, with this operational status."

    CONCRETE EXAMPLE
    ─────────────────────────────────────────────────────────────────────────
    OrgService:  "Visa Processing Program"

      service=Visa Processing, branch=Embassy of Rome,
        location=Via Veneto 121 Rome,        status=ACTIVE,
        hours="Mon–Fri 09:00–17:00 CET"
      service=Visa Processing, branch=Visa Section Rome,
        location=Piazza Repubblica 47 Rome,  status=ACTIVE,
        hours="Tue/Thu 10:00–14:00 CET"
      service=Visa Processing, branch=Embassy of Paris,
        location=4 Av Gabriel Paris,         status=PLANNED,
        started_on=2026-06-01

    MONITORING QUERY — Secretary of State sees ALL State Dept deployments:
    ─────────────────────────────────────────────────────────────────────────
      WITH RECURSIVE subtree AS (
        SELECT id FROM org_branches WHERE id = :state_dept_id
        UNION ALL
        SELECT b.id FROM org_branches b
          JOIN subtree ON b.parent_branch_id = subtree.id
      )
      SELECT sl.*, loc.city, loc.line1, b.name AS branch_name,
             svc.title AS service_title
        FROM org_service_locations sl
        JOIN org_locations loc   ON loc.id = sl.location_id
        JOIN org_branches  b     ON b.id   = sl.branch_id
        JOIN org_services  svc   ON svc.id = sl.service_id
       WHERE sl.service_id = :visa_processing_id
         AND sl.branch_id IN (SELECT id FROM subtree)
       ORDER BY b.name, loc.city;

    Ambassador of Rome uses same query with :state_dept_id = :embassy_rome_id
    to scope it to their branch only.

    UNIQUE  (service_id, branch_id, location_id) — no duplicate rows.

    branch_id   SET NULL on branch delete   → historical record preserved
    location_id SET NULL on location delete → historical record preserved

    Relationship wiring:
      OrgServiceLocation.service  ←→  OrgService.service_locations
      OrgServiceLocation.branch   ←→  OrgBranch.service_locations
      OrgServiceLocation.location ←→  OrgLocation.service_locations
    """
    __tablename__ = "org_service_locations"

    __table_args__ = (
        UniqueConstraint(
            "service_id", "branch_id", "location_id",
            name="uq_service_branch_location",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # CASCADE: deleting the Service removes all its deployment rows
    service_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("org_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)
    # SET NULL: historical records preserved when a branch is deleted
    branch_id: Optional[uuid.UUID] = Field(
    default=None,
    sa_column=Column(
        ForeignKey("org_branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    ),
)
    # SET NULL: historical records preserved when an address is deleted
    location_id: Optional[uuid.UUID] = Field(
    default=None,
    sa_column=Column(
        ForeignKey("org_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    ),
)

    # ── Operational status at this specific address ────────────────────────────
    status: ServiceLocationStatus = Field(
        default=ServiceLocationStatus.ACTIVE,
        sa_column=Column(
            SAEnum(ServiceLocationStatus, name="service_location_status"),
            nullable=False, index=True,
        ),
        description="ACTIVE | SUSPENDED | CLOSED | PLANNED at this address",
    )

    # ── Virtual vs physical deployment ────────────────────────────────────────
    # is_virtual=False → physical deployment; location_id SHOULD be set.
    # is_virtual=True  → remote/online deployment; location_id = NULL.
    #   The service layer resolves the display address by walking:
    #     branch primary OrgLocation → org HQ OrgLocation.
    #   virtual_platform + virtual_url carry the access details.
    is_virtual: bool = Field(
        default=False,
        nullable=False,
        index=True,
        description=(
            "False = in-person / physical deployment at location_id. "
            "True  = remote/online; location_id is NULL; "
            "branch/org address inherited for display."
        ),
    )
    virtual_platform: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description="Platform name for virtual delivery e.g. 'Zoom', 'Teams', 'Portal', 'Phone'",
    )
    virtual_url: Optional[str] = Field(
        default=None,
        max_length=1024,
        nullable=True,
        description="Access URL for virtual delivery e.g. 'https://zoom.us/j/12345'",
    )

    # ── Operational detail ────────────────────────────────────────────────────
    operating_hours: Optional[str] = Field(
        default=None, max_length=500, nullable=True,
        description="e.g. 'Mon–Fri 09:00–17:00 CET, closed public holidays'",
    )
    capacity: Optional[int] = Field(
        default=None, nullable=True,
        description="Max concurrent clients / appointments per day here",
    )
    notes: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True),
        description="Appointment-only, walk-in, accessibility, special instructions …",
    )

    # ── Location-specific contact overrides ───────────────────────────────────
    contact_phone: Optional[str] = Field(default=None, max_length=20,  nullable=True)
    contact_email: Optional[str] = Field(default=None, max_length=255, nullable=True)

    # ── Operational dates ─────────────────────────────────────────────────────
    started_on: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When this service began operating at this address",
    )
    ended_on: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When operations ended here (NULL = still active)",
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )

    service:  "OrgService"  = Relationship(back_populates="service_locations")
    branch:   "OrgBranch"   = Relationship(back_populates="service_locations")
    location: "OrgLocation" = Relationship(back_populates="service_locations")

    def is_active(self) -> bool:
        return self.status == ServiceLocationStatus.ACTIVE

    def __repr__(self) -> str:
        return (
            f"<OrgServiceLocation service={self.service_id} "
            f"branch={self.branch_id} location={self.location_id} [{self.status}]>"
        )


# ═════════════════════════════════════════════════════════════════════════════
# OrgBranchService  — M2M: which services a Branch offers
# ═════════════════════════════════════════════════════════════════════════════

class OrgBranchService(SQLModel, table=True):
    """
    Junction: OrgBranch ↔ OrgService.

    inherited=True  → branch re-uses the parent org's service unchanged
    inherited=False → branch-specific or overridden service

    UNIQUE  (branch_id, service_id).

    Relationship wiring:
      OrgBranchService.branch   ←→  OrgBranch.branch_services
      OrgBranchService.service  ←→  OrgService.branch_links
    """
    __tablename__ = "org_branch_services"
    __table_args__ = (UniqueConstraint("branch_id", "service_id", name="uq_branch_service"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    branch_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("org_branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)
    service_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("org_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    inherited: bool = Field(
        default=True, nullable=False,
        description="True = branch uses parent org service as-is; False = branch-specific",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    branch:  "OrgBranch"  = Relationship(back_populates="branch_services")
    service: "OrgService" = Relationship(back_populates="branch_links")


# ═════════════════════════════════════════════════════════════════════════════
# OrgServiceMedia
# ═════════════════════════════════════════════════════════════════════════════

class OrgServiceMedia(SQLModel, table=True):
    """
    Media assets (images, videos, documents) attached to an OrgService listing.

    media_url    → CDN-hosted asset (preferred)
    storage_key  → internal object-store key (S3 / GCS / R2)

    is_cover marks the primary thumbnail. display_order controls gallery sort.

    Relationship wiring:
      OrgServiceMedia.service  ←→  OrgService.media
    """
    __tablename__ = "org_service_media"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    service_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("org_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    media_type: OrgMediaType = Field(
        sa_column=Column(SAEnum(OrgMediaType, name="org_media_type"), nullable=False),
    )
    media_url:     Optional[str] = Field(default=None, max_length=1024, nullable=True)
    storage_key:   Optional[str] = Field(default=None, max_length=512,  nullable=True)
    alt_text:      Optional[str] = Field(default=None, max_length=255,  nullable=True)
    caption:       Optional[str] = Field(default=None, max_length=500,  nullable=True)
    is_cover:      bool = Field(default=False, nullable=False)
    display_order: int  = Field(default=0,     nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )

    service: "OrgService" = Relationship(back_populates="media")


# ═════════════════════════════════════════════════════════════════════════════
# OrgServiceFAQ
# ═════════════════════════════════════════════════════════════════════════════

class OrgServiceFAQ(SQLModel, table=True):
    """
    FAQ items on a specific service/product/program listing page.

    Answers service-specific questions:
      "What documents do I need for a visa application?"
      "Does this product include a warranty?"
      "Who qualifies for this government program?"

    Relationship wiring:
      OrgServiceFAQ.service  ←→  OrgService.faqs
    """
    __tablename__ = "org_service_faqs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    service_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("org_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    question:      str  = Field(sa_column=Column(Text, nullable=False))
    answer:        str  = Field(sa_column=Column(Text, nullable=False))
    display_order: int  = Field(default=0,    nullable=False)
    is_published:  bool = Field(default=True, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )

    service: "OrgService" = Relationship(back_populates="faqs")


# ═════════════════════════════════════════════════════════════════════════════
# OrgServicePolicy
# ═════════════════════════════════════════════════════════════════════════════

class OrgServicePolicy(SQLModel, table=True):
    """
    Policy and T&C text blocks for a specific service/program listing.

    Multiple blocks per service:
      policy_type="refund"       → refund / cancellation terms
      policy_type="terms_of_use" → full legal T&C for this service
      policy_type="delivery"     → delivery and handling conditions
      policy_type="eligibility"  → who can apply (government programs)
      policy_type="copyright"    → IP / ownership after delivery
      policy_type="privacy"      → data handling for this service

    Version history: set is_active=False on old version, insert new row.
    Old rows are retained as an audit log.

    Relationship wiring:
      OrgServicePolicy.service  ←→  OrgService.policies
    """
    __tablename__ = "org_service_policies"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    service_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("org_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    policy_type: str = Field(
        max_length=50, nullable=False, index=True,
        description="'refund', 'terms_of_use', 'delivery', 'eligibility', 'copyright' etc.",
    )
    title: str = Field(
        max_length=200, nullable=False,
        description="Display heading e.g. 'Refund Policy', 'Eligibility Requirements'",
    )
    content: str = Field(sa_column=Column(Text, nullable=False))
    version: str = Field(default="1.0", max_length=20, nullable=False)
    effective_date: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    is_active: bool = Field(
        default=True, nullable=False,
        description="Only the active version shown to users; old versions = history",
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )

    service: "OrgService" = Relationship(back_populates="policies")
