# Riviwa Subscription Service — Full API Reference

**Base URL:** `https://api.riviwa.com/api/v1`  
**Service port (internal):** `8140`  
**Version:** `1.0.0`  
**Last updated:** 2026-05-17

All endpoints tested and verified live against `77.237.241.13`.

---

## Contents

1. [Authentication](#authentication)
2. [Plans — Public](#plans--public)
3. [Plans — Admin](#plans--admin)
4. [Subscriptions](#subscriptions)
5. [Checkout](#checkout)
6. [Promotions — Public](#promotions--public)
7. [Promotions — Admin](#promotions--admin)
8. [Sales — Public](#sales--public)
9. [Sales — Admin](#sales--admin)
10. [Billing Admin](#billing-admin)
11. [Error Reference](#error-reference)

---

## Authentication

### Auth requirements per endpoint type

| Endpoint type | Requirement |
|---|---|
| Public endpoints | No header required |
| Org endpoints | `Authorization: Bearer <JWT>` |
| Admin endpoints | `Authorization: Bearer <JWT>` with `org_role` ∈ `OWNER`, `ADMIN`, `SUPER_ADMIN` |
| Internal (service-to-service) | `X-Service-Key: <INTERNAL_SERVICE_KEY>` |

### How to obtain a JWT

```
POST https://api.riviwa.com/api/v1/auth/login
```
```json
{ "identifier": "user@example.com", "password": "your-password" }
```
Response → `login_token`

```
POST https://api.riviwa.com/api/v1/auth/login/verify-otp
```
```json
{ "login_token": "<token>", "otp_code": "123456" }
```
Response → `access_token` (30-minute JWT), `refresh_token`

The JWT payload contains:
```json
{
  "sub": "user-uuid",
  "org_id": "org-uuid",
  "org_role": "OWNER",
  "exp": 1779017537
}
```

Pass the token on every authenticated request:
```
Authorization: Bearer eyJhbGci...
```

---

## Plans — Public

### `GET /plans`

List all public, active plans sorted by `sort_order`.

**Auth:** None

**Response `200`**
```json
{
  "plans": [
    {
      "id": "3a1b2c3d-...",
      "slug": "starter",
      "display_name": "Starter",
      "tagline": "Everything you need to start collecting feedback",
      "description": "Perfect for small NGOs...",
      "pricing": {
        "monthly_usd": "49.00",
        "annual_usd": "39.00",
        "annual_monthly_usd": "39.00",
        "annual_total_usd": "468.00",
        "annual_savings_pct": 20,
        "is_custom": false
      },
      "trial_days": 14,
      "limits": {
        "team_members": 5,
        "projects": 3,
        "submissions_per_month": 500,
        "sms_per_month": 200,
        "api_calls_per_month": 0,
        "storage_gb": 5,
        "qr_per_month": 0,
        "staff_profiles": 0
      },
      "features": {
        "sms_channel": false,
        "ai_conversation": false,
        "advanced_analytics": false,
        "...": "48 feature flags total"
      },
      "sla": "99.5%",
      "sort_order": 1
    }
  ]
}
```

---

### `GET /plans/compare`

Side-by-side comparison of all plans across every feature. Ideal for pricing page rendering.

**Auth:** None

**Response `200`**
```json
{
  "plans": [ "...same as /plans..." ],
  "comparison": {
    "Feedback Channels": [
      {
        "key": "sms_channel",
        "category": "Feedback Channels",
        "label": "SMS Channel",
        "description": "Receive feedback via inbound SMS...",
        "service": "feedback_service",
        "plans": {
          "starter": false,
          "professional": true,
          "business": true,
          "enterprise": true
        }
      }
    ],
    "AI & Intelligence": [ "..." ]
  },
  "categories": [
    "AI & Intelligence", "Analytics", "Authentication",
    "Feedback Channels", "Feedback Management", "Integration",
    "Notifications", "Payments", "Platform",
    "Product Catalog", "QR & Verification", "Queue Management",
    "Recommendation", "Staff", "Stakeholder", "Translation"
  ]
}
```

---

### `GET /plans/features`

Full catalog of all 48 Riviwa features with descriptions and service attribution.

**Auth:** None

**Query parameters**

| Param | Type | Description |
|---|---|---|
| `category` | string | Filter by category name (e.g. `AI & Intelligence`) |
| `service` | string | Filter by service name (e.g. `feedback_service`) |

**Response `200`**
```json
{
  "total_features": 48,
  "categories": ["AI & Intelligence", "Analytics", "..."],
  "services": ["ai_service", "analytics_service", "auth_service", "..."],
  "features": [
    {
      "key": "ai_conversation",
      "category": "AI & Intelligence",
      "label": "AI Conversation (Web/Mobile)",
      "description": "Guided AI dialogue on web and mobile. Auto-submits feedback at confidence ≥ 0.82.",
      "service": "ai_service"
    }
  ],
  "grouped": {
    "AI & Intelligence": [ "...feature objects..." ]
  }
}
```

---

### `GET /plans/addons`

List all purchasable add-ons.

**Auth:** None

**Response `200`**
```json
{
  "addons": [
    {
      "id": "uuid",
      "slug": "extra-sms-1k",
      "name": "Extra SMS Bundle",
      "description": "1,000 additional SMS notifications or AI conversations",
      "type": "extra_sms",
      "price_usd": "10.00",
      "unit": "1,000 SMS",
      "unit_quantity": 1000,
      "is_active": true,
      "created_at": "2026-05-17T10:52:47"
    }
  ]
}
```

**Seeded add-ons**

| Slug | Name | Price |
|---|---|---|
| `extra-sms-1k` | Extra SMS Bundle | $10.00 / 1,000 SMS |
| `extra-users-5` | Extra Team Members (5) | $25.00 / 5 users |
| `extra-storage-10g` | Extra Storage (10 GB) | $5.00 / 10 GB |
| `extra-api-10k` | Extra API Calls | $5.00 / 10,000 calls |
| `extra-qr-500` | Extra QR Codes (500) | $5.00 / 500 QR |
| `whatsapp-biz` | WhatsApp Business API | $25.00 / month |
| `custom-ai` | Custom AI Model | $199.00 / month |
| `dedicated-kafka` | Dedicated Kafka Cluster | $99.00 / month |
| `advanced-trans` | Advanced Translation | $15.00 / month |
| `phone-ai-minutes` | Phone Call AI (per min) | $0.05 / minute |
| `extra-project` | Extra Project | $10.00 / project |

---

### `GET /plans/{plan_id_or_slug}`

Get a single plan by UUID or slug.

**Auth:** None

**Path parameters**

| Param | Description |
|---|---|
| `plan_id_or_slug` | Plan UUID (`3a1b2c3d-...`) or slug (`starter`, `professional`, `business`, `enterprise`) |

**Response `200`** — same shape as a single object from `/plans`

**Response `404`**
```json
{ "error": "NOT_FOUND", "message": "Plan not found." }
```

---

## Plans — Admin

> All admin plan endpoints require `Authorization: Bearer <JWT>` with `org_role ∈ OWNER | ADMIN | SUPER_ADMIN`.

### `GET /plans/admin/plans`

List all plans including inactive ones.

**Response `200`**
```json
{
  "total": 4,
  "plans": [ "...plan objects with is_active, is_public, created_at, updated_at..." ]
}
```

---

### `POST /plans/admin/plans`

Create a new subscription plan.

**Request body**

| Field | Type | Required | Description |
|---|---|---|---|
| `slug` | string | ✓ | URL-safe unique identifier (e.g. `ngo-basic`) |
| `display_name` | string | ✓ | Human-readable name |
| `tagline` | string | | Short marketing line |
| `description` | string | | Full description |
| `monthly_price_usd` | string/number | | Monthly price in USD |
| `annual_price_usd` | string/number | | Per-month price when billed annually |
| `trial_days` | int | | Free trial length (default 14) |
| `sort_order` | int | | Display order |
| `max_team_members` | int | | `-1` = unlimited |
| `max_projects` | int | | `-1` = unlimited |
| `max_submissions_per_month` | int | | `-1` = unlimited |
| `max_sms_per_month` | int | | |
| `max_api_calls_per_month` | int | | `0` = no API access |
| `max_storage_gb` | int | | |
| `max_qr_per_month` | int | | |
| `max_staff_profiles` | int | | |
| `has_*` | bool | | Any of the 48 feature flags |

```json
{
  "slug": "ngo-basic",
  "display_name": "NGO Basic",
  "tagline": "Discounted plan for verified NGOs",
  "description": "Built for non-profit organisations with limited budgets.",
  "monthly_price_usd": "25.00",
  "annual_price_usd": "20.00",
  "trial_days": 30,
  "sort_order": 5,
  "max_team_members": 10,
  "max_projects": 5,
  "max_submissions_per_month": 1000,
  "max_sms_per_month": 500,
  "max_storage_gb": 10,
  "has_sms_channel": true,
  "has_ai_conversation": true,
  "has_translation": true,
  "has_fraud_detection": true
}
```

**Response `201`** — full plan object

---

### `PATCH /plans/admin/plans/{id}`

Update any field on a plan in a single call. `slug`, `id`, and `created_at` are immutable.

```json
{
  "display_name": "NGO Basic Plus",
  "tagline": "Updated tagline",
  "is_public": true
}
```

**Response `200`** — updated plan object

---

### `PATCH /plans/admin/plans/{id}/pricing`

Update pricing fields only.

```json
{
  "monthly_price_usd": "29.00",
  "annual_price_usd": "23.00",
  "trial_days": 30,
  "uptime_sla": "99.9%"
}
```

**Response `200`**
```json
{
  "id": "uuid",
  "slug": "ngo-basic",
  "pricing": {
    "monthly_usd": "29.00",
    "annual_usd": "23.00",
    "annual_total_usd": "276.00",
    "is_custom": false,
    "trial_days": 30,
    "uptime_sla": "99.9%"
  },
  "updated_at": "2026-05-17T11:07:32"
}
```

---

### `PATCH /plans/admin/plans/{id}/limits`

Update usage limits. Use `-1` for unlimited.

```json
{
  "max_team_members": 15,
  "max_projects": 8,
  "max_submissions_per_month": 2000,
  "max_sms_per_month": 1000,
  "max_api_calls_per_month": 5000,
  "max_storage_gb": 20,
  "max_qr_per_month": 200,
  "max_staff_profiles": 50
}
```

**Response `200`**
```json
{
  "id": "uuid",
  "slug": "ngo-basic",
  "limits": {
    "team_members": 15,
    "projects": 8,
    "submissions_per_month": 2000,
    "sms_per_month": 1000,
    "api_calls_per_month": 5000,
    "storage_gb": 20,
    "qr_per_month": 200,
    "staff_profiles": 50
  },
  "updated_at": "2026-05-17T11:07:35"
}
```

---

### `PATCH /plans/admin/plans/{id}/features`

Toggle any set of features on or off. See `GET /plans/features` for all valid keys.

```json
{
  "webhooks": true,
  "api_access": true,
  "advanced_analytics": true,
  "phone_call_ai": false,
  "sso": false
}
```

**Response `200`**
```json
{
  "id": "uuid",
  "slug": "ngo-basic",
  "features_changed": {
    "webhooks": true,
    "api_access": true,
    "advanced_analytics": true,
    "phone_call_ai": false,
    "sso": false
  },
  "features": {
    "sms_channel": true,
    "webhooks": true,
    "api_access": true,
    "...": "all 48 flags"
  },
  "warnings": ["Unknown feature key(s): ['invalid_key']. See GET /api/v1/plans/features for valid keys."]
}
```

---

### `PATCH /plans/admin/plans/{id}/publish`

Publish or unpublish a plan (controls public visibility).

```json
{ "is_public": true, "is_active": true }
```

**Response `200`**
```json
{
  "message": "Plan 'NGO Basic' published.",
  "is_public": true,
  "is_active": true
}
```

---

### `POST /plans/admin/plans/{id}/duplicate`

Clone an existing plan with a new slug. The duplicate starts as inactive (`is_active: false, is_public: false`) for review before publishing.

```json
{
  "slug": "ngo-enterprise",
  "display_name": "NGO Enterprise",
  "monthly_price_usd": "49.00",
  "annual_price_usd": "39.00"
}
```

**Response `200`** — new plan object with `is_active: false`

---

### `DELETE /plans/admin/plans/{id}`

Soft-delete (deactivate) a plan. Does not affect existing subscribers. Default plans (`starter`, `professional`, `business`, `enterprise`) cannot be deactivated.

**Response `200`**
```json
{
  "message": "Plan 'NGO Enterprise' deactivated.",
  "id": "uuid"
}
```

---

### `GET /plans/admin/addons`

List all add-ons including inactive.

**Response `200`**
```json
{ "addons": [ "...addon objects..." ] }
```

---

### `POST /plans/admin/addons`

Create a new purchasable add-on.

| Field | Type | Required | Description |
|---|---|---|---|
| `slug` | string | ✓ | Unique identifier |
| `name` | string | ✓ | Display name |
| `type` | string | ✓ | `extra_sms`, `extra_users`, `extra_storage`, `extra_api_calls`, `extra_qr`, `whatsapp_business`, `custom_ai`, `dedicated_kafka`, `phone_call_ai`, `advanced_translation` |
| `price_usd` | number | ✓ | Price per unit |
| `description` | string | | |
| `unit` | string | | Human label (e.g. `1,000 SMS`) |
| `unit_quantity` | int | | Units per purchase (e.g. `1000`) |

```json
{
  "slug": "extra-projects-3",
  "name": "Extra Projects (3)",
  "description": "3 additional project slots beyond plan limit",
  "type": "extra_users",
  "price_usd": "25.00",
  "unit": "3 projects",
  "unit_quantity": 3
}
```

**Response `201`** — add-on object

---

### `PATCH /plans/admin/addons/{id}`

Update an add-on. `slug` is immutable.

```json
{ "price_usd": "22.00", "description": "Updated description" }
```

**Response `200`** — updated add-on object

---

### `DELETE /plans/admin/addons/{id}`

Deactivate an add-on (soft delete).

**Response `200`**
```json
{ "message": "Add-on 'Extra Projects (3)' deactivated.", "id": "uuid" }
```

---

## Subscriptions

### `POST /subscriptions/trial`

Start a free trial for the authenticated org. Fails if the org already has an active subscription or trial.

**Auth:** Bearer JWT (org required)

**Request body**

| Field | Type | Default | Description |
|---|---|---|---|
| `plan_slug` | string | `professional` | Plan to trial (`starter`, `professional`, `business`) |

```json
{ "plan_slug": "professional" }
```

**Response `201`**
```json
{
  "subscription": {
    "id": "uuid",
    "org_id": "uuid",
    "plan_id": "uuid",
    "plan": { "slug": "professional", "display_name": "Professional" },
    "status": "trialing",
    "billing_cycle": "monthly",
    "current_period_start": "2026-05-17T11:03:45",
    "current_period_end": "2026-05-31T11:03:45",
    "trial_end": "2026-05-31T11:03:45",
    "cancel_at_period_end": false,
    "cancelled_at": null,
    "paused_at": null,
    "pause_resume_at": null,
    "discount_pct": "0",
    "discount_months_remaining": 0,
    "effective_monthly_usd": "149.00",
    "created_at": "2026-05-17T11:03:45"
  },
  "message": "14-day free trial started on Professional. Trial ends 2026-05-31.",
  "trial_end": "2026-05-31T11:03:45"
}
```

**Response `409`** — org already has an active subscription or trial

---

### `GET /subscriptions/current`

Get the authenticated org's current subscription with live usage meters.

**Auth:** Bearer JWT (org required)

**Response `200` — no subscription**
```json
{ "subscription": null, "has_subscription": false }
```

**Response `200` — active subscription**
```json
{
  "has_subscription": true,
  "subscription": {
    "id": "uuid",
    "org_id": "uuid",
    "plan_id": "uuid",
    "plan": { "slug": "professional", "display_name": "Professional" },
    "status": "active",
    "billing_cycle": "monthly",
    "current_period_start": "2026-05-17T11:03:50",
    "current_period_end": "2026-06-16T11:03:50",
    "trial_end": null,
    "cancel_at_period_end": false,
    "cancelled_at": null,
    "paused_at": null,
    "pause_resume_at": null,
    "discount_pct": "0",
    "discount_months_remaining": 0,
    "effective_monthly_usd": "149.00",
    "created_at": "2026-05-17T11:03:50"
  },
  "usage": {
    "submissions":   { "used": 0,  "limit": 5000 },
    "sms":           { "used": 0,  "limit": 2000 },
    "api_calls":     { "used": 0,  "limit": 10000 },
    "storage_bytes": { "used": 0,  "limit": 26843545600 },
    "qr_codes":      { "used": 0,  "limit": 500 },
    "team_members":  { "used": 0,  "limit": 25 }
  }
}
```

**Subscription statuses:** `trialing` | `active` | `paused` | `past_due` | `cancelled` | `expired`

---

### `POST /subscriptions/upgrade`

Upgrade to a higher plan. Generates a prorated invoice immediately.

**Auth:** Bearer JWT (org required)

```json
{ "plan_id": "uuid-of-business-plan" }
```

**Response `200`**
```json
{
  "subscription": { "...updated subscription..." },
  "message": "Upgraded to Business successfully."
}
```

**Response `400`** — trying to upgrade to same or lower plan  
**Response `404`** — no active subscription

---

### `POST /subscriptions/downgrade`

Downgrade to a lower plan. Takes effect at the end of the current billing period (no proration, no refund).

**Auth:** Bearer JWT (org required)

```json
{ "plan_id": "uuid-of-starter-plan" }
```

**Response `200`**
```json
{
  "subscription": { "...updated subscription..." },
  "message": "Downgrade to Starter scheduled. Takes effect at period end.",
  "effective_at": "2027-05-17T11:07:28"
}
```

---

### `POST /subscriptions/cancel`

Cancel the subscription. `immediate: false` (default) cancels at period end; `immediate: true` cancels right now.

**Auth:** Bearer JWT (org required)

```json
{
  "reason": "Too expensive for our current budget",
  "immediate": false
}
```

**Response `200`**
```json
{
  "subscription": { "...subscription with cancel_at_period_end: true..." },
  "message": "Subscription will cancel at 2027-05-17T11:07:28."
}
```

---

### `POST /subscriptions/pause`

Pause the subscription for 1–3 months. Available on **Business** and **Enterprise** plans only.

**Auth:** Bearer JWT (org required)

```json
{ "months": 1 }
```

**Response `200`**
```json
{
  "subscription": { "...subscription with status: paused..." },
  "message": "Subscription paused for 1 month(s). Resumes 2026-06-17T11:07:28."
}
```

**Response `400`** — plan does not support pause, or already paused

---

### `POST /subscriptions/resume`

Resume a paused subscription. Starts a new billing period immediately.

**Auth:** Bearer JWT (org required)

**Request body:** none required (empty `{}`)

**Response `200`**
```json
{
  "subscription": { "...subscription with status: active..." },
  "message": "Subscription resumed successfully."
}
```

---

### `POST /subscriptions/switch-billing-cycle`

Switch between monthly and annual billing.

- **Monthly → Annual:** Charges prorated difference immediately. Period resets to 12 months.
- **Annual → Monthly:** Takes effect at next renewal (no refund).

**Auth:** Bearer JWT (org required)

```json
{ "billing_cycle": "annual" }
```

**Response `200`**
```json
{
  "subscription": { "...subscription with billing_cycle: annual..." },
  "message": "Switched to annual billing. Invoice generated.",
  "amount_due_usd": "1283.97",
  "invoice_number": "INV-2026-537491",
  "new_period_end": "2027-05-17T11:07:28",
  "annual_savings_pct": 20
}
```

When switching to monthly:
```json
{
  "subscription": { "...updated..." },
  "message": "Switched to monthly billing. Takes effect at next renewal (2027-05-17).",
  "effective_at": "2027-05-17T11:07:28"
}
```

---

### `POST /subscriptions/billing-preview`

Calculate the exact price before subscribing. **Public endpoint — no auth required.**

**Auth:** None

| Field | Type | Required | Description |
|---|---|---|---|
| `plan_id` | string (UUID) | ✓ | Plan UUID |
| `billing_cycle` | string | | `monthly` (default) or `annual` |
| `promo_code` | string | | Optional promo code to preview discount |
| `addons` | array | | Add-ons to include |

```json
{
  "plan_id": "uuid-of-professional-plan",
  "billing_cycle": "annual",
  "promo_code": "ANNUAL20",
  "addons": [
    { "slug": "extra-sms-1k", "quantity": 2 }
  ]
}
```

**Response `200`**
```json
{
  "plan": { "id": "uuid", "slug": "professional", "display_name": "Professional" },
  "billing_cycle": "annual",
  "line_items": [
    { "description": "Professional — Annual", "amount_usd": "1428.00" },
    { "description": "Promo: Annual Plan Discount", "amount_usd": "-285.60" },
    { "description": "Extra SMS Bundle × 2", "amount_usd": "20.00", "quantity": 2, "unit_price_usd": "10.00", "subtotal_usd": "20.00" },
    { "description": "VAT (18%)", "amount_usd": "218.59" }
  ],
  "summary": {
    "subtotal_usd": "1448.00",
    "discount_usd": "285.60",
    "addon_total_usd": "20.00",
    "tax_usd": "218.59",
    "total_usd": "1401.00"
  },
  "promo": {
    "code": "ANNUAL20",
    "name": "Annual Plan Discount",
    "label": "20% off",
    "duration": "once"
  },
  "trial_days": 14,
  "next_renewal": "annually after trial"
}
```

---

### `POST /subscriptions/apply-promo`

Apply a promo code to an existing active subscription.

**Auth:** Bearer JWT (org required)

```json
{ "code": "PARTNER25" }
```

**Response `200`**
```json
{
  "message": "Promo code 'PARTNER25' applied — 25.00% off for 6 month(s).",
  "discount_pct": "25.00",
  "discount_months": 6
}
```

**Response `400`**
```json
{ "error": "PROMO_ERROR", "message": "You have already used this promo code." }
```

---

### `GET /subscriptions/invoices`

List all invoices for the authenticated org.

**Auth:** Bearer JWT (org required)

**Query parameters**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `size` | int | 20 | Results per page (max 100) |

**Response `200`**
```json
{
  "total": 3,
  "page": 1,
  "size": 20,
  "invoices": [
    {
      "id": "uuid",
      "invoice_number": "INV-2026-835389",
      "status": "open",
      "subtotal_usd": "49.00",
      "discount_usd": "0",
      "tax_usd": "8.82",
      "total_usd": "57.82",
      "billing_period_start": "2026-05-17T11:03:50",
      "billing_period_end": "2026-06-16T11:03:50",
      "due_date": "2026-05-20T11:03:50",
      "paid_at": null,
      "payment_method_type": "bank_transfer",
      "payment_reference": null,
      "line_items": [
        { "description": "Starter — Monthly", "amount_usd": "49.00", "quantity": 1 },
        { "description": "VAT (18%)", "amount_usd": "8.82", "quantity": 1 }
      ],
      "pdf_url": null,
      "created_at": "2026-05-17T11:03:50"
    }
  ]
}
```

**Invoice statuses:** `draft` | `open` | `paid` | `void` | `uncollectible`

---

### `GET /subscriptions/invoices/{id}`

Get a single invoice.

**Auth:** Bearer JWT (org required — only own invoices)

**Response `200`** — single invoice object (same shape as above)  
**Response `404`** — not found or belongs to different org

---

### `GET /subscriptions/payment-methods`

List saved payment methods for the org.

**Auth:** Bearer JWT (org required)

**Response `200`**
```json
{
  "payment_methods": [
    {
      "id": "uuid",
      "type": "mpesa",
      "is_default": true,
      "display_name": "Test M-Pesa",
      "phone_number": "+255712345678",
      "card_last4": null,
      "card_brand": null,
      "card_exp_month": null,
      "card_exp_year": null
    }
  ]
}
```

---

### `POST /subscriptions/payment-methods`

Add a payment method.

**Auth:** Bearer JWT (org required)

| Field | Type | Description |
|---|---|---|
| `type` | string | `mpesa`, `azampay`, `selcom`, `airtel`, `yas`, `stripe_card`, `bank_transfer` |
| `phone_number` | string | Required for mobile money |
| `display_name` | string | Label shown in UI |
| `is_default` | bool | Set as default (unsets existing default) |
| `card_last4` | string | For card payment methods |
| `card_brand` | string | e.g. `visa`, `mastercard` |
| `card_exp_month` | int | |
| `card_exp_year` | int | |

```json
{
  "type": "mpesa",
  "phone_number": "+255712345678",
  "display_name": "My M-Pesa",
  "is_default": true
}
```

**Response `201`**
```json
{ "id": "uuid", "type": "mpesa", "display_name": "My M-Pesa" }
```

---

### `DELETE /subscriptions/payment-methods/{id}`

Remove (soft-delete) a payment method.

**Auth:** Bearer JWT (org required)

**Response `200`**
```json
{ "message": "Payment method removed." }
```

---

### `GET /subscriptions/events`

Subscription audit trail — all lifecycle events for the org.

**Auth:** Bearer JWT (org required)

**Response `200`**
```json
{
  "events": [
    {
      "event_type": "upgraded",
      "from_plan_id": "uuid",
      "to_plan_id": "uuid",
      "metadata": { "plan": "professional", "billing_cycle": "monthly" },
      "created_at": "2026-05-17T11:07:12"
    },
    {
      "event_type": "subscribed",
      "from_plan_id": null,
      "to_plan_id": null,
      "metadata": { "plan": "starter", "billing_cycle": "monthly" },
      "created_at": "2026-05-17T11:03:52"
    }
  ]
}
```

**Event types:** `trial_started` | `subscribed` | `upgraded` | `downgraded` | `cancelled` | `paused` | `resumed` | `payment_succeeded` | `payment_failed` | `dunned` | `expired` | `promo_applied` | `addon_purchased`

---

### `GET /subscriptions/internal/feature-check`

Internal service-to-service endpoint. Check if an org has access to a specific feature.

**Auth:** `X-Service-Key: <INTERNAL_SERVICE_KEY>` header

**Query parameters**

| Param | Required | Description |
|---|---|---|
| `org_id` | ✓ | Organisation UUID |
| `feature` | ✓ | Feature key (without `has_` prefix, e.g. `ai_conversation`) |

```
GET /subscriptions/internal/feature-check?org_id=455bd8b1-...&feature=ai_conversation
X-Service-Key: change-me-set-a-real-secret-in-production
```

**Response `200`**
```json
{
  "org_id": "455bd8b1-...",
  "feature": "ai_conversation",
  "has_access": true,
  "limits": {
    "max_team_members": 25,
    "max_projects": 15,
    "max_submissions_per_month": 5000,
    "max_sms_per_month": 2000,
    "max_api_calls_per_month": 10000,
    "max_storage_gb": 25,
    "max_qr_per_month": 500,
    "max_staff_profiles": 100
  }
}
```

---

### `GET /subscriptions/admin/all`

List all subscriptions across all orgs.

**Auth:** Bearer JWT (admin role required)

**Query parameters**

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter: `trialing`, `active`, `paused`, `past_due`, `cancelled`, `expired` |
| `page` | int | Page number (default 1) |
| `size` | int | Results per page (default 50, max 100) |

**Response `200`**
```json
{
  "total": 15,
  "page": 1,
  "size": 50,
  "subscriptions": [ "...subscription objects..." ]
}
```

---

### `PATCH /subscriptions/admin/{subscription_id}`

Admin override — update specific fields on any subscription.

**Auth:** Bearer JWT (admin role required)

**Allowed fields:** `status`, `plan_id`, `billing_cycle`, `cancel_at_period_end`, `discount_pct`, `discount_months_remaining`, `current_period_end`

```json
{
  "status": "active",
  "current_period_end": "2026-12-31T23:59:59"
}
```

**Response `200`** — updated subscription object

---

## Checkout

### `POST /checkout`

Full checkout flow. Creates a subscription and delegates payment to `payment_service`. For `bank_transfer`, the subscription activates immediately and an open invoice is returned for manual payment.

**Auth:** Bearer JWT (org required)

| Field | Type | Required | Description |
|---|---|---|---|
| `plan_id` | string (UUID) | ✓ | Plan to subscribe to |
| `billing_cycle` | string | | `monthly` (default) or `annual` |
| `provider` | string | | `mpesa`, `azampay`, `selcom`, `paypal`, `airtel`, `yas`, `bank_transfer` (default) |
| `phone_number` | string | For mobile money | E.164 format, e.g. `+255712345678` |
| `payer_name` | string | | Payer display name |
| `payer_email` | string | | Payer email |
| `promo_code` | string | | Optional promo code |
| `save_method` | bool | | Save payment method for future use |

```json
{
  "plan_id": "uuid-of-professional-plan",
  "billing_cycle": "monthly",
  "provider": "bank_transfer",
  "payer_name": "Muhimbili National Hospital",
  "payer_email": "billing@mnh.go.tz"
}
```

**Response `201` — bank_transfer**
```json
{
  "subscription_id": "uuid",
  "status": "active",
  "invoice": {
    "invoice_number": "INV-2026-835389",
    "total_usd": "57.82",
    "status": "open",
    "due_date": "2026-05-20T11:03:50",
    "line_items": [
      { "description": "Starter — Monthly", "amount_usd": "49.00", "quantity": 1 },
      { "description": "VAT (18%)", "amount_usd": "8.82", "quantity": 1 }
    ]
  },
  "payment": {
    "provider": "bank_transfer",
    "instructions": "Transfer USD 57.82 to Riviwa. Reference: INV-2026-835389. Send proof to billing@riviwa.com."
  },
  "message": "Invoice created. Complete bank transfer to activate."
}
```

**Response `201` — mobile money (M-Pesa / AzamPay / Airtel / Yas)**
```json
{
  "subscription_id": "uuid",
  "status": "active",
  "payment_id": "payment-service-uuid",
  "invoice": { "...invoice object..." },
  "checkout_url": null,
  "payment": {
    "provider": "mpesa",
    "status": "pending",
    "transaction_id": "txn-uuid",
    "message": "USSD prompt sent. Customer enters PIN on their phone."
  },
  "message": "USSD prompt sent to your phone. Enter your PIN to complete payment.",
  "next_renewal": "2026-06-16T11:03:50"
}
```

**Response `201` — PayPal / Selcom (redirect required)**
```json
{
  "subscription_id": "uuid",
  "status": "active",
  "payment_id": "payment-service-uuid",
  "invoice": { "...invoice object..." },
  "checkout_url": "https://www.paypal.com/checkoutnow?token=...",
  "payment": {
    "provider": "paypal",
    "status": "pending",
    "transaction_id": null,
    "message": "Redirect user to: https://www.paypal.com/checkoutnow?token=..."
  },
  "message": "Redirecting to PayPal for payment.",
  "next_renewal": "2026-06-16T11:03:50"
}
```

**Notes:**
- If no `promo_code` is provided, the best active auto-apply sale is automatically applied.
- All invoices include 18% VAT.
- `bank_transfer` activates the subscription immediately without payment verification.

---

### `GET /checkout/status/{payment_id}`

Poll payment status from `payment_service`. Automatically activates the subscription when payment is confirmed.

**Auth:** Bearer JWT (org required)

**Response `200`**
```json
{
  "payment_id": "payment-service-uuid",
  "payment_status": "paid",
  "paid": true,
  "subscription_active": true
}
```

**Payment statuses:** `pending` | `paid` | `failed` | `cancelled` | `expired`

---

### `POST /checkout/pay-invoice/{invoice_id}`

Pay an outstanding open invoice.

**Auth:** Bearer JWT (org required)

```json
{
  "provider": "mpesa",
  "phone_number": "+255712345678"
}
```

**Response `200`**
```json
{
  "invoice_number": "INV-2026-835389",
  "payment_id": "payment-service-uuid",
  "checkout_url": null,
  "message": "USSD prompt sent. Customer enters PIN on their phone."
}
```

---

## Promotions — Public

### `GET /promotions`

List all currently active, publicly visible promotions. Does not expose promo codes — codes are shared separately (email campaigns, checkout forms).

**Auth:** None

**Query parameters**

| Param | Description |
|---|---|
| `plan_slug` | Filter by eligible plan |

**Response `200`**
```json
{
  "promotions": [
    {
      "name": "Riviwa Launch Offer",
      "description": "30% off your first 3 months — available to all new subscribers during our 2026 launch.",
      "discount_label": "30% off",
      "duration_label": "first 3 month(s)",
      "eligible_plans": "all",
      "expires_at": "2026-12-31T23:59:59",
      "new_subscribers_only": true
    }
  ],
  "total": 10
}
```

---

### `POST /promotions/validate`

Validate a promo code and preview the exact discount. Does **not** apply the code.

**Auth:** None

```json
{
  "code": "LAUNCH2026",
  "plan_id": "uuid-of-professional-plan",
  "billing_cycle": "monthly",
  "org_id": "uuid"
}
```

**Response `200` — valid**
```json
{
  "valid": true,
  "code": "LAUNCH2026",
  "name": "Riviwa Launch Offer",
  "discount_type": "percentage",
  "discount_value": "30",
  "discount_label": "30% off",
  "duration": "repeating",
  "duration_months": 3,
  "duration_label": "first 3 month(s)",
  "new_subscribers_only": true,
  "expires_at": "2026-12-31T23:59:59",
  "pricing_preview": {
    "base_price_usd": "149.00",
    "discount_usd": "44.70",
    "final_price_usd": "104.30",
    "billing_cycle": "monthly",
    "plan": "Professional"
  }
}
```

**Response `200` — invalid**
```json
{
  "valid": false,
  "reason": "This promo code has expired."
}
```

**Possible `reason` values:** `Promo code not found.` | `This promo code is no longer active.` | `This promo code has expired.` | `This promo code has reached its maximum redemptions.` | `You have already used this promo code.` | `This code is not valid for the {Plan} plan.`

---

## Promotions — Admin

### `GET /promotions/admin`

List all promo codes with full stats.

**Auth:** Bearer JWT (admin role required)

**Query parameters**

| Param | Description |
|---|---|
| `active_only` | `true` to show only active codes |
| `discount_type` | Filter: `percentage`, `fixed_amount`, `free_months` |
| `plan_slug` | Filter by eligible plan |
| `page` | Page number (default 1) |
| `size` | Results per page (default 50, max 100) |

**Response `200`**
```json
{
  "total": 10,
  "page": 1,
  "size": 50,
  "promo_codes": [
    {
      "id": "uuid",
      "code": "LAUNCH2026",
      "name": "Riviwa Launch Offer",
      "description": "30% off your first 3 months...",
      "discount_type": "percentage",
      "discount_value": "30",
      "duration": "repeating",
      "duration_months": 3,
      "max_redemptions": -1,
      "redemption_count": 0,
      "eligible_plans": null,
      "new_subscribers_only": true,
      "min_plan_price_usd": "0",
      "expires_at": "2026-12-31T23:59:59",
      "is_active": true,
      "created_at": "2026-05-17T10:52:47",
      "stats": {
        "redemptions_used": 0,
        "redemptions_remaining": null,
        "redemption_rate_pct": null,
        "is_expired": false,
        "is_exhausted": false
      }
    }
  ]
}
```

---

### `GET /promotions/admin/{id}`

Get a promo code with full stats and recent redemptions.

**Auth:** Bearer JWT (admin role required)

**Response `200`** — promo object with `stats` + `recent_redemptions`:
```json
{
  "...promo object...",
  "stats": {
    "redemptions_used": 1,
    "redemptions_remaining": 99,
    "redemption_rate_pct": 1.0,
    "is_expired": false,
    "is_exhausted": false
  },
  "recent_redemptions": [
    {
      "org_id": "uuid",
      "subscription_id": "uuid",
      "redeemed_at": "2026-05-17T11:07:28"
    }
  ]
}
```

---

### `POST /promotions/admin`

Create a promo code.

**Auth:** Bearer JWT (admin role required)

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | string | ✓ | Unique code (uppercased automatically) |
| `name` | string | ✓ | Display name |
| `discount_type` | string | ✓ | `percentage`, `fixed_amount`, `free_months` |
| `discount_value` | number | ✓ | 50 = 50%, $20 fixed, or 1 free month |
| `duration` | string | | `once`, `repeating`, `forever` |
| `duration_months` | int | | Months when `duration=repeating` |
| `description` | string | | |
| `max_redemptions` | int | | `-1` = unlimited |
| `eligible_plans` | array | | Plan slugs (null = all plans) |
| `new_subscribers_only` | bool | | Default `false` |
| `min_plan_price_usd` | number | | Minimum plan price to qualify |
| `expires_at` | ISO datetime | | Expiry date |

```json
{
  "code": "HOSPITAL30",
  "name": "Hospital Partner Discount",
  "description": "30% off for first 3 months for verified hospitals",
  "discount_type": "percentage",
  "discount_value": 30,
  "duration": "repeating",
  "duration_months": 3,
  "max_redemptions": 200,
  "eligible_plans": ["professional", "business"],
  "new_subscribers_only": true,
  "expires_at": "2026-12-31T23:59:59"
}
```

**Response `201`** — promo code object with stats

---

### `PATCH /promotions/admin/{id}`

Update a promo code. `code`, `id`, `created_at`, and `redemption_count` are immutable.

```json
{
  "max_redemptions": 500,
  "expires_at": "2027-06-30T23:59:59",
  "is_active": false
}
```

**Response `200`** — updated promo code with stats

---

### `DELETE /promotions/admin/{id}`

Deactivate a promo code (soft delete — sets `is_active: false`).

**Response `200`**
```json
{ "message": "Promo code 'HOSPITAL30' deactivated.", "id": "uuid" }
```

---

### `POST /promotions/admin/bulk-generate`

Generate up to 500 unique promo codes with identical discount settings. Each code is single-use (`max_redemptions: 1`). Useful for email campaigns, partner onboarding, event giveaways.

**Auth:** Bearer JWT (admin role required)

```json
{
  "prefix": "HOSPITAL",
  "count": 50,
  "discount_type": "percentage",
  "discount_value": 25,
  "duration": "once",
  "eligible_plans": ["professional", "business"],
  "new_subscribers_only": true,
  "expires_at": "2026-12-31T23:59:59",
  "name_prefix": "Hospital Partner Code",
  "description": "Hospital referral — 25% off first payment"
}
```

**Response `201`**
```json
{
  "generated": 50,
  "codes": ["HOSPITAL-A3B7C1", "HOSPITAL-D4E8F2", "..."],
  "discount": "25 percentage",
  "expires_at": "2026-12-31T23:59:59"
}
```

---

### `GET /promotions/admin/stats/summary`

Platform-wide promotions dashboard.

**Auth:** Bearer JWT (admin role required)

**Response `200`**
```json
{
  "total_codes": 47,
  "active_codes": 44,
  "total_redemptions": 3,
  "top_codes": [
    { "code": "LAUNCH2026", "name": "Riviwa Launch Offer", "redemptions": 2 },
    { "code": "DONOR10",     "name": "Donor-Funded Programme Discount", "redemptions": 1 }
  ],
  "expiring_soon": [
    { "code": "EARLYBIRD40", "name": "Early Bird — 40% off", "expires_at": "2026-08-01T00:00:00" }
  ]
}
```

---

## Seeded Promo Codes

| Code | Discount | Duration | Plans | New Only | Limit | Expires |
|---|---|---|---|---|---|---|
| `LAUNCH2026` | 30% off | 3 months | All | ✓ | Unlimited | Dec 2026 |
| `ANNUAL20` | 20% off | Once | All | ✗ | Unlimited | Never |
| `NGO50` | 50% off | Forever | Starter only | ✓ | 100 orgs | Never |
| `PARTNER25` | 25% off | 6 months | Pro, Business | ✓ | 500 | Dec 2026 |
| `WELCOME1` | 1 free month | Once | All | ✓ | Unlimited | Sep 2026 |
| `GOV30` | 30% off | Forever | Pro, Business, Enterprise | ✗ | 200 | Never |
| `UPGRADE30` | 30% off | Once | Business only | ✗ | Unlimited | Dec 2026 |
| `STUDENT15` | 15% off | 12 months | Professional only | ✓ | 300 | Jun 2027 |
| `EARLYBIRD40` | 40% off | 2 months | All | ✓ | 50 | Aug 2026 |
| `DONOR10` | $10/mo fixed | Forever | Pro, Business | ✗ | Unlimited | Never |

---

## Sales — Public

### `GET /sales`

List active and upcoming sale campaigns. Active = currently running. Upcoming = scheduled to start in the future.

**Auth:** None

**Query parameters**

| Param | Description |
|---|---|
| `plan_slug` | Filter by eligible plan |
| `cycle` | Filter by billing cycle: `monthly` or `annual` |
| `include_upcoming` | Include scheduled sales (default `true`) |

**Response `200`**
```json
{
  "active_sales": [
    {
      "id": "uuid",
      "name": "Launch Week Sale",
      "description": "Riviwa's official launch — 40% off all plans for new subscribers...",
      "banner_text": "Launch Week — 40% OFF for new subscribers. Ends 31 May!",
      "status": "active",
      "schedule": {
        "start_at": "2026-05-17T00:00:00",
        "end_at": "2026-05-31T23:59:59",
        "starts_in_secs": 0,
        "remaining_secs": 1251478,
        "duration_hours": 359.0
      },
      "discount": {
        "type": "percentage",
        "value": "40",
        "label": "40% off",
        "duration": "once",
        "duration_months": 1
      },
      "targeting": {
        "eligible_plans": "all",
        "eligible_billing_cycles": "all",
        "new_subscribers_only": true
      },
      "auto_apply": true,
      "is_active": true
    }
  ],
  "upcoming_sales": [
    {
      "name": "Mid-Year Sale 2026",
      "...": "same shape as active_sales"
    }
  ],
  "has_active_sale": true
}
```

**Sale statuses:** `scheduled` | `active` | `ended` | `cancelled`

---

### `GET /sales/current`

Get the single best (highest discount) active sale for a given plan and billing cycle. Used by the checkout flow.

**Auth:** None

**Query parameters**

| Param | Default | Description |
|---|---|---|
| `plan_slug` | — | Filter by plan |
| `cycle` | `monthly` | `monthly` or `annual` |

**Response `200` — sale found**
```json
{
  "sale": { "...sale object..." },
  "has_sale": true
}
```

**Response `200` — no applicable sale**
```json
{ "sale": null, "has_sale": false }
```

---

### `GET /sales/{id}`

Get a specific sale by UUID.

**Auth:** None

**Response `200`** — sale object  
**Response `404`** — sale not found or cancelled

---

## Sales — Admin

### `GET /sales/admin/all`

List all sales, optionally filtered by status.

**Auth:** Bearer JWT (admin role required)

**Query parameters**

| Param | Description |
|---|---|
| `status` | `scheduled`, `active`, `ended`, `cancelled` |
| `page` | Page number (default 1) |
| `size` | Results per page (default 50, max 100) |

**Response `200`**
```json
{
  "total": 6,
  "page": 1,
  "size": 50,
  "sales": [
    {
      "...sale object...",
      "limits": {
        "max_redemptions": -1,
        "redemption_count": 3,
        "remaining": null
      },
      "promo_code_id": null,
      "created_at": "2026-05-17T10:52:47",
      "updated_at": "2026-05-17T10:52:47"
    }
  ]
}
```

---

### `POST /sales/admin`

Create a sale campaign.

**Auth:** Bearer JWT (admin role required)

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Campaign name |
| `start_at` | ISO datetime | ✓ | Start time (UTC) |
| `end_at` | ISO datetime | ✓ | End time (UTC) |
| `discount_type` | string | ✓ | `percentage`, `fixed_amount`, `free_months` |
| `discount_value` | number | ✓ | Discount amount |
| `duration` | string | | `once` (default), `repeating`, `forever` |
| `duration_months` | int | | Months for `repeating` |
| `description` | string | | |
| `banner_text` | string | | Text for pricing page banner |
| `eligible_plans` | array | | Plan slugs (null = all) |
| `eligible_billing_cycles` | array | | `["monthly"]`, `["annual"]`, or null (both) |
| `new_subscribers_only` | bool | | Default `false` |
| `max_redemptions` | int | | `-1` = unlimited |
| `auto_apply` | bool | | Auto-apply at checkout without code (default `true`) |
| `generate_code` | bool | | Also create a linked PromoCode |
| `code_prefix` | string | | Prefix for auto-generated code |

```json
{
  "name": "World GRM Day Sale",
  "description": "Celebrating global GRM awareness — 30% off Business for 1 week.",
  "banner_text": "World GRM Day — 30% OFF Business. This week only!",
  "start_at": "2026-06-15T00:00:00",
  "end_at": "2026-06-22T23:59:59",
  "discount_type": "percentage",
  "discount_value": 30,
  "duration": "repeating",
  "duration_months": 3,
  "eligible_plans": ["business"],
  "new_subscribers_only": true,
  "max_redemptions": 500,
  "auto_apply": false,
  "generate_code": true,
  "code_prefix": "GRM"
}
```

**Response `201`** — full sale object (admin view including limits and promo_code_id)

---

### `PATCH /sales/admin/{id}`

Update any sale field. Cannot update a sale that has already ended.

```json
{
  "banner_text": "Updated banner text — sale extended!",
  "max_redemptions": 1000
}
```

**Response `200`** — updated sale object

---

### `POST /sales/admin/{id}/activate`

Force-start a scheduled sale immediately (moves `start_at` to now).

**Request body:** empty `{}`

**Response `200`**
```json
{
  "...sale object with status: active...",
  "message": "Sale 'World GRM Day Sale' is now active."
}
```

---

### `POST /sales/admin/{id}/end`

Force-stop a running sale immediately (moves `end_at` to now).

**Request body:** empty `{}`

**Response `200`**
```json
{
  "...sale object with status: ended...",
  "message": "Sale 'World GRM Day Sale' ended."
}
```

---

### `POST /sales/admin/{id}/extend`

Extend a sale by hours or to a specific new end date.

```json
{ "hours": 24 }
```
or
```json
{ "end_at": "2026-06-29T23:59:59" }
```

**Response `200`**
```json
{
  "...updated sale object...",
  "message": "Sale extended to 2026-06-29T23:59:59."
}
```

---

### `DELETE /sales/admin/{id}`

Cancel a scheduled or active sale. Cannot cancel an already-ended sale.

**Response `200`**
```json
{ "message": "Sale 'World GRM Day Sale' cancelled.", "id": "uuid" }
```

---

### `GET /sales/admin/{id}/stats`

Redemption count, progress, and time remaining for a sale.

**Auth:** Bearer JWT (admin role required)

**Response `200`**
```json
{
  "id": "uuid",
  "name": "Launch Week Sale",
  "status": "active",
  "redemption_count": 3,
  "max_redemptions": -1,
  "slots_remaining": null,
  "schedule": {
    "start_at": "2026-05-17T00:00:00",
    "end_at": "2026-05-31T23:59:59",
    "progress_pct": 0.9,
    "remaining_secs": 1251478,
    "remaining_human": "14d 3h"
  },
  "discount": {
    "type": "percentage",
    "value": "40",
    "label": "40% off"
  }
}
```

---

## Seeded Sale Campaigns

| Sale | Discount | When | Auto-apply | Targets |
|---|---|---|---|---|
| Launch Week Sale | 40% off | May 17–31 2026 **[ACTIVE NOW]** | ✓ | New subscribers, all plans |
| Mid-Year Sale 2026 | 25% off | June 2026 | ✓ | All orgs, all plans |
| Annual Plan Bonus | 15% off | July–Aug 2026 | ✓ | Annual billing only |
| Black Friday 2026 | 50% off | Nov 27 2026 | ✓ | All orgs, max 1,000 |
| Cyber Monday 2026 | 35% off | Nov 30 2026 | ✓ | Pro & Business |
| New Year 2027 Kickstart | 20% off | Jan 1–14 2027 | ✓ | All orgs, all plans |

---

## Billing Admin

All endpoints under `/billing/*` are for Riviwa platform administrators managing subscriptions on behalf of organisations.

### `GET /billing/metrics`

Platform-wide subscription revenue metrics.

**Auth:** Bearer JWT (admin role required)

**Response `200`**
```json
{
  "mrr_usd": "14750.00",
  "arr_usd": "177000.00",
  "monthly_revenue_usd": "6300.00",
  "active_subscriptions": 42,
  "churn_last_30_days": 2,
  "past_due_count": 1,
  "by_plan": [
    { "slug": "starter",      "display_name": "Starter",      "count": 18, "mrr_usd": "882.00" },
    { "slug": "professional", "display_name": "Professional",  "count": 15, "mrr_usd": "2235.00" },
    { "slug": "business",     "display_name": "Business",      "count": 9,  "mrr_usd": "3591.00" }
  ]
}
```

---

### `GET /billing/promo-codes`

List all promo codes (simple view, no stats).

**Auth:** Bearer JWT (admin role required)

**Query parameters**

| Param | Description |
|---|---|
| `active_only` | `true` to show only active codes |

**Response `200`**
```json
{
  "promo_codes": [
    {
      "id": "uuid",
      "code": "LAUNCH2026",
      "name": "Riviwa Launch Offer",
      "description": "30% off your first 3 months...",
      "discount_type": "percentage",
      "discount_value": "30",
      "duration": "repeating",
      "duration_months": 3,
      "max_redemptions": -1,
      "redemption_count": 2,
      "eligible_plans": null,
      "new_subscribers_only": true,
      "expires_at": "2026-12-31T23:59:59",
      "is_active": true,
      "created_at": "2026-05-17T10:52:47"
    }
  ]
}
```

---

### `POST /billing/promo-codes`

Create a promo code (billing admin route — same as `POST /promotions/admin` but without the stats response).

**Auth:** Bearer JWT (admin role required)

```json
{
  "code": "MINHEALTHTZ30",
  "name": "MoH Tanzania Partner Discount",
  "discount_type": "percentage",
  "discount_value": 30,
  "duration": "forever",
  "max_redemptions": 50,
  "eligible_plans": ["business"],
  "new_subscribers_only": false
}
```

**Response `201`** — promo code object

---

### `PATCH /billing/promo-codes/{id}`

Update a promo code.

```json
{ "max_redemptions": 100, "is_active": true }
```

**Response `200`** — updated promo code object

---

### `POST /billing/subscriptions/{subscription_id}/free-months`

Grant free months to a subscription by extending `current_period_end`.

**Auth:** Bearer JWT (admin role required)

```json
{ "months": 2 }
```

**Response `200`**
```json
{
  "message": "2 free month(s) granted.",
  "new_period_end": "2026-08-17T11:07:28"
}
```

---

### `POST /billing/subscriptions/{subscription_id}/cancel`

Admin cancel of any subscription by ID. Works on active, trialing, or paused subscriptions. If already cancelled, returns the current status without error.

**Auth:** Bearer JWT (admin role required)

```json
{
  "reason": "Account closed by organisation request",
  "immediate": true
}
```

**Response `200`**
```json
{ "message": "Subscription cancelled.", "status": "cancelled" }
```

---

### `GET /billing/subscriptions/{subscription_id}/events`

Subscription audit trail for any org by subscription ID.

**Auth:** Bearer JWT (admin role required)

**Response `200`**
```json
{
  "events": [
    {
      "event_type": "cancelled",
      "actor_type": "admin",
      "metadata": { "reason": "Account closed by organisation request", "immediate": true },
      "created_at": "2026-05-17T11:07:35"
    }
  ]
}
```

---

### `GET /billing/invoices`

List all invoices across all organisations.

**Auth:** Bearer JWT (admin role required)

**Query parameters**

| Param | Description |
|---|---|
| `status` | Filter: `draft`, `open`, `paid`, `void`, `uncollectible` |
| `page` | Page number |
| `size` | Results per page |

**Response `200`**
```json
{
  "total": 15,
  "page": 1,
  "invoices": [
    {
      "id": "uuid",
      "invoice_number": "INV-2026-835389",
      "org_id": "uuid",
      "total_usd": "57.82",
      "status": "open",
      "paid_at": null,
      "created_at": "2026-05-17T11:03:50"
    }
  ]
}
```

---

### `POST /billing/invoices/{invoice_id}/void`

Void an invoice. Once voided, the invoice cannot be paid.

**Auth:** Bearer JWT (admin role required)

**Request body:** empty `{}`

**Response `200`**
```json
{ "message": "Invoice voided.", "invoice_number": "INV-2026-835389" }
```

---

## Error Reference

All errors follow this envelope:

```json
{ "error": "ERROR_CODE", "message": "Human-readable description." }
```

| HTTP | Error Code | Meaning |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Missing or invalid request field |
| `400` | `SUBSCRIPTION_ERROR` | Subscription business rule violation (e.g. upgrade to same plan) |
| `400` | `PROMO_ERROR` | Promo code invalid, expired, exhausted, or already used |
| `401` | `UNAUTHORISED` | Missing or invalid Bearer token |
| `401` | `INVALID_SERVICE_KEY` | Invalid `X-Service-Key` header |
| `402` | `PAYMENT_ERROR` | Payment initiation or gateway failure |
| `403` | `FORBIDDEN` | Token valid but insufficient role |
| `403` | `FEATURE_NOT_AVAILABLE` | Feature not on org's current plan |
| `404` | `NOT_FOUND` | Resource does not exist or belongs to different org |
| `409` | `CONFLICT` | Duplicate slug, code, or org already subscribed |
| `500` | `INTERNAL_ERROR` | Unexpected server error |

---

## Discount Types Reference

| `discount_type` | `discount_value` meaning |
|---|---|
| `percentage` | Percentage off (e.g. `30` = 30%) |
| `fixed_amount` | Fixed USD deduction (e.g. `10` = $10 off) |
| `free_months` | N free months credited (e.g. `1` = 1 free month) |

## Duration Reference

| `duration` | Behaviour |
|---|---|
| `once` | Applied to first payment only |
| `repeating` | Applied for `duration_months` consecutive payments |
| `forever` | Applied every billing cycle permanently |

---

*Riviwa Subscription Service API — generated 2026-05-17*
