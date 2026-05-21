# Riviwa Staff Performance API Reference

**Base URL:** `https://api.riviwa.com/api/v1`  
**Auth:** `Authorization: Bearer <access_token>` (JWT, org admin role required)  
**Tested:** 2026-05-21 · Yas Tanzania org `163f4a76-b76b-449b-99e8-497388c8f0cf`

---

## Table of Contents

| # | Service | Endpoint | Purpose |
|---|---------|----------|---------|
| 1 | staff | `GET /staff/analytics/overview` | Staff count by status + departments |
| 2 | staff | `GET /staff/analytics/verifications` | Verification scan stats |
| 3 | staff | `GET /staff/analytics/feedback` | Customer feedback per staff member |
| 4 | staff | `GET /staff/analytics/fraud-reports` | Fraud report counts |
| 5 | analytics | `GET /analytics/staff/committee-performance` | Committee resolution metrics |
| 6 | analytics | `GET /analytics/staff/last-logins` | Last login + 24h login count per officer |
| 7 | analytics | `GET /analytics/staff/unread-assigned` | Officers with unread assigned feedback |
| 8 | analytics | `GET /analytics/staff/login-not-read` | Active today but not processing queue |
| 9 | analytics | `GET /analytics/org/{org_id}/staff-performance` | Per-staff queue timing metrics |
| 10 | analytics | `GET /analytics/org/{org_id}/staff-duty` | Duty sessions log |
| 11 | analytics | `GET /analytics/org/{org_id}/waiting-vs-feedback` | Wait time vs. complaint correlation |
| 12 | analytics | `GET /analytics/org/{org_id}/feedback-timing` | Hour×day feedback heatmap |
| 13 | analytics | `GET /analytics/org/{org_id}/employee-feedback/summary` | Internal employee feedback totals |
| 14 | analytics | `GET /analytics/org/{org_id}/employee-feedback/by-category` | Employee feedback by category |
| 15 | analytics | `GET /analytics/org/{org_id}/employee-feedback/by-department` | Employee feedback by department |
| 16 | analytics | `GET /analytics/org/{org_id}/employee-feedback/trend` | Employee feedback time series |
| 17 | analytics | `GET /analytics/org/{org_id}/combined-performance` | Unified org health score |
| 18 | waiting | `GET /waiting/analytics/dashboard` | Live queue + throughput dashboard |
| 19 | waiting | `GET /waiting/analytics/staff-duty` | Queue duty sessions |
| 20 | waiting | `GET /waiting/analytics/by-period` | Wait/service times over time |
| 21 | waiting | `GET /waiting/analytics/by-service-point` | Per-service-point timing |
| 22 | auth | `GET /orgs/{org_id}/members` | List org members with roles |

---

## staff_service Endpoints

### 1. `GET /staff/analytics/overview`

Staff totals by employment status and department breakdown for the caller's org.

**Auth:** org admin/owner or platform admin  
**Params:** none

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "total": 8,
  "active": 6,
  "suspended": 1,
  "terminated": 1,
  "on_leave": 0,
  "departments": [
    { "department": "Billing and Payments", "count": 1 },
    { "department": "Customer Care",        "count": 1 },
    { "department": "Network Operations",   "count": 1 },
    { "department": "Sales and Marketing",  "count": 1 },
    { "department": "Technical Support",    "count": 1 },
    { "department": "YasPesa Agency",       "count": 1 }
  ]
}
```

---

### 2. `GET /staff/analytics/verifications`

Verification scan stats: total scans, results breakdown (VALID/SUSPENDED/TERMINATED), and daily counts for the last 30 days.

**Auth:** org admin/owner  
**Params:** none

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "total": 38,
  "by_result": {
    "VALID": 34,
    "SUSPENDED": 3,
    "TERMINATED": 1
  },
  "by_day": [
    { "date": "2026-05-10", "count": 38 }
  ]
}
```

---

### 3. `GET /staff/analytics/feedback`

Customer feedback statistics per staff member: total feedback count, breakdown by type, applause rate.

**Auth:** org admin/owner  
**Params:** none

