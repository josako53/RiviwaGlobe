# Riviwa — Verification Badge Display: Frontend Implementation Guide
**For:** Frontend developers (React.js / Flutter)  
**Date:** 2026-05-20  
**Base URL (production):** `https://api.riviwa.com`  
**Auth service port:** `:8000` (behind Nginx — use base URL only)

---

## What is the verification badge?

A small visual indicator shown on org profiles, product listings, QR scan results, and anywhere an organisation appears publicly. It tells users and customers how trustworthy an org is on the Riviwa platform.

There are two possible badges, and one overrides the other:

| Badge | Color | Label | Condition | What it means |
|-------|-------|-------|-----------|---------------|
| **Verified Business** | Blue `#1d4ed8` | ✓ Verified Business | `is_kyc_verified = true` | Org submitted real business documents, reviewed and approved by Riviwa |
| **Active Subscriber** | Green `#16a34a` | ✓ Active Subscriber | `is_payment_verified = true` AND `is_kyc_verified = false` | Org has an active paid Riviwa subscription |
| *(no badge)* | — | — | Both false | Org has neither paid nor been KYC-verified |

**Priority rule:** If both are true, show only the blue badge. Blue always wins.

---

## The badge endpoint

```
GET /api/v1/orgs/{slug}/badge
```

- **No auth required** — fully public
- `{slug}` is the org's URL slug (e.g., `mnh-hospital`, `crdb-bank`)
- Cache aggressively — badges change rarely (only on payment or KYC approval)

**Response:**
```json
{
  "org_id":              "org-uuid",
  "slug":                "mnh-hospital",
  "display_name":        "Muhimbili National Hospital",
  "logo_url":            "https://...",
  "is_payment_verified": true,
  "is_kyc_verified":     true,
  "kyc_verified_at":     "2026-05-20T09:15:00",
  "verification_level":  "kyc_verified",
  "badge": {
    "show_payment_badge": true,
    "show_kyc_badge":     true,
    "label":  "Verified Business",
    "color":  "blue"
  }
}
```

**`verification_level` values:**

| Value | Meaning |
|-------|---------|
| `"unverified"` | Neither track verified — no badge |
| `"payment_verified"` | Active subscriber — green badge |
| `"kyc_verified"` | KYC approved — blue badge (highest) |

**When `badge.label` is `null`** — render nothing. Do not show an empty badge container.

---

---

# Part 1 — Core badge component

Build one reusable badge component used everywhere. Never build per-screen badge logic.

---

## React.js

### Hook — `useBadge`

```typescript
// hooks/useBadge.ts
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

export interface BadgeData {
  show_payment_badge: boolean;
  show_kyc_badge:     boolean;
  label:  string | null;
  color:  'blue' | 'green' | null;
}

export interface BadgeResponse {
  org_id:              string;
  slug:                string;
  display_name:        string;
  logo_url:            string | null;
  is_payment_verified: boolean;
  is_kyc_verified:     boolean;
  kyc_verified_at:     string | null;
  verification_level:  'unverified' | 'payment_verified' | 'kyc_verified';
  badge:               BadgeData;
}

export const useBadge = (slug: string | null | undefined) =>
  useQuery<BadgeResponse>({
    queryKey:  ['badge', slug],
    queryFn:   () => api.get(`/api/v1/orgs/${slug}/badge`).then(r => r.data),
    enabled:   !!slug,
    staleTime: 5 * 60_000,   // 5 minutes — badges rarely change
    gcTime:    30 * 60_000,  // keep in cache 30 minutes
    retry:     1,
  });
```

### Component — `VerificationBadge`

