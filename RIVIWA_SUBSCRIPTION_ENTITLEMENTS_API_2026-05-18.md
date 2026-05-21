# Riviwa Subscription Service — Entitlements & Feature Gating API Reference
**Date:** 2026-05-18  
**Service:** subscription_service — Port **8140**  
**Base path:** `/api/v1/subscriptions`

This document covers the subscription entitlement system: how organisations and users are related to their subscriptions, which features their plan unlocks, and how administrators override entitlements per-organisation for enterprise deals, pilot programmes, and contractual restrictions.

---

## Overview

Every organisation on Riviwa has exactly one active subscription linked to a **Plan**. A plan defines:

- **Feature flags** — 48 boolean capabilities (AI Insights, QR Generation, Staff Verification, etc.)
- **Usage limits** — 8 numeric quotas (SMS/month, API calls/month, team members, storage GB, etc.)

The entitlement system adds a layer on top of plan defaults:

| Layer | Precedence | Description |
|-------|-----------|-------------|
| **`OrgFeatureOverride`** | **Highest** | Per-org grant / revoke / limit override |
| **Plan flags** | Default | Boolean fields on the subscribed plan |

Overrides are checked first. If no override exists for a feature, the plan flag is used.

**Three override types:**

| Type | Effect |
|------|--------|
| `grant` | Enable a feature the plan does not include (e.g., give Professional org access to AI Insights) |
| `revoke` | Disable a feature the plan normally includes (e.g., contractual restriction) |
| `limit` | Replace a numeric usage limit with a custom value (e.g., raise SMS from 2,000 → 8,000) |

---

## Authentication

```
Authorization: Bearer <access_token>
```

| Auth Type | Header | Used by |
|-----------|--------|---------|
| JWT Bearer | `Authorization: Bearer <token>` | All org-facing endpoints |
| Service Key | `X-Service-Key: <key>` | Internal endpoints (service-to-service) |
| Admin JWT | `Authorization: Bearer <token>` (with `org_role` = OWNER/ADMIN/SUPER_ADMIN) | All `/admin/` endpoints |

---

## Feature Catalog

The platform defines **48 features** across 15 categories. Every feature has a `key` used in all API calls.

| Category | Feature Keys |
|----------|-------------|
| **Feedback Channels** | `sms_channel`, `whatsapp_channel`, `phone_call_ai` |
| **AI & Intelligence** | `ai_conversation`, `ai_insights`, `voice_transcription`, `ml_predictor`, `spark_streaming`, `recommendations`, `ai_counterfeit` |
| **Notifications** | `push_notifications`, `whatsapp_notif` |
| **Analytics** | `advanced_analytics`, `custom_reports` |
| **Feedback Management** | `employee_feedback`, `pap_registry`, `committee_mgmt`, `bulk_import` |
| **QR & Verification** | `qr_generation`, `product_verification`, `field_agents` |
| **Staff** | `staff_verification`, `bulk_staff_import`, `staff_analytics` |
| **Queue Management** | `waiting_queue` |
| **Stakeholder** | `stakeholder_engagement` |
| **Translation** | `translation`, `advanced_translation` |
| **Product Catalog** | `product_catalog`, `product_variations`, `rsin` |
| **Integration** | `api_access`, `webhooks`, `oauth2`, `widget_embed`, `audit_logs` |
| **Payments** | `mobile_money`, `paypal`, `payment_processing` |
| **Authentication** | `social_login`, `id_verification`, `fraud_detection`, `multi_org`, `2fa`, `sso` |
| **Platform** | `white_label`, `dedicated_support`, `custom_sla` |

> **Full feature catalog with descriptions and service attribution:** `GET /api/v1/plans/features`

---

## Usage Limit Keys

