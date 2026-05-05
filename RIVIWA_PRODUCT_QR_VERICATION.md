# Riviwa Product, QR & Verification API Reference

> Document: `RIVIWA_PRODUCT_QR_VERICATION.md`  
> Generated: 2026-05-05  
> Services: **product_service** (8110) · **qr_service** (8120) · **verification_service** (8125) · **ai_service** (8085) · **auth_service** (8000)  
> Base URL (production): `https://api.riviwa.com`  
> Direct (dev/server): `http://77.237.241.13:{port}`

---

## Table of Contents

1. [Authentication — Login & Registration](#1-authentication--login--registration)
2. [Organisation Setup — Prerequisites for Products](#2-organisation-setup--prerequisites-for-products)
3. [Product Creation — Step-by-Step Flow](#3-product-creation--step-by-step-flow)
4. [Product Service Endpoints](#4-product-service-endpoints)
5. [QR Service — Authenticated Endpoints](#5-qr-service--authenticated-endpoints)
6. [QR Service — Internal Endpoints](#6-qr-service--internal-endpoints)
7. [QR Service — Public Endpoint](#7-qr-service--public-endpoint)
8. [Verification Service — Consumer Endpoints](#8-verification-service--consumer-endpoints)
9. [Verification Service — Staff / Admin Endpoints](#9-verification-service--staff--admin-endpoints)
10. [Verification Service — Analytics Endpoints](#10-verification-service--analytics-endpoints)
11. [AI Service — Image Intelligence Endpoints](#11-ai-service--image-intelligence-endpoints)
12. [Auth Service — SMS Code](#12-auth-service--sms-code)
13. [End-to-End Flows](#13-end-to-end-flows)
14. [Code Formats & Rules](#14-code-formats--rules)
15. [Error Responses](#15-error-responses)

---

## 1. Authentication — Login & Registration

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

## 2. Organisation Setup — Prerequisites for Products

> Every product in Riviwa belongs to an **Organisation**. A user cannot create products in their personal (consumer) view — they must first create an organisation, have it verified by a platform admin, then switch their session into the org dashboard. Only then will the JWT carry an `org_id`, which all product endpoints require.

### 2.1 The Prerequisite Chain

```
 ┌─────────────────────────────────────────────────────────────┐
 │  STEP 1 — Register a user account                          │
 │  POST /api/v1/auth/register/init                            │
 │  POST /api/v1/auth/register/verify-otp                      │
 │  POST /api/v1/auth/register/complete   (set password)       │
 └────────────────────────────┬────────────────────────────────┘
                              │
 ┌────────────────────────────▼────────────────────────────────┐
 │  STEP 2 — Login                                             │
 │  POST /api/v1/auth/login                                    │
 │  POST /api/v1/auth/login/verify-otp                         │
 │  → JWT:  { sub, org_id: null, org_role: null }              │
 └────────────────────────────┬────────────────────────────────┘
                              │
 ┌────────────────────────────▼────────────────────────────────┐
 │  STEP 3 — Create an Organisation                            │
 │  POST /api/v1/orgs                                          │
 │  → status: PENDING_VERIFICATION                             │
 │  → caller becomes org OWNER automatically                   │
 └────────────────────────────┬────────────────────────────────┘
                              │
 ┌────────────────────────────▼────────────────────────────────┐
 │  STEP 4 — Platform Admin verifies the Organisation          │
 │  POST /api/v1/orgs/{org_id}/verify   [admin JWT required]   │
 │  → status: ACTIVE, is_verified: true                        │
 └────────────────────────────┬────────────────────────────────┘
                              │
 ┌────────────────────────────▼────────────────────────────────┐
 │  STEP 5 — Switch into the Org Dashboard                     │
 │  POST /api/v1/auth/switch-org  { "org_id": "..." }          │
 │  → NEW JWT: { sub, org_id: "...", org_role: "OWNER" }       │
 │  Use this new token for ALL product & QR endpoints          │
 └────────────────────────────┬────────────────────────────────┘
                              │
 ┌────────────────────────────▼────────────────────────────────┐
 │  STEP 6 — (Recommended) Set Org SMS Code                    │
 │  PATCH /api/v1/orgs/{org_id}  { "sms_code": "TARURA" }      │
 │  → All QR codes will use TARURA-{SHORT_CODE} format         │
 └────────────────────────────┬────────────────────────────────┘
                              │
 ┌────────────────────────────▼────────────────────────────────┐
 │  STEP 7 — Create & Publish Products                         │
 │  POST /api/v1/products/                                     │
 │  PATCH /api/v1/products/{id}/publish                        │
 │  → Product images auto-indexed into AI Qdrant collection    │
 └─────────────────────────────────────────────────────────────┘
```

---

### 2.2 Register a User Account (3-Step Flow)

#### Step 1A — Initiate Registration
```http
POST /api/v1/auth/register/init
Content-Type: application/json

{
  "email": "owner@company.com"
}
```
> Provide **exactly one** of `email` or `phone_number`. An OTP is dispatched.

Response: `{ "session_token": "...", "otp_channel": "email", "expires_in_seconds": 600 }`

#### Step 1B — Verify OTP
```http
POST /api/v1/auth/register/verify-otp
Content-Type: application/json

{
  "session_token": "<from step 1A>",
  "otp_code": "000000"
}
```
Response: `{ "continuation_token": "...", "expires_in_seconds": 600 }`

#### Step 1C — Complete Registration (set password)
```http
POST /api/v1/auth/register/complete
Content-Type: application/json

{
  "continuation_token": "<from step 1B>",
  "password": "SecurePass@2026!",
  "password_confirm": "SecurePass@2026!",
  "full_name": "John Komba"
}
```
Response: `{ "access_token": "...", "refresh_token": "...", "user_id": "..." }`

> In dev mode the OTP is always `000000`.

---

### 2.3 Login (2-Step Flow)

#### Step 2A — Submit Credentials
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "identifier": "owner@company.com",
  "password": "SecurePass@2026!"
}
```
Response: `{ "login_token": "...", "otp_channel": "email", "expires_in_seconds": 300 }`

#### Step 2B — Verify OTP
```http
POST /api/v1/auth/login/verify-otp
Content-Type: application/json

{
  "login_token": "<from step 2A>",
  "otp_code": "000000"
}
```
Response: `{ "access_token": "eyJ...", "refresh_token": "...", "expires_in": 1800 }`

> This JWT has `org_id: null` — the caller is in **personal/consumer view**. Products cannot be created yet.

---

### 2.4 Create Organisation

```http
POST /api/v1/orgs
Authorization: Bearer <personal-jwt>
Content-Type: application/json
```

**Requirement:** The user's email must be verified (`is_email_verified: true`). The caller automatically becomes the org `OWNER`.

```json
{
  "legal_name": "Tanzania Roads Authority",
  "display_name": "TARURA",
  "slug": "tarura",
  "org_type": "GOVERNMENT",
  "sms_code": "TARURA",
  "country_code": "TZ",
  "timezone": "Africa/Dar_es_Salaam",
  "website_url": "https://tarura.go.tz",
  "support_email": "grm@tarura.go.tz",
  "support_phone": "+255222123456",
  "registration_number": "GOV-TZ-TARURA-2026",
  "description": "Public Infrastructure Unit managing GRM for rural roads"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `legal_name` | string | ✅ | Official registered name (max 200 chars) |
| `display_name` | string | ✅ | Short UI name (max 100 chars) |
| `slug` | string | ✅ | URL-safe unique handle, lowercase alphanumeric + hyphens (e.g. `tarura`) |
| `org_type` | enum | ✅ | `BUSINESS` · `CORPORATE` · `GOVERNMENT` · `NGO` · `INDIVIDUAL_PRO` |
| `sms_code` | string | — | 2–10 uppercase alphanumeric SMS prefix (e.g. `TARURA`, `CRDB`, `NMB`) |
| `country_code` | string | — | ISO 2-letter country code |
| `timezone` | string | — | e.g. `Africa/Dar_es_Salaam` |
| `website_url` | string | — | Organisation website |
| `support_email` | string | — | Public support email |
| `support_phone` | string | — | Public support phone |
| `registration_number` | string | — | Company/charity/govt registration number |
| `tax_id` | string | — | VAT / tax identification |
| `description` | string | — | Max 1000 chars |
| `max_members` | int | — | Team size limit (0 = unlimited) |

**Response `201`:**
```json
{
  "id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "slug": "tarura",
  "legal_name": "Tanzania Roads Authority",
  "display_name": "TARURA",
  "org_type": "GOVERNMENT",
  "status": "PENDING_VERIFICATION",
  "is_verified": false,
  "sms_code": "TARURA",
  "country_code": "TZ",
  "created_at": "2026-05-05T10:00:00Z"
}
```

> Status is `PENDING_VERIFICATION`. The org is **not yet operational** — it cannot transact, create QR codes, or have products published until a platform admin verifies it.

---

### 2.5 Platform Admin Verifies Organisation

```http
POST /api/v1/orgs/{org_id}/verify
Authorization: Bearer <platform-admin-jwt>
```

**Requirement:** Caller must hold `platform_role = admin` or `super_admin`.  
No request body.

**Response `200`:**
```json
{
  "id": "32f183b3-...",
  "status": "ACTIVE",
  "is_verified": true,
  ...
}
```

> After this call the org transitions to `ACTIVE`. The owner can now switch into the org dashboard and start creating products.

**Other admin-only org status endpoints:**

| Endpoint | Effect |
|----------|--------|
| `POST /api/v1/orgs/{id}/suspend` | Temporarily disables org — `{ "reason": "..." }` |
| `POST /api/v1/orgs/{id}/ban` | Permanently bans org — `{ "reason": "..." }` |

---

### 2.6 Switch Into Org Dashboard

```http
POST /api/v1/auth/switch-org
Authorization: Bearer <personal-jwt>
Content-Type: application/json

{
  "org_id": "32f183b3-c09d-4824-b61f-d32e693ad30e"
}
```

**Purpose:** Switches the caller's active dashboard context from personal/consumer view to an org view. Returns a **new JWT** scoped to that org. **Replace your stored token immediately.**

**Requirement:** The caller must be an active member of the org.

**Response `200`:**
```json
{
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "org_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "org_role": "OWNER"
}
```

**JWT payload after switch:**
```json
{
  "sub": "24513388-1822-486e-bec4-15c843172a3d",
  "org_id": "32f183b3-c09d-4824-b61f-d32e693ad30e",
  "org_role": "OWNER",
  "iat": 1746450000,
  "exp": 1746451800
}
```

> This org-scoped JWT is **required** for all product, QR (authenticated), and org management endpoints. Without `org_id` in the JWT, product endpoints return `403`.

**Switch back to personal view:**
```json
{ "org_id": null }
```

---

### 2.7 List / Get / Update Organisation

#### List My Organisations
```http
GET /api/v1/orgs?is_verified=true&org_type=GOVERNMENT&page=1&limit=20
Authorization: Bearer <jwt>
```
Returns organisations created by the authenticated user.

#### Get Organisation
```http
GET /api/v1/orgs/{org_id}
Authorization: Bearer <jwt>
```

#### Update Organisation Profile
```http
PATCH /api/v1/orgs/{org_id}
Authorization: Bearer <org-jwt>      (must be ADMIN or OWNER in this org)
Content-Type: application/json

{
  "display_name": "TARURA Updated",
  "support_email": "newgrm@tarura.go.tz",
  "sms_code": "TARURA"
}
```
All fields optional. Returns updated org object.

#### Deactivate Organisation (Owner only)
```http
DELETE /api/v1/orgs/{org_id}?reason=Closing+operations
Authorization: Bearer <org-jwt>      (must be OWNER)
```

---

### 2.8 Org Membership Management

#### Add Member Directly
```http
POST /api/v1/orgs/{org_id}/members
Authorization: Bearer <org-jwt>      (ADMIN or OWNER required)
Content-Type: application/json

{
  "user_id": "24513388-...",
  "org_role": "MANAGER"
}
```

**Org Roles:**
| Role | Permissions |
|------|-------------|
| `OWNER` | Full control — can delete org, transfer ownership |
| `ADMIN` | Manage members, settings, billing, analytics |
| `MANAGER` | Create/update products, manage listings, images |
| `MEMBER` | Read-only access, limited task actions |

#### Remove Member
```http
DELETE /api/v1/orgs/{org_id}/members/{user_id}
Authorization: Bearer <org-jwt>      (ADMIN or OWNER required)
```

#### Change Member Role
```http
PATCH /api/v1/orgs/{org_id}/members/{user_id}/role
Authorization: Bearer <org-jwt>

{ "org_role": "ADMIN" }
```

#### Invite by Email
```http
POST /api/v1/orgs/{org_id}/invites
Authorization: Bearer <org-jwt>      (ADMIN or OWNER required)

{
  "invited_role": "MANAGER",
  "invited_email": "colleague@company.com",
  "message": "Join our TARURA team on Riviwa"
}
```

---

## 3. Product Creation — Step-by-Step Flow

> This section describes the complete journey from a new user to a published product with AI image indexing.

### Step-by-Step Summary

| Step | Action | Endpoint | JWT context |
|------|--------|----------|-------------|
| 1 | Register account | `POST /api/v1/auth/register/init` → `verify-otp` → `complete` | — |
| 2 | Login | `POST /api/v1/auth/login` → `verify-otp` | Personal JWT |
| 3 | Create org | `POST /api/v1/orgs` | Personal JWT |
| 4 | Admin verifies org | `POST /api/v1/orgs/{id}/verify` | Admin JWT |
| 5 | Switch to org | `POST /api/v1/auth/switch-org` | Personal JWT → Org JWT |
| 6 | Set org SMS code | `PATCH /api/v1/orgs/{id}` | Org JWT (ADMIN+) |
| 7 | Create product | `POST /api/v1/products/` | Org JWT (MANAGER+) |
| 8 | Add images | `POST /api/v1/products/{id}/images` | Org JWT (MANAGER+) |
| 9 | Add bullet points | `PUT /api/v1/products/{id}/bullet-points` | Org JWT (MANAGER+) |
| 10 | Set category attrs | `PUT /api/v1/products/{id}/category-attrs` | Org JWT (MANAGER+) |
| 11 | Publish product | `PATCH /api/v1/products/{id}/publish` | Org JWT (ADMIN+) |
| 12 | Generate product QR batch | `POST /api/v1/qr/bulk` | Org JWT (any) |

### Required Fields Before Publish

A product **cannot be published** unless all four of these are set:

| Field | How to set |
|-------|-----------|
| `title` | Set on create or via `PATCH /products/{id}` |
| `brand` | Set on create or via `PATCH /products/{id}` |
| `price` | Set on create or via `PATCH /products/{id}` |
| `main_image_url` | Set on create, or add a MAIN image via `POST /products/{id}/images` |

> If any are missing, publish returns `400 PRODUCT_NOT_PUBLISHABLE` with a list of the missing fields.

### What Happens on Publish

When `PATCH /api/v1/products/{id}/publish` succeeds:

1. `listing_status` → `BUYABLE` (product is now live)
2. `published_at` timestamp is recorded
3. `rsin` is generated if not already set (Riviwa Standard Identification Number)
4. Kafka event `product.published` is emitted
5. **Background:** all product images are downloaded, CLIP ViT-B/32 embedded, and indexed into the Qdrant `product_images` collection via `ai_service` — this powers counterfeit detection when consumers report suspected fakes

### Minimum Working Example (cURL)

```bash
# Step 5 — switch to org (assume org is already verified)
ORG_JWT=$(curl -s -X POST https://api.riviwa.com/api/v1/auth/switch-org \
  -H "Authorization: Bearer $PERSONAL_JWT" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"32f183b3-c09d-4824-b61f-d32e693ad30e"}' \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# Step 7 — create product
PRODUCT=$(curl -s -X POST https://api.riviwa.com/api/v1/products/ \
  -H "Authorization: Bearer $ORG_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "WEARABLE",
    "seller_sku": "WATCH-PRO-001",
    "title": "Smart Watch Pro",
    "brand": "TechBrand",
    "price": 250000,
    "currency": "TZS",
    "main_image_url": "https://images.example.com/watch.jpg"
  }')
PRODUCT_ID=$(echo $PRODUCT | grep -o '"product_id":"[^"]*"' | cut -d'"' -f4)

# Step 8 — add images
curl -s -X POST "https://api.riviwa.com/api/v1/products/$PRODUCT_ID/images" \
  -H "Authorization: Bearer $ORG_JWT" \
  -H "Content-Type: application/json" \
  -d '{"role":"ALTERNATE","position":2,"url":"https://images.example.com/watch-side.jpg"}'

# Step 11 — publish (indexes images to AI)
curl -s -X PATCH "https://api.riviwa.com/api/v1/products/$PRODUCT_ID/publish" \
  -H "Authorization: Bearer $ORG_JWT"

# Step 12 — generate 100 product QR codes for packaging
curl -s -X POST "https://api.riviwa.com/api/v1/qr/bulk" \
  -H "Authorization: Bearer $ORG_JWT" \
  -H "Content-Type: application/json" \
  -d "{
    \"organisation_id\": \"32f183b3-c09d-4824-b61f-d32e693ad30e\",
    \"product_id\": \"$PRODUCT_ID\",
    \"count\": 100,
    \"qr_type\": \"PRODUCT\",
    \"rsin\": \"RTEST00001\"
  }"
```

---

## 4. Product Service Endpoints

Base path: `/api/v1/products`  
Auth: **JWT** (org dashboard context required — caller must have switched into an org)  
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

## 5. QR Service — Authenticated Endpoints

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

## 6. QR Service — Internal Endpoints

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

## 7. QR Service — Public Endpoint

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

## 8. Verification Service — Consumer Endpoints

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

## 9. Verification Service — Staff / Admin Endpoints

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

## 10. Verification Service — Analytics Endpoints

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

## 11. AI Service — Image Intelligence Endpoints

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

## 12. Auth Service — SMS Code

### 12.1 Set Organisation SMS Code

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

### 12.2 Internal — Get Org SMS Code

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

## 13. End-to-End Flows

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

## 14. Code Formats & Rules

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

## 15. Error Responses

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

*Riviwa Product, QR & Verification API · Built 2026-05-05*
