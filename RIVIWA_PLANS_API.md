# Riviwa — Plans & Add-ons API Reference
**Service:** `subscription_service` · Port `8140` · Nginx path `/api/v1/plans`  
**Tested:** 2026-05-21 · All 21 endpoints verified against live server  
**Base URL:** `https://api.riviwa.com`

---

## Overview

The Plans API manages subscription plan definitions — their pricing, usage limits, and feature flags. It has two scopes:

- **Public** — no authentication. Used by the pricing page and checkout flow.
- **Admin** — requires a platform admin JWT. Used by the Riviwa billing team to create, update, and manage plans.

Plans are referenced by `plan_id` (UUID) throughout the subscription system. Every `subscriptions` row stores a `plan_id` foreign key. Feature entitlement checks join back to `plans` at runtime, so toggling a feature on a plan takes effect immediately for all subscribers on that plan.

---

## Live Plan IDs

| Slug | ID | Monthly | Annual/mo |
|------|----|---------|-----------|
| `starter` | `5b47dbcd-4f70-4673-bc57-84d8381bb77a` | $15.00 | $12.00 |
| `professional` | `70eac674-4e11-4d5b-9181-ec05c60b7189` | $49.00 | $39.00 |
| `business` | `98c3ad05-8d7f-49b8-ac34-1dd9fae4293c` | $149.00 | $119.00 |
| `enterprise` | `6fc8dbe6-f0d4-455d-8dfd-355c101dacfe` | Custom | Custom |

The default plans (`starter`, `professional`, `business`, `enterprise`) cannot be deactivated or deleted. Custom plans created by admins have no such restriction.

---

## Authentication

Admin endpoints require:
```
Authorization: Bearer <admin_access_token>
```

Get a token via the standard login flow:
```
POST /api/v1/auth/login           → login_token
POST /api/v1/auth/login/verify-otp → access_token
```

Unauthenticated requests to admin endpoints return:
```json
HTTP 401
{
  "detail": {
    "error": "UNAUTHORISED",
    "message": "Valid Bearer token required."
  }
}
```

---

---

# Public Endpoints

---

## 1. `GET /api/v1/plans`

List all active, publicly visible plans.

**Auth:** None  
**Used by:** Pricing page, plan selection UI, checkout flow

**Request:**
```
GET /api/v1/plans
```

**Response `200`:**
```json
{
  "plans": [
    {
      "id":           "5b47dbcd-4f70-4673-bc57-84d8381bb77a",
      "slug":         "starter",
      "display_name": "Starter",
      "tagline":      "Everything you need to get started with feedback management",
      "description":  "Perfect for small NGOs, community-based organisations...",
      "pricing": {
        "monthly_usd":        "15.00",
        "annual_usd":         "12.00",
        "annual_monthly_usd": "12.00",
        "annual_total_usd":   "144.00",
        "annual_savings_pct": 20,
        "is_custom":          false
      },
      "trial_days": 14,
      "limits": {
        "team_members":          5,
        "projects":              3,
        "submissions_per_month": 500,
        "sms_per_month":         200,
        "api_calls_per_month":   2000,
        "storage_gb":            2,
        "qr_per_month":          50,
        "staff_profiles":        0
      },
      "features": {
        "sms_channel":        true,
        "whatsapp_channel":   false,
        "phone_call_ai":      false,
        "ai_conversation":    false,
        "ai_insights":        false,
        "voice_transcription": false,
        "ml_predictor":       false,
        "spark_streaming":    false,
        "recommendations":    true,
        "ai_counterfeit":     false,
        "push_notifications": true,
        "whatsapp_notif":     false,
        "advanced_analytics": false,
        "custom_reports":     false,
        "employee_feedback":  true,
        "pap_registry":       true,
        "committee_mgmt":     false,
        "bulk_import":        false,
        "qr_generation":      true,
        "product_verification": true,
        "field_agents":       false,
        "staff_verification": true,
        "bulk_staff_import":  false,
        "staff_analytics":    false,
        "waiting_queue":      false,
        "stakeholder_engagement": false,
        "translation":        true,
        "advanced_translation": false,
        "product_catalog":    true,
        "product_variations": false,
        "rsin":               false,
        "api_access":         true,
        "webhooks":           false,
        "oauth2":             true,
        "widget_embed":       true,
        "audit_logs":         false,
        "mobile_money":       false,
        "paypal":             false,
        "payment_processing": false,
        "social_login":       true,
        "id_verification":    false,
        "fraud_detection":    true,
        "multi_org":          true,
        "2fa":                true,
        "sso":                false,
        "white_label":        false,
        "dedicated_support":  false,
        "custom_sla":         false
      },
      "sla":        "99.5%",
      "sort_order": 1
    }
  ]
}
```

