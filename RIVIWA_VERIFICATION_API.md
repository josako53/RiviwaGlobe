# Riviwa Product & Service Verification API

**Base URL:** `https://api.riviwa.com/api/v1`  
**Service port:** `8125`  
**Version:** 1.1.0

Verify product authenticity and service receipts via QR codes or SMS short codes. Handles genuine/used/unrecognized results, counterfeit reporting with GPS + photo, AI image analysis, field agent dispatch, and heatmap analytics.

---

## Verification Results

| Result | Meaning |
|--------|---------|
| `AUTHENTIC` | Code is genuine — feedback not yet submitted |
| `ALREADY_USED` | Feedback already submitted through this code (permanent proof) |
| `UNRECOGNIZED` | Code not found in the Riviwa system |

## QR Types

| Type | Use case |
|------|---------|
| `PRODUCT` | Physical product authenticity (medicines, seeds, goods) |
| `RECEIPT` | Service transaction receipt (bank, hospital, utility) |
| `LOCATION` | Service point / branch verification |
| `SERVICE` | General service delivery confirmation |

---

## Endpoints

---

### 1. Verify a Code

**`POST /verify`**

Verify a QR code or SMS short code. Accepts the raw code from a QR scan, a URL containing the code, or an SMS short code.

**Authentication:** None

#### Request Body

```json
{
  "code": "N9PEWMW5",
  "lat": -6.7924,
  "lng": 39.2083,
  "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | `string` | **Yes** | QR short code, SMS code, or full QR URL (`https://riviwa.com/qr/N9PEWMW5`) |
| `lat` | `float` | No | Scanner GPS latitude (for heatmap analytics) |
| `lng` | `float` | No | Scanner GPS longitude |
| `user_agent` | `string` | No | Browser/device user agent |

---

#### Response — `AUTHENTIC`

```json
{
  "result": "AUTHENTIC",
  "verification_event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "This is a genuine Riviwa-verified product. You can now leave feedback about your experience.",
  "short_code": "N9PEWMW5",
  "sms_code": "CRDB-N9PEWMW5",
  "qr_type": "PRODUCT",
  "organisation_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "scan_count": 1,
  "redirect_url": "https://riviwa.com/feedback?code=N9PEWMW5",
  "actions": ["submit_feedback"],
  "product": {
    "product_id": "7a8b9c0d-1e2f-3456-abcd-ef0123456789",
    "title": "Tembo Premium Cement 50kg",
    "brand": "Tembo",
    "rsin": "TZ-CEM-2026-0041",
    "product_type": "building_materials",
    "listing_status": "active",
    "price": 28000,
    "organisation_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17"
  }
}
```

---

#### Response — `ALREADY_USED`

```json
{
  "result": "ALREADY_USED",
  "verification_event_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "message": "Feedback has already been submitted for this transaction. This is your permanent proof of service.",
  "short_code": "N9PEWMW5",
  "sms_code": "CRDB-N9PEWMW5",
  "qr_type": "RECEIPT",
  "organisation_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "scan_count": 2,
  "feedback_id": "c3d4e5f6-a7b8-9012-cdef-012345678902",
  "actions": ["track_feedback", "view_service_details"],
  "service_context": {
    "service_name": "Cash Withdrawal",
    "department": "Teller Services",
    "attendant_name": "Emmanuel Mwamba",
    "location": "CRDB Kariakoo Branch",
    "transaction_datetime": "2026-05-15T10:30:00Z",
    "receipt_number": "TXN-2026-00432",
    "amount": 700000,
    "currency": "TZS"
  },
  "note": "This QR code is permanent evidence that you used this service."
}
```

---

#### Response — `UNRECOGNIZED`

```json
{
  "result": "UNRECOGNIZED",
  "verification_event_id": "d4e5f6a7-b8c9-0123-defa-123456789012",
  "message": "This code was not found in the Riviwa system. If you believe this is a genuine product or service, please report it.",
  "actions": ["report_fake"]
}
```

---

**Full response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `result` | `string` | `AUTHENTIC` \| `ALREADY_USED` \| `UNRECOGNIZED` |
| `verification_event_id` | `UUID` | Use this ID when filing a fake report |
| `message` | `string` | Human-readable result message (show to user) |
| `short_code` | `string\|null` | Cleaned short code |
| `sms_code` | `string\|null` | SMS-formatted code (e.g. `CRDB-N9PEWMW5`) |
| `qr_type` | `string\|null` | `PRODUCT` \| `RECEIPT` \| `LOCATION` \| `SERVICE` |
| `organisation_id` | `UUID\|null` | Organisation that owns this code |
| `scan_count` | `integer` | Total number of times this code has been scanned |
| `redirect_url` | `string\|null` | Feedback URL (AUTHENTIC only) |
| `feedback_id` | `UUID\|null` | Existing feedback ID (ALREADY_USED only) |
| `actions` | `array[string]` | Suggested next actions |
| `product` | `object\|null` | Product details (PRODUCT type only) |
| `service_context` | `object\|null` | Receipt service details (RECEIPT ALREADY_USED only) |

