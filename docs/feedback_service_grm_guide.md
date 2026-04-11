# Feedback Service — GRM Reference Guide

**Service:** `feedback_service` | Port `8090` | DB `feedback_db`  
**Base path:** `/api/v1`

---

## 1. Who Are the Users?

### PAP (Project-Affected Person)
Any authenticated Riviwa user **without** an active organisation context. They access the system through the self-service portal (`/my/feedback`). They can submit, track, comment on, appeal, and request escalation of their own submissions. They cannot see anyone else's feedback.

### Staff (Grievance Officers & Coordinators)
Authenticated users who have **switched into an active organisation** in their JWT. Their `org_id` and `org_role` claims determine what they can do. They only see feedback belonging to their organisation's projects.

| org_role | GRM Title | What they can do |
|---|---|---|
| `member` | Committee Member / Viewer | Read feedback, read history |
| `manager` | Grievance Officer | Everything a member can do + submit, acknowledge, assign, escalate, resolve, close, appeal |
| `admin` | GRM Coordinator | Everything a manager can do + **dismiss** |
| `owner` | GRM Coordinator | Same as admin |

### Platform Admins
Users with `platform_role: admin` or `super_admin`. They bypass org scoping and can see and act on feedback across **all organisations**.

---

## 2. GRM Lifecycle — Step-by-Step Journey

```
[SUBMISSION]
     │
     ▼
  SUBMITTED  ──────────────────────────────────────────► DISMISSED (admin/owner only — duplicate, out of scope)
     │
     │  Staff acknowledges receipt
     ▼
ACKNOWLEDGED
     │
     │  Staff assigns to officer or committee
     ▼
  IN_REVIEW
     │
     ├──► Staff resolves ──────────────────────────────► RESOLVED
     │         │
     │         │  PAP satisfied?
     │         ├── YES ──► Staff closes ──────────────► CLOSED
     │         │
     │         └── NO ───► PAP files appeal
     │                          │
     │                          ▼
     │                      APPEALED ──► escalated to next level ──► (cycle continues)
     │
     └──► Staff escalates ────────────────────────────► ESCALATED
               │                                           │
               │                                  (resolved/closed at higher level)
               ▼
         [next GRM level]
```

### GRM Levels (escalation hierarchy)

| Level | Who handles it |
|---|---|
| `ward` | Ward-level GHC (default on submission) |
| `lga_piu` | LGA / PIU office |
| `pcu` | Project Coordination Unit |
| `tarura_wbcu` | TARURA / World Bank Country Unit |
| `tanroads` | TANROADS HQ |
| `world_bank` | World Bank (highest — no further escalation) |

---

## 3. Staff Endpoints

All staff endpoints require a valid JWT with an active `org_id`. Responses are scoped to the user's organisation automatically.

---

### Submit Feedback on Behalf of PAP

**`POST /api/v1/feedback`** — Role: `manager`, `admin`, `owner`, or platform admin

**Request body:**
```json
{
  "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "feedback_type": "grievance",
  "category": "compensation",
  "channel": "paper_form",
  "subject": "Unfair compensation for land acquisition",
  "description": "PAP claims compensation offered for 2 acres is below market rate.",

  "is_anonymous": false,
  "submitter_name": "Amina Hassan",
  "submitter_phone": "+255712345678",
  "submitter_email": "amina@example.com",
  "submitter_type": "individual",
  "group_size": null,
  "submitter_location_region": "Dar es Salaam",
  "submitter_location_district": "Ilala",
  "submitter_location_lga": "Ilala",
  "submitter_location_ward": "Kariakoo",
  "submitter_location_street": "Plot 5, Msimbazi St",

  "priority": "high",

  "issue_location_description": "Near the bridge on Msimbazi road",
  "issue_region": "Dar es Salaam",
  "issue_district": "Ilala",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "issue_mtaa": "Msimbazi",
  "issue_gps_lat": -6.7924,
  "issue_gps_lng": 39.2083,

  "date_of_incident": "2025-09-15",
  "submitted_at": "2025-10-01",

  "media_urls": ["https://storage.riviwa.com/images/doc1.jpg"],

  "officer_recorded": true,
  "internal_notes": "PAP has supporting documents."
}
```

Required: `project_id`, `feedback_type`, `category`, `channel`, `subject`, `description`

