# Riviwa — New & Updated Endpoints Reference

**Last Updated:** 2026-04-22  
**Services updated:** `feedback_service` (8090) · `analytics_service` (8095) · `riviwa_auth_service` (8000)

---

## Table of Contents

1. [Feedback — Inquiry Type & New Fields](#1-feedback--inquiry-type--new-fields)
   - [Staff Submit Feedback](#post-apiv1feedback--staff)
   - [Consumer Submit Feedback](#post-apiv1myfeedback--consumer)
   - [Bulk Upload](#post-apiv1feedbackbulk-upload)
   - [List Feedback (Staff)](#get-apiv1feedback)
   - [List Feedback (Consumer)](#get-apiv1myfeedback)
2. [Analytics — Inquiry Analytics (Project-scoped)](#2-analytics--inquiry-analytics-project-scoped)
3. [Analytics — Organisation Analytics](#3-analytics--organisation-analytics)
4. [Analytics — Platform Analytics](#4-analytics--platform-analytics)
5. [Analytics — AI Insights (Expanded)](#5-analytics--ai-insights-expanded)
6. [Auth — Internal Org Context](#6-auth--internal-org-context)
7. [Auth — Addresses](#7-auth--addresses)
8. [Feedback — Categories](#8-feedback--categories)

---

## Auth Overview

| Auth Type | Header / Mechanism | Used By |
|-----------|-------------------|---------|
| Bearer JWT (staff) | `Authorization: Bearer <token>` | All analytics, feedback staff endpoints |
| Bearer JWT (consumer) | `Authorization: Bearer <token>` | `/api/v1/my/feedback` endpoints |
| Internal service key | `X-Service-Key: <INTERNAL_SERVICE_KEY>` | `/api/v1/internal/*` endpoints only |

> **Note:** Internal endpoints (`/internal/*`) are blocked by Nginx from external traffic — only accessible between containers.

---

## 1. Feedback — Inquiry Type & New Fields

`feedback_type: "inquiry"` is now a first-class type alongside `grievance`, `suggestion`, and `applause`.

### Unique Reference Prefixes

| Type | Prefix |
|------|--------|
| `grievance` | `GRM-YYYY-NNNN` |
| `suggestion` | `SGG-YYYY-NNNN` |
| `applause` | `APP-YYYY-NNNN` |
| **`inquiry`** | **`INQ-YYYY-NNNN`** |

### Inquiry-Specific Category Values

| Value | Use Case |
|-------|----------|
| `GENERAL_INQUIRY` | Open question about the project |
| `INFORMATION_REQUEST` | Request for documents or data |
| `PROCEDURE_INQUIRY` | Question about a process or step |
| `STATUS_UPDATE` | Asking for progress on an existing case |
| `DOCUMENT_REQUEST` | Requesting specific records |

### New Fields on Feedback (all types)

| Field | Type | Description |
|-------|------|-------------|
| `service_id` | `UUID \| null` | Soft link to an `OrgService` record where `service_type=SERVICE` |
| `product_id` | `UUID \| null` | Soft link to an `OrgService` record where `service_type=PRODUCT` |

---

### POST /api/v1/feedback — Staff

Submit a feedback record on behalf of a community member.

**Auth:** Bearer JWT (GRM Officer — manager / admin / owner / platform admin)

**Request Body**

```json
{
  "project_id": "uuid (required)",
  "feedback_type": "grievance | suggestion | applause | inquiry (required)",
  "category": "string — enum slug e.g. GENERAL_INQUIRY (required)",
  "channel": "WEB_PORTAL | SMS | PHONE | WALK_IN | EMAIL | COMMUNITY_MEETING | WHATSAPP | MOBILE_APP (required)",
  "subject": "string (required)",
  "description": "string (required)",

  "category_def_id": "uuid | null",
  "department_id": "uuid | null",
  "service_id": "uuid | null",
  "product_id": "uuid | null",
  "service_location_id": "uuid | null",

  "submitter_name": "string | null",
  "submitter_phone": "string | null",
  "submitter_email": "string | null",
  "submitter_type": "INDIVIDUAL | COMMUNITY_GROUP | BUSINESS | NGO | null",
  "is_anonymous": false,

  "priority": "LOW | MEDIUM | HIGH | CRITICAL | null",
  "date_of_incident": "YYYY-MM-DD | null",
  "target_resolution_date": "YYYY-MM-DD | null",
  "internal_notes": "string | null",

  "issue_lga": "string | null",
  "issue_ward": "string | null",
  "issue_location_description": "string | null",
  "issue_gps_lat": "float | null",
  "issue_gps_lng": "float | null",

  "media_urls": ["string"] 
}
```

**Response `201`**

```json
{
  "id": "uuid",
  "unique_ref": "INQ-2026-0001",
  "project_id": "uuid",
  "feedback_type": "inquiry",
  "status": "SUBMITTED",
  "category": "GENERAL_INQUIRY",
  "subject": "string",
  "description": "string",
  "channel": "WEB_PORTAL",
  "priority": "LOW",
  "service_id": "uuid | null",
  "product_id": "uuid | null",
  "department_id": "uuid | null",
  "is_anonymous": false,
  "submitted_at": "2026-04-21T10:00:00Z",
  "created_at": "2026-04-21T10:00:00Z"
}
```

---

### POST /api/v1/my/feedback — Consumer

Submit a feedback record as an authenticated community member.

**Auth:** Bearer JWT (consumer)

**Request Body**

```json
{
  "feedback_type": "grievance | suggestion | applause | inquiry (required)",
  "description": "string (required)",
  "issue_lga": "string (required)",

  "project_id": "uuid | null",
  "category": "string | null — auto-classified by AI if omitted",
  "category_def_id": "uuid | null",
  "subject": "string | null",
  "department_id": "uuid | null",
  "service_id": "uuid | null",
  "product_id": "uuid | null",
  "subproject_id": "uuid | null",

  "channel": "WEB_PORTAL | SMS | MOBILE_APP | null",
  "is_anonymous": false,
  "submitter_name": "string | null",
  "submitter_phone": "string | null",
  "submitter_type": "INDIVIDUAL | COMMUNITY_GROUP | BUSINESS | NGO | null",

  "issue_ward": "string | null",
  "issue_location_description": "string | null",
  "issue_gps_lat": "float | null",
  "issue_gps_lng": "float | null",
  "date_of_incident": "YYYY-MM-DD | null",
  "media_urls": ["string"]
}
```

**Response `201`**

```json
{
  "feedback_id": "uuid",
  "tracking_number": "INQ-2026-0001",
  "status": "SUBMITTED",
  "status_label": "Submitted",
  "feedback_type": "inquiry",
  "ai_classified": true,
  "message": "Your inquiry has been submitted successfully."
}
```

---

### POST /api/v1/feedback/bulk-upload

Import feedback records from a CSV file.

**Auth:** Bearer JWT (staff)  
**Content-Type:** `multipart/form-data`

**Form Field**

| Field | Type | Description |
|-------|------|-------------|
| `file` | CSV file | Max 1 000 rows |
| `project_id` | `UUID` | Target project for all rows |

**CSV Columns**

| Column | Required | Notes |
|--------|----------|-------|
| `feedback_type` | yes | `grievance \| suggestion \| applause \| inquiry` |
| `category` | yes | Category slug |
| `subject` | yes | |
| `description` | yes | |
| `channel` | yes | |
| `priority` | no | Defaults to `LOW` |
| `submitter_name` | no | |
| `submitter_phone` | no | |
| `is_anonymous` | no | `true \| false` |
| `issue_lga` | no | |
| `issue_ward` | no | |
| `issue_gps_lat` | no | |
| `issue_gps_lng` | no | |
| `date_of_incident` | no | `YYYY-MM-DD` |
| `submitted_at` | no | `ISO 8601` |
| **`service_id`** | no | **NEW** |
| **`product_id`** | no | **NEW** |

**Response `200`**

```json
{
  "total_rows": 50,
  "created": 48,
  "skipped": 1,
  "errors": [
    { "row": 12, "reason": "Invalid feedback_type: 'complaint'" }
  ]
}
```

---

### GET /api/v1/feedback

List feedback records (staff, org-scoped).

**Auth:** Bearer JWT (staff)

**Query Parameters**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `project_id` | UUID | no | |
| `feedback_type` | string | no | `grievance \| suggestion \| applause \| **inquiry**` |
| `status` | string | no | `SUBMITTED \| ACKNOWLEDGED \| IN_REVIEW \| RESOLVED \| CLOSED \| DISMISSED` |
| `priority` | string | no | `LOW \| MEDIUM \| HIGH \| CRITICAL` |
| `current_level` | string | no | GRM level |
| `category` | string | no | Category slug |
| `lga` | string | no | |
| `is_anonymous` | bool | no | |
| `channel` | string | no | |
| `department_id` | UUID | no | |
| **`service_id`** | UUID | no | **NEW** |
| **`product_id`** | UUID | no | **NEW** |
| `category_def_id` | UUID | no | |
| `assigned_committee_id` | UUID | no | |
| `submitted_by_stakeholder_id` | UUID | no | |
| `skip` | int | no | Default `0` |
| `limit` | int | no | Default `50`, max `200` |

**Response `200`**

```json
{
  "items": [ /* array of feedback objects */ ],
  "count": 48
}
```

---

### GET /api/v1/my/feedback

List consumer's own submissions.

**Auth:** Bearer JWT (consumer)

**Query Parameters**

| Parameter | Type | Required |
|-----------|------|----------|
| `feedback_type` | string | no — now accepts `inquiry` |
| `status` | string | no |
| `project_id` | UUID | no |
| `skip` | int | no |
| `limit` | int | no |

---

## 2. Analytics — Inquiry Analytics (Project-scoped)

**Service:** `analytics_service` · **Port:** 8095  
**Base path:** `/api/v1/analytics/inquiries`  
**Auth:** Bearer JWT (staff)

---

### GET /analytics/inquiries/summary

High-level inquiry counts for a project.

```
GET /api/v1/analytics/inquiries/summary
  ?project_id={uuid}          (required)
  [&date_from=YYYY-MM-DD]
  [&date_to=YYYY-MM-DD]
```

**Response `200`**

```json
{
  "total_inquiries": 12,
  "open_inquiries": 5,
  "resolved": 4,
  "closed": 1,
  "dismissed": 1,
  "avg_response_hours": 3.4,
  "avg_days_open": 1.2,
  "open_by_priority": {
    "CRITICAL": 0,
    "HIGH": 0,
    "MEDIUM": 2,
    "LOW": 3
  }
}
```

---

### GET /analytics/inquiries/unread

Inquiries in `SUBMITTED` status (not yet acknowledged).

```
GET /api/v1/analytics/inquiries/unread
  ?project_id={uuid}          (required)
  [&priority=LOW|MEDIUM|HIGH|CRITICAL]
  [&department_id={uuid}]
  [&service_id={uuid}]
  [&product_id={uuid}]
  [&category_def_id={uuid}]
```

**Response `200`**

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
GET /api/v1/analytics/inquiries/overdue
  ?project_id={uuid}          (required)
  [&department_id={uuid}]
  [&service_id={uuid}]
  [&product_id={uuid}]
  [&category_def_id={uuid}]
```

**Response `200`**

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

Inquiry volume grouped by submission channel.

```
GET /api/v1/analytics/inquiries/by-channel
  ?project_id={uuid}          (required)
  [&date_from=YYYY-MM-DD]
  [&date_to=YYYY-MM-DD]
```

**Response `200`**

```json
{
  "total_items": 2,
  "items": [
    { "channel": "WEB_PORTAL", "total": 7, "open_count": 3, "resolved": 4 },
    { "channel": "SMS",        "total": 3, "open_count": 2, "resolved": 1 }
  ]
}
```

---

### GET /analytics/inquiries/by-category

Inquiry volume grouped by dynamic category (`category_def_id`). Rows with no category are labelled `"uncategorised"`.

```
GET /api/v1/analytics/inquiries/by-category
  ?project_id={uuid}          (required)
  [&date_from=YYYY-MM-DD]
  [&date_to=YYYY-MM-DD]
```

**Response `200`**

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
**Base path:** `/api/v1/analytics/org/{org_id}`  
**Auth:** Bearer JWT (staff)

All endpoints accept optional `date_from` / `date_to` (`YYYY-MM-DD`) unless stated.

---

### GET /analytics/org/{org_id}/summary

High-level counts across all projects in the org.

```
GET /api/v1/analytics/org/{org_id}/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

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

### GET /analytics/org/{org_id}/by-project

Feedback counts per project within the org.

```
GET /api/v1/analytics/org/{org_id}/by-project
  [?feedback_type=grievance|suggestion|applause|inquiry]
  [&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

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

### GET /analytics/org/{org_id}/by-period

Submission volume over time.

```
GET /api/v1/analytics/org/{org_id}/by-period
  ?granularity=day|week|month   (required)
  [&feedback_type=grievance|suggestion|applause|inquiry]
  [&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

```json
{
  "granularity": "week",
  "total_items": 3,
  "items": [
    {
      "period": "2026-04-14",
      "total": 12,
      "grievances": 8,
      "suggestions": 3,
      "applause": 1,
      "inquiries": 0
    }
  ]
}
```

---

### GET /analytics/org/{org_id}/by-channel

```
GET /api/v1/analytics/org/{org_id}/by-channel
  [?feedback_type=...&date_from=...&date_to=...]
```

**Response `200`**

```json
{
  "total_items": 4,
  "items": [
    {
      "channel": "WEB_PORTAL",
      "total": 25,
      "grievances": 15,
      "suggestions": 8,
      "applause": 2,
      "inquiries": 0
    }
  ]
}
```

---

### GET /analytics/org/{org_id}/by-department

Feedback grouped by `department_id`.

```
GET /api/v1/analytics/org/{org_id}/by-department
  [?feedback_type=...&date_from=...&date_to=...]
```

**Response `200`**

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
      "inquiries": 0,
      "resolved": 6,
      "avg_resolution_hours": 52.0
    }
  ]
}
```

---

### GET /analytics/org/{org_id}/by-service

Same shape as `by-department` with `dimension: "service_id"`.

```
GET /api/v1/analytics/org/{org_id}/by-service
  [?feedback_type=...&date_from=...&date_to=...]
```

---

### GET /analytics/org/{org_id}/by-product

Same shape as `by-department` with `dimension: "product_id"`.

```
GET /api/v1/analytics/org/{org_id}/by-product
  [?feedback_type=...&date_from=...&date_to=...]
```

---

### GET /analytics/org/{org_id}/by-category

Feedback grouped by dynamic category (`category_def_id`). Includes name and slug from `feedback_category_defs`.

```
GET /api/v1/analytics/org/{org_id}/by-category
  [?feedback_type=...&date_from=...&date_to=...]
```

**Response `200`**

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
      "inquiries": 0,
      "resolved": 7,
      "avg_resolution_hours": 60.0
    }
  ]
}
```

---

### GET /analytics/org/{org_id}/grievances/summary

```
GET /api/v1/analytics/org/{org_id}/grievances/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

```json
{
  "total_grievances": 30,
  "unresolved": 18,
  "escalated": 3,
  "dismissed": 2,
  "resolved": 8,
  "closed": 2,
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

### GET /analytics/org/{org_id}/grievances/by-level

Grievance counts by current GRM escalation level.

```
GET /api/v1/analytics/org/{org_id}/grievances/by-level
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

```json
{
  "total_items": 3,
  "items": [
    { "level": "WARD",             "total": 22, "unresolved": 15, "resolved": 7 },
    { "level": "LGA_GRM_UNIT",     "total": 6,  "unresolved": 3,  "resolved": 3 },
    { "level": "COORDINATING_UNIT","total": 2,  "unresolved": 0,  "resolved": 2 }
  ]
}
```

---

### GET /analytics/org/{org_id}/grievances/by-location

Grievance counts grouped by LGA and ward.

```
GET /api/v1/analytics/org/{org_id}/grievances/by-location
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

```json
{
  "total_items": 7,
  "items": [
    { "issue_lga": "Ilala",    "issue_ward": "Kariakoo", "total": 5, "unresolved": 3, "resolved": 2 },
    { "issue_lga": "Kinondoni","issue_ward": null,        "total": 3, "unresolved": 2, "resolved": 1 }
  ]
}
```

---

### GET /analytics/org/{org_id}/grievances/sla

SLA compliance for grievances across the org.

**SLA targets:** `CRITICAL` 4 h ack / 72 h resolve · `HIGH` 8 h / 168 h · `MEDIUM` 24 h / 336 h · `LOW` 48 h / 720 h

```
GET /api/v1/analytics/org/{org_id}/grievances/sla
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

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

### GET /analytics/org/{org_id}/suggestions/summary

```
GET /api/v1/analytics/org/{org_id}/suggestions/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

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

### GET /analytics/org/{org_id}/suggestions/by-project

Implementation rate per project.

```
GET /api/v1/analytics/org/{org_id}/suggestions/by-project
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

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
      "pending": 5,
      "dismissed": 0,
      "avg_hours_to_implement": 96.0
    }
  ]
}
```

---

### GET /analytics/org/{org_id}/applause/summary

```
GET /api/v1/analytics/org/{org_id}/applause/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

```json
{
  "total_applause": 10,
  "this_month": 4,
  "last_month": 3,
  "mom_change": 33.33,
  "top_categories": [
    { "category": "RESPONSIVENESS", "count": 4 },
    { "category": "QUALITY",        "count": 3 }
  ],
  "by_project": [
    { "project_id": "uuid", "project_name": "Msimbazi Road", "total": 6 }
  ]
}
```

---

### GET /analytics/org/{org_id}/inquiries/summary

Org-wide inquiry summary across all projects. Same response shape as project-scoped inquiry summary.

```
GET /api/v1/analytics/org/{org_id}/inquiries/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

---

## 4. Analytics — Platform Analytics

**Service:** `analytics_service` · **Port:** 8095  
**Base path:** `/api/v1/analytics/platform`  
**Auth:** Bearer JWT (staff — platform admin)

Aggregates across **all** organisations and projects on the platform.

> `org_name` in all responses is populated from the `fb_projects.org_display_name` cache (synced via Kafka org events).

---

### GET /analytics/platform/summary

```
GET /api/v1/analytics/platform/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

```json
{
  "total_orgs": 5,
  "total_projects": 12,
  "total": 60,
  "grievances": 32,
  "suggestions": 16,
  "applause": 10,
  "inquiries": 2,
  "unresolved": 30,
  "resolved": 26,
  "dismissed": 4,
  "avg_resolution_hours": 5.6
}
```

---

### GET /analytics/platform/by-org

Feedback counts per organisation.

```
GET /api/v1/analytics/platform/by-org
  [?feedback_type=grievance|suggestion|applause|inquiry]
  [&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

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

---

### GET /analytics/platform/by-period

```
GET /api/v1/analytics/platform/by-period
  ?granularity=day|week|month   (required)
  [&feedback_type=...&date_from=...&date_to=...]
```

**Response `200`** — same shape as org `by-period`.

---

### GET /analytics/platform/by-channel

```
GET /api/v1/analytics/platform/by-channel
  [?feedback_type=...&date_from=...&date_to=...]
```

**Response `200`** — same shape as org `by-channel`.

---

### GET /analytics/platform/grievances/summary

```
GET /api/v1/analytics/platform/grievances/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`** — same shape as org `grievances/summary`.

---

### GET /analytics/platform/grievances/sla

```
GET /api/v1/analytics/platform/grievances/sla
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`** — same shape as org `grievances/sla`.

---

### GET /analytics/platform/suggestions/summary

```
GET /api/v1/analytics/platform/suggestions/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`** — same shape as org `suggestions/summary`.

---

### GET /analytics/platform/applause/summary

```
GET /api/v1/analytics/platform/applause/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`**

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
GET /api/v1/analytics/platform/inquiries/summary
  [?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD]
```

**Response `200`** — same shape as project-scoped `/analytics/inquiries/summary`.

---

## 5. Analytics — AI Insights (Expanded)

**Endpoint:** `POST /api/v1/analytics/ai/ask`  
**Auth:** Bearer JWT

Ask a natural language question about grievance/feedback data. The `scope` controls what data is fetched and enriched before sending to Groq `llama-3.3-70b-versatile`.

---

### POST /analytics/ai/ask

**Request Body**

```json
{
  "question": "string (5–1000 chars, required)",
  "scope":        "project | org | platform  (default: project)",
  "context_type": "see table below           (default: general)",
  "project_id":   "uuid — required when scope=project",
  "org_id":       "uuid — required when scope=org"
}
```

### context_type Values by Scope

| `scope` | `context_type` | Data fetched |
|---------|---------------|--------------|
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

### Context Enrichment (sent to AI)

| Scope | Extra fields added |
|-------|-------------------|
| `project` | `project_name`, `org_name`, `sector`, `category`, `region`, `primary_lga`, `country`, `project_status`, `project_description` |
| `org` | `org_name`, `org_type`, `description`, `country`, `verified`, `branches[]`, `faqs[]`, `departments[]`, `services[]` |
| `platform` | `top_orgs[]` each with `org_name` |

**Response `200`**

```json
{
  "answer": "Based on the data, your project has 3 overdue grievances...",
  "context_used": {
    "scope": "org",
    "org_id": "uuid",
    "org_name": "TARURA",
    "context_type": "org_grievances"
  },
  "model": "llama-3.3-70b-versatile"
}
```

**Errors**

| Status | Condition |
|--------|-----------|
| `422` | `scope=project` without `project_id` |
| `422` | `scope=org` without `org_id` |
| `400` | `question` < 5 chars or > 1000 chars |
| `400` | Invalid `context_type` for the given `scope` |

---

## 6. Auth — Internal Org Context

**Service:** `riviwa_auth_service` · **Port:** 8000  
**Auth:** `X-Service-Key: <INTERNAL_SERVICE_KEY>` header  
**Note:** This endpoint is blocked by Nginx from external traffic — service-to-service only.

---

### GET /internal/orgs/{org_id}/ai-context

Returns a compact org profile used by `analytics_service` to enrich AI insight context with human-readable names, branches, departments, and services.

```
GET /api/v1/internal/orgs/{org_id}/ai-context
X-Service-Key: <shared secret>
```

**Path Parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `org_id` | UUID | Organisation ID |

**Response `200`**

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
    {
      "question": "How do I report a road defect?",
      "answer": "Submit via the web portal or call our hotline."
    }
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
    {
      "id":   "uuid",
      "name": "Maintenance",
      "code": "MAINT"
    }
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

---

## Deployment Status

| Service | Container | Uptime | New Code Deployed |
|---------|-----------|--------|-------------------|
| `feedback_service` | ✅ Up | 35 h | ✅ Yes — inquiry type, service_id, product_id |
| `analytics_service` | ✅ Up | 35 h | ✅ Yes — all new analytics endpoints |
| `riviwa_auth_service` | ✅ Up | 35 h | ✅ Yes — internal org context endpoint |
| `ai_service` | ✅ Up | 9 d | — no changes |
| `stakeholder_service` | ✅ Up | 9 d | — no changes |
| `notification_service` | ✅ Up | 2 d | — no changes |
| `payment_service` | ✅ Up | 9 d | — no changes |

> Server: `77.237.241.13` · Verified `2026-04-22`

---

## 7. Auth — Addresses

**Service:** `riviwa_auth_service` · **Port:** 8000  
**Base path:** `/api/v1/addresses`

Geocoding via OpenStreetMap Nominatim. Two public lookup endpoints (no auth) plus full CRUD for saved addresses linked to users, org subprojects, or stakeholders.

---

### Address Response Schema (`AddressResponse`)

All write/read endpoints return this shape:

```json
{
  "id": "uuid",
  "entity_type": "user | org_subproject | stakeholder",
  "entity_id": "uuid",
  "address_type": "home | billing | shipping | site | office | depot | registered | operational | contact",
  "label": "string | null",
  "is_default": false,
  "source": "osm | gps | manual",
  "osm_id": 12345,
  "osm_type": "node | way | relation | null",
  "place_id": 98765,
  "display_name": "string | null",
  "place_rank": 30,
  "place_type": "string | null",
  "address_class": "string | null",
  "line1": "string | null",
  "line2": "string | null",
  "city": "string | null",
  "state": "string | null",
  "postal_code": "string | null",
  "country_code": "TZ",
  "region": "string | null",
  "district": "string | null",
  "lga": "string | null",
  "ward": "string | null",
  "mtaa": "string | null",
  "gps_latitude": null,
  "gps_longitude": null,
  "address_notes": "string | null",
  "display_lines": ["string"],
  "created_at": "2026-04-22T10:00:00Z",
  "updated_at": "2026-04-22T10:00:00Z"
}
```

---

### GET /addresses/search

Forward geocode — search for addresses by free text via Nominatim.

**Auth:** None (public)

```
GET /api/v1/addresses/search
  ?q={string}                   (required, min 2 chars)
  [&countrycodes=TZ]            (default: TZ — comma-separated ISO 3166-1 alpha-2)
  [&limit=8]                    (default: 8, min 1, max 20)
```

**Response `200`** — `List[NominatimResult]`

```json
[
  {
    "place_id": 98765,
    "osm_id": 12345,
    "osm_type": "node",
    "display_name": "Kariakoo, Ilala, Dar es Salaam, Tanzania",
    "place_rank": 25,
    "place_type": "suburb",
    "address_class": "place",
    "line1": null,
    "city": "Dar es Salaam",
    "postal_code": null,
    "country_code": "TZ",
    "region": "Dar es Salaam Region",
    "district": null,
    "lga": "Ilala",
    "ward": "Kariakoo",
    "mtaa": null,
    "gps_latitude": -6.8161,
    "gps_longitude": 39.2694
  }
]
```

---

### GET /addresses/reverse

Reverse geocode — look up address from GPS coordinates.

**Auth:** None (public)

```
GET /api/v1/addresses/reverse
  ?lat={float}                  (required, -90 to 90)
  &lon={float}                  (required, -180 to 180)
```

**Response `200`** — Single `NominatimResult` or `null` if not found. Same schema as search results above.

---

### POST /addresses

Save an address linked to an entity.

**Auth:** Bearer JWT (active user)

**Request Body**

```json
{
  "entity_type": "user | org_subproject | stakeholder  (required)",
  "entity_id":   "uuid (required)",
  "address_type": "home | billing | shipping | site | office | depot | registered | operational | contact  (required)",
  "label": "string | null  — human-readable label e.g. 'Home'",
  "is_default": false,

  "osm_place_id": 98765,
  "display_name": "string | null",
  "osm_id": 12345,
  "osm_type": "node | way | relation | null",

  "gps_latitude": null,
  "gps_longitude": null,

  "line1": "string | null",
  "line2": "string | null",
  "city": "string | null",
  "state": "string | null",
  "postal_code": "string | null",
  "country_code": "TZ",
  "region": "string | null",
  "district": "string | null",
  "lga": "string | null",
  "ward": "string | null",
  "mtaa": "string | null",
  "address_notes": "string | null"
}
```

> **Three modes:**
> - **OSM mode** — provide `osm_place_id` (from `/addresses/search`); lat/lng are derived automatically
> - **GPS mode** — provide `gps_latitude` + `gps_longitude` (both required together)
> - **Manual mode** — provide any combination of `line1`, `city`, `lga`, etc.

**Response `201`** — `AddressResponse` (see schema above)

---

### GET /addresses/{entity_type}/{entity_id}

List all saved addresses for an entity.

**Auth:** Bearer JWT (active user)

**Path Parameters**

| Parameter | Values |
|-----------|--------|
| `entity_type` | `user \| org_subproject \| stakeholder` |
| `entity_id` | UUID |

**Response `200`**

```json
{
  "total": 2,
  "addresses": [ /* array of AddressResponse */ ]
}
```

---

### GET /addresses/{address_id}

Get a single saved address.

**Auth:** Bearer JWT (active user)

**Response `200`** — `AddressResponse`

---

### PATCH /addresses/{address_id}

Update a saved address (partial update — all fields optional).

**Auth:** Bearer JWT (active user)

**Request Body**

```json
{
  "address_type": "string | null",
  "label": "string | null",
  "is_default": null,
  "line1": "string | null",
  "line2": "string | null",
  "city": "string | null",
  "state": "string | null",
  "postal_code": "string | null",
  "country_code": "string | null",
  "region": "string | null",
  "district": "string | null",
  "lga": "string | null",
  "ward": "string | null",
  "mtaa": "string | null",
  "gps_latitude": null,
  "gps_longitude": null,
  "address_notes": "string | null"
}
```

**Response `200`** — `AddressResponse`

---

### POST /addresses/{address_id}/set-default

Mark an address as the default for its entity + address_type combination.

**Auth:** Bearer JWT (active user)

**Body:** None

**Response `200`** — `AddressResponse`

---

### DELETE /addresses/{address_id}

Delete a saved address.

**Auth:** Bearer JWT (active user)

**Response `204`** — No content

---

## 8. Feedback — Categories

**Service:** `feedback_service` · **Port:** 8090  
**Base path:** `/api/v1/categories`  
**Auth:** Bearer JWT (staff) — all endpoints

Dynamic, project-scoped feedback categories (`FeedbackCategoryDef`). Categories can be created manually by staff or suggested by the AI classification pipeline and then approved/rejected.

---

### Category Response Schema

All endpoints return categories serialised via `category_out()`:

```json
{
  "id": "uuid",
  "name": "Water Supply",
  "slug": "water-supply",
  "description": "Issues related to water supply",
  "project_id": "uuid | null",
  "applicable_types": ["grievance", "suggestion"],
  "source": "manual | ml_suggested",
  "status": "active | pending | rejected | deactivated | merged",
  "color_hex": "#E24B4A",
  "icon": "water-drop",
  "display_order": 0,
  "ml_confidence": null,
  "ml_rationale": null,
  "merged_into_id": null,
  "created_by_user_id": "uuid",
  "reviewed_by_user_id": null,
  "reviewed_at": null,
  "review_notes": null,
  "created_at": "2026-04-22T10:00:00Z"
}
```

---

### POST /api/v1/categories

Create a new feedback category.

**Auth:** Bearer JWT (staff)

**Request Body**

```json
{
  "name": "string (required, 2–120 chars)",
  "slug": "string | null — auto-generated from name if omitted (max 80 chars)",
  "description": "string | null",
  "project_id": "uuid | null — scope to project; omit for platform-wide",
  "applicable_types": ["grievance", "suggestion", "applause", "inquiry"],
  "color_hex": "#E24B4A",
  "icon": "water-drop",
  "display_order": 0
}
```

**Response `201`** — Category object (see schema above)

---

### GET /api/v1/categories

List categories.

**Auth:** Bearer JWT (staff)

**Query Parameters**

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `project_id` | UUID | no | — | Filter by project |
| `feedback_type` | string | no | — | `grievance \| suggestion \| applause \| inquiry` |
| `source` | string | no | — | `manual \| ml_suggested` |
| `status` | string | no | — | `active \| pending \| rejected \| deactivated \| merged` |
| `include_global` | bool | no | `true` | Include platform-wide categories |
| `skip` | int | no | `0` | |
| `limit` | int | no | `100` | Max `500` |

**Response `200`**

```json
{
  "items": [ /* array of category objects */ ],
  "count": 12
}
```

---

### GET /api/v1/categories/summary

All category counts for a project — used for dashboard overview.

**Auth:** Bearer JWT (staff)

**Query Parameters**

| Parameter | Type | Required |
|-----------|------|----------|
| `project_id` | UUID | **yes** |
| `feedback_type` | string | no |
| `from_date` | string (`YYYY-MM-DD`) | no |
| `to_date` | string (`YYYY-MM-DD`) | no |

**Response `200`**

```json
{
  "categories": [
    {
      "id": "uuid",
      "name": "Water Supply",
      "slug": "water-supply",
      "total": 12,
      "open": 5,
      "resolved": 7
    }
  ]
}
```

---

### GET /api/v1/categories/{category_id}

Category detail.

**Auth:** Bearer JWT (staff)

**Response `200`** — Category object

---

### PATCH /api/v1/categories/{category_id}

Update a category (partial update — all fields optional).

**Auth:** Bearer JWT (staff)

**Request Body**

```json
{
  "name": "string | null  (2–120 chars)",
  "description": "string | null",
  "applicable_types": ["grievance", "suggestion"],
  "color_hex": "#E24B4A",
  "icon": "water-drop",
  "display_order": 1
}
```

**Response `200`** — Updated category object

---

### GET /api/v1/categories/{category_id}/rate

Feedback rate and volume for a category — supports real-time and period-based filtering.

**Auth:** Bearer JWT (staff)

**Query Parameters**

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `project_id` | UUID | — | |
| `stage_id` | UUID | — | |
| `period` | string | `week` | `day \| week \| month` |
| `from_date` | string | — | `YYYY-MM-DD` |
| `to_date` | string | — | `YYYY-MM-DD` |
| `feedback_type` | string | — | |
| `status` | string | — | |
| `open_only` | bool | `false` | |
| `priority` | string | — | |
| `current_level` | string | — | GRM escalation level |
| `lga` | string | — | |
| `ward` | string | — | |
| `is_anonymous` | bool | — | |
| `submitted_by_stakeholder_id` | UUID | — | |
| `assigned_committee_id` | UUID | — | |
| `assigned_to_user_id` | UUID | — | |

**Response `200`**

```json
{
  "category": { /* category object */ },
  "total": 12,
  "by_period": [
    { "period": "2026-04-14", "count": 4 },
    { "period": "2026-04-21", "count": 8 }
  ]
}
```

---

### POST /api/v1/categories/{category_id}/approve

Approve an ML-suggested category (changes `status` from `pending` → `active`).

**Auth:** Bearer JWT (staff)

**Request Body**

```json
{
  "notes": "string | null",
  "name": "string | null — override name before approving",
  "slug": "string | null — override slug before approving"
}
```

**Response `200`** — Updated category object

---

### POST /api/v1/categories/{category_id}/reject

Reject an ML-suggested category.

**Auth:** Bearer JWT (staff)

**Request Body**

```json
{
  "notes": "string | null — reason for rejection"
}
```

**Response `200`** — Updated category object (`status: "rejected"`)

---

### POST /api/v1/categories/{category_id}/deactivate

Deactivate an active category (soft-disable — existing feedback keeps the category).

**Auth:** Bearer JWT (staff)

**Request Body**

```json
{
  "notes": "string | null — reason for deactivation"
}
```

**Response `200`** — Updated category object (`status: "deactivated"`)

---

### POST /api/v1/categories/{category_id}/merge

Merge this category into another (redirects all feedback and sets `status: "merged"`).

**Auth:** Bearer JWT (staff)

**Request Body**

```json
{
  "merge_into_id": "uuid (required) — target category to merge into",
  "notes": "string | null — reason for merge"
}
```

**Response `200`** — Updated source category object (`status: "merged"`, `merged_into_id` set)

---

### POST /api/v1/feedback/{feedback_id}/classify

Run ML classification to assign or suggest a category for a feedback record.

**Auth:** Bearer JWT (staff)

**Request Body**

```json
{
  "force": false
}
```

> Set `force: true` to re-run classification even if a category is already assigned.

**Response `200`**

```json
{
  "category": { /* category object */ },
  "assigned": true,
  "confidence": 0.91,
  "rationale": "The feedback describes a water pipe burst near Kariakoo market."
}
```

---

### PATCH /api/v1/feedback/{feedback_id}/recategorise

Manually reassign a feedback record to a different category.

**Auth:** Bearer JWT (staff)

**Request Body**

```json
{
  "category_def_id": "uuid (required) — target FeedbackCategoryDef"
}
```

**Response `200`**

```json
{
  "category": { /* updated category object */ },
  "previous_category_def_id": "uuid | null",
  "updated_at": "2026-04-22T10:00:00Z"
}
```