---

### 2. Report Fake / Counterfeit

**`POST /verify/report-fake`**

Report a suspected counterfeit product or unrecognized code. Optionally attach a photo for AI analysis (CLIP + Llama 4 Scout). Requires a `verification_event_id` from a prior verify call.

**Authentication:** None  
**Content-Type:** `multipart/form-data`

#### Request Body (form-data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `verification_event_id` | `string` | **Yes** | UUID from the prior `POST /verify` response |
| `reporter_phone` | `string` | No | Reporter's phone number (for follow-up) |
| `reporter_name` | `string` | No | Reporter's name |
| `description` | `string` | No | Description of the suspected fake |
| `gps_lat` | `float` | No | GPS latitude of where the fake was found |
| `gps_lng` | `float` | No | GPS longitude |
| `location_description` | `string` | No | Human-readable location (e.g. "Kariakoo Market, Stall 42") |
| `photo` | `file` | No | Photo of the suspected counterfeit. Supported: `.jpg`, `.png`, `.webp` |

#### Example Request (curl)

```bash
curl -X POST https://api.riviwa.com/api/v1/verify/report-fake \
  -F "verification_event_id=d4e5f6a7-b8c9-0123-defa-123456789012" \
  -F "reporter_phone=+255712345678" \
  -F "reporter_name=Amina Juma" \
  -F "description=Packaging looks different, seal is broken" \
  -F "gps_lat=-6.8160" \
  -F "gps_lng=39.2803" \
  -F "location_description=Kariakoo Market, Stall 42" \
  -F "photo=@/path/to/photo.jpg"
```

#### Response `201 Created` — Without photo

```json
{
  "report_id": "e5f6a7b8-c9d0-1234-efab-234567890123",
  "status": "SUBMITTED",
  "message": "Thank you for reporting. Our field team will investigate this location.",
  "has_photo": false,
  "location": {
    "lat": -6.8160,
    "lng": 39.2803,
    "description": "Kariakoo Market, Stall 42"
  }
}
```

#### Response `201 Created` — With photo + AI analysis

```json
{
  "report_id": "e5f6a7b8-c9d0-1234-efab-234567890123",
  "status": "SUBMITTED",
  "message": "Thank you for reporting. Our field team will investigate this location.",
  "has_photo": true,
  "location": {
    "lat": -6.8160,
    "lng": 39.2803,
    "description": "Kariakoo Market, Stall 42"
  },
  "ai_analysis": {
    "verdict": "LIKELY_COUNTERFEIT",
    "confidence": 0.87,
    "clip_similarity": 0.43,
    "counterfeit_indicators": [
      "Logo font mismatch",
      "Packaging colour off",
      "Seal tamper evidence missing"
    ],
    "reasoning": "The label typography and colour saturation differ significantly from genuine product database. CLIP similarity score of 0.43 is below the 0.65 genuine threshold.",
    "recommended_action": "Escalate to field agent for physical verification. Do not purchase."
  }
}
```

**`ai_analysis` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `verdict` | `string` | `LIKELY_GENUINE` \| `LIKELY_COUNTERFEIT` \| `INCONCLUSIVE` |
| `confidence` | `float` | AI confidence 0.0–1.0 |
| `clip_similarity` | `float` | Visual similarity to genuine product (0.0–1.0). Below 0.65 = suspicious |
| `counterfeit_indicators` | `array[string]` | Specific visual anomalies detected |
| `reasoning` | `string` | AI explanation of verdict |
| `recommended_action` | `string` | Suggested next step |

---

## Reports Management

> **Authentication required:** `Authorization: Bearer <jwt_token>`

---

### 3. List Fake Reports

**`GET /verify/reports`**

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `organisation_id` | `UUID` | — | Filter by organisation |
| `status` | `string` | — | `SUBMITTED` \| `UNDER_INVESTIGATION` \| `CONFIRMED_FAKE` \| `DISMISSED` \| `RESOLVED` |
| `page` | `integer` | `1` | Page number |
| `size` | `integer` | `20` | Results per page (max 100) |

