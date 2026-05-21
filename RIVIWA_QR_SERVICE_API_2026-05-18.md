# Riviwa QR Service API

**Service:** `qr_service`  
**Port:** `8120`  
**Base URL:** `https://api.riviwa.com/api/v1`  
**Auth:** JWT Bearer token (from `/api/v1/auth/login`) unless noted otherwise.  
**Last updated:** 2026-05-18

---

## SMS Code Naming Convention

Every QR code carries two identifiers:

| Field | Example | Purpose |
|-------|---------|---------|
| `short_code` | `UEKCY2Q9` | 8-char random code. Used in QR image URL and as the bare scan code. |
| `sms_code` | `YAS-TANZANIA-UEKCY2Q9` | Full SMS-sendable code. Format: `{ORG_DISPLAY_NAME_WITH_HYPHENS}-{SHORT_CODE}`. |
| `org_sms_code` | `YAS-TANZANIA` | The org prefix portion only. Derived automatically from the org's `display_name`. |

**Derivation rule:** `display_name.upper().replace(" ", "-")`, stripping any character that is not `A–Z`, `0–9`, or `-`.

| Org display name | `org_sms_code` | Full `sms_code` example |
|-----------------|----------------|------------------------|
| TARURA | `TARURA` | `TARURA-UEKCY2Q9` |
| Yas Tanzania | `YAS-TANZANIA` | `YAS-TANZANIA-DB2R9TPW` |
| TARURA Test PIU | `TARURA-TEST-PIU` | `TARURA-TEST-PIU-B8SHFWG9` |
| MNH | `MNH` | `MNH-RRB9USY4` |
| Azam Group | `AZAM-GROUP` | `AZAM-GROUP-232HZ3ET` |
| CRDB Bank | `CRDB-BANK` | `CRDB-BANK-962GRWGT` |
| FAO Tanzania | `FAO-TANZANIA` | `FAO-TANZANIA-3Z9FXEGP` |
| WHO Tanzania | `WHO-TANZANIA` | `WHO-TANZANIA-5PWYYZV3` |

**Code resolution** (all formats accepted by the lookup endpoint):

```
UEKCY2Q9                    → bare short_code
TARURA-UEKCY2Q9             → full sms_code (hyphen-separated)
TARURA UEKCY2Q9             → SMS-text format (space between org prefix and code)
YAS-TANZANIA UEKCY2Q9       → SMS-text format with multi-word org prefix
https://app.riviwa.com/qr/UEKCY2Q9  → full URL
```

---

## QR Types

| `qr_type` | Use case |
|-----------|---------|
| `PRODUCT` | Physical product — links to a specific product item for verification or feedback |
| `SERVICE` | Service counter or access point — links to a service entity |
| `LOCATION` | Physical location such as a branch, office, or feedback station |
| `RECEIPT` | Transaction receipt — created via the internal receipt endpoint, carries consumer details |

---

## Endpoints

---

### 1. `POST /qr/generate`

**Purpose:** Generate a single QR code. Returns immediately. QR PNG is uploaded to MinIO in the background — poll `GET /qr/{id}` for `qr_image_url`.

**Auth:** JWT Bearer

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `organisation_id` | UUID | ✅ | The org that owns this QR code |
| `qr_type` | string | — | `PRODUCT` \| `SERVICE` \| `LOCATION` \| `RECEIPT` (default: `LOCATION`) |
| `redirect_url` | string | — | Where the QR scan redirects. Auto-generated from `short_code` if omitted |
| `product_id` | UUID | — | Link to a specific product (soft FK, cross-service) |
| `service_id` | UUID | — | Link to a specific service |
| `project_id` | UUID | — | Link to a GRM project |
| `branch_id` | UUID | — | Link to a physical branch or location |
| `department_id` | UUID | — | Link to a department |
| `label` | string | — | Human-readable name shown on dashboards, e.g. `"Counter 3 – DSM Branch"` |

**Example — product QR:**
```json
POST /api/v1/qr/generate
{
  "organisation_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "qr_type":        "PRODUCT",
  "product_id":     "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
  "label":          "Azam Drinking Water 500ml — Verification QR",
  "redirect_url":   "https://app.riviwa.com/verify?product=4ae4ecf5-22d0-4f86-8079-89a2e4e48b76"
}
```

