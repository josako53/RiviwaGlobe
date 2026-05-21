# RIVIWA Dimension Analytics API

**Service:** `analytics_service` · Port `8095`  
**Base URL:** `https://api.riviwa.com/api/v1`  
**Auth:** All endpoints require `Authorization: Bearer <JWT>` with at least `manager` org role or platform admin.  
**Tested:** 2026-05-17 · All 16 analytics endpoints + 1 feedback lifecycle endpoint verified with live data.

---

## Overview

This API provides deep analytics for four entity dimensions:

| Dimension | URL prefix | Scoped by |
|-----------|-----------|-----------|
| Product | `/analytics/products/{product_id}/...` | `feedbacks.product_id` |
| Service | `/analytics/services/{service_id}/...` | `feedbacks.service_id` |
| Branch | `/analytics/branches/{branch_id}/...` | `feedbacks.branch_id` |
| Department | `/analytics/departments/{department_id}/...` | `feedbacks.department_id` |

Each dimension exposes the same four endpoints:

| Endpoint | Purpose |
|----------|---------|
| `/summary` | Totals, type percentages, resolution rate, implementation rate |
| `/categories` | Category distribution with percentages |
| `/themes` | AI-mined recurring themes (Groq LLM) |
| `/feedback` | Paginated drill-down list with filters |

Also documented here: the companion `POST /feedback/{id}/action-suggestion` lifecycle endpoint in `feedback_service` (port 8090) which drives the implementation rate metric.

---

## Related: `POST /feedback/{id}/action-suggestion`

**Service:** `feedback_service` · Port `8090`  
**Auth:** Manager+ JWT required

Marks a SUGGESTION as implemented (ACTIONED). This is the only way `implementation_rate` in analytics becomes non-zero. Without actioning suggestions, `implementation_rate` always reads 0%.

### Request

```
POST /api/v1/feedback/{feedback_id}/action-suggestion
Authorization: Bearer <JWT>
Content-Type: application/json
```

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `feedback_id` | UUID | ID of the suggestion to action |

**Body**

