# Riviwa Auth Service — Organisation Verification & KYC API Reference
**Date:** 2026-05-19  
**Service:** riviwa_auth_service — Port **8000**  
**Base path:** `/api/v1`

This document covers the two-track organisation verification system:

| Track | Trigger | Badge | What it means |
|-------|---------|-------|---------------|
| **Payment Verification** | Automatic — subscription_service calls an internal endpoint the moment a payment is confirmed | `"Active Subscriber"` / green | Org has a paid, active subscription |
| **KYC Verification** | Manual — org submits documents, platform admin reviews and approves | `"Verified Business"` / blue | Org identity has been independently vetted |

Both tracks are **independent** — an org can be payment-verified without KYC documents, or KYC-verified on a free plan. The public badge reflects the highest verified level.

---

## Verification levels

| `verification_level` | Conditions | Frontend badge |
|----------------------|-----------|----------------|
| `unverified` | Neither flag set | No badge |
| `payment_verified` | `is_payment_verified = true` | Green — "Active Subscriber" |
| `kyc_verified` | `is_kyc_verified = true` (independent of payment) | Blue — "Verified Business" |

---

## Authentication

| Auth type | Header | Used by |
|-----------|--------|---------|
| JWT Bearer | `Authorization: Bearer <token>` | Org-facing and public endpoints |
| Service Key | `X-Service-Key: <key>` | Internal endpoints (service-to-service only) |
| Admin JWT | `Authorization: Bearer <token>` with `org_role` = OWNER/ADMIN or `platform_role` = super_admin/admin | All `/admin/` endpoints |

---

## New database tables

### `org_kyc_submissions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `org_id` | UUID | Organisation |
| `submitted_by_id` | UUID | User who created the submission |
| `status` | string | `pending` \| `under_review` \| `approved` \| `rejected` \| `more_info` |
| `business_type` | string | Org type declared at submission time |
| `reg_number` | string | Business registration number |
| `tax_id` | string | TIN/VAT number |
| `notes_for_admin` | text | Context message from the org |
| `admin_notes` | text | Internal admin notes (not shown to org) |
| `rejection_reason` | string | Rejection message or more-info request text |
| `reviewed_by_id` | UUID | Admin who reviewed |
| `submitted_at` | datetime | When submission was created |
| `reviewed_at` | datetime | When admin made a decision |

### `org_kyc_documents`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `org_id` | UUID | Organisation |
| `submission_id` | UUID | FK → `org_kyc_submissions.id` (CASCADE delete) |
| `document_type` | string | See document type catalog below |
| `file_url` | string | MinIO public URL |
| `file_name` | string | Original filename |
| `file_size_bytes` | integer | Size in bytes |
| `uploaded_by_id` | UUID | User who uploaded |
| `is_verified` | boolean | Set by admin per-document (for fine-grained review) |
| `uploaded_at` | datetime | Upload timestamp |

### New columns on `organisations`

| Column | Type | Description |
|--------|------|-------------|
| `is_payment_verified` | boolean | Auto-set by subscription_service on payment |
| `payment_verified_at` | datetime | When payment verification was first set |
| `is_kyc_verified` | boolean | Set by admin after KYC approval |
| `kyc_verified_at` | datetime | When KYC was approved |
| `kyc_verified_by_id` | UUID | Admin who approved |
| `kyc_rejection_reason` | string | Most recent rejection reason (if applicable) |

---

## Document type catalog

| `document_type` | Description | Common formats |
|----------------|-------------|---------------|
| `business_license` | Government-issued business registration / operating licence | PDF |
| `certificate_of_incorporation` | BRELA certificate of incorporation or equivalent | PDF |
| `tax_clearance` | TRA tax clearance certificate | PDF |
| `tax_id` | TIN certificate | PDF |
| `directors_national_id` | Director/trustee NIDA national ID scan | PDF, JPEG, PNG |
| `utility_bill` | Electricity/water/internet bill confirming physical address | PDF, JPEG, PNG |
| `bank_statement` | Bank statement covering recent activity | PDF |
| `memorandum_of_association` | Memorandum and Articles of Association | PDF, DOCX |
| `audited_accounts` | Last financial year's audited accounts | PDF |
| `other` | Any other supporting document | PDF, JPEG, PNG, DOCX |

