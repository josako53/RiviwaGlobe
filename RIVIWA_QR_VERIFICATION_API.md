# Riviwa QR & Verification API Reference

> Generated: 2026-05-05  
> Services: **qr_service** (port 8120) · **verification_service** (port 8125) · **ai_service** (port 8085) · **auth_service** (port 8000)  
> Base URL (production): `https://api.riviwa.com`  
> Direct (dev/server): `http://77.237.241.13:{port}`

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [QR Service — Authenticated Endpoints](#2-qr-service--authenticated-endpoints)
3. [QR Service — Internal Endpoints](#3-qr-service--internal-endpoints)
4. [QR Service — Public Endpoint](#4-qr-service--public-endpoint)
5. [Verification Service — Consumer Endpoints](#5-verification-service--consumer-endpoints)
6. [Verification Service — Staff / Admin Endpoints](#6-verification-service--staff--admin-endpoints)
7. [Verification Service — Analytics Endpoints](#7-verification-service--analytics-endpoints)
8. [AI Service — Image Intelligence Endpoints](#8-ai-service--image-intelligence-endpoints)
9. [Auth Service — SMS Code (Organisation)](#9-auth-service--sms-code-organisation)
10. [End-to-End Flows](#10-end-to-end-flows)
11. [Code Formats & Rules](#11-code-formats--rules)
12. [Error Responses](#12-error-responses)
13. [Product Service Endpoints](#13-product-service-endpoints)

---

## 1. Authentication

### JWT (Consumer/Staff endpoints)

All endpoints marked **JWT** require:
```
Authorization: Bearer <access_token>
```

Obtain a token via the 2-step login flow:

**Step 1 — Login**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "identifier": "testgrm@riviwa.com",
  "password": "TestGRM@2026!"
}
```
Response: `{ "login_token": "...", "otp_channel": "email", "expires_in_seconds": 300 }`

**Step 2 — Verify OTP**
```http
POST /api/v1/auth/login/verify-otp
Content-Type: application/json

{
  "login_token": "<from step 1>",
  "otp_code": "000000"
}
```
Response: `{ "access_token": "eyJ...", "refresh_token": "...", "expires_in": 1800 }`

> Dev/staging OTP is always `000000` — no email or SMS is sent.

---

### Internal Service Key (Service-to-service endpoints)

All endpoints marked **Internal** require:
```
X-Service-Key: <INTERNAL_SERVICE_KEY>
```
The key is shared across all Riviwa microservices and is set in the environment as `INTERNAL_SERVICE_KEY`.

---

## 2. QR Service — Authenticated Endpoints

Base path: `/api/v1/qr`  
Auth: **JWT**  
Service: `qr_service:8120`

---

### 2.1 Generate Single QR Code

```http
POST /api/v1/qr/generate
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Create a single QR code for a location, service, product, or receipt. The QR PNG image is generated and uploaded to MinIO as a background task — the response is immediate.

**Request Body:**
```json
{
  "organisation_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "qr_type": "LOCATION",
  "label": "Main Office Entrance",
  "redirect_url": "https://app.riviwa.com/feedback?qr=",
  "product_id": null,
  "project_id": null,
  "service_id": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `organisation_id` | UUID | ✅ | Organisation this QR belongs to |
| `qr_type` | string | ✅ | `LOCATION` · `SERVICE` · `PRODUCT` · `RECEIPT` |
| `label` | string | — | Human-readable label |
| `redirect_url` | string | — | Override default feedback URL |
| `product_id` | UUID | — | Link to a product (for PRODUCT type) |
| `project_id` | UUID | — | Link to a project |
| `service_id` | UUID | — | Link to a service |

**Response `201`:**
```json
{
  "id": "7ab75736-db36-4ff3-abc7-627b1235baf5",
  "short_code": "W6W4N7BG",
  "sms_code": "TARURA-W6W4N7BG",
  "qr_type": "LOCATION",
  "organisation_id": "32f183b3-...",
  "qr_image_url": "http://minio:9000/riviwa-qr-codes/...",
  "redirect_url": "https://app.riviwa.com/feedback?qr=W6W4N7BG",
  "scan_count": 0,
  "is_active": true,
  "expires_at": null,
  "created_at": "2026-05-05T14:26:46.472122"
}
```

> **SMS code format:** `{ORG_SMS_CODE}-{SHORT_CODE}` — derived from the organisation's registered `sms_code` field (e.g. `TARURA`, `CRDB`, `NMB`).

---

### 2.2 List Organisation QR Codes

```http
GET /api/v1/qr?organisation_id={uuid}&qr_type={type}&page=1&size=20
Authorization: Bearer <token>
```

**Purpose:** Paginated list of all active QR codes for an organisation.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `organisation_id` | UUID | ✅ | Filter by organisation |
| `qr_type` | string | — | Filter: `LOCATION` · `SERVICE` · `PRODUCT` · `RECEIPT` |
| `page` | int | — | Page number (default: 1) |
| `size` | int | — | Items per page (default: 20, max: 100) |

**Response `200`:**
```json
{
  "total": 5,
  "page": 1,
  "size": 20,
  "items": [{ "id": "...", "short_code": "W6W4N7BG", "sms_code": "TARURA-W6W4N7BG", ... }]
}
```

---

### 2.3 Get Single QR Code

```http
GET /api/v1/qr/{qr_id}
Authorization: Bearer <token>
```

**Purpose:** Retrieve full details of a specific QR code by its UUID.

**Path Parameter:** `qr_id` — UUID of the QR code.

**Response `200`:** Same structure as item in 2.2.

---

### 2.4 Deactivate QR Code

```http
DELETE /api/v1/qr/{qr_id}
Authorization: Bearer <token>
```

**Purpose:** Soft-deactivate a QR code. The physical code still exists in the database but `is_active` becomes `false`. Scanning a deactivated code redirects to an "unrecognized" page.

**Response `200`:**
```json
{
  "message": "QR code deactivated.",
  "short_code": "W6W4N7BG"
}
```

---

### 2.5 Queue Bulk QR Generation

```http
POST /api/v1/qr/bulk
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Generate multiple QR codes for product packaging in a single job. Returns immediately with a `batch_id`. The generation runs in the background — each QR code gets its own PNG file, and all PNGs are packaged into a downloadable ZIP. Poll `GET /api/v1/qr/bulk/{batch_id}` to track progress.

**Use case:** A manufacturer printing Riviwa QR codes onto 5,000 product boxes. Each box gets a unique code like `TARURA-AB3X9KPJ`. When a consumer scans it, they can verify the product and leave feedback.

**Request Body:**
```json
{
  "organisation_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "product_id": "aaaaaaaa-0000-0000-0000-000000000001",
  "count": 3,
  "qr_type": "PRODUCT",
  "title": "Smart Watch Pro",
  "brand": "TechBrand",
  "rsin": "RTEST00001",
  "label": "Smart Watch Pro - Unit"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `organisation_id` | UUID | ✅ | Organisation |
| `count` | int | ✅ | Number of QR codes (1–10,000) |
| `qr_type` | string | ✅ | Typically `PRODUCT` |
| `product_id` | UUID | — | Product to link each QR to |
| `title` | string | — | Product title (printed on QR label) |
| `brand` | string | — | Brand name |
| `rsin` | string | — | Riviwa Standard Identification Number |
| `label` | string | — | Human label for the batch |

**Response `202`:**
```json
{
  "batch_id": "b1e654d3-7f4b-4d95-9af0-1d5253e9907c",
  "organisation_id": "32f183b3-...",
  "qr_type": "PRODUCT",
  "count": 3,
  "status": "PENDING",
  "message": "Bulk generation queued. Poll GET /api/v1/qr/bulk/b1e654d3-... for status."
}
```

---

### 2.6 Get Bulk Batch Status

```http
GET /api/v1/qr/bulk/{batch_id}
Authorization: Bearer <token>
```

**Purpose:** Poll the status of a running bulk generation job.

**Batch statuses:**
| Status | Meaning |
|--------|---------|
| `PENDING` | Queued, not started |
| `GENERATING` | Generating QR PNG files |
| `PACKAGING` | Creating ZIP archive |
| `READY` | Done — `zip_url` is available for download |
| `FAILED` | Error — check `error_message` |

**Response `200`:**
```json
{
  "batch_id": "b1e654d3-...",
  "organisation_id": "32f183b3-...",
  "qr_type": "PRODUCT",
  "count": 3,
  "status": "READY",
  "generated_count": 3,
  "zip_url": "http://minio:9000/riviwa-qr-codes/batches/.../b1e654d3.zip",
  "error_message": null,
  "created_at": "2026-05-05T16:01:47.609444",
  "completed_at": "2026-05-05T16:01:50.244178"
}
```

---

### 2.7 Scan Analytics

```http
GET /api/v1/qr/analytics/scans?organisation_id={uuid}
Authorization: Bearer <token>
```

**Purpose:** Aggregate scan statistics for an organisation — total scans, unique scanners, and conversion rate (scans that led to feedback submission).

**Response `200`:**
```json
{
  "total_scans": 12,
  "unique_scanners": 8,
  "converted": 4,
  "conversion_rate": 33.33
}
```

---

## 3. QR Service — Internal Endpoints

Base path: `/api/v1/internal/qr`  
Auth: **Internal** (`X-Service-Key` header)  
Called by: `integration_service`, `verification_service`, `feedback_service` (Kafka consumer)

---

### 3.1 Create Receipt QR

```http
POST /api/v1/internal/qr/receipt
X-Service-Key: <INTERNAL_SERVICE_KEY>
Content-Type: application/json
```

**Purpose:** Called by `integration_service` when a third-party partner pushes a receipt (bus fare, hospital bill, grocery purchase, bank transaction, etc.). Creates a `ReceiptSession` with the full transaction context, generates a unique QR code and SMS code, uploads the QR PNG to MinIO, and returns everything needed to print on the receipt.

**Use case:** A passenger pays a bus fare at UTT. UTT's POS system pushes the receipt to Riviwa via integration_service. Riviwa generates `UTT-AB3X9KPJ`. The code is printed on the bus ticket. The passenger can either:
- Scan the QR code → directed to the Riviwa app to leave feedback
- Send SMS `UTT AB3X9KPJ` to the Riviwa SMS number → same flow by SMS

**Request Body:**
```json
{
  "organisation_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "service_name": "City Bus Line 12",
  "department": "Transport",
  "attendant_name": "John Mwangi",
  "location": "Dar es Salaam Central Station",
  "transaction_datetime": "2026-05-05T14:30:00",
  "receipt_number": "REC-2026-001",
  "amount": 2500,
  "currency": "TZS",
  "consumer_phone": "+255712345678",
  "consumer_name": "Test Consumer",
  "custom_attributes": {
    "route": "Msasani-CBD",
    "seat": "B12"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `organisation_id` | UUID | ✅ | Organisation issuing the receipt |
| `service_name` | string | — | Service provided (e.g. "City Bus Line 12") |
| `department` | string | — | Department within the org |
| `attendant_name` | string | — | Staff member who served the consumer |
| `location` | string | — | Where the service was provided |
| `transaction_datetime` | string (ISO) | — | When the transaction occurred |
| `receipt_number` | string | — | Third-party receipt/invoice number |
| `amount` | number | — | Transaction amount |
| `currency` | string | — | Currency code (e.g. `TZS`, `USD`) |
| `consumer_phone` | string | — | Consumer's phone (for SMS follow-up) |
| `consumer_name` | string | — | Consumer's name |
| `custom_attributes` | object | — | Any additional key-value pairs |

**Response `201`:**
```json
{
  "short_code": "E2GVG8PT",
  "sms_code": "TARURA-E2GVG8PT",
  "org_sms_code": "TARURA",
  "qr_image_url": "http://minio:9000/riviwa-qr-codes/.../E2GVG8PT.png",
  "qr_redirect_url": "https://app.riviwa.com/qr/E2GVG8PT",
  "redirect_url": "https://app.riviwa.com/feedback?qr=E2GVG8PT&session=TrtWUP2b...",
  "session_token": "TrtWUP2byUEZWOmfWRrVy1_OfnLnGtEImVeoeQ8tNio",
  "receipt_session_id": "a0a6d0fd-af00-4183-a7e3-07b147511aeb",
  "sms_instructions": "Text 'TARURA-E2GVG8PT' to +255XXXXXXX or reply 'E2GVG8PT' if already in conversation."
}
```

---

### 3.2 Lookup Code

```http
GET /api/v1/internal/qr/lookup?short_code={code}
X-Service-Key: <INTERNAL_SERVICE_KEY>
```

**Purpose:** Called by `verification_service` to check whether a scanned or texted code exists and whether feedback has already been submitted through it. Accepts any code format.

**Accepted formats for `short_code`:**
| Format | Example | Description |
|--------|---------|-------------|
| Bare code | `E2GVG8PT` | 8-char alphanumeric short code |
| Org-prefixed | `TARURA-E2GVG8PT` | With org SMS code prefix |
| SMS text | `TARURA E2GVG8PT` | Space-separated (from SMS body) |
| Full URL | `https://app.riviwa.com/qr/E2GVG8PT` | Strips URL, resolves code |

**Response `200`:**
```json
{
  "qr_code_id": "e7e8d74e-d3b9-446f-998b-b3d770e6f440",
  "short_code": "E2GVG8PT",
  "sms_code": "TARURA-E2GVG8PT",
  "org_sms_code": "TARURA",
  "qr_type": "RECEIPT",
  "organisation_id": "32f183b3-...",
  "product_id": null,
  "project_id": null,
  "service_id": null,
  "receipt_session_id": "a0a6d0fd-...",
  "is_active": true,
  "redirect_url": "https://app.riviwa.com/feedback?qr=E2GVG8PT&session=...",
  "feedback_already_submitted": false,
  "feedback_id": null,
  "scan_count": 1
}
```

**Response `404`:** `{"error": "CODE_NOT_FOUND"}`

---

### 3.3 Mark Code as Used (Feedback Submitted)

```http
POST /api/v1/internal/qr/mark-feedback
X-Service-Key: <INTERNAL_SERVICE_KEY>
Content-Type: application/json
```

**Purpose:** Mark a QR/SMS code as having feedback submitted through it. Once marked, subsequent verification of the same code returns `ALREADY_USED` — serving as permanent proof of service. Also called automatically by the Kafka consumer when `feedback_service` publishes a `feedback.submitted` event.

**Request Body:**
```json
{
  "short_code": "TARURA-E2GVG8PT",
  "feedback_id": "11111111-2222-3333-4444-555555555555"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `short_code` | string | ✅ | Any resolvable code format |
| `feedback_id` | UUID | — | UUID of the feedback record |

**Response `200`:**
```json
{
  "marked": true,
  "short_code": "TARURA-E2GVG8PT"
}
```

**Response `404`:** `{"error": "CODE_NOT_FOUND"}`

---

### 3.4 Get Receipt Session

```http
GET /api/v1/internal/qr/receipt-session/{session_id}
X-Service-Key: <INTERNAL_SERVICE_KEY>
```

**Purpose:** Called by `verification_service` to retrieve the full transaction context of a receipt, shown to the consumer when they verify an `ALREADY_USED` code (proof that the service was rendered).

**Response `200`:**
```json
{
  "id": "a0a6d0fd-af00-4183-a7e3-07b147511aeb",
  "organisation_id": "32f183b3-...",
  "consumer_name": "Test Consumer",
  "service_name": "City Bus Line 12",
  "department": "Transport",
  "attendant_name": "John Mwangi",
  "location": "Dar es Salaam Central Station",
  "transaction_datetime": "2026-05-05T14:30:00",
  "receipt_number": "REC-2026-001",
  "amount": 2500.0,
  "currency": "TZS",
  "custom_attributes": { "route": "Msasani-CBD", "seat": "B12" },
  "is_consumed": true
}
```

---

## 4. QR Service — Public Endpoint

Auth: **None** (consumer-facing, browser/mobile hit)

---

### 4.1 Public QR Scan Redirect

```http
GET /qr/{short_code}
```

**Purpose:** The URL encoded inside every printed Riviwa QR code. When a consumer scans the code with their camera, this endpoint:
1. Resolves the code (short or prefixed format)
2. Records the scan (IP, user-agent, fingerprint)
3. Increments the scan counter
4. Returns HTTP **302 redirect** to the Riviwa feedback app

If the code is not found or deactivated, redirects to an "unrecognized" page instead.

**No request body — path parameter only.**

**Response `302`:**
```
Location: https://app.riviwa.com/feedback?qr=E2GVG8PT&session=TrtWUP2b...
```

> **Design principle:** QR codes are **permanent evidence**. They never expire on time. A code is only marked `ALREADY_USED` when feedback is actually submitted through it — not when it's scanned, not after 30 days. Every scan increments the counter but never prevents a redirect.

---

## 5. Verification Service — Consumer Endpoints

Base path: `/api/v1/verify`  
Auth: **None** (consumer-facing)  
Service: `verification_service:8125`

---

### 5.1 Verify Code

```http
POST /api/v1/verify
Content-Type: application/json
```

**Purpose:** The primary consumer endpoint. A consumer scans or types a QR/SMS code and submits it here to check if the product or service is genuine. Works for all code formats including org-prefixed SMS codes (`TARURA-E2GVG8PT`), bare short codes (`E2GVG8PT`), SMS text format (`TARURA E2GVG8PT`), and full QR URLs.

**Three possible outcomes:**
| Result | Meaning | Next action |
|--------|---------|-------------|
| `AUTHENTIC` | Code is genuine, feedback not yet submitted | Consumer leaves feedback |
| `ALREADY_USED` | Feedback was already submitted via this code | Shows proof-of-service details |
| `UNRECOGNIZED` | Code not found in Riviwa system | Consumer reports as suspected fake |

**Request Body:**
```json
{
  "code": "TARURA-E2GVG8PT",
  "lat": -6.7924,
  "lng": 39.2083,
  "user_agent": "Mozilla/5.0 (Android 13)"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | ✅ | Any code format (bare, prefixed, SMS text, URL) |
| `lat` | float | — | Consumer GPS latitude |
| `lng` | float | — | Consumer GPS longitude |
| `user_agent` | string | — | Browser/app user-agent |

**Response `200` — AUTHENTIC:**
```json
{
  "result": "AUTHENTIC",
  "verification_event_id": "a7e599ae-9e00-4d5f-95b4-9b75b4fc09ce",
  "message": "Receipt verified. This is a genuine service transaction. You can now leave your feedback.",
  "short_code": "E2GVG8PT",
  "sms_code": "TARURA-E2GVG8PT",
  "qr_type": "RECEIPT",
  "organisation_id": "32f183b3-...",
  "scan_count": 1,
  "redirect_url": "https://app.riviwa.com/feedback?qr=E2GVG8PT&session=...",
  "actions": ["submit_feedback"]
}
```

**Response `200` — ALREADY_USED:**
```json
{
  "result": "ALREADY_USED",
  "verification_event_id": "55686b56-...",
  "message": "Feedback has already been submitted for this transaction. This is your permanent proof of service.",
  "short_code": "E2GVG8PT",
  "sms_code": "TARURA-E2GVG8PT",
  "qr_type": "RECEIPT",
  "feedback_id": "11111111-2222-3333-4444-555555555555",
  "actions": ["track_feedback", "view_service_details"],
  "service_context": {
    "service_name": "City Bus Line 12",
    "attendant_name": "John Mwangi",
    "location": "Dar es Salaam Central Station",
    "transaction_datetime": "2026-05-05T14:30:00",
    "receipt_number": "REC-2026-001",
    "amount": 2500.0,
    "currency": "TZS"
  },
  "note": "This QR code is permanent evidence that you used this service."
}
```

**Response `200` — UNRECOGNIZED:**
```json
{
  "result": "UNRECOGNIZED",
  "verification_event_id": "e09fe9d6-1c30-4d27-a075-5987a3c4b9c7",
  "message": "This code was not found in the Riviwa system. If you believe this is a genuine product or service, please report it.",
  "actions": ["report_fake"]
}
```

> The `verification_event_id` from an UNRECOGNIZED result is used in the `report-fake` call below to link the report to the failed scan.

---

### 5.2 Report Suspected Fake Product

```http
POST /api/v1/verify/report-fake
Content-Type: multipart/form-data
```

**Purpose:** After receiving an `UNRECOGNIZED` result, a consumer can report the product as a suspected counterfeit. If a photo is uploaded, the system automatically:
1. Uploads the photo to MinIO (permanent storage for field agents)
2. Sends the image bytes to `ai_service` for CLIP ViT-B/32 similarity search against the organisation's indexed product images (then platform-wide)
3. Passes the top matches to Llama 4 Scout (Groq multimodal) for visual reasoning
4. Returns the AI verdict immediately in the response — the consumer instantly knows if their product visually matches a known genuine product

**Form Data:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `verification_event_id` | string | ✅ | UUID from the preceding `POST /verify` call |
| `reporter_phone` | string | — | Consumer's phone number |
| `reporter_name` | string | — | Consumer's name |
| `description` | string | — | Free-text description of the suspected fake |
| `gps_lat` | float | — | GPS latitude of where the product was found |
| `gps_lng` | float | — | GPS longitude |
| `location_description` | string | — | Human-readable location (e.g. "Kariakoo Market, Stall 14B") |
| `photo` | file | — | Image of the suspected fake (JPEG/PNG, up to 10 MB) |

**Response `201` (no photo):**
```json
{
  "report_id": "8ba1edf6-4eb7-407d-886d-3bc60224c682",
  "status": "SUBMITTED",
  "message": "Thank you for reporting. Our field team will investigate this location.",
  "has_photo": false,
  "location": {
    "lat": -6.816,
    "lng": 39.2803,
    "description": "Kariakoo Market, Stall 14B"
  }
}
```

**Response `201` (with photo + AI analysis):**
```json
{
  "report_id": "87c428d0-7abd-48c3-bd73-fd1815c374a9",
  "status": "SUBMITTED",
  "message": "Thank you for reporting. Our field team will investigate this location.",
  "has_photo": true,
  "location": {
    "lat": -6.816,
    "lng": 39.2803,
    "description": "Kariakoo Market Stall 22"
  },
  "ai_analysis": {
    "verdict": "LIKELY_COUNTERFEIT",
    "confidence": 0.8,
    "suspected_brand": "TechBrand",
    "suspected_product": "Smart Watch Pro",
    "clip_similarity": 0.9931,
    "top_matches": [
      {
        "product_id": "aaaaaaaa-...",
        "title": "Smart Watch Pro",
        "brand": "TechBrand",
        "rsin": "RTEST00001",
        "similarity_pct": 99.3
      }
    ],
    "counterfeit_indicators": [
      "logo is blurry",
      "strap quality inconsistent with genuine product"
    ],
    "reasoning": "The 99.3% visual similarity score strongly suggests this is a counterfeit version of the Smart Watch Pro by TechBrand.",
    "recommended_action": "Dispatch field agent to investigate Kariakoo Market Stall 22."
  }
}
```

**AI verdict values:**
| Verdict | Meaning |
|---------|---------|
| `CONFIRMED_COUNTERFEIT` | Visually identical to genuine, high confidence |
| `LIKELY_COUNTERFEIT` | Strong visual match, likely fake |
| `POSSIBLY_COUNTERFEIT` | Moderate match, investigate |
| `AUTHENTIC` | Matches genuine product — not a fake |
| `DIFFERENT_PRODUCT` | Low similarity — different product entirely |
| `INCONCLUSIVE` | Cannot determine from image alone |
| `UNKNOWN_PRODUCT` | No product images indexed yet |

---

## 6. Verification Service — Staff / Admin Endpoints

Base path: `/api/v1/verify/reports`  
Auth: **JWT**

---

### 6.1 List Fake Reports

```http
GET /api/v1/verify/reports?organisation_id={uuid}&status={status}&page=1&size=20
Authorization: Bearer <token>
```

**Purpose:** List all fake product reports for an organisation. Supports filtering by status.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `organisation_id` | UUID | Filter by org |
| `status` | string | `SUBMITTED` · `UNDER_INVESTIGATION` · `CONFIRMED_FAKE` · `DISMISSED` · `RESOLVED` |
| `page` | int | Page (default: 1) |
| `size` | int | Per page (default: 20, max: 100) |

**Response `200`:**
```json
{
  "total": 4,
  "page": 1,
  "size": 20,
  "items": [
    {
      "id": "87c428d0-...",
      "short_code_scanned": "FAKEXXXX",
      "status": "CONFIRMED_FAKE",
      "reporter_phone": "+255712345679",
      "reporter_name": "AI Photo Reporter",
      "description": "Suspected fake watch",
      "photo_url": "http://minio:9000/riviwa-verification/...",
      "gps_lat": -6.816,
      "gps_lng": 39.2803,
      "location_description": "Kariakoo Market Stall 22",
      "assigned_agent_id": "44f03e19-...",
      "created_at": "2026-05-05T14:30:43",
      "updated_at": "2026-05-05T14:32:07",
      "resolved_at": "2026-05-05T14:32:07",
      "resolution_notes": "Field agent verified — confirmed counterfeit from China",
      "ai_analysis": {
        "verdict": "LIKELY_COUNTERFEIT",
        "confidence": 0.8,
        "clip_similarity": 0.9931,
        "reasoning": "..."
      }
    }
  ]
}
```

---

### 6.2 Get Single Report

```http
GET /api/v1/verify/reports/{report_id}
Authorization: Bearer <token>
```

**Purpose:** Full details of a specific report, including agent assignment history.

**Response `200`:** Same as list item plus:
```json
{
  "assignment_history": [
    {
      "agent_id": "44f03e19-...",
      "assigned_at": "2026-05-05T14:32:06",
      "completed_at": null,
      "notes": null
    }
  ]
}
```

---

### 6.3 Update Report Status

```http
PATCH /api/v1/verify/reports/{report_id}
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Update a report's investigation status and add resolution notes. Setting status to `CONFIRMED_FAKE`, `RESOLVED`, or `DISMISSED` automatically sets `resolved_at`.

**Request Body:**
```json
{
  "status": "CONFIRMED_FAKE",
  "resolution_notes": "Field agent verified — confirmed counterfeit from China"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `SUBMITTED` · `UNDER_INVESTIGATION` · `CONFIRMED_FAKE` · `DISMISSED` · `RESOLVED` |
| `resolution_notes` | string | Findings notes |

**Response `200`:** Updated report object.

---

### 6.4 Assign Field Agent to Report

```http
POST /api/v1/verify/reports/{report_id}/assign
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Dispatch a registered field agent to investigate a fake report. Sets report status to `UNDER_INVESTIGATION` and records the assignment.

**Request Body:**
```json
{
  "agent_id": "44f03e19-4951-4294-bed3-307f03bf3267"
}
```

**Response `200`:**
```json
{
  "assignment_id": "42530b9b-3376-45e5-a374-fb495d29c7a2",
  "agent_id": "44f03e19-...",
  "agent_name": "Juma Field Agent",
  "assigned_at": "2026-05-05T14:32:06.120057",
  "report_status": "UNDER_INVESTIGATION"
}
```

---

### 6.5 List Field Agents

```http
GET /api/v1/verify/reports/agents/list?organisation_id={uuid}&is_active=true
Authorization: Bearer <token>
```

**Purpose:** List registered field agents for an organisation.

**Response `200`:**
```json
{
  "total": 1,
  "items": [
    {
      "id": "44f03e19-...",
      "user_id": "24513388-...",
      "name": "Juma Field Agent",
      "phone": "+255711000001",
      "email": "juma@riviwa.com",
      "is_active": true,
      "assignment_count": 1
    }
  ]
}
```

---

### 6.6 Register Field Agent

```http
POST /api/v1/verify/reports/agents
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Register a Riviwa user as a field agent who can be dispatched to investigate fake product reports.

**Request Body:**
```json
{
  "user_id": "24513388-1822-486e-bec4-15c843172a3d",
  "organisation_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "name": "Juma Field Agent",
  "phone": "+255711000001",
  "email": "juma@riviwa.com"
}
```

**Response `201`:**
```json
{
  "id": "44f03e19-...",
  "name": "Juma Field Agent",
  "organisation_id": "32f183b3-..."
}
```

---

## 7. Verification Service — Analytics Endpoints

Auth: **JWT**

---

### 7.1 Verification Statistics

```http
GET /api/v1/verify/stats?organisation_id={uuid}&from_date=2026-04-01&to_date=2026-05-05
Authorization: Bearer <token>
```

**Purpose:** Aggregate verification statistics for a time period — counts by result and fake report breakdown.

**Response `200`:**
```json
{
  "period": {
    "from": "2026-04-05T14:31:07",
    "to": "2026-05-05T14:31:07"
  },
  "total_verifications": 12,
  "authentic_count": 8,
  "already_used_count": 4,
  "unrecognized_count": 0,
  "genuine_rate": 66.67,
  "fake_reports": {
    "SUBMITTED": 3,
    "CONFIRMED_FAKE": 1
  }
}
```

---

### 7.2 Fake Product Heatmap

```http
GET /api/v1/verify/heatmap?organisation_id={uuid}&from_date=2026-04-01&to_date=2026-05-05
Authorization: Bearer <token>
```

**Purpose:** Returns GPS points and geohash-clustered cells of all `UNRECOGNIZED` scan events — used to visualise where suspected counterfeit products are circulating geographically.

**Response `200`:**
```json
{
  "total_points": 4,
  "points": [
    { "lat": -6.7924, "lng": 39.2083, "at": "2026-05-05T08:00:10" },
    { "lat": -6.816, "lng": 39.2803, "at": "2026-05-05T14:28:45" }
  ],
  "clusters": [
    { "cell": "-6.816,39.28", "count": 2, "lat": -6.816, "lng": 39.28 },
    { "cell": "-6.792,39.208", "count": 1, "lat": -6.792, "lng": 39.208 }
  ],
  "period": { "from": "2026-04-05T14:31:08", "to": "2026-05-05T14:31:08" }
}
```

---

## 8. AI Service — Image Intelligence Endpoints

Base path: `/api/v1/ai/internal/image`  
Auth: **Internal** (`X-Service-Key`)  
Service: `ai_service:8085`

All endpoints are internal-only (not exposed via Nginx to the public internet).

---

### 8.1 Index Product Images

```http
POST /api/v1/ai/internal/image/index
X-Service-Key: <INTERNAL_SERVICE_KEY>
Content-Type: application/json
```

**Purpose:** Called by `product_service` when a product is published (or when images are updated). Downloads each image URL, generates a 512-dimensional CLIP ViT-B/32 embedding, and upserts into the Qdrant `product_images` collection. This builds the genuine product image database used by the counterfeit detection pipeline.

**Request Body:**
```json
{
  "product_id": "aaaaaaaa-0000-0000-0000-000000000001",
  "org_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "image_urls": [
    "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400",
    "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=400"
  ],
  "title": "Smart Watch Pro",
  "brand": "TechBrand",
  "rsin": "RTEST00001",
  "image_roles": ["main", "alternate"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_id` | UUID | ✅ | Product UUID |
| `org_id` | UUID | ✅ | Organisation UUID |
| `image_urls` | string[] | ✅ | List of publicly accessible image URLs |
| `title` | string | — | Product title (stored as metadata) |
| `brand` | string | — | Brand name |
| `rsin` | string | — | Riviwa Standard ID Number |
| `image_roles` | string[] | — | Role per image: `main`, `alternate`, `detail` |

**Response `201`:**
```json
{
  "product_id": "aaaaaaaa-...",
  "org_id": "32f183b3-...",
  "indexed_count": 2,
  "total_urls": 2,
  "message": "2/2 images indexed successfully."
}
```

---

### 8.2 Index Single Image by URL

```http
POST /api/v1/ai/internal/image/index-url
X-Service-Key: <INTERNAL_SERVICE_KEY>
Content-Type: application/json
```

**Purpose:** Lightweight version of `/index` for a single image. Used by `qr_service` when a product QR is generated.

**Request Body:**
```json
{
  "product_id": "aaaaaaaa-0000-0000-0000-000000000001",
  "org_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "image_url": "https://images.unsplash.com/...",
  "title": "Smart Watch Pro",
  "brand": "TechBrand",
  "rsin": "RTEST00001",
  "image_role": "main"
}
```

**Response `201`:**
```json
{
  "indexed": true,
  "product_id": "aaaaaaaa-..."
}
```

---

### 8.3 Analyse Image for Counterfeits

```http
POST /api/v1/ai/internal/image/analyze
X-Service-Key: <INTERNAL_SERVICE_KEY>
Content-Type: application/json
```

**Purpose:** The full three-stage counterfeit detection pipeline. Called by `verification_service` when a consumer submits a photo with a fake report.

**Pipeline:**
1. **CLIP ViT-B/32** — generates a 512-dim embedding of the submitted image
2. **Qdrant similarity search** — org-scoped first (same org's genuine products), then platform-wide (catches cross-brand counterfeits)
3. **Llama 4 Scout (Groq)** — multimodal visual reasoning comparing the submitted image to the top-matched genuine product image

**Request Body:**
```json
{
  "image_base64": "<base64-encoded JPEG/PNG bytes>",
  "org_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "short_code": "TARURA-E2GVG8PT",
  "location": "Kariakoo Market, Dar es Salaam"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image_base64` | string | ✅ | Base64-encoded JPEG or PNG |
| `org_id` | UUID | — | Scopes initial Qdrant search to this org's products |
| `short_code` | string | — | Code that triggered the report (context for LLM) |
| `location` | string | — | Location where fake was found (context for LLM) |

**Response `200`:**
```json
{
  "analysis_method": "clip_similarity + llama4_scout_vision",
  "clip_similarity": 0.9931,
  "top_matches": [
    {
      "product_id": "aaaaaaaa-...",
      "org_id": "32f183b3-...",
      "title": "Smart Watch Pro",
      "brand": "TechBrand",
      "rsin": "RTEST00001",
      "image_url": "https://images.unsplash.com/...",
      "similarity": 0.9931,
      "similarity_pct": 99.3
    }
  ],
  "ai_verdict": {
    "verdict": "LIKELY_COUNTERFEIT",
    "confidence": 0.8,
    "suspected_brand": "TechBrand",
    "suspected_product": "Smart Watch Pro",
    "counterfeit_indicators": ["logo blurry", "strap quality inconsistent"],
    "genuine_indicators": ["99.3% visual similarity to Smart Watch Pro"],
    "reasoning": "The high visual similarity score suggests this is a counterfeit version...",
    "recommended_action": "Dispatch field agent to Kariakoo Market."
  }
}
```

**Fallback:** If the Groq API is unavailable, returns CLIP-only verdict (`analysis_method: "clip_similarity_only"`) with simplified verdict based on similarity thresholds:
| Similarity | Verdict |
|-----------|---------|
| ≥ 82% | `LIKELY_COUNTERFEIT` |
| ≥ 70% | `POSSIBLY_COUNTERFEIT` |
| ≥ 55% | `INCONCLUSIVE` |
| < 55% | `DIFFERENT_PRODUCT` |

---

### 8.4 Search Similar Products by Image

```http
POST /api/v1/ai/internal/image/search
X-Service-Key: <INTERNAL_SERVICE_KEY>
Content-Type: application/json
```

**Purpose:** Search for visually similar products without full analysis (no LLM). Returns ranked matches by CLIP similarity. Useful for product deduplication, admin tools, or quick image lookup.

**Request Body:**
```json
{
  "image_base64": "<base64-encoded image>",
  "org_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "top_k": 5
}
```

**Response `200`:**
```json
{
  "matches": [
    {
      "product_id": "aaaaaaaa-...",
      "title": "Smart Watch Pro",
      "brand": "TechBrand",
      "similarity": 0.9699,
      "similarity_pct": 97.0
    }
  ],
  "total": 3
}
```

---

### 8.5 Collection Statistics

```http
GET /api/v1/ai/internal/image/stats
X-Service-Key: <INTERNAL_SERVICE_KEY>
```

**Purpose:** Returns statistics about the Qdrant `product_images` collection — total indexed images, vector dimensions, and model used.

**Response `200`:**
```json
{
  "collection": "product_images",
  "total_images": 4,
  "vector_dim": 512,
  "model": "clip-ViT-B-32"
}
```

---

## 9. Auth Service — SMS Code (Organisation)

### 9.1 Set Organisation SMS Code

```http
PATCH /api/v1/orgs/{org_id}
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Set or update the organisation's unique SMS prefix code. This short code (2–10 uppercase alphanumeric characters) is prepended to every QR/SMS code generated for the organisation. It must be unique platform-wide.

**Example values:** `UTT`, `CRDB`, `NMB`, `TARURA`, `CCBRT`, `TESLA`

**Request Body (partial PATCH):**
```json
{
  "sms_code": "TARURA"
}
```

| Field | Type | Validation | Description |
|-------|------|-----------|-------------|
| `sms_code` | string | 2–10 chars · uppercase · alphanumeric · globally unique | Org SMS prefix |

**Response `200`:** Full org object including:
```json
{
  "id": "32f183b3-...",
  "display_name": "TARURA Test PIU",
  "sms_code": "TARURA",
  ...
}
```

Once set, all new QR/SMS codes for this org use the format: `TARURA-{SHORT_CODE}`.

---

### 9.2 Internal — Get Org SMS Code

```http
GET /api/v1/internal/orgs/{org_id}/sms-code
X-Service-Key: <INTERNAL_SERVICE_KEY>
```

**Purpose:** Called by `qr_service` to look up an organisation's registered SMS code before generating a new QR code. Cached per `qr_service` process restart.

**Response `200`:**
```json
{
  "sms_code": "TARURA",
  "slug": "tarura-test-piu-2026",
  "display_name": "TARURA Test PIU"
}
```

If `sms_code` is null, `qr_service` derives a fallback from the org's `slug` (first 10 uppercase alphanumeric characters).

---

## 10. End-to-End Flows

### Flow A — Consumer Scans Receipt QR (Bus Ticket)

```
[Partner / Bus POS]
     │
     │  POST /api/v1/integration/receipt
     │  { organisation_id, service_name, amount, consumer_phone, ... }
     ▼
[integration_service]
     │
     │  POST /api/v1/internal/qr/receipt  (internal)
     │  { organisation_id, service_name, attendant_name, ... }
     ▼
[qr_service]
     │  1. GET /api/v1/internal/orgs/{org_id}/sms-code → "TARURA"
     │  2. Generate short_code = "E2GVG8PT"
     │  3. Build sms_code = "TARURA-E2GVG8PT"
     │  4. Save ReceiptSession + QRCode to DB
     │  5. Upload QR PNG to MinIO
     ▼
[integration_service → Partner]
  { short_code, sms_code: "TARURA-E2GVG8PT", qr_image_url, sms_instructions }
     │
     │  Printed on receipt / bus ticket
     ▼
[Consumer scans QR or texts "TARURA E2GVG8PT" to Riviwa number]
     │
     │  GET /qr/E2GVG8PT  (browser scan)
     ▼
[qr_service public]
     │  Record scan → 302 redirect
     ▼
[Riviwa App]
     │
     │  POST /api/v1/verify  { code: "TARURA-E2GVG8PT" }
     ▼
[verification_service]
     │  GET /api/v1/internal/qr/lookup?short_code=TARURA-E2GVG8PT
     │  → { qr_type: RECEIPT, feedback_already_submitted: false, ... }
     ▼
  Result: AUTHENTIC → consumer leaves feedback
     │
     │  [feedback_service publishes Kafka event: feedback.submitted]
     ▼
[qr_service Kafka consumer]
     │  Receives: { short_code: "TARURA-E2GVG8PT", feedback_id: "..." }
     │  Calls mark_feedback() → is_consumed = true
     ▼
[Next verification of same code]
  Result: ALREADY_USED + full service_context (proof of service)
```

---

### Flow B — Consumer Reports Suspected Fake Product

```
[Consumer buys product, scans unknown QR]
     │
     │  POST /api/v1/verify  { code: "FAKEXXXX", lat: -6.816, lng: 39.28 }
     ▼
[verification_service]
     │  qr_service.lookup("FAKEXXXX") → 404
     │  Save VerificationEvent (result=UNRECOGNIZED)
     │  Save UnrecognizedScanHeatmap point
     ▼
  Result: UNRECOGNIZED  +  verification_event_id: "e09fe9d6-..."
     │
     │  Consumer clicks "Report Fake" → takes photo
     │
     │  POST /api/v1/verify/report-fake  (multipart)
     │  { verification_event_id, description, gps_lat, gps_lng, photo }
     ▼
[verification_service]
     │  1. Upload photo → MinIO (riviwa-verification bucket)
     │  2. POST /api/v1/ai/internal/image/analyze
     │     { image_base64, org_id, short_code, location }
     ▼
[ai_service — image intelligence]
     │  Stage 1: CLIP ViT-B/32 → 512-dim embedding
     │  Stage 2: Qdrant search (org-scoped → platform-wide)
     │           → top match: Smart Watch Pro, 99.3% similarity
     │  Stage 3: Llama 4 Scout (Groq)
     │           → send submitted image + genuine product image
     │           → returns structured verdict
     ▼
[ai_service → verification_service]
  { verdict: LIKELY_COUNTERFEIT, confidence: 0.8, clip_similarity: 0.9931, ... }
     │
     │  Save FakeSuspectReport (with ai_analysis JSONB)
     ▼
[Consumer response — instant AI verdict]
  { report_id, status: SUBMITTED, ai_analysis: { verdict, reasoning, ... } }
     │
     │  [Field agent logs in to dashboard]
     │
     │  GET /api/v1/verify/reports?organisation_id=...
     │  POST /api/v1/verify/reports/{id}/assign  { agent_id }
     │  PATCH /api/v1/verify/reports/{id}  { status: CONFIRMED_FAKE }
```

---

### Flow C — Product Published → Images Indexed for AI

```
[Staff publishes product via product_service]
     │
     │  POST /api/v1/products/{id}/publish  (product_service)
     ▼
[product_service.publish_product()]
     │  fire-and-forget (background):
     │  repo.get_images(product_id) → [url1, url2]
     │
     │  POST /api/v1/ai/internal/image/index
     │  { product_id, org_id, image_urls, title, brand, rsin }
     ▼
[ai_service — image intelligence]
     │  For each URL:
     │    Download image → CLIP ViT-B/32 embed → upsert to Qdrant
     ▼
[Qdrant product_images collection]
  Now contains genuine product images for this product.
  Used by Stage 2 of the counterfeit detection pipeline.
```

---

### Flow D — Bulk QR for Product Packaging

```
[Manufacturer needs 5,000 QR codes for product boxes]
     │
     │  POST /api/v1/qr/bulk  { organisation_id, product_id, count: 5000,
     │                          qr_type: PRODUCT, rsin: RTARURA001 }
     ▼
[qr_service — immediate response 202]
  { batch_id: "b1e654d3-...", status: PENDING }
     │
     │  Background job runs:
     │  1. GET /api/v1/internal/orgs/{org_id}/sms-code → "TARURA"
     │  2. For each of 5,000 units:
     │     - Generate short_code
     │     - Build sms_code = "TARURA-{short_code}"
     │     - Generate QR PNG (qrcode[pil])
     │     - Upload PNG to MinIO
     │     - Save QRCode to DB
     │  3. Package all PNGs into ZIP → upload to MinIO
     ▼
[Poll: GET /api/v1/qr/bulk/{batch_id}]
  { status: READY, generated_count: 5000, zip_url: "http://minio:9000/..." }
     │
     │  Manufacturer downloads ZIP
     │  Each file: RTARURA001_{SHORT_CODE}.png
     │  Printed on product box
```

---

## 11. Code Formats & Rules

### SMS Code Format

All Riviwa QR/SMS codes follow the pattern:

```
{ORG_SMS_CODE}-{SHORT_CODE}
```

Examples:
- `TARURA-E2GVG8PT` — Tanzania Roads Authority
- `CRDB-AB3X9KPJ` — CRDB Bank  
- `UTT-W6W4N7BG` — UTT (bus company)
- `NMB-HKFJ2PQR` — NMB Bank
- `CCBRT-8YZNMPQT` — CCBRT Hospital

### Short Code Charset

All short codes use 8 characters from the unambiguous charset:
```
ABCDEFGHJKMNPQRSTUVWXYZ23456789
```
Characters removed: `O` (looks like `0`), `0` (looks like `O`), `I` (looks like `1`), `1` (looks like `I`), `L` (looks like `1`).

### Accepted Input Formats (for verify and lookup)

| Input | Resolved As |
|-------|-------------|
| `E2GVG8PT` | Bare short code lookup |
| `TARURA-E2GVG8PT` | Org-prefixed lookup |
| `TARURA E2GVG8PT` | Space-separated SMS text — normalised to `TARURA-E2GVG8PT` |
| `https://app.riviwa.com/qr/E2GVG8PT` | URL stripped to bare code `E2GVG8PT` |

### Code Lifecycle (Permanent Evidence)

```
GENERATED
    │
    ▼
AUTHENTIC  ←──── Every scan
    │
    │  (feedback submitted via app, SMS, or AI channel)
    ▼
ALREADY_USED  ←── Permanent proof of service
```

Codes **never expire on time**. `expires_at` is always `null` unless explicitly set. The only state change is `AUTHENTIC → ALREADY_USED`, which happens only when feedback is submitted.

---

## 12. Error Responses

All error responses follow the structure:
```json
{
  "error": "ERROR_CODE",
  "detail": "Human-readable message"
}
```

| HTTP | Error Code | Meaning |
|------|-----------|---------|
| 400 | `CODE_REQUIRED` | Missing code field in verify request |
| 401 | `MISSING_TOKEN` | No Bearer token |
| 401 | `INVALID_TOKEN` | JWT expired or invalid |
| 403 | `FORBIDDEN` | Wrong internal service key |
| 404 | `CODE_NOT_FOUND` | QR/SMS code does not exist |
| 404 | `SESSION_NOT_FOUND` | Receipt session not found |
| 404 | `REPORT_NOT_FOUND` | Fake report not found |
| 404 | `AGENT_NOT_FOUND` | Field agent not found |
| 404 | `BATCH_NOT_FOUND` | Bulk batch not found |
| 404 | `VERIFICATION_EVENT_NOT_FOUND` | Verification event not found |
| 422 | `image_base64 required` | Missing image in analyze request |
| 422 | `invalid base64 image` | Malformed base64 |
| 422 | `count must be 1–10000` | Bulk count out of range |
| 500 | Internal Server Error | Unexpected server error |

---

---

## 13. Product Service Endpoints

Base path: `/api/v1/products`  
Auth: **JWT** (org dashboard context required — caller must be switched into an org)  
Service: `product_service:8110`  
Nginx route: `/api/v1/products`

### Role Requirements

| Role | Can do |
|------|--------|
| `MEMBER` / `STAFF` | Read products, images, attributes, variants |
| `MANAGER` | Create, update, manage images, attributes, bullet points |
| `ADMIN` / `OWNER` | + Publish, deactivate |
| Platform `admin` / `super_admin` | All orgs, all products |

> **New in this session:** `PATCH /{product_id}/publish` now also fires a background call to `POST /api/v1/ai/internal/image/index` (ai_service) to index all the product's images into Qdrant. This builds the genuine product image database used by the counterfeit detection pipeline automatically on every publish.

---

### 13.1 Create Product

```http
POST /api/v1/products/
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Create a new product listing under the caller's active organisation. The listing starts in `DRAFT` status. All fields can be provided at creation or filled in later via PATCH. Product type (`product_type`) is **immutable after first publish**.

**Request Body:**
```json
{
  "product_type": "SMARTPHONE",
  "seller_sku": "TECHBRAND-WATCH-001",
  "title": "Smart Watch Pro",
  "brand": "TechBrand",
  "price": 250000,
  "currency": "TZS",
  "condition": "NEW",
  "quantity": 500,
  "fulfillment_method": "MERCHANT",
  "description": "Premium smart watch with heart rate monitor.",
  "main_image_url": "https://images.example.com/watch-main.jpg",
  "bullet_points": [
    { "position": 1, "content": "Heart rate & SpO2 monitoring" },
    { "position": 2, "content": "5-day battery life" }
  ],
  "images": [
    { "role": "MAIN", "position": 1, "url": "https://images.example.com/watch-main.jpg" },
    { "role": "ALTERNATE", "position": 1, "url": "https://images.example.com/watch-side.jpg" }
  ],
  "attributes": [
    { "attribute_name": "Display", "attribute_value": "1.4 inch AMOLED", "group": "Technical" }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_type` | enum | ✅ | Immutable. Determines category-attribute schema. See Product Types below. |
| `seller_sku` | string | ✅ | Your internal SKU (unique per org) |
| `title` | string | ✅ | Product title (max 500 chars) |
| `brand` | string | ✅ | Brand name |
| `price` | decimal | ✅ | Unit price (> 0) |
| `currency` | string | — | Default: `TZS` |
| `condition` | enum | — | `NEW` · `USED_LIKE_NEW` · `USED_GOOD` · `USED_ACCEPTABLE` · `REFURBISHED` · `OPEN_BOX` · `PARTS_ONLY` |
| `quantity` | int | — | Available stock |
| `fulfillment_method` | enum | — | `MERCHANT` · `RIVIWA` · `PICKUP` · `DIGITAL` |
| `main_image_url` | string | — | Required before publishing |
| `description` | string | — | Max 2000 chars |
| `bullet_points` | array | — | Max 5 items. Each: `{ position: 1–5, content: string }` |
| `images` | array | — | `{ role: MAIN/ALTERNATE, position, url, alt_text }` |
| `attributes` | array | — | `{ attribute_name, attribute_value, unit, group, position }` |
| `upc` / `ean` / `gtin` / `isbn` | string | — | Industry barcode identifiers |
| `is_parent` | bool | — | `true` if this is a variation parent |
| `parent_product_id` | UUID | — | Parent product for variant child |
| `variation_theme` | enum | — | `COLOR` · `SIZE` · `COLOR_SIZE` · `FLAVOR` · `STYLE` · etc. |

**Product Types (partial list):**
Electronics: `LAPTOP` `DESKTOP` `TABLET` `SMARTPHONE` `CAMERA` `TV` `WEARABLE`  
Apparel: `SHIRT` `PANTS` `DRESS` `JACKET` `SUIT` `TRADITIONAL_WEAR`  
Footwear: `SHOES` `SANDALS` `BOOTS` `SNEAKERS`  
Home: `COOKWARE` `FURNITURE` `SMALL_APPLIANCE` `LARGE_APPLIANCE`  
Food: `FOOD_AND_BEVERAGE` `GROCERY` `BEVERAGE`  
Health: `MEDICATION` `SUPPLEMENT` `PERSONAL_CARE` `MEDICAL_DEVICE`  
Vehicles: `CAR_NEW` `CAR_USED` `MOTORCYCLE` `BUS` `ELECTRIC_VEHICLE`  
Other: `JEWELRY` `WATCH` `TOOL` `AGRICULTURAL` `INDUSTRIAL`

**Response `201`:** Full `ProductResponse` (see §13.3).

---

### 13.2 List Products

```http
GET /api/v1/products/?product_type=SMARTPHONE&listing_status=BUYABLE&search=watch&page=1&page_size=20
Authorization: Bearer <token>
```

**Purpose:** Paginated list of products for the caller's org. Platform admins see all orgs.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `product_type` | enum | Filter by type |
| `listing_status` | enum | `DRAFT` · `PENDING_REVIEW` · `BUYABLE` · `DISCOVERABLE` · `SUPPRESSED` · `INCOMPLETE` · `INACTIVE` · `REJECTED` |
| `search` | string | Full-text search on title/brand/SKU |
| `page` | int | Default: 1 |
| `page_size` | int | Default: 20, max: 100 |

**Response `200`:**
```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3,
  "items": [
    {
      "product_id": "aaaaaaaa-0000-0000-0000-000000000001",
      "rsin": "RTEST00001",
      "organisation_id": "32f183b3-...",
      "product_type": "WEARABLE",
      "seller_sku": "TECHBRAND-WATCH-001",
      "title": "Smart Watch Pro",
      "brand": "TechBrand",
      "price": 250000,
      "currency": "TZS",
      "listing_status": "BUYABLE",
      "main_image_url": "https://...",
      "published_at": "2026-05-05T12:00:00"
    }
  ]
}
```

---

### 13.3 Get Product

```http
GET /api/v1/products/{product_id}
Authorization: Bearer <token>
```

**Purpose:** Full product detail including all images, bullet points, and flexible attributes.

**Response `200`:**
```json
{
  "product_id": "aaaaaaaa-0000-0000-0000-000000000001",
  "rsin": "RTEST00001",
  "organisation_id": "32f183b3-...",
  "product_type": "WEARABLE",
  "seller_sku": "TECHBRAND-WATCH-001",
  "title": "Smart Watch Pro",
  "brand": "TechBrand",
  "price": 250000.00,
  "currency": "TZS",
  "condition": "NEW",
  "quantity": 500,
  "fulfillment_method": "MERCHANT",
  "description": "Premium smart watch.",
  "main_image_url": "https://...",
  "listing_status": "BUYABLE",
  "is_active": true,
  "is_gated": false,
  "suppression_reason": null,
  "published_at": "2026-05-05T12:00:00",
  "created_at": "2026-05-05T10:00:00",
  "updated_at": "2026-05-05T12:00:00",
  "bullet_points": [
    { "id": "...", "position": 1, "content": "Heart rate & SpO2 monitoring" }
  ],
  "images": [
    { "id": "...", "role": "MAIN", "position": 1, "url": "https://...", "alt_text": null }
  ],
  "attributes": [
    { "id": "...", "attribute_name": "Display", "attribute_value": "1.4 inch AMOLED", "group": "Technical" }
  ]
}
```

---

### 13.4 Update Product

```http
PATCH /api/v1/products/{product_id}
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Update any product field (PATCH semantics — only fields present in the body are changed). `product_type` cannot be changed after first publish.

**Request Body:** Any subset of `ProductCreate` fields (all optional). Example:
```json
{
  "title": "Smart Watch Pro X",
  "price": 275000,
  "quantity": 450,
  "description": "Updated description with new features."
}
```

**Response `200`:** Full `ProductResponse`.

---

### 13.5 Publish Product ⭐ AI-enhanced

```http
PATCH /api/v1/products/{product_id}/publish
Authorization: Bearer <token>
```

**Purpose:** Move the product listing to `BUYABLE` status (live and purchasable). Requires at minimum: `title`, `brand`, `price`, and `main_image_url`.

**New behaviour added in this session:** After publishing, automatically fires a background call to index all product images into the Qdrant `product_images` collection via `POST /api/v1/ai/internal/image/index`. This makes the product's genuine images immediately available for the counterfeit detection pipeline — when a consumer later submits a suspected fake photo, the AI can compare it against this product's indexed images.

**No request body.**

**Response `200`:**
```json
{
  "product_id": "aaaaaaaa-0000-0000-0000-000000000001",
  "rsin": "RTEST00001",
  "listing_status": "BUYABLE",
  "published_at": "2026-05-05T12:00:00"
}
```

**Errors:**
- `400 PRODUCT_NOT_PUBLISHABLE` — missing required fields (lists which fields are missing)
- `403 FORBIDDEN` — not the product's org, or insufficient role

**Background flow triggered on publish:**
```
publish_product()
    │  fire-and-forget
    ▼
POST /api/v1/ai/internal/image/index
{
  product_id, org_id,
  image_urls: [all images from product_images table],
  title, brand, rsin,
  image_roles: [MAIN, ALTERNATE, ...]
}
    ▼
Qdrant product_images collection updated
```

---

### 13.6 Deactivate Product

```http
DELETE /api/v1/products/{product_id}
Authorization: Bearer <token>
```

**Purpose:** Soft-delete the product (`is_active=False`, `listing_status=INACTIVE`). The product remains in the database and can be reactivated. Does not delete images or attributes.

**Response `204`:** No content.

---

### 13.7 Manage Images

#### Add Image
```http
POST /api/v1/products/{product_id}/images
Authorization: Bearer <token>
Content-Type: application/json
```
```json
{
  "role": "ALTERNATE",
  "position": 2,
  "url": "https://images.example.com/watch-back.jpg",
  "alt_text": "Back view of Smart Watch Pro"
}
```

**Image roles:** `MAIN` · `ALTERNATE` · `DETAIL` · `LIFESTYLE` · `INFOGRAPHIC` · `SWATCH` · `PACKAGE` · `CERTIFICATION`

**Response `201`:** `{ "id": "...", "role": "ALTERNATE", "position": 2, "url": "...", "alt_text": "..." }`

#### List Images
```http
GET /api/v1/products/{product_id}/images
Authorization: Bearer <token>
```
**Response `200`:** Array of image objects.

#### Delete Image
```http
DELETE /api/v1/products/{product_id}/images/{image_id}
Authorization: Bearer <token>
```
**Response `204`:** No content.

---

### 13.8 Manage Bullet Points

```http
PUT /api/v1/products/{product_id}/bullet-points
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Replace all bullet points (full replacement, not merge). Maximum 5.

```json
[
  { "position": 1, "content": "Heart rate & SpO2 monitoring" },
  { "position": 2, "content": "5-day battery life" },
  { "position": 3, "content": "Water resistant IP68" }
]
```

**Response `200`:** Array of bullet point objects with IDs.

#### Get Bullet Points
```http
GET /api/v1/products/{product_id}/bullet-points
Authorization: Bearer <token>
```

---

### 13.9 Manage Flexible Attributes

```http
PUT /api/v1/products/{product_id}/attributes
Authorization: Bearer <token>
Content-Type: application/json
```

**Purpose:** Replace all name-value attributes. Used for any custom or industry-specific fields not covered by the typed category-attribute tables.

```json
[
  { "attribute_name": "Display", "attribute_value": "1.4 inch AMOLED", "group": "Technical", "position": 1 },
  { "attribute_name": "Battery", "attribute_value": "300 mAh", "group": "Technical", "position": 2 },
  { "attribute_name": "Warranty", "attribute_value": "12 months", "group": "Compliance", "position": 1, "is_searchable": true }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `attribute_name` | string | Key name (max 200 chars) |
| `attribute_value` | string | Value (max 1000 chars) |
| `unit` | string | e.g. `kg`, `cm`, `mAh` |
| `group` | string | Grouping label (Technical, Physical, Compliance, etc.) |
| `position` | int | Sort order within group |
| `is_searchable` | bool | Whether this attribute is indexed for search |

**Response `200`:** Array of attribute objects with IDs.

#### Get Attributes
```http
GET /api/v1/products/{product_id}/attributes
Authorization: Bearer <token>
```

---

### 13.10 Category-Specific Attributes

```http
GET  /api/v1/products/{product_id}/category-attrs
PUT  /api/v1/products/{product_id}/category-attrs
Authorization: Bearer <token>
```

**Purpose:** Typed attribute tables — the schema varies by `product_type`. For example:
- `LAPTOP` / `SMARTPHONE` / `TV` → `ElectronicsAttributes` (processor, RAM, storage, screen, etc.)
- `SHIRT` / `DRESS` / `JACKET` → `ApparelAttributes` (size, colour, material, gender, etc.)
- `CAR_NEW` / `CAR_USED` → `AutomotiveVehicleAttributes` (make, model, year, mileage, etc.)
- `MEDICATION` → `HealthAttributes` (dosage form, strength, etc.)
- `FOOD_AND_BEVERAGE` → `FoodBeverageAttributes` (ingredients, allergens, expiry, etc.)

**PUT Request Body** (example for `WEARABLE`):
```json
{
  "brand": "TechBrand",
  "display_type": "AMOLED",
  "screen_size_inches": 1.4,
  "battery_capacity_mah": 300,
  "water_resistance_rating": "IP68",
  "connectivity": ["Bluetooth 5.0", "GPS"],
  "compatible_os": ["Android", "iOS"],
  "sensors": ["Heart Rate", "SpO2", "Accelerometer"]
}
```

> Fields accepted depend entirely on `product_type`. Returns `{}` for types that don't have a dedicated schema.

---

### 13.11 Variants

```http
GET /api/v1/products/{product_id}/variants
Authorization: Bearer <token>
```

**Purpose:** List all child variant products under a variation parent.

**Use case:** A "Smart Watch Pro" parent with children: Red/Small, Red/Large, Blue/Small, Blue/Large — each has its own SKU, price, and stock but shares the parent's RSIN and category attributes.

**Response `200`:** Array of `ProductListItem` objects.

---

### Product Service — Error Codes

| HTTP | Error | Meaning |
|------|-------|---------|
| 400 | `PRODUCT_NOT_PUBLISHABLE` | Missing required fields for publish |
| 400 | `PRODUCT_TYPE_IMMUTABLE` | Tried to change product_type after publish |
| 409 | `DUPLICATE_SKU` | seller_sku already exists in this org |
| 403 | `FORBIDDEN` | Product belongs to a different org |
| 404 | `PRODUCT_NOT_FOUND` | Product does not exist or is inactive |
| 404 | `IMAGE_NOT_FOUND` | Image does not exist for this product |
| 422 | `VALIDATION_ERROR` | Schema validation failed |
| 400 | `BULLET_POINT_LIMIT` | More than 5 bullet points submitted |
| 400 | `ORG_NOT_FOUND` | Organisation does not exist |
| 400 | `ORG_INACTIVE` | Organisation is suspended/inactive |

---

*Riviwa QR, Verification & Product API · Built 2026-05-05*
