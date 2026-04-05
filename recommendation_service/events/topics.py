"""events/topics.py — Kafka topic constants."""


class KafkaTopics:
    ORG_EVENTS = "riviwa.org.events"
    USER_EVENTS = "riviwa.user.events"
    STAKEHOLDER_EVENTS = "riviwa.stakeholder.events"
    FEEDBACK_EVENTS = "riviwa.feedback.events"


class OrgProjectEvents:
    PUBLISHED = "org_project.published"
    UPDATED = "org_project.updated"
    PAUSED = "org_project.paused"
    RESUMED = "org_project.resumed"
    COMPLETED = "org_project.completed"
    CANCELLED = "org_project.cancelled"


class OrgProjectStageEvents:
    ACTIVATED = "org_project_stage.activated"
    COMPLETED = "org_project_stage.completed"
    SKIPPED = "org_project_stage.skipped"


class FeedbackEvents:
    SUBMITTED = "feedback.submitted"
    ACKNOWLEDGED = "feedback.acknowledged"
    ESCALATED = "feedback.escalated"
    RESOLVED = "feedback.resolved"
    CLOSED = "feedback.closed"


class StakeholderEvents:
    ACTIVITY_CONDUCTED = "engagement.activity.conducted"
    ATTENDANCE_LOGGED = "engagement.attendance.logged"
    CONCERN_RAISED = "engagement.concern.raised"