| Key | Description | Unit |
|-----|-------------|------|
| `max_team_members` | Maximum org members (staff + admins) | count |
| `max_projects` | Maximum projects (-1 = unlimited) | count |
| `max_submissions_per_month` | Feedback submissions per billing period | count |
| `max_sms_per_month` | SMS messages sent per billing period | count |
| `max_api_calls_per_month` | REST API calls per billing period | count |
| `max_storage_gb` | File + voice recording storage | gigabytes |
| `max_qr_per_month` | QR codes generated per billing period | count |
| `max_staff_profiles` | Staff identity profiles per org | count |

---

---

# Part 1 — Org-Facing Endpoints

---

## `GET /subscriptions/my/features`

**Auth:** Bearer token  
**Summary:** Returns the complete feature and limit entitlement map for the authenticated organisation.

The primary endpoint for the frontend to determine what features to show, hide, or lock behind an upgrade prompt. Returns all 48 features with their enabled state and source, plus all 8 limits with current usage.

### Response

```json
{
  "org_id": "16449750-e456-4c7f-ab76-0d59b526d7b5",
  "has_subscription": true,
  "subscription_status": "trialing",
  "plan": {
    "id": "b3e7c4a1-...",
    "slug": "professional",
    "display_name": "Professional"
  },
  "features": [
    {
      "key": "sms_channel",
      "label": "SMS Channel",
      "category": "Feedback Channels",
      "service": "feedback_service",
      "enabled": true,
      "plan_value": true,
      "source": "plan",
      "override_reason": null,
      "override_expires": null
    },
    {
      "key": "waiting_queue",
      "label": "Multi-Step Queue Management",
      "category": "Queue Management",
      "service": "waiting_service",
      "enabled": true,
      "plan_value": false,
      "source": "override",
      "override_reason": "MNH OPD pilot — 3-step patient queue (triage → consultation → pharmacy)",
      "override_expires": "2026-08-16T00:00:00"
    },
    {
      "key": "stakeholder_engagement",
      "label": "Stakeholder Engagement (SEP)",
      "category": "Stakeholder",
      "service": "stakeholder_service",
      "enabled": false,
      "plan_value": true,
      "source": "override",
      "override_reason": "Contractual exclusion: organisation uses Rimba SEP platform",
      "override_expires": null
    }
  ],
  "limits": [
    {
      "key": "max_sms_per_month",
      "plan_limit": 2000,
      "effective_limit": 8000,
      "used": 123,
      "pct_used": 1.5,
      "source": "override",
      "override_reason": "UNICEF WASH programme — 8,000 beneficiary households"
    },
    {
      "key": "max_submissions_per_month",
      "plan_limit": 5000,
      "effective_limit": 5000,
      "used": 47,
      "pct_used": 0.9,
      "source": "plan",
      "override_reason": null
    }
  ],
  "overrides": [
    {
      "id": "uuid",
      "feature_key": "waiting_queue",
      "override_type": "grant",
      "limit_value": null,
      "reason": "MNH OPD pilot",
      "note": "MoHSW approval ref: MNH/2026/IT/0042",
      "expires_at": "2026-08-16T00:00:00",
      "granted_by": "admin-user-uuid",
      "created_at": "2026-05-18T20:18:00"
    }
  ]
}
```

### Feature object fields

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Feature key used in all API calls |
| `label` | string | Human-readable display name |
| `category` | string | Grouping category (matches feature catalog) |
| `service` | string | Which Riviwa service delivers this feature |
| `enabled` | boolean | Whether the org can use this feature right now |
| `plan_value` | boolean | What the plan alone would give (before overrides) |
| `source` | `"plan"` \| `"override"` | Where `enabled` comes from |
| `override_reason` | string \| null | Admin-provided reason for the override |
| `override_expires` | ISO datetime \| null | When the override expires (null = permanent) |

### Limit object fields

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Limit key (matches usage meter field names) |
| `plan_limit` | integer | Quota from the subscribed plan |
| `effective_limit` | integer | Final quota after overrides (`-1` = unlimited) |
| `used` | integer | Current billing period consumption |
| `pct_used` | float | `used / effective_limit × 100` (0 if unlimited) |
| `source` | `"plan"` \| `"override"` | Where `effective_limit` comes from |
| `override_reason` | string \| null | Admin-provided reason for the limit change |

