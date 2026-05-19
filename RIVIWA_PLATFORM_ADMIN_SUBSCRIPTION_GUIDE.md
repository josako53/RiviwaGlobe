# Riviwa — Platform Admin: Subscription, Plans & Billing Management Guide
**For:** Riviwa platform operators, super_admins, billing team  
**Date:** 2026-05-19  
**Base URL:** `https://api.riviwa.com`  
**Scope:** All endpoints that manage the subscription infrastructure itself — plans, pricing, features, promo codes, sales campaigns, org-level overrides, KYC review, and billing metrics.

---

## Authentication

All endpoints in this guide require a platform admin JWT. The token must carry `platform_role: super_admin` or `platform_role: admin`.

```
Authorization: Bearer <admin_access_token>
```

Get a platform admin token exactly like a regular user:
```
Step 1 — POST /api/v1/auth/login          → returns login_token
Step 2 — POST /api/v1/auth/login/verify-otp  → returns access_token  ← use this everywhere
```

---

## Services and base paths

| Group | Base path | Service port |
|-------|-----------|-------------|
| Plan & Add-on CRUD | `/api/v1/plans/...` | subscription_service :8140 |
| Billing dashboard | `/api/v1/billing/...` | subscription_service :8140 |
| Org subscription overrides | `/api/v1/subscriptions/admin/...` | subscription_service :8140 |
| Promo code management | `/api/v1/promotions/admin/...` | subscription_service :8140 |
| Sales campaigns | `/api/v1/sales/admin/...` | subscription_service :8140 |
| KYC review | `/api/v1/admin/kyc/...` | auth_service :8000 |
| Platform metrics | `/api/v1/admin/platform/...` | auth_service :8000 |

---

---

# Step-by-Step Workflows

The sections below show the correct **order of operations** for every major admin task. Each step feeds output into the next.

---

## Workflow 1 — Create a New Plan from Scratch

Use this when adding a custom plan for an NGO programme, government contract, white-label client, or new product tier.

```
STEP 1 — Review existing plans
  GET /api/v1/plans/admin/plans
  → Note the IDs of existing plans (starter, professional, business, enterprise)
  → Check sort_order values so you know where to insert the new plan

STEP 2 — Review available feature keys
  GET /api/v1/plans/features
  → Returns all 46 feature keys with descriptions and service attribution
  → Save the keys you want to enable on the new plan

STEP 3 — Create the plan (starts inactive and unpublished)
  POST /api/v1/plans/admin/plans
  → Body: slug, display_name, pricing, limits, feature flags (see template below)
  → Response: { "id": "new-plan-uuid", "is_active": false, "is_public": false }
  → SAVE the returned plan ID — you need it in every subsequent step

STEP 4 — Fine-tune pricing (optional, can be done in Step 3 body too)
  PATCH /api/v1/plans/admin/plans/{plan_id}/pricing
  → Set monthly_price_usd, annual_price_usd, trial_days, uptime_sla

STEP 5 — Fine-tune usage limits
  PATCH /api/v1/plans/admin/plans/{plan_id}/limits
  → Set max_team_members, max_projects, max_submissions_per_month,
    max_sms_per_month, max_api_calls_per_month, max_storage_gb,
    max_qr_per_month, max_staff_profiles
  → Use -1 for unlimited

STEP 6 — Fine-tune feature flags
  PATCH /api/v1/plans/admin/plans/{plan_id}/features
  → Body: { "feature_key": true/false, ... }
  → Response confirms changed features and full feature snapshot

STEP 7 — Review the complete plan before going live
  GET /api/v1/plans/admin/plans  (or GET /api/v1/plans/{plan_id})
  → Verify pricing, limits, and all feature flags look correct

STEP 8 — Publish
  PATCH /api/v1/plans/admin/plans/{plan_id}/publish
  → Body: { "is_public": true, "is_active": true }
  → Plan now appears on GET /api/v1/plans (public pricing page)
```

**Tip — Clone an existing plan instead of building from scratch:**
```
STEP 3 (alternative) — Duplicate closest matching plan
  POST /api/v1/plans/admin/plans/{source_plan_id}/duplicate
  → Body: { "slug": "ngo-business", "display_name": "Business NGO", "monthly_price_usd": "74.50" }
  → All features/limits copied from source. Starts inactive/unpublished.
  → Then run Steps 4–8 above to adjust the clone.
```

**Full create body template:**
```json
POST /api/v1/plans/admin/plans
{
  "slug":         "ngo-custom",
  "display_name": "NGO Custom",
  "tagline":      "For registered NGOs — subsidised pricing",
  "description":  "Professional features at 50% off for verified NGOs and CBOs.",
  "monthly_price_usd": "24.50",
  "annual_price_usd":  "19.50",
  "trial_days":   14,
  "sort_order":   5,
  "is_custom":    false,

  "max_team_members":          25,
  "max_projects":              15,
  "max_submissions_per_month": 5000,
  "max_sms_per_month":         4000,
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
  "has_api_access":         true,
  "has_oauth2":             true,
  "has_widget_embed":       true,
  "has_advanced_analytics": true,
  "has_fraud_detection":    true,
  "has_social_login":       true,
  "has_multi_org":          true,
  "has_2fa":                true
}
```