**Response:**
```json
{
  "total": 17,
  "applause_rate": 58.8,
  "by_type": {
    "grievance": 3,
    "suggestion": 2,
    "applause": 10,
    "inquiry": 2
  },
  "by_staff": [
    {
      "staff_id": "d411e0d9-fbcb-4c74-92bd-bd18139afc44",
      "total": 3,
      "grievances": 0,
      "suggestions": 0,
      "applause": 3,
      "inquiries": 0,
      "applause_rate": 100.0
    }
  ]
}
```

**Notes:**
- `applause_rate` — percentage of feedback that is applause/positive
- `by_staff` — sorted by total feedback descending

---

### 4. `GET /staff/analytics/fraud-reports`

Fraud report counts for the org by status.

**Auth:** org admin/owner  
**Params:** none

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "total": 3,
  "by_status": {
    "CONFIRMED_FRAUD": 1,
    "UNDER_INVESTIGATION": 2
  }
}
```

---

## analytics_service Endpoints

### 5. `GET /analytics/staff/committee-performance`

Pre-computed committee performance metrics from analytics_db. Falls back to a live feedback_db query when no pre-computed data exists for the project.

**Auth:** org admin or platform admin  
**Required params:**

| Param | Type | Description |
|-------|------|-------------|
| `project_id` | UUID | GRM project UUID |

**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | string | — | ISO date `YYYY-MM-DD` |
| `date_to` | string | — | ISO date `YYYY-MM-DD` |
| `use_live` | bool | `false` | Force live query from feedback_db |

**Response:**
```json
{
  "total": 2,
  "items": [
    {
      "committee_id": "a1b2c3d4-...",
      "committee_name": "Grievance Committee - DSM",
      "project_id": null,
      "cases_assigned": 15,
      "cases_resolved": 12,
      "cases_overdue": 2,
      "avg_resolution_hours": 48.5,
      "resolution_rate": 80.0
    }
  ]
}
```

**Notes:**
- Pre-computed data comes from Spark batch jobs (analytics_db). No `project_id` in pre-computed table — returns all committees when using pre-computed path.
- Use `use_live=true` to force per-project filtering from feedback_db.

---

### 6. `GET /analytics/staff/last-logins`

Last login time and 24-hour login count per officer from the pre-aggregated analytics_db table.

**Auth:** org admin or platform admin  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | string | — | ISO date `YYYY-MM-DD` |
| `date_to` | string | — | ISO date `YYYY-MM-DD` |

**Response:**
```json
{
  "total": 5,
  "items": [
    {
      "user_id": "5183174a-bcad-4e68-bf06-700d1f1260dc",
      "last_login_at": "2026-05-21T14:32:10",
      "login_count_7d": 3,
      "platform": null
    }
  ]
}
```

**Notes:**
- Data is pre-aggregated by Spark jobs. `login_count_7d` maps to `login_count_24h` from the analytics table.
- Returns empty `items` if no Spark job has run yet.

---

### 7. `GET /analytics/staff/unread-assigned`

Officers who have feedback assigned to them but have taken no action (no acknowledgment, no response, no status change).

**Auth:** org admin or platform admin  
**Required params:**

| Param | Type | Description |
|-------|------|-------------|
| `project_id` | UUID | GRM project UUID |

**Response:**
```json
{
  "total": 2,
  "items": [
    {
      "user_id": "abc123-...",
      "assigned_count": 5,
      "unread_count": 3,
      "feedback_ids": ["uuid1", "uuid2", "uuid3"]
    }
  ]
}
```

---

### 8. `GET /analytics/staff/login-not-read`

Officers who logged in today AND still have unread/unprocessed assigned feedback — reveals staff who are active but not clearing their queue.

**Auth:** org admin or platform admin  
**Required params:**

| Param | Type | Description |
|-------|------|-------------|
| `project_id` | UUID | GRM project UUID |

**Response:**
```json
{
  "total": 1,
  "items": [
    {
      "user_id": "abc123-...",
      "last_login_at": "2026-05-21T09:15:00",
      "assigned_unread_count": 4,
      "feedback_ids": ["uuid1", "uuid2", "uuid3", "uuid4"]
    }
  ]
}
```

---

### 9. `GET /analytics/org/{org_id}/staff-performance`

Per-staff queue performance: average/min/max wait time and service time, tickets served, within the last 7 days by default.

**Auth:** org admin (must match `org_id`) or platform admin  
**Path param:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | string | 7 days ago | ISO date |
| `date_to` | string | today | ISO date |

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "date_from": "2026-05-14",
  "date_to": "2026-05-21",
  "total_staff": 3,
  "items": [
    {
      "user_id": "abc123-...",
      "tickets_served": 42,
      "avg_wait_seconds": 320,
      "min_wait_seconds": 45,
      "max_wait_seconds": 1200,
      "avg_service_seconds": 180,
      "feedback_count": 5
    }
  ]
}
```

