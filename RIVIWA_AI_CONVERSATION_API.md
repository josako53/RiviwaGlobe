# Riviwa AI Conversation API

**Base URL:** `https://api.riviwa.com/api/v1`  
**Service port:** `8085`  
**Version:** v1

Riviwa AI is a conversational interface that collects grievances, suggestions, and applause through guided dialogue. It supports Swahili and English, auto-detects language, and auto-submits feedback when confidence ≥ 0.82.

---

## Channels

| Channel | Value |
|---------|-------|
| Web app | `web` |
| Mobile app | `mobile` |
| SMS | `sms` (inbound webhook) |
| WhatsApp | `whatsapp` (inbound webhook) |
| Phone call | `phone_call` (Twilio IVR) |

---

## Conversation Stages

| Stage | Description |
|-------|-------------|
| `greeting` | AI greets, asks for language preference |
| `identify` | AI identifies the user (name, phone) |
| `collecting` | AI collects feedback details |
| `clarifying` | AI asks follow-up questions |
| `confirming` | AI reads back summary, asks to confirm |
| `followup` | Feedback submitted, AI offers follow-up |
| `done` | Conversation closed |

---

## Conversation Status

| Status | Description |
|--------|-------------|
| `active` | Conversation in progress |
| `confirming` | Awaiting Consumer confirmation |
| `submitted` | Feedback submitted to Riviwa |
| `followup` | Post-submission follow-up |
| `abandoned` | Consumer stopped responding |
| `timed_out` | Session expired (TTL) |
| `failed` | AI or submission error |

---

## Endpoints

---

### 1. Start a Conversation

**`POST /ai/conversations`**

Starts a new AI conversation session. No authentication required for anonymous web/mobile consumers. Pass `user_id` from JWT for registered users (auto-identifies them).

**Authentication:** Optional JWT (`Authorization: Bearer <token>`)

#### Request Body