---

## Workflow 2 — Update an Existing Plan's Pricing

Use this when adjusting prices for an existing plan (e.g., inflation adjustment, new market entry pricing).

```
STEP 1 — Get the plan ID
  GET /api/v1/plans/admin/plans
  → Find the plan by slug, note its "id"

STEP 2 — Update pricing
  PATCH /api/v1/plans/admin/plans/{plan_id}/pricing
  → Body: { "monthly_price_usd": "19.00", "annual_price_usd": "15.00" }
  → Response confirms new pricing

STEP 3 — Verify
  GET /api/v1/plans/{plan_id}
  → Confirm pricing.monthly_usd shows the new value
```

> **Important:** Changing plan pricing does NOT affect existing subscribers. They keep their locked `effective_monthly_usd` from the time they subscribed. Only new checkouts use the updated price. To change what an existing org pays, use `PATCH /subscriptions/admin/{subscription_id}` with `discount_pct` or extend their period.

---

## Workflow 3 — Toggle a Feature On/Off for a Plan

Use this when a new Riviwa service goes live and you want to enable it on specific plans.

```
STEP 1 — Check the feature key
  GET /api/v1/plans/features
  → Find the exact "key" value for the feature (e.g., "waiting_queue", "phone_call_ai")

STEP 2 — Get the plan ID
  GET /api/v1/plans/admin/plans
  → Note the plan's "id"

STEP 3 — Toggle the feature
  PATCH /api/v1/plans/admin/plans/{plan_id}/features
  → Body: { "waiting_queue": true }
  → Response: features_changed confirms the change; full features snapshot included

STEP 4 — Verify
  GET /api/v1/plans/{plan_id}
  → features.waiting_queue should be true
```

> **Effect is immediate** — every org on this plan can now access the feature. If you want to enable it for only one org without changing the plan, use Workflow 7 (per-org override) instead.

---

## Workflow 4 — Create a Promo Code

Use this for partner deals, hospital discounts, NGO programmes, referral campaigns.

```
STEP 1 — Create the code
  POST /api/v1/promotions/admin
  → Body: code, discount_type, discount_value, duration, eligible_plans, expires_at
  → Response: { "id": "promo-uuid", "code": "HOSPITAL30", "is_active": true }

STEP 2 — (Optional) Test validation before giving it to users
  POST /api/v1/promotions/validate
  → Body: { "code": "HOSPITAL30", "plan_slug": "business", "org_id": "any-test-org-id" }
  → Response: { "valid": true, "discount_label": "30% off for 6 months" }

STEP 3 — Share the code
  → Give the code to the org/partner. They enter it at checkout.
  → Frontend calls POST /promotions/validate first to show discount preview,
    then includes "promo_code" in POST /checkout/initiate body.

STEP 4 — Monitor usage
  GET /api/v1/promotions/admin/stats/summary
  → See total redemptions across all codes
  
  GET /api/v1/promotions/admin/{promo_id}
  → See usage for this specific code

STEP 5 — Update if needed
  PATCH /api/v1/promotions/admin/{promo_id}
  → Extend expires_at, raise max_redemptions, activate/deactivate

STEP 6 — Deactivate when done
  DELETE /api/v1/promotions/admin/{promo_id}
```

**Promo code field reference:**

| Field | Values | Notes |
|-------|--------|-------|
| `discount_type` | `percentage`, `fixed_amount`, `free_months` | Type of discount |
| `duration` | `once`, `repeating`, `forever` | `once` = first payment only |
| `duration_months` | integer | How many months for `repeating` |
| `max_redemptions` | integer, `-1` = unlimited | Total uses allowed |
| `eligible_plans` | `["starter"]` or `null` (all plans) | Restrict to specific plans |
| `new_subscribers_only` | `true`/`false` | Only first-time subscribers |

---

## Workflow 5 — Run a Sales Campaign (Auto-Apply Discount)

Sales campaigns auto-apply at checkout — no code needed. Used for launch week, Black Friday, flash sales.

```
STEP 1 — Create the campaign (can be done weeks in advance)
  POST /api/v1/sales/admin
  → Body: name, banner_text, start_at, end_at, discount_type, discount_value,
           eligible_plans, new_subscribers_only, max_redemptions, auto_apply: true
  → Response: { "id": "sale-uuid", "status": "scheduled" }

  Status is computed automatically:
    - "scheduled" when start_at is in the future
    - "active"    between start_at and end_at
    - "ended"     after end_at passes
    - "cancelled" if manually stopped

STEP 2 — Verify the campaign appears on public checkout
  GET /api/v1/checkout/active-sale   ← public endpoint, no auth
  → Response shows active campaign banner and discount details

STEP 3 — Monitor redemptions during the campaign
  GET /api/v1/sales/admin/{sale_id}/stats
  → { "status": "active", "redemption_count": 23, "remaining_hours": 48.5 }

STEP 4a — End the campaign early (if needed)
  POST /api/v1/sales/admin/{sale_id}/end
  → Stops immediately regardless of end_at

STEP 4b — Extend if it's performing well
  POST /api/v1/sales/admin/{sale_id}/extend
  → Body: { "new_end_at": "2026-06-07T23:59:59" }

STEP 5 — Campaign ends automatically at end_at (no action needed)
```