#### Response `200 OK`

```json
{
  "total": 47,
  "page": 1,
  "size": 20,
  "items": [
    {
      "id": "e5f6a7b8-c9d0-1234-efab-234567890123",
      "verification_event_id": "d4e5f6a7-b8c9-0123-defa-123456789012",
      "short_code_scanned": "N9PEWMW5",
      "status": "UNDER_INVESTIGATION",
      "reporter_phone": "+255712345678",
      "reporter_name": "Amina Juma",
      "description": "Packaging looks different, seal is broken",
      "photo_url": "https://minio.riviwa.com/riviwa-verification/fake-reports/...",
      "gps_lat": -6.8160,
      "gps_lng": 39.2803,
      "location_description": "Kariakoo Market, Stall 42",
      "organisation_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
      "assigned_agent_id": "f6a7b8c9-d0e1-2345-fabc-345678901234",
      "ai_analysis": {
        "verdict": "LIKELY_COUNTERFEIT",
        "confidence": 0.87,
        "clip_similarity": 0.43,
        "counterfeit_indicators": ["Logo font mismatch", "Packaging colour off"],
        "reasoning": "...",
        "recommended_action": "Escalate to field agent"
      },
      "created_at": "2026-05-17T08:00:00Z",
      "updated_at": "2026-05-17T09:30:00Z",
      "resolved_at": null,
      "resolution_notes": null
    }
  ]
}
```

---

### 4. Get Report Detail

**`GET /verify/reports/{report_id}`**

#### Response `200 OK`

Same as item in list above, plus `assignment_history`:

```json
{
  "id": "e5f6a7b8-...",
  "...": "...",
  "assignment_history": [
    {
      "agent_id": "f6a7b8c9-d0e1-2345-fabc-345678901234",
      "assigned_at": "2026-05-17T09:30:00Z",
      "completed_at": null,
      "notes": null
    }
  ]
}
```

---

### 5. Update Report Status

**`PATCH /verify/reports/{report_id}`**

#### Request Body

