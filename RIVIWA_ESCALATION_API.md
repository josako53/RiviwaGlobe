# Riviwa Escalation API — Full Reference

**Service:** `feedback_service` · Port `8090`  
**Base URL:** `https://api.riviwa.com`  
**Version:** v2.5 (Escalation v2 — org-dynamic paths)  
**Date:** 2026-05-11

---

## Overview

Riviwa's escalation system has two distinct layers:

| Layer | Purpose | Who uses it |
|-------|---------|------------|
| **Path Management** | Configure the GRM hierarchy (levels, SLAs, routing) | Org admins at setup time |
| **Lifecycle Actions** | Act on individual feedback (escalate, request, approve, appeal) | Staff & consumers day-to-day |

### How it works end-to-end

```
Org Admin                  GRM Officer             Consumer
─────────────────────────────────────────────────────────────
1. Create escalation path    
   (quick-setup / custom)
   Define 2–6 levels with
   SLAs, notify emails,
   auto-escalation rules
            │
            ▼
2. Feedback submitted ───────► 3. Staff escalates
   (by consumer or staff)         POST /feedback/{id}/escalate
                                  → to_level: "lga_grm_unit"
                                  → reason: "..."

                              OR

                 ◄────────── 4. Consumer requests escalation
                                POST /my/feedback/{id}/escalation-request

                             5. Staff reviews request
                                GET  /escalation-requests
                                POST /escalation-requests/{id}/approve
                                POST /escalation-requests/{id}/reject

                             6. If consumer unhappy with resolution:
                ◄────────── POST /my/feedback/{id}/appeal
```

---

## Authentication

All endpoints require a Bearer JWT.

```
Authorization: Bearer <access_token>
```

### Role levels (lowest → highest)

| Role | Org role value | Can do |
|------|---------------|--------|
| `StaffDep` | manager / admin / owner | Read escalation paths, list requests |
| `GRMOfficerDep` | manager / admin / owner | Escalate feedback, manage levels |
| `GRMCoordinatorDep` | admin / owner | Create / update / delete paths |
| `ConsumerDep` | Consumer JWT (no org role) | Request escalation, file appeal |

---

## Part 1 — Escalation Path Management

Configure the GRM hierarchy for your organisation. Do this once at setup, then update as your org structure changes.

---

### `GET /api/v1/escalation-paths/available-templates`

List all 6 built-in template types with descriptions and recommended org types.

**Auth:** `StaffDep` (manager+)

**No request body or query params required.**

**Response `200`:**
```json
[
  {
    "template_key": "SIMPLE_2_LEVEL",
    "display_name": "Simple 2-Level",
    "description": "Two-level hierarchy: front-line and management. Suitable for small orgs or single-branch businesses.",
    "org_types_hint": ["BUSINESS", "NGO", "INDIVIDUAL_PRO"],
    "level_count": 2
  },
  {
    "template_key": "CORPORATE_3_TIER",
    "display_name": "Corporate 3-Tier",
    "description": "Branch → Regional → HQ. Standard for multi-branch corporates.",
    "org_types_hint": ["CORPORATE", "BUSINESS"],
    "level_count": 3
  },
  {
    "template_key": "CUSTOMER_SERVICE_3_LEVEL",
    "display_name": "Customer Service 3-Level",
    "description": "Front-line agent → Team leader → Manager. Designed for customer-facing service teams.",
    "org_types_hint": ["BUSINESS", "CORPORATE"],
    "level_count": 3
  },
  {
    "template_key": "HEALTHCARE_4_LEVEL",
    "display_name": "Healthcare 4-Level",
    "description": "Clinician → Department Head → Hospital Management → Board. Matches hospital governance chains.",
    "org_types_hint": ["GOVERNMENT", "NGO"],
    "level_count": 4
  },
  {
    "template_key": "NGO_FIELD_3_LEVEL",
    "display_name": "NGO / CBO 3-Level",
    "description": "Field Officer → Programme Manager → Executive Director.",
    "org_types_hint": ["NGO"],
    "level_count": 3
  },
  {
    "template_key": "GOVT_GRM_STANDARD",
    "display_name": "TARURA / TANROADS GRM (Tanzania Default)",
    "description": "Full 6-level Tanzania GRM chain: Ward → LGA PIU → Coordinating Unit → TARURA WBCU → TANROADS → World Bank.",
    "org_types_hint": ["GOVERNMENT"],
    "level_count": 6
  }
]
```