```json
{
  "implementation_summary": "QR codes now printed on caps in the 2026 Q3 production run.",
  "implemented_at": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `implementation_summary` | string | ✓ | What was actually done. Min 10 characters. |
| `implemented_at` | ISO 8601 datetime | — | Override the implementation timestamp. Defaults to `now()`. |

**Validation rules**

- `feedback_type` must be `SUGGESTION` — returns `400` for any other type
- `status` must be `SUBMITTED`, `ACKNOWLEDGED`, or `IN_REVIEW` — returns `400` if already `ACTIONED`, `CLOSED`, or `DISMISSED`

### Response `200 OK`

Returns the updated feedback record with `status: ACTIONED` and `implemented_at` populated.

```json
{
  "id": "8cf1af9a-...",
  "unique_ref": "SGG-2026-0114",
  "feedback_type": "suggestion",
  "status": "actioned",
  "implemented_at": "2026-05-17T20:24:15.077645+00:00",
  "subject": "Add QR code on bottle cap",
  "description": "Would help verify authenticity directly from the cap."
}
```

### Error responses

| Status | Code | Reason |
|--------|------|--------|
| 400 | `VALIDATION_ERROR` | Not a suggestion, or already actioned/closed/dismissed |
| 404 | `NOT_FOUND` | Feedback not found or not in caller's org |
| 422 | `VALIDATION_ERROR` | `implementation_summary` missing or too short |

---

## Endpoint Pattern — All Four Dimensions

The routes below are shown for `products`. Replace `products/{product_id}` with:
- `services/{service_id}`
- `branches/{branch_id}`
- `departments/{department_id}`

All accept the same query parameters and return identically structured responses, with the matching `product_id` / `service_id` / `branch_id` / `department_id` field populated in the response (the rest are `null`).

---

## 1. Summary

```
GET /api/v1/analytics/products/{product_id}/summary
GET /api/v1/analytics/services/{service_id}/summary
GET /api/v1/analytics/branches/{branch_id}/summary
GET /api/v1/analytics/departments/{department_id}/summary
```

Returns full feedback metrics for a single entity — counts, percentage distribution across all feedback types, resolution rate, suggestion implementation rate, pipeline status, and (for products only) QR scan counts.

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `org_id` | UUID | — | Restrict to a specific organisation |
| `date_from` | `YYYY-MM-DD` | — | Start of date range (inclusive) |
| `date_to` | `YYYY-MM-DD` | — | End of date range (inclusive) |

### Response `200 OK`

```json
{
  "product_id": "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
  "service_id": null,
  "branch_id": null,
  "department_id": null,

  "total": 19,

  "by_type": {
    "grievance": {
      "count": 15,
      "pct": 78.9,
      "resolved": 1,
      "resolution_rate": 6.7
    },
    "suggestion": {
      "count": 2,
      "pct": 10.5,
      "implemented": 1,
      "implementation_rate": 50.0
    },
    "applause": {
      "count": 1,
      "pct": 5.3
    },
    "inquiry": {
      "count": 1,
      "pct": 5.3
    }
  },

  "resolved": 1,
  "resolution_rate_pct": 5.3,
  "avg_resolution_hours": 24.3,
  "pending": 17,
  "acknowledged": 0,
  "in_review": 0,
  "overdue": 2,

  "qr_scans": {
    "scan_count": 43,
    "authentic": 40,
    "already_used": 3,
    "unrecognized": 0
  }
}
```

### Response schema

| Field | Type | Description |
|-------|------|-------------|
| `total` | int | All feedback submitted for this entity |
| `by_type.grievance.count` | int | Number of grievances |
| `by_type.grievance.pct` | float | % of total (e.g. `78.9`) |
| `by_type.grievance.resolved` | int | Grievances with status RESOLVED or CLOSED |
| `by_type.grievance.resolution_rate` | float | `resolved / grievances × 100` |
| `by_type.suggestion.implemented` | int | Suggestions with `status=ACTIONED` or `implemented_at` set |
| `by_type.suggestion.implementation_rate` | float | `implemented / suggestions × 100` |
| `by_type.applause.count` | int | Positive recognition count |
| `by_type.inquiry.count` | int | Questions / info requests count |
| `resolved` | int | Total resolved across all types |
| `resolution_rate_pct` | float | `resolved / total × 100` |
| `avg_resolution_hours` | float | Mean hours from `submitted_at` → `resolved_at` |
| `pending` | int | Still in `SUBMITTED` status (not yet acknowledged) |
| `acknowledged` | int | Acknowledged but not yet in review |
| `in_review` | int | Actively being investigated |
| `overdue` | int | `ACKNOWLEDGED` or `IN_REVIEW` past `target_resolution_date` |
| `qr_scans` | object | **Products only.** QR scan counts from verification service |
| `qr_scans.scan_count` | int | Total scans |
| `qr_scans.authentic` | int | First-time scans (code not yet used) |
| `qr_scans.already_used` | int | Scans after feedback was submitted |
| `qr_scans.unrecognized` | int | Scans of codes not found in system |

**Service/branch/department responses:** identical structure but `qr_scans` is `null`.

---

## 2. Category Distribution

```
GET /api/v1/analytics/products/{product_id}/categories
GET /api/v1/analytics/services/{service_id}/categories
GET /api/v1/analytics/branches/{branch_id}/categories
GET /api/v1/analytics/departments/{department_id}/categories
```

Returns every feedback category assigned to this entity with its count and percentage — e.g. `"Quality of work: 31.6%, Other: 10.5%"`. Each category row also breaks down by feedback type and carries the `category_id` needed to drill down to individual feedback items.

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `org_id` | UUID | — | Restrict to a specific organisation |
| `feedback_type` | string | — | `grievance` \| `suggestion` \| `applause` \| `inquiry` |
| `date_from` | `YYYY-MM-DD` | — | Start of date range |
| `date_to` | `YYYY-MM-DD` | — | End of date range |

### Response `200 OK`

```json
{
  "product_id": "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
  "service_id": null,
  "branch_id": null,
  "department_id": null,
  "total_categorised": 8,
  "categories": [
    {
      "category_id": null,
      "category_name": "Uncategorised",
      "category_slug": "uncategorised",
      "color_hex": null,
      "icon": null,
      "count": 11,
      "pct": 57.9,
      "grievances": 11,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "resolved": 0,
      "avg_resolution_hours": 0.0
    },
    {
      "category_id": "c61cca36-0613-42f3-bd21-5e1b8e31573d",
      "category_name": "Quality of work",
      "category_slug": "quality",
      "color_hex": "#1D9E75",
      "icon": null,
      "count": 6,
      "pct": 31.6,
      "grievances": 3,
      "suggestions": 2,
      "applause": 1,
      "inquiries": 0,
      "resolved": 1,
      "avg_resolution_hours": 0.0
    },
    {
      "category_id": "78518804-9138-4f69-afad-8cc521e47193",
      "category_name": "Other",
      "category_slug": "other",
      "color_hex": "#888780",
      "icon": null,
      "count": 2,
      "pct": 10.5,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 1,
      "resolved": 0,
      "avg_resolution_hours": 0.0
    }
  ]
}
```

### Response schema — `categories[]` items

| Field | Type | Description |
|-------|------|-------------|
| `category_id` | UUID \| null | `null` for the "Uncategorised" bucket |
| `category_name` | string | Human-readable name. `"Uncategorised"` when `category_id` is null |
| `category_slug` | string | URL-safe slug |
| `color_hex` | string \| null | Hex colour for UI rendering (e.g. `"#1D9E75"`) |
| `icon` | string \| null | Icon identifier, if set |
| `count` | int | Total feedback in this category for the entity |
| `pct` | float | `count / total × 100` — percentage of **all** feedback for this entity |
| `grievances` | int | Grievances in this category |
| `suggestions` | int | Suggestions in this category |
| `applause` | int | Applause in this category |
| `inquiries` | int | Inquiries in this category |
| `resolved` | int | Resolved feedback in this category |
| `avg_resolution_hours` | float | Average resolution time for this category |

**Drill-down pattern:** pass the returned `category_id` to the `/feedback` endpoint to list every individual feedback item in that category.

---

## 3. AI-Mined Themes

```
GET /api/v1/analytics/products/{product_id}/themes
GET /api/v1/analytics/services/{service_id}/themes
GET /api/v1/analytics/branches/{branch_id}/themes
GET /api/v1/analytics/departments/{department_id}/themes
```

Fetches up to `limit` recent feedback descriptions and voice-note transcriptions, sends them to **Groq LLM** (`llama-3.3-70b-versatile`), and returns automatically identified recurring themes with percentage share. Unlike structured categories (which are pre-assigned), themes are derived directly from the language consumers used — exposing patterns that no predefined taxonomy would capture.

### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int (10–200) | 80 | Max feedback texts to analyse |

### Response `200 OK` — sufficient data

```json
{
  "product_id": "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
  "service_id": null,
  "branch_id": null,
  "department_id": null,
  "texts_analysed": 19,
  "themes": [
    { "name": "Quality Issues",        "count": 4, "pct": 21.1 },
    { "name": "Product Packaging",     "count": 3, "pct": 15.8 },
    { "name": "Authenticity Concerns", "count": 1, "pct": 5.3  },
    { "name": "Product Variety",       "count": 1, "pct": 5.3  }
  ],
  "powered_by": "groq",
  "note": null
}
```

### Response `200 OK` — insufficient data (< 5 texts)

```json
{
  "product_id": "...",
  "texts_analysed": 3,
  "themes": [],
  "powered_by": null,
  "note": "Not enough feedback to mine themes (minimum 5 required)."
}
```

### Response schema

| Field | Type | Description |
|-------|------|-------------|
| `texts_analysed` | int | Number of feedback texts passed to Groq |
| `themes` | array | Up to 8 themes, sorted by count descending |
| `themes[].name` | string | Short theme label (2–5 words, title case) |
| `themes[].count` | int | Approximate number of texts that mention this theme |
| `themes[].pct` | float | `count / texts_analysed × 100` |
| `powered_by` | `"groq"` \| null | `null` when Groq is unconfigured or returned no themes |
| `note` | string \| null | Set when there is insufficient data |

**Requirements:** `GROQ_API_KEY` must be set in the analytics service environment. Returns empty `themes: []` with `powered_by: null` if the key is absent.

---

## 4. Feedback Drill-Down

```
GET /api/v1/analytics/products/{product_id}/feedback
GET /api/v1/analytics/services/{service_id}/feedback
GET /api/v1/analytics/branches/{branch_id}/feedback
GET /api/v1/analytics/departments/{department_id}/feedback
```

Returns a paginated list of individual feedback records for the entity. This is the drill-down endpoint — it is called when a user clicks a feedback type chip (e.g. "Grievances") or a category bar on the dashboard.

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `feedback_type` | string | — | `grievance` \| `suggestion` \| `applause` \| `inquiry` |
| `category_id` | UUID | — | Filter to a specific category (from `/categories`) |
| `status` | string | — | `SUBMITTED` \| `ACKNOWLEDGED` \| `IN_REVIEW` \| `RESOLVED` \| `CLOSED` |
| `org_id` | UUID | — | Restrict to a specific organisation |
| `date_from` | `YYYY-MM-DD` | — | Start of date range |
| `date_to` | `YYYY-MM-DD` | — | End of date range |
| `page` | int ≥ 1 | — | Page number. Default: `1` |
| `size` | int 1–100 | — | Items per page. Default: `20` |

### Common drill-down patterns

| Use case | Query |
|----------|-------|
| See all grievances for a product | `?feedback_type=grievance` |
| See all suggestions for a service | `?feedback_type=suggestion` |
| Click a category bar → see its items | `?category_id=c61cca36-...` |
| See pending (unacknowledged) feedback | `?status=SUBMITTED` |
| Implemented suggestions only | `?feedback_type=suggestion&status=ACTIONED` |
| Overdue grievances this month | `?feedback_type=grievance&status=IN_REVIEW&date_from=2026-05-01` |

### Response `200 OK`

```json
{
  "product_id": "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
  "service_id": null,
  "branch_id": null,
  "department_id": null,
  "total": 15,
  "page": 1,
  "size": 2,
  "items": [
    {
      "feedback_id": "db72dc12-02c6-40ff-b710-89aa8c68d68d",
      "unique_ref": "GRV-2026-0263",
      "feedback_type": "GRIEVANCE",
      "status": "SUBMITTED",
      "priority": "MEDIUM",
      "subject": "Product quality below standard",
      "description": "Water has unusual taste, different from usual Azam quality standards.",
      "submitter_name": "Anonymous",
      "is_anonymous": true,
      "location": {
        "region": null,
        "lga": null,
        "ward": null
      },
      "category": {
        "id": "c61cca36-0613-42f3-bd21-5e1b8e31573d",
        "name": "Quality of work",
        "slug": "quality"
      },
      "channel": "WEB_PORTAL",
      "submitted_at": "2026-05-17T20:24:12.225091+00:00",
      "resolved_at": null,
      "implemented_at": null,
      "target_resolution_date": null,
      "org_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
      "project_id": "7ff2c82e-9bcd-4a79-8378-b71056806a78",
      "department_id": null,
      "service_id": null,
      "product_id": "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
      "branch_id": null
    },
    {
      "feedback_id": "c32f0a08-8ff6-48c3-b59f-49003a836fb3",
      "unique_ref": "GRV-2026-0262",
      "feedback_type": "GRIEVANCE",
      "status": "SUBMITTED",
      "priority": "MEDIUM",
      "subject": "Wrong expiry date on label",
      "description": "Expiry printed as 2025 but manufacturing date was 2026.",
      "submitter_name": "Anonymous",
      "is_anonymous": true,
      "location": {
        "region": null,
        "lga": null,
        "ward": null
      },
      "category": {
        "id": "c61cca36-0613-42f3-bd21-5e1b8e31573d",
        "name": "Quality of work",
        "slug": "quality"
      },
      "channel": "WEB_PORTAL",
      "submitted_at": "2026-05-17T20:24:12.127712+00:00",
      "resolved_at": null,
      "implemented_at": null,
      "target_resolution_date": null,
      "org_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
      "project_id": "7ff2c82e-9bcd-4a79-8378-b71056806a78",
      "department_id": null,
      "service_id": null,
      "product_id": "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
      "branch_id": null
    }
  ]
}
```

### Suggestion drill-down — ACTIONED item

When filtering suggestions (`?feedback_type=suggestion`), ACTIONED items show `implemented_at`:

```json
{
  "feedback_id": "7c18a28a-ddeb-428c-b287-f7a316427447",
  "unique_ref": "SGG-2026-0115",
  "feedback_type": "SUGGESTION",
  "status": "ACTIONED",
  "subject": "Install a customer feedback screen",
  "description": "A real-time feedback kiosk at the exit would help track satisfaction instantly.",
  "submitter_name": "Anonymous",
  "implemented_at": "2026-05-17T20:24:15.077645+00:00",
  "category": {
    "id": "c61cca36-0613-42f3-bd21-5e1b8e31573d",
    "name": "Quality of work",
    "slug": "quality"
  },
  "channel": "WEB_PORTAL",
  "submitted_at": "2026-05-17T20:24:12.703201+00:00",
  "service_id": "411da113-cb61-4819-9d11-af9ef08893c0"
}
```

### Response schema — `items[]`

| Field | Type | Description |
|-------|------|-------------|
| `feedback_id` | UUID | Feedback record UUID |
| `unique_ref` | string | Human-readable reference (e.g. `GRV-2026-0263`, `SGG-2026-0115`) |
| `feedback_type` | string | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` |
| `status` | string | `SUBMITTED` \| `ACKNOWLEDGED` \| `IN_REVIEW` \| `ESCALATED` \| `RESOLVED` \| `ACTIONED` \| `CLOSED` \| `DISMISSED` |
| `priority` | string | `CRITICAL` \| `HIGH` \| `MEDIUM` \| `LOW` |
| `subject` | string | Brief title |
| `description` | string | Full description text |
| `submitter_name` | string | Name or `"Anonymous"` if `is_anonymous = true` |
| `is_anonymous` | bool | Whether the submitter requested anonymity |
| `location.region` | string \| null | Region of the reported issue |
| `location.lga` | string \| null | LGA (Local Government Area) |
| `location.ward` | string \| null | Ward |
| `category.id` | UUID \| null | Structured category ID |
| `category.name` | string \| null | Category name |
| `category.slug` | string \| null | Category slug |
| `channel` | string | Intake channel: `WEB_PORTAL`, `MOBILE_APP`, `SMS`, `WHATSAPP`, `VOICE`, etc. |
| `submitted_at` | ISO 8601 | When the feedback was submitted |
| `resolved_at` | ISO 8601 \| null | When it was resolved (grievances) |
| `implemented_at` | ISO 8601 \| null | When the suggestion was implemented (suggestions) |
| `target_resolution_date` | ISO 8601 \| null | Deadline set by GRM officer |
| `org_id` | UUID | Organisation that owns this feedback |
| `project_id` | UUID \| null | Project this feedback is filed under |
| `department_id` | UUID \| null | Department linked to this feedback |
| `service_id` | UUID \| null | Service linked to this feedback |
| `product_id` | UUID \| null | Product linked to this feedback |
| `branch_id` | UUID \| null | Branch linked to this feedback |

