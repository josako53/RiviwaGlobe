# Riviwa Platform Monitoring API Reference
**Date:** 2026-05-18  
**Version:** Production

Endpoints for monitoring the health, growth, and revenue of the entire Riviwa platform — across all organisations, subscriptions, users, and countries.

---

## Services & Ports

| Service | Port | Base Path |
|---------|------|-----------|
| **auth_service** | 8000 | `/api/v1` |
| **subscription_service** | 8140 | `/api/v1` |

---

## Authentication

All monitoring endpoints require a valid JWT with **Platform Admin** or **Super Admin** role.

```
Authorization: Bearer <access_token>
```

`platform_role` must be `admin` or `super_admin`. Regular org users receive `403 FORBIDDEN`.

---

---

# Part 1 — auth_service (port 8000)

## Live Platform Statistics

### `GET /api/v1/admin/platform/stats`

**Single-call platform health dashboard** — all user and org counts in one request.

**Auth:** Platform Admin / Super Admin

**Query params:** None

**Response `200`:**
```json
{
  "total_users":     60,
  "active_today":    4,
  "active_7d":       12,
  "active_30d":      39,
  "new_users_today": 0,
  "total_orgs":      35,
  "active_orgs":     31,
  "new_orgs_today":  0,
  "countries_count": 3
}
```

| Field | Description |
|-------|-------------|
| `total_users` | All registered users on the platform |
| `active_today` | Users who logged in since midnight UTC today |
| `active_7d` | Users with a login in the last 7 days |
| `active_30d` | Users with a login in the last 30 days |
| `new_users_today` | User accounts created since midnight UTC today |
| `total_orgs` | All organisations (excluding deleted) |
| `active_orgs` | Organisations with status `ACTIVE` |
| `new_orgs_today` | Organisations created since midnight UTC today |
| `countries_count` | Distinct country codes across all organisations |

**Use case:** Render the platform admin home page KPI cards. Safe to poll every 60 seconds — all counts are direct DB aggregates with no caching.

---

## Organisations by Country

### `GET /api/v1/admin/platform/by-country`

**Organisations and users grouped by country code.**

**Auth:** Platform Admin / Super Admin

**Query params:** None

