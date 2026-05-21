# Riviwa — Plans, Pricing & Subscription Management

**Platform:** Grievance & Feedback Management (GRM) SaaS  
**Markets:** Tanzania, East Africa, Global development sector  
**Currency:** USD (primary) · TZS (local) · KES · UGX  
**Version:** 2026 Pricing

---

## 1. Platform Feature List (by Service)

### 1.1 Feedback Management (Core)
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Submit grievance / suggestion / compliment / inquiry | ✓ | ✓ | ✓ | ✓ |
| Feedback categories & sub-categories | ✓ | ✓ | ✓ | ✓ |
| Feedback channels (web, mobile, SMS, WhatsApp, phone, in-app) | ✓ | ✓ | ✓ | ✓ |
| Escalation paths & levels | ✓ | ✓ | ✓ | ✓ |
| Resolution & closure tracking | — | ✓ | ✓ | — |
| Feedback attachments (photos, voice) | ✓ | ✓ | — | ✓ |
| Anonymous submission | ✓ | ✓ | — | — |
| Bulk feedback import | ✓ | ✓ | — | — |
| PAP (Project Affected Persons) registry | ✓ | ✓ | ✓ | ✓ |
| Committee management | ✓ | ✓ | ✓ | ✓ |
| Employee feedback (360°) | ✓ | ✓ | ✓ | ✓ |

### 1.2 AI & Conversation
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| AI conversation (web / mobile) | ✓ | ✓ | — | — |
| AI via SMS | ✓ | ✓ | — | — |
| AI via WhatsApp | ✓ | ✓ | — | — |
| AI via phone call (IVR / TTS) | ✓ | ✓ | — | — |
| Auto-submit at confidence ≥ 0.82 | ✓ | ✓ | — | — |
| Voice message transcription (Whisper / Google STT) | ✓ | ✓ | — | — |
| Multi-language AI (Swahili + English auto-detect) | ✓ | ✓ | ✓ | — |
| AI-powered feedback classification | — | ✓ | — | — |
| AI insights & recommendations | — | ✓ | — | — |
| Knowledge base (Obsidian vault / RAG) | ✓ | ✓ | ✓ | ✓ |

### 1.3 Notifications
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Email notifications | ✓ | ✓ | ✓ | ✓ |
| SMS notifications | ✓ | ✓ | ✓ | ✓ |
| WhatsApp notifications | ✓ | ✓ | ✓ | ✓ |
| Push notifications (mobile) | ✓ | ✓ | ✓ | ✓ |
| In-app notifications | ✓ | ✓ | ✓ | ✓ |
| Scheduled reminders (APScheduler) | ✓ | ✓ | ✓ | ✓ |
| Notification templates (Jinja2) | ✓ | ✓ | ✓ | ✓ |
| Delivery receipts & retry | — | ✓ | — | — |

### 1.4 Analytics & Reporting
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Live dashboard | — | ✓ | — | — |
| KPI calculations (SLA, response time, resolution rate) | — | ✓ | — | — |
| Branch / department analytics | — | ✓ | — | — |
| Trend analysis | — | ✓ | — | — |
| AI-powered insights (Groq) | — | ✓ | — | — |
| Export reports (CSV / PDF) | ✓ | ✓ | — | ✓ |
| Custom report builder | ✓ | ✓ | ✓ | ✓ |
| Spark streaming (real-time hotspot / SLA monitor) | — | ✓ | — | — |
| ML escalation predictor | — | ✓ | — | — |
| Heatmap analytics | — | ✓ | — | — |

### 1.5 QR Code & Product Verification
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| QR code generation (product / receipt / location / service) | ✓ | ✓ | — | ✓ |
| Bulk QR batch generation | ✓ | ✓ | — | ✓ |
| SMS short code (ORG-CODE format) | ✓ | ✓ | — | — |
| Product authenticity verification (AUTHENTIC / ALREADY_USED / UNRECOGNIZED) | — | ✓ | — | — |
| Receipt session verification | ✓ | ✓ | ✓ | — |
| Counterfeit reporting with GPS + photo | ✓ | ✓ | ✓ | — |
| AI counterfeit image analysis (CLIP + Llama 4 Scout) | — | ✓ | — | — |
| Field agent management | ✓ | ✓ | ✓ | ✓ |
| Scan heatmap | — | ✓ | — | — |