```json
{
  "channel": "web",
  "language": "sw",
  "org_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "project_id": null,
  "user_id": null,
  "web_token": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `channel` | `string` | No | `web` \| `mobile`. Default: `web` |
| `language` | `string` | No | `sw` (Swahili) \| `en` (English). Default: `sw` |
| `org_id` | `UUID` | No | Organisation UUID — locks conversation to this org's projects. Omit for auto-detect |
| `project_id` | `UUID` | No | Pre-select a project. Omit to let AI detect from context |
| `user_id` | `UUID` | No | Authenticated user ID from JWT. If provided, Consumer is auto-identified |
| `web_token` | `string` | No | Anonymous session token for web (used when no `user_id`) |

#### Response `201 Created`

```json
{
  "conversation_id": "3f2e1a4b-8c7d-4e9f-b2a1-6d5c3e8f9a0b",
  "reply": "Karibu Riviwa! Mimi ni msaidizi wako wa AI. Je, ungependa kuwasiliana kwa Kiswahili au Kiingereza?",
  "status": "active",
  "stage": "greeting",
  "turn_count": 1,
  "confidence": 0.0,
  "language": "sw",
  "submitted": false,
  "submitted_feedback": [],
  "org_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "project_name": null,
  "is_urgent": false,
  "incharge_name": null,
  "incharge_phone": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | `UUID` | Session ID — use in all subsequent requests |
| `reply` | `string` | AI's opening message to show the user |
| `status` | `string` | Conversation status (see table above) |
| `stage` | `string` | Current stage in the dialogue flow |
| `turn_count` | `integer` | Number of turns so far |
| `confidence` | `float` | AI confidence in extracted data (0.0–1.0). Submits at ≥ 0.82 |
| `language` | `string` | Active language (`sw` or `en`) |
| `submitted` | `boolean` | `true` when feedback has been auto-submitted |
| `submitted_feedback` | `array` | List of submitted feedback items (populated on submit) |
| `org_id` | `UUID\|null` | Organisation the conversation is locked to |
| `project_name` | `string\|null` | Detected or pre-selected project name |
| `is_urgent` | `boolean` | `true` if AI detected urgency signals |
| `incharge_name` | `string\|null` | Name of project incharge (populated when project identified) |
| `incharge_phone` | `string\|null` | Phone of project incharge |

---

### 2. Send a Message

**`POST /ai/conversations/{conversation_id}/message`**

Send the Consumer's message to Riviwa AI. The AI responds in kind, progressively extracts feedback fields, and auto-submits when confidence ≥ 0.82.

**Authentication:** None

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `conversation_id` | `UUID` | Conversation session ID from Step 1 |

#### Request Body

```json
{
  "message": "Barabara ya Kisutu ina mashimo makubwa sana, magari yanashindwa kupita.",
  "media_urls": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | `string` | **Yes** | Consumer's message text. Min 1 char, max 4000 chars |
| `media_urls` | `array[string]\|null` | No | Optional image/document URLs (e.g. WhatsApp proof photos). Pass `null` if none |

#### Response `200 OK` — Collecting

```json
{
  "conversation_id": "3f2e1a4b-8c7d-4e9f-b2a1-6d5c3e8f9a0b",
  "reply": "Asante kwa taarifa hiyo. Unaweza kunieleza zaidi — tatizo hili limeanza lini?",
  "status": "active",
  "stage": "collecting",
  "turn_count": 3,
  "confidence": 0.45,
  "language": "sw",
  "submitted": false,
  "submitted_feedback": [],
  "org_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "project_name": "Mradi wa Barabara Dar es Salaam",
  "is_urgent": false,
  "incharge_name": "Eng. Rashid Mwangi",
  "incharge_phone": "+255754321098"
}
```

#### Response `200 OK` — Auto-submitted (confidence ≥ 0.82)

```json
{
  "conversation_id": "3f2e1a4b-8c7d-4e9f-b2a1-6d5c3e8f9a0b",
  "reply": "Malalamiko yako yamewasilishwa. Nambari ya kufuatilia: GRV-2026-0412. Utapata ujumbe wa SMS ukithibitisha.",
  "status": "submitted",
  "stage": "followup",
  "turn_count": 7,
  "confidence": 0.91,
  "language": "sw",
  "submitted": true,
  "submitted_feedback": [
    {
      "feedback_id": "c9a1e2f3-4b5d-6789-abcd-ef0123456789",
      "unique_ref": "GRV-2026-0412",
      "feedback_type": "grievance"
    }
  ],
  "org_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "project_name": "Mradi wa Barabara Dar es Salaam",
  "is_urgent": false,
  "incharge_name": "Eng. Rashid Mwangi",
  "incharge_phone": "+255754321098"
}
```

**`submitted_feedback` object:**

| Field | Type | Description |
|-------|------|-------------|
| `feedback_id` | `UUID` | Internal feedback UUID |
| `unique_ref` | `string` | Human-readable tracking number e.g. `GRV-2026-0412` |
| `feedback_type` | `string` | `grievance` \| `suggestion` \| `compliment` \| `inquiry` |

---

### 3. Get Conversation

**`GET /ai/conversations/{conversation_id}`**

Retrieve the full conversation including transcript, extracted data, and all submitted feedback.

**Authentication:** None

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `conversation_id` | `UUID` | Conversation session ID |

#### Response `200 OK`

```json
{
  "conversation_id": "3f2e1a4b-8c7d-4e9f-b2a1-6d5c3e8f9a0b",
  "channel": "web",
  "status": "submitted",
  "stage": "followup",
  "language": "sw",
  "turn_count": 7,
  "confidence": 0.91,
  "is_registered": true,
  "submitter_name": "John Komba",
  "project_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "project_name": "Mradi wa Barabara Dar es Salaam",
  "extracted_data": {
    "feedback_type": "grievance",
    "description": "Barabara ya Kisutu ina mashimo makubwa",
    "location": "Kisutu, Dar es Salaam",
    "submitter_name": "John Komba",
    "submitter_phone": "+255712345678",
    "confidence": 0.91
  },
  "submitted_feedback": [
    {
      "feedback_id": "c9a1e2f3-4b5d-6789-abcd-ef0123456789",
      "unique_ref": "GRV-2026-0412",
      "feedback_type": "grievance"
    }
  ],
  "transcript": [
    {
      "role": "assistant",
      "content": "Karibu Riviwa! Mimi ni msaidizi wako...",
      "timestamp": "2026-05-17T08:00:00Z"
    },
    {
      "role": "user",
      "content": "Barabara ya Kisutu ina mashimo makubwa sana...",
      "timestamp": "2026-05-17T08:00:45Z"
    }
  ],
  "is_urgent": false,
  "incharge_name": "Eng. Rashid Mwangi",
  "incharge_phone": "+255754321098",
  "started_at": "2026-05-17T08:00:00Z",
  "last_active_at": "2026-05-17T08:05:30Z",
  "completed_at": "2026-05-17T08:05:30Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `channel` | `string` | `web` \| `mobile` \| `sms` \| `whatsapp` \| `phone_call` |
| `is_registered` | `boolean` | Whether the submitter has a Riviwa account |
| `submitter_name` | `string\|null` | Name extracted by AI |
| `extracted_data` | `object` | All fields extracted so far (feedback_type, description, location, etc.) |
| `transcript` | `array` | Full dialogue history. Each item: `{role, content, timestamp}` |
| `started_at` | `ISO8601` | When the conversation was created |
| `last_active_at` | `ISO8601` | Last message timestamp |
| `completed_at` | `ISO8601\|null` | When the conversation was submitted/closed |

---

### 4. Send Voice Message

**`POST /ai/conversations/{conversation_id}/voice-message`**

Send an audio file as a message. The AI transcribes it (Whisper/Google STT) and processes it as a text message.

**Authentication:** None  
**Content-Type:** `multipart/form-data`

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `conversation_id` | `UUID` | Conversation session ID |

#### Request Body (form-data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `audio` | `file` | **Yes** | Audio file. Supported: `.mp3`, `.wav`, `.ogg`, `.m4a`, `.webm` |

#### Response `200 OK`

Same as [Send a Message](#2-send-a-message) response.

---

### 5. Inbound SMS Webhook

**`POST /ai/webhooks/sms`**

Handles inbound SMS messages from Africa's Talking or Twilio. Auto-creates a conversation if the phone number has no active session.

**Authentication:** SMS provider signature header

#### Request Body (form-data or JSON — provider dependent)

```json
{
  "from": "+255712345678",
  "text": "Tatizo la maji",
  "to": "RIVIWA"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `from` | `string` | Sender's phone number (E.164) |
| `text` | `string` | SMS body |
| `to` | `string` | Short code or long number that received the SMS |

#### Response `200 OK`

```json
{
  "status": "processed",
  "reply": "Karibu Riviwa! ..."
}
```

---

### 6. Inbound WhatsApp Webhook

**`POST /ai/webhooks/whatsapp`**

Handles inbound WhatsApp messages from the Meta Cloud API.

**Authentication:** None (verified by `hub.verify_token`)

#### Verification (GET)

**`GET /ai/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<challenge>`**

Returns the `hub.challenge` value as plain text to verify the webhook with Meta.

#### Request Body

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "changes": [
        {
          "value": {
            "messages": [
              {
                "from": "255712345678",
                "type": "text",
                "text": { "body": "Tatizo la barabara" }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

#### Response `200 OK`

```json
{ "status": "ok" }
```

---

## Admin Endpoints

> **Authentication required:** `Authorization: Bearer <staff_jwt>`

---

### 7. List All Conversations

**`GET /ai/admin/conversations`**

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | `string` | — | Filter by status: `active`, `submitted`, `abandoned`, etc. |
| `channel` | `string` | — | Filter by channel: `web`, `sms`, `whatsapp`, etc. |
| `org_id` | `UUID` | — | Filter by organisation |
| `limit` | `integer` | `50` | Max results |
| `offset` | `integer` | `0` | Pagination offset |

#### Response `200 OK`

```json
{
  "items": [
    {
      "conversation_id": "3f2e1a4b-...",
      "channel": "sms",
      "status": "submitted",
      "stage": "followup",
      "submitter_name": "Amina Juma",
      "turn_count": 9,
      "confidence": 0.88,
      "project_name": "Mradi wa Maji Dodoma",
      "is_urgent": true,
      "started_at": "2026-05-17T07:30:00Z",
      "last_active_at": "2026-05-17T07:38:00Z"
    }
  ],
  "total": 142,
  "limit": 50,
  "offset": 0
}
```

---

### 8. Get Conversation Detail (Admin)

**`GET /ai/admin/conversations/{conversation_id}`**

Same response as [Get Conversation](#3-get-conversation) with additional staff-only fields.

---

### 9. Force Submit (Staff Override)

**`POST /ai/admin/conversations/{conversation_id}/force-submit`**

Force-submit a conversation that is stuck or abandoned. Staff override — bypasses confidence threshold.

**Authentication:** Staff JWT

#### Response `200 OK`

```json
{
  "status": "submitted",
  "submitted_feedback": [
    {
      "feedback_id": "c9a1e2f3-...",
      "unique_ref": "GRV-2026-0413",
      "feedback_type": "grievance"
    }
  ]
}
```

---

## Internal Endpoints

> **Authentication:** `X-Service-Key: <INTERNAL_SERVICE_KEY>` header

---

### 10. Classify Feedback

**`POST /ai/internal/classify`**

Auto-detect `project_id` and `category_id` for a piece of text. Used by feedback_service for intelligent routing.

#### Request Body

```json
{
  "text": "Daraja la Selander lina ufa mkubwa upande wa kaskazini",
  "org_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "language": "sw"
}
```

#### Response `200 OK`

```json
{
  "project_id": "7a8b9c0d-...",
  "project_name": "Miundombinu Dar es Salaam",
  "category_id": "b1c2d3e4-...",
  "category_name": "Barabara na Madaraja",
  "confidence": 0.87,
  "feedback_type": "grievance"
}
```

---

### 11. Candidate Projects

**`POST /ai/internal/candidate-projects`**

Returns top matching projects for a given location + text. Used for project pre-selection.

#### Request Body

```json
{
  "text": "tatizo la maji safi",
  "org_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "location": "Dodoma, Tanzania",
  "top_k": 5
}
```

#### Response `200 OK`

```json
{
  "candidates": [
    {
      "project_id": "a1b2c3d4-...",
      "project_name": "Mradi wa Maji Dodoma",
      "score": 0.94,
      "distance_km": 2.3
    },
    {
      "project_id": "e5f6a7b8-...",
      "project_name": "DAWASA Maji Safi",
      "score": 0.81,
      "distance_km": 5.1
    }
  ]
}
```

---

## Error Responses

All errors follow a consistent envelope:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description."
}
```

| HTTP | Error Code | When |
|------|-----------|------|
| `404` | `NOT_FOUND` | Conversation ID does not exist |
| `400` | `VALIDATION_ERROR` | Invalid request body |
| `400` | `CONVERSATION_CLOSED` | Sending a message to a completed conversation |
| `401` | `UNAUTHORISED` | Missing or invalid JWT / service key |
| `422` | `UNPROCESSABLE_ENTITY` | Missing required field |
| `500` | `INTERNAL_ERROR` | Unexpected server error |

---

## Quick Start — Full Web Conversation Flow

```bash
# 1. Start conversation
curl -X POST https://api.riviwa.com/api/v1/ai/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "language": "sw",
    "org_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17"
  }'

# → Save conversation_id from response

# 2. Send messages (repeat until submitted=true)
curl -X POST https://api.riviwa.com/api/v1/ai/conversations/{conversation_id}/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Barabara ya Kisutu ina mashimo makubwa"}'

# 3. Retrieve full transcript
curl https://api.riviwa.com/api/v1/ai/conversations/{conversation_id}
```

---

## Notes

- **Auto-submit:** Riviwa AI submits feedback automatically when `confidence ≥ 0.82` — no extra API call needed. Watch for `"submitted": true` in the response.
- **Language detection:** AI auto-switches language mid-conversation if the Consumer switches. The `language` field in the response always reflects the current active language.
- **Urgency detection:** If `is_urgent: true`, the feedback is flagged for priority review and escalation.
- **Session TTL:** Inactive conversations are marked `timed_out` after 30 minutes of no messages.
- **Confidence scale:** `0.0` = no data collected, `1.0` = fully confident. Auto-submits at `0.82`.