---

### 10. `GET /analytics/org/{org_id}/staff-duty`

Log of all staff duty (counter) sessions: who was on duty, at which service point, when, and how many tickets they served.

**Auth:** org admin or platform admin  
**Path param:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | string | yesterday | ISO date |
| `date_to` | string | today | ISO date |
| `is_active` | bool | all | Filter active sessions only |

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "date_from": "2026-05-20",
  "date_to": "2026-05-21",
  "total_sessions": 12,
  "active_sessions": 2,
  "items": [
    {
      "session_id": "uuid",
      "user_id": "uuid",
      "service_point_id": "uuid",
      "service_point_name": "Customer Care",
      "started_at": "2026-05-21T08:00:00",
      "ended_at": "2026-05-21T16:00:00",
      "tickets_served": 18,
      "is_active": false
    }
  ]
}
```

---

### 11. `GET /analytics/org/{org_id}/waiting-vs-feedback`

Hourly correlation between queue wait times and feedback volume — helps identify whether long queues trigger complaint spikes.

**Auth:** org admin or platform admin  
**Path param:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | string | yesterday | ISO date |
| `date_to` | string | today | ISO date |
| `granularity` | string | `hour` | `hour` \| `day` |

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "granularity": "hour",
  "date_from": "2026-05-20",
  "date_to": "2026-05-21",
  "items": [
    {
      "period": "2026-05-21T09:00:00",
      "avg_wait_seconds": 480,
      "feedback_count": 3,
      "grievance_count": 2
    }
  ]
}
```

---

### 12. `GET /analytics/org/{org_id}/feedback-timing`

Feedback submission heatmap by hour-of-day × day-of-week. Identifies peak complaint windows.

**Auth:** org admin or platform admin  
**Path param:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | string | 30 days ago | ISO date |
| `date_to` | string | today | ISO date |

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "date_from": "2026-04-21",
  "date_to": "2026-05-21",
  "peak_hour": 15,
  "peak_day": "Sunday",
  "cells": [
    {
      "hour_of_day": 15,
      "day_of_week": 0,
      "day_name": "Sunday",
      "total": 4,
      "grievances": 3,
      "suggestions": 0,
      "applause": 1,
      "inquiries": 0
    }
  ]
}
```

**Notes:**
- `day_of_week`: 0 = Sunday, 6 = Saturday
- `hour_of_day`: 0–23 (UTC)
- Only cells with at least 1 submission are returned

---

### 13. `GET /analytics/org/{org_id}/employee-feedback/summary`

Aggregate summary of internal employee feedback (grievances, suggestions, applause, inquiries submitted by staff about their workplace).

**Auth:** org admin or platform admin  
**Path param:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | string | — | ISO date |
| `date_to` | string | — | ISO date |

**Response:**
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

---

### 14. `GET /analytics/org/{org_id}/employee-feedback/by-category`

Employee feedback breakdown by category (compensation, management, tools_resources, culture, etc.).

**Auth:** org admin or platform admin  
**Path param:** `org_id` (UUID)  
**Optional params:** `date_from`, `date_to` (ISO date strings)

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
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
      "category": "management",
      "total": 2,
      "grievances": 1,
      "suggestions": 1,
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
}
```

---

### 15. `GET /analytics/org/{org_id}/employee-feedback/by-department`

Employee feedback breakdown by department and branch.

