# Riviwa Platform — API Endpoints, Data Flow & Client Integration Guide

> **Base URL**: `https://api.riviwa.com/api/v1`
> **Auth**: JWT Bearer token on all protected endpoints
> **Content-Type**: `application/json`

---

## Table of Contents

1. [Authentication Flow](#1-authentication-flow)
2. [Auth Service Endpoints](#2-auth-service-endpoints-port-8000)
3. [Feedback Service Endpoints](#3-feedback-service-endpoints-port-8090)
4. [Stakeholder Service Endpoints](#4-stakeholder-service-endpoints-port-8070)
5. [Notification Service Endpoints](#5-notification-service-endpoints-port-8060)
6. [Payment Service Endpoints](#6-payment-service-endpoints-port-8040)
7. [Translation Service Endpoints](#7-translation-service-endpoints-port-8050)
8. [Kafka Event-Driven Data Flow](#8-kafka-event-driven-data-flow)
9. [Client Integration Guide (ReactJS & Flutter)](#9-client-integration-guide-reactjs--flutter)
10. [Error Handling](#10-error-handling)

---

## 1. Authentication Flow

All API calls (except registration, login, and public endpoints) require a JWT access token.

### 1.1 Registration (3-step)

```
Step 1: POST /auth/register/init         → sends OTP to email/phone
Step 2: POST /auth/register/verify-otp   → verifies OTP, returns continuation token
Step 3: POST /auth/register/complete     → sets password, activates account
```

**Step 1 — Initiate Registration**
```json
POST /api/v1/auth/register/init
{
  "identifier": "+255700000000",
  "channel": "sms"
}
// Response: { "session_token": "abc...", "otp_channel": "sms", "expires_in_seconds": 300 }
```

**Step 2 — Verify OTP**
```json
POST /api/v1/auth/register/verify-otp
{
  "session_token": "abc...",
  "otp_code": "000000"
}
// Response: { "continuation_token": "xyz...", "identifier": "+255700000000" }
```

**Step 3 — Complete Registration**
```json
POST /api/v1/auth/register/complete
{
  "continuation_token": "xyz...",
  "password": "MySecure@123",
  "display_name": "John Doe",
  "username": "johndoe"
}
// Response: { "action": "complete", "message": "Account created successfully." }
```

### 1.2 Login (2-step with OTP)

```
Step 1: POST /auth/login            → verifies credentials, sends OTP
Step 2: POST /auth/login/verify-otp → verifies OTP, returns JWT tokens
```

**Step 1 — Submit Credentials**
```json
POST /api/v1/auth/login
{
  "identifier": "+255700000000",
  "password": "MySecure@123"
}
// Response: { "login_token": "abc...", "otp_channel": "sms", "otp_destination": "+255***000", "expires_in_seconds": 300 }
```

**Step 2 — Verify OTP**
```json
POST /api/v1/auth/login/verify-otp
{
  "login_token": "abc...",
  "otp_code": "000000"
}
// Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "opaque-refresh-token-string",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 1.3 Token Refresh

```json
POST /api/v1/auth/token/refresh
{
  "refresh_token": "opaque-refresh-token-string"
}
// Response: { "access_token": "eyJ...", "refresh_token": "new-opaque-token", "token_type": "bearer", "expires_in": 1800 }
```

### 1.4 Using the Token

All subsequent requests include the header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 1.5 JWT Payload Structure

```json
{
  "sub": "user-uuid",
  "jti": "unique-token-id",
  "iat": 1700000000,
  "exp": 1700001800,
  "platform_role": "user"
}
```

---

## 2. Auth Service Endpoints (Port 8000)

### Authentication & Registration

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register/init` | No | Initiate registration (send OTP) |
| POST | `/auth/register/verify-otp` | No | Verify registration OTP |
| POST | `/auth/register/complete` | No | Complete registration (set password) |
| POST | `/auth/register/resend-otp` | No | Resend OTP (60s cooldown) |
| POST | `/auth/login` | No | Login step 1 (credentials + OTP dispatch) |
| POST | `/auth/login/verify-otp` | No | Login step 2 (verify OTP, get tokens) |
| POST | `/auth/token/refresh` | No | Refresh access token |
| POST | `/auth/token/logout` | Yes | Revoke session |
| POST | `/auth/social` | No | OAuth login (Google/Apple/Facebook) |
| POST | `/auth/social/set-password` | Yes | Set password on OAuth account |
| POST | `/auth/switch-org` | Yes | Switch active organisation context |

### Password Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/password/forgot` | No | Initiate password reset |
| POST | `/auth/password/forgot/verify-otp` | No | Verify reset OTP |
| POST | `/auth/password/forgot/reset` | No | Set new password |
| POST | `/auth/password/change` | Yes | Change password (authenticated) |

### User Profile

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users/me` | Yes | Get own profile |
| PATCH | `/users/me` | Yes | Update profile fields |
| DELETE | `/users/me` | Yes | Deactivate account |
| POST | `/users/me/avatar` | Yes | Update avatar URL |
| POST | `/users/me/verify-email` | Yes | Mark email verified |
| POST | `/users/me/verify-phone` | Yes | Mark phone verified |

### Organisations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/orgs` | Yes | List organisations (search & filter) |
| POST | `/orgs` | Yes | Create organisation (caller = OWNER) |
| GET | `/orgs/{org_id}` | Yes | Get organisation detail |
| PATCH | `/orgs/{org_id}` | Yes | Update organisation |
| DELETE | `/orgs/{org_id}` | Yes | Deactivate organisation |
| POST | `/orgs/{org_id}/members` | Yes | Add member directly |
| DELETE | `/orgs/{org_id}/members/{user_id}` | Yes | Remove member |
| PATCH | `/orgs/{org_id}/members/{user_id}/role` | Yes | Change member role |
| POST | `/orgs/{org_id}/transfer-ownership` | Yes | Transfer OWNER role |
| POST | `/orgs/{org_id}/invites` | Yes | Send invite |
| POST | `/orgs/invites/{invite_id}/accept` | Yes | Accept invite |
| POST | `/orgs/invites/{invite_id}/decline` | Yes | Decline invite |
| DELETE | `/orgs/{org_id}/invites/{invite_id}` | Yes | Cancel invite |
| POST | `/orgs/{org_id}/logo` | Yes | Upload logo |

### Organisation Extended (Locations, Branches, Services)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/orgs/{org_id}/locations` | Yes | Add location |
| GET | `/orgs/{org_id}/locations` | Yes | List locations |
| PATCH | `/orgs/{org_id}/locations/{loc_id}` | Yes | Update location |
| DELETE | `/orgs/{org_id}/locations/{loc_id}` | Yes | Remove location |
| POST | `/orgs/{org_id}/branches` | Yes | Create branch |
| GET | `/orgs/{org_id}/branches` | Yes | List branches |
| PATCH | `/orgs/{org_id}/branches/{branch_id}` | Yes | Update branch |
| POST | `/orgs/{org_id}/services` | Yes | Create service listing |
| GET | `/orgs/{org_id}/services` | Yes | List services |
| PATCH | `/orgs/{org_id}/services/{svc_id}` | Yes | Update service |
| POST | `/orgs/{org_id}/services/{svc_id}/publish` | Yes | Publish service |

### Projects

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/orgs/{org_id}/projects` | Yes | Create project |
| GET | `/orgs/{org_id}/projects` | Yes | List projects |
| GET | `/orgs/{org_id}/projects/{proj_id}` | Yes | Project detail |
| PATCH | `/orgs/{org_id}/projects/{proj_id}` | Yes | Update project |
| POST | `/orgs/{org_id}/projects/{proj_id}/activate` | Yes | Activate (publish) project |
| POST | `/orgs/{org_id}/projects/{proj_id}/pause` | Yes | Pause project |
| POST | `/orgs/{org_id}/projects/{proj_id}/resume` | Yes | Resume project |
| POST | `/orgs/{org_id}/projects/{proj_id}/complete` | Yes | Mark complete |
| POST | `/orgs/{org_id}/projects/{proj_id}/stages` | Yes | Add stage |
| PATCH | `/orgs/{org_id}/projects/{proj_id}/stages/{stage_id}` | Yes | Update stage |
| POST | `/orgs/{org_id}/projects/{proj_id}/stages/{stage_id}/activate` | Yes | Activate stage |
| POST | `/orgs/{org_id}/projects/{proj_id}/stages/{stage_id}/complete` | Yes | Complete stage |

### Checklists

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/projects/{proj_id}/checklists` | Yes | Create checklist item |
| GET | `/projects/{proj_id}/checklists` | Yes | List checklist items |
| PATCH | `/projects/{proj_id}/checklists/{item_id}` | Yes | Update item |
| POST | `/projects/{proj_id}/checklists/{item_id}/mark-done` | Yes | Mark done |
| GET | `/projects/{proj_id}/checklist-health` | Yes | Checklist health metrics |

### Admin Dashboard (requires `platform_role: admin` or `super_admin`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin/dashboard/summary` | Admin | Platform KPIs |
| GET | `/admin/users` | Admin | User list with search |
| GET | `/admin/users/growth` | Admin | Registration trend (chart) |
| GET | `/admin/users/status-breakdown` | Admin | Users by status (pie chart) |
| GET | `/admin/users/{user_id}` | Admin | User detail |
| POST | `/admin/users/{user_id}/suspend` | Admin | Suspend user |
| POST | `/admin/users/{user_id}/ban` | Admin | Ban user |
| POST | `/admin/users/{user_id}/reactivate` | Admin | Reactivate user |
| GET | `/admin/organisations` | Admin | Org list |
| GET | `/admin/organisations/pending` | Admin | Verification queue |
| GET | `/admin/organisations/breakdown` | Admin | Org type breakdown |
| GET | `/admin/organisations/growth` | Admin | Org creation trend |
| GET | `/admin/organisations/{org_id}` | Admin | Org detail |
| POST | `/admin/organisations/{org_id}/verify` | Admin | Approve org |
| POST | `/admin/organisations/{org_id}/suspend` | Admin | Suspend org |
| POST | `/admin/organisations/{org_id}/ban` | Admin | Ban org |
| GET | `/admin/projects` | Admin | Cross-org projects |
| GET | `/admin/projects/summary` | Admin | Project analytics |
| GET | `/admin/security/fraud` | Admin | Fraud summary |
| GET | `/admin/security/flagged-users` | Admin | Flagged accounts |
| GET | `/admin/staff` | Admin | Platform staff list |
| POST | `/admin/staff/{user_id}/roles` | SuperAdmin | Assign role |
| DELETE | `/admin/staff/{user_id}/roles/{role}` | SuperAdmin | Revoke role |
| GET | `/admin/checklist-health` | Admin | Platform checklist metrics |
| GET | `/admin/recent-actions` | Admin | Moderation log |

---

## 3. Feedback Service Endpoints (Port 8090)

### GRM Feedback (Staff)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/feedback` | Yes | Submit feedback (grievance/suggestion/applause) |
| GET | `/feedback` | Yes | List feedback (search, filter, paginate) |
| GET | `/feedback/{id}` | Yes | Feedback detail with full action history |
| PATCH | `/feedback/{id}/acknowledge` | Yes | Acknowledge receipt |
| PATCH | `/feedback/{id}/assign` | Yes | Assign to staff/committee |
| POST | `/feedback/{id}/escalate` | Yes | Escalate to next GRM level |
| POST | `/feedback/{id}/resolve` | Yes | Record resolution |
| POST | `/feedback/{id}/appeal` | Yes | File appeal |
| PATCH | `/feedback/{id}/close` | Yes | Close (final state) |
| PATCH | `/feedback/{id}/dismiss` | Yes | Dismiss feedback |
| POST | `/feedback/{id}/actions` | Yes | Log action |
| GET | `/feedback/{id}/actions` | Yes | List action log |

### PAP (Project-Affected Person) Self-Service

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/my/feedback` | Yes | List my submissions |
| GET | `/my/feedback/summary` | Yes | My feedback dashboard |
| GET | `/my/feedback/{id}` | Yes | Track specific submission |
| POST | `/my/feedback` | Yes | Submit new feedback |
| POST | `/my/feedback/{id}/escalation-request` | Yes | Request escalation |
| POST | `/my/feedback/{id}/appeal` | Yes | File appeal |
| POST | `/my/feedback/{id}/add-comment` | Yes | Add follow-up comment |

### Escalation Requests (Staff)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/escalation-requests` | Yes | List escalation requests |
| POST | `/escalation-requests/{id}/approve` | Yes | Approve escalation |
| POST | `/escalation-requests/{id}/reject` | Yes | Reject escalation |

### Categories

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/categories` | Yes | Create category |
| GET | `/categories` | Yes | List categories |
| GET | `/categories/summary` | Yes | Category counts |
| GET | `/categories/{id}` | Yes | Category detail |
| PATCH | `/categories/{id}` | Yes | Update category |
| POST | `/categories/{id}/deactivate` | Yes | Deactivate |
| POST | `/categories/{id}/merge` | Yes | Merge categories |
| POST | `/feedback/{id}/classify` | Yes | Run ML classification |
| PATCH | `/feedback/{id}/recategorise` | Yes | Manual recategorise |

### Committees (GHC)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/committees` | Yes | Create committee |
| GET | `/committees` | Yes | List committees |
| PATCH | `/committees/{id}` | Yes | Update committee |
| POST | `/committees/{id}/members` | Yes | Add member |
| DELETE | `/committees/{id}/members/{user_id}` | Yes | Remove member |

### Channel Sessions (SMS/WhatsApp)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/channel-sessions` | Yes | Start two-way session |
| GET | `/channel-sessions` | Yes | List sessions |
| GET | `/channel-sessions/{id}` | Yes | Session with transcript |
| POST | `/channel-sessions/{id}/message` | Yes | Add message, get LLM reply |
| POST | `/channel-sessions/{id}/submit` | Yes | Force-submit feedback |
| POST | `/channel-sessions/{id}/abandon` | Yes | Abandon session |

### Voice

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/voice/upload` | Yes | Upload voice recording |
| GET | `/voice/{id}` | Yes | Get recording + transcription |
| POST | `/voice/{id}/transcribe` | Yes | Trigger transcription |

### Reports

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/reports/summary` | Yes | Feedback summary by type/status |
| GET | `/reports/trend` | Yes | Daily/weekly/monthly trend |
| GET | `/reports/sla` | Yes | SLA compliance metrics |
| GET | `/reports/export` | Yes | Export CSV/Excel |

---

## 4. Stakeholder Service Endpoints (Port 8070)

### Stakeholders

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/stakeholders` | Yes | Register stakeholder |
| GET | `/stakeholders` | Yes | List with filters |
| GET | `/stakeholders/analysis` | Yes | Stakeholder analysis matrix |
| GET | `/stakeholders/{id}` | Yes | Detail with contacts |
| PATCH | `/stakeholders/{id}` | Yes | Update profile |
| DELETE | `/stakeholders/{id}` | Yes | Soft-delete |
| POST | `/stakeholders/{id}/projects` | Yes | Register under project |
| GET | `/stakeholders/{id}/projects` | Yes | List project registrations |
| GET | `/stakeholders/{id}/engagements` | Yes | Engagement history |
| POST | `/stakeholders/{id}/contacts` | Yes | Add contact |
| GET | `/stakeholders/{id}/contacts` | Yes | List contacts |
| PATCH | `/stakeholders/{id}/contacts/{cid}` | Yes | Update contact |
| DELETE | `/stakeholders/{id}/contacts/{cid}` | Yes | Deactivate contact |

### Activities

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/activities` | Yes | Create engagement activity |
| GET | `/activities` | Yes | List activities |
| GET | `/activities/{id}` | Yes | Detail with attendance |
| PATCH | `/activities/{id}` | Yes | Update / mark conducted |
| POST | `/activities/{id}/attendances` | Yes | Log attendance |
| POST | `/activities/{id}/attendances/bulk` | Yes | Bulk log attendance |
| PATCH | `/activities/{id}/attendances/{eid}` | Yes | Update attendance |
| DELETE | `/activities/{id}/attendances/{eid}` | Yes | Delete attendance |
| POST | `/activities/{id}/cancel` | Yes | Cancel activity |
| POST | `/activities/{id}/media` | Yes | Upload media |
| GET | `/activities/{id}/media` | Yes | List media |
| DELETE | `/activities/{id}/media/{mid}` | Yes | Delete media |

### Communications

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/communications` | Yes | Log communication |
| GET | `/communications` | Yes | List communications |
| GET | `/communications/{id}` | Yes | Communication detail |
| POST | `/communications/{id}/distributions` | Yes | Log distribution |
| PATCH | `/communications/{id}/distributions/{did}` | Yes | Update distribution |

### Focal Persons

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/focal-persons` | Yes | Register focal person |
| GET | `/focal-persons` | Yes | List focal persons |
| PATCH | `/focal-persons/{id}` | Yes | Update focal person |

### Reports

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/reports/stakeholder/engagement-summary` | Yes | Activity counts by stage/LGA |
| GET | `/reports/stakeholder/stakeholder-reach` | Yes | Counts by category |
| GET | `/reports/stakeholder/pending-distributions` | Yes | Pending distributions |
| GET | `/reports/stakeholder/pending-concerns` | Yes | Unresolved concerns |

---

## 5. Notification Service Endpoints (Port 8060)

### Device Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/devices` | Yes | Register push token |
| GET | `/devices` | Yes | List my devices |
| PATCH | `/devices/{id}/token` | Yes | Update push token |
| DELETE | `/devices/{id}` | Yes | Deregister device |

### Notifications

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/notifications` | Yes | Get inbox |
| GET | `/notifications/unread-count` | Yes | Get unread count |
| PATCH | `/notifications/deliveries/{id}/read` | Yes | Mark as read |
| POST | `/notifications/mark-all-read` | Yes | Mark all as read |

### Preferences

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/notification-preferences` | Yes | Get preferences |
| PUT | `/notification-preferences` | Yes | Update preferences |
| DELETE | `/notification-preferences/{type}/{channel}` | Yes | Delete preference |

---

## 6. Payment Service Endpoints (Port 8040)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/payments` | Yes | Create payment intent |
| GET | `/payments` | Yes | List payments |
| GET | `/payments/{id}` | Yes | Payment detail |
| POST | `/payments/{id}/initiate` | Yes | Initiate USSD push (AzamPay/Selcom/M-Pesa) |
| POST | `/payments/{id}/verify` | Yes | Poll provider for status |
| POST | `/payments/{id}/refund` | Yes | Refund payment |
| DELETE | `/payments/{id}` | Yes | Cancel pending payment |
| GET | `/payments/{id}/transactions` | Yes | List transactions |

---

## 7. Translation Service Endpoints (Port 8050)

### POST `/translate` — Translate single text

```json
// Request
{
  "text": "Habari yako?",
  "target_language": "en",
  "source_language": "sw",     // optional — auto-detected if omitted
  "provider": "google"          // optional — auto-selected if omitted
}

// Response
{
  "translated_text": "How are you?",
  "source_language": "sw",
  "target_language": "en",
  "provider": "google",
  "cached": false
}
```

### POST `/translate/batch` — Translate up to 50 texts

```json
// Request
{
  "texts": ["Habari yako?", "Jina lako nani?"],
  "target_language": "en",
  "source_language": "sw"
}

// Response
{
  "results": [
    { "translated_text": "How are you?", "source_language": "sw", "target_language": "en", "provider": "google", "cached": false },
    { "translated_text": "What is your name?", "source_language": "sw", "target_language": "en", "provider": "google", "cached": true }
  ],
  "total": 2
}
```

### POST `/detect` — Detect language

```json
// Request
{ "text": "Habari yangu nzuri sana. Ninatoka Tanzania." }

// Response
{
  "detected_language": "sw",
  "confidence": 0.95,
  "alternatives": [
    { "language": "pt", "confidence": 0.03 },
    { "language": "id", "confidence": 0.01 }
  ]
}
```

### GET `/languages` — List supported languages

```json
// Response
{
  "languages": [
    { "code": "sw", "flores_code": "swh_Latn" },
    { "code": "en", "flores_code": "eng_Latn" },
    { "code": "fr", "flores_code": "fra_Latn" }
  ],
  "total": 201
}
```

### GET `/health` — Provider health check

```json
// Response
{
  "status": "ok",
  "providers": { "google": true, "deepl": true, "nllb": false },
  "nllb_loaded": false
}
```

### Provider Selection Logic

The translation service automatically selects the best provider based on the target language:

| Language Group | Provider Priority (fallback chain) |
|---------------|-----------------------------------|
| **African** (sw, ha, yo, ig, zu, xh, am, so, rw, ...) | Google → Microsoft → LibreTranslate → NLLB |
| **European** (en, de, fr, es, it, pt, nl, pl, ru, ...) | DeepL → Google → Microsoft → NLLB |
| **Asian** (zh, ja, ko, hi, bn, th, vi, id, ...) | Google → Microsoft → LibreTranslate → NLLB |
| **RTL** (ar, fa, ur) | Google → Microsoft → LibreTranslate → NLLB |
| **Other / Unknown** | Google → Microsoft → LibreTranslate → NLLB |

---

## 8. Kafka Event-Driven Data Flow

### Topic Map

```
                    ┌──────────────────────┐
                    │  riviwa.user.events   │
                    │  (auth publishes)     │
                    └──────┬───┬───┬───────┘
                           │   │   │
              ┌────────────┘   │   └────────────┐
              ▼                ▼                  ▼
        feedback_svc    stakeholder_svc    translation_svc
        (project cache, (user-contact      (create default
         GDPR cleanup)   linking)           language pref)

                    ┌──────────────────────┐
                    │  riviwa.org.events    │
                    │  (auth publishes)     │
                    └──────┬───┬───────────┘
                           │   │
              ┌────────────┘   └────────────┐
              ▼                              ▼
        feedback_svc                  stakeholder_svc
        (ProjectCache sync)           (ProjectCache sync)

                    ┌──────────────────────────┐
                    │ riviwa.translation.events │
                    │ (translation publishes)   │
                    └──────────┬───────────────┘
                               │
                               ▼
                        auth_service
                        (sync User.language
                         for JWT payload)

                    ┌──────────────────────────┐
                    │   riviwa.notifications    │
                    │   (all services publish)  │
                    └──────────┬───────────────┘
                               │
                               ▼
                      notification_service
                      (template render →
                       push/SMS/email/in-app)
```

### Critical Data Flows

**Flow 1: User Registration → Language Preference**
```
auth_service → user.registered → translation_service (create pref sw/en)
                                → translation_service → language.preference_set → auth_service (sync User.language)
```

**Flow 2: Project Published → Feedback & Stakeholder Ready**
```
auth_service → org_project.published → feedback_service (create ProjectCache)
                                     → stakeholder_service (create ProjectCache)
auth_service → org_project_stage.activated → both services (create StageCache)
```

**Flow 3: Feedback Submitted → Notification to PAP**
```
feedback_service → feedback.submitted (Kafka event)
feedback_service → riviwa.notifications (notification request with language="sw")
                → notification_service → SMS/push/email to PAP
```

**Flow 4: Stakeholder Concern → Auto-Created Feedback**
```
stakeholder_service → engagement.concern.raised → feedback_service (auto-create Suggestion)
feedback_service → feedback.submitted → stakeholder_service (link feedback_ref_id)
```

**Flow 5: User Deactivation → GDPR Cleanup**
```
auth_service → user.deactivated → feedback_service (null submitted_by_user_id)
                                → stakeholder_service (null contact.user_id)
                                → translation_service (soft-delete preference)
```

### Event Envelope Format (Standard)

```json
{
  "event_type": "user.registered",
  "event_id": "uuid-for-deduplication",
  "occurred_at": "2026-04-05T14:30:45.123456Z",
  "schema_version": "1.0",
  "service": "riviwa_auth_service",
  "payload": {
    "user_id": "f47ac10b-...",
    "email": "user@example.com",
    "phone_number": "+255700000000",
    "status": "active",
    "language": "sw"
  }
}
```

---

## 9. Client Integration Guide (ReactJS & Flutter)

### 9.1 API Client Setup

**ReactJS (Axios)**
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://api.riviwa.com/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

// Interceptor: attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Interceptor: auto-refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      const { data } = await axios.post(
        'https://api.riviwa.com/api/v1/auth/token/refresh',
        { refresh_token: refreshToken }
      );
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      error.config.headers.Authorization = `Bearer ${data.access_token}`;
      return api(error.config);
    }
    return Promise.reject(error);
  }
);

export default api;
```

**Flutter (Dio)**
```dart
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

final storage = FlutterSecureStorage();
final dio = Dio(BaseOptions(
  baseUrl: 'https://api.riviwa.com/api/v1',
  headers: {'Content-Type': 'application/json'},
));

// Interceptor: attach JWT + auto-refresh
dio.interceptors.add(InterceptorsWrapper(
  onRequest: (options, handler) async {
    final token = await storage.read(key: 'access_token');
    if (token != null) options.headers['Authorization'] = 'Bearer $token';
    handler.next(options);
  },
  onError: (error, handler) async {
    if (error.response?.statusCode == 401) {
      final refresh = await storage.read(key: 'refresh_token');
      final res = await Dio().post(
        'https://api.riviwa.com/api/v1/auth/token/refresh',
        data: {'refresh_token': refresh},
      );
      await storage.write(key: 'access_token', value: res.data['access_token']);
      await storage.write(key: 'refresh_token', value: res.data['refresh_token']);
      error.requestOptions.headers['Authorization'] = 'Bearer ${res.data['access_token']}';
      handler.resolve(await dio.fetch(error.requestOptions));
    } else {
      handler.next(error);
    }
  },
));
```

### 9.2 Authentication Implementation

**ReactJS — Login Flow**
```javascript
// Step 1: Submit credentials
const { data: step1 } = await api.post('/auth/login', {
  identifier: '+255700000000',
  password: 'MySecure@123',
});
// step1 = { login_token, otp_channel, otp_destination, expires_in_seconds }

// Step 2: Show OTP input, verify
const { data: tokens } = await api.post('/auth/login/verify-otp', {
  login_token: step1.login_token,
  otp_code: otpInput,  // user enters this
});
localStorage.setItem('access_token', tokens.access_token);
localStorage.setItem('refresh_token', tokens.refresh_token);
```

**Flutter — Login Flow**
```dart
// Step 1
final step1 = await dio.post('/auth/login', data: {
  'identifier': '+255700000000',
  'password': 'MySecure@123',
});

// Step 2
final tokens = await dio.post('/auth/login/verify-otp', data: {
  'login_token': step1.data['login_token'],
  'otp_code': otpInput,
});
await storage.write(key: 'access_token', value: tokens.data['access_token']);
await storage.write(key: 'refresh_token', value: tokens.data['refresh_token']);
```

### 9.3 Translation Integration

**Translate user-facing content on demand**

```javascript
// ReactJS
async function translateText(text, targetLang = 'en') {
  const { data } = await api.post('/translate', {
    text,
    target_language: targetLang,
  });
  return data.translated_text;
}

// Usage: translate feedback description for admin
const translated = await translateText(feedback.description, 'en');
```

```dart
// Flutter
Future<String> translateText(String text, {String target = 'en'}) async {
  final res = await dio.post('/translate', data: {
    'text': text,
    'target_language': target,
  });
  return res.data['translated_text'];
}
```

**Batch translate for lists**

```javascript
// Translate all feedback descriptions in a list
const descriptions = feedbackList.map(f => f.description);
const { data } = await api.post('/translate/batch', {
  texts: descriptions,
  target_language: 'en',
});
// data.results[i].translated_text matches feedbackList[i]
```

**Detect language before translation**

```javascript
const { data } = await api.post('/detect', { text: userInput });
if (data.detected_language !== 'en') {
  const translation = await translateText(userInput, 'en');
  // Show original + translation
}
```

### 9.4 Feedback Submission (PAP Self-Service)

```javascript
// ReactJS
const submitFeedback = async (formData) => {
  const { data } = await api.post('/my/feedback', {
    project_id: formData.projectId,
    feedback_type: 'grievance',      // grievance | suggestion | applause
    category: 'infrastructure',
    description: formData.description,
    submitter_name: formData.name,
    submitter_phone: formData.phone,
    is_anonymous: false,
  });
  // data = { id, unique_ref, status, ... }
  return data;
};

// Track submitted feedback
const trackFeedback = async (feedbackId) => {
  const { data } = await api.get(`/my/feedback/${feedbackId}`);
  // data = { id, status, actions: [...], resolution_summary, ... }
  return data;
};
```

### 9.5 Organisation Management

```javascript
// Create org
const { data: org } = await api.post('/orgs', {
  legal_name: 'Riviwa Tanzania',
  display_name: 'Riviwa',
  slug: 'riviwa',
  org_type: 'business',
  support_email: 'support@riviwa.com',
  country_code: 'tz',
});

// Create project under org
const { data: project } = await api.post(`/orgs/${org.id}/projects`, {
  name: 'Road Construction Phase 1',
  sector: 'infrastructure',
  region: 'Dar es Salaam',
  primary_lga: 'Ilala',
  accepts_grievances: true,
  accepts_suggestions: true,
});

// Activate project (publishes to Kafka → syncs to feedback & stakeholder services)
await api.post(`/orgs/${org.id}/projects/${project.id}/activate`);
```

### 9.6 Notification Handling

```javascript
// Register device for push notifications
await api.post('/devices', {
  platform: 'android',       // android | ios | web
  push_token: fcmToken,
  device_name: 'Samsung Galaxy S24',
});

// Get notification inbox
const { data } = await api.get('/notifications', {
  params: { skip: 0, limit: 20 },
});
// data = { items: [...], total, unread_count }

// Get unread count (for badge)
const { data: unread } = await api.get('/notifications/unread-count');
// unread = { count: 5 }

// Mark as read
await api.patch(`/notifications/deliveries/${deliveryId}/read`);
```

### 9.7 Payment Integration (Mobile Money)

```javascript
// Step 1: Create payment intent
const { data: payment } = await api.post('/payments', {
  amount: 50000,
  currency: 'TZS',
  provider: 'mpesa',       // mpesa | azampay | selcom
  payer_phone: '+255700000000',
  description: 'Project contribution',
  reference_type: 'project',
  reference_id: projectId,
});

// Step 2: Initiate USSD push (user gets a push on their phone)
await api.post(`/payments/${payment.id}/initiate`);

// Step 3: Poll for completion (or wait for push notification)
const { data: status } = await api.post(`/payments/${payment.id}/verify`);
// status.status = 'completed' | 'failed' | 'pending'
```

### 9.8 Stakeholder Engagement

```javascript
// Register stakeholder
const { data: stakeholder } = await api.post('/stakeholders', {
  entity_type: 'individual',
  category: 'directly_affected',
  vulnerability_level: 'medium',
});

// Create engagement activity
const { data: activity } = await api.post('/activities', {
  project_id: projectId,
  stage_id: stageId,
  activity_type: 'public_meeting',
  title: 'Community Consultation Meeting',
  planned_date: '2026-04-15',
  planned_attendee_count: 50,
  location: 'Ilala Community Hall',
});

// Log attendance after the meeting
await api.post(`/activities/${activity.id}/attendances/bulk`, {
  attendances: [
    { contact_id: contact1Id, attended: true },
    { contact_id: contact2Id, attended: true, concerns: 'Road dust affecting my shop' },
  ],
});
```

---

## 10. Error Handling

### Standard Error Response

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description",
  "detail": {}
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORISED` | 401 | JWT missing, expired, or invalid |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_OTP` | 400 | Wrong OTP code |
| `OTP_EXPIRED` | 400 | OTP session expired — restart flow |
| `OTP_MAX_ATTEMPTS` | 400 | Too many wrong attempts |
| `OTP_COOLDOWN` | 429 | Resend too soon (60s cooldown) |
| `DUPLICATE_IDENTIFIER` | 409 | Email/phone already registered |
| `WEAK_PASSWORD` | 400 | Password doesn't meet requirements |
| `ACCOUNT_SUSPENDED` | 403 | Account suspended by admin |
| `ACCOUNT_BANNED` | 403 | Account permanently banned |
| `ACCOUNT_LOCKED` | 423 | Too many failed login attempts |
| `LANGUAGE_NOT_SUPPORTED` | 422 | Unsupported language code |
| `TRANSLATION_FAILED` | 502 | Translation provider error |
| `PROVIDER_NOT_CONFIGURED` | 503 | No translation provider available |

### Client Error Handling Pattern

```javascript
try {
  const { data } = await api.post('/auth/login/verify-otp', { login_token, otp_code });
} catch (error) {
  const { error: code, message } = error.response?.data || {};
  switch (code) {
    case 'INVALID_OTP':
      showError('Incorrect code. Please try again.');
      break;
    case 'OTP_EXPIRED':
      // Redirect back to login — need fresh session
      navigate('/login');
      break;
    case 'OTP_MAX_ATTEMPTS':
      showError('Too many attempts. Please login again.');
      navigate('/login');
      break;
    default:
      showError(message || 'Something went wrong.');
  }
}
```

---

## Interactive API Documentation

Each service exposes Swagger UI in development/staging:

| Service | Swagger URL |
|---------|-------------|
| Auth | `https://api.riviwa.com:8000/docs` (direct) or via local `http://localhost:8000/docs` |
| Feedback | `http://localhost:8090/docs` |
| Notification | `http://localhost:8060/docs` |
| Payment | `http://localhost:8040/docs` |
| Stakeholder | `http://localhost:8070/docs` |
| Translation | `http://localhost:8050/docs` |

> **Note**: Swagger UI is disabled in production (`ENVIRONMENT=production`).
