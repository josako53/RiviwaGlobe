from __future__ import annotations


class KafkaTopics:
    CMS_EVENTS = "riviwa.cms.events"
    ORG_EVENTS = "riviwa.organisation.events"


class CmsEvents:
    POST_PUBLISHED = "post.published"
    POST_UPDATED   = "post.updated"
    POST_ARCHIVED  = "post.archived"
    POST_SCHEDULED = "post.scheduled"
