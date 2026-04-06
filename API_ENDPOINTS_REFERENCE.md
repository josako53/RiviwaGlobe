# Riviwa Platform — Complete API Endpoints Reference

> **Base URL**: `https://api.riviwa.com/api/v1`
> **Content-Type**: `application/json` (unless noted otherwise)
> **Authentication**: `Authorization: Bearer <access_token>` (unless noted)

---

## Table of Contents

1. [Authentication & Registration](#1-authentication--registration)
2. [User Profile](#2-user-profile)
3. [Organisations & Membership](#3-organisations--membership)
4. [Projects & Stages](#4-projects--stages)
5. [Feedback — Staff Submission](#5-feedback--staff-submission)
6. [Feedback — PAP Self-Service](#6-feedback--pap-self-service)
7. [Feedback — AI/ML Channels](#7-feedback--aiml-channels)
8. [Feedback — Voice](#8-feedback--voice)
9. [Feedback — Lifecycle (Acknowledge → Resolve → Close)](#9-feedback--lifecycle)
10. [Feedback — Categories & Committees](#10-feedback--categories--committees)
11. [Feedback — Reports](#11-feedback--reports)
12. [Stakeholder Engagement](#12-stakeholder-engagement)
13. [Notifications](#13-notifications)
14. [Payments](#14-payments)
15. [Translation](#15-translation)
16. [Recommendations](#16-recommendations)
17. [Admin Dashboard](#17-admin-dashboard)
18. [Enums Reference](#18-enums-reference)

---

## 1. Authentication & Registration

### 1.1 Register — Step 1: Initiate

```
POST /auth/register/init
```

No auth required. Sends OTP to email or phone.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | One of email/phone | Email address to register |
| `phone_number` | string | One of email/phone | E.164 phone number (e.g. +255712345678) |

**Response (200):**
```json
{
  "session_token": "abc123...",
  "otp_channel": "sms",
  "otp_destination": "+255***678",
  "expires_in_seconds": 300
}
```

| Field | Description |
|-------|-------------|
| `session_token` | Pass to step 2 and 3. Expires in 5 minutes. |
| `otp_channel` | Where OTP was sent: `sms` or `email` |
| `otp_destination` | Masked recipient for UI display |

---

### 1.2 Register — Step 2: Verify OTP

```
POST /auth/register/verify-otp
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_token` | string | Yes | From step 1 |
| `otp_code` | string | Yes | 6-digit code received via SMS/email |

**Response (200):**
```json
{
  "continuation_token": "xyz789...",
  "identifier": "+255712345678"
}
```

---

### 1.3 Register — Step 3: Complete

```
POST /auth/register/complete
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `continuation_token` | string | Yes | From step 2 |
| `password` | string | Yes | Min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special |
| `display_name` | string | No | Full name |
| `username` | string | No | Unique username |

**Response (201):**
```json
{
  "action": "complete",
  "message": "Account created successfully. You may now log in."
}
```

---

### 1.4 Resend OTP

```
POST /auth/register/resend-otp
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_token` | string | Yes | From step 1. 60-second cooldown. |

---

### 1.5 Login — Step 1: Credentials

```
POST /auth/login
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `identifier` | string | Yes | Email or E.164 phone number |
| `password` | string | Yes | Account password |

**Response (200):**
```json
{
  "login_token": "5-1i6hOx...",
  "otp_channel": "sms",
  "otp_destination": "+255***678",
  "expires_in_seconds": 300
}
```

> **Important**: `login_token` is NOT the JWT. Pass it to step 2 with the OTP.

---

### 1.6 Login — Step 2: Verify OTP

```
POST /auth/login/verify-otp
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `login_token` | string | Yes | From step 1 |
| `otp_code` | string | Yes | 6-digit OTP code |

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "opaque-refresh-token",
  "token_type": "bearer",
  "expires_in": 1800
}
```

| Field | Description |
|-------|-------------|
| `access_token` | JWT — include as `Authorization: Bearer <token>` on all requests. Expires in 30 min. |
| `refresh_token` | Opaque token — use to get a new access_token without re-login |

---

### 1.7 Refresh Token

```
POST /auth/token/refresh
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | Yes | From login or previous refresh |

**Response (200):** Same as login step 2.

---

### 1.8 Logout

```
POST /auth/token/logout
```
**Auth**: Bearer token required.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | Yes | Revokes the refresh token and deny-lists the JWT |

---

### 1.9 Switch Organisation Context

```
POST /auth/switch-org
```
**Auth**: Bearer token required.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `org_id` | UUID or null | Yes | Organisation to switch to. `null` = personal dashboard. |

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "new-opaque-token",
  "token_type": "bearer",
  "expires_in": 1800,
  "org_id": "8ff4ce5f-...",
  "org_role": "owner"
}
```

> New JWT includes `org_id` and `org_role` claims.

---

### 1.10 Password Reset

```
POST /auth/password/forgot          → sends OTP
POST /auth/password/forgot/verify-otp → verifies OTP
POST /auth/password/forgot/reset     → sets new password
POST /auth/password/change           → change password (authenticated)
```

---

### 1.11 Social Auth (Google/Apple/Facebook)

```
POST /auth/social
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | Yes | `google`, `apple`, or `facebook` |
| `id_token` | string | Yes | OAuth ID token from provider |
| `device_fingerprint` | string | No | For fraud detection |

---

## 2. User Profile

### 2.1 Get My Profile

```
GET /users/me
```
**Auth**: Bearer token required.

**Response (200):**
```json
{
  "id": "7caa7de5-...",
  "email": "user@example.com",
  "phone_number": "+255712345678",
  "username": "johndoe",
  "display_name": "John Doe",
  "avatar_url": "https://...",
  "status": "active",
  "language": "sw",
  "is_email_verified": true,
  "phone_verified": true,
  "has_password": true,
  "platform_role": "user",
  "created_at": "2026-04-06T08:00:00Z"
}
```

### 2.2 Update My Profile

```
PATCH /users/me
```

**Request Body** (all optional — only include fields to change):
| Field | Type | Description |
|-------|------|-------------|
| `display_name` | string | Full name |
| `username` | string | Unique username |
| `avatar_url` | string or null | Profile picture URL |
| `country_code` | string | 2-letter ISO country code |
| `language` | string | BCP-47 language code (sw, en, fr) |

---

## 3. Organisations & Membership

### 3.1 Create Organisation

```
POST /orgs
```
**Auth**: Bearer token required.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `legal_name` | string | Yes | Official registered name |
| `display_name` | string | Yes | Public-facing name |
| `slug` | string | Yes | URL-friendly identifier (unique) |
| `org_type` | string | Yes | `business`, `government`, `ngo`, `academic`, `community` |
| `description` | string | No | About the organisation |
| `support_email` | string | No | Public support email |
| `support_phone` | string | No | Public support phone |
| `country_code` | string | No | 2-letter ISO code (e.g. `tz`) |
| `timezone` | string | No | IANA timezone |
| `registration_number` | string | No | Business registration number |
| `max_members` | integer | No | Member limit (0 = unlimited) |

> The creator automatically becomes the `owner` of the organisation.

**Response (201):**
```json
{
  "id": "8ff4ce5f-...",
  "slug": "msimbazi",
  "status": "pending_verification",
  "is_verified": false,
  "org_type": "business",
  "created_at": "2026-04-06T08:41:56Z"
}
```

### 3.2 Member Management

```
POST   /orgs/{org_id}/members                    → Add member
DELETE /orgs/{org_id}/members/{user_id}           → Remove member
PATCH  /orgs/{org_id}/members/{user_id}/role      → Change role
POST   /orgs/{org_id}/transfer-ownership          → Transfer owner
POST   /orgs/{org_id}/invites                     → Send invite
POST   /orgs/invites/{invite_id}/accept           → Accept invite
POST   /orgs/invites/{invite_id}/decline          → Decline invite
```

**Org roles**: `owner`, `admin`, `manager`, `member`, `viewer`

---

## 4. Projects & Stages

### 4.1 Create Project

```
POST /orgs/{org_id}/projects
```
**Auth**: Bearer token with org context (`org_id` and `org_role` in JWT).

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Project name |
| `code` | string | No | Short code (e.g. MVDP-001) |
| `slug` | string | No | URL-friendly identifier |
| `category` | string | No | Project category |
| `sector` | string | No | Sector (infrastructure, water, education, etc.) |
| `description` | string | No | Full description |
| `objectives` | string | No | Project objectives |
| `expected_outcomes` | string | No | Expected outcomes |
| `start_date` | date | No | Project start date (YYYY-MM-DD) |
| `end_date` | date | No | Expected end date |
| `budget_amount` | float | No | Total budget |
| `currency_code` | string | No | Currency (TZS, USD, etc.) |
| `country_code` | string | No | 2-letter ISO country code |
| `region` | string | No | Administrative region |
| `primary_lga` | string | No | Primary LGA |
| `accepts_grievances` | boolean | No | Accept grievance submissions (default: true) |
| `accepts_suggestions` | boolean | No | Accept suggestion submissions (default: true) |
| `accepts_applause` | boolean | No | Accept applause submissions (default: true) |
| `requires_grm` | boolean | No | Whether project requires formal GRM compliance |
| `cover_image_url` | string | No | Cover image URL |

> Project starts in `planning` status. You must **activate** it before feedback can be submitted.

### 4.2 Activate Project

```
POST /orgs/{org_id}/projects/{project_id}/activate
```

> Changes status `planning` → `active`. Publishes Kafka event that syncs the project to feedback_service and stakeholder_service.

### 4.3 Project Lifecycle

```
POST /orgs/{org_id}/projects/{project_id}/pause     → Pause
POST /orgs/{org_id}/projects/{project_id}/resume     → Resume
POST /orgs/{org_id}/projects/{project_id}/complete   → Mark complete
```

### 4.4 Project Stages

```
POST  /orgs/{org_id}/projects/{project_id}/stages                    → Add stage
PATCH /orgs/{org_id}/projects/{project_id}/stages/{stage_id}         → Update
POST  /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/activate → Activate
POST  /orgs/{org_id}/projects/{project_id}/stages/{stage_id}/complete → Complete
```

---

## 5. Feedback — Staff Submission

### 5.1 Submit Feedback (Staff/Officer)

```
POST /feedback
```
**Auth**: Bearer token (optional — staff identity captured from JWT if present).
**Service**: feedback_service (port 8090)

This is for **staff/officers** entering feedback on behalf of PAPs — from paper forms, walk-ins, phone calls, public meetings, notice boxes, etc. Staff can **backdate**, set **priority**, choose **channel**, and fill all Annex 5/6 fields.

**Request Body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| **SECTION A — Core** | | | | |
| `project_id` | UUID | **Yes** | — | Which project this feedback is about |
| `feedback_type` | string | **Yes** | — | `grievance` \| `suggestion` \| `applause` |
| `category` | string | **Yes** | — | What the feedback is about (see [Enums](#18-enums-reference)) |
| `channel` | string | **Yes** | — | How it arrived: `paper_form`, `in_person`, `email`, `public_meeting`, `notice_box`, `sms`, `phone_call`, etc. |
| `subject` | string | **Yes** | — | Short summary (5-500 chars). Annex 5: Complaint header |
| `description` | string | **Yes** | — | Full description (min 10 chars). Annex 5: Complaint Description |
| **SECTION B — Grievant Identity** | | | | |
| `is_anonymous` | boolean | No | `false` | CONFIDENTIAL — all identity fields hidden when true |
| `submitter_name` | string | No | — | Grievant Name (Annex 5) |
| `submitter_phone` | string | No | — | Contact phone (E.164 format: +255712345678) |
| `submitter_email` | string | No | — | Contact email |
| `submitter_type` | string | No | `individual` | `individual` \| `group` \| `community_organisation` |
| `group_size` | integer | No | — | Number of affected persons (when group) |
| `submitter_location_region` | string | No | — | Grievant address: region |
| `submitter_location_district` | string | No | — | Grievant address: district |
| `submitter_location_lga` | string | No | — | Grievant address: LGA |
| `submitter_location_ward` | string | No | — | Grievant address: ward |
| `submitter_location_street` | string | No | — | Grievant address: street/plot |
| `submitted_by_user_id` | UUID | No | — | Riviwa User ID (if PAP has account) |
| `submitted_by_stakeholder_id` | UUID | No | — | Stakeholder ID (from stakeholder_service) |
| `submitted_by_contact_id` | UUID | No | — | StakeholderContact ID |
| **SECTION C — Triage** | | | | |
| `priority` | string | No | `medium` | `critical` \| `high` \| `medium` \| `low` |
| **SECTION D — Issue Location** | | | | |
| `issue_location_description` | string | No | — | Free text: "Near Jangwani Bridge" |
| `issue_region` | string | No | — | Region where issue occurred |
| `issue_district` | string | No | — | District |
| `issue_lga` | string | No | — | LGA / Municipal |
| `issue_ward` | string | No | — | Ward |
| `issue_mtaa` | string | No | — | Mtaa / sub-ward |
| `issue_gps_lat` | float | No | — | GPS latitude (-90 to 90) |
| `issue_gps_lng` | float | No | — | GPS longitude (-180 to 180) |
| **SECTION E — Dates** | | | | |
| `date_of_incident` | string | No | — | When the issue happened (YYYY-MM-DD) |
| `submitted_at` | string | No | now | **Backdate**: override submission date (YYYY-MM-DD or ISO). For paper forms. |
| **SECTION F — Evidence** | | | | |
| `media_urls` | string[] | No | — | Photo/video/document URLs from MinIO |
| **SECTION G — Cross-references** | | | | |
| `service_location_id` | UUID | No | — | OrgServiceLocation where it happened |
| `stakeholder_engagement_id` | UUID | No | — | From a public meeting (Annex 5) |
| `distribution_id` | UUID | No | — | From a communication distribution |
| **SECTION H — Officer Metadata** | | | | |
| `officer_recorded` | boolean | No | `false` | True = staff entered on behalf of PAP |
| `internal_notes` | string | No | — | Internal PIU notes (never shown to PAP) |

**Response (201):**
```json
{
  "id": "a1b2c3d4-...",
  "feedback_id": "a1b2c3d4-...",
  "unique_ref": "GRV-2026-0001",
  "tracking_number": "GRV-2026-0001",
  "project_id": "71274571-...",
  "feedback_type": "grievance",
  "category": "compensation",
  "status": "submitted",
  "priority": "high",
  "channel": "paper_form",
  "submission_method": "self_service",
  "is_anonymous": false,
  "submitter_name": "Amina Hassan",
  "subject": "Unfair compensation for land acquisition",
  "description": "PAP claims the compensation...",
  "issue_lga": "Ilala",
  "issue_ward": "Kariakoo",
  "submitted_at": "2025-10-01T00:00:00+00:00",
  "date_of_incident": "2025-09-15T00:00:00+00:00"
}
```

---

### 5.2 Bulk Import from CSV

```
POST /feedback/bulk-upload
```
**Auth**: Staff token required.
**Content-Type**: `multipart/form-data`

Upload a CSV file to import up to 1000 feedback records at once. Failed rows are skipped — successful ones are not affected.

**Request:**
| Field | Type | Description |
|-------|------|-------------|
| `file` | File | CSV file (UTF-8, comma-separated, header row required) |

**CSV Columns:**
```csv
project_id,feedback_type,category,subject,description,channel,priority,submitter_name,submitter_phone,is_anonymous,issue_lga,issue_ward,date_of_incident,submitted_at
```

All columns from the staff form are supported. Column name aliases work: `type` = `feedback_type`, `name` = `submitter_name`, `phone` = `submitter_phone`, `date` = `date_of_incident`, `received_date` = `submitted_at`.

**Response (200):**
```json
{
  "total_rows": 50,
  "created": 47,
  "skipped": 3,
  "errors": [
    {"row": 12, "error": "Missing required field: description"},
    {"row": 23, "error": "Invalid feedback_type: complaint"},
    {"row": 45, "error": "Project not found"}
  ]
}
```

---

## 6. Feedback — PAP Self-Service

All PAP endpoints require a logged-in user (JWT Bearer token).

### 6.1 Submit Feedback (PAP)

```
POST /my/feedback
```
**Auth**: Bearer token required.

Simplified submission for end-users. Channel is auto-set to `web_portal`. Priority is always `medium`. `project_id` is optional — ML/AI can auto-detect from description.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `feedback_type` | string | **Yes** | `grievance` \| `suggestion` \| `applause` |
| `description` | string | **Yes** | What happened (min 10 chars) |
| `project_id` | UUID | No | If omitted, ML auto-detects from description |
| `category` | string | No | If omitted, ML auto-classifies |
| `subject` | string | No | If omitted, auto-generated from description |
| `is_anonymous` | boolean | No | Default: false |
| `submitter_name` | string | No | Your name |
| `submitter_phone` | string | No | Your phone |
| `issue_lga` | string | No | LGA where issue occurred |
| `issue_ward` | string | No | Ward where issue occurred |
| `issue_location_description` | string | No | Describe where the issue is |
| `issue_gps_lat` | float | No | GPS latitude (mobile app auto-captures) |
| `issue_gps_lng` | float | No | GPS longitude |
| `date_of_incident` | string | No | YYYY-MM-DD |
| `media_urls` | string[] | No | Photo/video URLs |

**Response (201):**
```json
{
  "feedback_id": "a1b2c3d4-...",
  "tracking_number": "GRV-2026-0001",
  "status": "submitted",
  "status_label": "Submitted — awaiting acknowledgement",
  "feedback_type": "grievance",
  "message": "Your grievance has been submitted successfully. Tracking number: GRV-2026-0001. You will be notified when PIU acknowledges receipt."
}
```

> **Tracking number format**: `GRV-2026-0001` (grievance), `SGG-2026-0001` (suggestion), `APP-2026-0001` (applause)

---

### 6.2 List My Feedback

```
GET /my/feedback?feedback_type=grievance&status=submitted&skip=0&limit=20
```

### 6.3 Track a Submission

```
GET /my/feedback/{feedback_id}
```

Returns full handling history: actions, escalations, resolution, appeal, and what the PAP can do next (`can_request_escalation`, `can_appeal`, `can_add_comment`).

### 6.4 Request Escalation

```
POST /my/feedback/{feedback_id}/escalation-request
```
**Body:** `{"reason": "No response after 30 days despite follow-ups"}`

### 6.5 File Appeal

```
POST /my/feedback/{feedback_id}/appeal
```
**Body:** `{"grounds": "Resolution does not address the core issue of fair compensation"}`

### 6.6 Add Follow-up Comment

```
POST /my/feedback/{feedback_id}/add-comment
```
**Body:** `{"comment": "I have new evidence to share regarding my case"}`

---

## 7. Feedback — AI/ML Channels

No authentication required. PAPs interact via phone number. The AI (Riviwa) collects all feedback details through conversation and auto-submits when confident.

### 7.1 Start AI Conversation

```
POST /ai/sessions
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `channel` | string | **Yes** | `sms` \| `whatsapp` \| `phone_call` |
| `phone_number` | string | No | E.164 phone number |
| `whatsapp_id` | string | No | WhatsApp ID (phone without +) |
| `project_id` | UUID | No | Auto-detected if omitted |
| `language` | string | No | `sw` (default) \| `en` |

**Response (201):**
```json
{
  "session_id": "d4e5f6a7-...",
  "reply": "Habari! Mimi ni Riviwa. Ninaweza kukusaidia kuwasilisha malalamiko au maoni kuhusu mradi. Tafadhali niambie tatizo lako.",
  "submitted": false,
  "status": "active",
  "turn_count": 1,
  "confidence": 0.0,
  "language": "sw"
}
```

### 7.2 Send Message

```
POST /ai/sessions/{session_id}/message
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | **Yes** | User's message (1-2000 chars) |

**Response (200):**
```json
{
  "session_id": "d4e5f6a7-...",
  "reply": "Pole sana kwa tatizo hilo. Je, tatizo limetokea wapi hasa? Tafadhali niambie LGA na Kata.",
  "submitted": false,
  "feedback_id": null,
  "status": "active",
  "turn_count": 3,
  "confidence": 0.65,
  "language": "sw"
}
```

When confidence reaches 0.80+, the AI auto-submits:
```json
{
  "session_id": "d4e5f6a7-...",
  "reply": "Asante! Malalamiko yako yamewasilishwa. Nambari ya rejeleo: GRV-2026-0002.",
  "submitted": true,
  "feedback_id": "b2c3d4e5-...",
  "tracking_number": "GRV-2026-0002",
  "status": "completed",
  "turn_count": 6,
  "confidence": 0.92,
  "language": "sw"
}
```

### 7.3 Webhooks (Fully Automated)

```
POST /webhooks/sms        → Africa's Talking / Twilio inbound
POST /webhooks/whatsapp   → Meta Cloud API inbound (text + voice notes)
GET  /webhooks/whatsapp   → Meta webhook verification
```

These are called by SMS/WhatsApp gateways. The system auto-creates sessions and runs the LLM pipeline.

---

## 8. Feedback — Voice

### 8.1 Attach Voice Note to Feedback

```
POST /voice/feedback/{feedback_id}/voice-note
```
**Auth**: Bearer token required.
**Content-Type**: `multipart/form-data`

PAP taps mic in the app to record their grievance. Audio is stored, transcribed, and attached to the feedback record.

**Request:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `audio` | File | **Yes** | Audio file (OGG, WebM, MP3, WAV, AAC, AMR). Max 25MB. |
| `language` | string | No | `sw` (default) \| `en` — helps STT accuracy |
| `use_as_description` | boolean | No | If true (default) and description is empty, transcript fills it |

**Response (200):**
```json
{
  "feedback_id": "a1b2c3d4-...",
  "voice_note_url": "https://minio.riviwa.com/riviwa-voice/feedback/a1b2c3d4/note.ogg",
  "transcription": "Ujenzi karibu na nyumba yangu unasababisha vumbi kubwa...",
  "language": "sw",
  "confidence": 0.87,
  "duration_seconds": 45,
  "service": "whisper",
  "flagged_for_review": false,
  "description_updated": true
}
```

### 8.2 Voice Turn in AI Conversation

```
POST /voice/sessions/{session_id}/audio-turn
```

PAP holds mic during live conversation. Audio → STT → text injected into LLM pipeline.

### 8.3 Text-to-Speech Reply

```
POST /voice/sessions/{session_id}/tts
```

Generate audio reply for phone calls or app voice mode.

---

## 9. Feedback — Lifecycle

All require Staff authentication.

| Method | Endpoint | Description | Key Body Fields |
|--------|----------|-------------|-----------------|
| PATCH | `/feedback/{id}/acknowledge` | Confirm receipt | `priority`, `target_resolution_date`, `notes` |
| PATCH | `/feedback/{id}/assign` | Assign to staff/committee | `assigned_to_user_id`, `assigned_committee_id` |
| POST | `/feedback/{id}/escalate` | Escalate to higher GRM level | `to_level`, `reason` |
| POST | `/feedback/{id}/resolve` | Record resolution | `resolution_summary`, `response_method`, `grievant_satisfied` |
| POST | `/feedback/{id}/appeal` | File appeal | `appeal_grounds` |
| PATCH | `/feedback/{id}/close` | Close (final state) | `notes` |
| PATCH | `/feedback/{id}/dismiss` | Dismiss | `reason` |
| POST | `/feedback/{id}/actions` | Log an action | `action_type`, `description`, `response_method` |
| GET | `/feedback/{id}/actions` | Get action log | — |

### Status Flow:
```
submitted → acknowledged → in_review → resolved → closed
                              ↓            ↓
                          escalated     appealed → resolved → closed
                                          ↓
                                       dismissed
```

---

## 10. Feedback — Categories & Committees

### Categories
```
POST   /categories                                → Create category
GET    /categories                                → List categories
GET    /categories/{id}                           → Category detail
PATCH  /categories/{id}                           → Update
POST   /categories/{id}/approve                   → Approve ML suggestion
POST   /categories/{id}/reject                    → Reject ML suggestion
POST   /categories/{id}/deactivate                → Deactivate
POST   /categories/{id}/merge                     → Merge into another
POST   /feedback/{id}/classify                    → Run ML classification
PATCH  /feedback/{id}/recategorise                → Manual recategorise
```

### Committees (GHC)
```
POST   /committees                                → Create GHC
GET    /committees                                → List GHCs
PATCH  /committees/{id}                           → Update
POST   /committees/{id}/members                   → Add member
DELETE /committees/{id}/members/{user_id}          → Remove member
```

---

## 11. Feedback — Reports

All reports support export via `?format=json|csv|xlsx|pdf`.

```
GET /reports/performance        → Overall dashboard
GET /reports/grievances         → Grievance-specific metrics
GET /reports/suggestions        → Suggestion metrics
GET /reports/applause           → Applause metrics
GET /reports/channels           → By channel breakdown
GET /reports/grievance-log      → Full log (Annex 5/6 format)
GET /reports/suggestion-log     → Full suggestion log
GET /reports/applause-log       → Full applause log
GET /reports/summary            → Count summary per project
GET /reports/overdue            → Past target resolution date
```

**Common query params**: `project_id`, `from_date`, `to_date`, `region`, `lga`, `priority`, `channel`, `format`

---

## 12. Stakeholder Engagement

### Stakeholders
```
POST   /stakeholders                              → Register stakeholder
GET    /stakeholders                              → List with filters
GET    /stakeholders/analysis                     → Annex 3 matrix
GET    /stakeholders/{id}                         → Detail + contacts
PATCH  /stakeholders/{id}                         → Update
POST   /stakeholders/{id}/contacts                → Add contact
```

### Engagement Activities
```
POST   /activities                                → Create activity
GET    /activities                                → List activities
GET    /activities/{id}                           → Detail + attendances
PATCH  /activities/{id}                           → Update / mark conducted
POST   /activities/{id}/attendances               → Log attendance
POST   /activities/{id}/attendances/bulk           → Bulk log
POST   /activities/{id}/media                     → Upload media
```

### Communications
```
POST   /communications                            → Log communication
GET    /communications                            → List
POST   /communications/{id}/distributions          → Log distribution
```

---

## 13. Notifications

**Header**: `X-User-Id: <user-uuid>` (instead of Bearer token)

```
POST   /devices                                   → Register push token
GET    /devices                                   → List my devices
PATCH  /devices/{id}/token                        → Update push token
DELETE /devices/{id}                              → Deregister

GET    /notifications                             → Get inbox
GET    /notifications/unread-count                → Badge count
PATCH  /notifications/deliveries/{id}/read        → Mark read
POST   /notifications/mark-all-read               → Mark all read

GET    /notification-preferences                  → Get preferences
PUT    /notification-preferences                  → Update preferences
```

---

## 14. Payments

```
POST   /payments                                  → Create payment intent
GET    /payments                                  → List payments
GET    /payments/{id}                             → Payment detail
POST   /payments/{id}/initiate                    → Initiate USSD push
POST   /payments/{id}/verify                      → Poll provider status
POST   /payments/{id}/refund                      → Refund [staff]
DELETE /payments/{id}                             → Cancel pending
```

**Providers**: `azampay`, `selcom`, `mpesa`
**Currency**: `TZS` (default)

---

## 15. Translation

No auth required.

```
POST /translate       → Translate single text
POST /translate/batch → Translate up to 50 texts
POST /detect          → Detect language
GET  /languages       → List supported languages (200+)
GET  /health          → Provider health
```

See [Section 7-8 in Integration Guide](RIVIWA_API_AND_INTEGRATION_GUIDE.md#7-translation-service-endpoints-port-8050) for full request/response examples.

---

## 16. Recommendations

Auth required.

```
GET /recommendations/{entity_id}  → Scored recommendations with interaction summaries
GET /similar/{entity_id}          → Semantic similarity (cross-region)
GET /discover/nearby              → Geo-based discovery
```

See [Section 8 in Integration Guide](RIVIWA_API_AND_INTEGRATION_GUIDE.md#8-recommendation-service-endpoints-port-8055) for full request/response examples.

---

## 17. Admin Dashboard

All require `platform_role: admin` or `super_admin`.

```
GET  /admin/dashboard/summary
GET  /admin/users
GET  /admin/users/growth
GET  /admin/users/status-breakdown
GET  /admin/users/{user_id}
POST /admin/users/{user_id}/suspend
POST /admin/users/{user_id}/ban
POST /admin/users/{user_id}/reactivate
GET  /admin/organisations
GET  /admin/organisations/pending
GET  /admin/organisations/{org_id}
POST /admin/organisations/{org_id}/verify
POST /admin/organisations/{org_id}/suspend
GET  /admin/projects
GET  /admin/security/fraud
GET  /admin/security/flagged-users
GET  /admin/staff
POST /admin/staff/{user_id}/roles          [super_admin only]
DELETE /admin/staff/{user_id}/roles/{role}  [super_admin only]
GET  /admin/recent-actions
```

---

## 18. Enums Reference

### feedback_type
| Value | Description |
|-------|-------------|
| `grievance` | Formal complaint requiring investigation and resolution |
| `suggestion` | Constructive idea or recommendation |
| `applause` | Positive feedback recognising good performance |

### status
| Value | Description | Applies To |
|-------|-------------|------------|
| `submitted` | Just received, not acknowledged | All |
| `acknowledged` | PIU confirmed receipt | All |
| `in_review` | Under investigation | Grievance |
| `escalated` | Moved to higher GRM level | Grievance |
| `resolved` | Resolution provided | All |
| `appealed` | Grievant challenged resolution | Grievance |
| `actioned` | Suggestion implemented | Suggestion |
| `noted` | Received but not implemented | Suggestion |
| `dismissed` | Unfounded/duplicate/out of scope | All |
| `closed` | Final state | All |

### priority
| Value | Ack SLA | Resolve SLA | Description |
|-------|---------|-------------|-------------|
| `critical` | 24 hours | 7 days | Safety risk, legal, World Bank escalation |
| `high` | 48 hours | 14 days | Significant PAP/project impact |
| `medium` | 5 days | 30 days | Standard grievance or suggestion |
| `low` | 10 days | — | Minor or informational |

### channel
| Value | Type | Description |
|-------|------|-------------|
| `sms` | AI | LLM converses via SMS |
| `whatsapp` | AI | LLM converses via WhatsApp |
| `whatsapp_voice` | AI | WhatsApp voice note → STT → LLM |
| `phone_call` | AI | Phone IVR/call with LLM |
| `mobile_app` | Self-service | Riviwa mobile app |
| `web_portal` | Self-service | Web frontend |
| `in_person` | Officer | Walk-in to PIU/LGA |
| `paper_form` | Officer | Physical form (Annex 5/6) |
| `email` | Officer | Email to PIU |
| `public_meeting` | Officer | Raised during consultation |
| `notice_box` | Officer | Complaint/suggestion box |
| `other` | Officer | Other channel |

### category
| Primarily For | Values |
|---------------|--------|
| **Grievance** | `compensation`, `resettlement`, `land_acquisition`, `construction_impact`, `traffic`, `worker_rights`, `safety_hazard`, `engagement`, `design_issue`, `project_delay`, `corruption` |
| **Suggestion** | `design`, `process`, `communication`, `community_benefit`, `employment` |
| **Applause** | `quality`, `timeliness`, `staff_conduct`, `community_impact`, `responsiveness` |
| **Shared** | `safety`, `environmental`, `accessibility`, `other` |

### grm_level (Escalation Hierarchy)
| Level | Name | Description |
|-------|------|-------------|
| 1 | `ward` | Ward/sub-project GHC |
| 2 | `lga_piu` | LGA GHC at PIU level |
| 3 | `pcu` | Programme Coordinating Unit |
| 4 | `tarura_wbcu` | TARURA World Bank Unit |
| 5 | `tanroads` | Road/bridge-specific |
| 6 | `world_bank` | Final escalation |

### org_role (within an organisation)
`owner`, `admin`, `manager`, `member`, `viewer`

### org_type
`business`, `government`, `ngo`, `academic`, `community`

### org_status
`pending_verification`, `active`, `suspended`, `banned`, `deactivated`