`feedback_type`: `grievance | suggestion | applause`  
`channel`: `sms | whatsapp | phone_call | mobile_app | web_portal | in_person | paper_form | email | public_meeting | notice_box | other`  
`priority`: `critical | high | medium (default) | low`

**Response `201`:**
```json
{
  "id": "a1b2c3d4-...",
  "feedback_id": "a1b2c3d4-...",
  "unique_ref": "GRV-2025-0001",
  "tracking_number": "GRV-2025-0001",
  "project_id": "3fa85f64-...",
  "stage_id": null,
  "feedback_type": "grievance",
  "category": "compensation",
  "status": "submitted",
  "priority": "high",
  "current_level": "ward",
  "channel": "paper_form",
  "submission_method": "officer_recorded",
  "is_anonymous": false,
  "submitter_name": "Amina Hassan",
  "submitter_phone": "+255712345678",
  "submitter_location_lga": "Ilala",
  "submitter_location_ward": "Kariakoo",
  "subject": "Unfair compensation for land acquisition",
  "description": "PAP claims compensation...",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "issue_gps_lat": -6.7924,
  "issue_gps_lng": 39.2083,
  "date_of_incident": "2025-09-15T00:00:00",
  "submitted_at": "2025-10-01T00:00:00+00:00",
  "acknowledged_at": null,
  "resolved_at": null,
  "target_resolution_date": null,
  "closed_at": null
}
```

---

### Bulk Import from CSV

**`POST /api/v1/feedback/bulk-upload`** — Role: `manager+`

**Request:** multipart form, field `file` (CSV, UTF-8, max 1000 rows)

CSV columns: `project_id`, `feedback_type`, `category`, `subject`, `description`, `channel`, `priority`, `submitter_name`, `submitter_phone`, `is_anonymous`, `issue_lga`, `issue_ward`, `issue_gps_lat`, `issue_gps_lng`, `date_of_incident`, `submitted_at`

**Response `200`:**
```json
{
  "total_rows": 50,
  "created": 48,
  "skipped": 2,
  "errors": [
    {"row": 12, "field": "feedback_type", "error": "invalid value 'complaint'"},
    {"row": 31, "field": "project_id", "error": "project not found"}
  ]
}
```

---

### List Feedback

**`GET /api/v1/feedback`** — Role: `member+` (any org role)

Results are automatically scoped to the user's organisation. Platform admins see all orgs.

**Query params:**

| Param | Type | Description |
|---|---|---|
| `project_id` | UUID | Filter to a specific project |
| `feedback_type` | string | `grievance \| suggestion \| applause` |
| `status` | string | `submitted \| acknowledged \| in_review \| escalated \| resolved \| appealed \| actioned \| noted \| dismissed \| closed` |
| `priority` | string | `critical \| high \| medium \| low` |
| `current_level` | string | GRM level (see hierarchy above) |
| `category` | string | Category slug |
| `lga` | string | Partial match on issue LGA |
| `is_anonymous` | bool | Filter anonymous submissions |
| `submission_method` | string | `self_service \| officer_recorded \| ai_channel \| sms_webhook \| whatsapp_webhook` |
| `channel` | string | Submission channel |
| `submitted_by_stakeholder_id` | UUID | Filter by stakeholder |
| `assigned_committee_id` | UUID | Filter by assigned committee |
| `skip` | int | Offset (default 0) |
| `limit` | int | Max results (default 50, max 200) |

**Response `200`:**
```json
{
  "items": [ /* array of feedback objects (same structure as submit response) */ ],
  "count": 48
}
```

---

### Get Feedback Detail

**`GET /api/v1/feedback/{feedback_id}`** — Role: `member+`

Returns full lifecycle history. Returns `404` if the feedback belongs to another organisation.

**Response `200`:**
```json
{
  "id": "a1b2c3d4-...",
  "unique_ref": "GRV-2025-0001",
  "status": "acknowledged",
  "priority": "high",
  "current_level": "ward",
  "subject": "Unfair compensation for land acquisition",
  "description": "...",
  "issue_gps_lat": -6.7924,
  "issue_gps_lng": 39.2083,
  "submitted_at": "2025-10-01T00:00:00+00:00",
  "acknowledged_at": "2025-10-03T09:15:00+00:00",
  "target_resolution_date": "2025-11-01T00:00:00+00:00",
  "resolved_at": null,
  "closed_at": null,
  "actions": [
    {
      "id": "...",
      "action_type": "acknowledgement",
      "description": "Feedback acknowledged. Assigned to field team.",
      "is_internal": false,
      "response_method": null,
      "response_summary": null,
      "performed_by_user_id": "...",
      "performed_at": "2025-10-03T09:15:00+00:00"
    }
  ],
  "escalations": [],
  "resolution": null,
  "appeal": null
}
```