### 1.6 Staff & Identity Verification
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Staff profile management (ORG-NNNNN codes) | ✓ | ✓ | ✓ | ✓ |
| Staff identity verification (public endpoint) | — | ✓ | — | — |
| Fraud report filing | ✓ | ✓ | ✓ | — |
| Employee feedback (post-verification) | ✓ | ✓ | — | — |
| Bulk staff CSV import | ✓ | ✓ | — | — |
| Staff analytics | — | ✓ | — | — |

### 1.7 Queue Management
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Multi-step queue flows | ✓ | ✓ | ✓ | ✓ |
| Priority queuing (Redis sorted set) | ✓ | ✓ | ✓ | — |
| ETA alerts (SMS) | ✓ | ✓ | ✓ | — |
| Staff counter sessions | ✓ | ✓ | ✓ | ✓ |
| Inbound SMS queue entry | ✓ | ✓ | — | — |
| APScheduler reminders | ✓ | ✓ | ✓ | ✓ |

### 1.8 Stakeholder Engagement (SEP)
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Stakeholder profiles | ✓ | ✓ | ✓ | ✓ |
| Stage engagement tracking | ✓ | ✓ | ✓ | ✓ |
| Activity logs | ✓ | ✓ | ✓ | ✓ |
| Communication records | ✓ | ✓ | ✓ | ✓ |
| Distribution lists | ✓ | ✓ | ✓ | ✓ |
| Focal person assignment | ✓ | ✓ | ✓ | ✓ |
| Annex 3 (Grievance log) | ✓ | ✓ | ✓ | ✓ |

### 1.9 Integration & API
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| API key management | ✓ | ✓ | ✓ | ✓ |
| OAuth2 PKCE | ✓ | ✓ | ✓ | ✓ |
| Webhook engine | ✓ | ✓ | ✓ | ✓ |
| Widget embed (JS) | ✓ | ✓ | ✓ | ✓ |
| Context sessions | ✓ | ✓ | ✓ | ✓ |
| Audit logs | — | ✓ | — | — |
| Third-party integrations | ✓ | ✓ | ✓ | ✓ |

### 1.10 Organisation & User Management
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Organisation profile | ✓ | ✓ | ✓ | ✓ |
| Team members (invite / remove) | ✓ | ✓ | ✓ | ✓ |
| Role-based access control (RBAC) | ✓ | ✓ | ✓ | ✓ |
| Multi-org switching | ✓ | ✓ | ✓ | — |
| OTP authentication (SMS / Email) | ✓ | ✓ | — | — |
| Social login (Google / Apple / Facebook) | ✓ | ✓ | — | — |
| Fraud detection (Argon2id + score) | — | ✓ | — | — |
| 2FA | ✓ | ✓ | ✓ | ✓ |

### 1.11 Translation
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Auto-translate (63 languages, NLLB-200) | ✓ | ✓ | — | — |
| Language detection | — | ✓ | — | — |
| Translation memory / cache | ✓ | ✓ | — | ✓ |
| Cloud provider fallback (Google / DeepL / Microsoft) | — | ✓ | ✓ | — |

### 1.12 Payment Processing
| Feature | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Payment intents | ✓ | ✓ | ✓ | — |
| AzamPay (Tanzania) | ✓ | ✓ | — | — |
| Selcom (Tanzania) | ✓ | ✓ | — | — |
| M-Pesa Vodacom TZ | ✓ | ✓ | — | — |
| Webhook reconciliation | — | ✓ | ✓ | — |
| Transaction history | — | ✓ | — | — |

---

## 2. Subscription Plans

---

### Plan Overview

| | **Starter** | **Professional** | **Business** | **Enterprise** |
|--|-------------|-----------------|--------------|----------------|
| **Monthly** | $49/mo | $149/mo | $399/mo | Custom |
| **Annual** | $39/mo | $119/mo | $319/mo | Custom |
| **Annual savings** | Save 20% | Save 20% | Save 20% | Negotiated |
| **Free trial** | 14 days | 14 days | 14 days | 30 days |
| **Setup fee** | None | None | None | None |
| **Target** | Small NGOs, CBOs | Mid-size orgs, hospitals | Banks, gov, large corps | Multinationals, donors |
| **Team members** | 5 | 25 | 100 | Unlimited |
| **Projects** | 3 | 15 | Unlimited | Unlimited |
| **Feedback submissions/mo** | 500 | 5,000 | Unlimited | Unlimited |
| **SMS notifications/mo** | 200 | 2,000 | 10,000 | Custom |
| **API calls/mo** | — | 10,000 | 100,000 | Unlimited |
| **Storage** | 5 GB | 25 GB | 100 GB | Custom |
| **Support** | Email | Email + Chat | Priority + Phone | Dedicated CSM |
| **SLA** | 99.5% | 99.9% | 99.95% | 99.99% |

