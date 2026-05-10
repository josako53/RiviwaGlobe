# Riviwa — Branch Analytics API Reference

> **Service:** `analytics_service` (port 8095)  
> **Base URL:** `https://api.riviwa.com/api/v1/analytics/org/{org_id}/branches`  
> **Version:** 2.3.0 · **Added:** 2026-05-09  
> **Source:** `analytics_service/api/v1/branch_analytics.py`  
> **Schemas:** `analytics_service/schemas/branch_analytics.py`

---

## Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [How Branch Data Works](#3-how-branch-data-works)
4. [Common Parameters](#4-common-parameters)
5. [Endpoints](#5-endpoints)
   - 5.1 [GET /branches/summary](#51-get-branchessummary)
   - 5.2 [GET /branches/performance](#52-get-branchesperformance)
   - 5.3 [GET /branches/trend](#53-get-branchestrend)
   - 5.4 [GET /branches/{branch_id}/detail](#54-get-branchesbranch_iddetail)
6. [Response Schemas](#6-response-schemas)
7. [Field Definitions](#7-field-definitions)
8. [Error Responses](#8-error-responses)
9. [Usage Patterns](#9-usage-patterns)

---

## 1. Overview

Four endpoints expose comprehensive feedback analytics broken down by **organisation branch**. Together they cover:

| Need | Endpoint |
|------|----------|
| See all branches at once with KPIs | `GET /branches/summary` |
| Rank branches best-to-worst on performance | `GET /branches/performance` |
| Plot multi-branch trends over time | `GET /branches/trend` |
| Deep-dive into one branch | `GET /branches/{branch_id}/detail` |

All four query `feedback_db` directly. No cross-service calls are made at request time.

---

## 2. Authentication

All endpoints require a **Bearer JWT** in the `Authorization` header.

```
Authorization: Bearer <access_token>
```

**Required role:** org `admin` or `owner` **or** platform `admin`/`super_admin`.  
Members with `member` or `manager` roles receive **403 Forbidden**.

**Getting a token:**

```http
POST /api/v1/auth/login
{ "identifier": "user@example.com", "password": "..." }
→ { "login_token": "..." }

POST /api/v1/auth/login/verify-otp
{ "login_token": "...", "otp_code": "123456" }
→ { "access_token": "..." }
```

Switch to an org context to embed `org_id` in the token (recommended):

```http
POST /api/v1/orgs/{org_id}/switch
→ { "tokens": { "access_token": "..." } }
```

Platform admins can query any org's data without switching.

---

## 3. How Branch Data Works

`branch_id` on a `Feedback` record is **denormalised at submission time** from `OrgDepartment.branch_id` (stored in `auth_service`). When a user submits feedback and provides a `department_id`, the feedback service resolves that department's branch and writes `branch_id` onto the feedback row.

```
feedback.branch_id ← OrgDepartment.branch_id (auth_service)
                       copied at submission, no live join required
```

**Implications:**

- Feedback submitted **without** a `department_id` has `branch_id = NULL` and is **excluded** from all branch analytics.
- Branch UUIDs in responses are `auth_service` `OrgBranch.id` values. To resolve branch names, call `GET /api/v1/orgs/{org_id}/branches`.
- Changing a department's branch assignment after submission does **not** update historical feedback records.

---

## 4. Common Parameters

### Path parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `org_id` | UUID | Organisation to query. Token's org must match unless caller is a platform admin. |
| `branch_id` | UUID | (`/detail` only) The specific branch UUID from `auth_service`. |

### Query parameters (shared across all four endpoints)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date_from` | date | No | `YYYY-MM-DD`. Filters `submitted_at >= date_from 00:00:00 UTC`. |
| `date_to` | date | No | `YYYY-MM-DD`. Filters `submitted_at < date_to 23:59:59 UTC`. |
| `feedback_type` | string | No | Restrict to one type: `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY`. Case-insensitive. |

When neither `date_from` nor `date_to` is provided the query covers **all time**.  
`feedback_type` is **not** available on `/detail` (it returns a breakdown across all types).

---

## 5. Endpoints

---

### 5.1 `GET /branches/summary`

**Full path:** `GET /api/v1/analytics/org/{org_id}/branches/summary`

Returns one record per branch, ordered by `total` feedback count descending. Every metric is computed over all feedback where `branch_id IS NOT NULL` within the org, subject to the date and type filters.

#### Request

```
GET /api/v1/analytics/org/3fa85f64-5717-4562-b3fc-2c963f66afa6/branches/summary
    ?date_from=2026-04-01
    &date_to=2026-04-30
    &feedback_type=GRIEVANCE
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "date_from": "2026-04-01",
  "date_to": "2026-04-30",
  "feedback_type": "GRIEVANCE",
  "total_branches": 3,
  "items": [
    {
      "branch_id": "a1b2c3d4-0001-0000-0000-000000000000",
      "total": 89,
      "grievances": 89,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "resolved": 61,
      "open_count": 21,
      "escalated": 7,
      "dismissed": 4,
      "overdue": 3,
      "avg_resolution_hours": 18.45,
      "resolution_rate": 68.54,
      "escalation_rate": 7.87
    },
    {
      "branch_id": "a1b2c3d4-0002-0000-0000-000000000000",
      "total": 54,
      "grievances": 54,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "resolved": 48,
      "open_count": 6,
      "escalated": 1,
      "dismissed": 0,
      "overdue": 0,
      "avg_resolution_hours": 11.2,
      "resolution_rate": 88.89,
      "escalation_rate": 1.85
    }
  ]
}
```

#### Notes

- `total_branches` equals the number of distinct `branch_id` values that have at least one matching feedback record. Branches with zero feedback in the filtered period are **not** returned.
- When `feedback_type` is set, `grievances`/`suggestions`/`applause`/`inquiries` sub-counts still reflect actual type breakdowns within the filtered result set. If you filter to `GRIEVANCE`, `suggestions`, `applause`, and `inquiries` will always be `0`.
- `resolution_rate` = `resolved / total * 100`. `null` if `total = 0`.
- `escalation_rate` = `escalated / total * 100`. `null` if `total = 0`.
- `avg_resolution_hours` is `null` if no feedback in the set has been resolved.
- `overdue` counts feedback that is **not** `RESOLVED`/`CLOSED`/`DISMISSED` AND has a `target_resolution_date` in the past.

---

### 5.2 `GET /branches/performance`

**Full path:** `GET /api/v1/analytics/org/{org_id}/branches/performance`

Identical data to `/summary` but **sorted as a ranked league table**:

1. Highest `resolution_rate` first (best performer = rank 1)
2. Ties broken by lowest `overdue` count
3. Remaining ties broken by highest `total` (more volume = higher ranking)

Each item gains a `rank` integer field. Use this endpoint for management dashboards that need to surface underperforming branches.

#### Request

```
GET /api/v1/analytics/org/3fa85f64-5717-4562-b3fc-2c963f66afa6/branches/performance
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
  "total_branches": 6,
  "items": [
    {
      "rank": 1,
      "branch_id": "a1b2c3d4-0002-0000-0000-000000000000",
      "total": 54,
      "grievances": 41,
      "suggestions": 7,
      "applause": 5,
      "inquiries": 1,
      "resolved": 48,
      "open_count": 6,
      "escalated": 1,
      "overdue": 0,
      "avg_resolution_hours": 11.2,
      "resolution_rate": 88.89,
      "escalation_rate": 1.85
    },
    {
      "rank": 2,
      "branch_id": "a1b2c3d4-0003-0000-0000-000000000000",
      "total": 32,
      "grievances": 20,
      "suggestions": 8,
      "applause": 4,
      "inquiries": 0,
      "resolved": 25,
      "open_count": 7,
      "escalated": 2,
      "overdue": 1,
      "avg_resolution_hours": 22.7,
      "resolution_rate": 78.13,
      "escalation_rate": 6.25
    }
  ]
}
```

#### Notes

- The ranking is computed in Python after the database query, not in SQL. This is intentional — it allows consistent tie-breaking without database-specific window function syntax.
- `dismissed` is not included in `BranchPerformanceItem` (unlike `BranchSummaryItem`). If you need dismissed counts alongside ranks, call `/summary` and sort client-side.
- A branch with `resolution_rate = null` (zero feedback) sorts last.

---

### 5.3 `GET /branches/trend`

**Full path:** `GET /api/v1/analytics/org/{org_id}/branches/trend`

Returns a time series where **each row is one `(branch_id, period)` combination**. Rows are ordered by `branch_id ASC, period ASC`. This structure is designed for rendering multiple branch lines on a single chart — group by `branch_id` client-side.

#### Additional query parameters

| Parameter | Type | Default | Valid values |
|-----------|------|---------|--------------|
| `granularity` | string | `day` | `hour` \| `day` \| `week` \| `month` |

Invalid `granularity` values silently fall back to `day`.

#### Request

```
GET /api/v1/analytics/org/3fa85f64-5717-4562-b3fc-2c963f66afa6/branches/trend
    ?granularity=week
    &date_from=2026-04-01
    &date_to=2026-05-09
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "granularity": "week",
  "date_from": "2026-04-01",
  "date_to": "2026-05-09",
  "items": [
    {
      "branch_id": "a1b2c3d4-0001-0000-0000-000000000000",
      "period": "2026-03-30T00:00:00Z",
      "total": 18,
      "grievances": 12,
      "suggestions": 3,
      "applause": 2,
      "inquiries": 1,
      "resolved": 14
    },
    {
      "branch_id": "a1b2c3d4-0001-0000-0000-000000000000",
      "period": "2026-04-06T00:00:00Z",
      "total": 22,
      "grievances": 16,
      "suggestions": 4,
      "applause": 1,
      "inquiries": 1,
      "resolved": 19
    },
    {
      "branch_id": "a1b2c3d4-0002-0000-0000-000000000000",
      "period": "2026-03-30T00:00:00Z",
      "total": 11,
      "grievances": 8,
      "suggestions": 2,
      "applause": 1,
      "inquiries": 0,
      "resolved": 10
    }
  ]
}
```

#### Notes

- `period` is the **start of the bucket** in UTC (PostgreSQL `date_trunc` output). For `granularity=week`, Monday is the week start (ISO week).
- Periods with zero feedback for a branch are **not** returned — the series may have gaps. Fill these with zeros client-side using the `date_from`/`date_to` window and the `granularity`.
- For intra-day analysis use `granularity=hour` with a 1–3 day window. For strategic trends use `granularity=month` with a 6–12 month window.
- The response can be large if the org has many branches and a long date range at fine granularity. Use `granularity=week` or `month` for ranges beyond 90 days.

---

### 5.4 `GET /branches/{branch_id}/detail`

**Full path:** `GET /api/v1/analytics/org/{org_id}/branches/{branch_id}/detail`

A single-branch deep-dive that executes **five SQL queries** in sequence and returns all results in one response:

1. **Summary** — full KPI set for the branch
2. **By department** — per-department breakdown within the branch
3. **By category** — top 15 categories (by total) driving feedback at this branch
4. **By service** — top 10 services (by total) with most feedback at this branch
5. **Daily trend** — one row per day within the date window

This endpoint is designed for a branch detail page or a drill-down modal.

#### Request

```
GET /api/v1/analytics/org/3fa85f64-5717-4562-b3fc-2c963f66afa6/branches/a1b2c3d4-0001-0000-0000-000000000000/detail
    ?date_from=2026-04-01
    &date_to=2026-04-30
Authorization: Bearer <token>
```

#### Response — `200 OK`

```json
{
  "org_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "branch_id": "a1b2c3d4-0001-0000-0000-000000000000",
  "date_from": "2026-04-01",
  "date_to": "2026-04-30",

  "total": 142,
  "grievances": 89,
  "suggestions": 23,
  "applause": 18,
  "inquiries": 12,
  "resolved": 95,
  "open_count": 41,
  "escalated": 8,
  "dismissed": 3,
  "overdue": 5,
  "critical_open": 2,
  "high_open": 9,
  "avg_resolution_hours": 16.82,
  "resolution_rate": 66.9,
  "escalation_rate": 5.63,

  "by_department": [
    {
      "department_id": "dept-uuid-0001",
      "total": 58,
      "grievances": 39,
      "applause": 8,
      "resolved": 41,
      "avg_resolution_hours": 14.3
    },
    {
      "department_id": "dept-uuid-0002",
      "total": 34,
      "grievances": 22,
      "applause": 5,
      "resolved": 20,
      "avg_resolution_hours": 21.7
    }
  ],

  "by_category": [
    {
      "category_def_id": "cat-uuid-0001",
      "category": "NETWORK",
      "total": 38,
      "grievances": 35,
      "resolved": 22
    },
    {
      "category_def_id": "cat-uuid-0002",
      "category": "BILLING",
      "total": 29,
      "grievances": 24,
      "resolved": 18
    }
  ],

  "by_service": [
    {
      "service_id": "svc-uuid-0001",
      "total": 45,
      "grievances": 31,
      "resolved": 28
    },
    {
      "service_id": "svc-uuid-0002",
      "total": 27,
      "grievances": 19,
      "resolved": 15
    }
  ],

  "trend": [
    {
      "period": "2026-04-01T00:00:00Z",
      "total": 4,
      "grievances": 3,
      "suggestions": 1,
      "applause": 0,
      "inquiries": 0
    },
    {
      "period": "2026-04-02T00:00:00Z",
      "total": 6,
      "grievances": 4,
      "suggestions": 0,
      "applause": 2,
      "inquiries": 0
    }
  ]
}
```

#### Notes

- **`critical_open` / `high_open`:** Count of feedback with `priority = CRITICAL` or `HIGH` that is **not** `RESOLVED`, `CLOSED`, or `DISMISSED`. These are the most operationally urgent items.
- **`by_department`:** Only departments with at least one matching feedback record appear. `department_id` can be joined against `GET /api/v1/orgs/{org_id}/departments` from `auth_service` to resolve names.
- **`by_category`:** Capped at **top 15** by total count. `category_def_id` links to `feedback_service` category definitions. `category` is the raw enum value (legacy field; prefer `category_def_id` for structured lookups).
- **`by_service`:** Capped at **top 10**. `service_id` references `auth_service` `OrgService.id`.
- **`trend`:** Always `day` granularity regardless of date range. Days with zero feedback for this branch are **not** returned (fill with zeros client-side).
- If `branch_id` does not exist or has no feedback for the given org and date range, the response is still `200 OK` with all numeric fields set to `0` and all arrays empty.

---

## 6. Response Schemas

### `BranchSummaryResponse`

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation queried |
| `date_from` | string \| null | Applied `date_from` filter (`YYYY-MM-DD`) |
| `date_to` | string \| null | Applied `date_to` filter (`YYYY-MM-DD`) |
| `feedback_type` | string \| null | Applied type filter, or `null` |
| `total_branches` | integer | Number of branches returned |
| `items` | `BranchSummaryItem[]` | One item per branch, sorted by `total` DESC |

### `BranchSummaryItem`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `branch_id` | UUID | No | Auth-service `OrgBranch.id` |
| `total` | integer | No | All feedback matching the filters |
| `grievances` | integer | No | Count where `feedback_type = GRIEVANCE` |
| `suggestions` | integer | No | Count where `feedback_type = SUGGESTION` |
| `applause` | integer | No | Count where `feedback_type = APPLAUSE` |
| `inquiries` | integer | No | Count where `feedback_type = INQUIRY` |
| `resolved` | integer | No | Status is `RESOLVED` or `CLOSED` |
| `open_count` | integer | No | Not `RESOLVED`, `CLOSED`, or `DISMISSED` |
| `escalated` | integer | No | Status is `ESCALATED` |
| `dismissed` | integer | No | Status is `DISMISSED` |
| `overdue` | integer | No | Open + `target_resolution_date < now()` |
| `avg_resolution_hours` | float \| null | Yes | Mean hours from `submitted_at` to `resolved_at` across resolved items |
| `resolution_rate` | float \| null | Yes | `resolved / total × 100`, rounded to 2 dp |
| `escalation_rate` | float \| null | Yes | `escalated / total × 100`, rounded to 2 dp |

---

### `BranchPerformanceResponse`

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation queried |
| `date_from` | string \| null | Applied filter |
| `date_to` | string \| null | Applied filter |
| `total_branches` | integer | Number of branches returned |
| `items` | `BranchPerformanceItem[]` | Sorted best → worst by resolution rate |

### `BranchPerformanceItem`

All `BranchSummaryItem` fields except `dismissed`, plus:

| Field | Type | Description |
|-------|------|-------------|
| `rank` | integer | 1 = best performer |

---

### `BranchTrendResponse`

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation queried |
| `granularity` | string | Effective granularity (`hour`/`day`/`week`/`month`) |
| `date_from` | string \| null | Applied filter |
| `date_to` | string \| null | Applied filter |
| `items` | `BranchTrendItem[]` | Ordered by `branch_id ASC, period ASC` |

### `BranchTrendItem`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `branch_id` | UUID | No | Branch identifier |
| `period` | datetime \| null | Yes | Bucket start timestamp (UTC) |
| `total` | integer | No | Feedback count in this bucket |
| `grievances` | integer | No | Grievance count |
| `suggestions` | integer | No | Suggestion count |
| `applause` | integer | No | Applause count |
| `inquiries` | integer | No | Inquiry count |
| `resolved` | integer | No | Status `RESOLVED` or `CLOSED` in this bucket |

---

### `BranchDetailResponse`

All summary fields from `BranchSummaryItem` plus:

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `branch_id` | UUID | No | Branch queried |
| `critical_open` | integer | No | Open items with `priority = CRITICAL` |
| `high_open` | integer | No | Open items with `priority = HIGH` |
| `by_department` | `BranchDeptItem[]` | No | Per-department breakdown |
| `by_category` | `BranchCategoryItem[]` | No | Top 15 categories |
| `by_service` | `BranchServiceItem[]` | No | Top 10 services |
| `trend` | `BranchDayItem[]` | No | Daily time series |

### `BranchDeptItem`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `department_id` | UUID \| null | Yes | Auth-service `OrgDepartment.id` |
| `total` | integer | No | Total feedback from this department at this branch |
| `grievances` | integer | No | Grievance count |
| `applause` | integer | No | Applause count |
| `resolved` | integer | No | Resolved count |
| `avg_resolution_hours` | float \| null | Yes | Mean hours to resolution for this department |

### `BranchCategoryItem`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `category_def_id` | UUID \| null | Yes | `feedback_service` `CategoryDef.id` (structured) |
| `category` | string \| null | Yes | Legacy `feedback.category` enum value |
| `total` | integer | No | Total feedback in this category at the branch |
| `grievances` | integer | No | Grievance count |
| `resolved` | integer | No | Resolved count |

### `BranchServiceItem`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `service_id` | UUID \| null | Yes | Auth-service `OrgService.id` |
| `total` | integer | No | Total feedback tagged with this service at the branch |
| `grievances` | integer | No | Grievance count |
| `resolved` | integer | No | Resolved count |

### `BranchDayItem`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `period` | datetime \| null | Yes | Day start UTC (always midnight) |
| `total` | integer | No | Total feedback submitted on this day |
| `grievances` | integer | No | Grievance count |
| `suggestions` | integer | No | Suggestion count |
| `applause` | integer | No | Applause count |
| `inquiries` | integer | No | Inquiry count |

---

## 7. Field Definitions

### Status groupings used across all endpoints

| Term | Statuses included |
|------|------------------|
| `resolved` | `RESOLVED`, `CLOSED` |
| `open_count` | All except `RESOLVED`, `CLOSED`, `DISMISSED` |
| `escalated` | `ESCALATED` only (subset of open) |
| `dismissed` | `DISMISSED` only |
| `overdue` | Open AND `target_resolution_date IS NOT NULL` AND `target_resolution_date < NOW()` |

### Rate calculations

```
resolution_rate  = (resolved / total) × 100  — rounded to 2 decimal places
escalation_rate  = (escalated / total) × 100 — rounded to 2 decimal places
```

Both return `null` when `total = 0`. Both are computed by PostgreSQL using `ROUND(CAST(... AS NUMERIC), 2)`.

### `avg_resolution_hours`

Mean number of hours between `submitted_at` and `resolved_at`, computed only over feedback where `resolved_at IS NOT NULL`. Returns `null` if no feedback has been resolved in the result set.

```sql
AVG(EXTRACT(EPOCH FROM (resolved_at - submitted_at)) / 3600.0)
```

---

## 8. Error Responses

All errors follow the standard Riviwa error envelope:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description."
}
```

| Status | Error code | Cause |
|--------|-----------|-------|
| 401 | `UNAUTHORISED` | Missing or malformed `Authorization` header |
| 401 | `TOKEN_EXPIRED` | JWT has expired — re-authenticate |
| 403 | `FORBIDDEN` | Token is valid but the caller's org role is below `admin` |
| 403 | `FORBIDDEN` | Caller's token `org_id` does not match the `org_id` path param (non-platform-admin) |
| 422 | `VALIDATION_ERROR` | `date_from` / `date_to` not a valid date; `org_id` / `branch_id` not a valid UUID |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

**Note:** A `branch_id` that exists in `auth_service` but has no feedback in `feedback_db` returns **200 OK** with all counts set to `0` and arrays empty — not a 404.

---

## 9. Usage Patterns

### Branch health check (management summary)

```http
GET /api/v1/analytics/org/{org_id}/branches/summary
    ?date_from=2026-05-01&date_to=2026-05-09
```

Use `resolution_rate` and `overdue` to flag branches that need attention. Branch UUIDs can be resolved to names via:
```http
GET /api/v1/orgs/{org_id}/branches
```

---

### Identify the worst-performing branch this month

```http
GET /api/v1/analytics/org/{org_id}/branches/performance
    ?date_from=2026-05-01&date_to=2026-05-31
```

`items[last].branch_id` is the worst performer. Pair with `/detail` for the root-cause breakdown.

---

### Overlay two branches on a 90-day complaint chart

```http
GET /api/v1/analytics/org/{org_id}/branches/trend
    ?granularity=week&date_from=2026-02-01&date_to=2026-05-09&feedback_type=GRIEVANCE
```

Group the returned `items` by `branch_id` client-side, then plot each group as a separate line.

---

### Branch root-cause analysis

```http
GET /api/v1/analytics/org/{org_id}/branches/{branch_id}/detail
    ?date_from=2026-04-01&date_to=2026-04-30
```

Check in order:
1. `critical_open` > 0 → urgent escalation needed
2. `overdue` > `open_count * 0.1` → SLA breach risk
3. `by_department` — which department has the worst `avg_resolution_hours`
4. `by_category` — which issue category is driving the most `grievances`
5. `trend` — is volume rising or falling toward end of period

---

### Filter branch analytics to grievances only

All endpoints except `/detail` accept `?feedback_type=GRIEVANCE`. This restricts the `total` count and rates to grievances only:

```http
GET /api/v1/analytics/org/{org_id}/branches/summary?feedback_type=GRIEVANCE
GET /api/v1/analytics/org/{org_id}/branches/performance?feedback_type=GRIEVANCE
GET /api/v1/analytics/org/{org_id}/branches/trend?feedback_type=GRIEVANCE&granularity=day
```

---

*Branch Analytics API — Riviwa v2.3.0 — analytics_service:8095*
