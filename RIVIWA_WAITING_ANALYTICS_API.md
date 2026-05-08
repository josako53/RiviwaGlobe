# Riviwa Waiting Service & Analytics API Reference

> Document: `RIVIWA_WAITING_ANALYTICS_API.md`  
> Generated: 2026-05-08  
> Services: **waiting_service** (8130) · **analytics_service** (8095)  
> Base URL (production): `https://api.riviwa.com`  
> Direct (dev/server): `http://77.237.241.13:{port}`

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Waiting Service — Overview](#2-waiting-service--overview)
3. [Admin — Service Points](#3-admin--service-points)
4. [Admin — Service Flows](#4-admin--service-flows)
5. [Admin — Staff Counters](#5-admin--staff-counters)
6. [Admin — Staff Sessions](#6-admin--staff-sessions)
7. [Admin — Urgency Requests](#7-admin--urgency-requests)
8. [Queue — Patient Endpoints](#8-queue--patient-endpoints)
9. [Staff — Queue Operations](#9-staff--queue-operations)
10. [Waiting — Analytics Dashboard](#10-waiting--analytics-dashboard)
11. [Waiting — SMS Inbound](#11-waiting--sms-inbound)
12. [Analytics Service — Overview](#12-analytics-service--overview)
13. [Analytics — Organisation Level](#13-analytics--organisation-level)
14. [Analytics — Project Level](#14-analytics--project-level)
15. [Analytics — Platform Level](#15-analytics--platform-level)
16. [Analytics — AI Insights](#16-analytics--ai-insights)
17. [End-to-End Flows](#17-end-to-end-flows)
18. [Enumerations Reference](#18-enumerations-reference)
19. [Error Responses](#19-error-responses)

---

## 1. Authentication

All endpoints marked **JWT** require:
```
Authorization: Bearer <access_token>
```

**Step 1 — Login**
```http
POST /api/v1/auth/login
Content-Type: application/json

{ "identifier": "user@example.com", "password": "P@ssword!" }
```
Response: `{ "login_token": "...", "otp_channel": "email", "expires_in_seconds": 300 }`

**Step 2 — Verify OTP**
```http
POST /api/v1/auth/login/verify-otp
Content-Type: application/json

{ "login_token": "<from step 1>", "otp_code": "000000" }
```
Response: `{ "access_token": "eyJ...", "refresh_token": "...", "expires_in": 1800 }`

**Switch Org Context** (required before accessing org-scoped endpoints)
```http
POST /api/v1/auth/switch-org
Authorization: Bearer <access_token>
Content-Type: application/json

{ "org_id": "<org_uuid>" }
```
Response: `{ "tokens": { "access_token": "eyJ..." } }`

> Use the new org-scoped `access_token` for all subsequent requests.

> Dev OTP is always `000000`.

---

## 2. Waiting Service — Overview

The Waiting Service manages real-time patient queues across hospital/clinic service points.

**Architecture concepts:**

| Concept | Description |
|---------|-------------|
| **ServicePoint** | A named location where patients are attended (e.g. "OPD Registration", "Doctor Room 1") |
| **ServiceFlow** | An ordered chain of ServicePoints a ticket passes through (e.g. Registration → Triage → Doctor → Pharmacy) |
| **StaffCounter** | A physical counter/desk at a ServicePoint. One counter handles one ticket at a time |
| **QueueTicket** | A patient's position in the queue. Has priority, ticket number, and current step |
| **StaffSession** | A staff member's active shift at a counter. Tracks tickets served and average service time |

**Priority scoring** — lower score is served first:

| Priority | Score prefix |
|----------|-------------|
| URGENT   | 0 × 10¹² + epoch_µs |
| HIGH     | 1 × 10¹² + epoch_µs |
| NORMAL   | 2 × 10¹² + epoch_µs |

**Ticket number format:** `{ORG_CODE}-{YYYYMMDD}-{NNNN}` e.g. `MNH-HOSP-20260508-0042`

---

## 3. Admin — Service Points

> **Auth:** JWT (org-scoped token) + staff/admin role  
> **Base:** `https://api.riviwa.com/api/v1/waiting/admin`

---

### POST `/waiting/admin/service-points` — Create Service Point

Creates a named location where staff attend to patients.

**Request body:**
```json
{
  "org_id": "uuid",
  "name": "OPD Registration",
  "code": "OPD-REG",
  "point_type": "DESK",
  "description": "First registration desk",
  "max_concurrent_staff": 3,
  "avg_service_minutes": 5.0,
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `org_id` | UUID | ✅ | Organisation ID |
| `name` | string | ✅ | Display name |
| `code` | string | ✅ | Unique code within org (e.g. `OPD-REG`) |
| `point_type` | string | ✅ | `DESK` `COUNTER` `ROOM` `KIOSK` `STAGE` `WARD` `CASHIER` |
| `description` | string | — | Optional description |
| `max_concurrent_staff` | int | — | Max staff at once (default: 1) |
| `avg_service_minutes` | float | — | Used for ETA calculation (default: 5.0) |
| `is_active` | bool | — | Default: `true` |

**Response `201`:**
```json
{
  "id": "uuid",
  "org_id": "uuid",
  "name": "OPD Registration",
  "code": "OPD-REG",
  "point_type": "DESK",
  "description": null,
  "max_concurrent_staff": 3,
  "avg_service_minutes": 5.0,
  "is_active": true,
  "created_at": "2026-05-08T09:00:00Z",
  "updated_at": "2026-05-08T09:00:00Z"
}
```

---

### GET `/waiting/admin/service-points` — List Service Points

```http
GET /api/v1/waiting/admin/service-points?org_id={uuid}&active_only=true
```

| Query param | Type | Required | Description |
|-------------|------|----------|-------------|
| `org_id` | UUID | ✅ | Filter by organisation |
| `active_only` | bool | — | Default: `true` |

**Response `200`:** Array of `ServicePointOut`

---

### GET `/waiting/admin/service-points/{point_id}` — Get Service Point

```http
GET /api/v1/waiting/admin/service-points/{point_id}
```

**Response `200`:** `ServicePointOut`

---

### PATCH `/waiting/admin/service-points/{point_id}` — Update Service Point

**Request body** (all fields optional):
```json
{
  "name": "New Name",
  "code": "NEW-CODE",
  "description": "Updated",
  "point_type": "ROOM",
  "max_concurrent_staff": 5,
  "avg_service_minutes": 10.0,
  "is_active": false
}
```

**Response `200`:** Updated `ServicePointOut`

---

## 4. Admin — Service Flows

A ServiceFlow defines the journey a patient takes: which ServicePoints they visit and in what order.

---

### POST `/waiting/admin/flows` — Create Service Flow

**Request body:**
```json
{
  "org_id": "uuid",
  "name": "OPD Standard Flow",
  "description": "Registration → Triage → Doctor → Pharmacy",
  "is_default": true,
  "is_active": true,
  "steps": [
    { "service_point_id": "uuid-reg",  "step_order": 1 },
    { "service_point_id": "uuid-trg",  "step_order": 2 },
    { "service_point_id": "uuid-doc",  "step_order": 3 },
    { "service_point_id": "uuid-phm",  "step_order": 4 }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `org_id` | UUID | ✅ | Organisation ID |
| `name` | string | ✅ | Flow name |
| `steps` | array | ✅ | At least 1 step. Steps must have sequential `step_order` starting at 1 |
| `is_default` | bool | — | If `true`, this flow is used when no flow is specified |
| `is_active` | bool | — | Default: `true` |

**Step object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `service_point_id` | UUID | ✅ | Must be an active service point in the same org |
| `step_order` | int | ✅ | Sequential starting at 1 |
| `is_optional` | bool | — | Optional steps can be skipped |

**Response `201`:**
```json
{
  "id": "uuid",
  "org_id": "uuid",
  "name": "OPD Standard Flow",
  "description": "Registration → Triage → Doctor → Pharmacy",
  "is_active": true,
  "is_default": true,
  "created_at": "2026-05-08T09:00:00Z",
  "updated_at": "2026-05-08T09:00:00Z",
  "steps": [
    { "id": "uuid", "flow_id": "uuid", "service_point_id": "uuid", "step_order": 1, "is_optional": false }
  ]
}
```

---

### GET `/waiting/admin/flows` — List Flows

```http
GET /api/v1/waiting/admin/flows?org_id={uuid}&active_only=true
```

**Response `200`:** Array of `ServiceFlowOut` (includes steps)

---

### GET `/waiting/admin/flows/{flow_id}` — Get Flow

**Response `200`:** `ServiceFlowOut` with steps

---

### PATCH `/waiting/admin/flows/{flow_id}` — Update Flow

**Request body** (all optional):
```json
{
  "name": "Updated Flow Name",
  "description": "New description",
  "is_active": true,
  "is_default": false,
  "steps": [ ... ]
}
```

> Providing `steps` replaces all existing steps atomically.

**Response `200`:** Updated `ServiceFlowOut`

---

## 5. Admin — Staff Counters

A StaffCounter is a physical desk/window at a ServicePoint. Each counter handles one ticket at a time.

---

### POST `/waiting/admin/counters` — Create Counter

**Request body:**
```json
{
  "org_id": "uuid",
  "service_point_id": "uuid",
  "name": "Counter 1 – Registration",
  "code": "REG-C1",
  "user_id": "uuid-optional"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `org_id` | UUID | ✅ | Organisation ID |
| `service_point_id` | UUID | ✅ | ServicePoint this counter belongs to |
| `name` | string | ✅ | Display name |
| `code` | string | ✅ | Unique per service point (e.g. `REG-C1`) |
| `user_id` | UUID | — | Optionally assign a staff user to this counter |

**Response `201`:**
```json
{
  "id": "uuid",
  "org_id": "uuid",
  "service_point_id": "uuid",
  "name": "Counter 1 – Registration",
  "code": "REG-C1",
  "user_id": null,
  "is_active": true,
  "is_available": true,
  "current_ticket_id": null,
  "created_at": "2026-05-08T09:00:00Z",
  "updated_at": "2026-05-08T09:00:00Z"
}
```

---

### GET `/waiting/admin/counters` — List Counters

```http
GET /api/v1/waiting/admin/counters?service_point_id={uuid}&active_only=true
```

| Query param | Type | Required |
|-------------|------|----------|
| `service_point_id` | UUID | ✅ |
| `active_only` | bool | — |

**Response `200`:** Array of `StaffCounterOut`

---

### PATCH `/waiting/admin/counters/{counter_id}` — Update Counter

**Request body** (all optional):
```json
{
  "name": "New Name",
  "code": "NEW-C1",
  "user_id": "uuid",
  "is_active": false
}
```

**Response `200`:** Updated `StaffCounterOut`

---

## 6. Admin — Staff Sessions

A StaffSession represents a staff member opening a counter for a shift. The session tracks tickets served and average service time.

---

### POST `/waiting/admin/counters/{counter_id}/session/open` — Open Session

Opens a shift on the given counter. Only one active session per counter is allowed.

```http
POST /api/v1/waiting/admin/counters/{counter_id}/session/open
Authorization: Bearer <jwt>
Content-Type: application/json

{}
```

**Response `201`:**
```json
{
  "id": "uuid",
  "staff_counter_id": "uuid",
  "org_id": "uuid",
  "service_point_id": "uuid",
  "opened_at": "2026-05-08T08:00:00Z",
  "closed_at": null,
  "is_active": true,
  "tickets_served": 0,
  "avg_service_seconds": 0.0
}
```

**Errors:**

| Code | Meaning |
|------|---------|
| `SESSION_ALREADY_OPEN` | Counter already has an active session |

---

### POST `/waiting/admin/counters/{counter_id}/session/close` — Close Session

Closes the active shift. The counter becomes unavailable until a new session is opened.

```http
POST /api/v1/waiting/admin/counters/{counter_id}/session/close
Authorization: Bearer <jwt>
Content-Type: application/json

{}
```

**Response `200`:** `SessionOut` with `closed_at` set and `is_active: false`

---

## 7. Admin — Urgency Requests

Patients can submit urgency requests to request priority elevation. Staff review and approve or reject.

---

### GET `/waiting/admin/urgency-requests` — List Pending Requests

```http
GET /api/v1/waiting/admin/urgency-requests?org_id={uuid}&skip=0&limit=20
```

| Query param | Type | Required |
|-------------|------|----------|
| `org_id` | UUID | ✅ |
| `skip` | int | — |
| `limit` | int | — |

**Response `200`:** Array of urgency request objects

---

### POST `/waiting/admin/urgency-requests/{request_id}/review` — Review Urgency Request

Approve or reject a patient's urgency escalation.

**Request body:**
```json
{
  "status": "APPROVED",
  "reviewer_notes": "Patient confirmed high fever and difficulty breathing"
}
```

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `status` | string | ✅ | `APPROVED` `REJECTED` |
| `reviewer_notes` | string | — | Optional review notes |

**Response `200`:** Updated urgency request

> If `APPROVED`, the ticket's priority is elevated to `URGENT` automatically.

---

## 8. Queue — Patient Endpoints

These endpoints are called by kiosks, mobile apps, or SMS. No authentication required for joining the queue.

---

### POST `/waiting/join` — Join Queue

A patient joins the queue for a specific service flow.

```http
POST /api/v1/waiting/join
Content-Type: application/json
```

**Request body:**
```json
{
  "org_id": "uuid",
  "flow_id": "uuid",
  "submitter_name": "Amina Ally",
  "phone_number": "+255712901001",
  "channel": "KIOSK",
  "priority": "NORMAL",
  "external_id": null,
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `org_id` | UUID | ✅ | Organisation ID |
| `flow_id` | UUID | ✅ | Service flow to join |
| `submitter_name` | string | — | Patient name |
| `phone_number` | string | — | For SMS notifications (E.164 format) |
| `channel` | string | — | `KIOSK` `SMS` `APP` `STAFF_RECORDED` (default: `KIOSK`) |
| `priority` | string | — | `NORMAL` `HIGH` `URGENT` (default: `NORMAL`) |
| `external_id` | string | — | Optional external reference ID |
| `notes` | string | — | Optional notes |

**Response `201`:**
```json
{
  "id": "uuid",
  "ticket_number": "MNH-HOSP-20260508-0001",
  "org_id": "uuid",
  "flow_id": "uuid",
  "current_service_point_id": "uuid",
  "current_step_order": 1,
  "status": "WAITING",
  "priority": 2,
  "channel": "KIOSK",
  "position_in_queue": 3,
  "eta_minutes": 15.0,
  "created_at": "2026-05-08T09:00:00Z",
  "completed_at": null,
  "current_stage": { ... }
}
```

---

### GET `/waiting/ticket/{ticket_id}/status` — Get Ticket Status

Check position and ETA for a ticket. Public — no auth required.

```http
GET /api/v1/waiting/ticket/{ticket_id}/status
```

**Response `200`:**
```json
{
  "id": "uuid",
  "ticket_number": "MNH-HOSP-20260508-0001",
  "status": "WAITING",
  "priority": 2,
  "position_in_queue": 2,
  "eta_minutes": 10.0,
  "current_service_point_id": "uuid",
  "current_step_order": 1,
  "current_stage": {
    "id": "uuid",
    "service_point_id": "uuid",
    "step_order": 1,
    "status": "WAITING",
    "entered_queue_at": "2026-05-08T09:00:00Z",
    "attending_started_at": null,
    "wait_duration_seconds": null
  }
}
```

---

### POST `/waiting/ticket/{ticket_id}/cancel` — Cancel Ticket

Patient cancels their own ticket.

```http
POST /api/v1/waiting/ticket/{ticket_id}/cancel
Authorization: Bearer <jwt>   (optional — staff can also cancel)
```

**Response `200`:** Updated ticket with `status: CANCELLED`

---

### POST `/waiting/ticket/{ticket_id}/no-show` — Mark No-Show

Staff marks a patient as a no-show. Releases the counter.

**Request body:**
```json
{
  "staff_counter_id": "uuid"
}
```

**Response `200`:** Updated ticket with `status: NO_SHOW`

---

### POST `/waiting/ticket/{ticket_id}/urgency` — Submit Urgency Request

Patient or kiosk submits a request to escalate priority (e.g. medical emergency).

**Request body:**
```json
{
  "urgency_type": "MEDICAL_EMERGENCY",
  "evidence_notes": "Patient showing signs of respiratory distress"
}
```

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `urgency_type` | string | ✅ | `MEDICAL_EMERGENCY` `ELDERLY_DISABLED` `PREGNANT` `INFANT` `OTHER` |
| `evidence_notes` | string | — | Supporting description |

**Response `201`:** Urgency request object with `status: PENDING`

> Staff must review and approve via `POST /waiting/admin/urgency-requests/{id}/review`

---

## 9. Staff — Queue Operations

> **Auth:** JWT (org-scoped token) + staff role  
> **Base:** `https://api.riviwa.com/api/v1/waiting/staff`

---

### POST `/waiting/staff/call-next` — Call Next Ticket

Staff calls the next waiting ticket at a service point.

**Counter auto-resolution order:**
1. Explicit `staff_counter_id` if provided
2. Staff's active session counter (from JWT `sub`)
3. First available (idle) counter at the service point

**Request body:**
```json
{
  "service_point_id": "uuid",
  "staff_counter_id": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `service_point_id` | UUID | ✅ | Which point to call from |
| `staff_counter_id` | UUID | — | Explicit counter. Auto-resolved if omitted |

**Response `200`:**
```json
{
  "ticket": {
    "id": "uuid",
    "ticket_number": "MNH-HOSP-20260508-0003",
    "status": "ATTENDING",
    "priority": 0,
    "submitter_name": "Salma Omar",
    "phone_number": "+255712901003",
    "position_in_queue": null,
    "eta_minutes": null,
    "current_stage": { ... }
  },
  "stage": { ... },
  "message": "Now serving MNH-HOSP-20260508-0003"
}
```

> When no tickets are waiting, returns: `{ "ticket": null, "stage": null, "message": "No tickets waiting." }`

**Errors:**

| Code | Meaning |
|------|---------|
| `COUNTER_ALREADY_BUSY` | The counter is already serving a ticket |
| `NO_TICKETS_WAITING` | Queue is empty at this service point |
| `STAFF_COUNTER_NOT_FOUND` | No available counters — open a session first |

---

### POST `/waiting/staff/ticket/{ticket_id}/finish` — Finish Attending

Marks a ticket as completed at the current step.

- If the flow has a **next step**: ticket status → `WAITING`, ticket is placed in the next service point's queue automatically.
- If this is the **final step**: ticket status → `COMPLETED`.

**Request body:**
```json
{
  "staff_counter_id": null,
  "notes": "Registration complete. Directed to triage."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `staff_counter_id` | UUID | — | Auto-resolved from the ticket's assigned counter if omitted |
| `notes` | string | — | Staff notes for this stage |

**Response `200`:**
```json
{
  "is_final": false,
  "ticket": { ... },
  "next_point": {
    "id": "uuid",
    "name": "OPD Triage",
    "code": "OPD-TRG"
  },
  "message": "Advanced to: OPD Triage"
}
```

When final step:
```json
{
  "is_final": true,
  "ticket": { "status": "COMPLETED", ... },
  "next_point": null,
  "message": "Completed."
}
```

---

### POST `/waiting/staff/ticket/{ticket_id}/priority` — Set Priority

Change a waiting ticket's priority. Only works on `WAITING` tickets.

**Request body:**
```json
{
  "priority": "HIGH",
  "reason": "Elderly patient, difficulty standing"
}
```

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `priority` | string | ✅ | `NORMAL` `HIGH` `URGENT` |
| `reason` | string | — | Reason for priority change |

**Response `200`:** Updated ticket. Redis score is updated immediately — ticket moves up in queue.

---

### GET `/waiting/staff/queue/{service_point_id}` — View Queue

Get a live snapshot of the queue at a service point.

```http
GET /api/v1/waiting/staff/queue/{service_point_id}
Authorization: Bearer <jwt>
```

**Response `200`:**
```json
{
  "service_point": { "id": "uuid", "name": "OPD Registration", ... },
  "waiting": [
    {
      "id": "uuid",
      "ticket_number": "MNH-HOSP-20260508-0002",
      "status": "WAITING",
      "priority": 1,
      "position_in_queue": 1,
      "eta_minutes": 5.0,
      "submitter_name": "Ibrahim Nkusi",
      "current_stage": { ... }
    }
  ],
  "attending": [
    {
      "ticket_number": "MNH-HOSP-20260508-0003",
      "status": "ATTENDING",
      "position_in_queue": null,
      ...
    }
  ]
}
```

---

## 10. Waiting — Analytics Dashboard

> **Auth:** JWT (org-scoped token)

### GET `/waiting/analytics/dashboard` — Queue Dashboard

Real-time summary of queue status across all service points for an org.

```http
GET /api/v1/waiting/analytics/dashboard?org_id={uuid}
Authorization: Bearer <jwt>
```

**Response `200`:**
```json
{
  "org_id": "uuid",
  "generated_at": "2026-05-08T09:30:00Z",
  "total_waiting": 12,
  "total_attending": 4,
  "total_completed_today": 87,
  "service_points": [
    {
      "service_point_id": "uuid",
      "service_point_name": "OPD Registration",
      "point_type": "DESK",
      "waiting_count": 5,
      "attending_count": 2,
      "avg_wait_seconds": 420.0,
      "avg_service_seconds": 280.0,
      "throughput_today": 34
    }
  ]
}
```

---

## 11. Waiting — SMS Inbound

### POST `/waiting/sms/inbound` — Handle Inbound SMS

Receives inbound SMS from an SMS gateway (Africa's Talking, Twilio, etc.). Patients can text a ticket number or join command.

```http
POST /api/v1/waiting/sms/inbound
Content-Type: application/x-www-form-urlencoded

From=+255712901001&Body=STATUS+MNH-HOSP-20260508-0001
```

| Field | Description |
|-------|-------------|
| `From` | Sender phone number |
| `Body` | SMS body text |

**Supported commands via SMS:**

| Command | Action |
|---------|--------|
| `STATUS <ticket_number>` | Returns current position and ETA |
| `CANCEL <ticket_number>` | Cancels the ticket |

**Response `200`:** Empty or SMS provider ACK format

---

## 12. Analytics Service — Overview

The Analytics Service (port 8095) aggregates feedback data and provides dashboards at three scopes:

| Scope | Description |
|-------|-------------|
| **Org** | Metrics for a specific organisation |
| **Project** | Metrics scoped to a specific project |
| **Platform** | Metrics across all organisations (superadmin) |

> **Auth:** JWT (org-scoped token for org/project endpoints; superadmin for platform)  
> **Base:** `https://api.riviwa.com/api/v1/analytics`

---

## 13. Analytics — Organisation Level

All org endpoints: `GET /api/v1/analytics/org/{org_id}/...`

> Auth: JWT with active org context matching `org_id`

---

### GET `/analytics/org/{org_id}/summary`

Overall feedback summary for the organisation.

**Response `200`:**
```json
{
  "org_id": "uuid",
  "total_feedback": 120,
  "grievances": 45,
  "suggestions": 38,
  "applause": 30,
  "inquiries": 7,
  "pending": 22,
  "resolved_this_month": 18,
  "avg_resolution_days": 3.4
}
```

---

### GET `/analytics/org/{org_id}/by-project`
### GET `/analytics/org/{org_id}/by-period`
### GET `/analytics/org/{org_id}/by-channel`
### GET `/analytics/org/{org_id}/by-branch`
### GET `/analytics/org/{org_id}/by-department`
### GET `/analytics/org/{org_id}/by-service`
### GET `/analytics/org/{org_id}/by-category`

Breakdowns of feedback volume by the specified dimension.

**Query params (all optional):**

| Param | Description |
|-------|-------------|
| `period` | `day` `week` `month` `year` (for `by-period`) |
| `start_date` | ISO date filter |
| `end_date` | ISO date filter |

**Response `200`:** Array of `{ dimension_id, dimension_name, count, breakdown_by_type }` objects.

---

### GET `/analytics/org/{org_id}/grievances/summary`

Summary of grievances: open, escalated, overdue, resolved, avg resolution time.

### GET `/analytics/org/{org_id}/grievances/dashboard`

Full grievance dashboard including SLA compliance and escalation rates.

### GET `/analytics/org/{org_id}/grievances/sla`

SLA performance: on-time vs breached by severity.

### GET `/analytics/org/{org_id}/grievances/by-level`

Grievance count broken down by GRM escalation level.

### GET `/analytics/org/{org_id}/grievances/by-location`

Grievances mapped by `issue_lga` / `issue_ward` geographic fields.

---

### GET `/analytics/org/{org_id}/suggestions/summary`

Suggestions overview: submitted, under review, implemented, rejected.

### GET `/analytics/org/{org_id}/suggestions/by-project`

Suggestion volume per project.

---

### GET `/analytics/org/{org_id}/applause/summary`

Compliments overview: count, top categories, top staff/departments mentioned.

---

### GET `/analytics/org/{org_id}/inquiries/summary`

Inquiry overview: total, unread, overdue, avg response time.

---

## 14. Analytics — Project Level

All project endpoints require `?project_id={uuid}` as a query parameter.

> Auth: JWT with active org context

---

### GET `/analytics/feedback/unread?project_id={uuid}`

Feedback items submitted but not yet opened by staff.

### GET `/analytics/feedback/overdue?project_id={uuid}`

Feedback past the target resolution date.

### GET `/analytics/feedback/by-category?project_id={uuid}`
### GET `/analytics/feedback/by-branch?project_id={uuid}`
### GET `/analytics/feedback/by-department?project_id={uuid}`
### GET `/analytics/feedback/by-service?project_id={uuid}`
### GET `/analytics/feedback/by-product?project_id={uuid}`
### GET `/analytics/feedback/by-stage?project_id={uuid}`

Breakdowns of feedback for a project by the specified dimension.

---

### GET `/analytics/feedback/not-processed?project_id={uuid}`

Feedback in `submitted` status — received but not yet acknowledged.

### GET `/analytics/feedback/processed-today?project_id={uuid}`

Feedback acknowledged or actioned today.

### GET `/analytics/feedback/resolved-today?project_id={uuid}`

Feedback resolved today.

### GET `/analytics/feedback/time-to-open?project_id={uuid}`

Average hours between submission and first acknowledgement.

---

### GET `/analytics/grievances/unresolved?project_id={uuid}`

Grievances still open with age in days.

### GET `/analytics/grievances/sla-status?project_id={uuid}`

SLA status per grievance (on-track, at-risk, breached).

### GET `/analytics/grievances/dashboard?project_id={uuid}`

Full grievance dashboard for the project.

### GET `/analytics/grievances/hotspots?project_id={uuid}`

Geographic or category hotspots with highest grievance concentration.

---

### GET `/analytics/suggestions/frequency?project_id={uuid}`

Most frequently suggested topics/categories.

### GET `/analytics/suggestions/unread?project_id={uuid}`

Suggestions not yet reviewed.

### GET `/analytics/suggestions/implemented-today?project_id={uuid}`

Suggestions marked implemented today.

### GET `/analytics/suggestions/implemented-this-week?project_id={uuid}`

Suggestions implemented in the current week.

### GET `/analytics/suggestions/by-location?project_id={uuid}`

Suggestion volume by geographic area.

---

### GET `/analytics/inquiries/summary?project_id={uuid}`
### GET `/analytics/inquiries/unread?project_id={uuid}`
### GET `/analytics/inquiries/overdue?project_id={uuid}`
### GET `/analytics/inquiries/by-channel?project_id={uuid}`
### GET `/analytics/inquiries/by-category?project_id={uuid}`

Inquiry metrics for the project.

---

### GET `/analytics/staff/committee-performance?project_id={uuid}`

GRM committee metrics: assignments, avg resolution time, SLA compliance.

### GET `/analytics/staff/unread-assigned?project_id={uuid}`

Feedback assigned to staff but not yet read.

### GET `/analytics/staff/last-logins?project_id={uuid}`

Staff last-login times (for activity monitoring).

### GET `/analytics/staff/login-not-read?project_id={uuid}`

Staff who logged in but have unread assigned feedback.

---

## 15. Analytics — Platform Level

Platform-level endpoints aggregate across all organisations. Requires superadmin JWT.

> Base: `GET /api/v1/analytics/platform/...`

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/platform/summary` | Total feedback across all orgs |
| `GET /analytics/platform/by-org` | Breakdown per organisation |
| `GET /analytics/platform/by-period` | Volume over time |
| `GET /analytics/platform/by-channel` | Channel distribution |
| `GET /analytics/platform/by-branch` | Branch-level aggregation |
| `GET /analytics/platform/by-department` | Department-level aggregation |
| `GET /analytics/platform/by-service` | Service-level aggregation |
| `GET /analytics/platform/by-product` | Product-level aggregation |
| `GET /analytics/platform/by-category` | Category breakdown |
| `GET /analytics/platform/grievances/summary` | Platform grievance totals |
| `GET /analytics/platform/grievances/dashboard` | Full grievance dashboard |
| `GET /analytics/platform/grievances/sla` | SLA compliance across all orgs |
| `GET /analytics/platform/suggestions/summary` | Platform suggestion totals |
| `GET /analytics/platform/applause/summary` | Platform compliment totals |
| `GET /analytics/platform/inquiries/summary` | Platform inquiry totals |

---

## 16. Analytics — AI Insights

> Auth: JWT

### POST `/analytics/ai/ask` — Ask AI a Question

Submit a natural-language question about feedback data for the org.

```http
POST /api/v1/analytics/ai/ask
Authorization: Bearer <jwt>
Content-Type: application/json
```

**Request body:**
```json
{
  "question": "What are the top 3 issues patients face and how can we improve?",
  "org_id": "uuid",
  "scope": "org"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | ✅ | Natural language question |
| `org_id` | UUID | ✅ | Organisation to analyse |
| `scope` | string | ✅ | `org` — org-level analysis |

**Response `200`:**
```json
{
  "question": "What are the top 3 issues patients face?",
  "answer": "Based on the feedback data: 1) Long waiting times in OPD (38% of grievances)...",
  "data_points_used": 45,
  "generated_at": "2026-05-08T09:00:00Z"
}
```

---

### POST `/analytics/ai/ask-voice` — Ask via Voice

Accepts a voice recording, transcribes it, and returns an AI answer.

```http
POST /api/v1/analytics/ai/ask-voice
Authorization: Bearer <jwt>
Content-Type: multipart/form-data

audio=<binary file>
org_id=<uuid>
```

**Response `200`:** Same as `/ai/ask` plus `transcription` field.

---

## 17. End-to-End Flows

### Flow A — Hospital OPD Queue (Full Journey)

```
1. Admin setup (once)
   POST /waiting/admin/service-points  → create REG, TRIAGE, DOCTOR, PHARMACY points
   POST /waiting/admin/flows           → create flow linking all 4 points
   POST /waiting/admin/counters        → create 1+ counters per point
   POST /waiting/admin/counters/{id}/session/open → staff opens shift

2. Patients arrive (kiosk / mobile)
   POST /waiting/join → returns ticket number + position

3. Patients check status
   GET  /waiting/ticket/{id}/status → position + ETA

4. Staff at Registration calls next
   POST /waiting/staff/call-next { service_point_id: "REG" }
   → returns highest-priority waiting ticket (URGENT first)

5. Staff finishes Registration
   POST /waiting/staff/ticket/{id}/finish { notes: "Registered" }
   → ticket auto-advances to TRIAGE queue

6. Same process repeats at TRIAGE → DOCTOR → PHARMACY

7. Final step finish
   POST /waiting/staff/ticket/{id}/finish
   → { is_final: true, message: "Completed." }

8. Staff ends shift
   POST /waiting/admin/counters/{id}/session/close
```

---

### Flow B — Priority Escalation

```
1. Patient joins with NORMAL priority
   POST /waiting/join { priority: "NORMAL" }

2. Patient submits urgency request (e.g. chest pain)
   POST /waiting/ticket/{id}/urgency { urgency_type: "MEDICAL_EMERGENCY" }

3. Staff reviews and approves
   POST /waiting/admin/urgency-requests/{id}/review { status: "APPROVED" }
   → ticket priority elevated to URGENT automatically

4. Next call-next at this service point will serve this ticket first
```

---

### Flow C — Analytics Query

```
1. Get org summary
   GET /analytics/org/{org_id}/summary

2. Drill into grievances
   GET /analytics/org/{org_id}/grievances/dashboard

3. Check SLA compliance
   GET /analytics/org/{org_id}/grievances/sla

4. Ask AI for insights
   POST /analytics/ai/ask { question: "...", org_id: "...", scope: "org" }
```

---

## 18. Enumerations Reference

### Ticket Status

| Value | Description |
|-------|-------------|
| `WAITING` | In queue, not yet called |
| `ATTENDING` | Currently being served at a counter |
| `COMPLETED` | Finished all flow steps |
| `CANCELLED` | Cancelled by patient or staff |
| `NO_SHOW` | Patient didn't appear when called |

### Ticket Priority

| Value | Int | Queue position |
|-------|-----|---------------|
| `URGENT` | 0 | First |
| `HIGH` | 1 | Second |
| `NORMAL` | 2 | Last |

### Ticket Channel

| Value | Description |
|-------|-------------|
| `KIOSK` | Walk-in self-service kiosk |
| `SMS` | Joined via SMS |
| `APP` | Mobile/web application |
| `STAFF_RECORDED` | Manually added by staff |

### Service Point Type

| Value | Typical use |
|-------|-------------|
| `DESK` | Open desk (registration, triage) |
| `COUNTER` | Closed counter (pharmacy, cashier) |
| `ROOM` | Consultation room (doctor, nurse) |
| `KIOSK` | Self-service kiosk |
| `STAGE` | Processing stage |
| `WARD` | Inpatient ward |
| `CASHIER` | Payment cashier |

### Urgency Type

| Value |
|-------|
| `MEDICAL_EMERGENCY` |
| `ELDERLY_DISABLED` |
| `PREGNANT` |
| `INFANT` |
| `OTHER` |

### Stage Status

| Value | Description |
|-------|-------------|
| `WAITING` | In queue for this step |
| `ATTENDING` | Being served at this step |
| `FINISHED` | Completed this step |

---

## 19. Error Responses

All errors follow this format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description"
}
```

### Waiting Service Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `ORG_NOT_FOUND` | 404 | Organisation not in waiting service cache |
| `SERVICE_POINT_NOT_FOUND` | 404 | Service point not found or wrong org |
| `SERVICE_FLOW_NOT_FOUND` | 404 | Flow not found |
| `TICKET_NOT_FOUND` | 404 | Ticket not found |
| `COUNTER_ALREADY_BUSY` | 409 | Counter is serving a ticket |
| `NO_TICKETS_WAITING` | 200 | Queue is empty (not an error, returns gracefully) |
| `TICKET_NOT_WAITING` | 409 | Ticket is not in WAITING status |
| `SESSION_ALREADY_OPEN` | 409 | Counter already has an active session |
| `STAFF_COUNTER_NOT_FOUND` | 404 | No available counters at this service point |
| `FORBIDDEN` | 403 | Wrong org or insufficient role |

### Analytics Service Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `FORBIDDEN` | 403 | Switch to an active organisation first |
| `VALIDATION_ERROR` | 422 | Missing required query param (e.g. `project_id`) |
| `INTERNAL_ERROR` | 500 | Server-side error |

---

*Document covers: `waiting_service` (port 8130) and `analytics_service` (port 8095)*  
*Previous document: `RIVIWA_PRODUCT_QR_VERICATION.md` covers `product_service`, `qr_service`, `verification_service`*
