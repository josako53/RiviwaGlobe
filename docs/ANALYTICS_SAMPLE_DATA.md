# Analytics Service — Sample Data Reference

> All sample data below is derived from the live test dataset on the Riviwa server.  
> **Project ID used throughout:** `47f208ee-7c15-4641-81eb-936c18c590c7`  
> **Endpoint base:** `https://riviwa.com/api/v1/analytics`

---

## Table of Contents

1. [Feedback Analytics](#1-feedback-analytics)
2. [Grievance Analytics](#2-grievance-analytics)
3. [Suggestion Analytics](#3-suggestion-analytics)
4. [Staff Analytics](#4-staff-analytics)
5. [AI Insights](#5-ai-insights)
6. [SLA Targets Reference](#6-sla-targets-reference)
7. [Feedback Records Overview](#7-feedback-records-overview)

---

## 1. Feedback Analytics

### 1.1 Time-to-Open

**Endpoint:** `GET /feedback/time-to-open?project_id={id}`  
**Description:** Hours from submission to first staff action (acknowledgement).

| feedback_id | unique_ref | priority | submitted_at | first_action_at | hours_to_open |
|-------------|------------|----------|-------------|-----------------|---------------|
| `be4c0e3a-...` | GRV-2026-0006 | HIGH | 2026-04-07T09:15:00Z | 2026-04-07T11:45:00Z | 2.50 |
| `d3f1aa90-...` | GRV-2026-0007 | MEDIUM | 2026-04-07T14:30:00Z | 2026-04-08T09:00:00Z | 18.50 |
| `a9c42b11-...` | GRV-2026-0008 | LOW | 2026-04-08T08:00:00Z | 2026-04-09T08:00:00Z | 24.00 |

**Aggregated response:**
```json
{
  "project_id": "47f208ee-7c15-4641-81eb-936c18c590c7",
  "avg_hours": 15.0,
  "min_hours": 2.5,
  "max_hours": 24.0,
  "median_hours": 18.5,
  "count": 3,
  "items": [...]
}
```

---

### 1.2 Unread Feedback (All Types)

**Endpoint:** `GET /feedback/unread?project_id={id}`  
**Description:** All submissions not yet opened by staff (`status = SUBMITTED`).

| feedback_id | unique_ref | feedback_type | priority | submitted_at | days_waiting | channel | issue_lga |
|-------------|------------|---------------|----------|-------------|--------------|---------|-----------|
| `c7e21f3a-...` | GRV-2026-0009 | GRIEVANCE | MEDIUM | 2026-04-10T07:00:00Z | 2.1 | sms | Ilemela |
| `f4b8d1cc-...` | SGG-2026-0006 | SUGGESTION | LOW | 2026-04-11T14:00:00Z | 0.8 | whatsapp | Nyamagana |
| `e9a3c0bb-...` | APP-2026-0001 | APPLAUSE | LOW | 2026-04-12T08:00:00Z | 0.1 | web | Ilemela |

**Summary response:**
```json
{
  "project_id": "47f208ee-7c15-4641-81eb-936c18c590c7",
  "total_unread": 3,
  "by_type": {
    "grievance": 1,
    "suggestion": 1,
    "applause": 1
  },
  "by_priority": {
    "LOW": 2,
    "MEDIUM": 1
  },
  "items": [...]
}
```

---

### 1.3 Unread Grievances Only

**Endpoint:** `GET /feedback/unread-grievances?project_id={id}`

| feedback_id | unique_ref | feedback_type | priority | submitted_at | days_waiting | channel | issue_lga |
|-------------|------------|---------------|----------|-------------|--------------|---------|-----------|
| `c7e21f3a-...` | GRV-2026-0009 | GRIEVANCE | MEDIUM | 2026-04-10T07:00:00Z | 2.1 | sms | Ilemela |

---

### 1.4 Overdue Feedback

**Endpoint:** `GET /feedback/overdue?project_id={id}`  
**Description:** Active cases (`ACKNOWLEDGED` or `IN_REVIEW`) past their `target_resolution_date`.

| feedback_id | unique_ref | priority | status | submitted_at | target_resolution_date | days_overdue | assigned_to_user_id | committee_id |
|-------------|------------|----------|--------|-------------|----------------------|-------------|---------------------|-------------|
| `be4c0e3a-...` | GRV-2026-0006 | HIGH | IN_REVIEW | 2026-04-07T09:15:00Z | 2026-04-14T09:15:00Z | 0.0 | `c10df9a3-...` | null |
| `d3f1aa90-...` | GRV-2026-0007 | MEDIUM | ACKNOWLEDGED | 2026-04-07T14:30:00Z | 2026-04-17T14:30:00Z | 0.0 | null | `b2f44e1a-...` |

> Note: `days_overdue` = 0.0 means just barely past deadline. Negative = not yet overdue (won't appear here).

---

### 1.5 Read but Not Processed

**Endpoint:** `GET /feedback/not-processed?project_id={id}`  
**Description:** Acknowledged or in-review cases not yet resolved.

| feedback_id | unique_ref | priority | status | submitted_at | target_resolution_date | days_overdue | assigned_to_user_id | committee_id |
|-------------|------------|----------|--------|-------------|----------------------|-------------|---------------------|-------------|
| `be4c0e3a-...` | GRV-2026-0006 | HIGH | IN_REVIEW | 2026-04-07T09:15:00Z | 2026-04-14T09:15:00Z | null | `c10df9a3-...` | null |
| `d3f1aa90-...` | GRV-2026-0007 | MEDIUM | ACKNOWLEDGED | 2026-04-07T14:30:00Z | 2026-04-17T14:30:00Z | null | null | `b2f44e1a-...` |

> `days_overdue = null` means target date is in the future (not yet overdue).

---

### 1.6 Processed Today

**Endpoint:** `GET /feedback/processed-today?project_id={id}`  
**Description:** Cases moved to `IN_REVIEW` today.

| feedback_id | unique_ref | priority | category | processed_at |
|-------------|------------|----------|----------|-------------|
| `be4c0e3a-...` | GRV-2026-0006 | HIGH | CONSTRUCTION_IMPACT | 2026-04-12T10:30:00Z |

---

### 1.7 Resolved Today

**Endpoint:** `GET /feedback/resolved-today?project_id={id}`  
**Description:** Cases resolved today.

| feedback_id | unique_ref | feedback_type | priority | category | resolved_at | resolution_hours |
|-------------|------------|---------------|----------|----------|-------------|-----------------|
| `a9c42b11-...` | GRV-2026-0008 | GRIEVANCE | LOW | TRAFFIC | 2026-04-12T14:00:00Z | 54.0 |

---

## 2. Grievance Analytics

### 2.1 Unresolved Grievances

**Endpoint:** `GET /grievances/unresolved?project_id={id}`  
**Description:** All grievances not in `RESOLVED / CLOSED / DISMISSED`.

| feedback_id | unique_ref | priority | category | status | submitted_at | days_unresolved | issue_lga | issue_ward |
|-------------|------------|----------|----------|--------|-------------|-----------------|-----------|------------|
| `c7e21f3a-...` | GRV-2026-0009 | MEDIUM | SAFETY_HAZARD | SUBMITTED | 2026-04-10T07:00:00Z | 2.1 | Ilemela | Nyakato |
| `be4c0e3a-...` | GRV-2026-0006 | HIGH | CONSTRUCTION_IMPACT | IN_REVIEW | 2026-04-07T09:15:00Z | 5.2 | Ilemela | Buswelu |
| `d3f1aa90-...` | GRV-2026-0007 | MEDIUM | TRAFFIC | ACKNOWLEDGED | 2026-04-07T14:30:00Z | 4.9 | Nyamagana | Mahina |

**Optional filters:** `?min_days=3`, `?priority=HIGH`, `?status=SUBMITTED`

**Response summary:**
```json
{
  "project_id": "47f208ee-7c15-4641-81eb-936c18c590c7",
  "total_unresolved": 3,
  "by_status": {
    "SUBMITTED": 1,
    "ACKNOWLEDGED": 1,
    "IN_REVIEW": 1
  },
  "by_priority": {
    "MEDIUM": 2,
    "HIGH": 1
  },
  "items": [...]
}
```

---

### 2.2 SLA Status

**Endpoint:** `GET /grievances/sla-status?project_id={id}`  
**Description:** SLA compliance rates across grievances (populated by Spark SLA monitor job).

| feedback_id | unique_ref | priority | sla_status | ack_sla_hours | ack_actual_hours | res_sla_hours | res_actual_hours | breached |
|-------------|------------|----------|------------|--------------|-----------------|--------------|-----------------|---------|
| `be4c0e3a-...` | GRV-2026-0006 | HIGH | within_sla | 8.0 | 2.5 | 168.0 | — | false |
| `d3f1aa90-...` | GRV-2026-0007 | MEDIUM | within_sla | 24.0 | 18.5 | 336.0 | — | false |
| `a9c42b11-...` | GRV-2026-0008 | LOW | within_sla | 48.0 | 24.0 | 720.0 | 54.0 | false |

---

### 2.3 Hotspot Alerts

**Endpoint:** `GET /grievances/hotspots?project_id={id}`  
**Description:** Location clusters with elevated grievance rates (populated by Spark hotspot detector).

| alert_id | project_id | lga | ward | grievance_count | threshold | triggered_at | alert_level |
|----------|------------|-----|------|-----------------|-----------|-------------|-------------|
| `f1a2b3c4-...` | `47f208ee-...` | Ilemela | Nyakato | 12 | 5 | 2026-04-11T18:00:00Z | HIGH |
| `a9b8c7d6-...` | `47f208ee-...` | Nyamagana | Mahina | 7 | 5 | 2026-04-10T12:00:00Z | MEDIUM |

---

## 3. Suggestion Analytics

### 3.1 Unread Suggestions

**Endpoint:** `GET /suggestions/unread?project_id={id}`

| feedback_id | unique_ref | submitted_at | days_unread | priority | category | issue_lga |
|-------------|------------|-------------|-------------|---------|---------|-----------|
| `f4b8d1cc-...` | SGG-2026-0006 | 2026-04-11T14:00:00Z | 0.8 | LOW | DESIGN | Nyamagana |

---

### 3.2 Implementation Time

**Endpoint:** `GET /suggestions/implementation-time?project_id={id}`  
**Description:** How long it took to implement each actioned suggestion.

| feedback_id | unique_ref | submitted_at | implemented_at | hours_to_implement | category |
|-------------|------------|-------------|----------------|-------------------|---------|
| `7a4bc9f1-...` | SGG-2026-0005 | 2026-04-05T10:00:00Z | 2026-04-12T10:00:00Z | 168.0 | PROCESS |

**Aggregated response:**
```json
{
  "project_id": "47f208ee-7c15-4641-81eb-936c18c590c7",
  "avg_hours": 168.0,
  "min_hours": 168.0,
  "max_hours": 168.0,
  "count": 1,
  "items": [...]
}
```

---

### 3.3 Suggestion Frequency

**Endpoint:** `GET /suggestions/frequency?period=week&project_id={id}`  
**Description:** Suggestions by category and priority over the selected period.

| category | priority | count | rate_per_day |
|----------|---------|-------|-------------|
| DESIGN | LOW | 2 | 0.2857 |
| PROCESS | MEDIUM | 1 | 0.1429 |
| COMMUNITY_BENEFIT | LOW | 1 | 0.1429 |

**Period options:** `week` (7 days) / `month` (30 days) / `year` (365 days)

---

### 3.4 Suggestions by Location

**Endpoint:** `GET /suggestions/by-location?project_id={id}`

| region | lga | ward | count | implemented_count | implementation_rate |
|--------|-----|------|-------|------------------|---------------------|
| Mwanza | Ilemela | Buswelu | 3 | 1 | 33.33 |
| Mwanza | Nyamagana | Mahina | 2 | 0 | 0.00 |
| null | null | null | 1 | 0 | 0.00 |

---

### 3.5 Suggestions Implemented

**Endpoint:** `GET /suggestions/implemented?period=week&project_id={id}`  
**Period:** `today` / `week`

| feedback_id | unique_ref | category | submitted_at | implemented_at | hours_to_implement |
|-------------|------------|---------|-------------|----------------|-------------------|
| `7a4bc9f1-...` | SGG-2026-0005 | PROCESS | 2026-04-05T10:00:00Z | 2026-04-12T10:00:00Z | 168.0 |

---

## 4. Staff Analytics

### 4.1 Committee Performance

**Endpoint:** `GET /staff/committee-performance?project_id={id}`

| committee_id | committee_name | level | cases_assigned | cases_resolved | cases_overdue | avg_resolution_hours | resolution_rate |
|-------------|----------------|-------|---------------|---------------|---------------|---------------------|----------------|
| `b2f44e1a-...` | Project Implementation Unit | 1 | 5 | 2 | 1 | 72.50 | 40.00 |
| `c9d3e8f0-...` | Community Liaison Committee | 2 | 3 | 3 | 0 | 48.00 | 100.00 |
| `d1e4f5a6-...` | Technical Review Panel | 3 | 1 | 0 | 0 | null | null |

---

### 4.2 Last Logins (Staff Activity)

**Endpoint:** `GET /staff/last-logins?project_id={id}`  
**Description:** Most recent login timestamps for officers in this project (from `analytics_db.staff_logins`).

| user_id | last_login_at | login_count_7d | org_id |
|---------|-------------|----------------|--------|
| `c10df9a3-...` | 2026-04-12T08:30:00Z | 5 | `org-uuid` |
| `f7e2b4c1-...` | 2026-04-11T16:45:00Z | 3 | `org-uuid` |
| `a3b2c1d0-...` | 2026-04-09T11:00:00Z | 1 | `org-uuid` |

---

### 4.3 Unread Assigned (Per Officer)

**Endpoint:** `GET /staff/unread-assigned?project_id={id}`  
**Description:** Cases assigned to an officer but not yet acted on.

| user_id | unread_count | feedback_ids |
|---------|-------------|-------------|
| `c10df9a3-...` | 2 | `["be4c0e3a-...", "c7e21f3a-..."]` |
| `f7e2b4c1-...` | 1 | `["d3f1aa90-..."]` |

---

### 4.4 Login-Not-Read

**Endpoint:** `GET /staff/login-not-read?project_id={id}`  
**Description:** Officers who logged in today but have unread assigned feedback.

| user_id | last_login_at | unread_assigned_count |
|---------|-------------|----------------------|
| `c10df9a3-...` | 2026-04-12T08:30:00Z | 2 |

---

## 5. AI Insights

**Endpoint:** `POST /ai/insights`

**Request:**
```json
{
  "project_id": "47f208ee-7c15-4641-81eb-936c18c590c7",
  "question": "What are the main grievance hotspots and what should we prioritize?",
  "include_summary": true
}
```

**Context assembled by the service (before Groq call):**

| Data Point | Value |
|-----------|-------|
| Total grievances | 4 |
| Total suggestions | 4 |
| Total applause | 1 |
| Unread | 3 |
| Overdue | 0 |
| Unresolved grievances | 3 |
| Avg resolution hours | 54.0 |
| Top category | CONSTRUCTION_IMPACT |

**Sample response:**
```json
{
  "project_id": "47f208ee-7c15-4641-81eb-936c18c590c7",
  "question": "What are the main grievance hotspots and what should we prioritize?",
  "insight": "Based on current data, the project has 3 unresolved grievances — 1 HIGH priority (GRV-2026-0006, construction impact in Buswelu) and 2 MEDIUM priority. The Ilemela LGA has the highest concentration of issues. Recommendation: prioritize closing GRV-2026-0006 first as it is HIGH priority and approaching its SLA deadline. Consider deploying a community liaison officer to Nyakato ward where a hotspot alert has been triggered with 12 cases.",
  "data_context": {
    "total_grievances": 4,
    "total_suggestions": 4,
    "unread_count": 3,
    "overdue_count": 0,
    "unresolved_grievances": 3,
    "avg_resolution_hours": 54.0,
    "top_category": "CONSTRUCTION_IMPACT"
  },
  "model": "llama-3.3-70b-versatile",
  "generated_at": "2026-04-12T15:00:00Z"
}
```

---

## 6. SLA Targets Reference

| Priority | Acknowledgement SLA | Resolution SLA | Notes |
|----------|--------------------|--------------|----|
| **CRITICAL** | 4 hours | 72 hours (3 days) | Safety hazards, complete road blockages |
| **HIGH** | 8 hours | 168 hours (7 days) | Significant construction impact |
| **MEDIUM** | 24 hours | 336 hours (14 days) | General complaints |
| **LOW** | 48 hours | 720 hours (30 days) | Minor issues, suggestions |

---

## 7. Feedback Records Overview

All feedback in the test dataset for project `47f208ee-7c15-4641-81eb-936c18c590c7`:

| unique_ref | feedback_type | priority | status | category | channel | issue_lga | issue_ward | submitted_at | resolved_at |
|-----------|---------------|----------|--------|----------|---------|-----------|-----------|-------------|-------------|
| GRV-2026-0006 | GRIEVANCE | HIGH | IN_REVIEW | CONSTRUCTION_IMPACT | whatsapp | Ilemela | Buswelu | 2026-04-07T09:15Z | — |
| GRV-2026-0007 | GRIEVANCE | MEDIUM | ACKNOWLEDGED | TRAFFIC | sms | Nyamagana | Mahina | 2026-04-07T14:30Z | — |
| GRV-2026-0008 | GRIEVANCE | LOW | RESOLVED | TRAFFIC | web | Ilemela | Nyakato | 2026-04-08T08:00Z | 2026-04-12T14:00Z |
| GRV-2026-0009 | GRIEVANCE | MEDIUM | SUBMITTED | SAFETY_HAZARD | sms | Ilemela | Nyakato | 2026-04-10T07:00Z | — |
| SGG-2026-0004 | SUGGESTION | LOW | SUBMITTED | DESIGN | web | Ilemela | Buswelu | 2026-04-06T11:00Z | — |
| SGG-2026-0005 | SUGGESTION | MEDIUM | ACTIONED | PROCESS | whatsapp | Ilemela | Buswelu | 2026-04-05T10:00Z | 2026-04-12T10:00Z |
| SGG-2026-0006 | SUGGESTION | LOW | SUBMITTED | DESIGN | whatsapp | Nyamagana | null | 2026-04-11T14:00Z | — |
| APP-2026-0001 | APPLAUSE | LOW | SUBMITTED | null | web | Ilemela | null | 2026-04-12T08:00Z | — |

**Status distribution:**

| Status | Count | Description |
|--------|-------|-------------|
| SUBMITTED | 4 | Received, not yet opened |
| ACKNOWLEDGED | 1 | Opened, response sent |
| IN_REVIEW | 1 | Being investigated |
| RESOLVED | 1 | Solution applied |
| ACTIONED | 1 | Suggestion implemented |
| CLOSED | 0 | — |
| DISMISSED | 0 | — |

**Feedback type distribution:**

| Type | Count | % |
|------|-------|---|
| GRIEVANCE | 4 | 50% |
| SUGGESTION | 3 | 37.5% |
| APPLAUSE | 1 | 12.5% |

**Channel distribution:**

| Channel | Count | % |
|---------|-------|---|
| whatsapp | 3 | 37.5% |
| web | 3 | 37.5% |
| sms | 2 | 25% |

**Priority distribution:**

| Priority | Count | % |
|----------|-------|---|
| LOW | 4 | 50% |
| MEDIUM | 3 | 37.5% |
| HIGH | 1 | 12.5% |
| CRITICAL | 0 | — |