**Example — location QR with branch and department:**
```json
POST /api/v1/qr/generate
{
  "organisation_id": "163f4a76-b76b-449b-99e8-497388c8f0cf",
  "qr_type":        "LOCATION",
  "branch_id":      "1ffae914-0000-0000-0000-000000000000",
  "department_id":  "699a2c9c-2cd8-4bda-93de-88c9aed3a861",
  "label":          "YPA Department — Mbeya Branch Feedback Point"
}
```

**Response `201 Created`:**
```json
{
  "id":              "26a7b9b0-e608-448a-a78b-ab8ff3cad05b",
  "short_code":      "UEKCY2Q9",
  "sms_code":        "TARURA-UEKCY2Q9",
  "org_sms_code":    "TARURA",
  "qr_type":         "PRODUCT",
  "organisation_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
  "product_id":      "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
  "service_id":      null,
  "project_id":      null,
  "branch_id":       null,
  "department_id":   null,
  "label":           "Azam Drinking Water 500ml — Verification QR",
  "redirect_url":    "https://app.riviwa.com/verify?product=4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
  "qr_image_url":    null,
  "scan_count":      0,
  "is_active":       true,
  "batch_id":        null,
  "expires_at":      null,
  "created_at":      "2026-05-18T12:32:00.000000",
  "updated_at":      "2026-05-18T12:32:00.000000"
}
```

> `qr_image_url` is `null` immediately. Poll `GET /qr/{id}` — it populates within seconds once the background PNG upload completes.

---

### 2. `GET /qr`

**Purpose:** List QR codes for an org. Supports filtering by any entity dimension — product, service, branch, department, project, type, or batch. All filter parameters are optional and combinable.

**Auth:** JWT Bearer

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `organisation_id` | UUID | ✅ required | Scope to this org |
| `qr_type` | string | — | `PRODUCT` \| `SERVICE` \| `LOCATION` \| `RECEIPT` |
| `product_id` | UUID | — | All QR codes linked to this product |
| `service_id` | UUID | — | All QR codes linked to this service |
| `project_id` | UUID | — | All QR codes linked to this project |
| `branch_id` | UUID | — | All QR codes placed at this branch |
| `department_id` | UUID | — | All QR codes associated with this department |
| `batch_id` | UUID | — | All QR codes generated in this bulk batch |
| `is_active` | bool | `true` | `true` = active only, `false` = deactivated only, omit = all |
| `page` | int | `1` | Page number |
| `size` | int | `20` | Page size (max 100) |

**Examples:**

```
GET /api/v1/qr?organisation_id=455bd8b1-...&product_id=4ae4ecf5-...
GET /api/v1/qr?organisation_id=455bd8b1-...&qr_type=SERVICE
GET /api/v1/qr?organisation_id=455bd8b1-...&department_id=699a2c9c-...&qr_type=LOCATION
GET /api/v1/qr?organisation_id=455bd8b1-...&batch_id=088adfb1-...
GET /api/v1/qr?organisation_id=455bd8b1-...&is_active=false
```

**Response `200 OK`:**
```json
{
  "total": 24,
  "page":  1,
  "size":  20,
  "items": [
    {
      "id":            "26a7b9b0-e608-448a-a78b-ab8ff3cad05b",
      "short_code":    "UEKCY2Q9",
      "sms_code":      "TARURA-UEKCY2Q9",
      "qr_type":       "PRODUCT",
      "product_id":    "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
      "service_id":    null,
      "branch_id":     null,
      "department_id": null,
      "label":         "Azam Drinking Water 500ml — Verification QR",
      "redirect_url":  "https://app.riviwa.com/verify?product=4ae4ecf5-...",
      "qr_image_url":  "https://minio.riviwa.com/qr-codes/455bd8b1-.../UEKCY2Q9.png",
      "scan_count":    3,
      "is_active":     true,
      "batch_id":      null,
      "created_at":    "2026-05-18T12:32:00.000000",
      "updated_at":    "2026-05-18T12:32:24.189268"
    }
  ]
}
```