**Response `200`:**
```json
{
  "countries_count": 4,
  "breakdown": [
    {
      "country_code":     "TZ",
      "org_count":        25,
      "active_orgs":      22,
      "verified_orgs":    22,
      "user_count":       148,
      "active_users_30d": 39,
      "first_registered": "2026-04-10",
      "last_registered":  "2026-05-18"
    },
    {
      "country_code":     "KE",
      "org_count":        5,
      "active_orgs":      4,
      "verified_orgs":    3,
      "user_count":       22,
      "active_users_30d": 8,
      "first_registered": "2026-04-22",
      "last_registered":  "2026-05-10"
    },
    {
      "country_code":     "UG",
      "org_count":        3,
      "active_orgs":      3,
      "verified_orgs":    2,
      "user_count":       11,
      "active_users_30d": 6,
      "first_registered": "2026-05-01",
      "last_registered":  "2026-05-15"
    },
    {
      "country_code":     "UNKNOWN",
      "org_count":        2,
      "active_orgs":      2,
      "verified_orgs":    1,
      "user_count":       4,
      "active_users_30d": 0,
      "first_registered": "2026-04-15",
      "last_registered":  "2026-04-20"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `countries_count` | Total distinct countries |
| `country_code` | ISO 2-letter code (e.g. `TZ`, `KE`, `UG`). `UNKNOWN` = no country set |
| `org_count` | Total orgs in this country |
| `active_orgs` | Orgs with status `ACTIVE` |
| `verified_orgs` | Orgs with `is_verified = true` |
| `user_count` | Distinct users who are members of orgs in this country |
| `active_users_30d` | Of those users, how many logged in within the last 30 days |
| `first_registered` | Date the earliest org in this country was created |
| `last_registered` | Date the most recent org in this country was created |

Results are ordered by `org_count` descending (largest country first).

**Note:** `user_count` counts users via their active org membership. A user in two orgs in different countries is counted in both.

**Use case:** Geographic market expansion view — which countries have the most orgs, which are growing fastest, where engagement is low.

---

## Organisations by Region

### `GET /api/v1/admin/platform/by-region`

**Organisations grouped by administrative region** (from org address records).

**Auth:** Platform Admin / Super Admin

**Query params:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `country_code` | string | No | ISO 2-letter code (e.g. `TZ`). Omit to see all countries. |

**Example requests:**
```
GET /api/v1/admin/platform/by-region                  → all regions, all countries
GET /api/v1/admin/platform/by-region?country_code=TZ  → regions within Tanzania
```

**Response `200`:**
```json
{
  "country_code":  "TZ",
  "total_regions": 5,
  "breakdown": [
    {
      "country_code": "TZ",
      "region":       "Dar es Salaam",
      "org_count":    14
    },
    {
      "country_code": "TZ",
      "region":       "Coast",
      "org_count":    4
    },
    {
      "country_code": "TZ",
      "region":       "Morogoro",
      "org_count":    3
    },
    {
      "country_code": "TZ",
      "region":       "Mwanza",
      "org_count":    2
    },
    {
      "country_code": "TZ",
      "region":       "Arusha",
      "org_count":    2
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `total_regions` | Distinct regions with at least one org address |
| `region` | Administrative region name (e.g. `Dar es Salaam`, `Coast`, `Morogoro`) |
| `org_count` | Orgs with an address record in this region |

Results ordered by `org_count` descending.

**Data source:** `addresses` table where `entity_type = 'organisation'` and `region IS NOT NULL`. Orgs must have an address record with the `region` field populated to appear here. Orgs with no address or no region set do not appear.

**Use case:** Regional distribution of platform adoption. Drill down from country to region for geographic market analysis.

---

---

# Part 2 — subscription_service (port 8140)

## Subscription Overview

### `GET /api/v1/billing/subscriptions/overview`

**Paginated list of all org subscriptions** with plan, billing cycle, renewal date, and cancellation status. The primary monitoring view for customer success teams.

**Auth:** Platform Admin / Super Admin

**Query params:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `status` | string | — | `active` \| `trialing` \| `past_due` \| `paused` \| `cancelled` \| `expired` |
| `plan_slug` | string | — | `starter` \| `professional` \| `business` \| `enterprise` |
| `expiring_days` | int | — | Return only subs whose period ends within the next N days |
| `page` | int | 1 | Page number |
| `size` | int | 50 | Page size (max 100) |

**Example requests:**
```
GET /api/v1/billing/subscriptions/overview                            → all subs
GET /api/v1/billing/subscriptions/overview?status=active              → active only
GET /api/v1/billing/subscriptions/overview?plan_slug=professional     → Pro plan only
GET /api/v1/billing/subscriptions/overview?expiring_days=7            → renewing in 7 days
GET /api/v1/billing/subscriptions/overview?status=past_due            → overdue accounts
```

**Response `200`:**
```json
{
  "total": 17,
  "page":  1,
  "size":  3,
  "items": [
    {
      "subscription_id":       "9fc8cf8a-13c4-4c63-a255-88fe0c78b7be",
      "org_id":                "455bd8b1-ce74-44c7-a571-e5986dd65d17",
      "plan": {
        "slug":         "starter",
        "display_name": "Starter"
      },
      "billing_cycle":         "monthly",
      "status":                "active",
      "current_period_start":  "2026-05-04T10:23:14",
      "current_period_end":    "2026-06-04T10:23:14",
      "days_until_renewal":    17,
      "hours_until_renewal":   407,
      "cancel_at_period_end":  false,
      "will_cancel":           false,
      "effective_monthly_usd": "49.00",
      "discount_pct":          "0",
      "trial_end":             null,
      "created_at":            "2026-05-04T10:23:14"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `subscription_id` | Subscription UUID |
| `org_id` | Organisation UUID |
| `plan` | Plan slug and display name |
| `billing_cycle` | `monthly` or `annual` |
| `status` | Current subscription status |
| `current_period_end` | Next renewal / expiry date (ISO 8601) |
| `days_until_renewal` | Days until the current period ends. Negative = already expired |
| `hours_until_renewal` | Hours until period end (for precision near the deadline) |
| `cancel_at_period_end` / `will_cancel` | `true` = org has cancelled; access ends at `current_period_end` |
| `effective_monthly_usd` | Actual monthly amount charged (after discounts) |
| `discount_pct` | Active discount percentage |
| `trial_end` | Trial end date if subscription is in trialing status |

Items are ordered by `current_period_end` ascending (soonest renewal first).

**Use case:**
- Full subscription roster for finance and customer success
- Filter `expiring_days=3` for a daily renewals digest
- Filter `status=past_due` for dunning/collections queue
- Filter `will_cancel=true` (use `cancel_at_period_end` logic) for churn risk list

---

## Subscriptions Due Soon

### `GET /api/v1/billing/subscriptions/due-soon`

**Subscriptions renewing or expiring within the next N days**, split into `renewing` (will auto-renew) and `cancelling` (org has cancelled — access ends at period end).

**Auth:** Platform Admin / Super Admin

**Query params:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `days` | int | 7 | Look-ahead window (1–90 days) |

**Example requests:**
```
GET /api/v1/billing/subscriptions/due-soon           → renewing in next 7 days
GET /api/v1/billing/subscriptions/due-soon?days=3    → next 3 days (urgent)
GET /api/v1/billing/subscriptions/due-soon?days=30   → monthly view
```

**Response `200`:**
```json
{
  "horizon_days":     30,
  "total":            4,
  "renewing_count":   3,
  "cancelling_count": 1,
  "renewing": [
    {
      "org_id":                "455bd8b1-ce74-44c7-a571-e5986dd65d17",
      "subscription_id":       "9fc8cf8a-13c4-4c63-a255-88fe0c78b7be",
      "plan":                  "starter",
      "plan_display":          "Starter",
      "billing_cycle":         "monthly",
      "status":                "active",
      "renews_at":             "2026-06-04T10:23:14",
      "days_left":             17,
      "hours_left":            407,
      "will_cancel":           false,
      "effective_monthly_usd": "49.00"
    }
  ],
  "cancelling": [
    {
      "org_id":                "b3c4d5e6-...",
      "subscription_id":       "f7a8b9c0-...",
      "plan":                  "professional",
      "plan_display":          "Professional",
      "billing_cycle":         "monthly",
      "status":                "active",
      "renews_at":             "2026-05-25T08:00:00",
      "days_left":             7,
      "hours_left":            167,
      "will_cancel":           true,
      "effective_monthly_usd": "149.00"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `renewing_count` | Orgs that will auto-renew |
| `cancelling_count` | Orgs that will lose access at period end (cancel_at_period_end=true) |
| `renewing` | List of subscriptions that will charge and renew |
| `cancelling` | **At-risk orgs** — access ends at `renews_at`. Contact for win-back. |
| `days_left` | Days until the billing event |
| `hours_left` | Hours until the billing event |

**Use case:**
- **Daily digest:** Run at 08:00 UTC with `days=1` — get today's renewals and access losses
- **Weekly planning:** `days=7` — pipeline of upcoming charges for finance
- **Churn prevention:** `cancelling` list → trigger customer success outreach workflow
- **Revenue forecast:** Sum `effective_monthly_usd` across `renewing` for expected revenue

---

## Plan Distribution

### `GET /api/v1/billing/subscriptions/by-plan`

**Org count and MRR breakdown per subscription plan.**

**Auth:** Platform Admin / Super Admin

**Query params:** None

**Response `200`:**
```json
{
  "total_orgs":    2,
  "total_mrr_usd": "198.00",
  "by_plan": [
    {
      "plan":         "professional",
      "display_name": "Professional",
      "total_orgs":   1,
      "active":       1,
      "trialing":     0,
      "past_due":     0,
      "billing": {
        "monthly": 0,
        "annual":  1
      },
      "mrr_usd": "119.00"
    },
    {
      "plan":         "starter",
      "display_name": "Starter",
      "total_orgs":   1,
      "active":       1,
      "trialing":     0,
      "past_due":     0,
      "billing": {
        "monthly": 1,
        "annual":  0
      },
      "mrr_usd": "49.00"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `total_orgs` | Total orgs across all plans (active + trialing + past_due) |
| `total_mrr_usd` | Platform Monthly Recurring Revenue across all paying plans |
| `by_plan[].mrr_usd` | MRR contribution from this plan (`monthly_price × monthly_orgs + annual_price × annual_orgs`) |
| `by_plan[].active` | Orgs in `active` status on this plan |
| `by_plan[].trialing` | Orgs in `trialing` status on this plan |
| `by_plan[].past_due` | Orgs in `past_due` status (payment failed) |
| `by_plan[].billing.monthly` | Orgs on monthly billing cycle |
| `by_plan[].billing.annual` | Orgs on annual billing cycle |

Results ordered by `total_orgs` descending.

**Note:** `trialing` orgs are included in counts but contribute `$0` to MRR until they convert. `cancelled` and `expired` subscriptions are excluded.

**Use case:**
- **Revenue breakdown:** Understand which plans drive the most MRR
- **Conversion tracking:** Watch trialing counts convert to active
- **Churn impact:** `past_due` count signals payment health
- **Billing cycle mix:** Monthly vs annual ratio (annual = higher retention)

---

---

## Summary — All New Monitoring Endpoints

| # | Service | Method | Endpoint | Purpose |
|---|---------|--------|----------|---------|
| 1 | auth (8000) | GET | `/api/v1/admin/platform/stats` | Total users, active today/7d/30d, total orgs, countries count |
| 2 | auth (8000) | GET | `/api/v1/admin/platform/by-country` | Orgs + users grouped by country code |
| 3 | auth (8000) | GET | `/api/v1/admin/platform/by-region` | Orgs grouped by region (filter by country_code) |
| 4 | sub (8140) | GET | `/api/v1/billing/subscriptions/overview` | All org subscriptions with renewal dates, filterable |
| 5 | sub (8140) | GET | `/api/v1/billing/subscriptions/due-soon` | Upcoming renewals and cancellations by horizon |
| 6 | sub (8140) | GET | `/api/v1/billing/subscriptions/by-plan` | Plan distribution with MRR breakdown |

---

## Related Existing Endpoints

These pre-existing endpoints complement the monitoring suite:

| Service | Endpoint | Purpose |
|---------|----------|---------|
| auth (8000) | `GET /api/v1/admin/dashboard/summary` | Single-call KPIs: user/org counts by status |
| auth (8000) | `GET /api/v1/admin/users/growth?days=30` | Daily user registration trend |
| auth (8000) | `GET /api/v1/admin/organisations/growth?days=30` | Daily org creation trend |
| auth (8000) | `GET /api/v1/admin/organisations/breakdown` | Orgs by type × status |
| sub (8140) | `GET /api/v1/billing/metrics` | MRR, ARR, monthly revenue, churn (last 30d), past-due count |
| sub (8140) | `GET /api/v1/subscriptions/admin/all` | All subscriptions with status filter and pagination |
| sub (8140) | `GET /api/v1/billing/invoices` | All invoices across all orgs with status filter |

---

## Error Reference

| Code | Error | Reason |
|------|-------|--------|
| `401` | `UNAUTHORISED` | Missing or invalid JWT |
| `403` | `FORBIDDEN` | JWT valid but `platform_role` is not `admin` or `super_admin` |
| `500` | `INTERNAL_ERROR` | Server-side error — check service logs |

---

## Live Data (as of 2026-05-18)

From `/admin/platform/stats`:

| Metric | Value |
|--------|-------|
| Total users | 60 |
| Active today | 4 |
| Active last 7 days | 12 |
| Active last 30 days | 39 |
| Total orgs | 35 |
| Active orgs | 31 |
| Countries | 3 |

From `/billing/subscriptions/by-plan`:

| Plan | Active Orgs | Billing | MRR |
|------|-------------|---------|-----|
| Professional | 1 | Annual | $119.00 |
| Starter | 1 | Monthly | $49.00 |
| **Total** | **2** | | **$198.00** |
