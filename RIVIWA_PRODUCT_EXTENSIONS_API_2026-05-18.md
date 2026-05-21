# Riviwa Product Service — Extensions API Reference
**Date:** 2026-05-18  
**Service:** product_service — Port **8110**  
**Base path:** `/api/v1/products`

This document covers three new capabilities added to the product service:
1. **`made_in` and `how_to_use` fields** on every product and service listing
2. **Org Custom Field Definitions** — organisation-defined attribute templates
3. **Product Documents** — manuals, guides, datasheets, safety sheets (PDF, Markdown, DOCX)

---

## Authentication

```
Authorization: Bearer <access_token>
```

| Role | Access |
|------|--------|
| **Staff** (`org_role` = viewer/staff) | Read endpoints (GET) |
| **Manager** (`org_role` = manager/admin/owner) | Full CRUD |
| **Platform Admin** | All orgs |

---

---

# Part 1 — New Fields on Products

Two new fields are available on every product and service listing. They are included in all create, update, and response payloads.

---

## `made_in`

**Type:** `string` (max 150 chars) · **Optional**

Display label shown on the product listing page to communicate the product's origin to buyers and compliance officers. More human-readable than `country_of_origin` (which stores the ISO code).

| Field | Example |
|-------|---------|
| `country_of_origin` | `"TZ"` (ISO 2-letter code) |
| `made_in` | `"Made in Tanzania — Milling plant, Dar es Salaam"` |

**Usage in `POST /products/` and `PATCH /products/{id}`:**
```json
{
  "country_of_origin": "TZ",
  "made_in": "Made in Tanzania — Karibu Food Industries, Dar es Salaam"
}
```

**Other examples:**
```
"Made in Tanzania"
"Assembled in Kenya — Components sourced from Germany"
"Manufactured in Tanzania by Zenufa Laboratories, Dar es Salaam"
"Designed by MikroTik, Latvia — Assembled in Latvia"
"Service provided by TechCare IT Services Ltd, Tanzania"
```

---

## `how_to_use`

**Type:** `text` (no length limit) · **Optional** · **Supports Markdown**

Step-by-step instructions on how to use, install, operate, or access the product or service. Distinct from `usage` (which describes the intended application context) — `how_to_use` is the actionable guide a user reads when they receive the product.

Rendered as a collapsible section on the product detail page. Markdown is parsed and displayed — headings, numbered lists, tables, code blocks, and warnings all render correctly.

**Example for a physical product (Flour):**
```json
{
  "how_to_use": "## Ugali (Stiff Porridge)\n1. Boil 2 cups of water\n2. Add 1.5 cups flour while stirring\n3. Reduce heat, cover for 3 minutes\n4. Stir until ugali pulls from the pot\n\n**Storage:** Keep in a cool dry place."
}
```

**Example for a networking device (Router):**
```json
{
  "how_to_use": "## Initial Setup\n\n### Step 1: Connect\nPlug your ISP modem into Port 1 (WAN).\nConnect your PC to Port 2.\n\n### Step 2: Access Web UI\nOpen browser → **http://192.168.88.1**\nDefault login: `admin` / *(empty password)*\n\n### Step 3: Change Password\nGo to **System → Password** and set a strong password immediately.\n\n### Factory Reset\nHold Reset button 5 seconds while powered on."
}
```

**Example for a service listing:**
```json
{
  "how_to_use": "# Onboarding Service — What to Expect\n\n## Phase 1: Discovery (Day 1–3)\n- Kick-off call with your team\n- Requirements gathering\n\n## Phase 2: Configuration (Day 4–10)\n- Project setup, channels, escalation paths\n\n## Phase 3: Training (Day 11–14)\n- Admin, staff, and field agent training sessions"
}
```

---

## Updated `ProductResponse` — new fields

Both fields appear in the full product response alongside all existing fields:

```json
{
  "product_id": "82387849-...",
  "title":      "Karibu Fortified Maize Flour 2kg",
  "brand":      "Karibu",

  "country_of_origin": "TZ",
  "made_in":           "Made in Tanzania — Milling plant, Dar es Salaam",

  "usage":       "Suitable for preparing ugali, uji, and baked goods.",
  "how_to_use":  "## Ugali\n1. Boil 2 cups water\n2. Add flour ...",

  "bullet_points": [...],
  "images":        [...],
  "attributes":    [...]
}
```

