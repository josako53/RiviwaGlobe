# Riviwa Platform — Full API Reference

> All services are fronted by Nginx. Base URL in production: `https://<host>/api/v1`
>
> **Authentication:** Unless stated otherwise, endpoints require `Authorization: Bearer <access_token>`.
> Internal service-to-service calls use `X-Service-Key: <INTERNAL_SERVICE_KEY>` instead.

---

## Table of Contents

1. [Auth Service (port 8000)](#1-auth-service)
   - [Authentication](#11-authentication)
   - [Registration](#12-registration)
   - [Password](#13-password)
   - [Users](#14-users)
   - [Organisations](#15-organisations)
   - [Projects (Auth)](#16-projects-auth)
   - [Checklists](#17-checklists)
   - [Admin Dashboard](#18-admin-dashboard)
   - [Webhooks (Auth)](#19-webhooks-auth)
2. [Feedback Service (port 8090)](#2-feedback-service)
   - [Feedback](#21-feedback)
   - [Categories](#22-categories)
   - [Channel Sessions](#23-channel-sessions)
   - [AI Channels](#24-ai-channels)
   - [Channel Webhooks](#25-channel-webhooks)
   - [Committees](#26-committees)
   - [PAP Portal](#27-pap-portal)
   - [Reports](#28-reports)
   - [Voice](#29-voice)
   - [Actions](#210-actions)
3. [Stakeholder Service (port 8070)](#3-stakeholder-service)
   - [Stakeholders](#31-stakeholders)
   - [Contacts](#32-contacts)
   - [Activities](#33-activities)
   - [Communications](#34-communications)
   - [Focal Persons](#35-focal-persons)
   - [Projects (Stakeholder)](#36-projects-stakeholder)
   - [Reports (Stakeholder)](#37-reports-stakeholder)
4. [Notification Service (port 8060)](#4-notification-service)
   - [Devices](#41-devices)
   - [Notifications Inbox](#42-notifications-inbox)
   - [Preferences](#43-preferences)
   - [Internal Dispatch](#44-internal-dispatch)
   - [Templates](#45-templates)
   - [Webhooks (Notification)](#46-webhooks-notification)
5. [Payment Service (port 8040)](#5-payment-service)
   - [Payments](#51-payments)
   - [Webhooks (Payment)](#52-webhooks-payment)
6. [AI Service (port 8085)](#6-ai-service)
   - [Conversations](#61-conversations)
   - [AI Admin](#62-ai-admin)
   - [AI Internal](#63-ai-internal)
   - [Webhooks (AI)](#64-webhooks-ai)
7. [Recommendation Service (port 8086)](#7-recommendation-service)
   - [Recommendations](#71-recommendations)
   - [Discovery](#72-discovery)
   - [Indexing](#73-indexing)

---

## Common Response Objects

### `MessageResponse`
```json
{ "message": "string" }
```

### `TokenResponse`
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Common HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 400 | Bad request / validation error |
| 401 | Unauthenticated |
| 403 | Forbidden (insufficient role) |
| 404 | Not found |
| 409 | Conflict (duplicate) |
| 410 | Session / token expired |
| 422 | Unprocessable entity |
| 429 | Rate limited |
| 500 | Server error |

---

## 1. Auth Service

Nginx routes: `/api/v1/auth`, `/api/v1/users`, `/api/v1/orgs`, `/api/v1/admin`, `/api/v1/webhooks`

### 1.1 Authentication

#### `POST /auth/login`
Step 1 of login — submit credentials, receive OTP.

**Auth:** Public

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `identifier` | string | ✓ | Email or E.164 phone |
| `password` | string | ✓ | Account password |
| `device_fingerprint` | string | — | For fraud scoring |

**Response `200`:**
| Field | Type | Notes |
|-------|------|-------|
| `login_token` | string | Opaque Redis key (5 min TTL) |
| `otp_channel` | string | `"email"` or `"sms"` |
| `otp_destination` | string | Masked, e.g. `"al***@example.com"` |
| `expires_in_seconds` | integer | 300 |

---

#### `POST /auth/login/verify-otp`
Step 2 — verify OTP and receive JWT pair.

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `login_token` | string | ✓ |
| `otp_code` | string | ✓ (6 digits) |

**Response `200`:** `TokenResponse`

---

#### `POST /auth/token/refresh`
Exchange refresh token for new access token (token rotation).

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `refresh_token` | string | ✓ |

**Response `200`:** `TokenResponse`

---

#### `POST /auth/token/logout`
Revoke session — JWT added to deny-list.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `refresh_token` | string | ✓ |

**Response `200`:** `MessageResponse`

---

#### `POST /auth/switch-org`
Switch active organisation context in JWT claims.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `org_id` | UUID | — | Null = personal view |

**Response `200`:**
| Field | Type |
|-------|------|
| `tokens` | `TokenResponse` |
| `org_id` | UUID (nullable) |
| `org_role` | string (nullable) |

---

#### `POST /auth/social`
OAuth login/register via Google, Apple, or Facebook.

**Auth:** Public

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `provider` | string | ✓ | `google` \| `apple` \| `facebook` |
| `id_token` | string | ✓ | JWT from provider |
| `device_fingerprint` | string | — | |

**Response `200`:**
| Field | Type |
|-------|------|
| `user_id` | UUID |
| `is_new_user` | boolean |
| `has_password` | boolean |
| `tokens` | `TokenResponse` |

---

#### `POST /auth/social/set-password`
Add a password to a social-only account.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `password` | string | ✓ |
| `confirm_password` | string | ✓ |

**Response `200`:** `MessageResponse`

---

#### `POST /auth/channel-register`
Auto-register a PAP from an inbound channel message.

**Auth:** `X-Service-Key` header (internal)

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `phone_number` | string | ✓ | E.164 |
| `channel` | string | — | `sms` \| `whatsapp` \| `phone_call` |
| `display_name` | string | — | |
| `language` | string | — | `sw` \| `en` |

**Response `200`:**
| Field | Type |
|-------|------|
| `user_id` | string |
| `is_new_user` | boolean |
| `must_set_password` | boolean |
| `access_token` | string |
| `refresh_token` | string |

---

#### `POST /auth/channel-login/request-otp`
Channel login Step 1 — send OTP to verified phone.

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `phone_number` | string | ✓ (E.164) |

**Response `200`:**
```json
{ "session_token": "string", "message": "string", "expires_in": 300 }
```

---

#### `POST /auth/channel-login/verify-otp`
Channel login Step 2 — verify OTP.

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `session_token` | string | ✓ |
| `otp_code` | string | ✓ |

**Response `200`:**
```json
{ "access_token": "string", "refresh_token": "string", "must_set_password": false, "user_id": "string" }
```

---

### 1.2 Registration

#### `POST /auth/register/init`
Step 1 — submit identifier and start OTP flow.

**Auth:** Public

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `email` | string | — | Exactly one of email/phone required |
| `phone_number` | string | — | E.164 |
| `first_name` | string | — | |
| `last_name` | string | — | |
| `device_fingerprint` | string | — | |

**Response `200`:**
| Field | Type |
|-------|------|
| `registration_token` | string |
| `otp_channel` | string |
| `otp_destination` | string |
| `expires_in_seconds` | integer (600) |

---

#### `POST /auth/register/verify-otp`
Step 2 — verify OTP.

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `registration_token` | string | ✓ |
| `otp_code` | string | ✓ |

**Response `200`:**
```json
{ "registration_token": "string", "message": "OTP verified." }
```

---

#### `POST /auth/register/complete`
Step 3 — set password and activate account.

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `registration_token` | string | ✓ |
| `password` | string | ✓ |
| `confirm_password` | string | ✓ |
| `username` | string | — |
| `first_name` | string | — |
| `last_name` | string | — |

**Response `200`:**
```json
{ "action": "complete" }
```

---

#### `POST /auth/register/resend-otp`
Resend OTP (60-second cooldown).

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `session_token` | string | ✓ |

**Response `200`:** Same as `/auth/register/init`

---

### 1.3 Password

#### `POST /auth/password/forgot`
Step 1 — request password reset OTP.

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `identifier` | string | ✓ (email or E.164) |
| `device_fingerprint` | string | — |

**Response `200`:**
| Field | Type |
|-------|------|
| `reset_token` | string |
| `otp_channel` | string |
| `otp_destination` | string |
| `expires_in_seconds` | integer (600) |
| `message` | string |

---

#### `POST /auth/password/forgot/verify-otp`
Step 2 — verify reset OTP.

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `reset_token` | string | ✓ |
| `otp_code` | string | ✓ |

**Response `200`:**
```json
{ "reset_token": "string", "message": "string" }
```

---

#### `POST /auth/password/forgot/reset`
Step 3 — set new password.

**Auth:** Public

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `reset_token` | string | ✓ |
| `new_password` | string | ✓ |
| `confirm_new_password` | string | ✓ |

**Response `200`:** `MessageResponse`

---

#### `POST /auth/password/change`
Change password for authenticated user.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `current_password` | string | ✓ |
| `new_password` | string | ✓ |
| `confirm_new_password` | string | ✓ |

**Response `200`:** `MessageResponse`

---

#### `POST /auth/password/channel/set-password`
Set first password for a channel-registered account.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `new_password` | string | ✓ |

**Response `200`:**
```json
{ "message": "string", "user_id": "string", "status": "active" }
```

---

### 1.4 Users

#### `GET /users/me`
Get authenticated user's full profile.

**Auth:** Bearer token

**Response `200`:**
| Field | Type |
|-------|------|
| `id` | UUID |
| `username` | string |
| `email` | string (nullable) |
| `phone_number` | string (nullable) |
| `is_email_verified` | boolean |
| `phone_verified` | boolean |
| `id_verified` | boolean |
| `display_name` | string (nullable) |
| `full_name` | string (nullable) |
| `avatar_url` | string (nullable) |
| `status` | string |
| `oauth_provider` | string (nullable) |
| `has_password` | boolean |
| `two_factor_enabled` | boolean |
| `active_org_id` | UUID (nullable) |
| `created_at` | datetime |
| `updated_at` | datetime |
| `last_login_at` | datetime (nullable) |

---

#### `PATCH /users/me`
Update profile (PATCH semantics — only provided fields updated).

**Auth:** Bearer token

**Request body** (all optional):
| Field | Type | Notes |
|-------|------|-------|
| `username` | string | |
| `display_name` | string | |
| `full_name` | string | |
| `date_of_birth` | string | ISO-8601 |
| `gender` | string | |
| `country_code` | string | ISO-3166-1 alpha-2 |
| `language` | string | BCP-47 |

**Response `200`:** `UserPrivateResponse` (same as GET)

---

#### `DELETE /users/me`
Soft-delete (deactivate) account.

**Auth:** Bearer token

**Response `200`:** `MessageResponse`

---

#### `POST /users/me/avatar`
Update avatar URL.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `avatar_url` | string | — | HTTPS URL or null to clear |

**Response `200`:** `UserPrivateResponse`

---

#### `POST /users/me/verify-email`
Mark email as verified.

**Auth:** Bearer token

**Response `200`:** `MessageResponse`

---

#### `POST /users/me/verify-phone`
Mark phone as verified.

**Auth:** Bearer token

**Response `200`:** `MessageResponse`

---

#### `POST /users/{user_id}/suspend`
**Auth:** Bearer token (admin)

**Response `200`:** `MessageResponse`

---

#### `POST /users/{user_id}/ban`
**Auth:** Bearer token (admin)

**Response `200`:** `MessageResponse`

---

#### `POST /users/{user_id}/reactivate`
**Auth:** Bearer token (admin)

**Response `200`:** `MessageResponse`

---

### 1.5 Organisations

#### `POST /orgs`
Create a new organisation. Caller becomes OWNER.

**Auth:** Bearer token (verified email required)

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `legal_name` | string | ✓ | 2–200 chars |
| `display_name` | string | ✓ | 2–100 chars |
| `slug` | string | ✓ | 3–80 chars, lowercase alphanumeric + hyphens |
| `org_type` | string | ✓ | `business` \| `corporate` \| `government` \| `ngo` \| `individual_pro` |
| `description` | string | — | |
| `logo_url` | string | — | |
| `website_url` | string | — | |
| `support_email` | string | — | |
| `support_phone` | string | — | |
| `country_code` | string | — | ISO-3166-1 alpha-2 |
| `timezone` | string | — | |
| `registration_number` | string | — | |
| `tax_id` | string | — | |
| `max_members` | integer | — | 0 = unlimited |

**Response `201`:** `OrgResponse`
```json
{
  "id": "uuid", "slug": "string", "legal_name": "string",
  "display_name": "string", "org_type": "string", "status": "string",
  "is_verified": false, "logo_url": null, "country_code": "TZ",
  "timezone": "string", "max_members": 0, "created_at": "datetime"
}
```

---

#### `GET /orgs`
List organisations for authenticated user.

**Auth:** Bearer token

**Query params:**
| Param | Type | Notes |
|-------|------|-------|
| `search` | string | Name or slug |
| `org_type` | string | Filter by type |
| `is_verified` | boolean | |
| `sort` | string | `name` \| `created` |
| `page` | integer | Default 1 |
| `limit` | integer | 1–100, default 20 |

**Response `200`:**
```json
{ "items": [...], "total": 0, "page": 1, "limit": 20, "pages": 1 }
```

---

#### `GET /orgs/{org_id}`
**Auth:** Bearer token

**Response `200`:** `OrgResponse`

---

#### `PATCH /orgs/{org_id}`
**Auth:** Bearer token (org ADMIN+)

**Request body:** All `CreateOrgRequest` fields optional.

**Response `200`:** `OrgResponse`

---

#### `DELETE /orgs/{org_id}`
Deactivate organisation. OWNER only.

**Auth:** Bearer token (org OWNER)

**Response `200`:** `MessageResponse`

---

#### `POST /orgs/{org_id}/verify`
**Auth:** Bearer token (platform admin)

**Response `200`:** `OrgResponse` (status = ACTIVE)

---

#### `POST /orgs/{org_id}/suspend`
**Auth:** Bearer token (platform admin)

**Request body:**
| Field | Type |
|-------|------|
| `reason` | string (optional) |

**Response `200`:** `MessageResponse`

---

#### `POST /orgs/{org_id}/ban`
**Auth:** Bearer token (platform admin)

**Request body:** `{ "reason": "string (optional)" }`

**Response `200`:** `MessageResponse`

---

#### `POST /orgs/{org_id}/members`
Add member directly (no invite).

**Auth:** Bearer token (org ADMIN+)

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `user_id` | UUID | ✓ |
| `org_role` | string | ✓ (`manager` \| `member` \| `admin` \| `owner`) |

**Response `200`:**
```json
{ "user_id": "uuid", "organisation_id": "uuid", "org_role": "string", "status": "string", "joined_at": "datetime" }
```

---

#### `DELETE /orgs/{org_id}/members/{user_id}`
**Auth:** Bearer token (org ADMIN+)

**Response `200`:** `MessageResponse`

---

#### `PATCH /orgs/{org_id}/members/{user_id}/role`
**Auth:** Bearer token (org ADMIN+)

**Request body:** `{ "org_role": "string" }`

**Response `200`:** `MemberResponse`

---

#### `POST /orgs/{org_id}/transfer-ownership`
**Auth:** Bearer token (org OWNER)

**Request body:** `{ "new_owner_id": "uuid" }`

**Response `200`:** `MessageResponse`

---

#### `GET /orgs/invites`
List pending invites for current user.

**Auth:** Bearer token

**Response `200`:** Array of invite objects
```json
{
  "id": "uuid", "organisation_id": "uuid",
  "invited_by_id": "uuid", "invited_email": "string",
  "invited_user_id": "uuid", "invited_role": "string",
  "status": "string", "expires_at": "datetime"
}
```

---

#### `POST /orgs/{org_id}/invites`
**Auth:** Bearer token (org MANAGER+)

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `invited_role` | string | ✓ |
| `invited_email` | string | — |
| `invited_user_id` | UUID | — |
| `message` | string | — |

**Response `200`:** Invite object

---

#### `POST /orgs/invites/{invite_id}/accept`
**Auth:** Bearer token

**Response `200`:** `MemberResponse`

---

#### `POST /orgs/invites/{invite_id}/decline`
**Auth:** Bearer token

**Response `200`:** `MessageResponse`

---

#### `DELETE /orgs/{org_id}/invites/{invite_id}`
**Auth:** Bearer token (org MANAGER+)

**Response `200`:** `MessageResponse`

---

#### `POST /orgs/{org_id}/logo`
Upload organisation logo.

**Auth:** Bearer token (org MANAGER+)

**Request:** `multipart/form-data` — `file` (JPEG/PNG/WebP/SVG, max 5 MB)

**Response `200`:**
```json
{ "org_id": "string", "logo_url": "string" }
```

---

### 1.6 Projects (Auth)

> All paths are under `/orgs/{org_id}/projects`.

#### `POST /orgs/{org_id}/projects`
Create project.

**Auth:** Bearer token (org ADMIN+)

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `name` | string | ✓ |
| `code` | string | — |
| `description` | string | — |
| `objectives` | string | — |
| `sector` | string | — |
| `region` | string | — |
| `start_date` | date | — |
| `end_date` | date | — |
| `budget_amount` | float | — |
| `currency_code` | string | — |
| `status` | string | — |
| `display_order` | integer | — |

**Response `201`:** `ProjectSummaryResponse`

---

#### `GET /orgs/{org_id}/projects`
**Auth:** Bearer token (org MANAGER+)

**Query params:** `status`, `branch_id`, `skip`, `limit`

**Response `200`:** Array of `ProjectSummaryResponse`

---

#### `GET /orgs/{org_id}/projects/{project_id}`
**Auth:** Bearer token (org MANAGER+)

**Response `200`:** `ProjectDetailResponse`

---

#### `PATCH /orgs/{org_id}/projects/{project_id}`
**Auth:** Bearer token (org ADMIN+)

**Request body:** All project fields optional.

**Response `200`:** `ProjectSummaryResponse`

---

#### `POST /orgs/{org_id}/projects/{project_id}/activate`
**Auth:** Bearer token (org OWNER+)

**Response `200`:** `ProjectSummaryResponse`

---

#### `POST /orgs/{org_id}/projects/{project_id}/pause`
**Auth:** Bearer token (org OWNER+) | **Response `200`:** `ProjectSummaryResponse`

---

#### `POST /orgs/{org_id}/projects/{project_id}/resume`
**Auth:** Bearer token (org OWNER+) | **Response `200`:** `ProjectSummaryResponse`

---

#### `POST /orgs/{org_id}/projects/{project_id}/complete`
**Auth:** Bearer token (org OWNER+) | **Response `200`:** `ProjectSummaryResponse`

---

#### `DELETE /orgs/{org_id}/projects/{project_id}`
**Auth:** Bearer token (org OWNER+) | **Response `200`:** `MessageResponse`

---

#### In-charge management (per project, stage, sub-project)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `.../in-charges` | Assign person | ADMIN+ |
| `GET` | `.../in-charges` | List team | MANAGER+ |
| `DELETE` | `.../in-charges/{user_id}` | Relieve (query: `role_title`) | ADMIN+ |

**Assign request body:**
| Field | Type | Required |
|-------|------|----------|
| `user_id` | UUID | ✓ |
| `role_title` | string | ✓ (max 200) |
| `duties` | string | — |
| `is_lead` | boolean | — |

---

#### Stage endpoints (under `/orgs/{org_id}/projects/{project_id}/stages`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/stages` | Create stage |
| `GET` | `/stages` | List stages |
| `GET` | `/stages/{stage_id}` | Stage detail |
| `PATCH` | `/stages/{stage_id}` | Update stage |
| `POST` | `/stages/{stage_id}/activate` | Activate |
| `POST` | `/stages/{stage_id}/complete` | Complete |
| `POST` | `/stages/{stage_id}/skip` | Skip |

**Create stage request body:**
| Field | Type | Required |
|-------|------|----------|
| `name` | string | ✓ |
| `description` | string | — |
| `objectives` | string | — |
| `start_date` | date | — |
| `end_date` | date | — |
| `display_order` | integer | — |

---

#### Sub-project endpoints (under `.../stages/{stage_id}/subprojects`)

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/subprojects` | Create |
| `GET` | `/subprojects` | List |
| `GET` | `/subprojects/{id}` | Detail |
| `GET` | `/subprojects/{id}/tree` | Nested tree |
| `PATCH` | `/subprojects/{id}` | Update |
| `DELETE` | `/subprojects/{id}` | Delete |

**Create sub-project fields:** `name`, `code`, `parent_subproject_id`, `description`, `objectives`, `activities`, `expected_outputs`, `start_date`, `end_date`, `budget_amount`, `currency_code`, `location`, `display_order`

---

### 1.7 Checklists

Checklist endpoints exist at **three levels**:

- Project: `/orgs/{org_id}/projects/{project_id}/checklist`
- Stage: `/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist`
- Sub-project: `/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist`

**All require MANAGER+ role.**

| Method | Path suffix | Description |
|--------|-------------|-------------|
| `POST` | `/checklist` | Create item |
| `GET` | `/checklist` | List items + progress |
| `GET` | `/checklist/progress` | Progress summary |
| `GET` | `/checklist/{item_id}` | Get item |
| `PATCH` | `/checklist/{item_id}` | Update item |
| `POST` | `/checklist/{item_id}/done` | Mark done |
| `PUT` | `/checklist/reorder` | Bulk reorder |
| `DELETE` | `/checklist/{item_id}` | Soft-delete |

**Create item request body:**
| Field | Type | Required |
|-------|------|----------|
| `title` | string | ✓ |
| `assign_to` | UUID | — |
| `due_date` | date | — |
| `category` | string | — |

---

### 1.8 Admin Dashboard

**Auth:** All require Bearer token with platform `admin` role.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/dashboard/summary` | Platform KPI overview |
| `GET` | `/admin/users` | List all users (filters: `status`, `search`, `platform_role`, `from_date`, `to_date`, `skip`, `limit`) |
| `GET` | `/admin/users/growth` | Daily registration trend (query: `days` 7–365, default 30) |
| `GET` | `/admin/users/status-breakdown` | Users by status |
| `GET` | `/admin/users/{user_id}` | User admin detail |
| `POST` | `/admin/users/{user_id}/suspend` | Suspend user |
| `POST` | `/admin/users/{user_id}/ban` | Ban user |
| `POST` | `/admin/users/{user_id}/reactivate` | Reactivate user |
| `GET` | `/admin/orgs` | List all organisations |
| `GET` | `/admin/orgs/pending` | Pending verification queue |
| `GET` | `/admin/orgs/breakdown` | Org by type/status |
| `GET` | `/admin/orgs/{org_id}` | Org admin detail |
| `GET` | `/admin/projects` | List all projects |
| `GET` | `/admin/security/fraud-summary` | Fraud detection summary |
| `GET` | `/admin/security/flagged-users` | Flagged user accounts |
| `GET` | `/admin/staff` | Platform staff list |
| `POST` | `/admin/staff/{user_id}/role` | Assign platform role |

---

### 1.9 Webhooks (Auth)

#### `POST /webhooks/id-verification`
ID verification provider callback.

**Auth:** Public (webhook signature via `X-Webhook-Signature`)

**Request body:**
| Field | Type | Notes |
|-------|------|-------|
| `event_type` | string | `check.completed` \| `check.expired` |
| `result` | string | `approved` \| `rejected` |

**Response `200`:** `{ "status": "processed" }`

---

## 2. Feedback Service

Nginx routes: `/api/v1/feedback`, `/api/v1/categories`, `/api/v1/channels`, `/api/v1/committees`, `/api/v1/pap`, `/api/v1/voice`, `/api/v1/reports`, `/api/v1/my`, `/api/v1/escalation-requests`

### Role abbreviations
| Symbol | Meaning |
|--------|---------|
| **Staff** | Org manager / admin / owner, or platform admin |
| **GRMOfficer** | Org manager+ or platform admin |
| **GRMCoordinator** | Org admin / owner or platform admin |
| **PAP** | Authenticated end-user (PAP/citizen) |
| **Internal** | `X-Service-Key` header |

---

### 2.1 Feedback

#### `POST /feedback`
Submit a single feedback record. Staff can backdate via `submitted_at`.

**Auth:** GRMOfficer (manager+)

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `project_id` | UUID | ✓ | |
| `feedback_type` | string | ✓ | `grievance` \| `suggestion` \| `applause` |
| `category` | string | ✓ | |
| `channel` | string | ✓ | `sms` \| `whatsapp` \| `phone_call` \| `mobile_app` \| `web_portal` \| `in_person` \| `paper_form` \| `email` \| `public_meeting` \| `notice_box` \| `other` |
| `subject` | string | ✓ | 5–500 chars |
| `description` | string | ✓ | min 10 chars |
| `is_anonymous` | boolean | — | default false |
| `submitter_name` | string | — | max 255 |
| `submitter_phone` | string | — | E.164, max 20 |
| `submitter_email` | string | — | max 255 |
| `submitter_type` | string | — | `individual` \| `group` \| `community_organisation` |
| `group_size` | integer | — | |
| `submitter_location_region` | string | — | |
| `submitter_location_district` | string | — | |
| `submitter_location_lga` | string | — | |
| `submitter_location_ward` | string | — | |
| `submitter_location_street` | string | — | |
| `submitted_by_user_id` | UUID | — | |
| `submitted_by_stakeholder_id` | UUID | — | |
| `submitted_by_contact_id` | UUID | — | |
| `priority` | string | — | `critical` \| `high` \| `medium` \| `low` (default `medium`) |
| `issue_location_description` | string | — | max 500 |
| `issue_region` | string | — | |
| `issue_district` | string | — | |
| `issue_lga` | string | — | |
| `issue_ward` | string | — | |
| `issue_mtaa` | string | — | |
| `issue_gps_lat` | float | — | −90 to 90 |
| `issue_gps_lng` | float | — | −180 to 180 |
| `date_of_incident` | string | — | YYYY-MM-DD |
| `submitted_at` | string | — | ISO datetime or date, defaults to now |
| `media_urls` | string[] | — | |
| `subproject_id` | UUID | — | |
| `service_location_id` | UUID | — | |
| `stakeholder_engagement_id` | UUID | — | |
| `distribution_id` | UUID | — | |
| `officer_recorded` | boolean | — | default false |
| `internal_notes` | string | — | |

**Response `201`:** Feedback object

---

#### `POST /feedback/bulk-upload`
CSV bulk import. Max 1000 rows per upload.

**Auth:** Staff

**Request:** `multipart/form-data`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `file` | UploadFile | ✓ | CSV, UTF-8 |

**CSV columns:** `project_id`, `feedback_type`, `category`, `subject`, `description`, `channel`, `priority`, `submitter_name`, `submitter_phone`, `is_anonymous`, `issue_lga`, `issue_ward`, `issue_gps_lat`, `issue_gps_lng`, `date_of_incident`, `submitted_at`

**Response `200`:**
```json
{ "total_rows": 0, "created": 0, "skipped": 0, "errors": [{"row": 1, "error": "string"}] }
```

---

#### `GET /feedback`
List feedback records.

**Auth:** Staff

**Query params:**
| Param | Type | Notes |
|-------|------|-------|
| `project_id` | UUID | |
| `feedback_type` | string | |
| `status` | string | |
| `priority` | string | |
| `current_level` | string | |
| `category` | string | |
| `lga` | string | |
| `is_anonymous` | boolean | |
| `submission_method` | string | |
| `channel` | string | |
| `submitted_by_stakeholder_id` | UUID | |
| `assigned_committee_id` | UUID | |
| `skip` | integer | default 0 |
| `limit` | integer | 1–200, default 50 |

**Response `200`:** `{ "items": [...], "count": 0 }`

---

#### `GET /feedback/{feedback_id}`
Full detail with actions, escalations, resolution, appeal.

**Auth:** Staff

**Response `200`:** Feedback object + `actions`, `escalations`, `resolution`, `appeal` arrays

---

#### `PATCH /feedback/{feedback_id}/acknowledge`
**Auth:** GRMOfficer (manager+)

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `priority` | string | — |
| `target_resolution_date` | string (YYYY-MM-DD) | — |
| `notes` | string | — |

**Response `200`:** Feedback object

---

#### `PATCH /feedback/{feedback_id}/assign`
**Auth:** GRMOfficer (manager+)

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `assigned_to_user_id` | UUID | — |
| `assigned_committee_id` | UUID | — |
| `notes` | string | — |

**Response `200`:** Feedback object

---

#### `POST /feedback/{feedback_id}/escalate`
**Auth:** GRMOfficer (manager+)

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `to_level` | string | ✓ | `ward` \| `lga_piu` \| `pcu` \| `tarura_wbcu` \| `tanroads` \| `world_bank` |
| `reason` | string | ✓ | min 10 chars |
| `escalated_to_committee_id` | UUID | — | |

**Response `200`:** Feedback object

---

#### `POST /feedback/{feedback_id}/resolve`
**Auth:** GRMOfficer (manager+)

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `resolution_summary` | string | ✓ | min 10 chars |
| `response_method` | string | — | `verbal` \| `written_letter` \| `email` \| `sms` \| `phone_call` \| `in_person_meeting` \| `notice_board` \| `other` |
| `grievant_satisfied` | boolean | — | |
| `grievant_response` | string | — | |
| `witness_name` | string | — | |

**Response `200`:** Feedback object

---

#### `POST /feedback/{feedback_id}/appeal`
**Auth:** GRMOfficer (manager+)

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `appeal_grounds` | string | ✓ (min 10) |

**Response `200`:** Feedback object

---

#### `PATCH /feedback/{feedback_id}/close`
**Auth:** GRMOfficer (manager+)

**Request body:** `{ "notes": "string (optional)" }`

**Response `200`:** Feedback object

---

#### `PATCH /feedback/{feedback_id}/dismiss`
Admin/owner only.

**Auth:** GRMCoordinator (admin/owner)

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `reason` | string | ✓ (min 5) |

**Response `200`:** Feedback object

---

#### `GET /feedback/by-ref/{unique_ref}`
Look up feedback status by reference number.

**Auth:** `X-Service-Key` (internal)

**Response `200`:**
```json
{
  "id": "uuid", "unique_ref": "string", "status": "string",
  "feedback_type": "string", "subject": "string", "description": "string (max 150)",
  "submitted_at": "datetime", "resolved_at": "datetime"
}
```

---

#### `GET /feedback/{feedback_id}/for-ai`
Fetch feedback data for AI classification.

**Auth:** `X-Service-Key` (internal)

**Response `200`:** Feedback fields used for classification (project_id, feedback_type, category, subject, description, location fields)

---

#### `PATCH /feedback/{feedback_id}/ai-enrich`
AI service backfill — set project_id and/or category_def_id.

**Auth:** `X-Service-Key` (internal)

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `project_id` | UUID | — |
| `category_def_id` | UUID | — |
| `note` | string | — |

**Response `200`:**
```json
{ "enriched": true, "reason": "string", "feedback_id": "uuid" }
```

---

### 2.2 Categories

#### `POST /categories`
**Auth:** Staff

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | ✓ | 2–120 chars |
| `slug` | string | — | max 80, auto-generated if omitted |
| `description` | string | — | |
| `project_id` | UUID | — | Platform-wide if omitted |
| `applicable_types` | string[] | — | `grievance` \| `suggestion` \| `applause` |
| `color_hex` | string | — | max 7 |
| `icon` | string | — | max 50 |
| `display_order` | integer | — | default 0 |

**Response `201`:** Category object

---

#### `GET /categories`
**Auth:** Staff

**Query params:** `project_id`, `feedback_type`, `source`, `status`, `include_global` (bool, default true), `skip`, `limit` (max 500)

**Response `200`:** `{ "items": [...], "count": 0 }`

---

#### `GET /categories/summary`
All category counts for a project (dashboard).

**Auth:** Staff

**Query params:** `project_id` (required), `feedback_type`, `from_date`, `to_date`

**Response `200`:** `{ "categories": [{"count": 0, ...category}] }`

---

#### `GET /categories/{category_id}`
**Auth:** Staff | **Response `200`:** Category object

---

#### `PATCH /categories/{category_id}`
**Auth:** Staff

**Request body** (all optional): `name`, `description`, `applicable_types`, `color_hex`, `icon`, `display_order`

**Response `200`:** Category object

---

#### `GET /categories/{category_id}/rate`
Feedback rate for a category.

**Auth:** Staff

**Query params:** `project_id`, `stage_id`, `period`, `from_date`, `to_date`, `feedback_type`, `status`, `open_only`, `priority`, `current_level`, `lga`, `ward`, `is_anonymous`, `submitted_by_stakeholder_id`, `assigned_committee_id`, `assigned_to_user_id`

**Response `200`:** Category + rate metrics

---

#### `POST /categories/{category_id}/approve`
Approve ML-suggested category.

**Auth:** Staff

**Request body:** `{ "notes": "string", "name": "string", "slug": "string" }` (all optional)

**Response `200`:** Category object

---

#### `POST /categories/{category_id}/reject`
**Auth:** Staff | **Request body:** `{ "notes": "string" }` | **Response `200`:** Category object

---

#### `POST /categories/{category_id}/deactivate`
**Auth:** Staff | **Request body:** `{ "notes": "string" }` | **Response `200`:** Category object

---

#### `POST /categories/{category_id}/merge`
**Auth:** Staff

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `merge_into_id` | UUID | ✓ |
| `notes` | string | — |

**Response `200`:** Category object

---

#### `POST /feedback/{feedback_id}/classify`
Run ML classification to assign/suggest a category.

**Auth:** Staff

**Request body:** `{ "force": false }` — set `true` to re-run even if already assigned

**Response `200`:** `{ "category": {...} }`

---

#### `PATCH /feedback/{feedback_id}/recategorise`
Manually reassign category.

**Auth:** Staff

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `category_def_id` | UUID | ✓ |

**Response `200`:** `{ "category": {...} }`

---

### 2.3 Channel Sessions

Staff-managed sessions (no AI automation).

#### `POST /channel-sessions`
**Auth:** Staff

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `channel` | string | ✓ | |
| `project_id` | UUID | — | |
| `phone_number` | string | — | max 20 |
| `whatsapp_id` | string | — | max 100 |
| `gateway_session_id` | string | — | max 200 |
| `gateway_provider` | string | — | default `"other"`, max 50 |
| `language` | string | — | default `"sw"`, max 10 |
| `is_officer_assisted` | boolean | — | default false |

**Response `201`:** Session object

---

#### `GET /channel-sessions`
**Auth:** Staff

**Query params:** `project_id`, `channel`, `status`, `skip`, `limit` (max 200)

**Response `200`:** `{ "items": [...], "count": 0 }`

---

#### `GET /channel-sessions/{session_id}`
**Auth:** Staff | **Response `200`:** Session object with full transcript

---

#### `POST /channel-sessions/{session_id}/message`
Add PAP message turn and get LLM reply.

**Auth:** Staff

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `message` | string | ✓ (1–2000 chars) |

**Response `200`:** Message processing result

---

#### `POST /channel-sessions/{session_id}/submit`
Force-submit feedback from current extracted data.

**Auth:** Staff | **Response `200`:** Submission result

---

#### `POST /channel-sessions/{session_id}/abandon`
**Auth:** Staff

**Request body:** `{ "reason": "string (optional)" }`

**Response `200`:** `{ "status": "abandoned" }`

---

### 2.4 AI Channels

Fully automated PAP-facing sessions.

#### `POST /ai/sessions`
Start an AI-powered feedback conversation.

**Auth:** Public

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `channel` | string | ✓ | `sms` \| `whatsapp` \| `phone_call` |
| `phone_number` | string | — | max 20 |
| `whatsapp_id` | string | — | max 50 |
| `project_id` | UUID | — | Auto-detected if omitted |
| `language` | string | — | `sw` \| `en` (default `sw`) |
| `gateway_session_id` | string | — | |
| `gateway_provider` | string | — | |

**Response `201`:**
| Field | Type |
|-------|------|
| `session_id` | UUID |
| `reply` | string |
| `submitted` | boolean |
| `status` | string |
| `turn_count` | integer |
| `confidence` | float |
| `language` | string |

---

#### `POST /ai/sessions/{session_id}/message`
Send PAP message. Auto-submits if confidence ≥ 0.80.

**Auth:** Public

**Request body:** `{ "message": "string (1–2000 chars)" }`

**Response `200`:**
| Field | Type |
|-------|------|
| `session_id` | UUID |
| `reply` | string |
| `submitted` | boolean |
| `feedback_id` | UUID (nullable) |
| `unique_ref` | string (nullable) |
| `status` | string |
| `turn_count` | integer |
| `confidence` | float |
| `language` | string |

---

#### `GET /ai/sessions/{session_id}`
Check session status and conversation history.

**Auth:** Public

**Response `200`:**
| Field | Type |
|-------|------|
| `session_id` | string |
| `status` | string |
| `channel` | string |
| `language` | string |
| `turn_count` | integer |
| `confidence` | float |
| `extracted_data` | object |
| `feedback_id` | string (nullable) |
| `transcript` | array |
| `started_at` | datetime |
| `completed_at` | datetime |

---

### 2.5 Channel Webhooks

#### `POST /webhooks/sms`
Inbound SMS (Africa's Talking / Twilio). Fully automated.

**Auth:** Public (webhook)

**Request:** Form data (provider-specific)

**Response `200`:** `{ "message": "reply text" }`

---

#### `POST /webhooks/whatsapp`
Inbound WhatsApp (Meta Cloud API). Supports text, voice notes, images, documents.

**Auth:** Public (webhook)

**Request:** JSON from Meta

**Response `200`:** `{ "status": "ok" }`

---

#### `GET /webhooks/whatsapp`
WhatsApp webhook verification (hub.challenge).

**Auth:** Public

**Query params:** `hub.mode`, `hub.verify_token`, `hub.challenge`

**Response `200`:** Plain text challenge or `"Forbidden"`

---

### 2.6 Committees

#### `POST /committees`
Create a Grievance Handling Committee (GHC).

**Auth:** Staff

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | ✓ | 3–255 chars |
| `level` | string | ✓ | `ward` \| `lga_piu` \| `pcu` \| `tarura_wbcu` \| `tanroads` |
| `project_id` | UUID | — | |
| `lga` | string | — | max 100 |
| `org_sub_project_id` | UUID | — | |
| `description` | string | — | max 500 |
| `stakeholder_ids` | UUID[] | — | |

**Response `201`:** Committee object

---

#### `GET /committees`
**Auth:** Staff

**Query params:** `project_id`, `level`, `lga`, `org_sub_project_id`, `stakeholder_id`, `active_only` (default true)

**Response `200`:** `{ "items": [...] }`

---

#### `PATCH /committees/{committee_id}`
**Auth:** Staff

**Request body** (all optional): `name`, `lga`, `description`, `is_active`, `org_sub_project_id`, `stakeholder_ids`

**Response `200`:** Committee object

---

#### `POST /committees/{committee_id}/stakeholders/{stakeholder_id}`
Link a stakeholder group to this GHC.

**Auth:** Staff | **Response `200`:** Committee object

---

#### `DELETE /committees/{committee_id}/stakeholders/{stakeholder_id}`
**Auth:** Staff | **Response `200`:** Committee object

---

#### `POST /committees/{committee_id}/members`
Add member.

**Auth:** Staff

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `user_id` | UUID | ✓ | |
| `role` | string | — | `chairperson` \| `secretary` \| `member` (default `member`) |

**Response `201`:** Member object

---

#### `DELETE /committees/{committee_id}/members/{user_id}`
**Auth:** Staff | **Response `200`:** `{ "message": "string" }`

---

### 2.7 PAP Portal

#### `POST /my/feedback`
PAP self-service submission. Channel auto-set to `web_portal`.

**Auth:** PAP (authenticated user)

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `feedback_type` | string | ✓ | `grievance` \| `suggestion` \| `applause` |
| `description` | string | ✓ | min 10 chars |
| `issue_lga` | string | ✓ | min 2 chars (required for AI detection) |
| `project_id` | UUID | — | |
| `category` | string | — | |
| `subject` | string | — | max 500 |
| `is_anonymous` | boolean | — | default false |
| `submitter_name` | string | — | max 255 |
| `submitter_phone` | string | — | max 20 |
| `issue_ward` | string | — | |
| `issue_location_description` | string | — | |
| `issue_gps_lat` | float | — | |
| `issue_gps_lng` | float | — | |
| `subproject_id` | UUID | — | |
| `date_of_incident` | string | — | YYYY-MM-DD |
| `media_urls` | string[] | — | |

**Response `201`:**
```json
{
  "feedback_id": "uuid", "tracking_number": "string", "status": "string",
  "status_label": "string", "feedback_type": "string", "ai_classified": true, "message": "string"
}
```

---

#### `GET /my/feedback`
List my submissions.

**Auth:** PAP

**Query params:** `feedback_type`, `status`, `project_id`, `skip`, `limit` (max 200)

**Response `200`:**
```json
{
  "items": [{"id": "uuid", "unique_ref": "string", "feedback_type": "string",
    "category": "string", "subject": "string", "channel": "string",
    "status": "string", "status_label": "string", "current_level": "string",
    "priority": "string", "submitted_at": "datetime", "resolved_at": "datetime",
    "project_id": "uuid"}],
  "count": 0
}
```

---

#### `GET /my/feedback/summary`
Counts for dashboard widget.

**Auth:** PAP

**Query params:** `project_id` (optional)

**Response `200`:**
```json
{
  "total": 0, "open": 0, "resolved": 0, "closed": 0,
  "by_type": [{"type": "grievance", "count": 0}],
  "by_status": [{"status": "string", "label": "string", "count": 0}],
  "pending_escalation_requests": 0
}
```

---

#### `GET /my/feedback/{feedback_id}`
Full tracking view with actions, escalations, resolution, appeal.

**Auth:** PAP

**Response `200`:** Comprehensive tracking object (all fields + `public_actions`, `escalation_trail`, `resolution`, `appeal`, `escalation_requests`, `can_request_escalation`, `can_appeal`, `can_add_comment`)

---

#### `POST /my/feedback/{feedback_id}/escalation-request`
Request PIU to escalate grievance.

**Auth:** PAP

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `reason` | string | ✓ (min 10) |
| `requested_level` | string | — |

**Response `201`:** `{ "id": "uuid", "status": "string", "message": "string" }`

---

#### `POST /my/feedback/{feedback_id}/appeal`
File formal appeal against resolution.

**Auth:** PAP

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `grounds` | string | ✓ (min 10) |

**Response `201`:**
```json
{ "appeal_id": "uuid", "status": "string", "now_at_level": "string", "message": "string" }
```

---

#### `POST /my/feedback/{feedback_id}/add-comment`
Add follow-up comment.

**Auth:** PAP

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `comment` | string | ✓ (5–2000 chars) |

**Response `201`:** `{ "message": "string", "action_id": "uuid" }`

---

#### `GET /escalation-requests`
List PAP escalation requests (staff view).

**Auth:** Staff

**Query params:** `project_id`, `status` (default `pending`), `skip`, `limit`

**Response `200`:** `{ "items": [...], "count": 0 }`

---

#### `POST /escalation-requests/{request_id}/approve`
**Auth:** Staff

**Request body:** `{ "notes": "string (optional)" }`

**Response `200`:** `{ "status": "string", "message": "string", "feedback_id": "uuid" }`

---

#### `POST /escalation-requests/{request_id}/reject`
**Auth:** Staff

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `notes` | string | ✓ (min 5) |

**Response `200`:** `{ "status": "string", "message": "string" }`

---

### 2.8 Reports

All report endpoints require **Staff** auth. Most support `format=json|pdf|xlsx|csv`.

#### `GET /reports/performance`
Overall performance dashboard (all types).

**Query params:** `project_id`, `stage_id`, `from_date`, `to_date`, `region`, `district`, `lga`, `ward`, `mtaa`, `priority`, `channel`, `submission_method`, `format`

---

#### `GET /reports/grievances`
Grievance performance page.

**Query params:** Same as above + `status`, `time_unit` (`seconds`\|`minutes`\|`hours`\|`days`\|`custom`), `custom_seconds`

---

#### `GET /reports/grievance-performance`
Full grievance analytics — volume, rates, response times, SLA compliance, escalation breakdown, location/category/daily/stage/stakeholder/channel breakdowns.

**Query params:** `project_id`, `stage_id`, `subproject_id`, `stakeholder_id`, `category`, `from_date`, `to_date`, `region`, `district`, `lga`, `ward`, `mtaa`, `channel`, `submission_method`, `status`, `time_unit`, `custom_seconds`

**Response `200`:** `GrievancePerformanceResponse`

---

#### `GET /reports/suggestions`
Suggestion performance page.

**Query params:** Same as grievances.

---

#### `GET /reports/suggestion-performance`
Full suggestion analytics.

**Query params:** Same as grievance-performance.

**Response `200`:** `SuggestionPerformanceResponse`

---

#### `GET /reports/suggestions/detailed`
Extended suggestion analytics (daily rate, category/location/stakeholder/stage/implementation time breakdown).

**Query params:** `project_id`, `stage_id`, `subproject_id`, `stakeholder_id`, `from_date`, `to_date`, `category`, `region`, `district`, `lga`, `ward`, `mtaa`, `group_location_by` (default `lga`), `format`

---

#### `GET /reports/applause`
Applause performance page.

---

#### `GET /reports/applause-performance`
Full applause analytics.

**Response `200`:** `ApplausePerformanceResponse`

---

#### `GET /reports/channels`
Breakdown by intake channel and submission method.

**Query params:** `project_id`, `from_date`, `to_date`, `feedback_type`, `format`

---

#### `GET /reports/grievance-log`
Full grievance log (SEP Annex 5/6 format).

**Query params:** `project_id`, `from_date`, `to_date`, `region`, `district`, `lga`, `ward`, `mtaa`, `priority`, `channel`, `status`, `skip`, `limit` (max 500), `format`

---

#### `GET /reports/suggestion-log`
Full suggestion log.

---

#### `GET /reports/applause-log`
Full applause log.

---

#### `GET /reports/summary`
Count summary.

**Query params:** `project_id` (required), `format`

---

#### `GET /reports/overdue`
Grievances past target resolution date.

**Query params:** `project_id`, `priority`, `format`

---

### 2.9 Voice

#### `POST /voice/feedback/{feedback_id}/voice-note`
Upload audio as voice note. Transcribed and optionally used as description.

**Auth:** Bearer token (authenticated user)

**Request:** `multipart/form-data`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `audio` | file | ✓ | OGG/WebM/MP3/WAV/AAC/AMR, max 25 MB |
| `language` | string | — | `sw` \| `en` (default `sw`) |
| `use_as_description` | boolean | — | default true |

**Response `200`:**
| Field | Type |
|-------|------|
| `feedback_id` | string |
| `voice_note_url` | string |
| `transcription` | string |
| `language` | string |
| `confidence` | float |
| `duration_seconds` | float |
| `service` | string |
| `flagged_for_review` | boolean |
| `description_updated` | boolean |

---

#### `POST /voice/sessions/{session_id}/audio-turn`
Submit voice turn in active conversation. Transcribed, fed to LLM, auto-submits if confident.

**Auth:** Public

**Request:** `multipart/form-data`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `audio` | file | ✓ | |
| `language` | string | — | Override detection |
| `tts_reply` | boolean | — | Synthesise TTS for reply |

**Response `200`:**
| Field | Type |
|-------|------|
| `session_id` | string |
| `turn_index` | integer |
| `transcription` | string |
| `language` | string |
| `confidence` | float |
| `audio_url` | string |
| `flagged_for_review` | boolean |
| `lm_reply` | string (nullable) |
| `tts_audio_url` | string (nullable) |
| `session_status` | string |
| `feedback_id` | string (nullable) |

---

#### `POST /voice/sessions/{session_id}/tts`
Generate TTS audio for playback.

**Auth:** Public

**Request:** `multipart/form-data`
| Field | Type | Required |
|-------|------|----------|
| `text` | string | ✓ |
| `language` | string | — (`sw` \| `en`) |
| `voice_id` | string | — |

**Response `200`:**
```json
{ "session_id": "string", "audio_url": "string", "duration_seconds": 0.0, "service": "string", "language": "string" }
```

---

### 2.10 Actions

#### `POST /feedback/{feedback_id}/actions`
Log an action taken on feedback.

**Auth:** Staff

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `action_type` | string | ✓ | `acknowledgement` \| `investigation` \| `site_visit` \| `stakeholder_meeting` \| `internal_review` \| `response` \| `escalation_note` \| `resolution_draft` \| `appeal_review` \| `note` |
| `description` | string | ✓ | min 5 chars |
| `is_internal` | boolean | — | default false |
| `response_method` | string | — | `verbal` \| `written_letter` \| `email` \| `sms` \| `phone_call` \| `in_person_meeting` \| `notice_board` \| `other` |
| `response_summary` | string | — | |

**Response `201`:** Action object

---

#### `GET /feedback/{feedback_id}/actions`
**Auth:** Staff | **Response `200`:** `{ "items": [...] }`

---

## 3. Stakeholder Service

Nginx routes: `/api/v1/projects`, `/api/v1/stakeholders`, `/api/v1/activities`, `/api/v1/communications`, `/api/v1/focal-persons`

All endpoints require **Staff** (Bearer token).

### 3.1 Stakeholders

#### `POST /stakeholders`
Register a stakeholder.

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `stakeholder_type` | string | ✓ | `pap` \| `interested_party` |
| `entity_type` | string | ✓ | `individual` \| `organization` \| `group` |
| `category` | string | ✓ | `individual` \| `local_government` \| `national_government` \| `ngo_cbo` \| `community_group` \| `private_company` \| `utility_provider` \| `development_partner` \| `media` \| `academic_research` \| `vulnerable_group` \| `other` |
| `org_name` | string | — | Required for org/group entity_type; max 255 |
| `first_name` | string | — | For individuals; max 100 |
| `last_name` | string | — | max 100 |
| `affectedness` | string | — | `positively_affected` \| `negatively_affected` \| `both` \| `unknown` |
| `importance_rating` | string | — | `high` \| `medium` \| `low` (default `medium`) |
| `lga` | string | — | |
| `ward` | string | — | |
| `language_preference` | string | — | `sw` \| `en` (default `sw`) |
| `preferred_channel` | string | — | `public_meeting` \| `focus_group` \| `email` \| `sms` \| `phone_call` \| `radio` \| `tv` \| `social_media` \| `billboard` \| `notice_board` \| `letter` \| `in_person` |
| `needs_translation` | boolean | — | default false |
| `needs_transport` | boolean | — | default false |
| `needs_childcare` | boolean | — | default false |
| `is_vulnerable` | boolean | — | default false |
| `vulnerable_group_types` | string[] | — | `children` \| `women_low_income` \| `disabled_physical` \| `disabled_mental` \| `elderly` \| `youth` \| `low_income` \| `indigenous` \| `language_barrier` |
| `participation_barriers` | string | — | |
| `org_id` | UUID | — | Riviwa org UUID |
| `address_id` | UUID | — | |
| `notes` | string | — | |

**Response `201`:** Stakeholder object

---

#### `GET /stakeholders`
**Query params:** `stakeholder_type`, `category`, `lga`, `affectedness`, `is_vulnerable`, `importance`, `project_id`, `stage_id`, `skip`, `limit` (max 200)

**Response `200`:** `{ "items": [...], "count": 0 }`

---

#### `GET /stakeholders/analysis`
Stakeholder Analysis Matrix (Annex 3 / SEP format).

**Query params:** `project_id` (required), `stage_id`, `importance`, `category`, `affectedness`, `is_vulnerable`, `skip`, `limit` (max 500)

**Response `200`:** Analysis rows with `why_important`, `interests`, `potential_risks`, `how_to_engage`, `when_to_engage`, `importance`

---

#### `GET /stakeholders/{stakeholder_id}`
Detail with contacts.

**Response `200`:** Stakeholder + `contacts` array

---

#### `PATCH /stakeholders/{stakeholder_id}`
**Request body** (all optional): `affectedness`, `importance_rating`, `org_name`, `first_name`, `last_name`, `address_id`, `lga`, `ward`, `language_preference`, `preferred_channel`, `needs_translation`, `needs_transport`, `needs_childcare`, `is_vulnerable`, `vulnerable_group_types`, `participation_barriers`, `notes`, `logo_url`

**Response `200`:** Stakeholder + contacts

---

#### `DELETE /stakeholders/{stakeholder_id}`
Soft-delete. Admin-only.

**Response `200`:** `{ "message": "string" }`

---

#### `POST /stakeholders/{stakeholder_id}/projects`
Register stakeholder under a project.

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `project_id` | UUID | ✓ |
| `is_pap` | boolean | — |
| `affectedness` | string | — |
| `impact_description` | string | — |

**Response `201`:** Project registration object

---

#### `GET /stakeholders/{stakeholder_id}/projects`
**Response `200`:** `{ "items": [...] }`

---

#### `GET /stakeholders/{stakeholder_id}/engagements`
**Response `200`:** `{ "items": [engagement objects] }`

---

### 3.2 Contacts

#### `POST /stakeholders/{stakeholder_id}/contacts`
**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `full_name` | string | ✓ | max 255 |
| `title` | string | — | max 100 |
| `role_in_org` | string | — | max 255 |
| `email` | string | — | max 255 |
| `phone` | string | — | E.164, max 20 |
| `user_id` | UUID | — | Link to Riviwa user |
| `preferred_channel` | string | — | default `phone_call` |
| `is_primary` | boolean | — | default false |
| `can_submit_feedback` | boolean | — | default true |
| `can_receive_communications` | boolean | — | default true |
| `can_distribute_communications` | boolean | — | default false |
| `notes` | string | — | |

**Response `201`:** Contact object

---

#### `GET /stakeholders/{stakeholder_id}/contacts`
**Query params:** `active_only` (default true)

**Response `200`:** `{ "items": [...] }`

---

#### `PATCH /stakeholders/{stakeholder_id}/contacts/{contact_id}`
**Request body** (all optional): same fields as create.

**Response `200`:** Contact object

---

#### `DELETE /stakeholders/{stakeholder_id}/contacts/{contact_id}`
**Request body:** `{ "reason": "string" }` (optional)

**Response `200`:** `{ "message": "string" }`

---

### 3.3 Activities

#### `POST /activities`
**Request body:** Activity fields (raw dict):
- `project_id` (UUID, required), `stage_id`, `subproject_id`, `stage`, `activity_type`, `status`, `title`, `description`, `agenda`, `venue`, `lga`, `ward`, `gps_lat`, `gps_lng`, `virtual_platform`, `virtual_url`, `scheduled_at`, `duration_hours`, `expected_count`

**Response `201`:** Activity object

---

#### `GET /activities`
**Query params:** `project_id`, `stage`, `status`, `lga`, `skip`, `limit`

**Response `200`:** `{ "items": [...] }`

---

#### `GET /activities/{activity_id}`
Detail with attendance records.

**Response `200`:** Activity + `attendances` array

---

#### `PATCH /activities/{activity_id}`
**Request body:** Fields to update (raw dict)

**Response `200`:** Activity object

---

#### `POST /activities/{activity_id}/cancel`
**Request body:** `{ "reason": "string" }` (optional)

**Response `200`:** Activity object

---

#### `POST /activities/{activity_id}/attendances`
Log attendance.

**Request body:** `{ "contact_id": "uuid", "attendance_status": "string", "concerns_raised": "string", ... }`

**Response `201`:** Attendance object

---

#### `PATCH /activities/{activity_id}/attendances/{engagement_id}`
**Request body:** Fields to update | **Response `200`:** Attendance object

---

#### `POST /activities/{activity_id}/attendances/bulk`
**Request body:** `{ "records": [{"contact_id": "uuid", ...}] }`

**Response `201`:** `{ "activity_id": "uuid", "logged": 0, "items": [...] }`

---

#### `DELETE /activities/{activity_id}/attendances/{engagement_id}`
**Response `200`:** `{ "message": "string" }`

---

#### `POST /activities/{activity_id}/media`
**Request:** `multipart/form-data`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `file` | file | ✓ | |
| `title` | string | ✓ | |
| `media_type` | string | — | `minutes` \| `photo` \| `presentation` \| `document` \| `other` |
| `description` | string | — | |

**Response `201`:** Media object

---

#### `GET /activities/{activity_id}/media`
**Query params:** `media_type`

**Response `200`:** `{ "activity_id": "uuid", "total": 0, "items": [...] }`

---

#### `DELETE /activities/{activity_id}/media/{media_id}`
**Response `200`:** `{ "message": "string" }`

---

### 3.4 Communications

#### `POST /communications`
**Request body:** Communication fields: `project_id` (required), `stakeholder_id`, `contact_id`, `channel`, `direction`, `purpose`, `subject`, `content_summary`, `document_urls`, `distribution_required`, `distribution_deadline`, `sent_at`

**Response `201`:** Communication object

---

#### `GET /communications`
**Query params:** `project_id`, `stakeholder_id`, `direction`, `channel`, `skip`, `limit`

**Response `200`:** `{ "items": [...] }`

---

#### `GET /communications/{comm_id}`
Detail with distributions.

**Response `200`:** Communication + `distributions` array

---

#### `POST /communications/{comm_id}/distributions`
**Request body:** `{ "contact_id": "uuid", "distribution_method": "string", "distributed_to_count": 0, ... }`

**Response `201`:** Distribution object

---

#### `PATCH /communications/{comm_id}/distributions/{dist_id}`
**Request body:** Fields to update (concerns, acknowledgement, feedback ref)

**Response `200`:** Distribution object

---

### 3.5 Focal Persons

#### `POST /focal-persons`
Register (SEP Table 9 format).

**Request body:** `project_id` (required), `org_type`, `organization_name`, `title`, `full_name`, `phone`, `email`, `address`, `lga`, `subproject`, `user_id`, `notes`

**Response `201`:** Focal person object

---

#### `GET /focal-persons`
**Query params:** `project_id`, `org_type`, `active_only` (default true)

**Response `200`:** `{ "items": [...] }`

---

#### `PATCH /focal-persons/{fp_id}`
**Request body:** Fields to update | **Response `200`:** Focal person object

---

### 3.6 Projects (Stakeholder)

#### `GET /projects`
List synced projects.

**Query params:** `status`, `org_id`, `lga`, `skip`, `limit`

**Response `200`:** `{ "items": [...project objects], "count": 0 }`

---

#### `GET /projects/{project_id}`
Project landing page with stages, counts, stakeholders, and activities.

**Response `200`:** Project + `stages` + `counts` + `stakeholders` + `activities`

---

### 3.7 Reports (Stakeholder)

| Endpoint | Description | Required Query Param |
|----------|-------------|----------------------|
| `GET /reports/engagement-summary` | Activity counts by stage and LGA | `project_id` |
| `GET /reports/stakeholder-reach` | Stakeholder counts by category and vulnerability | `project_id` |
| `GET /reports/pending-distributions` | Communications requiring distribution | `project_id` |
| `GET /reports/pending-concerns` | Distributions with unresolved concerns | `project_id` |

---

## 4. Notification Service

Nginx routes: `/api/v1/notifications`, `/api/v1/devices`, `/api/v1/notification-preferences`

### 4.1 Devices

#### `POST /devices`
Register a push notification device token.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `platform` | string | ✓ | `fcm` \| `apns` |
| `push_token` | string | ✓ | max 512 |
| `device_name` | string | — | |
| `app_version` | string | — | |

**Response `200`:**
```json
{ "id": "uuid", "platform": "string", "device_name": "string", "is_active": true, "registered_at": "datetime" }
```

---

#### `GET /devices`
List registered devices for current user.

**Auth:** Bearer token

**Response `200`:** Array of `DeviceResponse`

---

#### `PATCH /devices/{device_id}/token`
Update push token.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `push_token` | string | ✓ (max 512) |
| `app_version` | string | — |

**Response `200`:** `DeviceResponse`

---

#### `DELETE /devices/{device_id}`
Deregister device.

**Auth:** Bearer token | **Response `200`:** `{ "message": "string" }`

---

### 4.2 Notifications Inbox

#### `GET /notifications`
**Auth:** Bearer token

**Query params:** `unread_only` (bool, default false), `skip` (default 0), `limit` (1–100, default 30)

**Response `200`:**
```json
{
  "unread_count": 0,
  "returned": 0,
  "items": [{
    "delivery_id": "uuid",
    "notification_id": "uuid",
    "notification_type": "string",
    "priority": "string",
    "rendered_title": "string",
    "rendered_body": "string",
    "read_at": "datetime",
    "created_at": "datetime",
    "is_read": false
  }]
}
```

---

#### `GET /notifications/unread-count`
**Auth:** Bearer token | **Response `200`:** `{ "unread_count": 0 }`

---

#### `PATCH /notifications/deliveries/{delivery_id}/read`
Mark single notification as read.

**Auth:** Bearer token | **Response `200`:** `{ "message": "string", "delivery_id": "uuid" }`

---

#### `POST /notifications/mark-all-read`
**Auth:** Bearer token | **Response `200`:** `{ "message": "string", "count": 0 }`

---

### 4.3 Preferences

#### `GET /notification-preferences`
**Auth:** Bearer token

**Response `200`:** Array of preference objects:
```json
{ "id": "uuid", "user_id": "uuid", "notification_type": "string", "channel": "string", "enabled": true, "updated_at": "datetime" }
```

---

#### `PUT /notification-preferences`
Set a preference.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `notification_type` | string | ✓ | |
| `channel` | string | ✓ | `in_app` \| `push` \| `sms` \| `whatsapp` \| `email` |
| `enabled` | boolean | ✓ | |

**Response `200`:** `{ "message": "string", "notification_type": "string", "channel": "string", "enabled": true }`

---

#### `DELETE /notification-preferences/{notification_type}/{channel}`
Reset preference to default.

**Auth:** Bearer token | **Response `200`:** `{ "message": "string" }`

---

### 4.4 Internal Dispatch

#### `POST /internal/dispatch`
Dispatch a notification (HTTP alternative to Kafka).

**Auth:** `X-Service-Key`

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `notification_type` | string | ✓ | Template key |
| `recipient_user_id` | UUID | — | |
| `recipient_phone` | string | — | |
| `recipient_email` | string | — | |
| `recipient_push_tokens` | string[] | — | |
| `language` | string | — | default `en` |
| `variables` | object | — | Template variables |
| `preferred_channels` | string[] | — | `in_app` \| `push` \| `sms` \| `whatsapp` \| `email` |
| `priority` | string | — | `critical` \| `high` \| `medium` \| `low` |
| `idempotency_key` | string | — | |
| `scheduled_at` | datetime | — | |
| `source_service` | string | — | |
| `source_entity_id` | string | — | |
| `metadata` | object | — | |

**Response `200`:** `{ "notification_id": "uuid", "accepted": true }`

---

#### `POST /internal/dispatch/batch`
Dispatch multiple notifications.

**Auth:** `X-Service-Key`

**Request body:** Array of dispatch request objects.

**Response `200`:** `{ "accepted": 0, "results": [{"notification_id": "uuid"}] }`

---

### 4.5 Templates

#### `GET /templates`
**Auth:** `X-Service-Key`

**Query params:** `notification_type`, `channel`, `language`

**Response `200`:** Array of template objects

---

#### `PUT /templates`
Create or update a template.

**Auth:** `X-Service-Key`

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `notification_type` | string | ✓ | max 120 |
| `channel` | string | ✓ | `in_app` \| `push` \| `sms` \| `whatsapp` \| `email` |
| `language` | string | — | max 5, default `en` |
| `title_template` | string | — | max 300 |
| `subject_template` | string | — | max 300 |
| `body_template` | string | ✓ | Jinja2 template |
| `is_active` | boolean | — | default true |

**Response `200`:** Template object

---

#### `DELETE /templates/{template_id}`
**Auth:** `X-Service-Key` | **Response `200`:** `{ "message": "string" }`

---

### 4.6 Webhooks (Notification)

| Method | Path | Provider | Auth |
|--------|------|----------|------|
| `POST` | `/webhooks/sms/at/dlr` | Africa's Talking DLR | Public (form) |
| `POST` | `/webhooks/sms/twilio/dlr` | Twilio DLR | Public (form) |
| `POST` | `/webhooks/email/sendgrid` | SendGrid events | Public (JSON) |
| `POST` | `/webhooks/whatsapp/meta` | Meta WhatsApp status | Public (JSON) |
| `GET` | `/webhooks/whatsapp/meta` | Meta hub.challenge | Public |

---

## 5. Payment Service

Nginx routes: `/api/v1/payments`

### 5.1 Payments

#### `POST /payments`
Create payment intent.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `payment_type` | string | ✓ | `grievance_fee` \| `project_contribution` \| `service_fee` \| `subscription` \| `refund` |
| `amount` | float | ✓ | |
| `currency` | string | — | `TZS` \| `USD` \| `KES` (default `TZS`) |
| `phone` | string | ✓ | |
| `payer_name` | string | — | |
| `payer_email` | string | — | |
| `description` | string | — | |
| `org_id` | UUID | — | |
| `project_id` | UUID | — | |
| `reference_id` | UUID | — | |
| `reference_type` | string | — | |

**Response `201`:** Payment object:
```json
{
  "id": "uuid", "payment_type": "string", "amount": 0.0, "currency": "TZS",
  "description": "string", "status": "string", "external_ref": "string",
  "payer_user_id": "uuid", "payer_phone": "string", "payer_name": "string",
  "org_id": "uuid", "project_id": "uuid", "reference_id": "uuid",
  "reference_type": "string", "created_at": "datetime", "expires_at": "datetime", "paid_at": "datetime"
}
```

---

#### `GET /payments`
**Auth:** Bearer token

**Query params:** `payer_user_id`, `org_id`, `project_id`, `reference_id`, `status`, `payment_type`, `skip`, `limit` (max 200)

**Response `200`:** `{ "items": [...], "count": 0 }`

---

#### `GET /payments/{payment_id}`
Detail with transactions.

**Auth:** Bearer token

**Response `200`:** Payment + `transactions: [PaymentTransaction]`

---

#### `POST /payments/{payment_id}/initiate`
Initiate payment via provider.

**Auth:** Bearer token

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `provider` | string | ✓ | `azampay` \| `selcom` \| `mpesa` |

**Response `200`:** Transaction object + `checkout_url`, `message`

---

#### `POST /payments/{payment_id}/verify`
Poll provider for latest status.

**Auth:** Bearer token | **Response `200`:** `PaymentTransaction` object

---

#### `POST /payments/{payment_id}/refund`
**Auth:** Bearer token (staff role) | **Response `200`:** Transaction + `{ "message": "string" }`

---

#### `DELETE /payments/{payment_id}`
Cancel a PENDING payment.

**Auth:** Bearer token | **Response `200`:** `{ "message": "string", "payment_id": "uuid" }`

---

#### `GET /payments/{payment_id}/transactions`
**Auth:** Bearer token | **Response `200`:** `{ "items": [...], "count": 0 }`

**Transaction object fields:** `id`, `payment_id`, `provider`, `status`, `provider_ref`, `provider_receipt`, `settled_amount`, `failure_reason`, `initiated_at`, `completed_at`

---

### 5.2 Webhooks (Payment)

| Method | Path | Provider | Auth |
|--------|------|----------|------|
| `POST` | `/webhooks/azampay` | AzamPay callback | Public |
| `POST` | `/webhooks/selcom` | Selcom callback | HMAC signature |
| `POST` | `/webhooks/mpesa` | M-Pesa callback | Public |

All return `200` with `{ "status": "received" }`.

---

## 6. AI Service

Port 8085. Routes under `/api/v1/ai`.

### 6.1 Conversations

#### `POST /ai/conversations`
Start a new AI conversation (Rivai assistant).

**Auth:** Optional Bearer token

**Request body:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `channel` | string | — | `web` \| `mobile` (default `web`) |
| `language` | string | — | `sw` \| `en` (default `sw`) |
| `project_id` | UUID | — | |
| `user_id` | UUID | — | |
| `web_token` | string | — | |

**Response `201`:**
| Field | Type |
|-------|------|
| `conversation_id` | string |
| `reply` | string |
| `status` | string |
| `stage` | string |
| `turn_count` | integer |
| `confidence` | float |
| `language` | string |
| `submitted` | boolean |
| `submitted_feedback` | array |
| `project_name` | string (nullable) |
| `is_urgent` | boolean |
| `incharge_name` | string (nullable) |
| `incharge_phone` | string (nullable) |

---

#### `POST /ai/conversations/{conversation_id}/message`
Send a message.

**Auth:** None

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `message` | string | ✓ (1–4000 chars) |
| `media_urls` | string[] | — |

**Response `200`:** Same as `POST /ai/conversations`

---

#### `GET /ai/conversations/{conversation_id}`
Get status and transcript.

**Auth:** None

**Response `200`:**
| Field | Type |
|-------|------|
| `conversation_id` | string |
| `channel` | string |
| `status` | string |
| `stage` | string |
| `language` | string |
| `turn_count` | integer |
| `confidence` | float |
| `is_registered` | boolean |
| `submitter_name` | string (nullable) |
| `project_id` | UUID (nullable) |
| `project_name` | string (nullable) |
| `extracted_data` | object |
| `submitted_feedback` | array |
| `transcript` | array |
| `is_urgent` | boolean |
| `incharge_name` | string (nullable) |
| `incharge_phone` | string (nullable) |
| `started_at` | datetime |
| `last_active_at` | datetime |
| `completed_at` | datetime (nullable) |

---

### 6.2 AI Admin

All require staff role (Bearer token).

#### `GET /ai/admin/conversations`
**Query params:** `status`, `channel`, `skip`, `limit` (max 200)

**Response `200`:** `{ "items": [...], "count": 0 }`

---

#### `GET /ai/admin/conversations/{conversation_id}`
**Response `200`:** Full conversation detail (all fields)

---

#### `POST /ai/admin/conversations/{conversation_id}/force-submit`
**Response `200`:** `{ "submitted": true, "results": {...} }`

---

### 6.3 AI Internal

**Auth:** `X-Service-Key`

#### `POST /ai/internal/classify`
**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `feedback_type` | string | — |
| `description` | string | ✓ |
| `issue_location_description` | string | — |
| `issue_lga` | string | — |
| `issue_ward` | string | — |
| `issue_region` | string | — |

**Response `200`:**
```json
{ "project_id": "uuid", "project_name": "string", "category_slug": "string", "category_def_id": "uuid", "confidence": 0.0, "classified": true }
```

---

#### `POST /ai/internal/candidate-projects`
**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `description` | string | ✓ |
| `issue_lga` | string | ✓ |
| `issue_ward` | string | ✓ |
| `issue_location_description` | string | ✓ |
| `top_k` | integer | — (max 10, default 5) |

**Response `200`:**
```json
{ "projects": [{"project_id": "uuid", "name": "string", "region": "string", "lga": "string", "score": 0.0}] }
```

---

### 6.4 Webhooks (AI)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ai/webhooks/sms` | Inbound SMS (Africa's Talking / Twilio) |
| `POST` | `/ai/webhooks/whatsapp` | Inbound WhatsApp (Meta) |
| `GET` | `/ai/webhooks/whatsapp` | WhatsApp hub.challenge verification |

---

## 7. Recommendation Service

Port 8086.

### 7.1 Recommendations

#### `GET /recommendations/{entity_id}`
Get recommendations for an entity.

**Auth:** Bearer token

**Query params:**
| Param | Type | Notes |
|-------|------|-------|
| `limit` | integer | 1–100, default 20 |
| `page` | integer | default 1 |
| `min_score` | float | 0–1, default 0.1 |
| `entity_type` | string | `project` \| `organisation` |
| `category_filter` | string | |
| `geo_only` | boolean | default false |
| `include_explanation` | boolean | default false |

**Response `200`:**
```json
{
  "entity_id": "uuid",
  "recommendations": [{
    "entity_id": "uuid", "entity_type": "string",
    "name": "string", "slug": "string", "description": "string",
    "category": "string", "sector": "string",
    "cover_image_url": "string", "org_logo_url": "string",
    "latitude": 0.0, "longitude": 0.0, "city": "string",
    "region": "string", "country_code": "string", "status": "string",
    "score": 0.0, "score_breakdown": {}, "distance_km": 0.0,
    "shared_tags": [], "interactions": 0,
    "accepts_grievances": true, "accepts_suggestions": true, "accepts_applause": true
  }],
  "total": 0, "page": 1, "page_size": 20, "generated_at": "datetime", "cache_hit": false
}
```

---

#### `GET /similar/{entity_id}`
Find semantically similar entities.

**Auth:** Bearer token

**Query params:** `limit` (1–100, default 20), `page` (default 1)

**Response `200`:**
```json
{ "entity_id": "uuid", "similar": [...], "total": 0, "page": 1, "page_size": 20, "generated_at": "datetime" }
```

---

### 7.2 Discovery

#### `GET /discover/nearby`
Discover entities near a location.

**Auth:** Bearer token

**Query params:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `latitude` | float | ✓ | −90 to 90 |
| `longitude` | float | ✓ | −180 to 180 |
| `radius_km` | float | — | 1–5000, default 50 |
| `entity_type` | string | — | `project` \| `organisation` |
| `category` | string | — | |
| `limit` | integer | — | 1–100, default 20 |
| `page` | integer | — | default 1 |

**Response `200`:**
```json
{
  "latitude": 0.0, "longitude": 0.0, "radius_km": 50.0,
  "results": [...], "total": 0, "page": 1, "page_size": 20, "generated_at": "datetime"
}
```

---

### 7.3 Indexing

**Auth:** `X-Service-Key` (all indexing endpoints)

#### `POST /index/entity`
Index or create an entity.

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `entity_id` | UUID | ✓ |
| `entity_type` | string | — (default `project`) |
| `source_service` | string | — |
| `organisation_id` | UUID | — |
| `name` | string | ✓ |
| `slug` | string | — |
| `description` | string | — |
| `category` | string | — |
| `sector` | string | — |
| `tags` | string[] | — |
| `country_code` | string | — |
| `region` | string | — |
| `primary_lga` | string | — |
| `city` | string | — |
| `latitude` | float | — |
| `longitude` | float | — |
| `status` | string | — (default `active`) |
| `cover_image_url` | string | — |
| `org_logo_url` | string | — |
| `accepts_grievances` | boolean | — (default true) |
| `accepts_suggestions` | boolean | — (default true) |
| `accepts_applause` | boolean | — (default true) |

**Response `200`:** `{ "status": "indexed", "entity_id": "uuid" }`

---

#### `PUT /index/entity/{entity_id}`
Update an indexed entity.

**Request body:** Same as POST | **Response `200`:** `{ "status": "indexed", "entity_id": "uuid" }`

---

#### `DELETE /index/entity/{entity_id}`
**Response `200`:** `{ "status": "deleted", "entity_id": "uuid" }`

---

#### `POST /index/activity`
Log an activity event (used for scoring signals).

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| `entity_id` | UUID | ✓ |
| `event_type` | string | ✓ |
| `actor_id` | UUID | — |
| `feedback_type` | string | — |
| `occurred_at` | datetime | — |
| `payload` | object | — |

**Response `200`:** `{ "status": "recorded", "entity_id": "uuid" }`
