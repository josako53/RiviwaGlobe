"""
events/topics.py
═══════════════════════════════════════════════════════════════════════════════
Kafka topic names and event-type constants for the Riviwa platform.

Naming conventions
──────────────────
  Topics:      riviwa.<domain>.events
  Event types: <entity>.<past_tense_verb>   (dot-separated, lowercase)

Partition keys
──────────────
  Always the entity UUID string (user_id or org_id) so that all events
  for a given entity land on the same partition → total ordering per entity.
  Exception: auth.login_failed uses sha256(identifier)[:16] because the
  user_id is not known at that point.

Consumer groups (downstream services)
──────────────────────────────────────
  riviwa.user.events         → notification-service, analytics, CRM, compliance
  riviwa.organisation.events → billing-service, analytics, compliance
  riviwa.auth.events         → security-monitoring, audit-log, SIEM
  riviwa.fraud.events        → fraud-ops dashboard, ML retraining pipeline
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations


# ─────────────────────────────────────────────────────────────────────────────
# Topic names
# ─────────────────────────────────────────────────────────────────────────────

class KafkaTopics:
    USER_EVENTS  = "riviwa.user.events"
    ORG_EVENTS   = "riviwa.organisation.events"
    AUTH_EVENTS  = "riviwa.auth.events"
    FRAUD_EVENTS = "riviwa.fraud.events"


# ─────────────────────────────────────────────────────────────────────────────
# User event types
# ─────────────────────────────────────────────────────────────────────────────

class UserEvents:
    # Registration pipeline
    REGISTRATION_INITIATED    = "user.registration_initiated"   # Step 1 complete
    REGISTRATION_BLOCKED      = "user.registration_blocked"     # fraud hard block
    REGISTERED                = "user.registered"               # email/phone signup
    REGISTERED_SOCIAL         = "user.registered_social"        # OAuth signup

    # Verification
    EMAIL_VERIFIED            = "user.email_verified"
    PHONE_VERIFIED            = "user.phone_verified"
    ID_VERIFICATION_REQUIRED  = "user.id_verification_required"
    ID_VERIFIED               = "user.id_verified"
    ID_VERIFICATION_FAILED    = "user.id_verification_failed"
    ID_DUPLICATE_DETECTED     = "user.id_duplicate_detected"

    # Account status
    ACTIVATED                 = "user.activated"                # PENDING_* → ACTIVE
    SUSPENDED                 = "user.suspended"
    BANNED                    = "user.banned"
    DEACTIVATED               = "user.deactivated"              # soft delete
    REACTIVATED               = "user.reactivated"

    # Credentials
    PASSWORD_SET              = "user.password_set"             # first password on OAuth
    PASSWORD_CHANGED          = "user.password_changed"
    PASSWORD_RESET            = "user.password_reset"
    OAUTH_LINKED              = "user.oauth_linked"
    TWO_FACTOR_ENABLED        = "user.two_factor_enabled"
    TWO_FACTOR_DISABLED       = "user.two_factor_disabled"

    # Profile
    PROFILE_UPDATED           = "user.profile_updated"
    AVATAR_UPDATED            = "user.avatar_updated"


# ─────────────────────────────────────────────────────────────────────────────
# Organisation event types
# ─────────────────────────────────────────────────────────────────────────────

class OrgEvents:
    # Lifecycle
    CREATED              = "organisation.created"
    UPDATED              = "organisation.updated"
    VERIFIED             = "organisation.verified"
    SUSPENDED            = "organisation.suspended"
    BANNED               = "organisation.banned"
    DEACTIVATED          = "organisation.deactivated"

    # Membership
    MEMBER_ADDED         = "organisation.member_added"
    MEMBER_REMOVED       = "organisation.member_removed"
    MEMBER_ROLE_CHANGED  = "organisation.member_role_changed"
    OWNER_TRANSFERRED    = "organisation.owner_transferred"

    # Invites
    INVITE_SENT          = "organisation.invite_sent"
    INVITE_ACCEPTED      = "organisation.invite_accepted"
    INVITE_DECLINED      = "organisation.invite_declined"
    INVITE_CANCELLED     = "organisation.invite_cancelled"
    INVITE_EXPIRED       = "organisation.invite_expired"


# ─────────────────────────────────────────────────────────────────────────────
# Auth event types
# ─────────────────────────────────────────────────────────────────────────────

class AuthEvents:
    LOGIN_SUCCESS      = "auth.login_success"
    LOGIN_FAILED       = "auth.login_failed"
    LOGIN_LOCKED       = "auth.login_locked"
    LOGOUT             = "auth.logout"
    TOKEN_REFRESHED    = "auth.token_refreshed"
    DASHBOARD_SWITCHED = "auth.dashboard_switched"


# ─────────────────────────────────────────────────────────────────────────────
# Fraud event types  (topic: riviwa.fraud.events)
# ─────────────────────────────────────────────────────────────────────────────

class FraudEvents:
    SCORE_COMPUTED          = "fraud.score_computed"
    ACCOUNT_FLAGGED         = "fraud.account_flagged"
    ACCOUNT_CLEARED         = "fraud.account_cleared"
    DUPLICATE_DETECTED      = "fraud.duplicate_detected"
    ID_VERIFICATION_PASSED  = "fraud.id_verification_passed"
    ID_VERIFICATION_FAILED  = "fraud.id_verification_failed"


# ─────────────────────────────────────────────────────────────────────────────
# OrgService event types  (topic: riviwa.organisation.events)
# ─────────────────────────────────────────────────────────────────────────────

class OrgServiceEvents:
    PUBLISHED  = "org_service.published"
    UPDATED    = "org_service.updated"
    SUSPENDED  = "org_service.suspended"
    CLOSED     = "org_service.closed"


# ─────────────────────────────────────────────────────────────────────────────
# OrgProject event types  (topic: riviwa.organisation.events)
# ─────────────────────────────────────────────────────────────────────────────

class OrgProjectEvents:
    PUBLISHED  = "org_project.published"
    UPDATED    = "org_project.updated"
    PAUSED     = "org_project.paused"
    RESUMED    = "org_project.resumed"
    COMPLETED  = "org_project.completed"
    CANCELLED  = "org_project.cancelled"


class OrgProjectStageEvents:
    ACTIVATED  = "org_project_stage.activated"
    COMPLETED  = "org_project_stage.completed"
    SKIPPED    = "org_project_stage.skipped"