### Frontend usage patterns

```javascript
// Show/hide feature in UI
const features = entitlements.features.reduce((m, f) => ({ ...m, [f.key]: f }), {});

if (features.ai_insights.enabled) {
  showAIInsightsDashboard();
} else if (features.ai_insights.source === "plan") {
  showUpgradePrompt("ai_insights");   // plan doesn't include it
}

// Check if close to SMS limit (show warning at 80%)
const sms = entitlements.limits.find(l => l.key === "max_sms_per_month");
if (sms.pct_used >= 80) showSmsLimitWarning(sms.used, sms.effective_limit);
```

---

---

# Part 2 — Internal Endpoints (Service-to-Service)

These endpoints are called by other Riviwa services. They require the `X-Service-Key` header, not a JWT.

---

## `GET /subscriptions/internal/feature-check`

**Auth:** `X-Service-Key`  
**Summary:** Check whether an organisation has access to a specific feature. Used by every other service to gate its own endpoints.

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `org_id` | UUID string | Yes | Organisation ID from the JWT claim |
| `feature` | string | Yes | Feature key (e.g. `qr_generation`, `waiting_queue`) |

### Request

```
GET /api/v1/subscriptions/internal/feature-check?org_id=<uuid>&feature=waiting_queue
X-Service-Key: <key>
```

### Response

```json
{
  "org_id": "16449750-e456-4c7f-ab76-0d59b526d7b5",
  "feature": "waiting_queue",
  "has_access": true,
  "limits": {
    "max_team_members": 25,
    "max_projects": 15,
    "max_submissions_per_month": 5000,
    "max_sms_per_month": 8000,
    "max_api_calls_per_month": 50000,
    "max_storage_gb": 25,
    "max_qr_per_month": 500,
    "max_staff_profiles": 100
  }
}
```

`has_access: true` is returned when:
- Subscription status is `active` or `trialing`, AND
- Plan flag `has_{feature}` is `true`, OR an active `grant` override exists for the feature

`has_access: false` is returned when:
- No active subscription, OR
- Plan flag is `false` with no active `grant` override, OR
- An active `revoke` override exists (even if plan flag is `true`), OR
- A `grant` override exists but its `expires_at` is in the past

### How other services use this

```python
# In waiting_service: gate the queue endpoint
async def require_queue_feature(claims: dict, db) -> None:
    resp = await http_client.get(
        "http://subscription_service:8140/api/v1/subscriptions/internal/feature-check",
        headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
        params={"org_id": claims["org_id"], "feature": "waiting_queue"},
    )
    if not resp.json().get("has_access"):
        raise HTTPException(403, {"error": "FEATURE_NOT_AVAILABLE",
                                  "message": "Upgrade to Business plan to use Queue Management."})
```

For endpoints within subscription_service itself, use the `require_feature()` FastAPI dependency:

```python
from core.deps import require_feature

@router.post("/my-endpoint", dependencies=[require_feature("webhooks")])
async def my_endpoint(...):
    ...
```

Returns `HTTP 403` with body:
```json
{
  "error": "FEATURE_NOT_AVAILABLE",
  "message": "Your plan does not include 'webhooks'. Upgrade at /api/v1/plans.",
  "feature": "webhooks"
}
```

---

## `POST /subscriptions/internal/usage/increment`

**Auth:** `X-Service-Key`  
**Summary:** Increment a usage meter counter. Called by other services every time a metered resource is consumed.

Each service is responsible for calling this endpoint when it consumes a tracked resource. The subscription service aggregates usage for the current billing period and surfaces it in `/my/features`.

### Request body