---

### Starter — $49/month · $39/month billed annually

**Best for:** Small NGOs, community-based organisations, local government units

**Core Feedback**
- ✅ Grievance, suggestion, compliment, inquiry
- ✅ Web + mobile submission channels
- ✅ 3 feedback categories
- ✅ Basic escalation (2 levels)
- ✅ Resolution tracking
- ✅ Feedback tracking number (GRV-YYYY-XXXX)
- ✅ 500 submissions/month

**Notifications**
- ✅ Email notifications
- ✅ In-app notifications
- ✅ 200 SMS/month
- ❌ WhatsApp
- ❌ Push notifications

**Analytics**
- ✅ Basic dashboard (submission counts, status)
- ✅ CSV export
- ❌ AI insights
- ❌ Branch analytics
- ❌ Custom reports

**Users & Orgs**
- ✅ 5 team members
- ✅ 3 roles (Admin, Staff, Viewer)
- ✅ OTP login (email + SMS)
- ✅ 3 projects

**AI**
- ❌ AI conversation
- ❌ AI insights

**QR / Verification**
- ❌ QR generation
- ❌ Product verification

**Integrations**
- ❌ API access
- ❌ Webhooks
- ❌ Widget embed

**Payments**
- ❌ Payment processing

---

### Professional — $149/month · $119/month billed annually

**Best for:** Hospitals, universities, utilities, mid-size banks, development projects

Everything in **Starter**, plus:

**Core Feedback**
- ✅ Unlimited feedback categories
- ✅ Escalation (up to 5 levels, dynamic paths)
- ✅ Voice message submissions
- ✅ Photo attachments
- ✅ Employee feedback (360°)
- ✅ PAP registry (Project Affected Persons)
- ✅ 5,000 submissions/month

**Channels**
- ✅ SMS channel (inbound)
- ✅ WhatsApp channel
- ✅ 2,000 SMS notifications/month

**AI**
- ✅ AI conversation (web + mobile)
- ✅ Auto-language detection (Swahili + English)
- ✅ Voice message transcription
- ✅ AI feedback classification

**Analytics**
- ✅ Advanced KPI dashboard
- ✅ Branch / department analytics
- ✅ Trend analysis
- ✅ PDF + CSV export
- ✅ SLA tracking
- ❌ AI-powered insights
- ❌ Custom report builder

**QR & Verification**
- ✅ QR code generation (up to 500/month)
- ✅ Product & receipt verification
- ✅ SMS short codes (ORG-CODE)
- ❌ Bulk QR batch
- ❌ AI counterfeit analysis

**Staff**
- ✅ Staff profiles (up to 100)
- ✅ Staff identity verification
- ✅ Fraud report filing
- ❌ Bulk CSV import

**Users & Orgs**
- ✅ 25 team members
- ✅ Custom roles (RBAC)
- ✅ 15 projects
- ✅ Multi-org switching

**Integrations**
- ✅ API access (10,000 calls/month)
- ✅ API key management
- ✅ Widget embed
- ❌ Webhooks
- ❌ OAuth2

**Notifications**
- ✅ Push notifications
- ✅ WhatsApp notifications
- ✅ Delivery receipts

---

### Business — $399/month · $319/month billed annually

**Best for:** Commercial banks, government ministries, large hospitals, international NGOs

Everything in **Professional**, plus:

**Core Feedback**
- ✅ Unlimited submissions
- ✅ Escalation (unlimited levels, 7 system templates)
- ✅ Committee management
- ✅ Feedback bulk import (CSV)
- ✅ Anonymous submission controls

**Channels**
- ✅ Phone call AI (IVR / TTS)
- ✅ Twilio voice integration
- ✅ 10,000 SMS/month

**AI**
- ✅ AI via SMS, WhatsApp, phone call
- ✅ AI-powered insights (Groq)
- ✅ ML escalation predictor
- ✅ Spark streaming (real-time)