---

### Acknowledge Feedback

**`PATCH /api/v1/feedback/{feedback_id}/acknowledge`** — Role: `manager+`

Moves status from `submitted` → `acknowledged`. Sets the official response clock.

**Request body:**
```json
{
  "priority": "high",
  "target_resolution_date": "2026-05-15",
  "notes": "Assigned to field team for site inspection"
}
```

All fields optional. If `priority` is omitted, current priority is kept.

**Response `200`:** Full feedback object (status = `acknowledged`)

---

### Assign to Officer or Committee

**`PATCH /api/v1/feedback/{feedback_id}/assign`** — Role: `manager+`

Moves status to `in_review` if currently `submitted`. Assigns a responsible person or committee.

**Request body:**
```json
{
  "assigned_to_user_id": "7caa7de5-a260-43f8-9da1-30bc907be8ef",
  "assigned_committee_id": null,
  "notes": "Assigned to site engineer for investigation"
}
```

At least one of `assigned_to_user_id` or `assigned_committee_id` should be provided.

**Response `200`:** Full feedback object (status = `in_review`)

---

### Escalate to Next GRM Level

**`POST /api/v1/feedback/{feedback_id}/escalate`** — Role: `manager+`

Moves status to `escalated`. Requires a documented reason for audit trail.

**Request body:**
```json
{
  "to_level": "lga_piu",
  "reason": "Ward-level GHC unable to resolve within 30 days. PAP requires LGA intervention.",
  "escalated_to_committee_id": null
}
```

`to_level` required: `ward | lga_piu | pcu | tarura_wbcu | tanroads | world_bank`  
`reason` required (min 10 chars).

**Response `200`:** Full feedback object (status = `escalated`, `current_level` updated)

---

### Resolve Feedback

**`POST /api/v1/feedback/{feedback_id}/resolve`** — Role: `manager+`

Records the resolution. If the PAP is not satisfied, they may file an appeal.

**Request body:**
```json
{
  "resolution_summary": "Compensation re-assessed at market rate. PAP agrees to new valuation of TZS 45M.",
  "response_method": "in_person_meeting",
  "grievant_satisfied": true,
  "grievant_response": "PAP accepted the revised compensation amount.",
  "witness_name": "John Doe, LGA Representative"
}
```

`resolution_summary` required (min 10 chars).  
`response_method`: `verbal | written_letter | email | sms | phone_call | in_person_meeting | notice_board | other`

**Response `200`:** Full feedback object (status = `resolved`)

---

### File an Appeal (Staff-side)

**`POST /api/v1/feedback/{feedback_id}/appeal`** — Role: `manager+`

Used when a PAP verbally disputes a resolution and staff records it formally. Also auto-triggered when PAP uses `/my/feedback/{id}/appeal`.

**Request body:**
```json
{
  "appeal_grounds": "The revised compensation still does not reflect current market rates for commercial land in Ilala."
}
```

**Response `200`:** Full feedback object (status = `appealed`, escalated to next level)

---

### Close Feedback

**`PATCH /api/v1/feedback/{feedback_id}/close`** — Role: `manager+`

Final closure after resolution is accepted and confirmed.

**Request body:**
```json
{
  "notes": "PAP confirmed satisfaction in writing. Case closed per Annex 5."
}
```

**Response `200`:** Full feedback object (status = `closed`)

---

### Dismiss Feedback

**`PATCH /api/v1/feedback/{feedback_id}/dismiss`** — Role: `admin`, `owner`, or platform admin only

Irreversible. Use for duplicates, bad-faith submissions, or submissions outside project scope.

**Request body:**
```json
{
  "reason": "Duplicate of GRV-2026-0003. Same issue reported by the same PAP two days earlier."
}
```

`reason` required (min 5 chars).

**Response `200`:** Full feedback object (status = `dismissed`)

---

## 4. PAP Self-Service Endpoints

PAP endpoints require a valid JWT but **no org role**. All data is automatically scoped to `submitted_by_user_id == current user`.

---

### Submit Feedback

**`POST /api/v1/my/feedback`** — Any authenticated user

