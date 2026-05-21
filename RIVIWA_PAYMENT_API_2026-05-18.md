# Riviwa Payment API Reference
**Date:** 2026-05-18  
**Version:** Production

---

## Services

| Service | Internal Port | External Port | Base Path |
|---------|--------------|---------------|-----------|
| **payment_service** | 8040 | 8040 | `/api/v1` |
| **subscription_service** | 8140 | 8140 | `/api/v1` |

All endpoints require a valid JWT in the `Authorization: Bearer <token>` header unless marked **[Public]**.

---

## Authentication Roles

| Role | Who |
|------|-----|
| **Any authenticated user** | Valid JWT (any org_role or platform_role) |
| **Staff** | `org_role` ∈ {`owner`, `admin`, `manager`} OR `platform_role` ∈ {`super_admin`, `admin`, `moderator`} |
| **Platform Admin** | `platform_role` ∈ {`admin`, `super_admin`} |
| **[Public]** | No token required |

---

---

# Part 1 — payment_service (port 8040)

Handles raw payment intents, provider dispatch (AzamPay, M-Pesa, Selcom, Airtel, Yas, PayPal), webhook reconciliation, and outbound Airtel Money disbursements.

---

## Payments

### `POST /api/v1/payments`
**Create a payment intent**  
Creates a new payment record. Does **not** contact any provider — call `/initiate` next.

**Auth:** Any authenticated user

**Request body:**
```json
{
  "payment_type":  "subscription",
  "amount":        127400,
  "currency":      "TZS",
  "phone":         "255712345678",
  "payer_name":    "John Komba",
  "payer_email":   "john@example.com",
  "description":   "Starter plan — monthly",
  "org_id":        "uuid",
  "project_id":    "uuid",
  "reference_id":  "uuid",
  "reference_type": "plan"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `payment_type` | string | Yes | `subscription` \| `grievance_fee` \| `project_contribution` \| `service_fee` \| `refund` |
| `amount` | number | Yes | Amount in TZS (or chosen currency) |
| `currency` | string | No | `TZS` (default) \| `USD` \| `KES` |
| `phone` | string | Yes | E.164 mobile money number |
| `payer_name` | string | No | |
| `payer_email` | string | No | |
| `description` | string | No | |
| `org_id` | UUID | No | Organisation context |
| `project_id` | UUID | No | Project context |
| `reference_id` | UUID | No | ID of the domain object (invoice, plan, etc.) |
| `reference_type` | string | No | `plan` \| `invoice` \| `subproject` \| `feedback` |

**Response `201`:**
```json
{
  "id": "uuid",
  "payment_type": "subscription",
  "amount": 127400,
  "currency": "TZS",
  "status": "pending",
  "external_ref": "RVW-...",
  "payer_user_id": "uuid",
  "payer_phone": "255712345678",
  "org_id": "uuid",
  "reference_id": "uuid",
  "reference_type": "plan",
  "created_at": "2026-05-18T...",
  "expires_at": null,
  "paid_at": null
}
```

---

### `GET /api/v1/payments`
**List payments**

**Auth:** Any authenticated user (non-staff users only see their own payments)

**Query params:**
| Param | Type | Notes |
|-------|------|-------|
| `payer_user_id` | UUID | Staff only — filter by payer |
| `org_id` | UUID | Filter by organisation |
| `project_id` | UUID | Filter by project |
| `reference_id` | UUID | Filter by reference object |
| `status` | string | `pending` \| `initiated` \| `processing` \| `paid` \| `failed` \| `expired` \| `refunded` \| `cancelled` |
| `payment_type` | string | Filter by type |
| `skip` | int | Offset (default 0) |
| `limit` | int | Page size 1–200 (default 50) |

**Response `200`:**
```json
{
  "items": [ { ...payment } ],
  "count": 12
}
```

---

### `GET /api/v1/payments/{payment_id}`
**Payment detail with all transactions**

**Auth:** Any authenticated user

**Response `200`:**
```json
{
  "id": "uuid",
  "status": "paid",
  "transactions": [
    {
      "id": "uuid",
      "provider": "azampay",
      "status": "success",
      "provider_ref": "AZM-...",
      "provider_receipt": "...",
      "settled_amount": 127400,
      "initiated_at": "...",
      "completed_at": "..."
    }
  ]
}
```

---

### `POST /api/v1/payments/{payment_id}/initiate`
**Initiate USSD push via provider**  
Sends the payment request to the chosen provider. The customer receives a USSD prompt on their phone to confirm.

**Auth:** Any authenticated user

**Request body:**
```json
{
  "provider": "azampay"
}
```

| Provider | Network coverage |
|----------|-----------------|
| `azampay` | Airtel TZ, M-Pesa (via AzamPay gateway), CRDB, NMB |
| `selcom` | Tigo Pesa, TTCL Pesa, Halotel |
| `mpesa` | Vodacom M-Pesa TZ (direct) |
| `airtel` | Airtel Money TZ (direct) |
| `yas` | Yas Money TZ (formerly Tigo Pesa direct) |
| `paypal` | PayPal (returns `checkout_url` for redirect) |

**Response `200`:**
```json
{
  "id": "uuid",
  "provider": "azampay",
  "status": "pending",
  "checkout_url": null,
  "message": "Payment request sent. Customer will receive a USSD prompt."
}
```

---

### `POST /api/v1/payments/{payment_id}/verify`
**Poll provider for latest status**  
Re-queries the provider to update the transaction status.

**Auth:** Any authenticated user

**Response `200`:** Transaction object with updated `status`.

---

### `POST /api/v1/payments/{payment_id}/refund`
**Refund a paid payment**

**Auth:** Staff (org owner/admin/manager or platform admin)

**Response `200`:**
```json
{
  "message": "Refund initiated.",
  "status": "reversed"
}
```

---

### `DELETE /api/v1/payments/{payment_id}`
**Cancel a PENDING payment**  
Only works for payments in `pending` status (not yet sent to a provider).

**Auth:** Any authenticated user

**Response `200`:**
```json
{
  "message": "Payment cancelled.",
  "payment_id": "uuid"
}
```

---

### `GET /api/v1/payments/{payment_id}/transactions`
**List all transactions for a payment**

**Auth:** Any authenticated user

**Response `200`:**
```json
{
  "items": [ { ...transaction } ],
  "count": 2
}
```

---

## Disbursements

Outbound Airtel Money payments from the platform to wallets. **Platform Admin / Super Admin only.**

### Lifecycle

```
PENDING → PROCESSING → SUCCESS
                     ↘ FAILED
                     ↘ AMBIGUOUS  (TA — re-enquire after 1 minute)
