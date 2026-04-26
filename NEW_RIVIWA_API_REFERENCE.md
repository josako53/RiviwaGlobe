# NEW_RIVIWA_API_REFERENCE

> New and updated endpoints from session 2026-04-26.
> Base URL: `https://riviwa.com/api/v1`
> Auth: `Authorization: Bearer <access_token>` unless noted.

---

## Summary of Changes

| # | Type | Service | Endpoint |
|---|------|---------|---------|
| 1 | NEW | AI Service | `POST /ai/conversations/{id}/voice-message` |
| 2 | NEW | AI Service | `POST /ai/voice/call/inbound` |
| 3 | NEW | AI Service | `POST /ai/voice/call/gather` |
| 4 | NEW | AI Service | `POST /ai/voice/call/status` |
| 5 | NEW | Analytics Service | `POST /analytics/ai/ask-voice` |
| 6 | UPDATED | Feedback Service | `POST /feedback` — Kafka payload now includes all dimension fields |
| 7 | UPDATED | Feedback Service | `POST /my/feedback` — now fires `feedback.submitted` Kafka event (was missing) |
| 8 | UPDATED | Feedback Service | `PATCH /feedback/{id}/acknowledge` — Kafka payload updated |
| 9 | UPDATED | Feedback Service | `POST /feedback/{id}/escalate` — Kafka payload updated |
| 10 | UPDATED | Feedback Service | `POST /feedback/{id}/resolve` — Kafka payload updated |
| 11 | UPDATED | Feedback Service | `POST /feedback/{id}/appeal` — Kafka payload updated |
| 12 | UPDATED | Analytics Service | `POST /analytics/ai/ask` — context now includes dimensional breakdowns |
| 13 | UPDATED | AI Service | `POST /ai/conversations/{id}/message` — LLM now extracts and submits dimension IDs |
| 14 | UPDATED | Translation Service | `POST /translate` — Groq added as provider option |
| 15 | UPDATED | Translation Service | `POST /translate/batch` — Groq added as provider option |

---

## 1. NEW — AI Service: Voice Message (Web / Mobile)

### `POST /ai/conversations/{conversation_id}/voice-message`

Send a voice recording instead of a text message. The audio is:
1. Stored permanently in MinIO (`riviwa-voice/ai-conversations/{conv_id}/turn_{n}.wav`)
2. Transcribed by Groq Whisper (`whisper-large-v3-turbo`)
3. Language-confirmed via `translation_service /detect`
4. Translated to English/Swahili if needed
5. Fed into the existing AI conversation pipeline
6. Reply translated back to the caller's language if needed

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `audio` | file | Yes | Audio file — WebM, OGG, WAV, MP3, M4A, AAC (max 25 MB) |

**Path param:** `conversation_id` — UUID of an active conversation (start one first via `POST /ai/conversations/start`)

**Response** (extends the standard chat response):
```json
{
  "conversation_id": "uuid",
  "reply": "Asante kwa maelezo yako...",
  "status": "active",
  "stage": "collecting",
  "turn_count": 3,
  "confidence": 0.62,
  "language": "sw",
  "submitted": false,
  "submitted_feedback": [],
  "project_name": "Dodoma Water Supply Phase 2",
  "is_urgent": false,
  "incharge_name": null,
  "incharge_phone": null,
  "transcript": "Nina tatizo na bomba la maji...",
  "detected_language": "sw",
  "stt_confidence": 0.87,
  "translated": false,
  "original_reply": "Asante kwa maelezo yako...",
  "audio_url": "http://minio:9000/riviwa-voice/ai-conversations/uuid/turn_0001.wav"
}
```

**Errors:**
- `415` — unsupported audio format
- `400` — audio too short (< 512 bytes / ~0.3s)
- `413` — audio too large (> 25 MB)
- `422` — STT transcription returned empty

---

## 2. NEW — AI Service: Twilio Phone Call Channel