**Notes:**
- Returns only plans where `is_active=true` AND `is_public=true`.
- Plans are sorted by `sort_order` ascending.
- `features` contains all 48 feature keys — `true` = included in plan.
- `pricing.annual_monthly_usd` is the per-month cost when billed annually (same as `annual_usd`).
- `pricing.annual_savings_pct` is always 20 (hardcoded — annual is 20% cheaper).
- `limits` value of `-1` means unlimited.

---

## 2. `GET /api/v1/plans/{id_or_slug}`

Get a single plan by UUID or slug.

**Auth:** None  
**Used by:** Plan detail page, pre-checkout plan confirmation

**Request:**
```
GET /api/v1/plans/professional
GET /api/v1/plans/70eac674-4e11-4d5b-9181-ec05c60b7189
```

Both return the same result. The endpoint detects UUID vs slug automatically.

**Response `200`:** Same shape as a single item from `GET /plans`.

**Response `404`:**
```json
{
  "error": "NOT_FOUND",
  "message": "Plan not found."
}
```

---

## 3. `GET /api/v1/plans/compare`

Full side-by-side feature comparison across all public plans.

**Auth:** None  
**Used by:** Pricing page feature comparison table

**Request:**
```
GET /api/v1/plans/compare
```

**Response `200`:**
```json
{
  "plans": [ { ...same as GET /plans... } ],
  "comparison": {
    "Feedback Channels": [
      {
        "key":         "sms_channel",
        "category":    "Feedback Channels",
        "label":       "SMS Channel",
        "description": "Receive feedback via inbound SMS...",
        "service":     "feedback_service",
        "plans": {
          "starter":      true,
          "professional": true,
          "business":     true,
          "enterprise":   true
        }
      }
    ],
    "AI & Intelligence": [ ... ],
    "Notifications":     [ ... ]
  },
  "categories": [
    "Feedback Channels",
    "AI & Intelligence",
    "Notifications",
    "Analytics",
    "Feedback Management",
    "QR & Verification",
    "Staff",
    "Queue Management",
    "Stakeholder",
    "Translation",
    "Product Catalog",
    "Integration",
    "Payments",
    "Authentication",
    "Platform"
  ]
}
```

**Notes:**
- `comparison` is a dict keyed by category, each containing an array of feature rows.
- Each feature row has `plans` — a dict of `slug → true/false`.
- 15 categories, 48 features total.
- Use this response to render the pricing page comparison table without any client-side logic.

---

## 4. `GET /api/v1/plans/features`

Catalog of all 48 features with descriptions and service attribution.

**Auth:** None  
**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `category` | string | Filter by category name (e.g., `AI & Intelligence`) |
| `service` | string | Filter by service (e.g., `auth_service`, `feedback_service`) |

**Request:**
```
GET /api/v1/plans/features
GET /api/v1/plans/features?category=AI+%26+Intelligence
GET /api/v1/plans/features?service=auth_service
```

**Response `200`:**
```json
{
  "total_features": 48,
  "categories": [
    "AI & Intelligence",
    "Analytics",
    "Authentication",
    "Feedback Channels",
    "Feedback Management",
    "Integration",
    "Notifications",
    "Payments",
    "Platform",
    "Product Catalog",
    "QR & Verification",
    "Queue Management",
    "Staff",
    "Stakeholder",
    "Translation"
  ],
  "services": [
    "ai_service",
    "analytics_service",
    "auth_service",
    "feedback_service",
    "integration_service",
    "notification_service",
    "payment_service",
    "platform",
    "product_service",
    "qr_service",
    "recommendation_service",
    "staff_service",
    "stakeholder_service",
    "translation_service",
    "verification_service",
    "waiting_service"
  ],
  "features": [
    {
      "key":         "sms_channel",
      "category":    "Feedback Channels",
      "label":       "SMS Channel",
      "description": "Receive feedback via inbound SMS. Supports all Tanzanian networks via Karibu OTP API.",
      "service":     "feedback_service"
    }
  ],
  "grouped": {
    "Feedback Channels": [ ... ],
    "AI & Intelligence": [ ... ]
  }
}
```

