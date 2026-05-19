# Riviwa — Subscription, Plans & Payment Implementation Guide
**For:** Frontend developers (React.js / Flutter)  
**Date:** 2026-05-19  
**Base URL (production):** `https://api.riviwa.com`  
**Base URL (dev):** `http://77.237.241.13` or `http://localhost` (via Nginx)

---

## Services involved

| What | Nginx path | Service behind it |
|------|-----------|------------------|
| Auth / Users / Orgs | `/api/v1/auth`, `/api/v1/users`, `/api/v1/orgs` | auth_service :8000 |
| Plans (public) | `/api/v1/plans` | subscription_service :8140 |
| Subscriptions / Checkout | `/api/v1/subscriptions`, `/api/v1/checkout` | subscription_service :8140 |
| Payments | `/api/v1/payments` | payment_service :8040 |

Everything goes through a **single base URL** — Nginx routes to the correct service. Frontend never talks to service ports directly.

---

## Authentication pattern (applies to every step)

Every authenticated request needs:
```
Authorization: Bearer <access_token>
```

The JWT carries two critical claims:
- `sub` — user ID
- `org_id` — the organisation the user is currently acting as (switches via `POST /auth/switch-org`)

When `org_id` is present in the token, all subscription and billing calls are scoped to that organisation automatically.

---

---

# Step 1 — Login and get a token

**When:** App launch, or when `401` is received.

## 1a. Submit credentials

```
POST /api/v1/auth/login
```
```json
{ "identifier": "user@hospital.co.tz", "password": "SecurePass123" }
```

**Response:**
```json
{ "login_token": "eyJ...", "requires_otp": true }
```

## 1b. Verify OTP

```
POST /api/v1/auth/login/verify-otp
```
```json
{ "login_token": "eyJ...", "otp_code": "123456" }
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type":   "bearer",
  "org_id":       "16449750-e456-...",
  "org_role":     "OWNER"
}
```

Store `access_token` in secure storage. Use it in every subsequent request.

## 1c. If user belongs to multiple orgs — switch context

```
POST /api/v1/auth/switch-org
Authorization: Bearer <token>
```
```json
{ "org_id": "16449750-e456-..." }
```

Returns a new `access_token` with the selected `org_id` baked in. All subscription calls after this are scoped to that org.

---

### React.js — auth hook skeleton

```typescript
// hooks/useAuth.ts
const login = async (identifier: string, password: string) => {
  const { login_token } = await post("/api/v1/auth/login", { identifier, password });
  const { access_token } = await post("/api/v1/auth/login/verify-otp", {
    login_token,
    otp_code: await promptOTP(),   // show OTP dialog
  });
  localStorage.setItem("token", access_token);
  api.defaults.headers["Authorization"] = `Bearer ${access_token}`;
};
```

### Flutter — auth skeleton

```dart
// services/auth_service.dart
Future<String> login(String identifier, String password) async {
  final r1 = await dio.post('/api/v1/auth/login',
      data: {'identifier': identifier, 'password': password});
  final loginToken = r1.data['login_token'];

  final otp = await showOtpDialog();    // your OTP input widget
  final r2 = await dio.post('/api/v1/auth/login/verify-otp',
      data: {'login_token': loginToken, 'otp_code': otp});

  final token = r2.data['access_token'];
  dio.options.headers['Authorization'] = 'Bearer $token';
  await secureStorage.write(key: 'token', value: token);
  return token;
}
```

---

---

# Step 2 — Check the org's current subscription

**When:** App startup, after login, after switching org.  
**Rule:** Always check this before rendering the app shell. It tells you what the org can and cannot do.

```
GET /api/v1/subscriptions/current
Authorization: Bearer <token>
```

**Possible responses:**

### A — No subscription yet (brand new org)
```json
{ "has_subscription": false, "subscription": null }
```
→ Show onboarding / "Start free trial" screen.

### B — On trial
```json
{
  "has_subscription": true,
  "subscription": {
    "status":       "trialing",
    "plan":         { "slug": "professional", "display_name": "Professional" },
    "trial_end":    "2026-06-01T00:00:00",
    "billing_cycle": "monthly"
  },
  "usage": {
    "sms":           { "used": 23,  "limit": 2000 },
    "submissions":   { "used": 47,  "limit": 5000 },
    "api_calls":     { "used": 8,   "limit": 10000 },
    "storage_bytes": { "used": 5242880, "limit": 26843545600 },
    "qr_codes":      { "used": 12,  "limit": 500 },
    "team_members":  { "used": 3,   "limit": 25 }
  }
}
```
→ Show trial banner with countdown. Prompt to subscribe before `trial_end`.