**Banner text tip:** Keep `banner_text` short and urgent — it appears on the frontend checkout page:  
`"Launch Week — 40% OFF for new subscribers. Ends 31 May!"`

---

## Workflow 6 — Process a KYC Verification Request

Organisations submit identity documents to earn the "Verified Business" badge. Review queue is at auth_service.

```
STEP 1 — Check the review queue daily
  GET /api/v1/admin/kyc/pending
  → Lists all submissions in pending + under_review + more_info state
  → Sorted oldest first — review in order to avoid stale submissions
  → Each entry shows: org name, document count, submission date

STEP 2 — Open a submission (marks it under_review)
  GET /api/v1/admin/kyc/{submission_id}
  → Full submission detail: org info, all uploaded documents with download URLs
  → Status auto-changes: pending → under_review

STEP 3 — Review documents
  → Check business registration certificate (BRELA / NGO Board)
  → Check TIN / tax clearance
  → Check director/owner national ID
  → Check utility bill or bank statement (proof of address)

STEP 4a — Approve (all documents valid)
  POST /api/v1/admin/kyc/{submission_id}/review
  → Body: { "action": "approve", "admin_notes": "All 4 docs verified. BRELA valid." }
  → Effect: org.is_kyc_verified = true immediately
  → Org's badge becomes "Verified Business" / blue checkmark

STEP 4b — Reject (documents invalid or fraudulent)
  POST /api/v1/admin/kyc/{submission_id}/review
  → Body: {
      "action": "reject",
      "rejection_reason": "BRELA cert expired 2024. Audited accounts missing.",
      "admin_notes": "Sent email to contact on file."
    }
  → Org stays unverified. rejection_reason is shown to the org.

STEP 4c — Request more documents (docs partial but credible)
  POST /api/v1/admin/kyc/{submission_id}/review
  → Body: {
      "action": "more_info",
      "more_info_request": "Bank statement only covers Jan–Dec 2025. Need Jan–Mar 2026.",
      "admin_notes": "Credible NGO. Fast-track when resolved."
    }
  → Status becomes more_info. Org gets notified and can upload additional documents.
  → When org uploads, status auto-reverts to pending. Loops back to Step 1.
```

**KYC status flow:**
```
pending → under_review → approved   (done)
                       → rejected   (done)
                       → more_info  → [org uploads] → pending → under_review → ...
```

---

## Workflow 7 — Grant a Feature Override to One Org (Enterprise Deal)

Use this when an org on a lower plan needs a specific Business/Enterprise feature without upgrading, or when an org on Business needs a feature revoked per contract.

```
STEP 1 — Check what the org currently has
  GET /api/v1/subscriptions/admin/orgs/{org_id}/entitlements
  → Shows every feature with:
    - "enabled": true/false
    - "source": "plan" or "override"
    - "override_reason": why it was overridden
    - "effective_limit" vs "plan_limit" for quota features

STEP 2 — Create the override
  POST /api/v1/subscriptions/admin/orgs/{org_id}/overrides

  Grant a feature the plan doesn't include:
  → Body: {
      "feature_key":   "waiting_queue",
      "override_type": "grant",
      "reason":        "MNH OPD pilot — approved by CEO ref MNH/2026/IT/0042",
      "expires_at":    "2026-08-16T00:00:00"
    }

  Revoke a feature the plan includes:
  → Body: {
      "feature_key":   "stakeholder_engagement",
      "override_type": "revoke",
      "reason":        "Contractual exclusion: using Rimba SEP until Dec 2027"
    }

  Raise a usage limit:
  → Body: {
      "feature_key":   "max_sms_per_month",
      "override_type": "limit",
      "limit_value":   8000,
      "reason":        "UNICEF WASH — 8,000 beneficiary households"
    }

STEP 3 — Verify
  GET /api/v1/subscriptions/admin/orgs/{org_id}/entitlements
  → Feature now shows "source": "override", "override_reason": your reason

STEP 4 — Manage the override lifecycle
  PATCH /api/v1/subscriptions/admin/orgs/{org_id}/overrides/{override_id}
  → Extend expires_at, change reason, update limit_value

  DELETE /api/v1/subscriptions/admin/orgs/{org_id}/overrides/{override_id}
  → Revoke override immediately — feature reverts to plan value

STEP 5 — List all active overrides for the org
  GET /api/v1/subscriptions/admin/orgs/{org_id}/overrides?active_only=true
```

| `override_type` | Use case |
|----------------|----------|
| `grant` | Org on Starter/Professional needs a Business feature (pilot, partnership) |
| `revoke` | Org has a contractual restriction on a feature their plan includes |
| `limit` | Org needs a higher (or lower) quota than their plan provides |

---

## Workflow 8 — Grant Free Months / Compensate for Downtime