**Filtered response `200` (e.g., `?service=auth_service`):**
```json
{
  "total_features": 48,
  "features": [
    { "key": "social_login",     "category": "Authentication", "label": "Social Login",       "service": "auth_service" },
    { "key": "id_verification",  "category": "Authentication", "label": "ID Verification",    "service": "auth_service" },
    { "key": "fraud_detection",  "category": "Authentication", "label": "Fraud Detection",    "service": "auth_service" },
    { "key": "multi_org",        "category": "Authentication", "label": "Multi-Org Switching","service": "auth_service" },
    { "key": "2fa",              "category": "Authentication", "label": "Two-Factor Auth",    "service": "auth_service" },
    { "key": "sso",              "category": "Authentication", "label": "Single Sign-On",     "service": "auth_service" }
  ],
  "grouped": { "Authentication": [ ... ] }
}
```

**Available feature keys (all 48):**

| Key | Category | Service |
|-----|----------|---------|
| `sms_channel` | Feedback Channels | feedback_service |
| `whatsapp_channel` | Feedback Channels | feedback_service |
| `phone_call_ai` | Feedback Channels | ai_service |
| `ai_conversation` | AI & Intelligence | ai_service |
| `ai_insights` | AI & Intelligence | analytics_service |
| `voice_transcription` | AI & Intelligence | ai_service |
| `ml_predictor` | AI & Intelligence | analytics_service |
| `spark_streaming` | AI & Intelligence | analytics_service |
| `recommendations` | AI & Intelligence | recommendation_service |
| `ai_counterfeit` | AI & Intelligence | verification_service |
| `push_notifications` | Notifications | notification_service |
| `whatsapp_notif` | Notifications | notification_service |
| `advanced_analytics` | Analytics | analytics_service |
| `custom_reports` | Analytics | analytics_service |
| `employee_feedback` | Feedback Management | feedback_service |
| `pap_registry` | Feedback Management | feedback_service |
| `committee_mgmt` | Feedback Management | feedback_service |
| `bulk_import` | Feedback Management | feedback_service |
| `qr_generation` | QR & Verification | qr_service |
| `product_verification` | QR & Verification | verification_service |
| `field_agents` | QR & Verification | verification_service |
| `staff_verification` | Staff | staff_service |
| `bulk_staff_import` | Staff | staff_service |
| `staff_analytics` | Staff | staff_service |
| `waiting_queue` | Queue Management | waiting_service |
| `stakeholder_engagement` | Stakeholder | stakeholder_service |
| `translation` | Translation | translation_service |
| `advanced_translation` | Translation | translation_service |
| `product_catalog` | Product Catalog | product_service |
| `product_variations` | Product Catalog | product_service |
| `rsin` | Product Catalog | product_service |
| `api_access` | Integration | integration_service |
| `webhooks` | Integration | integration_service |
| `oauth2` | Integration | integration_service |
| `widget_embed` | Integration | integration_service |
| `audit_logs` | Integration | integration_service |
| `mobile_money` | Payments | payment_service |
| `paypal` | Payments | payment_service |
| `payment_processing` | Payments | payment_service |
| `social_login` | Authentication | auth_service |
| `id_verification` | Authentication | auth_service |
| `fraud_detection` | Authentication | auth_service |
| `multi_org` | Authentication | auth_service |
| `2fa` | Authentication | auth_service |
| `sso` | Authentication | auth_service |
| `white_label` | Platform | platform |
| `dedicated_support` | Platform | platform |
| `custom_sla` | Platform | platform |

---

## 5. `GET /api/v1/plans/addons`

List all active add-ons available for purchase.

**Auth:** None  
**Used by:** Checkout add-on selection, billing settings

**Response `200`:**
```json
{
  "addons": [
    {
      "id":            "1931d527-cc5b-44af-8a78-b6e8bf78dd92",
      "slug":          "advanced-trans",
      "name":          "Advanced Translation",
      "description":   "Cloud provider fallback (Google, DeepL, Microsoft) for all 63 languages",
      "type":          "advanced_translation",
      "price_usd":     "15.00",
      "unit":          "month",
      "unit_quantity": 1,
      "is_active":     true,
      "created_at":    "2026-05-17T10:52:47.703257"
    }
  ]
}
```

**Seeded add-ons:**