### C — Active paid subscription
```json
{
  "has_subscription": true,
  "subscription": {
    "status":           "active",
    "plan":             { "slug": "business", "display_name": "Business" },
    "current_period_end": "2026-06-18T00:00:00",
    "billing_cycle":   "monthly"
  }
}
```
→ Normal app flow.

### D — Past due / paused / cancelled
```json
{ "subscription": { "status": "past_due" } }
```
→ Show payment recovery banner. Restrict access to core features only.

---

### React.js

```typescript
// hooks/useSubscription.ts
const { data: sub } = useQuery("subscription", () =>
  api.get("/api/v1/subscriptions/current").then(r => r.data)
);

// In your app shell:
if (!sub?.has_subscription) return <StartTrialScreen />;
if (sub.subscription.status === "past_due") return <PaymentRequiredBanner />;
if (sub.subscription.status === "trialing") {
  const daysLeft = differenceInDays(new Date(sub.subscription.trial_end), new Date());
  showTrialBanner(`${daysLeft} days left in your free trial`);
}
```

### Flutter

```dart
// In initState or Provider
final sub = await api.get('/api/v1/subscriptions/current');
if (!sub['has_subscription']) {
  Navigator.pushNamed(context, '/start-trial');
} else if (sub['subscription']['status'] == 'past_due') {
  showPaymentRecoveryBanner();
}
```

---

---

# Step 3 — Fetch and display plans

**When:** Onboarding screen, upgrade/downgrade flow, pricing page.

## 3a. List all public plans

```
GET /api/v1/plans
```
No auth required. Returns Starter, Professional, Business, Enterprise.

**Response:**
```json
{
  "plans": [
    {
      "id":           "plan-uuid",
      "slug":         "professional",
      "display_name": "Professional",
      "tagline":      "AI-powered GRM for growing organisations",
      "pricing": {
        "monthly_usd":        "49.00",
        "annual_usd":         "39.00",
        "annual_total_usd":   "468.00",
        "annual_savings_pct": 20,
        "is_custom":          false
      },
      "trial_days": 14,
      "limits": {
        "team_members": 25, "projects": 15,
        "submissions_per_month": 5000, "sms_per_month": 2000,
        "api_calls_per_month": 10000, "storage_gb": 25,
        "qr_per_month": 500, "staff_profiles": 100
      },
      "features": {
        "sms_channel": true, "whatsapp_channel": true,
        "ai_conversation": true, "ai_insights": false,
        "qr_generation": true, "webhooks": false
      },
      "sla": "99.9%"
    }
  ]
}
```

## 3b. Side-by-side plan comparison (pricing page)

```
GET /api/v1/plans/compare
```
Returns every feature in a matrix — ideal for building a feature comparison table.

```json
{
  "plans": [ ... ],
  "comparison": {
    "AI & Intelligence": [
      {
        "key":   "ai_insights",
        "label": "AI-Powered Insights",
        "plans": {
          "starter": false, "professional": false,
          "business": true, "enterprise": true
        }
      }
    ]
  },
  "categories": ["Feedback Channels", "AI & Intelligence", ...]
}
```

## 3c. Preview exact price before checkout

```
POST /api/v1/subscriptions/billing-preview
```
```json
{
  "plan_id":       "plan-uuid",
  "billing_cycle": "annual",
  "promo_code":    "LAUNCH2026"
}
```

**Response:**
```json
{
  "summary": {
    "subtotal_usd":  "468.00",
    "discount_usd":  "140.40",
    "tax_usd":       "58.97",
    "total_usd":     "386.57"
  },
  "line_items": [
    { "description": "Professional — Annual (12 × $39)", "amount_usd": "468.00" },
    { "description": "Promo: Riviwa Launch Offer (30%)", "amount_usd": "-140.40" },
    { "description": "VAT (18%)", "amount_usd": "58.97" }
  ],
  "promo":      { "code": "LAUNCH2026", "label": "30% off for 3 months" },
  "trial_days": 14
}
```

Use this response to build an order summary / price breakdown component before the user clicks "Pay".

---

---

# Step 4 — Start a free trial

**When:** New org, `has_subscription = false`.  
**Rule:** Always start a trial before asking for payment. The trial gives full Professional features for 14 days with no card required.

```
POST /api/v1/subscriptions/trial
Authorization: Bearer <token>
```
```json
{ "plan_slug": "professional" }
```