---

### `POST /api/v1/escalation-paths/quick-setup`

**One-call wizard.** Pick a template, name the path, and optionally customise any levels. The fastest way to configure escalation for a new org.

**Auth:** `GRMCoordinatorDep` (admin / owner)

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Name for the new path |
| `template_key` | string | ✅ | Built-in template to clone (from `GET /available-templates`) |
| `set_as_default` | bool | — | Default: `true`. Makes this the org's active escalation path |
| `applies_to_feedback_types` | string[] | — | `grievance` / `suggestion` / `applause` / `inquiry`. Null = all types |
| `level_customizations` | object[] | — | Per-level overrides on top of template defaults (see below) |

**`level_customizations` fields** (all optional — only supply what you want to change):

| Field | Type | Description |
|-------|------|-------------|
| `level_order` | int | ✅ Which template level to customise (1-based) |
| `name` | string | Override level name |
| `consumer_visible_name` | string | Name shown to the feedback submitter |
| `description` | string | — |
| `ack_sla_hours` | int | Hours to acknowledge |
| `resolution_sla_hours` | int | Hours to resolve |
| `auto_escalate_on_breach` | bool | Auto-escalate when SLA breaches |
| `auto_escalate_after_hours` | int | Hours after SLA breach before auto-escalation fires |
| `notify_emails` | string[] | Emails notified when feedback reaches this level |
| `responsible_org_unit` | object | Link to org structure: `{department_id, branch_id, user_ids, committee_id}` |
| `is_final` | bool | Mark as top level (no further escalation) |

**Request example:**
```json
POST /api/v1/escalation-paths/quick-setup

{
  "name": "Yas Tanzania Customer Escalation",
  "template_key": "CUSTOMER_SERVICE_3_LEVEL",
  "set_as_default": true,
  "applies_to_feedback_types": ["grievance"],
  "level_customizations": [
    {
      "level_order": 1,
      "name": "Customer Care",
      "consumer_visible_name": "Customer Support Team",
      "resolution_sla_hours": 24,
      "notify_emails": ["customercare@yas.co.tz"],
      "responsible_org_unit": {
        "department_id": "afd5b4e2-10f5-4874-b1da-248a74091805"
      }
    },
    {
      "level_order": 2,
      "name": "CC Manager",
      "auto_escalate_on_breach": true,
      "auto_escalate_after_hours": 48,
      "notify_emails": ["cc.manager@yas.co.tz"],
      "responsible_org_unit": {
        "user_ids": ["5183174a-bcad-4e68-bf06-700d1f1260dc"]
      }
    },
    {
      "level_order": 3,
      "name": "CEO Office",
      "consumer_visible_name": "Senior Leadership",
      "notify_emails": ["ceo@yas.co.tz"],
      "is_final": true
    }
  ]
}
```