| Slug | Name | Price | Unit |
|------|------|-------|------|
| `extra-sms-1k` | Extra SMS Bundle | $10.00 | 1,000 SMS |
| `extra-users-5` | Extra Team Members (5) | $25.00 | 5 users |
| `extra-storage-10g` | Extra Storage (10 GB) | $5.00 | 10 GB |
| `extra-api-10k` | Extra API Calls | $5.00 | 10,000 calls |
| `extra-qr-500` | Extra QR Codes (500) | $5.00 | 500 QR |
| `whatsapp-biz` | WhatsApp Business API | $25.00 | month |
| `custom-ai` | Custom AI Model | $199.00 | month |
| `dedicated-kafka` | Dedicated Kafka Cluster | $99.00 | month |
| `advanced-trans` | Advanced Translation | $15.00 | month |
| `phone-ai-minutes` | Phone Call AI (per min) | $0.05 | minute |
| `extra-project` | Extra Project | $10.00 | project |

---

---

# Admin Endpoints

All admin endpoints require `Authorization: Bearer <admin_token>`.

---

## 6. `GET /api/v1/plans/admin/plans`

List all plans including inactive and unpublished ones.

**Auth:** Admin required  
**Used by:** Admin billing dashboard, plan management UI

**Request:**
```
GET /api/v1/plans/admin/plans
Authorization: Bearer <admin_token>
```

**Response `200`:**
```json
{
  "total": 15,
  "plans": [
    {
      "id":           "5b47dbcd-4f70-4673-bc57-84d8381bb77a",
      "slug":         "starter",
      "display_name": "Starter",
      "tagline":      "...",
      "pricing":      { ... },
      "trial_days":   14,
      "limits":       { ... },
      "features":     { ... },
      "sla":          "99.5%",
      "sort_order":   1,
      "is_active":    true,
      "is_public":    true,
      "created_at":   "2026-05-17T10:52:47.703257",
      "updated_at":   "2026-05-19T12:00:00.000000"
    }
  ]
}
```

**Notes:**
- Includes all 4 default plans plus any custom plans created via the admin API.
- Includes inactive (`is_active=false`) and unpublished (`is_public=false`) plans.
- Default plans will always appear at the top (sort_order 1–4).

---

## 7. `POST /api/v1/plans/admin/plans`

Create a new subscription plan.

**Auth:** Admin required  
**Used by:** Plan creation for NGO programmes, government contracts, white-label clients

