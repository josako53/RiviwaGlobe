# Riviwa Staff Service — Full API Reference & Implementation Guide

**Version:** 1.0.0 · **Port:** 8135 · **Base URL:** `https://api.riviwa.com`  
**Internal base:** `http://staff_service:8135`

---

## Table of Contents

1. [Service Purpose](#1-service-purpose)
2. [Architecture Overview](#2-architecture-overview)
3. [Database Schema](#3-database-schema)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [Staff Code Format](#5-staff-code-format)
6. [Public Endpoints](#6-public-endpoints)
   - 6.1 Verify Staff Identity
   - 6.2 Report Fraud
   - 6.3 Submit Feedback
7. [Admin Endpoints — Staff Profiles](#7-admin-endpoints--staff-profiles)
   - 7.1 Create Profile
   - 7.2 List Profiles
   - 7.3 Get Profile
   - 7.4 Update Profile
   - 7.5 Delete Profile
   - 7.6 Upload Photo
   - 7.7 Suspend
   - 7.8 Reinstate
   - 7.9 Terminate
   - 7.10 Mark as Verified
8. [Admin Endpoints — Bulk Import](#8-admin-endpoints--bulk-import)
   - 8.1 Start Bulk Import
   - 8.2 Get Import Job Status
9. [Admin Endpoints — Fraud Reports](#9-admin-endpoints--fraud-reports)
   - 9.1 List Fraud Reports
   - 9.2 Get Fraud Report
   - 9.3 Update Fraud Report
   - 9.4 Assign Investigator
10. [Admin Endpoints — Verifications](#10-admin-endpoints--verifications)
    - 10.1 List Verification Events
11. [Analytics Endpoints](#11-analytics-endpoints)
    - 11.1 Staff Overview
    - 11.2 Verification Statistics
    - 11.3 Feedback Statistics
    - 11.4 Fraud Report Statistics
12. [Internal & Third-Party Endpoints](#12-internal--third-party-endpoints)
    - 12.1 Sync Organisation
    - 12.2 Third-Party Staff Lookup
13. [Enumerations Reference](#13-enumerations-reference)
14. [Error Codes Reference](#14-error-codes-reference)
15. [Step-by-Step Implementation Guide](#15-step-by-step-implementation-guide)
16. [End-to-End Flows](#16-end-to-end-flows)

---

## 1. Service Purpose

The Staff Service solves a critical trust problem in service delivery: **how does a citizen know that a person claiming to represent an organisation is genuine?**

Organisations register their staff (field agents, sales representatives, inspectors, healthcare workers, etc.) with unique identifiers and optional QR codes. When a citizen encounters someone claiming to be from an organisation, they can:

1. **Verify** — enter the staff code or scan the QR badge to instantly confirm identity
2. **Report fraud** — if the person is suspicious, submit a report with photos and description
3. **Rate performance** — after a successful verification, submit feedback on service quality

This enables organisations to:
- Issue tamper-evident digital credentials to all staff
- Track where and when verifications are happening (geo + time analytics)
- Receive real-time fraud alerts with photo evidence
- Measure staff performance through citizen feedback scores
- Identify high-risk areas and under-performing staff

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        staff_service (8135)                         │
│                                                                     │
│  Public Layer:    /verify  /report-fraud  /feedback                 │
│  Admin Layer:     /admin/profiles  /admin/bulk-import               │
│                   /admin/fraud-reports  /admin/verifications        │
│  Analytics Layer: /analytics/overview  /verifications               │
│                   /feedback  /fraud-reports                         │
│  Internal Layer:  /internal/sync-org  /api/lookup/{code}            │
└──────────────┬────────────────────────────────────────┬────────────┘
               │                                        │
         ┌─────▼──────┐                        ┌───────▼──────┐
         │  staff_db  │                        │    MinIO     │
         │ (port 5447)│                        │ riviwa-staff │
         │            │                        │   bucket     │
         │ org_cache  │                        │              │
         │ staff_id_  │                        │ /photos/     │
         │ sequences  │                        │ /fraud/      │
         │ staff_     │                        │ /csv/        │
         │ profiles   │                        └──────────────┘
         │ staff_     │
         │ verifica-  │                        ┌──────────────┐
         │ tions      │                        │    Redis     │
         │ staff_     │                        │   DB 10      │
         │ fraud_     │                        │(rate limits) │
         │ reports    │                        └──────────────┘
         │ staff_     │
         │ feedbacks  │                        ┌──────────────┐
         │ bulk_      │                        │    Kafka     │
         │ import_    │◄───────────────────────│ riviwa.org.  │
         │ jobs       │   Consumes org events  │ events       │
         └────────────┘                        │              │
                                               │ Publishes to │
                                               │ riviwa.staff.│
                                               │ events       │
                                               └──────────────┘
```

### Infrastructure Summary

| Component | Value |
|-----------|-------|
| Port | 8135 |
| Database | staff_db (PostgreSQL 15, port 5447) |
| DB User | staff_admin |
| DB Password | staff_pass_135 |
| Redis DB | 10 (rate limiting) |
| MinIO Bucket | riviwa-staff |
| Kafka (publish) | `riviwa.staff.events` |
| Kafka (consume) | `riviwa.organisation.events` |
| Auth | JWT verified with `AUTH_SECRET_KEY` (same as auth_service) |

---

## 3. Database Schema

### `org_cache`
Local mirror of organisation records, populated by Kafka consumer.

| Column | Type | Notes |
|--------|------|-------|
| org_id | UUID (PK) | Organisation ID |
| name | VARCHAR(300) | Display name |
| slug | VARCHAR(200) | URL slug used in staff code prefix |
| is_active | BOOLEAN | Only active orgs can register staff |
| synced_at | TIMESTAMP | Last Kafka sync time |

### `staff_id_sequences`
Per-organisation atomic counter for generating staff codes.

| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL (PK) | Internal |
| org_id | UUID | Organisation (unique) |
| last_value | INTEGER | Auto-incremented on each new staff |

### `staff_profiles`
Core staff record. One row per staff member.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | Staff profile ID |
| org_id | UUID | Owning organisation |
| staff_code | VARCHAR(30) | Unique within org, e.g. `MNH-00042` |
| qr_code_id | UUID (nullable) | Links to qr_service QR |
| badge_number | VARCHAR(100) | Physical badge ID (optional) |
| first_name | VARCHAR(100) | |
| last_name | VARCHAR(100) | |
| middle_name | VARCHAR(100) | Optional |
| display_name | VARCHAR(200) | Auto-built from name parts |
| phone | VARCHAR(20) | |
| email | VARCHAR(200) | |
| position | VARCHAR(200) | Job title |
| department | VARCHAR(200) | Department name |
| branch_id | UUID | FK to org branch |
| branch_name | VARCHAR(200) | Denormalized branch name |
| supervisor_id | UUID (FK self) | Supervisor's profile ID |
| employment_type | VARCHAR(20) | FULL_TIME / PART_TIME / CONTRACT / INTERN / VOLUNTEER |
| status | VARCHAR(20) | ACTIVE / SUSPENDED / TERMINATED / ON_LEAVE |
| expertise | JSONB | List of skill strings |
| bio | TEXT | Free-text description |
| photo_key | VARCHAR(500) | MinIO object key |
| photo_url | VARCHAR(500) | Public URL |
| id_number | VARCHAR(100) | National ID / passport |
| project_ids | JSONB | List of UUIDs |
| metadata_ | JSONB (column: metadata) | Flexible extra data |
| is_verified | BOOLEAN | Org has confirmed identity document |
| hire_date | DATE | |
| suspension_reason | TEXT | Set when suspended |
| termination_reason | TEXT | Set when terminated |
| created_by | UUID | Admin user who created |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Indexes:** org_id, status, department, branch_id, supervisor_id  
**Unique:** (org_id, staff_code)

### `staff_verifications`
Immutable log of every verify call.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | Verification event ID |
| lookup_code | VARCHAR(50) | Code that was entered |
| staff_id | UUID (FK, nullable) | Resolved staff ID (null if NOT_FOUND) |
| org_id | UUID (nullable) | Resolved org ID |
| result | VARCHAR(20) | VALID / INVALID / SUSPENDED / TERMINATED / ON_LEAVE / NOT_FOUND |
| scanner_lat | FLOAT | GPS latitude of scanner |
| scanner_lng | FLOAT | GPS longitude of scanner |
| scanner_ip | VARCHAR(45) | IP address |
| user_agent | VARCHAR(512) | Browser/app user agent |
| verified_at | TIMESTAMP | |

### `staff_fraud_reports`
Citizen-submitted reports of impersonation.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| verification_event_id | UUID (FK, nullable) | Links to specific scan |
| org_id | UUID (nullable) | Organisation being impersonated |
| reporter_name | VARCHAR(200) | |
| reporter_phone | VARCHAR(20) | |
| reporter_email | VARCHAR(200) | |
| claimed_staff_name | VARCHAR(200) | Name the impersonator gave |
| claimed_staff_id | VARCHAR(100) | ID the impersonator showed |
| description | TEXT | Mandatory description |
| photo_keys | JSONB | MinIO keys for uploaded photos |
| photo_urls | JSONB | Public URLs for photos |
| status | VARCHAR(20) | SUBMITTED / UNDER_INVESTIGATION / CONFIRMED_FRAUD / DISMISSED / RESOLVED |
| ai_analysis | JSONB | Reserved for future AI analysis |
| assigned_agent_id | UUID | Investigator user ID |
| resolution_notes | TEXT | Final resolution comment |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### `staff_feedbacks`
Post-verification service ratings.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| verification_event_id | UUID (FK) | Must be VALID verification |
| staff_id | UUID (FK) | Staff being rated |
| org_id | UUID | |
| rating | INTEGER | 1–5 stars |
| comment | TEXT | Optional text |
| service_type | VARCHAR(200) | Type of service provided |
| location_description | VARCHAR(500) | Text description of location |
| location_lat | FLOAT | |
| location_lng | FLOAT | |
| is_anonymous | BOOLEAN | If true, name/phone are not stored |
| submitter_name | VARCHAR(200) | Only if not anonymous |
| submitter_phone | VARCHAR(20) | Only if not anonymous |
| created_at | TIMESTAMP | |

### `bulk_import_jobs`
Tracks progress of CSV import operations.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | Job ID |
| org_id | UUID | |
| imported_by | UUID | Admin user |
| file_key | VARCHAR(500) | MinIO CSV key |
| original_filename | VARCHAR(300) | |
| status | VARCHAR(20) | PENDING / PROCESSING / COMPLETED / FAILED |
| total_rows | INTEGER | |
| successful_rows | INTEGER | |
| failed_rows | INTEGER | |
| errors | JSONB | Per-row error list |
| created_at | TIMESTAMP | |
| completed_at | TIMESTAMP | |

---

## 4. Authentication & Authorization

### JWT Verification
The service verifies tokens signed by the auth_service using the shared `AUTH_SECRET_KEY`. Tokens must come from a `switch-org` call so they carry `org_id` and `org_role`.

**Header:**
```
Authorization: Bearer <access_token>
```

### Role Requirements

| Layer | Minimum role | Dependency |
|-------|-------------|------------|
| Public endpoints | None | No auth |
| Analytics | `manager` | `ManagerDep` |
| Admin read (list, get) | `manager` | `ManagerDep` |
| Admin write (create, update, photo) | `manager` | `ManagerDep` |
| Admin sensitive (suspend, terminate, delete) | `admin` / `owner` | `AdminDep` |
| Internal sync | Internal service key | `X-Internal-Service-Key` header |
| Third-party lookup | API key | `X-Api-Key` header |

### Role Hierarchy
```
owner (3) > admin (2) > manager (1) > member (0)
```
Platform admins (`super_admin`, `admin`) bypass all org-level role checks.

### Getting a Valid Token (3-step process)
```
1. POST /api/v1/auth/login           → login_token + OTP sent to email/phone
2. POST /api/v1/auth/login/verify-otp → access_token (global)
3. POST /api/v1/auth/switch-org      → access_token scoped to org_id + org_role
```
Use the token from step 3 for all admin and analytics calls.

---

## 5. Staff Code Format

Staff codes are unique within each organisation and follow the pattern:

```
{ORG_SLUG_UPPER_6CHARS}-{SEQUENCE:05d}
```

**Examples:**
- Organisation slug `mnh` → `MNH-00001`, `MNH-00042`
- Organisation slug `riviwa-test-org-2026` → `RIVIWA-00001`
- Organisation slug `healthcare-tz` → `HEALTH-00001`

**Generation:**
- Sequence is stored in `staff_id_sequences` with an atomic `INSERT ... ON CONFLICT DO UPDATE ... RETURNING last_value` pattern
- Thread-safe and collision-free across concurrent requests
- Sequence never resets (gap-safe: if a profile is deleted, the number is retired)

---

## 6. Public Endpoints

No authentication required. These are called by citizens from a mobile app, web browser, or kiosk.

---

### 6.1 Verify Staff Identity

```
POST /api/v1/staff/verify
Content-Type: application/json
```

**Purpose:** The primary citizen-facing endpoint. Accepts a staff code (typed or scanned from QR) and returns the verification result along with a public staff card on success.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| code | string | Yes | Staff code e.g. `MNH-00042` |
| scanner_lat | float | No | GPS latitude of scanner (for heatmap) |
| scanner_lng | float | No | GPS longitude of scanner |
| user_agent | string | No | Browser/app user agent string |

```json
{
  "code": "MNH-00042",
  "scanner_lat": -6.7924,
  "scanner_lng": 39.2083,
  "user_agent": "Riviwa-App/2.1 Android"
}
```

**Success Response `200 OK`:**

```json
{
  "result": "VALID",
  "verification_event_id": "8fc79fa7-af36-4df5-815a-4c23ce971204",
  "staff": {
    "staff_code": "MNH-00042",
    "display_name": "Dr. Amina Hassan",
    "position": "Senior Nurse",
    "department": "Emergency",
    "branch_name": "Muhimbili Main Campus",
    "employment_type": "FULL_TIME",
    "is_verified": true,
    "photo_url": "https://minio.riviwa.com/riviwa-staff/...",
    "org_id": "bd877fc4-0439-4e7a-871b-3701b95b3a02",
    "expertise": ["Emergency Care", "Triage"],
    "hire_year": 2019
  },
  "message": "Staff identity verified successfully.",
  "feedback_url": "/api/v1/staff/feedback?verification_event_id=8fc79fa7-af36-4df5-815a-4c23ce971204"
}
```

**All possible `result` values:**

| Value | Meaning | `staff` field |
|-------|---------|---------------|
| `VALID` | Staff is active — identity confirmed | Populated |
| `SUSPENDED` | Staff exists but is currently suspended | Populated |
| `TERMINATED` | Staff exists but has been terminated | Populated |
| `ON_LEAVE` | Staff exists but is on leave | Populated |
| `NOT_FOUND` | Code does not match any staff in the system | `null` |

> All results still return HTTP 200 — `result` determines the outcome. A verification event is recorded for every call, including NOT_FOUND.

> `hire_year` is intentionally only the year (not full date) to protect privacy.

> `feedback_url` is only included when `result = VALID`.

---

### 6.2 Report Fraud

```
POST /api/v1/staff/report-fraud
Content-Type: multipart/form-data
```

**Purpose:** Allows any citizen to report a suspected impersonation. The `description` field is the only required field — all others are optional. Up to 5 photos can be attached.

**Form Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| description | string | **Yes** | What happened — minimum useful report |
| verification_event_id | UUID | No | ID from a preceding verify call |
| reporter_name | string | No | Name of person submitting report |
| reporter_phone | string | No | Contact phone |
| reporter_email | string | No | Contact email |
| claimed_staff_name | string | No | Name the impersonator gave |
| claimed_staff_id | string | No | ID number the impersonator showed |
| photos | file[] | No | Up to 5 images (JPG/PNG/WEBP, max 5MB each) |

**Success Response `200 OK`:**

```json
{
  "report_id": "a1b2c3d4-...",
  "status": "SUBMITTED",
  "message": "Fraud report submitted. Thank you for helping keep your community safe."
}
```

**Notes:**
- Photos are uploaded to MinIO at `riviwa-staff/fraud/{org_id}/{report_id}/{filename}`
- If `verification_event_id` is provided, `org_id` is automatically resolved from the verification event
- The report enters the `SUBMITTED` status and is visible to org admins

---

### 6.3 Submit Feedback

```
POST /api/v1/staff/feedback
Content-Type: application/json
```

**Purpose:** After a successful verification (result = VALID), the citizen can submit a star rating and optional comment about the service received.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| verification_event_id | UUID | **Yes** | From the verify response |
| rating | integer | **Yes** | 1–5 stars |
| comment | string | No | Free-text feedback |
| service_type | string | No | Type of service e.g. "Health Consultation" |
| location_description | string | No | Text description of where service happened |
| location_lat | float | No | GPS latitude |
| location_lng | float | No | GPS longitude |
| is_anonymous | boolean | No | Default `false` |
| submitter_name | string | No | Ignored if `is_anonymous: true` |
| submitter_phone | string | No | Ignored if `is_anonymous: true` |

```json
{
  "verification_event_id": "8fc79fa7-af36-4df5-815a-4c23ce971204",
  "rating": 5,
  "comment": "Dr. Hassan was professional and thorough. Highly recommended.",
  "service_type": "Emergency Consultation",
  "is_anonymous": false,
  "submitter_name": "John Doe",
  "submitter_phone": "+255712345678"
}
```

**Success Response `200 OK`:**

```json
{
  "id": "4059fb0c-0f75-48a5-af5e-1f7e1522bfab",
  "verification_event_id": "8fc79fa7-af36-4df5-815a-4c23ce971204",
  "staff_id": "efcceedd-f456-4f3f-86fa-29026965505e",
  "org_id": "bd877fc4-0439-4e7a-871b-3701b95b3a02",
  "rating": 5,
  "comment": "Dr. Hassan was professional and thorough. Highly recommended.",
  "service_type": "Emergency Consultation",
  "location_description": null,
  "location_lat": null,
  "location_lng": null,
  "is_anonymous": false,
  "submitter_name": "John Doe",
  "submitter_phone": "+255712345678",
  "created_at": "2026-05-08T14:30:00.000000"
}
```

**Errors:**
- `404 VERIFICATION_EVENT_NOT_FOUND` — event ID doesn't exist
- `404 STAFF_NOT_FOUND` — the event has no associated staff (NOT_FOUND scan)

---

## 7. Admin Endpoints — Staff Profiles

All admin endpoints require an org-scoped JWT. Include `Authorization: Bearer <switch-org-token>`.

---

### 7.1 Create Profile

```
POST /api/v1/staff/admin/profiles
Authorization: Bearer <token>  [manager+]
Content-Type: application/json
```

**Purpose:** Register a new staff member. The service auto-generates a unique staff code.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| first_name | string | **Yes** | Max 100 chars |
| last_name | string | **Yes** | Max 100 chars |
| position | string | **Yes** | Job title, max 200 chars |
| middle_name | string | No | |
| display_name | string | No | Auto-built from name parts if omitted |
| badge_number | string | No | Physical badge ID |
| phone | string | No | |
| email | string | No | |
| department | string | No | |
| branch_id | UUID | No | |
| branch_name | string | No | Denormalized |
| supervisor_id | UUID | No | Must be a valid staff profile ID |
| employment_type | string | No | Default `FULL_TIME` |
| expertise | string[] | No | List of skill strings |
| bio | string | No | |
| id_number | string | No | National ID / passport |
| project_ids | UUID[] | No | |
| metadata | object | No | Any extra key-value data |
| hire_date | date | No | `YYYY-MM-DD` |
| qr_code_id | UUID | No | Links to QR service QR code |

```json
{
  "first_name": "Amina",
  "last_name": "Hassan",
  "position": "Senior Nurse",
  "department": "Emergency",
  "branch_name": "Muhimbili Main Campus",
  "employment_type": "FULL_TIME",
  "phone": "+255712000001",
  "email": "a.hassan@mnh.go.tz",
  "expertise": ["Emergency Care", "Triage", "Pediatrics"],
  "hire_date": "2019-03-15",
  "id_number": "19930501-12345-XXXXX-X"
}
```

**Success Response `200 OK`:**

```json
{
  "id": "efcceedd-f456-4f3f-86fa-29026965505e",
  "org_id": "bd877fc4-0439-4e7a-871b-3701b95b3a02",
  "staff_code": "MNH-00042",
  "qr_code_id": null,
  "badge_number": null,
  "first_name": "Amina",
  "last_name": "Hassan",
  "middle_name": null,
  "display_name": "Amina Hassan",
  "phone": "+255712000001",
  "email": "a.hassan@mnh.go.tz",
  "position": "Senior Nurse",
  "department": "Emergency",
  "branch_id": null,
  "branch_name": "Muhimbili Main Campus",
  "supervisor_id": null,
  "employment_type": "FULL_TIME",
  "status": "ACTIVE",
  "expertise": ["Emergency Care", "Triage", "Pediatrics"],
  "bio": null,
  "photo_url": null,
  "id_number": "19930501-12345-XXXXX-X",
  "project_ids": null,
  "metadata": null,
  "is_verified": false,
  "hire_date": "2019-03-15",
  "suspension_reason": null,
  "termination_reason": null,
  "created_by": "24513388-1822-486e-bec4-15c843172a3d",
  "created_at": "2026-05-08T13:45:00.000000",
  "updated_at": "2026-05-08T13:45:00.000000"
}
```

**Errors:**
- `403 FORBIDDEN` — no org_id in token
- `404 ORG_NOT_FOUND` — org not in local cache (Kafka sync pending)
- `403 ORG_INACTIVE` — organisation is deactivated

---

### 7.2 List Profiles

```
GET /api/v1/staff/admin/profiles
Authorization: Bearer <token>  [manager+]
```

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| department | string | — | Filter by department name |
| branch_id | UUID | — | Filter by branch |
| status | string | — | Filter: `ACTIVE`, `SUSPENDED`, `TERMINATED`, `ON_LEAVE` |
| position | string | — | Filter by position |
| page | integer | 1 | Page number |
| size | integer | 20 | Page size (max 100) |

```
GET /api/v1/staff/admin/profiles?department=Emergency&status=ACTIVE&page=1&size=10
```

**Success Response `200 OK`:**

```json
{
  "items": [
    {
      "id": "...",
      "staff_code": "MNH-00042",
      "display_name": "Amina Hassan",
      "position": "Senior Nurse",
      "department": "Emergency",
      "status": "ACTIVE",
      ...
    }
  ],
  "total": 87,
  "page": 1,
  "size": 10,
  "pages": 9
}
```

---

### 7.3 Get Profile

```
GET /api/v1/staff/admin/profiles/{profile_id}
Authorization: Bearer <token>  [manager+]
```

Returns the full `StaffProfileWithStats` object, which includes feedback count and average rating in addition to all profile fields.

**Success Response `200 OK`:**

```json
{
  "id": "efcceedd-f456-4f3f-86fa-29026965505e",
  "staff_code": "MNH-00042",
  "display_name": "Amina Hassan",
  "status": "ACTIVE",
  "feedback_count": 23,
  "avg_rating": 4.7,
  ...
}
```

**Errors:**
- `404 STAFF_NOT_FOUND`
- `403 FORBIDDEN` — profile belongs to a different org (non-platform-admins)

---

### 7.4 Update Profile

```
PATCH /api/v1/staff/admin/profiles/{profile_id}
Authorization: Bearer <token>  [manager+]
Content-Type: application/json
```

All fields are optional. Only provided fields are updated.

```json
{
  "department": "ICU",
  "branch_name": "Muhimbili North Wing",
  "bio": "10 years of emergency nursing experience."
}
```

**Note:** If `first_name`, `last_name`, or `middle_name` is updated and `display_name` is not explicitly provided, `display_name` is automatically recomputed.

**Success Response `200 OK`:** Updated `StaffProfileOut`

---

### 7.5 Delete Profile

```
DELETE /api/v1/staff/admin/profiles/{profile_id}
Authorization: Bearer <token>  [admin+]
```

Soft delete — sets `status = TERMINATED` with reason "Profile deleted". The record is retained for audit and analytics purposes.

**Success Response `204 No Content`**

---

### 7.6 Upload Photo

```
POST /api/v1/staff/admin/profiles/{profile_id}/photo
Authorization: Bearer <token>  [manager+]
Content-Type: multipart/form-data
```

Uploads a staff photo to MinIO and stores the URL on the profile.

**Form Fields:**

| Field | Type | Required |
|-------|------|----------|
| photo | file | **Yes** |

Accepted formats: JPG, PNG, WEBP. Max size: 5MB.

MinIO path: `riviwa-staff/{org_id}/{profile_id}/{filename}`

**Success Response `200 OK`:** Updated `StaffProfileOut` with `photo_url` populated.

---

### 7.7 Suspend

```
POST /api/v1/staff/admin/profiles/{profile_id}/suspend
Authorization: Bearer <token>  [admin+]
Content-Type: application/json
```

Sets `status = SUSPENDED` and records the reason.

**Request Body:**

```json
{
  "reason": "Under investigation for misconduct complaint #2026-034"
}
```

**Success Response `200 OK`:** Updated `StaffProfileOut`

**Errors:**
- `422 STAFF_ALREADY_SUSPENDED`
- `422 STAFF_ALREADY_TERMINATED`

**Effect on Verify:** A suspended staff member returns `result: SUSPENDED` on public verify — the staff card is shown but the citizen sees the suspension status.

---

### 7.8 Reinstate

```
POST /api/v1/staff/admin/profiles/{profile_id}/reinstate
Authorization: Bearer <token>  [admin+]
Content-Type: application/json
```

Sets `status = ACTIVE` and clears `suspension_reason`. No body required.

**Request Body:** `{}` (empty)

**Success Response `200 OK`:** Updated `StaffProfileOut`

**Errors:**
- `422 STAFF_NOT_SUSPENDED` — profile must be in SUSPENDED status

---

### 7.9 Terminate

```
POST /api/v1/staff/admin/profiles/{profile_id}/terminate
Authorization: Bearer <token>  [admin+]
Content-Type: application/json
```

Sets `status = TERMINATED` and records the reason. Termination is permanent — use Suspend for temporary holds.

**Request Body:**

```json
{
  "reason": "Employment contract ended 2026-04-30"
}
```

**Success Response `200 OK`:** Updated `StaffProfileOut`

**Errors:**
- `422 STAFF_ALREADY_TERMINATED`

**Effect on Verify:** Terminated staff return `result: TERMINATED`. The staff card is shown but clearly marked as terminated.

---

### 7.10 Mark as Verified

```
POST /api/v1/staff/admin/profiles/{profile_id}/verify
Authorization: Bearer <token>  [admin+]
```

Sets `is_verified = true`. This flag indicates the organisation has physically verified the staff member's identity documents (national ID, passport, etc.). It is separate from the public verification process.

No body required.

**Success Response `200 OK`:** Updated `StaffProfileOut` with `is_verified: true`

---

## 8. Admin Endpoints — Bulk Import

### 8.1 Start Bulk Import

```
POST /api/v1/staff/admin/bulk-import
Authorization: Bearer <token>  [admin+]
Content-Type: multipart/form-data
```

**Purpose:** Import many staff members at once from a CSV file. The CSV is processed asynchronously row by row. Failures on individual rows do not stop the import — they are recorded in the `errors` array.

**Required CSV Columns:**

| Column | Required | Notes |
|--------|----------|-------|
| first_name | Yes | |
| last_name | Yes | |
| position | Yes | Job title |
| middle_name | No | |
| phone | No | |
| email | No | |
| department | No | |
| branch_name | No | |
| employment_type | No | Default: FULL_TIME |
| hire_date | No | YYYY-MM-DD |
| id_number | No | |
| bio | No | |
| badge_number | No | |
| expertise | No | Comma-separated in quotes: `"Nursing,Triage"` |

**Example CSV:**
```csv
first_name,last_name,position,department,phone,hire_date
Amina,Hassan,Senior Nurse,Emergency,+255712000001,2019-03-15
Juma,Mwangi,Field Inspector,Operations,+255712000002,2021-07-01
Sara,Kimani,Community Officer,Outreach,+255712000003,2022-01-10
```

**Form Fields:**

| Field | Type | Required |
|-------|------|----------|
| file | .csv file | **Yes** |

**Success Response `200 OK`:**

```json
{
  "job_id": "d7e8f9a0-...",
  "status": "PENDING",
  "message": "Import job started. Check /bulk-import/{job_id} for progress."
}
```

---

### 8.2 Get Import Job Status

```
GET /api/v1/staff/admin/bulk-import/{job_id}
Authorization: Bearer <token>  [admin+]
```

Poll this endpoint to track import progress.

**Success Response `200 OK`:**

```json
{
  "id": "d7e8f9a0-...",
  "org_id": "bd877fc4-...",
  "status": "COMPLETED",
  "total_rows": 150,
  "successful_rows": 147,
  "failed_rows": 3,
  "errors": [
    {"row": 23, "error": "Missing required field: position", "data": {"first_name": "Ali"}},
    {"row": 87, "error": "Invalid employment_type: FREELANCE"},
    {"row": 134, "error": "Invalid hire_date format: 15/03/2021"}
  ],
  "original_filename": "staff_import_may2026.csv",
  "created_at": "2026-05-08T13:00:00.000000",
  "completed_at": "2026-05-08T13:00:45.000000"
}
```

**Job Status Values:**

| Status | Meaning |
|--------|---------|
| `PENDING` | Job queued, not started |
| `PROCESSING` | Currently processing rows |
| `COMPLETED` | All rows processed (check failed_rows) |
| `FAILED` | Fatal error — no rows processed |

---

## 9. Admin Endpoints — Fraud Reports

### 9.1 List Fraud Reports

```
GET /api/v1/staff/admin/fraud-reports
Authorization: Bearer <token>  [manager+]
```

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| status | string | Filter by status |
| page | integer | Default 1 |
| size | integer | Default 20, max 100 |

**Success Response `200 OK`:**

```json
{
  "items": [
    {
      "id": "a1b2c3d4-...",
      "verification_event_id": "8fc79fa7-...",
      "org_id": "bd877fc4-...",
      "reporter_name": "John Citizen",
      "reporter_phone": "+255712000099",
      "reporter_email": null,
      "claimed_staff_name": "Doctor X",
      "claimed_staff_id": "MNH-99999",
      "description": "Person demanded payment before treatment.",
      "photo_urls": ["https://minio.riviwa.com/riviwa-staff/fraud/..."],
      "status": "SUBMITTED",
      "ai_analysis": null,
      "assigned_agent_id": null,
      "resolution_notes": null,
      "created_at": "2026-05-08T10:00:00.000000",
      "updated_at": "2026-05-08T10:00:00.000000"
    }
  ],
  "total": 12,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

---

### 9.2 Get Fraud Report

```
GET /api/v1/staff/admin/fraud-reports/{report_id}
Authorization: Bearer <token>  [manager+]
```

Returns a single fraud report with all details including photo URLs.

**Success Response `200 OK`:** Single `FraudReportOut` object (same structure as list item).

---

### 9.3 Update Fraud Report

```
PATCH /api/v1/staff/admin/fraud-reports/{report_id}
Authorization: Bearer <token>  [admin+]
Content-Type: application/json
```

Update the status and/or resolution notes.

**Request Body:**

```json
{
  "status": "CONFIRMED_FRAUD",
  "resolution_notes": "Impersonator identified. Police report filed: TZ/2026/04/8872."
}
```

**Allowed status transitions:**

```
SUBMITTED → UNDER_INVESTIGATION → CONFIRMED_FRAUD → RESOLVED
SUBMITTED → UNDER_INVESTIGATION → DISMISSED
```

**Success Response `200 OK`:** Updated `FraudReportOut`

---

### 9.4 Assign Investigator

```
POST /api/v1/staff/admin/fraud-reports/{report_id}/assign
Authorization: Bearer <token>  [admin+]
Content-Type: application/json
```

Assign a specific user to investigate the fraud report.

**Request Body:**

```json
{
  "agent_user_id": "24513388-1822-486e-bec4-15c843172a3d",
  "notes": "Please prioritise — patient at risk"
}
```

**Success Response `200 OK`:** Updated `FraudReportOut` with `assigned_agent_id` set.

---

## 10. Admin Endpoints — Verifications

### 10.1 List Verification Events

```
GET /api/v1/staff/admin/verifications
Authorization: Bearer <token>  [manager+]
```

Audit log of all verify calls made against your organisation's staff.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| result | string | Filter: VALID, NOT_FOUND, SUSPENDED, etc. |
| from_date | string | ISO datetime: `2026-05-01T00:00:00` |
| to_date | string | ISO datetime: `2026-05-08T23:59:59` |
| page | integer | Default 1 |
| size | integer | Default 20, max 100 |

**Success Response `200 OK`:**

```json
{
  "items": [
    {
      "id": "8fc79fa7-af36-4df5-815a-4c23ce971204",
      "lookup_code": "MNH-00042",
      "staff_id": "efcceedd-f456-4f3f-86fa-29026965505e",
      "org_id": "bd877fc4-0439-4e7a-871b-3701b95b3a02",
      "result": "VALID",
      "scanner_lat": -6.7924,
      "scanner_lng": 39.2083,
      "scanner_ip": "196.201.45.100",
      "user_agent": "Riviwa-App/2.1 Android",
      "verified_at": "2026-05-08T14:30:00.000000"
    }
  ],
  "total": 342,
  "page": 1,
  "size": 20,
  "pages": 18
}
```

---

## 11. Analytics Endpoints

All analytics endpoints require `manager+` role. Platform admins can pass `?org_id=` to query any organisation.

---

### 11.1 Staff Overview

```
GET /api/v1/staff/analytics/overview
Authorization: Bearer <token>  [manager+]
```

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| org_id | UUID | Platform admins only |

**Success Response `200 OK`:**

```json
{
  "org_id": "bd877fc4-...",
  "total": 150,
  "active": 134,
  "suspended": 8,
  "terminated": 7,
  "on_leave": 1,
  "departments": [
    {"department": "Emergency", "count": 45},
    {"department": "ICU", "count": 32},
    {"department": "Outpatient", "count": 28},
    {"department": "Unassigned", "count": 29}
  ]
}
```

---

### 11.2 Verification Statistics

```
GET /api/v1/staff/analytics/verifications
Authorization: Bearer <token>  [manager+]
```

**Success Response `200 OK`:**

```json
{
  "org_id": "bd877fc4-...",
  "total": 1842,
  "by_result": {
    "VALID": 1753,
    "NOT_FOUND": 67,
    "SUSPENDED": 15,
    "TERMINATED": 7
  },
  "by_day": [
    {"date": "2026-05-01", "count": 89},
    {"date": "2026-05-02", "count": 102},
    ...
  ]
}
```

---

### 11.3 Feedback Statistics

```
GET /api/v1/staff/analytics/feedback
Authorization: Bearer <token>  [manager+]
```

**Success Response `200 OK`:**

```json
{
  "org_id": "bd877fc4-...",
  "total_feedback": 412,
  "avg_rating": 4.3,
  "by_rating": {
    "5": 198,
    "4": 134,
    "3": 48,
    "2": 22,
    "1": 10
  },
  "top_staff": [
    {
      "staff_id": "efcceedd-...",
      "display_name": "Dr. Amina Hassan",
      "avg_rating": 4.9,
      "feedback_count": 67
    }
  ]
}
```

---

### 11.4 Fraud Report Statistics

```
GET /api/v1/staff/analytics/fraud-reports
Authorization: Bearer <token>  [manager+]
```

**Success Response `200 OK`:**

```json
{
  "org_id": "bd877fc4-...",
  "total": 12,
  "by_status": {
    "SUBMITTED": 4,
    "UNDER_INVESTIGATION": 3,
    "CONFIRMED_FRAUD": 2,
    "DISMISSED": 2,
    "RESOLVED": 1
  }
}
```

---

## 12. Internal & Third-Party Endpoints

### 12.1 Sync Organisation

```
POST /api/v1/staff/internal/sync-org
X-Internal-Service-Key: <INTERNAL_SERVICE_KEY>
Content-Type: application/json
```

**Purpose:** Called internally by other Riviwa services to upsert an organisation into the staff_service's local org_cache. Normally this happens automatically via Kafka, but this endpoint provides a synchronous fallback.

**Request Body:**

```json
{
  "org_id": "bd877fc4-0439-4e7a-871b-3701b95b3a02",
  "name": "Muhimbili National Hospital",
  "slug": "mnh",
  "is_active": true
}
```

**Success Response `200 OK`:**

```json
{
  "org_id": "bd877fc4-0439-4e7a-871b-3701b95b3a02",
  "synced": true
}
```

---

### 12.2 Third-Party Staff Lookup

```
GET /api/v1/staff/api/lookup/{code}
X-Api-Key: <API_KEY>
```

**Purpose:** Partner systems (insurance platforms, government databases, employer verification portals) can look up a staff member by code using an API key. Returns the same public staff card as a valid verify result, but without creating a verification event.

**Authentication:** `X-Api-Key` header — currently uses the same `INTERNAL_SERVICE_KEY` value.

**Path Parameters:**

| Param | Description |
|-------|-------------|
| code | Staff code e.g. `MNH-00042` |

**Success Response `200 OK`:**

```json
{
  "staff_code": "MNH-00042",
  "display_name": "Dr. Amina Hassan",
  "position": "Senior Nurse",
  "department": "Emergency",
  "branch_name": "Muhimbili Main Campus",
  "employment_type": "FULL_TIME",
  "is_verified": true,
  "photo_url": "https://...",
  "org_id": "bd877fc4-...",
  "expertise": ["Emergency Care", "Triage"],
  "hire_year": 2019
}
```

**Errors:**
- `401` — Invalid API key
- `404 STAFF_NOT_FOUND` — Code not found in system

---

## 13. Enumerations Reference

### Employment Type (`employment_type`)

| Value | Description |
|-------|-------------|
| `FULL_TIME` | Permanent full-time employee |
| `PART_TIME` | Part-time employee |
| `CONTRACT` | Fixed-term contract |
| `INTERN` | Intern / trainee |
| `VOLUNTEER` | Unpaid volunteer |

### Staff Status (`status`)

| Value | Verify Result | Description |
|-------|--------------|-------------|
| `ACTIVE` | `VALID` | Normal working status |
| `SUSPENDED` | `SUSPENDED` | Temporarily removed from duty |
| `TERMINATED` | `TERMINATED` | No longer employed |
| `ON_LEAVE` | `ON_LEAVE` | Authorised leave |

### Verify Result (`result`)

| Value | Description |
|-------|-------------|
| `VALID` | Staff is active — identity confirmed |
| `SUSPENDED` | Staff exists but suspended |
| `TERMINATED` | Staff exists but terminated |
| `ON_LEAVE` | Staff exists but on leave |
| `NOT_FOUND` | Code not found in system |

### Fraud Report Status (`status`)

| Value | Description |
|-------|-------------|
| `SUBMITTED` | Newly received |
| `UNDER_INVESTIGATION` | Assigned to investigator |
| `CONFIRMED_FRAUD` | Impersonation confirmed |
| `DISMISSED` | Report found unfounded |
| `RESOLVED` | Case closed |

### Bulk Import Job Status

| Value | Description |
|-------|-------------|
| `PENDING` | Queued |
| `PROCESSING` | Active |
| `COMPLETED` | Finished (check failed_rows) |
| `FAILED` | Fatal error |

---

## 14. Error Codes Reference

All errors return JSON:

```json
{
  "error_code": "STAFF_NOT_FOUND",
  "message": "Staff profile not found",
  "detail": {}
}
```

| HTTP | error_code | Cause |
|------|-----------|-------|
| 401 | `TOKEN_INVALID` | Malformed or missing JWT |
| 401 | `TOKEN_EXPIRED` | JWT has expired |
| 401 | `UNAUTHORISED` | No Bearer token |
| 403 | `FORBIDDEN` | Insufficient role or wrong org |
| 403 | `ORG_INACTIVE` | Organisation is deactivated |
| 404 | `STAFF_NOT_FOUND` | Profile ID not found |
| 404 | `ORG_NOT_FOUND` | Org not in local cache |
| 404 | `FRAUD_REPORT_NOT_FOUND` | Report ID not found |
| 404 | `VERIFICATION_EVENT_NOT_FOUND` | Event ID not found |
| 404 | `BULK_IMPORT_JOB_NOT_FOUND` | Job ID not found |
| 409 | `STAFF_CODE_EXISTS` | Duplicate staff code |
| 422 | `STAFF_ALREADY_SUSPENDED` | Already in SUSPENDED status |
| 422 | `STAFF_ALREADY_TERMINATED` | Already in TERMINATED status |
| 422 | `STAFF_NOT_SUSPENDED` | Must be SUSPENDED to reinstate |
| 422 | `INVALID_FILE_TYPE` | Photo must be JPG/PNG/WEBP |
| 422 | `FILE_TOO_LARGE` | Photo exceeds 5MB |
| 422 | `VALIDATION_ERROR` | Pydantic validation failed |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## 15. Step-by-Step Implementation Guide

This section walks through how to fully integrate the staff service, from infrastructure setup to your first live verification.

---

### Step 1 — Infrastructure Setup

The service requires PostgreSQL, Redis, MinIO, and Kafka. In `docker-compose.yml`:

```yaml
staff_db:
  image: postgres:15
  environment:
    POSTGRES_USER:     staff_admin
    POSTGRES_PASSWORD: staff_pass_135
    POSTGRES_DB:       staff_db
  ports: ["5447:5432"]
  volumes: [staff_db_data:/var/lib/postgresql/data]
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U staff_admin -d staff_db"]

staff_service:
  build:
    context: ./staff_service
    dockerfile: Dockerfile
  ports: ["8135:8135"]
  environment:
    STAFF_DB_HOST:           staff_db
    DB_PORT:                 5432
    STAFF_DB_USER:           staff_admin
    STAFF_DB_PASSWORD:       staff_pass_135
    STAFF_DB_NAME:           staff_db
    AUTH_SECRET_KEY:         ${SECRET_KEY}
    AUTH_ALGORITHM:          HS256
    KAFKA_BOOTSTRAP_SERVERS: kafka-1:9092
    INTERNAL_SERVICE_KEY:    ${INTERNAL_SERVICE_KEY}
    REDIS_URL:               redis://redis:6379/10
    MINIO_ENDPOINT:          minio:9000
    MINIO_ACCESS_KEY:        ${MINIO_ACCESS_KEY}
    MINIO_SECRET_KEY:        ${MINIO_SECRET_KEY}
    STAFF_BUCKET:            riviwa-staff
    ENVIRONMENT:             production
  depends_on:
    staff_db: { condition: service_healthy }
    redis: { condition: service_healthy }
    kafka-1: { condition: service_healthy }
    minio: { condition: service_healthy }
```

---

### Step 2 — Nginx Routing

Add to `/etc/nginx/conf.d/default.conf`:

```nginx
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
```

Reload nginx after adding: `docker compose restart nginx`

---

### Step 3 — Database Migrations

The `entrypoint.sh` runs Alembic automatically on startup:

```bash
# Manual run inside container:
docker compose exec staff_service alembic upgrade head
```

The initial migration (`2026-05-08_00-00_initial_schema.py`) creates all 7 tables.

To create a new migration after model changes:

```bash
docker compose exec staff_service alembic revision --autogenerate -m "2026-05-08_12-00_add_field"
docker compose exec staff_service alembic upgrade head
```

---

### Step 4 — Org Cache Bootstrap

The service learns about organisations from the `riviwa.organisation.events` Kafka topic. When the service first starts, it replays all Kafka events from the beginning. This means:

- Existing orgs appear in `org_cache` within seconds of startup
- New orgs added after startup are synced within seconds via Kafka

**If an org is missing** (e.g. the Kafka event was lost):

```sql
INSERT INTO org_cache (org_id, name, slug, is_active, synced_at)
VALUES ('your-org-uuid', 'Org Name', 'org-slug', true, NOW())
ON CONFLICT (org_id) DO UPDATE
  SET name='Org Name', slug='org-slug', is_active=true, synced_at=NOW();
```

Or via the internal sync endpoint:

```bash
curl -X POST https://api.riviwa.com/api/v1/staff/internal/sync-org \
  -H "X-Internal-Service-Key: $INTERNAL_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"...","name":"Org Name","slug":"org-slug","is_active":true}'
```

---

### Step 5 — Authenticate and Get Org-Scoped Token

```bash
# Step 1: Login
LOGIN=$(curl -s -X POST https://api.riviwa.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"admin@yourorg.com","password":"YourPass@2026!"}')

LOGIN_TOKEN=$(echo $LOGIN | python3 -c "import sys,json; print(json.load(sys.stdin)['login_token'])")

# Step 2: Verify OTP (check email or use 000000 in staging)
VERIFY=$(curl -s -X POST https://api.riviwa.com/api/v1/auth/login/verify-otp \
  -H "Content-Type: application/json" \
  -d "{\"login_token\":\"$LOGIN_TOKEN\",\"otp_code\":\"000000\"}")

ACCESS_TOKEN=$(echo $VERIFY | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Step 3: Switch to your org
SCOPED=$(curl -s -X POST https://api.riviwa.com/api/v1/auth/switch-org \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"org_id":"YOUR_ORG_UUID"}')

ORG_TOKEN=$(echo $SCOPED | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

---

### Step 6 — Register Your First Staff Member

```bash
curl -s -X POST https://api.riviwa.com/api/v1/staff/admin/profiles \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Amina",
    "last_name": "Hassan",
    "position": "Field Agent",
    "department": "Community Outreach",
    "employment_type": "FULL_TIME",
    "phone": "+255712000001",
    "hire_date": "2022-06-01"
  }'
```

Response includes the auto-generated `staff_code` (e.g. `MYORG-00001`). Print this on the staff badge.

---

### Step 7 — Upload Staff Photo

```bash
curl -s -X POST https://api.riviwa.com/api/v1/staff/admin/profiles/{profile_id}/photo \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -F "photo=@/path/to/headshot.jpg"
```

---

### Step 8 — Bulk Import (Optional)

For large teams, prepare a CSV and import:

```bash
curl -s -X POST https://api.riviwa.com/api/v1/staff/admin/bulk-import \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -F "file=@/path/to/staff_import.csv"
```

Poll the job until `status = COMPLETED`:

```bash
curl -s https://api.riviwa.com/api/v1/staff/admin/bulk-import/{job_id} \
  -H "Authorization: Bearer $ORG_TOKEN"
```

---

### Step 9 — Citizen Verifies a Staff Member

No auth required. This is what the citizen-facing app calls:

```bash
curl -s -X POST https://api.riviwa.com/api/v1/staff/verify \
  -H "Content-Type: application/json" \
  -d '{
    "code": "MYORG-00001",
    "scanner_lat": -6.7924,
    "scanner_lng": 39.2083
  }'
```

Parse `result`:
- `VALID` → show green badge with staff card
- `SUSPENDED` / `TERMINATED` → show red warning with staff card
- `NOT_FOUND` → show fraud warning, offer to report

---

### Step 10 — Citizen Submits Feedback

Using the `verification_event_id` from Step 9:

```bash
curl -s -X POST https://api.riviwa.com/api/v1/staff/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "verification_event_id": "8fc79fa7-...",
    "rating": 5,
    "comment": "Very helpful agent.",
    "is_anonymous": true
  }'
```

---

### Step 11 — Citizen Reports Fraud

If the scan returned NOT_FOUND or the person seems suspicious:

```bash
curl -s -X POST https://api.riviwa.com/api/v1/staff/report-fraud \
  -F "description=Person claiming to be from the org was asking for cash bribes" \
  -F "reporter_name=John Citizen" \
  -F "reporter_phone=+255712000099" \
  -F "claimed_staff_name=Unknown Man in uniform" \
  -F "photos=@/path/to/suspect.jpg"
```

---

### Step 12 — Monitor with Analytics

```bash
# Staff headcount by department
curl -s "https://api.riviwa.com/api/v1/staff/analytics/overview" \
  -H "Authorization: Bearer $ORG_TOKEN"

# Verification activity (spot unusual NOT_FOUND spikes)
curl -s "https://api.riviwa.com/api/v1/staff/analytics/verifications" \
  -H "Authorization: Bearer $ORG_TOKEN"

# Staff performance scores
curl -s "https://api.riviwa.com/api/v1/staff/analytics/feedback" \
  -H "Authorization: Bearer $ORG_TOKEN"

# Fraud case pipeline
curl -s "https://api.riviwa.com/api/v1/staff/analytics/fraud-reports" \
  -H "Authorization: Bearer $ORG_TOKEN"
```

---

## 16. End-to-End Flows

### Flow A — Standard Citizen Verification

```
Citizen sees staff badge
         │
         ▼
POST /api/v1/staff/verify  {"code": "MNH-00042"}
         │
         ├── result: VALID
         │      │
         │      ├─ Show staff card (photo, name, position, department)
         │      │
         │      └─ Offer feedback form
         │              │
         │              ▼
         │         POST /api/v1/staff/feedback
         │         {"verification_event_id": "...", "rating": 4}
         │
         ├── result: SUSPENDED / TERMINATED
         │      │
         │      └─ Show warning banner + staff card
         │         "This staff member is currently suspended"
         │
         └── result: NOT_FOUND
                │
                └─ Show warning: "Code not recognised"
                   Offer fraud report button
                         │
                         ▼
                   POST /api/v1/staff/report-fraud
                   (multipart with optional photos)
```

---

### Flow B — Organisation Admin Registers Staff

```
Admin logs in → switch-org token
         │
         ▼
POST /api/v1/staff/admin/profiles
         │
         ▼
Receive staff_code: "MNH-00042"
Print on physical badge + generate QR
         │
         ├── Upload photo
         │   POST /api/v1/staff/admin/profiles/{id}/photo
         │
         ├── Link to QR service (optional)
         │   PATCH /api/v1/staff/admin/profiles/{id}
         │   {"qr_code_id": "..."}
         │
         └── Mark as verified (after checking documents)
             POST /api/v1/staff/admin/profiles/{id}/verify
```

---

### Flow C — Fraud Investigation Workflow

```
Citizen reports fraud
         │
         ▼
POST /api/v1/staff/report-fraud → status: SUBMITTED
         │
         ▼
Admin sees report in list
GET /api/v1/staff/admin/fraud-reports
         │
         ▼
Assign to investigator
POST /api/v1/staff/admin/fraud-reports/{id}/assign
{"agent_user_id": "..."}
         │
         ├── Investigator updates status
         │   PATCH /api/v1/staff/admin/fraud-reports/{id}
         │   {"status": "UNDER_INVESTIGATION"}
         │
         ├── If confirmed
         │   PATCH → {"status": "CONFIRMED_FRAUD",
         │            "resolution_notes": "Police case #..."}
         │   + Suspend or terminate the staff member
         │   POST /api/v1/staff/admin/profiles/{id}/suspend
         │
         └── If dismissed
             PATCH → {"status": "DISMISSED",
                      "resolution_notes": "Reporter could not verify claim"}
```

---

### Flow D — Bulk Onboarding

```
Prepare CSV file
         │
         ▼
POST /api/v1/staff/admin/bulk-import
    multipart: file=staff_import.csv
         │
         ▼
Receive job_id, status: PENDING
         │
    poll every 5s:
         ▼
GET /api/v1/staff/admin/bulk-import/{job_id}
         │
         ├── status: PROCESSING → keep polling
         │
         └── status: COMPLETED
                ├── successful_rows: 147
                ├── failed_rows: 3
                └── errors: [{row: 23, error: "..."}]
                     │
                     └── Fix CSV errors, re-import if needed
```

---

*Document generated 2026-05-08. Service version 1.0.0. Base URL: `https://api.riviwa.com`.*
