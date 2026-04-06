# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  stakeholder_service  |  Port: 8070  |  DB: stakeholder_db (5436)
# FILE     :  events/topics.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/topics.py — stakeholder_service
═══════════════════════════════════════════════════════════════════════════════
CONSUMES: riviwa.org.events  (auth_service)
  OrgProject lifecycle  (payload field: "id")
    org_project.published   → upsert ProjectCache (status = active)
    org_project.updated     → update ProjectCache fields
    org_project.paused      → ProjectCache.status = paused
    org_project.resumed     → ProjectCache.status = active
    org_project.completed   → ProjectCache.status = completed
    org_project.cancelled   → ProjectCache.status = cancelled

  OrgProjectStage lifecycle  (payload field: "stage_id")
    org_project_stage.activated → upsert ProjectStageCache (status = active)
    org_project_stage.completed → ProjectStageCache.status = completed
    org_project_stage.skipped   → ProjectStageCache.status = skipped

  OrgService lifecycle  (legacy, payload field: "org_service_id")
    org_service.*           → IGNORED (OrgProject events are canonical)

CONSUMES: riviwa.user.events  (auth_service)
  user.registered         → log (contact linking happens via API)
  user.profile_updated    → log (no local user cache needed)
  user.deactivated        → null StakeholderContact.user_id + log
  user.suspended          → null StakeholderContact.user_id + log
  user.banned             → null StakeholderContact.user_id + log

CONSUMES: riviwa.feedback.events  (feedback_service)
  feedback.submitted → link feedback_ref_id back to engagement + distribution

PUBLISHES: riviwa.stakeholder.events
  stakeholder.registered, .updated, .deactivated
  stakeholder.contact.added, .deactivated
  engagement.activity.planned, .conducted, .cancelled
  engagement.attendance.logged
  engagement.concern.raised            ← feedback_service auto-creates Suggestion
  communication.sent
  communication.distribution.logged
  communication.concerns.pending
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations


class KafkaTopics:
    ORG_EVENTS         = "riviwa.organisation.events"
    USER_EVENTS        = "riviwa.user.events"
    STAKEHOLDER_EVENTS = "riviwa.stakeholder.events"
    FEEDBACK_EVENTS    = "riviwa.feedback.events"


class OrgProjectEvents:
    """OrgProject lifecycle events on riviwa.org.events. Payload key: "id"."""
    PUBLISHED = "org_project.published"
    UPDATED   = "org_project.updated"
    PAUSED    = "org_project.paused"
    RESUMED   = "org_project.resumed"
    COMPLETED = "org_project.completed"
    CANCELLED = "org_project.cancelled"


class OrgProjectStageEvents:
    """OrgProjectStage lifecycle events. Payload key: "stage_id"."""
    ACTIVATED = "org_project_stage.activated"
    COMPLETED = "org_project_stage.completed"
    SKIPPED   = "org_project_stage.skipped"


class OrgEvents:
    """Organisation lifecycle events — published by riviwa_auth_service on riviwa.org.events."""
    CREATED   = "organisation.created"
    UPDATED   = "organisation.updated"   # logo_url change uses this event
    VERIFIED  = "organisation.verified"
    SUSPENDED = "organisation.suspended"
    BANNED    = "organisation.banned"
    DEACTIVATED = "organisation.deactivated"


class OrgServiceEvents:
    """Legacy OrgService events — ignored by stakeholder_service."""
    PUBLISHED = "org_service.published"
    UPDATED   = "org_service.updated"
    SUSPENDED = "org_service.suspended"
    CLOSED    = "org_service.closed"


class UserEvents:
    """
    User lifecycle events from riviwa.user.events (auth_service).
    stakeholder_service uses these to keep StakeholderContact.user_id
    in sync when a platform account is deactivated, suspended, or banned.
    """
    REGISTERED        = "user.registered"
    REGISTERED_SOCIAL = "user.registered_social"
    PROFILE_UPDATED   = "user.profile_updated"
    DEACTIVATED       = "user.deactivated"
    SUSPENDED         = "user.suspended"
    BANNED            = "user.banned"


class StakeholderEvents:
    """Event types this service publishes on riviwa.stakeholder.events."""
    REGISTERED          = "stakeholder.registered"
    UPDATED             = "stakeholder.updated"
    DEACTIVATED         = "stakeholder.deactivated"
    CONTACT_ADDED       = "stakeholder.contact.added"
    CONTACT_DEACTIVATED = "stakeholder.contact.deactivated"
    STAGE_ENGAGEMENT_SET     = "stakeholder.stage_engagement.set"
    STAGE_ENGAGEMENT_UPDATED = "stakeholder.stage_engagement.updated"
    ACTIVITY_PLANNED    = "engagement.activity.planned"
    ACTIVITY_CONDUCTED  = "engagement.activity.conducted"
    ACTIVITY_CANCELLED  = "engagement.activity.cancelled"
    ATTENDANCE_LOGGED   = "engagement.attendance.logged"
    CONCERN_RAISED      = "engagement.concern.raised"
    COMM_SENT                = "communication.sent"
    COMM_DISTRIBUTION_LOGGED = "communication.distribution.logged"
    COMM_CONCERNS_PENDING    = "communication.concerns.pending"


class FeedbackEvents:
    """Feedback events this service consumes."""
    SUBMITTED = "feedback.submitted"
    RESOLVED  = "feedback.resolved"