**Request:**
```
POST /api/v1/plans/admin/plans
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request body:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `slug` | string | **Yes** | URL-safe, unique. e.g. `ngo-starter`, `hospital-bundle` |
| `display_name` | string | **Yes** | Display name shown to users |
| `tagline` | string | No | Short one-line description |
| `description` | string | No | Full description paragraph |
| `monthly_price_usd` | string | No | Decimal string. Default `"0.00"` |
| `annual_price_usd` | string | No | Per-month price when billed annually |
| `trial_days` | int | No | Default `14` |
| `sort_order` | int | No | Position in plan list |
| `is_custom` | bool | No | `true` for "Contact us" Enterprise-style plans |
| `uptime_sla` | string | No | e.g. `"99.9%"` |
| `max_team_members` | int | No | Default `0`. `-1` = unlimited |
| `max_projects` | int | No | Default `0`. `-1` = unlimited |
| `max_submissions_per_month` | int | No | Default `0`. `-1` = unlimited |
| `max_sms_per_month` | int | No | Default `0`. `-1` = unlimited |
| `max_api_calls_per_month` | int | No | Default `0`. `-1` = unlimited |
| `max_storage_gb` | int | No | Default `0`. `-1` = unlimited |
| `max_qr_per_month` | int | No | Default `0`. `-1` = unlimited |
| `max_staff_profiles` | int | No | Default `0`. `-1` = unlimited |
| `has_<feature_key>` | bool | No | Any of the 48 feature flags. Default `false` |

**Request body example:**
```json
{
  "slug":         "ngo-bundle",
  "display_name": "NGO Bundle",
  "tagline":      "Professional features at subsidised pricing for registered NGOs",
  "description":  "Full GRM suite for verified NGOs and CBOs. Includes SMS, WhatsApp, AI conversation, analytics, and API access.",
  "monthly_price_usd": "24.50",
  "annual_price_usd":  "19.50",
  "trial_days": 14,
  "sort_order": 5,
  "max_team_members":          25,
  "max_projects":              15,
  "max_submissions_per_month": 5000,
  "max_sms_per_month":         2000,
  "max_api_calls_per_month":   10000,
  "max_storage_gb":            25,
  "max_qr_per_month":          500,
  "max_staff_profiles":        100,
  "has_sms_channel":        true,
  "has_whatsapp_channel":   true,
  "has_ai_conversation":    true,
  "has_qr_generation":      true,
  "has_product_verification": true,
  "has_staff_verification": true,
  "has_translation":        true,
  "has_advanced_analytics": true,
  "has_api_access":         true,
  "has_oauth2":             true,
  "has_widget_embed":       true,
  "has_fraud_detection":    true,
  "has_social_login":       true,
  "has_multi_org":          true,
  "has_2fa":                true,
  "has_push_notifications": true
}
```

**Response `201`:** Full plan object (same shape as `GET /plans/{slug}`) with additional admin fields:
```json
{
  "id":         "974e30e6-a228-4926-bdc3-80f5b58c38ec",
  "slug":       "ngo-bundle",
  "is_active":  true,
  "is_public":  true,
  "created_at": "2026-05-21T13:35:00.000000",
  "updated_at": "2026-05-21T13:35:00.000000",
  ...
}
```

**Response `409` — slug already exists:**
```json
{
  "detail": {
    "error": "CONFLICT",
    "message": "Plan with slug 'starter' already exists."
  }
}
```

**Notes:**
- New plans start with `is_active=true, is_public=true` unless you pass `is_active: false`.
- All unspecified feature flags default to `false`.
- All unspecified limit fields default to `0` (not unlimited).
- Publish explicitly after reviewing: `PATCH /plans/admin/plans/{id}/publish`.

---

## 8. `PATCH /api/v1/plans/admin/plans/{plan_id}`

Update any combination of plan fields in a single call.

**Auth:** Admin required  
**Used by:** Quick updates to name, tagline, sort order, trial period

**Request:**
```
PATCH /api/v1/plans/admin/plans/974e30e6-a228-4926-bdc3-80f5b58c38ec
Authorization: Bearer <admin_token>
Content-Type: application/json
```

```json
{
  "display_name": "NGO Bundle Plus",
  "tagline":      "Updated for 2027 NGO programme",
  "sort_order":   6,
  "trial_days":   21
}
```

**Immutable fields:** `id`, `slug`, `created_at` — these are ignored if included.

**Response `200`:** Full updated plan object with admin fields.

**Response `404`:**
```json
{ "error": "NOT_FOUND", "message": "Plan not found." }
```

---

## 9. `PATCH /api/v1/plans/admin/plans/{plan_id}/pricing`

Update pricing fields only — without touching features or limits.

**Auth:** Admin required  
**Used by:** Price adjustments, SLA tier changes

**Request:**
```
PATCH /api/v1/plans/admin/plans/70eac674-4e11-4d5b-9181-ec05c60b7189/pricing
Authorization: Bearer <admin_token>
Content-Type: application/json
```

```json
{
  "monthly_price_usd": "49.00",
  "annual_price_usd":  "39.00",
  "trial_days":        14,
  "uptime_sla":        "99.9%"
}
```

**Accepted fields:** `monthly_price_usd`, `annual_price_usd`, `is_custom`, `trial_days`, `uptime_sla`

**Response `200`:**
```json
{
  "id":   "70eac674-4e11-4d5b-9181-ec05c60b7189",
  "slug": "professional",
  "pricing": {
    "monthly_usd":      "49.00",
    "annual_usd":       "39.00",
    "annual_total_usd": "468.00",
    "is_custom":        false,
    "trial_days":       14,
    "uptime_sla":       "99.9%"
  },
  "updated_at": "2026-05-21T14:00:00.000000"
}
```

> **Important:** Changing plan pricing does **not** affect existing subscribers. They retain their locked `effective_monthly_usd` from the time they subscribed. Only new checkouts use the updated price.

---

## 10. `PATCH /api/v1/plans/admin/plans/{plan_id}/limits`

Update usage quota limits for a plan.

**Auth:** Admin required  
**Used by:** Adjusting capacity limits after upsell negotiations, capacity upgrades

**Request:**
```
PATCH /api/v1/plans/admin/plans/98c3ad05-8d7f-49b8-ac34-1dd9fae4293c/limits
Authorization: Bearer <admin_token>
Content-Type: application/json
```

```json
{
  "max_team_members":          100,
  "max_projects":              -1,
  "max_submissions_per_month": -1,
  "max_sms_per_month":         10000,
  "max_api_calls_per_month":   100000,
  "max_storage_gb":            100,
  "max_qr_per_month":          -1,
  "max_staff_profiles":        -1
}
```

**Accepted fields:** `max_team_members`, `max_projects`, `max_submissions_per_month`, `max_sms_per_month`, `max_api_calls_per_month`, `max_storage_gb`, `max_qr_per_month`, `max_staff_profiles`

Use `-1` for unlimited. Use `0` to restrict entirely (blocks usage for that quota).

**Response `200`:**
```json
{
  "id":   "98c3ad05-8d7f-49b8-ac34-1dd9fae4293c",
  "slug": "business",
  "limits": {
    "team_members":          100,
    "projects":              -1,
    "submissions_per_month": -1,
    "sms_per_month":         10000,
    "api_calls_per_month":   100000,
    "storage_gb":            100,
    "qr_per_month":          -1,
    "staff_profiles":        -1
  },
  "updated_at": "2026-05-21T14:05:00.000000"
}
```

> **Important:** Limit changes take effect immediately for all subscribers on this plan at their next usage check.

---

## 11. `PATCH /api/v1/plans/admin/plans/{plan_id}/features`

Enable or disable any set of feature flags on a plan.

**Auth:** Admin required  
**Used by:** Enabling new Riviwa services on existing plans, rolling out features by tier

**Request:**
```
PATCH /api/v1/plans/admin/plans/70eac674-4e11-4d5b-9181-ec05c60b7189/features
Authorization: Bearer <admin_token>
Content-Type: application/json
```

```json
{
  "whatsapp_channel":       true,
  "advanced_analytics":     true,
  "webhooks":               true,
  "phone_call_ai":          false,
  "ai_counterfeit":         false
}
```

Body is a flat object of `feature_key → boolean`. Pass only the keys you want to change.

**Response `200`:**
```json
{
  "id":   "70eac674-4e11-4d5b-9181-ec05c60b7189",
  "slug": "professional",
  "features_changed": {
    "whatsapp_channel":   true,
    "advanced_analytics": true,
    "webhooks":           true,
    "phone_call_ai":      false,
    "ai_counterfeit":     false
  },
  "features": {
    "sms_channel":        true,
    "whatsapp_channel":   true,
    "ai_conversation":    true,
    "advanced_analytics": true,
    "webhooks":           true,
    ...
  },
  "warnings": []
}
```

`warnings` lists any unrecognised feature keys that were ignored:
```json
"warnings": ["Unknown feature key(s): ['invalid_key']. See GET /api/v1/plans/features for valid keys."]
```

> **Important:** Feature changes take effect **immediately** for all subscribers on this plan.  
> To enable a feature for **one specific org only** without changing the plan, use `POST /api/v1/subscriptions/admin/orgs/{org_id}/overrides` instead.

---

## 12. `POST /api/v1/plans/admin/plans/{plan_id}/duplicate`

Clone an existing plan with a new slug and optional pricing overrides.

**Auth:** Admin required  
**Used by:** Creating custom plan variants (e.g., NGO version of Business, hospital bundle from Professional)

**Request:**
```
POST /api/v1/plans/admin/plans/5b47dbcd-4f70-4673-bc57-84d8381bb77a/duplicate
Authorization: Bearer <admin_token>
Content-Type: application/json
```

```json
{
  "slug":              "starter-ngo",
  "display_name":      "Starter NGO",
  "monthly_price_usd": "7.50",
  "annual_price_usd":  "6.00"
}
```

**Required:** `slug`  
**Optional:** Any plan field to override — all others are copied from the source plan.

**Response `201`:** Full plan object with admin fields. The clone starts as `is_active=false, is_public=false`:
```json
{
  "id":         "2e325d36-77e4-494a-9f4a-31e489aed828",
  "slug":       "starter-ngo",
  "is_active":  false,
  "is_public":  false,
  "created_at": "2026-05-21T13:40:00.000000",
  ...
}
```

**Response `409` — slug already exists:**
```json
{
  "detail": {
    "error": "CONFLICT",
    "message": "Plan slug 'starter-ngo' already exists."
  }
}
```

**Response `404` — source plan not found:**
```json
{ "error": "NOT_FOUND", "message": "Plan not found." }
```

**Workflow after cloning:**
```
1. POST /plans/admin/plans/{source_id}/duplicate  → clone created (inactive)
2. PATCH /plans/admin/plans/{clone_id}/pricing     → adjust pricing
3. PATCH /plans/admin/plans/{clone_id}/features    → adjust features
4. PATCH /plans/admin/plans/{clone_id}/limits      → adjust limits
5. PATCH /plans/admin/plans/{clone_id}/publish     → publish when ready
```

---

## 13. `PATCH /api/v1/plans/admin/plans/{plan_id}/publish`

Publish or unpublish a plan (controls public visibility).

**Auth:** Admin required  
**Used by:** Going live with a new plan, pulling a plan from public view

**Request:**
```
PATCH /api/v1/plans/admin/plans/974e30e6-a228-4926-bdc3-80f5b58c38ec/publish
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Publish:**
```json
{ "is_public": true, "is_active": true }
```