```
STEP 1 — Find the subscription ID
  GET /api/v1/subscriptions/admin/orgs/{org_id}/entitlements
  → Note the subscription_id at the top

  OR:
  GET /api/v1/billing/subscriptions/overview?org_id={org_id}

STEP 2 — Grant free months
  POST /api/v1/billing/subscriptions/{subscription_id}/free-months
  → Body: { "months": 2, "reason": "SLA breach — downtime on 2026-05-10" }
  → Extends current_period_end by N × 30 days
  → Logs a SubscriptionEvent audit entry

STEP 3 — Confirm
  GET /api/v1/billing/subscriptions/{subscription_id}/events
  → Audit trail shows free_months_granted event
```

---

## Workflow 9 — Daily Operations Checklist

Run this each working day:

```
Morning (5 min)
  1. GET /billing/metrics                      → MRR, churn, past-due count
  2. GET /billing/subscriptions/due-soon?days=3 → Subs expiring in 3 days (outreach)
  3. GET /admin/kyc/pending                    → Any new KYC submissions to review
  4. GET /admin/platform/stats                 → New orgs/users registered today

Weekly
  5. GET /billing/subscriptions/overview?status=past_due  → Follow up on unpaid
  6. GET /promotions/admin/stats/summary       → Promo performance
  7. GET /billing/subscriptions/by-plan        → Plan distribution + MRR trend
```

---

---

# Part 1 — Plan Management Endpoint Reference

Plans define what features and limits every subscribing org receives. The four default plans (`starter`, `professional`, `business`, `enterprise`) are seeded at startup — do not delete them. Create custom plans for NGO deals, government contracts, and white-label clients.

---

## `GET /plans/admin/plans`
**List all plans including inactive and unpublished ones.**

```
GET /api/v1/plans/admin/plans
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total": 4,
  "plans": [
    {
      "id":           "plan-uuid",
      "slug":         "professional",
      "display_name": "Professional",
      "pricing": {
        "monthly_usd":  "49.00",
        "annual_usd":   "39.00",
        "is_custom":    false
      },
      "trial_days": 14,
      "limits": { "team_members": 25, "projects": 15, "submissions_per_month": 5000 },
      "features": { "sms_channel": true, "ai_insights": false },
      "is_active": true,
      "is_public": true,
      "sort_order": 2,
      "created_at": "2026-03-01T00:00:00",
      "updated_at": "2026-05-19T00:00:00"
    }
  ]
}
```

---

## `POST /plans/admin/plans`
**Create a new plan.**

Required fields: `slug`, `display_name`, `monthly_price_usd`, `annual_price_usd`  
All feature flags default to `false` unless specified.  
All limit fields default to `0` unless specified (`-1` = unlimited).  
New plans start as `is_active=false, is_public=false` — always publish explicitly after review (Step 8 of Workflow 1).

---

## `PATCH /plans/admin/plans/{plan_id}`
**Update any plan field in one call** — shortcut when changing multiple things at once.

```json
{
  "display_name": "Professional Plus",
  "tagline":      "For established NGOs and hospitals",
  "sort_order":   3,
  "trial_days":   21
}
```

Immutable fields: `id`, `slug`, `created_at`.

---

## `PATCH /plans/admin/plans/{plan_id}/pricing`
**Update pricing only.**

```json
{
  "monthly_price_usd": "49.00",
  "annual_price_usd":  "39.00",
  "trial_days":        14,
  "uptime_sla":        "99.9%"
}
```

> **Rule:** Changing pricing does NOT affect existing subscriptions — they keep their `effective_monthly_usd`. Only new checkouts use the new price.

---

## `PATCH /plans/admin/plans/{plan_id}/limits`
**Update usage quotas.** Use `-1` for unlimited.

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

---

## `PATCH /plans/admin/plans/{plan_id}/features`
**Toggle individual features on or off.**

```json
{
  "ai_insights":            true,
  "phone_call_ai":          true,
  "spark_streaming":        false,
  "stakeholder_engagement": true,
  "webhooks":               true
}
```

All available feature keys: `GET /api/v1/plans/features`

**Response** includes `features_changed` and a full `features` snapshot:
```json
{
  "features_changed": { "ai_insights": true, "phone_call_ai": true },
  "features": { "sms_channel": true, "ai_insights": true },
  "warnings": []
}
```

---

## `POST /plans/admin/plans/{plan_id}/duplicate`
**Clone a plan.**

```json
{
  "slug":              "business-ngo",
  "display_name":      "Business NGO",
  "monthly_price_usd": "74.50",
  "annual_price_usd":  "59.50"
}
```

Cloned plan starts as `is_active=false, is_public=false`. Adjust features/limits/pricing, then publish.

---

## `PATCH /plans/admin/plans/{plan_id}/publish`
**Publish or unpublish a plan.**

```json
{ "is_public": true, "is_active": true }
```

---

## `DELETE /plans/admin/plans/{plan_id}`
**Deactivate a plan (soft delete — existing subscribers are not affected).**

- Default plans (`starter`, `professional`, `business`, `enterprise`) cannot be deactivated.
- Deactivated plans are hidden from `GET /plans` but visible in `GET /plans/admin/plans`.

