# Riviwa — Endpoint Reference
## Organisations · Projects · Stages · Stakeholders · Stage Engagements · Activities

> **Base URL:** `https://<host>/api/v1`
> **Auth header:** `Authorization: Bearer <access_token>`
> All authenticated endpoints require a valid JWT issued by `riviwa_auth_service`.
> Staff-only routes additionally require a platform role (`staff`, `admin`, or `super_admin`) embedded in the JWT.

---

## Table of Contents

1. [Data Flow Overview](#1-data-flow-overview)
2. [Organisations](#2-organisations) — auth service (port 8000)
3. [Projects](#3-projects) — auth service
4. [Stages](#4-stages) — auth service
5. [Sub-Projects](#5-sub-projects) — auth service
6. [Stakeholders](#6-stakeholders) — stakeholder service (port 8070)
7. [Stakeholder Stage Engagements](#7-stakeholder-stage-engagements) — stakeholder service
8. [Engagement Activities](#8-engagement-activities) — stakeholder service
9. [Enum Reference](#9-enum-reference)

---

## 1. Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SETUP PHASE (auth_service)                                                  │
│                                                                             │
│  1. User registers → email verified → User.is_email_verified = true        │
│  2. POST /orgs → Organisation created (PENDING_VERIFICATION)               │
│     └─ creator auto-added as OWNER member                                  │
│     └─ Kafka: riviwa.organisation.events { type: "organisation.created" }  │
│  3. POST /orgs/{id}/verify → status → ACTIVE + is_verified = true          │
│     └─ Kafka: { type: "organisation.verified" }                             │
│  4. POST /orgs/{id}/projects → OrgProject (status: PLANNING)               │
│     └─ Kafka: { type: "org_project.created" }                              │
│  5. POST /orgs/{id}/projects/{id}/stages → OrgProjectStage (PENDING)       │
│  6. POST /orgs/{id}/projects/{id}/activate → status → ACTIVE               │
│     └─ Kafka: { type: "org_project.published" }                            │
│     └─ stakeholder_service CONSUMES → creates ProjectCache row             │
│  7. POST /orgs/{id}/projects/{id}/stages/{id}/activate → ACTIVE            │
│     └─ only one stage can be ACTIVE at a time                              │
│     └─ Kafka: { type: "org_project_stage.activated" }                      │
│     └─ stakeholder_service CONSUMES → updates ProjectStageCache row        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ SEP PHASE (stakeholder_service)                                             │
│                                                                             │
│  8.  POST /stakeholders → Stakeholder registered                            │
│      └─ Kafka: { type: "stakeholder.registered" }                          │
│  9.  POST /stakeholders/{id}/contacts → Contact person added               │
│  10. POST /stakeholders/{id}/projects → StakeholderProject link created    │
│      └─ is_pap, affectedness, impact_description captured here             │
│  11. POST /activities → EngagementActivity scheduled (status: PLANNED)    │
│  12. POST /activities/{id}/attendances → StakeholderEngagement logged      │
│  13. PATCH /activities/{id} → mark as CONDUCTED                            │
│       └─ consultation_count++ on all participating stakeholders             │
│       └─ Kafka: { type: "activity.conducted" }                             │
│  14. GET /stakeholders/analysis?project_id= → Annex 3 SEP matrix           │
│       Returns every Stakeholder × StageEngagement row for reporting        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Cross-service sync:**
- `riviwa.organisation.events` → stakeholder_service caches org metadata
- `riviwa.organisation.events` (project published/stage activated) → stakeholder_service updates `ProjectCache` / `ProjectStageCache`
- `riviwa.stakeholder.events` → notification_service delivers engagement reminders

---

## 2. Organisations

> **Service:** `riviwa_auth_service` · **Router prefix:** `/api/v1/orgs`
> **Guard:** authenticated user. Write ops require MANAGER/ADMIN/OWNER org membership.

---

### POST `/orgs` — Create Organisation

**Who:** Any user with `is_email_verified = true`.

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|---|---|---|---|
| `legal_name` | string (max 255) | **Yes** | Official registered name |
| `display_name` | string (max 100) | **Yes** | Short public-facing name |
| `slug` | string (max 100) | **Yes** | URL-safe identifier, must be unique globally |
| `org_type` | enum | **Yes** | `BUSINESS` · `CORPORATE` · `GOVERNMENT` · `NGO` · `INDIVIDUAL_PRO` |
| `description` | string | No | Public description |
| `logo_url` | string (max 512) | No | Pre-uploaded logo URL |
| `website_url` | string | No | |
| `support_email` | string | No | |
| `support_phone` | string (max 20) | No | |
| `country_code` | string (2) | No | ISO 3166-1 alpha-2 |
| `timezone` | string (max 50) | No | e.g. `Africa/Dar_es_Salaam` |
| `registration_number` | string (max 100) | No | |
| `tax_id` | string (max 100) | No | |
| `max_members` | integer | No | 0 = unlimited (default 0) |

**Response `201`:**

```json
{
  "id": "uuid",
  "legal_name": "string",
  "display_name": "string",
  "slug": "string",
  "org_type": "GOVERNMENT",
  "status": "PENDING_VERIFICATION",
  "is_verified": false,
  "created_by_id": "uuid",
  "created_at": "2026-01-01T00:00:00Z"
}
```

**Data flow:**
1. Slug uniqueness checked.
2. `Organisation` row inserted (status: `PENDING_VERIFICATION`).
3. Creator added as `OWNER` member (`OrganisationMember`).
4. Commit.
5. Kafka `riviwa.organisation.events` → `{ type: "organisation.created", org_id, created_by }`.

---

### GET `/orgs` — List My Organisations

**Query params:** `search` (string) · `org_type` · `is_verified` (bool) · `sort` (`created_at`/`name`) · `skip` · `limit`

**Response `200`:**
```json
{
  "items": [{ /* OrgSummary */ }],
  "total": 12,
  "skip": 0,
  "limit": 20
}
```

---

### GET `/orgs/{org_id}` — Get Organisation Detail

**Response `200`:** Full organisation object including `members`, `branches` count, `services` count.

---

### PATCH `/orgs/{org_id}` — Update Organisation

**Role required:** ADMIN or OWNER.

**Request Body** (all optional):

| Field | Type | Description |
|---|---|---|
| `legal_name` | string | |
| `display_name` | string | |
| `slug` | string | Must be globally unique |
| `description` | string | |
| `website_url` | string | |
| `support_email` | string | |
| `support_phone` | string | |
| `country_code` | string (2) | |
| `timezone` | string | |
| `registration_number` | string | |
| `tax_id` | string | |
| `max_members` | integer | |

**Response `200`:** Updated organisation object.

**Data flow:** Slug uniqueness re-checked if changed → update → Kafka `organisation.updated`.

---

### DELETE `/orgs/{org_id}` — Soft-delete Organisation

**Role required:** OWNER only.

**Response `200`:** `{ "message": "Organisation deleted." }`

---

### POST `/orgs/{org_id}/verify` — Verify Organisation *(platform admin)*

**Response `200`:** `{ "message": "Organisation verified." }`

**Data flow:** `status → ACTIVE`, `is_verified = true`, `verified_at` stamped → Kafka `organisation.verified`.

---

### POST `/orgs/{org_id}/suspend` · `/ban`

**Role required:** Platform admin. Body: `{ "reason": "string" }` (optional).

---

### Members

#### POST `/orgs/{org_id}/members` — Add Member Directly

**Role required:** ADMIN+.

| Field | Type | Required |
|---|---|---|
| `user_id` | UUID | **Yes** |
| `org_role` | enum | **Yes** | `OWNER` · `ADMIN` · `MANAGER` · `MEMBER` |

**Response `201`:** `OrganisationMember` object.

**Data flow:** Check user exists + not already member → insert → Kafka `organisation.member_added`.

#### DELETE `/orgs/{org_id}/members/{user_id}` — Remove Member

**Role required:** ADMIN+. Cannot remove OWNER.

#### PATCH `/orgs/{org_id}/members/{user_id}/role` — Change Role

**Body:** `{ "new_role": "MANAGER" }`

#### POST `/orgs/{org_id}/transfer-ownership`

**Role required:** OWNER only. **Body:** `{ "new_owner_id": "uuid" }`

---

### Invites

#### POST `/orgs/{org_id}/invites` — Send Invite

**Role required:** MANAGER+.

| Field | Type | Required | Description |
|---|---|---|---|
| `invited_email` | string | No* | Email to invite (*one of email/user_id required) |
| `invited_user_id` | UUID | No* | Direct user UUID invite |
| `invited_role` | enum | **Yes** | `ADMIN` · `MANAGER` · `MEMBER` |
| `message` | string | No | Personal note in the invite email |

**Data flow:** SHA-256 token generated → 7-day expiry → `OrganisationInvite` inserted → notification email dispatched via Kafka.

#### GET `/orgs/invites` — List My Pending Invites

Returns all `PENDING` invites for the currently authenticated user.

#### POST `/orgs/invites/{invite_id}/accept`

**Data flow:** Validate token not expired + still PENDING → create `OrganisationMember` → mark invite `ACCEPTED` → Kafka `organisation.member_added`.

#### POST `/orgs/invites/{invite_id}/decline`

#### DELETE `/orgs/{org_id}/invites/{invite_id}` — Cancel Invite

**Role required:** MANAGER+.

---

### POST `/orgs/{org_id}/logo` — Upload Logo *(multipart/form-data)*

**Form field:** `file` (image/jpeg · image/png · image/webp · image/svg+xml, max 5 MB).

**Data flow:** Validate MIME + size → upload to MinIO `riviwa-images/organisations/{org_id}/logo.{ext}` → update `Organisation.logo_url` → Kafka `organisation.updated`.

---

## 3. Projects

> **Service:** `riviwa_auth_service` · **Router prefix:** `/api/v1/orgs/{org_id}/projects`
> **Read:** MANAGER+. **Write:** ADMIN+. **Status transitions:** OWNER.

---

### POST `/orgs/{org_id}/projects` — Create Project

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string (max 255) | **Yes** | Display name |
| `slug` | string (max 100) | **Yes** | Unique within org |
| `code` | string (max 50) | No | Optional internal code (unique within org) |
| `visibility` | enum | **Yes** | `public` · `org_only` · `private` |
| `category` | string (max 100) | No | Free-text category (e.g. "Infrastructure") |
| `sector` | string (max 100) | No | e.g. "Roads", "Water", "Health" |
| `description` | string | No | |
| `background` | string | No | Context and history |
| `objectives` | string | No | |
| `expected_outcomes` | string | No | |
| `target_beneficiaries` | string | No | |
| `start_date` | date (YYYY-MM-DD) | No | Planned start |
| `end_date` | date (YYYY-MM-DD) | No | Planned end |
| `budget_amount` | decimal | No | |
| `currency_code` | string (3) | No | ISO 4217, e.g. `TZS` |
| `funding_source` | string (max 255) | No | e.g. "World Bank", "GoT" |(Delimiters like..)
| `country_code` | string (2) | No | |
| `region` | string (max 100) | No | Administrative region |
| `primary_lga` | string (max 100) | No | Primary LGA |
| `location_description` | string | No | Free-text location |
| `cover_image_url` | string | No | |
| `document_urls` | object (JSON) | No | `{ "feasibility": "url", ... }` |
| `accepts_grievances` | boolean | No | Default `true` |(not to be shown in the form)
| `accepts_suggestions` | boolean | No | Default `true` | (not to be shown in the form)
| `accepts_applause` | boolean | No | Default `true` | (not to be shown in the form)
| `requires_grm` | boolean | No | Default `false` |(this default should be true) not be shown in form
| `branch_id` | UUID | No | Assign to a specific branch | (this can be referenced by branc id, when brances are already creace)
| `org_service_id` | UUID | No | Soft-link to an OrgService |( will be added automatically backend when services for the given org are created)

**Response `201`:** `ProjectSummaryResponse`

```json
{
  "id": "uuid",
  "organisation_id": "uuid",
  "branch_id": "uuid | null",
  "name": "Msimbazi River Corridor",
  "code": "MRC-2026",
  "slug": "msimbazi-river-corridor",
  "status": "planning",
  "visibility": "public",
  "category": "Infrastructure",
  "sector": "Flood Management",
  "start_date": "2026-03-01",
  "end_date": "2028-12-31",
  "budget_amount": "450000000.00",
  "currency_code": "TZS",
  "country_code": "TZ",
  "region": "Dar es Salaam",
  "primary_lga": "Ilala",
  "accepts_grievances": true,
  "accepts_suggestions": true,
  "accepts_applause": true,
  "requires_grm": false,
  "created_at": "2026-01-15T08:00:00Z"
}
```

**Data flow:**
1. Slug uniqueness checked within org.
2. Code uniqueness checked within org (if provided).
3. `OrgProject` inserted (status: `planning`).
4. Commit.
5. Kafka `riviwa.organisation.events` → `{ type: "org_project.created" }`.

---

### GET `/orgs/{org_id}/projects` — List Projects

**Query params:** `status` · `visibility` · `search` · `skip` · `limit`

**Response `200`:** `{ "items": [ProjectSummaryResponse], "total": int }`

---

### GET `/orgs/{org_id}/projects/{project_id}` — Project Detail

**Response `200`:** `ProjectDetailResponse` — full object with all stages (each with sub-projects up to 3 nesting levels) and all in-charges.

```json
{
  "id": "uuid",
  "name": "...",
  "description": "...",
  "background": "...",
  "objectives": "...",
  "expected_outcomes": "...",
  "target_beneficiaries": "...",
  "location_description": "...",
  "actual_start_date": "2026-04-01",
  "actual_end_date": null,
  "document_urls": {},
  "deleted_at": null,
  "in_charges": [ { "id": "...", "user_id": "...", "role_title": "Project Manager", "is_lead": true } ],
  "stages": [
    {
      "id": "uuid",
      "name": "Stage 1: Design",
      "stage_order": 1,
      "status": "active",
      "in_charges": [],
      "sub_projects": [
        {
          "id": "uuid",
          "name": "Hydraulic Survey",
          "children": [],
          "in_charges": []
        }
      ]
    }
  ]
}
```

---

### PATCH `/orgs/{org_id}/projects/{project_id}` — Update Project

All `CreateProjectRequest` fields are optional. Slug/code uniqueness re-checked if changed.

---

### Status Transitions

#### POST `/orgs/{org_id}/projects/{project_id}/activate`

`planning → active`. Requires no active project constraint (currently not enforced).
**Data flow:** Status set → Kafka `org_project.published` → **stakeholder_service consumes** and creates/updates `ProjectCache` row.

#### POST `/orgs/{org_id}/projects/{project_id}/pause`

`active → paused`. Body: `{ "reason": "string" }` (optional).

#### POST `/orgs/{org_id}/projects/{project_id}/resume`

`paused → active`.

#### POST `/orgs/{org_id}/projects/{project_id}/complete`

`active → completed`. All stages should be completed/skipped first.

#### DELETE `/orgs/{org_id}/projects/{project_id}`

Soft-delete (`deleted_at` stamped). Project must not be `active`.

---

### Project In-Charges

#### POST `/orgs/{org_id}/projects/{project_id}/in-charges`

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | UUID | **Yes** | Must be an org member |
| `role_title` | string (max 100) | **Yes** | e.g. "Project Manager", "PIU Coordinator" |
| `duties` | string | No | Scope of responsibilities |
| `is_lead` | boolean | No | Default `false` |

**Response `201`:** `ProjectInChargeResponse`

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "user_id": "uuid",
  "role_title": "Project Manager",
  "duties": "...",
  "is_lead": true,
  "assigned_at": "2026-01-15T08:00:00Z",
  "relieved_at": null
}
```

**Data flow:** UNIQUE(project_id, user_id, role_title) enforced → insert → Kafka `org_project.in_charge_assigned`.

#### GET `/orgs/{org_id}/projects/{project_id}/in-charges`

Returns list of `ProjectInChargeResponse`.

#### DELETE `/orgs/{org_id}/projects/{project_id}/in-charges/{user_id}`

Sets `relieved_at` timestamp (soft removal). Returns updated record.

---

### Progress Images

#### POST `/orgs/{org_id}/projects/{project_id}/progress-images` *(multipart/form-data)*

| Form field | Type | Required | Description |
|---|---|---|---|
| `file` | UploadFile | **Yes** | image/jpeg · png · webp · svg, max 5 MB |
| `title` | string | **Yes** | Short descriptive title |
| `phase` | enum | No | `before` · `during` · `after` · `other` (default `during`) |
| `description` | string | No | |
| `display_order` | integer | No | Default 0 |
| `location_description` | string | No | |
| `gps_lat` | float | No | |
| `gps_lng` | float | No | |
| `taken_at` | datetime (ISO) | No | When the photo was taken |

**Response `201`:** `ProgressImageResponse`

```json
{
  "id": "uuid",
  "entity_type": "project",
  "entity_id": "uuid",
  "image_url": "http://minio:9000/riviwa-images/projects/.../photo.jpg",
  "phase": "during",
  "title": "Foundation works — Chainage 1+250",
  "display_order": 0,
  "taken_at": "2026-04-01T10:30:00Z",
  "created_at": "2026-04-10T08:00:00Z"
}
```

**Data flow:** MIME + size validated → upload to MinIO `riviwa-images/projects/{project_id}/gallery/{image_id}.{ext}` → DB row inserted (`project_id` set, `subproject_id` null).

#### GET `/orgs/{org_id}/projects/{project_id}/progress-images`

**Query params:** `phase` (`before`/`during`/`after`/`other`) · `skip` · `limit`

**Response `200`:** `ProgressImageListResponse`
```json
{
  "entity_type": "project",
  "entity_id": "uuid",
  "phase_filter": "during",
  "total": 15,
  "returned": 10,
  "phase_counts": { "before": 3, "during": 10, "after": 2 },
  "items": [ /* ProgressImageResponse */ ]
}
```

#### PATCH `/orgs/{org_id}/projects/{project_id}/progress-images/{image_id}`

Updatable fields: `title` · `description` · `phase` · `display_order` · `location_description` · `gps_lat` · `gps_lng` · `taken_at`.

#### DELETE `/orgs/{org_id}/projects/{project_id}/progress-images/{image_id}`

Soft-delete only — file in MinIO is **never deleted** (evidence trail).

---

## 4. Stages

> Nested under `/api/v1/orgs/{org_id}/projects/{project_id}/stages`

---

### POST `.../stages` — Add Stage

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string (max 255) | **Yes** | e.g. "Stage 1: Design & Survey" |
| `stage_order` | integer (≥ 1) | **Yes** | Must be unique within project |
| `description` | string | No | |
| `objectives` | string | No | |
| `deliverables` | string | No | Key outputs expected |
| `start_date` | date | No | Planned start |
| `end_date` | date | No | Planned end |
| `accepts_grievances` | boolean | No | `null` = inherit from project |
| `accepts_suggestions` | boolean | No | `null` = inherit from project |
| `accepts_applause` | boolean | No | `null` = inherit from project |

**Response `201`:** `StageResponse`

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "name": "Stage 1: Design & Survey",
  "stage_order": 1,
  "status": "pending",
  "description": "...",
  "objectives": "...",
  "deliverables": "...",
  "start_date": "2026-03-01",
  "end_date": "2026-09-30",
  "actual_start_date": null,
  "actual_end_date": null,
  "accepts_grievances": null,
  "accepts_suggestions": null,
  "accepts_applause": null,
  "in_charges": [],
  "sub_projects": []
}
```

**Data flow:** UNIQUE(project_id, stage_order) checked → insert → commit.

---

### GET `.../stages` — List Stages

Returns ordered list of stages (by `stage_order`) with in-charges and top-level sub-projects.

---

### GET `.../stages/{stage_id}` — Stage Detail

Full `StageResponse` including sub-projects with full nesting.

---

### PATCH `.../stages/{stage_id}` — Update Stage

All `CreateStageRequest` fields optional + `actual_start_date` · `actual_end_date`.

---

### Status Transitions

#### POST `.../stages/{stage_id}/activate`

`pending → active`.

**Constraint:** Project must be `active`. Only **one** stage can be `active` at a time — will error if another stage is already active.

**Data flow:** `actual_start_date` stamped → status set → Kafka `org_project_stage.activated` → **stakeholder_service consumes** → updates `ProjectStageCache.status`.

#### POST `.../stages/{stage_id}/complete`

`active → completed`. **Body:** `{ "actual_end_date": "YYYY-MM-DD" }` (optional).

**Data flow:** `actual_end_date` stamped → Kafka `org_project_stage.completed`.

#### POST `.../stages/{stage_id}/skip`

`pending → skipped`. Used to skip a stage without activating it.

---

### Stage In-Charges

#### POST `.../stages/{stage_id}/in-charges`

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | UUID | **Yes** | Org member |
| `role_title` | string | **Yes** | e.g. "Stage Coordinator" |
| `duties` | string | No | |
| `is_lead` | boolean | No | Default `false` |

**Response `201`:** `StageInChargeResponse`

```json
{
  "id": "uuid",
  "stage_id": "uuid",
  "user_id": "uuid",
  "role_title": "Stage Coordinator",
  "duties": "Oversee design deliverables",
  "is_lead": true,
  "assigned_at": "2026-01-20T00:00:00Z",
  "relieved_at": null
}
```

#### GET `.../stages/{stage_id}/in-charges`

#### DELETE `.../stages/{stage_id}/in-charges/{user_id}` — Relieve

Sets `relieved_at`. Returns updated record.

---

## 5. Sub-Projects

> Nested under `.../stages/{stage_id}/subprojects`

---

### POST `.../subprojects` — Add Sub-Project

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string (max 255) | **Yes** | e.g. "Hydraulic Survey — Segment A" |
| `code` | string (max 50) | No | Internal reference code |
| `parent_subproject_id` | UUID | No | For nested sub-projects (children) |
| `description` | string | No | |
| `objectives` | string | No | |
| `activities` | object (JSON) | No | Key activity list as JSON |
| `expected_outputs` | string | No | |
| `start_date` | date | No | |
| `end_date` | date | No | |
| `budget_amount` | decimal | No | |
| `currency_code` | string (3) | No | |
| `location` | string (max 255) | No | Freetext location description |
| `display_order` | integer | No | Default 0 |

**Response `201`:** `SubProjectResponse`

```json
{
  "id": "uuid",
  "stage_id": "uuid",
  "parent_subproject_id": null,
  "name": "Hydraulic Survey — Segment A",
  "code": "HYD-SEG-A",
  "status": "pending",
  "start_date": "2026-03-01",
  "end_date": "2026-06-30",
  "budget_amount": "12500000.00",
  "currency_code": "TZS",
  "display_order": 1,
  "in_charges": [],
  "children": []
}
```

**Data flow:** If `parent_subproject_id` provided, validate it belongs to the same stage → insert → commit.

---

### GET `/orgs/{org_id}/projects/{project_id}/subprojects/{subproject_id}` — Detail

Returns `SubProjectResponse` with `in_charges` and `children` (1 level).

### GET `.../subprojects/{subproject_id}/tree` — Full Recursive Tree

Returns unlimited-depth tree via a `WITH RECURSIVE` CTE. Useful for large hierarchies.

```json
{
  "id": "uuid",
  "name": "...",
  "children": [
    { "id": "uuid", "name": "...", "children": [ ... ] }
  ]
}
```

### PATCH `.../subprojects/{subproject_id}` — Update Sub-Project

All fields optional + `actual_start_date` · `actual_end_date` · `status` · `address_id`.

`status` values: `pending` · `active` · `completed` · `cancelled`.

### DELETE `.../subprojects/{subproject_id}` — Soft-delete

Sets `deleted_at`. Sub-project and its children are excluded from all queries.

---

### Sub-Project In-Charges

#### POST `.../subprojects/{subproject_id}/in-charges`

Same shape as Stage In-Charges. UNIQUE(subproject_id, user_id, role_title) enforced.

| Field | Type | Required |
|---|---|---|
| `user_id` | UUID | **Yes** |
| `role_title` | string | **Yes** |
| `duties` | string | No |
| `is_lead` | boolean | No |

#### GET `.../subprojects/{subproject_id}/in-charges`

#### DELETE `.../subprojects/{subproject_id}/in-charges/{user_id}`

---

### Sub-Project Progress Images

#### POST `.../subprojects/{subproject_id}/progress-images` *(multipart)*

Same fields as project-level progress images. DB row uses `subproject_id`, `project_id = null`.

#### GET `.../subprojects/{subproject_id}/progress-images`

Same response as project-level with `entity_type: "subproject"`.

---

## 6. Stakeholders

> **Service:** `stakeholder_service` · **Router prefix:** `/api/v1/stakeholders`
> **Auth:** Staff token required for all write operations.

---

### POST `/stakeholders` — Register Stakeholder

| Field | Type | Required | Description |
|---|---|---|---|
| `stakeholder_type` | enum | **Yes** | `pap` · `interested_party` |
| `entity_type` | enum | **Yes** | `individual` · `organization` · `group` |
| `category` | enum | **Yes** | See [Enum Reference](#9-enum-reference) |
| `org_name` | string (max 255) | No* | Required if entity_type = `organization`/`group` |
| `first_name` | string (max 100) | No* | Required if entity_type = `individual` |
| `last_name` | string (max 100) | No | |
| `affectedness` | enum | No | `positively_affected` · `negatively_affected` · `both` · `unknown` (default `unknown`) |
| `importance_rating` | enum | No | `high` · `medium` · `low` (default `medium`) |
| `lga` | string | No | Local Government Authority |
| `ward` | string | No | Ward within LGA |
| `language_preference` | string | No | `sw` · `en` (default `sw`) |
| `preferred_channel` | enum | No | See enum list (default `public_meeting`) |
| `needs_translation` | boolean | No | Default `false` |
| `needs_transport` | boolean | No | Default `false` |
| `needs_childcare` | boolean | No | Default `false` |
| `is_vulnerable` | boolean | No | Default `false` |
| `vulnerable_group_types` | string[] | No | See enum list |
| `participation_barriers` | string | No | Free-text barriers |
| `org_id` | UUID | No | Soft-link to a Riviwa Organisation |
| `address_id` | UUID | No | Soft-link to an Address record |
| `notes` | string | No | Internal PIU notes |

**Response `201`:**

```json
{
  "id": "uuid",
  "stakeholder_type": "pap",
  "entity_type": "individual",
  "category": "individual",
  "display_name": "Juma Bakari",
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
  "registered_by_user_id": "uuid",
  "created_at": "2026-04-10T08:00:00Z"
}
```

**Data flow:**
1. Validate enums.
2. `Stakeholder` row inserted.
3. Commit.
4. Kafka `riviwa.stakeholder.events` → `{ type: "stakeholder.registered" }`.

---

### GET `/stakeholders` — List Stakeholders

**Query params:**

| Param | Type | Description |
|---|---|---|
| `stakeholder_type` | enum | `pap` · `interested_party` |
| `category` | enum | Filter by category |
| `lga` | string | Filter by LGA |
| `affectedness` | enum | |
| `is_vulnerable` | boolean | |
| `project_id` | UUID | Only stakeholders registered under this project |
| `stage_id` | UUID | Only stakeholders with a stage engagement in this stage |
| `importance` | enum | `high` · `medium` · `low` |
| `skip` | integer | Default 0 |
| `limit` | integer | Default 50 |

**Response `200`:**
```json
{
  "total": 234,
  "items": [ /* Stakeholder objects */ ]
}
```

---

### GET `/stakeholders/analysis` — SEP Annex 3 Matrix

Returns the full Stakeholder Engagement Plan analysis table: every `Stakeholder × StageEngagement × ProjectStageCache` row.

**Query params:**

| Param | Type | Required | Description |
|---|---|---|---|
| `project_id` | UUID | **Yes** | Project to analyse |
| `stage_id` | UUID | No | Filter to a specific stage |
| `importance` | enum | No | Filter by importance level |
| `category` | enum | No | Filter by stakeholder category |
| `affectedness` | enum | No | |
| `is_vulnerable` | boolean | No | |
| `skip` | integer | No | Default 0 |
| `limit` | integer | No | Default 200 |

**Response `200`:**
```json
{
  "project_id": "uuid",
  "total": 42,
  "items": [
    {
      "stakeholder_id": "uuid",
      "display_name": "Juma Bakari",
      "stakeholder_type": "pap",
      "entity_type": "individual",
      "category": "individual",
      "affectedness": "negatively_affected",
      "lga": "Ilala",
      "ward": "Kariakoo",
      "is_vulnerable": false,
      "consultation_count": 3,
      "stage_engagement_id": "uuid",
      "stage_id": "uuid",
      "stage_name": "Stage 1: Design",
      "stage_order": 1,
      "stage_status": "active",
      "importance": "high",
      "importance_justification": "Direct land impact",
      "interests": "Fair compensation and timely relocation",
      "potential_risks": "Protest if not consulted",
      "engagement_approach": "Individual household meetings + compensation negotiation",
      "engagement_frequency": "Monthly during resettlement phase",
      "allowed_activities": ["household_meeting", "focus_group"],
      "notify_on_stage_milestone": true,
      "notify_channel": "sms"
    }
  ]
}
```

---

### GET `/stakeholders/{stakeholder_id}` — Stakeholder Detail

**Response `200`:** Full stakeholder object with `contacts` list.

```json
{
  "id": "uuid",
  "display_name": "Ilala Community Group",
  "stakeholder_type": "pap",
  "entity_type": "group",
  "category": "community_group",
  "contacts": [
    {
      "id": "uuid",
      "full_name": "Amina Hassan",
      "role_in_org": "Community Liaison Officer",
      "phone": "+255712345678",
      "is_primary": true,
      "can_submit_feedback": true,
      "is_active": true
    }
  ]
}
```

---

### PATCH `/stakeholders/{stakeholder_id}` — Update Stakeholder

All `UpdateStakeholder` fields optional — see schema above.

---

### DELETE `/stakeholders/{stakeholder_id}` — Soft-delete *(admin)*

Sets `deleted_at`. Stakeholder excluded from all future queries.

---

### POST `/stakeholders/{stakeholder_id}/projects` — Register Under Project

**Purpose:** Links a stakeholder to a project and records PAP/affectedness status.

| Field | Type | Required | Description |
|---|---|---|---|
| `project_id` | UUID | **Yes** | Project must exist in `ProjectCache` |
| `is_pap` | boolean | No | Default `false` |
| `affectedness` | enum | No | Override stakeholder-level affectedness for this project |
| `impact_description` | string | No | How this project specifically impacts them |

**Response `201`:**
```json
{
  "id": "uuid",
  "stakeholder_id": "uuid",
  "project_id": "uuid",
  "is_pap": true,
  "affectedness": "negatively_affected",
  "impact_description": "Land acquisition for road widening affects 0.5 acres",
  "consultation_count": 0,
  "registered_at": "2026-04-10T08:00:00Z"
}
```

**Data flow:** Project existence checked against `ProjectCache` → UNIQUE(stakeholder_id, project_id) enforced → `StakeholderProject` inserted → Kafka `stakeholder.project_registered`.

---

### GET `/stakeholders/{stakeholder_id}/projects`

Returns list of all `StakeholderProject` records for this stakeholder.

---

### GET `/stakeholders/{stakeholder_id}/engagements` — Engagement History

Returns all `StakeholderEngagement` records (attendance at activities) for all contacts of this stakeholder.

```json
{
  "items": [
    {
      "id": "uuid",
      "contact_id": "uuid",
      "activity_id": "uuid",
      "attendance_status": "attended",
      "concerns_raised": "When will relocation start?",
      "response_given": "Estimated Q3 2026",
      "feedback_submitted": false,
      "notes": null,
      "created_at": "2026-03-15T10:00:00Z"
    }
  ]
}
```

---

## 7. Stakeholder Stage Engagements

> **Model:** `StakeholderStageEngagement` (`stakeholder_stage_engagements`)
> **Purpose:** SEP Annex 3 — records HOW, WHEN, and WHY each stakeholder is engaged per project stage.
> **Note:** These records are created/updated via the analysis workflow. There is currently no standalone CRUD endpoint — records are populated as part of project engagement planning and appear in the `/stakeholders/analysis` output.

**The `StakeholderStageEngagement` model captures:**

| Field | Type | Description |
|---|---|---|
| `stakeholder_id` | UUID | FK → Stakeholder |
| `project_id` | UUID | Soft-link to project |
| `stage_id` | UUID | FK → ProjectStageCache |
| `importance` | enum | `high` · `medium` · `low` |
| `importance_justification` | string | Why this stakeholder matters for this stage |
| `interests` | string | What their interests / expectations are |
| `potential_risks` | string | Risks if they are not engaged |
| `engagement_approach` | string | HOW to engage (Annex 3 "How to Engage" column) |
| `engagement_frequency` | string | WHEN to engage (Annex 3 "When to Engage" column) |
| `allowed_activities` | string[] | Activity types permitted for this stakeholder in this stage |
| `notify_on_stage_milestone` | boolean | Send notification when stage advances |
| `notify_channel` | enum | Channel for milestone notifications |

**UNIQUE constraint:** `(stakeholder_id, stage_id)` — one engagement plan entry per stakeholder per stage.

**Read via:** `GET /stakeholders/analysis?project_id={uuid}` — returns all rows joined with stakeholder and stage data.

---

## 8. Engagement Activities

> **Service:** `stakeholder_service` · **Router prefix:** `/api/v1/activities`
> **Auth:** Staff token required.

---

### POST `/activities` — Create Activity

| Field | Type | Required | Description |
|---|---|---|---|
| `project_id` | UUID | **Yes** | Project this activity belongs to |
| `stage_id` | UUID | No | Stage (if stage-specific) |
| `subproject_id` | UUID | No | Sub-project (if applicable) |
| `stage` | enum | **Yes** | SEP stage: `preparation` · `initial_disclosure` · `consultation` · `grievance_response` · `monitoring` · `reporting` |
| `activity_type` | enum | **Yes** | See enum reference |
| `title` | string (max 255) | **Yes** | e.g. "Community Meeting — Jangwani Ward" |
| `description` | string | No | Background and purpose |
| `agenda` | string | No | Meeting agenda |
| `venue` | string (max 255) | No | Physical venue name/address |
| `lga` | string (max 100) | No | |
| `ward` | string (max 100) | No | |
| `gps_lat` | float | No | |
| `gps_lng` | float | No | |
| `virtual_platform` | string | No | e.g. "Zoom", "Google Meet" |
| `virtual_url` | string | No | Meeting link |
| `virtual_meeting_id` | string | No | |
| `scheduled_at` | datetime (ISO) | No | Planned date/time |
| `expected_count` | integer | No | Expected number of attendees |
| `languages_used` | string[] | No | e.g. `["sw", "en"]` |
| `conducted_by_user_id` | UUID | No | Staff user who will facilitate |

**Response `201`:** Full activity object

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "stage_id": "uuid | null",
  "subproject_id": "uuid | null",
  "stage": "consultation",
  "activity_type": "public_meeting",
  "status": "planned",
  "title": "Community Meeting — Jangwani Ward",
  "description": "...",
  "agenda": "...",
  "venue": "Jangwani Community Hall",
  "lga": "Kinondoni",
  "ward": "Jangwani",
  "gps_lat": -6.785,
  "gps_lng": 39.218,
  "scheduled_at": "2026-05-15T09:00:00Z",
  "expected_count": 80,
  "actual_count": null,
  "female_count": null,
  "vulnerable_count": null,
  "conducted_at": null,
  "duration_hours": null,
  "languages_used": ["sw"],
  "conducted_by_user_id": "uuid",
  "created_at": "2026-04-10T08:00:00Z",
  "updated_at": "2026-04-10T08:00:00Z"
}
```

**Data flow:**
1. Validate project exists in `ProjectCache`.
2. `EngagementActivity` inserted (status: `planned`).
3. Commit.
4. Kafka `riviwa.stakeholder.events` → `{ type: "activity.created" }`.
5. Notification service schedules reminder (if `scheduled_at` provided).

---

### GET `/activities` — List Activities

**Query params:**

| Param | Type | Description |
|---|---|---|
| `project_id` | UUID | **Recommended** — filter to project |
| `stage_id` | UUID | Filter to stage |
| `subproject_id` | UUID | |
| `status` | enum | `planned` · `conducted` · `cancelled` |
| `activity_type` | enum | |
| `lga` | string | |
| `skip` | integer | |
| `limit` | integer | |

**Response `200`:** `{ "total": int, "items": [activity] }`

---

### GET `/activities/{activity_id}` — Activity Detail with Attendance

**Response `200`:**
```json
{
  "id": "uuid",
  "status": "conducted",
  "title": "...",
  "actual_count": 73,
  "female_count": 38,
  "vulnerable_count": 5,
  "summary_of_issues": "Residents concerned about dust during construction",
  "summary_of_responses": "PIU committed to water spraying twice daily",
  "action_items": [
    { "item": "Procure water bowser", "responsible": "PIU", "due": "2026-06-01" }
  ],
  "minutes_url": "https://...",
  "attendances": [
    {
      "id": "uuid",
      "contact_id": "uuid",
      "attendance_status": "attended",
      "concerns_raised": "Dust and noise",
      "response_given": "Water spraying committed",
      "feedback_submitted": false
    }
  ]
}
```

---

### PATCH `/activities/{activity_id}` — Update / Mark as Conducted

**To mark as conducted**, include:

| Field | Type | Description |
|---|---|---|
| `status` | `"conducted"` | Triggers consultation count increment |
| `conducted_at` | datetime | When it took place |
| `duration_hours` | float | |
| `actual_count` | integer | Total attendees |
| `female_count` | integer | Female attendees |
| `vulnerable_count` | integer | Vulnerable group attendees |
| `summary_of_issues` | string | Issues raised |
| `summary_of_responses` | string | PIU responses |
| `action_items` | object[] | `[{ "item": str, "responsible": str, "due": date }]` |
| `minutes_url` | string | Link to signed minutes |
| `photos_urls` | string[] | Array of photo URLs |
| `languages_used` | string[] | |

**Data flow (when status → `conducted`):**
1. `actual_count`, `conducted_at` recorded.
2. For every `StakeholderEngagement` linked to this activity → find `StakeholderProject` → `consultation_count++`.
3. Kafka `activity.conducted` published.
4. Notification service dispatches follow-up communications.

---

### POST `/activities/{activity_id}/cancel`

**Body:** `{ "reason": "string" }` (optional but recommended).

Sets `status = cancelled`, records `cancelled_reason`.

---

### Attendance

#### POST `/activities/{activity_id}/attendances` — Log Single Attendance

| Field | Type | Required | Description |
|---|---|---|---|
| `contact_id` | UUID | **Yes** | `StakeholderContact.id` |
| `attendance_status` | enum | **Yes** | `attended` · `absent` · `proxy` · `excused` |
| `proxy_name` | string | No | If `proxy` — name of the person who attended on their behalf |
| `concerns_raised` | string | No | Issues this contact raised during the activity |
| `response_given` | string | No | PIU response given on the spot |
| `feedback_submitted` | boolean | No | Whether they also submitted a GRM feedback |
| `feedback_ref_id` | UUID | No | Soft-link to feedback_service grievance/suggestion ID |
| `notes` | string | No | |

**Response `201`:** `StakeholderEngagement` object

```json
{
  "id": "uuid",
  "contact_id": "uuid",
  "activity_id": "uuid",
  "attendance_status": "attended",
  "proxy_name": null,
  "concerns_raised": "When will the contractor arrive?",
  "response_given": "Contractor mobilises June 2026",
  "feedback_submitted": false,
  "feedback_ref_id": null,
  "notes": null,
  "created_at": "2026-05-15T11:00:00Z"
}
```

**Constraint:** UNIQUE(contact_id, activity_id) — one attendance record per contact per activity.

#### PATCH `/activities/{activity_id}/attendances/{engagement_id}` — Update Record

Updatable: `attendance_status` · `concerns_raised` · `response_given` · `feedback_submitted` · `feedback_ref_id` · `notes`.

#### DELETE `/activities/{activity_id}/attendances/{engagement_id}`

Hard deletes the attendance record (does NOT decrement consultation count once activity is conducted).

#### POST `/activities/{activity_id}/attendances/bulk` — Bulk Log

| Field | Type | Required | Description |
|---|---|---|---|
| `attendances` | object[] | **Yes** | Array of attendance objects (same shape as single) |
| `skip_duplicates` | boolean | No | Default `false` — if `true`, silently skips UNIQUE violations |

**Response `201`:** `{ "created": 47, "skipped": 2, "items": [...] }`

**Data flow:**
1. Each contact validated.
2. Bulk insert with conflict handling if `skip_duplicates = true`.
3. If activity already `conducted`, `consultation_count` incremented per new record.

---

### Activity Media

#### POST `/activities/{activity_id}/media` *(multipart/form-data)*

| Form field | Type | Required | Description |
|---|---|---|---|
| `file` | UploadFile | **Yes** | Any file: PDF, image, PPT, etc. |
| `media_type` | enum | **Yes** | `minutes` · `photo` · `presentation` · `document` · `other` |
| `title` | string | No | |
| `description` | string | No | |

**Response `201`:**
```json
{
  "id": "uuid",
  "activity_id": "uuid",
  "media_type": "minutes",
  "file_url": "https://minio.../riviwa-images/activities/{id}/minutes.pdf",
  "file_name": "minutes-2026-05-15.pdf",
  "file_size_bytes": 245890,
  "mime_type": "application/pdf",
  "title": "Signed Minutes — Jangwani Meeting",
  "uploaded_by_user_id": "uuid",
  "uploaded_at": "2026-05-16T08:00:00Z"
}
```

**Data flow:** Upload to MinIO `riviwa-images/activities/{activity_id}/{media_type}/{id}.{ext}` → DB row inserted. File **never deleted** from object storage (evidence trail).

#### GET `/activities/{activity_id}/media`

**Query param:** `media_type` (optional filter).

#### DELETE `/activities/{activity_id}/media/{media_id}`

Soft-delete only — sets `deleted_at`. Object storage file preserved.

---

## 9. Enum Reference

### Organisation

| Enum | Values |
|---|---|
| `org_type` | `BUSINESS` · `CORPORATE` · `GOVERNMENT` · `NGO` · `INDIVIDUAL_PRO` |
| `org_status` | `PENDING_VERIFICATION` · `ACTIVE` · `SUSPENDED` · `BANNED` · `DEACTIVATED` |
| `org_member_role` | `OWNER` · `ADMIN` · `MANAGER` · `MEMBER` |
| `org_member_status` | `ACTIVE` · `INVITED` · `SUSPENDED` · `REMOVED` · `LEFT` |
| `org_invite_status` | `PENDING` · `ACCEPTED` · `DECLINED` · `EXPIRED` · `CANCELLED` |

### Projects & Stages

| Enum | Values |
|---|---|
| `project_status` | `planning` · `active` · `paused` · `completed` · `cancelled` |
| `project_visibility` | `public` · `org_only` · `private` |
| `stage_status` | `pending` · `active` · `completed` · `skipped` |
| `subproject_status` | `pending` · `active` · `completed` · `cancelled` |
| `progress_image_phase` | `before` · `during` · `after` · `other` |

### Stakeholders

| Enum | Values |
|---|---|
| `stakeholder_type` | `pap` · `interested_party` |
| `entity_type` | `individual` · `organization` · `group` |
| `category` | `individual` · `local_government` · `national_government` · `ngo_cbo` · `community_group` · `private_company` · `utility_provider` · `development_partner` · `media` · `academic_research` · `vulnerable_group` · `other` |
| `affectedness` | `positively_affected` · `negatively_affected` · `both` · `unknown` |
| `importance_rating` | `high` · `medium` · `low` |
| `vulnerable_group_types` | `children` · `women_low_income` · `disabled_physical` · `disabled_mental` · `elderly` · `youth` · `low_income` · `indigenous` · `language_barrier` |
| `preferred_channel` | `public_meeting` · `focus_group` · `email` · `sms` · `phone_call` · `radio` · `tv` · `social_media` · `billboard` · `notice_board` · `letter` · `in_person` |

### Activities

| Enum | Values |
|---|---|
| `engagement_stage` | `preparation` · `initial_disclosure` · `consultation` · `grievance_response` · `monitoring` · `reporting` |
| `activity_type` | `public_meeting` · `focus_group` · `household_visit` · `workshop` · `training` · `information_disclosure` · `survey` · `field_visit` · `grievance_session` · `other` |
| `activity_status` | `planned` · `conducted` · `cancelled` |
| `attendance_status` | `attended` · `absent` · `proxy` · `excused` |
| `media_type` | `minutes` · `photo` · `presentation` · `document` · `other` |

---

## Complete Data Flow: From Org Creation to SEP Report

```
1. AUTH SERVICE
   ├── POST /orgs                          → Organisation (PENDING_VERIFICATION)
   ├── POST /orgs/{id}/verify              → Organisation (ACTIVE + is_verified)
   ├── POST /orgs/{id}/projects            → OrgProject (planning)
   ├── POST /orgs/{id}/projects/{id}/stages
   │    ├── Stage 1: preparation
   │    ├── Stage 2: disclosure
   │    └── Stage 3: construction
   ├── POST /orgs/{id}/projects/{id}/stages/{id}/subprojects
   │    ├── Sub-project A (Segment 1)
   │    └── Sub-project B (Segment 2)
   ├── POST .../projects/{id}/activate     → Kafka org_project.published
   │                                       → stakeholder_service syncs ProjectCache
   └── POST .../stages/{id}/activate       → Kafka org_project_stage.activated
                                           → stakeholder_service syncs ProjectStageCache

2. STAKEHOLDER SERVICE (parallel to above)
   ├── POST /stakeholders                  → Stakeholder (PAPs + Interested Parties)
   ├── POST /stakeholders/{id}/contacts    → StakeholderContact (liaison persons)
   ├── POST /stakeholders/{id}/projects    → StakeholderProject (PAP registration)
   │    └── is_pap, affectedness, impact_description recorded
   │
   ├── POST /activities                    → EngagementActivity (planned)
   ├── POST /activities/{id}/attendances   → StakeholderEngagement (attendance log)
   │    └── bulk via POST /activities/{id}/attendances/bulk
   ├── POST /activities/{id}/media         → ActivityMedia (minutes, photos)
   ├── PATCH /activities/{id}              → status → conducted
   │    └── consultation_count++ per attending stakeholder
   │
   └── GET /stakeholders/analysis?project_id=
        └── Returns complete SEP Annex 3 matrix:
            Stakeholder × StageEngagement × Stage
            showing importance, interests, risks, approach, frequency
            → Used for World Bank / IFC PS1 reporting
```
