class KafkaTopics:
    WAITING_EVENTS  = "riviwa.waiting.events"
    FEEDBACK_EVENTS = "riviwa.feedback.events"
    ORG_EVENTS      = "riviwa.organisation.events"
    NOTIFICATIONS   = "riviwa.notifications"


class WaitingEventTypes:
    TICKET_JOINED           = "ticket.joined"
    TICKET_ATTENDING        = "ticket.attending"
    TICKET_FINISHED         = "ticket.finished"
    TICKET_COMPLETED        = "ticket.completed"
    TICKET_CANCELLED        = "ticket.cancelled"
    TICKET_NO_SHOW          = "ticket.no_show"
    TICKET_STAGE_ADVANCED   = "ticket.stage_advanced"
    TICKET_PRIORITY_CHANGED = "ticket.priority_changed"
    URGENCY_SUBMITTED       = "urgency.request_submitted"
    URGENCY_APPROVED        = "urgency.approved"
    URGENCY_REJECTED        = "urgency.rejected"
    ETA_ALERT_15MIN         = "eta.alert_15min"
    STAFF_SESSION_OPENED    = "staff.session_opened"
    STAFF_SESSION_CLOSED    = "staff.session_closed"
