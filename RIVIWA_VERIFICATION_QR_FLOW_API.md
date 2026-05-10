# Riviwa QR Verification & Feedback Flow — API Reference

**Version:** 1.1.0  
**Date:** 2026-05-11  
**Services:** `verification_service` (port 8125), `qr_service` (port 8120), `feedback_service` (port 8090)  
**Kafka topic:** `riviwa.verification.events`

---

## Overview

This document covers the complete QR-to-feedback lifecycle introduced and fixed in the 2026-05-11 session:

1. A consumer scans a QR/SMS code → `AUTHENTIC`, `ALREADY_USED`, or `UNRECOGNIZED`
2. Consumer submits feedback referencing the QR code (`qr_short_code`)
3. `feedback_service` publishes `feedback.submitted` with `short_code` in payload
4. `qr_service` consumer marks the QR as used
5. Next scan returns `ALREADY_USED` with the linked `feedback_id`

Throughout the flow, `verification_service` emits Kafka events to `riviwa.verification.events` for real-time org notifications and analytics.

---

## Part 1 — Verification Endpoints

### `POST /api/v1/verify`

Verify a QR code or SMS short code. Public — no authentication required.

**Request body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | ✅ | Short code (`ABCD1234`), SMS code (`UTT-ABCD1234`), or full QR URL (`https://app.riviwa.com/qr/ABCD1234`) |
| `lat` | float | — | Scanner GPS latitude (stored for heatmap) |
| `lng` | float | — | Scanner GPS longitude (stored for heatmap) |
| `user_agent` | string | — | Browser/app user agent (auto-read from header if omitted) |

```json
POST /api/v1/verify
{
  "code": "MYVKWZG5",
  "lat": -6.7924,
  "lng": 39.2083
}
```

**Response — `AUTHENTIC`**

Returned when the code is genuine and no feedback has been submitted yet. Consumer can now leave feedback.

```json
{
  "result": "AUTHENTIC",
  "verification_event_id": "582ec36a-e312-452e-8575-d6a6cae2df2a",
  "message": "This is a genuine Riviwa-verified product. You can now leave feedback about your experience.",
  "short_code": "MYVKWZG5",
  "sms_code": "YAS-TA-MYVKWZG5",
  "qr_type": "PRODUCT",
  "organisation_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "scan_count": 1,
  "redirect_url": "https://app.riviwa.com/feedback?qr=MYVKWZG5",
  "product": {
    "product_id": "4ae4ecf5-...",
    "title": "Riviwa ProBook X15",
    "brand": "Riviwa",
    "rsin": "R5D2GRM2HX",
    "product_type": "LAPTOP",
    "listing_status": "BUYABLE",
    "price": 1850000.00,
    "organisation_id": "163f4a76-..."
  },
  "actions": ["submit_feedback"]
}
```

**Response — `ALREADY_USED`**

Returned when feedback has already been submitted through this code. Serves as permanent proof of service.

```json
{
  "result": "ALREADY_USED",
  "verification_event_id": "d9e1f2a3-...",
  "message": "Feedback has already been submitted using this code. This is your permanent proof of service.",
  "short_code": "MYVKWZG5",
  "sms_code": "YAS-TA-MYVKWZG5",
  "qr_type": "SERVICE",
  "organisation_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "scan_count": 2,
  "feedback_id": "99cbcb54-e2dd-458f-8923-c835d916de04",
  "actions": ["track_feedback", "view_service_details"]
}
```

For `RECEIPT` type QR codes, `ALREADY_USED` also returns `service_context`:
```json
{
  "service_context": {
    "service_name": "Customer Care",
    "attendant_name": "Zuhura Rashidi",
    "location": "Dar es Salaam Branch",
    "transaction_datetime": "2026-05-11T10:30:00",
    "receipt_number": "RCP-2026-00142",
    "amount": 5000.00,
    "currency": "TZS"
  },
  "note": "This QR code is permanent evidence that you used this service."
}
```

**Response — `UNRECOGNIZED`**

Returned when the code is not found in the system.

```json
{
  "result": "UNRECOGNIZED",
  "verification_event_id": "651f20a1-...",
  "message": "This code was not found in the Riviwa system. If you believe this is a genuine product or service, please report it.",
  "actions": ["report_fake"]
}
```

**`qr_type` values and messages:**