**Analytics**
- ✅ Custom report builder
- ✅ AI-powered insights
- ✅ Hotspot detection (Spark streaming)
- ✅ Live SLA monitor
- ✅ ML escalation predictor

**QR & Verification**
- ✅ Unlimited QR generation
- ✅ Bulk QR batch
- ✅ AI counterfeit analysis (CLIP + Llama 4 Scout)
- ✅ Field agent management
- ✅ Scan heatmap
- ✅ Fake report management

**Staff**
- ✅ Unlimited staff profiles
- ✅ Bulk CSV import
- ✅ Staff analytics

**Queue Management**
- ✅ Multi-step queue flows
- ✅ Priority queuing
- ✅ ETA SMS alerts
- ✅ Staff counter sessions

**Stakeholder Engagement**
- ✅ Full SEP management
- ✅ Activity & communication tracking
- ✅ Distribution lists
- ✅ Focal person assignment
- ✅ Annex 3 (Grievance log)

**Translation**
- ✅ Auto-translation (63 languages)
- ✅ NLLB-200 local model
- ✅ Language detection

**Integrations**
- ✅ 100,000 API calls/month
- ✅ Webhooks (unlimited endpoints)
- ✅ OAuth2 PKCE
- ✅ Third-party integrations
- ✅ Audit logs

**Payments**
- ✅ AzamPay, Selcom, M-Pesa
- ✅ Payment intent tracking
- ✅ Transaction history

**Users**
- ✅ 100 team members
- ✅ Unlimited projects
- ✅ 2FA enforcement
- ✅ Single Sign-On (SSO) — coming Q3 2026

**Support**
- ✅ Priority email + chat
- ✅ Phone support (business hours)
- ✅ Dedicated onboarding session

---

### Enterprise — Custom Pricing

**Best for:** World Bank, UN agencies, governments, multinationals, donor programmes

Everything in **Business**, plus:

- ✅ Unlimited everything
- ✅ Dedicated Riviwa Customer Success Manager
- ✅ White-label option (custom domain, branding, mobile app)
- ✅ Custom SLA (99.99% uptime guarantee)
- ✅ HIPAA-ready configuration
- ✅ On-premise deployment option
- ✅ Custom Kafka topics & event streams
- ✅ Custom AI model fine-tuning
- ✅ Dedicated server cluster
- ✅ SCIM provisioning
- ✅ Custom data retention policies
- ✅ Legal & compliance review
- ✅ Training & workshops for staff
- ✅ Priority 24/7 phone + Slack support
- ✅ Volume SMS pricing negotiated with carrier
- ✅ Custom payment gateway integration

**Pricing:** Contact sales → sales@riviwa.com

---

## 3. Add-ons (Available on all plans)

| Add-on | Price | Description |
|--------|-------|-------------|
| Extra SMS bundle | $10 / 1,000 SMS | Additional SMS notifications or AI conversations |
| Extra team members | $5 / user / month | Beyond plan limit |
| Extra projects | $10 / project / month | Beyond plan limit |
| Extra storage | $5 / 10 GB / month | Beyond plan limit |
| Extra API calls | $5 / 10,000 calls | Beyond plan limit |
| WhatsApp Business API | $25 / month | Requires Meta Business verification |
| Custom AI model | $199 / month | Fine-tune on organisation's own data |
| Dedicated Kafka cluster | $99 / month | Isolated event streaming |
| Extra QR codes | $5 / 500 QR | Beyond plan limit |
| Advanced translation | $15 / month | Cloud provider fallback (Google / DeepL) |
| Phone call AI (IVR) | $0.05 / minute | Twilio voice, billed on usage |
| Data export archive | $20 one-time | Full historical data export (JSON / CSV) |

---

## 4. Payment Methods

### Tanzanian & East African
| Method | Provider | Currencies |
|--------|----------|-----------|
| M-Pesa | Vodacom Tanzania | TZS |
| AzamPay | AzamPay | TZS |
| Selcom | Selcom Mobile | TZS |
| Airtel Money | Airtel Tanzania | TZS |
| CRDB Bank Transfer | Direct bank | TZS |
| NMB Bank Transfer | Direct bank | TZS |