**Response:**
```json
{
  "subscription": {
    "status":     "trialing",
    "trial_end":  "2026-06-02T00:00:00"
  },
  "trial_end": "2026-06-02T00:00:00",
  "message":   "14-day free trial started on Professional. Trial ends 2026-06-02."
}
```

After this call:
- Update your subscription state cache
- Show trial banner with days remaining
- The org has full Professional feature access immediately

---

### React.js

```typescript
const startTrial = async () => {
  const { subscription, trial_end } = await api.post(
    "/api/v1/subscriptions/trial",
    { plan_slug: "professional" }
  ).then(r => r.data);

  queryClient.invalidateQueries("subscription");
  showToast(`Free trial started! Ends ${format(new Date(trial_end), "dd MMM yyyy")}`);
};
```

---

---

# Step 5 — Feature-gated UI (what to show / hide)

**When:** Once subscription is active or trialing. Call this once at startup and cache it.

```
GET /api/v1/subscriptions/my/features
Authorization: Bearer <token>
```

**Response structure:**
```json
{
  "subscription_status": "trialing",
  "plan":     { "slug": "professional", "display_name": "Professional" },
  "features": [
    {
      "key":     "ai_insights",
      "label":   "AI-Powered Insights",
      "enabled": false,
      "source":  "plan"
    },
    {
      "key":     "waiting_queue",
      "label":   "Queue Management",
      "enabled": true,
      "source":  "override",
      "override_reason": "MNH pilot programme"
    }
  ],
  "limits": [
    {
      "key":             "max_sms_per_month",
      "effective_limit": 2000,
      "used":            123,
      "pct_used":        6.2,
      "source":          "plan"
    }
  ],
  "overrides": []
}
```

### How to use features in the UI

```typescript
// utils/features.ts
type FeatureMap = Record<string, boolean>;

export function buildFeatureMap(entitlements: any): FeatureMap {
  return Object.fromEntries(
    entitlements.features.map((f: any) => [f.key, f.enabled])
  );
}

// In your component:
const { data: entitlements } = useQuery("features",
  () => api.get("/api/v1/subscriptions/my/features").then(r => r.data)
);
const features = buildFeatureMap(entitlements);

// Show/hide feature:
{features.ai_insights && <AIInsightsDashboard />}

// Show upgrade prompt for locked features:
{!features.stakeholder_engagement && (
  <UpgradeBanner
    feature="Stakeholder Engagement (SEP)"
    requiredPlan="Business"
    onUpgrade={() => navigate("/billing/upgrade")}
  />
)}
```

### Limits / usage meters

```typescript
// Show a usage bar for SMS:
const smsLimit = entitlements.limits.find(l => l.key === "max_sms_per_month");

<UsageMeter
  label="SMS this month"
  used={smsLimit.used}
  limit={smsLimit.effective_limit}   // -1 = unlimited
  pct={smsLimit.pct_used}
  warning={smsLimit.pct_used >= 80}  // orange at 80%
  danger={smsLimit.pct_used >= 95}   // red at 95%
/>
```

### Flutter

```dart
// providers/entitlement_provider.dart
class EntitlementProvider extends ChangeNotifier {
  Map<String, bool> _features = {};
  Map<String, dynamic> _limits = {};

  Future<void> load() async {
    final r = await api.get('/api/v1/subscriptions/my/features');
    _features = Map.fromEntries(
      (r.data['features'] as List).map((f) => MapEntry(f['key'] as String, f['enabled'] as bool))
    );
    notifyListeners();
  }

  bool can(String featureKey) => _features[featureKey] ?? false;
}

// In widget:
if (context.read<EntitlementProvider>().can('qr_generation'))
  ElevatedButton(onPressed: generateQR, child: Text('Generate QR'))
else
  UpgradePromptWidget(feature: 'QR Generation', plan: 'Professional')
```

---

---

# Step 6 — Checkout (subscribe to a plan)

**When:** User clicks "Subscribe", "Upgrade to Business", or trial is expiring.

## 6a. Check for active sales / validate promo code (optional)

**Active sale — auto-applied, no action needed:**  
If a sale campaign is running (e.g., "Launch Week — 40% OFF"), it auto-applies at checkout when you omit `promo_code`. The checkout response will include a `sale_applied` field.

**Promo code — validate before checkout:**
```
POST /api/v1/promotions/validate
```
```json
{ "code": "LAUNCH2026", "plan_slug": "professional", "org_id": "org-uuid" }
```
Response: `{ "valid": true, "discount_label": "30% off for 3 months" }`

Use this to show the discount preview in the UI before the user clicks "Pay". Then include `promo_code` in the checkout body.

## 6b. Initiate checkout

