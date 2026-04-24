# Analytics Guide — Riviwa GRM Platform

## Overview

The Riviwa analytics module provides real-time and historical performance metrics for GRM operations. This guide explains how each metric is calculated and what it means for project teams and GRM officers.

---

## Live Dashboard Metrics (analytics_service)

The analytics service exposes comprehensive dashboards at three levels — project, organisation, and platform. Each dashboard returns:

### Summary Stats (GrievanceSummaryStats)
- **total_grievances** — all grievances ever submitted (any status)
- **resolved** — status = RESOLVED
- **closed** — status = CLOSED
- **unresolved** — status NOT IN (RESOLVED, CLOSED, DISMISSED)
- **escalated** — status = ESCALATED
- **dismissed** — status = DISMISSED (unfounded, duplicate, out of scope)
- **acknowledged_count** — grievances where acknowledged_at IS NOT NULL
- **acknowledged_pct** — acknowledged_count / total × 100
- **resolved_on_time** — resolved_at ≤ target_resolution_date
- **resolved_late** — resolved_at > target_resolution_date
- **resolved_on_time_pct** — resolved_on_time / (resolved_on_time + resolved_late) × 100
- **resolved_late_pct** — resolved_late / (resolved_on_time + resolved_late) × 100
- **avg_resolution_hours** — average hours from submitted_at to resolved_at
- **avg_days_unresolved** — average days currently open (unresolved only)

### Priority Breakdown (by_priority)
Each row: priority (CRITICAL/HIGH/MEDIUM/LOW), total, unresolved, resolved

### Department Breakdown (by_department)
Each row: department_id, total, unresolved, resolved, avg_resolution_hours

### Stage / Sub-project Breakdown (by_stage — project level only)
Each row: stage_id, stage_name, stage_order, total, grievances, suggestions, applause, inquiries, resolved

### Per-project Breakdown (by_project — org/platform level)
Each row: project_id, project_name, total, unresolved, resolved

### Per-org Breakdown (by_org — platform level)
Each row: organisation_id, org_name, total, unresolved, resolved

### Overdue Grievances (overdue)
Grievances where target_resolution_date < NOW() and status NOT IN (RESOLVED, CLOSED, DISMISSED).
Fields: feedback_id, unique_ref, priority, status, submitted_at, target_resolution_date, days_overdue, department_id, issue_lga

### Grievance List (grievances — paginated)
Full list of all grievances matching the filters. Page/page_size supported.

---

## Dimension Breakdowns

All dimension breakdown endpoints return per-type counts (grievances, suggestions, applause, inquiries) for side-by-side comparison. Filter by `feedback_type` to isolate one type.

### By Branch (branch_id)
Groups feedback by organisational branch. `branch_id` is denormalised from the department's branch at submission time.

### By Department (department_id)
Groups feedback by the department it was directed to or handled by (HR, Finance, Customer Care, etc.).

### By Service (service_id)
Groups by the specific service or programme the feedback relates to.

### By Product (product_id)
Groups by the specific product the feedback relates to.

### By Category (category_def_id)
Groups by dynamic category (Compensation, Land acquisition, Safety, Construction Impact, etc.). Uncategorised rows appear as "uncategorised".

### By Stage (stage_id) — project level only
Groups by active sub-project stage at time of submission. Ordered by stage_order.

---

## Dimension Coverage Matrix

| Dimension   | Project level                      | Org level                       | Platform level                     |
|-------------|------------------------------------|---------------------------------|------------------------------------|
| branch      | /analytics/feedback/by-branch      | /analytics/org/{id}/by-branch   | /analytics/platform/by-branch      |
| department  | /analytics/feedback/by-department  | /analytics/org/{id}/by-dept     | /analytics/platform/by-department  |
| service     | /analytics/feedback/by-service     | /analytics/org/{id}/by-service  | /analytics/platform/by-service     |
| product     | /analytics/feedback/by-product     | /analytics/org/{id}/by-product  | /analytics/platform/by-product     |
| category    | /analytics/feedback/by-category    | /analytics/org/{id}/by-category | /analytics/platform/by-category    |
| stage       | /analytics/feedback/by-stage       | —                               | —                                  |

---

## SLA Targets by Priority

| Priority | Acknowledge within | Resolve within |
|----------|--------------------|----------------|
| CRITICAL | 4 hours            | 72 hours       |
| HIGH     | 8 hours            | 168 hours      |
| MEDIUM   | 24 hours           | 336 hours      |
| LOW      | 48 hours           | 720 hours      |

---

## Core Time Metrics

### Time to Open (Time to Acknowledge)
- **Definition**: Duration between `submitted_at` and the timestamp of the first action recorded.
- **Measurement unit**: hours
- **Target**: See SLA targets by priority above

