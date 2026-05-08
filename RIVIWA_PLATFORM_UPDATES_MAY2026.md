# Riviwa Platform — Full Update Reference (May 2026)

**Version:** 2.1.0 · **Date:** 2026-05-09  
**Live Server:** `77.237.241.13` · **Base URL:** `https://api.riviwa.com`  
**Repository:** `riviwaglobe` (github.com/josako53/RiviwaGlobe)

---

## Table of Contents

1. [Platform Status — All 15 Services](#1-platform-status--all-15-services)
2. [New Services Added](#2-new-services-added)
   - 2.1 Staff Service (port 8135)
   - 2.2 Waiting Service (port 8130)
3. [Analytics Service — Breaking Fix & New Features](#3-analytics-service--breaking-fix--new-features)
4. [Staff Service — Bug Fix](#4-staff-service--bug-fix)
5. [Infrastructure Changes](#5-infrastructure-changes)
6. [Full Nginx Routing Table](#6-full-nginx-routing-table)
7. [Staff Service — Complete API Reference](#7-staff-service--complete-api-reference)
8. [Waiting Service — API Summary](#8-waiting-service--api-summary)
9. [Analytics Service — Updated Endpoints](#9-analytics-service--updated-endpoints)
10. [Error Reference](#10-error-reference)
11. [End-to-End Demo: Yas Tanzania Telecom](#11-end-to-end-demo-yas-tanzania-telecom)

---

## 1. Platform Status — All 15 Services

All services are live on `77.237.241.13`. Health checks: `GET https://api.riviwa.com/health/{service}`.

| Service | Port | DB Port | Container | Status |
|---------|------|---------|-----------|--------|
| **Auth** | 8000 | 5433 | `riviwa_auth_service` | ✅ Up |
| **Payment** | 8040 | 5435 | `payment_service` | ✅ Up |
| **Translation** | 8050 | 5438 | `translation_service` | ✅ Up |
| **Recommendation** | 8055 | 5439 | `recommendation_service` | ✅ Up |
| **Notification** | 8060 | 5437 | `notification_service` | ✅ Up |
| **Stakeholder** | 8070 | 5436 | `stakeholder_service` | ✅ Up |
| **AI** | 8085 | 5440 | `ai_service` | ✅ Up (Groq updated) |
| **Feedback** | 8090 | 5434 | `feedback_service` | ✅ Up |
| **Analytics** | 8095 | 5441 | `analytics_service` | ✅ Up (updated) |
| **Integration** | 8100 | 5442 | `integration_service` | ✅ Up |
| **Product** | 8110 | 5443 | `product_service` | ✅ Up |
| **QR** | 8120 | 5444 | `qr_service` | ✅ Up |
| **Verification** | 8125 | 5445 | `verification_service` | ✅ Up |
| **Waiting** | 8130 | 5446 | `waiting_service` | ✅ Up (**NEW**) |
| **Staff** | 8135 | 5447 | `staff_service` | ✅ Up (**NEW**) |

**Infrastructure:**
- Redis: port 6379 (DB allocations: 0=auth, 3=notification, 6=spark, 9=waiting, 10=staff)
- MinIO: ports 9000/9001 (buckets: `riviwa-voice`, `riviwa-images`, `riviwa-staff`)
- Kafka: KRaft single-node (dev), 4-node cluster (prod)
- Qdrant: ports 6333/6334
- Ollama: port 11434

---

## 2. New Services Added

### 2.1 Staff Service (port 8135)

**Purpose:** Eliminate impersonation fraud in service delivery. Organisations register all staff with unique digital IDs and QR codes. Citizens verify identity by entering the staff code or scanning the QR badge in real time.

**Database:** `staff_db` (PostgreSQL 15, port 5447)  
**Redis DB:** 10 (rate limiting)  
**MinIO Bucket:** `riviwa-staff`  
**Kafka Topic (publish):** `riviwa.staff.events`  
**Kafka Topic (consume):** `riviwa.organisation.events` → `org_cache` table

#### Staff Code Format

```
{ORG_SLUG_UPPER_6CHARS}-{SEQUENCE:05d}
```

Examples: `MNH-00042`, `YAS-TZ-00015`, `RIVIWA-00001`

- Sequence is atomic per organisation using `INSERT ... ON CONFLICT DO UPDATE ... RETURNING last_value`
- Codes are globally unique per organisation — reuse across orgs is possible but resolved by newest
- Codes never reset — deleted staff numbers are retired

#### Database Tables

| Table | Purpose |
|-------|---------|
| `org_cache` | Synced from Kafka org events (org_id, name, slug, is_active) |
| `staff_id_sequences` | Per-org atomic counter (org_id UNIQUE, last_value) |
| `staff_profiles` | Full staff record (see schema below) |
| `staff_verifications` | Immutable scan log (lookup_code, result, GPS, IP, user_agent) |
| `staff_fraud_reports` | Citizen fraud submissions with photo attachments |
| `staff_feedbacks` | Post-verification star ratings (1–5) |
| `bulk_import_jobs` | CSV import tracking (status, row counts, per-row errors) |

#### Staff Profile Fields

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Auto-generated primary key |
| org_id | UUID | Owning organisation |
| staff_code | VARCHAR(30) | Unique within org |
| qr_code_id | UUID | Optional link to qr_service |
| badge_number | VARCHAR(100) | Physical badge ID |
| first_name | VARCHAR(100) | Required |
| last_name | VARCHAR(100) | Required |
| middle_name | VARCHAR(100) | Optional |
| display_name | VARCHAR(200) | Auto-built from name parts if omitted |
| phone | VARCHAR(20) | |
| email | VARCHAR(200) | |
| position | VARCHAR(200) | Job title (required) |
| department | VARCHAR(200) | Department name |
| branch_id | UUID | FK to org branch |
| branch_name | VARCHAR(200) | Denormalized |
| supervisor_id | UUID (self-FK) | Supervisor's profile ID |
| employment_type | VARCHAR(20) | FULL_TIME / PART_TIME / CONTRACT / INTERN / VOLUNTEER |
| status | VARCHAR(20) | ACTIVE / SUSPENDED / TERMINATED / ON_LEAVE |
| expertise | JSONB | List of skill strings |
| bio | TEXT | Free-text description |
| photo_key | VARCHAR(500) | MinIO object key |
| photo_url | VARCHAR(500) | Public URL |
| id_number | VARCHAR(100) | National ID / passport |
| project_ids | JSONB | List of UUIDs |
| metadata_ | JSONB | Flexible extra data |
| is_verified | BOOLEAN | Organisation confirmed identity documents |
| hire_date | DATE | |
| suspension_reason | TEXT | Set when status = SUSPENDED |
| termination_reason | TEXT | Set when status = TERMINATED |
| created_by | UUID | Admin user who created |
| created_at / updated_at | TIMESTAMP | |

---

### 2.2 Waiting Service (port 8130)

**Purpose:** Digital queue management for service delivery points — hospitals, banks, government offices, telecom shops. Citizens join queues, receive ticket numbers, and get real-time ETA notifications.

**Database:** `waiting_db` (PostgreSQL 15, port 5446)  
**Redis DB:** 9 (priority-sorted sets for live queue state)  
**Kafka Topic:** `riviwa.waiting.events`

#### Key Concepts

- **Service Flow:** A defined sequence of steps (e.g. Registration → Consultation → Billing → Pharmacy)
- **Service Counter:** A physical window/desk serving a queue step
- **Queue Ticket:** A citizen's position in a queue, with ticket number (e.g. `A-042`)
- **Priority Score:** Composite `priority_rank × 10¹² + epoch_µs` stored in Redis sorted set — ensures FIFO within same priority and instant emergency bumping

#### Supported Ticket Types
`GENERAL`, `PRIORITY`, `EMERGENCY`, `VIP`, `ONLINE`, `APPOINTMENT`

#### Supported Service Point Statuses
`OPEN`, `PAUSED`, `CLOSED`

---

## 3. Analytics Service — Breaking Fix & New Features

### What Changed

Six analytics endpoints that previously required `project_id` as a **mandatory** query parameter now also accept `org_id` as an **optional alternative**. This is a **backward-compatible additive change** — existing `project_id` usage is unaffected.

### Updated Endpoints

All six endpoints now accept either `project_id` OR `org_id`:

```
GET /api/v1/analytics/feedback/overdue
GET /api/v1/analytics/feedback/by-category
GET /api/v1/analytics/grievances/dashboard
GET /api/v1/analytics/grievances/sla-status
GET /api/v1/analytics/grievances/hotspots
GET /api/v1/analytics/suggestions/frequency
```

**New query parameter on all six:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | UUID | **Optional** (was required). Single project — existing behavior unchanged |
| `org_id` | UUID | **New.** Organisation UUID — aggregates across all org projects |

**Validation:** Provide exactly one of `project_id` or `org_id`. If neither is provided, returns `422 VALIDATION_ERROR`.

**Aggregation behaviour when `org_id` is used:**
- Retrieves all `fb_projects` belonging to the org
- If the org has no projects → returns an empty response (not an error)
- If the org has projects → runs the per-project query for each and merges results in Python
  - Counts are summed per category/priority/bucket
  - Lists are concatenated

**New repository method:**
```python
# repositories/feedback_analytics_repo.py
async def get_project_ids_for_org(org_id: UUID) -> List[UUID]:
    """Returns all project IDs for an organisation from fb_projects."""
```

**SLA pre-computed data fix:**

The `feedback_sla_status` table in `analytics_db` stores `project_id` as TEXT, but the SQLAlchemy model queries it with UUID. When pre-computed data exists, this caused a `ProgrammingError: operator does not exist: text = uuid`. The query is now wrapped in try/except — on failure it falls through to the live `feedback_db` computation.

### Groq API Key Updated

The Groq API key (`GROQ_API_KEY`) has been updated in `/opt/riviwa/.env`. Both `ai_service` and `analytics_service` have been restarted to pick up the new key.

Affected endpoints:
- `POST /api/v1/analytics/ai/ask` — Groq-powered org/platform analytics queries
- `POST /api/v1/analytics/ai/ask-voice` — Voice analytics
- `POST /api/v1/ai/conversations` — AI conversation service

---

## 4. Staff Service — Bug Fix

### `MultipleResultsFound` in cross-org staff code lookup

**Commit:** `e8bdc2d`

**Problem:** `get_by_code_any_org(code)` used `scalar_one_or_none()` which raises `MultipleResultsFound` when multiple organisations have staff with the same code pattern (e.g. multiple orgs can both have `ORG-00001`).

**Fix:** Changed to `.limit(1).scalars().first()` with ordering by `created_at DESC` (newest first).

```python
# Before (broken when same code exists in multiple orgs):
result = await self.db.execute(
    select(StaffProfile).where(
        func.lower(StaffProfile.staff_code) == code.strip().lower()
    )
)
return result.scalar_one_or_none()  # raises if >1 row

# After (safe):
result = await self.db.execute(
    select(StaffProfile).where(
        func.lower(StaffProfile.staff_code) == code.strip().lower()
    ).order_by(StaffProfile.created_at.desc()).limit(1)
)
return result.scalars().first()
```

**Impact:** `POST /api/v1/staff/verify` and `GET /api/v1/staff/api/lookup/{code}` both use this method. They will now always return the most recently created staff with that code instead of crashing.

---

## 5. Infrastructure Changes

### New docker-compose additions

**staff_db (port 5447):**
```yaml
staff_db:
  image: postgres:15
  container_name: staff_db
  environment:
    POSTGRES_USER:     staff_admin
    POSTGRES_PASSWORD: staff_pass_135
    POSTGRES_DB:       staff_db
  ports: ["5447:5432"]
  volumes: [staff_db_data:/var/lib/postgresql/data]
```

**staff_service (port 8135):**
```yaml
staff_service:
  build:
    context: ./staff_service
    dockerfile: Dockerfile
  ports: ["8135:8135"]
  environment:
    STAFF_DB_HOST:           staff_db
    AUTH_SECRET_KEY:         ${SECRET_KEY}
    KAFKA_BOOTSTRAP_SERVERS: kafka-1:9092
    REDIS_URL:               redis://redis:6379/10
    MINIO_ENDPOINT:          minio:9000
    STAFF_BUCKET:            riviwa-staff
    ENVIRONMENT:             production
  depends_on: [staff_db, redis, kafka-1, minio]
```

**waiting_db (port 5446)** and **waiting_service (port 8130):** Previously added.

### New Nginx Routes

```nginx
# Staff Service (port 8135)
location /api/v1/staff {
    set $staff http://staff_service:8135;
    proxy_pass $staff;
    include /etc/nginx/proxy_params;
    include /etc/nginx/cors_params;
}

location /health/staff {
    set $staff http://staff_service:8135;
    proxy_pass $staff/health;
    include /etc/nginx/proxy_params;
}

# Waiting Service (port 8130) — previously added
location /api/v1/waiting {
    set $waiting http://waiting_service:8130;
    proxy_pass $waiting;
    include /etc/nginx/proxy_params;
}
```

---

## 6. Full Nginx Routing Table

All routes proxied through `https://api.riviwa.com`.

| Path Prefix | Service | Port |
|-------------|---------|------|
| `/api/v1/auth` | Auth | 8000 |
| `/api/v1/users` | Auth | 8000 |
| `/api/v1/orgs` | Auth | 8000 |
| `/api/v1/admin` | Auth | 8000 |
| `/api/v1/system` | Auth | 8000 |
| `/api/v1/webhooks` | Auth | 8000 |
| `/api/v1/projects` | Stakeholder | 8070 |
| `/api/v1/stakeholders` | Stakeholder | 8070 |
| `/api/v1/activities` | Stakeholder | 8070 |
| `/api/v1/communications` | Stakeholder | 8070 |
| `/api/v1/focal-persons` | Stakeholder | 8070 |
| `/api/v1/reports/stakeholder` | Stakeholder | 8070 |
| `/api/v1/feedback` | Feedback | 8090 |
| `/api/v1/categories` | Feedback | 8090 |
| `/api/v1/channels` | Feedback | 8090 |
| `/api/v1/committees` | Feedback | 8090 |
| `/api/v1/pap` | Feedback | 8090 |
| `/api/v1/voice` | Feedback | 8090 |
| `/api/v1/reports` | Feedback | 8090 |
| `/api/v1/my` | Feedback | 8090 |
| `/api/v1/escalation-paths` | Feedback | 8090 |
| `/api/v1/escalation-requests` | Feedback | 8090 |
| `/api/v1/channel-sessions` | Feedback | 8090 |
| `/api/v1/ai/conversations` | AI | 8085 |
| `/api/v1/ai/voice` | AI | 8085 |
| `/api/v1/ai/webhooks` | AI | 8085 |
| `/api/v1/ai/admin` | AI | 8085 |
| `/api/v1/analytics` | Analytics | 8095 |
| `/api/v1/payments` | Payment | 8040 |
| `/api/v1/webhooks/payment` | Payment | 8040 |
| `/api/v1/notifications` | Notification | 8060 |
| `/api/v1/notification-preferences` | Notification | 8060 |
| `/api/v1/devices` | Notification | 8060 |
| `/api/v1/templates` | Notification | 8060 |
| `/api/v1/internal` | Notification | 8060 |
| `/api/v1/webhooks/notifications` | Notification | 8060 |
| `/api/v1/translate` | Translation | 8050 |
| `/api/v1/languages` | Translation | 8050 |
| `/api/v1/detect` | Translation | 8050 |
| `/api/v1/recommendations` | Recommendation | 8055 |
| `/api/v1/similar` | Recommendation | 8055 |
| `/api/v1/discover` | Recommendation | 8055 |
| `/api/v1/index` | Recommendation | 8055 |
| `/api/v1/integration` | Integration | 8100 |
| `/api/v1/integration/.well-known` | Integration | 8100 |
| `/api/v1/products` | Product | 8110 |
| `/api/v1/qr` | QR | 8120 |
| `/api/v1/verify` | Verification | 8125 |
| `/api/v1/waiting` | Waiting | 8130 |
| `/api/v1/staff` | **Staff** | **8135** |

---

## 7. Staff Service — Complete API Reference

**Base path:** `/api/v1/staff`  
**Auth header:** `Authorization: Bearer <org-scoped-token>`

### Authentication Flow

```
1. POST /api/v1/auth/login
   {"identifier": "email@org.com", "password": "..."}
   → {"login_token": "..."}

2. POST /api/v1/auth/login/verify-otp
   {"login_token": "...", "otp_code": "000000"}
   → {"access_token": "..."}

3. POST /api/v1/auth/switch-org
   {"org_id": "uuid"}
   → {"tokens": {"access_token": "..."}, "org_role": "OWNER"}
   ⚠ Token is under res["tokens"]["access_token"] — NOT res["access_token"]

4. Use the token from step 3 for all admin/analytics staff endpoints.
```

### Role Requirements

| Endpoint group | Minimum role |
|----------------|-------------|
| Public (`/verify`, `/report-fraud`, `/feedback`) | None |
| Analytics read | `manager` |
| Admin read (list, get) | `manager` |
| Admin write (create, update, photo) | `manager` |
| Admin sensitive (suspend, terminate, delete) | `admin` / `owner` |
| Internal sync | `X-Internal-Service-Key` header |
| Third-party lookup | `X-Api-Key` header |

---

### 7.1 Public Endpoints (No Authentication)

#### `POST /api/v1/staff/verify`

Verify a staff member's identity by code.

**Request:**
```json
{
  "code": "YAS-TZ-00004",
  "scanner_lat": -6.7924,
  "scanner_lng": 39.2083,
  "user_agent": "Mozilla/5.0 (Android 12)"
}
```

**Response `200 OK`:**
```json
{
  "result": "VALID",
  "verification_event_id": "8fc79fa7-...",
  "staff": {
    "staff_code": "YAS-TZ-00004",
    "display_name": "Omari Juma",
    "position": "Senior Field Agent",
    "department": "Field Services",
    "branch_name": "Dar es Salaam HQ",
    "employment_type": "FULL_TIME",
    "is_verified": false,
    "photo_url": null,
    "org_id": "455bd8b1-...",
    "expertise": ["Tower Inspection", "Customer Site Visits"],
    "hire_year": 2022
  },
  "message": "Staff identity verified successfully.",
  "feedback_url": "/api/v1/staff/feedback?verification_event_id=8fc79fa7-..."
}
```

**`result` values:**

| Value | Meaning | `staff` populated |
|-------|---------|:-----------------:|
| `VALID` | Active — identity confirmed | ✅ |
| `SUSPENDED` | Temporarily suspended | ✅ |
| `TERMINATED` | No longer employed | ✅ |
| `ON_LEAVE` | Authorised leave | ✅ |
| `NOT_FOUND` | Code not in system | ❌ |

> All results return HTTP `200`. A verification event is logged for every call including `NOT_FOUND`.

---

#### `POST /api/v1/staff/report-fraud`

Submit a fraud report. Accepts `multipart/form-data`.

**Form fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `description` | **Yes** | What happened |
| `verification_event_id` | No | UUID from a preceding verify call |
| `reporter_name` | No | |
| `reporter_phone` | No | |
| `reporter_email` | No | |
| `claimed_staff_name` | No | Name the impersonator gave |
| `claimed_staff_id` | No | Code the impersonator showed |
| `photos` | No | Up to 5 images (JPG/PNG/WEBP ≤ 5MB each) |

**Response `200 OK`:**
```json
{
  "report_id": "a1b2c3d4-...",
  "status": "SUBMITTED",
  "message": "Fraud report submitted. Thank you for helping keep your community safe."
}
```

---

#### `POST /api/v1/staff/feedback`

Submit post-verification star rating. Requires `result = VALID` from the preceding verify call.

**Request:**
```json
{
  "verification_event_id": "8fc79fa7-...",
  "rating": 5,
  "comment": "Very professional and helpful.",
  "service_type": "Network Site Visit",
  "location_description": "Kariakoo, Dar es Salaam",
  "location_lat": -6.8235,
  "location_lng": 39.2782,
  "is_anonymous": false,
  "submitter_name": "Asha Mwamba",
  "submitter_phone": "+255712900001"
}
```

**Fields:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| verification_event_id | UUID | **Yes** | Must be a VALID event |
| rating | integer | **Yes** | 1–5 |
| comment | string | No | |
| service_type | string | No | max 200 chars |
| location_description | string | No | |
| location_lat / location_lng | float | No | GPS coords |
| is_anonymous | boolean | No | Default false |
| submitter_name / submitter_phone | string | No | Ignored if anonymous |

**Response `200 OK`:** Full `StaffFeedbackOut` object.

---

### 7.2 Admin Endpoints — Profiles

All require `Authorization: Bearer <org-token>` with manager+ role.

#### `POST /api/v1/staff/admin/profiles`
Create a new staff profile. Staff code is auto-generated.

**Required fields:** `first_name`, `last_name`, `position`  
**Optional:** `middle_name`, `display_name`, `badge_number`, `phone`, `email`, `department`, `branch_id`, `branch_name`, `supervisor_id`, `employment_type` (default `FULL_TIME`), `expertise`, `bio`, `id_number`, `project_ids`, `metadata`, `hire_date`, `qr_code_id`

**Employment type values:** `FULL_TIME`, `PART_TIME`, `CONTRACT`, `INTERN`, `VOLUNTEER`

**Response `200 OK`:** Full `StaffProfileOut` with auto-generated `staff_code`.

---

#### `GET /api/v1/staff/admin/profiles`
List profiles with optional filters.

**Query params:** `department`, `branch_id`, `status`, `position`, `page` (default 1), `size` (default 20, max 100)

**Response:** Paginated `{items, total, page, size, pages}`

---

#### `GET /api/v1/staff/admin/profiles/{profile_id}`
Get single profile with feedback stats.

**Response:** `StaffProfileWithStats` — all profile fields plus `feedback_count` and `avg_rating`.

---

#### `PATCH /api/v1/staff/admin/profiles/{profile_id}`
Update profile. All fields optional. Display name is auto-recomputed if name fields change.

---

#### `DELETE /api/v1/staff/admin/profiles/{profile_id}` · [admin+]
Soft delete — sets `status = TERMINATED`. Record retained for audit.

**Response:** `204 No Content`

---

#### `POST /api/v1/staff/admin/profiles/{profile_id}/photo` · [manager+]
Upload staff photo (`multipart/form-data`, field `photo`). Stored in MinIO at `riviwa-staff/{org_id}/{profile_id}/{filename}`.

---

#### `POST /api/v1/staff/admin/profiles/{profile_id}/suspend` · [admin+]
```json
{"reason": "Under investigation — customer complaint #2026-034"}
```
Sets `status = SUSPENDED`. Returns `422` if already suspended or terminated.

---

#### `POST /api/v1/staff/admin/profiles/{profile_id}/reinstate` · [admin+]
Clears suspension. Sets `status = ACTIVE`. Returns `422` if not in SUSPENDED status.

---

#### `POST /api/v1/staff/admin/profiles/{profile_id}/terminate` · [admin+]
```json
{"reason": "Employment contract ended 2026-04-30"}
```
Sets `status = TERMINATED`. Permanent — use Suspend for temporary holds.

---

#### `POST /api/v1/staff/admin/profiles/{profile_id}/verify` · [admin+]
Marks `is_verified = true`. Confirms the organisation has physically verified the staff member's identity documents (NIN, passport, etc.).

---

### 7.3 Admin Endpoints — Bulk Import

#### `POST /api/v1/staff/admin/bulk-import` · [admin+]
Upload CSV file (`multipart/form-data`, field `file`).

**Required CSV columns:** `first_name`, `last_name`, `position`  
**Optional CSV columns:** `middle_name`, `phone`, `email`, `department`, `branch_name`, `employment_type`, `hire_date` (YYYY-MM-DD), `id_number`, `bio`, `badge_number`, `expertise` (comma-separated in quotes)

**Response:**
```json
{
  "job_id": "d7e8f9a0-...",
  "status": "PENDING",
  "message": "Import job started. Check /bulk-import/{job_id} for progress."
}
```

---

#### `GET /api/v1/staff/admin/bulk-import/{job_id}` · [admin+]

**Response:**
```json
{
  "id": "d7e8f9a0-...",
  "status": "COMPLETED",
  "total_rows": 150,
  "successful_rows": 147,
  "failed_rows": 3,
  "errors": [
    {"row": 23, "error": "Missing required field: position"},
    {"row": 87, "error": "Invalid employment_type: FREELANCE"}
  ],
  "original_filename": "staff_import.csv",
  "created_at": "2026-05-09T08:00:00",
  "completed_at": "2026-05-09T08:00:45"
}
```

**Job statuses:** `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`

---

### 7.4 Admin Endpoints — Fraud Reports

#### `GET /api/v1/staff/admin/fraud-reports`
**Query:** `status`, `page`, `size`

**Fraud report status values:**
`SUBMITTED` → `UNDER_INVESTIGATION` → `CONFIRMED_FRAUD` → `RESOLVED`  
`SUBMITTED` → `UNDER_INVESTIGATION` → `DISMISSED`

---

#### `GET /api/v1/staff/admin/fraud-reports/{report_id}`
Full detail including photo URLs.

---

#### `PATCH /api/v1/staff/admin/fraud-reports/{report_id}` · [admin+]
```json
{
  "status": "CONFIRMED_FRAUD",
  "resolution_notes": "Impersonator identified. Police report: TZ/2026/04/8872."
}
```

---

#### `POST /api/v1/staff/admin/fraud-reports/{report_id}/assign` · [admin+]
```json
{
  "agent_user_id": "24513388-...",
  "notes": "Priority: HIGH — NIN card photographed"
}
```

---

### 7.5 Admin Endpoints — Verifications

#### `GET /api/v1/staff/admin/verifications`
Audit log of all scan events.

**Query:** `result` (VALID/NOT_FOUND/SUSPENDED/TERMINATED), `from_date`, `to_date`, `page`, `size`

**Response item:**
```json
{
  "id": "8fc79fa7-...",
  "lookup_code": "YAS-TZ-00004",
  "staff_id": "efcceedd-...",
  "org_id": "455bd8b1-...",
  "result": "VALID",
  "scanner_lat": -6.7924,
  "scanner_lng": 39.2083,
  "scanner_ip": "196.201.45.100",
  "user_agent": "Mozilla/5.0 ...",
  "verified_at": "2026-05-09T08:30:00"
}
```

---

### 7.6 Analytics Endpoints

All require `Authorization: Bearer <org-token>` with manager+ role. Platform admins can add `?org_id=<target_org>`.

#### `GET /api/v1/staff/analytics/overview`
```json
{
  "org_id": "455bd8b1-...",
  "total": 15,
  "active": 14,
  "suspended": 1,
  "terminated": 0,
  "on_leave": 0,
  "departments": [
    {"department": "Customer Care", "count": 3},
    {"department": "Field Services", "count": 3},
    {"department": "Technical Support", "count": 2}
  ]
}
```

---

#### `GET /api/v1/staff/analytics/verifications`
**Query:** `days` (default 30)
```json
{
  "org_id": "...",
  "total": 1842,
  "by_result": {"VALID": 1753, "NOT_FOUND": 67, "SUSPENDED": 15, "TERMINATED": 7},
  "by_day": [{"date": "2026-05-01", "count": 89}, ...]
}
```

---

#### `GET /api/v1/staff/analytics/feedback`
```json
{
  "org_id": "...",
  "total_feedback": 412,
  "avg_rating": 4.58,
  "by_rating": {"5": 198, "4": 134, "3": 48, "2": 22, "1": 10},
  "top_staff": [
    {"staff_id": "...", "display_name": "Omari Juma", "avg_rating": 4.9, "feedback_count": 12}
  ]
}
```

---

#### `GET /api/v1/staff/analytics/fraud-reports`
```json
{
  "org_id": "...",
  "total": 3,
  "by_status": {
    "SUBMITTED": 1,
    "UNDER_INVESTIGATION": 2
  }
}
```

---

### 7.7 Internal & Third-Party

#### `POST /api/v1/staff/internal/sync-org`
**Header:** `X-Internal-Service-Key: <INTERNAL_SERVICE_KEY>`
```json
{
  "org_id": "455bd8b1-...",
  "name": "Yas Tanzania",
  "slug": "yas-tz",
  "is_active": true
}
```
Response: `{"org_id": "...", "synced": true}`

> **Note:** This is normally not needed — the service auto-syncs from Kafka. Use only when an org is missing from the cache after a Kafka replay failure.

---

#### `GET /api/v1/staff/api/lookup/{code}`
**Header:** `X-Api-Key: <API_KEY>`

Used by third-party systems (banks, insurance, government portals) to verify staff identity programmatically without creating a verification event.

**Response:**
```json
{
  "staff_code": "YAS-TZ-00004",
  "display_name": "Omari Juma",
  "position": "Senior Field Agent",
  "department": "Field Services",
  "branch_name": "Dar es Salaam HQ",
  "employment_type": "FULL_TIME",
  "is_verified": false,
  "photo_url": null,
  "org_id": "455bd8b1-...",
  "expertise": ["Tower Inspection"],
  "hire_year": 2022
}
```

---

## 8. Waiting Service — API Summary

See `RIVIWA_WAITING_ANALYTICS_API.md` for full documentation. Summary of key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/waiting/flows` | Create service flow with steps |
| `GET` | `/api/v1/waiting/flows` | List active flows |
| `GET` | `/api/v1/waiting/flows/{flow_id}` | Get flow with all steps |
| `POST` | `/api/v1/waiting/counters` | Create service counter (window) |
| `GET` | `/api/v1/waiting/counters` | List counters |
| `PATCH` | `/api/v1/waiting/counters/{counter_id}` | Update counter |
| `POST` | `/api/v1/waiting/counters/{counter_id}/open` | Open counter for service |
| `POST` | `/api/v1/waiting/counters/{counter_id}/pause` | Pause temporarily |
| `POST` | `/api/v1/waiting/counters/{counter_id}/close` | Close counter |
| `POST` | `/api/v1/waiting/queue/join` | Citizen joins queue |
| `GET` | `/api/v1/waiting/queue/status/{ticket_id}` | Check ticket status & ETA |
| `POST` | `/api/v1/waiting/queue/call-next` | Staff calls next citizen |
| `POST` | `/api/v1/waiting/queue/finish` | Mark service complete |
| `POST` | `/api/v1/waiting/queue/no-show` | Mark citizen as no-show |
| `POST` | `/api/v1/waiting/queue/cancel` | Cancel ticket |
| `GET` | `/api/v1/waiting/queue/live` | Live queue state |
| `POST` | `/api/v1/waiting/queue/urgency` | Request urgent priority bump |
| `GET` | `/api/v1/waiting/analytics/daily` | Daily queue stats |
| `GET` | `/api/v1/waiting/analytics/performance` | Counter performance stats |

---

## 9. Analytics Service — Updated Endpoints

### Org-Level Analytics (existing — confirmed working)

All use `{org_id}` as **path parameter**. Require org-scoped JWT where `token.org_id == org_id` OR platform admin token.

```
GET /api/v1/analytics/org/{org_id}/summary
GET /api/v1/analytics/org/{org_id}/by-project
GET /api/v1/analytics/org/{org_id}/by-period
GET /api/v1/analytics/org/{org_id}/by-channel
GET /api/v1/analytics/org/{org_id}/by-branch
GET /api/v1/analytics/org/{org_id}/by-department
GET /api/v1/analytics/org/{org_id}/by-service
GET /api/v1/analytics/org/{org_id}/by-product
GET /api/v1/analytics/org/{org_id}/by-category
GET /api/v1/analytics/org/{org_id}/grievances/summary
GET /api/v1/analytics/org/{org_id}/grievances/by-level
GET /api/v1/analytics/org/{org_id}/grievances/by-location
GET /api/v1/analytics/org/{org_id}/grievances/sla
GET /api/v1/analytics/org/{org_id}/suggestions/summary
GET /api/v1/analytics/org/{org_id}/applause/summary
```

### Feedback Analytics (updated — now accept `org_id`)

```
GET /api/v1/analytics/feedback/time-to-open?project_id=...
GET /api/v1/analytics/feedback/unread?project_id=...
GET /api/v1/analytics/feedback/overdue?project_id=... OR ?org_id=...   ← UPDATED
GET /api/v1/analytics/feedback/not-processed?project_id=...
GET /api/v1/analytics/feedback/processed-today?project_id=...
GET /api/v1/analytics/feedback/resolved-today?project_id=...
GET /api/v1/analytics/feedback/by-service?project_id=...
GET /api/v1/analytics/feedback/by-product?project_id=...
GET /api/v1/analytics/feedback/by-category?project_id=... OR ?org_id=... ← UPDATED
GET /api/v1/analytics/feedback/by-department?project_id=...
GET /api/v1/analytics/feedback/by-stage?project_id=...
GET /api/v1/analytics/feedback/by-branch?project_id=...
```

### Grievance Analytics (updated — now accept `org_id`)

```
GET /api/v1/analytics/grievances/unresolved?project_id=...
GET /api/v1/analytics/grievances/sla-status?project_id=... OR ?org_id=...  ← UPDATED
GET /api/v1/analytics/grievances/dashboard?project_id=... OR ?org_id=...   ← UPDATED
GET /api/v1/analytics/grievances/hotspots?project_id=... OR ?org_id=...    ← UPDATED
```

### Suggestions Analytics (updated)

```
GET /api/v1/analytics/suggestions/implementation-time?project_id=...
GET /api/v1/analytics/suggestions/frequency?project_id=... OR ?org_id=...  ← UPDATED
GET /api/v1/analytics/suggestions/by-location?project_id=...
GET /api/v1/analytics/suggestions/unread?project_id=...
GET /api/v1/analytics/suggestions/implemented-today?project_id=...
GET /api/v1/analytics/suggestions/implemented-this-week?project_id=...
```

### AI Insights (Groq — updated key)

```
POST /api/v1/analytics/ai/ask
{
  "question": "What are the top complaint types and highest-risk areas?",
  "org_id": "uuid",       // for org-scoped queries
  "scope": "org",         // "org" | "platform"
  "project_id": "uuid"    // optional — narrows to project context
}

POST /api/v1/analytics/ai/ask-voice
// Same payload, returns audio response
```

---

## 10. Error Reference

### Staff Service Errors

| HTTP | error_code | Cause |
|------|-----------|-------|
| 401 | `TOKEN_INVALID` | Malformed or missing JWT |
| 401 | `TOKEN_EXPIRED` | JWT has expired |
| 403 | `FORBIDDEN` | Insufficient role or wrong org |
| 403 | `ORG_INACTIVE` | Organisation is deactivated |
| 404 | `STAFF_NOT_FOUND` | Profile ID not found |
| 404 | `ORG_NOT_FOUND` | Org not in org_cache (Kafka sync pending) |
| 404 | `FRAUD_REPORT_NOT_FOUND` | Report ID not found |
| 404 | `VERIFICATION_EVENT_NOT_FOUND` | Event ID not found |
| 404 | `BULK_IMPORT_JOB_NOT_FOUND` | Job ID not found |
| 422 | `STAFF_ALREADY_SUSPENDED` | Already SUSPENDED |
| 422 | `STAFF_ALREADY_TERMINATED` | Already TERMINATED |
| 422 | `STAFF_NOT_SUSPENDED` | Must be SUSPENDED to reinstate |
| 422 | `INVALID_FILE_TYPE` | Photo must be JPG/PNG/WEBP |
| 422 | `FILE_TOO_LARGE` | Photo exceeds 5MB |
| 422 | `VALIDATION_ERROR` | Pydantic validation failed |

### Analytics Service Errors

| HTTP | error_code | Cause |
|------|-----------|-------|
| 403 | `FORBIDDEN` | `token.org_id` ≠ requested org (non-platform-admins) |
| 422 | `VALIDATION_ERROR` | Neither `project_id` nor `org_id` provided to updated endpoints |
| 502 | `AI_INSIGHT_ERROR` | Groq API error (expired key, rate limit, timeout) |

### Org Not Found in Staff Cache

If you get `404 ORG_NOT_FOUND` when creating staff, the org hasn't been synced to `staff_db` yet. Sync manually:

```bash
# Option 1: SQL direct
docker exec staff_db psql -U staff_admin -d staff_db -c \
  "INSERT INTO org_cache (org_id, name, slug, is_active, synced_at)
   VALUES ('your-org-uuid', 'Org Name', 'org-slug', true, NOW())
   ON CONFLICT (org_id) DO UPDATE
     SET name='Org Name', slug='org-slug', is_active=true, synced_at=NOW()"

# Option 2: API
curl -X POST https://api.riviwa.com/api/v1/staff/internal/sync-org \
  -H "X-Internal-Service-Key: $INTERNAL_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"...","name":"Org Name","slug":"org-slug","is_active":true}'
```

---

## 11. End-to-End Demo: Yas Tanzania Telecom

The full platform was tested with a real-world telecom scenario achieving **104/106 tests PASS (98%)**.

### Yas Tanzania Setup (automatically provisioned)

| Resource | Detail |
|----------|--------|
| Organisation | Yas Tanzania Telecommunications Ltd |
| Branches | 6: Dar es Salaam HQ, Arusha, Mwanza, Dodoma, Mbeya, Zanzibar |
| Departments | 8: Customer Care, Field Services, Sales, Technical Support, Anti-Fraud, YasPesa, NOC, Corporate |
| Products/Services | 6: YasPesa Mobile Money, 4G Data Bundles, Fiber, SIM Registration, Corporate Solutions, Customer Care |
| FAQ Articles | 5 customer knowledge articles |
| Feedback Categories | 9 telco-specific: Network Outage, Billing Dispute, SIM Fraud, YasPesa Fraud, Agent Misconduct, Bundle Issue, Roaming, Suggestion, Inquiry |
| Staff Members | 15 across all departments (codes `YAS-TZ-00001` to `YAS-TZ-00015`) |
| Project | Yas 4G Network Expansion — Tanzania 2026 |
| Stakeholders | TCRA (regulator), TACAN (consumer NGO), Kariakoo Business Community |

### Customer Scenarios Tested

| Scenario | Result |
|----------|--------|
| Citizen verifies Omari Juma (field agent) | **VALID** — staff card shown |
| Citizen encounters suspended Bakari Mwita | **SUSPENDED** — red warning banner |
| Citizen scans fake code YAS-99999 | **NOT_FOUND** — fraud alert shown |
| Org-verified investigator Salim Makame | **VALID + is_verified** badge |
| SIM swap fraud: TZS 320K stolen (Arusha) | Grievance submitted → escalated to Anti-Fraud |
| 4G outage: TZS 450K business loss (Kariakoo) | Grievance → acknowledged → resolved + 3GB compensation |
| YasPesa TZS 50K unauthorized deduction | Grievance → Anti-Fraud team |
| Fake Yas agent SIM swap attempt (Kinondoni) | Fraud report submitted with description |
| Fake YasPesa PIN phishing (Kariakoo) | Fraud report + NOT_FOUND verification proof |
| Fake Yas router salesman (Mbagala) | Fraud report submitted |
| Post-verification ratings (12 ratings) | Avg 4.58/5.0 |
| Bank/insurance API lookup | Third-party verified Omari Juma |

### Analytics Results

- **Staff overview:** 15 total (14 active, 1 suspended), breakdown by department
- **Verifications:** 13 events (12 VALID, 1 SUSPENDED), geo-tagged audit log
- **Feedback ratings:** 4.58/5.0 average across 12 ratings
- **Org analytics:** Feedback summary, by-department, by-branch (all 200 OK)
- **Grievance analytics:** Dashboard, SLA status, geographic hotspots (all 200 OK)
- **AI Business Intelligence:** `POST /api/v1/analytics/ai/ask` — top issues + fraud risk query

### 2 Known Non-Code Failures

| Test | Cause | Fix |
|------|-------|-----|
| AI support session (feedback service) | `/api/v1/ai/sessions` path requires specific session schema not yet matched | Use feedback service docs for exact payload |
| Analytics AI 502 | Groq API key was expired | **Fixed** — new key deployed |

---

## Appendix: Commit History (May 2026)

| Commit | Description |
|--------|-------------|
| `9338da1` | Add org_id alternative to 6 analytics endpoints + SLA try/except fix |
| `e8bdc2d` | Fix MultipleResultsFound in staff `get_by_code_any_org` |
| `6a4ef86` | RIVIWA_STAFF_SERVICE_API.md — full staff API reference |
| `2a553a0` | Add staff_service microservice (52 files) |
| `988d088` | RIVIWA_WAITING_ANALYTICS_API.md — waiting & analytics docs |
| `8ffb90f` | Add waiting_service microservice |
| `09de964` | Rename API doc to RIVIWA_PRODUCT_QR_VERICATION.md |

---

*Documentation generated 2026-05-09. Platform version 2.1.0. Live: `https://api.riviwa.com`*