```
POST /api/v1/checkout
Authorization: Bearer <token>
```

### Request body (M-Pesa / Vodacom TZ)
```json
{
  "plan_id":       "plan-uuid",
  "billing_cycle": "monthly",
  "provider":      "mpesa",
  "phone_number":  "+255712345678",
  "payer_name":    "John Komba",
  "payer_email":   "john@hospital.co.tz",
  "promo_code":    "LAUNCH2026",
  "save_method":   true
}
```

### Request body (PayPal — international USD)
```json
{
  "plan_id":       "plan-uuid",
  "billing_cycle": "annual",
  "provider":      "paypal",
  "payer_email":   "john@hospital.co.tz",
  "payer_name":    "Muhimbili Hospital"
}
```

### Request body (Bank transfer)
```json
{
  "plan_id":       "plan-uuid",
  "billing_cycle": "monthly",
  "provider":      "bank_transfer"
}
```

## 6c. Handle response by provider

### Mobile money (M-Pesa / AzamPay / Selcom / Airtel / Yas)

```json
{
  "subscription_id": "sub-uuid",
  "payment_id":      "pay-uuid",
  "payment": {
    "provider": "mpesa",
    "status":   "pending",
    "message":  "USSD prompt sent to your phone. Enter your PIN to complete payment."
  }
}
```

→ Show "Check your phone for the M-Pesa prompt" screen.  
→ Poll `GET /api/v1/checkout/status/{payment_id}` every 3 seconds for up to 60 seconds.

### PayPal

```json
{
  "checkout_url": "https://www.sandbox.paypal.com/checkoutnow?token=...",
  "payment": {
    "provider": "paypal",
    "message":  "Redirect to PayPal: https://..."
  }
}
```

→ Open `checkout_url` in a WebView or browser.  
→ When PayPal redirects back to your app (or the `return_url`), poll `GET /api/v1/checkout/status/{payment_id}`.

### Bank transfer

```json
{
  "payment": {
    "provider":     "bank_transfer",
    "instructions": "Transfer USD 149.00 to Riviwa. Reference: INV-2026-001234. Send proof to billing@riviwa.com."
  },
  "invoice": {
    "invoice_number": "INV-2026-001234",
    "total_usd":      "175.82",
    "due_date":       "2026-05-21T00:00:00"
  }
}
```

→ Show bank details and invoice number.  
→ Admin manually confirms. `is_payment_verified` is set via `PATCH /admin/orgs/{id}/payment-verification`.

---

---

# Step 7 — Poll for payment confirmation

```
GET /api/v1/checkout/status/{payment_id}
Authorization: Bearer <token>
```

**Response when pending:**
```json
{ "payment_status": "pending", "paid": false, "subscription_active": false }
```

**Response when paid:**
```json
{ "payment_status": "paid", "paid": true, "subscription_active": true }
```

When `paid: true`:
1. Subscription status is now `active`
2. `is_payment_verified` is automatically set on the org (no extra call needed)
3. Invalidate your subscription and features cache
4. Navigate to success screen

### React.js — polling hook

```typescript
const pollPayment = async (paymentId: string): Promise<boolean> => {
  const maxAttempts = 20;  // 20 × 3s = 60 seconds max
  for (let i = 0; i < maxAttempts; i++) {
    await sleep(3000);
    const { paid } = await api.get(`/api/v1/checkout/status/${paymentId}`)
      .then(r => r.data);
    if (paid) {
      queryClient.invalidateQueries(["subscription", "features"]);
      return true;
    }
  }
  return false;  // timeout — show "check back later" message
};

// In your checkout screen:
const checkout = async () => {
  setStep("processing");
  const { payment_id, checkout_url, payment } = await api.post("/api/v1/checkout", body)
    .then(r => r.data);

  if (payment.provider === "paypal" && checkout_url) {
    window.open(checkout_url);   // or Linking.openURL in React Native
  }

  const paid = await pollPayment(payment_id);
  if (paid) {
    setStep("success");
    navigate("/dashboard");
  } else {
    setStep("timeout");
  }
};
```

### Flutter — checkout flow

```dart
Future<void> checkout(Map<String, dynamic> body) async {
  setState(() => step = 'processing');

  final r = await api.post('/api/v1/checkout', data: body);
  final paymentId = r.data['payment_id'];
  final checkoutUrl = r.data['checkout_url'];

  if (checkoutUrl != null) {
    await launchUrl(Uri.parse(checkoutUrl));  // opens PayPal / Selcom
  }

  // Poll for confirmation
  for (int i = 0; i < 20; i++) {
    await Future.delayed(Duration(seconds: 3));
    final status = await api.get('/api/v1/checkout/status/$paymentId');
    if (status.data['paid'] == true) {
      ref.invalidate(subscriptionProvider);
      ref.invalidate(featuresProvider);
      setState(() => step = 'success');
      return;
    }
  }
  setState(() => step = 'timeout');
}
```