**Unpublish (hide from pricing page, keep existing subscribers):**
```json
{ "is_public": false, "is_active": false }
```

**Response `200`:**
```json
{
  "message":   "Plan 'NGO Bundle' published.",
  "is_public": true,
  "is_active": true
}
```

---

## 14. `DELETE /api/v1/plans/admin/plans/{plan_id}`

Deactivate a plan (soft delete).

**Auth:** Admin required  
**Used by:** Retiring custom plans that are no longer offered

**Request:**
```
DELETE /api/v1/plans/admin/plans/2e325d36-77e4-494a-9f4a-31e489aed828
Authorization: Bearer <admin_token>
```

No body required.

**Response `200`:**
```json
{
  "message": "Plan 'Starter Clone (Test)' deactivated.",
  "id":      "2e325d36-77e4-494a-9f4a-31e489aed828"
}
```

**Response `422` — attempting to delete a default plan:**
```json
{
  "detail": {
    "error": "VALIDATION_ERROR",
    "message": "Default plans cannot be deactivated. Create a custom plan instead."
  }
}
```

**Notes:**
- This is a **soft delete** — the plan row is not removed from the database.
- Sets `is_active=false, is_public=false`.
- Existing subscribers on this plan are **not affected** — they keep their subscription.
- The plan will no longer appear on `GET /plans` but remains visible in `GET /plans/admin/plans`.
- Protected plans: `starter`, `professional`, `business`, `enterprise` cannot be deactivated.