---

### 3. `PATCH /qr/{qr_id}`

**Purpose:** Update a QR code after creation. Use to correct the redirect URL, reassign to a different product/service/branch/department, rename the label, or toggle active state. Send only the fields you want to change.

**Auth:** JWT Bearer

**Path Parameter:** `qr_id` — UUID of the QR code.

**Request Body** (all fields optional, send only what changes):

| Field | Type | Description |
|-------|------|-------------|
| `redirect_url` | string | New destination URL for the QR scan |
| `label` | string | New human-readable name |
| `product_id` | UUID \| null | Reassign to a different product. Send `null` to clear. |
| `service_id` | UUID \| null | Reassign to a different service |
| `project_id` | UUID \| null | Reassign to a different project |
| `branch_id` | UUID \| null | Reassign to a different branch |
| `department_id` | UUID \| null | Reassign to a different department |
| `is_active` | bool | `false` to deactivate, `true` to reactivate |

> Unknown fields are silently ignored. `sms_code`, `short_code`, `qr_type`, and `organisation_id` cannot be changed after creation.

**Example — update redirect URL and label:**
```json
PATCH /api/v1/qr/26a7b9b0-e608-448a-a78b-ab8ff3cad05b
{
  "label":        "Azam Drinking Water 500ml — Production Line QR v2",
  "redirect_url": "https://app.riviwa.com/verify?product=4ae4ecf5-...&v=2"
}
```

**Example — add department context to an existing service QR:**
```json
PATCH /api/v1/qr/22c3cc08-6119-4c88-8c59-15ac600059c1
{
  "department_id": "699a2c9c-2cd8-4bda-93de-88c9aed3a861",
  "label":         "YasPesa — YPA Dept Counter"
}
```

**Example — deactivate:**
```json
PATCH /api/v1/qr/26a7b9b0-e608-448a-a78b-ab8ff3cad05b
{
  "is_active": false
}
```

**Response `200 OK`:** Full updated QR object (same shape as `POST /generate` response).

**Errors:**

| Code | `error` | Meaning |
|------|---------|---------|
| `404` | `QR_NOT_FOUND` | No QR code with that ID |

---

### 4. `GET /qr/{qr_id}/scans`

**Purpose:** List individual scan records for a specific QR code. Shows who scanned it, when, from which IP/device, and whether they submitted feedback. Use to audit scan activity or investigate conversion gaps.

**Auth:** JWT Bearer

**Path Parameter:** `qr_id` — UUID of the QR code.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `feedback_submitted` | bool | — | `true` = converted scans only, `false` = unconverted, omit = all |
| `page` | int | `1` | Page number |
| `size` | int | `20` | Page size (max 100) |

**Examples:**

```
GET /api/v1/qr/26a7b9b0-.../scans
GET /api/v1/qr/26a7b9b0-.../scans?feedback_submitted=false
GET /api/v1/qr/26a7b9b0-.../scans?feedback_submitted=true&size=50
```

**Response `200 OK`:**
```json
{
  "qr_id": "26a7b9b0-e608-448a-a78b-ab8ff3cad05b",
  "total": 3,
  "page":  1,
  "size":  20,
  "items": [
    {
      "id":                 "a1b2c3d4-...",
      "scanner_ip":         "172.18.0.39",
      "scanner_ua":         "Mozilla/5.0 (Linux; Android 12) Chrome/124",
      "fingerprint":        "a3f91bc204e8d7f1",
      "feedback_submitted": false,
      "feedback_id":        null,
      "scanned_at":         "2026-05-18T12:32:24.788336"
    }
  ]
}
```

**Errors:**

| Code | `error` | Meaning |
|------|---------|---------|
| `404` | `QR_NOT_FOUND` | No QR code with that ID |

---

### 5. `GET /qr/{qr_id}/analytics`

**Purpose:** Scan analytics breakdown for a single QR code. Returns total scans, unique scanners (by device fingerprint), converted scans (feedback submitted), and the conversion rate as a percentage.

**Auth:** JWT Bearer

**Path Parameter:** `qr_id` — UUID of the QR code.