---

---

# Part 2 — Add-on Management

Add-ons are extra capacity units that orgs purchase on top of their plan limits (e.g., extra SMS bundles, more team seats).

---

## `GET /plans/admin/addons`
List all add-ons including inactive ones.

## `POST /plans/admin/addons`
**Create a new add-on.**

```json
{
  "slug":          "extra-sms-5k",
  "name":          "Extra SMS Bundle (5,000)",
  "description":   "5,000 additional SMS per month — ideal for large outreach campaigns",
  "type":          "extra_sms",
  "price_usd":     "40.00",
  "unit":          "5,000 SMS",
  "unit_quantity": 5000
}
```

Valid `type` values: `extra_sms`, `extra_users`, `extra_storage`, `extra_api_calls`,
`extra_qr`, `whatsapp_business`, `custom_ai`, `dedicated_kafka`, `phone_call_ai`,
`advanced_translation`

## `PATCH /plans/admin/addons/{addon_id}`
Update name, description, price, or deactivate.

## `DELETE /plans/admin/addons/{addon_id}`
Soft deactivate — hides from checkout but does not affect orgs already subscribed to the add-on.

---

---

# Part 3 — Billing Dashboard

All billing admin endpoints are under `/api/v1/billing/`.

---

## `GET /billing/metrics`
**Platform-wide subscription health — the primary dashboard KPI card.**

```
GET /api/v1/billing/metrics
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "mrr_usd":        "4820.00",
  "arr_usd":        "57840.00",
  "active_count":   31,
  "trialing_count": 14,
  "past_due_count": 2,
  "churn_last_30_days": 3,
  "by_plan": [
    { "slug": "starter",      "display_name": "Starter",       "count": 8,  "mrr_usd": "120.00" },
    { "slug": "professional", "display_name": "Professional",   "count": 17, "mrr_usd": "833.00" },
    { "slug": "business",     "display_name": "Business",       "count": 6,  "mrr_usd": "894.00" }
  ]
}
```

---

## `GET /billing/subscriptions/overview`
**Paginated list of all org subscriptions — searchable and filterable.**

```
GET /api/v1/billing/subscriptions/overview?status=active&plan_slug=professional&page=1&size=25
```

| Query param | Values | Default |
|-------------|--------|---------|
| `status` | `active`, `trialing`, `past_due`, `paused`, `cancelled`, `expired` | all |
| `plan_slug` | `starter`, `professional`, `business`, `enterprise` | all |
| `expiring_days` | integer — only subs ending within N days | — |
| `page`, `size` | integers | 1, 20 |

---

## `GET /billing/subscriptions/due-soon`
**Subscriptions expiring within N days — for renewal outreach.**

```
GET /api/v1/billing/subscriptions/due-soon?days=7
```

**Response splits into `renewing` and `cancelling`:**
```json
{
  "horizon_days": 7,
  "renewing_count": 4,
  "cancelling_count": 1,
  "renewing": [
    { "org_id": "...", "plan": "business", "renews_at": "2026-05-25T..." }
  ],
  "cancelling": [
    { "org_id": "...", "plan": "starter", "will_cancel": true }
  ]
}
```

---

## `GET /billing/subscriptions/by-plan`
**Plan distribution with MRR breakdown — for business intelligence.**

```json
{
  "total_mrr_usd": "1847.00",
  "by_plan": [
    {
      "plan": "professional",
      "total_orgs": 17,
      "active": 15,
      "trialing": 2,
      "billing": { "monthly": 11, "annual": 6 },
      "mrr_usd": "833.00"
    }
  ]
}
```

---

## `GET /billing/invoices`
**All invoices platform-wide, filterable.**

```
GET /api/v1/billing/invoices?status=open&page=1&size=50
```

| Filter | Values |
|--------|--------|
| `status` | `open`, `paid`, `void`, `uncollectible` |

---

## `POST /billing/invoices/{invoice_id}/void`
**Void an open invoice** — for payment errors or bank transfer confirmations.  
No body required.

---

## `GET /billing/subscriptions/{subscription_id}/events`
**Full audit trail for a subscription.**  
Returns all lifecycle events: `trial_started`, `subscribed`, `upgraded`, `payment_succeeded`, `free_months_granted`, etc.

---

## `POST /billing/subscriptions/{subscription_id}/cancel`
**Admin-force cancel** a subscription — for fraud, policy violations, or org closure requests.

```json
{
  "reason":    "Organisation requested account closure",
  "immediate": true
}
```

Set `"immediate": false` to cancel at period end instead.

---

## `POST /billing/subscriptions/{subscription_id}/free-months`
**Grant free months** — for SLA breaches, partnerships, or goodwill gestures.

```json
{
  "months": 2,
  "reason": "SLA breach compensation — downtime on 2026-05-10"
}
```

Extends `current_period_end` by `months × 30 days`. Logs a `SubscriptionEvent`.

---

---

# Part 4 — Org Subscription Overrides

Override a specific org's feature access or usage limits without changing the plan for everyone. Used for enterprise deals, pilot programmes, NGO partnerships, and contractual exclusions.

---