### Time to Resolve
- **Definition**: Duration between `submitted_at` and `resolved_at`.
- **Measurement unit**: hours
- **Note**: Resolution means a resolution was proposed — it does NOT mean the grievant accepted it. Closure requires the grievant to accept.

### Time to Close
- **Definition**: Duration between `submitted_at` and `closed_at`. Includes resolution time plus any appeal period.

---

## Overdue Grievances

A grievance is **overdue** when ALL of the following are true:
1. Current timestamp is past `target_resolution_date`
2. Status is still ACKNOWLEDGED, IN_REVIEW, or ESCALATED (not RESOLVED, CLOSED, or DISMISSED)
3. The grievance has not been explicitly put on hold

### Overdue Rate
- Overdue rate = (number of overdue grievances / total active grievances) × 100
- A rate above 15% for any LGA triggers an alert to the PCU.
- A rate above 30% may trigger a World Bank safeguard review.

---

## Unread / Unacknowledged Grievances

A grievance is **unread** when:
- `status = SUBMITTED` (the initial state)
- No `FeedbackAction` records have been created for it
- No GRM officer has opened or viewed it in the platform

This is distinct from acknowledged: a grievance moves to ACKNOWLEDGED only when a GRM officer explicitly creates an acknowledgment action and the `acknowledged_at` timestamp is set.

---

## Suggestion Implementation Tracking

- A suggestion is **implemented** when `status = RESOLVED` and the action notes indicate the suggestion was acted upon
- Implementation rate = (resolved suggestions / total suggestions) × 100

---

## Committee Performance Metrics

GRM committees (Ward committees, LGA committees) are scored on:

1. **Acknowledgment Rate** — percentage of assigned grievances acknowledged within SLA. Target: ≥ 95%
2. **Resolution Rate** — percentage of assigned grievances resolved within SLA. Target: ≥ 80%
3. **Escalation Rate** — percentage of grievances escalated out of the committee. High (>20%) may indicate capacity issues.
4. **Reopen Rate** — percentage of closed grievances reopened due to appeal. Target: < 5%
5. **Average Resolution Time** — mean hours from submission to resolution

### Committee Leaderboard
Ranked monthly: 40% acknowledgment rate + 40% resolution rate + 20% avg resolution time (normalized).

---

## Staff Performance Metrics

1. **Cases Handled** — total grievances processed (acknowledged + resolved) in the period
2. **On-Time Acknowledgment Rate** — acknowledged within SLA / total assigned
3. **On-Time Resolution Rate** — resolved within SLA / total assigned
4. **Average Time to Acknowledge** — mean hours from assignment to acknowledgment
5. **Average Time to Resolve** — mean hours from assignment to resolution

### Performance Tiers
- **Green** (High Performer): On-time ack ≥ 95%, on-time resolution ≥ 85%
- **Amber** (Needs Improvement): On-time ack 80–94%, on-time resolution 70–84%
- **Red** (Underperforming): On-time ack < 80% or on-time resolution < 70%

Staff in Red tier for two consecutive months are flagged for supervisor review.

---

## Live Dashboard (Spark Streaming)

The real-time dashboard (powered by Spark Structured Streaming) shows:

- Total open grievances (SUBMITTED + ACKNOWLEDGED + IN_REVIEW + ESCALATED) broken down by priority
- Count of grievances breaching SLA in the next 24 hours
- Geographic hotspot map (heatmap by Ward and LGA — areas with >10 grievances per 1,000 PAPs highlighted)
- Channel distribution (SMS, WhatsApp, App, Web, In-person, Phone)
- Resolution funnel: Submitted → Acknowledged → In Review → Resolved → Closed

---

## Batch Analytics (Spark Jobs — nightly)

- **SLA compliance trends** — 7-day, 30-day, 90-day rolling averages by LGA
- **Category distribution trends** — which grievance categories are increasing month-over-month
- **ML escalation scoring** — probability that each active grievance will be escalated
- **Staff workload balancing** — recommendations for redistributing cases across officers

---

## Key Performance Indicators (KPIs)

### Project-Level KPIs
- Overall GRM acknowledgment rate (target: ≥ 95%)
- Overall GRM resolution rate within SLA (target: ≥ 80%)
- Percentage of grievances resolved at Level 1 (target: ≥ 70%)
- Average time to resolve (target: within SLA for 80% of cases)

### World Bank Safeguard Reporting KPIs
These KPIs are extracted monthly for World Bank progress reports:
- Total grievances received, by category
- Resolution rate, by priority and category
- Number of grievances pending > 30 days
- Number of cases escalated to Level 3+
- Number of cases that reached court or arbitration