**No additional query parameters.**

**Response `200 OK`:**
```json
{
  "qr_id":           "26a7b9b0-e608-448a-a78b-ab8ff3cad05b",
  "short_code":      "UEKCY2Q9",
  "total_scans":     5,
  "unique_scanners": 2,
  "converted":       1,
  "conversion_rate": 20.0
}
```

| Field | Description |
|-------|-------------|
| `total_scans` | Total number of times this QR was scanned |
| `unique_scanners` | Distinct devices (by SHA-256 fingerprint of IP+UA) |
| `converted` | Scans where the user went on to submit feedback |
| `conversion_rate` | `converted / total_scans × 100` (%) |

**Errors:**

| Code | `error` | Meaning |
|------|---------|---------|
| `404` | `QR_NOT_FOUND` | No QR code with that ID |

---

### 6. `GET /qr/bulk`

**Purpose:** List all bulk generation batches for an org. Filter by type or status to monitor ongoing jobs. Use to build a dashboard showing batch progress, counts, and ZIP download links.

**Auth:** JWT Bearer

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `organisation_id` | UUID | ✅ required | Scope to this org |
| `qr_type` | string | — | `PRODUCT` \| `SERVICE` \| `LOCATION` |
| `status` | string | — | `PENDING` \| `GENERATING` \| `READY` \| `FAILED` |
| `page` | int | `1` | Page number |
| `size` | int | `20` | Page size (max 100) |

**Examples:**

```
GET /api/v1/qr/bulk?organisation_id=455bd8b1-...
GET /api/v1/qr/bulk?organisation_id=455bd8b1-...&status=READY
GET /api/v1/qr/bulk?organisation_id=455bd8b1-...&qr_type=PRODUCT&status=GENERATING
```

**Response `200 OK`:**
```json
{
  "total": 3,
  "page":  1,
  "size":  20,
  "items": [
    {
      "batch_id":        "088adfb1-3a7f-469d-8c3c-2c2abdd7106c",
      "organisation_id": "455bd8b1-ce74-44c7-a571-e5986dd65d17",
      "product_id":      "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76",
      "qr_type":         "PRODUCT",
      "count":           5,
      "label":           "Azam Water 500ml — Shelf Labels Batch",
      "status":          "READY",
      "generated_count": 5,
      "zip_url":         "https://minio.riviwa.com/qr-batches/088adfb1-....zip?...",
      "error_message":   null,
      "created_at":      "2026-05-18T12:32:10.000000",
      "completed_at":    "2026-05-18T12:32:12.000000"
    }
  ]
}
```

**Batch status lifecycle:**

```
PENDING → GENERATING → READY
                     ↘ FAILED
```

| Status | Meaning |
|--------|---------|
| `PENDING` | Job queued, not yet started |
| `GENERATING` | Background task is generating PNGs and uploading to MinIO |
| `READY` | All QR codes generated. `zip_url` is populated — download the ZIP. |
| `FAILED` | Generation failed. `error_message` contains the reason. |

---

### 7. `GET /qr/receipt-sessions`

**Purpose:** List receipt sessions created by the internal receipt endpoint. Each session represents a transaction for which a QR code was issued to a consumer. Use to track outstanding receipts awaiting feedback (`is_consumed=false`) and completed ones (`is_consumed=true`).

**Auth:** JWT Bearer

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `organisation_id` | UUID | ✅ required | Scope to this org |
| `is_consumed` | bool | — | `true` = feedback submitted, `false` = pending, omit = all |
| `page` | int | `1` | Page number |
| `size` | int | `20` | Page size (max 100) |

**Examples:**

```
GET /api/v1/qr/receipt-sessions?organisation_id=455bd8b1-...
GET /api/v1/qr/receipt-sessions?organisation_id=455bd8b1-...&is_consumed=false
GET /api/v1/qr/receipt-sessions?organisation_id=455bd8b1-...&is_consumed=true&size=50
```