**Auth:** org admin or platform admin  
**Path param:** `org_id` (UUID)  
**Optional params:** `date_from`, `date_to` (ISO date strings)

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "items": [
    {
      "department_id": "17f96d55-6590-42e6-837f-48db490fcd96",
      "branch_id": "1ffae914-af34-436b-8452-32a05eef047b",
      "total": 1,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 0,
      "applause_rate": "0.0"
    }
  ]
}
```

**Notes:**
- `department_id: null` means the feedback was submitted without a department association (anonymous or org-level)

---

### 16. `GET /analytics/org/{org_id}/employee-feedback/trend`

Employee feedback volume over time. Supports hour/day/week/month granularity.

**Auth:** org admin or platform admin  
**Path param:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `granularity` | string | `day` | `hour` \| `day` \| `week` \| `month` |
| `date_from` | string | — | ISO date |
| `date_to` | string | — | ISO date |

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "granularity": "day",
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

---

### 17. `GET /analytics/org/{org_id}/combined-performance`

Unified organisational health score combining consumer feedback metrics with internal employee feedback. Returns a single `health_score` label.

**Auth:** org admin or platform admin  
**Path param:** `org_id` (UUID)  
**Optional params:** `date_from`, `date_to` (ISO date strings)

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "consumer": {
    "total": 74,
    "grievances": 35,
    "suggestions": 15,
    "applause": 16,
    "inquiries": 8,
    "resolved": 0,
    "open_count": 74,
    "applause_rate": "21.6",
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
    "applause_rate": "23.1"
  },
  "health_score": "needs_improvement"
}
```

**`health_score` values:** `excellent` | `good` | `fair` | `needs_improvement`

---

## waiting_service Endpoints

> All waiting endpoints require `org_id` as a **query parameter** (not path param).

### 18. `GET /waiting/analytics/dashboard`

Live queue status: total waiting, attending, completed today, and per-service-point breakdown.

**Auth:** org admin or platform admin  
**Required params:**

| Param | Type | Description |
|-------|------|-------------|
| `org_id` | UUID | Organisation UUID |

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "generated_at": "2026-05-21T18:48:48.531998Z",
  "total_waiting": 4,
  "total_attending": 0,
  "total_completed_today": 0,
  "service_points": [
    {
      "service_point_id": "6e66548d-a849-4a05-9aab-df4a53b94dfa",
      "service_point_name": "Customer Care",
      "point_type": "SERVICE",
      "waiting_count": 4,
      "attending_count": 0,
      "avg_wait_seconds": null,
      "avg_service_seconds": null,
      "throughput_today": 0
    }
  ]
}
```

---

### 19. `GET /waiting/analytics/staff-duty`

Queue staff duty sessions within a date range.

**Auth:** org admin or platform admin  
**Required params:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | string | yesterday | ISO date `YYYY-MM-DD` |
| `date_to` | string | today | ISO date |
| `is_active` | bool | all | Filter for active sessions only |

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "date_from": "2026-05-20",
  "date_to": "2026-05-21",
  "total_sessions": 12,
  "active_sessions": 2,
  "items": [
    {
      "session_id": "uuid",
      "user_id": "uuid",
      "counter_id": "uuid",
      "service_point_id": "uuid",
      "started_at": "2026-05-21T08:00:00Z",
      "ended_at": "2026-05-21T16:00:00Z",
      "tickets_served": 18,
      "is_active": false
    }
  ]
}
```

---

### 20. `GET /waiting/analytics/by-period`

Queue wait and service times aggregated by time period (hour/day/week).