```tsx
// components/VerificationBadge.tsx
import React from 'react';
import { useBadge } from '@/hooks/useBadge';

type BadgeSize = 'xs' | 'sm' | 'md' | 'lg';

interface Props {
  slug:         string;
  size?:        BadgeSize;
  showTooltip?: boolean;
  className?:   string;
}

const SIZE_CLASSES: Record<BadgeSize, string> = {
  xs: 'text-[10px] px-1.5 py-0.5 gap-0.5',
  sm: 'text-xs    px-2   py-0.5 gap-1',
  md: 'text-sm    px-2.5 py-1   gap-1',
  lg: 'text-base  px-3   py-1.5 gap-1.5',
};

const ICON_SIZES: Record<BadgeSize, number> = {
  xs: 10, sm: 12, md: 14, lg: 16,
};

const COLOR_STYLES = {
  blue:  { bg: '#1d4ed8', text: '#ffffff', border: '#1e40af' },
  green: { bg: '#16a34a', text: '#ffffff', border: '#15803d' },
};

const TOOLTIPS = {
  blue:  'Business identity verified by Riviwa — documents reviewed and approved',
  green: 'Active Riviwa subscriber with a paid plan',
};

export const VerificationBadge: React.FC<Props> = ({
  slug,
  size = 'sm',
  showTooltip = true,
  className = '',
}) => {
  const { data, isLoading } = useBadge(slug);

  // Don't render anything while loading — no skeleton, no placeholder
  if (isLoading || !data?.badge?.label) return null;

  const { badge } = data;
  const color     = badge.color as 'blue' | 'green';
  const styles    = COLOR_STYLES[color];
  const tooltip   = TOOLTIPS[color];

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${SIZE_CLASSES[size]} ${className}`}
      style={{
        backgroundColor: styles.bg,
        color:           styles.text,
        border:          `1px solid ${styles.border}`,
      }}
      title={showTooltip ? tooltip : undefined}
      role="img"
      aria-label={badge.label}
    >
      <svg
        width={ICON_SIZES[size]}
        height={ICON_SIZES[size]}
        viewBox="0 0 16 16"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0zm3.646 4.854-4.5 4.5a.5.5 0 0 1-.707 0l-2-2a.5.5 0 0 1 .707-.707L6.793 8.293l4.147-4.147a.5.5 0 0 1 .707.707z" />
      </svg>
      {badge.label}
    </span>
  );
};

export default VerificationBadge;
```

### Usage across screens

```tsx
// Org profile header
<div className="org-header">
  <img src={org.logo_url} alt={org.display_name} />
  <h1>{org.display_name}</h1>
  <VerificationBadge slug={org.slug} size="md" />
</div>

// Product listing card (compact)
<div className="product-card">
  <h3>{product.name}</h3>
  <span className="seller">{product.org_name}</span>
  <VerificationBadge slug={product.org_slug} size="xs" />
</div>

// Search result row
<div className="search-result">
  <span>{result.display_name}</span>
  <VerificationBadge slug={result.slug} size="sm" showTooltip={false} />
</div>

// QR scan result
<div className="scan-result">
  <h2>{scannedOrg.display_name}</h2>
  <VerificationBadge slug={scannedOrg.slug} size="lg" />
</div>
```

---

## Flutter

### Service — `BadgeService`

```dart
// services/badge_service.dart
import 'package:dio/dio.dart';

class BadgeData {
  final bool showPaymentBadge;
  final bool showKycBadge;
  final String? label;
  final String? color;    // 'blue' | 'green' | null

  const BadgeData({
    required this.showPaymentBadge,
    required this.showKycBadge,
    this.label,
    this.color,
  });

  bool get hasBadge => label != null;
  bool get isKycVerified => color == 'blue';

  factory BadgeData.fromJson(Map<String, dynamic> json) => BadgeData(
    showPaymentBadge: json['show_payment_badge'] as bool? ?? false,
    showKycBadge:     json['show_kyc_badge']     as bool? ?? false,
    label:            json['label']              as String?,
    color:            json['color']              as String?,
  );
}

class BadgeService {
  final Dio _dio;
  final Map<String, Future<BadgeData>> _cache = {};

  BadgeService(this._dio);

  Future<BadgeData> fetchBadge(String slug) {
    // Return cached future if available (prevents duplicate network calls)
    return _cache.putIfAbsent(slug, () async {
      final r = await _dio.get('/api/v1/orgs/$slug/badge');
      return BadgeData.fromJson(r.data['badge'] as Map<String, dynamic>);
    });
  }

  void invalidate(String slug) => _cache.remove(slug);
}
```

### Widget — `VerificationBadge`

```dart
// widgets/verification_badge.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/badge_service.dart';

enum BadgeSize { xs, sm, md, lg }

class VerificationBadge extends StatelessWidget {
  final String slug;
  final BadgeSize size;
  final bool showTooltip;