| `qr_type` | AUTHENTIC message |
|-----------|-------------------|
| `PRODUCT` | "This is a genuine Riviwa-verified product. You can now leave feedback..." |
| `RECEIPT` | "Receipt verified. This is a genuine service transaction. You can now leave your feedback." |
| `SERVICE` / `LOCATION` | "Verified. This is a registered Riviwa service point. You can now leave feedback." |
| other | "Verified. This is a genuine Riviwa-registered entity. You can now leave feedback." |

**Side effects (new as of 2026-05-11):**
- A `VerificationEvent` row is saved to `verification_db`
- `scan_count` is incremented on the QR code in `qr_db`
- A `QRScan` row is created in `qr_db`
- A `verification.scanned` Kafka event is published to `riviwa.verification.events`

---

### `POST /api/v1/verify/report-fake`

Report a suspected fake or counterfeit product. Requires a `verification_event_id` from a prior `POST /verify` call. Public — no authentication required.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `verification_event_id` | string (UUID) | ✅ | ID from the preceding `POST /verify` response |
| `description` | string | — | Free-text description of the suspicion |
| `reporter_phone` | string | — | Reporter's phone number |
| `reporter_name` | string | — | Reporter's name |
| `gps_lat` | float | — | GPS latitude of where the fake was found |
| `gps_lng` | float | — | GPS longitude |
| `location_description` | string | — | Human-readable location |
| `photo` | file | — | Photo of the suspected fake (≤10MB, any image format) |

**Flow:**
1. Call `POST /verify` with the code first — get `verification_event_id`
2. Call `POST /verify/report-fake` with that ID

```
# Step 1
POST /api/v1/verify
{ "code": "FAKECODE1" }
→ { "result": "UNRECOGNIZED", "verification_event_id": "651f20a1-..." }

# Step 2
POST /api/v1/verify/report-fake
-F verification_event_id=651f20a1-...
-F description="Product label looks printed, not embossed"
-F gps_lat=-6.7924
-F gps_lng=39.2083
-F photo=@suspicious_product.jpg
```

**Response (no photo):**
```json
{
  "report_id": "817ed453-0d03-4e38-a5af-a7ffc38ee54a",
  "status": "SUBMITTED",
  "message": "Thank you for reporting. Our field team will investigate this location.",
  "has_photo": false,
  "location": { "lat": -6.7924, "lng": 39.2083, "description": null }
}
```

**Response (with photo — AI analysis included):**
```json
{
  "report_id": "817ed453-...",
  "status": "SUBMITTED",
  "message": "Thank you for reporting. Our field team will investigate this location.",
  "has_photo": true,
  "location": { "lat": -6.7924, "lng": 39.2083, "description": "Near Kariakoo market" },
  "ai_analysis": {
    "verdict": "LIKELY_COUNTERFEIT",
    "confidence": 0.87,
    "clip_similarity": 0.43,
    "counterfeit_indicators": ["Label font mismatch", "Color saturation off", "Hologram missing"],
    "reasoning": "The product label shows signs of inkjet printing inconsistent with genuine packaging.",
    "recommended_action": "Confiscate and escalate to brand protection team"
  }
}
```

**Side effects (new as of 2026-05-11):**
- A `FakeSuspectReport` row is saved
- Photo uploaded to MinIO (`riviwa-verification` bucket)
- AI image analysis run via `ai_service` (CLIP + Groq Llama 4 Scout)
- A `verification.fake_reported` Kafka event published to `riviwa.verification.events`

---

### `GET /api/v1/verify/stats`

Platform-wide verification statistics for the last 30 days. Requires authentication.

**Headers:** `Authorization: Bearer <token>`

**Query parameters:** None required (defaults to last 30 days)

```
GET /api/v1/verify/stats
Authorization: Bearer eyJ...
```

**Response:**
```json
{
  "period": {
    "from": "2026-04-11T20:22:47.386230",
    "to": "2026-05-11T20:22:47.386266"
  },
  "total_verifications": 29,
  "authentic_count": 15,
  "already_used_count": 7,
  "unrecognized_count": 7,
  "genuine_rate": 51.72,
  "fake_reports": {
    "CONFIRMED_FAKE": 1,
    "SUBMITTED": 3
  }
}
```

---

### `GET /api/v1/verify/heatmap`

