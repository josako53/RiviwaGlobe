# Riviwa — Staff Performance Analytics API Reference

> **Services:** `analytics_service` (port 8095) · `waiting_service` (port 8130)  
> **Base URLs:**  
> &nbsp;&nbsp;`https://api.riviwa.com/api/v1/analytics/org/{org_id}` — cross-service endpoints  
> &nbsp;&nbsp;`https://api.riviwa.com/api/v1/waiting/analytics` — queue-native endpoints  
> **Version:** 2.2.0 · **Added:** 2026-05-09  
> **Sources:**  
> &nbsp;&nbsp;`analytics_service/api/v1/staff_performance.py`  
> &nbsp;&nbsp;`analytics_service/schemas/staff_performance.py`  
> &nbsp;&nbsp;`waiting_service/api/v1/analytics.py`  
> &nbsp;&nbsp;`waiting_service/schemas/analytics.py`

---

## Contents

1. [Overview](#1-overview)
2. [Architecture — Two Data Sources](#2-architecture--two-data-sources)
3. [Authentication](#3-authentication)
4. [Common Parameters](#4-common-parameters)
5. [Endpoints — analytics_service](#5-endpoints--analytics_service)
   - 5.1 [GET /staff-performance](#51-get-staff-performance)
   - 5.2 [GET /staff-duty](#52-get-staff-duty-analytics_service)
   - 5.3 [GET /waiting-vs-feedback](#53-get-waiting-vs-feedback)
   - 5.4 [GET /feedback-timing](#54-get-feedback-timing)
6. [Endpoints — waiting_service](#6-endpoints--waiting_service)
   - 6.1 [GET /waiting/analytics/staff-duty](#61-get-waitinganalyticsstaff-duty)
   - 6.2 [GET /waiting/analytics/by-period](#62-get-waitinganalyticsby-period)
   - 6.3 [GET /waiting/analytics/by-service-point](#63-get-waitinganalyticsby-service-point)
7. [Response Schemas](#7-response-schemas)
8. [Field Definitions](#8-field-definitions)
9. [Error Responses](#9-error-responses)
10. [Usage Patterns](#10-usage-patterns)

---

## 1. Overview

Seven endpoints deliver staff performance and queue analytics across two services:

| # | Endpoint | Service | What it answers |
|---|----------|---------|----------------|
| 1 | `GET /analytics/org/{org_id}/staff-performance` | analytics | Which staff served how many customers, how long they made customers wait, and how much feedback arrived during each shift |
| 2 | `GET /analytics/org/{org_id}/staff-duty` | analytics | Who was on duty, at which counter, when |
| 3 | `GET /analytics/org/{org_id}/waiting-vs-feedback` | analytics | Did long queue waits cause more complaints? |
| 4 | `GET /analytics/org/{org_id}/feedback-timing` | analytics | Which hour and day of the week gets the most feedback? |
| 5 | `GET /waiting/analytics/staff-duty` | waiting | Same duty session data, sourced directly from waiting_service |
| 6 | `GET /waiting/analytics/by-period` | waiting | Queue pressure over time — hourly or daily |
| 7 | `GET /waiting/analytics/by-service-point` | waiting | Which service point has the worst average wait? |

---

## 2. Architecture — Two Data Sources

The four `analytics_service` endpoints (#1–#4) query **two separate databases** at request time:

```
analytics_service
    ├── waiting_db (read-only) ── staff sessions, queue tickets, wait durations
    └── feedback_db (read-only) ── grievances, suggestions, applause, inquiries
```

The three `waiting_service` endpoints (#5–#7) query **only `waiting_db`** — they are the queue-native view of the same data, requiring no cross-service join.

### `waiting_db` tables used

| Table | Contents |
|-------|----------|
| `staff_sessions` | One row per counter session a staff member opens; stores `opened_at`, `closed_at`, `tickets_served`, `avg_service_seconds` |
| `queue_ticket_stages` | One row per service point a ticket passes through; stores `wait_duration_seconds`, `service_duration_seconds`, `assigned_staff_user_id`, `finished_at` |
| `service_points` | Named service locations; provides `name` and `point_type` |
| `staff_counters` | Individual desks within a service point; provides `name` and `code` |

### `feedback_db` tables used

| Table | Contents |
|-------|----------|
| `feedbacks` | All feedback submissions with `feedback_type`, `submitted_at`, and `branch_id` / `department_id` |
| `fb_projects` | Joins `feedbacks` → `organisation_id` so queries can be scoped by org |

### Feedback attribution model

The feedback counts on `/staff-performance` are **not** per-transaction. The service:
1. Finds each staff member's first `attending_started_at` and last `finished_at` across all tickets they served in the period
2. Counts **all feedback submitted to the org** during that time window

This means if Staff A served customers 08:00–17:00 and 15 grievances were filed during that shift (by anyone), those 15 appear on Staff A's record. This is a duty-window correlation, not individual attribution.

---

## 3. Authentication

### analytics_service endpoints (`/analytics/org/{org_id}/...`)

Requires a **Bearer JWT** with org `admin` or `owner` role, **or** platform `admin`/`super_admin`.

```
Authorization: Bearer <access_token>
```

`member` and `manager` roles receive **403 Forbidden**.

The token's embedded `org_id` must match the `org_id` path parameter. Platform admins bypass this check and can query any org.

### waiting_service endpoints (`/waiting/analytics/...`)

Requires a Bearer JWT with org `manager`, `admin`, or `owner` role, **or** platform admin.

```
Authorization: Bearer <access_token>
```

`member` role receives **403 Forbidden**. The token's `org_id` must match the `org_id` query parameter.

### Getting a token

```http
POST /api/v1/auth/login
{ "identifier": "manager@example.com", "password": "..." }
→ { "login_token": "..." }

POST /api/v1/auth/login/verify-otp
{ "login_token": "...", "otp_code": "123456" }
→ { "access_token": "..." }
```

Switch org to embed `org_id` in the token:

```http
POST /api/v1/orgs/{org_id}/switch
→ { "tokens": { "access_token": "..." } }
```

---

## 4. Common Parameters

### `analytics_service` endpoints — date parameters

All four analytics_service endpoints accept `date_from` and `date_to` as `YYYY-MM-DD` strings (not `date` objects — the service parses them internally).

| Parameter | Type | Description | Behaviour when omitted |
|-----------|------|-------------|----------------------|
| `date_from` | string | `YYYY-MM-DD` — window start | Defaults to midnight UTC N days ago (N varies per endpoint) |
| `date_to` | string | `YYYY-MM-DD` — window end | Defaults to `now()` UTC |

When provided, `date_from` is interpreted as `00:00:00 UTC` on that day; `date_to` as `23:59:59 UTC` on that day.

### `waiting_service` endpoints — date parameters

Same string format (`YYYY-MM-DD`), same interpretation.

---

## 5. Endpoints — analytics_service

All four endpoints live under `/api/v1/analytics/org/{org_id}/`.

---

### 5.1 `GET /staff-performance`

**Full path:** `GET /api/v1/analytics/org/{org_id}/staff-performance`

Returns one item per staff member (per service point) who served at least one customer in the period. Combines queue metrics from `waiting_db` with feedback volume from `feedback_db`.

#### Query parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `date_from` | string | No | 7 days ago (midnight UTC) | Window start |
| `date_to` | string | No | now | Window end |
| `service_point_id` | UUID | No | — | Restrict to one service point |

#### How results are grouped

Results are grouped by `(assigned_staff_user_id, service_point_id)`. If a staff member worked at two different service points during the period, they appear as **two separate items** — one per service point.

#### Request

```http
GET /api/v1/analytics/org/3fa85f64-5717-4562-b3fc-2c963f66afa6/staff-performance
    ?date_from=2026-05-01
    &date_to=2026-05-09
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "date_from": "2026-05-01",
  "date_to": "2026-05-09",
  "total_staff": 5,
  "items": [
    {
      "staff_user_id": "user-uuid-0001",
      "service_point_id": "sp-uuid-0001",
      "service_point_name": "Customer Care Counter A",
      "point_type": "SERVICE",
      "tickets_served": 87,
      "avg_wait_seconds": 312.4,
      "avg_service_seconds": 185.0,
      "min_wait_seconds": 18.0,
      "max_wait_seconds": 1840.0,
      "first_attended_at": "2026-05-01T07:58:22Z",
      "last_finished_at": "2026-05-09T16:44:51Z",
      "feedback_total": 34,
      "feedback_grievances": 11,
      "feedback_suggestions": 8,
      "feedback_applause": 12,
      "feedback_inquiries": 3
    },
    {
      "staff_user_id": "user-uuid-0002",
      "service_point_id": "sp-uuid-0001",
      "service_point_name": "Customer Care Counter A",
      "point_type": "SERVICE",
      "tickets_served": 62,
      "avg_wait_seconds": 528.7,
      "avg_service_seconds": 220.3,
      "min_wait_seconds": 45.0,
      "max_wait_seconds": 2910.0,
      "first_attended_at": "2026-05-02T08:01:05Z",
      "last_finished_at": "2026-05-08T17:02:18Z",
      "feedback_total": 29,
      "feedback_grievances": 18,
      "feedback_suggestions": 4,
      "feedback_applause": 5,
      "feedback_inquiries": 2
    }
  ]
}
```

#### Notes

- Items are ordered by `tickets_served DESC` (highest throughput first).
- `avg_wait_seconds` is the average of `queue_ticket_stages.wait_duration_seconds` across all stages where this staff member was the `assigned_staff_user_id` and stage status is `FINISHED`.
- `feedback_*` counts reflect **all** feedback submitted to the org between `first_attended_at` and `last_finished_at`. Two staff members with overlapping shifts will show overlapping feedback counts — this is expected.
- If a staff member has no completed ticket stages in the period, they do not appear in the response.
- `service_point_id` and `service_point_name` can be `null` if the stage record has no linked service point (data integrity edge case).

---

### 5.2 `GET /staff-duty` (analytics_service)

**Full path:** `GET /api/v1/analytics/org/{org_id}/staff-duty`

Lists all `StaffSession` records opened within the date window. Each session represents one continuous duty period a staff member spent at a specific counter. Reads only `waiting_db`.

#### Query parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `date_from` | string | No | Today (midnight UTC) | Window start |
| `date_to` | string | No | now | Window end |
| `is_active` | boolean | No | — | `true` → only sessions still open; `false` → only closed sessions; omit → all |

#### Request

```http
GET /api/v1/analytics/org/3fa85f64-5717-4562-b3fc-2c963f66afa6/staff-duty
    ?is_active=true
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "date_from": "2026-05-10",
  "date_to": "2026-05-10",
  "total_sessions": 4,
  "active_sessions": 3,
  "items": [
    {
      "session_id": "sess-uuid-0001",
      "staff_user_id": "user-uuid-0001",
      "counter_name": "Counter 1",
      "counter_code": "C1",
      "service_point_id": "sp-uuid-0001",
      "service_point_name": "Customer Care Counter A",
      "point_type": "SERVICE",
      "opened_at": "2026-05-10T07:55:00Z",
      "closed_at": null,
      "is_active": true,
      "tickets_served": 14,
      "avg_service_seconds": 192.5
    },
    {
      "session_id": "sess-uuid-0002",
      "staff_user_id": "user-uuid-0003",
      "counter_name": "Counter 2",
      "counter_code": "C2",
      "service_point_id": "sp-uuid-0001",
      "service_point_name": "Customer Care Counter A",
      "point_type": "SERVICE",
      "opened_at": "2026-05-10T08:00:00Z",
      "closed_at": "2026-05-10T12:30:00Z",
      "is_active": false,
      "tickets_served": 22,
      "avg_service_seconds": 175.0
    }
  ]
}
```

#### Notes

- Items are ordered by `opened_at DESC` (most recently opened first).
- `active_sessions` is the count of items where `is_active = true`, regardless of any `is_active` filter applied.
- `closed_at` is `null` for active sessions.
- `avg_service_seconds` reflects the running average maintained on the `StaffSession` row — it is updated as each ticket is completed and may lag slightly behind real-time.
- `staff_user_id` maps to `auth_service` user UUIDs. Resolve names via `GET /api/v1/users/{user_id}`.

---

### 5.3 `GET /waiting-vs-feedback`

**Full path:** `GET /api/v1/analytics/org/{org_id}/waiting-vs-feedback`

Joins two period-bucketed time series — queue wait times from `waiting_db` and feedback volume from `feedback_db` — into a single response. Each item represents one time period with both queue and feedback data side by side.

#### Query parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `granularity` | string | No | `hour` | `hour` \| `day` \| `week`. Invalid values fall back to `hour`. |
| `date_from` | string | No | 1 day ago (`hour`) / 7 days ago (`day`/`week`) | Window start |
| `date_to` | string | No | now | Window end |
| `feedback_type` | string | No | — | Restrict feedback counts to one type: `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` |

#### How merging works

The service queries both databases independently and merges on the `period` key in Python:

- Periods that have queue data but no feedback → `feedback_*` fields are `0`
- Periods that have feedback but no queue activity → `tickets_served` is `0`, wait fields are `null`
- A period present in neither source is never returned

#### Request

```http
GET /api/v1/analytics/org/3fa85f64-5717-4562-b3fc-2c963f66afa6/waiting-vs-feedback
    ?granularity=hour
    &date_from=2026-05-09
    &date_to=2026-05-09
    &feedback_type=GRIEVANCE
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "granularity": "hour",
  "date_from": "2026-05-09",
  "date_to": "2026-05-09",
  "items": [
    {
      "period": "2026-05-09T08:00:00Z",
      "tickets_served": 12,
      "avg_wait_seconds": 210.5,
      "avg_service_seconds": 165.0,
      "min_wait_seconds": 30.0,
      "max_wait_seconds": 840.0,
      "feedback_total": 2,
      "feedback_grievances": 2,
      "feedback_suggestions": 0,
      "feedback_applause": 0,
      "feedback_inquiries": 0
    },
    {
      "period": "2026-05-09T10:00:00Z",
      "tickets_served": 28,
      "avg_wait_seconds": 1380.0,
      "avg_service_seconds": 240.0,
      "min_wait_seconds": 120.0,
      "max_wait_seconds": 3240.0,
      "feedback_total": 9,
      "feedback_grievances": 9,
      "feedback_suggestions": 0,
      "feedback_applause": 0,
      "feedback_inquiries": 0
    },
    {
      "period": "2026-05-09T11:00:00Z",
      "tickets_served": 0,
      "avg_wait_seconds": null,
      "avg_service_seconds": null,
      "min_wait_seconds": null,
      "max_wait_seconds": null,
      "feedback_total": 3,
      "feedback_grievances": 3,
      "feedback_suggestions": 0,
      "feedback_applause": 0,
      "feedback_inquiries": 0
    }
  ]
}
```

#### Notes

- `period` is the **bucket start** in UTC (PostgreSQL `date_trunc` output). For `hour`, the value is always on the hour (e.g., `10:00:00`, not `10:23:00`).
- Items are ordered by `period ASC`.
- When `feedback_type` is applied, `feedback_total` reflects only the filtered type; `feedback_grievances`/`suggestions`/`applause`/`inquiries` sub-counts still reflect actual type breakdown within the filtered set (so the unfiltered sub-counts remain `0` for excluded types).
- `granularity=week` is available but `month` is not (query falls back to `hour`).
- The feedback query joins `feedbacks → fb_projects` on `organisation_id`, so it captures feedback from **all projects** under the org.

---

### 5.4 `GET /feedback-timing`

**Full path:** `GET /api/v1/analytics/org/{org_id}/feedback-timing`

Returns a **hour-of-day × day-of-week heatmap** showing when feedback volume peaks. Each cell represents one `(hour, weekday)` combination, aggregated across all days in the date range. Reads only `feedback_db`.

#### Query parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `date_from` | string | No | 30 days ago | Window start |
| `date_to` | string | No | now | Window end |
| `feedback_type` | string | No | — | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` |

#### Request

```http
GET /api/v1/analytics/org/3fa85f64-5717-4562-b3fc-2c963f66afa6/feedback-timing
    ?date_from=2026-04-01
    &date_to=2026-05-09
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "date_from": "2026-04-01",
  "date_to": "2026-05-09",
  "peak_hour": 10,
  "peak_day": "Monday",
  "cells": [
    {
      "hour_of_day": 8,
      "day_of_week": 1,
      "day_name": "Monday",
      "total": 14,
      "grievances": 9,
      "suggestions": 2,
      "applause": 2,
      "inquiries": 1
    },
    {
      "hour_of_day": 9,
      "day_of_week": 1,
      "day_name": "Monday",
      "total": 21,
      "grievances": 15,
      "suggestions": 3,
      "applause": 2,
      "inquiries": 1
    },
    {
      "hour_of_day": 10,
      "day_of_week": 1,
      "day_name": "Monday",
      "total": 38,
      "grievances": 28,
      "suggestions": 4,
      "applause": 4,
      "inquiries": 2
    },
    {
      "hour_of_day": 14,
      "day_of_week": 5,
      "day_name": "Friday",
      "total": 19,
      "grievances": 12,
      "suggestions": 2,
      "applause": 3,
      "inquiries": 2
    }
  ]
}
```

#### Notes

- `peak_hour` and `peak_day` identify the single cell with the highest `total` across the entire heatmap. Computed in Python after the DB query.
- `day_of_week` follows PostgreSQL `EXTRACT(DOW ...)` convention: **0 = Sunday, 1 = Monday, …, 6 = Saturday**.
- `hour_of_day` is UTC (`EXTRACT(HOUR FROM submitted_at AT TIME ZONE 'UTC')`). If customers are in a different timezone, offset accordingly.
- Only cells with at least one feedback record are returned. Cells with zero feedback are **not** in the response.
- Cells are ordered by `day_of_week ASC, hour_of_day ASC`.
- A 30-day window gives 168 possible cells (24h × 7 days). Most orgs will have 20–100 non-empty cells depending on operating hours.

---

## 6. Endpoints — waiting_service

All three endpoints live under `/api/v1/waiting/analytics/`. They query `waiting_db` directly without any feedback data. **Auth: Bearer JWT with org `manager`/`admin`/`owner` or platform admin.**

---

### 6.1 `GET /waiting/analytics/staff-duty`

**Full path:** `GET /api/v1/waiting/analytics/staff-duty`

Returns staff duty sessions from `waiting_db` directly. Functionally similar to `analytics_service /staff-duty` but served from `waiting_service` — useful when you want real-time session data without going through `analytics_service`.

#### Query parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `org_id` | UUID | **Yes** | — | Organisation to query |
| `date_from` | string | No | Today (midnight UTC) | `YYYY-MM-DD` |
| `date_to` | string | No | now | `YYYY-MM-DD` |
| `is_active` | boolean | No | — | Filter to active/closed sessions |

#### Request

```http
GET /api/v1/waiting/analytics/staff-duty
    ?org_id=3fa85f64-5717-4562-b3fc-2c963f66afa6
    &is_active=true
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "date_from": "2026-05-10",
  "date_to": "2026-05-10",
  "total_sessions": 3,
  "active_sessions": 3,
  "items": [
    {
      "session_id": "sess-uuid-0001",
      "staff_user_id": "user-uuid-0001",
      "counter_name": "Counter 1",
      "counter_code": "C1",
      "service_point_id": "sp-uuid-0001",
      "service_point_name": "Customer Care Counter A",
      "point_type": "SERVICE",
      "opened_at": "2026-05-10T07:55:00Z",
      "closed_at": null,
      "is_active": true,
      "tickets_served": 14,
      "avg_service_seconds": 192.5
    }
  ]
}
```

#### Difference from `/analytics/org/{id}/staff-duty`

| | `waiting_service` | `analytics_service` |
|-|-------------------|---------------------|
| `org_id` | Query param (required) | Path param |
| Min auth role | `manager` | `admin` |
| Data source | `waiting_db` (direct) | `waiting_db` (via `WaitingAnalyticsRepository`) |
| Response schema | `StaffDutyOut` | `StaffDutyResponse` |
| Schema differences | None — field names are identical | — |

---

### 6.2 `GET /waiting/analytics/by-period`

**Full path:** `GET /api/v1/waiting/analytics/by-period`

Queue wait and service time statistics bucketed by time period. Use for queue pressure charts and intra-day throughput analysis.

#### Query parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `org_id` | UUID | **Yes** | — | Organisation to query |
| `granularity` | string | No | `hour` | `hour` \| `day` \| `week`. Invalid values fall back to `hour`. |
| `date_from` | string | No | 1 day ago (`hour`) / 7 days ago (`day`/`week`) | `YYYY-MM-DD` |
| `date_to` | string | No | now | `YYYY-MM-DD` |

#### Request

```http
GET /api/v1/waiting/analytics/by-period
    ?org_id=3fa85f64-5717-4562-b3fc-2c963f66afa6
    &granularity=hour
    &date_from=2026-05-09
    &date_to=2026-05-09
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "granularity": "hour",
  "date_from": "2026-05-09",
  "date_to": "2026-05-09",
  "items": [
    {
      "period": "2026-05-09T08:00:00Z",
      "tickets_served": 12,
      "avg_wait_seconds": 210.5,
      "avg_service_seconds": 165.0,
      "min_wait_seconds": 30.0,
      "max_wait_seconds": 840.0
    },
    {
      "period": "2026-05-09T09:00:00Z",
      "tickets_served": 18,
      "avg_wait_seconds": 480.0,
      "avg_service_seconds": 195.0,
      "min_wait_seconds": 60.0,
      "max_wait_seconds": 1200.0
    },
    {
      "period": "2026-05-09T10:00:00Z",
      "tickets_served": 31,
      "avg_wait_seconds": 1380.0,
      "avg_service_seconds": 240.0,
      "min_wait_seconds": 120.0,
      "max_wait_seconds": 3240.0
    }
  ]
}
```

#### Notes

- `period` is the bucket start in UTC. All times are derived from `queue_ticket_stages.finished_at`.
- Only periods with at least one `FINISHED` stage are returned. Gaps (no customers served in that hour) are not included.
- All wait/service values are computed from `queue_ticket_stages` where `status = 'FINISHED'`.
- `avg_wait_seconds` / `avg_service_seconds` / `min_wait_seconds` / `max_wait_seconds` are `null` if no finished stages exist for that period (rare edge case with partial data).
- Items are ordered by `period ASC`.

---

### 6.3 `GET /waiting/analytics/by-service-point`

**Full path:** `GET /api/v1/waiting/analytics/by-service-point`

Aggregated queue statistics per service point, ordered worst-to-best by average wait time. Use to identify which service points are creating the longest waits.

#### Query parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `org_id` | UUID | **Yes** | — | Organisation to query |
| `date_from` | string | No | 7 days ago | `YYYY-MM-DD` |
| `date_to` | string | No | now | `YYYY-MM-DD` |

#### Request

```http
GET /api/v1/waiting/analytics/by-service-point
    ?org_id=3fa85f64-5717-4562-b3fc-2c963f66afa6
    &date_from=2026-05-01
    &date_to=2026-05-09
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "date_from": "2026-05-01",
  "date_to": "2026-05-09",
  "items": [
    {
      "service_point_id": "sp-uuid-0003",
      "service_point_name": "Payments Counter",
      "point_type": "PAYMENT",
      "tickets_served": 312,
      "avg_wait_seconds": 1542.0,
      "avg_service_seconds": 380.0,
      "max_wait_seconds": 5400.0,
      "min_wait_seconds": 45.0
    },
    {
      "service_point_id": "sp-uuid-0001",
      "service_point_name": "Customer Care Counter A",
      "point_type": "SERVICE",
      "tickets_served": 487,
      "avg_wait_seconds": 312.0,
      "avg_service_seconds": 192.0,
      "max_wait_seconds": 1840.0,
      "min_wait_seconds": 18.0
    },
    {
      "service_point_id": "sp-uuid-0002",
      "service_point_name": "Information Desk",
      "point_type": "INFORMATION",
      "tickets_served": 98,
      "avg_wait_seconds": 85.0,
      "avg_service_seconds": 60.0,
      "max_wait_seconds": 420.0,
      "min_wait_seconds": 10.0
    }
  ]
}
```

#### Notes

- Items are ordered by `avg_wait_seconds DESC NULLS LAST` — worst (longest) wait first.
- Service points with no `FINISHED` ticket stages in the period are not returned.
- `point_type` values are defined in the `waiting_service` `ServicePoint` model. Common values: `SERVICE`, `PAYMENT`, `INFORMATION`, `REGISTRATION`.

---

## 7. Response Schemas

### `StaffPerformanceResponse` (analytics_service)

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation queried |
| `date_from` | string | Effective window start (`YYYY-MM-DD`) |
| `date_to` | string | Effective window end (`YYYY-MM-DD`) |
| `total_staff` | integer | Number of items returned |
| `items` | `StaffPerformanceItem[]` | One item per `(staff_user_id, service_point_id)` pair |

### `StaffPerformanceItem`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `staff_user_id` | UUID | No | Auth-service user ID |
| `service_point_id` | UUID | Yes | Service point where the staff served |
| `service_point_name` | string | Yes | Human-readable name of the service point |
| `point_type` | string | Yes | Type label from the service point record |
| `tickets_served` | integer | No | Count of `FINISHED` stages assigned to this staff member |
| `avg_wait_seconds` | float | Yes | Mean customer wait time created by this staff member |
| `avg_service_seconds` | float | Yes | Mean time this staff member spent on each customer |
| `min_wait_seconds` | float | Yes | Shortest wait any customer had for this staff member |
| `max_wait_seconds` | float | Yes | Longest wait any customer had for this staff member |
| `first_attended_at` | datetime | Yes | Earliest `attending_started_at` for this staff member in the period |
| `last_finished_at` | datetime | Yes | Latest `finished_at` for this staff member in the period |
| `feedback_total` | integer | No | All feedback submitted to the org during `first_attended_at`→`last_finished_at` |
| `feedback_grievances` | integer | No | Grievance count in the same window |
| `feedback_suggestions` | integer | No | Suggestion count |
| `feedback_applause` | integer | No | Applause count |
| `feedback_inquiries` | integer | No | Inquiry count |

---

### `StaffDutyResponse` (analytics_service) / `StaffDutyOut` (waiting_service)

Both services return the same field set under different class names.

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation queried |
| `date_from` | string | Effective window start |
| `date_to` | string | Effective window end |
| `total_sessions` | integer | Total sessions in response |
| `active_sessions` | integer | Count where `is_active = true` |
| `items` | `StaffDutySessionItem[]` / `StaffDutyItem[]` | Sessions ordered by `opened_at DESC` |

### `StaffDutySessionItem` / `StaffDutyItem` (identical fields)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `session_id` | UUID | No | `StaffSession.id` from waiting_db |
| `staff_user_id` | UUID | Yes | Auth-service user ID of the staff member |
| `counter_name` | string | Yes | Name of the counter (desk) |
| `counter_code` | string | Yes | Short code of the counter (e.g. `C1`) |
| `service_point_id` | UUID | Yes | Service point containing the counter |
| `service_point_name` | string | Yes | Human-readable service point name |
| `point_type` | string | Yes | Service point type label |
| `opened_at` | datetime | Yes | When the staff member opened this session |
| `closed_at` | datetime | Yes | When the session was closed; `null` if still active |
| `is_active` | boolean | No | Whether the session is currently open |
| `tickets_served` | integer | No | Running count of tickets completed in this session |
| `avg_service_seconds` | float | Yes | Running average service time for this session |

---

### `WaitingVsFeedbackResponse`

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation queried |
| `granularity` | string | Effective granularity: `hour`, `day`, or `week` |
| `date_from` | string | Effective window start |
| `date_to` | string | Effective window end |
| `items` | `WaitingFeedbackPeriodItem[]` | Ordered by `period ASC` |

### `WaitingFeedbackPeriodItem`

| Field | Type | Nullable | Source DB | Description |
|-------|------|----------|-----------|-------------|
| `period` | datetime | Yes | Either | Bucket start (UTC) |
| `tickets_served` | integer | No | waiting_db | Customers served in this period |
| `avg_wait_seconds` | float | Yes | waiting_db | Mean queue wait time |
| `avg_service_seconds` | float | Yes | waiting_db | Mean service time |
| `min_wait_seconds` | float | Yes | waiting_db | Shortest wait in period |
| `max_wait_seconds` | float | Yes | waiting_db | Longest wait in period |
| `feedback_total` | integer | No | feedback_db | Total feedback submitted |
| `feedback_grievances` | integer | No | feedback_db | Grievance count |
| `feedback_suggestions` | integer | No | feedback_db | Suggestion count |
| `feedback_applause` | integer | No | feedback_db | Applause count |
| `feedback_inquiries` | integer | No | feedback_db | Inquiry count |

---

### `FeedbackTimingResponse`

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation queried |
| `date_from` | string | Effective window start |
| `date_to` | string | Effective window end |
| `peak_hour` | integer \| null | Hour (0–23) with the highest total across all cells |
| `peak_day` | string \| null | Day name of the peak cell (e.g. `"Monday"`) |
| `cells` | `FeedbackTimingCell[]` | Non-empty cells only, ordered by `day_of_week ASC, hour_of_day ASC` |

### `FeedbackTimingCell`

| Field | Type | Description |
|-------|------|-------------|
| `hour_of_day` | integer | 0–23 (UTC) |
| `day_of_week` | integer | 0 (Sunday) – 6 (Saturday) |
| `day_name` | string | Full weekday name: `Sunday`, `Monday`, …, `Saturday` |
| `total` | integer | All feedback received in this cell |
| `grievances` | integer | Grievance count |
| `suggestions` | integer | Suggestion count |
| `applause` | integer | Applause count |
| `inquiries` | integer | Inquiry count |

---

### `WaitByPeriodOut` (waiting_service)

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation queried |
| `granularity` | string | Effective granularity |
| `date_from` | string | Effective window start |
| `date_to` | string | Effective window end |
| `items` | `WaitByPeriodItem[]` | Ordered by `period ASC` |

### `WaitByPeriodItem`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `period` | datetime | Yes | Bucket start (UTC) |
| `tickets_served` | integer | No | Customers served in the period |
| `avg_wait_seconds` | float | Yes | Mean queue wait |
| `avg_service_seconds` | float | Yes | Mean service time |
| `min_wait_seconds` | float | Yes | Shortest wait |
| `max_wait_seconds` | float | Yes | Longest wait |

---

### `ServicePointWaitOut` (waiting_service)

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation queried |
| `date_from` | string | Effective window start |
| `date_to` | string | Effective window end |
| `items` | `ServicePointWaitItem[]` | Ordered by `avg_wait_seconds DESC NULLS LAST` |

### `ServicePointWaitItem`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `service_point_id` | UUID | No | Service point identifier |
| `service_point_name` | string | No | Human-readable name |
| `point_type` | string | No | Type label |
| `tickets_served` | integer | No | Total finished stages at this point |
| `avg_wait_seconds` | float | Yes | Mean customer wait |
| `avg_service_seconds` | float | Yes | Mean service time |
| `max_wait_seconds` | float | Yes | Worst single wait |
| `min_wait_seconds` | float | Yes | Best single wait |

---

## 8. Field Definitions

### Wait / service time fields

All wait and service duration fields come from `queue_ticket_stages`:

| Column | Meaning |
|--------|---------|
| `wait_duration_seconds` | Time from `entered_queue_at` to `attending_started_at` — how long the customer waited |
| `service_duration_seconds` | Time from `attending_started_at` to `finished_at` — how long the staff member took |

Both columns are `Float` and can be `null` if the stage did not complete normally.

### `point_type` values

`point_type` is a free-text field on `ServicePoint` with no enforced enum in the database, but conventional values used by the platform are:

| Value | Meaning |
|-------|---------|
| `SERVICE` | General customer service desk |
| `PAYMENT` | Payment or cashier counter |
| `INFORMATION` | Information / enquiries desk |
| `REGISTRATION` | Registration or onboarding desk |

### Day-of-week encoding (`feedback-timing`)

PostgreSQL `EXTRACT(DOW ...)` returns:

| Integer | Day |
|---------|-----|
| 0 | Sunday |
| 1 | Monday |
| 2 | Tuesday |
| 3 | Wednesday |
| 4 | Thursday |
| 5 | Friday |
| 6 | Saturday |

`day_name` in the response is the string equivalent of `day_of_week`.

---

## 9. Error Responses

All errors follow the standard Riviwa error envelope:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description."
}
```

### analytics_service errors

| Status | Error code | Cause |
|--------|-----------|-------|
| 401 | `UNAUTHORISED` | Missing or malformed `Authorization` header |
| 401 | `TOKEN_EXPIRED` | JWT has expired |
| 403 | `FORBIDDEN` | Org role below `admin`, or token `org_id` ≠ path `org_id` |
| 422 | `VALIDATION_ERROR` | Invalid UUID in path, unrecognised `feedback_type` |
| 500 | `INTERNAL_ERROR` | Unhandled server error (includes `waiting_db` connection failures) |

### waiting_service errors

| Status | Error code | Cause |
|--------|-----------|-------|
| 401 | `UNAUTHORISED` | Missing or malformed `Authorization` header |
| 403 | `FORBIDDEN` | Org role below `manager`, or token `org_id` ≠ query `org_id` |
| 422 | `VALIDATION_ERROR` | `org_id` query param missing or not a valid UUID |
| 500 | `INTERNAL_ERROR` | Database error |

---

## 10. Usage Patterns

### Identify which staff cause the most customer complaints

```http
GET /analytics/org/{org_id}/staff-performance
    ?date_from=2026-05-01&date_to=2026-05-09
```

Sort the response items by `feedback_grievances / tickets_served` (complaint rate) client-side. Also compare `avg_wait_seconds` — staff with high wait times and high grievance counts are the primary operational concern.

---

### Live duty board — who is currently serving

```http
GET /analytics/org/{org_id}/staff-duty?is_active=true
```
or equivalently:
```http
GET /waiting/analytics/staff-duty?org_id={id}&is_active=true
```

Use `tickets_served` as a running throughput counter and `avg_service_seconds` to flag counters that are significantly slower than the org average.

---

### Prove the wait time → complaint correlation

```http
GET /analytics/org/{org_id}/waiting-vs-feedback
    ?granularity=hour&date_from=2026-05-05&date_to=2026-05-07
    &feedback_type=GRIEVANCE
```

Scan the response for periods where `avg_wait_seconds` is high AND `feedback_grievances` spikes. If the correlation holds, you can calculate a wait-time SLA threshold beyond which complaint volume increases.

---

### Optimise counter staffing hours

```http
GET /analytics/org/{org_id}/feedback-timing
    ?date_from=2026-04-01&date_to=2026-05-09
    &feedback_type=GRIEVANCE
```

`peak_day` and `peak_hour` give the single busiest slot instantly. Inspect `cells` to build a full 7×24 grid. Open extra counters 30 minutes before the peak hour on peak days.

---

### Find the most overloaded service point

```http
GET /waiting/analytics/by-service-point
    ?org_id={id}&date_from=2026-05-01&date_to=2026-05-09
```

`items[0]` (worst average wait) is the service point that needs the most urgent capacity increase. Compare `max_wait_seconds` across points to find outlier single-customer delays.

---

### Week-over-week queue trend

```http
GET /waiting/analytics/by-period
    ?org_id={id}&granularity=day&date_from=2026-04-01&date_to=2026-05-09
```

Group the daily `avg_wait_seconds` by ISO week client-side. Rising week-on-week trend indicates growing demand without proportional staffing increase.

---

*Staff Performance Analytics API — Riviwa v2.2.0 — analytics_service:8095 · waiting_service:8130*
