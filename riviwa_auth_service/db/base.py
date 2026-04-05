"""
app/db/base.py
═══════════════════════════════════════════════════════════════════════════════
Single import point for Alembic autogenerate.

Base = SQLModel  →  SQLModel.metadata is the same MetaData registry that
SQLAlchemy's DeclarativeBase produces. Alembic reads Base.metadata to
discover all tables. Every model class MUST be imported here — if a model
is not imported, Alembic will generate a DROP TABLE migration for it.

IMPORT ORDER
───────────────────────────────────────────────────────────────────────────────
SQLAlchemy's mapper resolves FK references lazily, so strict import order is
not required for the ORM to work. However, for Alembic's autogenerate to
produce clean dependency-ordered migrations, we import in FK dependency order:

  1. role.py          Permission, Role, RolePermission
                      No FK deps on other app models.

  2. user.py          User
                      No FK deps. (active_org_id is a plain UUID column —
                      no DB-level FK; constraint enforced in the service layer.)

  3. organisation.py  Organisation, OrganisationMember, OrganisationInvite
                      Organisation.created_by_id → users.id
                      OrganisationMember.user_id → users.id
                      OrganisationMember.organisation_id → organisations.id
                      OrganisationInvite.* → users.id + organisations.id

  4. user_role.py     UserRole
                      user_id → users.id
                      role_id → roles.id

  5. address.py       Address
                      user_id → users.id

  6. password_reset.py  PasswordResetToken
                        user_id → users.id

  7. fraud.py         DeviceFingerprint, IPRecord, FraudAssessment,
                      IDVerification, BehavioralSession
                      FraudAssessment.id_verification_id → id_verifications.id
                      (must come after IDVerification is registered)

  8. organisation_extended.py
                      OrgLocation, OrgContent, OrgFAQ
                        FK → organisations.id, org_branches.id (SET NULL)
                      OrgBranch
                        FK → organisations.id; self-ref parent_branch_id (SET NULL)
                      OrgBranchManager
                        FK → org_branches.id, users.id
                      OrgService
                        FK → organisations.id, org_branches.id (SET NULL)
                      OrgBranchService
                        FK → org_branches.id, org_services.id
                      OrgServiceLocation
                        FK → org_services.id, org_branches.id (SET NULL),
                             org_locations.id (SET NULL)
                      OrgServiceMedia, OrgServiceFAQ, OrgServicePolicy
                        FK → org_services.id

TABLE INVENTORY  (27 tables total)
───────────────────────────────────────────────────────────────────────────────
  permissions             role.py
  roles                   role.py
  role_permissions        role.py
  users                   user.py
  organisations           organisation.py
  organisation_members    organisation.py
  organisation_invites    organisation.py
  user_roles              user_role.py
  addresses               address.py
  password_reset_tokens   password_reset.py
  device_fingerprints     fraud.py
  ip_records              fraud.py
  fraud_assessments       fraud.py
  id_verifications        fraud.py
  behavioral_sessions     fraud.py
  org_locations           organisation_extended.py
  org_content             organisation_extended.py
  org_faqs                organisation_extended.py
  org_branches            organisation_extended.py
  org_branch_managers     organisation_extended.py
  org_services            organisation_extended.py
  org_service_personnel   organisation_extended.py
  org_branch_services     organisation_extended.py
  org_service_locations   organisation_extended.py
  org_service_media       organisation_extended.py
  org_service_faqs        organisation_extended.py
  org_service_policies    organisation_extended.py
  behavioral_sessions   fraud.py
  org_locations         organisation_extended.py
  org_content           organisation_extended.py
  org_faqs              organisation_extended.py
  org_branches          organisation_extended.py
  org_branch_managers   organisation_extended.py
  org_services          organisation_extended.py
  org_branch_services   organisation_extended.py
  org_service_media     organisation_extended.py
  org_service_faqs      organisation_extended.py
  org_service_policies  organisation_extended.py
═══════════════════════════════════════════════════════════════════════════════
"""
from sqlmodel import SQLModel

# Alembic target: target_metadata = Base.metadata
Base = SQLModel

# ── 1. Roles and permissions (no FK deps) ────────────────────────────────────
from models.role import Permission, Role, RolePermission          # noqa: F401, E402

# ── 2. Core user (no FK deps) ────────────────────────────────────────────────
from models.user import User                                       # noqa: F401, E402

# ── 3. Organisations (FK → users) ────────────────────────────────────────────
from models.organisation import (                                  # noqa: F401, E402
    Organisation,
    OrganisationMember,
    OrganisationInvite,
)

# ── 4. Platform staff role assignments (FK → users + roles) ──────────────────
from models.user_role import UserRole                              # noqa: F401, E402

# ── 5. Personal addresses (FK → users) ───────────────────────────────────────
from models.address import Address                                 # noqa: F401, E402

# ── 6. Password reset tokens (FK → users) ────────────────────────────────────
from models.password_reset import PasswordResetToken               # noqa: F401, E402

# ── 7. Fraud detection (FK → users; FraudAssessment also FK → id_verifications)
from models.fraud import (                                         # noqa: F401, E402
    BehavioralSession,
    DeviceFingerprint,
    FraudAssessment,
    IDVerification,
    IPRecord,
)

# ── 8. Extended org content, branches, and services ──────────────────────────
#    FK chains:
#      OrgLocation        → organisations.id, org_branches.id (SET NULL)
#      OrgContent         → organisations.id
#      OrgFAQ             → organisations.id
#      OrgBranch          → organisations.id, org_branches.id (self-ref, SET NULL)
#      OrgBranchManager   → org_branches.id, users.id
#      OrgService         → organisations.id, org_branches.id (SET NULL)
#      OrgBranchService   → org_branches.id, org_services.id
#      OrgServiceMedia    → org_services.id
#      OrgServiceFAQ      → org_services.id
#      OrgServicePolicy   → org_services.id
from models.organisation_extended import (                         # noqa: F401, E402
    OrgLocation,
    OrgContent,
    OrgFAQ,
    OrgBranch,
    OrgBranchManager,
    OrgService,
    OrgServicePersonnel,
    OrgBranchService,
    OrgServiceLocation,
    OrgServiceMedia,
    OrgServiceFAQ,
    OrgServicePolicy,
)