---

---

# Part 2 — Org Custom Field Definitions

Each organisation can define its own custom attribute fields that appear on all product edit forms within that org. These are templates — once defined, they apply to every product created by the org (optionally scoped to specific product types).

**Use cases by industry:**

| Industry | Example fields |
|----------|---------------|
| Food / FMCG | Batch Number (required), Expiry Date (required), Halal Certified, Net Weight |
| Pharmaceutical | TFDA Registration No., Controlled Substance Level, NDC Code |
| Manufacturing | Warranty Terms, Compliance Standard, Production Line |
| NGO / Government | Donor Reference, Project Code, Grant Number |
| Agriculture | Season Grown, Pesticide-Free, Organic Certification |
| Automotive | Chassis Number, Engine Displacement, Emission Standard |

---

## `GET /api/v1/products/org-custom-fields`

**List this organisation's custom field definitions.**

**Auth:** Staff+

**Query params:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `active_only` | bool | `true` | `false` returns deactivated fields too |

**Response `200`:**
```json
[
  {
    "id":          "a1b2c3d4-...",
    "org_id":      "455bd8b1-...",
    "field_name":  "batch_number",
    "field_label": "Batch / Lot Number",
    "field_type":  "text",
    "options":     null,
    "placeholder": "e.g. BT-2026-0512-A",
    "help_text":   "Production batch number printed on the packaging. Required by TFDA.",
    "is_required": true,
    "max_length":  null,
    "applies_to_product_types": [
      "FOOD_AND_BEVERAGE", "GROCERY", "ORGANIC_PRODUCT",
      "FROZEN_FOOD", "MEDICATION", "SUPPLEMENT"
    ],
    "group":       "Regulatory Compliance",
    "position":    1,
    "unit":        null,
    "is_active":   true,
    "created_at":  "2026-05-18T...",
    "updated_at":  "2026-05-18T..."
  },
  {
    "id":          "b2c3d4e5-...",
    "field_name":  "storage_conditions",
    "field_label": "Storage Conditions",
    "field_type":  "select",
    "options": [
      "Ambient (15–25°C, dry)",
      "Cool & Dry (10–15°C)",
      "Refrigerated (2–8°C)",
      "Frozen (below -18°C)",
      "Protect from light"
    ],
    "is_required": false,
    "applies_to_product_types": ["FOOD_AND_BEVERAGE", "MEDICATION", "SUPPLEMENT"],
    "group":       "Storage & Handling",
    "position":    1,
    "is_active":   true
  }
]
```

Results are ordered by `group` then `position`.

---

## `POST /api/v1/products/org-custom-fields`

**Create a new custom field definition.**

**Auth:** Manager+

**Request body:**
```json
{
  "field_name":   "batch_number",
  "field_label":  "Batch / Lot Number",
  "field_type":   "text",
  "placeholder":  "e.g. BT-2026-0512-A",
  "help_text":    "Production batch number printed on the packaging. Required by TFDA.",
  "is_required":  true,
  "max_length":   50,
  "applies_to_product_types": ["FOOD_AND_BEVERAGE", "GROCERY", "MEDICATION"],
  "group":        "Regulatory Compliance",
  "position":     1,
  "unit":         null
}
```

### Field types

| `field_type` | UI control | `options` needed |
|-------------|-----------|-----------------|
| `text` | Single-line text input | No |
| `textarea` | Multi-line text area | No |
| `number` | Numeric input | No — use `unit` for suffix |
| `date` | Date picker | No |
| `url` | URL input with validation | No |
| `select` | Dropdown | Yes — list of strings |
| `boolean` | Checkbox / toggle | No |

