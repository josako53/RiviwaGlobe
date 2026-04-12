# Riviwa API Reference

**Version:** 2026-04-08  
**Base URL (production):** `https://api.riviwa.com`  
**Base URL (local dev):** `http://localhost`

---

## Table of Contents

1. [Authentication & Conventions](#1-authentication--conventions)
2. [Auth Service](#2-auth-service--port-8000)
   - [Registration](#21-registration-3-step)
   - [Login](#22-login-2-step)
   - [Token Management](#23-token-management)
   - [Social Auth](#24-social-auth)
   - [Password](#25-password)
   - [User Profile](#26-user-profile)
   - [Organisations](#27-organisations)
3. [Feedback Service](#3-feedback-service--port-8090)
   - [PAP Self-Service](#31-pap-self-service)
   - [Staff Feedback Management](#32-staff-feedback-management)
   - [Escalation Requests](#33-escalation-requests-staff)
   - [Categories](#34-categories)
   - [Committees](#35-committees-ghc)
4. [AI Service (Riviwa AI)](#4-ai-service-rivai--port-8085)
   - [Conversational AI](#41-conversational-ai)
   - [AI Admin](#42-ai-admin-staff)
   - [AI Internal](#43-ai-internal-service-to-service)
5. [Stakeholder Service](#5-stakeholder-service--port-8070)
   - [Stakeholders](#51-stakeholders)
   - [Contacts](#52-contacts)
   - [Activities](#53-activities)
   - [Communications](#54-communications)
   - [Focal Persons](#55-focal-persons)
6. [Recommendation Service](#6-recommendation-service--port-8055)
7. [Notification Service](#7-notification-service--port-8060)
   - [Inbox](#71-inbox)
   - [Preferences](#72-preferences)
   - [Devices](#73-devices-push-tokens)
   - [Templates](#74-templates-admin)
   - [Internal Dispatch](#75-internal-dispatch)

---

## 1. Authentication & Conventions

### Bearer Token

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

### JWT Payload Structure
```json
{
  "sub":           "user-uuid",
  "jti":           "token-uuid",
  "iat":           1700000000,
  "exp":           1700001800,
  "org_id":        "org-uuid | null",
  "org_role":      "owner | admin | manager | member | null",
  "platform_role": "super_admin | admin | moderator | null"
}
```

### Org Roles
| Role | Description |
|------|-------------|
| `owner` | Full access, can delete org and transfer ownership |
| `admin` | Full org management except deletion |
| `manager` | Can manage feedback, members; limited org settings |
| `member` | Read-only access to org resources |

### Notification Service Auth
The notification service uses `X-User-Id` header (UUID string) instead of Bearer.  
Nginx/gateway extracts this from the JWT and sets it automatically.  
For direct calls: `X-User-Id: <user-uuid>`

### Internal Service-to-Service
Services call each other with:
```
X-Service-Key: <INTERNAL_SERVICE_KEY>
```
These endpoints are hidden from public API docs.

### Password Policy
- Minimum 8 characters
- At least 1 uppercase letter (A–Z)
- At least 1 lowercase letter (a–z)
- At least 1 digit (0–9)
- At least 1 special character (`!@#$%^&*` etc.)

### Common Error Responses
```json
{ "detail": "Not authenticated." }                  // 401
{ "detail": "You do not have permission." }         // 403
{ "detail": "Not found." }                          // 404
{ "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }  // 422 validation
```

---

## 2. Auth Service — Port 8000

### 2.1 Registration (3-step)

#### Step 1 — Initiate
```
POST /api/v1/auth/register/init
Auth: none
```

**Request body:**
```json
{
  "email": "alice@example.com",
  "phone_number": "+255712345678",
  "first_name": "Alice",
  "last_name": "Smith",
  "device_fingerprint": "optional-client-fingerprint"
}
```
> Provide **either** `email` **or** `phone_number` — not both.

**Response `200`:**
```json
{
  "registration_token": "reg:abc123...",
  "otp_channel": "email",
  "otp_destination": "al***@example.com",
  "expires_in_seconds": 600
}
```

---

#### Step 2 — Verify OTP
```
POST /api/v1/auth/register/verify-otp
Auth: none
```

**Request body:**
```json
{
  "registration_token": "reg:abc123...",
  "otp_code": "483920"
}
```

**Response `200`:**
```json
{
  "registration_token": "reg:abc123...",
  "message": "OTP verified. Proceed to complete registration."
}
```

---

#### Step 3 — Complete
```
POST /api/v1/auth/register/complete
Auth: none
```

**Request body:**
```json
{
  "registration_token": "reg:abc123...",
  "password": "MyP@ssw0rd!",
  "confirm_password": "MyP@ssw0rd!",
  "username": "alice_smith",
  "first_name": "Alice",
  "last_name": "Smith"
}
```
> `username` is optional — auto-generated from name/email if omitted.

**Response `201`:**
```json
{
  "message": "Account created successfully.",
  "user_id": "uuid",
  "is_new_user": true,
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "opaque-uuid",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

---

#### Resend OTP
```
POST /api/v1/auth/register/resend-otp
Auth: none
```

**Request body:**
```json
{
  "session_token": "reg:abc123..."
}
```

**Response `200`:**
```json
{
  "message": "A new OTP has been sent.",
  "otp_channel": "email",
  "otp_destination": "al***@example.com",
  "resends_remaining": 2
}
```

---

### 2.2 Login (2-step)

#### Step 1 — Credentials
```
POST /api/v1/auth/login
Auth: none
```

**Request body:**
```json
{
  "identifier": "alice@example.com",
  "password": "MyP@ssw0rd!",
  "device_fingerprint": "optional"
}
```
> `identifier` accepts email or E.164 phone number.

**Response `200`:**
```json
{
  "login_token": "login:xyz789...",
  "otp_channel": "email",
  "otp_destination": "al***@example.com",
  "expires_in_seconds": 300
}
```

---

#### Step 2 — Verify OTP
```
POST /api/v1/auth/login/verify-otp
Auth: none
```

**Request body:**
```json
{
  "login_token": "login:xyz789...",
  "otp_code": "193847"
}
```

**Response `200`:** → `TokenResponse` (same shape as `register/complete`)

---

### 2.3 Token Management

#### Refresh Token
```
POST /api/v1/auth/token/refresh
Auth: none
```

**Request body:**
```json
{
  "refresh_token": "opaque-uuid"
}
```

**Response `200`:** → `TokenResponse`

---

#### Logout
```
POST /api/v1/auth/token/logout
Auth: Bearer
```

**Request body:**
```json
{
  "refresh_token": "opaque-uuid"
}
```

**Response `200`:**
```json
{ "message": "Logged out successfully." }
```

---

#### Switch Org Dashboard
```
POST /api/v1/auth/switch-org
Auth: Bearer
```

**Request body:**
```json
{
  "org_id": "uuid-or-null"
}
```
> Pass `null` to return to personal view.

**Response `200`:**
```json
{
  "message": "Dashboard context switched.",
  "tokens": { "...TokenResponse" },
  "org_id": "uuid",
  "org_role": "admin"
}
```

---

### 2.4 Social Auth

#### Login / Register via OAuth
```
POST /api/v1/auth/social
Auth: none
```

**Request body:**
```json
{
  "provider": "google",
  "id_token": "provider-sdk-id-token",
  "device_fingerprint": "optional"
}
```
> `provider`: `google` | `apple` | `facebook`

**Response `200`:**
```json
{
  "message": "Social authentication successful.",
  "user_id": "uuid",
  "is_new_user": false,
  "has_password": false,
  "tokens": { "...TokenResponse" }
}
```

---

#### Set Password on Social Account
```
POST /api/v1/auth/social/set-password
Auth: Bearer
```

**Request body:**
```json
{
  "password": "MyP@ssw0rd!",
  "confirm_password": "MyP@ssw0rd!"
}
```

**Response `200`:**
```json
{ "message": "Password set successfully." }
```

---

### 2.5 Password

#### Forgot Password — Step 1
```
POST /api/v1/auth/password/forgot
Auth: none
```

**Request body:**
```json
{
  "identifier": "alice@example.com",
  "device_fingerprint": "optional"
}
```
> Always returns `200` — prevents account enumeration.

**Response `200`:**
```json
{
  "reset_token": "pwd_reset:...",
  "otp_channel": "email",
  "otp_destination": "al***@example.com",
  "expires_in_seconds": 600,
  "message": "If an account with that identifier exists, a verification code has been sent."
}
```

---

#### Forgot Password — Step 2 (Verify OTP)
```
POST /api/v1/auth/password/forgot/verify-otp
Auth: none
```

**Request body:**
```json
{
  "reset_token": "pwd_reset:...",
  "otp_code": "920384"
}
```

**Response `200`:**
```json
{
  "reset_token": "pwd_reset:...",
  "message": "OTP verified. You may now set a new password."
}
```

---

#### Forgot Password — Step 3 (Reset)
```
POST /api/v1/auth/password/forgot/reset
Auth: none
```

**Request body:**
```json
{
  "reset_token": "pwd_reset:...",
  "new_password": "NewP@ss1!",
  "confirm_new_password": "NewP@ss1!"
}
```

**Response `200`:**
```json
{ "message": "Password reset successfully. Please log in." }
```

---

#### Change Password (Authenticated)
```
POST /api/v1/auth/password/change
Auth: Bearer
```

**Request body:**
```json
{
  "current_password": "OldP@ss1!",
  "new_password": "NewP@ss1!",
  "confirm_new_password": "NewP@ss1!"
}
```

**Response `200`:**
```json
{ "message": "Password changed." }
```

---

### 2.6 User Profile

#### Get My Profile
```
GET /api/v1/users/me
Auth: Bearer
```

**Response `200`:**
```json
{
  "id": "uuid",
  "username": "alice_smith",
  "email": "alice@example.com",
  "phone_number": null,
  "is_email_verified": true,
  "phone_verified": false,
  "id_verified": false,
  "display_name": "Alice S.",
  "full_name": "Alice Smith",
  "avatar_url": null,
  "date_of_birth": "1990-07-15",
  "gender": "female",
  "country_code": "TZ",
  "language": "sw",
  "status": "active",
  "oauth_provider": null,
  "has_password": true,
  "two_factor_enabled": true,
  "active_org_id": null,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-04-08T00:00:00Z",
  "last_login_at": "2026-04-08T08:00:00Z"
}
```

---

#### Update My Profile
```
PATCH /api/v1/users/me
Auth: Bearer
```

**Request body** (all fields optional):
```json
{
  "username": "new_handle",
  "display_name": "Alice S.",
  "full_name": "Alice Smith",
  "date_of_birth": "1990-07-15",
  "gender": "female",
  "country_code": "TZ",
  "language": "sw"
}
```

**Response `200`:** → `UserPrivateResponse` (same as GET /me)

---

#### Update Avatar
```
POST /api/v1/users/me/avatar
Auth: Bearer
```

**Request body:**
```json
{
  "avatar_url": "https://cdn.riviwa.com/avatars/uuid.jpg"
}
```
> Pass `null` to clear the avatar.

---

#### Account Actions
```
DELETE /api/v1/users/me                        → deactivate own account
POST   /api/v1/users/{user_id}/suspend         → [Admin] suspend user
POST   /api/v1/users/{user_id}/ban             → [Admin] ban user
POST   /api/v1/users/{user_id}/reactivate      → [Admin] reactivate user
```

All admin actions accept an optional body: `{ "reason": "..." }`

---

### 2.7 Organisations

#### Create Organisation
```
POST /api/v1/orgs
Auth: Bearer
```

**Request body:**
```json
{
  "legal_name": "Tanzania Roads Authority",
  "display_name": "TANROADS",
  "slug": "tanroads",
  "org_type": "government",
  "description": "National roads authority of Tanzania.",
  "logo_url": null,
  "website_url": "https://tanroads.go.tz",
  "support_email": "info@tanroads.go.tz",
  "support_phone": "+255222865063",
  "country_code": "TZ",
  "timezone": "Africa/Dar_es_Salaam",
  "registration_number": "GOV-001",
  "tax_id": null,
  "max_members": 100
}
```
> `slug`: lowercase letters, digits, hyphens only (e.g. `tanroads-tz`)

**Response `201`:**
```json
{
  "id": "uuid",
  "slug": "tanroads",
  "legal_name": "Tanzania Roads Authority",
  "display_name": "TANROADS",
  "org_type": "government",
  "status": "pending",
  "is_verified": false,
  "description": "...",
  "logo_url": null,
  "website_url": "...",
  "support_email": "...",
  "support_phone": "...",
  "country_code": "TZ",
  "timezone": "Africa/Dar_es_Salaam",
  "registration_number": "GOV-001",
  "tax_id": null,
  "max_members": 100,
  "created_at": "..."
}
```

---

#### List / Get / Update / Delete
```
GET    /api/v1/orgs                    → my organisations
GET    /api/v1/orgs/{org_id}          → org detail
PATCH  /api/v1/orgs/{org_id}          → update (all fields optional, same shape as create)
DELETE /api/v1/orgs/{org_id}          → deactivate (OWNER only)
```

---

#### Members
```
POST   /api/v1/orgs/{org_id}/members
Auth: Bearer (ADMIN+)
```
**Request body:**
```json
{
  "user_id": "uuid",
  "org_role": "manager"
}
```

```
DELETE /api/v1/orgs/{org_id}/members/{user_id}   → remove member
PATCH  /api/v1/orgs/{org_id}/members/{user_id}/role
```
**PATCH body:**
```json
{ "org_role": "admin" }
```

---

#### Invites
```
POST   /api/v1/orgs/{org_id}/invites
Auth: Bearer
```
**Request body:**
```json
{
  "invited_role": "member",
  "invited_email": "bob@example.com",
  "invited_user_id": null,
  "message": "Welcome to our team!"
}
```
> Provide either `invited_email` **or** `invited_user_id`, not both.

```
POST   /api/v1/orgs/invites/{invite_id}/accept
POST   /api/v1/orgs/invites/{invite_id}/decline
DELETE /api/v1/orgs/{org_id}/invites/{invite_id}  → cancel pending invite
```

---

#### Ownership Transfer
```
POST /api/v1/orgs/{org_id}/transfer-ownership
Auth: Bearer (OWNER)
```
**Request body:**
```json
{ "new_owner_id": "uuid" }
```

---

#### Admin Actions
```
POST /api/v1/orgs/{org_id}/verify    → [Admin] verify org
POST /api/v1/orgs/{org_id}/suspend   → [Admin] suspend org
POST /api/v1/orgs/{org_id}/ban       → [Admin] ban org
```
All accept: `{ "reason": "optional reason string" }`

---

## 3. Feedback Service — Port 8090

### 3.1 PAP Self-Service

#### Submit Feedback
```
POST /api/v1/my/feedback
Auth: Bearer (PAP)
```

**Request body:**
```json
{
  "feedback_type": "grievance",
  "description": "Construction crew has blocked the only road to my shop since Monday.",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "issue_location_description": "Near Kariakoo market, next to the blue gate",
  "project_id": null,
  "category": null,
  "subject": null,
  "is_anonymous": false,
  "submitter_name": "Juma Bakari",
  "submitter_phone": "+255787654321",
  "date_of_incident": "2026-04-01",
  "issue_gps_lat": -6.7924,
  "issue_gps_lng": 39.2083,
  "media_urls": ["https://cdn.riviwa.com/evidence/photo1.jpg"]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `feedback_type` | Yes | `grievance` \| `suggestion` \| `applause` |
| `description` | Yes | Min 10 chars |
| `issue_lga` | Yes | District/LGA — required for AI project detection |
| `project_id` | No | Omit to let AI auto-detect |
| `category` | No | Omit to let AI auto-classify |
| `subject` | No | Auto-generated from description if omitted |

**Response `201`:**
```json
{
  "feedback_id": "uuid",
  "tracking_number": "GRV-2026-0001",
  "status": "submitted",
  "status_label": "Received — awaiting acknowledgement",
  "feedback_type": "grievance",
  "ai_classified": true,
  "message": "Your grievance has been submitted. Tracking number: GRV-2026-0001. You will be notified when the PIU acknowledges receipt."
}
```

**Response `422` — project not identified (show picker):**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "We could not automatically identify the project for your location. Please select the correct project from the list below.",
  "detail": {
    "error_code": "PROJECT_UNIDENTIFIED",
    "candidate_projects": [
      {
        "project_id": "uuid",
        "name": "Dodoma Road Rehabilitation Project",
        "region": "Dodoma",
        "lga": "Bahi",
        "score": 0.72
      }
    ]
  }
}
```
> When 422 is returned, re-submit with `project_id` set to the user's chosen project.

---

#### List My Submissions
```
GET /api/v1/my/feedback
Auth: Bearer (PAP)
```

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `feedback_type` | string | Filter by type |
| `status` | string | Filter by status |
| `project_id` | UUID | Filter by project |
| `skip` | int | Pagination offset (default 0) |
| `limit` | int | Page size 1–200 (default 50) |

**Response `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "unique_ref": "GRV-2026-0001",
      "feedback_type": "grievance",
      "category": "road_access",
      "subject": "Road blockage near Kariakoo market",
      "channel": "web_portal",
      "status": "acknowledged",
      "status_label": "Acknowledged — under review",
      "current_level": "ward",
      "priority": "medium",
      "submitted_at": "2026-04-01T10:00:00Z",
      "resolved_at": null,
      "project_id": "uuid"
    }
  ],
  "count": 1
}
```

---

#### Dashboard Summary
```
GET /api/v1/my/feedback/summary
Auth: Bearer (PAP)
```

**Query params:** `?project_id=uuid` (optional)

**Response `200`:**
```json
{
  "total": 8,
  "open": 4,
  "resolved": 3,
  "closed": 1,
  "by_type": [
    { "type": "grievance", "count": 5 },
    { "type": "suggestion", "count": 2 },
    { "type": "applause", "count": 1 }
  ],
  "by_status": [
    { "status": "submitted", "label": "Received — awaiting acknowledgement", "count": 2 },
    { "status": "acknowledged", "label": "Acknowledged — under review", "count": 2 }
  ],
  "pending_escalation_requests": 1
}
```

---

#### Tracking Detail
```
GET /api/v1/my/feedback/{feedback_id}
Auth: Bearer (PAP)
```

**Response `200`:**
```json
{
  "id": "uuid",
  "unique_ref": "GRV-2026-0001",
  "feedback_type": "grievance",
  "category": "road_access",
  "subject": "Road blockage near Kariakoo market",
  "description": "Construction crew has blocked the only road...",
  "channel": "web_portal",
  "submission_method": null,
  "is_anonymous": false,
  "project_id": "uuid",
  "current_level": "ward",
  "priority": "medium",
  "status": "in_review",
  "status_label": "Under investigation",
  "issue_location_description": "Near blue gate",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "issue_gps_lat": -6.7924,
  "issue_gps_lng": 39.2083,
  "submitted_at": "2026-04-01T10:00:00Z",
  "acknowledged_at": "2026-04-02T09:00:00Z",
  "target_resolution_date": "2026-04-22T00:00:00Z",
  "resolved_at": null,
  "closed_at": null,
  "hours_open": 48.5,
  "public_actions": [
    {
      "id": "uuid",
      "action_type": "acknowledged",
      "description": "Acknowledged and assigned to field officer.",
      "response_method": null,
      "response_summary": null,
      "performed_at": "2026-04-02T09:00:00Z",
      "performed_by": "PIU / GHC"
    }
  ],
  "escalation_trail": [],
  "resolution": null,
  "appeal": null,
  "escalation_requests": [
    {
      "id": "uuid",
      "reason": "No response for 30 days.",
      "requested_level": "lga_piu",
      "status": "pending",
      "reviewer_notes": null,
      "requested_at": "2026-04-05T00:00:00Z",
      "reviewed_at": null
    }
  ],
  "can_request_escalation": false,
  "can_appeal": false,
  "can_add_comment": true
}
```

---

#### Request Escalation
```
POST /api/v1/my/feedback/{feedback_id}/escalation-request
Auth: Bearer (PAP)
```

**Request body:**
```json
{
  "reason": "The PIU has not responded in over 30 days despite multiple follow-ups."
}
```

**Response `201`:**
```json
{
  "id": "uuid",
  "status": "pending",
  "message": "Your escalation request has been submitted. PIU will review it and either approve (and escalate your case) or explain why escalation is not applicable at this stage."
}
```

---

#### File Appeal
```
POST /api/v1/my/feedback/{feedback_id}/appeal
Auth: Bearer (PAP)
```
> Only available when `can_appeal: true` (status is `resolved` and PAP is not satisfied).

**Request body:**
```json
{
  "appeal_grounds": "The compensation offered is far below the independent market valuation obtained from a licensed surveyor."
}
```

**Response `201`:**
```json
{
  "appeal_id": "uuid",
  "status": "appealed",
  "now_at_level": "lga_piu",
  "message": "Your appeal has been filed. Your case has been escalated to LGA PIU for review. If you remain unsatisfied after the appeal outcome, you have the right to seek resolution through the courts."
}
```

---

#### Add Comment
```
POST /api/v1/my/feedback/{feedback_id}/add-comment
Auth: Bearer (PAP)
```

**Request body:**
```json
{
  "comment": "I can provide the signed lease agreement as additional evidence if required."
}
```

**Response `201`:**
```json
{
  "message": "Your comment has been added and is visible to PIU staff.",
  "action_id": "uuid"
}
```

---

### 3.2 Staff Feedback Management

#### Submit Feedback (Staff)
```
POST /api/v1/feedback
Auth: Bearer (Staff)
```

**Request body (Annex 5 full form):**
```json
{
  "project_id": "uuid",
  "feedback_type": "grievance",
  "category": "compensation",
  "channel": "paper_form",
  "subject": "Unfair compensation for land acquisition",
  "description": "PAP claims the compensation offered for 2 acres is below market rate. Land acquired on 15 Sep 2025.",
  "is_anonymous": false,
  "submitter_name": "Amina Hassan",
  "submitter_phone": "+255712345678",
  "submitter_email": null,
  "submitter_type": "individual",
  "group_size": null,
  "submitter_location_region": "Dar es Salaam",
  "submitter_location_district": "Ilala",
  "submitter_location_lga": "Ilala",
  "submitter_location_ward": "Kariakoo",
  "submitter_location_street": null,
  "submitted_by_user_id": null,
  "submitted_by_stakeholder_id": null,
  "submitted_by_contact_id": null,
  "priority": "high",
  "issue_location_description": "Plot 14, Kariakoo",
  "issue_region": "Dar es Salaam",
  "issue_district": "Ilala",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "issue_mtaa": null,
  "issue_gps_lat": -6.7924,
  "issue_gps_lng": 39.2083,
  "date_of_incident": "2025-09-15",
  "submitted_at": "2025-10-01",
  "media_urls": [],
  "service_location_id": null,
  "stakeholder_engagement_id": null,
  "distribution_id": null,
  "officer_recorded": true,
  "internal_notes": "PAP has supporting documents. Scheduled for valuation review."
}
```

| Field | Required | Options |
|-------|----------|---------|
| `project_id` | Yes | UUID |
| `feedback_type` | Yes | `grievance` \| `suggestion` \| `applause` |
| `category` | Yes | Category slug |
| `channel` | Yes | `sms` \| `whatsapp` \| `phone_call` \| `mobile_app` \| `web_portal` \| `in_person` \| `paper_form` \| `email` \| `public_meeting` \| `notice_box` \| `other` |
| `subject` | Yes | Min 5, max 500 chars |
| `description` | Yes | Min 10 chars |
| `priority` | No | `critical` \| `high` \| `medium` (default) \| `low` |
| `submitted_at` | No | Backdate override (YYYY-MM-DD or ISO) |

---

#### List Feedback
```
GET /api/v1/feedback
Auth: Bearer (Staff)
```

**Query params:**
| Param | Description |
|-------|-------------|
| `project_id` | Filter by project |
| `feedback_type` | `grievance` \| `suggestion` \| `applause` |
| `status` | `submitted` \| `acknowledged` \| `in_review` \| `escalated` \| `resolved` \| `appealed` \| `actioned` \| `noted` \| `dismissed` \| `closed` |
| `priority` | `critical` \| `high` \| `medium` \| `low` |
| `current_level` | GRM level filter |
| `skip` / `limit` | Pagination |

---

#### Lifecycle Actions

**Acknowledge:**
```
PATCH /api/v1/feedback/{feedback_id}/acknowledge
Auth: Bearer (Manager+)
```
```json
{
  "notes": "Acknowledged. Assigned to field officer for investigation.",
  "target_resolution_date": "2026-05-01"
}
```

**Assign:**
```
PATCH /api/v1/feedback/{feedback_id}/assign
Auth: Bearer (Manager+)
```
```json
{
  "assigned_to_user_id": "uuid",
  "assigned_to_committee_id": null,
  "notes": "Assigned to valuation committee."
}
```

**Escalate:**
```
POST /api/v1/feedback/{feedback_id}/escalate
Auth: Bearer (Manager+)
```
```json
{
  "to_level": "lga_piu",
  "reason": "Ward-level committee unable to resolve — requires LGA PIU intervention."
}
```
> GRM levels: `ward` → `lga_piu` → `pcu` → `tarura_wbcu` → `tanroads` → `world_bank`

**Resolve:**
```
POST /api/v1/feedback/{feedback_id}/resolve
Auth: Bearer (Manager+)
```
```json
{
  "resolution_summary": "Compensation amount revised upward to reflect independent valuation.",
  "response_method": "in_person",
  "grievant_satisfied": true,
  "grievant_response": "PAP confirmed satisfaction and signed acknowledgement.",
  "internal_notes": "Valuation committee approved revised amount."
}
```
> `response_method`: `phone_call` \| `email` \| `sms` \| `in_person` \| `letter`

**Close:**
```
PATCH /api/v1/feedback/{feedback_id}/close
Auth: Bearer (Manager+)
```
```json
{ "notes": "Case closed after resolution confirmed by PAP." }
```

**Dismiss:**
```
PATCH /api/v1/feedback/{feedback_id}/dismiss
Auth: Bearer (Admin/Owner)
```
```json
{ "reason": "Outside project scope — relates to a different implementing agency." }
```

---

#### Feedback Detail
```
GET /api/v1/feedback/{feedback_id}
Auth: Bearer (Staff)
```
Returns full feedback record with all actions, escalation trail, resolution, appeal, committee assignments, and escalation requests.

---

#### Internal Endpoints (X-Service-Key only)
```
GET   /api/v1/feedback/by-ref/{unique_ref}   → lookup by tracking number
GET   /api/v1/feedback/{id}/for-ai           → fields for AI classification
PATCH /api/v1/feedback/{id}/ai-enrich        → AI writes back project_id + category
```

**ai-enrich request body:**
```json
{
  "project_id": "uuid",
  "category_def_id": "uuid",
  "category_slug": "road_access",
  "confidence": 0.87,
  "reasoning": "Matched to Ilala Urban Roads Project based on location and description."
}
```

---

### 3.3 Escalation Requests (Staff)

```
GET /api/v1/escalation-requests
Auth: Bearer (Staff)
```

**Query params:** `?status=pending&project_id=uuid&skip=0&limit=50`

**Response `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "feedback_id": "uuid",
      "feedback_ref": "GRV-2026-0001",
      "reason": "No PIU response for 30 days.",
      "requested_level": "lga_piu",
      "status": "pending",
      "requested_at": "2026-04-05T10:00:00Z",
      "reviewed_at": null,
      "reviewer_notes": null
    }
  ],
  "count": 1
}
```

---

#### Approve Escalation Request
```
POST /api/v1/escalation-requests/{request_id}/approve
Auth: Bearer (Staff)
```
```json
{ "notes": "Approved — PAP request meets escalation criteria." }
```

**Response `200`:**
```json
{
  "status": "approved",
  "message": "Escalation request approved.",
  "feedback_id": "uuid"
}
```

---

#### Reject Escalation Request
```
POST /api/v1/escalation-requests/{request_id}/reject
Auth: Bearer (Staff)
```
```json
{
  "reviewer_notes": "Case is still within the standard 21-day response window. PIU is actively investigating."
}
```

**Response `200`:**
```json
{
  "status": "rejected",
  "message": "Escalation request rejected. The PAP has been notified."
}
```

---

### 3.4 Categories

```
POST  /api/v1/categories            → create category
GET   /api/v1/categories            → list (?project_id=&is_active=)
GET   /api/v1/categories/summary    → counts per category for project
GET   /api/v1/categories/{id}       → detail
PATCH /api/v1/categories/{id}       → update
POST  /api/v1/categories/{id}/approve    → approve ML-suggested category
POST  /api/v1/categories/{id}/deactivate
POST  /api/v1/categories/{id}/merge → { "merge_into_id": "uuid" }
POST  /api/v1/feedback/{id}/classify
PATCH /api/v1/feedback/{id}/recategorise → { "category_def_id": "uuid" }
```

**Create category body:**
```json
{
  "name": "Land Compensation",
  "slug": "land_compensation",
  "description": "Issues related to land valuation and compensation payments.",
  "project_id": "uuid",
  "is_active": true
}
```

---

### 3.5 Committees (GHC)

```
POST   /api/v1/committees                                             → create GHC
GET    /api/v1/committees                                             → list
PATCH  /api/v1/committees/{id}                                        → update
POST   /api/v1/committees/{id}/stakeholders/{stakeholder_id}          → add stakeholder group
DELETE /api/v1/committees/{id}/stakeholders/{stakeholder_id}
POST   /api/v1/committees/{id}/members                                → add member
DELETE /api/v1/committees/{id}/members/{user_id}                      → remove member
```

---

## 4. AI Service (Riviwa AI) — Port 8085

### 4.1 Conversational AI

#### Health Check
```
GET /health/ai
Auth: none
```

**Response `200`:**
```json
{
  "status": "ok",
  "service": "ai_service",
  "ollama": "ready",
  "model": "llama3.2:3b"
}
```

---

#### Start Conversation
```
POST /api/v1/ai/conversations
Auth: none (Bearer optional for registered PAPs)
```

**Request body:**
```json
{
  "channel": "web",
  "language": "sw",
  "project_id": null,
  "user_id": null,
  "web_token": null
}
```

| Field | Options | Description |
|-------|---------|-------------|
| `channel` | `web` \| `mobile` | Conversation channel |
| `language` | `sw` \| `en` | Preferred language (AI auto-detects) |
| `project_id` | UUID \| null | Pre-select project (e.g. from project page) |
| `user_id` | UUID \| null | From JWT `sub` for registered PAPs |
| `web_token` | string \| null | Anonymous session token for web |

**Response `201`:**
```json
{
  "conversation_id": "uuid",
  "reply": "Karibu! Mimi ni Riviwa AI, msaidizi wa malalamiko ya mradi. Unaweza kunieleza tatizo lako au maoni yako.",
  "status": "active",
  "stage": "greeting",
  "turn_count": 1,
  "confidence": 0.0,
  "language": "sw",
  "submitted": false,
  "submitted_feedback": [],
  "project_name": null,
  "is_urgent": false,
  "incharge_name": null,
  "incharge_phone": null
}
```

**Conversation stages:**
| Stage | Meaning |
|-------|---------|
| `greeting` | Initial greeting, collecting basic info |
| `collecting` | AI extracting feedback fields |
| `confirming` | AI confirming extracted data with PAP |
| `submitted` | Feedback submitted to feedback_service |
| `done` | Conversation complete |

---

#### Send Message
```
POST /api/v1/ai/conversations/{conversation_id}/message
Auth: none
```

**Request body:**
```json
{
  "message": "Barabara imezuiwa karibu na duka langu tangu Jumatatu, Ilala, Kariakoo.",
  "media_urls": ["https://cdn.riviwa.com/evidence/photo1.jpg"]
}
```

**Response `200` (mid-conversation):**
```json
{
  "conversation_id": "uuid",
  "reply": "Asante kwa taarifa. Je, unaweza kunipa jina lako ili niweze kusajili malalamiko haya rasmi?",
  "status": "active",
  "stage": "collecting",
  "turn_count": 3,
  "confidence": 0.55,
  "language": "sw",
  "submitted": false,
  "submitted_feedback": [],
  "project_name": "Ilala Urban Roads Project",
  "is_urgent": false,
  "incharge_name": null,
  "incharge_phone": null
}
```

**Response `200` (auto-submitted, confidence ≥ 0.82):**
```json
{
  "conversation_id": "uuid",
  "reply": "Malalamiko yako yamefanikiwa kutumwa! Nambari yako ya ufuatiliaji ni GRV-2026-0042. Utapokea ujumbe ukikubaliwa na PIU.",
  "status": "submitted",
  "stage": "done",
  "turn_count": 6,
  "confidence": 0.92,
  "language": "sw",
  "submitted": true,
  "submitted_feedback": [
    {
      "feedback_id": "uuid",
      "unique_ref": "GRV-2026-0042",
      "feedback_type": "grievance"
    }
  ],
  "project_name": "Ilala Urban Roads Project",
  "is_urgent": false
}
```

---

#### Get Conversation Detail
```
GET /api/v1/ai/conversations/{conversation_id}
Auth: none
```

**Response `200`:**
```json
{
  "conversation_id": "uuid",
  "channel": "web",
  "status": "submitted",
  "stage": "done",
  "language": "sw",
  "turn_count": 6,
  "confidence": 0.92,
  "is_registered": false,
  "submitter_name": "Juma Bakari",
  "project_id": "uuid",
  "project_name": "Ilala Urban Roads Project",
  "extracted_data": {
    "feedback_type": "grievance",
    "description": "Barabara imezuiwa karibu na duka langu...",
    "issue_lga": "Ilala",
    "issue_ward": "Kariakoo",
    "submitter_name": "Juma Bakari",
    "submitter_phone": "+255787654321",
    "category": "road_access",
    "confidence": 0.92
  },
  "submitted_feedback": [
    { "feedback_id": "uuid", "unique_ref": "GRV-2026-0042", "feedback_type": "grievance" }
  ],
  "transcript": [
    { "role": "assistant", "content": "Karibu!...", "timestamp": "2026-04-08T08:00:00Z" },
    { "role": "user", "content": "Barabara imezuiwa...", "timestamp": "2026-04-08T08:01:00Z" }
  ],
  "is_urgent": false,
  "incharge_name": null,
  "incharge_phone": null,
  "started_at": "2026-04-08T08:00:00Z",
  "last_active_at": "2026-04-08T08:08:00Z",
  "completed_at": "2026-04-08T08:08:00Z"
}
```

---

### 4.2 AI Admin (Staff)

```
GET  /api/v1/ai/admin/conversations                       → list all conversations
GET  /api/v1/ai/admin/conversations/{id}                  → detail with full transcript
POST /api/v1/ai/admin/conversations/{id}/force-submit     → force-submit from extracted data
```

**List query params:** `?status=active&channel=web&skip=0&limit=50`

**force-submit response `200`:**
```json
{
  "submitted": true,
  "results": [
    { "feedback_id": "uuid", "unique_ref": "GRV-2026-0043", "feedback_type": "grievance" }
  ]
}
```

---

### 4.3 AI Internal (Service-to-Service)

> All internal endpoints require `X-Service-Key` header and are hidden from public docs.

#### Classify Feedback
```
POST /api/v1/ai/internal/classify
X-Service-Key: <key>
```

**Request body:**
```json
{
  "feedback_type": "grievance",
  "description": "Construction workers blocked the road to my shop.",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "issue_location_description": "Near Kariakoo market, next to the blue gate",
  "issue_region": "Dar es Salaam",
  "project_id": null
}
```

**Response `200`:**
```json
{
  "project_id": "uuid-or-null",
  "project_name": "Ilala Urban Roads Project",
  "category_slug": "road_access",
  "category_def_id": "uuid-or-null",
  "confidence": 0.87,
  "classified": true
}
```

---

#### Get Candidate Projects
```
POST /api/v1/ai/internal/candidate-projects
X-Service-Key: <key>
```

**Request body:**
```json
{
  "description": "Road blocked near my shop in Kariakoo",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "issue_location_description": "Near the blue gate",
  "top_k": 5
}
```

**Response `200`:**
```json
{
  "projects": [
    { "project_id": "uuid", "name": "Ilala Urban Roads Project", "region": "Dar es Salaam", "lga": "Ilala", "score": 0.87 },
    { "project_id": "uuid", "name": "Kariakoo Market Upgrade", "region": "Dar es Salaam", "lga": "Ilala", "score": 0.61 },
    { "project_id": "uuid", "name": "Dar Port Access Road", "region": "Dar es Salaam", "lga": "Temeke", "score": 0.44 }
  ]
}
```

---

## 5. Stakeholder Service — Port 8070

### 5.1 Stakeholders

#### Register Stakeholder
```
POST /api/v1/stakeholders
Auth: Bearer (Staff)
```

**Request body:**
```json
{
  "stakeholder_type": "pap",
  "entity_type": "individual",
  "category": "individual",
  "first_name": "Juma",
  "last_name": "Bakari",
  "org_name": null,
  "affectedness": "negatively_affected",
  "importance_rating": "high",
  "lga": "Ilala",
  "ward": "Kariakoo",
  "language_preference": "sw",
  "preferred_channel": "sms",
  "needs_translation": false,
  "needs_transport": false,
  "needs_childcare": false,
  "is_vulnerable": false,
  "vulnerable_group_types": null,
  "participation_barriers": null,
  "org_id": null,
  "address_id": null,
  "notes": null
}
```

| Field | Options |
|-------|---------|
| `stakeholder_type` | `pap` \| `interested_party` |
| `entity_type` | `individual` \| `organization` \| `group` |
| `category` | `individual` \| `local_government` \| `national_government` \| `ngo_cbo` \| `community_group` \| `private_company` \| `utility_provider` \| `development_partner` \| `media` \| `academic_research` \| `vulnerable_group` \| `other` |
| `affectedness` | `positively_affected` \| `negatively_affected` \| `both` \| `unknown` |
| `importance_rating` | `high` \| `medium` \| `low` |
| `preferred_channel` | `public_meeting` \| `focus_group` \| `email` \| `sms` \| `phone_call` \| `radio` \| `tv` \| `social_media` \| `billboard` \| `notice_board` \| `letter` \| `in_person` |
| `vulnerable_group_types` | `children` \| `women_low_income` \| `disabled_physical` \| `disabled_mental` \| `elderly` \| `youth` \| `low_income` \| `indigenous` \| `language_barrier` |

---

#### List / Get / Update / Delete
```
GET    /api/v1/stakeholders                    → list (query: ?project_id=&category=&lga=&ward=)
GET    /api/v1/stakeholders/analysis           → SEP Annex 3 analysis matrix
GET    /api/v1/stakeholders/{id}              → detail with contacts
PATCH  /api/v1/stakeholders/{id}              → partial update (all fields optional)
DELETE /api/v1/stakeholders/{id}              → soft-delete [Admin]
GET    /api/v1/stakeholders/{id}/projects     → project registrations
GET    /api/v1/stakeholders/{id}/engagements  → engagement history
```

---

#### Register Under Project
```
POST /api/v1/stakeholders/{stakeholder_id}/projects
Auth: Bearer (Staff)
```

**Request body:**
```json
{
  "project_id": "uuid",
  "is_pap": true,
  "affectedness": "negatively_affected",
  "impact_description": "Land acquisition for road widening affects 0.5 acres of farmland"
}
```

---

### 5.2 Contacts

#### Add Contact
```
POST /api/v1/stakeholders/{stakeholder_id}/contacts
Auth: Bearer (Staff)
```

**Request body:**
```json
{
  "full_name": "Amina Hassan",
  "title": "Ms.",
  "role_in_org": "Community Liaison Officer",
  "email": "amina.hassan@example.com",
  "phone": "+255712345678",
  "preferred_channel": "phone_call",
  "is_primary": true,
  "can_submit_feedback": true,
  "can_receive_communications": true,
  "can_distribute_communications": false,
  "user_id": null,
  "notes": null
}
```

```
GET    /api/v1/stakeholders/{id}/contacts
PATCH  /api/v1/stakeholders/{id}/contacts/{contact_id}  → partial update
DELETE /api/v1/stakeholders/{id}/contacts/{contact_id}  → { "reason": "..." }
```

---

### 5.3 Activities

```
POST   /api/v1/activities               → create meeting/activity
GET    /api/v1/activities               → list
GET    /api/v1/activities/{id}          → detail
PATCH  /api/v1/activities/{id}          → update
DELETE /api/v1/activities/{id}          → cancel
POST   /api/v1/activities/{id}/participants → register participants
GET    /api/v1/activities/{id}/participants → list participants
```

---

### 5.4 Communications

```
POST /api/v1/communications     → create communication record
GET  /api/v1/communications     → list
GET  /api/v1/communications/{id}
```

---

### 5.5 Focal Persons

```
POST /api/v1/focal-persons      → register focal person for project
GET  /api/v1/focal-persons      → list
GET  /api/v1/focal-persons/{id}
```

---

## 6. Recommendation Service — Port 8055

### Get Recommendations
```
GET /api/v1/recommendations/{entity_id}
Auth: Bearer
```

**Query params:**
| Param | Default | Description |
|-------|---------|-------------|
| `limit` | 20 | Results per page (max 100) |
| `page` | 1 | Page number |
| `min_score` | 0.1 | Minimum relevance score (0–1) |
| `entity_type` | null | `project` \| `organisation` |
| `category_filter` | null | Filter by category |
| `geo_only` | false | Restrict to same region |
| `include_explanation` | false | Include score breakdown |

**Response `200`:**
```json
{
  "entity_id": "uuid",
  "recommendations": [
    {
      "entity_id": "uuid",
      "entity_type": "project",
      "name": "Dodoma Road Rehabilitation",
      "slug": "dodoma-road-rehab",
      "description": "...",
      "category": "infrastructure",
      "sector": "transport",
      "cover_image_url": null,
      "org_logo_url": null,
      "latitude": -6.17,
      "longitude": 35.74,
      "city": "Dodoma",
      "region": "Dodoma",
      "country_code": "TZ",
      "status": "active",
      "score": 0.87,
      "score_breakdown": {
        "semantic": 0.40,
        "tag_overlap": 0.20,
        "geo_proximity": 0.20,
        "recency": 0.07
      },
      "distance_km": 12.4,
      "shared_tags": ["road", "infrastructure", "dodoma"],
      "interactions": {
        "feedback_count": 15,
        "grievance_count": 10,
        "suggestion_count": 4,
        "applause_count": 1,
        "engagement_count": 8
      },
      "accepts_grievances": true,
      "accepts_suggestions": true,
      "accepts_applause": true
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "generated_at": "2026-04-08T08:00:00Z",
  "cache_hit": false
}
```

---

### Similar Entities
```
GET /api/v1/similar/{entity_id}
Auth: Bearer
```

**Query params:** `?limit=20&page=1`

**Response `200`:** Same shape as recommendations but without geo constraints.

---

### Discover Nearby
```
GET /api/v1/discover/nearby
Auth: Bearer
```

**Query params:**
| Param | Required | Description |
|-------|----------|-------------|
| `latitude` | Yes | -90 to 90 |
| `longitude` | Yes | -180 to 180 |
| `radius_km` | No (default 50) | Search radius, 1–5000 km |
| `entity_type` | No | `project` \| `organisation` |
| `category` | No | Category filter |
| `limit` | No | Max 100 |
| `page` | No | Page number |

**Response `200`:**
```json
{
  "latitude": -6.7924,
  "longitude": 39.2083,
  "radius_km": 50.0,
  "results": [ { "...RecommendedEntity" } ],
  "total": 3,
  "page": 1,
  "page_size": 20,
  "generated_at": "2026-04-08T08:00:00Z"
}
```

---

### Index Entity (Internal)
```
POST /api/v1/indexing/entities
Auth: Bearer (Staff)
```

**Request body:**
```json
{
  "entity_id": "uuid",
  "entity_type": "project",
  "source_service": "riviwa_auth_service",
  "organisation_id": "uuid",
  "name": "Ilala Urban Roads Project",
  "slug": "ilala-urban-roads",
  "description": "Road rehabilitation and upgrade in Ilala district.",
  "category": "infrastructure",
  "sector": "transport",
  "tags": ["road", "construction", "ilala", "dar-es-salaam"],
  "country_code": "TZ",
  "region": "Dar es Salaam",
  "primary_lga": "Ilala",
  "city": "Dar es Salaam",
  "latitude": -6.7924,
  "longitude": 39.2083,
  "status": "active",
  "cover_image_url": null,
  "org_logo_url": null,
  "accepts_grievances": true,
  "accepts_suggestions": true,
  "accepts_applause": true
}
```

---

### Log Activity
```
POST /api/v1/indexing/activities
Auth: Bearer (Staff)
```

**Request body:**
```json
{
  "entity_id": "uuid",
  "event_type": "feedback.submitted",
  "actor_id": "uuid",
  "feedback_type": "grievance",
  "occurred_at": "2026-04-08T10:00:00Z",
  "payload": { "category": "road_access" }
}
```

---

## 7. Notification Service — Port 8060

> **Auth:** All endpoints require `X-User-Id: <user-uuid>` header  
> (set automatically by Nginx from validated JWT).

---

### 7.1 Inbox

#### Get Notification Feed
```
GET /api/v1/notifications
X-User-Id: <user-uuid>
```

**Query params:**
| Param | Default | Description |
|-------|---------|-------------|
| `unread_only` | false | Show only unread |
| `skip` | 0 | Pagination offset |
| `limit` | 30 | Max 100 |

**Response `200`:**
```json
{
  "unread_count": 3,
  "returned": 5,
  "items": [
    {
      "delivery_id": "uuid",
      "notification_id": "uuid",
      "notification_type": "grm.feedback.acknowledged",
      "priority": "medium",
      "rendered_title": "Feedback Acknowledged",
      "rendered_body": "Your grievance GRV-2026-0001 has been acknowledged by the PIU.",
      "read_at": null,
      "created_at": "2026-04-02T09:00:00Z",
      "is_read": false
    }
  ]
}
```

---

#### Unread Count (Badge)
```
GET /api/v1/notifications/unread-count
X-User-Id: <user-uuid>
```

**Response `200`:**
```json
{ "unread_count": 3 }
```

---

#### Mark Single as Read
```
PATCH /api/v1/notifications/deliveries/{delivery_id}/read
X-User-Id: <user-uuid>
```

**Response `200`:**
```json
{ "message": "Marked as read.", "delivery_id": "uuid" }
```

---

#### Mark All as Read
```
POST /api/v1/notifications/mark-all-read
X-User-Id: <user-uuid>
```

**Response `200`:**
```json
{ "message": "5 notification(s) marked as read.", "count": 5 }
```

---

### 7.2 Preferences

#### Get All Preferences
```
GET /api/v1/notification-preferences
X-User-Id: <user-uuid>
```

**Response `200`:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "notification_type": "grm.feedback.acknowledged",
    "channel": "sms",
    "enabled": false,
    "updated_at": "2026-04-01T00:00:00Z"
  }
]
```
> If a (type, channel) pair is **not listed**, the default is `enabled = true`.

---

#### Set Preference
```
PUT /api/v1/notification-preferences
X-User-Id: <user-uuid>
```

**Request body:**
```json
{
  "notification_type": "grm.feedback.acknowledged",
  "channel": "sms",
  "enabled": false
}
```
> Use wildcard `grm.*` to control all GRM notifications at once.  
> `channel`: `in_app` | `push` | `sms` | `whatsapp` | `email`

**Response `200`:**
```json
{
  "message": "Preference disabled for grm.feedback.acknowledged on sms.",
  "notification_type": "grm.feedback.acknowledged",
  "channel": "sms",
  "enabled": false
}
```

---

#### Reset Preference to Default
```
DELETE /api/v1/notification-preferences/{notification_type}/{channel}
X-User-Id: <user-uuid>
```

**Response `200`:**
```json
{ "message": "Preference reset to default (enabled)." }
```

---

### 7.3 Devices (Push Tokens)

#### Register Device
```
POST /api/v1/devices
X-User-Id: <user-uuid>
```

**Request body:**
```json
{
  "platform": "fcm",
  "push_token": "fcm-registration-token-from-firebase-sdk",
  "device_name": "Juma's Android Phone",
  "app_version": "1.2.3"
}
```
> `platform`: `fcm` (Android/Firebase) | `apns` (iOS/Apple)

**Response `201`:**
```json
{
  "id": "uuid",
  "platform": "fcm",
  "device_name": "Juma's Android Phone",
  "is_active": true,
  "registered_at": "2026-04-08T08:00:00Z"
}
```

---

#### Update Push Token
```
PATCH /api/v1/devices/{device_id}/token
X-User-Id: <user-uuid>
```

**Request body:**
```json
{
  "push_token": "new-fcm-registration-token",
  "app_version": "1.3.0"
}
```

---

#### List / Delete Devices
```
GET    /api/v1/devices                     → list registered devices
DELETE /api/v1/devices/{device_id}         → deregister device
```

---

### 7.4 Templates (Admin)

#### Create Template
```
POST /api/v1/templates
Auth: Bearer (Staff)
```

**Request body:**
```json
{
  "notification_type": "grm.feedback.acknowledged",
  "channel": "sms",
  "language": "sw",
  "title_template": null,
  "subject_template": null,
  "body_template": "Malalamiko yako {{ unique_ref }} yamepokewa na PIU ya mradi {{ project_name }}.",
  "is_active": true
}
```
> Templates use Jinja2 syntax. Variables passed at dispatch time via the `variables` field.  
> `channel`: `in_app` | `push` | `sms` | `whatsapp` | `email`

**Response `201`:**
```json
{
  "id": "uuid",
  "notification_type": "grm.feedback.acknowledged",
  "channel": "sms",
  "language": "sw",
  "title_template": null,
  "subject_template": null,
  "body_template": "Malalamiko yako {{ unique_ref }} yamepokewa...",
  "is_active": true,
  "updated_at": "2026-04-08T08:00:00Z"
}
```

```
GET   /api/v1/templates              → list (?notification_type=&channel=&language=)
GET   /api/v1/templates/{id}
PATCH /api/v1/templates/{id}         → { "body_template": "...", "is_active": true }
DELETE /api/v1/templates/{id}
```

---

### 7.5 Internal Dispatch

> Called by other services instead of (or as fallback to) Kafka.

```
POST /api/v1/internal/dispatch
X-Service-Key: <INTERNAL_SERVICE_KEY>
```

**Request body:**
```json
{
  "notification_type": "grm.feedback.acknowledged",
  "recipient_user_id": "uuid",
  "recipient_phone": "+255712345678",
  "recipient_email": null,
  "recipient_push_tokens": [],
  "language": "sw",
  "variables": {
    "unique_ref": "GRV-2026-0001",
    "project_name": "Ilala Urban Roads Project",
    "piu_name": "Ilala PIU"
  },
  "preferred_channels": ["push", "sms"],
  "priority": "medium",
  "idempotency_key": "ack-grv-2026-0001",
  "scheduled_at": null,
  "source_service": "feedback_service",
  "source_entity_id": "feedback-uuid",
  "metadata": {}
}
```

| Field | Options |
|-------|---------|
| `priority` | `critical` \| `high` \| `medium` \| `low` |
| `preferred_channels` | `in_app` \| `push` \| `sms` \| `whatsapp` \| `email` |

**Response `200`:**
```json
{
  "notification_id": "uuid",
  "accepted": true
}
```

---

#### Get Notification Status (Internal)
```
GET /api/v1/internal/notifications/{notification_id}
X-Service-Key: <INTERNAL_SERVICE_KEY>
```

**Response `200`:** → Full `NotificationResponse` with all delivery channel statuses.

---

## Notification Types Reference

| Type | Description |
|------|-------------|
| `grm.feedback.submitted` | New feedback submitted |
| `grm.feedback.acknowledged` | PIU acknowledged receipt |
| `grm.feedback.assigned` | Feedback assigned to officer/committee |
| `grm.feedback.escalated` | Case escalated to higher GRM level |
| `grm.feedback.resolved` | Resolution provided |
| `grm.feedback.closed` | Case closed |
| `grm.feedback.dismissed` | Case dismissed |
| `grm.appeal.filed` | PAP filed an appeal |
| `grm.escalation_request.approved` | PAP escalation request approved |
| `grm.escalation_request.rejected` | PAP escalation request rejected |
| `auth.otp.login` | OTP for login |
| `auth.otp.registration` | OTP for registration |
| `auth.otp.password_reset` | OTP for password reset |
| `auth.account.suspended` | Account suspended |
| `org.invite.received` | Organisation invite |
| `org.invite.accepted` | Invite accepted |

---

*Generated: 2026-04-08 — Riviwa Platform v2*