---

---

# Admin — Add-on Management

---

## 15. `GET /api/v1/plans/admin/addons`

List all add-ons including inactive ones.

**Auth:** Admin required

**Response `200`:**
```json
{
  "addons": [
    {
      "id":            "uuid",
      "slug":          "extra-sms-1k",
      "name":          "Extra SMS Bundle",
      "description":   "1,000 additional SMS notifications or AI conversations",
      "type":          "extra_sms",
      "price_usd":     "10.00",
      "unit":          "1,000 SMS",
      "unit_quantity": 1000,
      "is_active":     true,
      "created_at":    "2026-05-17T10:52:47.703257"
    }
  ]
}
```

---

## 16. `POST /api/v1/plans/admin/addons`

Create a new add-on.

**Auth:** Admin required

**Request:**
```
POST /api/v1/plans/admin/addons
Authorization: Bearer <admin_token>
Content-Type: application/json
```

```json
{
  "slug":          "extra-sms-5k",
  "name":          "Extra SMS Bundle (5,000)",
  "description":   "5,000 additional SMS per month for large outreach campaigns",
  "type":          "extra_sms",
  "price_usd":     "40.00",
  "unit":          "5,000 SMS",
  "unit_quantity": 5000
}
```

**Required fields:** `slug`, `name`, `type`, `price_usd`

**Valid `type` values:** `extra_sms`, `extra_users`, `extra_storage`, `extra_api_calls`, `extra_qr`, `whatsapp_business`, `custom_ai`, `dedicated_kafka`, `phone_call_ai`, `advanced_translation`

**Response `201`:** Full add-on object.

**Response `409` — slug already exists:**
```json
{
  "detail": {
    "error": "CONFLICT",
    "message": "Add-on slug 'extra-sms-5k' already exists."
  }
}
```

---

## 17. `PATCH /api/v1/plans/admin/addons/{addon_id}`

Update an add-on's name, description, price, or active status.

**Auth:** Admin required

**Request:**
```
PATCH /api/v1/plans/admin/addons/{addon_id}
Authorization: Bearer <admin_token>
Content-Type: application/json
```

```json
{
  "name":        "Extra SMS Bundle (5,000) — Launch Price",
  "price_usd":   "35.00",
  "description": "5,000 SMS — reduced price during 2026 launch",
  "is_active":   true
}
```

**Immutable fields:** `id`, `slug`, `created_at`

**Response `200`:** Full updated add-on object.

---

## 18. `DELETE /api/v1/plans/admin/addons/{addon_id}`

Deactivate an add-on (soft delete — hides from checkout).

**Auth:** Admin required