**Auth:** org admin or platform admin  
**Required params:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `granularity` | string | `hour` | `hour` \| `day` \| `week` |
| `date_from` | string | 7 days ago | ISO date |
| `date_to` | string | today | ISO date |

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "granularity": "day",
  "date_from": "2026-05-14",
  "date_to": "2026-05-21",
  "items": [
    {
      "period": "2026-05-21",
      "tickets_completed": 42,
      "avg_wait_seconds": 280,
      "avg_service_seconds": 150,
      "p90_wait_seconds": 600
    }
  ]
}
```

---

### 21. `GET /waiting/analytics/by-service-point`

Wait and service time aggregated per service point — identifies which counters have the longest queues.

**Auth:** org admin or platform admin  
**Required params:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | string | 7 days ago | ISO date |
| `date_to` | string | today | ISO date |

**Response:**
```json
{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "date_from": "2026-05-14",
  "date_to": "2026-05-21",
  "items": [
    {
      "service_point_id": "6e66548d-...",
      "service_point_name": "Customer Care",
      "tickets_completed": 124,
      "avg_wait_seconds": 320,
      "avg_service_seconds": 175,
      "p90_wait_seconds": 720
    }
  ]
}
```

---

## auth_service Endpoints

### 22. `GET /orgs/{org_id}/members`

List all members of an organisation with their roles and status.

**Auth:** at least `MEMBER` role in the org  
**Path param:** `org_id` (UUID)  
**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `active_only` | bool | `false` | Return only ACTIVE members (excludes suspended/removed) |

**Response:**
```json
[
  {
    "user_id": "5183174a-bcad-4e68-bf06-700d1f1260dc",
    "organisation_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
    "org_role": "OWNER",
    "status": "ACTIVE",
    "joined_at": "2026-05-10T12:05:22.697082Z"
  }
]
```

**`org_role` values:** `OWNER` | `ADMIN` | `MANAGER` | `MEMBER`  
**`status` values:** `ACTIVE` | `SUSPENDED` | `REMOVED`

**Error — was returning 405:**  
Previously `GET /orgs/{org_id}/members` returned `405 Method Not Allowed` because only `POST` existed. The GET endpoint was added in commit `f69bbdb`.

---

## Known Empty Results

The following endpoints return `items: []` for Yas Tanzania because the data requires Spark jobs or active queue sessions to populate:

| Endpoint | Why empty |
|----------|-----------|
| `/analytics/staff/committee-performance` | Spark batch job hasn't run for this project |
| `/analytics/staff/last-logins` | Spark job populates `staff_logins` table — not yet run |
| `/analytics/staff/unread-assigned` | All assigned feedback has been actioned |
| `/analytics/staff/login-not-read` | Depends on `last-logins` data from Spark |
| `/analytics/org/{org_id}/staff-performance` | Requires active queue sessions |
| `/analytics/org/{org_id}/staff-duty` | No duty sessions in the last 2 days |
| `/waiting/analytics/staff-duty` | No duty sessions in the last 2 days |
| `/waiting/analytics/by-period` | No completed tickets in the last 7 days |
| `/waiting/analytics/by-service-point` | No completed tickets in the last 7 days |

---

## Quick Reference — Required Params Cheat Sheet

```
# staff_service — no params required
GET /staff/analytics/overview
GET /staff/analytics/verifications
GET /staff/analytics/feedback
GET /staff/analytics/fraud-reports

# analytics_service — project_id required
GET /analytics/staff/committee-performance?project_id={uuid}
GET /analytics/staff/unread-assigned?project_id={uuid}
GET /analytics/staff/login-not-read?project_id={uuid}

# analytics_service — no params required
GET /analytics/staff/last-logins

# analytics_service — org_id in path
GET /analytics/org/{org_id}/staff-performance
GET /analytics/org/{org_id}/staff-duty
GET /analytics/org/{org_id}/waiting-vs-feedback
GET /analytics/org/{org_id}/feedback-timing
GET /analytics/org/{org_id}/employee-feedback/summary
GET /analytics/org/{org_id}/employee-feedback/by-category
GET /analytics/org/{org_id}/employee-feedback/by-department
GET /analytics/org/{org_id}/employee-feedback/trend
GET /analytics/org/{org_id}/combined-performance

# waiting_service — org_id as QUERY PARAM (not path)
GET /waiting/analytics/dashboard?org_id={uuid}
GET /waiting/analytics/staff-duty?org_id={uuid}
GET /waiting/analytics/by-period?org_id={uuid}&granularity=day
GET /waiting/analytics/by-service-point?org_id={uuid}

# auth_service — org_id in path
GET /orgs/{org_id}/members
```
