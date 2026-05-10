# Riviwa — Employee Internal Feedback API Reference

> **Services:** `feedback_service` (port 8090) · `analytics_service` (port 8095)
> **Base URL:** `https://api.riviwa.com/api/v1`
> **Version:** 2.5.0 · **Added:** 2026-05-10
> **Source files:**
> - `feedback_service/api/v1/employee_feedback.py`
> - `feedback_service/models/employee_feedback.py`
> - `feedback_service/schemas/employee_feedback.py`
> - `feedback_service/services/employee_feedback_service.py`
> - `feedback_service/repositories/employee_feedback_repo.py`
> - `analytics_service/api/v1/employee_feedback_analytics.py`
> - `analytics_service/repositories/employee_feedback_analytics_repo.py`
> - **Migration:** `feedback_service/alembic/versions/2026-05-10_16-00_add_employee_feedbacks.py`

---

## Table of Contents

1. [Overview](#1-overview)
2. [How Employee Feedback Differs from Consumer GRM Feedback](#2-how-employee-feedback-differs-from-consumer-grm-feedback)
3. [Authentication & Authorization](#3-authentication--authorization)
4. [Tracking Number Format](#4-tracking-number-format)
5. [Enumerations](#5-enumerations)
   - 5.1 [feedback_type](#51-feedback_type)
   - 5.2 [category](#52-category)
   - 5.3 [status](#53-status)
6. [Submission Endpoints — `feedback_service`](#6-submission-endpoints--feedback_service)
   - 6.1 [POST /my/employee-feedback](#61-post-myemployee-feedback)
   - 6.2 [GET /my/employee-feedback](#62-get-myemployee-feedback)
   - 6.3 [GET /employee-feedback](#63-get-employee-feedback)
   - 6.4 [GET /employee-feedback/{id}](#64-get-employee-feedbackid)
   - 6.5 [PATCH /employee-feedback/{id}](#65-patch-employee-feedbackid)
7. [Analytics Endpoints — `analytics_service`](#7-analytics-endpoints--analytics_service)
   - 7.1 [GET /analytics/org/{org_id}/employee-feedback/summary](#71-get-analyticsorgorg_idemployee-feedbacksummary)
   - 7.2 [GET /analytics/org/{org_id}/employee-feedback/by-category](#72-get-analyticsorgorg_idemployee-feedbackby-category)
   - 7.3 [GET /analytics/org/{org_id}/employee-feedback/by-department](#73-get-analyticsorgorg_idemployee-feedbackby-department)
   - 7.4 [GET /analytics/org/{org_id}/employee-feedback/trend](#74-get-analyticsorgorg_idemployee-feedbacktrend)
   - 7.5 [GET /analytics/org/{org_id}/combined-performance](#75-get-analyticsorgorg_idcombined-performance)
8. [Database Schema](#8-database-schema)
9. [Error Responses](#9-error-responses)
10. [End-to-End Implementation Guide](#10-end-to-end-implementation-guide)

---

## 1. Overview

The Employee Internal Feedback feature gives every authenticated member of an organisation a private, structured channel to share feedback **about their own organisation** — independently of any GRM project or consumer complaint.

| Need | Solution |
|------|----------|
| Staff want to raise a workplace concern | `POST /my/employee-feedback` with `feedback_type=grievance` |
| Staff want to suggest an internal improvement | `feedback_type=suggestion` |
| Staff want to recognise good leadership or culture | `feedback_type=applause` |
| Staff want to ask an internal question | `feedback_type=inquiry` |
| Staff fear retaliation | `is_anonymous=true` — user identity is never stored |
| Managers want to see all internal feedback | `GET /employee-feedback` (admin list) |
| Managers want to respond to a specific item | `PATCH /employee-feedback/{id}` |
| Leadership wants internal sentiment analytics | `/analytics/org/{org_id}/employee-feedback/*` |
| Leadership wants the full org health picture | `GET /analytics/org/{org_id}/combined-performance` |

**10 endpoints total:** 5 on `feedback_service`, 5 on `analytics_service`.

---

## 2. How Employee Feedback Differs from Consumer GRM Feedback

| Dimension | Consumer GRM Feedback | Employee Internal Feedback |
|-----------|----------------------|---------------------------|
| **Who submits** | External citizens, community members | Organisation's own employees / members |
| **Table** | `feedbacks` | `employee_feedbacks` |
| **Tracking prefix** | `GRV-`, `SGG-`, `APP-`, `INQ-` | `EF-` |
| **Requires project** | Optional (org-level allowed) | Never — always org-scoped |
| **Lifecycle** | Full GRM flow: acknowledge → assign → escalate → resolve | Simple: submitted → acknowledged → resolved → closed |
| **Anonymous** | Yes (submitter_name omitted) | Yes (`employee_user_id` not stored at all) |
| **Categories** | GRM categories (compensation, land acquisition, safety hazard…) | Internal categories (management, culture, compensation…) |
| **Management response** | Formal GRM resolution with action records | Free-text `management_response` field |
| **Analytics** | Organisation / project / branch / grievance / SLA analytics | Employee summary / by-category / by-department / trend |
| **Combined view** | — | `/combined-performance` merges both sources |

---

## 3. Authentication & Authorization

All endpoints require a Bearer JWT in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Getting a token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "identifier": "staff@yourorg.com",
  "password": "YourPassword123!"
}
```

```json
{ "login_token": "eyJ..." }
```

```http
POST /api/v1/auth/login/verify-otp
Content-Type: application/json

{
  "login_token": "eyJ...",
  "otp_code": "123456"
}
```

```json
{ "access_token": "eyJ..." }
```

### Switching to org context (recommended)

Switching embeds `org_id` directly in the JWT. This means you do not need to pass `org_id` as a query parameter on submission endpoints.

```http
POST /api/v1/auth/switch-org
Authorization: Bearer <access_token>
Content-Type: application/json

{ "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf" }
```

```json
{
  "tokens": {
    "access_token": "eyJ..."
  }
}
```

### Role requirements per endpoint

| Endpoint group | Minimum role |
|----------------|-------------|
| `POST /my/employee-feedback` | `member` (any org member) |
| `GET /my/employee-feedback` | `member` |
| `GET /employee-feedback` | `manager` |
| `GET /employee-feedback/{id}` | `manager` |
| `PATCH /employee-feedback/{id}` | `manager` |
| All analytics endpoints | `member` (own org only) |
| All analytics endpoints (other org) | Platform `admin` / `super_admin` |

---

## 4. Tracking Number Format

Every employee feedback submission receives a unique tracking number in the format:

```
EF-{YEAR}-{SEQUENCE}
```

Examples: `EF-2026-0001`, `EF-2026-0013`

The sequence is **org-global** (not per-org) and resets each calendar year. Tracking numbers are stable identifiers — they do not change when status is updated.

---

## 5. Enumerations

### 5.1 `feedback_type`

| Value | When to use |
|-------|-------------|
| `grievance` | A problem, complaint, or unacceptable situation |
| `suggestion` | An idea for improvement |
| `applause` | Recognition of something done well |
| `inquiry` | A question seeking clarification or information |

### 5.2 `category`

| Value | Description |
|-------|-------------|
| `working_conditions` | Physical workspace, equipment, temperature, cleanliness |
| `management` | Day-to-day management practices, micromanagement, support |
| `culture` | Organisational values, inclusivity, team spirit, morale |
| `compensation` | Salary, bonuses, allowances, contractual pay obligations |
| `tools_resources` | Software, hardware, systems, internet connectivity |
| `communication` | Internal comms, transparency, meeting effectiveness |
| `career_growth` | Training, promotion, mentorship, development opportunities |
| `safety` | Physical safety, psychological safety, harassment |
| `team_dynamics` | Collaboration, inter-team conflict, cooperation |
| `leadership` | Senior leadership direction, vision, decision-making |
| `benefits` | Leave, health insurance, transport, meals, perks |
| `other` | Anything not covered by the above |

### 5.3 `status`

| Value | Meaning | Set by |
|-------|---------|--------|
| `submitted` | Newly created, awaiting admin attention | System (auto) |
| `acknowledged` | Admin has seen and logged the item | Admin via `PATCH` |
| `resolved` | Issue addressed or response provided | Admin via `PATCH` |
| `closed` | No further action required | Admin via `PATCH` |

> When `management_response` is provided in a `PATCH` and the current status is `submitted`, status automatically advances to `acknowledged`.

---

## 6. Submission Endpoints — `feedback_service`

Base path: `https://api.riviwa.com/api/v1`

---

### 6.1 `POST /my/employee-feedback`

Submit internal feedback about your organisation.

**Auth:** Any authenticated org member (`member` or higher).
**Org resolution:** `org_id` is taken from the JWT. Switch to the target org before calling (see §3).

#### Request body

```json
{
  "feedback_type": "grievance",
  "category": "working_conditions",
  "subject": "AC broken in HQ for 3 weeks",
  "description": "The AC units in the main office have been broken for 3 weeks. Staff are working in extreme heat which is affecting productivity and health.",
  "is_anonymous": false,
  "department_id": "17865dce-9c61-484c-a9dc-8d9696315904",
  "branch_id": "1ffae914-af34-436b-8452-32a05eef047b"
}
```

#### Request fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `feedback_type` | string | **Yes** | `grievance` \| `suggestion` \| `applause` \| `inquiry` |
| `category` | string | **Yes** | See [§5.2](#52-category) for all values |
| `description` | string | **Yes** | Full description — minimum 10 characters |
| `subject` | string | No | Short summary — max 500 characters. Auto-generated if omitted. |
| `is_anonymous` | boolean | No | Default `false`. When `true`, your user ID is **never stored**. |
| `department_id` | UUID | No | Your department's UUID (from `auth_service`). Enables department-level analytics. |
| `branch_id` | UUID | No | Your branch's UUID (from `auth_service`). Enables branch-level analytics. |

> **Anonymous submissions:** When `is_anonymous=true`, the `employee_user_id` field is set to `null` at write time. The submitting user's identity cannot be recovered even by platform admins. Anonymous submissions do not appear in `GET /my/employee-feedback` because there is no user ID to link them back to.

#### Response `201 Created`

```json
{
  "feedback_id": "f8a1e395-f8c7-40a4-acb2-e3311d0b7101",
  "tracking_number": "EF-2026-0001",
  "feedback_type": "grievance",
  "status": "submitted",
  "message": "Your feedback has been submitted. Thank you for helping improve our organisation."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `feedback_id` | UUID | Database primary key — use for `PATCH` |
| `tracking_number` | string | Human-readable reference (`EF-YYYY-NNNN`) |
| `feedback_type` | string | Echoed back from request |
| `status` | string | Always `submitted` on creation |
| `message` | string | Confirmation message suitable for display to the user |

#### Example — anonymous suggestion with branch context

```json
{
  "feedback_type": "suggestion",
  "category": "career_growth",
  "subject": "Internal job postings before external hiring",
  "description": "Three senior roles were filled externally in the past 6 months. Existing qualified staff were not given the opportunity to apply first. An internal-first posting policy would significantly improve retention.",
  "is_anonymous": true,
  "branch_id": "a1e87f8c-f578-4498-ac46-1f3b7ba034e1"
}
```

#### Example — applause with department + branch

```json
{
  "feedback_type": "applause",
  "category": "leadership",
  "subject": "New MD is making a real difference",
  "description": "The new managing directors open-door approach and monthly all-hands meetings have genuinely improved morale. Staff feel heard for the first time.",
  "is_anonymous": false,
  "department_id": "afd5b4e2-10f5-4874-b1da-248a74091805",
  "branch_id": "1ffae914-af34-436b-8452-32a05eef047b"
}
```

---

### 6.2 `GET /my/employee-feedback`

List your own employee feedback submissions. Anonymous submissions are excluded because there is no user ID link.

**Auth:** Any authenticated org member.

#### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | `0` | Pagination offset |
| `limit` | integer | `50` | Page size — max `200` |

#### Response `200 OK`

```json
{
  "total": 10,
  "skip": 0,
  "limit": 50,
  "items": [
    {
      "id": "168f77cc-72ca-4575-abe0-1a04a440ee5d",
      "tracking_number": "EF-2026-0005",
      "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
      "feedback_type": "suggestion",
      "category": "tools_resources",
      "subject": "Laptops instead of desktops would enable hybrid work",
      "description": "Providing laptops would allow staff to work remotely during network outages and enable hybrid arrangements that competitors already offer.",
      "is_anonymous": false,
      "employee_user_id": "5183174a-bcad-4e68-bf06-700d1f1260dc",
      "employee_name": null,
      "department_id": null,
      "branch_id": null,
      "status": "submitted",
      "management_response": null,
      "responded_at": null,
      "responded_by_user_id": null,
      "submitted_at": "2026-05-10T16:20:54.510855",
      "updated_at": "2026-05-10T16:20:54.510878"
    }
  ]
}
```

Items are ordered by `submitted_at DESC` (newest first).

---

### 6.3 `GET /employee-feedback`

List all employee feedback submissions for the organisation. Org admins can see all records including anonymous ones (but cannot de-anonymise — `employee_user_id` is `null`).

**Auth:** `manager`, `admin`, or `owner`. Platform admins can pass `org_id` query param to access any org.

#### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `feedback_type` | string | — | Filter: `grievance` \| `suggestion` \| `applause` \| `inquiry` |
| `category` | string | — | Filter by category slug (see §5.2) |
| `status` | string | — | Filter: `submitted` \| `acknowledged` \| `resolved` \| `closed` |
| `is_anonymous` | boolean | — | `true` = only anonymous, `false` = only identified |
| `branch_id` | UUID | — | Filter to a specific branch |
| `department_id` | UUID | — | Filter to a specific department |
| `skip` | integer | `0` | Pagination offset |
| `limit` | integer | `50` | Page size — max `200` |
| `org_id` | UUID | — | Platform admins only. Omit to use the JWT org. |

#### Example requests

```http
GET /api/v1/employee-feedback
Authorization: Bearer <token>
```

```http
GET /api/v1/employee-feedback?feedback_type=grievance&is_anonymous=false&limit=20
Authorization: Bearer <token>
```

```http
GET /api/v1/employee-feedback?branch_id=ba6eea7d-e946-465e-8180-2b99d479ea49&status=submitted
Authorization: Bearer <token>
```

#### Response `200 OK`

```json
{
  "total": 13,
  "skip": 0,
  "limit": 50,
  "items": [
    {
      "id": "08da9930-4461-4ea2-b96a-14c6241054f6",
      "tracking_number": "EF-2026-0003",
      "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
      "feedback_type": "applause",
      "category": "leadership",
      "subject": "New MD is making a real difference",
      "description": "The new MDs open-door approach and monthly all-hands meetings have genuinely improved morale. Staff feel heard.",
      "is_anonymous": true,
      "employee_user_id": null,
      "employee_name": null,
      "department_id": null,
      "branch_id": null,
      "status": "submitted",
      "management_response": null,
      "responded_at": null,
      "responded_by_user_id": null,
      "submitted_at": "2026-05-10T16:20:54.219002",
      "updated_at": "2026-05-10T16:20:54.219019"
    }
  ]
}
```

> Note: `employee_user_id` is `null` for anonymous submissions. This is permanent — it cannot be recovered.

---

### 6.4 `GET /employee-feedback/{id}`

Retrieve a single employee feedback record by its UUID.

**Auth:** `manager`, `admin`, or `owner` of the same org.

#### Path parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | The `feedback_id` (UUID) returned on submission |

#### Example request

```http
GET /api/v1/employee-feedback/f8a1e395-f8c7-40a4-acb2-e3311d0b7101
Authorization: Bearer <token>
```

#### Response `200 OK`

```json
{
  "id": "f8a1e395-f8c7-40a4-acb2-e3311d0b7101",
  "tracking_number": "EF-2026-0001",
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "feedback_type": "grievance",
  "category": "working_conditions",
  "subject": "AC broken in HQ for 3 weeks",
  "description": "The AC units in the main office have been broken for 3 weeks. Staff are working in extreme heat affecting productivity and health.",
  "is_anonymous": false,
  "employee_user_id": "5183174a-bcad-4e68-bf06-700d1f1260dc",
  "employee_name": null,
  "department_id": null,
  "branch_id": null,
  "status": "acknowledged",
  "management_response": "Thank you for reporting this. Maintenance request logged — AC will be repaired within 5 business days.",
  "responded_at": "2026-05-10T16:26:57.615649",
  "responded_by_user_id": "5183174a-bcad-4e68-bf06-700d1f1260dc",
  "submitted_at": "2026-05-10T16:20:53.869621",
  "updated_at": "2026-05-10T16:26:57.615686"
}
```

#### Response fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `tracking_number` | string | `EF-YYYY-NNNN` human-readable reference |
| `org_id` | UUID | Organisation this feedback belongs to |
| `feedback_type` | string | `grievance` \| `suggestion` \| `applause` \| `inquiry` |
| `category` | string | Category slug (see §5.2) |
| `subject` | string \| null | Short summary |
| `description` | string | Full text of the feedback |
| `is_anonymous` | boolean | Whether the submitter requested anonymity |
| `employee_user_id` | UUID \| null | `null` when anonymous or not yet resolved |
| `employee_name` | string \| null | Display name — currently `null` (resolved from auth_service in future) |
| `department_id` | UUID \| null | Department UUID if provided at submission |
| `branch_id` | UUID \| null | Branch UUID if provided at submission |
| `status` | string | Current lifecycle status |
| `management_response` | string \| null | Official management response |
| `responded_at` | datetime \| null | When management first responded |
| `responded_by_user_id` | UUID \| null | User ID of the admin who responded |
| `submitted_at` | datetime | Submission timestamp (UTC) |
| `updated_at` | datetime | Last modification timestamp (UTC) |

---

### 6.5 `PATCH /employee-feedback/{id}`

Update the status of an employee feedback item and/or add a management response. Partial updates — only supply the fields you want to change.

**Auth:** `manager`, `admin`, or `owner` of the same org.

#### Path parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | The `feedback_id` to update |

#### Request body

All fields are optional. Supply only the fields you want to change.

```json
{
  "status": "acknowledged",
  "management_response": "Thank you for raising this. We have logged a maintenance request and will update you within 5 business days."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | New status: `submitted` \| `acknowledged` \| `resolved` \| `closed` |
| `management_response` | string | Official response visible to the submitter (if they check their item). Providing this auto-advances status from `submitted` → `acknowledged`. |

#### Auto-advance rule

```
if management_response is provided AND current status == "submitted"
  → status is automatically set to "acknowledged"
```

This means you can write a response without explicitly setting `status`, and the system will still acknowledge the item.

#### Example — acknowledge only

```json
{
  "status": "acknowledged"
}
```

#### Example — respond and resolve

```json
{
  "status": "resolved",
  "management_response": "The night shift allowance arrears have been processed in the May payroll. Staff will see the corrected amount plus all outstanding months from January. We apologise for the delay."
}
```

#### Example — close without response

```json
{
  "status": "closed"
}
```

#### Response `200 OK`

Returns the full updated feedback record (same schema as `GET /employee-feedback/{id}`).

```json
{
  "id": "f8a1e395-f8c7-40a4-acb2-e3311d0b7101",
  "tracking_number": "EF-2026-0001",
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "feedback_type": "grievance",
  "category": "working_conditions",
  "subject": "AC broken in HQ for 3 weeks",
  "description": "The AC units in the main office have been broken for 3 weeks. Staff are working in extreme heat affecting productivity and health.",
  "is_anonymous": false,
  "employee_user_id": "5183174a-bcad-4e68-bf06-700d1f1260dc",
  "employee_name": null,
  "department_id": null,
  "branch_id": null,
  "status": "resolved",
  "management_response": "The night shift allowance arrears have been processed in the May payroll.",
  "responded_at": "2026-05-10T16:34:33.364208",
  "responded_by_user_id": "5183174a-bcad-4e68-bf06-700d1f1260dc",
  "submitted_at": "2026-05-10T16:20:53.869621",
  "updated_at": "2026-05-10T16:34:33.364208"
}
```

---

## 7. Analytics Endpoints — `analytics_service`

Base path: `https://api.riviwa.com/api/v1/analytics/org/{org_id}`

All analytics endpoints:
- **Auth:** Any org member (own org) or platform admin (any org).
- Accept `date_from` and `date_to` query params (`YYYY-MM-DD`). Both are optional. When omitted, all-time data is returned.
- Query `feedback_db` directly — no real-time cross-service calls.

---

### 7.1 `GET /analytics/org/{org_id}/employee-feedback/summary`

Overall employee feedback totals and rates for the organisation.

#### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | date | `YYYY-MM-DD` — start of window (inclusive) |
| `date_to` | date | `YYYY-MM-DD` — end of window (inclusive) |

#### Example requests

```http
GET /api/v1/analytics/org/163f4a76-b76b-449b-99e8-497388c8f0cf/employee-feedback/summary
Authorization: Bearer <token>
```

```http
GET /api/v1/analytics/org/163f4a76-b76b-449b-99e8-497388c8f0cf/employee-feedback/summary?date_from=2026-05-01&date_to=2026-05-31
Authorization: Bearer <token>
```

#### Response `200 OK`

```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "date_from": null,
  "date_to": null,
  "total": 13,
  "grievances": 5,
  "suggestions": 4,
  "applause": 3,
  "inquiries": 1,
  "anonymous_count": 3,
  "pending": 11,
  "acknowledged": 1,
  "resolved": 1,
  "closed": 0,
  "applause_rate": "23.1"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | All employee feedback in the window |
| `grievances` | integer | Count of `feedback_type=grievance` |
| `suggestions` | integer | Count of `feedback_type=suggestion` |
| `applause` | integer | Count of `feedback_type=applause` |
| `inquiries` | integer | Count of `feedback_type=inquiry` |
| `anonymous_count` | integer | Submissions with `is_anonymous=true` |
| `pending` | integer | Items still in `submitted` status |
| `acknowledged` | integer | Items in `acknowledged` status |
| `resolved` | integer | Items in `resolved` status |
| `closed` | integer | Items in `closed` status |
| `applause_rate` | string | `applause / total × 100`, rounded to 1 decimal place. Primary sentiment indicator. |

---

### 7.2 `GET /analytics/org/{org_id}/employee-feedback/by-category`

Employee feedback broken down by category, sorted by total volume descending.

#### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | date | `YYYY-MM-DD` |
| `date_to` | date | `YYYY-MM-DD` |

#### Example request

```http
GET /api/v1/analytics/org/163f4a76-b76b-449b-99e8-497388c8f0cf/employee-feedback/by-category
Authorization: Bearer <token>
```

#### Response `200 OK`

```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "date_from": null,
  "date_to": null,
  "items": [
    {
      "category": "compensation",
      "total": 2,
      "grievances": 2,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "category": "tools_resources",
      "total": 2,
      "grievances": 1,
      "suggestions": 1,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "category": "management",
      "total": 2,
      "grievances": 1,
      "suggestions": 1,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "category": "culture",
      "total": 1,
      "grievances": 0,
      "suggestions": 0,
      "applause": 1,
      "inquiries": 0,
      "applause_rate": "100.0"
    },
    {
      "category": "leadership",
      "total": 1,
      "grievances": 0,
      "suggestions": 0,
      "applause": 1,
      "inquiries": 0,
      "applause_rate": "100.0"
    },
    {
      "category": "safety",
      "total": 1,
      "grievances": 0,
      "suggestions": 0,
      "applause": 1,
      "inquiries": 0,
      "applause_rate": "100.0"
    },
    {
      "category": "benefits",
      "total": 1,
      "grievances": 0,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 1,
      "applause_rate": "0.0"
    },
    {
      "category": "working_conditions",
      "total": 1,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "category": "career_growth",
      "total": 1,
      "grievances": 0,
      "suggestions": 1,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "category": "communication",
      "total": 1,
      "grievances": 0,
      "suggestions": 1,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    }
  ]
}
```

Each `items` entry:

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Category slug |
| `total` | integer | Total submissions in this category |
| `grievances` | integer | Grievance count |
| `suggestions` | integer | Suggestion count |
| `applause` | integer | Applause count |
| `inquiries` | integer | Inquiry count |
| `applause_rate` | string | `applause / total × 100` for this category |

> **Insight use:** categories with high grievance counts and zero applause point to systemic problem areas. Categories with high `applause_rate` confirm what the org is doing well.

---

### 7.3 `GET /analytics/org/{org_id}/employee-feedback/by-department`

Employee feedback broken down by `(department_id, branch_id)` combination. Items with no department or branch (org-level submissions) appear with `null` values.

#### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | date | `YYYY-MM-DD` |
| `date_to` | date | `YYYY-MM-DD` |

#### Example request

```http
GET /api/v1/analytics/org/163f4a76-b76b-449b-99e8-497388c8f0cf/employee-feedback/by-department
Authorization: Bearer <token>
```

#### Response `200 OK`

```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "date_from": null,
  "date_to": null,
  "items": [
    {
      "department_id": null,
      "branch_id": null,
      "total": 5,
      "grievances": 2,
      "suggestions": 2,
      "applause": 1,
      "inquiries": 0,
      "applause_rate": "20.0"
    },
    {
      "department_id": "17f96d55-6590-42e6-837f-48db490fcd96",
      "branch_id": "1ffae914-af34-436b-8452-32a05eef047b",
      "total": 1,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "department_id": "17f96d55-6590-42e6-837f-48db490fcd96",
      "branch_id": "a1e87f8c-f578-4498-ac46-1f3b7ba034e1",
      "total": 1,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "department_id": "afd5b4e2-10f5-4874-b1da-248a74091805",
      "branch_id": "1ffae914-af34-436b-8452-32a05eef047b",
      "total": 1,
      "grievances": 0,
      "suggestions": 0,
      "applause": 1,
      "inquiries": 0,
      "applause_rate": "100.0"
    },
    {
      "department_id": "17865dce-9c61-484c-a9dc-8d9696315904",
      "branch_id": "1ffae914-af34-436b-8452-32a05eef047b",
      "total": 1,
      "grievances": 0,
      "suggestions": 1,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "department_id": null,
      "branch_id": "1ffae914-af34-436b-8452-32a05eef047b",
      "total": 1,
      "grievances": 0,
      "suggestions": 0,
      "applause": 1,
      "inquiries": 0,
      "applause_rate": "100.0"
    },
    {
      "department_id": null,
      "branch_id": "a1e87f8c-f578-4498-ac46-1f3b7ba034e1",
      "total": 1,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "department_id": null,
      "branch_id": "ba6eea7d-e946-465e-8180-2b99d479ea49",
      "total": 1,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    },
    {
      "department_id": "afd5b4e2-10f5-4874-b1da-248a74091805",
      "branch_id": "ba6eea7d-e946-465e-8180-2b99d479ea49",
      "total": 1,
      "grievances": 0,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 1,
      "applause_rate": "0.0"
    }
  ]
}
```

Each `items` entry:

| Field | Type | Description |
|-------|------|-------------|
| `department_id` | UUID \| null | Department UUID, or `null` for org/branch-only submissions |
| `branch_id` | UUID \| null | Branch UUID, or `null` for org-level submissions |
| `total` | integer | Total submissions for this combination |
| `grievances` | integer | |
| `suggestions` | integer | |
| `applause` | integer | |
| `inquiries` | integer | |
| `applause_rate` | string | |

> Results are sorted by `total` descending. To display human-readable names, resolve department and branch UUIDs against `auth_service` (`GET /api/v1/orgs/{org_id}/departments` and `/branches`).

---

### 7.4 `GET /analytics/org/{org_id}/employee-feedback/trend`

Time series of employee feedback volume, broken down by type. Use for charts showing how internal sentiment is changing over time.

#### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `granularity` | string | `day` | `hour` \| `day` \| `week` \| `month` |
| `date_from` | date | — | `YYYY-MM-DD` |
| `date_to` | date | — | `YYYY-MM-DD` |

#### Example requests

```http
GET /api/v1/analytics/org/163f4a76-b76b-449b-99e8-497388c8f0cf/employee-feedback/trend?granularity=day&date_from=2026-05-01
Authorization: Bearer <token>
```

```http
GET /api/v1/analytics/org/163f4a76-b76b-449b-99e8-497388c8f0cf/employee-feedback/trend?granularity=month
Authorization: Bearer <token>
```

#### Response `200 OK`

```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "granularity": "day",
  "date_from": "2026-05-01",
  "date_to": null,
  "items": [
    {
      "period": "2026-05-10T00:00:00",
      "total": 13,
      "grievances": 5,
      "suggestions": 4,
      "applause": 3,
      "inquiries": 1
    }
  ]
}
```

Each `items` entry:

| Field | Type | Description |
|-------|------|-------------|
| `period` | datetime | Start of the bucket (UTC). For `day`, this is midnight of that day. For `month`, the first of the month. |
| `total` | integer | All submissions in this period |
| `grievances` | integer | |
| `suggestions` | integer | |
| `applause` | integer | |
| `inquiries` | integer | |

> Periods with zero submissions are **not included** in the response. Build a complete time axis client-side by filling gaps with zeros.

---

### 7.5 `GET /analytics/org/{org_id}/combined-performance`

The flagship analytics endpoint. Merges **consumer GRM feedback** (from the `feedbacks` table) with **employee internal feedback** (from `employee_feedbacks`) into a single organisation health view.

Use this as the primary KPI dashboard for org leadership.

#### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | date | `YYYY-MM-DD` — applies to both consumer and employee data |
| `date_to` | date | `YYYY-MM-DD` |

#### Example request

```http
GET /api/v1/analytics/org/163f4a76-b76b-449b-99e8-497388c8f0cf/combined-performance
Authorization: Bearer <token>
```

```http
GET /api/v1/analytics/org/163f4a76-b76b-449b-99e8-497388c8f0cf/combined-performance?date_from=2026-01-01&date_to=2026-05-31
Authorization: Bearer <token>
```

#### Response `200 OK`

```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "date_from": null,
  "date_to": null,
  "consumer": {
    "total": 53,
    "grievances": 27,
    "suggestions": 10,
    "applause": 10,
    "inquiries": 6,
    "resolved": 0,
    "open_count": 53,
    "applause_rate": "18.9",
    "resolution_rate": "0.0",
    "avg_resolution_hours": null
  },
  "employee": {
    "total": 13,
    "grievances": 5,
    "suggestions": 4,
    "applause": 3,
    "inquiries": 1,
    "anonymous_count": 3,
    "pending": 11,
    "acknowledged": 1,
    "resolved": 1,
    "closed": 0,
    "applause_rate": "23.1",
    "by_category": [
      {
        "category": "compensation",
        "total": 2,
        "grievances": 2,
        "suggestions": 0,
        "applause": 0,
        "inquiries": 0,
        "applause_rate": "0.0"
      },
      {
        "category": "tools_resources",
        "total": 2,
        "grievances": 1,
        "suggestions": 1,
        "applause": 0,
        "inquiries": 0,
        "applause_rate": "0.0"
      }
    ]
  },
  "combined": {
    "total": 66,
    "applause": 13,
    "applause_rate": 19.7,
    "health_score": "needs_improvement"
  }
}
```

#### Response structure

**`consumer` object** — aggregated from the `feedbacks` table:

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total GRM feedback submissions from the public |
| `grievances` | integer | |
| `suggestions` | integer | |
| `applause` | integer | |
| `inquiries` | integer | |
| `resolved` | integer | Count with status in `RESOLVED, ACTIONED, NOTED, DISMISSED, CLOSED` |
| `open_count` | integer | Count with status in `SUBMITTED, ACKNOWLEDGED, IN_REVIEW, ESCALATED, APPEALED` |
| `applause_rate` | string | `applause / total × 100` |
| `resolution_rate` | string | `resolved / total × 100` |
| `avg_resolution_hours` | number \| null | Mean hours from `submitted_at` to `resolved_at`. `null` if no resolved items. |

**`employee` object** — aggregated from the `employee_feedbacks` table:

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total internal employee feedback |
| `grievances` | integer | |
| `suggestions` | integer | |
| `applause` | integer | |
| `inquiries` | integer | |
| `anonymous_count` | integer | Count submitted anonymously |
| `pending` | integer | Items in `submitted` status |
| `acknowledged` | integer | Items in `acknowledged` status |
| `resolved` | integer | Items in `resolved` status |
| `closed` | integer | Items in `closed` status |
| `applause_rate` | string | Internal applause rate |
| `by_category` | array | Per-category breakdown (same structure as §7.2 items) |

**`combined` object** — computed from both sources:

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | `consumer.total + employee.total` |
| `applause` | integer | `consumer.applause + employee.applause` |
| `applause_rate` | number | `combined_applause / combined_total × 100` — the primary org health metric |
| `health_score` | string | Qualitative score (see table below) |

#### Health score bands

| `health_score` | Combined applause rate | Interpretation |
|----------------|----------------------|----------------|
| `excellent` | ≥ 70 % | Strong positive signal from both external and internal stakeholders |
| `good` | 50 % – 69 % | More positive than negative — continue monitoring |
| `fair` | 30 % – 49 % | Mixed signals — investigate category breakdowns |
| `needs_improvement` | < 30 % | Significant dissatisfaction from external or internal sources |

> **Calculation note:** `applause_rate` is computed on the combined total, not as an average of the two individual rates. This gives appropriate weight to each source based on volume.

---

## 8. Database Schema

Table: `employee_feedbacks` in `feedback_db` (PostgreSQL 15).

**Created by migration:** `f1a2b3c4d5e6` (`2026-05-10_16-00_add_employee_feedbacks.py`)

```sql
CREATE TABLE employee_feedbacks (
    id                    UUID         PRIMARY KEY,
    tracking_number       VARCHAR(20)  NOT NULL UNIQUE,
    org_id                UUID         NOT NULL,
    feedback_type         VARCHAR(20)  NOT NULL,
    category              VARCHAR(40)  NOT NULL,
    subject               VARCHAR(500),
    description           TEXT         NOT NULL,
    is_anonymous          BOOLEAN      NOT NULL DEFAULT false,
    employee_user_id      UUID,
    employee_name         VARCHAR(255),
    department_id         UUID,
    branch_id             UUID,
    status                VARCHAR(20)  NOT NULL DEFAULT 'submitted',
    management_response   TEXT,
    responded_at          TIMESTAMP,
    responded_by_user_id  UUID,
    submitted_at          TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at            TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE INDEX ix_employee_feedbacks_org_id           ON employee_feedbacks (org_id);
CREATE INDEX ix_employee_feedbacks_feedback_type    ON employee_feedbacks (feedback_type);
CREATE INDEX ix_employee_feedbacks_category         ON employee_feedbacks (category);
CREATE INDEX ix_employee_feedbacks_status           ON employee_feedbacks (status);
CREATE INDEX ix_employee_feedbacks_is_anonymous     ON employee_feedbacks (is_anonymous);
CREATE INDEX ix_employee_feedbacks_employee_user_id ON employee_feedbacks (employee_user_id);
CREATE INDEX ix_employee_feedbacks_department_id    ON employee_feedbacks (department_id);
CREATE INDEX ix_employee_feedbacks_branch_id        ON employee_feedbacks (branch_id);
CREATE UNIQUE INDEX ix_employee_feedbacks_tracking_number ON employee_feedbacks (tracking_number);
```

> The table has **no foreign keys** by design. `org_id`, `department_id`, `branch_id`, and `employee_user_id` are soft links to `auth_service` entities — this maintains service isolation and allows feedback to survive org restructuring.

---

## 9. Error Responses

All error responses follow the standard Riviwa error envelope:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description.",
  "details": []
}
```

| HTTP | `error` code | When |
|------|-------------|------|
| `401 Unauthorized` | `UNAUTHORIZED` | Missing or no `Authorization` header |
| `401 Unauthorized` | `TOKEN_EXPIRED` | JWT has expired |
| `401 Unauthorized` | `TOKEN_INVALID` | JWT signature invalid or malformed |
| `403 Forbidden` | `FORBIDDEN` | Valid token but insufficient role (e.g. `member` hitting an admin endpoint) |
| `403 Forbidden` | `FORBIDDEN` | No org context in JWT — switch to an org first |
| `404 Not Found` | `NOT_FOUND` | `{id}` does not exist or belongs to a different org |
| `422 Unprocessable Entity` | `VALIDATION_ERROR` | Request body fails schema validation |
| `500 Internal Server Error` | `INTERNAL_ERROR` | Unexpected server error |

#### Common validation errors

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid request.",
  "details": [
    { "field": "body.feedback_type", "message": "Input should be 'grievance', 'suggestion', 'applause' or 'inquiry'" },
    { "field": "body.description", "message": "String should have at least 10 characters" }
  ]
}
```

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid request.",
  "details": [
    { "field": "body.category", "message": "Input should be 'working_conditions', 'management', 'culture', 'compensation', 'tools_resources', 'communication', 'career_growth', 'safety', 'team_dynamics', 'leadership', 'benefits' or 'other'" }
  ]
}
```

---

## 10. End-to-End Implementation Guide

### Step 1 — Authenticate

```http
POST /api/v1/auth/login
{ "identifier": "staff@yourorg.com", "password": "..." }

POST /api/v1/auth/login/verify-otp
{ "login_token": "...", "otp_code": "123456" }

POST /api/v1/auth/switch-org
{ "org_id": "your-org-uuid" }
→ use tokens.access_token for all subsequent calls
```

### Step 2 — Submit employee feedback

```http
POST /api/v1/my/employee-feedback
Authorization: Bearer <org_token>
Content-Type: application/json

{
  "feedback_type": "grievance",
  "category": "compensation",
  "subject": "Night shift allowance not paid for 4 months",
  "description": "Technical staff on night shifts in Arusha have not received the contractual night shift allowance since January 2026. HR says it is a payroll system issue but nothing has been corrected despite multiple follow-ups.",
  "is_anonymous": true,
  "department_id": "17f96d55-6590-42e6-837f-48db490fcd96",
  "branch_id": "a1e87f8c-f578-4498-ac46-1f3b7ba034e1"
}
```

### Step 3 — Admin views the list (filtered)

```http
GET /api/v1/employee-feedback?feedback_type=grievance&status=submitted
Authorization: Bearer <manager_token>
```

### Step 4 — Admin responds

```http
PATCH /api/v1/employee-feedback/d03e2c2f-dcce-4bfd-b8ef-1f9545accbaf
Authorization: Bearer <manager_token>
Content-Type: application/json

{
  "status": "resolved",
  "management_response": "The night shift allowance arrears have been corrected in the May payroll. All outstanding months from January have been included. We apologise for the delay and have put controls in place to prevent recurrence."
}
```

### Step 5 — Leadership views combined performance dashboard

```http
GET /api/v1/analytics/org/163f4a76-b76b-449b-99e8-497388c8f0cf/combined-performance?date_from=2026-01-01
Authorization: Bearer <admin_token>
```

Interpret the response:

| Signal | Action |
|--------|--------|
| `combined.health_score = "needs_improvement"` | Review top grievance categories immediately |
| `employee.applause_rate` significantly below `consumer.applause_rate` | Internal culture issue — external perception better than internal reality |
| `employee.applause_rate` significantly above `consumer.applause_rate` | Staff motivated but delivery problems — check consumer grievance categories |
| `employee.anonymous_count` is high relative to total | Staff fear retaliation — investigate management safety |
| `consumer.resolution_rate` is low | GRM team capacity or process problem |

---

*Riviwa Employee Internal Feedback API — v2.5.0 — 2026-05-10*