  const VerificationBadge({
    Key? key,
    required this.slug,
    this.size = BadgeSize.sm,
    this.showTooltip = true,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final svc = context.read<BadgeService>();

    return FutureBuilder<BadgeData>(
      future: svc.fetchBadge(slug),
      builder: (ctx, snap) {
        if (!snap.hasData || !snap.data!.hasBadge) {
          return const SizedBox.shrink();   // no badge — render nothing
        }

        final badge = snap.data!;
        final isBlue = badge.color == 'blue';

        final config = _BadgeConfig.forSize(size);

        final badgeWidget = Container(
          padding: EdgeInsets.symmetric(
            horizontal: config.hPad,
            vertical:   config.vPad,
          ),
          decoration: BoxDecoration(
            color:        isBlue ? const Color(0xFF1d4ed8) : const Color(0xFF16a34a),
            borderRadius: BorderRadius.circular(config.radius),
            border: Border.all(
              color: isBlue ? const Color(0xFF1e40af) : const Color(0xFF15803d),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.verified_rounded,
                color: Colors.white,
                size: config.iconSize,
              ),
              SizedBox(width: config.gap),
              Text(
                badge.label!,
                style: TextStyle(
                  color:      Colors.white,
                  fontSize:   config.fontSize,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.1,
                ),
              ),
            ],
          ),
        );

        if (!showTooltip) return badgeWidget;

        return Tooltip(
          message: isBlue
              ? 'Business identity verified by Riviwa'
              : 'Active Riviwa subscriber',
          child: badgeWidget,
        );
      },
    );
  }
}

class _BadgeConfig {
  final double hPad, vPad, radius, iconSize, gap, fontSize;
  const _BadgeConfig({
    required this.hPad,
    required this.vPad,
    required this.radius,
    required this.iconSize,
    required this.gap,
    required this.fontSize,
  });

  static _BadgeConfig forSize(BadgeSize size) => const {
    BadgeSize.xs: _BadgeConfig(hPad:  6, vPad: 2, radius: 8,  iconSize: 10, gap: 2, fontSize: 10),
    BadgeSize.sm: _BadgeConfig(hPad:  8, vPad: 3, radius: 10, iconSize: 12, gap: 3, fontSize: 11),
    BadgeSize.md: _BadgeConfig(hPad: 10, vPad: 4, radius: 12, iconSize: 14, gap: 4, fontSize: 13),
    BadgeSize.lg: _BadgeConfig(hPad: 12, vPad: 5, radius: 14, iconSize: 16, gap: 4, fontSize: 15),
  }[size]!;
}
```

### Usage in Flutter

```dart
// Org profile
Row(children: [
  Text(org.displayName, style: Theme.of(context).textTheme.headlineSmall),
  const SizedBox(width: 8),
  VerificationBadge(slug: org.slug, size: BadgeSize.md),
])

// Product card
VerificationBadge(slug: product.orgSlug, size: BadgeSize.xs, showTooltip: false)

// QR scan result
VerificationBadge(slug: scannedOrg.slug, size: BadgeSize.lg)
```

---

---

# Part 2 — Where to show the badge

Show the badge in every place where an organisation's name or identity appears to users or customers.

---

## 1. Org public profile page

The most prominent placement. Show the badge next to the org name in the header.

```tsx
// React
<div className="org-profile-header">
  {org.logo_url && <img src={org.logo_url} className="org-logo" />}
  <div className="org-title">
    <h1>{org.display_name}</h1>
    <VerificationBadge slug={org.slug} size="md" />
  </div>
  <p className="org-tagline">{org.tagline}</p>
</div>
```

```dart
// Flutter
Column(
  crossAxisAlignment: CrossAxisAlignment.start,
  children: [
    if (org.logoUrl != null)
      CircleAvatar(backgroundImage: NetworkImage(org.logoUrl!), radius: 32),
    const SizedBox(height: 12),
    Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 8,
      children: [
        Text(org.displayName, style: headlineStyle),
        VerificationBadge(slug: org.slug, size: BadgeSize.md),
      ],
    ),
  ],
)
```

---

## 2. Product listing card

Show badge inline with the seller name — compact (`xs` or `sm`).

```tsx
// React
<div className="product-card">
  <img src={product.image_url} className="product-image" />
  <div className="product-info">
    <h3 className="product-name">{product.name}</h3>
    <div className="product-seller">
      <span>{product.org_display_name}</span>
      <VerificationBadge slug={product.org_slug} size="xs" />
    </div>
    <span className="product-price">{product.price}</span>
  </div>