---

---

# Step 8 — Post-payment state

After `paid: true`, these things are true automatically — **no extra API calls needed**:

| What | Where it's set | How frontend sees it |
|------|---------------|---------------------|
| Subscription `status = active` | subscription_service | `GET /subscriptions/current` → `status: "active"` |
| `is_payment_verified = true` | auth_service (auto) | `GET /orgs/{slug}/badge` → `is_payment_verified: true` |
| All plan features unlocked | subscription_service | `GET /subscriptions/my/features` → all plan flags enabled |
| "Active Subscriber" badge | auth_service | `GET /orgs/{slug}/badge` → `badge.label: "Active Subscriber"` |

### Fetch verification badge (for public profile display)

```
GET /api/v1/orgs/{slug}/badge
```
No auth required. Use on product listings, org pages, QR scan results.

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

```tsx
// VerificationBadge component
const VerificationBadge = ({ slug }: { slug: string }) => {
  const { data: badge } = useQuery(["badge", slug],
    () => api.get(`/api/v1/orgs/${slug}/badge`).then(r => r.data.badge)
  );

  if (badge?.show_kyc_badge)
    return <Badge color="blue" icon="✓" label="Verified Business" />;
  if (badge?.show_payment_badge)
    return <Badge color="green" icon="✓" label="Active Subscriber" />;
  return null;
};
```

---

---

# Step 9 — KYC verification (Verified Business badge)

**When:** Org wants the blue "Verified Business" badge shown on public profiles.  
**KYC is independent of payment** — an org can be KYC-verified on any plan.

## 9a. Check current KYC status

```
GET /api/v1/orgs/my/verification
Authorization: Bearer <token>
```

Returns `is_kyc_verified`, `kyc_rejection_reason`, and the latest submission status.

## 9b. Submit KYC documents

Two options — use whichever fits your UI:

### Option A: File picker (direct upload — recommended)

```
POST /api/v1/orgs/my/kyc/submit
Authorization: Bearer <token>
Content-Type: application/json
```
```json
{
  "business_type":   "GOVERNMENT",
  "reg_number":      "MNH/MOH/TZ/REG/1956/001",
  "tax_id":          "TIN-100-234-567",
  "notes_for_admin": "State hospital under MoHSW. World Bank tender deadline 30 May.",
  "documents": []
}
```

Then upload each file:

```
POST /api/v1/orgs/my/kyc/documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<binary>          (PDF / JPEG / PNG / DOCX — max 15 MB)
document_type=business_license
```

Valid `document_type` values:
`business_license` | `certificate_of_incorporation` | `tax_clearance` | `tax_id` |  
`directors_national_id` | `utility_bill` | `bank_statement` |  
`memorandum_of_association` | `audited_accounts` | `other`

### React.js — file upload

```typescript
const uploadKYCDoc = async (file: File, documentType: string) => {
  const form = new FormData();
  form.append("file", file);
  form.append("document_type", documentType);

  const { document } = await api.post(
    "/api/v1/orgs/my/kyc/documents/upload",
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  ).then(r => r.data);

  return document;  // { id, file_name, file_url, document_type }
};
```

### Flutter

```dart
Future<Map> uploadKycDocument(File file, String documentType) async {
  final form = FormData.fromMap({
    'document_type': documentType,
    'file': await MultipartFile.fromFile(
      file.path,
      filename: path.basename(file.path),
      contentType: MediaType('application', 'pdf'),
    ),
  });

  final r = await dio.post('/api/v1/orgs/my/kyc/documents/upload', data: form);
  return r.data['document'];
}
```

## 9c. Track submission status

```
GET /api/v1/orgs/my/kyc
Authorization: Bearer <token>
```

| `status` | Meaning | Show user |
|---------|---------|-----------|
| `pending` | Submitted, waiting for admin | "Submitted — review within 2-3 business days" |
| `under_review` | Admin has opened it | "Under review by Riviwa team" |
| `more_info` | Admin wants more docs | Show `rejection_reason` + upload button |
| `approved` | KYC passed | "KYC Verified ✓" — fetch badge |
| `rejected` | KYC failed | Show `rejection_reason` + re-submit button |

## 9d. After approval — badge becomes "Verified Business"

