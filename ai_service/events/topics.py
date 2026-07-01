"""
events/topics.py — ai_service
═══════════════════════════════════════════════════════════════════════════════
CONSUMES:
  riviwa.organisation.events → sync projects into ProjectKnowledgeBase
                               and index into Qdrant for RAG
  riviwa.stakeholder.events  → sync stakeholder incharge contacts
  riviwa.feedback.events     → feedback.submitted → auto-classify project_id + category_def_id

PUBLISHES:
  riviwa.notifications       → send reply SMS/WhatsApp via notification_service
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations


class KafkaTopics:
    ORG_EVENTS         = "riviwa.organisation.events"
    USER_EVENTS        = "riviwa.user.events"
    STAKEHOLDER_EVENTS = "riviwa.stakeholder.events"
    FEEDBACK_EVENTS    = "riviwa.feedback.events"
    STAFF_EVENTS       = "riviwa.staff.events"
    NOTIFICATIONS      = "riviwa.notifications"


class OrgProjectEvents:
    PUBLISHED = "org_project.published"
    UPDATED   = "org_project.updated"
    PAUSED    = "org_project.paused"
    RESUMED   = "org_project.resumed"
    COMPLETED = "org_project.completed"
    CANCELLED = "org_project.cancelled"


class OrgProjectStageEvents:
    ACTIVATED = "org_project_stage.activated"
    COMPLETED = "org_project_stage.completed"
    SKIPPED   = "org_project_stage.skipped"


class StakeholderEvents:
    CREATED = "stakeholder.created"
    UPDATED = "stakeholder.updated"
    REMOVED = "stakeholder.removed"
    ENGAGEMENT_CREATED = "engagement.created"


class FeedbackEvents:
    """Events consumed from riviwa.feedback.events."""
    SUBMITTED    = "feedback.submitted"
    ACKNOWLEDGED = "feedback.acknowledged"
    RESOLVED     = "feedback.resolved"
    ACTIONED     = "feedback.actioned"   # AI-20: suggestion marked implemented by staff


class OrgEntityEvents:
    """Org/branch/dept/service entity lifecycle — published on riviwa.organisation.events."""
    ORG_CREATED        = "organisation.created"
    ORG_UPDATED        = "organisation.updated"
    BRANCH_CREATED     = "org_branch.created"
    BRANCH_UPDATED     = "org_branch.updated"
    BRANCH_CLOSED      = "org_branch.closed"
    DEPT_CREATED       = "org_department.created"
    DEPT_UPDATED       = "org_department.updated"
    SERVICE_PUBLISHED  = "org_service.published"
    SERVICE_UPDATED    = "org_service.updated"
    SERVICE_CLOSED     = "org_service.closed"


class StaffProfileEvents:
    """Staff lifecycle — published on riviwa.staff.events."""
    CREATED    = "staff.profile.created"
    UPDATED    = "staff.profile.updated"
    SUSPENDED  = "staff.profile.suspended"
    TERMINATED = "staff.profile.terminated"


class NotificationEvents:
    """Event types published to riviwa.notifications."""
    AI_SMS_REPLY       = "ai.sms_reply"
    AI_WHATSAPP_REPLY  = "ai.whatsapp_reply"