### Field schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `field_name` | string | Yes | Internal key (unique per org). Use snake_case e.g. `batch_number`. Immutable after creation. |
| `field_label` | string | Yes | Human-readable label in the form UI e.g. `"Batch / Lot Number"` |
| `field_type` | string | No | Default: `text` |
| `options` | list | Conditional | Required when `field_type = "select"`. List of option strings. |
| `placeholder` | string | No | Input placeholder text |
| `help_text` | string | No | Tooltip / explanation shown below the input |
| `is_required` | bool | No | Default: `false`. If `true`, product cannot be published without this field filled. |
| `max_length` | int | No | Maximum character length for `text`/`textarea` fields |
| `applies_to_product_types` | list | No | List of `ProductType` values. **Null = applies to all types.** |
| `group` | string | No | Section heading in the form e.g. `"Regulatory Compliance"`, `"Storage"` |
| `position` | int | No | Display order within the group. Default: 0 |
| `unit` | string | No | Unit suffix for number fields e.g. `"g"`, `"days"`, `"°C"` |

**Response `201`:** Full field definition object (same as GET response item).

**Error `409`:** `FIELD_NAME_EXISTS` — a field with that `field_name` already exists for this org.

---

### Complete examples

**Pharmaceutical org — Batch + Expiry + TFDA:**
```json
[
  {
    "field_name": "batch_number",
    "field_label": "Batch / Lot Number",
    "field_type": "text",
    "is_required": true,
    "placeholder": "e.g. BT-2026-0512-A",
    "help_text": "As printed on packaging. Required by TFDA GMP.",
    "group": "Regulatory Compliance",
    "position": 1,
    "applies_to_product_types": ["MEDICATION", "SUPPLEMENT", "MEDICAL_DEVICE"]
  },
  {
    "field_name": "expiry_date",
    "field_label": "Expiry / Best Before Date",
    "field_type": "date",
    "is_required": true,
    "group": "Regulatory Compliance",
    "position": 2,
    "applies_to_product_types": ["MEDICATION", "SUPPLEMENT", "FOOD_AND_BEVERAGE"]
  },
  {
    "field_name": "tfda_reg_number",
    "field_label": "TFDA Registration Number",
    "field_type": "text",
    "is_required": false,
    "placeholder": "e.g. TFDA/MED/2022/T/004521",
    "group": "Regulatory Compliance",
    "position": 3,
    "applies_to_product_types": ["MEDICATION", "SUPPLEMENT", "MEDICAL_DEVICE", "FOOD_AND_BEVERAGE"]
  }
]
```

**Food org — Halal + Storage + Net Weight:**
```json
[
  {
    "field_name": "halal_certified",
    "field_label": "Halal Certified",
    "field_type": "boolean",
    "help_text": "Check if this product is certified Halal by an accredited body.",
    "group": "Certifications",
    "position": 1,
    "applies_to_product_types": ["FOOD_AND_BEVERAGE", "GROCERY", "BEVERAGE", "SNACK"]
  },
  {
    "field_name": "storage_conditions",
    "field_label": "Storage Conditions",
    "field_type": "select",
    "options": ["Ambient (15–25°C)", "Refrigerated (2–8°C)", "Frozen (below -18°C)", "Protect from light"],
    "group": "Storage & Handling",
    "applies_to_product_types": ["FOOD_AND_BEVERAGE", "MEDICATION", "SUPPLEMENT"]
  },
  {
    "field_name": "net_weight_g",
    "field_label": "Net Weight",
    "field_type": "number",
    "unit": "g",
    "help_text": "Net weight of product contents, excluding packaging.",
    "group": "Packaging",
    "applies_to_product_types": ["FOOD_AND_BEVERAGE", "GROCERY", "ORGANIC_PRODUCT", "SNACK"]
  }
]
```

**NGO / Government project org:**
```json
[
  {
    "field_name": "donor_reference",
    "field_label": "Donor Reference / Grant Number",
    "field_type": "text",
    "is_required": false,
    "placeholder": "e.g. WB-TZ-P175247",
    "group": "Project Compliance"
  },
  {
    "field_name": "procurement_category",
    "field_label": "Procurement Category",
    "field_type": "select",
    "options": ["Goods", "Works", "Non-Consulting Services", "Consulting Services"],
    "is_required": true,
    "group": "Project Compliance"
  }
]
```

---