```
GET /api/v1/orgs/{slug}/badge
```
```json
{
  "is_kyc_verified": true,
  "badge": {
    "label": "Verified Business",
    "color": "blue"
  }
}
```

---

---

# Step 10 — Plan management

## Upgrade

```
POST /api/v1/subscriptions/upgrade
Authorization: Bearer <token>
```
```json
{ "plan_id": "business-plan-uuid" }
```

Response includes a prorated invoice. Upgrade is immediate — new features unlocked instantly.

## Downgrade

```
POST /api/v1/subscriptions/downgrade
Authorization: Bearer <token>
```
```json
{ "plan_id": "professional-plan-uuid" }
```

Takes effect at the end of the current billing period. Show `effective_at` date in the UI.

## Cancel

```
POST /api/v1/subscriptions/cancel
Authorization: Bearer <token>
```
```json
{
  "reason":    "Too expensive for our budget",
  "immediate": false
}
```

`immediate: false` = cancel at period end (recommended). `immediate: true` = cancel now (access revoked).

## Switch billing cycle (monthly ↔ annual)

```
POST /api/v1/subscriptions/switch-billing-cycle
Authorization: Bearer <token>
```
```json
{ "billing_cycle": "annual" }
```

Monthly → annual: charges prorated difference immediately, unlocks 20% saving.  
Annual → monthly: takes effect at next renewal.

## Pause subscription (Business/Enterprise only)

```
POST /api/v1/subscriptions/pause
Authorization: Bearer <token>
```
```json
{ "reason": "Staff strike — no operations for 2 weeks" }
```

Access is frozen at current state. No new charges during pause. Resume within the plan's allowed pause window.

## Resume subscription

```
POST /api/v1/subscriptions/resume
Authorization: Bearer <token>
```
No body required. Billing resumes from resume date.

---

## Apply promo code

```
POST /api/v1/subscriptions/apply-promo
Authorization: Bearer <token>
```
```json
{ "code": "NGO50" }
```

```json
{
  "message":         "Promo code 'NGO50' applied — 50% off for 9999 month(s).",
  "discount_pct":    "50.00",
  "discount_months": 9999
}
```

## Get invoices

```
GET /api/v1/subscriptions/invoices?page=1&size=20
Authorization: Bearer <token>
```

```json
{
  "invoices": [
    {
      "invoice_number": "INV-2026-001234",
      "status":         "paid",
      "total_usd":      "175.82",
      "paid_at":        "2026-05-18T20:30:00"
    }
  ]
}
```

## Pay an overdue invoice

```
POST /api/v1/checkout/pay-invoice/{invoice_id}
Authorization: Bearer <token>
```
```json
{ "provider": "mpesa", "phone_number": "+255712345678" }
```

---

---

# Step 11 — Subscription event history

Show a timeline of billing events in the account settings.

```
GET /api/v1/subscriptions/events
Authorization: Bearer <token>
```

```json
{
  "events": [
    { "event_type": "trial_started",     "created_at": "2026-05-04T..." },
    { "event_type": "subscribed",        "created_at": "2026-05-18T..." },
    { "event_type": "payment_succeeded", "created_at": "2026-05-18T..." }
  ]
}
```

Event types: `trial_started`, `subscribed`, `upgraded`, `downgraded`, `cancelled`,
`paused`, `resumed`, `payment_succeeded`, `payment_failed`, `promo_applied`.

---

---

# Complete flow diagram