**Response `201`:** Full `EscalationPathResponse` (see [Path Response Schema](#path-response-schema)).

---

### `POST /api/v1/escalation-paths`

Create a fully custom escalation path. Define levels inline or add them one by one later.

**Auth:** `GRMCoordinatorDep`

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | — |
| `description` | string | — | — |
| `project_id` | UUID | — | Scope path to a specific project. Null = org-wide |
| `is_default` | bool | — | Set as the org's active path. Clears previous default |
| `applies_to_feedback_types` | string[] | — | Null = all types |
| `levels` | object[] | — | Inline level definitions (`EscalationLevelCreate[]`) |

**`EscalationLevelCreate` fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `level_order` | int (≥1) | ✅ | Position in chain. `1` = entry point |
| `name` | string | ✅ | Display name e.g. `"Ward GHC"` |
| `code` | string | ✅ | Slug unique within path e.g. `"ward_ghc"` |
| `description` | string | — | — |
| `is_final` | bool | — | No further escalation from this level |
| `ack_sla_hours` | int | — | Hours to acknowledge |
| `resolution_sla_hours` | int | — | Hours to resolve |
| `sla_overrides` | object | — | Per-priority SLA overrides (see below) |
| `auto_escalate_on_breach` | bool | — | Default: `false` |
| `auto_escalate_after_hours` | int | — | Hours after SLA breach before auto-escalation |
| `responsible_role` | string | — | Role responsible at this level |
| `notify_emails` | string[] | — | Notified when escalation reaches this level |
| `responsible_org_unit` | object | — | `{department_id, branch_id, user_ids, committee_id}` |
| `consumer_visible_name` | string | — | Label shown to submitter (hides internal org terms) |
| `grm_level_ref` | string | — | Legacy enum link: `ward / lga_grm_unit / coordinating_unit / tarura_wbcu / tanroads / world_bank` |

**`sla_overrides` structure:**
```json
{
  "critical": { "ack_hours": 24,  "resolution_hours": 168 },
  "high":     { "ack_hours": 48,  "resolution_hours": 336 },
  "medium":   { "ack_hours": 120, "resolution_hours": 720 },
  "low":      { "ack_hours": 240, "resolution_hours": null }
}
```
Overrides `ack_sla_hours`/`resolution_sla_hours` for that priority. `null` = no SLA for that priority.

**Request example:**
```json
POST /api/v1/escalation-paths

{
  "name": "MNH Patient Complaint Chain",
  "description": "4-level hospital escalation for patient grievances.",
  "is_default": true,
  "applies_to_feedback_types": ["grievance", "inquiry"],
  "levels": [
    {
      "level_order": 1,
      "name": "Department Head",
      "code": "dept_head",
      "ack_sla_hours": 48,
      "resolution_sla_hours": 168,
      "auto_escalate_on_breach": true,
      "auto_escalate_after_hours": 192,
      "notify_emails": ["complaints@mnh.go.tz"],
      "responsible_org_unit": { "department_id": "uuid" },
      "grm_level_ref": "ward"
    },
    {
      "level_order": 2,
      "name": "Hospital Management",
      "code": "hospital_mgmt",
      "resolution_sla_hours": 336,
      "sla_overrides": {
        "critical": { "ack_hours": 24, "resolution_hours": 72 }
      },
      "notify_emails": ["cmo@mnh.go.tz"],
      "grm_level_ref": "lga_grm_unit"
    },
    {
      "level_order": 3,
      "name": "MOHCDGEC",
      "code": "moh",
      "notify_emails": ["grm@health.go.tz"],
      "grm_level_ref": "coordinating_unit"
    },
    {
      "level_order": 4,
      "name": "World Bank",
      "code": "world_bank",
      "is_final": true,
      "grm_level_ref": "world_bank"
    }
  ]
}
```

**Response `201`:** `EscalationPathResponse`

---

### `POST /api/v1/escalation-paths/from-template`

Clone a system template (or any other path) into a fully editable org copy. All levels are deep-copied.

**Auth:** `GRMCoordinatorDep`

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `template_id` | UUID | ✅ | UUID of the source path or system template |
| `name` | string | ✅ | Name for the cloned path |
| `set_as_default` | bool | — | Make this the org's default. Default: `false` |

```json
POST /api/v1/escalation-paths/from-template

{
  "template_id": "uuid-of-GOVT_GRM_STANDARD-template",
  "name": "Our TARURA GRM Chain",
  "set_as_default": true
}
```

**Response `201`:** `EscalationPathResponse`

---

### `GET /api/v1/escalation-paths`

List all active escalation paths for the current organisation.

**Auth:** `StaffDep`

**No query params.**

**Response `200`:**
```json
{
  "total": 2,
  "items": [ <EscalationPathResponse>, ... ]
}
```

---

### `GET /api/v1/escalation-paths/system-templates`

List all 6 read-only system templates. Clone one to create an editable org copy.

**Auth:** `StaffDep`

**Response `200`:** `EscalationPathResponse[]`

---

### `GET /api/v1/escalation-paths/{path_id}`

Get a single escalation path with all its levels, ordered by `level_order`.

**Auth:** `StaffDep`

**Response `200`:** `EscalationPathResponse`

**Error responses:**

| Status | Condition |
|--------|-----------|
| 404 | Path not found |

---

### `PATCH /api/v1/escalation-paths/{path_id}`

Update path metadata. Cannot modify system templates. All fields optional.

**Auth:** `GRMCoordinatorDep`

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | — |
| `description` | string | — |
| `is_default` | bool | Setting `true` clears the previous org default |
| `is_active` | bool | `false` to soft-deactivate |
| `applies_to_feedback_types` | string[] | — |

```json
PATCH /api/v1/escalation-paths/uuid

{
  "name": "Yas Customer Escalation v2",
  "is_default": true,
  "applies_to_feedback_types": ["grievance", "inquiry"]
}
```

**Response `200`:** `EscalationPathResponse`

---

### `DELETE /api/v1/escalation-paths/{path_id}`

Soft-deactivate a path (`is_active → false`). System templates cannot be deleted.

**Auth:** `GRMCoordinatorDep`

**Response `204 No Content`**

---

### `POST /api/v1/escalation-paths/{path_id}/levels`

Add a new level to an existing path.

**Auth:** `GRMOfficerDep` (manager+)

**Request body:** `EscalationLevelCreate` (all fields listed in [POST /escalation-paths](#post-apiv1escalation-paths)).

`level_order` must be unique within the path. Use `POST .../levels/reorder` first if needed.

**Response `201`:** `EscalationLevelResponse`

---

### `POST /api/v1/escalation-paths/{path_id}/levels/reorder`

Reassign `level_order` values across all levels by supplying all level IDs in the desired sequence.

**Auth:** `GRMOfficerDep`

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ordered_level_ids` | UUID[] | ✅ | All level IDs in desired order. First → `level_order=1` |

All level IDs belonging to this path must be included.

```json
POST /api/v1/escalation-paths/uuid/levels/reorder

{
  "ordered_level_ids": [
    "uuid-of-old-level-3",
    "uuid-of-old-level-1",
    "uuid-of-old-level-2"
  ]
}
```

**Response `200`:** Full `EscalationPathResponse` with updated `level_order` values on all levels.

---

### `PATCH /api/v1/escalation-paths/{path_id}/levels/{level_id}`

Update any field on a level. All fields optional.

**Auth:** `GRMOfficerDep`

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | — |
| `description` | string | — |
| `is_final` | bool | — |
| `ack_sla_hours` | int | — |
| `resolution_sla_hours` | int | — |
| `sla_overrides` | object | Per-priority SLA overrides |
| `auto_escalate_on_breach` | bool | — |
| `auto_escalate_after_hours` | int | — |
| `responsible_role` | string | — |
| `notify_emails` | string[] | — |
| `responsible_org_unit` | object | `{department_id, branch_id, user_ids, committee_id}` |
| `consumer_visible_name` | string | — |
| `grm_level_ref` | string | Legacy GRM level reference |

```json
PATCH /api/v1/escalation-paths/uuid/levels/uuid

{
  "name": "Regional Customer Manager",
  "resolution_sla_hours": 72,
  "auto_escalate_on_breach": true,
  "auto_escalate_after_hours": 96,
  "notify_emails": ["regional.manager@yas.co.tz"],
  "sla_overrides": {
    "critical": { "ack_hours": 12, "resolution_hours": 48 }
  }
}
```

**Response `200`:** `EscalationLevelResponse`

---

### `DELETE /api/v1/escalation-paths/{path_id}/levels/{level_id}`

Hard-delete a level row. Reorder the remaining levels afterwards to close the gap.

**Auth:** `GRMOfficerDep`

**Response `204 No Content`**

---

## Part 2 — Escalation Lifecycle Actions

Act on individual feedback items — staff escalating, consumers requesting, approvals, appeals.

---

### `POST /api/v1/feedback/{feedback_id}/escalate`

Staff escalates a feedback item to a higher GRM level.

**Auth:** `GRMOfficerDep` (manager+)

**Path param:** `feedback_id` — UUID of the feedback record

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to_level` | string | ✅ | Target GRM level (see values below) |
| `reason` | string (≥10 chars) | ✅ | Documented reason for audit trail |
| `escalated_to_committee_id` | UUID | — | GHC committee at the target level |

**`to_level` values:**

| Value | Description |
|-------|-------------|
| `ward` | Ward GRM Committee (GHC) |
| `lga_grm_unit` | LGA Project Implementation Unit |
| `coordinating_unit` | Coordinating Unit (PCU) |
| `tarura_wbcu` | TARURA World Bank Coordination Unit |
| `tanroads` | TANROADS Central GRM |
| `world_bank` | World Bank (final level) |

```json
POST /api/v1/feedback/uuid/escalate

{
  "to_level": "lga_grm_unit",
  "reason": "Ward GHC unable to resolve within 30 days. Land valuation dispute requires district-level intervention.",
  "escalated_to_committee_id": "uuid-optional"
}
```

**Response `200`:** Full feedback object. Key updated fields:

```json
{
  "status": "escalated",
  "current_level": "lga_grm_unit",
  "escalations": [
    {
      "id": "uuid",
      "from_level": "ward",
      "to_level": "lga_grm_unit",
      "reason": "Ward GHC unable to resolve within 30 days...",
      "escalated_by_user_id": "uuid",
      "escalated_at": "2026-05-11T09:00:00Z",
      "committee_id": "uuid"
    }
  ]
}
```

**Error responses:**

| Status | Error | Condition |
|--------|-------|-----------|
| 404 | `FEEDBACK_NOT_FOUND` | Feedback ID does not exist |
| 403 | `FORBIDDEN` | Feedback belongs to a different org |
| 422 | Validation error | `to_level` is not a valid enum value |

---

### `POST /api/v1/my/feedback/{feedback_id}/escalation-request`

Consumer requests the GRM Unit to escalate their grievance. A staff member must then approve or reject.

**Auth:** Consumer JWT

**Path param:** `feedback_id` — UUID of the consumer's own feedback

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string (≥10 chars) | ✅ | Why the consumer wants escalation |
| `requested_level` | string | — | Optional preferred level. GRM Unit makes the final decision |

```json
POST /api/v1/my/feedback/uuid/escalation-request

{
  "reason": "It has been 45 days with no response despite three follow-ups. I need this escalated urgently.",
  "requested_level": "lga_grm_unit"
}
```

**Response `201`:**
```json
{
  "id": "uuid",
  "status": "pending",
  "message": "Your escalation request has been submitted. The GRM Unit will review it and either approve (and escalate your case) or explain why escalation is not applicable at this stage."
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| 404 | Feedback not found or not owned by this consumer |
| 409 | A pending escalation request already exists for this feedback |

---

### `GET /api/v1/escalation-requests`

Staff lists consumer escalation requests, filterable by status and project.

**Auth:** `StaffDep` (any staff)

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | string | `pending` | `pending` / `approved` / `rejected` |
| `project_id` | UUID | — | Filter to a specific project |
| `skip` | int | `0` | Pagination offset |
| `limit` | int | `50` | Max `200` |

```
GET /api/v1/escalation-requests?status=pending&project_id=uuid&limit=20
```

**Response `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "feedback_id": "uuid",
      "status": "pending",
      "reason": "45 days with no response",
      "requested_level": "lga_grm_unit",
      "requested_by_user_id": "uuid",
      "requested_by_stakeholder_id": null,
      "reviewer_notes": null,
      "reviewed_by_user_id": null,
      "reviewed_at": null,
      "created_at": "2026-05-11T08:00:00Z"
    }
  ],
  "count": 1
}
```

---

### `POST /api/v1/escalation-requests/{request_id}/approve`

Staff approves a consumer's escalation request. The linked feedback is automatically escalated.

**Auth:** `StaffDep` (any staff)

**Path param:** `request_id` — UUID of the escalation request

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `notes` | string | — | Approval notes (internal, not visible to consumer) |

```json
POST /api/v1/escalation-requests/uuid/approve

{
  "notes": "Justified — unresolved for 45 days. Escalating to LGA GRM Unit."
}
```

**Response `200`:**
```json
{
  "status": "approved",
  "message": "Escalation request approved.",
  "feedback_id": "uuid"
}
```

The linked feedback `status` changes to `escalated` and `current_level` advances.

---

### `POST /api/v1/escalation-requests/{request_id}/reject`

Staff rejects a consumer's escalation request. The rejection notes are visible to the consumer.

**Auth:** `StaffDep` (any staff)

**Path param:** `request_id` — UUID of the escalation request

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `notes` | string (≥5 chars) | ✅ | Reason for rejection — **shown to the consumer** |

```json
POST /api/v1/escalation-requests/uuid/reject

{
  "notes": "Case is actively under investigation. A resolution is expected within 7 days. Please allow the process to proceed."
}
```

**Response `200`:**
```json
{
  "status": "rejected",
  "message": "Escalation request rejected. The Consumer has been notified."
}
```

The consumer receives a notification with the `notes` explaining why their request was not approved.

---

### `POST /api/v1/my/feedback/{feedback_id}/appeal`

Consumer files a formal appeal after receiving an unsatisfactory resolution. The case is automatically re-escalated one level.

**Auth:** Consumer JWT

**Path param:** `feedback_id` — UUID of the consumer's own feedback (must be in `resolved` status)

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grounds` | string (≥10 chars) | ✅ | Grounds for the appeal |

```json
POST /api/v1/my/feedback/uuid/appeal

{
  "grounds": "The proposed compensation does not reflect market value. Independent valuation shows my land is worth TZS 45M, not the TZS 28M offered."
}
```

**Response `201`:**
```json
{
  "appeal_id": "uuid",
  "status": "appealed",
  "now_at_level": "lga_grm_unit",
  "message": "Your appeal has been filed. Your case has been escalated to LGA GRM UNIT for review. If you remain unsatisfied after the appeal outcome, you have the right to seek resolution through the courts."
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| 404 | Feedback not found or not owned by this consumer |
| 422 | Feedback is not in `resolved` status (can only appeal a resolved case) |

---

## Part 3 — Response Schemas

### Path Response Schema

```json
{
  "id": "uuid",
  "org_id": "uuid",
  "project_id": "uuid or null",
  "name": "Yas Tanzania Customer Escalation",
  "description": "3-level customer service escalation",
  "is_default": true,
  "is_system_template": false,
  "is_active": true,
  "template_key": "CUSTOMER_SERVICE_3_LEVEL",
  "applies_to_feedback_types": ["grievance"],
  "created_by_user_id": "uuid",
  "created_at": "2026-05-11T10:00:00Z",
  "updated_at": "2026-05-11T10:00:00Z",
  "levels": [
    {
      "id": "uuid",
      "path_id": "uuid",
      "level_order": 1,
      "name": "Customer Care",
      "code": "customer_care",
      "description": null,
      "is_final": false,
      "ack_sla_hours": 48,
      "resolution_sla_hours": 24,
      "sla_overrides": {
        "critical": { "ack_hours": 12, "resolution_hours": 48 }
      },
      "auto_escalate_on_breach": true,
      "auto_escalate_after_hours": 72,
      "responsible_role": null,
      "notify_emails": ["customercare@yas.co.tz"],
      "responsible_org_unit": {
        "department_id": "afd5b4e2-..."
      },
      "consumer_visible_name": "Customer Support Team",
      "grm_level_ref": "ward",
      "created_at": "2026-05-11T10:00:00Z",
      "updated_at": "2026-05-11T10:00:00Z"
    },
    {
      "id": "uuid",
      "path_id": "uuid",
      "level_order": 2,
      "name": "CC Manager",
      "code": "cc_manager",
      "is_final": false,
      "ack_sla_hours": null,
      "resolution_sla_hours": null,
      "sla_overrides": null,
      "auto_escalate_on_breach": true,
      "auto_escalate_after_hours": 48,
      "notify_emails": ["cc.manager@yas.co.tz"],
      "responsible_org_unit": {
        "user_ids": ["5183174a-..."]
      },
      "consumer_visible_name": null,
      "grm_level_ref": "lga_grm_unit",
      "created_at": "...", "updated_at": "..."
    },
    {
      "id": "uuid",
      "path_id": "uuid",
      "level_order": 3,
      "name": "CEO Office",
      "code": "ceo_office",
      "is_final": true,
      "auto_escalate_on_breach": false,
      "notify_emails": ["ceo@yas.co.tz"],
      "consumer_visible_name": "Senior Leadership",
      "grm_level_ref": "world_bank",
      "created_at": "...", "updated_at": "..."
    }
  ]
}
```

---

## Part 4 — Quick Reference

### All endpoints at a glance

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/escalation-paths/available-templates` | Staff | List built-in template options |
| `POST` | `/escalation-paths/quick-setup` | Coordinator | One-call wizard from template |
| `POST` | `/escalation-paths` | Coordinator | Create custom path with inline levels |
| `POST` | `/escalation-paths/from-template` | Coordinator | Clone existing path/template |
| `GET` | `/escalation-paths` | Staff | List org's active paths |
| `GET` | `/escalation-paths/system-templates` | Staff | List read-only system templates |
| `GET` | `/escalation-paths/{path_id}` | Staff | Get path with all levels |
| `PATCH` | `/escalation-paths/{path_id}` | Coordinator | Update path metadata |
| `DELETE` | `/escalation-paths/{path_id}` | Coordinator | Deactivate path (soft delete) |
| `POST` | `/escalation-paths/{path_id}/levels` | Officer | Add level to path |
| `POST` | `/escalation-paths/{path_id}/levels/reorder` | Officer | Reorder all levels |
| `PATCH` | `/escalation-paths/{path_id}/levels/{level_id}` | Officer | Update level |
| `DELETE` | `/escalation-paths/{path_id}/levels/{level_id}` | Officer | Remove level |
| `POST` | `/feedback/{feedback_id}/escalate` | Officer | Staff escalates feedback |
| `POST` | `/my/feedback/{feedback_id}/escalation-request` | Consumer | Consumer requests escalation |
| `GET` | `/escalation-requests` | Staff | List consumer escalation requests |
| `POST` | `/escalation-requests/{request_id}/approve` | Staff | Approve and escalate |
| `POST` | `/escalation-requests/{request_id}/reject` | Staff | Reject with explanation |
| `POST` | `/my/feedback/{feedback_id}/appeal` | Consumer | File formal appeal |

### `to_level` / `grm_level_ref` values

| Value | Description |
|-------|-------------|
| `ward` | Ward GRM Committee (GHC) — entry level |
| `lga_grm_unit` | LGA Project Implementation Unit |
| `coordinating_unit` | Coordinating Unit (PCU) |
| `tarura_wbcu` | TARURA World Bank Coordination Unit |
| `tanroads` | TANROADS Central GRM |
| `world_bank` | World Bank — final level |

### Built-in template keys

| Key | Levels | Best for |
|-----|--------|---------|
| `SIMPLE_2_LEVEL` | 2 | Small orgs, single-branch |
| `CORPORATE_3_TIER` | 3 | Multi-branch corporates |
| `CUSTOMER_SERVICE_3_LEVEL` | 3 | Customer-facing teams |
| `HEALTHCARE_4_LEVEL` | 4 | Hospitals, clinics |
| `NGO_FIELD_3_LEVEL` | 3 | NGOs, CBOs |
| `GOVT_GRM_STANDARD` | 6 | Government / TARURA / TANROADS |

### Common error responses

| Status | Error | Cause |
|--------|-------|-------|
| 401 | `MISSING_TOKEN` | No Authorization header |
| 403 | `FORBIDDEN` | Insufficient org role |
| 404 | `NOT_FOUND` | Path / level / feedback / request not found |
| 409 | `CONFLICT` | Duplicate `level_order` or pending request already exists |
| 422 | `VALIDATION_ERROR` | Invalid field value (e.g. unknown `to_level`) |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
