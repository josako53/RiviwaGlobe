# Apache Spark Integration — Riviwa GRM Platform

> **Purpose:** How Apache Spark accelerates real-time grievance resolution, suggestion tracking,
> and applause acknowledgement across the Riviwa GRM microservices platform.
>
> **Audience:** Engineering leads, product owners, DevOps.  
> **Date:** 2026-04-12

---

## Table of Contents

1. [What Apache Spark Is — In the Context of Riviwa](#1-what-apache-spark-is)
2. [The Current Problem — Why Riviwa Needs Spark](#2-the-current-problem)
3. [What Spark Brings to Riviwa — Benefits by Objective](#3-benefits-by-objective)
4. [Spark Architecture in Riviwa](#4-spark-architecture-in-riviwa)
5. [The Six Core Spark Jobs](#5-the-six-core-spark-jobs)
6. [End-to-End Data Flow — From Submission to Real-Time Dashboard](#6-end-to-end-data-flow)
7. [Implementation Plan — How to Integrate](#7-implementation-plan)
8. [New Service: analytics_service](#8-new-service-analytics_service)
9. [Expected Outcomes — Before vs After](#9-expected-outcomes)
10. [Summary](#10-summary)

---

## 1. What Apache Spark Is

Apache Spark is a **distributed data processing engine** that processes large volumes of data in parallel across a cluster of machines. It has two operating modes relevant to Riviwa:

| Mode | What it does | Riviwa use case |
|------|-------------|-----------------|
| **Structured Streaming** | Processes data as it arrives — milliseconds to seconds latency | Real-time SLA monitoring, hotspot detection, live dashboards |
| **Batch processing** | Processes accumulated data in scheduled jobs — seconds to minutes | Historical reports, trend analysis, ML model training |

Spark reads natively from **Apache Kafka** (which Riviwa already uses), processes data in-memory across workers, and writes results to **PostgreSQL, Redis, or a data warehouse** — all systems already in the Riviwa stack.

> Spark does not replace any existing Riviwa service. It sits **alongside** them as an analytics layer, consuming the same Kafka events your services already publish.

---

## 2. The Current Problem

### 2.1 How reports are generated today

Every time a report is requested (e.g. `GET /reports/grievance-performance`), the `report_service.py` does this:

```
HTTP request arrives
    ↓
SELECT * FROM feedbacks WHERE project_id = ? AND created_at BETWEEN ? AND ?
    → pulls potentially 10,000–500,000 rows into memory
    ↓
Python loops calculate:
    _avg_h()         → iterate every row, compute timedelta, average in Python
    _res_rate()      → iterate again
    _by_status()     → iterate again
    _by_priority()   → iterate again
    _by_channel()    → iterate again
    _by_location()   → iterate again (region → district → LGA → ward → mtaa)
    ↓
Repeat for escalations JOIN, resolutions JOIN, appeals JOIN
    ↓
Format → return JSON / PDF / XLSX
```

This means:
- A report covering 6 months of data for a large project runs **10–30 seconds**
- Each report is **recomputed from scratch** every request
- The database takes the full load of these analytical queries alongside transactional writes
- **SLA monitoring** (who is overdue?) runs as a live full-table scan — no pre-computed flags
- **Real-time hotspot detection** (5 grievances from Kinondoni in the last hour) is **impossible** without a streaming layer

### 2.2 Specific bottlenecks in your code

| Bottleneck | Location in code | Impact |
|-----------|-----------------|--------|
| Full table scan on every report | `report_service.py` — all `_avg_h()`, `_by_*()` helpers | Slow reports, high DB CPU |
| No pre-computed SLA status | `feedbacks.target_resolution_date` exists but no `sla_breached` flag | Overdue report re-scans every row every time |
| Two-column category system | `category` ENUM + `category_def_id` FK — conditional aggregation required | Poor GROUP BY performance |
| Multi-level location rollup | `issue_region → district → lga → ward → mtaa` — 5 separate GROUP BY passes | Reports repeat work for every geographic level |
| No status transition history | Status lives in single ENUM column | Cannot answer "how many entered IN_REVIEW this week?" efficiently |
| SLA targets in Python code | `_ACK_SLA_H`, `_RES_SLA_H` dicts in `report_service.py` | No DB-level breach flag, recomputed at request time |
| Zero streaming analytics | No consumer reads Kafka for analytics | Realtime hotspots, SLA breach alerts, escalation signals — all missing |

---

## 3. Benefits by Objective

### Objective: Resolve grievances faster and prove it

| Without Spark | With Spark |
|--------------|-----------|
| SLA status computed on every API request | SLA breach flag pre-written to DB in seconds of deadline crossing |
| "Overdue" report takes 10–30s | Overdue list updated in real-time by streaming job |
| No automatic escalation trigger on SLA breach | Streaming job publishes `feedback.sla_breached` Kafka event → feedback_service auto-escalates |
| Officer sees stale workload numbers | Live workload counter per officer updated every 30s via Redis |
| Project manager checks reports manually | Push notification fired within 60s of SLA breach |

### Objective: Detect and act on patterns (hotspots)

| Without Spark | With Spark |
|--------------|-----------|
| No geographic clustering | Streaming job detects 5+ grievances from same ward in 60 min → fires alert |
| No category spike detection | Rolling 7-day baseline; >2× spike in any category → fires alert |
| No seasonal trend insight | Batch job computes weekly/monthly baselines per project/category |
| No escalation chain analysis | Batch job maps full escalation paths; flags cases stuck at same level 7+ days |

### Objective: Deliver rich, instant analytics to project managers

| Without Spark | With Spark |
|--------------|-----------|
| Dashboard loads in 10–30s | Pre-computed metrics served from Redis in <50ms |
| Reports recomputed every request | Spark writes materialized metrics to a dedicated `analytics_db` every 5 minutes |
| No historical trend charts | Batch job maintains daily/weekly snapshots going back 2 years |
| No predictive insights | ML model (Spark MLlib) predicts: likelihood of escalation, estimated resolution time |

### Objective: Improve recommendation engine scoring

| Without Spark | With Spark |
|--------------|-----------|
| Interaction counts updated one-at-a-time on each Kafka event | Spark batch job recomputes all entity scores nightly with full signal history |
| IDF map for tag scoring rebuilt on each recommendation request | Spark pre-computes global IDF weights, writes to Redis, recommendation_service reads them |
| No cross-project engagement patterns | Spark computes topic vectors across all entities for improved semantic grouping |

### Objective: Accountability and transparency reporting

| Without Spark | With Spark |
|--------------|-----------|
| SEP Annex reports generated on demand; slow for auditors | Spark generates Annex 5/6 Excel exports nightly, available for instant download |
| Committee performance not measured | Spark computes per-committee resolution rates, average handling times, member workloads |
| No cross-project / cross-organisation benchmarks | Spark aggregates across all projects; anonymised benchmark tables available to all orgs |

---

## 4. Spark Architecture in Riviwa

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          EXISTING RIVIWA SERVICES                               │
│                                                                                 │
│  feedback_service   auth_service   stakeholder_service   recommendation_service │
│       │                  │                │                       │             │
│       └──────────────────┴────────────────┴───────────────────────┘             │
│                                    │ publishes to                               │
└────────────────────────────────────┼────────────────────────────────────────────┘
                                     │
                         ┌───────────▼────────────┐
                         │      Apache Kafka       │
                         │                         │
                         │  riviwa.feedback.events │
                         │  riviwa.org.events      │
                         │  riviwa.stakeholder.*   │
                         │  riviwa.auth.events     │
                         └──────┬──────────┬───────┘
                                │          │
               ┌────────────────▼──┐   ┌───▼──────────────────┐
               │  SPARK STREAMING  │   │   SPARK BATCH (Cron)  │
               │  (always-on)      │   │   (hourly / nightly)  │
               │                   │   │                        │
               │  · SLA monitor    │   │  · Historical reports  │
               │  · Hotspot detect │   │  · Trend analysis      │
               │  · Live counters  │   │  · ML scoring          │
               │  · Fraud signals  │   │  · SEP annexes         │
               └────────┬──────────┘   └────────┬───────────────┘
                        │                        │
          ┌─────────────▼────────────────────────▼──────────────┐
          │                  OUTPUT LAYER                        │
          │                                                      │
          │  Redis DB 6         analytics_db (PostgreSQL)        │
          │  (live counters,    (materialized metrics,           │
          │   SLA flags,        trend tables, ML scores,         │
          │   hotspot alerts)   audit snapshots)                 │
          └──────────┬───────────────────────┬───────────────────┘
                     │                       │
          ┌──────────▼───────┐   ┌───────────▼──��─────────────────┐
          │  notification_   │   │  analytics_service (new)        │
          │  service         │   │  FastAPI — serves pre-computed  │
          │  (fires breach   │   │  metrics to frontend in <50ms   │
          │   alerts, push   │   │  replaces slow report queries   │
          │   notifications) │   └────────────────────────────────┘
          └──────────────────┘
```

### Infrastructure components

| Component | Role | Where runs |
|-----------|------|------------|
| **Spark master** | Coordinates jobs | `spark_master` container |
| **Spark workers (×2)** | Execute tasks in parallel | `spark_worker_1`, `spark_worker_2` containers |
| **analytics_db** | PostgreSQL for pre-computed metrics | `analytics_db` container (port 5438) |
| **Redis DB 6** | Live counters, hotspot cache, SLA flags | Existing Redis (new DB index) |
| **analytics_service** | FastAPI serving analytics endpoints | `analytics_service` container (port 8095) |

---

## 5. The Six Core Spark Jobs

---

### Job 1 — Real-Time SLA Monitor (Streaming)

**What it does:** Reads every `feedback.submitted`, `feedback.acknowledged`, `feedback.resolved` event from Kafka. Tracks SLA deadlines. Fires an alert the moment a deadline is crossed.

**SLA targets defined in your current code:**
```python
# From report_service.py
_ACK_SLA_H  = {critical: 4,  high: 8,  medium: 24, low: 48}   # hours to acknowledge
_RES_SLA_H  = {critical: 72, high: 168, medium: 336, low: 720} # hours to resolve
```

**How it works:**
```
Kafka stream: riviwa.feedback.events
    ↓
filter: event_type IN ('feedback.submitted', 'feedback.acknowledged', 'feedback.resolved')
    ↓
Maintain state table (in Spark memory, checkpointed to disk):
    feedback_id → {priority, submitted_at, acknowledged_at, resolved_at,
                   ack_deadline, res_deadline, ack_sla_met, res_sla_met}
    ↓
Every 60 seconds — watermark check:
    WHERE ack_deadline < now() AND acknowledged_at IS NULL
        → write sla_status='ACK_BREACHED' to analytics_db.feedback_sla_status
        → publish event to riviwa.feedback.events:
            { event_type: 'feedback.sla_breached',
              feedback_id, breach_type: 'acknowledgement',
              priority, project_id, assigned_to_user_id }
        → set Redis key: sla:breach:{feedback_id} = 1 (TTL 86400s)
    WHERE res_deadline < now() AND resolved_at IS NULL
        → same flow with breach_type: 'resolution'
    ↓
feedback_service consumer receives 'feedback.sla_breached'
    → auto-escalates to next GRM level
    → notification_service fires push + SMS to assigned officer and project manager
```

**Profit to Riviwa:** Grievances that were quietly expiring are now caught automatically within 60 seconds of their deadline. Officers are notified before they become complaints. SLA compliance rates improve because the system reminds, escalates, and records proactively.

---

### Job 2 — Hotspot Detector (Streaming)

**What it does:** Detects geographic and categorical spikes in grievance submissions within rolling time windows. Sends alerts when abnormal concentrations appear.

**How it works:**
```
Kafka stream: riviwa.feedback.events
    ↓
filter: event_type = 'feedback.submitted' AND feedback_type = 'grievance'
    ↓
Extract: project_id, issue_lga, issue_ward, category, submitted_at
    ↓
Spark sliding window: 60-minute window, sliding every 15 minutes
    GROUP BY project_id, issue_lga, category
    COUNT submissions per window
    ↓
Compare to 7-day rolling baseline (stored in analytics_db):
    IF count > (baseline_avg × 2.0) AND count >= 5:
        → write to analytics_db.hotspot_alerts:
            { project_id, location: issue_lga, category,
              count_in_window: N, baseline_avg, spike_factor,
              window_start, window_end, alert_status: 'active' }
        → publish to riviwa.notifications:
            { notification_type: 'grievance_hotspot_detected',
              recipient: project managers,
              variables: { location, category, count, spike_factor } }
        → store in Redis: hotspot:{project_id}:{lga}:{category}
    ↓
Second window: 24-hour window for lower-frequency categories (resettlement, land_acquisition)
    same logic, threshold: count >= 3 AND spike_factor >= 1.5
```

**Profit to Riviwa:** A community experiencing a sudden burst of construction-impact grievances in one ward gets a project manager's attention within 15 minutes — not after the weekly report review. The GRM becomes proactive, not reactive.

---

### Job 3 — Live Dashboard Metrics (Streaming + Micro-batch)

**What it does:** Maintains live counters per project that the frontend can query without touching the main `feedback_db`.

**Metrics maintained in Redis (updated every 30 seconds):**
```
dashboard:{project_id}:total_grievances         → integer
dashboard:{project_id}:open_grievances           → integer
dashboard:{project_id}:critical_open             → integer
dashboard:{project_id}:overdue_count             → integer
dashboard:{project_id}:resolved_today            → integer
dashboard:{project_id}:avg_resolution_hours      → float
dashboard:{project_id}:ack_rate_7d               → float (0.0–1.0)
dashboard:{project_id}:resolution_rate_30d       → float
dashboard:{project_id}:sla_compliance_rate        → float
dashboard:{project_id}:top_category              → string
dashboard:{project_id}:channel_breakdown         → JSON hash
dashboard:{project_id}:last_updated              → ISO timestamp
```

**How it works:**
```
Spark micro-batch: process Kafka stream every 30 seconds
    ↓
Aggregate per project_id:
    COUNT total, COUNT by status, COUNT priority=critical
    COUNT WHERE target_resolution_date < now() AND status NOT IN (resolved, closed, dismissed)
    COUNT WHERE DATE(resolved_at) = today()
    AVG((resolved_at - submitted_at) / 3600) WHERE resolved_at IS NOT NULL
    COUNT(acknowledged_at IS NOT NULL) / COUNT(*) — last 7 days
    COUNT(resolved_at IS NOT NULL) / COUNT(*) — last 30 days
    ↓
MSET all keys to Redis (pipeline, atomic) — TTL 120s each
    ↓
analytics_service exposes GET /analytics/dashboard/{project_id}
    → reads from Redis (< 5ms)
    → fallback: query analytics_db if Redis miss
```

**Profit to Riviwa:** The project manager dashboard loads in under 50ms instead of 10–30 seconds. Numbers update live while they watch. No need to refresh the page to see if a new grievance came in or a deadline was just crossed.

---

### Job 4 — Historical Analytics Engine (Batch — runs every hour)

**What it does:** Replaces the current slow Python aggregation loops in `report_service.py`. Pre-computes all report dimensions across the full historical dataset and stores them in `analytics_db`.

**What it precomputes — mirrors your current report endpoints:**

```python
# Spark SQL equivalent of your current _avg_h(), _res_rate(), _by_*() helpers
# Runs in parallel across Spark workers — 100x faster than sequential Python loops

df = spark.read.jdbc(url=FEEDBACK_DB_URL, table="feedbacks")

# ── Status distribution ────────────────────────────────────────────────────────
status_counts = df.groupBy("project_id", "feedback_type", "status") \
    .agg(count("id").alias("count"))

# ── SLA compliance per priority ───────────────────────────────────────────────
sla_df = df.withColumn(
    "ack_hours", (col("acknowledged_at").cast("long") - col("submitted_at").cast("long")) / 3600
).withColumn(
    "res_hours", (col("resolved_at").cast("long") - col("submitted_at").cast("long")) / 3600
).withColumn(
    "ack_sla_target", when(col("priority")=="critical", 4)
                     .when(col("priority")=="high", 8)
                     .when(col("priority")=="medium", 24)
                     .otherwise(48)
).withColumn(
    "ack_sla_met", col("ack_hours") <= col("ack_sla_target")
)

sla_compliance = sla_df.groupBy("project_id", "priority") \
    .agg(
        count("id").alias("total"),
        sum(col("ack_sla_met").cast("int")).alias("ack_sla_met_count"),
        avg("ack_hours").alias("avg_ack_hours"),
        avg("res_hours").alias("avg_res_hours"),
        percentile_approx("ack_hours", 0.5).alias("median_ack_hours"),
        percentile_approx("res_hours", 0.5).alias("median_res_hours"),
    )

# ── N-dimensional cube: location × category × channel × priority ──────────────
cube_df = df.cube("project_id", "issue_region", "issue_district",
                  "issue_lga", "category", "channel", "priority") \
    .agg(
        count("id").alias("count"),
        sum(when(col("status").isin(["resolved","closed"]), 1).otherwise(0)).alias("resolved_count"),
        avg("ack_hours").alias("avg_ack_hours"),
        avg("res_hours").alias("avg_res_hours"),
    )
# Writes 256+ dimension combinations in one pass — impossible in current Python loops

# ── Daily trend time series ──────────────────────────────────────────────���────
daily_trend = df.withColumn("day", date_trunc("day", col("submitted_at"))) \
    .groupBy("project_id", "feedback_type", "day") \
    .agg(count("id").alias("submitted_count"),
         sum(when(col("resolved_at").isNotNull(), 1).otherwise(0)).alias("resolved_count"))

# ── Escalation path analysis ──────────────────────────────────────────────────
esc_df = spark.read.jdbc(url=FEEDBACK_DB_URL, table="feedback_escalations")
escalation_paths = df.join(esc_df, "feedback_id") \
    .groupBy("project_id", "from_level", "to_level") \
    .agg(count("id").alias("escalation_count"),
         avg("days_at_level").alias("avg_days_stuck"))

# Write all to analytics_db
status_counts.write.jdbc(ANALYTICS_DB_URL, "analytics_status_counts", mode="overwrite")
sla_compliance.write.jdbc(ANALYTICS_DB_URL, "analytics_sla_compliance", mode="overwrite")
cube_df.write.jdbc(ANALYTICS_DB_URL, "analytics_feedback_cube", mode="overwrite")
daily_trend.write.jdbc(ANALYTICS_DB_URL, "analytics_daily_trend", mode="overwrite")
escalation_paths.write.jdbc(ANALYTICS_DB_URL, "analytics_escalation_paths", mode="overwrite")
```

**Profit to Riviwa:** The existing `/reports/grievance-performance` endpoint currently takes 10–30 seconds. With Spark pre-computing everything hourly into `analytics_db`, the analytics_service returns the same data in under 100ms. The load is **completely removed from feedback_db**, which can now focus purely on transactional writes.

---

### Job 5 — ML Escalation Predictor (Batch — runs nightly)

**What it does:** Trains a machine learning model on historical feedback data. For every open grievance, predicts: (a) likelihood it will escalate, (b) estimated resolution time, (c) recommended priority adjustment.

**Features used (all exist in your `feedbacks` table):**
```python
features = [
    "category",                    # category ENUM
    "channel",                     # intake channel
    "submission_method",           # self_service / officer_recorded / ai_conversation
    "priority",                    # current priority
    "issue_region",                # geographic location
    "issue_lga",
    "hours_since_submitted",       # age of grievance
    "days_to_deadline",            # time remaining on SLA
    "action_count",                # how many feedback_actions logged
    "has_voice_note",              # bool
    "is_anonymous",                # bool
    "escalation_count",            # how many times already escalated
    "submitter_historical_rate",   # how often this submitter's grievances escalate
    "project_category",            # project sector
    "project_region",
    "current_level",               # ward / lga_piu / pcu / tanroads / world_bank
]

label = "will_escalate_within_14_days"   # boolean, derived from historical data
```

**Training pipeline:**
```
Spark reads historical feedbacks + escalations (last 2 years)
    ↓
Feature engineering (SparkML Pipeline):
    StringIndexer   → encode categoricals
    VectorAssembler → combine features
    StandardScaler  → normalize
    ↓
Train GBTClassifier (Gradient Boosted Trees) on 80% split
    ↓
Evaluate on 20% test: AUC-ROC, precision, recall
    ↓
Save model to: /opt/riviwa/spark/models/escalation_predictor_v{date}
    ↓
Score all currently open grievances:
    predictions = model.transform(open_grievances_df)
    predictions.select("feedback_id", "escalation_probability", "predicted_resolution_hours")
    ↓
Write to analytics_db.feedback_ml_scores:
    { feedback_id, escalation_probability, predicted_resolution_hours,
      recommended_priority, model_version, scored_at }
    ↓
feedback_service reads ml_scores when officer opens a case
    → displays: "High escalation risk (87%) — consider expediting"
```

**Profit to Riviwa:** Officers triage their workload based on risk scores, not just submission order. High-probability-of-escalation cases get attention early — before they reach the World Bank level. Resolution time predictions help managers allocate staff and set realistic expectations with grievants.

---

### Job 6 — SEP Annex Report Generator (Batch — runs nightly)

**What it does:** Generates the Stakeholder Engagement Plan Annex 5 (Grievance Log) and Annex 6 (Summary Table) that World Bank-funded projects are required to submit. These are the Excel/PDF reports your system already has but generates slowly on demand.

**How it works:**
```
Spark reads: feedbacks, feedback_actions, feedback_escalations,
             feedback_resolutions, feedback_appeals,
             fb_projects, fb_project_stages, grm_committees
    ↓
Full JOIN in Spark (distributed — no OOM risk regardless of dataset size)
    ↓
Format Annex 5 (Grievance Log):
    One row per grievance, all columns:
    Ref No | Type | Date | Name | Contact | Location | Category |
    Description | Status | Priority | Level | Assigned To |
    Acknowledged At | Resolved At | Resolution Summary |
    Grievant Satisfied | Appeal Filed | Closed At
    ↓
Format Annex 6 (Summary Table):
    Per period: total submitted, acknowledged, resolved, pending,
    escalated, dismissed, appealed, average resolution days
    ↓
Write to MinIO (S3-compatible):
    s3://riviwa-reports/{org_id}/{project_id}/annex5_{date}.xlsx
    s3://riviwa-reports/{org_id}/{project_id}/annex6_{date}.pdf
    ↓
Write download URL to analytics_db.generated_reports:
    { project_id, report_type, period, file_url, generated_at }
    ↓
analytics_service exposes GET /analytics/reports/{project_id}/{type}
    → returns pre-built file URL for instant download
```

**Profit to Riviwa:** The Annex reports that previously required clicking "Generate Report" and waiting 20–30 seconds are now pre-built every night. An auditor or World Bank reviewer gets a download link instantly. The feedback_db is never stressed by report generation.

---

## 6. End-to-End Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   GRIEVANT submits a grievance (SMS / WhatsApp / App / Web)                  │
│                                                                              │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  feedback_service                                                            │
│    • Saves Feedback row to feedback_db                                       │
│    • Publishes to riviwa.feedback.events:                                    │
│        { event_type: "feedback.submitted",                                   │
│          feedback_id, project_id, feedback_type, category,                  │
│          priority, issue_lga, issue_ward, submitted_at,                      │
│          channel, submission_method }                                        │
└──────────┬──────────────────────────────────────���───┬────────────────────────┘
           │                                          │
           ▼                                          ▼
┌──────────────────────────┐             ┌────────────────────────────────────┐
│  notification_service    │             │  SPARK STREAMING JOBS (always-on)  │
│  (existing)              │             │                                    │
│  • Sends "received"      │             │  Job 1 — SLA Monitor:              │
│    notification to       │             │    → register feedback in state    │
│    grievant              │             │    → compute ack_deadline =        │
│  • Alerts PIU officer    │             │       submitted_at + _ACK_SLA_H    │
│    of new submission     │             │       [priority]                   │
└──────────────────────────┘             │                                    │
                                         │  Job 2 — Hotspot Detector:         │
                                         │    → add to 60-min sliding window  │
                                         │    → compare to 7-day baseline     │
                                         │                                    │
                                         │  Job 3 — Live Dashboard:           │
                                         │    → increment open_grievances     │
                                         │       counter for project_id       │
                                         │    → update Redis dashboard key    │
                                         └────────────┬───────────────────────┘
                                                      │
                        ┌─────────────────────────────┴────────┐
                        │                                       │
                        ▼                                       ▼
          ┌─────────────────────────┐            ┌─────────────────────────────┐
          │  SLA deadline crosses   │            │  Hotspot threshold hit:     │
          │  (Job 1 fires):         │            │  5 grievances from          │
          │                         │            │  Kinondoni/construction in  │
          │  • Write SLA breach to  │            │  60 min                     │
          │    analytics_db         │            │                             │
          │  • Publish              │            │  ��� Write to                 │
          │    feedback.sla_breached│            │    analytics_db.hotspots    │
          │    to Kafka             │            │  • Publish hotspot alert    │
          │                         │            │    to riviwa.notifications  │
          └──────────┬──────────────┘            └──────────┬──────────────────┘
                     │                                       │
                     ▼                                       ▼
          ┌──────────────────────────────────────────────────────────────────────┐
          │  notification_service + feedback_service                             │
          │    • Officer receives push notification: "DAWASA grievance #GRM-    │
          │      2026-047 is overdue for acknowledgement (Critical)"            │
          │    • feedback_service auto-escalates to next GRM level              │
          │    • Project manager receives hotspot alert:                        │
          │      "5 construction-impact grievances from Kinondoni this hour"    │
          └──────────────────────────────────────────────────────────────────────┘

────────────────────────── NIGHTLY BATCH (02:00 server time) ─────────────────────

          ┌──────────────────────────────────────────────────────────────────────┐
          │  Job 4 — Historical Analytics Engine                                │
          │    Reads: feedback_db (feedbacks, escalations, resolutions)         │
          │    Computes: status cubes, SLA compliance, location rollups,        │
          │              daily trends, category performance                     │
          │    Writes: analytics_db.analytics_* tables                          │
          └──────────────────────────────────────────────────────────────────────┘
          ┌──────────────────────────────────────────────────────────────────────┐
          │  Job 5 — ML Escalation Predictor                                    │
          │    Trains on last 2 years of feedback + outcome labels              │
          │    Scores all currently open grievances                             │
          │    Writes: analytics_db.feedback_ml_scores                          │
          └──────────────────────────────────────────────────────────────────────┘
          ┌──────────────────────────────────────────────────────────────────────┐
          │  Job 6 — SEP Annex Report Generator                                 │
          │    Full JOIN across all feedback tables                             │
          │    Produces: Annex 5 (xlsx), Annex 6 (pdf)                         │
          │    Uploads to MinIO, stores URL in analytics_db.generated_reports  │
          └──────────────────────────────────────────────────────────────────────┘
```

---

## 7. Implementation Plan

### Phase 1 — Infrastructure (Week 1–2)

Add Spark and analytics_db to the Docker Compose stack:

```yaml
# docker-compose.yml additions

spark_master:
  image: bitnami/spark:3.5
  environment:
    - SPARK_MODE=master
    - SPARK_RPC_AUTHENTICATION_ENABLED=no
  ports:
    - "8080:8080"   # Spark Web UI
    - "7077:7077"   # Spark master port
  networks:
    - riviwa_network

spark_worker_1:
  image: bitnami/spark:3.5
  environment:
    - SPARK_MODE=worker
    - SPARK_MASTER_URL=spark://spark_master:7077
    - SPARK_WORKER_MEMORY=2G
    - SPARK_WORKER_CORES=2
  depends_on:
    - spark_master
  networks:
    - riviwa_network

spark_worker_2:
  image: bitnami/spark:3.5
  environment:
    - SPARK_MODE=worker
    - SPARK_MASTER_URL=spark://spark_master:7077
    - SPARK_WORKER_MEMORY=2G
    - SPARK_WORKER_CORES=2
  depends_on:
    - spark_master
  networks:
    - riviwa_network

analytics_db:
  image: postgres:15
  environment:
    POSTGRES_DB: analytics_db
    POSTGRES_USER: analytics_admin
    POSTGRES_PASSWORD: analytics_pass_789
  ports:
    - "5438:5432"
  volumes:
    - analytics_db_data:/var/lib/postgresql/data
  networks:
    - riviwa_network
```

**analytics_db schema (initial tables):**
```sql
-- Pre-computed metrics
CREATE TABLE analytics_status_counts (
    project_id UUID, feedback_type VARCHAR(20), status VARCHAR(30),
    count INT, computed_at TIMESTAMP DEFAULT now()
);

CREATE TABLE analytics_sla_compliance (
    project_id UUID, priority VARCHAR(20),
    total INT, ack_sla_met_count INT,
    avg_ack_hours FLOAT, avg_res_hours FLOAT,
    median_ack_hours FLOAT, median_res_hours FLOAT,
    computed_at TIMESTAMP DEFAULT now()
);

CREATE TABLE analytics_daily_trend (
    project_id UUID, feedback_type VARCHAR(20), day DATE,
    submitted_count INT, resolved_count INT,
    computed_at TIMESTAMP DEFAULT now()
);

CREATE TABLE analytics_feedback_cube (
    project_id UUID, issue_region VARCHAR(100), issue_district VARCHAR(100),
    issue_lga VARCHAR(100), category VARCHAR(100), channel VARCHAR(50),
    priority VARCHAR(20), count INT, resolved_count INT,
    avg_ack_hours FLOAT, avg_res_hours FLOAT,
    computed_at TIMESTAMP DEFAULT now()
);

-- SLA tracking
CREATE TABLE feedback_sla_status (
    feedback_id UUID PRIMARY KEY,
    priority VARCHAR(20),
    submitted_at TIMESTAMP,
    ack_deadline TIMESTAMP,
    res_deadline TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    ack_sla_met BOOLEAN,
    res_sla_met BOOLEAN,
    ack_sla_breached BOOLEAN DEFAULT false,
    res_sla_breached BOOLEAN DEFAULT false,
    updated_at TIMESTAMP DEFAULT now()
);

-- Hotspot alerts
CREATE TABLE hotspot_alerts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    project_id UUID,
    location VARCHAR(200),
    category VARCHAR(100),
    count_in_window INT,
    baseline_avg FLOAT,
    spike_factor FLOAT,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    alert_status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT now()
);

-- ML scores
CREATE TABLE feedback_ml_scores (
    feedback_id UUID PRIMARY KEY,
    escalation_probability FLOAT,
    predicted_resolution_hours FLOAT,
    recommended_priority VARCHAR(20),
    model_version VARCHAR(50),
    scored_at TIMESTAMP DEFAULT now()
);

-- Pre-built report files
CREATE TABLE generated_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    project_id UUID,
    report_type VARCHAR(50),    -- 'annex5', 'annex6', 'grievance_performance', etc.
    period_start DATE,
    period_end DATE,
    file_url VARCHAR(500),
    file_format VARCHAR(10),    -- 'xlsx', 'pdf', 'csv'
    generated_at TIMESTAMP DEFAULT now()
);
```

---

### Phase 2 — Spark Jobs Directory

New service directory: `spark_jobs/`

```
spark_jobs/
├── Dockerfile
├── requirements.txt           # pyspark, psycopg2, redis, kafka-python
├── jobs/
│   ├── streaming/
│   │   ├── sla_monitor.py         # Job 1
│   │   ├── hotspot_detector.py    # Job 2
│   │   └── live_dashboard.py      # Job 3
│   └── batch/
│       ├── historical_analytics.py  # Job 4
│       ├── ml_escalation.py         # Job 5
│       └── annex_reports.py         # Job 6
├── lib/
│   ├── db_config.py           # DB connection settings
│   ├── kafka_config.py        # Kafka bootstrap servers
│   └── redis_client.py        # Redis writes
└── scheduler/
    └── cron.py                # APScheduler submits batch jobs to Spark master
```

**Job submission pattern:**
```python
# scheduler/cron.py
from pyspark.sql import SparkSession
import subprocess

def submit_job(job_path: str):
    subprocess.run([
        "spark-submit",
        "--master", "spark://spark_master:7077",
        "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                      "org.postgresql:postgresql:42.6.0",
        job_path
    ])

# Batch jobs schedule
scheduler.add_job(lambda: submit_job("jobs/batch/historical_analytics.py"),
                  "cron", hour=2, minute=0)   # 02:00 nightly

scheduler.add_job(lambda: submit_job("jobs/batch/ml_escalation.py"),
                  "cron", hour=3, minute=0)   # 03:00 nightly

scheduler.add_job(lambda: submit_job("jobs/batch/annex_reports.py"),
                  "cron", hour=4, minute=0)   # 04:00 nightly

scheduler.add_job(lambda: submit_job("jobs/batch/historical_analytics.py"),
                  "cron", minute=0)           # Also runs every hour (incremental)
```

**Streaming jobs start on container boot:**
```bash
# entrypoint.sh for spark_jobs container
spark-submit --master spark://spark_master:7077 jobs/streaming/sla_monitor.py &
spark-submit --master spark://spark_master:7077 jobs/streaming/hotspot_detector.py &
spark-submit --master spark://spark_master:7077 jobs/streaming/live_dashboard.py &
```

---

### Phase 3 — analytics_service (Week 3–4)

New FastAPI service that reads from `analytics_db` and Redis, replacing slow report queries.

```
analytics_service/
├── main.py
├── api/v1/
│   ├── dashboard.py       # GET /analytics/dashboard/{project_id}
│   ├── reports.py         # GET /analytics/reports/{project_id}/{type}
│   ├── sla.py             # GET /analytics/sla/{project_id}
│   ├── hotspots.py        # GET /analytics/hotspots/{project_id}
│   └── predictions.py     # GET /analytics/predictions/{feedback_id}
├── repositories/
│   └── analytics_repository.py   # reads analytics_db
└── core/
    └── config.py
```

**Nginx routing addition** (new prefix → analytics_service:8095):
```nginx
location /api/v1/analytics {
    proxy_pass http://analytics_service:8095;
}
```

---

### Phase 4 — Connect feedback_service to ML scores (Week 4)

One addition to `feedback_service` to display ML risk scores to officers:

```python
# feedback_service/api/v1/feedback.py — existing GET /feedback/{id}
# Add: fetch ML score from analytics_db and attach to response

async def get_feedback(feedback_id: UUID, db: DbDep):
    feedback = await repo.get_by_id(feedback_id)
    # Existing code above
    
    # NEW: fetch ML prediction
    ml_score = await analytics_repo.get_ml_score(feedback_id)
    return FeedbackDetailResponse(
        ...existing_fields...,
        ml_prediction=MLPrediction(
            escalation_probability=ml_score.escalation_probability if ml_score else None,
            predicted_resolution_hours=ml_score.predicted_resolution_hours if ml_score else None,
            recommended_priority=ml_score.recommended_priority if ml_score else None,
        )
    )
```

---

## 8. New Service: analytics_service

**Key endpoints added to the platform:**

| Endpoint | Description | Response time |
|----------|-------------|---------------|
| `GET /analytics/dashboard/{project_id}` | Live counters, all metrics | < 5ms (Redis) |
| `GET /analytics/sla/{project_id}` | SLA compliance table per priority | < 20ms (analytics_db) |
| `GET /analytics/hotspots/{project_id}` | Active hotspot alerts | < 20ms (analytics_db) |
| `GET /analytics/trends/{project_id}` | Daily/weekly time series | < 30ms (analytics_db) |
| `GET /analytics/reports/{project_id}/annex5` | Download pre-built Annex 5 XLSX | < 50ms (MinIO redirect) |
| `GET /analytics/reports/{project_id}/annex6` | Download pre-built Annex 6 PDF | < 50ms (MinIO redirect) |
| `GET /analytics/predictions/{feedback_id}` | ML escalation risk for one case | < 10ms (analytics_db) |
| `GET /analytics/leaderboard/{project_id}` | Officer performance (resolution speed) | < 30ms (analytics_db) |
| `GET /analytics/escalation-paths/{project_id}` | Escalation flow diagram data | < 30ms (analytics_db) |

---

## 9. Expected Outcomes — Before vs After

### Performance

| Metric | Current (without Spark) | With Spark |
|--------|------------------------|------------|
| Report load time | 10–30 seconds | < 100ms |
| Dashboard refresh | On request (stale data) | Live, 30-second cadence |
| SLA breach detection | Only when officer checks manually | Within 60 seconds of deadline |
| Hotspot detection | Only on weekly report | Within 15 minutes of threshold hit |
| Annex 5/6 export | 20–30 seconds per request | Instant (pre-built, download link) |
| feedback_db CPU during reports | High (report queries compete with writes) | Near zero (all analytics offloaded) |

### Real-Time GRM Service Delivery

| Scenario | Without Spark | With Spark |
|----------|--------------|-----------|
| Critical grievance unacknowledged for 4 hours | Nobody knows until manual check | Officer and manager notified at hour 4 + automatic escalation |
| 10 water-related grievances from same ward in 1 hour | Noticed at next week's meeting | Alert fired within 15 minutes |
| Officer has 30 open cases — which to prioritise? | First-in-first-out or manual judgment | ML scores rank by escalation risk |
| World Bank auditor wants Annex 5 for last quarter | Report officer spends 20 min generating | Instant download from pre-built file |
| Project manager wants live resolution rate | Refreshes report page every hour | Live counter on dashboard |

### Suggestion and Applause Benefits

| Feature | Suggestions | Applause |
|---------|-------------|---------|
| SLA monitoring | Tracks actioned-by deadline (if set) | Tracks acknowledgement-by deadline |
| Hotspot detection | Surge of suggestions in one category → product team alert | Surge of applause → positive signal to communications team |
| ML prediction | Estimates probability suggestion will be actioned (vs noted/dismissed) | — |
| Trend analytics | Implementation rate over time by category | Acknowledgement rate by channel |
| Pre-built reports | Suggestion-log Annex pre-generated nightly | Applause-log Annex pre-generated nightly |

---

## 10. Summary

Apache Spark transforms Riviwa from a **record-keeping system** into a **real-time action platform**.

The six jobs address the six core GRM failures that lead to grievances being ignored:

| GRM failure | Spark job that prevents it |
|------------|---------------------------|
| Deadlines crossed silently | Job 1 — SLA Monitor fires alert within 60s |
| Geographic problems missed until too late | Job 2 — Hotspot Detector fires in 15 min |
| Dashboard data stale, managers uninformed | Job 3 — Live Dashboard updated every 30s |
| Reports too slow to use in real-time decisions | Job 4 — Analytics Engine pre-computes hourly |
| Officers don't know which cases need urgency | Job 5 — ML Predictor ranks by escalation risk |
| Compliance reporting is manual effort | Job 6 — SEP Annex auto-generated nightly |

None of this replaces any existing Riviwa service. Spark sits as an **analytics layer** that reads the Kafka events your services already publish, processes them in parallel, and writes results to Redis and analytics_db. The existing services remain unchanged except for one addition: the feedback officer case view gets ML risk scores displayed alongside the grievance details.

The total infrastructure addition is:
- 1 Spark master container
- 2 Spark worker containers
- 1 analytics_db (PostgreSQL)
- 1 analytics_service (FastAPI, ~500 lines)
- 1 spark_jobs directory (~1,200 lines of PySpark)

This is the smallest possible footprint for the largest possible improvement in real-time service delivery.