```
────────────────────────────────────────────────────────────────────────
 AUTHENTICATION
────────────────────────────────────────────────────────────────────────
App launch
    │
    ▼
POST /auth/login                          → returns login_token
    │
    ▼
POST /auth/login/verify-otp               → returns access_token  ← store this
    │
    ▼  (user has multiple orgs?)
POST /auth/switch-org                     → returns new access_token scoped to org
    │
    ▼

────────────────────────────────────────────────────────────────────────
 SUBSCRIPTION STATE CHECK  (run on every app start)
────────────────────────────────────────────────────────────────────────
    │
    ▼
GET /subscriptions/current
    │
    ├── has_subscription=false ──────────────────────────────────────────┐
    │                                                                    │
    ├── status=past_due ─────────────────────────── show recovery UI    │
    │                     POST /checkout/pay-invoice/{id}               │
    │                                                                    │
    ├── status=paused ──────────────────────────── show resume UI       │
    │                     POST /subscriptions/resume                    │
    │                                                                    │
    └── status=trialing / active ────────────────────────────────────┐  │
                                                                     │  │
                                                                     │  ▼
────────────────────────────────────────────────────────────────────────
 ONBOARDING (new org, no subscription)
────────────────────────────────────────────────────────────────────────
                                                                        │
GET /plans                                → show pricing page           │
GET /plans/compare                        → show feature matrix         │
                                                                        │
POST /subscriptions/trial                                               │
    └─ { "plan_slug": "professional" }    → status=trialing, 14 days   │
       ┌──────────────────────────────────────────────────────────────┘ │
       │                                                                │
────────────────────────────────────────────────────────────────────────
 CHECKOUT FLOW  (trial expiring, or new subscriber)
────────────────────────────────────────────────────────────────────────
       │
       ▼
GET /plans                                → user selects plan + billing_cycle
       │
       ▼
POST /promotions/validate (optional)      → validate promo code, show discount preview
       │  (or auto-sale applies at checkout if active)
       ▼
POST /subscriptions/billing-preview       → show exact breakdown before payment
    └─ { plan_id, billing_cycle, promo_code }
       │
       ▼
POST /checkout
    └─ { plan_id, billing_cycle, provider, phone/email, promo_code }
       │
       ├── provider=mpesa/azampay/selcom/airtel/yas
       │     → USSD prompt to phone
       │     → poll GET /checkout/status/{payment_id}  every 3s × 20 attempts
       │
       ├── provider=paypal
       │     → open checkout_url in browser/WebView
       │     → on return URL, poll GET /checkout/status/{payment_id}
       │
       └── provider=bank_transfer
             → show invoice_number + wire instructions
             → admin confirms manually via PATCH /admin/orgs/{id}/payment-verification
       │
       ▼  (paid=true from poll or bank confirm)
is_payment_verified=true  ← set automatically on org

────────────────────────────────────────────────────────────────────────
 ACTIVE SUBSCRIPTION
────────────────────────────────────────────────────────────────────────
       │
       ▼
GET /subscriptions/my/features            → build feature gate map (cache this)
       │
       ├── feature.enabled=true  → show the feature
       ├── feature.enabled=false → show upgrade prompt with suggestedPlan
       └── source="override"     → custom deal, show as normal
       │
GET /orgs/{slug}/badge                    → display verification badge
       ├── is_payment_verified → green "Active Subscriber" badge
       └── is_kyc_verified     → blue "Verified Business" badge  (overrides green)

────────────────────────────────────────────────────────────────────────
 KYC FLOW  (optional — earn "Verified Business" badge)
────────────────────────────────────────────────────────────────────────
       │
POST /orgs/my/kyc/submit                  → create submission
POST /orgs/my/kyc/documents/upload ×N     → upload docs (PDF/JPEG/PNG ≤15MB each)
GET  /orgs/my/kyc                         → poll status
       │
       ├── pending       → "Submitted — review within 2-3 business days"
       ├── under_review  → "Under review by Riviwa team"
       ├── more_info     → show rejection_reason + upload more docs → loops back
       ├── approved      → badge becomes "Verified Business" / blue ✓
       └── rejected      → show rejection_reason + re-submit button

────────────────────────────────────────────────────────────────────────
 PLAN MANAGEMENT (account settings)
────────────────────────────────────────────────────────────────────────
       │
       ├── POST /subscriptions/upgrade              → immediate, prorated invoice
       ├── POST /subscriptions/downgrade            → at period end, show effective_at
       ├── POST /subscriptions/switch-billing-cycle → monthly ↔ annual
       ├── POST /subscriptions/apply-promo          → apply code to active sub
       ├── POST /subscriptions/pause                → freeze (Business/Enterprise only)
       ├── POST /subscriptions/resume               → unfreeze
       ├── POST /subscriptions/cancel               → at period end or immediate
       ├── GET  /subscriptions/invoices             → billing history
       └── GET  /subscriptions/events               → audit timeline
```

---

---

# Error reference

| HTTP | Error code | When | What to show |
|------|-----------|------|-------------|
| `401` | `UNAUTHORISED` | Token missing/expired | Redirect to login |
| `400` | `NO_ORG` | Not in org context | Prompt to switch org |
| `402` | `PAYMENT_REQUIRED` | Plan requires payment | Show upgrade/checkout screen |
| `403` | `FEATURE_NOT_AVAILABLE` | Feature not in plan | Show upgrade prompt with `feature` name |
| `404` | `NOT_FOUND` | Plan/invoice/sub not found | Show "not found" |
| `409` | `CONFLICT` | Already has subscription | Show current subscription |
| `409` | `SUBMISSION_UNDER_REVIEW` | KYC already under review | Show current status |
| `422` | `VALIDATION_ERROR` | Missing field | Show field error |
| `422` | `UPLOAD_ERROR` | Wrong file type / too large | "PDF, JPEG, PNG only — max 15 MB" |
| `503` | `PAYMENT_GATEWAY_ERROR` | Provider unavailable | "Try again or use a different payment method" |