```

---

### `POST /api/v1/payments/disbursements`
**Create and send an Airtel Money disbursement**

**Auth:** Platform Admin / Super Admin only

**Request body:**
```json
{
  "payee_msisdn":     "756789012",
  "payee_name":       "John Staff Member",
  "amount":           50000,
  "reference":        "STAFF-ALLOWANCE-2026-001",
  "description":      "Monthly field agent allowance",
  "transaction_type": "B2B",
  "org_id":           "uuid",
  "notes":            "Approved by Finance Manager on 2026-05-18"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `payee_msisdn` | string | Yes | Airtel phone WITHOUT country code, e.g. `756789012` |
| `amount` | integer | Yes | Amount in TZS, must be > 0 |
| `reference` | string | Yes | Reference shown on recipient's Airtel receipt |
| `payee_name` | string | No | Recipient display name |
| `description` | string | No | Internal note — not sent to Airtel |
| `transaction_type` | string | No | `B2B` (default) \| `B2C` |
| `org_id` | UUID | No | Org context for reporting |
| `notes` | string | No | Internal admin notes |

**Response `201`:**
```json
{
  "id": "uuid",
  "payee_msisdn": "756789012",
  "payee_name": "John Staff Member",
  "amount": 50000.0,
  "currency": "TZS",
  "reference": "STAFF-ALLOWANCE-2026-001",
  "transaction_type": "B2B",
  "status": "processing",
  "our_transaction_id": "RVW-DSB-26AA2253148C4170",
  "airtel_money_id": "MP...",
  "airtel_reference_id": "...",
  "failure_reason": null,
  "initiated_by": "uuid",
  "org_id": "uuid",
  "notes": "...",
  "created_at": "...",
  "completed_at": null
}
```

**Errors:**
| Code | Error | Reason |
|------|-------|--------|
| 403 | FORBIDDEN | Not platform admin |
| 422 | validation | Missing `payee_msisdn`, `amount`, `reference`, or invalid `transaction_type` |

> **Note:** Requires `AIRTEL_DISBURSEMENT_PIN` and `AIRTEL_PUBLIC_KEY` set in `payment/.env`.

---

### `GET /api/v1/payments/disbursements`
**List disbursements**

**Auth:** Platform Admin / Super Admin only

**Query params:**
| Param | Notes |
|-------|-------|
| `status` | `pending` \| `processing` \| `success` \| `failed` \| `ambiguous` \| `cancelled` |
| `org_id` | Filter by organisation |
| `transaction_type` | `B2B` \| `B2C` |
| `page` | Page number (default 1) |
| `size` | Page size 1–100 (default 20) |

**Response `200`:**
```json
{
  "total": 15,
  "page": 1,
  "size": 20,
  "items": [ { ...disbursement } ]
}
```

---

### `GET /api/v1/payments/disbursements/{id}`
**Get a single disbursement**

**Auth:** Platform Admin / Super Admin only

**Response `200`:** Full disbursement object.  
**Response `404`:** `DISBURSEMENT_NOT_FOUND`

---

### `POST /api/v1/payments/disbursements/{id}/enquiry`
**Poll Airtel for latest disbursement status**  
Queries Airtel's `GET /standard/v2/disbursements/{id}` endpoint. Useful for resolving `AMBIGUOUS` (`TA`) and `PROCESSING` (`TIP`) states.

**Auth:** Platform Admin / Super Admin only

> **Wait at least 1 minute** after creating a disbursement before calling enquiry.

**Response `200`:** Updated disbursement object. If already in a terminal state, includes `"note": "Already in terminal state: success"`.  
**Response `502`:** `AIRTEL_ENQUIRY_FAILED` — Airtel API error.

---

### `DELETE /api/v1/payments/disbursements/{id}`
**Cancel a PENDING disbursement**  
Only disbursements with `status=pending` can be cancelled. Once `PROCESSING` or later, contact Airtel support for reversal.

**Auth:** Platform Admin / Super Admin only

**Response `200`:**
```json
{
  "message": "Disbursement cancelled.",
  "id": "uuid",
  "status": "cancelled"
}
```

**Response `409`:** `CANNOT_CANCEL` — disbursement is not in `pending` state.

---

## Webhooks

Inbound callbacks from payment gateways. All webhook endpoints are excluded from API docs (`include_in_schema=False`) and receive raw payloads before any processing.

| Endpoint | Provider | Notes |
|----------|----------|-------|
| `POST /api/v1/webhooks/azampay` | AzamPay | Standard callback |
| `POST /api/v1/webhooks/selcom` | Selcom | HMAC-SHA256 signature verified if `SELCOM_API_SECRET` is set |
| `POST /api/v1/webhooks/mpesa` | Vodacom M-Pesa | Returns `output_ResponseCode: INS-0` |
| `POST /api/v1/webhooks/airtel` | Airtel Money | Optional HMAC-SHA256 hash if `AIRTEL_CLIENT_SECRET` set |
| `POST /api/v1/webhooks/yas` | Yas Money | Maps `reference` field to transaction |
| `POST /api/v1/webhooks/paypal` | PayPal | Handles `PAYMENT.CAPTURE.COMPLETED` and `CHECKOUT.ORDER.APPROVED` |
| `GET /api/v1/webhooks/paypal/return` | PayPal | Return URL after user approves; captures order |
| `GET /api/v1/webhooks/paypal/cancel` | PayPal | Redirect to cancellation page |

All webhook endpoints return `{"status": "received"}` immediately — processing is asynchronous.

---

---

# Part 2 — subscription_service (port 8140)

Manages subscription plans, trials, billing cycles, invoices, promo codes, and sale campaigns.

---

## Plans

### `GET /api/v1/plans`  
**[Public]** List all active plans

**Query params:**
| Param | Notes |
|-------|-------|
| `active_only` | bool (default true) |
| `include_features` | bool — include feature breakdown |
| `include_addons` | bool — include add-on catalogue |

**Response `200`:**
```json
{
  "plans": [
    {
      "id": "uuid",
      "slug": "starter",
      "display_name": "Starter",
      "tagline": "...",
      "pricing": {
        "monthly_usd": "49.00",
        "annual_usd": "39.00",
        "annual_total_usd": "468.00",
        "monthly_tzs": 127400,
        "annual_tzs": 101400,
        "annual_savings_pct": 20,
        "is_custom": false,
        "trial_days": 14
      },
      "limits": {
        "team_members": 10,
        "projects": 5,
        "submissions_per_month": 1000,
        "sms_per_month": 500,
        "api_calls_per_month": 5000,
        "storage_gb": 10,
        "qr_per_month": 100,
        "staff_profiles": 50
      },
      "features": { "sms_channel": true, "ai_conversation": false, ... },
      "is_popular": false
    }
  ]
}
```

---

### `GET /api/v1/plans/{slug}`  
**[Public]** Get plan detail by slug

**Path param:** `slug` — e.g. `starter`, `professional`, `business`, `enterprise`

**Response `200`:** Full plan object with features and add-ons.

---

### `GET /api/v1/plans/features`  
**[Public]** Feature catalogue — all features in the platform, grouped by service category

**Response `200`:**
```json
{
  "features": [
    {
      "key": "sms_channel",
      "category": "Feedback Channels",
      "label": "SMS Channel",
      "description": "...",
      "service": "feedback_service"
    }
  ]
}
```

---

### `POST /api/v1/plans/admin`
**Admin: create a new plan**

**Auth:** Platform Admin

**Request body:** All Plan model fields (`slug`, `display_name`, `monthly_price_usd`, feature flags, limits, etc.)

---

### `PATCH /api/v1/plans/admin/{plan_id}`
**Admin: update any plan field**

**Auth:** Platform Admin

**Request body:** Any subset of plan fields. `id`, `slug`, `created_at` are immutable.

---

### `PATCH /api/v1/plans/admin/{plan_id}/pricing`
**Admin: update plan pricing**

**Auth:** Platform Admin

**Request body:**
```json
{
  "monthly_price_usd": "49.00",
  "annual_price_usd":  "39.00",
  "is_custom":         false,
  "trial_days":        14
}
```

---

### `PATCH /api/v1/plans/admin/{plan_id}/limits`
**Admin: update usage limits for a plan**  
Use `-1` for unlimited.

**Auth:** Platform Admin

**Request body:**
```json
{
  "max_team_members": 25,
  "max_projects": 15,
  "max_submissions_per_month": 5000,
  "max_sms_per_month": 2000,
  "max_api_calls_per_month": 10000,
  "max_storage_gb": 25,
  "max_qr_per_month": 500,
  "max_staff_profiles": 100
}
```

---

### `PATCH /api/v1/plans/admin/{plan_id}/features`
**Admin: toggle features on/off for a plan**

**Auth:** Platform Admin

**Request body:**
```json
{
  "ai_conversation": true,
  "phone_call_ai": false,
  "webhooks": true
}
```

All available feature keys: `GET /api/v1/plans/features`

---

## Subscriptions

### `POST /api/v1/subscriptions/trial`
**Start a free trial**  
Called automatically on first org creation, or explicitly by the org admin.

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{
  "plan_slug": "professional"
}
```

**Response `201`:**
```json
{
  "subscription": { ...sub },
  "message": "14-day free trial started on Professional.",
  "trial_end": "2026-06-01T..."
}
```

---

### `GET /api/v1/subscriptions/current`
**Get organisation's current subscription with usage**

**Auth:** Any authenticated user (org context required)

**Response `200`:**
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
    "current_period_start": "...",
    "current_period_end": "...",
    "trial_end": null,
    "cancel_at_period_end": false,
    "discount_pct": "0",
    "effective_monthly_usd": "149.00"
  },
  "usage": {
    "submissions":   { "used": 342, "limit": 5000 },
    "sms":           { "used": 120, "limit": 2000 },
    "api_calls":     { "used": 1800, "limit": 10000 },
    "storage_bytes": { "used": 2048000, "limit": 26843545600 },
    "qr_codes":      { "used": 45, "limit": 500 },
    "team_members":  { "used": 8, "limit": 25 }
  }
}
```

---

### `POST /api/v1/subscriptions/upgrade`
**Upgrade to a higher plan**

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{ "plan_id": "uuid" }
```

---

### `POST /api/v1/subscriptions/downgrade`
**Downgrade to a lower plan**  
Takes effect at end of current billing period.

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{ "plan_id": "uuid" }
```

---

### `POST /api/v1/subscriptions/cancel`
**Cancel subscription**

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{
  "reason":    "Switching to competitor",
  "immediate": false
}
```

`immediate: false` (default) — cancels at period end.  
`immediate: true` — cancels right now.

---

### `POST /api/v1/subscriptions/pause`
**Pause subscription (Business / Enterprise only)**  
Pauses billing for 1–3 months.

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{ "months": 2 }
```

---

### `POST /api/v1/subscriptions/resume`
**Resume a paused subscription**

**Auth:** Any authenticated user (org context required)

---

### `POST /api/v1/subscriptions/switch-billing-cycle`
**Switch between monthly and annual billing**

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{ "billing_cycle": "annual" }
```

- **monthly → annual:** Charged the prorated annual price immediately. Annual is ~20% cheaper.
- **annual → monthly:** Takes effect at next renewal. No refund.

**Response `200`:**
```json
{
  "subscription": { ... },
  "message": "Switched to annual billing. Invoice generated.",
  "amount_due_usd": "468.00",
  "invoice_number": "INV-2026-...",
  "new_period_end": "...",
  "annual_savings_pct": 20
}
```

---

### `POST /api/v1/subscriptions/billing-preview`
**Preview exact cost before subscribing or changing plan**  
Calculates the exact price with promo code and add-ons applied.

**Auth:** None required

**Request body:**
```json
{
  "plan_id":       "uuid",
  "billing_cycle": "monthly",
  "promo_code":    "RIVIWA50",
  "addons": [
    { "slug": "extra-sms-1k", "quantity": 2 }
  ]
}
```

**Response `200`:**
```json
{
  "plan": { "slug": "professional", "display_name": "Professional" },
  "billing_cycle": "monthly",
  "line_items": [
    { "description": "Professional — Monthly",     "amount_usd": "149.00" },
    { "description": "Promo: Summer Sale",         "amount_usd": "-74.50" },
    { "description": "Extra SMS 1K × 2",           "amount_usd": "10.00" },
    { "description": "VAT (18%)",                  "amount_usd": "15.21" }
  ],
  "summary": {
    "subtotal_usd":    "159.00",
    "discount_usd":    "74.50",
    "addon_total_usd": "10.00",
    "tax_usd":         "15.21",
    "total_usd":       "99.71"
  },
  "promo": { "code": "RIVIWA50", "label": "50% off", "duration": "once" },
  "trial_days": 14
}
```

---

### `POST /api/v1/subscriptions/apply-promo`
**Apply a promo code to an existing subscription**

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{ "code": "REVIWA50" }
```

---

### `GET /api/v1/subscriptions/invoices`
**List organisation invoices**

**Auth:** Any authenticated user (org context required)

**Query params:** `page`, `size`

---

### `GET /api/v1/subscriptions/invoices/{invoice_id}`
**Get invoice detail**

**Auth:** Any authenticated user (org context required)

---

### `GET /api/v1/subscriptions/payment-methods`
**List saved payment methods**

**Auth:** Any authenticated user (org context required)

---

### `POST /api/v1/subscriptions/payment-methods`
**Add a payment method**

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{
  "type":         "mpesa",
  "phone_number": "+255712345678",
  "display_name": "John Komba",
  "is_default":   true
}
```

---

### `DELETE /api/v1/subscriptions/payment-methods/{method_id}`
**Remove a payment method**

**Auth:** Any authenticated user (org context required)

---

### `GET /api/v1/subscriptions/events`
**Subscription audit history** (last 50 events)

**Auth:** Any authenticated user (org context required)

---

### `GET /api/v1/subscriptions/internal/feature-check`
**Internal: check if an org has access to a feature**

**Auth:** Internal service key (`X-Service-Key` header)

**Query params:** `org_id`, `feature`

**Response `200`:**
```json
{
  "org_id": "uuid",
  "feature": "ai_conversation",
  "has_access": true,
  "limits": { "max_team_members": 25, ... }
}
```

---

### `GET /api/v1/subscriptions/admin/all`
**Admin: list all subscriptions**

**Auth:** Platform Admin

**Query params:** `status`, `page`, `size`

---

### `PATCH /api/v1/subscriptions/admin/{subscription_id}`
**Admin: override any subscription field**

**Auth:** Platform Admin

**Allowed fields:** `status`, `plan_id`, `billing_cycle`, `cancel_at_period_end`, `discount_pct`, `discount_months_remaining`, `current_period_end`

---

## Checkout

### `POST /api/v1/checkout`
**Subscribe to a plan — full checkout flow**  
Creates subscription + invoice, delegates payment to payment_service, and initiates with the provider.

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{
  "plan_id":       "uuid",
  "billing_cycle": "monthly",
  "provider":      "mpesa",
  "phone_number":  "+255712345678",
  "payer_name":    "John Komba",
  "payer_email":   "john@example.com",
  "promo_code":    "RIVIWA50",
  "save_method":   true
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `plan_id` | UUID | Yes | |
| `billing_cycle` | string | No | `monthly` (default) \| `annual` |
| `provider` | string | No | `mpesa` \| `azampay` \| `selcom` \| `airtel` \| `yas` \| `paypal` \| `bank_transfer` (default) |
| `phone_number` | string | Required for mobile money | E.164 format |
| `payer_name` | string | No | |
| `payer_email` | string | No | |
| `promo_code` | string | No | If not provided, best active auto-apply sale is used automatically |
| `save_method` | bool | No | Save payment method for future renewals |

**Response `201` (mobile money):**
```json
{
  "subscription_id": "uuid",
  "status": "trialing",
  "payment_id": "uuid",
  "invoice": {
    "invoice_number": "INV-2026-...",
    "total_usd": "149.00",
    "status": "pending",
    "due_date": "..."
  },
  "checkout_url": null,
  "payment": {
    "provider": "mpesa",
    "status": "pending",
    "message": "USSD prompt sent to your phone. Enter your PIN to complete payment."
  },
  "next_renewal": "2026-06-18T..."
}
```

**Response `201` (bank_transfer):**
```json
{
  "payment": {
    "provider": "bank_transfer",
    "instructions": "Transfer USD 149.00 to Riviwa. Reference: INV-2026-...",
  }
}
```

**Response `201` (PayPal):**
```json
{
  "checkout_url": "https://www.paypal.com/checkoutnow?token=...",
  "message": "Redirecting to PayPal for payment."
}
```

---

### `GET /api/v1/checkout/status/{payment_id}`
**Check payment status and activate subscription on success**

**Auth:** Any authenticated user (org context required)

**Response `200`:**
```json
{
  "payment_id": "uuid",
  "payment_status": "paid",
  "paid": true,
  "subscription_active": true
}
```

---

### `POST /api/v1/checkout/pay-invoice/{invoice_id}`
**Pay an outstanding (unpaid) invoice**

**Auth:** Any authenticated user (org context required)

**Request body:**
```json
{
  "provider":     "mpesa",
  "phone_number": "+255712345678"
}
```

---

## Promotions

### `GET /api/v1/promotions`  
**[Public]** Active promotions — safe for pricing page banners  
Does NOT expose promo codes. Codes are revealed at checkout or sent via email.

**Query params:** `plan_slug` — filter by eligible plan

**Response `200`:**
```json
{
  "promotions": [
    {
      "name": "Early Adopter Discount",
      "description": "50% off your first 3 months",
      "discount_label": "50% off",
      "duration_label": "first 3 month(s)",
      "eligible_plans": "all",
      "expires_at": "2026-12-31T...",
      "new_subscribers_only": true
    }
  ],
  "total": 1
}
```

---

### `POST /api/v1/promotions/validate`  
**[Public]** Validate a promo code and preview the discount  
Does NOT apply the code — safe to call during checkout.

**Request body:**
```json
{
  "code":          "RIVIWA50",
  "plan_id":       "uuid",
  "billing_cycle": "monthly",
  "org_id":        "uuid"
}
```

**Response `200` (valid):**
```json
{
  "valid": true,
  "code": "RIVIWA50",
  "discount_label": "50% off",
  "duration_label": "first payment",
  "pricing_preview": {
    "base_price_usd":  "149.00",
    "discount_usd":    "74.50",
    "final_price_usd": "74.50",
    "billing_cycle":   "monthly",
    "plan":            "Professional"
  }
}
```

**Response `200` (invalid):**
```json
{ "valid": false, "reason": "This promo code has expired." }
```

---

### `GET /api/v1/promotions/admin`
**Admin: list all promo codes with stats**

**Auth:** Platform Admin

**Query params:** `active_only`, `discount_type`, `plan_slug`, `page`, `size`

---

### `GET /api/v1/promotions/admin/{promo_id}`
**Admin: promo code detail with full stats and recent redemptions**

**Auth:** Platform Admin

---

### `POST /api/v1/promotions/admin`
**Admin: create a promo code**

**Auth:** Platform Admin

**Request body:**
```json
{
  "code":                 "LAUNCH50",
  "name":                 "Launch Offer",
  "description":          "50% off for new subscribers",
  "discount_type":        "percentage",
  "discount_value":       50,
  "duration":             "repeating",
  "duration_months":      3,
  "max_redemptions":      500,
  "eligible_plans":       ["professional", "business"],
  "new_subscribers_only": true,
  "expires_at":           "2026-12-31T23:59:59"
}
```

| `discount_type` | Meaning |
|----------------|---------|
| `percentage` | `discount_value` = 50 → 50% off |
| `fixed_amount` | `discount_value` = 20 → $20 off |
| `free_months` | `discount_value` = 1 → 1 free month |

| `duration` | Applies to |
|-----------|-----------|
| `once` | First payment only |
| `repeating` | First `duration_months` payments |
| `forever` | Every billing cycle permanently |

---

### `PATCH /api/v1/promotions/admin/{promo_id}`
**Admin: update a promo code**

**Auth:** Platform Admin  
`id`, `code`, `created_at`, `redemption_count` are immutable.

---

### `DELETE /api/v1/promotions/admin/{promo_id}`
**Admin: deactivate a promo code**

**Auth:** Platform Admin

---

### `POST /api/v1/promotions/admin/bulk-generate`
**Admin: generate multiple unique promo codes** (max 500 at a time)

**Auth:** Platform Admin

**Request body:**
```json
{
  "prefix":              "NGO",
  "count":               100,
  "discount_type":       "percentage",
  "discount_value":      30,
  "duration":            "once",
  "eligible_plans":      ["professional", "business"],
  "new_subscribers_only": true,
  "expires_at":          "2026-12-31T23:59:59",
  "name_prefix":         "NGO Partner Code"
}
```

Each generated code is single-use (`max_redemptions=1`). Format: `NGO-XXXXXX`.

---

### `GET /api/v1/promotions/admin/stats/summary`
**Admin: promotions revenue impact summary**

**Auth:** Platform Admin

Returns total codes, active codes, redemption counts, top 5 most redeemed codes, and codes expiring in the next 7 days.

---

## Sales Campaigns

Time-bounded sale campaigns with scheduling, auto-apply, and countdown timers.

### `GET /api/v1/sales`  
**[Public]** Active and upcoming sales

**Query params:**
| Param | Notes |
|-------|-------|
| `plan_slug` | Filter by eligible plan |
| `cycle` | `monthly` \| `annual` |
| `include_upcoming` | bool — include scheduled future sales (default true) |

**Response `200`:**
```json
{
  "active_sales": [
    {
      "id": "uuid",
      "name": "Flash Friday",
      "banner_text": "⚡ Flash Sale — 40% off ends tonight!",
      "status": "active",
      "schedule": {
        "start_at": "...",
        "end_at": "...",
        "remaining_secs": 43200,
        "duration_hours": 24
      },
      "discount": {
        "type":  "percentage",
        "value": "40",
        "label": "40% off"
      },
      "auto_apply": true,
      "is_active": true
    }
  ],
  "upcoming_sales": [ ... ],
  "has_active_sale": true
}
```

---

### `GET /api/v1/sales/current`  
**[Public]** Best active sale for a given plan — used by checkout to auto-apply

**Query params:** `plan_slug`, `cycle`

**Response `200`:**
```json
{
  "sale": { ...sale },
  "has_sale": true
}
```

---

### `GET /api/v1/sales/{sale_id}`  
**[Public]** Get sale detail

---

### `GET /api/v1/sales/admin/all`
**Admin: list all sales by status**

**Auth:** Platform Admin

**Query params:** `status` (`scheduled` \| `active` \| `ended` \| `cancelled`), `page`, `size`

---

### `POST /api/v1/sales/admin`
**Admin: create a sale campaign**

**Auth:** Platform Admin

**Request body:**
```json
{
  "name":            "Flash Friday",
  "description":     "24-hour flash sale",
  "banner_text":     "⚡ Flash Sale — 40% off ends tonight!",
  "start_at":        "2026-06-01T00:00:00",
  "end_at":          "2026-06-01T23:59:59",
  "discount_type":   "percentage",
  "discount_value":  40,
  "duration":        "once",
  "eligible_plans":  ["professional", "business"],
  "eligible_billing_cycles": ["monthly", "annual"],
  "new_subscribers_only": false,
  "max_redemptions": -1,
  "auto_apply":      true,
  "generate_code":   true,
  "code_prefix":     "FLASH"
}
```

`generate_code: true` auto-creates a shareable promo code (e.g. `FLASH-X7KP9Q`).

---

### `PATCH /api/v1/sales/admin/{sale_id}`
**Admin: update a sale** (cannot update ended sales)

**Auth:** Platform Admin

---

### `POST /api/v1/sales/admin/{sale_id}/activate`
**Admin: manually activate a sale immediately**  
Force-starts a scheduled sale by moving `start_at` to now.

**Auth:** Platform Admin

---

### `POST /api/v1/sales/admin/{sale_id}/end`
**Admin: manually end a sale immediately**  
Force-stops a running sale by moving `end_at` to now.

**Auth:** Platform Admin

---

### `DELETE /api/v1/sales/admin/{sale_id}`
**Admin: cancel a sale**

**Auth:** Platform Admin

---

### `POST /api/v1/sales/admin/{sale_id}/extend`
**Admin: extend a sale's end date**

**Auth:** Platform Admin

**Request body:**
```json
{ "hours": 24 }
```
or
```json
{ "end_at": "2026-06-10T23:59:59" }
```

---

### `GET /api/v1/sales/admin/{sale_id}/stats`
**Admin: sale performance stats**  
Redemption count, max redemptions, time remaining, progress percentage.

**Auth:** Platform Admin

---

## Admin — Billing Management

Prefix: `/api/v1/billing`  
All endpoints require Platform Admin.

---

### `GET /api/v1/billing/metrics`
**Platform-wide subscription metrics**

Returns MRR, ARR, monthly revenue, active subscriptions, churn count (last 30 days), past-due count, and breakdown by plan.

**Response `200`:**
```json
{
  "mrr_usd": "14900.00",
  "arr_usd": "178800.00",
  "monthly_revenue_usd": "14900.00",
  "active_subscriptions": 100,
  "churn_last_30_days": 3,
  "past_due_count": 2,
  "by_plan": [
    { "slug": "professional", "display_name": "Professional", "count": 60, "mrr_usd": "8940.00" }
  ]
}
```

---

### `GET /api/v1/billing/promo-codes`
**List promo codes** (billing-admin alias)

**Query params:** `active_only`

---

### `POST /api/v1/billing/promo-codes`
**Create a promo code** (billing-admin alias)

---

### `PATCH /api/v1/billing/promo-codes/{promo_id}`
**Update a promo code** (billing-admin alias)

---

### `POST /api/v1/billing/subscriptions/{subscription_id}/free-months`
**Grant free months to an org**

**Request body:**
```json
{ "months": 2 }
```

---

### `POST /api/v1/billing/subscriptions/{subscription_id}/cancel`
**Admin: cancel a subscription on behalf of an org**

**Request body:**
```json
{
  "immediate": true,
  "reason":    "Payment dispute"
}
```

---

### `GET /api/v1/billing/subscriptions/{subscription_id}/events`
**Subscription audit trail**

---

### `GET /api/v1/billing/invoices`
**Admin: list all invoices across all orgs**

**Query params:** `status` (`pending` \| `paid` \| `void`), `page`, `size`

---

### `POST /api/v1/billing/invoices/{invoice_id}/void`
**Admin: void an invoice**

---

---

## Subscription Statuses

| Status | Meaning |
|--------|---------|
| `trialing` | Free trial active |
| `active` | Paid and active |
| `past_due` | Payment missed; grace period |
| `paused` | Billing paused (1–3 months) |
| `cancelled` | Cancelled by org or admin |
| `expired` | Trial or subscription ended without renewal |

## Payment Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Created, not yet sent to provider |
| `initiated` | Sent to provider, awaiting customer action |
| `processing` | Customer actioned, provider processing |
| `paid` | Confirmed paid |
| `failed` | Provider rejected |
| `expired` | Timed out with no action |
| `refunded` | Money returned to payer |
| `cancelled` | Cancelled before initiation |

## Disbursement Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Created, not yet sent to Airtel |
| `processing` | Sent to Airtel (`TIP`) |
| `success` | Airtel confirmed delivery (`TS`) |
| `failed` | Airtel rejected (`TF`) |
| `ambiguous` | Unclear state (`TA`) — re-enquire after 1 min |
| `cancelled` | Cancelled before sending |

---

## Pricing (Live — 2026-05-18)

| Plan | Monthly (USD) | Monthly (TZS) | Annual/mo (USD) | Annual/mo (TZS) | Annual savings |
|------|--------------|---------------|-----------------|-----------------|----------------|
| Starter | $49.00 | 127,400 | $39.00 | 101,400 | 20% |
| Professional | $149.00 | 387,400 | $119.00 | 309,400 | 20% |
| Business | $399.00 | 1,037,400 | $319.00 | 829,400 | 20% |
| Enterprise | Custom | Custom | Custom | Custom | Negotiable |

**Conversion rate:** 1 USD = 2,600 TZS  
**VAT:** 18% added at checkout
