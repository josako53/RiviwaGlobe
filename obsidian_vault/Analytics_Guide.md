# Analytics Guide — Riviwa GRM Platform

## Overview

The Riviwa analytics module provides real-time and historical performance metrics for GRM operations. This guide explains how each metric is calculated and what it means for project teams and GRM officers.

## Core Time Metrics

### Time to Open (Time to Acknowledge)
- **Definition**: Duration between `submitted_at` (when grievance was created) and the timestamp of the first action recorded in the system.
- **Measurement unit**: hours
- **Target**: See SLA targets by priority (Critical: 4h, High: 8h, Medium: 24h, Low: 48h)
- **How it appears in reports**: Average time to open per priority level, per LGA, per time period

### Time to Resolve
- **Definition**: Duration between `submitted_at` and `resolved_at` (when status changed to `resolved`).
- **Measurement unit**: hours
- **Target**: 72h (Critical), 168h (High), 336h (Medium), 720h (Low)
- **Note**: Resolution means a resolution was proposed — it does NOT mean the grievant accepted it. Closure requires the grievant to accept.

### Time to Close
- **Definition**: Duration between `submitted_at` and `closed_at` (when status changed to `closed`).
- **Includes**: Resolution time plus any appeal period.

## Overdue Grievances

### What "Overdue" Means
A grievance is classified as **overdue** when ALL of the following are true:
1. Current timestamp is past `target_resolution_date`
2. The grievance status is still `acknowledged`, `in_review`, or `escalated` (i.e., NOT resolved, closed, or dismissed)
3. The grievance has not been explicitly put on hold

`target_resolution_date` is calculated at submission time based on `submitted_at` + SLA hours for the grievance's priority level.

### Overdue Rate
- Overdue rate = (number of overdue grievances / total active grievances) × 100
- A rate above 15% for any LGA triggers an alert to the PCU.
- A rate above 30% may trigger a World Bank safeguard review.

## Unread / Unacknowledged Grievances

### What "Unread" Means in Riviwa
A grievance is classified as **unread** (or unacknowledged) when:
- `status = submitted` (the initial state)
- No `FeedbackAction` records have been created for it
- No GRM officer has opened or viewed it in the platform

This is distinct from acknowledged: a grievance moves to `acknowledged` only when a GRM officer explicitly creates an acknowledgment action and the `acknowledged_at` timestamp is set.

### Unread Count
The unread count visible on the GRM dashboard shows all grievances in `submitted` status older than 1 hour (to exclude very recent submissions still within the notification delivery window).

## Suggestion Implementation Tracking

### How Suggestions Are Tracked
Suggestions follow the same lifecycle as grievances but use different resolution semantics:
- A suggestion is considered **implemented** when `status = resolved` AND the action notes indicate the suggestion was acted upon
- `resolved_at` is set when the GRM officer marks the suggestion as actioned
- Implementation rate = (resolved suggestions / total suggestions) × 100

### Suggestion Categories
Suggestions are tracked by category to identify the most common improvement areas:
- Construction methods, safety, community engagement, environmental mitigation, compensation process

## Committee Performance Metrics

### How Committee Performance Is Measured
GRM committees (Ward committees, LGA committees) are scored on:

1. **Acknowledgment Rate** — percentage of assigned grievances acknowledged within SLA
   - Formula: acknowledged_within_SLA / total_assigned × 100
   - Target: ≥ 95%

2. **Resolution Rate** — percentage of assigned grievances resolved within SLA
   - Formula: resolved_within_SLA / total_assigned × 100
   - Target: ≥ 80%

3. **Escalation Rate** — percentage of grievances escalated out of the committee
   - High escalation rate (>20%) may indicate capacity or authority issues
   - Formula: escalated / total_assigned × 100

4. **Reopen Rate** — percentage of closed grievances that were reopened due to appeal
   - Target: < 5%

5. **Average Resolution Time** — mean hours from submission to resolution for the committee's cases

### Committee Leaderboard
The analytics dashboard ranks committees monthly on a composite score weighted:
- 40% acknowledgment rate
- 40% resolution rate
- 20% average resolution time (normalized)

## Staff Performance Metrics

### How Staff Performance Is Measured
Individual GRM officers are evaluated on the cases assigned to them:

1. **Cases Handled** — total grievances processed (acknowledged + resolved) in the period
2. **On-Time Acknowledgment Rate** — acknowledged within SLA / total assigned
3. **On-Time Resolution Rate** — resolved within SLA / total assigned
4. **Average Time to Acknowledge** — mean hours from assignment to acknowledgment
5. **Average Time to Resolve** — mean hours from assignment to resolution
6. **Escalation-to-Resolution Ratio** — escalated cases vs. cases they resolved themselves

### Performance Tiers
- **Green** (High Performer): On-time ack ≥ 95%, on-time resolution ≥ 85%
- **Amber** (Needs Improvement): On-time ack 80–94%, on-time resolution 70–84%
- **Red** (Underperforming): On-time ack < 80% or on-time resolution < 70%

Staff in Red tier for two consecutive months are flagged for supervisor review.

## Live Dashboard Metrics

The real-time dashboard (powered by Spark Structured Streaming) shows:

### Active Grievances Panel
- Total open grievances (status: submitted + acknowledged + in_review + escalated)
- Broken down by priority level
- Count of grievances breaching SLA in the next 24 hours

### Geographic Hotspot Map
- Heatmap of grievance density by Ward and LGA
- Areas with > 10 grievances per 1,000 PAPs are highlighted as hotspots
- Hotspots trigger automatic notification to LGA PIU supervisors

### Channel Distribution
- Breakdown of submissions by channel: SMS, WhatsApp, App, Web, In-person, Phone
- Used to optimize resource allocation per channel

### Resolution Funnel
- Shows the flow: Submitted → Acknowledged → In Review → Resolved → Closed
- Drop-off at each stage highlights bottlenecks

## Batch Analytics (Spark Jobs)

The following analytics are computed nightly by Spark batch jobs and stored in analytics_db:

- **SLA compliance trends** — 7-day, 30-day, 90-day rolling averages by LGA
- **Category distribution trends** — which grievance categories are increasing month-over-month
- **ML escalation scoring** — probability that each active grievance will be escalated (based on features: age, priority, category, past behavior of the assigned committee)
- **Staff workload balancing** — recommendations for redistributing cases across officers

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