**Request body:**
```json
{
  "feedback_type": "grievance",
  "description": "Since Monday the construction crew has blocked the only road to my shop in Kariakoo.",
  "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "category": "construction_impact",
  "subject": "Road construction blocking access to my shop",
  "is_anonymous": false,
  "submitter_name": "Juma Bakari",
  "submitter_phone": "+255787654321",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "issue_location_description": "Near the Kariakoo market entrance",
  "issue_gps_lat": -6.8235,
  "issue_gps_lng": 39.2695,
  "date_of_incident": "2026-04-01",
  "media_urls": ["https://storage.riviwa.com/images/photo.jpg"]
}
```

Required: `feedback_type`, `description`  
Channel is auto-set to `web_portal`. Priority is always `medium`. `project_id` is optional — ML auto-detects if omitted.

**Response `201`:**
```json
{
  "feedback_id": "a1b2c3d4-...",
  "tracking_number": "GRV-2026-0001",
  "status": "submitted",
  "status_label": "Received — awaiting acknowledgement",
  "feedback_type": "grievance",
  "message": "Your grievance has been submitted successfully. Tracking number: GRV-2026-0001. You will be notified when PIU acknowledges receipt."
}
```

---

### List My Submissions

**`GET /api/v1/my/feedback`** — Any authenticated user

**Query params:** `feedback_type`, `status`, `project_id`, `skip` (default 0), `limit` (default 50, max 200)

**Response `200`:**
```json
{
  "items": [
    {
      "id": "a1b2c3d4-...",
      "unique_ref": "GRV-2026-0001",
      "feedback_type": "grievance",
      "category": "construction_impact",
      "subject": "Road construction blocking access",
      "channel": "web_portal",
      "status": "acknowledged",
      "status_label": "Acknowledged — under review",
      "current_level": "ward",
      "priority": "medium",
      "submitted_at": "2026-04-01T10:00:00+00:00",
      "resolved_at": null,
      "project_id": "3fa85f64-..."
    }
  ],
  "count": 1
}
```

---

### My Feedback Summary (Dashboard Widget)

**`GET /api/v1/my/feedback/summary`** — Any authenticated user

**Query params:** `project_id` (optional)

**Response `200`:**
```json
{
  "total": 3,
  "open": 2,
  "resolved": 0,
  "closed": 1,
  "by_type": [
    {"type": "grievance", "count": 2},
    {"type": "suggestion", "count": 1}
  ],
  "by_status": [
    {"status": "submitted", "label": "Received — awaiting acknowledgement", "count": 1},
    {"status": "acknowledged", "label": "Acknowledged — under review", "count": 1},
    {"status": "closed", "label": "Closed", "count": 1}
  ],
  "pending_escalation_requests": 0
}
```

---

### Track a Specific Submission

**`GET /api/v1/my/feedback/{feedback_id}`** — Any authenticated user (own submissions only)

**Response `200`:**
```json
{
  "id": "a1b2c3d4-...",
  "unique_ref": "GRV-2026-0001",
  "feedback_type": "grievance",
  "category": "construction_impact",
  "subject": "Road construction blocking access",
  "description": "Since Monday the construction crew...",
  "channel": "web_portal",
  "is_anonymous": false,
  "project_id": "3fa85f64-...",
  "current_level": "ward",
  "priority": "medium",
  "status": "resolved",
  "status_label": "Resolution provided",
  "issue_location_description": "Near the Kariakoo market entrance",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "issue_gps_lat": -6.8235,
  "issue_gps_lng": 39.2695,
  "submitted_at": "2026-04-01T10:00:00+00:00",
  "acknowledged_at": "2026-04-03T09:00:00+00:00",
  "target_resolution_date": "2026-05-01T00:00:00+00:00",
  "resolved_at": "2026-04-20T14:30:00+00:00",
  "closed_at": null,
  "hours_open": 254.5,
  "public_actions": [
    {
      "id": "...",
      "action_type": "acknowledgement",
      "description": "Your submission has been received and assigned to the PIU field team.",
      "response_method": null,
      "response_summary": null,
      "performed_at": "2026-04-03T09:00:00+00:00",
      "performed_by": "PIU / GHC"
    }
  ],
  "escalation_trail": [],
  "resolution": {
    "summary": "Road cleared. Contractor issued notice to maintain site access at all times.",
    "response_method": "in_person_meeting",
    "resolved_at": "2026-04-20T14:30:00+00:00",
    "grievant_satisfied": true,
    "grievant_response": "Access restored.",
    "appeal_filed": false
  },
  "appeal": null,
  "escalation_requests": [],
  "can_request_escalation": false,
  "can_appeal": false,
  "can_add_comment": false
}
```