```json
{
  "org_id": "16449750-e456-4c7f-ab76-0d59b526d7b5",
  "metric": "sms_count",
  "amount": 1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `org_id` | UUID string | Yes | Organisation whose meter to increment |
| `metric` | string | Yes | Meter field name (see table below) |
| `amount` | integer | No | How much to add (default: `1`) |

### Valid `metric` values

| Metric | Incremented by | `amount` unit |
|--------|---------------|--------------|
| `submissions_count` | `feedback_service` on every submission created | 1 per submission |
| `sms_count` | `notification_service` on every SMS dispatched | 1 per SMS |
| `api_calls_count` | `integration_service` on every authenticated API call | 1 per call |
| `storage_bytes` | `ai_service`, `product_service` on file upload | bytes added |
| `qr_codes_count` | `qr_service` on every QR code generated | 1 per QR |
| `team_members_count` | `auth_service` on member add/remove | 1 or -1 |
| `staff_profiles_count` | `staff_service` on profile create | 1 per profile |

### Response

```json
{
  "ok": true,
  "org_id": "16449750-e456-4c7f-ab76-0d59b526d7b5",
  "metric": "sms_count"
}
```

### Example: notification_service increments SMS counter

```python
# notification_service/services/dispatcher.py
async def _after_sms_sent(org_id: str, count: int = 1):
    await http_client.post(
        "http://subscription_service:8140/api/v1/subscriptions/internal/usage/increment",
        headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
        json={"org_id": org_id, "metric": "sms_count", "amount": count},
    )
```

### Example: qr_service increments QR counter

```python
# qr_service/services/qr_generator.py
async def _after_qr_generated(org_id: str):
    asyncio.ensure_future(
        http_client.post(
            "http://subscription_service:8140/api/v1/subscriptions/internal/usage/increment",
            headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            json={"org_id": org_id, "metric": "qr_codes_count", "amount": 1},
        )
    )
