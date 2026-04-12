# Riviwa — AI Service & Analytics Service API Reference

> Base URL (production): `https://api.riviwa.com`  
> All analytics endpoints require `Authorization: Bearer <JWT>`.  
> AI conversation endpoints (`/api/v1/ai/conversations`) are public (no auth required for PAPs).

---

## Table of Contents

1. [AI Service](#1-ai-service)
   - [Models & Enums](#11-models--enums)
   - [Endpoints](#12-endpoints)
     - [POST /api/v1/ai/conversations](#post-apiv1aiconversations)
     - [POST /api/v1/ai/conversations/{id}/message](#post-apiv1aiconversationsidmessage)
     - [GET /api/v1/ai/conversations/{id}](#get-apiv1aiconversationsid)
     - [POST /api/v1/ai/webhooks/sms](#post-apiv1aiwebhookssms)
     - [POST /api/v1/ai/webhooks/whatsapp](#post-apiv1aiwebhookswhatsapp)
     - [GET /api/v1/ai/webhooks/whatsapp](#get-apiv1aiwebhookswhatsapp)
2. [Analytics Service](#2-analytics-service)
   - [Authentication](#21-authentication)
   - [SLA Targets](#22-sla-targets)
   - [Feedback Endpoints](#23-feedback-endpoints)
   - [Grievance Endpoints](#24-grievance-endpoints)
   - [Suggestion Endpoints](#25-suggestion-endpoints)
   - [Staff Endpoints](#26-staff-endpoints)
   - [AI Insights Endpoint](#27-ai-insights-endpoint)
3. [End-to-End Data Flow](#3-end-to-end-data-flow)

---

## 1. AI Service

Port `8085` — Nginx route: `/api/v1/ai/**` and `/health/ai`

### 1.1 Models & Enums

#### `AIConversation` — Database table `ai_conversations`

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `channel` | `ConversationChannel` | `sms \| whatsapp \| phone_call \| web \| mobile` |
| `status` | `ConversationStatus` | `active \| confirming \| submitted \| followup \| abandoned \| timed_out \| failed` |
| `stage` | `ConversationStage` | `greeting \| identify \| collecting \| clarifying \| confirming \| followup \| done` |
| `language` | string | `"sw"` (Swahili) or `"en"` (English) |
| `phone_number` | string? | Populated for SMS/WhatsApp conversations |
| `whatsapp_id` | string? | Meta WhatsApp sender ID |
| `web_token` | string? | Anonymous browser session token |
| `user_id` | UUID? | Auth service user ID (registered PAPs) |
| `is_registered` | bool | True if PAP is a registered platform user |
| `submitter_name` | string? | Name extracted or provided by PAP |
| `turn_count` | int | Total messages exchanged |
| `turns` | JSONB | `[{"role": "user\|assistant", "content": "...", "timestamp": "ISO"}]` |
| `extracted_data` | JSONB | Progressively filled feedback fields (see below) |
| `submitted_feedback` | JSONB | `[{"feedback_id": "...", "unique_ref": "...", "feedback_type": "..."}]` |
| `project_id` | UUID? | Auto-detected via Qdrant RAG |
| `project_name` | string? | Resolved project name |
| `is_urgent` | bool | True if safety/life threat detected |
| `incharge_name` | string? | Project officer name (from StakeholderCache) |
| `incharge_phone` | string? | Project officer phone for urgent escalation |
| `started_at` | datetime | Conversation start |
| `last_active_at` | datetime | Last message timestamp |
| `completed_at` | datetime? | Set when stage = `done` |

**`extracted_data` schema (JSONB, progressively filled):**

```json
{
  "feedback_type":    "grievance | suggestion | applause",
  "subject":          "Short summary",
  "description":      "Full narrative",
  "priority":         "critical | high | medium | low",
  "category":         "category slug (e.g. SAFETY_HAZARD)",
  "channel":          "sms | whatsapp | web | mobile_app",
  "issue_lga":        "District / LGA name",
  "issue_ward":       "Ward name",
  "issue_region":     "Region name",
  "issue_location_description": "Free-text location",
  "submitter_name":   "PAP's name",
  "is_anonymous":     false,
  "confidence":       0.0
}
```

#### `ProjectKnowledgeBase` — table `ai_project_kb`

Mirrors project data consumed from Kafka (`riviwa.organisation.events`).  
Used by Qdrant RAG to match a PAP's location/description to the correct project.

| Field | Type | Description |
|---|---|---|
| `project_id` | UUID | Unique, indexed |
| `organisation_id` | UUID | Owner org |
| `name` | string | Project display name |
| `slug` | string | URL-safe identifier |
| `description` | text | Full project description |
| `region` | string? | Tanzania region |
| `primary_lga` | string? | Primary LGA |
| `wards` | JSONB | `{"wards": ["ward1", "ward2"]}` |
| `keywords` | JSONB | `{"keywords": ["road", "bridge"]}` |
| `status` | string | `active \| paused \| completed \| cancelled` |
| `accepts_grievances` | bool | |
| `accepts_suggestions` | bool | |
| `accepts_applause` | bool | |
| `vector_indexed` | bool | True when embedded in Qdrant |

#### `StakeholderCache` — table `ai_stakeholder_cache`

Consumed from Kafka for urgency escalation — surfaces the project officer's contact.

| Field | Type | Description |
|---|---|---|
| `stakeholder_id` | UUID | |
| `project_id` | UUID? | |
| `name` | string | |
| `phone` | string? | |
| `is_incharge` | bool | True = project officer / PIU incharge |
| `lga` | string? | |

---

### 1.2 Endpoints

---

#### `POST /api/v1/ai/conversations`

Start a new AI-assisted feedback conversation.  
**Auth:** None required (anonymous PAPs supported).

**Request Body:**

```json
{
  "channel":    "web",
  "language":   "sw",
  "project_id": "47f208ee-7c15-4641-81eb-936c18c590c7",
  "user_id":    null,
  "web_token":  "anon-session-abc123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `channel` | string | No (default `"web"`) | `web \| mobile` |
| `language` | string | No (default `"sw"`) | `sw` = Swahili, `en` = English |
| `project_id` | UUID | No | Pre-select project; omit to let AI detect from conversation |
| `user_id` | UUID | No | Authenticated user ID from JWT |
| `web_token` | string | No | Anonymous browser session token |

**Response `201`:**

```json
{
  "conversation_id":   "14e60e92-a3fd-442b-9881-8e98ac06adea",
  "reply":             "Habari! Mimi ni Riviwa AI, msaidizi wako wa Riviwa...",
  "status":            "active",
  "stage":             "greeting",
  "turn_count":        1,
  "confidence":        0.0,
  "language":          "sw",
  "submitted":         false,
  "submitted_feedback": [],
  "project_name":      null,
  "is_urgent":         false,
  "incharge_name":     null,
  "incharge_phone":    null
}
```

---

#### `POST /api/v1/ai/conversations/{id}/message`

Send a PAP message and receive the AI reply.  
**Auth:** None required.

**Path param:** `id` — conversation UUID from start response.

**Request Body:**

```json
{
  "message":    "Kuna shimo kubwa barabarani karibu na hospitali",
  "media_urls": ["https://storage.riviwa.com/proof/img1.jpg"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes (1–4000 chars) | PAP's text message |
| `media_urls` | string[] | No | Proof images/documents (WhatsApp attachments) |

**Response `200`:**

```json
{
  "conversation_id":   "14e60e92-a3fd-442b-9881-8e98ac06adea",
  "reply":             "Asante. Shimo hilo liko wapi hasa? Taja mtaa au karibu na nini.",
  "status":            "active",
  "stage":             "collecting",
  "turn_count":        3,
  "confidence":        0.6,
  "language":          "sw",
  "submitted":         false,
  "submitted_feedback": [],
  "project_name":      "Dar es Salaam Road Upgrade",
  "is_urgent":         false,
  "incharge_name":     null,
  "incharge_phone":    null
}
```

When confidence ≥ 0.82 and all required fields are collected, `submitted: true` and `submitted_feedback` is populated:

```json
{
  "submitted": true,
  "submitted_feedback": [
    {
      "feedback_id":   "cd28ae8c-9ba9-475a-a277-2d5a46bf87ec",
      "unique_ref":    "GRV-2026-0009",
      "feedback_type": "grievance"
    }
  ]
}
```

---

#### `GET /api/v1/ai/conversations/{id}`

Retrieve full conversation transcript and extracted data.  
**Auth:** None required.

**Response `200`:**

```json
{
  "conversation_id":    "14e60e92-a3fd-442b-9881-8e98ac06adea",
  "channel":            "web",
  "status":             "active",
  "stage":              "collecting",
  "language":           "sw",
  "turn_count":         6,
  "confidence":         0.75,
  "is_registered":      false,
  "submitter_name":     "Ibrahim Salim",
  "project_id":         "47f208ee-7c15-4641-81eb-936c18c590c7",
  "project_name":       "Dar es Salaam Road Upgrade",
  "extracted_data": {
    "feedback_type":   "grievance",
    "subject":         "Flooded drainage near Temeke market",
    "description":     "Construction blocked the drainage channel...",
    "priority":        "high",
    "issue_lga":       "Temeke",
    "issue_ward":      "Miburani",
    "submitter_name":  "Ibrahim Salim",
    "is_anonymous":    false,
    "confidence":      0.75
  },
  "submitted_feedback": [],
  "transcript": [
    {"role": "assistant", "content": "Habari! Mimi ni Riviwa AI...", "timestamp": "2026-04-12T11:00:00"},
    {"role": "user",      "content": "Kuna shimo kubwa barabarani...", "timestamp": "2026-04-12T11:00:30"}
  ],
  "is_urgent":      true,
  "incharge_name":  "Mr. Joseph Makamba",
  "incharge_phone": "+255712345678",
  "started_at":     "2026-04-12T11:00:00",
  "last_active_at": "2026-04-12T11:02:45",
  "completed_at":   null
}
```

---

#### `POST /api/v1/ai/webhooks/sms`

Inbound SMS handler. Called by Africa's Talking or Twilio when a PAP sends an SMS.  
**Auth:** None (provider-to-service webhook).

**Africa's Talking format:**

```json
{
  "from":        "+255712345678",
  "to":          "RIVIWA",
  "text":        "Kuna tatizo la maji safi katika mtaa wetu",
  "date":        "2026-04-12 11:05:00",
  "id":          "at_msg_001",
  "linkId":      "",
  "networkCode": "62002"
}
```

**Twilio format:**

```json
{
  "From":   "+255712345678",
  "To":     "+255800123456",
  "Body":   "There is a dangerous pothole on the main road",
  "NumMedia": "0"
}
```

**Response `200` (Africa's Talking):**

```json
{
  "message": "Asante! Tumepokea tatizo lako. Tupa maelezo zaidi - tatizo liko wapi hasa?"
}
```

**Response `200` (Twilio):**

```json
{
  "message": "ok",
  "reply":   "Thank you! Please describe where exactly the pothole is located."
}
```

---

#### `POST /api/v1/ai/webhooks/whatsapp`

Inbound WhatsApp handler. Called by Meta Cloud API.  
**Auth:** None (Meta webhook).

**Request Body (Meta Cloud API format):**

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "255800123456", "phone_number_id": "PHONE_ID"},
        "messages": [{
          "from": "255712345678",
          "id":   "wamid.abc123",
          "timestamp": "1744455600",
          "text": {"body": "Kuna tatizo la barabara hapa"},
          "type": "text"
        }]
      },
      "field": "messages"
    }]
  }]
}
```

**Response `200`:**

```json
{"status": "ok"}
```

The service calls Meta Graph API to send the reply back to the PAP automatically.

---

#### `GET /api/v1/ai/webhooks/whatsapp`

Meta webhook verification challenge.  
**Auth:** None.

**Query params:**

| Param | Value |
|---|---|
| `hub.mode` | `subscribe` |
| `hub.verify_token` | Must match `WHATSAPP_VERIFY_TOKEN` env var |
| `hub.challenge` | Challenge string from Meta |

**Response `200`:** Plain text challenge string (echoed back to Meta).  
**Response `403`:** `Forbidden` — token mismatch.

---

## 2. Analytics Service

Port `8095` — Nginx route: `/api/v1/analytics/**` and `/health/analytics`

All endpoints except `/health/analytics` require `Authorization: Bearer <JWT>`.

### 2.1 Authentication

Staff-level endpoints (`feedback`, `grievances`, `suggestions`) accept any valid JWT.  
Staff admin endpoints (`staff/*`) require `org_role` = `OWNER` or `ADMIN`.

### 2.2 SLA Targets

Applied automatically in `grievances/sla-status` and AI insights:

| Priority | Acknowledge SLA | Resolve SLA |
|---|---|---|
| `critical` | 4 hours | 72 hours (3 days) |
| `high` | 8 hours | 168 hours (7 days) |
| `medium` | 24 hours | 336 hours (14 days) |
| `low` | 48 hours | 720 hours (30 days) |

---

### 2.3 Feedback Endpoints

All feedback endpoints share these query parameters:

| Param | Type | Required | Description |
|---|---|---|---|
| `project_id` | UUID | **Yes** | Target project |
| `date_from` | string | No | `YYYY-MM-DD` filter start |
| `date_to` | string | No | `YYYY-MM-DD` filter end |

---

#### `GET /api/v1/analytics/feedback/time-to-open`

Hours from submission to first staff action per feedback item.

**Query params:** `project_id`, `date_from?`, `date_to?`

**Response `200`:**

```json
{
  "avg_hours":    3.25,
  "min_hours":    0.5,
  "max_hours":    12.0,
  "median_hours": 2.75,
  "sample_count": 8,
  "items": [
    {
      "feedback_id":    "cd28ae8c-9ba9-475a-a277-2d5a46bf87ec",
      "unique_ref":     "GRV-2026-0006",
      "priority":       "CRITICAL",
      "submitted_at":   "2026-04-10T10:35:29Z",
      "first_action_at":"2026-04-10T11:05:29Z",
      "hours_to_open":  0.5
    }
  ]
}
```

---

#### `GET /api/v1/analytics/feedback/unread`

All feedbacks with `status = SUBMITTED` (received, not yet acknowledged).

**Query params:** `project_id`, `priority?` (`critical|high|medium|low`), `feedback_type?` (`grievance|suggestion|applause`)

**Response `200`:**

```json
{
  "total": 6,
  "items": [
    {
      "feedback_id":    "cd28ae8c-9ba9-475a-a277-2d5a46bf87ec",
      "unique_ref":     "SGG-2026-0004",
      "feedback_type":  "SUGGESTION",
      "priority":       "MEDIUM",
      "submitted_at":   "2026-04-09T10:35:29Z",
      "days_waiting":   3.01,
      "channel":        "MOBILE_APP",
      "issue_lga":      "Kinondoni",
      "submitter_name": null
    }
  ]
}
```

---

#### `GET /api/v1/analytics/feedback/overdue`

Feedbacks in `ACKNOWLEDGED` or `IN_REVIEW` status where `target_resolution_date < now()`.

**Query params:** `project_id`, `feedback_type?`

**Response `200`:**

```json
{
  "total": 2,
  "items": [
    {
      "feedback_id":             "7d31212c-298c-4893-9d94-78432b15abe5",
      "unique_ref":              "GRV-2026-0007",
      "priority":                "HIGH",
      "status":                  "ACKNOWLEDGED",
      "submitted_at":            "2026-04-07T10:35:29Z",
      "target_resolution_date":  "2026-04-09T10:35:29Z",
      "days_overdue":            3.0,
      "assigned_to_user_id":     "a1b2c3d4-...",
      "committee_id":            null
    }
  ]
}
```

---

#### `GET /api/v1/analytics/feedback/not-processed`

Feedbacks acknowledged/in-review but not yet resolved.  
Same shape as `/overdue` — all cases in the pipeline regardless of deadline.

**Query params:** `project_id`, `feedback_type?`

**Response `200`:** Same schema as `OverdueFeedbackResponse` above.

---

#### `GET /api/v1/analytics/feedback/processed-today`

Feedbacks that moved to `IN_REVIEW` status today (`DATE(updated_at) = CURRENT_DATE`).

**Query params:** `project_id`

**Response `200`:**

```json
{
  "total": 1,
  "items": [
    {
      "feedback_id":  "0126278b-1d2e-4ad8-8656-f92b1267c40d",
      "unique_ref":   "GRV-2026-0008",
      "priority":     "MEDIUM",
      "category":     "ENVIRONMENTAL",
      "processed_at": "2026-04-12T09:50:30Z"
    }
  ]
}
```

---

#### `GET /api/v1/analytics/feedback/resolved-today`

Feedbacks where `DATE(resolved_at) = CURRENT_DATE`.

**Query params:** `project_id`

**Response `200`:**

```json
{
  "total": 1,
  "items": [
    {
      "feedback_id":      "7a5bcce5-efef-47ed-811a-7cb09579f3cb",
      "unique_ref":       "GRV-2026-0007",
      "feedback_type":    "GRIEVANCE",
      "priority":         "HIGH",
      "category":         "CONSTRUCTION_IMPACT",
      "resolved_at":      "2026-04-12T14:30:00Z",
      "resolution_hours": 96.0
    }
  ]
}
```

---

### 2.4 Grievance Endpoints

---

#### `GET /api/v1/analytics/grievances/unresolved`

All grievances where `status NOT IN (RESOLVED, CLOSED, DISMISSED)`.

**Query params:**

| Param | Type | Required | Description |
|---|---|---|---|
| `project_id` | UUID | Yes | |
| `min_days` | float | No | Minimum days unresolved (e.g. `7`) |
| `priority` | string | No | `critical \| high \| medium \| low` |
| `status` | string | No | Specific status to filter by |

**Response `200`:**

```json
{
  "total": 3,
  "items": [
    {
      "feedback_id":         "0126278b-1d2e-4ad8-8656-f92b1267c40d",
      "unique_ref":          "GRV-2026-0008",
      "priority":            "MEDIUM",
      "category":            "ENVIRONMENTAL",
      "status":              "IN_REVIEW",
      "submitted_at":        "2026-04-02T10:35:29Z",
      "days_unresolved":     10.0,
      "assigned_to_user_id": null,
      "committee_id":        null,
      "issue_lga":           "Ilala",
      "issue_ward":          "Kariakoo"
    },
    {
      "feedback_id":     "7d31212c-298c-4893-9d94-78432b15abe5",
      "unique_ref":      "GRV-2026-0007",
      "priority":        "HIGH",
      "category":        "CONSTRUCTION_IMPACT",
      "status":          "ACKNOWLEDGED",
      "submitted_at":    "2026-04-07T10:35:29Z",
      "days_unresolved": 5.0,
      "issue_lga":       "Temeke",
      "issue_ward":      "Mbagala"
    },
    {
      "feedback_id":     "7a5bcce5-efef-47ed-811a-7cb09579f3cb",
      "unique_ref":      "GRV-2026-0006",
      "priority":        "CRITICAL",
      "category":        "SAFETY_HAZARD",
      "status":          "SUBMITTED",
      "submitted_at":    "2026-04-10T10:35:29Z",
      "days_unresolved": 2.0,
      "issue_lga":       "Ilala",
      "issue_ward":      "Upanga"
    }
  ]
}
```

---

#### `GET /api/v1/analytics/grievances/sla-status`

SLA compliance per priority. Uses pre-computed `analytics_db.sla_records` when available; falls back to live `feedback_db` query.

**Query params:**

| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `project_id` | UUID | Yes | | |
| `breached_only` | bool | No | `false` | Return only breached records |

**Response `200`:**

```json
{
  "by_priority": [
    {
      "priority":        "critical",
      "total":           1,
      "ack_met":         0,
      "ack_breached":    0,
      "res_met":         0,
      "res_breached":    0,
      "compliance_rate": 0.0
    },
    {
      "priority":        "high",
      "total":           1,
      "ack_met":         0,
      "ack_breached":    0,
      "res_met":         0,
      "res_breached":    0,
      "compliance_rate": 0.0
    },
    {
      "priority":        "medium",
      "total":           1,
      "ack_met":         0,
      "ack_breached":    0,
      "res_met":         0,
      "res_breached":    0,
      "compliance_rate": 0.0
    }
  ],
  "overdue_list": [],
  "total_breached": 0,
  "overall_compliance_rate": 0.0
}
```

`SLAOverdueItem` (appears in `overdue_list` when breaches exist):

```json
{
  "feedback_id":      "7d31212c-...",
  "priority":         "high",
  "status":           "ACKNOWLEDGED",
  "submitted_at":     "2026-04-07T10:35:29Z",
  "ack_deadline":     "2026-04-07T18:35:29Z",
  "res_deadline":     "2026-04-14T10:35:29Z",
  "acknowledged_at":  null,
  "resolved_at":      null,
  "ack_sla_met":      null,
  "res_sla_met":      null,
  "days_unresolved":  5.0
}
```

---

#### `GET /api/v1/analytics/grievances/hotspots`

Geographic/category spike alerts from Spark's hotspot detector.  
Populated only after the Spark streaming job runs.

**Query params:**

| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `project_id` | UUID | Yes | | |
| `alert_status` | string | No | `"active"` | `active \| resolved \| all` |

**Response `200`:**

```json
{
  "total": 2,
  "alerts": [
    {
      "id":           "f1e2d3c4-...",
      "location":     "Ilala/Kariakoo",
      "category":     "ENVIRONMENTAL",
      "count":        12,
      "spike_factor": 4.5,
      "baseline_avg": 2.67,
      "window_start": "2026-04-12T06:00:00Z",
      "window_end":   "2026-04-12T12:00:00Z",
      "alert_status": "active"
    }
  ]
}
```

---

### 2.5 Suggestion Endpoints

---

#### `GET /api/v1/analytics/suggestions/implementation-time`

Hours from submission to `ACTIONED` status for all implemented suggestions  
(only suggestions where `resolved_at IS NOT NULL`).

**Query params:** `project_id`

**Response `200`:**

```json
{
  "avg_hours":    168.0,
  "min_hours":    168.0,
  "max_hours":    168.0,
  "median_hours": 168.0,
  "sample_count": 1,
  "items": [
    {
      "feedback_id":       "2bf25845-f3fd-48f8-be16-bb17d6769bb0",
      "unique_ref":        "SGG-2026-0005",
      "submitted_at":      "2026-03-28T10:35:29Z",
      "implemented_at":    "2026-04-04T10:35:29Z",
      "hours_to_implement":168.0,
      "category":          "COMMUNITY_BENEFIT"
    }
  ]
}
```

---

#### `GET /api/v1/analytics/suggestions/frequency`

Suggestion volume by category + priority for the current period.

**Query params:**

| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `project_id` | UUID | Yes | | |
| `period` | string | No | `"week"` | `week \| month \| year` |

**Response `200`:**

```json
{
  "period":      "week",
  "period_days": 7,
  "total":       3,
  "items": [
    {
      "category":    "DESIGN",
      "priority":    "MEDIUM",
      "count":       1,
      "rate_per_day":0.1429
    },
    {
      "category":    "OTHER",
      "priority":    "HIGH",
      "count":       1,
      "rate_per_day":0.1429
    },
    {
      "category":    "OTHER",
      "priority":    "MEDIUM",
      "count":       1,
      "rate_per_day":0.1429
    }
  ]
}
```

---

#### `GET /api/v1/analytics/suggestions/by-location`

Suggestion counts grouped by `region / LGA / ward` with implementation rates.

**Query params:** `project_id`

**Response `200`:**

```json
{
  "total": 4,
  "items": [
    {
      "region":              null,
      "lga":                 "Kinondoni",
      "ward":                "Magomeni",
      "count":               2,
      "implemented_count":   0,
      "implementation_rate": 0.0
    },
    {
      "region":              null,
      "lga":                 "Kinondoni",
      "ward":                "Sinza",
      "count":               1,
      "implemented_count":   1,
      "implementation_rate": 100.0
    },
    {
      "region":              null,
      "lga":                 "Ilala",
      "ward":                "Msimbazi",
      "count":               1,
      "implemented_count":   0,
      "implementation_rate": 0.0
    }
  ]
}
```

---

#### `GET /api/v1/analytics/suggestions/unread`

Suggestions with `status = SUBMITTED` (received, not yet actioned).

**Query params:** `project_id`

**Response `200`:**

```json
{
  "total": 3,
  "items": [
    {
      "feedback_id":  "cd28ae8c-9ba9-475a-a277-2d5a46bf87ec",
      "unique_ref":   "SGG-2026-0004",
      "submitted_at": "2026-04-09T10:35:29Z",
      "days_unread":  3.01,
      "priority":     "MEDIUM",
      "category":     "DESIGN",
      "issue_lga":    "Kinondoni"
    }
  ]
}
```

---

#### `GET /api/v1/analytics/suggestions/implemented-today`

Suggestions marked `ACTIONED` today (`DATE(resolved_at) = CURRENT_DATE`).

**Query params:** `project_id`

**Response `200`:**

```json
{
  "total": 1,
  "items": [
    {
      "feedback_id":         "2bf25845-...",
      "unique_ref":          "SGG-2026-0010",
      "category":            "DESIGN",
      "submitted_at":        "2026-04-05T09:00:00Z",
      "implemented_at":      "2026-04-12T11:00:00Z",
      "hours_to_implement":  170.0
    }
  ]
}
```

---

#### `GET /api/v1/analytics/suggestions/implemented-this-week`

Suggestions marked `ACTIONED` in the current ISO week.

**Query params:** `project_id`

**Response `200`:** Same schema as `implemented-today`.

---

### 2.6 Staff Endpoints

> **Auth required:** JWT with `org_role = OWNER or ADMIN`.

---

#### `GET /api/v1/analytics/staff/committee-performance`

Performance metrics per active GRM committee. Uses pre-computed `analytics_db` data unless `use_live=true`.

**Query params:**

| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `project_id` | UUID | Yes | | |
| `date_from` | string | No | | `YYYY-MM-DD` |
| `date_to` | string | No | | `YYYY-MM-DD` |
| `use_live` | bool | No | `false` | Force live query from `feedback_db` |

**Response `200`:**

```json
{
  "total": 2,
  "items": [
    {
      "committee_id":          "a1b2c3d4-...",
      "committee_name":        "District GRM Committee",
      "level":                 "district",
      "project_id":            "47f208ee-...",
      "cases_assigned":        15,
      "cases_resolved":        12,
      "cases_overdue":         1,
      "avg_resolution_hours":  96.5,
      "resolution_rate":       80.0
    }
  ]
}
```

---

#### `GET /api/v1/analytics/staff/last-logins`

Last login time and 7-day login count per staff member.  
Sourced from `analytics_db.staff_logins` (populated by Spark batch job + auth events).

**Query params:** `date_from?`, `date_to?`

**Response `200`:**

```json
{
  "total": 3,
  "items": [
    {
      "user_id":       "24513388-1822-486e-bec4-15c843172a3d",
      "last_login_at": "2026-04-12T09:30:00Z",
      "login_count_7d":5,
      "platform":      "web"
    }
  ]
}
```

---

#### `GET /api/v1/analytics/staff/unread-assigned`

Officers with feedbacks assigned but no action taken yet (`status = SUBMITTED` + no `feedback_actions` row from that officer).

**Query params:** `project_id`

**Response `200`:**

```json
{
  "total": 2,
  "items": [
    {
      "user_id":       "24513388-1822-486e-bec4-15c843172a3d",
      "assigned_count":5,
      "unread_count":  3,
      "feedback_ids":  ["cd28ae8c-...", "7d31212c-...", "0126278b-..."]
    }
  ]
}
```

---

#### `GET /api/v1/analytics/staff/login-not-read`

Officers who logged in today AND still have unread assigned feedbacks — i.e., active but not processing their queue.

**Query params:** `project_id`

**Response `200`:**

```json
{
  "total": 1,
  "items": [
    {
      "user_id":              "24513388-1822-486e-bec4-15c843172a3d",
      "last_login_at":        "2026-04-12T09:30:00Z",
      "assigned_unread_count":3,
      "feedback_ids":         ["cd28ae8c-...", "7d31212c-...", "0126278b-..."]
    }
  ]
}
```

---

### 2.7 AI Insights Endpoint

---

#### `POST /api/v1/analytics/ai/ask`

Ask a natural language question about project analytics. The service assembles a data context from live + pre-computed metrics, then calls **Groq `llama-3.3-70b-versatile`** for the answer.

**Auth:** Any valid JWT.

**Request Body:**

```json
{
  "question":     "Which grievances are most at risk of breaching their SLA?",
  "project_id":   "47f208ee-7c15-4641-81eb-936c18c590c7",
  "context_type": "sla"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | string | Yes (5–1000 chars) | Natural language question |
| `project_id` | UUID | Yes | Target project |
| `context_type` | string | No (default `"general"`) | Controls which metrics are fetched — see below |

**`context_type` values and what data each fetches:**

| Value | Data fetched |
|---|---|
| `general` | Summary counts + unresolved + overdue + SLA + suggestions + hotspots + committees + resolved today |
| `grievances` | Summary + unresolved + overdue + SLA |
| `suggestions` | Summary + implementation time + unread suggestions |
| `sla` | Summary + unresolved + overdue + pre-computed SLA records |
| `committees` | Summary + committee performance |
| `hotspots` | Summary + active hotspot alerts |
| `staff` | Summary + staff unread assignments + logins today |
| `unresolved` | Summary + unresolved + overdue |

**Response `200`:**

```json
{
  "answer": "Based on the current data, the HIGH priority grievance GRV-2026-0007 is the most at risk. It was submitted 5 days ago and its resolution deadline (168 hours = 7 days) is in 2 days. The CRITICAL grievance GRV-2026-0006 already breached its 72-hour resolution SLA 2 days ago...",
  "model": "llama-3.3-70b-versatile",
  "context_used": {
    "project_id":              "47f208ee-7c15-4641-81eb-936c18c590c7",
    "context_type":            "sla",
    "summary": {
      "total_grievances":      3,
      "total_suggestions":     4,
      "total_applause":        2,
      "unread_count":          6,
      "overdue_count":         0,
      "unresolved_grievances": 3,
      "avg_resolution_hours":  168.0,
      "top_category":          "SAFETY_HAZARD"
    },
    "unresolved_grievances_count": 3,
    "unresolved_by_priority":  {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1},
    "overdue_count":           0,
    "sla_total_records":       0,
    "sla_ack_breached":        0,
    "sla_res_breached":        0,
    "sla_compliance_rate":     null
  }
}
```

---

## 3. End-to-End Data Flow

> Step-by-step from a PAP submitting feedback to analytics and AI insights being available.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              RIVIWA DATA FLOW                                           │
│                 PAP Feedback → Processing → Analytics → AI Insights                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Stage 1 — PAP Submits Feedback (AI Conversation)

```
PAP
 │
 │  SMS / WhatsApp / Web / Mobile App
 ▼
ai_service (port 8085)
 │
 ├─ 1a. PAP sends first message
 │      POST /api/v1/ai/conversations
 │      → ai_conversations row created (stage=greeting, status=active)
 │      → Qdrant RAG matches PAP's location to a Project KB entry
 │        (ai_project_kb, populated from Kafka: riviwa.organisation.events)
 │
 ├─ 1b. Multi-turn collection (1–6+ turns)
 │      POST /api/v1/ai/conversations/{id}/message
 │      Each turn:
 │        • Groq llama-3.3-70b-versatile generates context-aware reply (Swahili/English)
 │        • Obsidian vault RAG: project-specific policies are retrieved for context
 │        • extracted_data fields filled progressively (subject, description,
 │          priority, category, issue_lga, issue_ward, submitter_name…)
 │        • confidence score rises with each filled field
 │        • If is_urgent detected → StakeholderCache queried → incharge_name/phone returned
 │
 └─ 1c. Auto-submit when confidence ≥ 0.82
        ai_service calls feedback_service internally:
        POST http://feedback_service:8090/api/v1/feedback
        Body: {feedback_type, subject, description, priority, category,
               channel, issue_lga, issue_ward, project_id, submitter_name,
               is_anonymous, media_urls}
        → feedback_service returns {id, unique_ref}
        → ai_conversations.submitted_feedback updated with [{"feedback_id","unique_ref"}]
        → ai_conversations.status = "submitted", stage = "done"
```

---

### Stage 2 — Feedback Ingestion (feedback_service)

```
feedback_service (port 8090)
 │
 ├─ 2a. Feedback stored in feedback_db.feedbacks
 │      status = SUBMITTED
 │      unique_ref = GRV/SGG/APP-YYYY-NNNN
 │
 ├─ 2b. Kafka event published: riviwa.feedback.events
 │      key = project_id
 │      payload: {
 │        event_type: "feedback.submitted",
 │        feedback_id, unique_ref, feedback_type, priority,
 │        category, project_id, org_id, channel, submitted_at
 │      }
 │
 └─ 2c. Notification published: riviwa.notifications
        → notification_service delivers:
          • SMS / WhatsApp acknowledgement to PAP (if phone known)
          • In-app / push alert to assigned GRM officer
```

---

### Stage 3 — Organisation & Auth Events (Auth Service → Kafka)

```
auth_service (port 8000)
 │
 ├─ 3a. On user login → JWT issued
 │      → Staff login event published to Kafka (riviwa.user.events)
 │      → analytics_service Kafka consumer writes to analytics_db.staff_logins
 │        (used by /analytics/staff/last-logins and /analytics/staff/login-not-read)
 │
 └─ 3b. On project created / updated → riviwa.organisation.events
        → ai_service Kafka consumer updates ai_project_kb
        → Qdrant re-indexes the project embedding
```

---

### Stage 4 — GRM Officer Processes Feedback (feedback_service)

```
GRM Officer (Web Dashboard / Mobile App)
 │
 │  PATCH /api/v1/feedback/{id}/status
 ▼
feedback_service
 │
 ├─ 4a. status SUBMITTED → ACKNOWLEDGED
 │      feedback_db.feedbacks.status updated
 │      target_resolution_date set (based on priority SLA)
 │      feedback_actions row inserted (action_type=ACKNOWLEDGE)
 │      Kafka event: riviwa.feedback.events (feedback.acknowledged)
 │
 ├─ 4b. status ACKNOWLEDGED → IN_REVIEW
 │      feedback_actions row inserted (action_type=REVIEW_STARTED)
 │      Kafka event: feedback.in_review
 │
 ├─ 4c. status IN_REVIEW → RESOLVED
 │      feedbacks.resolved_at = now()
 │      feedback_actions row: action_type=RESOLVED, resolution_note
 │      Kafka event: feedback.resolved
 │      Notification to PAP: your issue has been resolved
 │
 └─ 4d. Optional: ESCALATED → re-assigned to higher committee
        feedback_actions row: action_type=ESCALATED
        Kafka: feedback.escalated
```

---

### Stage 5 — Spark Streaming Jobs (Real-time Analytics)

```
spark_jobs container
 │
 ├─ 5a. SLA Monitor (streaming, ~30s micro-batch)
 │      Reads: Kafka topic riviwa.feedback.events
 │      Computes: ack_deadline, res_deadline per priority
 │      Writes: analytics_db.sla_records (upsert)
 │        - ack_sla_met, ack_sla_breached
 │        - res_sla_met, res_sla_breached
 │        - days_unresolved
 │
 ├─ 5b. Hotspot Detector (streaming, 1h sliding window)
 │      Reads: Kafka topic riviwa.feedback.events
 │      Computes: grievance count per (location, category) in 1h window
 │      Detects: spike_factor > 3× baseline avg
 │      Writes: analytics_db.hotspot_alerts
 │        - location, category, count_in_window, spike_factor, baseline_avg
 │        - alert_status = "active"
 │
 └─ 5c. Live Dashboard (streaming, 5-min micro-batch)
        Reads: Kafka topic riviwa.feedback.events
        Computes: rolling 24h counts (submitted/resolved/escalated)
        Writes: Redis DB 6 (live counters, TTL=24h)
          - "dashboard:{project_id}:submitted_24h"
          - "dashboard:{project_id}:resolved_24h"
```

---

### Stage 6 — Spark Batch Jobs (Scheduled Analytics)

```
spark_jobs → APScheduler
 │
 ├─ 6a. Historical Analytics (daily @ 02:00 UTC)
 │      Reads: feedback_db (full scan per project)
 │      Computes: daily/weekly/monthly aggregates
 │      Writes: analytics_db.daily_metrics
 │
 ├─ 6b. Staff Analytics (daily @ 03:00 UTC)
 │      Reads: feedback_db.feedbacks + feedback_actions
 │             + analytics_db.staff_logins (from Kafka/auth events)
 │      Computes: per-committee resolution rate, avg hours
 │      Writes: analytics_db.committee_performance_snapshots
 │      → Used by /analytics/staff/committee-performance (use_live=false)
 │
 └─ 6c. ML Escalation Predictor (daily @ 04:00 UTC)
        Reads: feedback_db (historical patterns)
        Computes: escalation probability score per open grievance
        Writes: analytics_db.escalation_predictions
        (Used in future risk scoring dashboard)
```

---

### Stage 7 — Analytics API Queries (analytics_service)

```
GRM Manager / Dashboard
 │
 │  GET /api/v1/analytics/...?project_id=...
 ▼
analytics_service (port 8095)
 │
 ├─ 7a. Feedback endpoints → read-only query to feedback_db
 │      (feedback/unread, feedback/overdue, feedback/not-processed,
 │       feedback/time-to-open, feedback/processed-today, feedback/resolved-today)
 │
 ├─ 7b. Grievance endpoints
 │      grievances/unresolved → feedback_db (live)
 │      grievances/sla-status → analytics_db.sla_records (Spark-computed)
 │                               falls back to live feedback_db if empty
 │      grievances/hotspots   → analytics_db.hotspot_alerts (Spark-computed)
 │
 ├─ 7c. Suggestion endpoints → read-only query to feedback_db
 │      (by-location, frequency, implementation-time, unread,
 │       implemented-today, implemented-this-week)
 │
 └─ 7d. Staff endpoints → analytics_db.staff_logins + feedback_db
        committee-performance → analytics_db or live feedback_db
        last-logins           → analytics_db.staff_logins
        unread-assigned       → feedback_db
        login-not-read        → analytics_db.staff_logins ∩ feedback_db
```

---

### Stage 8 — AI Insights (Groq)

```
GRM Manager
 │
 │  POST /api/v1/analytics/ai/ask
 │  {"question": "...", "project_id": "...", "context_type": "sla"}
 ▼
analytics_service
 │
 ├─ 8a. Build context dict based on context_type:
 │        • Always: get_summary_counts() → feedback_db aggregate
 │        • sla: unresolved + overdue + sla_records (analytics_db)
 │        • grievances: unresolved + overdue + sla
 │        • suggestions: implementation_time + unread_suggestions
 │        • hotspots: active hotspot_alerts (analytics_db)
 │        • committees: committee_performance rows (feedback_db)
 │        • staff: unread_assigned + logins_today (analytics_db)
 │        • general: all of the above
 │
 └─ 8b. Call Groq API
        Model: llama-3.3-70b-versatile
        System prompt: "You are a GRM analytics expert..."
        User message: f"Data context:\n{json(context_data)}\n\nQuestion: {question}"
        →  Response: natural language answer in English
        →  Return: {answer, context_used, model}
```

---

### Complete Flow Summary

```
PAP
 │ SMS/WhatsApp/Web
 ▼
ai_service ──► Qdrant RAG (project matching)
     │         Groq (conversation turns)
     │         Obsidian vault (policy context)
     │
     │ internal HTTP
     ▼
feedback_service ──► feedback_db.feedbacks (SUBMITTED)
     │                feedback_db.feedback_actions
     │
     │ Kafka: riviwa.feedback.events
     ▼
┌────────────────────────────────────────────────┐
│  Kafka Consumers                               │
│                                                │
│  spark_jobs ──► analytics_db.sla_records       │
│             ──► analytics_db.hotspot_alerts    │
│             ──► analytics_db.committee_perf    │
│             ──► Redis DB6 (live counters)      │
│                                                │
│  notification_service ──► SMS/push/email/WA    │
│                                                │
│  ai_service ──► ai_project_kb (project sync)  │
└────────────────────────────────────────────────┘
     │
     │ Auth events: riviwa.user.events
     ▼
analytics_db.staff_logins (login tracking)
     │
     ▼
analytics_service (port 8095)
  ├── feedback/* → feedback_db (live read-only)
  ├── grievances/* → feedback_db + analytics_db
  ├── suggestions/* → feedback_db (live read-only)
  ├── staff/* → analytics_db + feedback_db
  └── ai/ask → Groq (llama-3.3-70b-versatile)
                  ↑ context built from all of the above
```

---

*Generated 2026-04-12 — Riviwa platform v2.0*