---

### Request Escalation

**`POST /api/v1/my/feedback/{feedback_id}/escalation-request`** — Any authenticated user (own submissions only)

PAP can ask PIU to escalate their case. PIU staff review and approve or reject.

**Request body:**
```json
{
  "reason": "No response after 30 days despite multiple follow-ups.",
  "requested_level": "lga_piu"
}
```

**Response `201`:**
```json
{
  "id": "...",
  "status": "pending",
  "message": "Your escalation request has been submitted. PIU will review it and either approve (and escalate your case) or explain why escalation is not applicable at this stage."
}
```

---

### Staff: Review Escalation Requests

**`GET /api/v1/escalation-requests`** — Role: `member+`

**Query params:** `project_id`, `status` (default `pending`), `skip`, `limit`

**Response `200`:**
```json
{
  "items": [
    {
      "id": "...",
      "feedback_id": "...",
      "reason": "No response after 30 days...",
      "requested_level": "lga_piu",
      "status": "pending",
      "reviewer_notes": null,
      "requested_at": "2026-04-10T08:00:00+00:00",
      "reviewed_at": null
    }
  ],
  "count": 1
}
```

---

### Staff: Approve Escalation Request

**`POST /api/v1/escalation-requests/{request_id}/approve`** — Role: `manager+`

**Request body:**
```json
{ "notes": "Justified — unresolved for 45 days." }
```

**Response `200`:**
```json
{
  "status": "approved",
  "message": "Escalation request approved.",
  "feedback_id": "..."
}
```

---

### Staff: Reject Escalation Request

**`POST /api/v1/escalation-requests/{request_id}/reject`** — Role: `manager+`

**Request body:**
```json
{ "notes": "Case is being actively investigated. Resolution expected within 7 days." }
```

**Response `200`:**
```json
{
  "status": "rejected",
  "message": "Escalation request rejected. The PAP has been notified."
}
```

---

### PAP: File Appeal

**`POST /api/v1/my/feedback/{feedback_id}/appeal`** — Any authenticated user (own resolved submissions only)

Only available when `status = resolved` and PAP was not satisfied.

**Request body:**
```json
{
  "grounds": "Resolution does not address the core issue of fair compensation for my land."
}
```

**Response `201`:**
```json
{
  "appeal_id": "...",
  "status": "appealed",
  "now_at_level": "lga_piu",
  "message": "Your appeal has been filed. Your case has been escalated to LGA PIU for review. If you remain unsatisfied after the appeal outcome, you have the right to seek resolution through the courts."
}
```

---

### PAP: Add Comment

**`POST /api/v1/my/feedback/{feedback_id}/add-comment`** — Any authenticated user (own open submissions only)

**Request body:**
```json
{
  "comment": "I have new photographs showing the damage from last week's construction activity."
}
```

**Response `201`:**
```json
{
  "message": "Your comment has been added and is visible to PIU staff.",
  "action_id": "..."
}
```

---

## 5. Status Flow Quick Reference

| From status | Action | By | To status |
|---|---|---|---|
| `submitted` | acknowledge | manager+ | `acknowledged` |
| `submitted` | assign | manager+ | `in_review` |
| `submitted` | dismiss | admin/owner | `dismissed` |
| `acknowledged` | assign | manager+ | `in_review` |
| `acknowledged` | escalate | manager+ | `escalated` |
| `in_review` | resolve | manager+ | `resolved` |
| `in_review` | escalate | manager+ | `escalated` |
| `escalated` | resolve | manager+ | `resolved` |
| `resolved` | appeal (PAP or staff) | any / manager+ | `appealed` |
| `resolved` | close | manager+ | `closed` |
| `appealed` | resolve | manager+ | `resolved` |
| any open | dismiss | admin/owner | `dismissed` |

---

## 6. Tracking Number Format

| Type | Prefix | Example |
|---|---|---|
| Grievance | `GRV` | `GRV-2026-0001` |
| Suggestion | `SGG` | `SGG-2026-0014` |
| Applause | `APP` | `APP-2026-0003` |

Format: `{PREFIX}-{YEAR}-{SEQUENCE:04d}` — sequence resets per year per project.