```

> **Note:** Increment calls are fire-and-forget — they should not block the primary request path. Silently fail if the subscription service is unreachable.

---

---

# Part 3 — Admin Endpoints

All admin endpoints require a Bearer token with `org_role` = `OWNER`, `ADMIN`, or `SUPER_ADMIN`.

---

## `GET /subscriptions/admin/orgs/{org_id}/entitlements`

**Auth:** Admin Bearer token  
**Summary:** Returns the full entitlement map for any organisation, identical in structure to `/my/features` but accessible by platform administrators across all orgs.

```
GET /api/v1/subscriptions/admin/orgs/16449750-e456-4c7f-ab76-0d59b526d7b5/entitlements
```

**Response structure:** identical to `GET /subscriptions/my/features` above.

**Use cases:**
- Support team debugging why an org cannot access a feature
- Sales team checking what a prospect is currently using before an upgrade call
- Finance verifying override terms before invoice generation

---

## `GET /subscriptions/admin/orgs/{org_id}/overrides`

**Auth:** Admin Bearer token  
**Summary:** List all feature overrides for an organisation.

### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `active_only` | boolean | `true` | `true` = active overrides only; `false` = include revoked/expired |

### Response

```json
{
  "org_id": "16449750-e456-4c7f-ab76-0d59b526d7b5",
  "total": 3,
  "overrides": [
    {
      "id": "5fa7f3c5-...",
      "feature_key": "waiting_queue",
      "override_type": "grant",
      "limit_value": null,
      "reason": "MNH OPD + Emergency queue (scope expanded after clinical review)",
      "note": "UPDATED: now covers 5 departments. MoHSW ref: MNH/2026/IT/0042",
      "is_active": true,
      "expires_at": "2026-09-15T00:00:00",
      "granted_by": "admin-user-uuid",
      "created_at": "2026-05-18T20:18:44"
    },
    {
      "id": "a2c3d4e5-...",
      "feature_key": "max_sms_per_month",
      "override_type": "limit",
      "limit_value": 8000,
      "reason": "UNICEF WASH programme — 8,000 beneficiary households across 3 districts",
      "note": "Project code: UNICEF-TZ-2026-WASH-047",
      "is_active": true,
      "expires_at": null,
      "granted_by": "admin-user-uuid",
      "created_at": "2026-05-18T20:18:48"
    },
    {
      "id": "b3d4e5f6-...",
      "feature_key": "stakeholder_engagement",
      "override_type": "revoke",
      "limit_value": null,
      "reason": "Contractual exclusion: organisation uses Rimba SEP platform (existing contract until Dec 2027)",
      "note": "Re-activate when Rimba contract expires. Contact: procurement@org.co.tz",
      "is_active": true,
      "expires_at": null,
      "granted_by": "admin-user-uuid",
      "created_at": "2026-05-18T20:18:52"
    }
  ]
}
```

---

## `POST /subscriptions/admin/orgs/{org_id}/overrides`

**Auth:** Admin Bearer token  
**Status:** `201 Created`  
**Summary:** Grant, revoke, or override a usage limit for a specific organisation.

If an active override of the same type already exists for the same `feature_key`, it is deactivated and replaced by the new one — **no duplicates accumulate**.

### Request body

```json
{
  "feature_key":   "waiting_queue",
  "override_type": "grant",
  "limit_value":   null,
  "reason":        "MNH OPD pilot — 3-step patient queue (triage → consultation → pharmacy)",
  "note":          "MoHSW approval ref: MNH/2026/IT/0042. Review at 90 days.",
  "expires_at":    "2026-08-16T00:00:00"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `feature_key` | string | **Yes** | Feature key or limit key to override |
| `override_type` | `"grant"` \| `"revoke"` \| `"limit"` | **Yes** | What the override does |
| `limit_value` | integer | **Required when `override_type=limit`** | New limit value (`-1` = unlimited) |
| `reason` | string | Recommended | Why this override was granted (shown in entitlement map) |
| `note` | string | No | Internal admin note (approval reference, ticket number, etc.) |
| `expires_at` | ISO datetime string | No | When the override expires. `null` = permanent |

### override_type reference

**`grant`** — Enables a feature the plan does not include:
```json
{
  "feature_key":   "ai_insights",
  "override_type": "grant",
  "reason":        "60-day pilot: Groq analysis for hospital management board reports",
  "expires_at":    "2026-07-18T00:00:00"
}
```

**`revoke`** — Disables a feature the plan normally includes:
```json
{
  "feature_key":   "stakeholder_engagement",
  "override_type": "revoke",
  "reason":        "Contractual exclusion: using Rimba SEP until December 2027"
}
```

**`limit`** — Overrides a numeric usage quota:
```json
{
  "feature_key":   "max_sms_per_month",
  "override_type": "limit",
  "limit_value":   8000,
  "reason":        "UNICEF WASH programme — 8,000 beneficiary household notifications/month"
}
```

### Response

```json
{
  "id":            "5fa7f3c5-a1b2-4c3d-8e9f-0a1b2c3d4e5f",
  "org_id":        "16449750-e456-4c7f-ab76-0d59b526d7b5",
  "feature_key":   "waiting_queue",
  "override_type": "grant",
  "limit_value":   null,
  "reason":        "MNH OPD pilot — 3-step patient queue",
  "note":          "MoHSW approval ref: MNH/2026/IT/0042",
  "expires_at":    "2026-08-16T00:00:00",
  "granted_by":    "admin-user-uuid",
  "created_at":    "2026-05-18T20:18:44",
  "message":       "Override 'grant' for 'waiting_queue' granted to org 16449750-..."
}
```

### Common enterprise scenarios

| Scenario | override_type | feature_key | limit_value | expires_at |
|----------|--------------|-------------|-------------|------------|
| Hospital pilot: queue management | `grant` | `waiting_queue` | — | 90 days |
| Hospital pilot: AI insights dashboard | `grant` | `ai_insights` | — | 60 days |
| NGO partner: double SMS allowance | `limit` | `max_sms_per_month` | `4000` | — |
| UNICEF programme: high API volume | `limit` | `max_api_calls_per_month` | `50000` | project end date |
| Donor: unlimited submissions | `limit` | `max_submissions_per_month` | `-1` | project end date |
| Contractual: disable SEP module | `revoke` | `stakeholder_engagement` | — | vendor contract end |
| Compliance: force-disable social login | `revoke` | `social_login` | — | — |
| Government: SSO without Enterprise plan | `grant` | `sso` | — | — |
| Beta tester: early ML predictor access | `grant` | `ml_predictor` | — | 30 days |
| Enterprise pre-sales: white-label trial | `grant` | `white_label` | — | 14 days |

---

## `PATCH /subscriptions/admin/orgs/{org_id}/overrides/{override_id}`

**Auth:** Admin Bearer token  
**Summary:** Update an existing override's metadata without revoking and re-creating it.

### Request body (all fields optional)

```json
{
  "reason":      "Extended: 60-day pilot approved by CEO — now 90 days",
  "note":        "Board approval email ref: CEO/2026-05-18. Extension covers AI analysis rollout.",
  "limit_value": 10000,
  "is_active":   true,
  "expires_at":  "2026-08-18T00:00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `reason` | string | Update the override reason |
| `note` | string | Update the internal admin note |
| `limit_value` | integer | Change the limit (only meaningful for `override_type=limit`) |
| `is_active` | boolean | `false` = soft-deactivate without deleting (same effect as DELETE) |
| `expires_at` | ISO datetime \| null | Extend, shorten, or remove the expiry (`null` = permanent) |

### Response

```json
{
  "id":            "5fa7f3c5-...",
  "feature_key":   "ai_insights",
  "override_type": "grant",
  "limit_value":   null,
  "reason":        "Extended: 60-day pilot approved by CEO — now 90 days",
  "note":          "Board approval email ref: CEO/2026-05-18",
  "is_active":     true,
  "expires_at":    "2026-08-18T00:00:00",
  "updated_at":    "2026-05-18T21:00:00"
}
```

---

## `DELETE /subscriptions/admin/orgs/{org_id}/overrides/{override_id}`

**Auth:** Admin Bearer token  
**Summary:** Revoke an active override. The feature immediately reverts to what the plan provides.

This is a **soft delete** (`is_active = false`). The override record is retained for audit purposes and visible via `GET /overrides?active_only=false`.

```
DELETE /api/v1/subscriptions/admin/orgs/{org_id}/overrides/{override_id}
```

### Response

```json
{
  "message": "Override 'waiting_queue' (grant) revoked.",
  "id":      "5fa7f3c5-..."
}
```

After this call, `GET /my/features` will show `waiting_queue.enabled = false` and `waiting_queue.source = "plan"` for this org.

---

---

# Part 4 — Expiry and Idempotency Behaviour

## Override Expiry

Overrides with an `expires_at` in the past are **silently ignored** — they are not deleted, but the feature reverts to its plan value as if the override does not exist. This happens automatically without any scheduled job.

```
expires_at = "2026-05-01T00:00:00"   ← past date
→ feature check returns plan value
→ GET /my/features shows: source="plan"

expires_at = "2026-08-01T00:00:00"   ← future date
→ override is active
→ GET /my/features shows: source="override", override_expires="2026-08-01T00:00:00"

expires_at = null
→ permanent override (no expiry)
```

## Idempotency on Re-Grant

`POST /overrides` with the same `feature_key` and `override_type` as an existing active override:

1. Existing override is set `is_active = false`
2. New override is created with new ID and updated fields
3. Only **one active override** per `(org_id, feature_key, override_type)` at any time

This means re-granting does not stack — the second grant replaces the first.

Different `override_type` values for the same `feature_key` are stored independently. However, a `grant` and a `revoke` for the same feature at the same time is contradictory — the system will apply whichever was created most recently.

---

---

# Part 5 — Live Test Results

Tests run 2026-05-18 against production server (77.237.241.13). Org: `johnsabaskomba@gmail.com` on Professional (trialing).

```
Auth: OK  →  eyJhbGciOiJIUzI1NiIs...

─ A. Muhimbili Hospital: GRANT queue_management + ai_insights ─────────────────
  [PASS] queue_management: NOT enabled on Professional (correct base state)
  [PASS] GRANT waiting_queue  →  expires=2026-08-16
  [PASS] GRANT ai_insights    →  60-day pilot access

─ B. NGO: LIMIT — raise SMS 2,000 → 8,000 (UNICEF WASH) ──────────────────────
  [PASS] Base SMS plan limit confirmed  →  2000 SMS/month (Professional)
  [PASS] LIMIT max_sms_per_month → 8,000
  [PASS] LIMIT max_api_calls_per_month → 50,000

─ C. Contractual REVOKE: disable stakeholder_engagement ────────────────────────
  [PASS] REVOKE stakeholder_engagement  →  contractual exclusion

─ D. Expired Override: grant spark_streaming with past expiry ──────────────────
  [PASS] Created expired override for spark_streaming
  [PASS] Expired override: spark_streaming NOT enabled (correct)  source=plan

─ E. Idempotency: re-grant waiting_queue → replaces previous ───────────────────
  [PASS] Re-granted waiting_queue (updated scope)
  [PASS] New override ID is different from original (not a dup)
  [PASS] Idempotency: only 1 active waiting_queue override  →  expires=2026-09-15

─ F. Usage Metering ────────────────────────────────────────────────────────────
  [PASS] Usage: +47 feedback submissions    ok=True
  [PASS] Usage: +23 SMS sent                ok=True
  [PASS] Usage: +12 QR codes generated      ok=True
  [PASS] Usage: +8 API calls (integration)  ok=True
  [PASS] Usage: +5 MB voice storage         ok=True
  [PASS] Usage shown in /my/features        sms=123/8000  api=8/50000  submissions=47/5000

─ G. Internal Feature-Check (cross-service gating) ────────────────────────────
  [PASS] QR service: qr_generation has_access=True  (plan)
  [PASS] Waiting service: waiting_queue=True         (override, not plan)
  [PASS] Spark: spark_streaming=False                (expired override rejected)
  [PASS] Stakeholder: stakeholder_engagement=False   (contractual revoke honoured)

─ H. Full Entitlement Map ──────────────────────────────────────────────────────
  [PASS] Feature map completeness  →  48 total features
  [PASS] Enabled/disabled split    →  24 enabled  24 disabled
  [PASS] Override-sourced features →  3 via override  45 via plan

  Override-sourced features:
    [GRANT]  ai_insights              expires=2026-07-17  Groq analysis for management board
    [GRANT]  waiting_queue            expires=2026-09-15  MNH OPD + Emergency queue
    [REVOKE] stakeholder_engagement   expires=no expiry   Contractual exclusion (Rimba SEP)

  Limit breakdown:
    max_submissions_per_month   [ ░░░░░░░░░░ ]    47 / 5000
    max_sms_per_month           [ ░░░░░░░░░░ ]   123 / 8000   (OVERRIDE)
    max_api_calls_per_month     [ ░░░░░░░░░░ ]     8 / 50000  (OVERRIDE)
    max_qr_per_month            [ ░░░░░░░░░░ ]    12 / 500
    max_storage_gb              [ ░░░░░░░░░░ ]   0.0 / 25

  [PASS] Active overrides count  →  5 stored
  [PASS] Granted feature is enabled:  ai_insights
  [PASS] Revoked feature is disabled: stakeholder_engagement
  [PASS] Granted feature is enabled:  waiting_queue

─ I. Admin Plan Comparison ─────────────────────────────────────────────────────
  [PASS] Plan comparison fetched  →  8 plans  15 categories

══════════════════════════════════
  Passed: 31   Failed: 0
  ALL PASS ✓
══════════════════════════════════
```

---

---

# Part 6 — Error Reference

| HTTP | `error` code | When |
|------|-------------|------|
| `400` | `NO_ORG` | JWT has no `org_id` claim |
| `401` | `UNAUTHORISED` | Missing or invalid Bearer token |
| `401` | `INVALID_SERVICE_KEY` | `X-Service-Key` header missing or wrong |
| `403` | `FORBIDDEN` | Bearer token present but `org_role` is not OWNER/ADMIN/SUPER_ADMIN |
| `403` | `FEATURE_NOT_AVAILABLE` | `require_feature()` dependency — plan/override does not grant access |
| `404` | `NOT_FOUND` | Override ID not found or belongs to a different org |
| `422` | `VALIDATION_ERROR` | `override_type` is not `grant`/`revoke`/`limit`; missing `feature_key`; missing `limit_value` when `override_type=limit` |
| `500` | `INTERNAL_ERROR` | Unexpected server error |

### `FEATURE_NOT_AVAILABLE` response body

```json
{
  "error":   "FEATURE_NOT_AVAILABLE",
  "message": "Your plan does not include 'webhooks'. Upgrade at /api/v1/plans.",
  "feature": "webhooks"
}
```

---

---

# Part 7 — Plan Feature Comparison

For reference, key feature availability across the four standard plans:

| Feature | Starter | Professional | Business | Enterprise |
|---------|---------|-------------|----------|------------|
| SMS Channel | ✗ | ✓ | ✓ | ✓ |
| WhatsApp Channel | ✗ | ✓ | ✓ | ✓ |
| AI Conversation | ✗ | ✓ | ✓ | ✓ |
| AI Insights | ✗ | ✗ | ✓ | ✓ |
| Phone Call AI (IVR) | ✗ | ✗ | ✓ | ✓ |
| Advanced Analytics | ✗ | ✓ | ✓ | ✓ |
| ML Escalation Predictor | ✗ | ✗ | ✓ | ✓ |
| Real-Time Spark Streaming | ✗ | ✗ | ✓ | ✓ |
| QR Generation | ✗ | ✓ | ✓ | ✓ |
| Product Verification | ✗ | ✓ | ✓ | ✓ |
| AI Counterfeit Analysis | ✗ | ✗ | ✓ | ✓ |
| Staff Verification | ✗ | ✓ | ✓ | ✓ |
| Queue Management | ✗ | ✗ | ✓ | ✓ |
| Stakeholder Engagement | ✗ | ✗ | ✓ | ✓ |
| Translation (63 languages) | ✗ | ✓ | ✓ | ✓ |
| REST API Access | ✗ | ✓ | ✓ | ✓ |
| Webhooks | ✗ | ✗ | ✓ | ✓ |
| OAuth2 PKCE | ✗ | ✓ | ✓ | ✓ |
| Audit Logs | ✗ | ✗ | ✓ | ✓ |
| Mobile Money Payments | ✗ | ✗ | ✓ | ✓ |
| PayPal | ✗ | ✗ | ✓ | ✓ |
| 2FA | ✗ | ✓ | ✓ | ✓ |
| SSO (SAML/OIDC) | ✗ | ✗ | ✗ | ✓ |
| White-Label | ✗ | ✗ | ✗ | ✓ |
| Custom SLA (99.99%) | ✗ | ✗ | ✗ | ✓ |

**Usage limits by plan:**

| Limit | Starter | Professional | Business | Enterprise |
|-------|---------|-------------|----------|------------|
| Team members | 5 | 25 | 100 | Unlimited |
| Projects | 3 | 15 | Unlimited | Unlimited |
| Submissions/month | 500 | 5,000 | Unlimited | Unlimited |
| SMS/month | 200 | 2,000 | 10,000 | Unlimited |
| API calls/month | 0 | 10,000 | 100,000 | Unlimited |
| Storage | 5 GB | 25 GB | 100 GB | Unlimited |
| QR codes/month | 0 | 500 | Unlimited | Unlimited |
| Staff profiles | 0 | 100 | Unlimited | Unlimited |

> **Retrieve live plan data** (including any plans created after this document): `GET /api/v1/plans/compare`
