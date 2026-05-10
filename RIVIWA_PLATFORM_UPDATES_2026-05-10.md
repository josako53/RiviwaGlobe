# Riviwa Platform — May 2026 Update (v2.2 → v2.4)

**Date:** 2026-05-09/10  
**Version:** 2.4.0  
**Base URL:** `https://api.riviwa.com`

This document covers **only what is new or changed** since the last documented state.
For full API references see the existing docs:

| Document | Covers |
|----------|--------|
| `RIVIWA_FULL_API_REFERENCE.md` | All core services (auth, feedback, stakeholder, payment, notification) |
| `RIVIWA_STAFF_SERVICE_API.md` | Staff service — complete endpoint reference (updated for v2.4) |
| `RIVIWA_WAITING_ANALYTICS_API.md` | Waiting service basic API + analytics dashboard |
| `RIVIWA_NEW_ENDPOINTS_REFERENCE.md` | Analytics org/platform endpoints up to 2026-04-22 |
| `RIVIWA_PRODUCT_QR_VERICATION.md` | Product, QR, verification service endpoints |

---

## What Changed

| Version | Change |
|---------|--------|
| v2.4 | **Org-level feedback** — feedback no longer requires a project; `org_id` stored directly on every feedback record |
| v2.4 | **Staff feedback redesigned** — 5-star rating replaced with Riviwa feedback vocabulary |
| v2.4 | **Bug fix**: `auth_service` project activation silently dropped Kafka events (lazy-load crash) |
| v2.4 | **Bug fix**: `feedback_service` Kafka consumer stopped on exception, never restarted |
| v2.4 | **Bug fix**: Fraud reports with `org_id=null` now accessible to org admins |
| v2.3 | **4 new branch analytics endpoints** on `analytics_service` |
| v2.2 | **4 new staff-performance endpoints** on `analytics_service` (cross-service: waiting_db + feedback_db) |
| v2.2 | **3 new waiting analytics endpoints** on `waiting_service` |
| v2.2 | `analytics_service` gains read-only connection to `waiting_db` |
| v2.2 | `waiting_service` added to `docker-compose.yml` and nginx |
| v2.1 | **6 existing analytics endpoints** updated: `project_id` optional, `org_id` accepted as alternative |
| v2.1 | Bug fix: `StaffProfile.get_by_code_any_org` `MultipleResultsFound` crash |

---

## 1. New Branch Analytics Endpoints (v2.3)

All four endpoints live under `/api/v1/analytics/org/{org_id}/branches/`.  
**Auth:** Bearer JWT — org `admin`/`owner` or platform admin.

`branch_id` is denormalised onto `feedbacks` at submission time from `OrgDepartment.branch_id`, so all queries run against `feedback_db` without cross-service joins.

---

### `GET /api/v1/analytics/org/{org_id}/branches/summary`

All branches in one response, sorted by total feedback DESC.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `feedback_type` | string | Optional — `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` |
| `date_from` | date | `YYYY-MM-DD` |
| `date_to` | date | `YYYY-MM-DD` |

**Response:**
```json
{
  "org_id": "uuid",
  "date_from": "2026-05-01",
  "date_to": "2026-05-09",
  "feedback_type": null,
  "total_branches": 6,
  "items": [
    {
      "branch_id": "uuid",
      "total": 142,
      "grievances": 89,
      "suggestions": 23,
      "applause": 18,
      "inquiries": 12,
      "resolved": 95,
      "open_count": 47,
      "escalated": 8,
      "dismissed": 3,
      "overdue": 5,
      "avg_resolution_hours": 14.3,
      "resolution_rate": 66.9,
      "escalation_rate": 5.6
    }
  ]
}
```

---

### `GET /api/v1/analytics/org/{org_id}/branches/performance`

Same data as `/summary` but ranked **best → worst** by `resolution_rate`. Ties resolved by fewest `overdue`, then highest total.

Each item gains a `rank` field (1 = best). Use to identify which branches need operational support.

**Same query params as `/summary`.**

---

### `GET /api/v1/analytics/org/{org_id}/branches/trend`