## `PATCH /api/v1/products/org-custom-fields/{field_id}`

**Update a custom field definition.**

**Auth:** Manager+

Any field may be updated except `id`, `org_id`, `created_by`, `created_at`, and `field_name` (immutable).

**Request body (partial — any subset of fields):**
```json
{
  "field_label":   "Batch Number / Lot Code",
  "help_text":     "Updated: as required by TBS TZS 5:2015 and TFDA regulations",
  "options":       ["Option A", "Option B", "Option C"],
  "is_required":   true,
  "position":      0
}
```

**Response `200`:** Updated field definition object.
**Error `404`:** `CUSTOM_FIELD_NOT_FOUND`

---

## `DELETE /api/v1/products/org-custom-fields/{field_id}`

**Deactivate a custom field definition.**

Does not hard-delete — sets `is_active = false` so existing product data using this field is preserved. The field will no longer appear on new product forms.

**Auth:** Manager+

**Response `204` No Content**
**Error `404`:** `CUSTOM_FIELD_NOT_FOUND`

---

---

# Part 3 — Product Documents

Attach PDFs, Markdown guides, DOCX files, and other documents to any product or service listing. Each document has a type, format, access level (public/private), and optional inline Markdown content.

---

## `GET /api/v1/products/{product_id}/documents`

**List all documents attached to a product.**

**Auth:** Staff+

**Query params:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `public_only` | bool | `false` | `true` returns only documents with `is_public = true` (for public-facing views and QR scanners) |

**Response `200`:**
```json
[
  {
    "id":             "c3d4e5f6-...",
    "product_id":     "82387849-...",
    "title":          "Karibu Fortified Maize Flour — Product Specification Sheet",
    "document_type":  "DATASHEET",
    "file_format":    "PDF",
    "file_url":       "https://minio.riviwa.com/riviwa-products/karibu/karibu-flour-spec-sheet.pdf",
    "file_size_bytes": 312450,
    "content_md":     null,
    "version":        "3.2",
    "language":       "en",
    "description":    "Full product specs including nutritional analysis and TBS compliance details.",
    "is_public":      true,
    "uploaded_by":    "uuid",
    "created_at":     "2026-05-18T...",
    "updated_at":     "2026-05-18T..."
  },
  {
    "id":             "d4e5f6a7-...",
    "title":          "Cooking Guide — Mwongozo wa Kupika (Kiswahili)",
    "document_type":  "MANUAL",
    "file_format":    "MD",
    "file_url":       "https://minio.riviwa.com/riviwa-products/karibu/cooking-guide-sw.md",
    "file_size_bytes": null,
    "content_md":     "# Mwongozo wa Kupika\n\n## Ugali\n1. Chemsha maji...",
    "version":        "1.0",
    "language":       "sw",
    "is_public":      true
  },
  {
    "id":             "e5f6a7b8-...",
    "title":          "Batch Quality Control Report — May 2026",
    "document_type":  "OTHER",
    "file_format":    "PDF",
    "file_url":       "https://minio.riviwa.com/riviwa-products/karibu/qc-may2026.pdf",
    "version":        "BT-2026-0512",
    "is_public":      false,
    "description":    "Internal QC lab results — staff access only."
  }
]
```

**`is_public = false` documents** are only visible to authenticated org staff. Public-facing views (QR scanner, consumer app) should always call with `?public_only=true`.

---

## `POST /api/v1/products/{product_id}/documents`

**Attach a document to a product.**

**Auth:** Manager+

Upload the file to MinIO first (`/api/v1/products/{id}/images` uses the same MinIO bucket pattern), then call this endpoint with the resulting URL.

**Request body:**
```json
{
  "title":          "User Manual v2.1",
  "document_type":  "MANUAL",
  "file_format":    "PDF",
  "file_url":       "https://minio.riviwa.com/riviwa-products/brand/product-manual-v2.1.pdf",
  "file_size_bytes": 524288,
  "content_md":     null,
  "version":        "2.1",
  "language":       "en",
  "description":    "Full user manual including installation, operation, and troubleshooting.",
  "is_public":      true
}
```

### Document types

