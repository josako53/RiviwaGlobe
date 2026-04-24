# New Endpoints — 2026-04-21

Added in the session covering: inquiry feedback type, org/platform analytics, AI insights multi-scope, and internal org context enrichment.

---

## Table of Contents

1. [Feedback — Inquiry Type](#1-feedback--inquiry-type)
2. [Analytics — Inquiry Analytics (project-scoped)](#2-analytics--inquiry-analytics-project-scoped)
3. [Analytics — Organisation Analytics](#3-analytics--organisation-analytics)
4. [Analytics — Platform Analytics](#4-analytics--platform-analytics)
5. [Analytics — AI Insights (expanded scopes)](#5-analytics--ai-insights-expanded-scopes)
6. [Auth — Internal Org Context](#6-auth--internal-org-context)

---

## 1. Feedback — Inquiry Type

`feedback_type=inquiry` is now a first-class value alongside `grievance`, `suggestion`, and `applause`.

### Unique ref prefix

| Type | Prefix |
|------|--------|
| GRIEVANCE | `GRM-YYYY-NNNN` |
| SUGGESTION | `SGG-YYYY-NNNN` |
| APPLAUSE | `APP-YYYY-NNNN` |
| **INQUIRY** | **`INQ-YYYY-NNNN`** |

### Inquiry-specific categories

| Value | Use case |
|-------|----------|
| `GENERAL_INQUIRY` | Open question about the project |
| `INFORMATION_REQUEST` | Request for documents or data |
| `PROCEDURE_INQUIRY` | Question about a process or step |
| `STATUS_UPDATE` | Asking for progress on existing case |
| `DOCUMENT_REQUEST` | Requesting specific records |

### Affected existing endpoints

| Method | Path | Change |
|--------|------|--------|
| `POST` | `/api/v1/feedback` | `feedback_type: "inquiry"` now accepted |
| `POST` | `/api/v1/my/feedback` | `feedback_type: "inquiry"` now accepted |
| `GET` | `/api/v1/feedback` | `?feedback_type=inquiry` filter now works |
| `GET` | `/api/v1/my/feedback` | `?feedback_type=inquiry` filter now works |

### New fields on Feedback (all types)

| Field | Type | Description |
|-------|------|-------------|
| `service_id` | `UUID?` | Soft link to auth_service `OrgService.id` |
| `product_id` | `UUID?` | Soft link to a service where `service_type=PRODUCT` |

---

## 2. Analytics — Inquiry Analytics (project-scoped)

**Service:** `analytics_service` · **Port:** 8095  
**Auth:** Bearer JWT (staff)  
**Base path:** `/api/v1/analytics/inquiries`

---

### GET /analytics/inquiries/summary

```
GET /api/v1/analytics/inquiries/summary?project_id={uuid}[&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response**
```json
{
  "total_inquiries": 12,
  "open_inquiries": 5,
  "resolved": 6,
  "dismissed": 1,
  "avg_response_hours": 3.4,
  "avg_days_open": 1.2,
  "open_by_priority": {
    "LOW": 3,
    "MEDIUM": 2
  }
}
```

---

### GET /analytics/inquiries/unread

Inquiries in `SUBMITTED` status (not yet acknowledged).

```
GET /api/v1/analytics/inquiries/unread?project_id={uuid}
  [&priority=low|medium|high|critical]
  [&department_id={uuid}]
  [&service_id={uuid}]
  [&product_id={uuid}]
  [&category_def_id={uuid}]
```

**Response**
```json
{
  "total": 3,
  "items": [
    {
      "feedback_id": "uuid",
      "unique_ref": "INQ-2026-0001",
      "priority": "LOW",
      "submitted_at": "2026-04-21T10:00:00Z",
      "days_waiting": 0.25,
      "channel": "WEB_PORTAL",
      "issue_lga": "Ilala",
      "department_id": null,
      "service_id": null,
      "product_id": null,
      "category_def_id": null
    }
  ]
}
```

---

### GET /analytics/inquiries/overdue

Inquiries in `ACKNOWLEDGED` or `IN_REVIEW` status that have passed `target_resolution_date`.

```
GET /api/v1/analytics/inquiries/overdue?project_id={uuid}
  [&department_id={uuid}] [&service_id={uuid}]
  [&product_id={uuid}] [&category_def_id={uuid}]
```

**Response**
```json
{
  "total": 1,
  "items": [
    {
      "feedback_id": "uuid",
      "unique_ref": "INQ-2026-0002",
      "priority": "MEDIUM",
      "status": "ACKNOWLEDGED",
      "submitted_at": "2026-04-10T08:00:00Z",
      "target_resolution_date": "2026-04-17T08:00:00Z",
      "days_overdue": 4.2,
      "assigned_to_user_id": "uuid",
      "department_id": null,
      "service_id": null,
      "product_id": null,
      "category_def_id": null
    }
  ]
}
```

---

### GET /analytics/inquiries/by-channel

```
GET /api/v1/analytics/inquiries/by-channel?project_id={uuid}
  [&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response**
```json
{
  "total_items": 3,
  "items": [
    { "channel": "WEB_PORTAL", "total": 7, "open_count": 3, "resolved": 4 },
    { "channel": "SMS",        "total": 3, "open_count": 2, "resolved": 1 }
  ]
}
```

---

### GET /analytics/inquiries/by-category

Groups inquiries by dynamic category (`category_def_id`). Uncategorised rows are labelled `"uncategorised"`.

```
GET /api/v1/analytics/inquiries/by-category?project_id={uuid}
  [&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response**
```json
{
  "total_items": 2,
  "items": [
    {
      "category_def_id": "uuid",
      "category_name": "Road Status",
      "category_slug": "road-status",
      "total": 5,
      "open_count": 2,
      "resolved": 3,
      "avg_response_hours": 4.5
    },
    {
      "category_def_id": null,
      "category_name": "uncategorised",
      "category_slug": null,
      "total": 2,
      "open_count": 2,
      "resolved": 0,
      "avg_response_hours": null
    }
  ]
}
```

---

## 3. Analytics — Organisation Analytics

**Service:** `analytics_service` · **Port:** 8095  
**Auth:** Bearer JWT (staff)  
**Base path:** `/api/v1/analytics/org/{org_id}`

All endpoints accept optional `date_from` / `date_to` (ISO `YYYY-MM-DD`) query parameters unless stated otherwise.

---

### General

#### GET /analytics/org/{org_id}/summary

High-level counts across all projects in the org.

```
GET /api/v1/analytics/org/{org_id}/summary[?date_from=&date_to=]
```

**Response**
```json
{
  "total": 57,
  "grievances": 30,
  "suggestions": 15,
  "applause": 10,
  "inquiries": 2,
  "unresolved": 28,
  "resolved": 25,
  "dismissed": 4,
  "avg_resolution_hours": 48.2,
  "avg_days_unresolved": 5.1
}
```

---

#### GET /analytics/org/{org_id}/by-project

Feedback counts per project.

```
GET /api/v1/analytics/org/{org_id}/by-project
  [?feedback_type=grievance|suggestion|applause|inquiry&date_from=&date_to=]
```

**Response**
```json
{
  "total_items": 2,
  "items": [
    {
      "project_id": "uuid",
      "project_name": "Msimbazi Road Improvement",
      "total": 34,
      "grievances": 20,
      "suggestions": 8,
      "applause": 6,
      "inquiries": 0,
      "unresolved": 18,
      "resolved": 14,
      "avg_resolution_hours": 36.0
    }
  ]
}
```

---

#### GET /analytics/org/{org_id}/by-period

Submission volume over time.

```
GET /api/v1/analytics/org/{org_id}/by-period
  ?granularity=day|week|month
  [&feedback_type=...&date_from=&date_to=]
```

**Response**
```json
{
  "granularity": "week",
  "total_items": 3,
  "items": [
    { "period": "2026-04-14", "total": 12, "grievances": 8, "suggestions": 3, "applause": 1 }
  ]
}
```

---

#### GET /analytics/org/{org_id}/by-channel

```
GET /api/v1/analytics/org/{org_id}/by-channel
  [?feedback_type=...&date_from=&date_to=]
```

**Response**
```json
{
  "total_items": 4,
  "items": [
    { "channel": "WEB_PORTAL", "total": 25, "grievances": 15, "suggestions": 8, "applause": 2 }
  ]
}
```

---

#### GET /analytics/org/{org_id}/by-department

Feedback grouped by `department_id`.

```
GET /api/v1/analytics/org/{org_id}/by-department
  [?feedback_type=...&date_from=&date_to=]
```

**Response**
```json
{
  "dimension": "department_id",
  "total_items": 3,
  "items": [
    {
      "dimension_id": "uuid",
      "total": 14,
      "grievances": 9,
      "suggestions": 4,
      "applause": 1,
      "resolved": 6,
      "avg_resolution_hours": 52.0
    }
  ]
}
```

---

#### GET /analytics/org/{org_id}/by-service

Same response shape as `by-department` with `dimension: "service_id"`.

```
GET /api/v1/analytics/org/{org_id}/by-service[?feedback_type=...&date_from=&date_to=]
```

---

#### GET /analytics/org/{org_id}/by-product

Same response shape as `by-department` with `dimension: "product_id"`.

```
GET /api/v1/analytics/org/{org_id}/by-product[?feedback_type=...&date_from=&date_to=]
```

---

#### GET /analytics/org/{org_id}/by-category

Feedback grouped by dynamic category (`category_def_id`). Includes name/slug from `feedback_category_defs`.

```
GET /api/v1/analytics/org/{org_id}/by-category[?feedback_type=...&date_from=&date_to=]
```

**Response**
```json
{
  "total_items": 5,
  "items": [
    {
      "category_def_id": "uuid",
      "category_name": "Land Compensation",
      "category_slug": "land-compensation",
      "total": 12,
      "grievances": 10,
      "suggestions": 2,
      "applause": 0,
      "resolved": 7,
      "avg_resolution_hours": 60.0
    }
  ]
}
```

---

### Grievances

#### GET /analytics/org/{org_id}/grievances/summary

```
GET /api/v1/analytics/org/{org_id}/grievances/summary[?date_from=&date_to=]
```

**Response**
```json
{
  "total_grievances": 30,
  "unresolved": 18,
  "escalated": 3,
  "dismissed": 2,
  "avg_resolution_hours": 72.4,
  "avg_days_unresolved": 5.8,
  "unresolved_by_priority": {
    "CRITICAL": 1,
    "HIGH": 4,
    "MEDIUM": 10,
    "LOW": 3
  }
}
```

---

#### GET /analytics/org/{org_id}/grievances/by-level

Grievance counts by current GRM escalation level.

```
GET /api/v1/analytics/org/{org_id}/grievances/by-level[?date_from=&date_to=]
```

**Response**
```json
{
  "total_items": 3,
  "items": [
    { "level": "WARD", "total": 22, "unresolved": 15, "resolved": 7 },
    { "level": "LGA_GRM_UNIT", "total": 6, "unresolved": 3, "resolved": 3 },
    { "level": "COORDINATING_UNIT", "total": 2, "unresolved": 0, "resolved": 2 }
  ]
}
```

---

#### GET /analytics/org/{org_id}/grievances/by-location

Grievance counts grouped by LGA and ward.

```
GET /api/v1/analytics/org/{org_id}/grievances/by-location[?date_from=&date_to=]
```

**Response**
```json
{
  "total_items": 7,
  "items": [
    { "issue_lga": "Ilala", "issue_ward": "Kariakoo", "total": 5, "unresolved": 3, "resolved": 2 },
    { "issue_lga": "Kinondoni", "issue_ward": null, "total": 3, "unresolved": 2, "resolved": 1 }
  ]
}
```

---

#### GET /analytics/org/{org_id}/grievances/sla

SLA compliance for grievances across the org.

SLA targets: `CRITICAL` 4h ack / 72h resolve · `HIGH` 8h / 168h · `MEDIUM` 24h / 336h · `LOW` 48h / 720h

```
GET /api/v1/analytics/org/{org_id}/grievances/sla[?date_from=&date_to=]
```

**Response**
```json
{
  "by_priority": [
    {
      "priority": "MEDIUM",
      "total": 15,
      "ack_met": 12,
      "ack_breached": 3,
      "res_met": 10,
      "res_breached": 5,
      "compliance_rate": 66.67
    }
  ],
  "total_breached": 5,
  "overall_compliance_rate": 71.4
}
```

---

### Suggestions

#### GET /analytics/org/{org_id}/suggestions/summary

```
GET /api/v1/analytics/org/{org_id}/suggestions/summary[?date_from=&date_to=]
```

**Response**
```json
{
  "total_suggestions": 15,
  "actioned": 4,
  "noted": 3,
  "pending": 6,
  "dismissed": 2,
  "actioned_rate": 26.67,
  "avg_hours_to_implement": 168.0
}
```

---

#### GET /analytics/org/{org_id}/suggestions/by-project

Implementation rate per project.

```
GET /api/v1/analytics/org/{org_id}/suggestions/by-project[?date_from=&date_to=]
```

**Response**
```json
{
  "total_items": 2,
  "items": [
    {
      "project_id": "uuid",
      "project_name": "Msimbazi Road Improvement",
      "total": 8,
      "actioned": 2,
      "noted": 1,
      "dismissed": 0,
      "avg_hours_to_implement": 96.0
    }
  ]
}
```

---

### Applause

#### GET /analytics/org/{org_id}/applause/summary

```
GET /api/v1/analytics/org/{org_id}/applause/summary[?date_from=&date_to=]
```

**Response**
```json
{
  "total_applause": 10,
  "this_month": 4,
  "last_month": 3,
  "mom_change": 33.33,
  "top_categories": [
    { "category": "RESPONSIVENESS", "count": 4 },
    { "category": "QUALITY",        "count": 3 }
  ]
}
```

---

### Inquiries

#### GET /analytics/org/{org_id}/inquiries/summary

Org-wide inquiry summary across all projects.

```
GET /api/v1/analytics/org/{org_id}/inquiries/summary[?date_from=&date_to=]
```

**Response** — same shape as project-scoped `/analytics/inquiries/summary`.

---

## 4. Analytics — Platform Analytics

**Service:** `analytics_service` · **Port:** 8095  
**Auth:** Bearer JWT (staff — platform admin)  
**Base path:** `/api/v1/analytics/platform`

Aggregates across **all** organisations and projects on the platform.

---

### GET /analytics/platform/summary

```
GET /api/v1/analytics/platform/summary[?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response**
```json
{
  "total": 60,
  "grievances": 32,
  "suggestions": 16,
  "applause": 10,
  "inquiries": 2,
  "unresolved": 30,
  "resolved": 26,
  "avg_resolution_hours": 5.6
}
```

---

### GET /analytics/platform/by-org

Feedback counts per organisation.

```
GET /api/v1/analytics/platform/by-org
  [?feedback_type=grievance|suggestion|applause|inquiry&date_from=&date_to=]
```

**Response**
```json
{
  "total_items": 3,
  "items": [
    {
      "organisation_id": "uuid",
      "org_name": "Tanzania Roads Authority",
      "total_projects": 4,
      "total": 29,
      "grievances": 18,
      "suggestions": 7,
      "applause": 4,
      "inquiries": 0,
      "unresolved": 16,
      "resolved": 11,
      "avg_resolution_hours": 6.2
    }
  ]
}
```

> `org_name` is populated from the `fb_projects.org_display_name` cache (synced via Kafka org events).

---

### GET /analytics/platform/by-period

```
GET /api/v1/analytics/platform/by-period
  ?granularity=day|week|month
  [&feedback_type=...&date_from=&date_to=]
```

**Response** — same shape as org `by-period`.

---

### GET /analytics/platform/by-channel

```
GET /api/v1/analytics/platform/by-channel
  [?feedback_type=...&date_from=&date_to=]
```

**Response** — same shape as org `by-channel`.

---

### GET /analytics/platform/grievances/summary

```
GET /api/v1/analytics/platform/grievances/summary[?date_from=&date_to=]
```

**Response** — same shape as org `grievances/summary`.

---

### GET /analytics/platform/grievances/sla

```
GET /api/v1/analytics/platform/grievances/sla[?date_from=&date_to=]
```

**Response** — same shape as org `grievances/sla`.

---

### GET /analytics/platform/suggestions/summary

```
GET /api/v1/analytics/platform/suggestions/summary[?date_from=&date_to=]
```

**Response** — same shape as org `suggestions/summary`.

---

### GET /analytics/platform/applause/summary

```
GET /api/v1/analytics/platform/applause/summary[?date_from=&date_to=]
```

**Response**
```json
{
  "total_applause": 10,
  "this_month": 10,
  "last_month": 0,
  "mom_change": null,
  "top_categories": [
    { "category": "OTHER",          "count": 4 },
    { "category": "RESPONSIVENESS", "count": 3 }
  ],
  "by_org": [
    { "organisation_id": "uuid", "org_name": "TARURA", "total": 6 }
  ]
}
```

---

### GET /analytics/platform/inquiries/summary

```
GET /api/v1/analytics/platform/inquiries/summary[?date_from=&date_to=]
```

**Response** — same shape as project-scoped `/analytics/inquiries/summary`.

---

## 5. Analytics — AI Insights (expanded scopes)

**Endpoint:** `POST /api/v1/analytics/ai/ask`  
**Auth:** Bearer JWT

The `scope` field now selects which data is fetched. `project_id` and `org_id` are both optional at the schema level — which one is required depends on the scope.

### Request

```json
{
  "question": "string (5–1000 chars)",
  "scope":        "project | org | platform",
  "context_type": "see table below",
  "project_id":   "uuid (required when scope=project)",
  "org_id":       "uuid (required when scope=org)"
}
```

### context_type values by scope

| scope | context_type | Data fetched |
|-------|-------------|--------------|
| `project` | `general` | Full project overview — all metrics |
| `project` | `grievances` | Unresolved, overdue, SLA compliance |
| `project` | `suggestions` | Impl time, unread, actioned counts |
| `project` | `sla` | SLA records and compliance rate |
| `project` | `committees` | Committee performance ranking |
| `project` | `hotspots` | Active hotspot alerts |
| `project` | `staff` | Unread assignments, logins today |
| `project` | `unresolved` | Unresolved grievances with priority breakdown |
| `project` | `inquiries` | Inquiry summary + unread count |
| `org` | `org_general` | Full org overview including all sub-summaries |
| `org` | `org_grievances` | Grievance summary + SLA + by-level |
| `org` | `org_suggestions` | Suggestion summary |
| `org` | `org_applause` | Applause total and trend |
| `org` | `org_inquiries` | Inquiry summary |
| `platform` | `platform_general` | Full platform overview + top 5 orgs by volume |
| `platform` | `platform_grievances` | Platform grievance summary + SLA |
| `platform` | `platform_suggestions` | Platform suggestion summary |
| `platform` | `platform_applause` | Platform applause summary |
| `platform` | `platform_inquiries` | Platform inquiry summary |

### Context enrichment

The AI context is enriched with human-readable identifiers before being sent to Groq:

- **scope=project**: `project_name`, `org_name`, `sector`, `category`, `region`, `primary_lga`, `country`, `project_status`, `project_description` (from `fb_projects` cache)
- **scope=org**: `org_name`, `org_type`, `description`, `country`, `verified`, `branches[]`, `faqs[]`, `departments[]`, `services[]` (from auth_service internal endpoint + `fb_projects` cache)
- **scope=platform**: `top_orgs[]` with `org_name` field (from `fb_projects.org_display_name`)

### Response

```json
{
  "answer": "Based on the data...",
  "context_used": { "scope": "org", "org_id": "...", "org_name": "TARURA", ... },
  "model": "llama-3.3-70b-versatile"
}
```

### Errors

| Status | Condition |
|--------|-----------|
| `422` | `scope=project` without `project_id` |
| `422` | `scope=org` without `org_id` |
| `400` | `question` shorter than 5 chars or longer than 1000 |

---

## 6. Auth — Internal Org Context

**Service:** `riviwa_auth_service` · **Port:** 8000  
**Auth:** `X-Service-Key: <INTERNAL_SERVICE_KEY>` header  
**Note:** This endpoint is for service-to-service calls only. Nginx blocks it from external traffic.

---

### GET /internal/orgs/{org_id}/ai-context

Returns a compact org profile used by `analytics_service` to enrich AI insight context with human-readable names and structure.

```
GET /api/v1/internal/orgs/{org_id}/ai-context
X-Service-Key: <shared secret>
```

**Response**
```json
{
  "org_id":        "uuid",
  "legal_name":    "Tanzania Rural and Urban Roads Agency",
  "display_name":  "TARURA",
  "description":   "Roads authority for rural and urban roads",
  "org_type":      "GOVERNMENT",
  "status":        "active",
  "country_code":  "TZ",
  "website_url":   "https://tarura.go.tz",
  "support_email": "info@tarura.go.tz",
  "is_verified":   true,
  "faqs": [
    { "question": "How do I report a road defect?", "answer": "..." }
  ],
  "branches": [
    {
      "id":          "uuid",
      "name":        "Dar es Salaam Region",
      "code":        "DAR",
      "branch_type": "REGIONAL",
      "is_root":     false
    }
  ],
  "departments": [
    { "id": "uuid", "name": "Maintenance", "code": "MAINT" }
  ],
  "services": [
    {
      "id":           "uuid",
      "title":        "Road Pothole Reporting",
      "service_type": "SERVICE",
      "category":     "INFRASTRUCTURE",
      "summary":      "Report road potholes for repair"
    }
  ]
}
```

**Errors**

| Status | Condition |
|--------|-----------|
| `401` | Missing or invalid `X-Service-Key` |
| `404` | Organisation not found or soft-deleted |