---

## Live Test Data — Service Summary

```
GET /api/v1/analytics/services/411da113-cb61-4819-9d11-af9ef08893c0/summary
```

```json
{
  "service_id": "411da113-cb61-4819-9d11-af9ef08893c0",
  "total": 19,
  "by_type": {
    "grievance":  { "count": 9, "pct": 47.4, "resolved": 1, "resolution_rate": 11.1 },
    "suggestion": { "count": 4, "pct": 21.1, "implemented": 1, "implementation_rate": 25.0 },
    "applause":   { "count": 5, "pct": 26.3 },
    "inquiry":    { "count": 1, "pct": 5.3  }
  },
  "resolved": 1,
  "resolution_rate_pct": 5.3,
  "avg_resolution_hours": 0.0,
  "pending": 17,
  "overdue": 0,
  "qr_scans": null
}
```

## Live Test Data — Department Categories

```
GET /api/v1/analytics/departments/699a2c9c-2cd8-4bda-93de-88c9aed3a861/categories
```

```json
{
  "department_id": "699a2c9c-2cd8-4bda-93de-88c9aed3a861",
  "total_categorised": 6,
  "categories": [
    { "category_name": "Uncategorised",  "count": 12, "pct": 66.7, "grievances": 7, "suggestions": 2, "applause": 2, "inquiries": 1 },
    { "category_name": "Staff conduct",  "count": 2,  "pct": 11.1, "color_hex": "#085041" },
    { "category_name": "Quality of work","count": 2,  "pct": 11.1, "color_hex": "#1D9E75" },
    { "category_name": "Timeliness",     "count": 1,  "pct": 5.6,  "color_hex": "#0F6E56" },
    { "category_name": "Corruption",     "count": 1,  "pct": 5.6  }
  ]
}
```