Multi-branch time series — one row per `(branch_id, period)`. Use for comparison charts.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `granularity` | string | `day` | `hour` \| `day` \| `week` \| `month` |
| `feedback_type` | string | — | Optional filter |
| `date_from` / `date_to` | date | — | Date window |

**Response:**
```json
{
  "org_id": "uuid",
  "granularity": "day",
  "items": [
    {
      "branch_id": "uuid",
      "period": "2026-05-07T00:00:00Z",
      "total": 12,
      "grievances": 8,
      "suggestions": 2,
      "applause": 1,
      "inquiries": 1,
      "resolved": 7
    }
  ]
}
```

---

### `GET /api/v1/analytics/org/{org_id}/branches/{branch_id}/detail`

Complete single-branch analytics in one call.

**Query params:** `date_from`, `date_to`

**Response fields:**

| Field | Description |
|-------|-------------|
| `total`, `grievances`, `suggestions`, `applause`, `inquiries` | Feedback counts by type |
| `resolved`, `open_count`, `escalated`, `dismissed`, `overdue` | Status counts |
| `critical_open`, `high_open` | Unresolved CRITICAL/HIGH items |
| `resolution_rate`, `escalation_rate` | Percentages |
| `avg_resolution_hours` | Mean hours from submitted_at to resolved_at |
| `by_department` | Array — per-department breakdown within the branch |
| `by_category` | Array — top 15 categories (grievances, resolved counts) |
| `by_service` | Array — top 10 services |
| `trend` | Array — daily time series for the selected window |

---

## 2. New Staff Performance Analytics Endpoints (v2.2)

Four endpoints on `analytics_service` that join `waiting_db` (queue data) and `feedback_db` (feedback data) in Python. The analytics_service opens a read-only asyncpg connection to `waiting_db`.

**Auth:** Bearer JWT — org `admin`/`owner` or platform admin.

---

### `GET /api/v1/analytics/org/{org_id}/staff-performance`

Per-staff member: queue throughput correlated with feedback submitted during their duty window.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | date | 7 days ago | Start of window |
| `date_to` | date | now | End of window |
| `service_point_id` | uuid | — | Optional — filter to one service point |

**Response:**
```json
{
  "org_id": "uuid",
  "total_staff": 8,
  "items": [
    {
      "staff_user_id": "uuid",
      "service_point_id": "uuid",
      "service_point_name": "Customer Care Counter A",
      "point_type": "SERVICE",
      "tickets_served": 45,
      "avg_wait_seconds": 480.0,
      "avg_service_seconds": 210.0,
      "min_wait_seconds": 45.0,
      "max_wait_seconds": 1920.0,
      "first_attended_at": "2026-05-08T08:12:00Z",
      "last_finished_at": "2026-05-08T17:45:00Z",
      "feedback_total": 12,
      "feedback_grievances": 4,
      "feedback_suggestions": 2,
      "feedback_applause": 5,
      "feedback_inquiries": 1
    }
  ]
}
```

> Feedback counts reflect all feedback submitted to the org during each staff member's exact duty window (`first_attended_at` → `last_finished_at`), not per-transaction attribution.

---

### `GET /api/v1/analytics/org/{org_id}/staff-duty`

All staff duty sessions in a period — who was on duty, at which counter and service point.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` / `date_to` | date | today | Date window |
| `is_active` | bool | — | `true` = currently active sessions only |

**Response:** `{ total_sessions, active_sessions, items: [ { session_id, staff_user_id, counter_name, counter_code, service_point_name, point_type, opened_at, closed_at, is_active, tickets_served, avg_service_seconds } ] }`

---

### `GET /api/v1/analytics/org/{org_id}/waiting-vs-feedback`

Side-by-side per period: average queue wait time vs. feedback volume.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `granularity` | string | `hour` | `hour` \| `day` \| `week` |
| `date_from` / `date_to` | date | last 1 day (hour) / 7 days (day) | Date window |
| `feedback_type` | string | — | Optional filter |

**Response:**
```json
{
  "granularity": "hour",
  "items": [
    {
      "period": "2026-05-08T10:00:00Z",
      "tickets_served": 18,
      "avg_wait_seconds": 1320.0,
      "avg_service_seconds": 420.0,
      "min_wait_seconds": 60.0,
      "max_wait_seconds": 3600.0,
      "feedback_total": 7,
      "feedback_grievances": 5,
      "feedback_applause": 1,
      "feedback_suggestions": 1,
      "feedback_inquiries": 0
    }
  ]
}
```

> Use `granularity=hour` with a 1–3 day range to detect intra-day wait→complaint correlations.

---

### `GET /api/v1/analytics/org/{org_id}/feedback-timing`

Hour-of-day × day-of-week heatmap. Each cell is one `(hour, weekday)` combination aggregated over the date range.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` / `date_to` | date | last 30 days | Date window |
| `feedback_type` | string | — | Optional filter |