Geographic heatmap of unrecognized scan locations (counterfeit hotspots). Requires authentication.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "total_points": 5,
  "points": [
    { "lat": -6.7924, "lng": 39.2083, "at": "2026-05-05T08:00:10" },
    { "lat": -6.8160, "lng": 39.2803, "at": "2026-05-05T08:35:35" }
  ],
  "clusters": [
    { "cell": "-6.792,39.208", "count": 1, "lat": -6.792, "lng": 39.208 }
  ],
  "period": {
    "from": "2026-04-11T20:22:47",
    "to": "2026-05-11T20:22:47"
  }
}
```

---

## Part 2 — New Internal QR Endpoint

### `POST /api/v1/internal/qr/increment-scan` *(new — 2026-05-11)*

**Service:** `qr_service` (port 8120)  
**Auth:** `X-Service-Key` header (internal services only — not exposed via Nginx)  
**Called by:** `verification_service` automatically after every successful code lookup

Records a scan event and increments `scan_count` on the QR code. Called by `verification_service` as a fire-and-forget after every `AUTHENTIC` or `ALREADY_USED` verify response. Never blocks the verify response — failures are logged as warnings only.

**Request body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `qr_code_id` | string (UUID) | ✅ | UUID of the QR code record |
| `short_code` | string | ✅ | Short code string (for `QRScan` row) |
| `scanner_ip` | string | — | Scanner IP address |
| `user_agent` | string | — | Scanner browser/app user agent |

```json
POST /api/v1/internal/qr/increment-scan
X-Service-Key: <INTERNAL_SERVICE_KEY>

{
  "qr_code_id": "96ed677c-a2c9-4573-a824-556499add081",
  "short_code": "MYVKWZG5",
  "scanner_ip": "172.18.0.37",
  "user_agent": "Mozilla/5.0 (Android 14)"
}
```

**Response:**
```json
{
  "recorded": true,
  "qr_code_id": "96ed677c-a2c9-4573-a824-556499add081"
}
```

**Side effects:**
- `qr_codes.scan_count` incremented by 1
- New `qr_scans` row created with `organisation_id`, `qr_type`, IP, UA

**Error responses:**

| Status | Error | Cause |
|--------|-------|-------|
| 401 | `UNAUTHORIZED` | Missing or invalid `X-Service-Key` |
| 404 | `QR_NOT_FOUND` | No QR code found with the given UUID |
| 500 | Internal error | DB failure |

---

## Part 3 — Updated Feedback Submission (qr_short_code field)

### `POST /api/v1/feedback` *(updated — 2026-05-11)*

**New field:** `qr_short_code`

When a consumer scans a QR code and then submits feedback, include the `qr_short_code` field to link the feedback to the QR code. This triggers `ALREADY_USED` on the next scan of that code.

**New field added to `StaffSubmitFeedback`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `qr_short_code` | string | — | Short code from the QR scan (e.g. `MYVKWZG5`). Triggers ALREADY_USED on next scan. |

```json
POST /api/v1/feedback
Authorization: Bearer <manager/admin/owner token>

{
  "org_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "feedback_type": "applause",
  "category": "other",
  "channel": "mobile_app",
  "subject": "Great service at Yas Tanzania",
  "description": "Staff were very helpful and professional.",
  "qr_short_code": "MYVKWZG5"
}
```

---

### `POST /api/v1/my/feedback` *(updated — 2026-05-11)*

**New field:** `qr_short_code` (same as staff endpoint above)

```json
POST /api/v1/my/feedback
Authorization: Bearer <consumer token>