## `GET /subscriptions/admin/all`
**List every subscription across all orgs.**

```
GET /api/v1/subscriptions/admin/all?status=active&page=1&size=50
```

---

## `PATCH /subscriptions/admin/{subscription_id}`
**Directly override any subscription field** — last resort for manual corrections.

Allowed fields: `status`, `plan_id`, `billing_cycle`, `cancel_at_period_end`,
`discount_pct`, `discount_months_remaining`, `current_period_end`

```json
{
  "current_period_end": "2027-05-19T00:00:00",
  "discount_pct": "30.00",
  "discount_months_remaining": 9999
}
```

---

## `GET /subscriptions/admin/orgs/{org_id}/entitlements`
**Full entitlement map for any org.**

Shows every feature flag and usage limit with:
- current value (`enabled: true/false`)
- source (`"plan"` or `"override"`)
- `override_reason` if applicable
- `plan_limit` vs `effective_limit` (after overrides)
- `used` and `pct_used` for quota features

---

## `POST /subscriptions/admin/orgs/{org_id}/overrides`
**Grant a feature, revoke a feature, or override a usage limit for one org.**

### Grant a Business feature to a Professional org (pilot)
```json
{
  "feature_key":   "waiting_queue",
  "override_type": "grant",
  "reason":        "MNH OPD pilot — 3-step patient queue, approved CEO ref MNH/2026/IT/0042",
  "note":          "Review at 90 days.",
  "expires_at":    "2026-08-19T00:00:00"
}
```

### Revoke a feature from an org (contractual exclusion)
```json
{
  "feature_key":   "stakeholder_engagement",
  "override_type": "revoke",
  "reason":        "Contractual exclusion: using Rimba SEP until December 2027"
}
```

### Raise a usage limit (NGO partner programme)
```json
{
  "feature_key":   "max_sms_per_month",
  "override_type": "limit",
  "limit_value":   8000,
  "reason":        "UNICEF WASH — 8,000 beneficiary households across 3 districts"
}
```

| `override_type` | `feature_key` accepts | Effect |
|----------------|----------------------|--------|
| `grant` | Any feature key from catalog | Enables feature even if plan excludes it |
| `revoke` | Any feature key from catalog | Disables feature even if plan includes it |
| `limit` | Any `max_*` limit key | Replaces plan quota with `limit_value` (`-1` = unlimited) |

**Idempotent:** If the same `(org_id, feature_key, override_type)` already exists and is active, the old override is deactivated and replaced.

---

## `PATCH /subscriptions/admin/orgs/{org_id}/overrides/{override_id}`
**Update an existing override** — extend expiry, change reason, modify limit value.

```json
{
  "reason":      "Extended: 90-day pilot approved by CEO",
  "expires_at":  "2026-09-19T00:00:00",
  "limit_value": 12000
}
```

---

## `DELETE /subscriptions/admin/orgs/{org_id}/overrides/{override_id}`
**Revoke an override** — feature reverts to plan value immediately.

---

## `GET /subscriptions/admin/orgs/{org_id}/overrides`
**List all overrides for an org.**

```
GET /api/v1/subscriptions/admin/orgs/{org_id}/overrides?active_only=true
```

---

---

# Part 5 — Promo Code Management

Promo codes give discounts to specific orgs at checkout or on existing subscriptions.

---

## `GET /promotions/admin`
**List all promo codes with redemption stats.**

```
GET /api/v1/promotions/admin?active_only=false&page=1&size=50
```

---

## `POST /promotions/admin`
**Create a promo code.**

```json
{
  "code":                 "HOSPITAL30",
  "name":                 "Hospital & Clinic Discount",
  "description":          "30% off for 6 months — hospitals and clinics on Business plan.",
  "discount_type":        "percentage",
  "discount_value":       30,
  "duration":             "repeating",
  "duration_months":      6,
  "max_redemptions":      200,
  "eligible_plans":       ["business"],
  "new_subscribers_only": false,
  "min_plan_price_usd":   "0",
  "expires_at":           "2026-12-31T23:59:59",
  "is_active":            true
}
```

---

## `POST /promotions/admin/bulk-generate`
**Generate multiple unique codes for a campaign** — useful for partner referral batches.

```json
{
  "prefix":           "PARTNER",
  "count":            50,
  "discount_type":    "percentage",
  "discount_value":   25,
  "duration":         "repeating",
  "duration_months":  6,
  "eligible_plans":   ["professional", "business"],
  "expires_at":       "2026-12-31T23:59:59"
}
```

Generates codes like `PARTNER-X7Y2A1`, `PARTNER-K9B3C8`, etc.

---

## `GET /promotions/admin/stats/summary`
**Aggregate promo performance across all codes.**

```json
{
  "total_codes":        18,
  "active_codes":       12,
  "total_redemptions":  147,
  "total_discount_usd": "3820.00",
  "top_codes": [
    { "code": "LAUNCH2026", "redemptions": 43 }
  ]
}
```

---

## `GET /promotions/admin/{promo_id}`
**Single promo code with detailed stats.**

---