```json
{
  "status": "CONFIRMED_FAKE",
  "resolution_notes": "Field agent confirmed counterfeit goods at Kariakoo Stall 42. Goods seized."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `SUBMITTED` \| `UNDER_INVESTIGATION` \| `CONFIRMED_FAKE` \| `DISMISSED` \| `RESOLVED` |
| `resolution_notes` | `string` | Resolution details (required when closing a report) |

Setting status to `RESOLVED`, `CONFIRMED_FAKE`, or `DISMISSED` automatically sets `resolved_at`.

#### Response `200 OK`

Updated report object.

---

### 6. Assign Field Agent

**`POST /verify/reports/{report_id}/assign`**

Assign a field agent to physically investigate a fake report. Sets report status to `UNDER_INVESTIGATION`.

#### Request Body

```json
{
  "agent_id": "f6a7b8c9-d0e1-2345-fabc-345678901234"
}
```

#### Response `200 OK`

```json
{
  "assignment_id": "a7b8c9d0-e1f2-3456-abcd-456789012345",
  "agent_id": "f6a7b8c9-d0e1-2345-fabc-345678901234",
  "agent_name": "Rashid Mwanga",
  "assigned_at": "2026-05-17T09:30:00Z",
  "report_status": "UNDER_INVESTIGATION"
}
```

---

## Field Agents

> **Authentication required:** `Authorization: Bearer <jwt_token>`

---

### 7. List Field Agents

**`GET /verify/reports/agents/list`**

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `organisation_id` | `UUID` | — | Filter by organisation |
| `is_active` | `boolean` | `true` | Filter by active status |

#### Response `200 OK`

```json
{
  "total": 8,
  "items": [
    {
      "id": "f6a7b8c9-d0e1-2345-fabc-345678901234",
      "user_id": "24513388-1822-486e-bec4-15c843172a3d",
      "name": "Rashid Mwanga",
      "phone": "+255754321098",
      "email": "rashid.mwanga@riviwa.com",
      "is_active": true,
      "assignment_count": 12
    }
  ]
}
```

---

### 8. Create Field Agent

**`POST /verify/reports/agents`**

#### Request Body

```json
{
  "user_id": "24513388-1822-486e-bec4-15c843172a3d",
  "organisation_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "name": "Rashid Mwanga",
  "phone": "+255754321098",
  "email": "rashid.mwanga@riviwa.com"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | `UUID` | **Yes** | Riviwa user ID of the agent |
| `organisation_id` | `UUID` | **Yes** | Organisation the agent belongs to |
| `name` | `string` | **Yes** | Agent's full name |
| `phone` | `string` | No | Contact phone (E.164) |
| `email` | `string` | No | Contact email |

#### Response `201 Created`

```json
{
  "id": "f6a7b8c9-d0e1-2345-fabc-345678901234",
  "name": "Rashid Mwanga",
  "organisation_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17"
}
```

---

## Analytics

> **Authentication required:** `Authorization: Bearer <jwt_token>`

---

### 9. Verification Statistics

**`GET /verify/stats`**

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `organisation_id` | `UUID` | — | Filter by organisation |
| `from_date` | `ISO8601` | 30 days ago | Start date e.g. `2026-05-01` |
| `to_date` | `ISO8601` | now | End date |

#### Response `200 OK`

```json
{
  "period": {
    "from": "2026-04-17T00:00:00",
    "to": "2026-05-17T00:00:00"
  },
  "total_verifications": 1842,
  "authentic_count": 1654,
  "already_used_count": 143,
  "unrecognized_count": 45,
  "genuine_rate": 89.79,
  "fake_reports": {
    "SUBMITTED": 12,
    "UNDER_INVESTIGATION": 8,
    "CONFIRMED_FAKE": 5,
    "DISMISSED": 3,
    "RESOLVED": 17
  }
}
```

---

### 10. Counterfeit Heatmap

**`GET /verify/heatmap`**

Returns GPS points and cluster cells of all `UNRECOGNIZED` scans — use to visualise where suspected counterfeit products are circulating.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `organisation_id` | `UUID` | — | Filter by organisation |
| `from_date` | `ISO8601` | 30 days ago | Start date |
| `to_date` | `ISO8601` | now | End date |

#### Response `200 OK`

```json
{
  "total_points": 45,
  "points": [
    { "lat": -6.8160, "lng": 39.2803, "at": "2026-05-15T14:32:00Z" },
    { "lat": -6.8165, "lng": 39.2810, "at": "2026-05-16T09:15:00Z" }
  ],
  "clusters": [
    { "cell": "-6.82,39.28", "count": 18, "lat": -6.82, "lng": 39.28 },
    { "cell": "-6.79,39.21", "count": 7,  "lat": -6.79, "lng": 39.21 }
  ],
  "period": {
    "from": "2026-04-17T00:00:00",
    "to": "2026-05-17T00:00:00"
  }
}
```

| Field | Description |
|-------|-------------|
| `points` | Raw GPS scan locations (capped at 500 for response size) |
| `clusters` | Aggregated grid cells sorted by scan count (hotspots first) |

---

## Report Status Flow

```
SUBMITTED
    ↓
UNDER_INVESTIGATION  (agent assigned)
    ↓
CONFIRMED_FAKE   ← genuine counterfeit confirmed
DISMISSED        ← false alarm
RESOLVED         ← issue resolved
```

---

## Kafka Events

The service publishes to `riviwa.verification.events`:

| Event type | Trigger |
|------------|---------|
| `verification.scanned` | Every `POST /verify` call |
| `verification.fake_reported` | Every `POST /verify/report-fake` call |

---

## Error Responses

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description."
}
```

| HTTP | Error Code | When |
|------|-----------|------|
| `422` | `CODE_REQUIRED` | Empty `code` field in verify request |
| `404` | `VERIFICATION_EVENT_NOT_FOUND` | Invalid `verification_event_id` in fake report |
| `404` | `REPORT_NOT_FOUND` | Report ID does not exist |
| `404` | `AGENT_NOT_FOUND` | Agent ID does not exist |
| `401` | `MISSING_TOKEN` | No `Authorization` header on protected endpoint |
| `401` | `INVALID_TOKEN` | Invalid or expired JWT |

---

## Quick Start — Full Verification Flow

```bash
# 1. Scan a QR code
curl -X POST https://api.riviwa.com/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "code": "N9PEWMW5",
    "lat": -6.7924,
    "lng": 39.2083
  }'

# 2a. If AUTHENTIC — redirect user to submit feedback
#     Use redirect_url from response

# 2b. If UNRECOGNIZED — report as fake
curl -X POST https://api.riviwa.com/api/v1/verify/report-fake \
  -F "verification_event_id=<id from step 1>" \
  -F "reporter_phone=+255712345678" \
  -F "gps_lat=-6.8160" \
  -F "gps_lng=39.2803" \
  -F "photo=@photo.jpg"

# 3. Admin — check stats
curl https://api.riviwa.com/api/v1/verify/stats \
  -H "Authorization: Bearer <token>"
```