### `POST /ai/voice/call/inbound`

Twilio calls this webhook when a caller rings the Riviwa GRM phone number.
Creates a `PHONE_CALL` conversation and returns TwiML to greet the caller and start recording.

**Content-Type:** `application/x-www-form-urlencoded` (Twilio format)

| Field | Description |
|-------|-------------|
| `CallSid` | Twilio call identifier |
| `CallerCountry` | ISO country code — used to select language (`TZ/KE/UG` → Swahili, else English) |
| `From` | Caller's phone number (E.164) |
| `To` | Riviwa GRM phone number |

**Response:** TwiML XML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="sw-TZ" voice="Google.sw-TZ-Standard-A">Karibu Riviwa GRM...</Say>
  <Record maxLength="30" trim="trim-silence" timeout="5" playBeep="true"
          action="https://riviwa.com/api/v1/ai/voice/call/gather?call_sid=CA...&amp;conv_id=uuid" />
  <Say language="sw-TZ" voice="Google.sw-TZ-Standard-A">Samahani, sikusikia...</Say>
  <Redirect>...&amp;retry=1</Redirect>
</Response>
```

**Twilio console config:**
- Voice webhook URL → `https://riviwa.com/api/v1/ai/voice/call/inbound`
- HTTP method → `POST`

---

### `POST /ai/voice/call/gather`

Twilio posts here when a `<Record>` completes. Downloads the MP3, transcribes it, feeds the AI, returns TwiML reply.

**Content-Type:** `application/x-www-form-urlencoded`

**Query params:**

| Param | Description |
|-------|-------------|
| `call_sid` | Twilio CallSid |
| `conv_id` | AI conversation UUID (from inbound response) |
| `retry` | Retry count (default 0) |

**Form fields (from Twilio):**

| Field | Description |
|-------|-------------|
| `RecordingUrl` | MP3 URL of the recording |
| `CallSid` | Twilio call identifier |

**Response:** TwiML XML — either:
- AI reply + next `<Record>` (conversation continues)
- Farewell + `<Hangup>` (feedback auto-submitted)
- Retry prompt (no audio received)

**On auto-submit:**
```xml
<Response>
  <Say language="sw-TZ" voice="Google.sw-TZ-Standard-A">
    Asante sana. Tatizo lako limewasilishwa. Nambari yako ya ufuatiliaji ni GRV-2026-0042. Kwa heri.
  </Say>
  <Hangup/>
</Response>
```

---

### `POST /ai/voice/call/status`

Twilio posts here on every call status change. On terminal states (`completed`, `no-answer`, `busy`, `failed`, `canceled`) the conversation is marked `ABANDONED`.

**Content-Type:** `application/x-www-form-urlencoded`

**Query params:**

| Param | Description |
|-------|-------------|
| `conv_id` | AI conversation UUID |

**Form fields (from Twilio):**

| Field | Description |
|-------|-------------|
| `CallStatus` | `completed` \| `no-answer` \| `busy` \| `failed` \| `canceled` \| `in-progress` |
| `CallSid` | Twilio call identifier |

**Response:** HTTP `204 No Content`

**Twilio console config:**
- Status callback URL → `https://riviwa.com/api/v1/ai/voice/call/status`

---

## 3. NEW — Analytics Service: AI Insights by Voice

### `POST /analytics/ai/ask-voice`

Ask an analytics question by speaking instead of typing. Audio is transcribed via Groq Whisper, then the transcript is sent to the AI insights LLM with the requested analytics context — identical pipeline to `POST /analytics/ai/ask` but with audio input.

**Content-Type:** `multipart/form-data`
**Auth:** `Authorization: Bearer <staff_token>`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `audio` | file | Yes | Audio file — WebM, OGG, WAV, MP3, M4A, AAC (max 25 MB) |
| `scope` | string | No | `project` \| `org` \| `platform` (default: `project`) |
| `context_type` | string | No | Same values as `POST /analytics/ai/ask` (default: `general`) |
| `project_id` | UUID | Conditional | Required when `scope=project` |
| `org_id` | UUID | Conditional | Required when `scope=org` |
| `language` | string | No | STT hint: `sw` \| `en` (default: `sw`) |

