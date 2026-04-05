# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  events/topics.py
# ───────────────────────────────────────────────────────────────────────────
"""
events/topics.py — feedback_service
═══════════════════════════════════════════════════════════════════════════════
CONSUMES: riviwa.org.events
  org_project.published   → upsert fb_projects (status = active)
  org_project.updated     → update fb_projects fields
  org_project.paused      → fb_projects.status = paused
  org_project.resumed     → fb_projects.status = active
  org_project.completed   → fb_projects.status = completed
  org_project.cancelled   → fb_projects.status = cancelled
  org_project_stage.*     → upsert/update fb_project_stages
  org_service.*           → IGNORED (OrgProject events are canonical)

CONSUMES: riviwa.user.events
  user.registered         → log (no local cache needed)
  user.profile_updated    → log (no local cache needed)
  user.deactivated        → null user_id columns on non-anonymous feedback
  user.suspended          → same as deactivated
  user.banned             → same as deactivated

CONSUMES: riviwa.stakeholder.events
  engagement.concern.raised     → auto-create Suggestion feedback
  communication.concerns.pending → auto-create Suggestion feedback

PUBLISHES: riviwa.feedback.events
  feedback.submitted, .acknowledged, .escalated,
  feedback.resolved, .appealed, .closed
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations


class KafkaTopics:
    ORG_EVENTS         = "riviwa.org.events"
    USER_EVENTS        = "riviwa.user.events"
    STAKEHOLDER_EVENTS = "riviwa.stakeholder.events"
    FEEDBACK_EVENTS    = "riviwa.feedback.events"


class OrgProjectEvents:
    """OrgProject lifecycle events. Payload key: "id"."""
    PUBLISHED = "org_project.published"
    UPDATED   = "org_project.updated"
    PAUSED    = "org_project.paused"
    RESUMED   = "org_project.resumed"
    COMPLETED = "org_project.completed"
    CANCELLED = "org_project.cancelled"


class OrgProjectStageEvents:
    """OrgProjectStage events. Payload keys: "stage_id", "project_id"."""
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
    """Legacy OrgService events — ignored by feedback_service."""
    PUBLISHED = "org_service.published"
    UPDATED   = "org_service.updated"
    SUSPENDED = "org_service.suspended"
    CLOSED    = "org_service.closed"


class UserEvents:
    """
    User lifecycle events from riviwa.user.events (auth_service).
    feedback_service uses these to protect user privacy when
    an account is deactivated, suspended, or banned.
    """
    REGISTERED       = "user.registered"
    REGISTERED_SOCIAL= "user.registered_social"
    PROFILE_UPDATED  = "user.profile_updated"
    DEACTIVATED      = "user.deactivated"
    SUSPENDED        = "user.suspended"
    BANNED           = "user.banned"


class StakeholderEvents:
    """Stakeholder events this service consumes."""
    CONCERN_RAISED        = "engagement.concern.raised"
    COMM_CONCERNS_PENDING = "communication.concerns.pending"


class FeedbackEvents:
    """Events this service publishes on riviwa.feedback.events."""
    SUBMITTED     = "feedback.submitted"
    ACKNOWLEDGED  = "feedback.acknowledged"
    ESCALATED     = "feedback.escalated"
    RESOLVED      = "feedback.resolved"
    APPEALED      = "feedback.appealed"
    CLOSED        = "feedback.closed"
    DAILY_SUMMARY = "feedback.summary.daily"
