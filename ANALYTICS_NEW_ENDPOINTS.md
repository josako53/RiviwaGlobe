# Riviwa Analytics — New Endpoints Reference

> **Service:** `analytics_service` · Port `8095` · Nginx path `/api/v1/analytics/*`
> **Auth:** All endpoints require `Authorization: Bearer <JWT>` (staff token)
> **Base URL (production):** `https://api.riviwa.com/api/v1/analytics`

---

## Table of Contents

1. [Platform Grievance Dashboard](#1-platform-grievance-dashboard)
2. [Project — Feedback by Department](#2-project--feedback-by-department)
3. [Project — Feedback by Stage (Sub-project)](#3-project--feedback-by-stage-sub-project)
4. [Platform — Feedback by Department](#4-platform--feedback-by-department)
5. [Platform — Feedback by Service](#5-platform--feedback-by-service)
6. [Platform — Feedback by Product](#6-platform--feedback-by-product)
7. [Platform — Feedback by Category](#7-platform--feedback-by-category)
8. [Project — Feedback by Branch](#8-project--feedback-by-branch)
9. [Organisation — Feedback by Branch](#9-organisation--feedback-by-branch)
10. [Platform — Feedback by Branch](#10-platform--feedback-by-branch)

---

## Common Concepts

### feedback_type values
| Value | Description |
|---|---|
| `GRIEVANCE` | Complaints and grievances |
| `SUGGESTION` | Suggestions and ideas |
| `APPLAUSE` | Positive feedback / praise |
| `INQUIRY` | Information requests |

Omit `feedback_type` to get **all types combined in one response** — each row returns counts broken down by type, enabling side-by-side comparison.

### All endpoints are GET — no request body
Query parameters only. All `date_from` / `date_to` values use ISO format `YYYY-MM-DD`.

---

## 1. Platform Grievance Dashboard

```
GET /api/v1/analytics/platform/grievances/dashboard
```

Comprehensive grievance dashboard across the **entire platform**. All filters are optional — omit all to get platform-wide data.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `org_id` | UUID | No | Scope to a specific organisation |
| `project_id` | UUID | No | Scope to a specific project |
| `department_id` | UUID | No | Filter by department |
| `status` | string | No | `SUBMITTED` \| `ACKNOWLEDGED` \| `IN_REVIEW` \| `ESCALATED` \| `RESOLVED` \| `CLOSED` \| `DISMISSED` |
| `priority` | string | No | `CRITICAL` \| `HIGH` \| `MEDIUM` \| `LOW` |
| `date_from` | string | No | ISO date `YYYY-MM-DD` — filter by submission date (inclusive) |
| `date_to` | string | No | ISO date `YYYY-MM-DD` — filter by submission date (inclusive) |
| `page` | integer | No | Page number (default: `1`) |
| `page_size` | integer | No | Items per page (default: `50`, max: `200`) |

### Response Schema

```json
{
  "summary": {
    "total_grievances": 32,
    "resolved": 1,
    "closed": 1,
    "unresolved": 30,
    "escalated": 3,
    "dismissed": 0,
    "acknowledged_count": 6,
    "acknowledged_pct": 18.75,
    "resolved_on_time": 1,
    "resolved_late": 0,
    "resolved_on_time_pct": 100.0,
    "resolved_late_pct": 0.0,
    "avg_resolution_hours": 5.59,
    "avg_days_unresolved": 8.02
  },
  "by_priority": [
    { "priority": "CRITICAL", "total": 1, "unresolved": 1, "resolved": 0 },
    { "priority": "HIGH",     "total": 4, "unresolved": 3, "resolved": 1 },
    { "priority": "MEDIUM",   "total": 25,"unresolved": 24,"resolved": 1 },
    { "priority": "LOW",      "total": 2, "unresolved": 2, "resolved": 0 }
  ],
  "by_department": [
    {
      "department_id": "d48b2c34-76d1-4fc1-997b-f26e00f5e31e",
      "total": 1,
      "unresolved": 1,
      "resolved": 0,
      "avg_resolution_hours": null
    }
  ],
  "by_org": [
    {
      "organisation_id": "7fdcb62a-010c-4000-868c-80d72e0f1504",
      "org_name": null,
      "total": 16,
      "unresolved": 16,
      "resolved": 0
    }
  ],
  "overdue": [
    {
      "feedback_id": "uuid",
      "unique_ref": "GRV-2026-0001",
      "priority": "HIGH",
      "status": "IN_REVIEW",
      "submitted_at": "2026-01-10T09:00:00Z",
      "target_resolution_date": "2026-01-17T09:00:00Z",
      "days_overdue": 3.5,
      "department_id": "uuid-or-null",
      "assigned_to_user_id": "uuid-or-null",
      "committee_id": "uuid-or-null",
      "issue_lga": "Ilala"
    }
  ],
  "grievances": {
    "total": 32,
    "page": 1,
    "page_size": 50,
    "items": [
      {
        "feedback_id": "9e03ffa6-85db-424c-9e77-f02d1bcbb6d1",
        "unique_ref": "GRV-2026-0033",
        "priority": "MEDIUM",
        "status": "SUBMITTED",
        "category": "OTHER",
        "submitted_at": "2026-04-20T07:09:15.577164Z",
        "resolved_at": null,
        "acknowledged_at": null,
        "target_resolution_date": null,
        "days_unresolved": 4.07,
        "department_id": "e6d492db-f602-4198-8096-3374aed182d8",
        "service_id": null,
        "product_id": null,
        "category_def_id": null,
        "issue_lga": "Ilala",
        "issue_ward": null,
        "assigned_to_user_id": null,
        "committee_id": null,
        "stage_id": null,
        "project_id": "c3bcb428-dba2-4bb7-b35d-bb8972ba1cc5"
      }
    ]
  }
}
```

### Example Requests

```bash
# Platform-wide (no filters)
GET /api/v1/analytics/platform/grievances/dashboard

# Scoped to one org
GET /api/v1/analytics/platform/grievances/dashboard?org_id=7fdcb62a-010c-4000-868c-80d72e0f1504

# Scoped to one project
GET /api/v1/analytics/platform/grievances/dashboard?project_id=47f208ee-7c15-4641-81eb-936c18c590c7

# Filter by priority + date range
GET /api/v1/analytics/platform/grievances/dashboard?priority=HIGH&date_from=2026-01-01&date_to=2026-12-31

# Filter by status
GET /api/v1/analytics/platform/grievances/dashboard?status=ESCALATED

# With pagination
GET /api/v1/analytics/platform/grievances/dashboard?page=2&page_size=20
```

### Counterparts at other levels

| Level | Endpoint |
|---|---|
| Project | `GET /api/v1/analytics/grievances/dashboard?project_id=<uuid>` |
| Organisation | `GET /api/v1/analytics/org/{org_id}/grievances/dashboard` |
| **Platform** | `GET /api/v1/analytics/platform/grievances/dashboard` ← this endpoint |

---

## 2. Project — Feedback by Department

```
GET /api/v1/analytics/feedback/by-department
```

Feedback counts grouped by **department_id** (branch) within a single project. Returns all feedback types side-by-side for cross-department comparison.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_id` | UUID | **Yes** | Project to analyse |
| `feedback_type` | string | No | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` — omit for all types |
| `date_from` | string | No | ISO date `YYYY-MM-DD` |
| `date_to` | string | No | ISO date `YYYY-MM-DD` |

> Only feedback rows where `department_id IS NOT NULL` are included.

### Response Schema

```json
{
  "total_items": 2,
  "items": [
    {
      "department_id": "d48b2c34-76d1-4fc1-997b-f26e00f5e31e",
      "total": 18,
      "grievances": 10,
      "suggestions": 5,
      "applause": 2,
      "inquiries": 1,
      "resolved": 3,
      "avg_resolution_hours": 24.5
    },
    {
      "department_id": "e6d492db-f602-4198-8096-3374aed182d8",
      "total": 7,
      "grievances": 4,
      "suggestions": 2,
      "applause": 1,
      "inquiries": 0,
      "resolved": 1,
      "avg_resolution_hours": null
    }
  ]
}
```

### Example Requests

```bash
# All feedback types per department
GET /api/v1/analytics/feedback/by-department?project_id=47f208ee-7c15-4641-81eb-936c18c590c7

# Grievances only per department
GET /api/v1/analytics/feedback/by-department?project_id=47f208ee-7c15-4641-81eb-936c18c590c7&feedback_type=GRIEVANCE

# Date-filtered
GET /api/v1/analytics/feedback/by-department?project_id=47f208ee-7c15-4641-81eb-936c18c590c7&date_from=2026-01-01&date_to=2026-12-31
```

### Counterparts at other levels

| Level | Endpoint |
|---|---|
| **Project** | `GET /api/v1/analytics/feedback/by-department` ← this endpoint |
| Organisation | `GET /api/v1/analytics/org/{org_id}/by-department` |
| Platform | `GET /api/v1/analytics/platform/by-department` |

---

## 3. Project — Feedback by Stage (Sub-project)

```
GET /api/v1/analytics/feedback/by-stage
```

Feedback counts grouped by **project stage** (sub-project) within a single project. Rows are ordered by `stage_order` ascending so they reflect the project lifecycle sequence.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_id` | UUID | **Yes** | Project to analyse |
| `feedback_type` | string | No | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` — omit for all types |
| `date_from` | string | No | ISO date `YYYY-MM-DD` |
| `date_to` | string | No | ISO date `YYYY-MM-DD` |

> Only feedback rows where `stage_id IS NOT NULL` are included.

### Response Schema

```json
{
  "total_items": 1,
  "items": [
    {
      "stage_id": "42c5b84e-005e-4236-adbc-b5a66cfa786a",
      "stage_name": "Initial stage",
      "stage_order": 1,
      "total": 17,
      "grievances": 8,
      "suggestions": 5,
      "applause": 4,
      "inquiries": 0,
      "resolved": 0,
      "avg_resolution_hours": null
    }
  ]
}
```

### Example Requests

```bash
# All feedback types per stage
GET /api/v1/analytics/feedback/by-stage?project_id=47f208ee-7c15-4641-81eb-936c18c590c7

# Grievances only per stage
GET /api/v1/analytics/feedback/by-stage?project_id=47f208ee-7c15-4641-81eb-936c18c590c7&feedback_type=GRIEVANCE

# Date-filtered
GET /api/v1/analytics/feedback/by-stage?project_id=47f208ee-7c15-4641-81eb-936c18c590c7&date_from=2026-01-01&date_to=2026-12-31
```

---

## 4. Platform — Feedback by Department

```
GET /api/v1/analytics/platform/by-department
```

Feedback counts grouped by **department_id** across the entire platform. All filters are optional.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `org_id` | UUID | No | Scope to a specific organisation |
| `project_id` | UUID | No | Scope to a specific project |
| `feedback_type` | string | No | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` — omit for all types |
| `date_from` | string | No | ISO date `YYYY-MM-DD` |
| `date_to` | string | No | ISO date `YYYY-MM-DD` |

> Only feedback rows where `department_id IS NOT NULL` are included.

### Response Schema

```json
{
  "dimension": "department_id",
  "total_items": 2,
  "items": [
    {
      "dimension_id": "d48b2c34-76d1-4fc1-997b-f26e00f5e31e",
      "total": 1,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "resolved": 0,
      "avg_resolution_hours": null
    },
    {
      "dimension_id": "e6d492db-f602-4198-8096-3374aed182d8",
      "total": 1,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "resolved": 0,
      "avg_resolution_hours": null
    }
  ]
}
```

### Example Requests

```bash
# Platform-wide department breakdown (all types)
GET /api/v1/analytics/platform/by-department

# Grievances only
GET /api/v1/analytics/platform/by-department?feedback_type=GRIEVANCE

# Scoped to one org
GET /api/v1/analytics/platform/by-department?org_id=7fdcb62a-010c-4000-868c-80d72e0f1504

# Scoped to one project
GET /api/v1/analytics/platform/by-department?project_id=47f208ee-7c15-4641-81eb-936c18c590c7

# Date-filtered
GET /api/v1/analytics/platform/by-department?date_from=2026-01-01&date_to=2026-12-31
```

---

## 5. Platform — Feedback by Service

```
GET /api/v1/analytics/platform/by-service
```

Feedback counts grouped by **service_id** across the entire platform.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `org_id` | UUID | No | Scope to a specific organisation |
| `project_id` | UUID | No | Scope to a specific project |
| `feedback_type` | string | No | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` — omit for all types |
| `date_from` | string | No | ISO date `YYYY-MM-DD` |
| `date_to` | string | No | ISO date `YYYY-MM-DD` |

> Only feedback rows where `service_id IS NOT NULL` are included.

### Response Schema

```json
{
  "dimension": "service_id",
  "total_items": 3,
  "items": [
    {
      "dimension_id": "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb",
      "total": 12,
      "grievances": 7,
      "suggestions": 3,
      "applause": 2,
      "inquiries": 0,
      "resolved": 4,
      "avg_resolution_hours": 36.2
    }
  ]
}
```

### Example Requests

```bash
# Platform-wide service breakdown (all types)
GET /api/v1/analytics/platform/by-service

# Suggestions only
GET /api/v1/analytics/platform/by-service?feedback_type=SUGGESTION

# Scoped to one org
GET /api/v1/analytics/platform/by-service?org_id=7fdcb62a-010c-4000-868c-80d72e0f1504
```

### Counterparts at other levels

| Level | Endpoint |
|---|---|
| Project | `GET /api/v1/analytics/feedback/by-service?project_id=<uuid>` |
| Organisation | `GET /api/v1/analytics/org/{org_id}/by-service` |
| **Platform** | `GET /api/v1/analytics/platform/by-service` ← this endpoint |

---

## 6. Platform — Feedback by Product

```
GET /api/v1/analytics/platform/by-product
```

Feedback counts grouped by **product_id** across the entire platform.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `org_id` | UUID | No | Scope to a specific organisation |
| `project_id` | UUID | No | Scope to a specific project |
| `feedback_type` | string | No | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` — omit for all types |
| `date_from` | string | No | ISO date `YYYY-MM-DD` |
| `date_to` | string | No | ISO date `YYYY-MM-DD` |

> Only feedback rows where `product_id IS NOT NULL` are included.

### Response Schema

```json
{
  "dimension": "product_id",
  "total_items": 2,
  "items": [
    {
      "dimension_id": "cccccccc-4444-5555-6666-dddddddddddd",
      "total": 8,
      "grievances": 3,
      "suggestions": 4,
      "applause": 1,
      "inquiries": 0,
      "resolved": 2,
      "avg_resolution_hours": 48.0
    }
  ]
}
```

### Example Requests

```bash
# Platform-wide product breakdown (all types)
GET /api/v1/analytics/platform/by-product

# Applause only
GET /api/v1/analytics/platform/by-product?feedback_type=APPLAUSE

# Scoped to one org, date-filtered
GET /api/v1/analytics/platform/by-product?org_id=7fdcb62a-010c-4000-868c-80d72e0f1504&date_from=2026-01-01
```

### Counterparts at other levels

| Level | Endpoint |
|---|---|
| Project | `GET /api/v1/analytics/feedback/by-product?project_id=<uuid>` |
| Organisation | `GET /api/v1/analytics/org/{org_id}/by-product` |
| **Platform** | `GET /api/v1/analytics/platform/by-product` ← this endpoint |

---

## 7. Platform — Feedback by Category

```
GET /api/v1/analytics/platform/by-category
```

Feedback counts grouped by **dynamic category** (`category_def_id`) across the entire platform. Rows with no category set appear under `category_name: "uncategorised"`.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `org_id` | UUID | No | Scope to a specific organisation |
| `project_id` | UUID | No | Scope to a specific project |
| `feedback_type` | string | No | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` — omit for all types |
| `date_from` | string | No | ISO date `YYYY-MM-DD` |
| `date_to` | string | No | ISO date `YYYY-MM-DD` |

### Response Schema

```json
{
  "total_items": 10,
  "items": [
    {
      "category_def_id": null,
      "category_name": "uncategorised",
      "category_slug": null,
      "total": 30,
      "grievances": 14,
      "suggestions": 5,
      "applause": 8,
      "inquiries": 3,
      "resolved": 1,
      "avg_resolution_hours": 168.0
    },
    {
      "category_def_id": "78518804-9138-4f69-afad-8cc521e47193",
      "category_name": "Other",
      "category_slug": "other",
      "total": 11,
      "grievances": 6,
      "suggestions": 5,
      "applause": 0,
      "inquiries": 0,
      "resolved": 0,
      "avg_resolution_hours": null
    },
    {
      "category_def_id": "bd830aab-f26a-43af-b914-938a0b76e2d0",
      "category_name": "Compensation",
      "category_slug": "compensation",
      "total": 5,
      "grievances": 5,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "resolved": 1,
      "avg_resolution_hours": 16.36
    },
    {
      "category_def_id": "cbc6b72d-0372-421b-b33c-7006bf7550f4",
      "category_name": "Land acquisition",
      "category_slug": "land-acquisition",
      "total": 3,
      "grievances": 3,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "resolved": 0,
      "avg_resolution_hours": null
    }
  ]
}
```

### Example Requests

```bash
# All categories, all feedback types
GET /api/v1/analytics/platform/by-category

# Grievances only — compare grievance volume per category
GET /api/v1/analytics/platform/by-category?feedback_type=GRIEVANCE

# Suggestions only — compare suggestion topics
GET /api/v1/analytics/platform/by-category?feedback_type=SUGGESTION

# Applause only — see what's being praised most
GET /api/v1/analytics/platform/by-category?feedback_type=APPLAUSE

# Inquiries only
GET /api/v1/analytics/platform/by-category?feedback_type=INQUIRY

# Scoped to one org
GET /api/v1/analytics/platform/by-category?org_id=7fdcb62a-010c-4000-868c-80d72e0f1504

# Scoped to one project
GET /api/v1/analytics/platform/by-category?project_id=47f208ee-7c15-4641-81eb-936c18c590c7

# Date-filtered
GET /api/v1/analytics/platform/by-category?date_from=2026-01-01&date_to=2026-12-31

# Combined: grievances only in one org, this year
GET /api/v1/analytics/platform/by-category?org_id=7fdcb62a-010c-4000-868c-80d72e0f1504&feedback_type=GRIEVANCE&date_from=2026-01-01
```

### Counterparts at other levels

| Level | Endpoint |
|---|---|
| Project | `GET /api/v1/analytics/feedback/by-category?project_id=<uuid>` |
| Organisation | `GET /api/v1/analytics/org/{org_id}/by-category` |
| **Platform** | `GET /api/v1/analytics/platform/by-category` ← this endpoint |

---

## 8. Project — Feedback by Branch

```
GET /api/v1/analytics/feedback/by-branch
```

Feedback counts grouped by **branch_id** within a single project. `branch_id` is denormalised onto each feedback row at submission time from `OrgDepartment.branch_id` via the auth service. Only rows where `branch_id IS NOT NULL` are returned.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_id` | UUID | **Yes** | Project to analyse |
| `feedback_type` | string | No | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` — omit for all types |
| `date_from` | string | No | ISO date `YYYY-MM-DD` |
| `date_to` | string | No | ISO date `YYYY-MM-DD` |

### Response Schema

```json
{
  "total_items": 2,
  "items": [
    {
      "branch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "total": 24,
      "grievances": 12,
      "suggestions": 6,
      "applause": 4,
      "inquiries": 2,
      "resolved": 5,
      "avg_resolution_hours": 18.4
    },
    {
      "branch_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "total": 11,
      "grievances": 7,
      "suggestions": 3,
      "applause": 1,
      "inquiries": 0,
      "resolved": 2,
      "avg_resolution_hours": null
    }
  ]
}
```

### Example Requests

```bash
# All feedback types per branch
GET /api/v1/analytics/feedback/by-branch?project_id=47f208ee-7c15-4641-81eb-936c18c590c7

# Grievances only — compare grievance load per branch
GET /api/v1/analytics/feedback/by-branch?project_id=47f208ee-7c15-4641-81eb-936c18c590c7&feedback_type=GRIEVANCE

# Suggestions only
GET /api/v1/analytics/feedback/by-branch?project_id=47f208ee-7c15-4641-81eb-936c18c590c7&feedback_type=SUGGESTION

# Date-filtered
GET /api/v1/analytics/feedback/by-branch?project_id=47f208ee-7c15-4641-81eb-936c18c590c7&date_from=2026-01-01&date_to=2026-12-31
```

### How branch_id is populated

`branch_id` is **not submitted by the client** — it is resolved automatically at submission time:

1. Client submits feedback with a `department_id`
2. `feedback_service` calls `GET /internal/departments/{dept_id}` on the auth service
3. Auth service returns `branch_id` from `OrgDepartment.branch_id`
4. `branch_id` is stored on the feedback row

If a department has no branch assigned (`OrgDepartment.branch_id = NULL`) the feedback row will also have `branch_id = NULL` and will not appear in branch analytics. Clients may also pass `branch_id` directly in the submission payload to override.

---

## 9. Organisation — Feedback by Branch

```
GET /api/v1/analytics/org/{org_id}/by-branch
```

Feedback counts grouped by **branch_id** across all projects in an organisation.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `org_id` | UUID | **Yes** (path) | Organisation to analyse |
| `feedback_type` | string | No | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` — omit for all types |
| `date_from` | string | No | ISO date `YYYY-MM-DD` |
| `date_to` | string | No | ISO date `YYYY-MM-DD` |

### Response Schema

```json
{
  "dimension": "branch_id",
  "total_items": 3,
  "items": [
    {
      "dimension_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "total": 38,
      "grievances": 20,
      "suggestions": 10,
      "applause": 6,
      "inquiries": 2,
      "resolved": 8,
      "avg_resolution_hours": 22.1
    },
    {
      "dimension_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "total": 15,
      "grievances": 9,
      "suggestions": 4,
      "applause": 2,
      "inquiries": 0,
      "resolved": 3,
      "avg_resolution_hours": 47.5
    }
  ]
}
```

> `dimension_id` is the `branch_id` UUID. Resolve branch names by calling `GET /api/v1/orgs/{org_id}/branches` on the auth service.

### Example Requests

```bash
# All feedback types per branch in org
GET /api/v1/analytics/org/7fdcb62a-010c-4000-868c-80d72e0f1504/by-branch

# Grievances only — cross-branch comparison
GET /api/v1/analytics/org/7fdcb62a-010c-4000-868c-80d72e0f1504/by-branch?feedback_type=GRIEVANCE

# Suggestions only
GET /api/v1/analytics/org/7fdcb62a-010c-4000-868c-80d72e0f1504/by-branch?feedback_type=SUGGESTION

# Applause only
GET /api/v1/analytics/org/7fdcb62a-010c-4000-868c-80d72e0f1504/by-branch?feedback_type=APPLAUSE

# Date-filtered
GET /api/v1/analytics/org/7fdcb62a-010c-4000-868c-80d72e0f1504/by-branch?date_from=2026-01-01&date_to=2026-12-31
```

---

## 10. Platform — Feedback by Branch

```
GET /api/v1/analytics/platform/by-branch
```

Feedback counts grouped by **branch_id** across the entire platform. All filters optional.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `org_id` | UUID | No | Scope to a specific organisation |
| `project_id` | UUID | No | Scope to a specific project |
| `feedback_type` | string | No | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` — omit for all types |
| `date_from` | string | No | ISO date `YYYY-MM-DD` |
| `date_to` | string | No | ISO date `YYYY-MM-DD` |

### Response Schema

```json
{
  "dimension": "branch_id",
  "total_items": 5,
  "items": [
    {
      "dimension_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "total": 62,
      "grievances": 30,
      "suggestions": 18,
      "applause": 10,
      "inquiries": 4,
      "resolved": 12,
      "avg_resolution_hours": 19.8
    }
  ]
}
```

### Example Requests

```bash
# Platform-wide branch comparison (all types)
GET /api/v1/analytics/platform/by-branch

# Grievances only across all branches platform-wide
GET /api/v1/analytics/platform/by-branch?feedback_type=GRIEVANCE

# Suggestions only
GET /api/v1/analytics/platform/by-branch?feedback_type=SUGGESTION

# Applause only
GET /api/v1/analytics/platform/by-branch?feedback_type=APPLAUSE

# Inquiries only
GET /api/v1/analytics/platform/by-branch?feedback_type=INQUIRY

# Scoped to one organisation
GET /api/v1/analytics/platform/by-branch?org_id=7fdcb62a-010c-4000-868c-80d72e0f1504

# Scoped to one project
GET /api/v1/analytics/platform/by-branch?project_id=47f208ee-7c15-4641-81eb-936c18c590c7

# Combined: grievances in one org, date-filtered
GET /api/v1/analytics/platform/by-branch?org_id=7fdcb62a-010c-4000-868c-80d72e0f1504&feedback_type=GRIEVANCE&date_from=2026-01-01

# Date-filtered platform-wide
GET /api/v1/analytics/platform/by-branch?date_from=2026-01-01&date_to=2026-12-31
```

### Counterparts at other levels

| Level | Endpoint |
|---|---|
| **Project** | `GET /api/v1/analytics/feedback/by-branch?project_id=<uuid>` |
| **Organisation** | `GET /api/v1/analytics/org/{org_id}/by-branch` |
| **Platform** | `GET /api/v1/analytics/platform/by-branch` ← this endpoint |

---

## Full Dimension Coverage Matrix

| Dimension | Project | Organisation | Platform |
|---|---|---|---|
| **branch_id** | `/analytics/feedback/by-branch?project_id=` | `/analytics/org/{id}/by-branch` | `/analytics/platform/by-branch` |
| **department_id** | `/analytics/feedback/by-department?project_id=` | `/analytics/org/{id}/by-department` | `/analytics/platform/by-department` |
| **service_id** | `/analytics/feedback/by-service?project_id=` | `/analytics/org/{id}/by-service` | `/analytics/platform/by-service` |
| **product_id** | `/analytics/feedback/by-product?project_id=` | `/analytics/org/{id}/by-product` | `/analytics/platform/by-product` |
| **category_def_id** | `/analytics/feedback/by-category?project_id=` | `/analytics/org/{id}/by-category` | `/analytics/platform/by-category` |
| **stage_id** (sub-project) | `/analytics/feedback/by-stage?project_id=` | — | — |

All endpoints accept `feedback_type=GRIEVANCE|SUGGESTION|APPLAUSE|INQUIRY` — omit to see all types combined in a single response for side-by-side comparison.

---

## Grievance Dashboard Coverage Matrix

| Level | Endpoint | Filters |
|---|---|---|
| **Project** | `GET /api/v1/analytics/grievances/dashboard` | `project_id` (required), `department_id`, `status`, `priority`, `date_from/to`, `page/page_size` |
| **Organisation** | `GET /api/v1/analytics/org/{org_id}/grievances/dashboard` | `project_id` (optional), `department_id`, `status`, `priority`, `date_from/to`, `page/page_size` |
| **Platform** | `GET /api/v1/analytics/platform/grievances/dashboard` | `org_id`, `project_id`, `department_id`, `status`, `priority`, `date_from/to`, `page/page_size` |

All three return: `summary` (total, resolved on time %, resolved late %, acknowledged %), `by_priority`, `by_department`, `by_project/by_org`, `overdue` list, paginated `grievances` list.

---

## Auth Service — Internal Endpoint

### GET /api/v1/internal/departments/{dept_id}

Used by `feedback_service` at submission time to resolve `branch_id`.

**Auth:** `X-Service-Key: <INTERNAL_SERVICE_KEY>` header (not a JWT)

**Response:**

```json
{
  "id": "11b760b3-7fc7-402e-ae64-b001e0359e78",
  "name": "HR",
  "code": "HR",
  "branch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

`branch_id` is `null` when the department is not assigned to a branch.