| `document_type` | Purpose | Typical `file_format` |
|----------------|---------|----------------------|
| `MANUAL` | Full user / operator manual | PDF, DOCX |
| `INSTALLATION` | Setup and installation guide | PDF, MD |
| `DATASHEET` | Technical specification sheet | PDF |
| `SAFETY_SHEET` | MSDS / safety data sheet | PDF |
| `CERTIFICATE` | Compliance / certification scan | PDF |
| `WARRANTY` | Warranty terms and conditions | PDF, DOCX |
| `TERMS` | Terms of service / use | PDF, DOCX, MD |
| `API_REFERENCE` | Developer / API documentation | MD, HTML |
| `TRAINING_GUIDE` | Course materials or syllabus | PDF, DOCX, MD |
| `QUICK_START` | Quick-start / getting-started guide | PDF, MD |
| `BROCHURE` | Product brochure or catalogue page | PDF |
| `OTHER` | Any other document | Any |

### File formats

| `file_format` | Notes |
|--------------|-------|
| `PDF` | Served as download link |
| `MD` | Markdown — can be rendered inline via `content_md` field |
| `DOCX` | Served as download link |
| `TXT` | Plain text |
| `HTML` | Served as download or rendered in iframe |

### Request body fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | Yes | Display name e.g. `"User Manual v2.1"` |
| `document_type` | string | No | Default: `OTHER` |
| `file_format` | string | No | Default: `PDF` |
| `file_url` | string | Yes | MinIO URL or signed download URL |
| `file_size_bytes` | int | No | File size shown to user (e.g. `524288` = 512 KB) |
| `content_md` | string | No | Raw Markdown content — renders inline on product page. Use for MD-format guides. |
| `version` | string | No | e.g. `"2.1"`, `"v4.1-2026"`, `"BT-2026-0512"` |
| `language` | string | No | BCP-47 language tag. Default: `"en"`. Use `"sw"` for Kiswahili. |
| `description` | string | No | Short summary (max 500 chars) |
| `is_public` | bool | No | Default: `true`. Set to `false` for internal/staff-only documents. |

**Response `201`:** Full document object.

---

### Examples by product type

**Food product — TFDA compliance documents:**
```json
[
  {
    "title":         "TFDA Certificate of Registration",
    "document_type": "CERTIFICATE",
    "file_format":   "PDF",
    "file_url":      "https://minio.riviwa.com/products/karibu/tfda-cert-2023.pdf",
    "file_size_bytes": 98304,
    "version":       "2023",
    "language":      "en",
    "description":   "TFDA certificate valid until December 2025.",
    "is_public":     true
  },
  {
    "title":         "Cooking Guide — Mwongozo wa Kupika (Kiswahili)",
    "document_type": "MANUAL",
    "file_format":   "MD",
    "file_url":      "https://minio.riviwa.com/products/karibu/cooking-guide-sw.md",
    "content_md":    "# Mwongozo wa Kupika\n\n## Ugali\n1. Chemsha maji mawili vikombe...",
    "version":       "1.0",
    "language":      "sw",
    "is_public":     true
  },
  {
    "title":         "Batch QC Report — May 2026",
    "document_type": "OTHER",
    "file_format":   "PDF",
    "file_url":      "https://minio.riviwa.com/products/karibu/qc-may2026.pdf",
    "version":       "BT-2026-0512",
    "description":   "Internal QC report — staff only.",
    "is_public":     false
  }
]
```

**Medication — Patient Information Leaflet + dosage guide:**
```json
[
  {
    "title":         "Patient Information Leaflet (PIL)",
    "document_type": "MANUAL",
    "file_format":   "PDF",
    "file_url":      "https://minio.riviwa.com/products/dawa-plus/para500-pil.pdf",
    "file_size_bytes": 142336,
    "version":       "v4.1-2026",
    "language":      "en",
    "description":   "Full patient info including contraindications, interactions, and overdose guidance.",
    "is_public":     true
  },
  {
    "title":         "Quick Dosage Guide (Kiswahili)",
    "document_type": "QUICK_START",
    "file_format":   "MD",
    "file_url":      "https://minio.riviwa.com/products/dawa-plus/dosage-guide-sw.md",
    "content_md":    "# Dawa Plus — Mwongozo\n\n## Kipimo\n- Tembe 1–2 kila masaa 4–6\n- Usiwe zaidi ya tembe 8 kwa siku",
    "version":       "1.0",
    "language":      "sw",
    "is_public":     true
  }
]
```