## `PATCH /promotions/admin/{promo_id}`
**Update a promo** — extend expiry, raise redemption limit, activate/deactivate.

```json
{
  "expires_at":      "2027-03-31T23:59:59",
  "max_redemptions": 500,
  "is_active":       true
}
```

---

## `DELETE /promotions/admin/{promo_id}`
**Deactivate a promo code.** Existing redemptions are not affected.

---

## `POST /promotions/validate`
**Validate a promo code** — use from the checkout UI to show discount preview before payment.

```json
{
  "code":      "LAUNCH2026",
  "plan_slug": "professional",
  "org_id":    "org-uuid"
}
```

**Response:**
```json
{
  "valid":          true,
  "code":           "LAUNCH2026",
  "discount_label": "30% off for 3 months",
  "discount_type":  "percentage",
  "discount_value": "30.00"
}
```

---

---

# Part 6 — Sales Campaigns

Sales are time-bounded discounts that **auto-apply at checkout** — no code required. Used for product launches, end-of-year promotions, and flash sales.

---

## `GET /sales/admin/all`
**List all campaigns** — scheduled, active, ended, and cancelled.

---

## `POST /sales/admin`
**Create a sale campaign.**

```json
{
  "name":           "Q3 Tanzania Launch 2026",
  "description":    "30% off all plans for Tanzanian organisations. 2 weeks only.",
  "banner_text":    "Tanzania Launch — 30% OFF all plans. Ends 31 July!",
  "start_at":       "2026-07-01T00:00:00",
  "end_at":         "2026-07-14T23:59:59",
  "discount_type":  "percentage",
  "discount_value": 30,
  "duration":       "once",
  "eligible_plans": null,
  "new_subscribers_only": true,
  "max_redemptions": -1,
  "auto_apply":     true
}
```

| Field | Description |
|-------|-------------|
| `auto_apply: true` | Discount applies automatically at checkout — no code needed |
| `eligible_plans: null` | Applies to all plans; or `["professional", "business"]` to restrict |
| `new_subscribers_only` | Restrict to first-time subscribers only |
| `max_redemptions: -1` | Unlimited redemptions |

**Status is computed automatically** from `start_at`/`end_at`:
- `scheduled` — start_at is in the future
- `active` — currently between start_at and end_at
- `ended` — end_at has passed
- `cancelled` — manually stopped

---

## `PATCH /sales/admin/{sale_id}`
Update banner text, discount amount, targeting, or redemption cap.

## `POST /sales/admin/{sale_id}/activate`
**Force-activate early** — starts immediately regardless of `start_at`.

## `POST /sales/admin/{sale_id}/end`
**End early** — stops immediately regardless of `end_at`.

## `POST /sales/admin/{sale_id}/extend`
**Extend end date.**
```json
{ "new_end_at": "2026-07-21T23:59:59" }
```

## `GET /sales/admin/{sale_id}/stats`
**Redemption statistics.**
```json
{
  "name":             "Q3 Tanzania Launch 2026",
  "status":           "active",
  "redemption_count": 12,
  "remaining_hours":  162.5
}
```

## `DELETE /sales/admin/{sale_id}`
**Cancel a campaign** — marks it cancelled. Cannot be undone.

---

---

# Part 7 — KYC Review

Review and approve identity documents submitted by organisations requesting the "Verified Business" badge.

---

## `GET /admin/kyc/pending`
**The KYC review queue** — sorted oldest first.

```
GET /api/v1/admin/kyc/pending?status=pending&page=1&size=20
Authorization: Bearer <admin_token>
```

| `status` filter | Meaning |
|----------------|---------|
| *(default)* | `pending` + `under_review` + `more_info` — all actionable |
| `pending` | Submitted, not yet opened |
| `under_review` | Admin has opened it |
| `more_info` | Org was asked for more docs |
| `approved` | Completed — org has verified badge |
| `rejected` | Rejected |

---

## `GET /admin/kyc/{submission_id}`
**Open a submission for review.**  
Side effect: status auto-changes from `pending` → `under_review`.  
Returns full submission with all documents and the org's current verification state.

---

## `POST /admin/kyc/{submission_id}/review`
**Make a decision.**

### Approve
```json
{
  "action":      "approve",
  "admin_notes": "All 4 documents verified. MNH reg cert, TRA clearance, director NIDA, TANESCO bill — all valid."
}
```
Sets `org.is_kyc_verified = true`. Badge immediately becomes "Verified Business".

### Reject
```json
{
  "action":           "reject",
  "rejection_reason": "Missing BRELA certificate and audited accounts for 2024/2025.",
  "admin_notes":      "Legitimate NGO — docs just incomplete. Emailed contact."
}
```

### Request more information
```json
{
  "action":            "more_info",
  "more_info_request": "Bank statement only covers to December 2025. Need Jan–Mar 2026.",
  "admin_notes":       "Documents credible. Fast-track on resolution."
}
```

---

## `PATCH /admin/orgs/{org_id}/payment-verification`
**Manually set payment verification** — for bank transfer confirmations or legacy migrations.

```json
{ "is_payment_verified": true }
```

---

---

# Part 8 — Platform Metrics (Auth Service)