{
  "feedback_type": "grievance",
  "description": "The product I bought did not match the description on the packaging.",
  "issue_lga": "Ilala",
  "qr_short_code": "YDQK8CKK"
}
```

**How `qr_short_code` links to ALREADY_USED:**

1. Consumer submits feedback with `qr_short_code`
2. `feedback_service` includes `short_code` in the `feedback.submitted` Kafka event
3. `qr_service` Kafka consumer (`riviwa.feedback.events`) receives the event
4. `qr_service` calls `mark_feedback(short_code, feedback_id)` — sets `qr_scans.feedback_submitted = true`
5. Next `POST /verify` on the same code returns `ALREADY_USED` with `feedback_id`

---

## Part 4 — Kafka Events: `riviwa.verification.events`

**Topic:** `riviwa.verification.events` *(new — 2026-05-11)*  
**Publisher:** `verification_service`  
**Consumers:** analytics aggregation, org notification triggers  
**Partition key:** `organisation_id` (or `"unrecognized"` for unknown codes)

All events share this envelope:

```json
{
  "event_type": "verification.scanned",
  "event_id": "516a3464-52b6-4635-be20-3d5c12c5ce03",
  "occurred_at": "2026-05-11T20:45:09.285609+00:00",
  "schema_version": "1.0",
  "service": "verification_service",
  "payload": { ... }
}
```

---

### `verification.scanned`

Published on every `POST /verify` call — for all three results (AUTHENTIC, ALREADY_USED, UNRECOGNIZED).

**Payload:**

| Field | Type | Description |
|-------|------|-------------|
| `verification_event_id` | UUID | ID of the VerificationEvent row |
| `short_code` | string | The code that was scanned |
| `result` | string | `AUTHENTIC` / `ALREADY_USED` / `UNRECOGNIZED` |
| `organisation_id` | UUID or null | Owning org (null for UNRECOGNIZED) |
| `product_id` | UUID or null | Product linked to QR code (null if none) |
| `qr_type` | string or null | `PRODUCT` / `SERVICE` / `RECEIPT` / `LOCATION` |
| `scanner_lat` | float or null | GPS latitude of scanner |
| `scanner_lng` | float or null | GPS longitude of scanner |

```json
{
  "event_type": "verification.scanned",
  "event_id": "516a3464-52b6-4635-be20-3d5c12c5ce03",
  "occurred_at": "2026-05-11T20:45:09.285609+00:00",
  "schema_version": "1.0",
  "service": "verification_service",
  "payload": {
    "verification_event_id": "406dea7c-947b-4482-8d30-91e0a41d17c2",
    "short_code": "MYVKWZG5",
    "result": "AUTHENTIC",
    "organisation_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
    "product_id": "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
    "qr_type": "PRODUCT",
    "scanner_lat": -6.7924,
    "scanner_lng": 39.2083
  }
}
```

**Use cases for consumers:**
- Org receives real-time alert when their product/service QR is scanned
- Analytics service aggregates scan counts per org, per product, per day
- Fraud detection: burst of UNRECOGNIZED scans at same location = counterfeit ring

---

### `verification.fake_reported`

Published on every `POST /verify/report-fake` call.

**Payload:**

| Field | Type | Description |
|-------|------|-------------|
| `report_id` | UUID | ID of the `FakeSuspectReport` row |
| `verification_event_id` | UUID | ID of the preceding verification event |
| `short_code` | string | The code that was reported as fake |
| `organisation_id` | UUID or null | Org that owns the code (null if UNRECOGNIZED scan) |
| `has_photo` | boolean | Whether a photo was uploaded |
| `gps_lat` | float or null | Location of the report |
| `gps_lng` | float or null | Location of the report |

```json
{
  "event_type": "verification.fake_reported",
  "event_id": "9ed0a613-3154-4036-b56e-9b85abe38445",
  "occurred_at": "2026-05-11T20:45:11.607954+00:00",
  "schema_version": "1.0",
  "service": "verification_service",
  "payload": {
    "report_id": "817ed453-0d03-4e38-a5af-a7ffc38ee54a",
    "verification_event_id": "406dea7c-947b-4482-8d30-91e0a41d17c2",
    "short_code": "FAKECODE1",
    "organisation_id": null,
    "has_photo": true,
    "gps_lat": -6.7924,
    "gps_lng": 39.2083
  }
}
```

**Use cases for consumers:**
- Notify org admin immediately when a fake is reported for their product
- Escalate to fraud investigation team
- Feed into counterfeit heatmap analytics

---

## Part 5 — Complete ALREADY_USED Flow

```
Consumer scans QR                         verification_service
────────────────────────────────────────────────────────────────
POST /verify { code: "MYVKWZG5" }
        │
        ├─► GET /internal/qr/lookup (qr_service)
        │       Returns: { qr_type, org_id, product_id, feedback_already_submitted: false }
        │
        ├─► POST /internal/qr/increment-scan (qr_service)     ← NEW
        │       scan_count + 1, QRScan row created
        │
        ├─► Kafka: verification.scanned → riviwa.verification.events  ← NEW
        │
        └─► Response: { result: "AUTHENTIC", scan_count: 1, ... }


Consumer submits feedback                 feedback_service
────────────────────────────────────────────────────────────────
POST /api/v1/my/feedback
  { qr_short_code: "MYVKWZG5", ... }     ← NEW field
        │
        ├─► Save Feedback to DB
        │
        └─► Kafka: feedback.submitted     riviwa.feedback.events
              { short_code: "MYVKWZG5",  ← NEW field in event
                feedback_id: "99cbcb54..." }


