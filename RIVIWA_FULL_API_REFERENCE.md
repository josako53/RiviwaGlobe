# Riviwa Platform — Full API Reference

> **Base URL:** `https://api.riviwa.com/api/v1`  
> **Auth:** `Authorization: Bearer <access_token>` (JWT, HS256)  
> **Content-Type:** `application/json` (unless noted as `multipart/form-data`)  
> **All timestamps:** ISO 8601 UTC  

---

## Table of Contents

1. [Auth Service](#1-auth-service-port-8000)
2. [Feedback Service](#2-feedback-service-port-8090)
3. [Stakeholder Service](#3-stakeholder-service-port-8070)
4. [Notification Service](#4-notification-service-port-8060)
5. [Payment Service](#5-payment-service-port-8040)
6. [AI Service](#6-ai-service-port-8085)
7. [Analytics Service](#7-analytics-service-port-8095)
   - 7.1 General Feedback Analytics
   - 7.2 Grievance Analytics
   - 7.3 Suggestion Analytics
   - 7.4 Staff Analytics
   - 7.5 Inquiry Analytics _(new)_
   - 7.6 Org-level Analytics _(new)_
   - 7.7 Platform-level Analytics _(new)_
   - 7.8 AI Insights — multi-scope _(updated)_
8. [Data Flow & Kafka Events](#8-data-flow--kafka-events)

---

## Role Hierarchy

| Org Role | Capabilities |
|----------|-------------|
| `MEMBER` | Read-only access |
| `MANAGER` | Read + invite members + create content |
| `ADMIN` | MANAGER + create/update most resources |
| `OWNER` | Full control including status changes, deletes |

| Platform Role | Capabilities |
|--------------|-------------|
| `moderator` | Limited admin |
| `admin` | Full platform access, bypass org scoping |
| `super_admin` | All access |

---

## 1. Auth Service (Port 8000)

**DB:** `auth_db` (port 5433) · **Redis:** DB 0 · **Nginx:** `/api/v1/auth`, `/api/v1/users`, `/api/v1/orgs`, `/api/v1/webhooks`

---

### 1.1 Registration

#### `POST /auth/register/init` — Step 1: submit email or phone
**Auth:** None

**Request body:**
```json
{
  "email": "user@example.com",
  "phone_number": "+255712345678",
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "John",
  "language": "en"
}
```
> Supply exactly one of `email` or `phone_number`.

**Response 200:**
```json
{
  "session_token": "eyJ...",
  "otp_channel": "email",
  "otp_destination": "u***@example.com",
  "expires_in_seconds": 600,
  "message": "OTP sent"
}
```

**Data flow:** Fraud engine → OTP dispatch (email/SMS) → `User` row created (no password yet) → Redis `reg_otp:<session_token>` (TTL 10 min)

**Errors:** `400` invalid format · `409` already registered · `403` fraud blocked

---

#### `POST /auth/register/verify-otp` — Step 2: verify OTP
**Auth:** None

**Request body:**
```json
{
  "session_token": "eyJ...",
  "otp_code": "123456"
}
```

**Response 200:**
```json
{
  "continuation_token": "eyJ...",
  "message": "Email verified. Complete registration."
}
```

**Data flow:** Redis lookup → OTP match → User email/phone marked verified → Redis `reg_cont:<continuation_token>` created (TTL 30 min)

**Errors:** `400` wrong OTP · `410` session expired · `429` max attempts (5 tries → session destroyed)

---

#### `POST /auth/register/complete` — Step 3: set password and activate
**Auth:** None

**Request body:**
```json
{
  "continuation_token": "eyJ...",
  "password": "Str0ng@Pass!",
  "confirm_password": "Str0ng@Pass!"
}
```

**Response 201:**
```json
{
  "action": "complete",
  "user_id": "uuid",
  "message": "Account active. Please log in."
}
```
> `action = "id_verification_pending"` if fraud score triggered REVIEW.

**Data flow:** Password hashed (Argon2id) → User status → `ACTIVE` → Kafka `user.registered` published → continuation token deleted

**Errors:** `400` weak password · `410` token expired

---

#### `POST /auth/register/resend-otp` — Resend OTP
**Auth:** None

**Request body:**
```json
{ "session_token": "eyJ..." }
```

**Response 200:** New `session_token` + `otp_destination`

**Errors:** `410` session expired · `429` 60-second cooldown

---

### 1.2 Login

#### `POST /auth/login` — Step 1: submit credentials
**Auth:** None

**Request body:**
```json
{
  "identifier": "user@example.com",
  "password": "Str0ng@Pass!"
}
```
> `identifier` = email or E.164 phone number.

**Response 200:**
```json
{
  "login_token": "eyJ...",
  "otp_channel": "email",
  "otp_destination": "u***@example.com",
  "expires_in_seconds": 300
}
```

**Data flow:** Credentials verified → OTP dispatched (email/SMS) → Redis `login_otp:<login_token>` (TTL 5 min)

**Errors:** `401` invalid credentials · `403` account suspended/banned · `423` account locked

---

#### `POST /auth/login/verify-otp` — Step 2: verify OTP → JWT pair
**Auth:** None

**Request body:**
```json
{
  "login_token": "eyJ...",
  "otp_code": "123456"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "opaque_token_string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Data flow:** Redis OTP match → JWT issued (claims: `sub`, `jti`, `org_id`, `org_role`) → Refresh token stored in Redis (TTL 30 days) → `failed_login_attempts` reset → `last_login_at` updated

**Errors:** `400` invalid/expired OTP · `429` max attempts (5 tries → session destroyed)

---

#### `POST /auth/token/refresh` — Rotate refresh token
**Auth:** None (refresh token in body)

**Request body:**
```json
{ "refresh_token": "opaque_token_string" }
```

**Response 200:** New `access_token` + `refresh_token` (old token deleted from Redis)

**Errors:** `401` invalid or expired refresh token

---

#### `POST /auth/token/logout` — Revoke session
**Auth:** Bearer JWT

**Request body:**
```json
{ "refresh_token": "opaque_token_string" }
```

**Response 200:** `{ "message": "Logged out successfully." }`

**Data flow:** JWT JTI added to Redis deny-list (TTL = remaining JWT lifetime) → Refresh token deleted from Redis

---

#### `POST /auth/switch-org` — Switch active org dashboard
**Auth:** Bearer JWT

**Request body:**
```json
{ "org_id": "uuid-or-null" }
```
> `org_id = null` → return to personal/consumer view.

**Response 200:**
```json
{
  "tokens": { "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 3600 },
  "org_id": "uuid",
  "org_role": "ADMIN"
}
```

**Errors:** `403` not an active member of requested org

---

#### `POST /auth/social` — Social login / registration (Google · Apple · Facebook)
**Auth:** None

**Request body:**
```json
{
  "provider": "google",
  "id_token": "google_credential_or_identity_token",
  "device_fingerprint": "optional_device_id"
}
```
> `provider`: `google` | `apple` | `facebook`

**Response 200:**
```json
{
  "user_id": "uuid",
  "is_new_user": true,
  "has_password": false,
  "tokens": { "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 3600 }
}
```

**Data flow:** Provider token verified → User upserted → JWT pair issued → Kafka `user.registered_social` (new) or `auth.login_success` (returning)

**Errors:** `401` invalid provider token · `409` email linked to different provider

---

#### `POST /auth/social/set-password` — Add password to social-only account
**Auth:** Bearer JWT

**Request body:**
```json
{ "password": "Str0ng@Pass!" }
```

**Response 200:** `{ "message": "Password set." }`

**Errors:** `400` weak password · `409` password already set (use `/auth/password/change`)

---

### 1.3 Password Management

#### `POST /auth/password/forgot` — Step 1: request OTP
**Auth:** None

**Request body:**
```json
{ "identifier": "user@example.com" }
```

**Response 200 (always, even if no account found):**
```json
{
  "reset_token": "eyJ...",
  "otp_channel": "email",
  "otp_destination": "u***@example.com",
  "expires_in_seconds": 600,
  "message": "If an account matches, an OTP has been sent."
}
```

---

#### `POST /auth/password/forgot/verify-otp` — Step 2: verify OTP
**Auth:** None

**Request body:**
```json
{ "reset_token": "eyJ...", "otp_code": "123456" }
```

**Response 200:**
```json
{ "reset_token": "eyJ...", "message": "OTP verified. Proceed to reset." }
```

**Errors:** `400` wrong OTP · `410` session expired · `429` max attempts

---

#### `POST /auth/password/forgot/reset` — Step 3: set new password
**Auth:** None

**Request body:**
```json
{ "reset_token": "eyJ...", "new_password": "NewStr0ng@Pass!" }
```

**Response 200:** `{ "message": "Password reset. Please log in." }`

**Data flow:** Redis session deleted → Password Argon2id-hashed → All existing DB reset tokens invalidated

---

#### `POST /auth/password/change` — Change password (authenticated)
**Auth:** Bearer JWT

**Request body:**
```json
{ "current_password": "OldPass!", "new_password": "NewStr0ng@Pass!" }
```

**Response 200:** `{ "message": "Password changed. All other sessions terminated." }`

**Data flow:** Old password verified → New password hashed → All other active sessions terminated (Redis purge)

---

#### `POST /auth/password/channel/set-password` — Set first password (channel accounts)
**Auth:** Bearer JWT (channel-registered account)

**Request body:**
```json
{ "new_password": "NewStr0ng@Pass!" }
```

**Response 200:**
```json
{ "message": "Password set. Your account is now fully active.", "user_id": "uuid", "status": "active" }
```

---

### 1.4 Channel Auth (SMS/WhatsApp/Call)

#### `POST /auth/channel-register` — Auto-register Consumer from inbound channel message
**Auth:** `X-Service-Key: <INTERNAL_SERVICE_KEY>` (internal only — called by feedback_service)

**Request body:**
```json
{
  "phone_number": "+255712345678",
  "channel": "sms",
  "display_name": "Fatuma",
  "language": "sw"
}
```

**Response 200:**
```json
{
  "user_id": "uuid",
  "is_new_user": true,
  "must_set_password": true,
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Data flow:** Idempotent — returns existing user if phone already registered. New users get `status=CHANNEL_REGISTERED`, `hashed_password=null`. Kafka `user.registered` published.

---

#### `POST /auth/channel-login/request-otp` — Channel login Step 1
**Auth:** None

**Request body:**
```json
{ "phone_number": "+255712345678" }
```

**Response 200:**
```json
{ "session_token": "...", "message": "OTP sent to registered phone.", "expires_in": 300 }
```

---

#### `POST /auth/channel-login/verify-otp` — Channel login Step 2
**Auth:** None

**Request body:**
```json
{ "session_token": "...", "otp_code": "123456" }
```

**Response 200:**
```json
{
  "user_id": "uuid",
  "must_set_password": true,
  "next_step": "set_password",
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### 1.5 Users

#### `GET /users/me` — Get my profile
**Auth:** Bearer JWT

**Response 200:**
```json
{
  "id": "uuid",
  "username": "john_doe",
  "email": "user@example.com",
  "phone_number": "+255712345678",
  "display_name": "John",
  "full_name": "John Doe",
  "avatar_url": null,
  "is_email_verified": true,
  "is_phone_verified": false,
  "has_password": true,
  "status": "ACTIVE",
  "platform_role": null,
  "language": "en",
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

#### `PATCH /users/me` — Update profile (PATCH semantics)
**Auth:** Bearer JWT

**Request body (all fields optional):**
```json
{
  "display_name": "Johnny",
  "full_name": "John Doe",
  "username": "johnny_d",
  "language": "sw",
  "bio": "GRM Officer"
}
```

**Errors:** `409` username already taken

---

#### `DELETE /users/me` — Deactivate account (soft-delete)
**Auth:** Bearer JWT

**Response 200:** `{ "message": "Account deactivated." }`

---

#### `POST /users/me/avatar` — Update avatar URL
**Auth:** Bearer JWT

**Request body:**
```json
{ "avatar_url": "https://cdn.riviwa.com/avatars/user.jpg" }
```
> Pass `avatar_url: null` to clear avatar. URL must be HTTPS.

---

#### `POST /users/me/verify-email` · `POST /users/me/verify-phone`
**Auth:** Bearer JWT · No body · Marks the field as verified

---

#### `POST /users/{user_id}/suspend` — Suspend user [Admin]
**Auth:** Bearer JWT + `platform_role = admin`

**Query param:** `reason=string` (optional)

**Response 200:** `{ "message": "User {id} suspended." }`

---

#### `POST /users/{user_id}/ban` · `POST /users/{user_id}/reactivate`
**Auth:** Bearer JWT + `platform_role = admin` · No body

---

### 1.6 Organisations

#### `POST /orgs` — Create organisation
**Auth:** Bearer JWT (verified email required)

**Request body:**
```json
{
  "legal_name": "Acme Ltd",
  "display_name": "Acme",
  "slug": "acme",
  "org_type": "government",
  "description": "Infrastructure agency",
  "website_url": "https://acme.go.tz",
  "support_email": "info@acme.go.tz",
  "support_phone": "+255700000000",
  "country_code": "TZ",
  "timezone": "Africa/Dar_es_Salaam",
  "registration_number": "TZ-12345",
  "tax_id": "TAX-001"
}
```

**Response 201:** Full `OrgResponse` object. Status starts as `PENDING_VERIFICATION`.

**Data flow:** Creator → `OWNER` member. Kafka `org.created` published.

---

#### `GET /orgs` — List my organisations
**Auth:** Bearer JWT

**Query params:** `search` · `org_type` · `is_verified` · `sort=name|created` · `page` · `limit`

**Response 200:**
```json
{
  "items": [...],
  "total": 5,
  "page": 1,
  "limit": 20,
  "pages": 1
}
```

---

#### `GET /orgs/invites` — List pending invites for me
**Auth:** Bearer JWT · Response: array of `InviteResponse`

---

#### `GET /orgs/{org_id}` — Get organisation
**Auth:** Bearer JWT

---

#### `PATCH /orgs/{org_id}` — Update organisation [ADMIN+]
**Auth:** Bearer JWT on org dashboard

**Request body (PATCH — all optional):**
```json
{
  "display_name": "Updated Name",
  "description": "New desc",
  "slug": "new-slug",
  "website_url": "https://new.go.tz",
  "support_email": "new@go.tz"
}
```

---

#### `DELETE /orgs/{org_id}` — Deactivate organisation [OWNER]
**Auth:** Bearer JWT + OWNER role

**Query param:** `reason=string` (optional)

---

#### `POST /orgs/{org_id}/verify` — Verify organisation [Platform Admin]
#### `POST /orgs/{org_id}/suspend` — Suspend [Platform Admin]
#### `POST /orgs/{org_id}/ban` — Ban [Platform Admin]
**Auth:** Bearer JWT + `platform_role = admin`

**Request body for suspend/ban:**
```json
{ "reason": "Violated terms of service" }
```

---

#### `POST /orgs/{org_id}/members` — Add member directly [ADMIN+]
**Auth:** Bearer JWT on org dashboard (ADMIN role)

**Request body:**
```json
{ "user_id": "uuid", "org_role": "MANAGER" }
```

**Response 201:** `MemberResponse`

---

#### `DELETE /orgs/{org_id}/members/{user_id}` — Remove member [ADMIN+]
**Query param:** `reason=string`

---

#### `PATCH /orgs/{org_id}/members/{user_id}/role` — Change role [ADMIN+]
**Request body:** `{ "org_role": "MANAGER" }`

---

#### `POST /orgs/{org_id}/transfer-ownership` — Transfer ownership [OWNER]
**Request body:** `{ "new_owner_id": "uuid" }`

**Data flow:** Current OWNER → demoted to ADMIN. New owner → OWNER. Kafka `org.ownership_transferred`.

---

#### `POST /orgs/{org_id}/invites` — Send invite [MANAGER+]
**Request body:**
```json
{
  "invited_role": "MEMBER",
  "invited_email": "new@example.com",
  "invited_user_id": null,
  "message": "Please join our organisation"
}
```

---

#### `POST /orgs/invites/{invite_id}/accept` — Accept invite
#### `POST /orgs/invites/{invite_id}/decline` — Decline invite
#### `DELETE /orgs/{org_id}/invites/{invite_id}` — Cancel invite [MANAGER+]
**Auth:** Bearer JWT · No body

---

#### `GET /orgs/{org_id}/logo` — Get logo URL
#### `POST /orgs/{org_id}/logo` — Upload logo [MANAGER+]
**Content-Type:** `multipart/form-data`  
**Body:** `file` (JPEG/PNG/WebP/SVG/GIF, max 5 MB)  
**Response:** `{ "org_id": "uuid", "logo_url": "https://..." }`  
**Data flow:** MinIO `organisations/{org_id}/logo.{ext}` → DB updated → Kafka `org.updated`

#### `DELETE /orgs/{org_id}/logo` — Remove logo [MANAGER+]
**Data flow:** MinIO object deleted → DB `logo_url` = null → Kafka `org.updated`

---

### 1.7 Departments

All under `/orgs/{org_id}/departments`. Caller must be an active member (any role to read; ADMIN+ to mutate).

#### `POST /orgs/{org_id}/departments` — Create [ADMIN+]
**Request body:**
```json
{
  "name": "Human Resources",
  "code": "HR",
  "description": "HR department",
  "branch_id": null,
  "sort_order": 0
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "org_id": "uuid",
  "branch_id": null,
  "name": "Human Resources",
  "code": "HR",
  "description": "HR department",
  "sort_order": 0,
  "is_active": true,
  "created_at": "...",
  "updated_at": "..."
}
```

**Data flow:** Kafka `org_department.created` published. `code` must be unique per org.

**Errors:** `409 DEPARTMENT_NAME_CONFLICT` or `409 DEPARTMENT_CODE_CONFLICT`

---

#### `GET /orgs/{org_id}/departments` — List departments
**Query params:** `branch_id` (filter to branch) · `active_only=true` (default)

**Response 200:** `{ "items": [...], "count": 3 }`

---

#### `GET /orgs/{org_id}/departments/{dept_id}` — Get department
#### `PATCH /orgs/{org_id}/departments/{dept_id}` — Update [ADMIN+]
**Request body (all optional):**
```json
{
  "name": "Updated Name",
  "description": "New description",
  "sort_order": 1,
  "is_active": true
}
```

#### `DELETE /orgs/{org_id}/departments/{dept_id}` — Deactivate [ADMIN+]
> Soft-delete: sets `is_active = false`. Department still accessible via GET.  
> Kafka `org_department.deactivated` published.

---

### 1.8 Extended Org (Locations, Content, FAQs, Branches, Services)

All under `/orgs/{org_id}/...`

#### Locations
| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/orgs/{org_id}/locations` | ADMIN | Add a physical address |
| `GET` | `/orgs/{org_id}/locations` | Any auth | List all locations |
| `PATCH` | `/orgs/{org_id}/locations/{location_id}` | ADMIN | Update location |
| `DELETE` | `/orgs/{org_id}/locations/{location_id}` | ADMIN | Delete location |
| `GET` | `/orgs/{org_id}/branches/{branch_id}/locations` | Any auth | Branch locations |

**Create location body:**
```json
{
  "location_type": "HEADQUARTERS",
  "line1": "123 Main St",
  "city": "Dar es Salaam",
  "country_code": "TZ",
  "region": "Dar es Salaam",
  "latitude": -6.8235,
  "longitude": 39.2695,
  "is_primary": true
}
```

#### Content (1-to-1 upsert)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| `GET` | `/orgs/{org_id}/content` | Any auth | Get vision/mission/policies |
| `PUT` | `/orgs/{org_id}/content` | ADMIN | Upsert content profile |

**Content body:**
```json
{
  "vision": "A better Tanzania",
  "mission": "Build quality infrastructure",
  "objectives": "Complete 50 road projects",
  "global_policy": "Zero tolerance for corruption",
  "terms_of_use": "...",
  "privacy_policy": "..."
}
```

#### Org FAQs
| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/orgs/{org_id}/faqs` | MANAGER | Add FAQ |
| `GET` | `/orgs/{org_id}/faqs` | Any auth | List FAQs (`?published_only=true`) |
| `PATCH` | `/orgs/{org_id}/faqs/{faq_id}` | MANAGER | Update FAQ |
| `DELETE` | `/orgs/{org_id}/faqs/{faq_id}` | MANAGER | Delete FAQ |

**FAQ body:** `{ "question": "...", "answer": "...", "display_order": 0, "is_published": true }`

#### Branches
| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/orgs/{org_id}/branches` | ADMIN | Create branch / sub-branch |
| `GET` | `/orgs/{org_id}/branches` | Any auth | Top-level branches |
| `GET` | `/orgs/{org_id}/branches/{branch_id}/children` | Any auth | Child branches |
| `GET` | `/orgs/{org_id}/branches/{branch_id}/tree` | Any auth | All IDs in subtree (CTE) |
| `PATCH` | `/orgs/{org_id}/branches/{branch_id}` | ADMIN | Update branch |
| `POST` | `/orgs/{org_id}/branches/{branch_id}/close` | ADMIN | Close branch |
| `DELETE` | `/orgs/{org_id}/branches/{branch_id}` | OWNER | Delete branch |

**Create branch body:**
```json
{
  "name": "Dar es Salaam Region Office",
  "code": "DSM",
  "branch_type": "Regional Office",
  "parent_branch_id": null,
  "status": "ACTIVE",
  "phone": "+255222000000",
  "email": "dsm@acme.go.tz"
}
```

#### Branch Managers
| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/orgs/{org_id}/branches/{branch_id}/managers` | ADMIN | Assign manager |
| `GET` | `/orgs/{org_id}/branches/{branch_id}/managers` | Any auth | List managers |
| `DELETE` | `/orgs/{org_id}/branches/{branch_id}/managers/{user_id}` | ADMIN | Remove manager |

**Assign body:** `{ "user_id": "uuid", "manager_title": "Branch Manager", "is_primary": true }`

#### Services
| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/orgs/{org_id}/services` | MANAGER | Create service/product/program |
| `GET` | `/orgs/{org_id}/services` | Any auth | List (`?status=` `?active_only=`) |
| `GET` | `/orgs/{org_id}/services/{service_id}` | Any auth | Get service |
| `PATCH` | `/orgs/{org_id}/services/{service_id}` | MANAGER | Update service |
| `POST` | `/orgs/{org_id}/services/{service_id}/publish` | MANAGER | DRAFT → ACTIVE |
| `POST` | `/orgs/{org_id}/services/{service_id}/archive` | ADMIN | Soft-delete |
| `POST` | `/orgs/{org_id}/branches/{branch_id}/services/{service_id}/link` | MANAGER | Link to branch |
| `DELETE` | `/orgs/{org_id}/branches/{branch_id}/services/{service_id}/link` | MANAGER | Unlink from branch |

**Service body:**
```json
{
  "title": "Road Permit Processing",
  "slug": "road-permit",
  "service_type": "SERVICE",
  "delivery_mode": "PHYSICAL",
  "summary": "Process road construction permits",
  "base_price": 0.0,
  "currency_code": "TZS"
}
```
> `service_type`: `SERVICE` | `PRODUCT` | `PROGRAM`

#### Service Personnel, Media, FAQs, Policies
| Method | Path | Role | Notes |
|--------|------|------|-------|
| `POST/GET/DELETE` | `/orgs/{org_id}/services/{service_id}/personnel[/{user_id}/{role}]` | ADMIN/Any | Assign/list/remove |
| `POST/GET` | `/orgs/{org_id}/services/{service_id}/locations[/{sl_id}]` | MANAGER/Any | Service deployment |
| `PATCH/DELETE` | `/orgs/{org_id}/services/{service_id}/locations/{sl_id}` | MANAGER/ADMIN | Update/remove |
| `POST/GET` | `/orgs/{org_id}/services/{service_id}/media[/{media_id}]` | MANAGER/Any | Media gallery |
| `POST/GET/PATCH/DELETE` | `/orgs/{org_id}/services/{service_id}/faqs[/{faq_id}]` | MANAGER/Any | FAQs |
| `POST/GET/PATCH/DELETE` | `/orgs/{org_id}/services/{service_id}/policies[/{policy_id}]` | ADMIN/Any | Policy versions |

---

### 1.9 Projects

All under `/orgs/{org_id}/projects/...`

#### Projects
| Method | Path | Role | Status Transition |
|--------|------|------|------------------|
| `POST` | `/orgs/{org_id}/projects` | ADMIN | Creates in `PLANNING` |
| `GET` | `/orgs/{org_id}/projects` | MANAGER | List (`?status=` `?branch_id=`) |
| `GET` | `/orgs/{org_id}/projects/{project_id}` | MANAGER | Detail with stages |
| `PATCH` | `/orgs/{org_id}/projects/{project_id}` | ADMIN | Update fields |
| `POST` | `/orgs/{org_id}/projects/{project_id}/activate` | OWNER | `PLANNING → ACTIVE` |
| `POST` | `/orgs/{org_id}/projects/{project_id}/pause` | OWNER | `ACTIVE → PAUSED` |
| `POST` | `/orgs/{org_id}/projects/{project_id}/resume` | OWNER | `PAUSED → ACTIVE` |
| `POST` | `/orgs/{org_id}/projects/{project_id}/complete` | OWNER | `→ COMPLETED` |
| `DELETE` | `/orgs/{org_id}/projects/{project_id}` | OWNER | `→ CANCELLED` |

**Create project body:**
```json
{
  "name": "Dar-Morogoro Highway Upgrade",
  "description": "Phase 2 rehabilitation",
  "project_code": "TARURA-2026-001",
  "start_date": "2026-01-01",
  "end_date": "2028-12-31",
  "budget": 50000000.00,
  "currency_code": "USD",
  "branch_id": null,
  "accepts_grievances": true,
  "accepts_suggestions": true,
  "accepts_applause": true
}
```

**Data flow on activate:** Kafka `org_project.published` → stakeholder_service and feedback_service create `ProjectCache` records

#### Project In-charges
`POST/GET /orgs/{org_id}/projects/{project_id}/in-charges` (ADMIN)  
`DELETE /orgs/{org_id}/projects/{project_id}/in-charges/{user_id}?role_title=...` (ADMIN)

#### Project Cover Image
`POST /orgs/{org_id}/projects/{project_id}/cover-image` (MANAGER, `multipart/form-data`)  
**Data flow:** MinIO → DB updated → Kafka `org_project.updated`

#### Progress Image Gallery
| Method | Path | Role |
|--------|------|------|
| `POST` | `/orgs/{org_id}/projects/{project_id}/images` | MANAGER |
| `GET` | `/orgs/{org_id}/projects/{project_id}/images` | MEMBER |
| `PATCH/DELETE` | `/orgs/{org_id}/projects/{project_id}/images/{image_id}` | MANAGER |
| `POST/GET/PATCH/DELETE` | `/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/images[/{image_id}]` | MANAGER/MEMBER |

**Image upload:** `multipart/form-data` with `file`, `title`, `phase` (before/during/after/other), `description`, `location_description`, `gps_lat`, `gps_lng`, `captured_at`

#### Stages
| Method | Path | Role | Transition |
|--------|------|------|-----------|
| `POST` | `.../stages` | ADMIN | Create in `PENDING` |
| `GET` | `.../stages` | MANAGER | List |
| `GET` | `.../stages/{stage_id}` | MANAGER | Detail |
| `PATCH` | `.../stages/{stage_id}` | ADMIN | Update |
| `POST` | `.../stages/{stage_id}/activate` | ADMIN | `PENDING → ACTIVE` |
| `POST` | `.../stages/{stage_id}/complete` | ADMIN | `ACTIVE → COMPLETED` |
| `POST` | `.../stages/{stage_id}/skip` | ADMIN | `PENDING → SKIPPED` |

**Data flow on activate:** Kafka `org_project_stage.activated` → downstream services update `ProjectStageCache`

#### Sub-projects & Sub-project In-charges
`POST/GET /stages/{stage_id}/subprojects` (ADMIN/MANAGER)  
`GET/.../subprojects/{subproject_id}` · `GET/.../tree` · `PATCH` · `DELETE` (ADMIN)  
`POST/GET/DELETE .../subprojects/{subproject_id}/in-charges[/{user_id}]` (ADMIN/MANAGER)

---

### 1.10 System Settings & Admin Dashboard

#### `GET/PATCH /system-settings` — Platform-wide settings [Platform Admin]
#### `GET /system-settings/logo` · `POST /system-settings/logo` · `DELETE /system-settings/logo`
Platform-level logo (shown when no org logo set). `multipart/form-data`.

#### Admin Dashboard
`GET /admin/dashboard` — Platform metrics summary [Platform Admin]  
`GET /admin/users` — All users with filters [Platform Admin]  
`GET /admin/orgs` — All organisations [Platform Admin]

---

## 2. Feedback Service (Port 8090)

**DB:** `feedback_db` (port 5434) · **Kafka consumer + producer** · **Nginx:** `/api/v1/feedback`, `/api/v1/categories`, `/api/v1/committees`, `/api/v1/my`, `/api/v1/escalation-requests`, `/api/v1/voice`, `/api/v1/reports`, `/api/v1/channels`

---

### 2.1 Staff Feedback CRUD

#### `POST /feedback` — Submit feedback [GRM Officer: manager/admin/owner]
**Auth:** Bearer JWT (org staff)

**Request body:**
```json
{
  "project_id": "uuid",
  "feedback_type": "grievance",
  "category": "compensation",
  "channel": "in_person",
  "subject": "Unpaid compensation for land acquisition",
  "description": "My plot was taken 3 months ago and I have not received compensation.",
  "priority": "high",
  "is_anonymous": false,
  "submitter_name": "Amina Hassan",
  "submitter_phone": "+255712345678",
  "submission_method": "officer_recorded",
  "issue_lga": "Ilala",
  "issue_ward": "Mchikichini",
  "issue_gps_lat": -6.8235,
  "issue_gps_lng": 39.2695,
  "date_of_incident": "2026-01-15",
  "submitted_at": "2026-01-20T09:00:00Z",
  "department_id": "uuid",
  "service_id": "uuid",
  "product_id": "uuid",
  "category_def_id": "uuid",
  "stage_id": "uuid",
  "subproject_id": "uuid",
  "media_urls": ["https://..."]
}
```
> `feedback_type`: `grievance` | `suggestion` | `applause` | `inquiry`  
> `department_id` — soft FK to `auth_db.org_departments` (UUID, no DB-level FK constraint)  
> `service_id` — soft FK to `auth_db.org_services` (service_type = SERVICE or PROGRAM)  
> `product_id` — soft FK to `auth_db.org_services` (service_type = PRODUCT)  
> `category_def_id` — optional FK to `feedback_category_defs` (dynamic categories)  
> `submitted_at` can be backdated for paper form entries  
> `category` (static enum): compensation, resettlement, land-acquisition, construction-impact, traffic, worker-rights, project-delay, corruption, safety-hazard, environmental, engagement, design-issue, accessibility, design, process, community-benefit, employment, quality, timeliness, staff-conduct, community-impact, responsiveness, communication, safety, information_request, procedure_inquiry, status_update, document_request, general_inquiry, other

**Response 201:**
```json
{
  "id": "uuid",
  "unique_ref": "GRV-2026-0042",
  "feedback_type": "grievance",
  "category": "compensation",
  "status": "SUBMITTED",
  "priority": "HIGH",
  "current_level": "WARD",
  "project_id": "uuid",
  "department_id": "uuid",
  "service_id": "uuid",
  "product_id": "uuid",
  "category_def_id": "uuid",
  "subject": "...",
  "submitted_at": "...",
  "target_resolution_date": "..."
}
```

**`unique_ref` prefix by type:** `GRV-` grievance · `SGG-` suggestion · `APP-` applause · `INQ-` inquiry

**Data flow:** `unique_ref` auto-generated (per-project sequence) → `category_def_id` auto-linked by slug → Kafka `feedback.submitted` published → PAP notified

---

#### `POST /feedback/bulk-upload` — Bulk CSV import [Any staff]
**Auth:** Bearer JWT  
**Content-Type:** `multipart/form-data`  
**Body:** `file` (CSV, UTF-8, max 1000 rows)

**CSV columns:** `project_id`, `feedback_type`, `category`, `subject`, `description`, `channel`, `priority`, `submitter_name`, `submitter_phone`, `is_anonymous`, `issue_lga`, `issue_ward`, `issue_gps_lat`, `issue_gps_lng`, `date_of_incident`, `submitted_at`

**Response 200:**
```json
{
  "total_rows": 50,
  "created": 48,
  "skipped": 2,
  "errors": [{ "row": 12, "error": "Invalid project_id" }]
}
```

---

#### `GET /feedback` — List feedback [Staff]
**Auth:** Bearer JWT (org staff — scoped to org; platform admin sees all)

**Query params:** `project_id` · `feedback_type` (grievance|suggestion|applause|inquiry) · `status` · `priority` · `current_level` · `category` · `lga` · `is_anonymous` · `channel` · `submission_method` · `department_id` · `service_id` · `product_id` · `category_def_id` · `submitted_by_stakeholder_id` · `assigned_committee_id` · `skip` · `limit`

**Response 200:** `{ "items": [...], "count": 50 }`

---

#### `GET /feedback/{feedback_id}` — Feedback detail with full history
**Auth:** Bearer JWT (staff)

**Response 200:**
```json
{
  "id": "uuid",
  "unique_ref": "GRV-2026-0042",
  "status": "IN_REVIEW",
  "actions": [...],
  "escalations": [...],
  "resolution": null,
  "appeal": null
}
```

---

### 2.2 Feedback Lifecycle

All require `Bearer JWT` with GRM Officer role (manager/admin/owner) or platform admin.

#### `PATCH /feedback/{feedback_id}/acknowledge` — Acknowledge receipt
**Request body:**
```json
{
  "response_method": "phone_call",
  "response_summary": "Called submitter, acknowledged receipt.",
  "target_resolution_date": "2026-02-15",
  "notes": "Internal note"
}
```

#### `PATCH /feedback/{feedback_id}/assign` — Assign
**Request body:**
```json
{
  "assigned_committee_id": "uuid",
  "assigned_to_user_id": "uuid",
  "notes": "Assigned to Ward GRM Committee"
}
```

#### `POST /feedback/{feedback_id}/escalate` — Escalate to next GRM level
**Request body:**
```json
{
  "reason": "Ward committee unable to resolve within SLA",
  "escalated_to_committee_id": "uuid",
  "notes": "Escalating to LGA GRM Unit"
}
```
> GRM level order: `WARD → LGA_PIU → PCU → TARURA_WBCU → TANROADS → WORLD_BANK`

#### `POST /feedback/{feedback_id}/resolve` — Record resolution
**Request body:**
```json
{
  "resolution_summary": "Compensation of TZS 5,000,000 paid on 2026-02-10.",
  "response_method": "in_person_meeting",
  "grievant_satisfied": true,
  "grievant_response": "Satisfied with the resolution.",
  "witness_name": "Ward Executive Officer"
}
```

#### `POST /feedback/{feedback_id}/appeal` — File appeal
**Request body:**
```json
{
  "appeal_grounds": "Resolution amount insufficient — valuation was incorrect.",
  "appeal_status": "pending"
}
```

#### `PATCH /feedback/{feedback_id}/close` — Close feedback
**Request body:** `{ "notes": "Case closed after resolution." }`

#### `PATCH /feedback/{feedback_id}/dismiss` — Dismiss [Admin/Owner only]
**Request body:**
```json
{ "reason": "Assessed as outside project scope — refer to district office." }
```

---

### 2.3 Categories

#### `POST /categories` — Create category [Staff]
**Request body:**
```json
{
  "name": "Dust Pollution",
  "slug": "dust-pollution",
  "description": "Air quality issues from construction",
  "project_id": "uuid",
  "applicable_types": ["grievance", "suggestion"],
  "color_hex": "#FF5733",
  "icon": "🌫️",
  "display_order": 10
}
```

#### `GET /categories` — List
**Query:** `project_id` · `feedback_type` · `source` · `status` · `include_global=true`

#### `GET /categories/summary` — Dashboard category counts
**Query:** `project_id` (required) · `feedback_type` · `from_date` · `to_date`

#### `GET/PATCH /categories/{category_id}`
#### `GET /categories/{category_id}/rate` — Feedback rate for a category
**Query:** `project_id` · `stage_id` · `period=week|month|year` · `from_date` · `to_date`

#### `POST /feedback/{feedback_id}/classify` — ML auto-classify
**Auth:** Staff · No body · Triggers Claude AI classification

#### `PATCH /feedback/{feedback_id}/recategorise` — Manual reassign
**Request body:** `{ "category_def_id": "uuid", "reason": "Reclassified after review" }`

#### `POST /categories/{category_id}/approve|reject|deactivate|merge`
**Approve/Reject body:** `{ "notes": "..." }`  
**Merge body:** `{ "merge_into_id": "uuid" }`

---

### 2.4 Committees

#### `POST /committees` — Create GRM committee
**Request body:**
```json
{
  "level": "WARD",
  "project_id": "uuid",
  "lga": "Ilala",
  "name": "Ilala Ward GRM Committee",
  "stakeholder_ids": ["uuid1", "uuid2"]
}
```

#### `GET /committees` — List (`?project_id=` `?level=` `?lga=`)
#### `GET /committees/{committee_id}`
#### `PATCH /committees/{committee_id}`
#### `POST /committees/{committee_id}/members` — Add member
**Body:** `{ "stakeholder_id": "uuid", "role": "chairperson" }`

---

### 2.5 Consumer (PAP) Portal

#### `POST /my/feedback` — PAP submit feedback
**Auth:** Bearer JWT (any authenticated user)

**Request body:**
```json
{
  "project_id": "uuid",
  "feedback_type": "grievance",
  "category": "compensation",
  "subject": "Unpaid compensation",
  "description": "...",
  "issue_lga": "Ilala",
  "department_id": "uuid"
}
```
> Channel auto-set to `WEB_PORTAL`. `submission_method` = `SELF_SERVICE`.

**Response 201:** Tracking view with `unique_ref`, `status_label`, `can_request_escalation`, `can_appeal`

---

#### `GET /my/feedback` — List my submissions
**Auth:** Bearer JWT · **Query:** `status` · `feedback_type` · `skip` · `limit`

#### `GET /my/feedback/{feedback_id}` — Tracking detail
#### `GET /my/feedback/summary` — My feedback summary counts

#### `POST /my/feedback/{feedback_id}/appeal` — File appeal (PAP)
**Request body:** `{ "appeal_grounds": "Resolution amount insufficient" }`

#### `POST /my/feedback/{feedback_id}/escalation-request` — Request escalation (PAP)
**Request body:**
```json
{ "reason": "No response in 30 days", "requested_level": "LGA_PIU" }
```

#### `POST /my/feedback/{feedback_id}/add-comment` — Add comment (PAP)
**Request body:** `{ "comment": "I provided additional documents." }`

---

### 2.6 Escalation Requests (Staff Review)

#### `GET /escalation-requests` — List PAP escalation requests [Staff]
**Query:** `project_id` · `status=pending|approved|rejected`

#### `POST /escalation-requests/{id}/approve` — Approve escalation [GRM Officer]
**Request body:** `{ "notes": "Approved — escalating to LGA PIU" }`

#### `POST /escalation-requests/{id}/reject` — Reject escalation [GRM Officer]
**Request body:** `{ "notes": "Insufficient grounds for escalation" }`

---

### 2.7 Voice Notes

#### `POST /voice/upload` — Upload voice note
**Content-Type:** `multipart/form-data`  
**Body:** `file` (audio), `feedback_id` (optional), `language=sw|en`

**Response:**
```json
{
  "voice_note_url": "https://minio.../voice/...",
  "transcription": "Nchi yangu ilichukuliwa...",
  "duration_seconds": 45,
  "language": "sw",
  "confidence": 0.92
}
```

**Data flow:** Audio → MinIO `riviwa-voice` bucket → STT (Whisper/Google/Azure) → transcription stored

#### `POST /voice/transcribe` — Transcribe existing audio URL
**Body:** `{ "audio_url": "https://...", "language": "sw" }`

#### `GET /voice/{voice_id}` — Get voice note metadata

---

### 2.8 Channel Sessions (SMS/WhatsApp/Call)

#### `POST /channel-sessions` — Create session
**Body:** `{ "channel": "whatsapp", "project_id": "uuid", "phone_number": "+255..." }`

#### `GET /channel-sessions` — List (`?channel=` `?status=`)
#### `GET /channel-sessions/{session_id}`
#### `POST /channel-sessions/{session_id}/abandon` — Abandon session

---

### 2.9 Reports

All require Bearer JWT (staff). Query param `project_id` required for most.

#### `GET /reports/performance` — GRM performance overview
#### `GET /reports/grievances` — Grievance breakdown
#### `GET /reports/suggestions` — Suggestion breakdown
#### `GET /reports/applause` — Applause breakdown
#### `GET /reports/escalations` — Escalation patterns
#### `GET /reports/resolution-time` — Time-to-resolution analysis
#### `GET /reports/channel-breakdown` — Feedback by submission channel
#### `GET /reports/geographic` — Feedback by location (region/LGA/ward)
#### `GET /reports/committee-performance` — Per-committee GRM stats

**Common query params:** `project_id` · `stage_id` · `from_date` · `to_date` · `feedback_type`

---

## 3. Stakeholder Service (Port 8070)

**DB:** `stakeholder_db` (port 5436) · **Nginx:** `/api/v1/stakeholders`, `/api/v1/activities`, `/api/v1/communications`, `/api/v1/focal-persons`, `/api/v1/projects`

---

### 3.1 Stakeholders

#### `POST /stakeholders` — Register stakeholder [Staff]
**Auth:** Bearer JWT

**Request body:**
```json
{
  "stakeholder_type": "consumer",
  "entity_type": "individual",
  "category": "affected_community",
  "affectedness": "directly_affected",
  "display_name": "Hassan Mohamed",
  "first_name": "Hassan",
  "last_name": "Mohamed",
  "org_name": null,
  "lga": "Ilala",
  "ward": "Mchikichini",
  "language_preference": "sw",
  "preferred_channel": "sms",
  "is_vulnerable": true,
  "vulnerable_group_types": ["elderly"],
  "participation_barriers": ["transport"],
  "notes": "Lives near chainage 5+000"
}
```
> `stakeholder_type`: consumer, interested_party, implementing_agency, local_authority, civil_society, media, private_sector, government, international_org

**Response 201:** Full stakeholder object

---

#### `GET /stakeholders` — List with filters
**Query:** `stakeholder_type` · `category` · `lga` · `affectedness` · `is_vulnerable` · `importance` · `project_id` · `stage_id` · `skip` · `limit`

#### `GET /stakeholders/analysis` — Annex 3 / SEP analysis matrix
**Query:** `project_id` (required) · `stage_id` · `importance` · `category` · `affectedness` · `is_vulnerable`

**Response:** Matrix rows with `why_important`, `interests`, `potential_risks`, `how_to_engage`, `importance`

#### `GET /stakeholders/{stakeholder_id}` — Detail with contacts
#### `PATCH /stakeholders/{stakeholder_id}` — Update
#### `DELETE /stakeholders/{stakeholder_id}` — Soft-delete [Platform Admin]

#### `POST /stakeholders/{stakeholder_id}/projects` — Register for project
**Body:**
```json
{
  "project_id": "uuid",
  "is_consumer": true,
  "affectedness": "directly_affected",
  "impact_description": "House within 50m of construction"
}
```

#### `GET /stakeholders/{stakeholder_id}/projects` — List project registrations
#### `GET /stakeholders/{stakeholder_id}/engagements` — Engagement history

---

### 3.2 Contacts

#### `POST /stakeholders/{stakeholder_id}/contacts` — Add contact
**Body:**
```json
{
  "full_name": "Amina Hassan",
  "title": "Mrs",
  "role_in_org": "Community Representative",
  "email": "amina@example.com",
  "phone": "+255712345678",
  "preferred_channel": "whatsapp",
  "is_primary": true,
  "can_submit_feedback": true,
  "can_receive_communications": true,
  "can_distribute_communications": false
}
```

#### `GET /stakeholders/{stakeholder_id}/contacts` — List
#### `PATCH /contacts/{contact_id}` — Update
#### `DELETE /contacts/{contact_id}` — Remove

---

### 3.3 Engagement Activities

#### `POST /activities` — Create activity [Staff]
**Body:**
```json
{
  "project_id": "uuid",
  "stage_id": "uuid",
  "activity_type": "public_consultation",
  "title": "Community Consultation — Ilala Ward",
  "description": "Quarterly SEP consultation",
  "venue": "Ilala Ward Office",
  "lga": "Ilala",
  "ward": "Mchikichini",
  "scheduled_at": "2026-03-15T09:00:00Z",
  "expected_count": 50,
  "agenda": "Road project update + grievance collection",
  "languages_used": ["sw", "en"]
}
```

**Response 201:** Full activity object

---

#### `GET /activities` — List (`?project_id=` `?stage=` `?status=` `?lga=`)
#### `GET /activities/{activity_id}` — Detail with attendance list
#### `PATCH /activities/{activity_id}` — Update / mark as conducted

**Conduct body:**
```json
{
  "status": "conducted",
  "conducted_at": "2026-03-15T11:30:00Z",
  "actual_count": 43,
  "female_count": 18,
  "vulnerable_count": 5,
  "summary_of_issues": "Community raised compensation and dust concerns.",
  "summary_of_responses": "PIU committed to respond within 30 days.",
  "action_items": ["Send written response by 2026-04-15"]
}
```

#### `POST /activities/{activity_id}/attendances` — Log attendance
**Body:**
```json
{
  "contact_id": "uuid",
  "attendance_status": "present",
  "concerns_raised": "Compensation not received",
  "response_given": "Referred to GRM Unit",
  "feedback_submitted": true,
  "feedback_ref_id": "GRV-2026-0042"
}
```

#### `PATCH /activities/{activity_id}/attendances/{engagement_id}` — Update attendance
#### `POST /activities/{activity_id}/attendances/bulk` — Bulk attendance upload (CSV)
#### `POST/GET/DELETE /activities/{activity_id}/media` — Activity photo/document management

---

### 3.4 Communications

#### `POST /communications` — Create communication record
**Body:**
```json
{
  "project_id": "uuid",
  "stage_id": "uuid",
  "communication_type": "newsletter",
  "title": "Project Update — March 2026",
  "content": "Road works progress at 65%...",
  "language": "sw",
  "distribution_method": "whatsapp",
  "scheduled_at": "2026-03-20T08:00:00Z"
}
```

#### `GET /communications` — List (`?project_id=` `?type=` `?status=`)
#### `GET /communications/{comm_id}` — Detail
#### `PATCH /communications/{comm_id}` — Update
#### `POST /communications/{comm_id}/distribute` — Trigger distribution
#### `GET/POST /communications/{comm_id}/distributions` — Distribution list management

---

### 3.5 Focal Persons

#### `POST /focal-persons` — Register focal person
**Body:**
```json
{
  "user_id": "uuid",
  "project_id": "uuid",
  "role": "GRM Officer",
  "lga": "Ilala",
  "phone": "+255700000000",
  "is_primary": true
}
```

#### `GET /focal-persons` — List (`?project_id=` `?lga=`)
#### `GET/PATCH/DELETE /focal-persons/{fp_id}`

---

### 3.6 Projects (Stakeholder Read-Only Cache)

#### `GET /projects` — List projects (`?org_id=` `?status=`)
**Auth:** Bearer JWT · Read-only mirror of auth_service ProjectCache

#### `GET /projects/{project_id}` — Project detail

---

## 4. Notification Service (Port 8060)

**DB:** `notification_db` (port 5437) · **Redis:** DB 3 · **Nginx:** proxied internally (not direct user access) and via `/api/v1/notifications`, `/api/v1/devices`, `/api/v1/preferences`

---

### 4.1 Notification Inbox

#### `GET /notifications` — Get notification inbox
**Auth:** Bearer JWT

**Query:** `unread_only=false` · `skip=0` · `limit=30`

**Response 200:**
```json
{
  "unread_count": 5,
  "returned": 10,
  "items": [
    {
      "delivery_id": "uuid",
      "notification_type": "feedback.submitted",
      "title": "New Grievance Submitted",
      "body": "GRV-2026-0042: Unpaid compensation for land acquisition",
      "icon_url": null,
      "action_url": "/feedback/uuid",
      "is_read": false,
      "created_at": "...",
      "read_at": null
    }
  ]
}
```

#### `GET /notifications/unread-count` — Badge count
**Response:** `{ "unread_count": 5 }`

#### `PATCH /notifications/deliveries/{delivery_id}/read` — Mark one as read
#### `POST /notifications/mark-all-read` — Mark all as read
**Response:** `{ "message": "5 notification(s) marked as read.", "count": 5 }`

#### `DELETE /notifications/{notification_id}` — Cancel scheduled notification
**Errors:** `404` not found · `409` already dispatched

---

### 4.2 Push Devices

#### `POST /devices` — Register device token
**Auth:** Bearer JWT

**Request body:**
```json
{
  "platform": "fcm",
  "push_token": "fcm_token_string",
  "device_name": "Samsung Galaxy S24"
}
```
> `platform`: `fcm` (Android/Web) | `apns` (iOS)

**Response 201:** Device record with `id`, `platform`, `device_name`, `registered_at`

**Data flow:** Idempotent — updates token if same device_name already registered. Handles token refresh and device transfer.

#### `GET /devices` — List my devices
#### `PATCH /devices/{device_id}` — Update token
**Body:** `{ "push_token": "new_token" }`
#### `DELETE /devices/{device_id}` — Unregister device

---

### 4.3 Notification Preferences

#### `GET /preferences` — Get my notification preferences
**Auth:** Bearer JWT

**Response 200:**
```json
{
  "user_id": "uuid",
  "channels": {
    "in_app": true,
    "push": true,
    "sms": false,
    "email": true,
    "whatsapp": false
  },
  "types": {
    "feedback_submitted": true,
    "feedback_status_changed": true,
    "escalation": true,
    "system_announcement": true
  }
}
```

#### `PATCH /preferences` — Update preferences
**Body (any field):**
```json
{
  "channels": { "sms": true, "whatsapp": true },
  "types": { "system_announcement": false }
}
```

---

### 4.4 Internal API (service-to-service)

#### `POST /internal/notify` — Dispatch notification
**Auth:** `X-Service-Key: <INTERNAL_SERVICE_KEY>`

**Request body:**
```json
{
  "notification_type": "feedback.status_changed",
  "recipient_user_id": "uuid",
  "variables": {
    "unique_ref": "GRV-2026-0042",
    "new_status": "Acknowledged",
    "project_name": "Dar-Morogoro Highway"
  },
  "channels": ["in_app", "push", "sms"],
  "source_service": "feedback_service",
  "source_entity_id": "uuid",
  "scheduled_for": null
}
```

**Data flow:** Template rendered (Jinja2) → Deliveries created per channel → Channel dispatchers invoked → Retries via APScheduler (exponential backoff)

---

### 4.5 Notification Webhooks (DLR)

#### `POST /webhooks/sms/dlr` — SMS delivery receipt (Africa's Talking / Twilio)
#### `POST /webhooks/email/dlr` — Email delivery receipt (SendGrid)
#### `POST /webhooks/whatsapp/dlr` — WhatsApp status callback (Meta)

All DLR webhooks update `NotificationDelivery.status` and `delivered_at`.

---

### 4.6 Templates

#### `GET /templates` — List notification templates [Platform Admin]
#### `POST /templates` — Create template [Platform Admin]
**Body:**
```json
{
  "notification_type": "custom.announcement",
  "channel": "email",
  "subject_template": "Important: {{ title }}",
  "body_template": "Dear {{ name }},\n\n{{ message }}\n\nRiviwa Team"
}
```

#### `GET/PATCH/DELETE /templates/{template_id}`

---

## 5. Payment Service (Port 8040)

**DB:** `payment_db` (port 5435) · **Nginx:** `/api/v1/payments`

---

### 5.1 Payments

#### `POST /payments` — Create payment intent
**Auth:** Bearer JWT

**Request body:**
```json
{
  "payment_type": "service_fee",
  "amount": 50000.00,
  "currency": "TZS",
  "phone": "+255712345678",
  "payer_name": "Hassan Mohamed",
  "payer_email": "hassan@example.com",
  "description": "Road permit processing fee",
  "org_id": "uuid",
  "project_id": "uuid",
  "reference_id": "uuid",
  "reference_type": "permit_application"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "payment_type": "service_fee",
  "amount": 50000.00,
  "currency": "TZS",
  "status": "PENDING",
  "external_ref": null,
  "payer_phone": "+255712345678",
  "created_at": "...",
  "expires_at": "2026-04-21T10:00:00Z"
}
```

---

#### `GET /payments` — List payments
**Auth:** Bearer JWT  
**Query:** `payer_user_id` · `org_id` · `project_id` · `reference_id` · `status` · `payment_type` · `skip` · `limit`  
> Non-staff users see only their own payments.

#### `GET /payments/{payment_id}` — Detail with transactions
**Response includes:** Payment fields + `transactions` array

---

#### `POST /payments/{payment_id}/initiate` — Initiate USSD push
**Auth:** Bearer JWT

**Request body:**
```json
{ "provider": "azampay" }
```
> `provider`: `azampay` (Airtel/M-Pesa/CRDB/NMB) | `selcom` (Tigo/TTCL/Halotel) | `mpesa` (Vodacom direct)

**Response 200:**
```json
{
  "id": "uuid",
  "payment_id": "uuid",
  "provider": "azampay",
  "status": "PENDING",
  "provider_ref": "AZM-12345",
  "checkout_url": null,
  "message": "Payment request sent. Customer will receive a USSD prompt."
}
```

**Data flow:** Provider API called → Transaction record created → Kafka `payment.initiated` published → Customer receives USSD push

---

#### `POST /payments/{payment_id}/verify` — Poll provider for status
**Auth:** Bearer JWT  
**No body** · Queries latest transaction's provider status

**Response:** Updated transaction with `status: COMPLETED|FAILED`

---

#### `POST /payments/{payment_id}/refund` — Initiate refund [Staff]
**Auth:** Bearer JWT (staff role required)  
**No body** · Kafka `payment.refunded` published

#### `DELETE /payments/{payment_id}` — Cancel PENDING payment
#### `GET /payments/{payment_id}/transactions` — List all transactions

---

### 5.2 Payment Webhooks

#### `POST /webhooks/azampay` — AzamPay callback
#### `POST /webhooks/selcom` — Selcom callback
#### `POST /webhooks/mpesa` — M-Pesa callback

All webhooks validate provider signatures, update payment/transaction status, publish Kafka `payment.completed|failed` events.

---

## 6. AI Service (Port 8085)

**DB:** `ai_db` (conversations) · **Kafka:** consumer + producer · **LLM:** Groq `llama-3.3-70b-versatile` + Ollama fallback · **RAG:** Qdrant

---

### 6.1 Web/Mobile AI Conversation

#### `POST /ai/conversations` — Start a new AI conversation
**Auth:** Optional Bearer JWT (anonymous consumers allowed)

**Request body:**
```json
{
  "channel": "web_portal",
  "language": "sw",
  "project_id": "uuid",
  "user_id": null,
  "web_token": null
}
```
> `channel`: `web_portal` | `mobile_app` | `sms` | `whatsapp` | `phone_call`  
> `language`: `sw` (Swahili) | `en` (English) — auto-detected from messages

**Response 201:**
```json
{
  "conversation_id": "uuid",
  "reply": "Habari! Mimi ni Riviwa AI. Ninaweza kukusaidia kuwasilisha malalamiko...",
  "status": "active",
  "stage": "greeting",
  "turn_count": 1,
  "confidence": 0.0,
  "language": "sw",
  "submitted": false,
  "submitted_feedback": [],
  "project_name": "Dar-Morogoro Highway",
  "is_urgent": false,
  "incharge_name": null,
  "incharge_phone": null
}
```

**Data flow:** Project loaded from DB → Dynamic greeting with project name + locations → Conversation record created

---

#### `POST /ai/conversations/{conversation_id}/message` — Send a message
**Auth:** None required

**Request body:**
```json
{
  "message": "Nina tatizo la fidia kwa ardhi yangu iliyochukuliwa",
  "media_urls": ["https://..."]
}
```

**Response 200:**
```json
{
  "conversation_id": "uuid",
  "reply": "Samahani kusikia hilo. Je, unaweza nieleze zaidi kuhusu ardhi yako...",
  "status": "active",
  "stage": "collecting",
  "turn_count": 3,
  "confidence": 0.65,
  "submitted": false,
  "submitted_feedback": []
}
```

**Data flow (on confidence ≥ 0.82):**
1. Feedback auto-submitted to feedback_service via HTTP
2. Unique ref returned (GRV-YYYY-NNNN)
3. `submitted = true` in response
4. Conversation status → `COMPLETED`

---

#### `GET /ai/conversations/{conversation_id}` — Get conversation status and transcript
**Response:** Full conversation with `transcript`, `extracted_data`, `submitted_feedback`

---

### 6.2 Webhook Handlers (SMS/WhatsApp)

#### `POST /ai/webhooks/sms` — Inbound SMS
**Auth:** None (verified by provider signature internally)

**Africa's Talking body (form):**
```
phoneNumber=+255712345678&text=Nina tatizo&linkId=...
```

**Twilio body (form):**
```
From=+255712345678&Body=Nina tatizo&MessageSid=...
```

**Response:** `{ "message": "Asante kwa kuwasiliana nasi..." }` (Africa's Talking format)

---

#### `POST /ai/webhooks/whatsapp` — Inbound WhatsApp (Meta Cloud API)
**Auth:** Webhook verification via `hub.verify_token`

**GET** (verification): `?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...`

**POST** (messages): Meta Cloud API payload with `entry[0].changes[0].value.messages`

Supports: text, audio (voice notes → STT transcription), images

---

### 6.3 Internal

#### `POST /ai/internal/classify` — Classify feedback [Internal]
**Auth:** `X-Service-Key`  
**Body:** `{ "feedback_id": "uuid", "text": "...", "project_id": "uuid" }`  
**Response:** `{ "category_def_id": "uuid", "confidence": 0.87 }`

---

### 6.4 Admin

#### `GET /ai/admin/conversations` — List all conversations [Platform Admin]
#### `GET /ai/admin/stats` — AI usage statistics

---

## 7. Analytics Service (Port 8095)

**DB:** Reads `feedback_db` (read-only) + `analytics_db` (own) · **Auth:** Bearer JWT (staff role for all endpoints)

---

### 7.1 General Feedback Analytics

All under `/analytics/feedback`. Query param `project_id` (UUID) required.

#### `GET /analytics/feedback/time-to-open`
Time from `submitted_at` to first action (avg/min/max/median hours).  
**Query:** `project_id` · `date_from` · `date_to`

#### `GET /analytics/feedback/unread`
All feedback with `status=SUBMITTED` (unacknowledged).  
**Query:** `project_id` · `priority` · `feedback_type`

**Response:** `{ "total": 12, "items": [{ "feedback_id", "unique_ref", "days_waiting", ... }] }`

#### `GET /analytics/feedback/overdue`
Feedback in `acknowledged|in_review` past `target_resolution_date`.  
**Query:** `project_id` · `feedback_type`

#### `GET /analytics/feedback/not-processed`
Acknowledged/in_review but not yet resolved.

#### `GET /analytics/feedback/processed-today`
Feedback that moved to `in_review` today.

#### `GET /analytics/feedback/resolved-today`
Resolved today with `resolution_hours` duration.

---

### 7.2 Grievance Analytics

All under `/analytics/grievances`. Query param `project_id` required.

#### `GET /analytics/grievances/unresolved`
**Query:** `project_id` · `min_days` · `priority` · `status`

**Response:** `{ "total": 8, "items": [{ "feedback_id", "days_unresolved", "issue_lga", ... }] }`

#### `GET /analytics/grievances/sla-status`
SLA compliance by priority bucket.

**SLA targets:**
| Priority | Acknowledgement | Resolution |
|---------|----------------|-----------|
| CRITICAL | 4 hours | 72 hours |
| HIGH | 8 hours | 168 hours |
| MEDIUM | 24 hours | 336 hours |
| LOW | 48 hours | 720 hours |

**Response:** `{ "by_priority": [{ "priority", "total", "ack_compliant", "res_compliant", "sla_pct" }] }`

#### `GET /analytics/grievances/hotspots`
Geographic clustering of grievances by LGA/ward.  
**Query:** `project_id` · `from_date` · `to_date` · `min_count`

---

### 7.3 Suggestion Analytics

All under `/analytics/suggestions`.

#### `GET /analytics/suggestions/summary` — Suggestion counts by category
#### `GET /analytics/suggestions/top-categories` — Most submitted categories
#### `GET /analytics/suggestions/implementation-rate` — Actioned vs total

---

### 7.4 Staff Analytics

All under `/analytics/staff`.

#### `GET /analytics/staff/workload` — Feedback assigned per staff member
**Query:** `project_id` · `from_date` · `to_date`

#### `GET /analytics/staff/resolution-rate` — Resolution rate per officer
#### `GET /analytics/staff/response-time` — Average response time per officer

---

### 7.5 Inquiry Analytics

All under `/analytics/inquiries`. Query param `project_id` required.

#### `GET /analytics/inquiries/summary`
Total, open, resolved, dismissed, avg response hours, avg days open, open counts by priority.  
**Query:** `project_id` · `date_from` · `date_to`

**Response:**
```json
{
  "total_inquiries": 34,
  "open_inquiries": 12,
  "resolved": 18,
  "closed": 3,
  "dismissed": 1,
  "avg_response_hours": 6.4,
  "avg_days_open": 2.1,
  "critical_open": 1,
  "high_open": 4,
  "medium_open": 5,
  "low_open": 2
}
```

#### `GET /analytics/inquiries/unread`
Inquiries with `status=SUBMITTED` (not yet acknowledged).  
**Query:** `project_id` · `priority` · `department_id` · `service_id` · `product_id` · `category_def_id`

**Response:** `{ "total": 5, "items": [{ "feedback_id", "unique_ref", "days_waiting", "channel", ... }] }`

#### `GET /analytics/inquiries/overdue`
Inquiries in `acknowledged|in_review` past their `target_resolution_date`.  
**Query:** `project_id` · `department_id` · `service_id` · `product_id` · `category_def_id`

**Response:** `{ "total": 2, "items": [{ "feedback_id", "days_overdue", "assigned_to_user_id", ... }] }`

#### `GET /analytics/inquiries/by-channel`
Inquiry counts grouped by intake channel.  
**Query:** `project_id` · `date_from` · `date_to`

**Response:** `{ "total_items": 4, "items": [{ "channel", "total", "open_count", "resolved" }] }`

#### `GET /analytics/inquiries/by-category`
Inquiry counts grouped by dynamic category (`category_def_id`).  
**Query:** `project_id` · `date_from` · `date_to`

**Response:** `{ "total_items": 6, "items": [{ "category_def_id", "category_name", "category_slug", "total", "open_count", "resolved", "avg_response_hours" }] }`

---

### 7.6 Org-level Analytics

All under `/analytics/org/{org_id}/...`. Aggregates across **all projects** in the organisation.

#### General

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/org/{org_id}/summary` | Totals by type/status/priority across all org projects |
| `GET /analytics/org/{org_id}/by-project` | Per-project breakdown (includes `project_name`) |
| `GET /analytics/org/{org_id}/by-period` | Submission volume over time (`?granularity=day\|week\|month`) |
| `GET /analytics/org/{org_id}/by-channel` | Counts by intake channel |
| `GET /analytics/org/{org_id}/by-department` | Counts grouped by `department_id` |
| `GET /analytics/org/{org_id}/by-service` | Counts grouped by `service_id` |
| `GET /analytics/org/{org_id}/by-product` | Counts grouped by `product_id` |
| `GET /analytics/org/{org_id}/by-category` | Counts grouped by `category_def_id` (includes `category_name`) |

**Common query params:** `date_from` · `date_to` · `feedback_type`

**Summary response example:**
```json
{
  "total": 842,
  "grievances": 410,
  "suggestions": 280,
  "applause": 115,
  "inquiries": 37,
  "unresolved": 94,
  "resolved": 613,
  "avg_resolution_hours": 38.4
}
```

#### Grievances

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/org/{org_id}/grievances/summary` | Unresolved, escalated, overdue, avg resolution, priority breakdown |
| `GET /analytics/org/{org_id}/grievances/by-level` | Counts grouped by GRM level |
| `GET /analytics/org/{org_id}/grievances/by-location` | Counts grouped by LGA/ward |
| `GET /analytics/org/{org_id}/grievances/sla` | SLA compliance by priority across the org |

#### Suggestions

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/org/{org_id}/suggestions/summary` | Total, actioned, noted, pending, dismissed, avg impl hours |
| `GET /analytics/org/{org_id}/suggestions/by-project` | Implementation rate per project |

#### Applause

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/org/{org_id}/applause/summary` | Total, this month, MoM change, top categories, by project |

#### Inquiries

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/org/{org_id}/inquiries/summary` | Total, open, resolved, dismissed, avg response hours |

---

### 7.7 Platform-level Analytics

All under `/analytics/platform/...`. Aggregates across **all organisations** and **all projects**. Intended for platform admins.

#### General

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/platform/summary` | Platform-wide totals by type/status/priority |
| `GET /analytics/platform/by-org` | Per-organisation breakdown (includes `org_name`) |
| `GET /analytics/platform/by-period` | Submission volume over time across entire platform |
| `GET /analytics/platform/by-channel` | Intake channel breakdown across all orgs |

**Common query params:** `date_from` · `date_to` · `feedback_type` · `granularity` (for by-period)

**`/platform/summary` response:**
```json
{
  "total": 12840,
  "grievances": 6200,
  "suggestions": 4100,
  "applause": 2200,
  "inquiries": 340,
  "total_inquiries": 340,
  "unresolved": 890,
  "resolved": 10940,
  "avg_resolution_hours": 42.1
}
```

**`/platform/by-org` response:**
```json
{
  "total_items": 8,
  "items": [
    {
      "organisation_id": "uuid",
      "org_name": "TANROADS",
      "total_projects": 12,
      "total": 4820,
      "grievances": 2400,
      "suggestions": 1600,
      "applause": 700,
      "inquiries": 120,
      "unresolved": 310,
      "resolved": 4100,
      "avg_resolution_hours": 38.2
    }
  ]
}
```

#### Grievances

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/platform/grievances/summary` | Platform-wide grievance totals, priority/status breakdown |
| `GET /analytics/platform/grievances/sla` | SLA compliance by priority across entire platform |

#### Suggestions

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/platform/suggestions/summary` | Total, actioned, pending, dismissed, actioned_rate, avg impl hours |

#### Applause

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/platform/applause/summary` | Total, MoM trend, top categories, by-org breakdown |

**Response:**
```json
{
  "total_applause": 2200,
  "this_month": 180,
  "last_month": 155,
  "mom_change": 16.1,
  "top_categories": [{ "category", "count" }],
  "by_org": [{ "organisation_id", "count" }]
}
```

#### Inquiries

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/platform/inquiries/summary` | Platform-wide inquiry totals, open by priority, avg response hours |

---

### 7.8 AI Insights (Groq — multi-scope)

#### `POST /analytics/ai/ask`
**Auth:** Bearer JWT

Ask a natural language question about analytics data at project, org, or platform scope. Context is automatically fetched from the database and enriched with human-readable names (project name, org name, branches, FAQs, departments, services) before being sent to Groq `llama-3.3-70b-versatile`.

**Request body:**
```json
{
  "question": "Which departments have the most unresolved grievances this month?",
  "scope": "project",
  "context_type": "grievances",
  "project_id": "uuid",
  "org_id": null
}
```

**`scope` values:**

| scope | Required field | `context_type` options |
|-------|---------------|----------------------|
| `project` | `project_id` | `general` · `grievances` · `suggestions` · `sla` · `committees` · `hotspots` · `staff` · `unresolved` · `inquiries` |
| `org` | `org_id` | `org_general` · `org_grievances` · `org_suggestions` · `org_applause` · `org_inquiries` |
| `platform` | _(none)_ | `platform_general` · `platform_grievances` · `platform_suggestions` · `platform_applause` · `platform_inquiries` |

**Response:**
```json
{
  "answer": "The Customer Care department has 14 unresolved grievances this month, the highest of any department. The majority are HIGH priority compensation cases in Ilala Ward. SLA compliance for this department stands at 61%...",
  "context_used": {
    "scope": "project",
    "project_name": "Dar-Morogoro Highway Upgrade",
    "org_name": "TANROADS",
    "region": "Dar es Salaam",
    "summary": { "total": 142, "grievances": 80, "suggestions": 45, "applause": 12, "inquiries": 5 },
    "departments": [{ "id": "uuid", "name": "Customer Care" }],
    "unresolved_grievances_count": 22,
    "sla_compliance_rate": 68.4
  },
  "model": "llama-3.3-70b-versatile"
}
```

**Context enrichment:** Before calling Groq, the service:
1. Resolves `project_name`, `org_name`, `sector`, `region`, `primary_lga` from `fb_projects`
2. For `scope=org|platform`: calls `GET /internal/orgs/{org_id}/ai-context` on auth_service to include branches, FAQs, departments, and services as named entities
3. Fetches live metrics from feedback_db matching the `context_type`

---

## 8. Data Flow & Kafka Events

### Kafka Topics

| Topic | Producer | Consumers | Description |
|-------|----------|-----------|-------------|
| `riviwa.user.events` | auth_service | notification, stakeholder | User lifecycle |
| `riviwa.organisation.events` | auth_service | feedback, stakeholder, notification | Org/project/invite events — `org.updated` includes `display_name` + `logo_url` for downstream sync |
| `riviwa.stakeholder.events` | stakeholder_service | notification, feedback | Engagement events |
| `riviwa.feedback.events` | feedback_service | notification, analytics, spark | GRM lifecycle |
| `riviwa.payment.events` | payment_service | notification | Payment lifecycle |
| `riviwa.notifications` | All services → | notification_service | Notification requests (inbound) |
| `riviwa.notifications.events` | notification_service | All | Delivery receipts |

---

### Key Data Flows

#### Consumer Registers via SMS/WhatsApp → Submits Grievance
```
Consumer sends SMS/WhatsApp
  → AI Service webhook handler
  → ConversationService.handle_inbound_sms/whatsapp()
  → If new number: POST /auth/channel-register (X-Service-Key)
    → auth_service creates User(status=CHANNEL_REGISTERED)
    → Kafka user.registered
  → AI collects fields (multiple turns)
  → On confidence ≥ 0.82: POST /feedback (X-Service-Key)
    → feedback_service.submit()
    → unique_ref generated (GRV-YYYY-NNNN)
    → Kafka feedback.submitted
    → notification_service sends SMS with ref number
```

#### Staff Login → Submit Feedback → PAP Notified
```
Staff: POST /auth/login → login_token
Staff: POST /auth/login/verify-otp → access_token + refresh_token
Staff: POST /feedback (Bearer token)
  → FeedbackService.submit()
  → Feedback row created, unique_ref assigned
  → category_def_id auto-linked by category slug
  → Kafka feedback.submitted published
    → notification_service consumes:
      → Finds PAP user (if submitted_by_user_id set)
      → Sends in_app + push + SMS notification with ref
    → analytics_service updates counters
    → spark SLA monitor picks up new grievance
```

#### Project Activated → Downstream Services Sync
```
Admin: POST /orgs/{org_id}/projects/{project_id}/activate
  → ProjectService.activate_project()
  → OrgProject.status → ACTIVE
  → Kafka org_project.published
    → feedback_service consumes: creates ProjectCache row
    → stakeholder_service consumes: creates ProjectCache row
    → notification_service: notifies project in-charges
```

#### Department Created → Feedback Filed Against It
```
Admin: POST /orgs/{org_id}/departments (auth_service)
  → DepartmentService.create() → org_departments row in auth_db
  → Kafka org_department.created

Staff/PAP: POST /feedback or POST /my/feedback
  → body.department_id = <org_departments.id>
  → feedback_service stores UUID in feedbacks.department_id
    (soft FK — no DB constraint, cross-database reference)
  → Analytics queries join feedbacks on department_id
    to produce per-department breakdown reports
```

#### Organization Logo Updated → Downstream Sync
```
Admin: POST /orgs/{org_id}/logo (multipart/form-data)
  → ImageService.upload() → MinIO organisations/{org_id}/logo.{ext}
  → Organisation.logo_url updated in auth_db
  → Kafka org.updated { org_id, display_name, legal_name, logo_url }
    → feedback_service: updates fb_projects.org_logo_url + fb_projects.org_display_name
    → stakeholder_service: updates project cache
```

#### Organisation Created/Updated → Org Name Synced to Projects
```
Admin: POST /orgs (or PATCH /orgs/{org_id})
  → Kafka org.created / org.updated { org_id, display_name, legal_name, logo_url, ... }
    → feedback_service: updates fb_projects.org_display_name
      for all projects WHERE organisation_id = org_id
    → analytics_service AI insights: can now resolve org name without HTTP call
      (fb_projects.org_display_name used in get_platform_by_org, get_org_name)
```

#### Inquiry Submitted → Tracked Like Any Feedback Type
```
Staff/PAP: POST /feedback or POST /my/feedback { feedback_type: "inquiry" }
  → FeedbackService.submit()
  → unique_ref = "INQ-YYYY-NNNN" (per-project sequence in feedback_ref_sequences)
  → Kafka feedback.submitted published
  → Analytics: counted in total_inquiries, inquiry_summary, org/platform inquiry endpoints
  → AI insights: included in context when context_type = "inquiries" | "org_inquiries" | "platform_inquiries"
```

---

### Internal Service-to-Service Authentication

All service-to-service calls use the `X-Service-Key` header with the shared `INTERNAL_SERVICE_KEY`.

Internal-only endpoints (not proxied by Nginx, not in public docs):
- `POST /auth/channel-register` — feedback_service → auth_service
- `GET /internal/orgs/{org_id}/ai-context` — analytics_service → auth_service _(new)_
- `GET /feedback/{id}/for-ai` — ai_service → feedback_service
- `PATCH /feedback/{id}/ai-enrich` — ai_service → feedback_service
- `GET /feedback/by-ref/{ref}` — ai_service → feedback_service
- `POST /internal/notify` — any service → notification_service
- `POST /ai/internal/classify` — feedback_service → ai_service

#### `GET /internal/orgs/{org_id}/ai-context` — Org profile for AI enrichment
**Auth:** `X-Service-Key: <INTERNAL_SERVICE_KEY>` · Called by analytics_service AI insights

**Response:**
```json
{
  "org_id": "uuid",
  "legal_name": "Tanzania National Roads Agency",
  "display_name": "TANROADS",
  "description": "Agency responsible for trunk and regional roads",
  "org_type": "GOVERNMENT",
  "status": "ACTIVE",
  "country_code": "TZ",
  "is_verified": true,
  "branches": [
    { "id": "uuid", "name": "Dar es Salaam Zone", "branch_type": "Regional Office", "is_root": true }
  ],
  "faqs": [
    { "q": "How do I submit a grievance?", "a": "Call our toll-free number or visit the nearest zone office." }
  ],
  "departments": [
    { "id": "uuid", "name": "Customer Care", "code": "CC" }
  ],
  "services": [
    { "id": "uuid", "name": "Road Permit Processing", "type": "SERVICE", "cat": "Permits" }
  ]
}
```

---

### JWT Claims

```json
{
  "sub": "user_uuid",
  "jti": "unique_token_id",
  "iat": 1713600000,
  "exp": 1713603600,
  "org_id": "org_uuid_or_null",
  "org_role": "ADMIN|MANAGER|MEMBER|OWNER|null",
  "platform_role": "admin|super_admin|moderator|null"
}
```

**Verification:** All services verify JWT using `AUTH_SECRET_KEY` + `AUTH_ALGORITHM=HS256`. JTI deny-list checked in Redis on every request.

---

### Common Error Responses

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description",
  "detail": { "field": "additional context" }
}
```

| Code | HTTP | Common Causes |
|------|------|---------------|
| `VALIDATION_ERROR` | 400 | Missing required field, invalid format |
| `INVALID_OTP` | 400 | Wrong 6-digit code |
| `UNAUTHORISED` | 401 | Missing/invalid/expired JWT |
| `FORBIDDEN` | 403 | Insufficient role or service key |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `CONFLICT` | 409 | Duplicate (slug/email/name already taken) |
| `OTP_EXPIRED` | 410 | Session TTL passed — restart flow |
| `TOO_MANY_ATTEMPTS` | 429 | Rate limit or max OTP tries exceeded |
| `PAYMENT_NOT_FOUND` | 404 | Payment not found |
| `FRAUD_BLOCKED` | 403 | Registration blocked by fraud engine |
| `DEPARTMENT_NAME_CONFLICT` | 409 | Department name already exists in org |
| `DEPARTMENT_CODE_CONFLICT` | 409 | Department code already exists in org |