**Response `200`:**
```json
{
  "message": "Add-on 'Extra SMS Bundle (5,000)' deactivated.",
  "id":      "uuid"
}
```

**Notes:** Deactivation hides the add-on from `GET /plans/addons` (public) but does not affect orgs that already purchased it.

---

---

# Error Reference

| HTTP | Code | When | Example |
|------|------|------|---------|
| `401` | `UNAUTHORISED` | Missing/expired/invalid Bearer token | Admin endpoints without token |
| `404` | `NOT_FOUND` | Plan or add-on does not exist | `GET /plans/nonexistent` |
| `409` | `CONFLICT` | Duplicate slug on create | `POST /plans/admin/plans` with existing slug |
| `422` | `VALIDATION_ERROR` | Missing required field or protected plan | `DELETE` on default plan |
| `422` | `VALIDATION_ERROR` | Missing required field | `POST /plans/admin/plans` without `slug` |

---

---

# Complete Endpoint Inventory

| # | Method | Path | Auth | Tested |
|---|--------|------|------|--------|
| 1 | `GET` | `/api/v1/plans` | None | ✓ |
| 2 | `GET` | `/api/v1/plans/{id_or_slug}` | None | ✓ (both UUID and slug) |
| 3 | `GET` | `/api/v1/plans/compare` | None | ✓ |
| 4 | `GET` | `/api/v1/plans/features` | None | ✓ (no filter, category filter, service filter) |
| 5 | `GET` | `/api/v1/plans/addons` | None | ✓ |
| 6 | `GET` | `/api/v1/plans/admin/plans` | Admin | ✓ |
| 7 | `POST` | `/api/v1/plans/admin/plans` | Admin | ✓ |
| 8 | `PATCH` | `/api/v1/plans/admin/plans/{id}` | Admin | ✓ |
| 9 | `PATCH` | `/api/v1/plans/admin/plans/{id}/pricing` | Admin | ✓ |
| 10 | `PATCH` | `/api/v1/plans/admin/plans/{id}/limits` | Admin | ✓ |
| 11 | `PATCH` | `/api/v1/plans/admin/plans/{id}/features` | Admin | ✓ |
| 12 | `POST` | `/api/v1/plans/admin/plans/{id}/duplicate` | Admin | ✓ |
| 13 | `PATCH` | `/api/v1/plans/admin/plans/{id}/publish` | Admin | ✓ (publish and unpublish) |
| 14 | `DELETE` | `/api/v1/plans/admin/plans/{id}` | Admin | ✓ (custom plan and default plan protection) |
| 15 | `GET` | `/api/v1/plans/admin/addons` | Admin | ✓ |
| 16 | `POST` | `/api/v1/plans/admin/addons` | Admin | ✓ |
| 17 | `PATCH` | `/api/v1/plans/admin/addons/{id}` | Admin | ✓ |
| 18 | `DELETE` | `/api/v1/plans/admin/addons/{id}` | Admin | ✓ |

---

---

# How Plan ID Is Used in Subscriptions

Every subscription stores the plan's UUID as a foreign key. Feature access and limits are resolved at runtime by joining to the `plans` table.

```
subscriptions row
├── plan_id          = "70eac674-..."  ← FK to plans.id
├── org_id           = "455bd8b1-..."
├── status           = "active"
├── billing_cycle    = "monthly"
└── effective_monthly_usd = "49.00"   ← locked at checkout, not from plans.monthly_price_usd
```

**Using plan_id in practice:**

```bash
# Step 1 — get the plan_id for the plan the org wants
GET /api/v1/plans/professional
→ { "id": "70eac674-4e11-4d5b-9181-ec05c60b7189", ... }

# Step 2 — pass plan_id to billing preview
POST /api/v1/subscriptions/billing-preview
{ "plan_id": "70eac674-...", "billing_cycle": "monthly" }

# Step 3 — pass plan_id to checkout
POST /api/v1/checkout
{ "plan_id": "70eac674-...", "billing_cycle": "monthly", "provider": "mpesa", ... }

# Step 4 — pass plan_id to upgrade/downgrade
POST /api/v1/subscriptions/upgrade
{ "plan_id": "98c3ad05-..." }   ← business plan id
```

**Feature resolution flow:**
```
check_feature(org_id, "ai_conversation")
    │
    ├── 1. Check OrgFeatureOverride for (org_id, "ai_conversation")
    │       → if GRANT override:  return True
    │       → if REVOKE override: return False
    │
    └── 2. Read subscriptions.plan_id → plans.has_ai_conversation
            → return the plan flag
```