---

## Existing Dimension Analytics (Pre-existing)

These endpoints existed before the new additions. They are scoped differently — project-level or org-level aggregates — and do not support drill-down.

### Project-level

```
GET /api/v1/analytics/feedback/by-product?project_id={id}
GET /api/v1/analytics/feedback/by-service?project_id={id}
```

**Query parameters:** `project_id` (required), `feedback_type`, `date_from`, `date_to`

Returns a flat list of `{ product_id, total, grievances, suggestions, applause, inquiries, resolved, avg_resolution_hours }` rows, one per distinct product/service in the project.

### Org-level

```
GET /api/v1/analytics/org/{org_id}/by-product
GET /api/v1/analytics/org/{org_id}/by-service
```

Same structure but aggregates across all projects in the org.

### Platform-level (super admin)

```
GET /api/v1/analytics/platform/by-product
GET /api/v1/analytics/platform/by-service
```

**Optional filters:** `org_id`, `project_id`, `feedback_type`, `date_from`, `date_to`

---

## Error Reference

| Status | Body | Cause |
|--------|------|-------|
| 401 | `{"detail": {"error": "UNAUTHORISED"}}` | Missing or expired JWT |
| 403 | `{"detail": {"error": "FORBIDDEN"}}` | Insufficient role (need manager+ or platform admin) |
| 422 | `{"detail": [...]}` | Invalid query parameter type |
| 500 | `{"error": "INTERNAL_ERROR"}` | Database query failed; check analytics_service logs |