---

## `GET /admin/platform/stats`
**Top-level platform KPIs.**

```json
{
  "total_users":    1240,
  "active_today":   87,
  "active_7d":      312,
  "active_30d":     680,
  "new_users_today": 14,
  "total_orgs":     145,
  "active_orgs":    132,
  "new_orgs_today": 3,
  "countries_count": 18
}
```

## `GET /admin/platform/by-country`
**Org and user count per country.**

```json
{
  "countries": [
    { "country_code": "TZ", "org_count": 78, "user_count": 612 },
    { "country_code": "KE", "org_count": 31, "user_count": 248 }
  ]
}
```

## `GET /admin/platform/by-region`
**Breakdown by region within a country.**

```
GET /api/v1/admin/platform/by-region?country_code=TZ
```

---

---

# Complete Admin Endpoint Inventory

## Subscription service (`/api/v1/`)

### Plans
| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/plans/admin/plans` | List all plans incl. inactive |
| `POST` | `/plans/admin/plans` | Create new plan |
| `PATCH` | `/plans/admin/plans/{id}` | Update any field |
| `PATCH` | `/plans/admin/plans/{id}/pricing` | Update pricing only |
| `PATCH` | `/plans/admin/plans/{id}/limits` | Update usage limits |
| `PATCH` | `/plans/admin/plans/{id}/features` | Toggle features on/off |
| `POST` | `/plans/admin/plans/{id}/duplicate` | Clone a plan |
| `PATCH` | `/plans/admin/plans/{id}/publish` | Publish / unpublish |
| `DELETE` | `/plans/admin/plans/{id}` | Deactivate (soft delete) |

### Add-ons
| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/plans/admin/addons` | List all add-ons |
| `POST` | `/plans/admin/addons` | Create add-on |
| `PATCH` | `/plans/admin/addons/{id}` | Update add-on |
| `DELETE` | `/plans/admin/addons/{id}` | Deactivate add-on |

### Billing dashboard
| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/billing/metrics` | MRR, ARR, plan distribution, churn |
| `GET` | `/billing/subscriptions/overview` | All subscriptions paginated |
| `GET` | `/billing/subscriptions/due-soon` | Expiring in N days |
| `GET` | `/billing/subscriptions/by-plan` | Plan distribution + MRR |
| `GET` | `/billing/invoices` | All invoices platform-wide |
| `POST` | `/billing/invoices/{id}/void` | Void an invoice |
| `GET` | `/billing/subscriptions/{id}/events` | Subscription audit trail |
| `POST` | `/billing/subscriptions/{id}/cancel` | Admin force-cancel |
| `POST` | `/billing/subscriptions/{id}/free-months` | Grant free months |

### Subscription overrides
| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/subscriptions/admin/all` | Every subscription |
| `PATCH` | `/subscriptions/admin/{id}` | Direct field override |
| `GET` | `/subscriptions/admin/orgs/{org_id}/entitlements` | Full feature map with usage |
| `POST` | `/subscriptions/admin/orgs/{org_id}/overrides` | Grant / revoke / limit |
| `PATCH` | `/subscriptions/admin/orgs/{org_id}/overrides/{id}` | Update override |
| `DELETE` | `/subscriptions/admin/orgs/{org_id}/overrides/{id}` | Revoke override |
| `GET` | `/subscriptions/admin/orgs/{org_id}/overrides` | List overrides |

### Promotions
| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/promotions/admin` | List all promo codes |
| `POST` | `/promotions/admin` | Create promo code |
| `GET` | `/promotions/admin/stats/summary` | Aggregate promo performance |
| `GET` | `/promotions/admin/{id}` | Single promo with stats |
| `PATCH` | `/promotions/admin/{id}` | Update promo |
| `DELETE` | `/promotions/admin/{id}` | Deactivate promo |
| `POST` | `/promotions/admin/bulk-generate` | Generate batch of codes |
| `POST` | `/promotions/validate` | Validate a code at checkout |

### Sales campaigns
| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/sales/admin/all` | All campaigns |
| `POST` | `/sales/admin` | Create campaign |
| `PATCH` | `/sales/admin/{id}` | Update campaign |
| `POST` | `/sales/admin/{id}/activate` | Activate early |
| `POST` | `/sales/admin/{id}/end` | End early |
| `POST` | `/sales/admin/{id}/extend` | Extend end date |
| `GET` | `/sales/admin/{id}/stats` | Redemption stats |
| `DELETE` | `/sales/admin/{id}` | Cancel campaign |

## Auth service (`/api/v1/`)

### KYC review
| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/admin/kyc/pending` | Review queue (pending+under_review+more_info) |
| `GET` | `/admin/kyc/{id}` | Open submission (auto → under_review) |
| `POST` | `/admin/kyc/{id}/review` | Approve / reject / request more_info |
| `PATCH` | `/admin/orgs/{id}/payment-verification` | Manual payment flag |

### Platform metrics
| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/admin/platform/stats` | Users, orgs, activity |
| `GET` | `/admin/platform/by-country` | Distribution by country |
| `GET` | `/admin/platform/by-region` | Distribution by region |