qr_service Kafka consumer                 qr_service
────────────────────────────────────────────────────────────────
Receives: feedback.submitted
  payload.short_code = "MYVKWZG5"        ← Fixed: was looking at wrong level
  payload.feedback_id = "99cbcb54..."
        │
        └─► mark_feedback("MYVKWZG5", "99cbcb54...")
              qr_scans.feedback_submitted = true
              qr_scans.feedback_id = "99cbcb54..."


Consumer scans QR again                   verification_service
────────────────────────────────────────────────────────────────
POST /verify { code: "MYVKWZG5" }
        │
        ├─► GET /internal/qr/lookup (qr_service)
        │       Returns: { feedback_already_submitted: true, feedback_id: "99cbcb54..." }
        │
        └─► Response: {
                result: "ALREADY_USED",
                feedback_id: "99cbcb54...",
                actions: ["track_feedback", "view_service_details"]
              }
```

---

## Part 6 — Changes to Existing Kafka Events

### `riviwa.feedback.events` — `feedback.submitted` *(updated — 2026-05-11)*

**New field added to payload:**

| Field | Type | Description |
|-------|------|-------------|
| `short_code` | string or null | QR/SMS short code submitted with the feedback via `qr_short_code` field. Null if no QR code was scanned. |

Before (old payload):
```json
{
  "feedback_id": "99cbcb54-...",
  "project_id": null,
  "feedback_type": "applause",
  "category": "other",
  "org_id": "163f4a76-..."
}
```

After (new payload):
```json
{
  "feedback_id": "99cbcb54-...",
  "project_id": null,
  "feedback_type": "applause",
  "category": "other",
  "org_id": "163f4a76-...",
  "short_code": "MYVKWZG5"
}
```

**Important:** `project_id` is now nullable in the event (was previously always a UUID). This reflects the v2.4 change allowing feedback without a project.

---

## Part 7 — Error Reference

### Verification Errors

| Status | Error code | Cause |
|--------|-----------|-------|
| 422 | `CODE_REQUIRED` | Empty `code` field in request body |
| 404 | `VERIFICATION_EVENT_NOT_FOUND` | `verification_event_id` not in DB (for report-fake) |

### QR Internal Errors

| Status | Error code | Cause |
|--------|-----------|-------|
| 401 | `UNAUTHORIZED` | Missing/invalid `X-Service-Key` |
| 404 | `QR_NOT_FOUND` | QR UUID not found (increment-scan) |
| 404 | `CODE_NOT_FOUND` | Short code not found (lookup, mark-feedback) |

---

## Part 8 — Bugs Fixed (2026-05-11)

| Bug | Root cause | Fix |
|-----|-----------|-----|
| `scan_count` never incremented | `verification_service` only called `/lookup` (read-only) | Added `POST /internal/qr/increment-scan`, called after every verify |
| `QRScan` rows had null `organisation_id` | SQLModel class missing fields that exist in DB schema | Added `organisation_id` and `qr_type` to `QRScan` model |
| ALREADY_USED never triggered | `feedback.submitted` event had no `short_code` field | Added `qr_short_code` to submit schemas; passed to Kafka event |
| qr_service consumer silently ignored all events | Looked for `event["short_code"]` instead of `event["payload"]["short_code"]` | Fixed payload lookup in consumer |
| qr_service consumer crashed on zstd messages | `cramjam` not in requirements; feedback_service uses zstd compression | Added `cramjam==2.11.0` to qr_service |
| Stats/heatmap returned 401 for public access | Auth dependency required | By design — these are staff-only endpoints |

---

## Part 9 — Infrastructure Notes

### Kafka Topic Created

```bash
# Topic was created manually on 2026-05-11:
kafka-topics.sh --bootstrap-server localhost:9092 \
  --create --topic riviwa.verification.events \
  --partitions 3 --replication-factor 1
```

In production (3-node Kafka), replication factor should be 3 and `min.insync.replicas=2`.

### MinIO Bucket

Fake report photos are uploaded to `riviwa-verification` bucket (auto-created on first upload). Presigned URL expiry: 1 year.

### Services Updated

| Service | What changed | Rebuilt |
|---------|-------------|---------|
| `verification_service` | New producer, config, verify.py, verify_service.py, main.py | ✅ |
| `qr_service` | New `increment-scan` endpoint, QRScan model fix, consumer fix, cramjam | ✅ |
| `feedback_service` | qr_short_code in schemas, producer, service | ✅ |