</div>
```

---

## 3. QR scan result

When a user scans a QR code, the scan result page shows the org that issued it. Use a large badge here — it's a key trust signal at the moment of verification.

```tsx
// React — QR scan result page
const QRScanResult = ({ scannedOrg, verificationResult }) => (
  <div className="scan-result">
    <div className={`scan-status ${verificationResult.status}`}>
      {verificationResult.status === 'AUTHENTIC'    && <span className="authentic">✓ Authentic</span>}
      {verificationResult.status === 'ALREADY_USED' && <span className="warning">⚠ Already Used</span>}
      {verificationResult.status === 'UNRECOGNIZED' && <span className="danger">✗ Unrecognized</span>}
    </div>

    <div className="issuing-org">
      <p className="label">Issued by</p>
      <div className="org-row">
        {scannedOrg.logo_url && <img src={scannedOrg.logo_url} className="org-logo-sm" />}
        <span className="org-name">{scannedOrg.display_name}</span>
        <VerificationBadge slug={scannedOrg.slug} size="md" />
      </div>
    </div>
  </div>
);
```

```dart
// Flutter — QR scan result
Column(
  children: [
    _ScanStatusWidget(status: result.status),
    const SizedBox(height: 16),
    Text('Issued by', style: labelStyle),
    const SizedBox(height: 8),
    Row(
      children: [
        if (org.logoUrl != null)
          CircleAvatar(backgroundImage: NetworkImage(org.logoUrl!), radius: 16),
        const SizedBox(width: 8),
        Text(org.displayName),
        const SizedBox(width: 6),
        VerificationBadge(slug: org.slug, size: BadgeSize.md),
      ],
    ),
  ],
)
```

---

## 4. Search results list

Show badge inline with each result row — `sm` size, no tooltip on mobile.

```tsx
// React
{searchResults.map(result => (
  <div key={result.slug} className="search-row" onClick={() => navigate(`/orgs/${result.slug}`)}>
    <div className="search-row-left">
      {result.logo_url && <img src={result.logo_url} className="search-logo" />}
      <div>
        <p className="search-name">{result.display_name}</p>
        <p className="search-meta">{result.org_type} · {result.country_code}</p>
      </div>
    </div>
    <VerificationBadge slug={result.slug} size="sm" showTooltip={false} />
  </div>
))}
```

---

## 5. Staff identity verification result

When someone scans a staff QR code (`GET /api/v1/staff/verify/{code}`), the result shows which org issued the staff card. Show badge next to the org name.

```tsx
// React
<div className="staff-verify-result">
  <img src={staff.photo_url} className="staff-photo" />
  <h2>{staff.full_name}</h2>
  <p>{staff.job_title} — {staff.department}</p>
  <div className="issuing-org">
    <span>{staff.org_display_name}</span>
    <VerificationBadge slug={staff.org_slug} size="sm" />
  </div>
</div>
```

---

## 6. Feedback submission receipt / confirmation

After a user submits feedback, the confirmation screen shows which org received it. Include the badge.

```tsx
// React
<div className="submission-confirmation">
  <span className="check-icon">✓</span>
  <h2>Feedback submitted</h2>
  <p>Your feedback has been sent to:</p>
  <div className="recipient-org">
    <span>{org.display_name}</span>
    <VerificationBadge slug={org.slug} size="sm" />
  </div>
  <p className="ref">Reference: {submission.reference_code}</p>