### International
| Method | Provider | Currencies |
|--------|----------|-----------|
| Visa / Mastercard | Stripe | USD, EUR, GBP |
| Visa / Mastercard | Flutterwave | USD, KES, UGX, NGN |
| PayPal | PayPal | USD |
| Bank Wire Transfer | SWIFT | USD, EUR |
| Purchase Order | Enterprise only | USD |

### Billing Cycles
- **Monthly** — Charged on the same date each month
- **Annual** — Charged upfront, 20% discount applied
- **Multi-year** — Enterprise only, negotiated discount up to 35%

---

## 5. Promotions & Discounts

### Launch Promotions

| Promotion | Details | Valid Until |
|-----------|---------|-------------|
| 🎉 **First 3 months — 50% off** | New organisations only. Applies to Starter, Professional, Business. Code: `RIVIWA50` | 2026-12-31 |
| 🌍 **NGO / Donor Discount** | 30% off any plan for verified NGOs and donor-funded projects. Apply via sales team | Ongoing |
| 🏥 **Health Sector Discount** | 25% off Business plan for hospitals and health ministries | Ongoing |
| 🎓 **Education Discount** | 30% off Professional for universities and schools | Ongoing |
| 🤝 **Annual Commitment** | 20% off (built into annual pricing) | Ongoing |
| 🚀 **Referral Programme** | 1 free month for every new org you refer that subscribes | Ongoing |
| 💳 **Pay with M-Pesa** | Additional 5% off when paying via M-Pesa or AzamPay | Ongoing |

### Volume Discounts (Enterprise)
| Active Users | Discount |
|-------------|---------|
| 500–1,000 | 10% |
| 1,001–5,000 | 20% |
| 5,001–10,000 | 30% |
| 10,000+ | Negotiated |

### Coupon Codes
Coupon codes can be applied at checkout. Each code has:
- Discount type: `percentage` | `fixed_amount` | `free_months`
- Duration: `once` | `repeating` | `forever`
- Eligibility: new only | all | specific plan
- Expiry date
- Max redemptions

---

## 6. Trial Policy

| | Detail |
|--|--------|
| Duration | 14 days (30 days for Enterprise) |
| Credit card required | No |
| Full feature access | Yes (plan features unlocked) |
| Submission limit during trial | 100 |
| Conversion | Auto-prompts on day 10. Converts on day 14 if payment added |
| Post-trial | Data retained 30 days, then archived |

---

## 7. Platform Owner (Admin) Management

> Riviwa internal admin panel — accessed by the Riviwa team

### 7.1 Organisation Management
| Action | Description |
|--------|-------------|
| View all organisations | List with plan, status, MRR, last active |
| Create organisation | Manual onboarding for enterprise clients |
| Suspend / reactivate | Immediately lock access or restore |
| Impersonate org | Log in as any org user for support |
| Change plan | Upgrade / downgrade any org's plan |
| Apply discount | One-time or recurring coupon to any org |
| View usage | Real-time submissions, SMS, API calls, storage |
| View billing history | All invoices, payment attempts, failures |
| Export org data | Full JSON / CSV data export |
| Delete organisation | Soft delete with 30-day retention |

### 7.2 Plan Management
| Action | Description |
|--------|-------------|
| Create / edit plans | Name, price, limits, features, billing cycles |
| Set feature flags | Enable / disable features per plan |
| Create promo codes | Percentage, fixed, free months, max redemptions |
| Set usage limits | SMS, API calls, submissions, storage, users |
| Set overage pricing | Price per unit beyond plan limit |
| Archive old plans | Grandfather existing subscribers |
| A/B test pricing | Show different prices to different cohorts |

### 7.3 Billing & Revenue
| Action | Description |
|--------|-------------|
| MRR / ARR dashboard | Monthly recurring and annual recurring revenue |
| Churn report | Cancellations, downgrades, failed payments |
| Payment failure alerts | Retry logic, dunning emails |
| Manual invoice | Issue invoice for bank wire / PO customers |
| Refund processing | Full / partial refunds |
| Tax configuration | VAT / TZS tax rates per country |
| Revenue by plan | Breakdown of revenue by plan tier |
| Failed payment recovery | Automated retry + email dunning sequence |

### 7.4 Subscriptions
| Action | Description |
|--------|-------------|
| View all subscriptions | Filter by plan, status, billing cycle, country |
| Override renewal date | Extend trial, push next billing date |
| Cancel on behalf of org | With optional reason and refund |
| Pause subscription | Suspend billing for up to 3 months (Enterprise) |
| Apply free months | Add complimentary months to any subscription |
| View subscription events | Full audit trail of all plan changes |