**Response:**
```json
{
  "peak_hour": 10,
  "peak_day": "Monday",
  "cells": [
    {
      "hour_of_day": 10,
      "day_of_week": 1,
      "day_name": "Monday",
      "total": 28,
      "grievances": 19,
      "suggestions": 3,
      "applause": 4,
      "inquiries": 2
    }
  ]
}
```

> `day_of_week`: 0 = Sunday, 1 = Monday, … 6 = Saturday.

---

## 3. New Waiting Service Analytics Endpoints (v2.2)

Added to `waiting_service` (port 8130). **Auth:** Bearer JWT — org `manager`/`admin`/`owner` role.  
These endpoints were **not included** in `RIVIWA_WAITING_ANALYTICS_API.md` (generated before v2.2).

---

### `GET /api/v1/waiting/analytics/staff-duty`

**Query params:** `org_id` (required), `date_from`, `date_to`, `is_active`

Returns all staff duty sessions with counter and service-point details.

**Response:** `{ org_id, date_from, date_to, total_sessions, active_sessions, items: [ { session_id, staff_user_id, counter_name, counter_code, service_point_name, point_type, opened_at, closed_at, is_active, tickets_served, avg_service_seconds } ] }`

---

### `GET /api/v1/waiting/analytics/by-period`

**Query params:** `org_id` (required), `granularity` (`hour`|`day`|`week`, default `hour`), `date_from`, `date_to`

Queue wait and service times bucketed by period. Use for queue pressure charts.

**Response:** `{ org_id, granularity, date_from, date_to, items: [ { period, tickets_served, avg_wait_seconds, avg_service_seconds, min_wait_seconds, max_wait_seconds } ] }`

---

### `GET /api/v1/waiting/analytics/by-service-point`

**Query params:** `org_id` (required), `date_from`, `date_to` (default: last 7 days)

Per-service-point throughput and wait times, ordered by worst average wait first.

**Response:** `{ org_id, date_from, date_to, items: [ { service_point_id, service_point_name, point_type, tickets_served, avg_wait_seconds, avg_service_seconds, max_wait_seconds, min_wait_seconds } ] }`

---

## 4. Updated Endpoints — `project_id` Now Optional (v2.1)

Six existing analytics endpoints now accept `org_id` as an alternative to `project_id`. When `org_id` is provided, the service resolves all project IDs for that org and aggregates results across them.

| Endpoint | Previous behaviour | New behaviour |
|----------|-------------------|---------------|
| `GET /api/v1/analytics/feedback/overdue` | `project_id` required | `project_id` **or** `org_id` |
| `GET /api/v1/analytics/feedback/by-category` | `project_id` required | `project_id` **or** `org_id` |
| `GET /api/v1/analytics/grievances/sla-status` | `project_id` required | `project_id` **or** `org_id` |
| `GET /api/v1/analytics/grievances/dashboard` | `project_id` required | `project_id` **or** `org_id` |
| `GET /api/v1/analytics/grievances/hotspots` | `project_id` required | `project_id` **or** `org_id` |
| `GET /api/v1/analytics/suggestions/frequency` | `project_id` required | `project_id` **or** `org_id` |

Passing both is invalid — use one or the other.

---

## 5. Infrastructure Changes (v2.2)

### `docker-compose.yml`

