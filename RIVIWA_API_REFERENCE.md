# Riviwa Platform — Full API Reference

> **Base URL (production):** `https://riviwa.com/api/v1`  
> **Auth:** `Authorization: Bearer <access_token>` unless noted  
> **Internal:** `X-Service-Key: <INTERNAL_SERVICE_KEY>` header  
> **Date format:** ISO 8601 — `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`

---

## Table of Contents

1. [Auth Service](#1-auth-service-port-8000)
2. [Feedback Service](#2-feedback-service-port-8090)
3. [AI Service](#3-ai-service-port-8085)
4. [Analytics Service](#4-analytics-service-port-8095)
5. [Stakeholder Service](#5-stakeholder-service-port-8070)
6. [Notification Service](#6-notification-service-port-8060)
7. [Translation Service](#7-translation-service-port-8050)
8. [Payment Service](#8-payment-service-port-8040)

---

## 1. Auth Service (port 8000)

### Registration

#### `POST /auth/register/init`
Start registration — send OTP to email or phone.
```json
{
  "email": "user@example.com",       // or use phone
  "phone": "+255712345678",          // E.164
  "full_name": "Amina Hassan",
  "account_type": "individual"       // individual | organisation
}
```

#### `POST /auth/register/verify-otp`
Verify registration OTP.
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

#### `POST /auth/register/complete`
Set password and activate account.
```json
{
  "email": "user@example.com",
  "otp": "123456",
  "password": "SecurePass@2026!",
  "full_name": "Amina Hassan"        // optional override
}
```

#### `POST /auth/register/resend-otp`
Resend registration OTP.
```json
{ "email": "user@example.com" }
```

---

### Authentication

#### `POST /auth/login`
Step 1 — submit credentials, receive OTP.
```json
{
  "email": "user@example.com",
  "password": "SecurePass@2026!"
}
```

#### `POST /auth/login/verify-otp`
Step 2 — verify OTP, receive tokens.
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```
**Response:** `{ access_token, refresh_token, token_type, expires_in, user: {...} }`

#### `POST /auth/refresh`
Refresh access token.
```json
{ "refresh_token": "eyJ..." }
```

#### `POST /auth/logout`
Revoke session.
```json
{ "refresh_token": "eyJ..." }
```

#### `POST /auth/switch-org`
Switch active org dashboard.
```json
{ "org_id": "uuid" }
```

#### `POST /auth/social`
Social login/registration.
```json
{
  "provider": "google",              // google | apple | facebook
  "token": "<provider_id_token>"
}
```

#### `POST /auth/social/set-password`
Set password on a social-only account.
```json
{
  "current_social_token": "<token>",
  "new_password": "SecurePass@2026!"
}
```

---

### Password

#### `POST /auth/password/forgot`
Forgot password — request OTP.
```json
{ "email": "user@example.com" }
```

#### `POST /auth/password/forgot/verify`
Verify forgot-password OTP.
```json
{ "email": "user@example.com", "otp": "123456" }
```

#### `POST /auth/password/forgot/reset`
Set new password.
```json
{
  "email": "user@example.com",
  "otp": "123456",
  "new_password": "NewPass@2026!"
}
```

#### `POST /auth/password/change`
Change password (authenticated).
```json
{
  "current_password": "OldPass@2026!",
  "new_password": "NewPass@2026!"
}
```

#### `POST /auth/password/channel-set`
Set first password for a channel-registered account (SMS/WhatsApp/Call).
```json
{
  "phone": "+255712345678",
  "otp": "123456",
  "new_password": "NewPass@2026!"
}
```

---

### Users

#### `GET /users/me`
Get my profile. **No body.**

#### `PATCH /users/me`
Update my profile.
```json
{
  "full_name": "Amina Hassan",
  "bio": "...",
  "language": "sw"
}
```

#### `DELETE /users/me`
Deactivate my account. **No body.**

#### `POST /users/me/avatar`
Update avatar URL.
```json
{ "avatar_url": "https://cdn.example.com/avatar.jpg" }
```

#### `POST /users/verify-email`
Mark email verified.
```json
{ "token": "<verification_token>" }
```

#### `POST /users/verify-phone`
Mark phone verified.
```json
{ "otp": "123456" }
```

#### `POST /users/{user_id}/suspend` `[Admin]`
```json
{ "reason": "Violation of terms" }
```

#### `POST /users/{user_id}/ban` `[Admin]`
```json
{ "reason": "Fraud detected" }
```

#### `POST /users/{user_id}/reactivate` `[Admin]`
**No body.**

---

### Organisations

#### `GET /orgs`
List my organisations. **No body.**

#### `POST /orgs`
Create an organisation.
```json
{
  "legal_name": "Dodoma Water Authority",
  "display_name": "DWA",
  "org_type": "government",          // government | ngo | private | parastatal
  "country_code": "TZ",
  "description": "Water utility...",
  "website_url": "https://dwa.go.tz",
  "support_email": "info@dwa.go.tz"
}
```

#### `GET /orgs/{org_id}`
Organisation details. **No body.**

#### `PATCH /orgs/{org_id}`
Update organisation.
```json
{
  "display_name": "DWA Tanzania",
  "description": "Updated description"
}
```

#### `DELETE /orgs/{org_id}`
Deactivate (close) organisation. **No body.**

#### `POST /orgs/{org_id}/verify` `[Admin]`
Verify organisation. **No body.**

#### `POST /orgs/{org_id}/suspend` `[Admin]`
```json
{ "reason": "Compliance issue" }
```

#### `POST /orgs/{org_id}/ban` `[Admin]`
```json
{ "reason": "Fraud" }
```

#### `POST /orgs/{org_id}/members`
Add member directly (no invite).
```json
{
  "user_id": "uuid",
  "role": "grm_officer"              // owner | admin | grm_coordinator | grm_officer | viewer
}
```

#### `DELETE /orgs/{org_id}/members/{user_id}`
Remove member. **No body.**

#### `PATCH /orgs/{org_id}/members/{user_id}/role`
Change member role.
```json
{ "role": "grm_coordinator" }
```

#### `POST /orgs/{org_id}/transfer-ownership`
Transfer org ownership.
```json
{ "new_owner_user_id": "uuid" }
```

---

### Org Extended (Branches, Departments, FAQs, Locations, Content)

#### `POST /orgs/{org_id}/branches`
Create a branch or sub-branch.
```json
{
  "name": "Dodoma Regional Office",
  "code": "DRO",
  "branch_type": "regional",
  "parent_branch_id": null           // null = top-level
}
```

#### `GET /orgs/{org_id}/branches`
List top-level branches. **No body.**

#### `POST /orgs/{org_id}/locations`
Add physical location.
```json
{
  "name": "Head Office",
  "address": "Plot 123, Dodoma",
  "region": "Dodoma",
  "lga": "Dodoma Urban",
  "latitude": -6.1722,
  "longitude": 35.7395,
  "branch_id": "uuid"                // optional
}
```

#### `GET /orgs/{org_id}/locations`
List locations. **No body.**

#### `PATCH /orgs/{org_id}/locations/{location_id}`
Update location. Same fields as POST.

#### `DELETE /orgs/{org_id}/locations/{location_id}`
Delete location. **No body.**

#### `GET /orgs/{org_id}/branches/{branch_id}/locations`
List locations for a specific branch. **No body.**

#### `GET /orgs/{org_id}/content`
Get content profile. **No body.**

#### `PUT /orgs/{org_id}/content`
Create or update content profile.
```json
{
  "tagline": "Quality water for all",
  "about": "Long description...",
  "logo_url": "https://cdn.example.com/logo.png",
  "banner_url": "https://cdn.example.com/banner.png"
}
```

#### `POST /orgs/{org_id}/faqs`
Add FAQ.
```json
{
  "question": "How do I submit a complaint?",
  "answer": "Visit our portal at...",
  "display_order": 1,
  "is_published": true
}
```

#### `GET /orgs/{org_id}/faqs`
List FAQs. **No body.**

#### `PATCH /orgs/{org_id}/faqs/{faq_id}`
Update FAQ. Same fields as POST.

#### `DELETE /orgs/{org_id}/faqs/{faq_id}`
Delete FAQ. **No body.**

---

### Departments

#### `POST /departments`
Create department.
```json
{
  "org_id": "uuid",
  "name": "Customer Care",
  "code": "CC",
  "branch_id": "uuid"               // optional — which branch this dept belongs to
}
```

#### `GET /departments`
List departments. Query: `?org_id=uuid`

#### `GET /departments/{dept_id}`
Department detail. **No body.**

#### `PATCH /departments/{dept_id}`
Update department.
```json
{ "name": "Customer Relations", "is_active": true }
```

#### `DELETE /departments/{dept_id}`
Deactivate department. **No body.**

---

### Projects

#### `POST /projects`
Create execution project.
```json
{
  "org_id": "uuid",
  "name": "Dodoma Water Supply Phase 2",
  "code": "DWS-P2",
  "sector": "water_sanitation",
  "category": "infrastructure",
  "description": "...",
  "region": "Dodoma",
  "primary_lga": "Dodoma Urban",
  "start_date": "2026-01-01",
  "end_date": "2028-12-31",
  "budget": 5000000.00,
  "funding_source": "World Bank",
  "accepts_grievances": true,
  "accepts_suggestions": true,
  "accepts_applause": true
}
```

#### `GET /projects`
List projects. Query: `?org_id=uuid&status=active`

#### `GET /projects/{project_id}`
Project detail with stages and in-charges. **No body.**

#### `PATCH /projects/{project_id}`
Update project fields. Same fields as POST.

#### `POST /projects/{project_id}/activate`
Activate project (PLANNING → ACTIVE). **No body.**

#### `POST /projects/{project_id}/pause`
Pause project. **No body.**

#### `POST /projects/{project_id}/resume`
Resume paused project. **No body.**

#### `POST /projects/{project_id}/complete`
Mark project completed. **No body.**

#### `DELETE /projects/{project_id}`
Cancel and soft-delete. **No body.**

#### `POST /projects/{project_id}/in-charges`
Assign person to project leadership.
```json
{
  "user_id": "uuid",
  "role": "project_manager",
  "phone": "+255712345678"
}
```

#### `GET /projects/{project_id}/in-charges`
List project leadership. **No body.**

#### `DELETE /projects/{project_id}/in-charges/{user_id}`
Relieve from leadership. **No body.**

#### `POST /projects/{project_id}/stages`
Add a stage.
```json
{
  "name": "Construction Phase 1",
  "description": "...",
  "start_date": "2026-06-01",
  "end_date": "2027-06-01",
  "order": 1
}
```

---

### Channel Auth (Internal)

#### `POST /internal/channel/register`
Auto-register Consumer from inbound channel.
```json
{
  "phone": "+255712345678",
  "channel": "whatsapp",             // sms | whatsapp | phone_call
  "name": "Fatuma"                   // optional
}
```

#### `POST /internal/channel/login/request-otp`
Channel login Step 1 — send OTP.
```json
{ "phone": "+255712345678", "channel": "sms" }
```

#### `POST /internal/channel/login/verify-otp`
Channel login Step 2 — verify OTP, receive tokens.
```json
{ "phone": "+255712345678", "otp": "123456" }
```

---

### Internal Org Context

#### `GET /internal/orgs/{org_id}/ai-context` `[Service Key]`
Compact org profile for AI enrichment.  
Returns: org name, branches (with IDs), departments, services, products, FAQs.

#### `GET /internal/departments/{dept_id}` `[Service Key]`
Resolve department → branch_id.  
Returns: `{ id, name, code, branch_id }`

---

### Admin Dashboard `[Admin]`

#### `GET /admin/dashboard/summary`
Platform KPIs — user counts, org counts, verification queue size.

#### `GET /admin/dashboard/users`
List all users. Query: `?status=active&page=1&limit=50`

#### `GET /admin/dashboard/users/{user_id}`
Full admin view of a user.

#### `GET /admin/dashboard/users/growth`
Daily registration trend (chart data). Query: `?days=30`

#### `GET /admin/dashboard/users/status-breakdown`
Users by account status.

#### `POST /admin/dashboard/users/{user_id}/suspend`
```json
{ "reason": "..." }
```

#### `POST /admin/dashboard/users/{user_id}/ban`
```json
{ "reason": "..." }
```

#### `POST /admin/dashboard/users/{user_id}/reactivate`
**No body.**

#### `GET /admin/dashboard/orgs`
List all organisations. Query: `?status=verified&page=1`

#### `GET /admin/dashboard/orgs/pending-verification`
Orgs awaiting platform verification.

#### `GET /admin/dashboard/orgs/breakdown`
Orgs by type and status.

#### `GET /admin/dashboard/orgs/growth`
Daily org creation trend.

#### `GET /admin/dashboard/orgs/member-distribution`
Platform-wide member role distribution.

---

## 2. Feedback Service (port 8090)

### Staff Feedback

#### `POST /feedback`
Submit feedback (grievance / suggestion / applause / inquiry) — staff.
```json
{
  "project_id": "uuid",              // required
  "feedback_type": "grievance",      // grievance | suggestion | applause | inquiry
  "category": "infrastructure",
  "channel": "in_person",           // walk_in | phone | email | sms | whatsapp | in_person | web_portal | mobile_app
  "subject": "Broken water pipe",
  "description": "The main supply pipe on Kilimani Street burst...",
  "is_anonymous": false,
  "submitter_name": "Amina Hassan",
  "submitter_phone": "+255712345678",
  "submitter_email": "amina@example.com",
  "submitter_type": "individual",    // individual | group | organisation
  "group_size": null,
  "submitter_location_region": "Dodoma",
  "submitter_location_district": "Dodoma",
  "submitter_location_lga": "Dodoma Urban",
  "submitter_location_ward": "Kilimani",
  "submitter_location_street": "Kilimani Street, Plot 12",
  "issue_region": "Dodoma",
  "issue_district": "Dodoma",
  "issue_lga": "Dodoma Urban",
  "issue_ward": "Kilimani",
  "issue_mtaa": "Mtaa wa Kilimani",
  "issue_location_description": "Near the secondary school gate",
  "issue_gps_lat": -6.1722,
  "issue_gps_lng": 35.7395,
  "date_of_incident": "2026-04-20",
  "priority": "high",               // low | medium | high | critical
  "department_id": "uuid",          // optional — which department handles it
  "branch_id": "uuid",              // optional — auto-resolved from dept if omitted
  "service_id": "uuid",             // optional — which service this is about
  "product_id": "uuid",             // optional — which product this is about
  "subproject_id": "uuid",          // optional — work package
  "media_urls": ["https://..."],
  "internal_notes": "Walk-in complaint logged by officer",
  "stakeholder_engagement_id": "uuid",
  "distribution_id": "uuid",
  "officer_recorded": true,
  "submitted_at": "2026-04-20T09:00:00Z"  // backdating support
}
```

#### `POST /feedback/bulk-upload`
Bulk import from CSV. `multipart/form-data`
- `file` — CSV file
- `project_id` — UUID (form field)

#### `GET /feedback`
List feedback records (staff, org-scoped).  
Query: `?project_id=uuid&feedback_type=grievance&status=submitted&priority=high&page=1&limit=20&date_from=2026-01-01&date_to=2026-12-31`

#### `GET /feedback/{feedback_id}`
Feedback detail with full history. **No body.**

#### `PATCH /feedback/{feedback_id}/acknowledge`
Acknowledge receipt.
```json
{
  "priority": "high",
  "note": "Received and logged",
  "response_method": "phone",
  "response_summary": "Called grievant",
  "assigned_to_user_id": "uuid",
  "target_resolution_date": "2026-05-01"
}
```

#### `PATCH /feedback/{feedback_id}/assign`
Assign to staff or committee.
```json
{
  "assigned_to_user_id": "uuid",    // assign to a person
  "committee_id": "uuid"            // or assign to a committee
}
```

#### `POST /feedback/{feedback_id}/escalate`
Escalate to next GRM level.
```json
{
  "reason": "Unresolved after 14 days",
  "target_level": "district"        // optional — defaults to next level
}
```

#### `POST /feedback/{feedback_id}/resolve`
Record resolution.
```json
{
  "resolution_description": "Pipe repaired on 2026-04-25",
  "resolution_type": "fully_resolved",   // fully_resolved | partially_resolved | no_action
  "response_method": "phone",
  "response_summary": "Informed grievant",
  "resolved_at": "2026-04-25T14:00:00Z"
}
```

#### `POST /feedback/{feedback_id}/appeal`
File appeal against resolution.
```json
{
  "grounds": "Resolution was inadequate — pipe still leaks",
  "additional_evidence_urls": ["https://..."]
}
```

#### `PATCH /feedback/{feedback_id}/close`
Close feedback.
```json
{ "reason": "Resolved and confirmed by grievant" }
```

#### `PATCH /feedback/{feedback_id}/dismiss`
Dismiss feedback (admin/owner only).
```json
{ "reason": "Duplicate submission" }
```

#### `PATCH /feedback/{feedback_id}/ai-enrich` `[Internal]`
AI enrichment — set project_id and/or category_def_id.
```json
{
  "project_id": "uuid",
  "category_def_id": "uuid",
  "category_slug": "water_supply"
}
```

---

### Consumer Feedback

#### `GET /my/feedback`
List my feedback submissions. Query: `?project_id=uuid&status=submitted`

#### `GET /my/feedback/summary`
Dashboard widget counts. Query: `?project_id=uuid`

#### `GET /my/feedback/{feedback_id}`
Track a specific submission — full handling history. **No body.**

#### `POST /my/feedback`
Submit feedback (consumer).
```json
{
  "feedback_type": "grievance",      // required
  "description": "Full description of the issue",  // required
  "issue_lga": "Dodoma Urban",       // required
  "project_id": "uuid",              // optional — AI auto-detects if omitted
  "category": "water_supply",
  "subject": "No water for 3 days",
  "is_anonymous": false,
  "submitter_name": "Amina Hassan",
  "submitter_phone": "+255712345678",
  "issue_ward": "Kilimani",
  "issue_location_description": "Near school gate",
  "issue_gps_lat": -6.1722,
  "issue_gps_lng": 35.7395,
  "subproject_id": "uuid",
  "department_id": "uuid",
  "service_id": "uuid",
  "product_id": "uuid",
  "date_of_incident": "2026-04-20",
  "media_urls": ["https://..."]
}
```

#### `POST /my/feedback/{feedback_id}/escalation-request`
Request GRM Unit to escalate grievance.
```json
{
  "reason": "No response in 21 days",
  "additional_details": "..."
}
```

#### `POST /my/feedback/{feedback_id}/appeal`
File formal appeal.
```json
{
  "grounds": "Resolution did not address root cause",
  "desired_outcome": "Full repair of the pipe"
}
```

#### `POST /my/feedback/{feedback_id}/add-comment`
Add follow-up comment.
```json
{ "comment": "Still not resolved as of today" }
```

---

### Escalation Requests (Staff)

#### `GET /escalation-requests`
List consumer escalation requests. Query: `?project_id=uuid&status=pending`

#### `POST /escalation-requests/{request_id}/approve`
Approve escalation request.
```json
{ "note": "Approved — escalating to district level" }
```

#### `POST /escalation-requests/{request_id}/reject`
Reject with explanation.
```json
{ "reason": "Already in resolution process" }
```

---

### Actions

#### `POST /feedback/{feedback_id}/actions`
Log an action.
```json
{
  "action_type": "site_visit",       // acknowledgement | site_visit | investigation | meeting | communication | resolution | escalation | appeal | closure
  "description": "Visited site on 2026-04-22",
  "performed_by_user_id": "uuid",
  "action_date": "2026-04-22T10:00:00Z",
  "notes": "Confirmed damage"
}
```

#### `GET /feedback/{feedback_id}/actions`
List action log. **No body.**

---

### Categories

#### `POST /categories`
Create a feedback category.
```json
{
  "project_id": "uuid",             // null = global
  "name": "Water Supply",
  "slug": "water_supply",
  "description": "Issues related to water supply",
  "parent_id": "uuid",              // optional — for sub-categories
  "is_active": true
}
```

#### `GET /categories`
List categories. Query: `?project_id=uuid&is_active=true`

#### `GET /categories/summary`
Category counts for dashboard. Query: `?project_id=uuid`

#### `GET /categories/{category_id}`
Category detail. **No body.**

#### `PATCH /categories/{category_id}`
Update category.
```json
{ "name": "Water & Sanitation", "is_active": true }
```

#### `GET /categories/{category_id}/rate`
Feedback rate for category. Query: `?project_id=uuid&period=7d`

#### `POST /categories/{category_id}/approve`
Approve ML-suggested category.
```json
{ "note": "Verified by coordinator" }
```

#### `POST /categories/{category_id}/reject`
Reject ML-suggested category.
```json
{ "reason": "Too similar to existing category" }
```

#### `POST /categories/{category_id}/deactivate`
Deactivate category.
```json
{ "reason": "Replaced by more specific categories" }
```

#### `POST /categories/{category_id}/merge`
Merge into another category.
```json
{ "target_category_id": "uuid" }
```

#### `POST /feedback/{feedback_id}/classify`
Run ML classification.
```json
{ "force": false }
```

#### `PATCH /feedback/{feedback_id}/recategorise`
Manually reassign category.
```json
{ "category_def_id": "uuid", "reason": "Incorrect auto-classification" }
```

---

### Committees

#### `POST /committees`
Create a Grievance Handling Committee (GHC).
```json
{
  "project_id": "uuid",
  "name": "Ward GHC — Kilimani",
  "description": "...",
  "grm_level": "ward",              // ward | district | regional | national
  "meeting_frequency": "monthly"
}
```

#### `GET /committees`
List GHCs. Query: `?project_id=uuid&grm_level=ward`

#### `PATCH /committees/{committee_id}`
Update committee.
```json
{ "name": "Updated Name", "meeting_frequency": "weekly" }
```

#### `POST /committees/{committee_id}/stakeholders/{stakeholder_id}`
Add stakeholder group coverage. **No body.**

#### `DELETE /committees/{committee_id}/stakeholders/{stakeholder_id}`
Remove stakeholder coverage. **No body.**

#### `POST /committees/{committee_id}/members`
Add member.
```json
{
  "user_id": "uuid",
  "role": "chairperson"             // chairperson | secretary | member
}
```

#### `DELETE /committees/{committee_id}/members/{user_id}`
Remove member. **No body.**

---

### Escalation Paths

#### `POST /escalation-paths`
Create escalation path.
```json
{
  "org_id": "uuid",
  "name": "Standard GRM Path",
  "description": "Default 4-level escalation",
  "is_default": true
}
```

#### `POST /escalation-paths/clone-from-template`
Clone system template.
```json
{
  "org_id": "uuid",
  "template_id": "uuid",
  "name": "Our Custom Path"
}
```

#### `GET /escalation-paths`
List org paths. Query: `?org_id=uuid`

#### `GET /escalation-paths/system-templates`
List read-only system templates. **No body.**

#### `GET /escalation-paths/{path_id}`
Path detail with levels. **No body.**

#### `PATCH /escalation-paths/{path_id}`
Update metadata.
```json
{ "name": "Updated", "is_default": true, "is_active": true }
```

#### `DELETE /escalation-paths/{path_id}`
Deactivate (soft delete). **No body.**

#### `POST /escalation-paths/{path_id}/levels`
Add level.
```json
{
  "name": "Ward Level",
  "grm_level": "ward",
  "sla_days": 14,
  "auto_escalate": true,
  "auto_escalate_after_days": 21,
  "order": 1
}
```

#### `POST /escalation-paths/{path_id}/levels/reorder`
Reorder levels.
```json
{ "level_ids": ["uuid1", "uuid2", "uuid3"] }
```

#### `PATCH /escalation-paths/{path_id}/levels/{level_id}`
Update level.
```json
{ "sla_days": 10, "auto_escalate_after_days": 14 }
```

#### `DELETE /escalation-paths/{path_id}/levels/{level_id}`
Remove level. **No body.**

---

### Voice (Feedback Service)

#### `POST /voice/feedback/{feedback_id}/voice-note`
Attach a voice note to a feedback record. `multipart/form-data`
- `audio` — audio file (OGG/WebM/MP3/WAV/AAC/AMR, max 25 MB)
- `language` — `sw` or `en` (default: `sw`)
- `use_as_description` — `true`/`false` — populate description from transcript

**Response:** `{ voice_note_url, voice_note_transcription, voice_note_language, voice_note_confidence, voice_note_duration_seconds }`

#### `POST /voice/sessions/{session_id}/audio-turn`
Submit a voice turn in an active ChannelSession. `multipart/form-data`
- `audio` — audio file
- `language` — hint

#### `POST /voice/sessions/{session_id}/tts`
Synthesise TTS audio reply.
```json
{
  "text": "Asante kwa kuwasiliana nasi...",
  "language": "sw",
  "voice": "Google.sw-TZ-Standard-A"
}
```

---

### Channel Sessions (AI Conversation — Feedback Service)

#### `POST /ai-sessions`
Start AI-powered feedback conversation.
```json
{
  "channel": "mobile_app",           // mobile_app | web_portal | whatsapp | sms | phone_call
  "language": "sw",
  "project_id": "uuid",             // optional
  "org_id": "uuid"                  // optional
}
```

#### `POST /ai-sessions/{session_id}/message`
Send a message.
```json
{ "message": "Nina tatizo..." }
```

#### `GET /ai-sessions/{session_id}`
Session status and transcript. **No body.**

#### `POST /channel-sessions`
Start staff-managed channel session.
```json
{
  "channel": "phone_call",
  "project_id": "uuid",
  "language": "sw"
}
```

#### `GET /channel-sessions`
List sessions. Query: `?project_id=uuid&status=active`

#### `GET /channel-sessions/{session_id}`
Session detail with transcript. **No body.**

#### `POST /channel-sessions/{session_id}/message`
Add Consumer message turn and get LLM reply.
```json
{ "message": "..." }
```

#### `POST /channel-sessions/{session_id}/submit`
Force-submit feedback from extracted data. **No body.**

#### `POST /channel-sessions/{session_id}/abandon`
Mark session abandoned.
```json
{ "reason": "Consumer hung up" }
```

---

### Webhooks (Feedback Service)

#### `POST /webhooks/sms`
Inbound SMS (Africa's Talking / Twilio). Form-encoded body from provider.

#### `POST /webhooks/whatsapp`
Inbound WhatsApp (Meta Cloud API). Supports text, **voice notes** (auto-transcribed), images, documents.
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "type": "audio",
          "from": "255712000001",
          "audio": { "id": "WHATSAPP_MEDIA_ID" }
        }]
      }
    }]
  }]
}
```

#### `GET /webhooks/whatsapp`
WhatsApp webhook verification (Meta hub.challenge). **No body.**

---

### Reports

#### `GET /reports/performance`
Overall performance dashboard. Query: `?project_id=uuid&date_from=2026-01-01&format=json`

#### `GET /reports/grievances`
Grievance performance page. Query: `?project_id=uuid&date_from=...&format=csv`

#### `GET /reports/grievances/full`
Comprehensive grievance performance report.

#### `GET /reports/suggestions`
Suggestion performance page.

#### `GET /reports/suggestions/full`
Comprehensive suggestion performance report.

#### `GET /reports/suggestions/detailed`
Detailed suggestion performance — rate, category, location, implementation time.

#### `GET /reports/applause`
Applause performance page.

#### `GET /reports/applause/full`
Comprehensive applause performance report.

#### `GET /reports/channels`
Breakdown by intake channel.

#### `GET /reports/grievance-log`
Full grievance log (SEP Annex 5/6 format). Query: `?project_id=uuid&format=csv`

#### `GET /reports/suggestion-log`
Full suggestion log.

#### `GET /reports/applause-log`
Full applause log.

#### `GET /reports/summary`
Count summary.

#### `GET /reports/overdue`
Grievances past target resolution date.

---

## 3. AI Service (port 8085)

### Conversations

#### `POST /ai/conversations/start`
Start a new AI conversation.
```json
{
  "channel": "web",                  // web | mobile | sms | whatsapp | phone_call
  "language": "sw",                  // sw | en (default: sw)
  "org_id": "uuid",                 // optional — bind to org
  "project_id": "uuid",             // optional — pre-select project
  "user_id": "uuid",                // optional — link to authenticated user
  "web_token": "session-token"      // optional — anonymous web session
}
```
**Response:** `{ conversation_id, reply, status, stage, turn_count, confidence, language, ... }`

#### `POST /ai/conversations/{conversation_id}/message`
Send a text message.
```json
{
  "message": "Habari, nina tatizo na bomba...",
  "media_urls": ["https://..."]      // optional — photo evidence
}
```
**Response:** `{ conversation_id, reply, status, stage, turn_count, confidence, language, submitted, submitted_feedback, project_name, is_urgent, incharge_name, incharge_phone }`

#### `GET /ai/conversations/{conversation_id}`
Get conversation with full transcript.  
**Response:** `{ conversation_id, channel, status, stage, language, turn_count, confidence, is_registered, submitter_name, project_id, project_name, extracted_data, submitted_feedback, transcript: [{role, content, timestamp, audio_url?}], is_urgent, incharge_name, incharge_phone, started_at, last_active_at, completed_at }`

---

### Voice — Web/Mobile

#### `POST /ai/conversations/{conversation_id}/voice-message`
Send a voice message. `multipart/form-data`
- `audio` — audio file (WebM/OGG/WAV/MP3/M4A/AAC, max 25 MB)

**Response (extends standard chat response):**
```json
{
  "reply": "Asante...",
  "transcript": "Nina tatizo na bomba...",
  "detected_language": "sw",
  "stt_confidence": 0.87,
  "translated": false,
  "original_reply": "Asante...",
  "audio_url": "http://minio:9000/riviwa-voice/ai-conversations/..."
}
```

---

### Voice — Twilio Phone Call

#### `POST /ai/voice/call/inbound`
Twilio: caller dials in. Form-encoded (Twilio format).  
Returns TwiML greeting + `<Record>`.

#### `POST /ai/voice/call/gather`
Twilio: recording ready. Query: `?call_sid=CA...&conv_id=uuid`  
Downloads MP3, transcribes, feeds AI, returns TwiML reply.

#### `POST /ai/voice/call/status`
Twilio: call status change. Query: `?conv_id=uuid`  
Closes conversation on terminal states. Returns HTTP 204.

---

### Webhooks (AI Service)

#### `POST /ai/webhooks/sms`
Inbound SMS (Africa's Talking / Twilio). Form-encoded from provider.

#### `POST /ai/webhooks/whatsapp`
Inbound WhatsApp. Handles text and **audio voice notes**.
```json
{
  "entry": [{ "changes": [{ "value": { "messages": [{ "type": "audio", "from": "255712...", "audio": { "id": "MEDIA_ID" } }] } }] }]
}
```

#### `GET /ai/webhooks/whatsapp`
WhatsApp verification endpoint. **No body.**

---

### Admin (AI Service) `[Staff]`

#### `GET /ai/admin/conversations`
List all AI conversations. Query: `?status=active&channel=web&page=1&limit=20`

#### `GET /ai/admin/conversations/{conversation_id}`
Conversation detail with full transcript. **No body.**

#### `POST /ai/admin/conversations/{conversation_id}/force-submit`
Force-submit extracted feedback. **No body.**

#### `POST /ai/admin/reindex-projects`
Re-index all projects into Qdrant vector store. **No body.**

#### `POST /ai/admin/index-vault`
Index Obsidian GRM knowledge base vault into Qdrant. **No body.**

---

### Internal (AI Service) `[Service Key]`

#### `POST /ai/internal/classify`
Auto-classify feedback — detect project_id and category.
```json
{
  "description": "Bomba la maji limeharibiwa...",
  "issue_lga": "Dodoma Urban",
  "issue_ward": "Kilimani",
  "org_id": "uuid"                  // optional
}
```
**Response:** `{ project_id, project_name, category_slug, category_def_id, confidence }`

#### `POST /ai/internal/candidate-projects`
Return candidate projects for a feedback description.
```json
{
  "description": "Road damage near school",
  "org_id": "uuid",
  "limit": 5
}
```

---

## 4. Analytics Service (port 8095)

> **Auth:** Staff JWT (`Authorization: Bearer <token>`)  
> **Common query params:** `?project_id=uuid`, `?date_from=YYYY-MM-DD`, `?date_to=YYYY-MM-DD`

---

### AI Insights

#### `POST /analytics/ai/ask`
Ask analytics question in natural language.
```json
{
  "question": "What is the top grievance category this month?",
  "scope": "project",               // project | org | platform
  "context_type": "general",        // see below
  "project_id": "uuid",            // required for scope=project
  "org_id": "uuid"                  // required for scope=org
}
```
**Context types:**
- `project`: `general` | `grievances` | `suggestions` | `sla` | `committees` | `hotspots` | `staff` | `unresolved` | `inquiries`
- `org`: `org_general` | `org_grievances` | `org_suggestions` | `org_applause` | `org_inquiries`
- `platform`: `platform_general` | `platform_grievances` | `platform_suggestions` | `platform_applause` | `platform_inquiries`

**Response:** `{ answer, context_used, model }`

#### `POST /analytics/ai/ask-voice`
Ask analytics question **by voice audio**. `multipart/form-data`
- `audio` — audio file (WebM/OGG/WAV/MP3/M4A/AAC, max 25 MB)
- `scope` — `project` | `org` | `platform`
- `context_type` — same values as `/ask`
- `project_id` — UUID (required for scope=project)
- `org_id` — UUID (required for scope=org)
- `language` — `sw` | `en` (STT hint, default: `sw`)

**Response:** `{ answer, context_used, model, transcript, detected_language }`

---

### Feedback Analytics

All endpoints require `?project_id=uuid`.  
Optional filters: `?feedback_type=grievance&date_from=...&date_to=...&department_id=uuid&service_id=uuid&product_id=uuid&category_def_id=uuid`

#### `GET /analytics/feedback/time-to-open`
Average time from submission to first acknowledgement.

#### `GET /analytics/feedback/unread`
List unread (unacknowledged) feedback items.

#### `GET /analytics/feedback/overdue`
Feedback past target resolution date.

#### `GET /analytics/feedback/not-processed`
Submitted feedback with no action taken.

#### `GET /analytics/feedback/processed-today`
Feedback processed today.

#### `GET /analytics/feedback/resolved-today`
Feedback resolved today.

#### `GET /analytics/feedback/by-service`
Breakdown by service_id. Query: `?project_id=uuid&feedback_type=...`

#### `GET /analytics/feedback/by-product`
Breakdown by product_id.

#### `GET /analytics/feedback/by-category`
Breakdown by category_def_id (dynamic categories).

#### `GET /analytics/feedback/by-department`
Breakdown by department_id.

#### `GET /analytics/feedback/by-stage`
Breakdown by project stage.

#### `GET /analytics/feedback/by-branch`
Breakdown by branch_id.

---

### Grievance Analytics

#### `GET /analytics/grievances/unresolved`
Unresolved grievances list. Query: `?project_id=uuid&priority=high`

#### `GET /analytics/grievances/sla-status`
SLA compliance status. Query: `?project_id=uuid`

#### `GET /analytics/grievances/dashboard`
Full grievance dashboard. Query: `?project_id=uuid`

#### `GET /analytics/grievances/hotspots`
Geographic hotspots. Query: `?project_id=uuid`

---

### Suggestion Analytics

#### `GET /analytics/suggestions/implementation-time`
Average time to implement suggestions. Query: `?project_id=uuid`

#### `GET /analytics/suggestions/frequency`
Suggestion submission frequency over time.

#### `GET /analytics/suggestions/by-location`
Suggestions broken down by location (LGA/ward).

#### `GET /analytics/suggestions/unread`
Unread suggestions.

#### `GET /analytics/suggestions/implemented-today`
Suggestions implemented today.

#### `GET /analytics/suggestions/implemented-this-week`
Suggestions implemented this week.

---

### Staff Analytics

#### `GET /analytics/staff/committee-performance`
Committee performance metrics. Query: `?project_id=uuid`

#### `GET /analytics/staff/last-logins`
Staff last login timestamps. Query: `?org_id=uuid`

#### `GET /analytics/staff/unread-assigned`
Feedback assigned to staff but not yet read.

#### `GET /analytics/staff/login-not-read`
Staff who logged in but haven't read assigned feedback.

---

### Inquiry Analytics

#### `GET /analytics/inquiries/summary`
Inquiry summary. Query: `?project_id=uuid`

#### `GET /analytics/inquiries/unread`
Unread inquiries.

#### `GET /analytics/inquiries/overdue`
Overdue inquiries.

#### `GET /analytics/inquiries/by-channel`
Inquiries by channel.

#### `GET /analytics/inquiries/by-category`
Inquiries by category.

---

### Org Analytics

All endpoints: `?date_from=...&date_to=...&feedback_type=grievance`

#### `GET /analytics/org/{org_id}/summary`
Org-level summary — total feedback, by type, by status.

#### `GET /analytics/org/{org_id}/by-project`
Feedback counts per project.

#### `GET /analytics/org/{org_id}/by-period`
Trend over time. Query: `?period=month` (day|week|month)

#### `GET /analytics/org/{org_id}/by-channel`
Breakdown by intake channel.

#### `GET /analytics/org/{org_id}/by-branch`
Breakdown by branch_id (with counts, resolved %, avg resolution hours).

#### `GET /analytics/org/{org_id}/by-department`
Breakdown by department_id.

#### `GET /analytics/org/{org_id}/by-service`
Breakdown by service_id.

#### `GET /analytics/org/{org_id}/by-product`
Breakdown by product_id.

#### `GET /analytics/org/{org_id}/by-category`
Breakdown by category_def_id.

#### `GET /analytics/org/{org_id}/grievances/summary`
Org grievance summary.

#### `GET /analytics/org/{org_id}/grievances/by-level`
Grievances by GRM level.

#### `GET /analytics/org/{org_id}/grievances/by-location`
Grievances by location (region/LGA/ward).

#### `GET /analytics/org/{org_id}/grievances/dashboard`
Full grievance dashboard for org.

#### `GET /analytics/org/{org_id}/grievances/sla`
SLA compliance for org.

#### `GET /analytics/org/{org_id}/suggestions/summary`
Org suggestion summary.

#### `GET /analytics/org/{org_id}/suggestions/by-project`
Suggestions per project.

#### `GET /analytics/org/{org_id}/applause/summary`
Applause summary.

#### `GET /analytics/org/{org_id}/inquiries/summary`
Inquiry summary.

---

### Platform Analytics `[Admin/Platform Staff]`

#### `GET /analytics/platform/summary`
Platform-wide summary.

#### `GET /analytics/platform/by-org`
Feedback per organisation.

#### `GET /analytics/platform/by-period`
Trend over time.

#### `GET /analytics/platform/by-channel`
Breakdown by channel.

#### `GET /analytics/platform/by-branch`
Platform-wide by-branch breakdown.

#### `GET /analytics/platform/by-department`
Platform-wide by-department breakdown.

#### `GET /analytics/platform/by-service`
Platform-wide by-service breakdown.

#### `GET /analytics/platform/by-product`
Platform-wide by-product breakdown.

#### `GET /analytics/platform/by-category`
Platform-wide by-category breakdown.

#### `GET /analytics/platform/grievances/summary`
Platform grievance summary.

#### `GET /analytics/platform/grievances/dashboard`
Platform grievance dashboard.

#### `GET /analytics/platform/grievances/sla`
Platform SLA compliance.

#### `GET /analytics/platform/suggestions/summary`
Platform suggestion summary.

#### `GET /analytics/platform/applause/summary`
Platform applause summary.

#### `GET /analytics/platform/inquiries/summary`
Platform inquiry summary.

---

## 5. Stakeholder Service (port 8070)

### Stakeholders

#### `POST /stakeholders`
Register a stakeholder group.
```json
{
  "project_id": "uuid",
  "name": "Kilimani Residents Association",
  "category": "affected_community",  // affected_community | government | ngo | private | media | vulnerable
  "vulnerability_flags": ["women", "youth"],
  "influence_level": "medium",       // low | medium | high
  "impact_level": "high",
  "is_pap": true,                    // Project Affected Person
  "description": "...",
  "location_region": "Dodoma",
  "location_lga": "Dodoma Urban",
  "location_ward": "Kilimani"
}
```

#### `GET /stakeholders`
List stakeholders. Query: `?project_id=uuid&category=affected_community&is_pap=true`

#### `GET /stakeholders/analysis`
Stakeholder analysis matrix (SEP Annex 3 format). Query: `?project_id=uuid`

#### `GET /stakeholders/{stakeholder_id}`
Stakeholder detail with contacts. **No body.**

#### `PATCH /stakeholders/{stakeholder_id}`
Update stakeholder profile. Same fields as POST.

#### `DELETE /stakeholders/{stakeholder_id}` `[Admin]`
Soft-delete. **No body.**

#### `POST /stakeholders/{stakeholder_id}/projects`
Register stakeholder under a project.
```json
{
  "project_id": "uuid",
  "relationship_type": "affected",
  "notes": "..."
}
```

#### `GET /stakeholders/{stakeholder_id}/projects`
List project registrations. **No body.**

#### `GET /stakeholders/{stakeholder_id}/engagements`
Engagement history. **No body.**

---

### Contacts

#### `POST /stakeholders/{stakeholder_id}/contacts`
Add contact.
```json
{
  "name": "Juma Mohamed",
  "role": "Chairperson",
  "phone": "+255712345678",
  "email": "juma@example.com",
  "is_primary": true,
  "language": "sw"
}
```

#### `GET /stakeholders/{stakeholder_id}/contacts`
List contacts. Query: `?active_only=true`

#### `PATCH /stakeholders/{stakeholder_id}/contacts/{contact_id}`
Update contact. Same fields as POST.

#### `DELETE /stakeholders/{stakeholder_id}/contacts/{contact_id}`
Deactivate contact.
```json
{ "reason": "Person left organisation" }
```

---

### Activities

#### `POST /activities`
Create engagement activity.
```json
{
  "project_id": "uuid",
  "stage_id": "uuid",
  "activity_type": "consultation",   // consultation | information_dissemination | field_visit | training | public_hearing
  "title": "Community Meeting — Kilimani Ward",
  "description": "...",
  "location": "Kilimani Community Hall",
  "scheduled_date": "2026-05-15T10:00:00Z",
  "lga": "Dodoma Urban",
  "ward": "Kilimani"
}
```

#### `GET /activities`
List activities. Query: `?project_id=uuid&activity_type=consultation&date_from=...`

#### `GET /activities/{activity_id}`
Activity detail with attendance. **No body.**

#### `PATCH /activities/{activity_id}`
Update / mark as conducted.
```json
{
  "actual_date": "2026-05-15T10:30:00Z",
  "status": "conducted",
  "attendance_count": 45,
  "summary": "Meeting went well..."
}
```

#### `POST /activities/{activity_id}/attendances`
Log attendance.
```json
{
  "stakeholder_id": "uuid",
  "contact_id": "uuid",
  "attended": true,
  "notes": "..."
}
```

#### `PATCH /activities/{activity_id}/attendances/{engagement_id}`
Update attendance record.
```json
{ "attended": true, "concerns_raised": "Road dust is causing health issues" }
```

#### `POST /activities/{activity_id}/attendances/bulk`
Bulk log attendance.
```json
{
  "attendances": [
    { "stakeholder_id": "uuid", "contact_id": "uuid", "attended": true },
    { "stakeholder_id": "uuid2", "contact_id": "uuid2", "attended": false }
  ]
}
```

#### `DELETE /activities/{activity_id}/attendances/{engagement_id}`
Remove attendance record. **No body.**

#### `POST /activities/{activity_id}/cancel`
Cancel activity.
```json
{ "reason": "Venue not available" }
```

#### `POST /activities/{activity_id}/media`
Upload file (photo, PDF minutes). `multipart/form-data`
- `file` — file to upload
- `title` — display title
- `media_type` — `photo` | `document` | `presentation`

#### `GET /activities/{activity_id}/media`
List activity media files. **No body.**

#### `DELETE /activities/{activity_id}/media/{media_id}`
Remove media file. **No body.**

---

### Communications

#### `POST /communications`
Log a communication record.
```json
{
  "project_id": "uuid",
  "stage_id": "uuid",
  "title": "Project Update Newsletter — April 2026",
  "communication_type": "newsletter", // newsletter | sms | notice | social_media | radio | meeting_minutes
  "description": "...",
  "date": "2026-04-01",
  "target_audience": "all_stakeholders"
}
```

#### `GET /communications`
List records. Query: `?project_id=uuid`

#### `GET /communications/{comm_id}`
Detail with distributions. **No body.**

#### `POST /communications/{comm_id}/distributions`
Log distribution.
```json
{
  "stakeholder_id": "uuid",
  "contact_id": "uuid",
  "distributed_at": "2026-04-02T09:00:00Z",
  "method": "email"
}
```

#### `PATCH /communications/{comm_id}/distributions/{dist_id}`
Update distribution — confirm, add concerns, link feedback.
```json
{
  "confirmed": true,
  "concerns_raised": "Road closure affecting farm access",
  "feedback_ref_id": "uuid"
}
```

---

### Focal Persons

#### `POST /focal-persons`
Register focal person (SEP Table 9).
```json
{
  "project_id": "uuid",
  "name": "Dr. Juma Mohamed",
  "role": "GRM Coordinator",
  "phone": "+255712345678",
  "email": "juma@dwa.go.tz",
  "organisation": "Dodoma Water Authority",
  "lga": "Dodoma Urban"
}
```

#### `GET /focal-persons`
List focal persons. Query: `?project_id=uuid`

#### `PATCH /focal-persons/{fp_id}`
Update focal person. Same fields as POST.

---

### Projects (Stakeholder Service)

#### `GET /projects`
List synced projects. Query: `?org_id=uuid&status=active`

#### `GET /projects/{project_id}`
Project landing page — details, stages, stakeholders, activities. **No body.**

---

### Reports (Stakeholder Service)

#### `GET /reports/engagement-summary`
Activity counts by stage and LGA. Query: `?project_id=uuid`

#### `GET /reports/stakeholder-reach`
Stakeholder counts by category and vulnerability. Query: `?project_id=uuid`

#### `GET /reports/pending-distributions`
Communications awaiting distribution. Query: `?project_id=uuid`

#### `GET /reports/pending-concerns`
Distributions with unresolved concerns. Query: `?project_id=uuid`

---

## 6. Notification Service (port 8060)

### Notifications

#### `GET /notifications`
Get notification inbox.  
Query: `?user_id=uuid&unread_only=false&page=1&limit=20`

#### `GET /notifications/unread-count`
Unread badge count. Query: `?user_id=uuid`

#### `PATCH /notifications/{notification_id}/read`
Mark a notification read. **No body.**

#### `POST /notifications/mark-all-read`
Mark all notifications read. Query: `?user_id=uuid`

#### `DELETE /notifications/{notification_id}`
Cancel a scheduled notification. **No body.**

---

### Devices (Push Tokens)

#### `POST /devices`
Register push device token.
```json
{
  "user_id": "uuid",
  "platform": "android",             // android | ios | web
  "token": "FCM_OR_APNs_TOKEN",
  "device_name": "Amina's Phone"
}
```

#### `GET /devices`
List registered devices. Query: `?user_id=uuid`

#### `PATCH /devices/{device_id}`
Update push token.
```json
{ "token": "NEW_FCM_TOKEN" }
```

#### `DELETE /devices/{device_id}`
Deregister device (logout/uninstall). **No body.**

---

### Preferences

#### `GET /preferences`
Get all notification preferences. Query: `?user_id=uuid`

#### `PUT /preferences`
Set a notification preference.
```json
{
  "user_id": "uuid",
  "notification_type": "grm_feedback_submitted",
  "channel": "push",                 // push | sms | email | whatsapp | in_app
  "enabled": true
}
```

#### `DELETE /preferences/{preference_id}`
Reset preference to default. **No body.**

---

### Templates

#### `GET /templates`
List notification templates. Query: `?notification_type=grm_feedback_submitted`

#### `PUT /templates`
Create or update template.
```json
{
  "notification_type": "grm_feedback_submitted",
  "channel": "sms",
  "language": "sw",
  "subject": null,
  "body": "Malalamiko yako {{feedback_ref}} yamewasilishwa. Asante.",
  "variables": ["feedback_ref", "project_name"]
}
```

#### `DELETE /templates/{template_id}`
Delete template. **No body.**

---

### Internal `[Service Key]`

#### `POST /internal/dispatch`
Dispatch a notification (HTTP alternative to Kafka).
```json
{
  "notification_type": "grm_feedback_submitted",
  "recipient": {
    "user_id": "uuid",
    "phone": "+255712345678",
    "email": "user@example.com",
    "whatsapp_id": "255712345678"
  },
  "channels": ["push", "sms"],
  "variables": {
    "feedback_ref": "GRV-2026-0042",
    "project_name": "Dodoma Water Phase 2"
  },
  "scheduled_at": null               // ISO datetime or null for immediate
}
```

#### `POST /internal/dispatch/batch`
Dispatch multiple notifications.
```json
{
  "notifications": [
    { "notification_type": "...", "recipient": {...}, "channels": [...], "variables": {...} }
  ]
}
```

---

### Delivery Webhooks

#### `POST /webhooks/sms/at`
Africa's Talking SMS delivery report. Form-encoded from AT.

#### `POST /webhooks/sms/twilio`
Twilio SMS delivery report. Form-encoded from Twilio.

#### `POST /webhooks/email/sendgrid`
SendGrid email event webhook. JSON from SendGrid.

#### `POST /webhooks/whatsapp/meta`
Meta WhatsApp message status webhook. JSON from Meta.

#### `GET /webhooks/whatsapp/meta`
WhatsApp webhook verification. **No body.**

---

## 7. Translation Service (port 8050)

#### `POST /translate`
Translate a single text.
```json
{
  "text": "Barabara imechoka sana",
  "target_language": "en",           // BCP-47 code
  "source_language": "sw",           // optional — auto-detect if omitted
  "provider": "groq"                 // optional — google | deepl | microsoft | groq | libretranslate | nllb
}
```
**Response:** `{ translated_text, source_language, target_language, provider, cached }`

#### `POST /translate/batch`
Translate multiple texts (max 50).
```json
{
  "texts": ["Text one", "Text two"],
  "target_language": "en",
  "source_language": "sw",
  "provider": null
}
```
**Response:** `{ results: [{ translated_text, source_language, target_language, provider, cached }], total }`

#### `POST /detect`
Detect the language of a text (min 5 chars).
```json
{ "text": "Habari za asubuhi" }
```
**Response:** `{ detected_language, confidence, alternatives: [{ language, confidence }] }`

#### `GET /languages`
List all supported BCP-47 language codes.  
**Response:** `{ languages: [{ code, flores_code }], total }`

#### `GET /health`
Provider health check.  
**Response:** `{ status, providers: { google, deepl, microsoft, groq, libretranslate, nllb }, nllb_loaded }`

---

## 8. Payment Service (port 8040)

#### `POST /payments`
Create payment intent.
```json
{
  "amount": 5000.00,
  "currency": "TZS",
  "provider": "azampay",             // azampay | selcom | mpesa
  "phone": "+255712345678",
  "description": "GRM Service Fee",
  "reference": "INV-2026-001",
  "metadata": {}
}
```

#### `GET /payments`
List payments. Query: `?status=pending&page=1&limit=20`

#### `GET /payments/{payment_id}`
Payment detail with transactions. **No body.**

#### `POST /payments/{payment_id}/initiate`
Initiate USSD push via provider.
```json
{ "phone": "+255712345678" }
```

#### `POST /payments/{payment_id}/verify`
Poll provider for latest status. **No body.**

#### `POST /payments/{payment_id}/refund` `[Staff]`
Refund a paid payment. **No body.**

#### `DELETE /payments/{payment_id}`
Cancel a PENDING payment. **No body.**

#### `GET /payments/{payment_id}/transactions`
List transactions for a payment. **No body.**

---

### Payment Webhooks

#### `POST /webhooks/payments/azampay`
AzamPay payment callback. JSON from AzamPay.

#### `POST /webhooks/payments/selcom`
Selcom payment callback.

#### `POST /webhooks/payments/mpesa`
M-Pesa payment callback.

---

## Common Response Codes

| Code | Meaning |
|------|---------|
| `200` | OK |
| `201` | Created |
| `204` | No Content (e.g. call status hangup) |
| `400` | Bad Request — validation error or too-short audio |
| `401` | Unauthorized — missing or invalid token |
| `403` | Forbidden — insufficient role |
| `404` | Not Found |
| `409` | Conflict — duplicate resource |
| `413` | Payload Too Large — audio > 25 MB |
| `415` | Unsupported Media Type — invalid audio format |
| `422` | Unprocessable Entity — business logic error |
| `502` | Bad Gateway — upstream STT/LLM failure |
| `503` | Service Unavailable — provider not configured |

## Kafka Events Published

| Topic | Event | Publisher |
|-------|-------|-----------|
| `riviwa.feedback.events` | `feedback.submitted` | feedback_service |
| `riviwa.feedback.events` | `feedback.acknowledged` | feedback_service |
| `riviwa.feedback.events` | `feedback.escalated` | feedback_service |
| `riviwa.feedback.events` | `feedback.resolved` | feedback_service |
| `riviwa.feedback.events` | `feedback.appealed` | feedback_service |
| `riviwa.user.events` | `user.registered`, `user.verified`, `user.suspended` | auth_service |
| `riviwa.organisation.events` | `org.created`, `org.verified`, `project.created` | auth_service |
| `riviwa.stakeholder.events` | `stakeholder.registered`, `engagement.logged` | stakeholder_service |
| `riviwa.notifications` | `notification.dispatch` | all services |
| `riviwa.notifications.events` | `notification.delivered`, `notification.failed` | notification_service |
| `riviwa.payment.events` | `payment.initiated`, `payment.completed`, `payment.failed` | payment_service |

**All `feedback.submitted` payloads include:**
`feedback_id`, `project_id`, `feedback_type`, `category`, `org_id`, `branch_id`, `department_id`, `service_id`, `product_id`, `category_def_id`, `stakeholder_engagement_id`, `distribution_id`