### Handle 403 FEATURE_NOT_AVAILABLE

```json
{
  "error":   "FEATURE_NOT_AVAILABLE",
  "message": "Your plan does not include 'webhooks'. Upgrade at /api/v1/plans.",
  "feature": "webhooks"
}
```

```typescript
// Intercept 403 in axios
api.interceptors.response.use(null, (error) => {
  if (error.response?.status === 403) {
    const { error: code, feature } = error.response.data;
    if (code === "FEATURE_NOT_AVAILABLE") {
      showUpgradeModal({ feature, suggestedPlan: "Business" });
      return;
    }
  }
  return Promise.reject(error);
});
```

---

---

# Add-ons (extra capacity)

Add-ons give extra capacity on top of plan limits without requiring an upgrade.

```
GET /api/v1/plans/addons
```

| Slug | Name | Price | Adds |
|------|------|-------|------|
| `extra-sms-1k` | Extra SMS Bundle | $10 | 1,000 SMS |
| `extra-users-5` | Extra Team Members | $25 | 5 seats |
| `extra-storage-10g` | Extra Storage | $5 | 10 GB |
| `extra-api-10k` | Extra API Calls | $5 | 10,000 calls |
| `extra-qr-500` | Extra QR Codes | $5 | 500 QR/month |
| `whatsapp-biz` | WhatsApp Business API | $25/mo | Meta-verified sender |
| `custom-ai` | Custom AI Model | $199/mo | Fine-tuned model |

Include in checkout:
```json
{
  "plan_id": "...",
  "billing_cycle": "monthly",
  "provider": "mpesa",
  "addons": [
    { "slug": "extra-sms-1k", "quantity": 2 }
  ]
}
```

---

---

# Promo codes available for testing

| Code | Discount | Applies to |
|------|---------|-----------|
| `LAUNCH2026` | 30% off × 3 months | All plans — new subscribers |
| `ANNUAL20` | 20% off | Annual plans only |
| `NGO50` | 50% off forever | Starter plan — NGOs only (limit: 100) |
| `GOV30` | 30% off forever | Professional/Business/Enterprise — government |
| `PARTNER25` | 25% off × 6 months | Professional/Business |
| `WELCOME1` | 1 free month | All plans — new subscribers |

---

---

# Quick-start checklist

```
Authentication
□ 1.  POST /auth/login                          → get login_token
□ 2.  POST /auth/login/verify-otp               → get access_token  ← use in all headers
□ 3.  POST /auth/switch-org (if multi-org)       → get org-scoped token

Subscription state
□ 4.  GET  /subscriptions/current               → branch by status (see Step 2)

New org — onboarding
□ 5.  GET  /plans                               → show pricing page
□ 6.  GET  /plans/compare                       → show feature comparison table
□ 7.  POST /subscriptions/trial                 → start 14-day free trial

Feature gates (run after trial starts OR after payment)
□ 8.  GET  /subscriptions/my/features           → build feature gate map, cache it

Checkout
□ 9.  POST /promotions/validate (optional)      → show discount preview
□ 10. POST /subscriptions/billing-preview       → show exact price before paying
□ 11. POST /checkout                            → initiate payment (mpesa/paypal/bank)
□ 12. GET  /checkout/status/{payment_id}        → poll every 3s until paid=true
□ 13. GET  /subscriptions/my/features           → refresh feature map after payment

Verification badges
□ 14. GET  /orgs/{slug}/badge                   → show green "Active Subscriber" badge

KYC (optional — blue "Verified Business" badge)
□ 15. POST /orgs/my/kyc/submit                  → start submission
□ 16. POST /orgs/my/kyc/documents/upload ×N     → upload each document
□ 17. GET  /orgs/my/kyc                         → poll status until approved
□ 18. GET  /orgs/{slug}/badge                   → badge is now blue "Verified Business"

Ongoing plan management
□ 19. POST /subscriptions/upgrade               → move to higher plan
□ 20. POST /subscriptions/switch-billing-cycle  → monthly → annual (20% saving)
□ 21. POST /subscriptions/apply-promo           → apply promo code to active sub
□ 22. GET  /subscriptions/invoices              → billing history
□ 23. GET  /subscriptions/events                → full audit timeline
```
