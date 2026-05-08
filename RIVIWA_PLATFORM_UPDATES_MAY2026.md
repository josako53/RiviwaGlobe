# Riviwa Platform — Full Update Reference (May 2026)

**Version:** 2.3.0 · **Date:** 2026-05-09  
**Live Server:** `77.237.241.13` · **Base URL:** `https://api.riviwa.com`  
**Repository:** `riviwaglobe` (github.com/josako53/RiviwaGlobe)

---

## Table of Contents

1. [Platform Status — All 16 Services](#1-platform-status--all-16-services)
2. [New Services Added (v2.1–v2.3)](#2-new-services-added)
3. [Analytics Service — All New Endpoints](#3-analytics-service--all-new-endpoints)
   - 3.1 Branch Analytics (v2.3 — 4 new endpoints)
   - 3.2 Staff Performance Analytics (v2.2 — 4 new endpoints)
   - 3.3 Waiting Service Analytics (v2.2 — 3 new endpoints)
   - 3.4 Org-level Analytics Fixes (v2.1 — project_id → org_id)
4. [Real-time Analytics — Spark Architecture](#4-real-time-analytics--spark-architecture)
5. [Infrastructure Changes](#5-infrastructure-changes)
6. [Full Nginx Routing Table](#6-full-nginx-routing-table)
7. [Staff Service — Complete API Reference](#7-staff-service--complete-api-reference)
8. [Waiting Service — API Reference](#8-waiting-service--api-reference)
9. [Analytics Service — Complete Endpoint Reference](#9-analytics-service--complete-endpoint-reference)
10. [Error Reference](#10-error-reference)
11. [End-to-End Demo: Yas Tanzania Telecom](#11-end-to-end-demo-yas-tanzania-telecom)

---

## 1. Platform Status — All 16 Services

All services live on `77.237.241.13`. Health: `GET https://api.riviwa.com/health/{service}`.

| Service | Port | DB Port | Container | Status |
|---------|------|---------|-----------|--------|
| auth_service | 8000 | 5433 | `riviwa_auth_service` | ✅ Running |
| feedback_service | 8090 | 5434 | `feedback_service` | ✅ Running |
| stakeholder_service | 8070 | 5436 | `stakeholder_service` | ✅ Running |
| payment_service | 8040 | 5435 | `payment_service` | ✅ Running |
| notification_service | 8060 | 5437 | `notification_service` | ✅ Running |
| analytics_service | 8095 | 5441 | `analytics_service` | ✅ Running |
| ai_service | 8085 | 5438 | `ai_service` | ✅ Running |
| translation_service | 8050 | 5439 | `translation_service` | ✅ Running |
| recommendation_service | 8055 | 5440 | `recommendation_service` | ✅ Running |
| integration_service | 8100 | 5442 | `integration_service` | ✅ Running |
| product_service | 8110 | 5443 | `product_service` | ✅ Running |
| qr_service | 8120 | 5444 | `qr_service` | ✅ Running |
| verification_service | 8125 | 5445 | `verification_service` | ✅ Running |
| **staff_service** | **8135** | **5447** | `staff_service` | ✅ Running (new v2.1) |
| **waiting_service** | **8130** | **5448** | `waiting_service` | ✅ Running (new v2.1) |
| spark_jobs | — | — | `spark_jobs` | ✅ Running |

---

## 2. New Services Added

### 2.1 Staff Service (port 8135) — added v2.1

Identity verification for organisation staff members using `ORG-NNNNN` codes.

**DB:** `staff_db` (PostgreSQL 15, port 5447)  
**Redis DB:** 10  
**MinIO bucket:** `riviwa-staff`  
**Kafka:** consumes `riviwa.organisation.events` for org cache  

**Core tables:** `staff_profiles`, `staff_id_sequences`, `staff_verification_events`, `staff_fraud_reports`, `staff_feedback`, `bulk_import_jobs`, `org_cache`

**Code format:** `{ORG_SLUG_UPPER_6CHARS}-{SEQ:05d}` e.g. `YASTZ-00001`

**Key endpoints:**
```
POST   /api/v1/staff/register                        — register a staff member
GET    /api/v1/staff/                                — list org staff
GET    /api/v1/staff/{staff_id}                      — get profile
POST   /api/v1/staff/verify                          — verify by code (public)
POST   /api/v1/staff/{staff_id}/fraud-report         — report fraudulent identity
POST   /api/v1/staff/feedback                        — submit service feedback
GET    /api/v1/staff/analytics/overview              — status counts
GET    /api/v1/staff/analytics/verifications         — verification trends
GET    /api/v1/staff/analytics/feedback              — avg rating, top staff
GET    /api/v1/staff/analytics/fraud-reports         — fraud report counts
POST   /api/v1/staff/bulk-import                     — CSV bulk import
```

**Bug fix (v2.1):** `get_by_code_any_org` crashed with `MultipleResultsFound` when same code pattern existed across multiple orgs. Fixed with `.limit(1).scalars().first()` ordered by `created_at DESC`.

---

### 2.2 Waiting Service (port 8130) — added v2.1

Real-time queue management: tickets, priority, ETA, staff counters, and analytics.

**DB:** `waiting_db` (PostgreSQL 15, port 5448)  
**Redis DB:** 9  
**Kafka:** consumes `riviwa.organisation.events` for org cache  

**Core tables:** `queue_tickets`, `queue_ticket_stages`, `service_points`, `service_flows`, `flow_steps`, `staff_counters`, `staff_sessions`, `urgency_requests`, `org_cache`

**Key models:**
- `QueueTicket` — one record per customer in the queue; tracks status through WAITING → ATTENDING → FINISHED → COMPLETED
- `QueueTicketStage` — one record per service point a ticket passes through; records `wait_duration_seconds` and `service_duration_seconds`
- `StaffSession` — tracks when a staff member opens/closes a counter session; stores `tickets_served` and `avg_service_seconds`
- `StaffCounter` — individual desk within a `ServicePoint`; can be assigned to a staff user

---

## 3. Analytics Service — All New Endpoints

### 3.1 Branch Analytics (v2.3 — 4 new endpoints)

Comprehensive branch-level feedback analytics. `branch_id` is denormalised onto `feedbacks` from `OrgDepartment.branch_id` at submission time, enabling branch queries without cross-DB joins.

**Auth:** Bearer JWT with org admin role (`admin` / `owner`) or platform admin.

---

#### `GET /api/v1/analytics/org/{org_id}/branches/summary`

All branches at a glance — sorted by total feedback DESC.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `feedback_type` | string | Optional: GRIEVANCE \| SUGGESTION \| APPLAUSE \| INQUIRY |
| `date_from` | date | YYYY-MM-DD |
| `date_to` | date | YYYY-MM-DD |

**Response `BranchSummaryResponse`:**
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

#### `GET /api/v1/analytics/org/{org_id}/branches/performance`

Branch performance league table — ranked **best to worst** by `resolution_rate`.  
Ties broken by: fewest `overdue` first, then highest total volume.

**Response `BranchPerformanceResponse`:**  
Same fields as summary items but each includes a `rank` integer (1 = best performer).

Use this endpoint to identify which branches need operational support.

---

#### `GET /api/v1/analytics/org/{org_id}/branches/trend`

Multi-branch time series — one row per `(branch_id, period)` pair.  
Useful for overlaying multiple branches on a comparison chart.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `granularity` | string | `day` | hour \| day \| week \| month |
| `feedback_type` | string | — | Optional filter |
| `date_from` / `date_to` | date | — | Date window |

**Response `BranchTrendResponse`:**
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

#### `GET /api/v1/analytics/org/{org_id}/branches/{branch_id}/detail`

Complete single-branch analytics in one call:

| Field | Description |
|-------|-------------|
| Summary totals | total, by-type, resolved, open, escalated, dismissed, overdue |
| Priority urgency | `critical_open`, `high_open` (unresolved CRITICAL/HIGH items) |
| Performance | `resolution_rate`, `escalation_rate`, `avg_resolution_hours` |
| `by_department` | Per-department breakdown within the branch |
| `by_category` | Top 15 categories driving feedback at this branch |
| `by_service` | Top 10 services with most feedback |
| `trend` | Daily time series for the selected period |

**Example response excerpt:**
```json
{
  "org_id": "uuid",
  "branch_id": "uuid",
  "total": 142,
  "resolution_rate": 66.9,
  "escalation_rate": 5.6,
  "critical_open": 3,
  "high_open": 11,
  "by_department": [
    { "department_id": "uuid", "total": 45, "grievances": 31, "resolved": 28, "avg_resolution_hours": 12.1 }
  ],
  "by_category": [
    { "category": "NETWORK", "total": 38, "grievances": 35, "resolved": 22 }
  ],
  "by_service": [
    { "service_id": "uuid", "total": 29, "grievances": 22, "resolved": 19 }
  ],
  "trend": [
    { "period": "2026-05-07T00:00:00Z", "total": 12, "grievances": 8 }
  ]
}
```

---

### 3.2 Staff Performance Analytics (v2.2 — 4 new endpoints)

Cross-service analytics combining `waiting_db` (queue data) with `feedback_db` (feedback data). The analytics_service opens a read-only connection to `waiting_db` via `WaitingAnalyticsRepository`.

---

#### `GET /api/v1/analytics/org/{org_id}/staff-performance`

Per-staff member: queue throughput + correlated feedback volume during their duty window.

**Query params:** `date_from`, `date_to` (default: last 7 days), `service_point_id` (optional filter)

**Response `StaffPerformanceResponse`:**
```json
{
  "total_staff": 8,
  "items": [
    {
      "staff_user_id": "uuid",
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

---

#### `GET /api/v1/analytics/org/{org_id}/staff-duty`

Who was on duty, at which counter and service point, when sessions opened/closed.

**Query params:** `date_from`, `date_to` (default: today), `is_active=true` for live view

**Response:** `StaffDutyResponse` with `total_sessions`, `active_sessions`, and per-session items.

---

#### `GET /api/v1/analytics/org/{org_id}/waiting-vs-feedback`

Side-by-side per period: avg queue wait time vs. feedback volume.

**Query params:** `granularity` (hour/day/week), `date_from`, `date_to`, `feedback_type`

Use `granularity=hour` (1–3 day range) to detect intra-day correlations.  
Use `granularity=day` for weekly trends.

**Response `WaitingVsFeedbackResponse`:**
```json
{
  "granularity": "hour",
  "items": [
    {
      "period": "2026-05-08T10:00:00Z",
      "tickets_served": 18,
      "avg_wait_seconds": 1320.0,
      "feedback_total": 7,
      "feedback_grievances": 5,
      "feedback_applause": 1,
      "feedback_suggestions": 1,
      "feedback_inquiries": 0
    }
  ]
}
```

---

#### `GET /api/v1/analytics/org/{org_id}/feedback-timing`

Hour-of-day × day-of-week heatmap. Each cell shows feedback volume at that exact hour on that weekday, aggregated over the date range.

**Query params:** `date_from`, `date_to` (default: last 30 days), `feedback_type`

**Response `FeedbackTimingResponse`:**
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

---

### 3.3 Waiting Service Analytics (v2.2 — 3 new endpoints)

Direct analytics from `waiting_service` (port 8130). Auth: Bearer JWT with org `manager` role or higher.

#### `GET /api/v1/waiting/analytics/staff-duty`

```
Query: org_id (required), date_from, date_to, is_active
```
Returns all staff sessions with counter/service-point detail and throughput.

#### `GET /api/v1/waiting/analytics/by-period`

```
Query: org_id (required), granularity (hour|day|week), date_from, date_to
```
Wait and service times bucketed by period. Use for queue pressure charts.

#### `GET /api/v1/waiting/analytics/by-service-point`

```
Query: org_id (required), date_from, date_to
```
Per-service-point stats: tickets served, avg/min/max wait seconds. Ranks by worst wait time.

---

### 3.4 Org-level Analytics Fixes (v2.1)

Six endpoints were updated to accept `org_id` as an alternative to `project_id`:

| Endpoint | Change |
|----------|--------|
| `GET /analytics/feedback/overdue` | `project_id` OR `org_id` |
| `GET /analytics/feedback/by-category` | `project_id` OR `org_id` |
| `GET /analytics/grievances/sla-status` | `project_id` OR `org_id` |
| `GET /analytics/grievances/dashboard` | `project_id` OR `org_id` |
| `GET /analytics/grievances/hotspots` | `project_id` OR `org_id` |
| `GET /analytics/suggestions/frequency` | `project_id` OR `org_id` |

When `org_id` is provided, the analytics service resolves all project IDs for that org and aggregates across them.

---

## 4. Real-time Analytics — Spark Architecture

Spark is the real-time analytics backbone. Three streaming jobs run continuously in the `spark_jobs` container.

### 4.1 Streaming Jobs

| Job | Input | Processing | Output | Latency |
|-----|-------|------------|--------|---------|
| **SLA Monitor** | `riviwa.feedback.events` | Stateful per-feedback tracking with `flatMapGroupsWithState`; detects ACK and resolution deadline breaches | `analytics_db.feedback_sla_status` + Redis `sla:breach:*` (24h TTL) | 30-second micro-batches |
| **Hotspot Detector** | `riviwa.feedback.events` | 60-min sliding window, 15-min slides; flags `(project, lga, category)` when count > 2× 7-day baseline AND count ≥ 5 | `analytics_db.hotspot_alerts` + Redis `hotspot:{project}:{lga}:{category}` (1h TTL) | 60-second micro-batches |
| **Live Dashboard** | `riviwa.feedback.events` | Per-project delta aggregation: open, resolved_today, critical_open, overdue | Redis hashes `dashboard:{project_id}:*` (120s TTL) | 30-second micro-batches |

### 4.2 Batch Jobs (APScheduler)

| Job | Schedule | What it computes |
|-----|----------|-----------------|
| `historical_analytics.py` | Hourly at :00 | Status distribution, SLA compliance, daily trends → `analytics_db` |
| `staff_analytics.py` | Daily 03:00 UTC | Committee performance, staff login aggregation → `analytics_db` |
| `ml_escalation.py` | Daily 04:00 UTC | GBT classifier escalation probability scoring per grievance → `analytics_db.feedback_ml_scores` |

### 4.3 API Read Strategy

The `analytics_service` API reads **Redis first** (sub-second) for live dashboard endpoints and falls back to `analytics_db` for historical queries. The staff-performance and branch analytics endpoints read `waiting_db` and `feedback_db` directly (no Spark layer) since queue session data is operational state, not event-sourced.

### 4.4 Redis DB Isolation

| DB | Owner | Contents |
|----|-------|----------|
| 0 | auth_service | Sessions, JTI deny-list, Celery broker |
| 3 | notification_service | Rate limiting, dedup |
| 4 | analytics_service | Analytics cache |
| 6 | spark_jobs | SLA breaches, hotspot alerts, dashboard counters |
| 9 | waiting_service | Queue depths, ETA cache |
| 10 | staff_service | Staff cache |

---

## 5. Infrastructure Changes

### docker-compose additions (v2.1–v2.3)

```yaml
# New services
staff_service:   port 8135, staff_db port 5447
waiting_service: port 8130, waiting_db port 5448

# analytics_service new env vars (v2.2)
WAITING_DB_HOST:     waiting_db
WAITING_DB_PORT:     5432
WAITING_DB_USER:     waiting_admin
WAITING_DB_PASSWORD: waiting_pass_130
WAITING_DB_NAME:     waiting_db
```

### Nginx routing additions

```nginx
# v2.1
location /api/v1/staff  → staff_service:8135

# v2.2
location /api/v1/waiting → waiting_service:8130
```

### analytics_service cross-service DB connections

`analytics_service` now holds **three** read-only DB connections:
- `feedback_db` (existing) — all feedback analytics
- `analytics_db` (own, read/write) — pre-computed Spark output
- `waiting_db` (new v2.2) — staff session and queue analytics

---

## 6. Full Nginx Routing Table

| URL Prefix | Service | Port |
|-----------|---------|------|
| `/api/v1/auth`, `/api/v1/users`, `/api/v1/orgs`, `/api/v1/admin`, `/api/v1/system` | auth | 8000 |
| `/api/v1/projects`, `/api/v1/stakeholders`, `/api/v1/activities`, `/api/v1/communications`, `/api/v1/focal-persons` | stakeholder | 8070 |
| `/api/v1/feedback`, `/api/v1/categories`, `/api/v1/channels`, `/api/v1/committees`, `/api/v1/pap`, `/api/v1/voice`, `/api/v1/reports`, `/api/v1/my`, `/api/v1/escalation-*`, `/api/v1/channel-sessions` | feedback | 8090 |
| `/api/v1/payments`, `/api/v1/webhooks/payment` | payment | 8040 |
| `/api/v1/notifications`, `/api/v1/notification-preferences`, `/api/v1/devices`, `/api/v1/templates`, `/api/v1/internal` | notification | 8060 |
| `/api/v1/analytics` | analytics | 8095 |
| `/api/v1/waiting` | waiting | 8130 |
| `/api/v1/integration`, `/api/v1/integration/.well-known` | integration | 8100 |
| `/api/v1/products` | product | 8110 |
| `/api/v1/qr` | qr | 8120 |
| `/api/v1/verify` | verification | 8125 |
| `/api/v1/staff` | staff | 8135 |
| `/api/v1/recommendations`, `/api/v1/similar`, `/api/v1/discover`, `/api/v1/index` | recommendation | 8055 |
| `/api/v1/translate`, `/api/v1/languages`, `/api/v1/detect` | translation | 8050 |
| `/api/v1/ai/conversations`, `/api/v1/ai/admin`, `/api/v1/ai/voice`, `/api/v1/ai/webhooks` | ai | 8085 |

---

## 7. Staff Service — Complete API Reference

**Base:** `https://api.riviwa.com/api/v1/staff`  
**Auth:** Bearer JWT. Public endpoints: `/verify`, `/feedback`.

### Staff Profiles

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/register` | admin/owner | Register a new staff member; auto-generates code |
| GET | `/` | member+ | List org staff (paginated) |
| GET | `/{staff_id}` | member+ | Get profile |
| PUT | `/{staff_id}` | admin/owner | Update profile |
| DELETE | `/{staff_id}` | admin/owner | Soft-delete |
| GET | `/code/{code}` | member+ | Lookup by staff code |

### Verification

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/verify` | Public | Verify staff by code; records scan event |
| GET | `/{staff_id}/verifications` | member+ | List scan history |

### Fraud Reports

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/{staff_id}/fraud-report` | Public | Submit fraud report with optional photos |
| GET | `/fraud-reports` | admin/owner | List org fraud reports |
| PUT | `/fraud-reports/{id}` | admin/owner | Update report status |

### Staff Feedback

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/feedback` | Public | Submit service feedback (rating + comment) |
| GET | `/feedback` | admin/owner | List feedback for org staff |

### Analytics

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/analytics/overview` | admin/owner | Active/suspended/terminated counts + by-department |
| GET | `/analytics/verifications` | admin/owner | Scan stats: VERIFIED/FAKE/UNKNOWN daily trend |
| GET | `/analytics/feedback` | admin/owner | Avg rating, top 10 staff by feedback |
| GET | `/analytics/fraud-reports` | admin/owner | Total reports by status |

### Bulk Import

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/bulk-import` | admin/owner | Upload CSV; async processing |
| GET | `/bulk-import/{job_id}` | admin/owner | Check job status |

### Internal

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/internal/sync-org` | X-Service-Key | Manually sync org cache |

---

## 8. Waiting Service — API Reference

**Base:** `https://api.riviwa.com/api/v1/waiting`  
**Auth:** Bearer JWT. Public endpoints: ticket creation via kiosk/SMS.

### Queue Tickets

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/tickets` | member+ | Create ticket (kiosk/app) |
| GET | `/tickets` | member+ | List tickets for org |
| GET | `/tickets/{id}` | member+ | Get ticket + current stage |
| POST | `/tickets/{id}/next` | member+ | Move ticket to next service point |
| POST | `/tickets/{id}/complete` | member+ | Mark ticket completed |
| POST | `/tickets/{id}/cancel` | member+ | Cancel ticket |
| GET | `/tickets/{id}/position` | Public | Queue position + ETA |

### Service Points

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/service-points` | admin/owner | Create service point |
| GET | `/service-points` | member+ | List org service points |
| PUT | `/service-points/{id}` | admin/owner | Update |
| DELETE | `/service-points/{id}` | admin/owner | Delete |

### Staff Counters

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/counters` | admin/owner | Create counter at service point |
| GET | `/service-points/{id}/counters` | member+ | List counters |
| POST | `/counters/{id}/assign` | member+ | Assign ticket to counter |
| POST | `/counters/{id}/release` | member+ | Release current ticket |

### Staff Sessions

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/sessions/open` | member+ | Open a duty session at a counter |
| POST | `/sessions/{id}/close` | member+ | Close session |
| GET | `/sessions/active` | member+ | My active session |

### Service Flows

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/flows` | admin/owner | Create multi-step service flow |
| GET | `/flows` | member+ | List flows |
| PUT | `/flows/{id}/steps` | admin/owner | Update flow steps |

### Urgency Requests

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/tickets/{id}/urgency` | Public | Request priority escalation |
| POST | `/urgency/{id}/review` | member+ | Approve/reject urgency |

### Analytics

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/analytics/dashboard` | member+ | Live queue depths + service point stats |
| GET | `/analytics/staff-duty` | manager+ | Staff sessions with counter/service-point detail |
| GET | `/analytics/by-period` | manager+ | Wait/service times bucketed by hour/day/week |
| GET | `/analytics/by-service-point` | manager+ | Per-service-point throughput + avg wait |

---

## 9. Analytics Service — Complete Endpoint Reference

**Base:** `https://api.riviwa.com/api/v1/analytics`  
**Auth:** Bearer JWT. Org admin = `admin`/`owner` role or platform admin.

### Project-level Endpoints

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /feedback/time-to-open` | `project_id` | Hours from submission to first staff action |
| `GET /feedback/unread` | `project_id` | Feedback sitting unprocessed with `days_waiting` |
| `GET /feedback/overdue` | `project_id` OR `org_id` | Past target resolution date |
| `GET /feedback/not-processed` | `project_id` | Untouched since submission |
| `GET /feedback/processed-today` | `project_id` | Processed today |
| `GET /feedback/resolved-today` | `project_id` | Resolved today |
| `GET /feedback/by-service` | `project_id` | Breakdown by service |
| `GET /feedback/by-product` | `project_id` | Breakdown by product |
| `GET /feedback/by-category` | `project_id` OR `org_id` | Breakdown by category definition |
| `GET /feedback/by-department` | `project_id` | Breakdown by department |
| `GET /feedback/by-branch` | `project_id` | Breakdown by branch |
| `GET /feedback/by-stage` | `project_id` | Breakdown by workflow stage |
| `GET /grievances/unresolved` | `project_id` | Unresolved grievances list |
| `GET /grievances/sla-status` | `project_id` OR `org_id` | SLA breach status per grievance |
| `GET /grievances/dashboard` | `project_id` OR `org_id` | Grievance KPI dashboard |
| `GET /grievances/hotspots` | `project_id` OR `org_id` | Geographic/category hotspots |
| `GET /suggestions/implementation-time` | `project_id` | Time to implement suggestions |
| `GET /suggestions/frequency` | `project_id` OR `org_id` | Count by category + priority |
| `GET /suggestions/by-location` | `project_id` | Count by region/LGA/ward |
| `GET /suggestions/unread` | `project_id` | Unread suggestions |
| `GET /suggestions/implemented-today` | `project_id` | Suggestions actioned today |
| `GET /suggestions/implemented-this-week` | `project_id` | Suggestions actioned this week |
| `GET /inquiries/summary` | `project_id` | Open/resolved, avg response hours |
| `GET /inquiries/unread` | `project_id` | Unread inquiries |
| `GET /inquiries/overdue` | `project_id` | Overdue inquiries |
| `GET /inquiries/by-channel` | `project_id` | Inquiries by submission channel |
| `GET /inquiries/by-category` | `project_id` | Inquiries by category |
| `GET /staff/committee-performance` | `project_id` | Cases assigned/resolved/overdue per committee |
| `GET /staff/last-logins` | date range | Last login + 7-day count per staff member |
| `GET /staff/unread-assigned` | `project_id` | Staff with unread assigned feedback |
| `GET /staff/login-not-read` | `project_id` | Logged-in staff ignoring their queue |

### Organisation-level Endpoints

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /org/{id}/summary` | date range | Total counts, statuses, avg resolution hours |
| `GET /org/{id}/by-project` | date range | Breakdown by project |
| `GET /org/{id}/by-period` | `granularity`, date range | Time series (day/week/month) |
| `GET /org/{id}/by-channel` | date range | By submission channel |
| `GET /org/{id}/by-branch` | `feedback_type`, date range | By branch (basic) |
| `GET /org/{id}/by-department` | `feedback_type`, date range | By department |
| `GET /org/{id}/by-service` | `feedback_type`, date range | By service |
| `GET /org/{id}/by-product` | `feedback_type`, date range | By product |
| `GET /org/{id}/by-category` | `feedback_type`, date range | By category definition |
| `GET /org/{id}/grievances/summary` | date range | Grievance KPIs |
| `GET /org/{id}/grievances/by-level` | date range | By escalation level |
| `GET /org/{id}/grievances/by-location` | date range | By region/LGA |
| `GET /org/{id}/grievances/dashboard` | date range | Full grievance dashboard |
| `GET /org/{id}/grievances/sla` | date range | SLA compliance by priority |
| `GET /org/{id}/suggestions/summary` | date range | Actioned/pending/dismissed rates |
| `GET /org/{id}/suggestions/by-project` | date range | By project |
| `GET /org/{id}/applause/summary` | date range | Applause with MoM change % |
| `GET /org/{id}/inquiries/summary` | date range | Open/resolved, avg response hours |
| **`GET /org/{id}/branches/summary`** | `feedback_type`, date range | **All branches: full summary (v2.3)** |
| **`GET /org/{id}/branches/performance`** | `feedback_type`, date range | **League table by resolution rate (v2.3)** |
| **`GET /org/{id}/branches/trend`** | `granularity`, date range | **Multi-branch time series (v2.3)** |
| **`GET /org/{id}/branches/{branch_id}/detail`** | date range | **Single-branch deep-dive (v2.3)** |
| **`GET /org/{id}/staff-duty`** | date range, `is_active` | **Who was on duty when (v2.2)** |
| **`GET /org/{id}/staff-performance`** | date range, `service_point_id` | **Per-staff: wait + feedback (v2.2)** |
| **`GET /org/{id}/waiting-vs-feedback`** | `granularity`, date range | **Wait time vs feedback correlation (v2.2)** |
| **`GET /org/{id}/feedback-timing`** | date range, `feedback_type` | **Hour × day-of-week heatmap (v2.2)** |

### Platform-level Endpoints (platform admin only)

| Endpoint | Description |
|----------|-------------|
| `GET /platform/summary` | All orgs aggregate |
| `GET /platform/by-org` | Breakdown per organisation |
| `GET /platform/by-period` | Platform-wide time series |
| `GET /platform/by-channel` | By channel across all orgs |
| `GET /platform/by-branch` | By branch across all orgs |
| `GET /platform/by-department` | By department across all orgs |
| `GET /platform/by-service` | By service across all orgs |
| `GET /platform/by-product` | By product across all orgs |
| `GET /platform/by-category` | By category across all orgs |
| `GET /platform/grievances/summary` | Platform grievance KPIs |
| `GET /platform/grievances/dashboard` | Full grievance dashboard |
| `GET /platform/grievances/sla` | SLA compliance platform-wide |
| `GET /platform/suggestions/summary` | Platform suggestion rates |
| `GET /platform/applause/summary` | Platform applause trends |
| `GET /platform/inquiries/summary` | Platform inquiry KPIs |

### AI Insights

| Endpoint | Body | Description |
|----------|------|-------------|
| `POST /analytics/ai/ask` | `{ "question": "...", "scope": "platform\|org\|project", "org_id": "uuid" }` | Groq-powered analytics Q&A |
| `POST /analytics/ai/ask-voice` | multipart/audio | Voice question → transcribe → AI answer |

---

## 10. Error Reference

All services return consistent error envelopes:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description.",
  "details": [{ "field": "...", "message": "..." }]
}
```

| HTTP | Error Code | Meaning |
|------|-----------|---------|
| 400 | `VALIDATION_ERROR` | Request body / query param invalid |
| 401 | `UNAUTHORISED` | Missing or expired Bearer token |
| 403 | `FORBIDDEN` | Authenticated but insufficient role |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Duplicate resource (slug, code, etc.) |
| 422 | `VALIDATION_ERROR` | FastAPI request validation failure |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

**Token expired:** `{"error": "TOKEN_EXPIRED", "message": "Access token has expired."}`

---

## 11. End-to-End Demo: Yas Tanzania Telecom

Test run results for Yas Tanzania Telecommunications Ltd (`yas-tz-991088`):

- **6 branches**, **8 departments**, **15 staff members** created
- **Feedback** submitted: grievances, suggestions, applause, inquiries
- **Staff verifications** tested; fraud reports filed
- **Analytics** all returning correct data
- **Final test pass rate: 98%** (49/50 checks)

**Live org:** `org_id = 455bd8b1-ce74-44c7-a571-e5986dd65d17`  
**Test credentials:** `testgrm@riviwa.com` / `TestGRM@2026!` · OTP: `000000`

---

*Generated 2026-05-09 — Riviwa Platform v2.3.0*