**Context types:**
- `scope=project`: `general` \| `grievances` \| `suggestions` \| `sla` \| `committees` \| `hotspots` \| `staff` \| `unresolved` \| `inquiries`
- `scope=org`: `org_general` \| `org_grievances` \| `org_suggestions` \| `org_applause` \| `org_inquiries`
- `scope=platform`: `platform_general` \| `platform_grievances` \| `platform_suggestions` \| `platform_applause` \| `platform_inquiries`

**Response:**
```json
{
  "answer": "The top grievance category this month is water supply with 42 cases...",
  "transcript": "What is the top grievance category this month?",
  "detected_language": "en",
  "context_used": { "scope": "project", "summary": {}, "by_branch": [] },
  "model": "llama-3.3-70b-versatile"
}
```

**Errors:**
- `415` — unsupported audio format
- `400` — audio too short
- `413` — audio too large
- `422` — transcription returned empty text
- `503` — no STT provider configured (set `GROQ_API_KEY`)

**Browser example:**
```js
const fd = new FormData();
fd.append('audio', audioBlob, 'question.webm');
fd.append('scope', 'org');
fd.append('org_id', orgId);
fd.append('context_type', 'org_general');
const res = await fetch('/api/v1/analytics/ai/ask-voice', {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}` },
  body: fd,
});
const { answer, transcript } = await res.json();
```

---

## 4. UPDATED — Feedback Service: Kafka Payloads Now Include All Dimension Fields

All five feedback lifecycle endpoints now publish complete dimension context in their Kafka events.

### Fields added to all Kafka event payloads

| Field | Type | Events | Description |
|-------|------|--------|-------------|
| `org_id` | UUID \| null | `submitted` only | Organisation UUID — derived from project |
| `branch_id` | UUID \| null | all 5 | `auth_service OrgBranch.id` — auto-resolved from `department_id` at submission |
| `department_id` | UUID \| null | all 5 | `auth_service OrgDepartment.id` |
| `service_id` | UUID \| null | all 5 | `auth_service OrgService.id` (service_type ≠ PRODUCT) |
| `product_id` | UUID \| null | all 5 | `auth_service OrgService.id` (service_type = PRODUCT) |
| `category_def_id` | UUID \| null | all 5 | Dynamic category definition UUID |

### `POST /feedback` — Staff Submission (updated Kafka event)

No request body changes. The `feedback.submitted` Kafka event now includes:
```json
{
  "event_type": "feedback.submitted",
  "payload": {
    "feedback_id": "uuid",
    "project_id": "uuid",
    "feedback_type": "grievance",
    "category": "water_supply",
    "org_id": "uuid",
    "branch_id": "uuid",
    "department_id": "uuid",
    "service_id": "uuid",
    "product_id": "uuid",
    "category_def_id": "uuid",
    "stakeholder_engagement_id": "uuid",
    "distribution_id": "uuid"
  }
}
```

### `POST /my/feedback` — Consumer Submission (critical fix)

**Was:** Did not fire `feedback.submitted` Kafka event at all — AI service and stakeholder service were blind to all consumer-submitted feedback.

**Now:** Fires `feedback.submitted` with all dimension fields. No request body changes.

### `PATCH /feedback/{id}/acknowledge` — Updated Kafka event

`feedback.acknowledged` payload now includes `branch_id`, `department_id`, `service_id`, `product_id`, `category_def_id`.

### `POST /feedback/{id}/escalate` — Updated Kafka event

`feedback.escalated` payload now includes `branch_id`, `department_id`, `service_id`, `product_id`, `category_def_id`.

### `POST /feedback/{id}/resolve` — Updated Kafka event

`feedback.resolved` payload now includes `branch_id`, `department_id`, `service_id`, `product_id`, `category_def_id`.

### `POST /feedback/{id}/appeal` — Updated Kafka event

`feedback.appealed` payload now includes `branch_id`, `department_id`, `service_id`, `product_id`, `category_def_id`.

---

## 5. UPDATED — Analytics Service: AI Insights Context Enriched

### `POST /analytics/ai/ask`

No request body changes. When `context_type=org_general`, the AI context now additionally includes:

| New context key | Description |
|----------------|-------------|
| `by_branch` | Feedback counts + resolved % + avg resolution hours per branch |
| `by_department` | Same breakdown per department |
| `by_service` | Same breakdown per service |
| `by_product` | Same breakdown per product |
| `by_category` | Same breakdown per category definition |

The org structure (branches with UUIDs, departments, services, products) is also injected so the AI can answer "which branch has the most grievances?" with accurate data and real UUIDs.

---

## 6. UPDATED — AI Service: Conversation LLM Extracts Dimension IDs

### `POST /ai/conversations/{conversation_id}/message`

No request body changes. The LLM system prompt now instructs the model to:
- Detect `department_id`, `branch_id`, `service_id`, `product_id`, `category_def_id` from the Consumer's description
- Match mentions (e.g. "Dodoma branch", "water service") to real UUIDs from the injected org structure
- Include matched UUIDs in the auto-submitted feedback payload

**Org structure block injected into each prompt** (fetched live from auth_service):
```
ORG STRUCTURE (use these UUIDs when Consumer mentions a branch/dept/service/product):
BRANCHES: Dodoma Regional Office (id=uuid-xxx); Arusha Office (id=uuid-yyy)
DEPARTMENTS: Customer Care (id=uuid-aaa); Technical (id=uuid-bbb)
SERVICES: Water Supply (id=uuid-ccc); Sanitation (id=uuid-ddd)
PRODUCTS: Water Meter (id=uuid-eee)
```

**Updated extracted JSON schema** (fields added):
```json
{
  "department_id": null,
  "branch_id": null,
  "service_id": null,
  "product_id": null,
  "category_def_id": null
}
```

---

## 7. UPDATED — Translation Service: Groq Provider Added

### `POST /translate`
### `POST /translate/batch`

The `provider` field now accepts `"groq"`. Groq uses `llama-3.3-70b-versatile` for translation.

```json
{
  "text": "Barabara imechoka sana",
  "target_language": "en",
  "source_language": "sw",
  "provider": "groq"
}
```

**Auto-cascade order** (when `provider` is omitted or `TRANSLATION_PROVIDER=auto`):
```
google → deepl → microsoft → groq → libretranslate → nllb
```

Groq is the recommended fallback — requires only `GROQ_API_KEY` which is already configured.

---

## Nginx Changes

| Route | Change |
|-------|--------|
| `location /api/v1/ai/voice` | NEW — routes Twilio call webhooks to ai_service:8085 |
| `location /api/v1/ai/conversations` | UPDATED — `client_max_body_size 25m` added for audio uploads |

---

## Required Environment Variables (New)

| Variable | Service | Purpose |
|----------|---------|---------|
| `GROQ_API_KEY` | ai_service, translation_service | Whisper STT + LLM translation (already set) |
| `TWILIO_ACCOUNT_SID` | ai_service | Download Twilio call recordings |
| `TWILIO_AUTH_TOKEN` | ai_service | Validate Twilio webhook signatures |
| `TWILIO_PHONE_NUMBER` | ai_service | GRM phone number |
| `AI_WEBHOOK_BASE_URL` | ai_service | Twilio callback base URL (default: `https://riviwa.com`) |
| `VOICE_STORAGE_BUCKET` | ai_service | MinIO bucket for AI audio (default: `riviwa-voice`) |