```yaml
# Added
waiting_db:       postgres:15, port 5448, volume waiting_db_data
waiting_service:  build ./waiting_service, port 8130, depends: waiting_db + kafka-1 + redis

# analytics_service — new env vars
WAITING_DB_HOST:     waiting_db
WAITING_DB_PORT:     5432
WAITING_DB_USER:     waiting_admin
WAITING_DB_PASSWORD: waiting_pass_130
WAITING_DB_NAME:     waiting_db
# analytics_service — new depends_on
waiting_db: condition: service_healthy
```

### `nginx/nginx.conf`

```nginx
# Added
location /api/v1/waiting {
    set $waiting http://waiting_service:8130;
    proxy_pass $waiting;
    include /etc/nginx/proxy_params;
    include /etc/nginx/cors_params;
}
location /health/waiting {
    set $waiting http://waiting_service:8130;
    proxy_pass $waiting/health;
    include /etc/nginx/proxy_params;
}
```

### `analytics_service` — new DB connection

`analytics_service` now holds three read-only cross-service connections:

| Connection | Purpose |
|-----------|---------|
| `feedback_db` | All feedback/grievance/suggestion/applause/inquiry analytics |
| `analytics_db` | Pre-computed Spark output (read/write) |
| `waiting_db` *(new)* | Staff session and queue wait-time analytics |

---

## 6. Bug Fix (v2.1)

**`staff_service` — `get_by_code_any_org` MultipleResultsFound**

When the same staff code pattern existed across multiple orgs, `scalar_one_or_none()` raised `MultipleResultsFound`. Fixed to `.limit(1).scalars().first()` ordered by `created_at DESC`. Committed `e8bdc2d`.

---

## 7. Staff Feedback Redesign (v2.4)

### What changed

The staff feedback endpoint previously accepted a numeric `rating` (integer 1–5). This is replaced with `feedback_type`, using the same four-value vocabulary as all other Riviwa feedback surfaces.

**Migration:** `c3d4e5f6a7b8` drops the `rating` column and adds `feedback_type VARCHAR(20)` with an index. Non-destructive — the column is new, no existing data is migrated.

### `POST /api/v1/staff/feedback` — field change

**Before:**
```json
{ "verification_event_id": "...", "rating": 5, "comment": "..." }
```

**After:**
```json
{ "verification_event_id": "...", "feedback_type": "applause", "comment": "..." }
```

`feedback_type` accepts: `grievance` | `suggestion` | `applause` | `inquiry`

### `GET /api/v1/staff/analytics/feedback` — response change

**Before:**
```json
{
  "avg_rating": 4.3,
  "by_rating": { "5": 198, "4": 134, "3": 48, "2": 22, "1": 10 }
}
```

**After:**
```json
{
  "total": 412,
  "applause_rate": 74.3,
  "by_type": { "grievance": 62, "suggestion": 44, "applause": 306, "inquiry": 0 },
  "by_staff": [
    {
      "staff_id": "uuid",
      "total": 67,
      "grievances": 2,
      "suggestions": 5,
      "applause": 58,
      "inquiries": 2,
      "applause_rate": 86.6
    }
  ]
}
```

**`applause_rate`** is the primary performance metric: `applause / total × 100`. It produces the same quality signal as the org-level feedback analytics and removes the ambiguity of numeric averages (is 4.2 good? compared to what?).

### Database schema diff (`staff_feedbacks` table)

| Column | v2.3 | v2.4 |
|--------|------|------|
| `rating` | INTEGER (1–5) | **Removed** |
| `feedback_type` | — | VARCHAR(20), indexed |

---

## 8. Bug Fixes (v2.4)

### `auth_service` — Project Kafka events silently dropped

**Symptom:** Activating an org project via `POST /api/v1/orgs/{org_id}/projects/{id}/activate` returned 200, but the `org_project.published` event was never delivered to Kafka consumers (`feedback_service`, `stakeholder_service`). Projects did not appear in `fb_projects` and feedback submissions returned `PROJECT_NOT_FOUND`.

**Root cause:** `_project_payload()` in `events/publisher.py` accessed `project.organisation.display_name` — a SQLAlchemy lazy relationship — after the DB session had been committed. In an async context this raises `greenlet_spawn has not been called`, which was caught and logged as `project_service.publish_failed` but silently dropped.