### 7.5 Notifications & Communication
| Action | Description |
|--------|-------------|
| Send announcement | Email blast to all orgs or by plan segment |
| Payment reminder | Trigger manual dunning email |
| Plan change notification | Auto-email on upgrade / downgrade |
| Feature announcement | In-app banner to all orgs |

### 7.6 Analytics
| Action | Description |
|--------|-------------|
| Platform-wide KPIs | Total orgs, feedback volume, uptime |
| Plan conversion funnel | Trial → paid conversion rates |
| Feature adoption | Which features are most/least used |
| Geographic distribution | Orgs by country / region |
| SMS / API usage | Platform-wide consumption |

---

## 8. End-User (Organisation) Subscription Management

> Self-serve portal for organisations — just like Shopify's billing portal

### 8.1 Subscribe

**Flow:**
1. Organisation signs up → 14-day free trial starts automatically
2. Dashboard shows trial countdown banner: *"12 days left in your trial — choose a plan"*
3. Click **Upgrade** → Plan comparison page
4. Select plan → Select billing cycle (monthly / annual)
5. Enter promo code (optional)
6. Choose payment method
7. Review order summary → **Confirm & Subscribe**
8. Confirmation email + receipt sent immediately

**Checkout Summary example:**
```
Business Plan — Annual
$319/month × 12 months = $3,828/year
Promo code RIVIWA50: -$191.40 (first 3 months 50% off)
VAT (18%): +$643.03
──────────────────────
Total due today: $4,279.63
Next renewal: 17 May 2027
```

### 8.2 Upgrade

- Click **Upgrade Plan** in Settings → Billing
- Select new plan
- Prorated credit applied for remaining days on current plan
- New plan active immediately
- Email confirmation sent

**Proration example:**
> Upgrading from Professional ($119/mo annual) to Business ($319/mo annual) on day 15 of a 30-day cycle.
> Credit: $119 × 15/30 = $59.50  
> Charged today: $319 – $59.50 = $259.50  
> Next renewal at full Business rate.

### 8.3 Downgrade

- Click **Change Plan** → select lower tier
- Downgrade takes effect at end of current billing period
- Banner shown: *"Your plan will change to Professional on 17 June 2026"*
- Data above new plan limits is preserved (read-only) for 30 days
- Email notification sent

### 8.4 Cancel

- Settings → Billing → **Cancel Subscription**
- Must select cancellation reason (churn survey):
  - Too expensive
  - Missing features
  - Switching to another platform
  - Project ended
  - Other
- Option to **Pause** instead (available on Business/Enterprise — pause up to 3 months, 50% billing reduction)
- Cancellation confirmed via email
- Access continues until end of billing period
- Data retained 30 days post-cancellation, then archived
- Re-subscribe anytime — data restored within 24 hours

### 8.5 Recurring Billing

| Event | Action |
|-------|--------|
| 7 days before renewal | Email reminder with invoice preview |
| Renewal date | Automatic charge via saved payment method |
| Payment success | Receipt emailed, next renewal date updated |
| Payment failure | Retry after 3 days, then 5 days, then 7 days |
| 3rd retry failure | Subscription suspended (read-only mode), dunning email |
| 14 days after suspension | Subscription cancelled, data archived |
| Card expiry approaching | Email alert 30 days before expiry |

### 8.6 Billing Portal (self-serve)

| Action | Where |
|--------|-------|
| View current plan | Settings → Billing → Overview |
| View usage | Settings → Billing → Usage (real-time meters) |
| Download invoices | Settings → Billing → Invoices |
| Update payment method | Settings → Billing → Payment Methods |
| Add backup payment | Settings → Billing → Payment Methods → Add |
| Apply promo code | Settings → Billing → Promotions |
| View payment history | Settings → Billing → Transaction History |
| Request refund | Settings → Billing → Contact Support |
| Switch billing cycle | Settings → Billing → Change Cycle |

### 8.7 Usage Meters (real-time)

Visible in the billing dashboard:

```
Feedback submissions   ████████░░  412 / 500  (82%)
Team members           ███░░░░░░░  3 / 5      (60%)
SMS sent               ██████░░░░  143 / 200  (72%)
Storage                █░░░░░░░░░  0.8 / 5 GB (16%)
Projects               ██░░░░░░░░  1 / 3      (33%)
```

