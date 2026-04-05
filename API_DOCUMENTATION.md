# Riviwa Platform API Documentation -- Part 1: Auth Service & Feedback Service

---

## Table of Contents

- [1. Auth Service (Port 8000)](#1-auth-service)
  - [1.1 Authentication](#11-authentication)
  - [1.2 Channel Auth](#12-channel-auth)
  - [1.3 Registration](#13-registration)
  - [1.4 Password Management](#14-password-management)
  - [1.5 Users](#15-users)
  - [1.6 Organisations](#16-organisations)
  - [1.7 Org Extended (Locations, Content, FAQs, Branches, Services)](#17-org-extended)
  - [1.8 Projects, Stages, Sub-projects](#18-projects)
  - [1.9 Checklists](#19-checklists)
  - [1.10 Admin Dashboard](#110-admin-dashboard)
  - [1.11 Webhooks](#111-webhooks)
- [2. Feedback Service (Port 8090)](#2-feedback-service)
  - [2.1 Feedback](#21-feedback)
  - [2.2 Actions](#22-actions)
  - [2.3 Categories](#23-categories)
  - [2.4 Channel Sessions](#24-channel-sessions)
  - [2.5 GRM Committees](#25-grm-committees)
  - [2.6 PAP Portal](#26-pap-portal)
  - [2.7 Reports](#27-reports)
  - [2.8 Voice](#28-voice)

---

## Base URLs

| Service | Base URL |
|---------|----------|
| Auth Service | `https://api.riviwa.com/api/v1` (Port 8000) |
| Feedback Service | `https://api.riviwa.com/api/v1` (Port 8090) |

## Authentication Types

| Type | Description |
|------|-------------|
| **None** | Public endpoint, no authentication needed |
| **Bearer JWT** | `Authorization: Bearer <access_token>` |
| **X-Service-Key** | Internal service-to-service API key header |
| **Org Role** | Bearer JWT + caller must hold the specified role in the target org (MEMBER, MANAGER, ADMIN, OWNER) |
| **Platform Role** | Bearer JWT + `platform_role` claim must be `admin` or `super_admin` |
| **StaffDep** | Bearer JWT + caller must be PIU/GRM staff for the project |
| **PAPDep** | Bearer JWT + caller is a PAP (Project Affected Person) |

## Common Error Response Format

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Request body is invalid.",
  "details": [
    { "field": "body.email", "message": "Invalid email." }
  ]
}
```

---

# 1. Auth Service

## 1.1 Authentication

### POST `/api/v1/auth/login`

**Summary:** Login Step 1 -- submit credentials, receive OTP.

**Auth:** None

**Request Body:**
```json
{
  "identifier": "alice@example.com",       // string, email or E.164 phone
  "password": "MyP@ssw0rd!",              // string
  "device_fingerprint": "abc123..."        // string | null, optional
}
```

**Success Response (200):**
```json
{
  "login_token": "opaque-redis-key",
  "otp_channel": "email",
  "otp_destination": "al***@example.com",
  "expires_in_seconds": 300
}
```

**Error Codes:** `400` Validation error, `401` Invalid credentials, `403` Account suspended/banned/deactivated, `423` Account temporarily locked

---

### POST `/api/v1/auth/login/verify-otp`

**Summary:** Login Step 2 -- verify OTP and receive JWT token pair.

**Auth:** None

**Request Body:**
```json
{
  "login_token": "opaque-redis-key",      // string, from Step 1
  "otp_code": "193847"                     // string, exactly 6 digits
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "opaque-refresh-token",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error Codes:** `400` Invalid or expired OTP, `429` Maximum OTP attempts exceeded (session destroyed)

---

### POST `/api/v1/auth/token/refresh`

**Summary:** Exchange a valid refresh token for a new access token. Refresh token is rotated.

**Auth:** None (refresh token in body)

**Request Body:**
```json
{
  "refresh_token": "opaque-refresh-token"  // string
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "new-opaque-refresh-token",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error Codes:** `401` Refresh token invalid or expired

---

### POST `/api/v1/auth/token/logout`

**Summary:** Revoke current session -- deny-lists the access token JTI and deletes the refresh token.

**Auth:** Bearer JWT

**Request Body:**
```json
{
  "refresh_token": "opaque-refresh-token"  // string
}
```

**Success Response (200):**
```json
{
  "message": "Logged out successfully."
}
```

**Error Codes:** `401` Not authenticated

---

### POST `/api/v1/auth/switch-org`

**Summary:** Switch active org dashboard context. Returns new token pair scoped to the new org.

**Auth:** Bearer JWT (active user)

**Request Body:**
```json
{
  "org_id": "uuid-of-target-org"           // UUID | null (null = personal view)
}
```

**Success Response (200):**
```json
{
  "message": "Dashboard context switched.",
  "tokens": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "org_id": "uuid-of-target-org",
  "org_role": "admin"
}
```

**Error Codes:** `401` Not authenticated, `403` Not an active member of the requested org

---

### POST `/api/v1/auth/social`

**Summary:** Social login/registration (Google, Apple, Facebook). Single-step.

**Auth:** None

**Request Body:**
```json
{
  "provider": "google",                    // "google" | "apple" | "facebook"
  "id_token": "eyJhbGciOiJSUzI1NiIs...",  // string, OIDC JWT from provider
  "device_fingerprint": "abc123..."        // string | null, optional
}
```

**Success Response (200):**
```json
{
  "message": "Social authentication successful.",
  "user_id": "uuid",
  "is_new_user": true,
  "has_password": false,
  "tokens": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

**Error Codes:** `401` Invalid or expired provider token, `409` Email linked to a different OAuth provider

---

### POST `/api/v1/auth/social/set-password`

**Summary:** Add a password to a social-only account so the user can also log in via email+password.

**Auth:** Bearer JWT (active user)

**Request Body:**
```json
{
  "password": "MyP@ssw0rd!",              // string, min 8 chars, must meet policy
  "confirm_password": "MyP@ssw0rd!"       // string, must match password
}
```

**Success Response (200):**
```json
{
  "message": "Password set. You can now log in with email and password."
}
```

**Error Codes:** `400` Password policy violation, `401` Not authenticated, `409` Account already has a password

---

## 1.2 Channel Auth

### POST `/api/v1/auth/channel-register`

**Summary:** [Internal] Auto-register a PAP from an inbound channel message. Called by feedback_service.

**Auth:** X-Service-Key header

**Request Body:**
```json
{
  "phone_number": "+255712345678",         // string, E.164
  "channel": "whatsapp",                   // "sms" | "whatsapp" | "phone_call"
  "display_name": "John Doe",             // string | null, optional
  "language": "sw"                         // "sw" | "en", optional
}
```

**Success Response (200):**
```json
{
  "user_id": "uuid",
  "is_new_user": true,
  "must_set_password": true,
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error Codes:** `400` Invalid phone format, `401` Invalid service key

---

### POST `/api/v1/auth/channel-login/request-otp`

**Summary:** Channel login Step 1 -- send OTP to a channel-registered phone number.

**Auth:** None

**Request Body:**
```json
{
  "phone_number": "+255712345678"          // string, E.164
}
```

**Success Response (200):**
```json
{
  "session_token": "opaque-session-token",
  "message": "OTP sent to your registered phone number.",
  "expires_in": 300
}
```

**Error Codes:** `400` Invalid phone format

---

### POST `/api/v1/auth/channel-login/verify-otp`

**Summary:** Channel login Step 2 -- verify OTP, receive tokens. Includes `must_set_password` flag.

**Auth:** None

**Request Body:**
```json
{
  "session_token": "opaque-session-token", // string, from Step 1
  "otp_code": "483920"                     // string, 6 digits
}
```

**Success Response (200):**
```json
{
  "user_id": "uuid",
  "must_set_password": true,
  "next_step": "set_password",
  "message": "Please set a password to complete your account setup.",
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error Codes:** `400` Invalid OTP or missing fields

---

## 1.3 Registration

### POST `/api/v1/auth/register/init`

**Summary:** Registration Step 1 -- submit email OR phone number, receive OTP.

**Auth:** None

**Request Body:**
```json
{
  "email": "alice@example.com",            // EmailStr | null (XOR with phone_number)
  "phone_number": null,                    // string E.164 | null (XOR with email)
  "first_name": "Alice",                  // string | null, optional
  "last_name": "Smith",                   // string | null, optional
  "device_fingerprint": "abc123..."        // string | null, optional
}
```

**Success Response (200):**
```json
{
  "registration_token": "opaque-redis-key",
  "otp_channel": "email",
  "otp_destination": "al***@example.com",
  "expires_in_seconds": 600
}
```

**Error Codes:** `400` Invalid identifier, `409` Email/phone already registered, `422` Both or neither identifier supplied, `403` Registration blocked by fraud engine

---

### POST `/api/v1/auth/register/verify-otp`

**Summary:** Registration Step 2 -- verify the 6-digit OTP.

**Auth:** None

**Request Body:**
```json
{
  "registration_token": "opaque-redis-key", // string
  "otp_code": "483920"                      // string, 6 digits
}
```

**Success Response (200):**
```json
{
  "registration_token": "same-token-now-promoted",
  "message": "OTP verified. Proceed to complete registration."
}
```

**Error Codes:** `400` Invalid OTP, `410` Session expired, `429` Max attempts exceeded

---

### POST `/api/v1/auth/register/complete`

**Summary:** Registration Step 3 -- set password, activate account.

**Auth:** None

**Request Body:**
```json
{
  "registration_token": "promoted-token",  // string, from Step 2
  "password": "MyP@ssw0rd!",              // string, min 8, must meet policy
  "confirm_password": "MyP@ssw0rd!",      // string, must match
  "username": "alice_smith",               // string | null, optional (auto-generated if omitted)
  "first_name": "Alice",                  // string | null, optional
  "last_name": "Smith"                    // string | null, optional
}
```

**Success Response (201):**
```json
{
  "message": "Account created successfully.",
  "user_id": "uuid",
  "is_new_user": true,
  "action": "complete",
  "tokens": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

**Error Codes:** `400` Weak password / policy violation, `410` Continuation token expired

---

### POST `/api/v1/auth/register/resend-otp`

**Summary:** Resend OTP for an active registration session (60s cooldown between resends).

**Auth:** None

**Request Body:**
```json
{
  "session_token": "registration-or-login-token" // string
}
```

**Success Response (200):**
```json
{
  "registration_token": "new-session-token",
  "otp_channel": "email",
  "otp_destination": "al***@example.com",
  "expires_in_seconds": 600
}
```

**Error Codes:** `410` Session expired, `429` Resend cooldown active (60s minimum)

---

## 1.4 Password Management

### POST `/api/v1/auth/password/forgot`

**Summary:** Forgot password Step 1 -- request OTP. Always returns 200 (prevents enumeration).

**Auth:** None

**Request Body:**
```json
{
  "identifier": "alice@example.com",       // string, email or E.164 phone
  "device_fingerprint": "abc..."           // string | null, optional
}
```

**Success Response (200):**
```json
{
  "reset_token": "opaque-redis-key",
  "otp_channel": "email",
  "otp_destination": "al***@example.com",
  "expires_in_seconds": 600,
  "message": "If an account with that identifier exists, a verification code has been sent."
}
```

**Error Codes:** Always 200 (by design)

---

### POST `/api/v1/auth/password/forgot/verify-otp`

**Summary:** Forgot password Step 2 -- verify OTP, promote the reset token.

**Auth:** None

**Request Body:**
```json
{
  "reset_token": "opaque-redis-key",       // string
  "otp_code": "920384"                     // string, 6 digits
}
```

**Success Response (200):**
```json
{
  "reset_token": "same-token-promoted",
  "message": "OTP verified. You may now set a new password."
}
```

**Error Codes:** `400` Invalid OTP, `410` Session expired, `429` Max attempts exceeded

---

### POST `/api/v1/auth/password/forgot/reset`

**Summary:** Forgot password Step 3 -- set new password using the promoted reset token.

**Auth:** None

**Request Body:**
```json
{
  "reset_token": "promoted-token",         // string
  "new_password": "NewP@ssw0rd!",         // string, min 8, must meet policy
  "confirm_new_password": "NewP@ssw0rd!"  // string, must match
}
```

**Success Response (200):**
```json
{
  "message": "Password reset successfully. Please log in with your new password."
}
```

**Error Codes:** `400` Password policy violation / OTP not verified, `410` Session expired

---

### POST `/api/v1/auth/password/change`

**Summary:** Change password for the currently authenticated user. Terminates all other sessions.

**Auth:** Bearer JWT (active user)

**Request Body:**
```json
{
  "current_password": "OldP@ssw0rd!",     // string
  "new_password": "NewP@ssw0rd!",         // string, min 8, must meet policy
  "confirm_new_password": "NewP@ssw0rd!"  // string, must match
}
```

**Success Response (200):**
```json
{
  "message": "Password changed. All other sessions have been terminated."
}
```

**Error Codes:** `400` Current password incorrect / policy violation, `401` Not authenticated, `409` No password set (use social/set-password)

---

### POST `/api/v1/auth/password/channel/set-password`

**Summary:** Set first password for a channel-registered account (upgrades status to ACTIVE).

**Auth:** Bearer JWT (active user or channel-registered)

**Request Body:**
```json
{
  "new_password": "MyP@ssw0rd!"           // string, must meet policy
}
```

**Success Response (200):**
```json
{
  "message": "Password set. Your account is now fully active.",
  "user_id": "uuid",
  "status": "active"
}
```

**Error Codes:** `400` Password policy violation, `401` Not authenticated

---

## 1.5 Users

### GET `/api/v1/users/me`

**Summary:** Get the full private profile for the authenticated user.

**Auth:** Bearer JWT (active user)

**Success Response (200):**
```json
{
  "id": "uuid",
  "username": "alice_smith",
  "email": "alice@example.com",
  "phone_number": "+12125551234",
  "is_email_verified": true,
  "phone_verified": true,
  "id_verified": false,
  "display_name": "Alice Smith",
  "full_name": "Alice Jane Smith",
  "avatar_url": "https://cdn.riviwa.com/avatars/uuid.jpg",
  "date_of_birth": "1990-07-15",
  "gender": "female",
  "country_code": "US",
  "language": "en",
  "status": "active",
  "oauth_provider": null,
  "has_password": true,
  "two_factor_enabled": false,
  "active_org_id": null,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-06-01T08:30:00Z",
  "last_login_at": "2025-06-10T14:22:00Z"
}
```

**Error Codes:** `401` Not authenticated

---

### PATCH `/api/v1/users/me`

**Summary:** Update profile fields (PATCH semantics -- only supplied fields are changed).

**Auth:** Bearer JWT (active user)

**Request Body:**
```json
{
  "username": "alice_s",                   // string | null, optional
  "display_name": "Alice S.",             // string | null, optional
  "full_name": "Alice Jane Smith",        // string | null, optional
  "date_of_birth": "1990-07-15",          // string YYYY-MM-DD | null, optional
  "gender": "female",                      // string | null, optional
  "country_code": "TZ",                   // string 2-char ISO | null, optional
  "language": "sw"                         // string BCP-47 | null, optional
}
```

**Success Response (200):** Same structure as GET `/users/me`

**Error Codes:** `400` Validation error, `401` Not authenticated, `409` Username already taken

---

### DELETE `/api/v1/users/me`

**Summary:** Soft-delete (deactivate) the authenticated user's account. Terminates all sessions.

**Auth:** Bearer JWT (active user)

**Success Response (200):**
```json
{
  "message": "Your account has been deactivated. Contact support to reactivate."
}
```

**Error Codes:** `401` Not authenticated

---

### POST `/api/v1/users/me/avatar`

**Summary:** Set or clear the profile avatar URL.

**Auth:** Bearer JWT (active user)

**Request Body:**
```json
{
  "avatar_url": "https://cdn.riviwa.com/avatars/uuid.jpg"  // string HTTPS | null
}
```

**Success Response (200):** Same structure as GET `/users/me`

**Error Codes:** `400` URL is not HTTPS, `401` Not authenticated

---

### POST `/api/v1/users/me/verify-email`

**Summary:** Mark the authenticated user's email as verified.

**Auth:** Bearer JWT (active user)

**Success Response (200):**
```json
{ "message": "Email address verified." }
```

**Error Codes:** `401` Not authenticated

---

### POST `/api/v1/users/me/verify-phone`

**Summary:** Mark the authenticated user's phone as verified.

**Auth:** Bearer JWT (active user)

**Success Response (200):**
```json
{ "message": "Phone number verified." }
```

**Error Codes:** `401` Not authenticated

---

### POST `/api/v1/users/{user_id}/suspend`

**Summary:** [Admin] Suspend a user account.

**Auth:** Platform Role (admin)

**Query Parameters:** `reason` (string, optional)

**Success Response (200):**
```json
{ "message": "User {user_id} has been suspended." }
```

**Error Codes:** `401`, `403` Insufficient platform role, `404` User not found

---

### POST `/api/v1/users/{user_id}/ban`

**Summary:** [Admin] Permanently ban a user account.

**Auth:** Platform Role (admin)

**Query Parameters:** `reason` (string, optional)

**Success Response (200):**
```json
{ "message": "User {user_id} has been banned." }
```

**Error Codes:** `401`, `403`, `404`

---

### POST `/api/v1/users/{user_id}/reactivate`

**Summary:** [Admin] Reactivate a suspended or deactivated user (not banned).

**Auth:** Platform Role (admin)

**Success Response (200):**
```json
{ "message": "User {user_id} has been reactivated." }
```

**Error Codes:** `401`, `403`, `404`

---

## 1.6 Organisations

### GET `/api/v1/orgs`

**Summary:** Public org discovery with search, filter, and pagination.

**Auth:** None

**Query Parameters:** `search` (string), `org_type` (string), `verified_only` (bool, default true), `sort` ("name"|"created"), `page` (int), `limit` (int, max 100)

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "acme-corp",
      "legal_name": "Acme Corporation Ltd",
      "display_name": "Acme Corp",
      "org_type": "corporate",
      "status": "active",
      "is_verified": true,
      "description": "Infrastructure company",
      "logo_url": "https://...",
      "website_url": "https://...",
      "support_email": "info@acme.com",
      "support_phone": "+255...",
      "country_code": "TZ",
      "timezone": "Africa/Dar_es_Salaam",
      "registration_number": "REG-12345",
      "tax_id": "TAX-456",
      "max_members": 50,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 142,
  "page": 1,
  "limit": 20,
  "pages": 8
}
```

---

### POST `/api/v1/orgs`

**Summary:** Create an organisation. Caller becomes OWNER. Starts as PENDING_VERIFICATION.

**Auth:** Bearer JWT (verified email required)

**Request Body:**
```json
{
  "legal_name": "Acme Corporation Ltd",
  "display_name": "Acme Corp",
  "slug": "acme-corp",
  "org_type": "corporate",
  "description": "Infrastructure company",
  "logo_url": null,
  "website_url": null,
  "support_email": "info@acme.com",
  "support_phone": "+255...",
  "country_code": "TZ",
  "timezone": "Africa/Dar_es_Salaam",
  "registration_number": "REG-12345",
  "tax_id": null,
  "max_members": 50
}
```

**Success Response (201):** OrgResponse (same as items above)

**Error Codes:** `401`, `403` Email not verified, `409` Slug already taken

---

### GET `/api/v1/orgs/{org_id}`

**Summary:** Get organisation details.

**Auth:** Bearer JWT (active user)

**Success Response (200):** OrgResponse

**Error Codes:** `401`, `404`

---

### PATCH `/api/v1/orgs/{org_id}`

**Summary:** Update organisation profile (PATCH semantics). Requires ADMIN role.

**Auth:** Org Role (ADMIN)

**Request Body:** Same fields as CreateOrgRequest, all optional.

**Success Response (200):** OrgResponse

**Error Codes:** `401`, `403`, `404`, `409` Slug taken

---

### DELETE `/api/v1/orgs/{org_id}`

**Summary:** Deactivate (close) organisation. OWNER only. Reversible by platform admin.

**Auth:** Org Role (OWNER)

**Query Parameters:** `reason` (string, optional)

**Success Response (200):**
```json
{ "message": "Organisation 'acme-corp' has been deactivated." }
```

**Error Codes:** `401`, `403`, `404`

---

### POST `/api/v1/orgs/{org_id}/verify`

**Summary:** [Admin] Verify a pending organisation.

**Auth:** Platform Role (admin)

**Success Response (200):** OrgResponse (status = "active", is_verified = true)

---

### POST `/api/v1/orgs/{org_id}/suspend`

**Summary:** [Admin] Suspend an organisation.

**Auth:** Platform Role (admin)

**Request Body:**
```json
{ "reason": "Violation of platform policy" }
```

**Success Response (200):**
```json
{ "message": "Organisation {org_id} has been suspended." }
```

---

### POST `/api/v1/orgs/{org_id}/ban`

**Summary:** [Admin] Permanently ban an organisation.

**Auth:** Platform Role (admin)

**Request Body:**
```json
{ "reason": "Repeated violations" }
```

**Success Response (200):**
```json
{ "message": "Organisation {org_id} has been banned." }
```

---

### POST `/api/v1/orgs/{org_id}/members`

**Summary:** Add a platform user as a member directly (no invite flow). Requires ADMIN.

**Auth:** Org Role (ADMIN)

**Request Body:**
```json
{
  "user_id": "uuid",
  "org_role": "manager"                    // "member" | "manager" | "admin" (not "owner")
}
```

**Success Response (201):**
```json
{
  "user_id": "uuid",
  "organisation_id": "uuid",
  "org_role": "manager",
  "status": "active",
  "joined_at": "2025-06-10T14:22:00Z"
}
```

**Error Codes:** `403`, `404` User not found, `409` Already a member

---

### DELETE `/api/v1/orgs/{org_id}/members/{user_id}`

**Summary:** Remove a member. Cannot remove OWNER. Requires ADMIN.

**Auth:** Org Role (ADMIN)

**Success Response (200):**
```json
{ "message": "User {user_id} removed from organisation." }
```

**Error Codes:** `403`, `404`

---

### PATCH `/api/v1/orgs/{org_id}/members/{user_id}/role`

**Summary:** Change a member's role (cannot assign OWNER; use transfer-ownership).

**Auth:** Org Role (ADMIN)

**Request Body:**
```json
{ "org_role": "admin" }
```

**Success Response (200):** MemberResponse

**Error Codes:** `400` Cannot assign OWNER, `403`, `404`

---

### POST `/api/v1/orgs/{org_id}/transfer-ownership`

**Summary:** Transfer OWNER role to another active member. Current owner becomes ADMIN.

**Auth:** Org Role (OWNER)

**Request Body:**
```json
{ "new_owner_id": "uuid" }
```

**Success Response (200):**
```json
{ "message": "Ownership transferred to user {uuid}." }
```

**Error Codes:** `403`, `404` New owner is not an active member

---

### POST `/api/v1/orgs/{org_id}/invites`

**Summary:** Send an organisation invite. Requires MANAGER.

**Auth:** Org Role (MANAGER)

**Request Body:**
```json
{
  "invited_role": "member",
  "invited_email": "bob@example.com",      // string | null
  "invited_user_id": null,                 // UUID | null
  "message": "Welcome aboard!"            // string | null, optional
}
```

**Success Response (201):** InviteResponse

**Error Codes:** `400`, `403`, `409` Pending invite already exists

---

### POST `/api/v1/orgs/invites/{invite_id}/accept`

**Summary:** Accept a pending organisation invite.

**Auth:** Bearer JWT (active user)

**Success Response (200):** MemberResponse

**Error Codes:** `401`, `404` Invite not found/expired, `409` Already a member

---

### POST `/api/v1/orgs/invites/{invite_id}/decline`

**Summary:** Decline a pending invite.

**Auth:** Bearer JWT (active user)

**Success Response (200):**
```json
{ "message": "Invite declined." }
```

---

### DELETE `/api/v1/orgs/{org_id}/invites/{invite_id}`

**Summary:** Cancel a pending invite. Requires MANAGER.

**Auth:** Org Role (MANAGER)

**Success Response (200):**
```json
{ "message": "Invite {invite_id} cancelled." }
```

---

### POST `/api/v1/orgs/{org_id}/logo`

**Summary:** Upload organisation logo. JPEG, PNG, WebP, SVG. Max 5 MB. Requires MANAGER.

**Auth:** Org Role (MANAGER)

**Request Body:** `multipart/form-data` with `file` field

**Success Response (200):**
```json
{
  "org_id": "uuid",
  "logo_url": "https://minio.riviwa.com/images/organisations/{org_id}/logo.png"
}
```

**Error Codes:** `400` Invalid file type/size, `403`, `404`

---

## 1.7 Org Extended

*All routes are under `/api/v1/orgs/{org_id}/...`*

### Locations

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| POST | `/{org_id}/locations` | Add a physical location | Org ADMIN |
| GET | `/{org_id}/locations` | List all locations | Bearer JWT |
| PATCH | `/{org_id}/locations/{location_id}` | Update a location | Org ADMIN |
| DELETE | `/{org_id}/locations/{location_id}` | Delete a location | Org ADMIN |
| GET | `/{org_id}/branches/{branch_id}/locations` | List locations for a branch | Bearer JWT |

**Create Location Request Body:**
```json
{
  "location_type": "headquarters",
  "branch_id": null,
  "label": "Head Office",
  "line1": "123 Main Street",
  "line2": null,
  "city": "Dar es Salaam",
  "state": null,
  "postal_code": "11000",
  "country_code": "TZ",
  "region": "Dar es Salaam",
  "latitude": -6.7924,
  "longitude": 39.2083,
  "is_primary": true
}
```

### Content

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| GET | `/{org_id}/content` | Get org content profile | Bearer JWT |
| PUT | `/{org_id}/content` | Create or update content profile | Org ADMIN |

**Upsert Content Request:**
```json
{
  "vision": "...", "mission": "...", "objectives": "...",
  "global_policy": "...", "terms_of_use": "...", "privacy_policy": "..."
}
```

### Org-level FAQs

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| POST | `/{org_id}/faqs` | Add an FAQ | Org MANAGER |
| GET | `/{org_id}/faqs` | List FAQs | Bearer JWT |
| PATCH | `/{org_id}/faqs/{faq_id}` | Update an FAQ | Org MANAGER |
| DELETE | `/{org_id}/faqs/{faq_id}` | Delete an FAQ | Org MANAGER |

### Branches

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| POST | `/{org_id}/branches` | Create a branch or sub-branch | Org ADMIN |
| GET | `/{org_id}/branches` | List top-level branches | Bearer JWT |
| GET | `/{org_id}/branches/{branch_id}/children` | List child branches | Bearer JWT |
| GET | `/{org_id}/branches/{branch_id}/tree` | Get all branch IDs in subtree (recursive) | Bearer JWT |
| PATCH | `/{org_id}/branches/{branch_id}` | Update a branch | Org ADMIN |
| POST | `/{org_id}/branches/{branch_id}/close` | Close a branch | Org ADMIN |
| DELETE | `/{org_id}/branches/{branch_id}` | Delete a branch | Org ADMIN |

### Branch Managers

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| POST | `/{org_id}/branches/{branch_id}/managers` | Add branch manager | Org ADMIN |
| GET | `/{org_id}/branches/{branch_id}/managers` | List branch managers | Bearer JWT |
| DELETE | `/{org_id}/branches/{branch_id}/managers/{user_id}` | Remove branch manager | Org ADMIN |

### Services

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| POST | `/{org_id}/services` | Create a service | Org ADMIN |
| GET | `/{org_id}/services` | List services | Bearer JWT |
| GET | `/{org_id}/services/{service_id}` | Get service detail | Bearer JWT |
| PATCH | `/{org_id}/services/{service_id}` | Update service | Org ADMIN |
| POST | `/{org_id}/services/{service_id}/publish` | Publish service | Org ADMIN |
| POST | `/{org_id}/services/{service_id}/archive` | Archive service | Org ADMIN |
| POST | `/{org_id}/branches/{branch_id}/services/{service_id}/link` | Link service to branch | Org ADMIN |
| DELETE | `/{org_id}/branches/{branch_id}/services/{service_id}/link` | Unlink service from branch | Org ADMIN |

### Service Personnel, Locations, Media, FAQs, Policies

All follow the same CRUD pattern under `/{org_id}/services/{service_id}/...`. Require Org ADMIN for writes, Bearer JWT for reads.

---

## 1.8 Projects

*All routes under `/api/v1/orgs/{org_id}/projects/...`*

### Projects

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| POST | `/{org_id}/projects` | Create execution project (PLANNING status) | Org ADMIN |
| GET | `/{org_id}/projects` | List projects | Org MANAGER |
| GET | `/{org_id}/projects/{project_id}` | Project detail with stages and in-charges | Org MANAGER |
| PATCH | `/{org_id}/projects/{project_id}` | Update project fields | Org ADMIN |
| POST | `/{org_id}/projects/{project_id}/activate` | PLANNING -> ACTIVE (publishes Kafka event) | Org OWNER |
| POST | `/{org_id}/projects/{project_id}/pause` | ACTIVE -> PAUSED | Org OWNER |
| POST | `/{org_id}/projects/{project_id}/resume` | PAUSED -> ACTIVE | Org OWNER |
| POST | `/{org_id}/projects/{project_id}/complete` | -> COMPLETED | Org OWNER |
| DELETE | `/{org_id}/projects/{project_id}` | Soft-delete -> CANCELLED | Org OWNER |
| POST | `/{org_id}/projects/{project_id}/cover-image` | Upload cover image (multipart) | Org MANAGER |

**Query params for list:** `status` (planning|active|paused|completed|cancelled), `branch_id`, `skip`, `limit`

### Project In-charges

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| POST | `/{org_id}/projects/{project_id}/in-charges` | Assign person to leadership team | Org ADMIN |
| GET | `/{org_id}/projects/{project_id}/in-charges` | List leadership team | Org MANAGER |
| DELETE | `/{org_id}/projects/{project_id}/in-charges/{user_id}?role_title=...` | Relieve in-charge | Org ADMIN |

### Stages

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| POST | `/{org_id}/projects/{project_id}/stages` | Add a stage | Org ADMIN |
| GET | `/{org_id}/projects/{project_id}/stages` | List stages in order | Org MANAGER |
| GET | `/{org_id}/projects/{project_id}/stages/{stage_id}` | Stage detail | Org MANAGER |
| PATCH | `/{org_id}/projects/{project_id}/stages/{stage_id}` | Update stage | Org ADMIN |
| POST | `.../stages/{stage_id}/activate` | PENDING -> ACTIVE | Org ADMIN |
| POST | `.../stages/{stage_id}/complete` | ACTIVE -> COMPLETED | Org ADMIN |
| POST | `.../stages/{stage_id}/skip` | PENDING -> SKIPPED | Org ADMIN |

### Stage In-charges

Same pattern as project in-charges under `.../stages/{stage_id}/in-charges`. Org ADMIN for writes, Org MANAGER for reads.

### Sub-projects

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| POST | `.../stages/{stage_id}/subprojects` | Create sub-project in stage | Org ADMIN |
| GET | `.../stages/{stage_id}/subprojects` | List sub-projects for a stage | Org MANAGER |
| GET | `.../subprojects/{subproject_id}` | Sub-project detail with children | Org MANAGER |
| GET | `.../subprojects/{subproject_id}/tree` | All IDs in subtree (recursive) | Org MANAGER |
| PATCH | `.../subprojects/{subproject_id}` | Update sub-project | Org ADMIN |
| DELETE | `.../subprojects/{subproject_id}` | Soft-delete -> CANCELLED | Org ADMIN |

### Sub-project In-charges

Same pattern under `.../subprojects/{subproject_id}/in-charges`.

---

## 1.9 Checklists

Checklists are available at three levels with identical endpoint patterns:

- **Project:** `/api/v1/orgs/{org_id}/projects/{project_id}/checklist`
- **Stage:** `/api/v1/orgs/{org_id}/projects/{project_id}/stages/{stage_id}/checklist`
- **Sub-project:** `/api/v1/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}/checklist`

### Checklist CRUD (same pattern for each level)

| Method | Path suffix | Summary | Auth |
|--------|-------------|---------|------|
| POST | `/checklist` | Add a checklist item | Org MANAGER |
| GET | `/checklist` | List items + progress summary | Org MEMBER |
| GET | `/checklist/progress` | Progress summary only (lightweight) | Org MEMBER |
| GET | `/checklist/{item_id}` | Get a single item | Org MEMBER |
| PATCH | `/checklist/{item_id}` | Update item | Org MANAGER |
| POST | `/checklist/{item_id}/done` | Mark item as DONE | Org MANAGER |
| PUT | `/checklist/reorder` | Bulk reorder (drag-and-drop) | Org MANAGER |
| DELETE | `/checklist/{item_id}` | Soft-delete | Org MANAGER |

**Create Checklist Item Request:**
```json
{
  "title": "Complete environmental assessment",
  "description": "Full EIA report",
  "category": "compliance",
  "assigned_to": "user-uuid",
  "due_date": "2025-09-01",
  "priority": "high",
  "display_order": 1
}
```

**Mark Done Request:**
```json
{
  "completion_note": "Completed ahead of schedule",
  "completion_evidence_url": "https://...",
  "completion_date": "2025-08-15"
}
```

**List query params:** `status` (pending|in_progress|done|skipped|blocked), `category`, `assigned_to`, `skip`, `limit`

### Checklist Performance Reports

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| GET | `/{org_id}/projects/{project_id}/checklist-performance` | Project-level performance report | Org MEMBER |
| GET | `/{org_id}/checklist-performance` | Org-level portfolio performance | Org MEMBER |
| GET | `.../stages/{stage_id}/checklist-performance` | Stage-level performance | Org MEMBER |
| GET | `.../subprojects/{subproject_id}/checklist-performance` | Sub-project performance | Org MEMBER |

**Query params:** `entity_type`, `status`, `overdue_only` (bool), `region`, `lga`

---

## 1.10 Admin Dashboard

*All routes under `/api/v1/admin/...`. All require Platform Role (admin) unless noted.*

### Platform Overview

| Method | Path | Summary |
|--------|------|---------|
| GET | `/admin/dashboard/summary` | Platform overview KPIs (single call) |

**Response:**
```json
{
  "generated_at": "2025-06-10T14:22:00Z",
  "users": { "total": 5000, "active": 4200, "pending": 100, "suspended": 50, "banned": 10, "new_this_month": 200, "new_today": 12 },
  "organisations": { "total": 150, "active": 120, "pending_verification": 15, "suspended": 5, "banned": 2, "deactivated": 8 },
  "projects": { "total": 45, "active": 30, "by_status": {"planning": 5, "active": 30, "paused": 3, "completed": 7} },
  "security": { "high_risk_fraud_flags": 3 }
}
```

### User Management

| Method | Path | Summary |
|--------|------|---------|
| GET | `/admin/users` | List all users (paginated, filterable) |
| GET | `/admin/users/growth` | Daily registration trend (chart data) |
| GET | `/admin/users/status-breakdown` | Users by status (pie chart data) |
| GET | `/admin/users/{user_id}` | Single user admin detail |
| POST | `/admin/users/{user_id}/suspend` | Suspend user |
| POST | `/admin/users/{user_id}/ban` | Ban user |
| POST | `/admin/users/{user_id}/reactivate` | Reactivate user |

### Organisation Management

| Method | Path | Summary |
|--------|------|---------|
| GET | `/admin/organisations` | List all orgs (paginated, filterable) |
| GET | `/admin/organisations/pending` | Verification queue |
| GET | `/admin/organisations/breakdown` | Type x status chart data |
| GET | `/admin/organisations/growth` | Daily creation trend |
| GET | `/admin/organisations/member-distribution` | Platform-wide member role distribution |
| GET | `/admin/organisations/{org_id}` | Single org admin detail |
| POST | `/admin/organisations/{org_id}/verify` | Verify org |
| POST | `/admin/organisations/{org_id}/suspend` | Suspend org |
| POST | `/admin/organisations/{org_id}/ban` | Ban org |

### Projects

| Method | Path | Summary |
|--------|------|---------|
| GET | `/admin/projects` | Cross-org project list |
| GET | `/admin/projects/summary` | By status + sector chart data |

### Security / Fraud

| Method | Path | Summary |
|--------|------|---------|
| GET | `/admin/security/fraud` | Fraud assessment summary by risk level |
| GET | `/admin/security/flagged-users` | High-risk accounts list |

### Staff Management

| Method | Path | Summary | Auth |
|--------|------|---------|------|
| GET | `/admin/staff` | List platform staff | Platform admin |
| POST | `/admin/staff/{user_id}/roles` | Assign platform role | **Platform super_admin** |
| DELETE | `/admin/staff/{user_id}/roles/{role_name}` | Revoke platform role | **Platform super_admin** |

**Assign Role Request:**
```json
{ "role": "moderator" }   // "moderator" | "admin" | "super_admin"
```

### Other

| Method | Path | Summary |
|--------|------|---------|
| GET | `/admin/checklist-health` | Platform-wide checklist completion stats |
| GET | `/admin/recent-actions` | Recent moderation actions log |

---

## 1.11 Webhooks

### POST `/api/v1/webhooks/id-verification`

**Summary:** ID verification provider callback (Onfido, Stripe Identity). Always returns 200.

**Auth:** None (public; validated via `X-Webhook-Signature` HMAC-SHA256)

**Request Body:** Provider-specific JSON payload with `event_type` and `result` fields.

**Success Response (200):**
```json
{ "message": "Webhook processed." }
```

**Error Codes:** Always returns 200 (by design -- errors are logged internally)

---

# 2. Feedback Service

## Enums Reference

| Enum | Values |
|------|--------|
| FeedbackType | `grievance`, `suggestion`, `applause` |
| FeedbackStatus | `submitted`, `acknowledged`, `in_review`, `escalated`, `resolved`, `appealed`, `actioned`, `noted`, `dismissed`, `closed` |
| FeedbackPriority | `critical`, `high`, `medium`, `low` |
| GRMLevel | `ward`, `lga_piu`, `pcu`, `tarura_wbcu`, `tanroads`, `world_bank` |
| FeedbackChannel | `sms`, `whatsapp`, `whatsapp_voice`, `phone_call`, `mobile_app`, `web_portal`, `in_person`, `paper_form`, `email`, `public_meeting`, `notice_box`, `other` |
| SubmissionMethod | `self_service`, `ai_conversation`, `officer_recorded` |
| FeedbackCategory | `compensation`, `resettlement`, `land_acquisition`, `construction_impact`, `traffic`, `worker_rights`, `safety_hazard`, `environmental`, `engagement`, `design_issue`, `project_delay`, `corruption`, `communication`, `safety`, `accessibility`, `other`, ... |

---

## 2.1 Feedback

### POST `/api/v1/feedback`

**Summary:** Submit feedback (grievance / suggestion / applause).

**Auth:** Bearer JWT (optional -- anonymous submissions allowed)

**Request Body:**
```json
{
  "feedback_type": "grievance",
  "category": "compensation",
  "subject": "Unfair compensation for land",
  "description": "The offered amount does not reflect market value...",
  "project_id": "uuid",
  "channel": "mobile_app",
  "submission_method": "self_service",
  "is_anonymous": false,
  "submitter_name": "John Doe",
  "submitter_phone": "+255712345678",
  "issue_location": { "region": "Dar es Salaam", "district": "Ilala", "lga": "Ilala MC", "ward": "Jangwani" },
  "submitted_by_stakeholder_id": "uuid",
  "priority": "high"
}
```

**Success Response (201):** Feedback record object

**Error Codes:** `400` Validation error, `404` Project not found

---

### GET `/api/v1/feedback`

**Summary:** List feedback records. Staff only.

**Auth:** StaffDep (Bearer JWT, project staff)

**Query Parameters:** `project_id`, `feedback_type`, `status`, `priority`, `current_level`, `category`, `lga`, `is_anonymous`, `submission_method`, `channel`, `submitted_by_stakeholder_id`, `assigned_committee_id`, `skip`, `limit`

**Success Response (200):**
```json
{
  "items": [ { /* feedback record */ } ],
  "count": 42
}
```

---

### GET `/api/v1/feedback/{feedback_id}`

**Summary:** Feedback detail with full history (actions, escalations, resolution, appeal).

**Auth:** StaffDep

**Success Response (200):**
```json
{
  "id": "uuid",
  "unique_ref": "GRV-2025-0001",
  "feedback_type": "grievance",
  "status": "in_review",
  "actions": [ { "id": "uuid", "action_type": "investigation", "description": "...", "performed_at": "..." } ],
  "escalations": [ { "from_level": "ward", "to_level": "lga_piu", "reason": "...", "escalated_at": "..." } ],
  "resolution": null,
  "appeal": null
}
```

---

### PATCH `/api/v1/feedback/{feedback_id}/acknowledge`

**Summary:** Acknowledge receipt of feedback.

**Auth:** StaffDep

**Request Body:**
```json
{
  "acknowledgement_note": "We have received your grievance...",
  "priority": "high",
  "target_resolution_date": "2025-07-15"
}
```

**Success Response (200):** Updated feedback record

---

### PATCH `/api/v1/feedback/{feedback_id}/assign`

**Summary:** Assign feedback to a staff member or committee.

**Auth:** StaffDep

**Request Body:**
```json
{
  "assigned_to_user_id": "uuid",
  "assigned_committee_id": "uuid"
}
```

---

### POST `/api/v1/feedback/{feedback_id}/escalate`

**Summary:** Escalate to next GRM level.

**Auth:** StaffDep

**Request Body:**
```json
{
  "to_level": "lga_piu",
  "reason": "Issue requires higher authority approval",
  "notes": "Ward committee unable to resolve within mandate"
}
```

---

### POST `/api/v1/feedback/{feedback_id}/resolve`

**Summary:** Record resolution for feedback.

**Auth:** StaffDep

**Request Body:**
```json
{
  "resolution_summary": "Compensation amount revised to market value.",
  "response_method": "meeting",
  "grievant_satisfied": true,
  "grievant_response": "Accepted the revised amount"
}
```

---

### POST `/api/v1/feedback/{feedback_id}/appeal`

**Summary:** File appeal against a resolution.

**Auth:** StaffDep

**Request Body:**
```json
{
  "appeal_grounds": "The revised compensation is still below market value",
  "requested_level": "pcu"
}
```

---

### PATCH `/api/v1/feedback/{feedback_id}/close`

**Summary:** Close feedback (final state).

**Auth:** StaffDep

**Request Body:**
```json
{ "closure_note": "All actions completed." }
```

---

### PATCH `/api/v1/feedback/{feedback_id}/dismiss`

**Summary:** Dismiss feedback (out of scope, duplicate, unfounded).

**Auth:** StaffDep

**Request Body:**
```json
{ "dismiss_reason": "Duplicate of GRV-2025-0003" }
```

---

## 2.2 Actions

### POST `/api/v1/feedback/{feedback_id}/actions`

**Summary:** Log an action taken on a feedback item.

**Auth:** StaffDep

**Request Body:**
```json
{
  "action_type": "investigation",
  "description": "Site visit conducted to assess damage",
  "response_method": "site_visit",
  "response_summary": "Confirmed structural damage to property",
  "is_internal": false
}
```

**Success Response (201):** Action record

---

### GET `/api/v1/feedback/{feedback_id}/actions`

**Summary:** Get the action log for a feedback item.

**Auth:** StaffDep

**Success Response (200):**
```json
{
  "items": [ { "id": "uuid", "action_type": "investigation", "description": "...", "performed_at": "..." } ]
}
```

---

## 2.3 Categories

### POST `/api/v1/categories`

**Summary:** Create a feedback category. Staff only.

**Auth:** StaffDep

**Request Body:**
```json
{
  "name": "Road Safety",
  "feedback_type": "grievance",
  "project_id": "uuid",
  "source": "manual",
  "description": "Issues related to road safety during construction"
}
```

---

### GET `/api/v1/categories`

**Summary:** List feedback categories.

**Auth:** StaffDep

**Query Parameters:** `project_id`, `feedback_type`, `source`, `status`, `include_global` (bool), `skip`, `limit`

---

### GET `/api/v1/categories/summary`

**Summary:** Category counts for a project (dashboard overview).

**Auth:** StaffDep

**Query Parameters:** `project_id` (required), `feedback_type`, `from_date`, `to_date`

---

### GET `/api/v1/categories/{category_id}`

**Summary:** Category detail.

**Auth:** StaffDep

---

### PATCH `/api/v1/categories/{category_id}`

**Summary:** Update category.

**Auth:** StaffDep

---

### GET `/api/v1/categories/{category_id}/rate`

**Summary:** Feedback rate for a category -- real-time and by period.

**Auth:** StaffDep

**Query Parameters:** `project_id`, `stage_id`, `period` ("week"|"month"|"day"), `from_date`, `to_date`, `feedback_type`, `status`, `open_only`, `priority`, `current_level`, `lga`, `ward`, `is_anonymous`, `submitted_by_stakeholder_id`, `assigned_committee_id`, `assigned_to_user_id`

---

### POST `/api/v1/categories/{category_id}/approve`

**Summary:** Approve an ML-suggested category.

**Auth:** StaffDep

---

### POST `/api/v1/categories/{category_id}/reject`

**Summary:** Reject an ML-suggested category.

**Auth:** StaffDep

---

### POST `/api/v1/categories/{category_id}/deactivate`

**Summary:** Deactivate a category.

**Auth:** StaffDep

---

### POST `/api/v1/categories/{category_id}/merge`

**Summary:** Merge this category into another.

**Auth:** StaffDep

**Request Body:**
```json
{ "target_category_id": "uuid" }
```

---

### POST `/api/v1/feedback/{feedback_id}/classify`

**Summary:** Run ML classification to assign or suggest a category.

**Auth:** StaffDep

---

### PATCH `/api/v1/feedback/{feedback_id}/recategorise`

**Summary:** Manually reassign category to a feedback submission.

**Auth:** StaffDep

**Request Body:**
```json
{ "category_id": "uuid" }
```

---

## 2.4 Channel Sessions

### POST `/api/v1/channel-sessions`

**Summary:** Start a two-way channel session (LLM conversation).

**Auth:** StaffDep

**Request Body:**
```json
{
  "phone_number": "+255712345678",
  "channel": "sms",
  "project_id": "uuid",
  "language": "sw"
}
```

**Success Response (201):** Session record

---

### GET `/api/v1/channel-sessions`

**Summary:** List channel sessions.

**Auth:** StaffDep

**Query Parameters:** `project_id`, `channel`, `status`, `skip`, `limit`

---

### GET `/api/v1/channel-sessions/{session_id}`

**Summary:** Session detail with full transcript (all turns).

**Auth:** StaffDep

---

### POST `/api/v1/channel-sessions/{session_id}/message`

**Summary:** Add a PAP message turn and get the LLM reply.

**Auth:** StaffDep

**Request Body:**
```json
{ "message": "I want to report damage to my property" }
```

---

### POST `/api/v1/channel-sessions/{session_id}/submit`

**Summary:** Force-submit feedback from current extracted data.

**Auth:** StaffDep

---

### POST `/api/v1/channel-sessions/{session_id}/abandon`

**Summary:** Mark session as abandoned.

**Auth:** StaffDep

**Request Body:**
```json
{ "reason": "PAP stopped responding" }
```

---

### POST `/api/v1/webhooks/sms` (hidden from schema)

**Summary:** Inbound SMS webhook (Africa's Talking / Twilio).

**Auth:** None (webhook)

---

### POST `/api/v1/webhooks/whatsapp` (hidden from schema)

**Summary:** Inbound WhatsApp webhook (Meta Cloud API). Handles text, voice notes, images.

**Auth:** None (webhook)

---

### GET `/api/v1/webhooks/whatsapp` (hidden from schema)

**Summary:** WhatsApp webhook verification (Meta hub.challenge).

**Auth:** None (Meta verification token)

---

## 2.5 GRM Committees

### POST `/api/v1/committees`

**Summary:** Create a Grievance Handling Committee (GHC).

**Auth:** StaffDep

**Request Body:**
```json
{
  "name": "Jangwani Ward GHC",
  "level": "ward",
  "project_id": "uuid",
  "lga": "Ilala",
  "org_sub_project_id": "uuid"
}
```

---

### GET `/api/v1/committees`

**Summary:** List GHCs.

**Auth:** StaffDep

**Query Parameters:** `project_id`, `level`, `lga`, `org_sub_project_id`, `stakeholder_id`, `active_only` (bool)

---

### PATCH `/api/v1/committees/{committee_id}`

**Summary:** Update committee details.

**Auth:** StaffDep

---

### POST `/api/v1/committees/{committee_id}/stakeholders/{stakeholder_id}`

**Summary:** Add a stakeholder group to this committee's coverage.

**Auth:** StaffDep

---

### DELETE `/api/v1/committees/{committee_id}/stakeholders/{stakeholder_id}`

**Summary:** Remove a stakeholder group from coverage.

**Auth:** StaffDep

---

### POST `/api/v1/committees/{committee_id}/members`

**Summary:** Add member to GHC.

**Auth:** StaffDep

**Request Body:**
```json
{
  "user_id": "uuid",
  "role": "chairperson",
  "name": "Jane Doe"
}
```

---

### DELETE `/api/v1/committees/{committee_id}/members/{user_id}`

**Summary:** Remove member from GHC.

**Auth:** StaffDep

---

## 2.6 PAP Portal

### GET `/api/v1/my/feedback`

**Summary:** List all my feedback submissions (PAP view).

**Auth:** PAPDep (Bearer JWT)

**Query Parameters:** `feedback_type`, `status`, `project_id`, `skip`, `limit`

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "unique_ref": "GRV-2025-0001",
      "feedback_type": "grievance",
      "category": "compensation",
      "subject": "Unfair compensation",
      "channel": "mobile_app",
      "status": "in_review",
      "status_label": "Under investigation",
      "current_level": "ward",
      "priority": "high",
      "submitted_at": "2025-06-01T10:00:00Z",
      "resolved_at": null,
      "project_id": "uuid"
    }
  ],
  "count": 5
}
```

---

### GET `/api/v1/my/feedback/summary`

**Summary:** My feedback summary -- counts for dashboard widget.

**Auth:** PAPDep

**Query Parameters:** `project_id` (optional)

**Success Response (200):**
```json
{
  "total": 5,
  "open": 3,
  "resolved": 1,
  "closed": 1,
  "by_type": [ {"type": "grievance", "count": 3}, {"type": "suggestion", "count": 2} ],
  "by_status": [ {"status": "submitted", "label": "Received -- awaiting acknowledgement", "count": 1} ],
  "pending_escalation_requests": 1
}
```

---

### GET `/api/v1/my/feedback/{feedback_id}`

**Summary:** Track a specific submission -- full handling history (public-safe view).

**Auth:** PAPDep

**Success Response (200):**
```json
{
  "id": "uuid",
  "unique_ref": "GRV-2025-0001",
  "feedback_type": "grievance",
  "category": "compensation",
  "subject": "Unfair compensation",
  "description": "...",
  "channel": "mobile_app",
  "status": "in_review",
  "status_label": "Under investigation",
  "current_level": "ward",
  "priority": "high",
  "submitted_at": "2025-06-01T10:00:00Z",
  "acknowledged_at": "2025-06-02T08:00:00Z",
  "target_resolution_date": "2025-07-01T00:00:00Z",
  "hours_open": 216.5,
  "public_actions": [ { "action_type": "investigation", "description": "...", "performed_at": "..." } ],
  "escalation_trail": [],
  "resolution": null,
  "appeal": null,
  "escalation_requests": [],
  "can_request_escalation": true,
  "can_appeal": false,
  "can_add_comment": true
}
```

---

### POST `/api/v1/my/feedback`

**Summary:** Submit a new grievance, suggestion, or applause (PAP self-service).

**Auth:** PAPDep

**Request Body:**
```json
{
  "feedback_type": "grievance",
  "category": "compensation",
  "subject": "Unfair compensation for land",
  "description": "The offered amount does not reflect market value...",
  "project_id": "uuid",
  "is_anonymous": false,
  "issue_location": { "region": "Dar es Salaam", "lga": "Ilala MC", "ward": "Jangwani" }
}
```

**Success Response (201):**
```json
{
  "id": "uuid",
  "unique_ref": "GRV-2025-0042",
  "status": "submitted",
  "status_label": "Received -- awaiting acknowledgement",
  "message": "Your grievance has been submitted successfully. Reference number: GRV-2025-0042. You will be notified when PIU acknowledges receipt."
}
```

---

### POST `/api/v1/my/feedback/{feedback_id}/escalation-request`

**Summary:** Request PIU to escalate your grievance to a higher GRM level.

**Auth:** PAPDep

**Request Body:**
```json
{
  "reason": "No response after 30 days",
  "requested_level": "lga_piu"
}
```

**Success Response (201):**
```json
{
  "id": "uuid",
  "status": "pending",
  "message": "Your escalation request has been submitted. PIU will review it..."
}
```

---

### POST `/api/v1/my/feedback/{feedback_id}/appeal`

**Summary:** File a formal appeal against an unsatisfactory resolution.

**Auth:** PAPDep

**Request Body:**
```json
{ "appeal_grounds": "The revised compensation is still below market value" }
```

**Success Response (201):**
```json
{
  "appeal_id": "uuid",
  "status": "appealed",
  "now_at_level": "lga_piu",
  "message": "Your appeal has been filed. Your case has been escalated to LGA PIU for review..."
}
```

---

### POST `/api/v1/my/feedback/{feedback_id}/add-comment`

**Summary:** Add a follow-up comment to your submission.

**Auth:** PAPDep

**Request Body:**
```json
{ "comment": "I wanted to add that the construction damage is getting worse" }
```

**Success Response (201):**
```json
{
  "message": "Your comment has been added and is visible to PIU staff.",
  "action_id": "uuid"
}
```

---

### GET `/api/v1/escalation-requests`

**Summary:** [Staff] List PAP escalation requests.

**Auth:** StaffDep

**Query Parameters:** `project_id`, `status` (default "pending"), `skip`, `limit`

---

### POST `/api/v1/escalation-requests/{request_id}/approve`

**Summary:** [Staff] Approve a PAP escalation request.

**Auth:** StaffDep

---

### POST `/api/v1/escalation-requests/{request_id}/reject`

**Summary:** [Staff] Reject a PAP escalation request with explanation.

**Auth:** StaffDep

**Request Body:**
```json
{ "reviewer_notes": "The case is still within the ward committee's mandate to resolve." }
```

---

## 2.7 Reports

*All reports under `/api/v1/reports/...`. All require StaffDep auth. All support `format` query param: `json` (default) | `pdf` | `xlsx` | `csv`.*

### GET `/api/v1/reports/performance`

**Summary:** Overall performance dashboard -- all feedback types. Exportable.

**Query Parameters:** `project_id`, `stage_id`, `from_date`, `to_date`, `region`, `district`, `lga`, `ward`, `mtaa`, `priority`, `channel`, `submission_method`, `format`

---

### GET `/api/v1/reports/grievances`

**Summary:** Grievance performance page. Exportable.

**Query Parameters:** Same as performance + `status`, `time_unit` ("seconds"|"minutes"|"hours"|"days"|"custom"), `custom_seconds`

---

### GET `/api/v1/reports/suggestions`

**Summary:** Suggestion performance page. Exportable.

**Query Parameters:** Same as grievances

---

### GET `/api/v1/reports/suggestion-performance`

**Summary:** Comprehensive suggestion performance report -- volume, rates, response times, implementation tracking, location/category/stakeholder/channel breakdowns, daily trend.

**Query Parameters:** `project_id`, `stage_id`, `subproject_id`, `stakeholder_id`, `category`, `from_date`, `to_date`, `region`, `district`, `lga`, `ward`, `mtaa`, `channel`, `submission_method`, `status`, `time_unit`, `custom_seconds`

---

### GET `/api/v1/reports/suggestions/detailed`

**Summary:** Detailed suggestion performance -- rate, category, location, stakeholder, implementation time.

**Query Parameters:** Same as suggestion-performance + `group_location_by` ("region"|"district"|"lga"|"ward"|"mtaa"), `format`

---

### GET `/api/v1/reports/applause`

**Summary:** Applause performance page. Exportable.

**Query Parameters:** `project_id`, `stage_id`, `from_date`, `to_date`, location filters, `channel`, `submission_method`, `format`

---

### GET `/api/v1/reports/applause-performance`

**Summary:** Comprehensive applause performance report with flexible time units.

**Query Parameters:** Same as suggestion-performance + `status`, `time_unit`, `custom_seconds`

---

### GET `/api/v1/reports/channels`

**Summary:** Breakdown by intake channel and submission method. Exportable.

**Query Parameters:** `project_id`, `from_date`, `to_date`, `feedback_type`, `format`

---

### GET `/api/v1/reports/grievance-log`

**Summary:** Full grievance log (SEP Annex 5/6 format). Exportable.

**Query Parameters:** `project_id`, `from_date`, `to_date`, location filters, `priority`, `channel`, `status`, `skip`, `limit`, `format`

---

### GET `/api/v1/reports/suggestion-log`

**Summary:** Full suggestion log. Exportable.

**Query Parameters:** Same as grievance-log minus `priority`

---

### GET `/api/v1/reports/applause-log`

**Summary:** Full applause log. Exportable.

**Query Parameters:** `project_id`, `from_date`, `to_date`, location filters, `channel`, `skip`, `limit`, `format`

---

### GET `/api/v1/reports/summary`

**Summary:** Feedback count summary for a project. Exportable.

**Query Parameters:** `project_id` (required), `format`

---

### GET `/api/v1/reports/overdue`

**Summary:** Grievances past target resolution date. Exportable.

**Query Parameters:** `project_id`, `priority`, `format`

---

## 2.8 Voice

### POST `/api/v1/voice/feedback/{feedback_id}/voice-note`

**Summary:** Attach a voice note to a feedback record. Audio is stored, transcribed via STT, and written to voice_note fields. If description is empty and `use_as_description=true`, the transcript populates it.

**Auth:** Bearer JWT (CurrentUserDep)

**Request Body:** `multipart/form-data`
- `audio` -- Audio file (OGG, WebM, MP3, WAV, AAC, AMR). Max 25 MB.
- `language` -- string, "sw" or "en" (default "sw")
- `use_as_description` -- bool (default true)

**Success Response (200):**
```json
{
  "feedback_id": "uuid",
  "voice_note_url": "https://storage.riviwa.com/feedback/uuid/voice.ogg",
  "transcription": "Nyumba yangu imeharibiwa na ujenzi...",
  "language": "sw",
  "confidence": 0.87,
  "duration_seconds": 45.2,
  "service": "whisper",
  "flagged_for_review": false,
  "description_updated": true
}
```

**Error Codes:** `404` Feedback not found, `413` File exceeds 25MB, `415` Unsupported audio format

---

### POST `/api/v1/voice/sessions/{session_id}/audio-turn`

**Summary:** Submit a voice turn in an active conversation session. Audio is transcribed and fed into the LLM pipeline. Returns the LLM's text reply and optionally TTS audio.

**Auth:** Bearer JWT (CurrentUserDep)

**Request Body:** `multipart/form-data`
- `audio` -- Audio recording (OGG, WebM, MP3, WAV, AAC, AMR). Max 25 MB.
- `language` -- string, optional override
- `tts_reply` -- bool (default false). If true, synthesise TTS audio for the LLM reply.

**Success Response (200):**
```json
{
  "session_id": "uuid",
  "turn_index": 3,
  "transcription": "I want to report damage to my fence",
  "language": "en",
  "confidence": 0.92,
  "audio_url": "https://storage.riviwa.com/sessions/uuid/turn_3.ogg",
  "flagged_for_review": false,
  "lm_reply": "I understand. Can you tell me which project area this occurred in?",
  "tts_audio_url": "https://storage.riviwa.com/sessions/uuid/tts_4.mp3",
  "session_status": "active",
  "feedback_id": null
}
```

**Error Codes:** `404` Session not found, `409` Session not ACTIVE, `413`, `415`

---

### POST `/api/v1/voice/sessions/{session_id}/tts`

**Summary:** Synthesise TTS audio for playback to the PAP (IVR or app voice mode).

**Auth:** Bearer JWT (CurrentUserDep)

**Request Body:** `multipart/form-data`
- `text` -- string (required), text to synthesise
- `language` -- string, "sw" or "en" (default: session language)
- `voice_id` -- string, optional provider-specific voice ID

**Success Response (200):**
```json
{
  "session_id": "uuid",
  "audio_url": "https://storage.riviwa.com/sessions/uuid/tts_5.mp3",
  "duration_seconds": 4.2,
  "service": "google_tts",
  "language": "sw"
}
```

**Error Codes:** `404` Session not found

---

## Kafka Events Reference

### Auth Service Publishes

| Topic | Event Types |
|-------|-------------|
| `riviwa.user.events` | `user.registration_initiated`, `user.registered`, `user.registered_social`, `user.email_verified`, `user.phone_verified`, `user.id_verified`, `user.activated`, `user.suspended`, `user.banned`, `user.deactivated`, `user.reactivated`, `user.password_set`, `user.password_changed`, `user.password_reset`, `user.profile_updated`, `user.avatar_updated` |
| `riviwa.organisation.events` | `organisation.created`, `organisation.updated`, `organisation.verified`, `organisation.suspended`, `organisation.banned`, `organisation.deactivated`, `organisation.member_added`, `organisation.member_removed`, `organisation.member_role_changed`, `organisation.owner_transferred`, `organisation.invite_sent`, `organisation.invite_accepted` |
| `riviwa.auth.events` | `auth.login_success`, `auth.login_failed`, `auth.login_locked`, `auth.logout`, `auth.token_refreshed`, `auth.dashboard_switched` |
| `riviwa.fraud.events` | `fraud.score_computed`, `fraud.account_flagged`, `fraud.account_cleared`, `fraud.duplicate_detected` |

### Feedback Service Publishes

| Topic | Event Types |
|-------|-------------|
| `riviwa.feedback.events` | `feedback.submitted`, `feedback.acknowledged`, `feedback.escalated`, `feedback.resolved`, `feedback.appealed`, `feedback.closed`, `feedback.summary.daily` |

### Feedback Service Consumes

| Topic | Event Types |
|-------|-------------|
| `riviwa.org.events` | `org_project.published`, `org_project.updated`, `org_project.paused`, `org_project.resumed`, `org_project.completed`, `org_project.cancelled`, `org_project_stage.activated`, `org_project_stage.completed`, `org_project_stage.skipped` |
| `riviwa.user.events` | `user.registered`, `user.profile_updated`, `user.deactivated`, `user.suspended`, `user.banned` |
| `riviwa.stakeholder.events` | `engagement.concern.raised`, `communication.concerns.pending` |

---

# 3. STAKEHOLDER SERVICE

**Port:** 8070 | **Database:** stakeholder_db (PostgreSQL, port 5436)

The Stakeholder Service manages the Stakeholder Engagement Plan (SEP) for World Bank-funded projects. It tracks stakeholder entities, their contact persons, engagement activities, communication records, and focal persons. It maintains a local read-only cache of projects and stages synced from the Auth Service via Kafka.

---

## 3.1 Database Schema Overview

### Table: `stakeholders`
The core entity -- an NGO, community group, government body, private company, or individual affected by or interested in a project.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| stakeholder_type | enum | `pap`, `interested_party` |
| entity_type | enum | `individual`, `organization`, `group` |
| category | enum | `individual`, `local_government`, `national_government`, `ngo_cbo`, `community_group`, `private_company`, `utility_provider`, `development_partner`, `media`, `academic_research`, `vulnerable_group`, `other` |
| affectedness | enum | `positively_affected`, `negatively_affected`, `both`, `unknown` |
| importance_rating | enum | `high`, `medium`, `low` |
| org_name | varchar(255) | Org/group name (null for individuals) |
| first_name, last_name | varchar | Individual name fields |
| org_id | UUID (soft link) | auth_service Organisation.id |
| address_id | UUID (soft link) | auth_service Address.id |
| lga, ward | varchar | Denormalised geographic fields |
| language_preference | varchar(10) | Default `sw` (Swahili) |
| preferred_channel | enum | `public_meeting`, `focus_group`, `email`, `sms`, `phone_call`, `radio`, `tv`, `social_media`, `billboard`, `notice_board`, `letter`, `in_person` |
| is_vulnerable | boolean | ESS 7/10 classification |
| vulnerable_group_types | JSONB | e.g. `{"types": ["elderly", "disabled_physical"]}` |
| needs_translation, needs_transport, needs_childcare | boolean | Accommodation flags |
| deleted_at | timestamptz | Soft-delete |

### Table: `stakeholder_contacts`
A named person representing a stakeholder entity.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| stakeholder_id | UUID (FK) | |
| user_id | UUID (soft link) | auth_service User.id |
| full_name | varchar(200) | |
| title, role_in_org | varchar | |
| email, phone | varchar | |
| preferred_channel | enum | Contact-level preference |
| is_primary | boolean | Main point of contact |
| can_submit_feedback | boolean | |
| can_receive_communications | boolean | |
| can_distribute_communications | boolean | |
| is_active | boolean | |

### Table: `stakeholder_projects`
Junction: registers a stakeholder against a specific project.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| stakeholder_id | UUID (FK) | |
| project_id | UUID | |
| is_pap | boolean | PAP for this project? |
| affectedness | enum | Project-specific |
| impact_description | text | |
| consultation_count | integer | Running count |
| UNIQUE | | (stakeholder_id, project_id) |

### Table: `stakeholder_stage_engagements`
Per-stage engagement definition: importance, role, goals, permitted activities.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| stakeholder_id | UUID (FK) | |
| project_id | UUID | |
| stage_id | UUID (FK) | |
| importance | enum | `high`, `medium`, `low` |
| importance_justification | text | |
| engagement_role | text | Why they matter to this stage |
| goals, interests, potential_risks | text | SEP Annex 3 fields |
| engagement_approach | text | How to engage |
| allowed_activities | JSONB | e.g. `{"activities": ["attend_meetings", "submit_grievances"]}` |
| engagement_frequency | varchar(100) | e.g. "Weekly during RAP" |
| UNIQUE | | (stakeholder_id, project_id, stage_id) |

### Table: `engagement_activities`
A single consultation event (meeting, workshop, site visit, etc.).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| project_id | UUID | |
| stage_id | UUID | |
| subproject_id | UUID | |
| stage | enum | `preparation`, `feasibility_design`, `construction`, `finalization`, `operation` |
| activity_type | enum | `public_meeting`, `workshop`, `focus_group`, `site_visit`, `survey`, `radio_tv`, `social_media`, `key_informant`, `round_table`, `online_webinar`, `other` |
| status | enum | `planned`, `conducted`, `cancelled` |
| title | varchar(255) | |
| venue, lga, ward, gps_lat, gps_lng | various | Physical location |
| virtual_platform, virtual_url, virtual_meeting_id | various | Virtual location |
| scheduled_at, conducted_at, duration_hours | various | Timing |
| expected_count, actual_count, female_count, vulnerable_count | integer | Attendance tracking |
| summary_of_issues, summary_of_responses | text | Outcomes |
| action_items | JSONB | |
| minutes_url, photos_urls | various | Evidence |

### Table: `stakeholder_engagements`
Junction: contact x activity attendance record.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| contact_id | UUID (FK) | |
| activity_id | UUID (FK) | |
| attendance_status | enum | `attended`, `absent`, `represented`, `remote` |
| proxy_name | varchar(200) | Delegate name if represented |
| concerns_raised | text | |
| response_given | text | |
| feedback_submitted | boolean | True if escalated to GRM |
| feedback_ref_id | UUID (soft link) | feedback_service Feedback.id |
| UNIQUE | | (contact_id, activity_id) |

### Table: `activity_media`
Files attached to engagement activities (minutes, photos, presentations).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| activity_id | UUID (FK) | |
| media_type | enum | `minutes`, `photo`, `presentation`, `document`, `other` |
| file_url | text | MinIO path: `activities/{activity_id}/media/{id}.{ext}` |
| file_name, file_size_bytes, mime_type | various | |
| title | varchar(300) | Required |
| deleted_at | timestamptz | Soft-delete; file in MinIO never deleted |

### Table: `communication_records`
Every logged communication (outgoing or incoming) for a project.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| project_id | UUID (FK) | |
| stakeholder_id | UUID | Nullable for broadcast |
| contact_id | UUID (FK) | Nullable for entity-level |
| channel | enum | `email`, `sms`, `letter`, `phone_call`, `in_person`, `public_meeting`, `radio`, `tv`, `social_media`, `billboard`, `notice_board`, `website`, `newspaper`, `flyer_poster`, `whatsapp_group`, `other` |
| direction | enum | `outgoing`, `incoming` |
| purpose | enum | `information_disclosure`, `meeting_invitation`, `meeting_minutes`, `grievance_response`, `progress_update`, `compensation_notice`, `general_inquiry`, `complaint`, `suggestion`, `acknowledgement`, `other` |
| subject | varchar(500) | |
| content_summary | text | |
| in_response_to_id | UUID (self-FK) | Threading |
| distribution_required | boolean | |
| distribution_deadline | timestamptz | |

### Table: `communication_distributions`
Tracks what happened after a contact received a communication -- proof that info reached communities.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| communication_id | UUID (FK) | |
| contact_id | UUID (FK) | |
| distributed_to_count | integer | |
| distribution_method | enum | `verbal`, `notice_board`, `whatsapp_group`, `public_meeting`, `sms_blast`, `door_to_door`, `radio`, `printed_copies`, `other` |
| concerns_raised_after | text | Post-distribution concerns |
| feedback_ref_id | UUID (soft link) | Linked grievance |

### Table: `focal_persons`
Named PIU contact at each implementing agency (SEP Table 9).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| project_id | UUID (FK) | |
| org_type | enum | `lga`, `tanroads`, `po_ralg`, `piu`, `tarura`, `other` |
| organization_name | varchar(255) | |
| title, full_name, phone, email, address | various | |
| lga, subproject | varchar | Scope |
| user_id | UUID (soft link) | Riviwa account link |

### Table: `projects` (read-only cache)
Local cache of OrgProject from auth_service. Synced via Kafka.

### Table: `project_stages` (read-only cache)
Local cache of OrgProjectStage from auth_service. Synced via Kafka.

---

## 3.2 API Endpoints

**Base URL:** `http://<host>:8070/api/v1`

### 3.2.1 Stakeholders

All endpoints require **StaffDep** (JWT with org staff role) unless noted.

#### POST /stakeholders
**Summary:** Register a stakeholder
**Auth:** Staff JWT
**Request Body:**
```json
{
  "stakeholder_type": "pap",
  "entity_type": "group",
  "category": "community_group",
  "affectedness": "negatively_affected",
  "importance_rating": "high",
  "org_name": "M18 Flood Community Leaders",
  "language_preference": "sw",
  "preferred_channel": "public_meeting",
  "is_vulnerable": true,
  "vulnerable_group_types": {"types": ["low_income"]},
  "lga": "Ilala",
  "ward": "Jangwani",
  "notes": "Requires sign language interpreter"
}
```
**Response (201):**
```json
{
  "id": "uuid",
  "stakeholder_type": "pap",
  "entity_type": "group",
  "category": "community_group",
  "affectedness": "negatively_affected",
  "importance_rating": "high",
  "display_name": "M18 Flood Community Leaders",
  "org_name": "M18 Flood Community Leaders",
  "first_name": null,
  "last_name": null,
  "org_id": null,
  "address_id": null,
  "lga": "Ilala",
  "ward": "Jangwani",
  "language_preference": "sw",
  "preferred_channel": "public_meeting",
  "needs_translation": false,
  "needs_transport": false,
  "needs_childcare": false,
  "is_vulnerable": true,
  "vulnerable_group_types": {"types": ["low_income"]},
  "participation_barriers": null,
  "notes": "Requires sign language interpreter",
  "created_at": "2025-06-15T10:00:00+00:00"
}
```

#### GET /stakeholders
**Summary:** List stakeholders with optional filters
**Auth:** Staff JWT
**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| stakeholder_type | string | `pap` / `interested_party` |
| category | string | Any StakeholderCategory value |
| lga | string | Partial match |
| affectedness | string | `directly_affected` / `indirectly_affected` / `not_affected` |
| is_vulnerable | boolean | Filter to vulnerable only |
| importance | string | `high` / `medium` / `low` (requires project_id or stage_id) |
| project_id | UUID | Filter to project |
| stage_id | UUID | Filter to stage |
| skip | int | Default 0 |
| limit | int | Default 50, max 200 |

**Response (200):**
```json
{
  "items": [ /* stakeholder objects */ ],
  "count": 42
}
```

#### GET /stakeholders/analysis
**Summary:** Stakeholder analysis matrix (SEP Annex 3 format)
**Auth:** Staff JWT
**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| project_id | UUID | Yes | Project to analyse |
| stage_id | UUID | No | Narrow to specific stage |
| importance | string | No | `high` / `medium` / `low` |
| category | string | No | |
| affectedness | string | No | |
| is_vulnerable | boolean | No | |
| skip | int | No | Default 0 |
| limit | int | No | Default 200, max 500 |

**Response (200):**
```json
{
  "project_id": "uuid",
  "stage_id": "uuid|null",
  "filters": { "importance": null, "category": null, "affectedness": null, "is_vulnerable": null },
  "count": 15,
  "items": [
    {
      "stakeholder_id": "uuid",
      "display_name": "World Bank",
      "stage_name": "Preparation",
      "importance": "high",
      "importance_justification": "...",
      "why_important": "Fund provider and technical advisor",
      "interests": "ESS compliance and PDO achievement",
      "potential_risks": "...",
      "how_to_engage": "Direct consultation, quarterly reviews",
      "when_to_engage": "Quarterly during preparation"
    }
  ]
}
```

#### GET /stakeholders/{stakeholder_id}
**Summary:** Stakeholder detail with contacts
**Auth:** Staff JWT
**Response (200):**
```json
{
  "id": "uuid",
  "stakeholder_type": "pap",
  "display_name": "M18 Flood Community Leaders",
  "...": "...all stakeholder fields...",
  "contacts": [
    {
      "id": "uuid",
      "full_name": "John Chairperson",
      "title": "Ward Executive Officer",
      "role_in_org": "Chairperson M18",
      "email": "john@example.com",
      "phone": "+255712345678",
      "preferred_channel": "phone_call",
      "is_primary": true,
      "can_submit_feedback": true,
      "can_receive_communications": true,
      "can_distribute_communications": true,
      "user_id": "uuid|null",
      "is_active": true
    }
  ]
}
```

#### PATCH /stakeholders/{stakeholder_id}
**Summary:** Update stakeholder profile
**Auth:** Staff JWT
**Request Body:** Partial update -- any subset of stakeholder fields.
**Response (200):** Updated stakeholder object.

#### DELETE /stakeholders/{stakeholder_id}
**Summary:** Soft-delete a stakeholder
**Auth:** Admin role required (`require_platform_role("admin")`)
**Response (200):**
```json
{ "message": "Stakeholder {id} deactivated." }
```

#### POST /stakeholders/{stakeholder_id}/projects
**Summary:** Register stakeholder under a project
**Auth:** Staff JWT
**Request Body:**
```json
{
  "project_id": "uuid",
  "is_pap": true,
  "affectedness": "negatively_affected",
  "impact_description": "Land acquisition required for flood channel"
}
```
**Response (201):**
```json
{
  "id": "uuid",
  "stakeholder_id": "uuid",
  "project_id": "uuid",
  "is_pap": true,
  "affectedness": "negatively_affected",
  "impact_description": "Land acquisition required for flood channel",
  "consultation_count": 0,
  "registered_at": "2025-06-15T10:00:00+00:00"
}
```

#### GET /stakeholders/{stakeholder_id}/projects
**Summary:** List project registrations
**Auth:** Staff JWT
**Response (200):**
```json
{ "items": [ /* stakeholder_project objects */ ] }
```

#### GET /stakeholders/{stakeholder_id}/engagements
**Summary:** Engagement history for a stakeholder
**Auth:** Staff JWT
**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "contact_id": "uuid",
      "activity_id": "uuid",
      "attendance_status": "attended",
      "concerns_raised": "Compensation timeline unclear",
      "response_given": "RAP schedule shared; payments start Q3",
      "feedback_submitted": false,
      "feedback_ref_id": null,
      "created_at": "2025-06-15T10:00:00+00:00"
    }
  ]
}
```

### 3.2.2 Contacts

#### POST /stakeholders/{stakeholder_id}/contacts
**Summary:** Add a contact to a stakeholder
**Auth:** Staff JWT
**Request Body:**
```json
{
  "full_name": "Jane Representative",
  "title": "Community Development Officer",
  "role_in_org": "Secretary",
  "email": "jane@example.com",
  "phone": "+255712345679",
  "preferred_channel": "email",
  "is_primary": false,
  "can_submit_feedback": true,
  "can_receive_communications": true,
  "can_distribute_communications": false
}
```
**Response (201):** Contact object with all fields.

#### GET /stakeholders/{stakeholder_id}/contacts
**Summary:** List contacts for a stakeholder
**Auth:** Staff JWT
**Query:** `active_only` (boolean, default true)
**Response (200):**
```json
{ "items": [ /* contact objects */ ] }
```

#### PATCH /stakeholders/{stakeholder_id}/contacts/{contact_id}
**Summary:** Update a contact
**Auth:** Staff JWT
**Request Body:** Partial update of contact fields.
**Response (200):** Updated contact object.

#### DELETE /stakeholders/{stakeholder_id}/contacts/{contact_id}
**Summary:** Deactivate a contact
**Auth:** Staff JWT
**Request Body:**
```json
{ "reason": "Left the organization" }
```
**Response (200):**
```json
{ "message": "Contact {id} deactivated." }
```

### 3.2.3 Engagement Activities

#### POST /activities
**Summary:** Create an engagement activity
**Auth:** Staff JWT
**Request Body:**
```json
{
  "project_id": "uuid",
  "stage_id": "uuid",
  "stage": "preparation",
  "activity_type": "public_meeting",
  "title": "Community Consultation â€” Jangwani Ward",
  "description": "Initial stakeholder consultation for the Msimbazi project",
  "agenda": "1. Project overview\n2. Q&A\n3. Next steps",
  "venue": "Jangwani Community Hall",
  "lga": "Ilala",
  "ward": "Jangwani",
  "gps_lat": -6.8088,
  "gps_lng": 39.2712,
  "scheduled_at": "2025-07-01T09:00:00+03:00",
  "expected_count": 150,
  "languages_used": {"languages": ["sw", "en"]}
}
```
**Response (201):** Full activity object with all fields.

#### GET /activities
**Summary:** List engagement activities
**Auth:** Staff JWT
**Query Parameters:** `project_id`, `stage`, `status`, `lga`, `skip`, `limit`
**Response (200):**
```json
{ "items": [ /* activity objects */ ] }
```

#### GET /activities/{activity_id}
**Summary:** Activity detail with attendance
**Auth:** Staff JWT
**Response (200):**
```json
{
  "id": "uuid",
  "title": "Community Consultation â€” Jangwani Ward",
  "...": "...all activity fields...",
  "attendances": [
    {
      "id": "uuid",
      "contact_id": "uuid",
      "activity_id": "uuid",
      "attendance_status": "attended",
      "proxy_name": null,
      "concerns_raised": "When will compensation be paid?",
      "response_given": "RAP payments begin Q3 2025",
      "feedback_submitted": false,
      "feedback_ref_id": null,
      "notes": null,
      "created_at": "2025-07-01T12:00:00+00:00"
    }
  ]
}
```

#### PATCH /activities/{activity_id}
**Summary:** Update activity / mark as conducted
**Auth:** Staff JWT
**Request Body:** Partial update. To mark as conducted, set `status: "conducted"`, `conducted_at`, `actual_count`, etc.
**Response (200):** Updated activity object.

#### POST /activities/{activity_id}/cancel
**Summary:** Cancel a planned or scheduled activity
**Auth:** Staff JWT
**Request Body:**
```json
{ "reason": "Flood warning â€” venue inaccessible" }
```
**Response (200):** Updated activity object with `status: "cancelled"`.
**Errors:** 400 if activity already conducted.

#### POST /activities/{activity_id}/attendances
**Summary:** Log attendance
**Auth:** Staff JWT
**Request Body:**
```json
{
  "contact_id": "uuid",
  "attendance_status": "attended",
  "concerns_raised": "Compensation timeline unclear",
  "response_given": "RAP schedule shared"
}
```
**Response (201):** Engagement record object.

#### POST /activities/{activity_id}/attendances/bulk
**Summary:** Bulk log attendance -- multiple contacts in one request
**Auth:** Staff JWT
**Request Body:**
```json
{
  "records": [
    {"contact_id": "uuid", "attendance_status": "attended", "concerns_raised": "..."},
    {"contact_id": "uuid", "attendance_status": "absent"}
  ]
}
```
**Response (201):**
```json
{
  "activity_id": "uuid",
  "logged": 2,
  "items": [ /* engagement record objects */ ]
}
```
**Errors:** 400 if `records` list is empty.

#### PATCH /activities/{activity_id}/attendances/{engagement_id}
**Summary:** Update attendance record
**Auth:** Staff JWT
**Response (200):** Updated engagement record.

#### DELETE /activities/{activity_id}/attendances/{engagement_id}
**Summary:** Remove an attendance record
**Auth:** Staff JWT
**Response (200):**
```json
{ "message": "Attendance record {id} removed." }
```

#### POST /activities/{activity_id}/media
**Summary:** Upload a file to an activity
**Auth:** Staff JWT
**Content-Type:** multipart/form-data
**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| file | file | Yes | Accepted: JPEG, PNG, WebP, PDF, PPTX, DOCX, XLSX |
| title | string (form) | Yes | Short descriptive title |
| media_type | string (form) | No | `minutes`, `photo`, `presentation`, `document`, `other` (default: document) |
| description | string (form) | No | |

**Response (201):**
```json
{
  "id": "uuid",
  "activity_id": "uuid",
  "media_type": "minutes",
  "file_url": "https://cdn.riviwa.com/activities/{id}/media/{id}.pdf",
  "file_name": "minutes_jangwani.pdf",
  "file_size_bytes": 245760,
  "mime_type": "application/pdf",
  "title": "Meeting Minutes â€” Jangwani Consultation 2025-07-01",
  "description": null,
  "uploaded_by_user_id": "uuid",
  "uploaded_at": "2025-07-01T14:00:00+00:00"
}
```
**Errors:** 400 for unsupported file type or upload failure.

#### GET /activities/{activity_id}/media
**Summary:** List all media files attached to an activity
**Auth:** Staff JWT
**Query:** `media_type` (optional filter)
**Response (200):**
```json
{
  "activity_id": "uuid",
  "total": 3,
  "items": [ /* media objects */ ]
}
```

#### DELETE /activities/{activity_id}/media/{media_id}
**Summary:** Remove a media file (soft delete)
**Auth:** Staff JWT
**Response (200):**
```json
{ "message": "Media {id} removed from activity." }
```
**Note:** File in MinIO/S3 is NEVER deleted -- engagement media is part of the SEP evidence trail.

### 3.2.4 Communications

#### POST /communications
**Summary:** Log a communication record
**Auth:** Staff JWT
**Request Body:**
```json
{
  "project_id": "uuid",
  "stakeholder_id": "uuid",
  "contact_id": "uuid",
  "channel": "letter",
  "direction": "outgoing",
  "purpose": "information_disclosure",
  "subject": "RAP Disclosure â€” Msimbazi Phase 1",
  "content_summary": "Full RAP document shared for community review",
  "document_urls": {"urls": ["https://cdn.riviwa.com/docs/rap_phase1.pdf"]},
  "distribution_required": true,
  "distribution_deadline": "2025-07-15T17:00:00+03:00"
}
```
**Response (201):** Full communication record object.

#### GET /communications
**Summary:** List communication records
**Auth:** Staff JWT
**Query Parameters:** `project_id`, `stakeholder_id`, `direction`, `channel`, `skip`, `limit`
**Response (200):**
```json
{ "items": [ /* communication record objects */ ] }
```

#### GET /communications/{comm_id}
**Summary:** Communication detail with distributions
**Auth:** Staff JWT
**Response (200):**
```json
{
  "id": "uuid",
  "...": "...all communication fields...",
  "distributions": [
    {
      "id": "uuid",
      "communication_id": "uuid",
      "contact_id": "uuid",
      "distributed_to_count": 120,
      "distribution_method": "public_meeting",
      "distribution_notes": "Announced at Friday baraza",
      "distributed_at": "2025-07-03T10:00:00+03:00",
      "concerns_raised_after": "3 members asked about compensation timeline",
      "feedback_ref_id": null,
      "acknowledged_at": null,
      "has_pending_concerns": true,
      "created_at": "2025-07-03T12:00:00+00:00"
    }
  ]
}
```

#### POST /communications/{comm_id}/distributions
**Summary:** Log that a contact distributed this communication
**Auth:** Staff JWT
**Request Body:**
```json
{
  "contact_id": "uuid",
  "distributed_to_count": 120,
  "distribution_method": "public_meeting",
  "distribution_notes": "Announced at Friday baraza, 47 households represented",
  "distributed_at": "2025-07-03T10:00:00+03:00",
  "concerns_raised_after": "3 members asked about compensation timeline"
}
```
**Response (201):** Distribution record object.

#### PATCH /communications/{comm_id}/distributions/{dist_id}
**Summary:** Update distribution record (confirm, add concerns, link feedback)
**Auth:** Staff JWT
**Response (200):** Updated distribution object.

### 3.2.5 Focal Persons

#### POST /focal-persons
**Summary:** Register a focal person (SEP Table 9)
**Auth:** Staff JWT
**Request Body:**
```json
{
  "project_id": "uuid",
  "org_type": "lga",
  "organization_name": "Ilala Municipal Council",
  "title": "Community Development Officer",
  "full_name": "James Mkwawa",
  "phone": "+255712000001",
  "email": "james@ilala.go.tz",
  "lga": "Ilala"
}
```
**Response (201):** Focal person object.

#### GET /focal-persons
**Summary:** List focal persons
**Auth:** Staff JWT
**Query Parameters:** `project_id`, `org_type`, `active_only` (default true)
**Response (200):**
```json
{ "items": [ /* focal person objects */ ] }
```

#### PATCH /focal-persons/{fp_id}
**Summary:** Update focal person details
**Auth:** Staff JWT
**Response (200):** Updated focal person object.

### 3.2.6 Projects (Read-Only Cache)

#### GET /projects
**Summary:** List synced projects
**Auth:** Staff JWT
**Query Parameters:** `status` (`planning`/`active`/`paused`/`completed`/`cancelled`), `org_id`, `lga`, `skip`, `limit`
**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "organisation_id": "uuid",
      "branch_id": "uuid|null",
      "name": "Msimbazi Flood Control",
      "code": "MSB-001",
      "slug": "msimbazi-flood-control",
      "status": "active",
      "category": "infrastructure",
      "sector": "water",
      "country_code": "TZ",
      "region": "Dar es Salaam",
      "primary_lga": "Ilala",
      "accepts_grievances": true,
      "accepts_suggestions": true,
      "accepts_applause": true,
      "published_at": "2025-01-15T10:00:00+00:00",
      "synced_at": "2025-06-15T10:00:00+00:00"
    }
  ],
  "count": 5
}
```

#### GET /projects/{project_id}
**Summary:** Project detail with engagement counts
**Auth:** Staff JWT
**Response (200):**
```json
{
  "id": "uuid",
  "...": "...all project fields...",
  "counts": {
    "stakeholders": 42,
    "activities_planned": 5,
    "activities_conducted": 12,
    "communications": 28
  }
}
```

### 3.2.7 Reports

#### GET /reports/engagement-summary
**Summary:** Activity counts by stage and LGA for a project
**Auth:** Staff JWT
**Query:** `project_id` (required)

#### GET /reports/stakeholder-reach
**Summary:** Stakeholder counts by category and vulnerability
**Auth:** Staff JWT
**Query:** `project_id` (required)

#### GET /reports/pending-distributions
**Summary:** Communications requiring distribution that have not been logged yet
**Auth:** Staff JWT
**Query:** `project_id` (required)

#### GET /reports/pending-concerns
**Summary:** Distribution records with unresolved concerns
**Auth:** Staff JWT
**Query:** `project_id` (required)

---

# 4. PAYMENT SERVICE

**Port:** 8080 | **Database:** payment_db (PostgreSQL)

The Payment Service handles mobile money payments for Tanzania via three providers: AzamPay, Selcom, and M-Pesa. It supports payment intent creation, USSD push initiation, webhook processing, verification, and refunds.

---

## 4.1 Database Schema Overview

### Table: `payments`
A payment intent -- what should be paid, by whom, for what.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| payment_type | enum | `grievance_fee`, `project_contribution`, `service_fee`, `subscription`, `refund` |
| amount | float | Amount in minor units |
| currency | enum | `TZS`, `USD`, `KES` |
| description | text | |
| payer_user_id | UUID (soft link) | auth_service User.id |
| payer_phone | varchar(20) | E.164 phone for mobile money |
| payer_name, payer_email | varchar | |
| org_id | UUID (soft link) | |
| project_id | UUID (soft link) | |
| reference_id | UUID | Domain object ID (invoice, subproject, etc.) |
| reference_type | varchar(50) | `invoice`, `subproject`, `subscription`, `feedback` |
| status | enum | `pending`, `initiated`, `processing`, `paid`, `failed`, `expired`, `refunded`, `cancelled` |
| external_ref | varchar(255) | Reference sent to provider for callback matching |
| paid_at | timestamptz | |
| expires_at | timestamptz | |

### Table: `payment_transactions`
One provider transaction attempt for a Payment. A Payment can have multiple transactions (retries, refunds).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| payment_id | UUID (FK) | |
| provider | enum | `azampay`, `selcom`, `mpesa` |
| status | enum | `pending`, `success`, `failed`, `timeout`, `reversed` |
| provider_ref | varchar(255) | Provider-assigned reference |
| provider_order_id | varchar(255) | |
| provider_receipt | varchar(255) | |
| provider_request | JSONB | Raw request sent |
| provider_response | JSONB | Raw response received |
| settled_amount | float | May differ from requested |
| failure_reason | text | |
| initiated_at | timestamptz | |
| completed_at | timestamptz | |

### Table: `webhook_logs`
Raw inbound webhook payloads -- audit trail and replay source.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| provider | enum | `azampay`, `selcom`, `mpesa` |
| headers | JSONB | |
| body | JSONB | Parsed body |
| raw_body | text | Original body |
| transaction_id | UUID (FK, nullable) | Matched transaction |
| processed | boolean | |
| process_error | text | |

---

## 4.2 Payment Providers

| Provider | Networks Supported | Flow |
|----------|--------------------|------|
| **AzamPay** | Airtel Money TZ, M-Pesa (via AzamPay), CRDB, NMB | OAuth token -> mobile-checkout -> USSD push -> webhook callback |
| **Selcom** | Tigo Pesa, TTCL Pesa, Halotel | HMAC-signed create-order -> checkout URL or USSD -> webhook callback |
| **M-Pesa** | Vodacom M-Pesa TZ (direct) | RSA-encrypted session key -> c2bPayment/singleStage -> USSD push -> webhook callback |

All providers support: `initiate()`, `verify()`, `refund()` (refund raises error -- must use merchant portal).

---

## 4.3 API Endpoints

**Base URL:** `http://<host>:8080/api/v1`

### 4.3.1 Payments

#### POST /payments
**Summary:** Create payment intent
**Auth:** AuthDep (any authenticated user)
**Request Body:**
```json
{
  "payment_type": "project_contribution",
  "amount": 50000,
  "currency": "TZS",
  "phone": "+255712345678",
  "payer_name": "John Doe",
  "payer_email": "john@example.com",
  "description": "Community contribution to Msimbazi project",
  "org_id": "uuid",
  "project_id": "uuid",
  "reference_id": "uuid",
  "reference_type": "subproject"
}
```
**Response (201):**
```json
{
  "id": "uuid",
  "payment_type": "project_contribution",
  "amount": 50000,
  "currency": "TZS",
  "description": "Community contribution to Msimbazi project",
  "status": "pending",
  "external_ref": null,
  "payer_user_id": "uuid",
  "payer_phone": "+255712345678",
  "payer_name": "John Doe",
  "org_id": "uuid",
  "project_id": "uuid",
  "reference_id": "uuid",
  "reference_type": "subproject",
  "created_at": "2025-06-15T10:00:00+00:00",
  "expires_at": null,
  "paid_at": null
}
```

#### GET /payments
**Summary:** List payments
**Auth:** AuthDep (staff see all; regular users see only their own)
**Query Parameters:** `payer_user_id`, `org_id`, `project_id`, `reference_id`, `status`, `payment_type`, `skip`, `limit`
**Response (200):**
```json
{
  "items": [ /* payment objects */ ],
  "count": 12
}
```

#### GET /payments/{payment_id}
**Summary:** Payment detail with transactions
**Auth:** AuthDep
**Response (200):**
```json
{
  "id": "uuid",
  "...": "...all payment fields...",
  "transactions": [
    {
      "id": "uuid",
      "payment_id": "uuid",
      "provider": "azampay",
      "status": "success",
      "provider_ref": "ATX123456",
      "provider_receipt": "RCP789",
      "settled_amount": 50000,
      "failure_reason": null,
      "initiated_at": "2025-06-15T10:01:00+00:00",
      "completed_at": "2025-06-15T10:02:30+00:00"
    }
  ]
}
```

#### POST /payments/{payment_id}/initiate
**Summary:** Initiate USSD push via provider
**Auth:** AuthDep
**Request Body:**
```json
{
  "provider": "azampay"
}
```
**Providers:** `azampay` (Airtel, M-Pesa via AzamPay, CRDB, NMB), `selcom` (Tigo Pesa, TTCL Pesa, Halotel), `mpesa` (Vodacom M-Pesa TZ direct)
**Response (200):**
```json
{
  "id": "uuid",
  "payment_id": "uuid",
  "provider": "azampay",
  "status": "pending",
  "provider_ref": "ATX123456",
  "provider_receipt": null,
  "settled_amount": null,
  "failure_reason": null,
  "initiated_at": "2025-06-15T10:01:00+00:00",
  "completed_at": null,
  "checkout_url": "https://...",
  "message": "Payment request sent. Customer will receive a USSD prompt."
}
```

#### POST /payments/{payment_id}/verify
**Summary:** Poll provider for latest status
**Auth:** AuthDep
**Response (200):** Transaction object with current provider status.
**Errors:** 404 if no transaction found.

#### POST /payments/{payment_id}/refund
**Summary:** Refund a paid payment
**Auth:** StaffDep (staff only)
**Response (200):**
```json
{
  "id": "uuid",
  "...": "...transaction fields...",
  "message": "Refund initiated."
}
```
**Note:** Automated refunds are not supported by any provider. Raises error directing to merchant portal.

#### DELETE /payments/{payment_id}
**Summary:** Cancel a PENDING payment
**Auth:** AuthDep
**Response (200):**
```json
{ "message": "Payment cancelled.", "payment_id": "uuid" }
```

#### GET /payments/{payment_id}/transactions
**Summary:** List transactions for a payment
**Auth:** AuthDep
**Response (200):**
```json
{
  "items": [ /* transaction objects */ ],
  "count": 2
}
```

### 4.3.2 Webhooks (Provider Callbacks)

These endpoints are NOT included in the OpenAPI schema (`include_in_schema=False`). They receive raw callbacks from payment gateways.

| Endpoint | Provider | Notes |
|----------|----------|-------|
| `POST /webhooks/azampay` | AzamPay | JSON body |
| `POST /webhooks/selcom` | Selcom | JSON body, HMAC-SHA256 signature validation |
| `POST /webhooks/mpesa` | M-Pesa | JSON body, returns M-Pesa format response |

All webhook endpoints: log raw body to `webhook_logs`, match transaction by provider_ref, update Payment status.

---

# 5. NOTIFICATION SERVICE

**Port:** 8060 | **Database:** notification_db (PostgreSQL, port 5437)

The Notification Service is a channel-agnostic delivery platform. It is ignorant of business logic -- it receives notification requests (via Kafka or HTTP), looks up templates, checks user preferences, renders messages, and delivers through configured channels. It supports in-app, push (FCM/APNs), SMS (Africa's Talking/Twilio), WhatsApp (Meta Cloud API), and email (SendGrid/SMTP).

---

## 5.1 Database Schema Overview

### Table: `notification_templates`
Jinja2 templates per (notification_type, channel, language).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| notification_type | varchar(120) | e.g. `grm.feedback.acknowledged` |
| channel | enum | `in_app`, `push`, `sms`, `whatsapp`, `email` |
| language | varchar(5) | ISO 639-1: `en`, `sw` |
| title_template | varchar(300) | Push notification title (Jinja2) |
| subject_template | varchar(300) | Email subject (Jinja2) |
| body_template | text | Message body (Jinja2, HTML for email) |
| is_active | boolean | |
| UNIQUE | | (notification_type, channel, language) |

### Table: `notifications`
Every dispatched or scheduled notification.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| recipient_user_id | UUID | Nullable (pre-reg OTPs, anonymous) |
| recipient_phone | varchar(20) | |
| recipient_email | varchar(320) | |
| notification_type | varchar(120) | Template key |
| variables | JSONB | Rendering variables |
| language | varchar(5) | |
| requested_channels | JSONB | `{"channels": ["push", "sms"]}` |
| priority | enum | `critical`, `high`, `medium`, `low` |
| scheduled_at | timestamptz | Null = immediate; future = reminder |
| status | enum | `pending_scheduled`, `processing`, `partially_sent`, `sent`, `failed`, `cancelled` |
| idempotency_key | varchar(255) | Deduplication key, UNIQUE |
| source_service | varchar(60) | |
| source_entity_id | varchar(36) | |
| extra_data (metadata) | JSONB | |

### Table: `notification_deliveries`
One row per channel attempt per notification.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| notification_id | UUID (FK) | |
| channel | enum | |
| rendered_title | varchar(300) | Stored for audit |
| rendered_subject | varchar(300) | |
| rendered_body | text | |
| status | enum | `pending`, `sent`, `delivered`, `failed`, `skipped`, `read` |
| retry_count | integer | Max retries: 3 |
| next_retry_at | timestamptz | |
| failure_reason | varchar(500) | |
| provider_name | varchar(60) | e.g. `africas_talking`, `sendgrid`, `fcm` |
| provider_message_id | varchar(255) | For DLR correlation |
| read_at | timestamptz | In-app: when user opened |
| sent_at | timestamptz | |
| delivered_at | timestamptz | |

### Table: `notification_preferences`
Per-user opt-in/out per notification_type x channel.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| user_id | UUID | |
| notification_type | varchar(120) | Exact type or wildcard `grm.*` |
| channel | enum | |
| enabled | boolean | |
| UNIQUE | | (user_id, notification_type, channel) |

**Note:** CRITICAL priority notifications bypass preferences and are always sent.

### Table: `notification_devices`
Push token registry (FCM/APNs).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| user_id | UUID | |
| platform | enum | `fcm`, `apns` |
| push_token | varchar(512) | UNIQUE |
| device_name | varchar(100) | |
| app_version | varchar(30) | |
| is_active | boolean | |
| last_active_at | timestamptz | Stale > 90 days pruned |

---

## 5.2 API Endpoints

**Base URL:** `http://<host>:8060/api/v1`

### 5.2.1 Notification Inbox (Public)

Authentication via `X-User-Id` header (set by API gateway after JWT validation).

#### GET /notifications
**Summary:** Get notification inbox
**Auth:** X-User-Id header
**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| unread_only | boolean | false | Return only unread |
| skip | int | 0 | |
| limit | int | 30 | Max 100 |

**Response (200):**
```json
{
  "unread_count": 5,
  "returned": 30,
  "items": [
    {
      "delivery_id": "uuid",
      "notification_id": "uuid",
      "notification_type": "grm.feedback.acknowledged",
      "priority": "high",
      "rendered_title": "Complaint Acknowledged",
      "rendered_body": "Your complaint GRV-2025-0041 has been acknowledged...",
      "read_at": null,
      "created_at": "2025-06-15T10:00:00+00:00",
      "is_read": false
    }
  ]
}
```

#### GET /notifications/unread-count
**Summary:** Get unread notification count (for badge)
**Auth:** X-User-Id header
**Response (200):**
```json
{ "unread_count": 5 }
```

#### PATCH /notifications/deliveries/{delivery_id}/read
**Summary:** Mark a single notification as read
**Auth:** X-User-Id header
**Response (200):**
```json
{ "message": "Marked as read.", "delivery_id": "uuid" }
```
**Errors:** 404 if delivery not found.
**Idempotent:** Calling twice has no side-effects.

#### POST /notifications/mark-all-read
**Summary:** Mark all notifications as read
**Auth:** X-User-Id header
**Response (200):**
```json
{ "message": "5 notification(s) marked as read.", "count": 5 }
```

### 5.2.2 Notification Preferences

#### GET /notification-preferences
**Summary:** Get all notification preferences for the current user
**Auth:** X-User-Id header
**Response (200):**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "notification_type": "grm.feedback.submitted",
    "channel": "sms",
    "enabled": false,
    "updated_at": "2025-06-15T10:00:00+00:00"
  }
]
```
**Note:** If a (notification_type, channel) combination is not listed, default is ENABLED.

#### PUT /notification-preferences
**Summary:** Set a notification preference
**Auth:** X-User-Id header
**Request Body:**
```json
{
  "notification_type": "grm.feedback.submitted",
  "channel": "sms",
  "enabled": false
}
```
**Channels:** `in_app`, `push`, `sms`, `whatsapp`, `email`
**Wildcards:** Use `grm.*` to control all GRM notifications at once.
**Response (200):**
```json
{
  "message": "Preference disabled for grm.feedback.submitted on sms.",
  "notification_type": "grm.feedback.submitted",
  "channel": "sms",
  "enabled": false
}
```

#### DELETE /notification-preferences/{notification_type}/{channel}
**Summary:** Reset a preference to default (remove opt-out)
**Auth:** X-User-Id header
**Response (200):**
```json
{ "message": "Preference reset to default (enabled)." }
```
**Errors:** 404 if preference not found.

### 5.2.3 Push Devices

#### POST /devices
**Summary:** Register a push notification device token
**Auth:** X-User-Id header
**Request Body:**
```json
{
  "platform": "fcm",
  "push_token": "dGVzdC10b2tlbi0xMjM...",
  "device_name": "Samsung Galaxy S24",
  "app_version": "1.2.0"
}
```
**Platforms:** `fcm` (Android/Web), `apns` (iOS)
**Response (201):**
```json
{
  "id": "uuid",
  "platform": "fcm",
  "device_name": "Samsung Galaxy S24",
  "is_active": true,
  "registered_at": "2025-06-15T10:00:00+00:00"
}
```

#### GET /devices
**Summary:** List registered devices for the current user
**Auth:** X-User-Id header
**Response (200):** Array of device objects.

#### PATCH /devices/{device_id}/token
**Summary:** Update push token for a device
**Auth:** X-User-Id header
**Request Body:**
```json
{
  "push_token": "new-token-abc123...",
  "app_version": "1.3.0"
}
```
**Response (200):** Updated device object.
**Errors:** 404 if device not found.

#### DELETE /devices/{device_id}
**Summary:** Deregister a push device (logout / uninstall)
**Auth:** X-User-Id header
**Response (200):**
```json
{ "message": "Device deregistered. Push notifications will no longer be sent to this device." }
```

### 5.2.4 Templates (Admin)

All template endpoints require **X-Service-Key** header (internal service secret).

#### GET /templates
**Summary:** List notification templates
**Auth:** Service Key
**Query Parameters:** `notification_type`, `channel`, `language`
**Response (200):** Array of template objects.

#### PUT /templates
**Summary:** Create or update a notification template
**Auth:** Service Key
**Request Body:**
```json
{
  "notification_type": "grm.feedback.acknowledged",
  "channel": "sms",
  "language": "sw",
  "title_template": null,
  "subject_template": null,
  "body_template": "Malalamiko yako {{ feedback_ref }} yamekubaliwa. Mradi: {{ project_name }}. Majibu yatatolewa kabla ya {{ target_resolution_date }}.",
  "is_active": true
}
```
**Response (200):** Upserted template object.

#### DELETE /templates/{template_id}
**Summary:** Delete a template
**Auth:** Service Key
**Response (200):**
```json
{ "message": "Template deleted." }
```
**Errors:** 404 if not found.

### 5.2.5 Internal Dispatch (Service-to-Service)

Alternative to Kafka for synchronous dispatch (e.g. OTP flows).

#### POST /internal/dispatch
**Summary:** Dispatch a notification (HTTP alternative to Kafka)
**Auth:** X-Service-Key header
**Request Body:**
```json
{
  "notification_type": "auth.login.otp_requested",
  "recipient_user_id": "uuid",
  "recipient_phone": "+255712345678",
  "recipient_email": null,
  "recipient_push_tokens": [],
  "language": "en",
  "variables": {"otp_code": "123456", "expires_minutes": 5},
  "preferred_channels": ["sms"],
  "priority": "critical",
  "idempotency_key": "auth:uuid:login_otp:2025-06-15",
  "scheduled_at": null,
  "source_service": "riviwa_auth_service",
  "source_entity_id": "uuid",
  "metadata": {}
}
```
**Response (202):**
```json
{
  "notification_id": "uuid",
  "accepted": true
}
```
**Idempotent:** Duplicate requests with same `idempotency_key` return existing notification_id.

#### POST /internal/dispatch/batch
**Summary:** Dispatch multiple notifications in one request
**Auth:** X-Service-Key header
**Request Body:** Array of `NotificationDispatchRequest` objects.
**Response (202):**
```json
{
  "accepted": 10,
  "results": [
    {"notification_id": "uuid"},
    {"notification_id": "uuid"}
  ]
}
```

### 5.2.6 Provider Webhooks (DLR)

All webhook endpoints are hidden from OpenAPI (`include_in_schema=False`).

| Endpoint | Provider | Format | Status Mapping |
|----------|----------|--------|----------------|
| `POST /webhooks/sms/at/dlr` | Africa's Talking | form-encoded | Success->delivered, Failed/Rejected->failed, Buffered->no change |
| `POST /webhooks/sms/twilio/dlr` | Twilio | form-encoded | delivered->delivered, undelivered/failed->failed, sent->sent |
| `POST /webhooks/email/sendgrid` | SendGrid | JSON array | delivered->delivered, bounce/dropped/spam_report->failed |
| `POST /webhooks/whatsapp/meta` | Meta Cloud API | JSON | delivered->delivered, read->delivered, failed->failed |
| `GET /webhooks/whatsapp/meta` | Meta Cloud API | query params | hub.challenge verification for webhook registration |

---

## 5.3 Notification Channels

### In-App (`in_app`)
- **Provider:** None (internal)
- **Implementation:** No external dispatch. The delivery record in the database IS the notification. Clients poll `GET /notifications` or use SSE. Read receipts via `PATCH /notifications/deliveries/{id}/read`.
- **Always available:** No credentials needed.

### Push (`push`)
- **Provider:** Firebase Cloud Messaging (FCM) for Android/Web. APNs proxied through FCM for iOS.
- **Configuration:** `FCM_SERVICE_ACCOUNT_JSON`, `FCM_PROJECT_ID`
- **Token source:** `notification_devices` table. Clients register via `POST /devices`.
- **Priority mapping:** critical/high -> FCM HIGH + apns-priority 10; medium/low -> FCM NORMAL + apns-priority 5.
- **Invalid tokens:** `UnregisteredError` -> permanent_fail (token must be removed from devices table).
- **Multi-device:** Push sent to all active tokens for the user.

### SMS (`sms`)
- **Primary provider:** Africa's Talking (preferred for Tanzania/East Africa -- lower latency, local number support)
- **Fallback provider:** Twilio
- **Configuration:** `AT_API_KEY`, `AT_USERNAME`, `AT_SENDER_ID` (primary); `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` (fallback)
- **DLR:** Africa's Talking posts to `/webhooks/sms/at/dlr`; Twilio posts to `/webhooks/sms/twilio/dlr`.
- **Message length:** 160 chars (GSM-7) or 70 chars (Unicode/Swahili) for single SMS. Longer messages auto-split.

### WhatsApp (`whatsapp`)
- **Provider:** Meta Cloud API v18+
- **Configuration:** `META_WHATSAPP_TOKEN`, `META_WHATSAPP_PHONE_ID`
- **Template messages:** All outbound notifications use pre-approved WhatsApp Business Templates (required for non-session messages). The `notification_type` maps to a template name in the DB.
- **Free-form messages:** Only within 24-hour customer service window.
- **DLR:** Meta posts status updates to `/webhooks/whatsapp/meta`.
- **Permanent failures:** Code 131026 (not on WhatsApp), 131047 (re-engagement needed).

### Email (`email`)
- **Primary provider:** SendGrid
- **Fallback provider:** SMTP
- **Configuration:** `SENDGRID_API_KEY` (primary); `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS` (fallback)
- **Content:** `body_template` contains HTML. Plain-text version auto-derived by stripping HTML tags.
- **DLR:** SendGrid posts event batches to `/webhooks/email/sendgrid`.
- **From address:** `EMAIL_FROM`, `EMAIL_FROM_NAME`

### Channel Selection Logic
1. Originating service specifies `preferred_channels` in the notification request.
2. Notification service checks user preferences (opt-outs). CRITICAL priority bypasses preferences.
3. Template availability per channel is checked. If no active template for a channel, delivery is SKIPPED.
4. For each enabled channel, template is rendered with `variables` using Jinja2.
5. Each channel delivery attempt creates a `notification_deliveries` row.
6. Failed deliveries are retried up to 3 times with exponential backoff.

---

# 6. KAFKA DATA FLOW

## 6.1 Topics

| Topic | Owner | Description |
|-------|-------|-------------|
| `riviwa.user.events` | Auth Service | User lifecycle events |
| `riviwa.organisation.events` / `riviwa.org.events` | Auth Service | Organisation, OrgProject, OrgProjectStage, OrgService lifecycle |
| `riviwa.auth.events` | Auth Service | Login, logout, token events |
| `riviwa.fraud.events` | Auth Service | Fraud scoring, ID verification |
| `riviwa.feedback.events` | Feedback Service | Feedback lifecycle (submitted, acknowledged, escalated, resolved, etc.) |
| `riviwa.stakeholder.events` | Stakeholder Service | Stakeholder, contact, activity, attendance, communication events |
| `riviwa.payment.events` | Payment Service | Payment lifecycle (initiated, completed, failed, refunded) |
| `riviwa.notifications` | All services (publish) / Notification Service (consume) | Notification dispatch requests |
| `riviwa.notifications.events` | Notification Service | Delivery receipts (sent, failed, read) |

## 6.2 Event Envelope Format

All services use a standard envelope:

```json
{
  "event_type":     "user.registered",
  "event_id":       "uuid4",
  "occurred_at":    "2025-06-15T10:30:00.000000Z",
  "schema_version": "1.0",
  "service":        "riviwa_auth_service",
  "payload":        { }
}
```

- `event_id` -- consumers use for idempotent deduplication
- At-least-once delivery with `acks=all`, `enable_idempotence=True`
- Fire-and-forget: Kafka publish failures are logged but never raise to callers

## 6.3 Auth Service Publishes

### Topic: `riviwa.user.events`
| Event Type | Payload Key | Consumers |
|------------|-------------|-----------|
| `user.registered` | user_id, username, email, phone_number, status, method, country_code | Stakeholder, Notification |
| `user.registered_social` | user_id, username, email, oauth_provider | Stakeholder, Notification |
| `user.registration_blocked` | email (hashed), ip_address, fraud_score | -- |
| `user.email_verified` | user_id, email | -- |
| `user.phone_verified` | user_id, phone_number | -- |
| `user.profile_updated` | user_id, changed_fields | Stakeholder (syncs contact fields) |
| `user.suspended` | user_id, status, reason | Stakeholder (nulls contact.user_id), Feedback |
| `user.banned` | user_id, status, reason | Stakeholder, Feedback |
| `user.deactivated` | user_id, status, reason | Stakeholder, Feedback |
| `user.reactivated` | user_id, status | Stakeholder (logged, no auto-restore) |
| `user.password_changed` | user_id, all_sessions_revoked | -- |
| `user.avatar_updated` | user_id | -- |

### Topic: `riviwa.organisation.events` / `riviwa.org.events`
| Event Type | Payload Key | Consumers |
|------------|-------------|-----------|
| `organisation.created` | org_id, slug, legal_name, org_type, status | -- |
| `organisation.updated` | org_id, changed_fields, logo_url | Stakeholder (syncs org_logo_url to ProjectCache) |
| `organisation.verified` | org_id, verified_by_id | -- |
| `organisation.suspended` | org_id, status, reason | -- |
| `organisation.member_added` | org_id, user_id, org_role | -- |
| `organisation.invite_sent` | org_id, invited_email, invited_role | -- |
| `organisation.invite_accepted` | org_id, user_id, invite_id | -- |
| `org_project.published` | id (project UUID), name, slug, organisation_id, status, category, accepts_* | Stakeholder (upsert ProjectCache), Feedback (upsert fb_projects) |
| `org_project.updated` | id, all project fields, changed_fields | Stakeholder, Feedback |
| `org_project.paused` | id, status="paused" | Stakeholder, Feedback |
| `org_project.resumed` | id, status="active" | Stakeholder, Feedback |
| `org_project.completed` | id, status="completed" | Stakeholder, Feedback |
| `org_project.cancelled` | id, status="cancelled" | Stakeholder, Feedback |
| `org_project_stage.activated` | stage_id, project_id, name, stage_order, accepts_* | Stakeholder, Feedback |
| `org_project_stage.completed` | stage_id, project_id | Stakeholder, Feedback |
| `org_project_stage.skipped` | stage_id, project_id | Stakeholder, Feedback |

### Topic: `riviwa.auth.events`
| Event Type | Payload |
|------------|---------|
| `auth.login_success` | user_id, ip_address, user_agent |
| `auth.login_failed` | identifier_hash (SHA256[:16]), ip_address, reason |
| `auth.login_locked` | user_id, ip_address |
| `auth.logout` | user_id, jti |
| `auth.token_refreshed` | user_id, ip_address |
| `auth.dashboard_switched` | user_id, org_id, view |

### Topic: `riviwa.fraud.events`
| Event Type | Payload |
|------------|---------|
| `fraud.score_computed` | user_id, total_score, action, details |
| `fraud.id_verification_passed` | user_id, provider |
| `fraud.id_verification_failed` | user_id, provider, rejection_reason |

## 6.4 Feedback Service Publishes

### Topic: `riviwa.feedback.events`
| Event Type | Payload | Consumers |
|------------|---------|-----------|
| `feedback.submitted` | feedback_id, project_id, feedback_type, category, stakeholder_engagement_id, distribution_id | Stakeholder (links feedback_ref_id to engagement/distribution) |
| `feedback.acknowledged` | feedback_id, project_id, priority | -- |
| `feedback.escalated` | feedback_id, project_id, from_level, to_level, reason | -- |
| `feedback.resolved` | feedback_id, project_id | Stakeholder |
| `feedback.appealed` | feedback_id, project_id, grounds | -- |
| `feedback.summary.daily` | -- | -- |

**Feedback Service Consumes:**

| Topic | Events | Action |
|-------|--------|--------|
| `riviwa.org.events` | `org_project.*`, `org_project_stage.*` | Upsert/update fb_projects and fb_project_stages cache |
| `riviwa.user.events` | `user.deactivated/suspended/banned` | Null user_id columns on feedback records |
| `riviwa.stakeholder.events` | `engagement.concern.raised` | Auto-create Suggestion feedback from consultation concerns |
| `riviwa.stakeholder.events` | `communication.concerns.pending` | Auto-create Suggestion feedback from distribution concerns |

## 6.5 Stakeholder Service Publishes

### Topic: `riviwa.stakeholder.events`
| Event Type | Payload | Consumers |
|------------|---------|-----------|
| `stakeholder.registered` | stakeholder_id, entity_type, category | -- |
| `stakeholder.updated` | stakeholder_id, changed_fields | -- |
| `stakeholder.deactivated` | stakeholder_id | -- |
| `stakeholder.contact.added` | stakeholder_id, contact_id, is_primary | -- |
| `stakeholder.contact.deactivated` | stakeholder_id, contact_id | -- |
| `stakeholder.stage_engagement.set` | -- | -- |
| `stakeholder.stage_engagement.updated` | -- | -- |
| `engagement.activity.planned` | -- | -- |
| `engagement.activity.conducted` | activity_id, project_id, stage, actual_count | -- |
| `engagement.activity.cancelled` | -- | -- |
| `engagement.attendance.logged` | -- | -- |
| `engagement.concern.raised` | activity_id, contact_id, stakeholder_id, project_id, concerns | Feedback (auto-creates Suggestion) |
| `communication.sent` | -- | -- |
| `communication.distribution.logged` | -- | -- |
| `communication.concerns.pending` | distribution_id, comm_id, contact_id, project_id, concerns | Feedback (auto-creates Suggestion) |

**Stakeholder Service Consumes:**

| Topic | Events | Action |
|-------|--------|--------|
| `riviwa.org.events` | `org_project.*` | Upsert/update ProjectCache |
| `riviwa.org.events` | `org_project_stage.*` | Upsert/update ProjectStageCache |
| `riviwa.org.events` | `organisation.updated` (with logo_url) | Sync org_logo_url to all ProjectCache rows for that org |
| `riviwa.user.events` | `user.registered`, `user.registered_social` | Auto-link StakeholderContact.user_id by email/phone match |
| `riviwa.user.events` | `user.profile_updated` | Sync changed fields (email, phone, full_name) to linked contact |
| `riviwa.user.events` | `user.deactivated/suspended/banned` | Null StakeholderContact.user_id |
| `riviwa.feedback.events` | `feedback.submitted` | Link feedback_ref_id to engagement and/or distribution records |

## 6.6 Payment Service Publishes

### Topic: `riviwa.payment.events`
| Event Type | Payload | Consumers |
|------------|---------|-----------|
| `payment.initiated` | payment_id, provider, amount, currency, payment_type, payer_user_id, org_id, project_id, reference_id, reference_type | Notification Service |
| `payment.completed` | payment_id, provider, amount | Notification Service |
| `payment.failed` | payment_id, reason | Notification Service |
| `payment.refunded` | payment_id, amount | Notification Service |
| `payment.expired` | payment_id | -- |

## 6.7 Notification Service

### Consumes from: `riviwa.notifications`
All other services publish notification requests to this topic. Consumer group: `notification_service_group`.

**Request envelope format:**
```json
{
  "notification_type":    "grm.feedback.acknowledged",
  "recipient_user_id":    "uuid|null",
  "recipient_phone":      "+255...|null",
  "recipient_email":      "user@example.com|null",
  "recipient_push_tokens": [],
  "language":             "sw",
  "variables":            {"feedback_ref": "GRV-2025-0041", "project_name": "Msimbazi"},
  "preferred_channels":   ["push", "sms"],
  "priority":             "high",
  "idempotency_key":      "feedback:uuid:acknowledged:2025-06-15",
  "scheduled_at":         null,
  "source_service":       "feedback_service",
  "source_entity_id":     "uuid",
  "metadata":             {}
}
```

### Publishes to: `riviwa.notifications.events`
Delivery receipts: sent, failed, read.

## 6.8 Cross-Service Data Flow Diagram

```
                        Auth Service (8000)
                        Publishes to:
                          riviwa.user.events
                          riviwa.org.events
                          riviwa.auth.events
                          riviwa.fraud.events
                              |
          +-------------------+--------------------+
          |                   |                    |
          v                   v                    v
  Feedback Service     Stakeholder Service    (Other consumers)
     (8090)                (8070)
  Consumes:             Consumes:
    org.events            org.events
    user.events           user.events
    stakeholder.events    feedback.events
  Publishes:            Publishes:
    feedback.events       stakeholder.events
          |                   |
          +-------------------+
          |                   |
          v                   v
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚     riviwa.notifications            â”‚ <â”€â”€ All services publish here
  â”‚     (Notification Requests)         â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                  |
                  v
        Notification Service (8060)
        Consumes: riviwa.notifications
        Delivers via: in_app, push, sms, whatsapp, email
        Publishes: riviwa.notifications.events

  Payment Service (8080)
  Publishes: riviwa.payment.events
  (consumed by Notification Service for payment confirmations)
```

## 6.9 Notification Types (Complete Registry)

### Authentication
| Type | Priority | Channels | Variables |
|------|----------|----------|-----------|
| `auth.registration.otp_requested` | critical | sms or email | otp_code, expires_minutes |
| `auth.login.otp_requested` | critical | sms or email | otp_code, expires_minutes |
| `auth.password_reset.otp_requested` | critical | sms or email | otp_code, expires_minutes |
| `auth.channel_login.otp_requested` | critical | sms or email | otp_code, expires_minutes |
| `auth.password.changed` | high | push, sms, email, in_app | -- |
| `auth.social.password_set` | medium | push, in_app | -- |
| `system.welcome` | low | push, in_app | display_name |
| `system.account_verified` | high | push, sms, email, in_app | -- |
| `system.account_suspended` | high | push, sms, email, in_app | reason |
| `system.account_banned` | high | push, sms, email, in_app | reason |
| `system.account_reactivated` | high | push, sms, email, in_app | -- |

### GRM (Feedback)
| Type | Priority | Channels | Variables |
|------|----------|----------|-----------|
| `grm.feedback.submitted` | medium | sms, push, in_app | feedback_ref, project_name, feedback_type |
| `grm.feedback.acknowledged` | high | sms, push, in_app | feedback_ref, project_name, target_resolution_date |
| `grm.feedback.assigned` | medium | push, in_app | -- |
| `grm.feedback.escalated` | high | push, in_app | -- |
| `grm.feedback.resolved` | high | sms, push, in_app | feedback_ref, project_name, resolution_summary |
| `grm.feedback.closed` | medium | push, in_app | -- |
| `grm.feedback.dismissed` | medium | push, in_app | -- |
| `grm.feedback.appeal_filed` | high | push, in_app | -- |
| `grm.feedback.appeal_resolved` | high | push, in_app | -- |
| `grm.feedback.sla_breach_warning` | high | push, in_app | feedback_ref, project_name, priority, hours_overdue |
| `grm.feedback.comment_added` | medium | push, in_app | -- |
| `grm.escalation_request.received` | high | push, in_app | -- |
| `grm.escalation_request.approved` | high | push, in_app | -- |
| `grm.escalation_request.rejected` | high | push, in_app | -- |

### Projects
| Type | Priority | Channels | Variables |
|------|----------|----------|-----------|
| `project.activated` | medium | push, in_app | project_name, project_code |
| `project.paused` | medium | push, in_app | -- |
| `project.resumed` | medium | push, in_app | -- |
| `project.completed` | medium | push, in_app | -- |
| `project.stage.activated` | medium | push, in_app | -- |
| `project.stage.completed` | medium | push, in_app | -- |

### Checklists
| Type | Priority | Channels | Variables |
|------|----------|----------|-----------|
| `project.checklist.item_due_soon` | medium | push, in_app | item_title, due_date, entity_name, days_remaining |
| `project.checklist.item_overdue` | high | push, sms, in_app | item_title, due_date, entity_name, days_overdue |
| `project.checklist.item_done` | low | in_app | -- |

### Activities
| Type | Priority | Channels | Variables |
|------|----------|----------|-----------|
| `activity.reminder` | medium | push, in_app | activity_title, venue, scheduled_at |
| `activity.conducted` | low | in_app | -- |
| `activity.cancelled` | medium | push, in_app | -- |

### Stakeholders
| Type | Priority | Channels | Variables |
|------|----------|----------|-----------|
| `stakeholder.concern_auto_created` | medium | push, in_app | -- |

### Payments
| Type | Priority | Channels | Variables |
|------|----------|----------|-----------|
| `payment.initiated` | medium | push, in_app | -- |
| `payment.confirmed` | high | sms, push, in_app | amount, currency, description |
| `payment.failed` | high | sms, push, in_app | amount, currency, reason |
| `payment.refunded` | high | sms, push, in_app | -- |

### Organisations
| Type | Priority | Channels | Variables |
|------|----------|----------|-----------|
| `org.invite.received` | medium | email | org_name, role, inviter_name |
| `org.invite.accepted` | low | in_app | -- |
| `org.member.role_changed` | medium | push, in_app | -- |
| `org.ownership.transferred` | high | push, email, in_app | -- |