**Fix:** Set `org_display_name: None` in the payload. The field is already populated by the separate `org.updated` event path. Committed `f01a787`.

**Effect:** All project activations now publish correctly. Projects sync to `feedback_db` within ~15 seconds of activation.

---

### `feedback_service` — Kafka consumer stopped permanently on exception

**Symptom:** After a transient error (network hiccup, malformed message), the consumer task stopped and was never restarted. Subsequent Kafka events were committed by the broker but not processed.

**Fix:** Split `_consume_loop` into `_consume_once` (single run) + `_consume_loop` (retry wrapper with exponential backoff 5 s → 60 s). Committed `e7e8526`.

---

### `staff_service` — Fraud reports with `org_id=null` returned 403 to org admins

**Symptom:** Public fraud reports submitted without a `verification_event_id` have `org_id=null`. When an org admin tried to view or update these reports, the service compared `null != org_id` and raised 403.

**Fix:** Service now treats `org_id=null` as "unaffiliated — any org admin may investigate." The first org admin to update a null-org report stamps their `org_id` on it for future scoping. Committed `8891d83`.

---

## 9. Org-Level Feedback — Project No Longer Required (v2.4)

### Architecture

Previously every feedback submission had to reference a GRM `project_id`. This created two problems:

1. Organisations without an active GRM project could not receive feedback at all.
2. Feedback about a branch, department, service, or product (e.g. "your billing team is slow") had no natural home if it didn't relate to a specific project.

**v2.4 decouples feedback from projects.** `org_id` is now stored directly on every feedback record, denormalised at submission time. Feedback can target any combination of:

| Scope | Field |
|-------|-------|
| Organisation (top-level) | `org_id` only — no `project_id` required |
| Branch | `branch_id` |
| Department | `department_id` |
| Service / Programme | `service_id` |
| Product | `product_id` |
| Sub-project / Work package | `subproject_id` |

A `project_id` is still accepted and is recommended for GRM-managed projects. When present, `org_id` is derived automatically from the project's owning organisation.

### Database Change

**Migration `e9f0a1b2c3d4`** (down: `d8e9f0a1b2c3`):

```sql
ALTER TABLE feedbacks ADD COLUMN org_id UUID;
CREATE INDEX ix_feedbacks_org_id ON feedbacks (org_id);

-- back-fill existing rows that have a project
UPDATE feedbacks f
SET    org_id = p.organisation_id
FROM   fb_projects p
WHERE  f.project_id = p.id
  AND  f.org_id IS NULL;
```

### `org_id` Resolution at Submission

```
effective_org_id =
    project.organisation_id   -- if project_id supplied
    ?? explicit_org_id         -- field on StaffSubmitFeedback
    ?? token.org_id            -- org scope of the submitting user's JWT
```

### `POST /api/v1/feedback` — schema change

`project_id` is now **optional**. Either `project_id` or `org_id` must be provided (not both required, but at least one).

**Before (v2.3):**
```json
{ "project_id": "uuid (required)", "feedback_type": "grievance", ... }
```

**After (v2.4):**
```json
{ "org_id": "uuid", "feedback_type": "grievance", ... }
```
or:
```json
{ "project_id": "uuid", "feedback_type": "grievance", ... }
```

Validation: if neither `project_id` nor `org_id` is supplied → HTTP 422 `"Provide either project_id or org_id"`.

### `feedback_type` — `inquiry` added

`StaffSubmitFeedback` now accepts `inquiry` alongside `grievance | suggestion | applause`.

### Analytics Impact

All 30 org-scoped analytics queries now filter on `feedbacks.org_id` directly instead of JOINing through `fb_projects`. This means:

- Org analytics now include **project-less feedback** automatically.
- No JOIN overhead on every analytics query.
- Analytics work for orgs that have never created a GRM project.

The five project-centric queries (e.g. `FROM fb_projects LEFT JOIN feedbacks`) are unchanged — they still require a `project_id`.

### Consumer Submission

`POST /api/v1/my/feedback` already accepted `project_id` as optional. Consumers do not supply `org_id` directly — it is resolved from the JWT's org scope or from the AI-detected project. No change to the consumer schema.

---

*Riviwa Platform v2.4.0 — 2026-05-10*