- Warning at 80% usage: orange alert
- Warning at 95% usage: red alert + email
- At 100%: soft block with upgrade prompt (submissions still accepted for 24 hours grace period)

### 8.8 Invoices

Each invoice includes:
- Invoice number (INV-2026-XXXXX)
- Organisation name & address
- Billing period
- Plan name & price
- Add-ons itemised
- Promo code discount (if any)
- Tax (VAT / local tax)
- Total charged
- Payment method used
- Download as PDF

---

## 9. Checkout Flow

```
Step 1: Plan Selection
├─ Monthly / Annual toggle (show savings)
├─ Plan cards (Starter / Professional / Business)
└─ Enterprise → "Contact Sales" button

Step 2: Add-ons (optional)
├─ Extra SMS bundle
├─ Extra team members
└─ Extra storage

Step 3: Promo Code
└─ Text field: "Enter promo code" → Apply

Step 4: Payment Method
├─ M-Pesa (TZ: enter phone number → STK push)
├─ AzamPay (TZ: mobile money)
├─ Selcom (TZ: mobile money)
├─ Visa / Mastercard (Stripe: card form)
└─ Bank Transfer (generate invoice for wire)

Step 5: Review & Confirm
├─ Order summary
├─ Trial end date (if applicable)
├─ Next renewal date
├─ Terms of service checkbox
└─ "Start Subscription" button

Step 6: Confirmation
├─ Success screen
├─ Receipt emailed
└─ Redirect to dashboard
```

---

## 10. Plan Comparison Summary

| Feature | Starter | Professional | Business | Enterprise |
|---------|---------|-------------|----------|------------|
| **Price/month (annual)** | $39 | $119 | $319 | Custom |
| **Free trial** | 14 days | 14 days | 14 days | 30 days |
| **Team members** | 5 | 25 | 100 | Unlimited |
| **Projects** | 3 | 15 | Unlimited | Unlimited |
| **Submissions/mo** | 500 | 5,000 | Unlimited | Unlimited |
| **SMS/mo** | 200 | 2,000 | 10,000 | Custom |
| **API calls/mo** | — | 10,000 | 100,000 | Unlimited |
| **Storage** | 5 GB | 25 GB | 100 GB | Custom |
| Web + mobile feedback | ✅ | ✅ | ✅ | ✅ |
| SMS + WhatsApp channels | ❌ | ✅ | ✅ | ✅ |
| Phone call AI (IVR) | ❌ | ❌ | ✅ | ✅ |
| AI conversation | ❌ | ✅ | ✅ | ✅ |
| AI insights (Groq) | ❌ | ❌ | ✅ | ✅ |
| Email notifications | ✅ | ✅ | ✅ | ✅ |
| Push + WhatsApp notifications | ❌ | ✅ | ✅ | ✅ |
| Basic analytics | ✅ | ✅ | ✅ | ✅ |
| Advanced analytics | ❌ | ✅ | ✅ | ✅ |
| Custom reports | ❌ | ❌ | ✅ | ✅ |
| QR code generation | ❌ | ✅ | ✅ | ✅ |
| Product verification | ❌ | ✅ | ✅ | ✅ |
| AI counterfeit analysis | ❌ | ❌ | ✅ | ✅ |
| Staff verification | ❌ | ✅ | ✅ | ✅ |
| Queue management | ❌ | ❌ | ✅ | ✅ |
| Stakeholder engagement (SEP) | ❌ | ❌ | ✅ | ✅ |
| Translation (63 languages) | ❌ | ❌ | ✅ | ✅ |
| API access | ❌ | ✅ | ✅ | ✅ |
| Webhooks | ❌ | ❌ | ✅ | ✅ |
| OAuth2 + widget embed | ❌ | ✅ | ✅ | ✅ |
| Payment processing (M-Pesa etc.) | ❌ | ❌ | ✅ | ✅ |
| White-label | ❌ | ❌ | ❌ | ✅ |
| Dedicated CSM | ❌ | ❌ | ❌ | ✅ |
| SLA guarantee | 99.5% | 99.9% | 99.95% | 99.99% |
| Support | Email | Email + Chat | Priority + Phone | 24/7 Dedicated |