</div>
```

---

## 7. Account settings — own org verification status

On the org owner's settings page, show a richer version that explains the badge and links to KYC.

```tsx
// React — verification settings card
const VerificationSettingsCard = () => {
  const { data: verification } = useQuery({
    queryKey: ['verification'],
    queryFn: () => api.get('/api/v1/orgs/my/verification').then(r => r.data),
  });

  return (
    <div className="settings-card">
      <h3>Verification Status</h3>

      {/* Payment verification row */}
      <div className="verify-row">
        <span className={`dot ${verification?.is_payment_verified ? 'green' : 'grey'}`} />
        <div>
          <p className="row-title">Active Subscriber</p>
          <p className="row-desc">
            {verification?.is_payment_verified
              ? `Verified ${formatDate(verification.payment_verified_at)}`
              : 'Subscribe to a plan to earn this badge'}
          </p>
        </div>
        {verification?.is_payment_verified && (
          <VerificationBadge slug={verification.slug} size="sm" />
        )}
      </div>

      {/* KYC verification row */}
      <div className="verify-row">
        <span className={`dot ${verification?.is_kyc_verified ? 'blue' : 'grey'}`} />
        <div>
          <p className="row-title">Verified Business</p>
          <p className="row-desc">
            {verification?.is_kyc_verified
              ? `Approved ${formatDate(verification.kyc_verified_at)}`
              : verification?.kyc_submission
                ? `KYC ${verification.kyc_submission.status.replace('_', ' ')}`
                : 'Submit business documents to earn the blue badge'}
          </p>
        </div>
        {!verification?.is_kyc_verified && (
          <button onClick={() => navigate('/account/verification/kyc')}>
            {verification?.kyc_submission ? 'View status' : 'Apply now'}
          </button>
        )}
        {verification?.is_kyc_verified && (
          <VerificationBadge slug={verification.slug} size="sm" />
        )}
      </div>
    </div>
  );
};
```

---

---

# Part 3 — Caching strategy

The badge endpoint is called from many places. Cache it centrally to avoid redundant network calls.

## React Query — prefetch on org page load

```typescript
// When navigating to any org-related page, prefetch the badge
const queryClient = useQueryClient();

const prefetchBadge = (slug: string) => {
  queryClient.prefetchQuery({
    queryKey:  ['badge', slug],
    queryFn:   () => api.get(`/api/v1/orgs/${slug}/badge`).then(r => r.data),
    staleTime: 5 * 60_000,
  });
};

// In a list component, prefetch all visible org badges at once
useEffect(() => {
  orgs.forEach(org => prefetchBadge(org.slug));
}, [orgs]);
```

## React Query — batch fetch for lists

```typescript
// hooks/useBadges.ts — fetch multiple badges in parallel
export const useBadges = (slugs: string[]) => {
  const queries = useQueries({
    queries: slugs.map(slug => ({
      queryKey:  ['badge', slug],
      queryFn:   () => api.get(`/api/v1/orgs/${slug}/badge`).then(r => r.data),
      staleTime: 5 * 60_000,
      enabled:   !!slug,
    })),
  });

  // Return as a slug → badge map
  return Object.fromEntries(
    slugs.map((slug, i) => [slug, queries[i].data?.badge ?? null])
  );
};

// In a list:
const badges = useBadges(orgs.map(o => o.slug));
// Then: badges['mnh-hospital']?.label
```

## Flutter — invalidate after KYC approval

```dart
// After KYC status changes to approved, invalidate the cached badge
// so the next render fetches the fresh blue badge
ref.read(badgeServiceProvider).invalidate(org.slug);
```

---

---

# Part 4 — Badge in context: full response shapes

## After payment succeeds (green badge)

```json
{
  "is_payment_verified": true,
  "is_kyc_verified":     false,
  "verification_level":  "payment_verified",
  "badge": {
    "show_payment_badge": true,
    "show_kyc_badge":     false,
    "label":  "Active Subscriber",
    "color":  "green"
  }
}
```

## After KYC approved (blue badge)

```json
{
  "is_payment_verified": true,
  "is_kyc_verified":     true,
  "verification_level":  "kyc_verified",
  "badge": {
    "show_payment_badge": true,
    "show_kyc_badge":     true,
    "label":  "Verified Business",
    "color":  "blue"
  }
}
```

Note: `show_payment_badge` stays `true` even when `show_kyc_badge` is `true` — but you only render **one** badge. Use `badge.label` and `badge.color` directly; ignore `show_payment_badge` when `show_kyc_badge` is `true`.

## No badge

```json
{
  "is_payment_verified": false,
  "is_kyc_verified":     false,
  "verification_level":  "unverified",
  "badge": {
    "show_payment_badge": false,
    "show_kyc_badge":     false,
    "label":  null,
    "color":  null
  }
}
```

→ `badge.label === null` → render nothing.

---

---

# Part 5 — Design reference

## Color tokens

```css
/* Badge colors */
--badge-kyc-bg:          #1d4ed8;   /* blue-700 */
--badge-kyc-border:      #1e40af;   /* blue-800 */
--badge-kyc-text:        #ffffff;