**Response `200 OK`:**
```json
{
  "total": 6,
  "page":  1,
  "size":  20,
  "items": [
    {
      "id":                   "fdac1595-cb12-4b74-b1a7-5406d0cc5bc7",
      "organisation_id":      "455bd8b1-ce74-44c7-a571-e5986dd65d17",
      "consumer_name":        "Fatuma Hassan",
      "consumer_phone":       "+255712345678",
      "service_name":         "YasPesa Mobile Money",
      "department":           "Mobile Banking",
      "attendant_name":       "John Baraka",
      "location":             "Kariakoo Branch, Dar es Salaam",
      "receipt_number":       "RCP-001-2026",
      "amount":               50000.0,
      "currency":             "TZS",
      "transaction_datetime": "2026-05-18T10:30:00",
      "is_consumed":          false,
      "created_at":           "2026-05-18T12:35:00.000000"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `is_consumed` | `false` = QR issued but consumer hasn't submitted feedback yet. `true` = feedback received, receipt closed. |
| `consumer_phone` | Phone used for SMS QR delivery (optional) |
| `department` | Free-text department label from the transaction system |
| `location` | Free-text location string from the receipt issuer |

---

## Existing Endpoints — Updated Fields

The following existing endpoints were updated to support new fields. No breaking changes.

### `POST /qr/generate` — new fields added

`branch_id`, `department_id`, and `label` are now accepted in the request body (all optional). See endpoint 1 above.

### `GET /qr` — new filter parameters added

`product_id`, `service_id`, `project_id`, `branch_id`, `department_id`, `batch_id`, and `is_active` are now accepted as query parameters. See endpoint 2 above.

### QR object — new fields in all responses

All endpoints that return a QR code object now include:

```json
"branch_id":     "1ffae914-0000-0000-0000-000000000000",
"department_id": "699a2c9c-2cd8-4bda-93de-88c9aed3a861",
"label":         "Counter 3 – DSM Branch",
"updated_at":    "2026-05-18T12:32:24.189268"
```

---

## Complete Endpoint Reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/qr/generate` | JWT | Generate a single QR code |
| `GET` | `/qr` | JWT | List QR codes with filters (product, service, branch, dept, type…) |
| `PATCH` | `/qr/{id}` | JWT | Update redirect URL, label, entity links, or active state |
| `DELETE` | `/qr/{id}` | JWT | Deactivate a QR code (soft delete) |
| `GET` | `/qr/{id}` | JWT | Get a single QR code by ID |
| `GET` | `/qr/{id}/scans` | JWT | List individual scan records for a QR code |
| `GET` | `/qr/{id}/analytics` | JWT | Per-QR analytics: scans, unique, converted, rate |
| `GET` | `/qr/analytics/scans` | JWT | Org-wide scan analytics |
| `POST` | `/qr/bulk` | JWT | Queue a bulk QR generation job (1–10,000 codes) |
| `GET` | `/qr/bulk` | JWT | List bulk batches with status and ZIP URL |
| `GET` | `/qr/bulk/{batch_id}` | JWT | Get single batch status |
| `GET` | `/qr/receipt-sessions` | JWT | List receipt sessions (filter by consumed state) |
| `GET` | `/qr/{short_code}` | Public | Scan redirect (records scan, 302 → redirect_url) |
| `POST` | `/internal/qr/receipt` | X-Service-Key | Create receipt QR + session (service-to-service) |
| `GET` | `/internal/qr/lookup` | X-Service-Key | Resolve QR by any code format |
| `POST` | `/internal/qr/mark-feedback` | X-Service-Key | Mark QR as having feedback submitted |
| `GET` | `/internal/qr/receipt-session/{id}` | X-Service-Key | Fetch receipt session by ID |
| `POST` | `/internal/qr/increment-scan` | X-Service-Key | Record a scan event |

---

## Error Reference

| HTTP | `error` | Meaning |
|------|---------|---------|
| `400` | `BAD_REQUEST` | Malformed UUID or invalid field value |
| `401` | — | Missing or invalid JWT |
| `403` | `FORBIDDEN` | Valid JWT but insufficient permission |
| `404` | `QR_NOT_FOUND` | No QR code matching the given ID |
| `404` | `BATCH_NOT_FOUND` | No batch matching the given batch_id |
| `422` | — | Validation error (e.g. `count` out of 1–10000 range) |