---

## Implementation Notes

### Implementation Rate Formula

```
implementation_rate = suggestions_implemented / total_suggestions × 100
```

A suggestion is counted as **implemented** if:
- `feedbacks.status = 'ACTIONED'`, **OR**
- `feedbacks.implemented_at IS NOT NULL`

Both conditions are checked via `POST /feedback/{id}/action-suggestion` which sets both fields atomically.

### Category Distribution vs. AI Themes

| | `/categories` | `/themes` |
|---|---|---|
| Source | Structured `category_def_id` from `feedback_category_defs` | Free-text descriptions + transcriptions |
| How assigned | By GRM officer or ML classifier | Groq LLM on-demand |
| Accuracy | Exact — enum categories | Approximate — natural language patterns |
| Speed | Instant SQL | ~2–5 seconds (LLM call) |
| Use case | Pie charts, filter chips | Insight cards, "what are people talking about?" |

### Uncategorised Bucket

Feedback with `category_def_id = NULL` is included in the `/categories` response as a single **"Uncategorised"** row (`category_id: null`). This bucket is typically the largest and represents feedback where no category was assigned. It cannot be drilled into by `category_id`; instead filter by `?status=SUBMITTED` in the `/feedback` endpoint to find unreviewed items.

### QR Scans (products only)