--badge-payment-bg:      #16a34a;   /* green-600 */
--badge-payment-border:  #15803d;   /* green-700 */
--badge-payment-text:    #ffffff;
```

## Size reference

| Size | Font | Height | Padding H | Icon | Use case |
|------|------|--------|-----------|------|----------|
| `xs` | 10px | ~18px | 6px | 10px | Product card, dense list |
| `sm` | 11px | ~22px | 8px | 12px | Search results, staff card |
| `md` | 13px | ~26px | 10px | 14px | Org profile, QR scan |
| `lg` | 15px | ~30px | 12px | 16px | Full-width scan result, hero |

## Tailwind classes (if using Tailwind CSS)

```typescript
const BADGE_CLASSES = {
  blue: {
    base: 'inline-flex items-center gap-1 rounded-full font-semibold',
    color: 'bg-blue-700 text-white border border-blue-800',
  },
  green: {
    base: 'inline-flex items-center gap-1 rounded-full font-semibold',
    color: 'bg-green-600 text-white border border-green-700',
  },
};

const SIZE_CLASSES = {
  xs: 'text-[10px] px-1.5 py-0.5',
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-2.5 py-1',
  lg: 'text-base px-3 py-1.5',
};
```

---

---

# Part 6 — Edge cases and gotchas

## Org slug vs org ID

The badge endpoint uses **slug** (`mnh-hospital`), not UUID. If you only have the UUID, fetch the org first to get its slug, or store the slug in your local state when loading org data.

```typescript
// Wrong — UUIDs don't work here
GET /api/v1/orgs/16449750-e456-.../badge  → 404

// Correct
GET /api/v1/orgs/mnh-hospital/badge       → 200
```

## Render nothing — not a placeholder

When `badge.label` is `null`, render `null` / `SizedBox.shrink()`. Do not show an empty grey pill, a lock icon, or "Unverified" text — that draws unnecessary negative attention to unverified orgs. Let the absence of a badge speak for itself.

```tsx
// Wrong
if (!badge.label) return <span className="unverified-badge">Unverified</span>;

// Correct
if (!badge.label) return null;
```

## No loading state

Don't show a skeleton/spinner for badges. The badge is supplementary information — if it hasn't loaded yet, render nothing. It will appear once the query resolves.

```tsx
// Wrong — causes layout shift
if (isLoading) return <SkeletonBadge />;

// Correct
if (isLoading || !data?.badge?.label) return null;
```

## Cache invalidation after KYC approval

When the org's KYC submission is approved, the badge changes from green to blue. Invalidate the cached badge at that moment so the update appears immediately.

```typescript
// In your KYC polling hook, when status changes to 'approved':
queryClient.invalidateQueries({ queryKey: ['badge', org.slug] });
queryClient.invalidateQueries({ queryKey: ['verification'] });
```

## When both tracks are true

Both `show_payment_badge` and `show_kyc_badge` are `true`. Always use `badge.label` and `badge.color` directly — the API has already resolved priority. Never build your own "blue wins" logic client-side; the API handles it.

```typescript
// Wrong — redundant client-side logic
const label = org.is_kyc_verified ? 'Verified Business' : org.is_payment_verified ? 'Active Subscriber' : null;

// Correct — use what the API computed
const label = badge.label;   // already resolved by the server
const color = badge.color;
```

---

---

# Implementation checklist

```
Core component
□ Build VerificationBadge component accepting slug + size props
□ Render nothing when badge.label is null (no loading state, no placeholder)
□ Two colors: blue (#1d4ed8) for kyc_verified, green (#16a34a) for payment_verified
□ Four sizes: xs / sm / md / lg
□ Optional tooltip: "Business identity verified by Riviwa" / "Active Riviwa subscriber"
□ Accessible: role="img", aria-label={badge.label}

Caching
□ staleTime: 5 minutes (badges rarely change)
□ Prefetch badge when navigating to any org page
□ For lists: fetch all visible slugs in parallel (useQueries / Future.wait)
□ Invalidate after KYC approval (queryClient.invalidateQueries / svc.invalidate)

Placements — show badge on:
□ Org public profile page (md size, next to org name)
□ Product listing card (xs size, next to seller name)
□ QR scan result page (md size, in "Issued by" section)
□ Search results list (sm size, trailing)
□ Staff identity verification result (sm size, next to org name)
□ Feedback submission confirmation (sm size, next to recipient org)
□ Account settings / verification status card (sm size, with KYC CTA)

Edge cases
□ slug not UUID — always use org.slug, never org.id
□ render null when badge.label is null — no "Unverified" text
□ no skeleton state — just render nothing until resolved
□ use badge.label + badge.color from API, not client-side logic
```