**Networking device — router setup:**
```json
[
  {
    "title":         "Quick Start Guide",
    "document_type": "QUICK_START",
    "file_format":   "PDF",
    "file_url":      "https://minio.riviwa.com/products/mikrotik/rb750gr3-quickstart.pdf",
    "file_size_bytes": 524288,
    "version":       "7.x",
    "is_public":     true
  },
  {
    "title":         "Basic Network Setup (renders inline)",
    "document_type": "INSTALLATION",
    "file_format":   "MD",
    "file_url":      "https://minio.riviwa.com/products/mikrotik/setup.md",
    "content_md":    "# Network Setup\n\n```\nISP Modem → Port 1 [Router] Port 2 → Your PC\n```\n\nOpen browser → `http://192.168.88.1`\nLogin: `admin` / *(empty)*",
    "version":       "1.0",
    "is_public":     true
  }
]
```

**Consulting service — scope document:**
```json
{
  "title":         "Service Scope & Deliverables",
  "document_type": "TERMS",
  "file_format":   "PDF",
  "file_url":      "https://minio.riviwa.com/products/services/scope-2026.pdf",
  "file_size_bytes": 456704,
  "version":       "2026-Q2",
  "language":      "en",
  "description":   "Full scope, deliverables, and acceptance criteria.",
  "is_public":     true
}
```

**Maintenance service — SLA agreement:**
```json
{
  "title":         "AMC Agreement Template",
  "document_type": "TERMS",
  "file_format":   "DOCX",
  "file_url":      "https://minio.riviwa.com/products/techcare/amc-template.docx",
  "file_size_bytes": 87552,
  "version":       "2026.1",
  "description":   "Standard AMC agreement. Fill in facility details and sign.",
  "is_public":     true
}
```

---

## `PATCH /api/v1/products/{product_id}/documents/{doc_id}`

**Update document metadata or replace the file URL.**

**Auth:** Manager+

All fields are optional — send only what needs to change.

**Request body:**
```json
{
  "title":         "User Manual v2.2",
  "file_url":      "https://minio.riviwa.com/products/brand/product-manual-v2.2.pdf",
  "file_size_bytes": 598016,
  "version":       "2.2",
  "description":   "Updated manual — added troubleshooting section.",
  "content_md":    null,
  "language":      "en",
  "is_public":     true
}
```

| Updatable fields | `title` · `document_type` · `file_url` · `file_size_bytes` · `content_md` · `version` · `language` · `description` · `is_public` |
|---|---|

**Response `200`:** Updated document object.
**Error `404`:** `DOCUMENT_NOT_FOUND`

---

## `DELETE /api/v1/products/{product_id}/documents/{doc_id}`

**Remove a document from a product.**

**Auth:** Manager+

Hard deletes the document record. The file itself in MinIO is not deleted — manage file cleanup separately if needed.

**Response `204` No Content**
**Error `404`:** `DOCUMENT_NOT_FOUND`

---

---

# Part 4 — New Service Product Types

Eight service-specific product types have been added to `ProductType`. Services use the same product API as physical goods, with `how_to_use` being especially important for describing how to access or engage the service.

| `product_type` | Use for |
|---------------|---------|
| `SERVICE` | Generic service offering not covered by a specific type |
| `CONSULTING_SERVICE` | Advisory, professional services, audits, feasibility studies |
| `DIGITAL_SERVICE` | SaaS platforms, APIs, digital subscriptions, cloud services |
| `MAINTENANCE_SERVICE` | AMC contracts, repairs, upkeep, preventive maintenance |
| `INSTALLATION_SERVICE` | Setup, deployment, commissioning, configuration services |
| `TRAINING_SERVICE` | Workshops, courses, certification programmes |
| `HEALTHCARE_SERVICE` | Medical consultations, lab services, wellness programmes |
| `LOGISTICS_SERVICE` | Freight, delivery, warehousing, last-mile logistics |

**Example — creating a training service:**
```json
{
  "product_type":  "TRAINING_SERVICE",
  "seller_sku":    "TRAIN-GRM-ADMIN-001",
  "title":         "Riviwa GRM Admin Training — 2-Day Workshop",
  "brand":         "Riviwa Academy",
  "price":         350000,
  "currency":      "TZS",
  "quantity":      20,
  "made_in":       "Training delivered by Riviwa Technologies Ltd, Tanzania",
  "how_to_use":    "## How to Enrol\n1. Register via the Riviwa Academy portal\n2. Pay the training fee\n3. Receive calendar invite and pre-reading materials\n\n## What to Bring\n- Laptop with internet access\n- Your Riviwa admin credentials\n\n## Schedule\n- Day 1: Platform navigation, org setup, user management\n- Day 2: Projects, escalations, reports, analytics",
  "description":   "Hands-on 2-day training for Riviwa GRM platform administrators.",
  "attributes": [
    {"attribute_name": "Duration",     "attribute_value": "2 days (16 hours)"},
    {"attribute_name": "Language",     "attribute_value": "English and Kiswahili"},
    {"attribute_name": "Max Trainees", "attribute_value": "20 per cohort"},
    {"attribute_name": "Certificate",  "attribute_value": "Riviwa Certified GRM Admin (RCGA)"}
  ]
}
```

---

---

# Summary — All New Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| `GET` | `/products/org-custom-fields` | Staff | List org's custom field definitions |
| `POST` | `/products/org-custom-fields` | Manager | Create a custom field definition |
| `PATCH` | `/products/org-custom-fields/{field_id}` | Manager | Update field label, options, required flag |
| `DELETE` | `/products/org-custom-fields/{field_id}` | Manager | Deactivate a field definition |
| `GET` | `/products/{id}/documents` | Staff | List product documents (filter `?public_only=true`) |
| `POST` | `/products/{id}/documents` | Manager | Attach a PDF, Markdown, DOCX, etc. |
| `PATCH` | `/products/{id}/documents/{doc_id}` | Manager | Update document metadata or file URL |
| `DELETE` | `/products/{id}/documents/{doc_id}` | Manager | Remove a document |

**New fields on existing endpoints** (`POST /products/`, `PATCH /products/{id}`, `GET /products/{id}`):

| Field | Type | In Create | In Update | In Response |
|-------|------|-----------|-----------|-------------|
| `made_in` | string (150) | Optional | Optional | ✅ |
| `how_to_use` | text (Markdown) | Optional | Optional | ✅ |

---

## Error Reference

| Code | Error | Reason |
|------|-------|--------|
| `401` | `UNAUTHORISED` | Missing or invalid JWT |
| `403` | `FORBIDDEN` | Insufficient role (need Manager+) |
| `404` | `CUSTOM_FIELD_NOT_FOUND` | Field ID not found or belongs to another org |
| `404` | `DOCUMENT_NOT_FOUND` | Document ID not found or belongs to another product |
| `409` | `FIELD_NAME_EXISTS` | A field with that `field_name` already exists for this org |

---

## Live Data (as of 2026-05-18)

From the test run — products created with all new fields:

| Product | Type | `made_in` | `how_to_use` | Docs |
|---------|------|-----------|--------------|------|
| Karibu Fortified Maize Flour 2kg | FOOD_AND_BEVERAGE | Made in Tanzania | 675 chars | 4 (1 private) |
| Dawa Plus Paracetamol 500mg | MEDICATION | Manufactured in Tanzania | ✅ | 3 public |
| MikroTik hEX RB750GR3 Router | NETWORKING_DEVICE | Designed in Latvia | ✅ | 3 public |
| Riviwa GRM Onboarding Service | CONSULTING_SERVICE | Tanzania | ✅ | 3 public |
| Hospital IT AMC | MAINTENANCE_SERVICE | Tanzania | ✅ | 2 public |

**Org custom fields defined:** 7 active fields across 3 compliance groups (Regulatory Compliance · Certifications · Storage & Handling · Packaging).
