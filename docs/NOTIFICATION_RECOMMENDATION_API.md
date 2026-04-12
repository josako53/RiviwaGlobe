# Notification & Recommendation Service — API Reference

> **Platform:** Riviwa GRM Microservices  
> **Generated:** 2026-04-12  
> **Services covered:** `notification_service` (port 8060) · `recommendation_service` (port 8055)

---

## Table of Contents

- [Authentication](#authentication)
- [Notification Service](#notification-service)
  - [Devices](#devices)
  - [Inbox](#inbox)
  - [Preferences](#preferences)
  - [Internal Dispatch](#internal-dispatch)
  - [Templates](#templates)
  - [Webhooks — Delivery Reports](#webhooks--delivery-reports)
  - [Background Jobs](#background-jobs)
  - [Kafka Integration](#notification-kafka-integration)
- [Recommendation Service](#recommendation-service)
  - [Health](#health)
  - [Recommendations](#recommendations)
  - [Similar](#similar)
  - [Discover Nearby](#discover-nearby)
  - [Indexing (Internal)](#indexing-internal)
  - [Kafka Consumer](#recommendation-kafka-consumer)
- [End-to-End Data Flow](#end-to-end-data-flow)

---

## Authentication

| Type | Header | Used by |
|------|--------|---------|
| User JWT | `Authorization: Bearer <token>` | All user-facing endpoints |
| Internal service key | `X-Service-Key: <key>` | Internal/admin endpoints |

JWT tokens are issued by `riviwa_auth_service` and verified by all other services using `AUTH_SECRET_KEY`.

---

# Notification Service

**Base URL:** `https://<host>/api/v1`  
**Internal port:** `8060`  
**Database:** `notification_db` (PostgreSQL 5437)  
**Redis:** DB 3 (rate limiting, dedup)

---

## Devices

### `POST /devices` — Register a push device

**Auth:** Bearer JWT  
**Status:** `201 Created`

**Request body:**
```json
{
  "platform": "fcm",
  "push_token": "fcm-token-abc123",
  "device_name": "Pixel 7",
  "app_version": "2.1.0"
}
```

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `platform` | string | yes | `fcm` · `apns` |
| `push_token` | string | yes | Provider token |
| `device_name` | string | no | Human label |
| `app_version` | string | no | Semver string |

**Response:**
```json
{
  "id": "uuid",
  "platform": "fcm",
  "device_name": "Pixel 7",
  "is_active": true,
  "registered_at": "2026-04-12T10:00:00Z"
}
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.register_device(user_id, platform, push_token, device_name, app_version)
    ↓
INSERT into notification_devices
    ↓
DB commit → return DeviceResponse
```

---

### `GET /devices` — List registered devices

**Auth:** Bearer JWT  
**Status:** `200 OK`  
**No request body.**

**Response:**
```json
[
  {
    "id": "uuid",
    "platform": "fcm",
    "device_name": "Pixel 7",
    "is_active": true,
    "registered_at": "2026-04-12T10:00:00Z"
  }
]
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.get_devices(user_id)
    ↓
SELECT from notification_devices WHERE user_id = ? AND is_active = true
    ↓
Return List[DeviceResponse]
```

---

### `PATCH /devices/{device_id}/token` — Rotate push token

**Auth:** Bearer JWT  
**Status:** `200 OK`

**Request body:**
```json
{
  "push_token": "new-fcm-token-xyz",
  "app_version": "2.2.0"
}
```

**Response:** `DeviceResponse` (same shape as register)

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.update_device_token(device_id, user_id, new_token, app_version)
    ↓
UPDATE notification_devices SET push_token = ?, app_version = ?, updated_at = now
WHERE id = ? AND user_id = ?
    ↓
DB commit → return DeviceResponse
```

---

### `DELETE /devices/{device_id}` — Deregister device

**Auth:** Bearer JWT  
**Status:** `200 OK`  
**No request body.**

**Response:**
```json
{ "message": "Device deregistered" }
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.deregister_device(device_id, user_id)
    ↓
UPDATE notification_devices SET is_active = false WHERE id = ? AND user_id = ?
    ↓
DB commit → return message
```

---

## Inbox

### `GET /notifications` — Notification inbox

**Auth:** Bearer JWT  
**Status:** `200 OK`

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `unread_only` | bool | `false` | Only return unread |
| `skip` | int | `0` | Offset |
| `limit` | int | `30` | Max 100 |

**Response:**
```json
{
  "unread_count": 4,
  "returned": 10,
  "items": [
    {
      "delivery_id": "uuid",
      "notification_type": "grievance_acknowledged",
      "title": "Your grievance was acknowledged",
      "body": "Project DAWASA has acknowledged grievance #GRM-2026-001.",
      "is_read": false,
      "created_at": "2026-04-12T09:30:00Z"
    }
  ]
}
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.list_inbox(user_id, unread_only, skip, limit)
    ↓  SELECT from notification_deliveries
       JOIN notifications ON notification_id
       WHERE user_id = ? AND channel = 'in_app'
       ORDER BY created_at DESC
    ↓
NotificationRepository.unread_count(user_id)
    ↓  COUNT(*) WHERE user_id = ? AND is_read = false
    ↓
Build NotificationInboxResponse → return
```

---

### `GET /notifications/unread-count` — Badge count

**Auth:** Bearer JWT  
**Status:** `200 OK`  
**No request body.**

**Response:**
```json
{ "unread_count": 4 }
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.unread_count(user_id)
    ↓
SELECT COUNT(*) FROM notification_deliveries
WHERE user_id = ? AND channel = 'in_app' AND is_read = false
    ↓
Return UnreadCountResponse
```

---

### `PATCH /notifications/deliveries/{delivery_id}/read` — Mark one as read

**Auth:** Bearer JWT  
**Status:** `200 OK`  
**No request body.**

**Response:**
```json
{ "message": "Marked as read", "delivery_id": "uuid" }
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.mark_delivery_read(delivery_id, user_id)
    ↓
UPDATE notification_deliveries
SET is_read = true, read_at = now
WHERE id = ? AND user_id = ?
    ↓
DB commit → return message
```

---

### `POST /notifications/mark-all-read` — Mark all as read

**Auth:** Bearer JWT  
**Status:** `200 OK`  
**No request body.**

**Response:**
```json
{ "message": "All marked as read", "count": 12 }
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.mark_all_read(user_id)
    ↓
UPDATE notification_deliveries
SET is_read = true, read_at = now
WHERE user_id = ? AND channel = 'in_app' AND is_read = false
    ↓
DB commit → return count of updated rows
```

---

### `DELETE /notifications/{notification_id}` — Cancel scheduled notification

**Auth:** Bearer JWT  
**Status:** `200 OK`  
**No request body.**

**Response:**
```json
{ "message": "Notification cancelled", "notification_id": "uuid" }
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
SELECT notification WHERE id = ? AND recipient_user_id = ?
    ↓ status ≠ PENDING_SCHEDULED → 400 Bad Request
    ↓ status = PENDING_SCHEDULED → continue
    ↓
UPDATE notifications SET status = 'CANCELLED'
    ↓
DB commit
    ↓
Publish to Kafka topic: riviwa.notifications.events
    { event_type: "notification.cancelled", notification_id, recipient_user_id }
    ↓
Return message
```

---

## Preferences

### `GET /notification-preferences` — Get all preferences

**Auth:** Bearer JWT  
**Status:** `200 OK`

**Response:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "notification_type": "grievance_submitted",
    "channel": "sms",
    "enabled": false,
    "updated_at": "2026-04-11T08:00:00Z"
  }
]
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.get_preferences(user_id)
    ↓
SELECT * FROM notification_preferences WHERE user_id = ?
    ↓
Return List[NotificationPreferenceItem]
```

---

### `PUT /notification-preferences` — Set a preference

**Auth:** Bearer JWT  
**Status:** `200 OK`

**Request body:**
```json
{
  "notification_type": "grievance_submitted",
  "channel": "email",
  "enabled": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `notification_type` | string | yes | Template key e.g. `grievance_acknowledged` |
| `channel` | string | yes | `in_app` · `push` · `sms` · `email` · `whatsapp` |
| `enabled` | bool | yes | Enable or disable this channel for this type |

**Response:**
```json
{
  "message": "Preference updated",
  "notification_type": "grievance_submitted",
  "channel": "email",
  "enabled": false
}
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.upsert_preference(user_id, notification_type, channel, enabled)
    ↓
INSERT INTO notification_preferences (...) ON CONFLICT (user_id, notification_type, channel)
DO UPDATE SET enabled = ?, updated_at = now
    ↓
DB commit → return message
```

---

### `DELETE /notification-preferences/{notification_type}/{channel}` — Reset to default

**Auth:** Bearer JWT  
**Status:** `200 OK`  
**No request body.**

**Response:**
```json
{ "message": "Preference reset to platform default" }
```

**Data flow:**
```
JWT decoded → extract user_id
    ↓
NotificationRepository.delete_preference(user_id, notification_type, channel)
    ↓
DELETE FROM notification_preferences
WHERE user_id = ? AND notification_type = ? AND channel = ?
    ↓
DB commit → return message
```

---

## Internal Dispatch

### `POST /internal/dispatch` — Send a notification (HTTP path)

**Auth:** `X-Service-Key` header  
**Status:** `202 Accepted`

**Request body:**
```json
{
  "notification_type": "grievance_acknowledged",
  "recipient_user_id": "uuid",
  "recipient_phone": "+255712345678",
  "recipient_email": "user@example.com",
  "recipient_push_tokens": ["fcm-token-abc"],
  "language": "en",
  "variables": {
    "grievance_id": "GRM-2026-001",
    "project_name": "DAWASA Water Expansion",
    "status": "Acknowledged"
  },
  "preferred_channels": ["in_app", "push", "sms"],
  "priority": "normal",
  "idempotency_key": "grievance-ack-GRM-2026-001",
  "scheduled_at": null,
  "source_service": "feedback_service",
  "source_entity_id": "uuid",
  "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `notification_type` | string | yes | Template key — must match a template in DB |
| `recipient_user_id` | uuid | no | Target user (for in_app, push) |
| `recipient_phone` | string | no | E.164 format — for SMS / WhatsApp |
| `recipient_email` | string | no | For email channel |
| `recipient_push_tokens` | array | no | Override device tokens |
| `language` | string | yes | `en` · `sw` |
| `variables` | object | yes | Jinja2 template variables |
| `preferred_channels` | array | no | `in_app` · `push` · `sms` · `email` · `whatsapp` |
| `priority` | string | no | `low` · `normal` · `high` · `critical` |
| `idempotency_key` | string | no | Dedup key — same key = skip duplicate |
| `scheduled_at` | datetime | no | ISO-8601 — schedule for future delivery |
| `source_service` | string | no | Originating service name |
| `source_entity_id` | uuid | no | Originating entity ID |
| `metadata` | object | no | Arbitrary extra data |

**Response:**
```json
{
  "notification_id": "uuid",
  "accepted": true
}
```

**Data flow:**
```
X-Service-Key validated
    ↓
Check idempotency_key in Redis
    → key exists → return existing notification_id immediately
    → key missing → continue
    ↓
Create Notification row in DB (status = PROCESSING)
    ↓
scheduled_at is future?
    YES → status = PENDING_SCHEDULED → DB commit → return id
           APScheduler job "dispatch_scheduled" fires at scheduled_at
    NO  → _dispatch() immediately ↓

_dispatch():
    ↓
_resolve_channels(user_id, preferred_channels, priority, notification_type)
    → load user preferences from notification_preferences
    → remove channels user has disabled
    → if priority = CRITICAL → ignore preferences, use all channels
    → always keep at least in_app
    ↓
Load push tokens from notification_devices if not provided inline
    ↓
For each resolved channel → _deliver_to_channel():
    ↓
    Create NotificationDelivery row (status = PENDING)
        ↓
    TemplateService.render(notification_type, channel, language, variables)
        → SELECT template WHERE type=? AND channel=? AND language=?
        → Jinja2 render title + body with variables
        ↓
    Channel sender dispatch:
        in_app    → mark delivery SENT (no external call)
        push      → FCM / APNs API call
        sms       → Africa's Talking or Twilio API call
        email     → SendGrid API call
        whatsapp  → Meta Cloud API call
        ↓
    Record provider_message_id
    Update delivery status → SENT / FAILED / SKIPPED
        ↓
    If FAILED and retry_count < MAX_RETRIES:
        Schedule retry via APScheduler (exponential backoff)
    ↓
Update Notification.status:
    all SENT           → SENT
    some SENT          → PARTIALLY_SENT
    all FAILED/SKIPPED → FAILED
    ↓
DB commit
    ↓
Return notification_id
```

---

### `POST /internal/dispatch/batch` — Batch dispatch

**Auth:** `X-Service-Key`  
**Status:** `202 Accepted`

**Request body:** Array of dispatch requests
```json
[
  { ...same as single dispatch... },
  { ...same as single dispatch... }
]
```

**Response:**
```json
{
  "accepted": 2,
  "results": [
    { "notification_id": "uuid-1", "accepted": true },
    { "notification_id": "uuid-2", "accepted": true }
  ]
}
```

**Data flow:** Iterates each item → calls `DeliveryService.process_request()` per item in sequence.

---

## Templates

### `GET /templates` — List templates

**Auth:** `X-Service-Key`  
**Status:** `200 OK`

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `notification_type` | string | Filter by type key |
| `channel` | string | `in_app` · `push` · `sms` · `email` · `whatsapp` |
| `language` | string | `en` · `sw` |

**Response:**
```json
[
  {
    "id": "uuid",
    "notification_type": "grievance_acknowledged",
    "channel": "sms",
    "language": "sw",
    "title_template": null,
    "subject_template": null,
    "body_template": "Malalamiko {{ grievance_id }} yamepokewa na {{ project_name }}.",
    "is_active": true,
    "updated_at": "2026-04-11T08:00:00Z"
  }
]
```

---

### `PUT /templates` — Create or update a template

**Auth:** `X-Service-Key`  
**Status:** `200 OK`

**Request body:**
```json
{
  "notification_type": "grievance_acknowledged",
  "channel": "sms",
  "language": "sw",
  "title_template": null,
  "subject_template": null,
  "body_template": "Malalamiko {{ grievance_id }} yamepokewa na {{ project_name }}.",
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `notification_type` | string | yes | Template key |
| `channel` | string | yes | Delivery channel |
| `language` | string | yes | ISO language code |
| `title_template` | string | no | Push notification title (Jinja2) |
| `subject_template` | string | no | Email subject (Jinja2) |
| `body_template` | string | yes | Message body (Jinja2) |
| `is_active` | bool | yes | Enable/disable this template |

**Data flow:**
```
X-Service-Key validated
    ↓
NotificationRepository.upsert_template(data)
    ↓
INSERT INTO notification_templates (...)
ON CONFLICT (notification_type, channel, language)
DO UPDATE SET body_template = ?, is_active = ?, updated_at = now
    ↓
DB commit → refresh row → return TemplateResponse
```

---

### `DELETE /templates/{template_id}` — Delete a template

**Auth:** `X-Service-Key`  
**Status:** `200 OK`  
**No request body.**

**Data flow:**
```
X-Service-Key validated
    ↓
NotificationRepository.delete_template(template_id)
    ↓
DELETE FROM notification_templates WHERE id = ?
    ↓
DB commit → return {"message": "Template deleted"}
```

---

## Webhooks — Delivery Reports

> These endpoints receive delivery receipts from external providers.  
> **No authentication required** (called by providers).

---

### `POST /webhooks/sms/at/dlr` — Africa's Talking SMS DLR

**Content-Type:** `application/x-www-form-urlencoded`

**Form fields:**
```
messageId=ATxxx123&status=Success&phoneNumber=+255712345678&networkCode=62002
```

| `status` value | Internal status |
|----------------|-----------------|
| `Success` | `delivered` |
| `Failed` | `failed` |
| `Rejected` | `failed` |
| `Buffered` | no change |

**Data flow:**
```
Parse form fields
    ↓
Map AT status → internal status
    ↓
NotificationRepository.update_delivery_status(messageId, status, delivered_at, failure_reason)
    ↓
DB commit → return {"received": true}
```

---

### `POST /webhooks/sms/twilio/dlr` — Twilio SMS DLR

**Content-Type:** `application/x-www-form-urlencoded`

**Form fields:**
```
MessageSid=SMxxx&MessageStatus=delivered
```

| `MessageStatus` value | Internal status |
|-----------------------|-----------------|
| `delivered` | `delivered` |
| `undelivered` | `failed` |
| `failed` | `failed` |
| `sent` | `sent` |

**Data flow:** Same as Africa's Talking ��� uses `MessageSid` as provider key.

---

### `POST /webhooks/email/sendgrid` — SendGrid email events

**Content-Type:** `application/json`

**Request body:**
```json
[
  {
    "event": "delivered",
    "sg_message_id": "msg-id-001.filter0",
    "timestamp": 1744400000,
    "email": "user@example.com"
  },
  {
    "event": "bounce",
    "sg_message_id": "msg-id-002.filter0",
    "timestamp": 1744400010,
    "reason": "550 5.1.1 The email account does not exist"
  }
]
```

| `event` value | Internal status |
|---------------|-----------------|
| `delivered` | `delivered` |
| `bounce` | `failed` |
| `dropped` | `failed` |
| `open` / `click` | no status change |
| `unsubscribe` / `spam_report` | no status change |

**Data flow:**
```
Parse JSON array
    ↓
For each event:
    Map event type → internal status
    NotificationRepository.update_delivery_status(sg_message_id, status, delivered_at, failure_reason)
    DB commit
    ↓
Return {"received": true}
```

---

### `POST /webhooks/whatsapp/meta` — Meta WhatsApp status

**Content-Type:** `application/json`

**Request body:**
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "statuses": [{
          "id": "wamid.HBgMxxx",
          "status": "delivered",
          "timestamp": "1744400000",
          "errors": []
        }]
      }
    }]
  }]
}
```

| `status` value | Internal status |
|----------------|-----------------|
| `delivered` | `delivered` |
| `read` | `delivered` |
| `failed` | `failed` |

**Data flow:**
```
Parse nested entry → changes → value → statuses
    ↓
For each status entry:
    Map Meta status → internal status
    NotificationRepository.update_delivery_status(wamid, status, delivered_at, failure_reason)
    DB commit
    ↓
Return {"ok": true}
```

---

### `GET /webhooks/whatsapp/meta` — Meta webhook verification

**No auth. Called by Meta during webhook setup.**

**Query parameters:**
```
hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<int>
```

**Data flow:**
```
Compare hub.verify_token against settings.WHATSAPP_VERIFY_TOKEN
    ↓
Match     → return hub.challenge as integer (200 OK)
No match  → return 403 Forbidden
```

---

## Background Jobs

These run automatically via APScheduler — not HTTP endpoints.

| Job | Interval | Trigger | What happens |
|-----|----------|---------|--------------|
| `dispatch_scheduled` | every 1 min | Notifications with `status = PENDING_SCHEDULED` and `scheduled_at <= now` | Sets status → PROCESSING → calls `_dispatch()` |
| `retry_failed_deliveries` | every 5 min | Deliveries with `status = FAILED`, `retry_count < MAX_RETRIES`, `next_retry_at <= now` | Increments `retry_count`, calls `_deliver_to_channel()` again, schedules next retry with exponential backoff |

---

## Notification Kafka Integration

| Direction | Topic | Message format |
|-----------|-------|----------------|
| **Consumes** | `riviwa.notifications` | Full dispatch request (same shape as `POST /internal/dispatch` body) — sent by any service needing to notify a user |
| **Produces** | `riviwa.notifications.events` | Delivery receipt events (sent / delivered / failed / read / cancelled) |

**Produced event envelope:**
```json
{
  "event_type": "notification.delivered",
  "notification_id": "uuid",
  "delivery_id": "uuid",
  "notification_type": "grievance_acknowledged",
  "channel": "sms",
  "recipient_user_id": "uuid",
  "source_entity_id": "uuid",
  "source_service": "feedback_service",
  "provider": "africastalking",
  "provider_message_id": "ATxxx123",
  "status": "delivered",
  "failure_reason": null,
  "occurred_at": "2026-04-12T10:05:00Z",
  "metadata": {}
}
```

---
---

# Recommendation Service

**Base URL:** `https://<host>/api/v1`  
**Internal port:** `8055`  
**Database:** `recommendation_db` (PostgreSQL)  
**Vector DB:** Qdrant — collection `riviwa_entities` (384-dim, COSINE)  
**Cache:** Redis DB 5 (TTL 3600s recommendations, 7200s candidates)  
**Embedding model:** `all-MiniLM-L6-v2` (SentenceTransformer, lazy-loaded on startup)

---

## Health

### `GET /health/recommendation` — Service health

**Auth:** None  
**Status:** `200 OK`

**Response:**
```json
{
  "status": "ok",
  "database": true,
  "qdrant": true,
  "redis": true,
  "embedding_model_loaded": true
}
```

**Data flow:**
```
Ping PostgreSQL connection pool
Ping Qdrant HTTP client
Ping Redis PING command
Check embedding_service.is_model_loaded()
    ↓
Return HealthResponse — status = "ok" if all true, "degraded" otherwise
```

---

## Recommendations

### `GET /recommendations/{entity_id}` — Get recommendations for an entity

**Auth:** Bearer JWT  
**Status:** `200 OK`

**Path parameter:** `entity_id` (UUID) — the entity to get recommendations for

**Query parameters:**

| Param | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `limit` | int | `20` | 1–100 | Results per page |
| `page` | int | `1` | ≥1 | Page number |
| `min_score` | float | `0.1` | 0.0–1.0 | Minimum composite score threshold |
| `entity_type` | string | — | — | Filter candidates: `project` · `organisation` |
| `category_filter` | string | — | — | Filter candidates by category e.g. `infrastructure` |
| `geo_only` | bool | `false` | — | Restrict results to same region as query entity |
| `include_explanation` | bool | `false` | — | Include `score_breakdown` per result |

**Response:**
```json
{
  "entity_id": "11111111-0001-4000-a000-000000000001",
  "recommendations": [
    {
      "entity_id": "11111111-0007-4000-a000-000000000007",
      "entity_type": "project",
      "name": "Dar es Salaam Bus Rapid Transit (DART) Phase 2 Expansion",
      "slug": "dart-brt-phase-2-expansion",
      "description": "Extension of the DART BRT system with two new corridors...",
      "category": "infrastructure",
      "sector": "transport",
      "cover_image_url": null,
      "org_logo_url": null,
      "latitude": -6.8092,
      "longitude": 39.2694,
      "city": "Dar es Salaam",
      "region": "Dar es Salaam",
      "country_code": "TZ",
      "status": "active",
      "score": 0.73,
      "score_breakdown": {
        "semantic": 0.81,
        "tag_overlap": 0.60,
        "geo_proximity": 1.0,
        "recency": 0.55
      },
      "distance_km": 8.2,
      "shared_tags": ["infrastructure", "urban", "dar-es-salaam"],
      "interactions": {
        "feedback_count": 8,
        "grievance_count": 5,
        "suggestion_count": 2,
        "applause_count": 3,
        "engagement_count": 4
      },
      "accepts_grievances": true,
      "accepts_suggestions": true,
      "accepts_applause": true
    }
  ],
  "total": 7,
  "page": 1,
  "page_size": 20,
  "generated_at": "2026-04-12T10:00:00Z",
  "cache_hit": false
}
```

**Scoring formula:**

| Signal | Weight | Source |
|--------|--------|--------|
| Semantic similarity | 0.35 | Qdrant cosine distance (ANN search) |
| Tag overlap | 0.25 | Jaccard + IDF-weighted tag intersection |
| Geo proximity | 0.25 | Haversine distance → tiered (city / region / country) |
| Recency | 0.15 | Exponential decay from `last_active_at` |

**Data flow:**
```
JWT validated
    ↓
Check Redis cache (key: rec:recs:{entity_id}:{md5(params)}, TTL 3600s)
    → HIT  → return immediately with cache_hit = true
    → MISS → continue
    ↓
EntityRepository.get_by_id(entity_id)
    → Not found → 404 EntityNotFoundError
    ↓
embedding_service.build_entity_text(entity)
    → concatenates: name + description + category + sector + tags
    ↓
embedding_service.encode(text)
    → SentenceTransformer("all-MiniLM-L6-v2").encode(text)
    → 384-dimensional float vector
    ↓
Qdrant ANN search (limit × 5, max 200 candidates)
    → payload filters: entity_type?, category?
    → excludes query entity_id
    → returns: [(entity_id, cosine_score), ...]
    ↓ Qdrant unavailable
    → fallback: EntityRepository.get_candidates(entity_type, category, region, limit=200)
    ↓
EntityRepository.bulk_get(candidate_ids)
    → SELECT * FROM rec_entities WHERE id IN (...)
    ↓
geo_only = true → filter: candidate.region == query_entity.region
    ↓
tag_service.build_idf_map(EntityRepository.get_all_tag_sets())
    → compute IDF weights for all tags in corpus
    ↓
scoring_engine.score_candidates(query_entity, candidates, semantic_scores, idf_map)
    → for each candidate:
       semantic_signal  = cosine_score_from_qdrant          × 0.35
       tag_signal       = jaccard_idf(query.tags, cand.tags) × 0.25
       geo_signal       = tiered_proximity(query, candidate) × 0.25
                          (1.0 same city · 0.75 same region · 0.5 same country · 0.0 different)
       recency_signal   = exp(-days_since_active / 30)       × 0.15
       composite        = sum of above
    ↓
Filter: composite_score >= min_score
    ↓
Sort by composite_score descending
    ↓
Paginate: slice [((page-1)*limit) : (page*limit)]
    ↓
Write result to Redis (TTL 3600s)
    ↓
Return RecommendationResponse
```

---

## Similar

### `GET /similar/{entity_id}` — Find semantically similar entities

**Auth:** Bearer JWT  
**Status:** `200 OK`

**Path parameter:** `entity_id` (UUID)

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | `20` | 1–100, results per page |
| `page` | int | `1` | ≥1, page number |

**Response:**
```json
{
  "entity_id": "uuid",
  "similar": [
    {
      "entity_id": "uuid",
      "name": "Mwanza Lake Victoria Water Treatment Plant Upgrade",
      "category": "infrastructure",
      "sector": "water",
      "region": "Mwanza",
      "score": 0.84,
      "score_breakdown": null,
      "distance_km": null,
      "shared_tags": [],
      "accepts_grievances": true,
      "accepts_suggestions": true,
      "accepts_applause": true
    }
  ],
  "total": 7,
  "page": 1,
  "page_size": 20,
  "generated_at": "2026-04-12T10:00:00Z"
}
```

**Data flow:**
```
JWT validated
    ↓
EntityRepository.get_by_id(entity_id)
    → Not found → 404
    ↓
embedding_service.build_entity_text(entity) → encode → 384-dim vector
    ↓
Qdrant ANN search (limit × 2, NO geo/category/type filters)
    → pure semantic similarity
    → excludes query entity itself
    ↓
EntityRepository.bulk_get(candidate_ids)
    ↓
Filter: status == "active" only
    ↓
Map Qdrant cosine_score → RecommendedEntity.score
    ↓
Sort by score descending
    ↓
Paginate → return SimilarResponse
```

> **Difference from `/recommendations`:** Similar uses only the semantic signal (Qdrant ANN) with no geo, tag, or recency weighting. It answers "what is textually alike?" not "what should this user engage with next?"

---

## Discover Nearby

### `GET /discover/nearby` — Geo-based entity discovery

**Auth:** Bearer JWT  
**Status:** `200 OK`

**Query parameters:**

| Param | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `latitude` | float | yes | — | -90 to 90 | Centre point latitude |
| `longitude` | float | yes | — | -180 to 180 | Centre point longitude |
| `radius_km` | float | no | `50` | 1–5000 | Search radius in kilometres |
| `entity_type` | string | no | — | — | `project` · `organisation` |
| `category` | string | no | — | — | e.g. `infrastructure` · `agriculture` |
| `limit` | int | no | `20` | 1–100 | Results per page |
| `page` | int | no | `1` | ≥1 | Page number |

**Response:**
```json
{
  "latitude": -6.7924,
  "longitude": 39.2083,
  "radius_km": 20,
  "results": [
    {
      "entity_id": "uuid",
      "name": "Sinza-Mwenge Road Rehabilitation Phase III",
      "category": "infrastructure",
      "sector": "transport",
      "region": "Dar es Salaam",
      "latitude": -6.7672,
      "longitude": 39.2176,
      "distance_km": 3.1,
      "score": 0.24,
      "interactions": {
        "feedback_count": 2,
        "grievance_count": 0,
        "suggestion_count": 2,
        "applause_count": 0,
        "engagement_count": 0
      },
      "accepts_grievances": true,
      "accepts_suggestions": true,
      "accepts_applause": false
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "generated_at": "2026-04-12T10:00:00Z"
}
```

**Data flow:**
```
JWT validated
    ↓
EntityRepository.get_nearby(lat, lon, radius_km, entity_type, category, limit × 3)
    ↓
SQL bounding-box filter:
    WHERE status = 'active'
      AND latitude  IS NOT NULL
      AND longitude IS NOT NULL
      AND latitude  BETWEEN (lat - Δlat) AND (lat + Δlat)
      AND longitude BETWEEN (lon - Δlon) AND (lon + Δlon)
    (Δlat = radius_km / 111.0,  Δlon adjusted for cos(lat))
    ↓
Filter: status == "active" (post-query guard)
    ↓
For each result:
    distance_km = geo_service.haversine(centre_lat, centre_lon, entity.lat, entity.lon)
    score       = 1 / (1 + distance_km)
    interactions = InteractionSummary from entity counters
    ↓
Sort by distance_km ascending (nearest first)
    ↓
Paginate → return NearbyResponse
```

---

## Indexing (Internal)

> All indexing endpoints require `X-Service-Key` header.  
> These are called by other services (auth, stakeholder) when projects/orgs are created or updated.  
> Under normal operation, indexing happens automatically via the Kafka consumer.

---

### `POST /index/entity` — Index or create an entity

**Auth:** `X-Service-Key`  
**Status:** `200 OK`

**Request body:**
```json
{
  "entity_id": "11111111-0001-4000-a000-000000000001",
  "entity_type": "project",
  "source_service": "riviwa_auth_service",
  "organisation_id": "aaaaaaaa-0001-4000-b000-000000000001",
  "name": "Dar es Salaam Water Infrastructure Expansion",
  "slug": "dawasa-water-expansion-2026",
  "description": "DAWASA is expanding water supply and sewerage infrastructure...",
  "category": "infrastructure",
  "sector": "water",
  "tags": ["water", "infrastructure", "urban", "dar-es-salaam", "DAWASA"],
  "country_code": "TZ",
  "region": "Dar es Salaam",
  "primary_lga": "Kinondoni",
  "city": "Dar es Salaam",
  "latitude": -6.7924,
  "longitude": 39.2083,
  "status": "active",
  "cover_image_url": null,
  "org_logo_url": null,
  "accepts_grievances": true,
  "accepts_suggestions": true,
  "accepts_applause": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_id` | uuid | yes | ID from source service (project.id or org.id) |
| `entity_type` | string | yes | `project` · `organisation` |
| `source_service` | string | yes | Originating service name |
| `organisation_id` | uuid | no | Parent organisation (for projects) |
| `name` | string | yes | Display name |
| `slug` | string | no | URL-friendly identifier |
| `description` | string | no | Full description text — used for embedding |
| `category` | string | no | Top-level category e.g. `infrastructure` |
| `sector` | string | no | Sub-sector e.g. `water` |
| `tags` | array | no | Free-form tag list |
| `country_code` | string | no | ISO 3166-1 alpha-2 e.g. `TZ` |
| `region` | string | no | Administrative region |
| `primary_lga` | string | no | Local Government Authority |
| `city` | string | no | City name |
| `latitude` | float | no | -90 to 90 |
| `longitude` | float | no | -180 to 180 |
| `status` | string | yes | `active` · `inactive` · `paused` |
| `cover_image_url` | string | no | CDN URL |
| `org_logo_url` | string | no | Organisation logo URL |
| `accepts_grievances` | bool | yes | Grievance channel enabled |
| `accepts_suggestions` | bool | yes | Suggestion channel enabled |
| `accepts_applause` | bool | yes | Applause channel enabled |

**Response:**
```json
{ "status": "indexed", "entity_id": "uuid" }
```

**Data flow:**
```
X-Service-Key validated
    ↓
data["id"] = data.pop("entity_id")   (transform for DB layer)
    ↓
EntityRepository.upsert(data)
    ↓
    entity exists?
        YES → UPDATE fields, updated_at = now → flush
        NO  → INSERT new RecommendationEntity row → flush
    ↓
embedding_service.is_model_loaded()?
    YES →
        text  = build_entity_text(data)     (name + desc + category + sector + tags)
        hash  = md5(text)
        vector = encode(text)               (384-dim float32 via SentenceTransformer)
        embedding_service.upsert_vector(entity_id, vector, {entity_type, category, region})
            → Qdrant upsert into collection "riviwa_entities"
        EntityRepository.mark_indexed(entity_id, hash)
    NO  → skip Qdrant step
    ↓
DB commit
    ↓
cache_service.invalidate("recs", entity_id)
    → DEL all Redis keys matching rec:recs:{entity_id}:*
    ↓
Return {"status": "indexed", "entity_id": "uuid"}
```

---

### `PUT /index/entity/{entity_id}` — Update an indexed entity

**Auth:** `X-Service-Key`  
**Status:** `200 OK`

Same request body as `POST /index/entity`. Sets `entity_id` from path parameter and calls the same handler.

---

### `DELETE /index/entity/{entity_id}` — Remove from index

**Auth:** `X-Service-Key`  
**Status:** `200 OK`  
**No request body.**

**Response:**
```json
{ "status": "deleted", "entity_id": "uuid" }
```

**Data flow:**
```
X-Service-Key validated
    ↓
EntityRepository.delete_entity(entity_id)
    → DELETE FROM rec_entities WHERE id = ?
    ↓
embedding_service.delete_vector(entity_id)
    → Qdrant DELETE point from "riviwa_entities" collection
    ↓
DB commit
    ↓
cache_service.invalidate("recs", entity_id)
    ↓
Return {"status": "deleted", "entity_id": "uuid"}
```

---

### `POST /index/activity` — Log an activity event

**Auth:** `X-Service-Key`  
**Status:** `200 OK`

**Request body:**
```json
{
  "entity_id": "11111111-0001-4000-a000-000000000001",
  "event_type": "feedback_submitted",
  "actor_id": "cb657408-bbea-4f55-ba95-3bcc5b645708",
  "feedback_type": "grievance",
  "occurred_at": "2026-04-12T10:00:00Z",
  "payload": {
    "feedback_id": "uuid",
    "category": "water_quality"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_id` | uuid | yes | Target entity |
| `event_type` | string | yes | `feedback_submitted` · `feedback_resolved` · `engagement_logged` · etc. |
| `actor_id` | uuid | no | User who triggered the event |
| `feedback_type` | string | no | `grievance` · `suggestion` · `applause` (used when event_type contains "feedback") |
| `occurred_at` | datetime | no | Defaults to now |
| `payload` | object | no | Arbitrary extra context |

**Response:**
```json
{ "status": "recorded", "entity_id": "uuid" }
```

**Data flow:**
```
X-Service-Key validated
    ↓
Create ActivityEvent(entity_id, event_type, actor_id, feedback_type, occurred_at, payload)
EntityRepository.add_activity(event)
    → INSERT INTO rec_activity_events
    ↓
"feedback" in event_type?
    YES → EntityRepository.increment_feedback(entity_id, feedback_type)
              UPDATE rec_entities SET
                  feedback_count = feedback_count + 1,
                  grievance_count  += 1  (if feedback_type = "grievance")
                  suggestion_count += 1  (if feedback_type = "suggestion")
                  applause_count   += 1  (if feedback_type = "applause")
                  last_active_at = now,
                  updated_at = now
    NO  → EntityRepository.increment_engagement(entity_id)
              UPDATE rec_entities SET
                  engagement_count = engagement_count + 1,
                  last_active_at = now,
                  updated_at = now
    ↓
DB commit
    ↓
cache_service.invalidate("recs", entity_id)
    ↓
Return {"status": "recorded", "entity_id": "uuid"}
```

---

### `GET /index/entity/{entity_id}` — Get full entity record

**Auth:** `X-Service-Key`  
**Status:** `200 OK` or `404 Not Found`

**Response:**
```json
{
  "entity_id": "uuid",
  "entity_type": "project",
  "source_service": "riviwa_auth_service",
  "organisation_id": "uuid",
  "name": "Dar es Salaam Water Infrastructure Expansion",
  "slug": "dawasa-water-expansion-2026",
  "description": "...",
  "category": "infrastructure",
  "sector": "water",
  "tags": ["water", "infrastructure", "urban", "dar-es-salaam"],
  "country_code": "TZ",
  "region": "Dar es Salaam",
  "primary_lga": "Kinondoni",
  "city": "Dar es Salaam",
  "latitude": -6.7924,
  "longitude": 39.2083,
  "status": "active",
  "cover_image_url": null,
  "org_logo_url": null,
  "feedback_count": 10,
  "grievance_count": 10,
  "suggestion_count": 0,
  "applause_count": 0,
  "engagement_count": 0,
  "is_indexed": true,
  "accepts_grievances": true,
  "accepts_suggestions": true,
  "accepts_applause": true,
  "last_active_at": "2026-04-12T10:00:00Z",
  "created_at": "2026-04-11T22:18:55Z",
  "updated_at": "2026-04-12T10:00:00Z"
}
```

---

### `GET /index/entities` — List all indexed entities

**Auth:** `X-Service-Key`  
**Status:** `200 OK`

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `entity_type` | string | — | `project` · `organisation` |
| `category` | string | — | e.g. `infrastructure` |
| `region` | string | — | e.g. `Dar es Salaam` |
| `status` | string | — | `active` · `inactive` · `paused` |
| `page` | int | `1` | ≥1 |
| `page_size` | int | `50` | 1–200 |

**Response:**
```json
{
  "items": [ ...EntityResponse objects... ],
  "total": 8,
  "page": 1,
  "page_size": 50
}
```

**Data flow:**
```
X-Service-Key validated
    ↓
offset = (page - 1) × page_size
    ↓
EntityRepository.list_entities(entity_type, category, region, status, limit=page_size, offset)
    → SELECT * FROM rec_entities [WHERE filters] ORDER BY created_at DESC LIMIT ? OFFSET ?
    ↓
EntityRepository.count_entities(entity_type, category, region, status)
    → SELECT COUNT(*) FROM rec_entities [WHERE same filters]
    ↓
Transform each row → EntityResponse.from_entity(e)
    ↓
Return EntityListResponse(items, total, page, page_size)
```

---

## Recommendation Kafka Consumer

The service consumes **3 topics** automatically — no HTTP call needed for normal indexing.

| Topic | Event type | Handler | What happens |
|-------|-----------|---------|--------------|
| `riviwa.organisation.events` | `project.PUBLISHED` `project.UPDATED` `project.RESUMED` | `_handle_project_upsert` | Upsert entity row → encode text → upsert Qdrant vector → mark_indexed |
| `riviwa.organisation.events` | `project.PAUSED` `project.COMPLETED` `project.CANCELLED` | `_handle_project_deactivate` | `update_status(entity_id, new_status)` |
| `riviwa.feedback.events` | `SUBMITTED` `ACKNOWLEDGED` `ESCALATED` `RESOLVED` `CLOSED` | `_handle_feedback_event` | INSERT ActivityEvent → increment_feedback |
| `riviwa.stakeholder.events` | `ACTIVITY_CONDUCTED` `ATTENDANCE_LOGGED` `CONCERN_RAISED` | `_handle_engagement_event` | INSERT ActivityEvent → increment_engagement |

**Consumer group:** `recommendation_service_group`  
**Partition key used by producers:** `entity_id` — guarantees ordered processing per project

---
---

# End-to-End Data Flow

## User sees recommendations → submits feedback → receives notification

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1 — Project published (auth service)                                   │
│                                                                             │
│  riviwa_auth_service publishes to: riviwa.organisation.events               │
│  { event_type: "project.PUBLISHED", entity_id, name, category, lat, lon }  │
│                                                                             │
│  recommendation_service consumer receives event                             │
│    → _handle_project_upsert()                                               │
│    → EntityRepository.upsert()  → INSERT rec_entities                       │
│    → encode text → Qdrant.upsert_vector()                                   │
│    → mark_indexed = true                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2 — User opens a project page (frontend → recommendation_service)      │
│                                                                             │
│  GET /recommendations/{project_id}?include_explanation=true                 │
│  Authorization: Bearer <user_jwt>                                            │
│                                                                             │
│  recommendation_service:                                                    │
│    Check Redis cache → MISS                                                 │
│    Load project from DB                                                     │
│    Encode project text → 384-dim vector                                     │
│    Qdrant ANN search → 100 candidate IDs + cosine scores                    │
│    Bulk load candidate entities from DB                                     │
│    Score each: semantic(0.35) + tag(0.25) + geo(0.25) + recency(0.15)      │
│    Filter min_score=0.1 → sort → paginate                                   │
│    Cache in Redis (TTL 1h)                                                  │
│    Return RecommendationResponse (cache_hit=false)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3 — User submits a grievance on a recommended project                  │
│                                                                             │
│  POST /feedback  (feedback_service)                                         │
│                                                                             │
│  feedback_service:                                                          │
│    Save Feedback row to DB                                                  │
│    Publish to: riviwa.feedback.events                                       │
│      { event_type: "SUBMITTED", entity_id, actor_id, feedback_type }       │
│    Publish to: riviwa.notifications                                         │
│      { notification_type: "grievance_submitted", recipient_user_id,        │
│        variables: { grievance_id, project_name }, channels: [...] }        │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓                          ↓
┌──────────────────────────────┐   ┌──────────────────────────────────────────┐
│ recommendation_service       │   │ notification_service                     │
│ consumer receives event      │   │ consumer receives event                  │
│                              │   │                                          │
│ _handle_feedback_event()     │   │ DeliveryService.process_request()        │
│ → INSERT ActivityEvent       │   │ → Check idempotency key (Redis)          │
│ → increment_feedback()       │   │ → Create Notification row                │
│   feedback_count += 1        │   │ → _resolve_channels()                    │
│   grievance_count += 1       │   │   apply user preferences                 │
│   last_active_at = now       │   │ → For each channel:                      │
│ → Invalidate Redis cache     │   │   TemplateService.render(Jinja2)         │
│   for this entity            │   │   → in_app: mark SENT                    │
└──────────────────────────────┘   │   → push:   FCM API call                 │
                                   │   → sms:    Africa's Talking API call    │
                                   │ → Update Notification.status = SENT      │
                                   │ → DB commit                              │
                                   └──────────────────────────────────────────┘
                                                       ↓
                                   ┌──────────────────────────────────────────┐
                                   │ STEP 4 — Provider sends DLR webhook      │
                                   │                                          │
                                   │ POST /webhooks/sms/at/dlr                │
                                   │   { messageId, status: "Success" }       │
                                   │                                          │
                                   │ notification_service:                    │
                                   │   map "Success" → "delivered"            │
                                   │   update_delivery_status(messageId)      │
                                   │   DB commit                              │
                                   │   Publish to: riviwa.notifications.events│
                                   │     { event_type: "notification.delivered│
                                   │       channel: "sms", status: "delivered"}│
                                   └──────────────────────────────────────────┘
                                                       ↓
                                   ┌──────────────────────────────────────────┐
                                   │ STEP 5 — User reads notification in-app  │
                                   │                                          │
                                   │ GET  /notifications                      │
                                   │ PATCH /notifications/deliveries/{id}/read│
                                   │                                          │
                                   │ notification_service:                    │
                                   │   mark_delivery_read(delivery_id)        │
                                   │   Publish notification.read event        │
                                   └──────────────────────────────────────────┘
```

---

## Quick Reference — All Endpoints

### Notification Service

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/devices` | JWT | Register push device |
| `GET` | `/devices` | JWT | List user devices |
| `PATCH` | `/devices/{id}/token` | JWT | Rotate push token |
| `DELETE` | `/devices/{id}` | JWT | Deregister device |
| `GET` | `/notifications` | JWT | Inbox |
| `GET` | `/notifications/unread-count` | JWT | Badge count |
| `PATCH` | `/notifications/deliveries/{id}/read` | JWT | Mark one read |
| `POST` | `/notifications/mark-all-read` | JWT | Mark all read |
| `DELETE` | `/notifications/{id}` | JWT | Cancel scheduled |
| `GET` | `/notification-preferences` | JWT | Get preferences |
| `PUT` | `/notification-preferences` | JWT | Set preference |
| `DELETE` | `/notification-preferences/{type}/{channel}` | JWT | Reset preference |
| `POST` | `/internal/dispatch` | Service Key | Send notification |
| `POST` | `/internal/dispatch/batch` | Service Key | Batch send |
| `GET` | `/templates` | Service Key | List templates |
| `PUT` | `/templates` | Service Key | Upsert template |
| `DELETE` | `/templates/{id}` | Service Key | Delete template |
| `POST` | `/webhooks/sms/at/dlr` | None | AT delivery report |
| `POST` | `/webhooks/sms/twilio/dlr` | None | Twilio DLR |
| `POST` | `/webhooks/email/sendgrid` | None | SendGrid events |
| `POST` | `/webhooks/whatsapp/meta` | None | Meta WA status |
| `GET` | `/webhooks/whatsapp/meta` | None | Meta WA verify |

### Recommendation Service

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/health/recommendation` | None | Service health |
| `GET` | `/recommendations/{entity_id}` | JWT | 4-signal recommendations |
| `GET` | `/similar/{entity_id}` | JWT | Semantic similarity |
| `GET` | `/discover/nearby` | JWT | Geo-based discovery |
| `POST` | `/index/entity` | Service Key | Index entity |
| `PUT` | `/index/entity/{id}` | Service Key | Update indexed entity |
| `DELETE` | `/index/entity/{id}` | Service Key | Remove from index |
| `POST` | `/index/activity` | Service Key | Log activity event |
| `GET` | `/index/entity/{id}` | Service Key | Get entity record |
| `GET` | `/index/entities` | Service Key | List all entities |