---

## Accepted file types for upload

| MIME type | Extension | Max size |
|-----------|-----------|---------|
| `application/pdf` | `.pdf` | 15 MB |
| `image/jpeg` | `.jpg` | 15 MB |
| `image/png` | `.png` | 15 MB |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` | 15 MB |
| `application/msword` | `.doc` | 15 MB |
| `image/tiff` | `.tiff` | 15 MB |

All other MIME types return `HTTP 422 UPLOAD_ERROR`.

---

---

# Part 1 — Org-Facing Endpoints

---

## `GET /orgs/my/verification`

**Auth:** Bearer token  
**Summary:** Returns both verification tracks for the authenticated organisation, plus the latest KYC submission status.

```
GET /api/v1/orgs/my/verification
```

### Response

```json
{
  "org_id":              "16449750-e456-4c7f-ab76-0d59b526d7b5",
  "slug":                "muhimbili-national-hospital",
  "display_name":        "Muhimbili National Hospital",
  "is_payment_verified": true,
  "payment_verified_at": "2026-05-18T20:30:00",
  "is_kyc_verified":     true,
  "kyc_verified_at":     "2026-05-18T21:15:00",
  "kyc_rejection_reason": null,
  "verification_level":  "kyc_verified",
  "kyc_submission": {
    "id":              "46cb5583-9752-4b21-86c5-e644b30665a0",
    "org_id":          "16449750-e456-4c7f-ab76-0d59b526d7b5",
    "status":          "approved",
    "business_type":   "GOVERNMENT",
    "reg_number":      "MNH/MOH/TZ/REG/1956/001",
    "tax_id":          "TIN-100-234-567",
    "notes_for_admin": "Muhimbili National Hospital — Tanzania's national referral hospital...",
    "rejection_reason": null,
    "submitted_at":    "2026-05-18T20:18:00",
    "reviewed_at":     "2026-05-18T21:15:00",
    "updated_at":      "2026-05-18T21:15:00"
  }
}
```

---

## `GET /orgs/my/kyc`

**Auth:** Bearer token  
**Summary:** Lists all KYC submissions for the authenticated organisation (up to the 5 most recent), each with their documents.

```
GET /api/v1/orgs/my/kyc
```

### Response

```json
{
  "org_id":          "16449750-...",
  "is_kyc_verified": true,
  "kyc_verified_at": "2026-05-18T21:15:00",
  "submissions": [
    {
      "id":              "46cb5583-...",
      "status":          "approved",
      "business_type":   "GOVERNMENT",
      "reg_number":      "MNH/MOH/TZ/REG/1956/001",
      "rejection_reason": null,
      "submitted_at":    "2026-05-18T20:18:00",
      "reviewed_at":     "2026-05-18T21:15:00",
      "documents": [
        {
          "id":              "doc-uuid",
          "document_type":   "business_license",
          "file_url":        "http://minio:9000/riviwa-kyc/kyc/16449750-.../business_license_8bba0dc7.pdf",
          "file_name":       "mnh_establishment_cert.pdf",
          "file_size_bytes": 437,
          "is_verified":     true,
          "uploaded_at":     "2026-05-18T20:19:00"
        }
      ]
    }
  ]
}
```

---

## `POST /orgs/my/kyc/submit`

**Auth:** Bearer token  
**Status:** `201 Created`  
**Summary:** Create a KYC submission and optionally attach document URLs in the same request.

Use this endpoint to start the KYC process. Documents can be attached as URL references in the body (if already uploaded elsewhere) or uploaded separately via `POST /orgs/my/kyc/documents/upload`.

If a `pending` or `more_info` submission already exists it is re-opened rather than creating a duplicate. An `under_review` submission blocks re-submission with `HTTP 409`.

### Request body

```json
{
  "business_type":   "GOVERNMENT",
  "reg_number":      "MNH/MOH/TZ/REG/1956/001",
  "tax_id":          "TIN-100-234-567",
  "notes_for_admin": "Muhimbili National Hospital — state hospital under MoHSW. World Bank GRM tender deadline 30 May 2026.",
  "documents": [
    {
      "document_type": "business_license",
      "file_url":      "https://minio.riviwa.com/reviwa-kyc/uuid/establishment_cert.pdf",
      "file_name":     "establishment_cert.pdf",
      "file_size_bytes": 312450
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `business_type` | string | No | Org type for context (`BUSINESS`, `GOVERNMENT`, `NGO`, etc.) |
| `reg_number` | string | No | Business/charity/government registration number |
| `tax_id` | string | No | TIN or VAT number |
| `notes_for_admin` | string | No | Any context the admin should know (urgency, special circumstances) |
| `documents` | array | No | Pre-existing document URL references. Can also be empty and uploaded separately. |

### Response

```json
{
  "message": "KYC submission received. Our team will review within 2–3 business days.",
  "submission": {
    "id":            "46cb5583-...",
    "status":        "pending",
    "submitted_at":  "2026-05-18T20:18:00",
    "documents": []
  }
}
```

### Errors

| HTTP | `error` | When |
|------|---------|------|
| `409` | `SUBMISSION_UNDER_REVIEW` | A submission is already being reviewed — cannot create another |

---

## `POST /orgs/my/kyc/documents/upload`

**Auth:** Bearer token  
**Content-Type:** `multipart/form-data`  
**Status:** `201 Created`  
**Summary:** Upload a document file directly to MinIO and attach it to the current pending submission.

This is the **primary upload endpoint** for the frontend file picker. Accepts real files from the browser. A `pending` or `more_info` KYC submission must exist before calling this endpoint.

### Form fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | **Yes** | The document file — PDF, JPEG, PNG, DOCX, DOC, or TIFF. Max 15 MB. |
| `document_type` | string | **Yes** | See document type catalog above |

### Request example (cURL)

```bash
curl -X POST https://api.riviwa.com/api/v1/orgs/my/kyc/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/establishment_cert.pdf;type=application/pdf" \
  -F "document_type=business_license"
```

### Request example (JavaScript / fetch)

```javascript
const form = new FormData();
form.append("file", fileInput.files[0]);
form.append("document_type", "business_license");

const response = await fetch("/api/v1/orgs/my/kyc/documents/upload", {
  method: "POST",
  headers: { "Authorization": `Bearer ${token}` },
  body: form,
});
```

### MinIO storage path

Files are stored at:
```
reviwa-kyc / kyc / {org_id} / {submission_id} / {document_type}_{short_uuid}.{ext}
```

Example:
```
reviwa-kyc/kyc/16449750-e456-4c7f-ab76-0d59b526d7b5/
            46cb5583-9752-4b21-86c5-e644b30665a0/
            business_license_8bba0dc7.pdf
```

### Response

```json
{
  "message":  "Document 'mnh_establishment_cert.pdf' uploaded successfully.",
  "document": {
    "id":              "doc-uuid",
    "document_type":   "business_license",
    "file_url":        "http://minio:9000/riviwa-kyc/kyc/16449750-.../business_license_8bba0dc7.pdf",
    "file_name":       "mnh_establishment_cert.pdf",
    "file_size_bytes": 312450,
    "is_verified":     false,
    "uploaded_at":     "2026-05-18T20:19:00"
  },
  "submission_status": "pending"
}
```

Note: when a document is uploaded to a `more_info` submission, `submission_status` returns `"pending"` — the upload automatically moves the submission back to pending for admin review.

### Errors

| HTTP | `error` | When |
|------|---------|------|
| `404` | `NO_ACTIVE_SUBMISSION` | No pending/more_info submission exists yet. Call `POST /orgs/my/kyc/submit` first. |
| `422` | `UPLOAD_ERROR` | Unsupported MIME type, file exceeds 15 MB, or empty file |

---

## `POST /orgs/my/kyc/documents`

**Auth:** Bearer token  
**Status:** `201 Created`  
**Summary:** Attach a document by URL reference to the current pending submission (no file upload — URL must already point to a MinIO object).

Use this when the file has already been uploaded to MinIO via another flow (e.g., the org's own file manager). For direct browser uploads use `POST /orgs/my/kyc/documents/upload` instead.

### Request body

```json
{
  "document_type":   "utility_bill",
  "file_url":        "https://minio.riviwa.com/reviwa-kyc/uuid/tanesco_bill.pdf",
  "file_name":       "tanesco_bill_apr2026.pdf",
  "file_size_bytes": 102400
}
```

### Response

```json
{
  "message": "Document added.",
  "document": {
    "id":            "doc-uuid",
    "document_type": "utility_bill",
    "file_url":      "https://minio.riviwa.com/reviwa-kyc/uuid/tanesco_bill.pdf",
    "file_name":     "tanesco_bill_apr2026.pdf",
    "is_verified":   false,
    "uploaded_at":   "2026-05-18T20:25:00"
  }
}
```

---

## `DELETE /orgs/my/kyc/documents/{doc_id}`

**Auth:** Bearer token  
**Summary:** Remove a document from a pending or more_info submission. The file is also deleted from MinIO.

```
DELETE /api/v1/orgs/my/kyc/documents/{doc_id}
```

**Blocked if** the submission is `under_review` or `approved` — returns `HTTP 409`.

### Response

```json
{
  "message": "Document 'mnh_nbs_statement_q1_2026.pdf' removed.",
  "id":      "doc-uuid"
}
```

### Replace workflow (delete + re-upload)

```
1. GET /orgs/my/kyc                          → find document ID to replace
2. DELETE /orgs/my/kyc/documents/{old_id}    → removes old file from MinIO and DB
3. POST /orgs/my/kyc/documents/upload         → upload corrected version
```

### Errors

| HTTP | `error` | When |
|------|---------|------|
| `404` | `NOT_FOUND` | Document not found or belongs to a different org |
| `409` | `SUBMISSION_NOT_EDITABLE` | Submission is `under_review` or `approved` |

---

---

# Part 2 — Public Endpoint

---

## `GET /orgs/{slug}/badge`

**Auth:** None (public)  
**Summary:** Returns verification badge data for an organisation's public profile. Used by the frontend on product listings, org pages, search results, and QR scan results.

Returns **only non-sensitive data** — no document URLs, no KYC details, no internal notes.

```
GET /api/v1/orgs/muhimbili-national-hospital/badge
```

### Response

```json
{
  "org_id":              "16449750-e456-4c7f-ab76-0d59b526d7b5",
  "slug":                "muhimbili-national-hospital",
  "display_name":        "Muhimbili National Hospital",
  "logo_url":            "https://minio.riviwa.com/riviwa-images/organisations/16449750.../logo.jpg",
  "is_payment_verified": true,
  "is_kyc_verified":     true,
  "kyc_verified_at":     "2026-05-18T21:15:00",
  "verification_level":  "kyc_verified",
  "badge": {
    "show_payment_badge": true,
    "show_kyc_badge":     true,
    "label":  "Verified Business",
    "color":  "blue"
  }
}
```

### Badge states by level

| Org state | `label` | `color` | `show_kyc_badge` | `show_payment_badge` |
|-----------|---------|---------|-----------------|---------------------|
| Neither verified | `null` | `null` | `false` | `false` |
| Payment only | `"Active Subscriber"` | `"green"` | `false` | `true` |
| KYC verified (any payment state) | `"Verified Business"` | `"blue"` | `true` | `true` (if paid) |

### Frontend rendering

```jsx
{badge.show_kyc_badge && (
  <VerifiedBadge color="blue" label="Verified Business" />
)}
{!badge.show_kyc_badge && badge.show_payment_badge && (
  <VerifiedBadge color="green" label="Active Subscriber" />
)}
```

---

---

# Part 3 — Internal Endpoints (Service-to-Service)

These endpoints require the `X-Service-Key` header, not a JWT. They are called by subscription_service automatically — the org owner never calls them directly.

---

## `POST /internal/orgs/{org_id}/set-payment-verified`

**Auth:** `X-Service-Key`  
**Summary:** Mark an organisation as payment-verified. Called by subscription_service every time a subscription payment is confirmed.

This endpoint is **idempotent** — safe to call multiple times. If the org is already payment-verified it simply returns the current state without modifying `payment_verified_at`.

It also auto-activates the org status from `PENDING_VERIFICATION` to `ACTIVE` if the subscription payment is the first confirmed transaction.

```
POST /api/v1/internal/orgs/16449750-e456-4c7f-ab76-0d59b526d7b5/set-payment-verified
X-Service-Key: <key>
```

No request body required.

### Response

```json
{
  "ok":                  true,
  "org_id":              "16449750-e456-4c7f-ab76-0d59b526d7b5",
  "is_payment_verified": true,
  "payment_verified_at": "2026-05-18T20:30:00"
}
```

### Where it is called from (subscription_service)

```python
# subscription_service/api/v1/checkout.py

# 1. After payment poll confirms paid:
if paid and inv.status != InvoiceStatus.PAID.value:
    ...
    notify_payment_verified(org_id)   # fire-and-forget

# 2. After Kafka payment.completed event:
if sub:
    sub.status = SubscriptionStatus.ACTIVE.value
    notify_payment_verified(str(sub.org_id))
```

```python
# subscription_service/services/auth_client.py

def notify_payment_verified(org_id: str) -> None:
    """Fire-and-forget — never blocks the checkout path."""
    asyncio.ensure_future(_set_payment_verified(org_id))
```

---

---

# Part 4 — Admin Endpoints

---

## `GET /admin/kyc/pending`

**Auth:** Admin Bearer token  
**Summary:** Returns the KYC review queue. By default shows all actionable submissions (pending + under_review + more_info), sorted oldest first to encourage processing in order.

### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | _(all actionable)_ | Filter: `pending`, `under_review`, `more_info`, `approved`, `rejected` |
| `page` | integer | `1` | Page number |
| `size` | integer | `20` | Items per page (max 100) |

### Response

```json
{
  "total": 3,
  "page":  1,
  "size":  20,
  "submissions": [
    {
      "id":           "46cb5583-...",
      "status":       "pending",
      "business_type": "GOVERNMENT",
      "reg_number":   "MNH/MOH/TZ/REG/1956/001",
      "submitted_at": "2026-05-18T20:18:00",
      "document_count": 9,
      "org": {
        "display_name": "Muhimbili National Hospital",
        "slug":         "muhimbili-national-hospital",
        "org_type":     "GOVERNMENT",
        "country_code": "TZ"
      }
    }
  ]
}
```

---

## `GET /admin/kyc/{submission_id}`

**Auth:** Admin Bearer token  
**Summary:** Open a KYC submission for review. Returns the full submission with all documents and the org's current verification state.

**Side effect:** if the submission is `pending`, opening it automatically moves it to `under_review`.

```
GET /api/v1/admin/kyc/46cb5583-9752-4b21-86c5-e644b30665a0
```

### Response

```json
{
  "id":              "46cb5583-...",
  "org_id":          "16449750-...",
  "status":          "under_review",
  "business_type":   "GOVERNMENT",
  "reg_number":      "MNH/MOH/TZ/REG/1956/001",
  "tax_id":          "TIN-100-234-567",
  "notes_for_admin": "Muhimbili National Hospital — Tanzania's national referral hospital...",
  "rejection_reason": null,
  "submitted_at":    "2026-05-18T20:18:00",
  "reviewed_at":     null,
  "documents": [
    {
      "id":              "doc-uuid",
      "document_type":   "business_license",
      "file_url":        "http://minio:9000/riviwa-kyc/kyc/.../business_license_8bba0dc7.pdf",
      "file_name":       "mnh_establishment_cert.pdf",
      "file_size_bytes": 437,
      "is_verified":     false,
      "uploaded_at":     "2026-05-18T20:19:00"
    },
    {
      "id":              "doc-uuid-2",
      "document_type":   "tax_clearance",
      "file_url":        "http://minio:9000/riviwa-kyc/kyc/.../tax_clearance_82d31545.pdf",
      "file_name":       "mnh_tra_clearance_2026.pdf",
      "file_size_bytes": 437,
      "is_verified":     false,
      "uploaded_at":     "2026-05-18T20:19:10"
    }
  ],
  "org": {
    "id":               "16449750-...",
    "display_name":     "Muhimbili National Hospital",
    "legal_name":       "Muhimbili National Hospital",
    "slug":             "muhimbili-national-hospital",
    "org_type":         "GOVERNMENT",
    "country_code":     "TZ",
    "registration_number": "MNH/MOH/TZ/REG/1956/001",
    "tax_id":           "TIN-100-234-567",
    "support_email":    "ict@mnh.or.tz",
    "is_payment_verified": true,
    "is_kyc_verified":  false
  }
}
```

---

## `POST /admin/kyc/{submission_id}/review`

**Auth:** Admin Bearer token  
**Summary:** Make a decision on a KYC submission: approve, reject, or request more information.

### Request body

```json
{
  "action":            "approve" | "reject" | "more_info",
  "rejection_reason":  "...",
  "admin_notes":       "...",
  "more_info_request": "..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | **Yes** | `approve`, `reject`, or `more_info` |
| `rejection_reason` | string | **Required for `reject`** | Shown to the org. Be specific about what is missing. |
| `more_info_request` | string | **Required for `more_info`** | Specific document(s) or clarification requested |
| `admin_notes` | string | No | Internal note — never shown to the org |

---

### `action: approve`

Sets `org.is_kyc_verified = true`, `org.is_verified = true`, and records `kyc_verified_at` + `kyc_verified_by_id`.

```json
{
  "action":       "approve",
  "admin_notes":  "All 4 documents verified. MNH reg cert, TRA clearance, NIDA director ID, TANESCO bill all valid. Approved."
}
```

**Response:**
```json
{
  "message":          "KYC approved. Organisation 'Muhimbili National Hospital' is now KYC-verified.",
  "submission":       { "status": "approved", ... },
  "org_verification": {
    "is_payment_verified": true,
    "is_kyc_verified":     true,
    "verification_level":  "kyc_verified"
  }
}
```

---

### `action: reject`

Sets submission status to `rejected`. Records `rejection_reason` on both the submission and the org row.

```json
{
  "action": "reject",
  "rejection_reason": "NGO registration and director ID received. Missing required documents for NGO KYC: (1) BRELA Certificate of Registration, (2) Audited financial accounts 2024/2025, (3) TIN certificate from TRA. Re-submit with all three.",
  "admin_notes": "Legitimate NGO — docs just incomplete. Emailed contact to re-submit."
}
```

**Response:**
```json
{
  "message":    "KYC rejected. Organisation notified.",
  "submission": { "status": "rejected", "rejection_reason": "..." }
}
```

---

### `action: more_info`

Sets submission status to `more_info`. Records the request text as `rejection_reason` (shown to org). Org can then upload additional documents and the submission reverts to `pending`.

```json
{
  "action": "more_info",
  "more_info_request": "The bank statement provided covers only up to December 2025. Please provide an NBS or CRDB statement covering at least January–March 2026. Also: the utility bill date is unclear — please re-upload a legible scan.",
  "admin_notes": "Financial docs look credible. Fast-track on resolution."
}
```

**Response:**
```json
{
  "message":    "More information requested. Organisation can re-submit.",
  "submission": { "status": "more_info" },
  "request":    "The bank statement provided covers only..."
}
```

### State transitions

```
pending  ──(admin opens)──>  under_review
                               │
              ┌────────────────┼───────────────────┐
              ↓                ↓                   ↓
           approve           reject            more_info
              │                │                   │
              ↓                ↓                   ↓
           approved         rejected           more_info
                                                   │
                                        (org uploads doc)
                                                   ↓
                                                pending
```

### Errors

| HTTP | `error` | When |
|------|---------|------|
| `404` | `NOT_FOUND` | Submission not found |
| `409` | `ALREADY_APPROVED` | Submission already approved — cannot change |
| `422` | `VALIDATION_ERROR` | Invalid action, or missing `rejection_reason` / `more_info_request` |

---

## `PATCH /admin/orgs/{org_id}/payment-verification`

**Auth:** Admin Bearer token  
**Summary:** Manually set or revoke payment verification for an organisation. Used for bank transfer confirmations or corrections.

```
PATCH /api/v1/admin/orgs/16449750-e456-4c7f-ab76-0d59b526d7b5/payment-verification
```

### Request body

```json
{ "is_payment_verified": true }
```

### Response

```json
{
  "message":          "Payment verification set to True.",
  "org_verification": {
    "is_payment_verified": true,
    "payment_verified_at": "2026-05-18T20:30:00",
    "is_kyc_verified":     false,
    "verification_level":  "payment_verified"
  }
}
```

---

---

# Part 5 — End-to-End Flows

## Flow A — Automatic payment verification (most orgs)

```
1. Org subscribes via POST /api/v1/checkout (subscription_service)
2. Org pays via M-Pesa / PayPal / bank transfer
3. subscription_service confirms payment → calls:
     POST /api/v1/internal/orgs/{org_id}/set-payment-verified
4. org.is_payment_verified = true automatically
5. GET /orgs/{slug}/badge → badge.label = "Active Subscriber" / green
```

No org action required. No admin action required.

---

## Flow B — Full KYC verification (manual vetting)

```
Org side:
  1. POST /orgs/my/kyc/submit           → create submission, provide reg number + tax ID
  2. POST /orgs/my/kyc/documents/upload → upload business_license (PDF)
  3. POST /orgs/my/kyc/documents/upload → upload tax_clearance (PDF)
  4. POST /orgs/my/kyc/documents/upload → upload directors_national_id (JPEG)
  5. POST /orgs/my/kyc/documents/upload → upload utility_bill (PNG)
  6. GET  /orgs/my/kyc                  → check status

Admin side:
  7. GET  /admin/kyc/pending            → see submission in queue
  8. GET  /admin/kyc/{submission_id}    → open it (status → under_review), review docs
  9. POST /admin/kyc/{sub_id}/review    → action: more_info (request utility bill re-scan)

Org side:
  10. POST /orgs/my/kyc/documents/upload → upload clear utility bill scan
      (submission automatically reverts to pending)

Admin side:
  11. GET  /admin/kyc/{submission_id}   → re-open (status → under_review)
  12. POST /admin/kyc/{sub_id}/review   → action: approve
      (org.is_kyc_verified = true)

Result:
  13. GET  /orgs/{slug}/badge           → badge.label = "Verified Business" / blue
```

---

## Flow C — Replace a document

```
1. GET  /orgs/my/kyc              → find document ID to replace
2. DELETE /orgs/my/kyc/documents/{old_id}  → removes file from MinIO and DB record
3. POST /orgs/my/kyc/documents/upload       → upload corrected version
```

Only possible when submission is `pending` or `more_info`. Blocked with `HTTP 409` if `under_review` or `approved`.

---

# Part 6 — Live Test Results

Tests run 2026-05-19 against production server (77.237.241.13).

```
─ 1. Payment verification ──────────────────────────────────────────
  [PASS] Pre-payment badge  ->  payment=False kyc=True label=Verified Business
  [PASS] set-payment-verified  ->  verified_at=2026-05-18
  [PASS] Idempotent: calling set-payment-verified twice is safe
  [PASS] Badge after payment  ->  label=Verified Business color=blue

─ 2. Muhimbili Hospital KYC — 5 documents ──────────────────────────
  [PASS] KYC submission created  sub_id=46cb5583
  [PASS] Uploaded business_license    mnh_establishment_cert.pdf      (437 bytes)
  [PASS] Uploaded tax_clearance       mnh_tra_clearance_2026.pdf      (437 bytes)
  [PASS] Uploaded directors_national_id  dr_kaisi_mwanri_nida.jpg    (1868 bytes)
  [PASS] Uploaded memorandum_of_association  mnh_moa_hospitals_act.pdf (442 bytes)
  [PASS] Uploaded bank_statement      mnh_nbs_statement_q1_2026.pdf   (434 bytes)

─ 3. File validation ───────────────────────────────────────────────
  [PASS] Reject video/mp4
  [PASS] Reject application/zip
  [PASS] Reject empty file
  [PASS] Accept PNG utility bill   tanesco_bill_apr2026.png
  [PASS] Accept DOCX memorandum    mnh_charter.docx

─ 4. Document list ─────────────────────────────────────────────────
  [PASS] Documents on submission: 9

─ 5. Replace document ──────────────────────────────────────────────
  [PASS] Deleted old bank statement
  [PASS] Uploaded corrected bank statement  mnh_nbs_statement_q1_2026_v2.pdf

─ 6. State machine enforcement ─────────────────────────────────────
  [PASS] Admin opened submission  status=under_review  docs=9
  [PASS] Cannot delete doc while under_review (409 correct)
  [PASS] Cannot re-submit while under_review (409 correct)

─ 7. Admin requests more info ──────────────────────────────────────
  [PASS] More info requested  status=more_info  request_len=271 chars

─ 8. Org responds with updated documents ───────────────────────────
  [PASS] Org uploaded bank_statement  mnh_crdb_statement_jan_mar_2026.pdf  status_now=pending
  [PASS] Org uploaded utility_bill    tanesco_invoice_mar2026_clear.jpg     status_now=pending

─ 9. Admin approves ────────────────────────────────────────────────
  [PASS] KYC APPROVED  kyc_verified=True payment_verified=True level=kyc_verified

─ 10. Public badge ─────────────────────────────────────────────────
  [PASS] Public badge  payment=True kyc=True label=Verified Business color=blue
  [PASS] Badge: 'Verified Business' / blue

─ 11. NGO reject scenario ──────────────────────────────────────────
  [PASS] NGO submission created  sub_id=adb23d55
  [PASS] NGO rejected correctly  status=rejected  reason_len=322 chars

─ 12. Admin KYC queue ──────────────────────────────────────────────
  [PASS] Queue [actionable]  total=0
  [PASS] Queue [approved]    total=2
  [PASS] Queue [rejected]    total=2

─ 13. Complete status ──────────────────────────────────────────────
  [PASS] my/verification  payment=True kyc=True level=kyc_verified
  [PASS] Latest KYC submission  status=rejected

═══════════════════════════════════════════════
  Passed: 35   Failed: 0 — ALL PASS
═══════════════════════════════════════════════
```

---

# Part 7 — Error Reference

| HTTP | `error` | Endpoint | Cause |
|------|---------|----------|-------|
| `400` | `NO_ORG` | All org-facing | JWT has no `org_id` claim — not in org context |
| `401` | `UNAUTHORISED` | All | Missing or invalid Bearer token |
| `401` | `INVALID_SERVICE_KEY` | `/internal/...` | Wrong or missing `X-Service-Key` |
| `403` | `FORBIDDEN` | All `/admin/...` | Token present but `org_role` / `platform_role` insufficient |
| `404` | `NOT_FOUND` | Any | Org, submission, or document not found or belongs to different org |
| `404` | `NO_ACTIVE_SUBMISSION` | `POST /kyc/documents/upload` | No `pending` or `more_info` submission exists |
| `409` | `SUBMISSION_UNDER_REVIEW` | `POST /kyc/submit` | Cannot re-submit while admin is reviewing |
| `409` | `SUBMISSION_NOT_EDITABLE` | `DELETE /kyc/documents/{id}` | Submission is `under_review` or `approved` |
| `409` | `ALREADY_APPROVED` | `POST /admin/kyc/{id}/review` | Submission already approved |
| `422` | `UPLOAD_ERROR` | `POST /kyc/documents/upload` | Invalid MIME type, file > 15 MB, empty file |
| `422` | `VALIDATION_ERROR` | `POST /admin/kyc/{id}/review` | Missing required field for the chosen action |