`qr_scans` in the product summary queries `verification_events.product_id`. This cross-database query gracefully returns `{scan_count: 0}` if the verification_db is unreachable. The analytics service and verification service must share a network for this to return live data.

### Paging

The `/feedback` endpoint returns `total` (overall count matching the filters) alongside the current page. Use this to render pagination controls:

```
pages = ceil(total / size)
```

---

## Seeded Test Data (Reference)

The following data was seeded during API testing on 2026-05-17 and can be used for further testing:

**Product:** `4ae4ecf5-22d0-4f86-8079-89a2e4e48b76`

| Type | Count | Notes |
|------|-------|-------|
| Grievance | 15 | 1 resolved (packaging issue), rest SUBMITTED |
| Suggestion | 2 | 1 ACTIONED (QR cap), 1 SUBMITTED (1L variant) |
| Applause | 1 | "Best water brand in Dar" |
| Inquiry | 1 | Bulk purchase question |

**Service:** `411da113-cb61-4819-9d11-af9ef08893c0`

| Type | Count | Notes |
|------|-------|-------|
| Grievance | 9 | 1 resolved (waiting time), 8 SUBMITTED |
| Suggestion | 4 | 1 ACTIONED (feedback kiosk), 3 SUBMITTED |
| Applause | 5 | Positive service recognition |
| Inquiry | 1 | General question |

**Department:** `699a2c9c-2cd8-4bda-93de-88c9aed3a861`

| Type | Count | Notes |
|------|-------|-------|
| Grievance | 7 | No response + other issues |
| Suggestion | 3 | 1 ACTIONED (digital portal) |
| Applause | 6 | Quick permit processing |
| Inquiry | 2 | General questions |
