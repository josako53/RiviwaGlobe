-- analytics_db schema initialisation
-- Run once against analytics_db (PostgreSQL port 5441).
-- All tables use CREATE TABLE IF NOT EXISTS so they are safe to re-run.

-- -----------------------------------------------------------------------
-- feedback_sla_status
-- Written by: sla_monitor (streaming) and historical_analytics (batch)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback_sla_status (
    feedback_id             TEXT        PRIMARY KEY,
    project_id              TEXT,
    priority                TEXT,
    submitted_at            TIMESTAMPTZ,
    ack_deadline            TIMESTAMPTZ,
    res_deadline            TIMESTAMPTZ,
    acknowledged_at         TIMESTAMPTZ,
    resolved_at             TIMESTAMPTZ,
    ack_sla_met             BOOLEAN,
    ack_sla_breached        BOOLEAN,
    res_sla_met             BOOLEAN,
    res_sla_breached        BOOLEAN,
    days_unresolved         DOUBLE PRECISION,
    updated_at              TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sla_status_project
    ON feedback_sla_status (project_id);
CREATE INDEX IF NOT EXISTS idx_sla_status_breached
    ON feedback_sla_status (ack_sla_breached, res_sla_breached);

-- -----------------------------------------------------------------------
-- hotspot_alerts
-- Written by: hotspot_detector (streaming)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hotspot_alerts (
    id              BIGSERIAL   PRIMARY KEY,
    project_id      TEXT,
    issue_lga       TEXT,
    category        TEXT,
    window_start    TIMESTAMPTZ,
    window_end      TIMESTAMPTZ,
    event_count     INTEGER,
    baseline_avg    DOUBLE PRECISION,
    detected_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hotspot_project
    ON hotspot_alerts (project_id, detected_at DESC);

-- -----------------------------------------------------------------------
-- hotspot_baseline_7d  (materialised baseline – refreshed by batch jobs)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hotspot_baseline_7d (
    project_id      TEXT,
    issue_lga       TEXT,
    category        TEXT,
    baseline_avg    DOUBLE PRECISION,
    computed_at     TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (project_id, issue_lga, category)
);

-- -----------------------------------------------------------------------
-- committee_performance
-- Written by: staff_analytics (batch nightly)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS committee_performance (
    committee_id            TEXT,
    committee_name          TEXT,
    cases_assigned          BIGINT,
    cases_resolved          BIGINT,
    cases_overdue           BIGINT,
    avg_resolution_hours    DOUBLE PRECISION,
    resolution_rate         DOUBLE PRECISION,
    partition_date          TEXT,           -- YYYY-MM-DD string for partitioning
    computed_at             TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (committee_id, partition_date)
);

-- -----------------------------------------------------------------------
-- staff_logins
-- Written by: staff_analytics (batch nightly)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staff_logins (
    user_id             TEXT        PRIMARY KEY,
    last_login          TIMESTAMPTZ,
    login_count_24h     INTEGER,
    computed_at         TIMESTAMPTZ DEFAULT now()
);

-- -----------------------------------------------------------------------
-- feedback_ml_scores
-- Written by: ml_escalation (batch nightly)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback_ml_scores (
    feedback_id                 TEXT        PRIMARY KEY,
    escalation_probability      DOUBLE PRECISION,
    predicted_resolution_hours  DOUBLE PRECISION,
    recommended_priority        TEXT,
    scored_at                   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ml_scores_prob
    ON feedback_ml_scores (escalation_probability DESC);

-- -----------------------------------------------------------------------
-- analytics_status_counts
-- Written by: historical_analytics (batch hourly)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_status_counts (
    project_id      TEXT,
    feedback_type   TEXT,
    status          TEXT,
    count           BIGINT,
    computed_at     TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (project_id, feedback_type, status)
);

-- -----------------------------------------------------------------------
-- analytics_sla_compliance
-- Written by: historical_analytics (batch hourly)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_sla_compliance (
    project_id              TEXT,
    priority                TEXT,
    total_count             BIGINT,
    avg_ack_hours           DOUBLE PRECISION,
    median_ack_hours        DOUBLE PRECISION,
    avg_res_hours           DOUBLE PRECISION,
    median_res_hours        DOUBLE PRECISION,
    ack_sla_met_count       BIGINT,
    res_sla_met_count       BIGINT,
    ack_compliance_pct      DOUBLE PRECISION,
    res_compliance_pct      DOUBLE PRECISION,
    computed_at             TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (project_id, priority)
);

-- -----------------------------------------------------------------------
-- analytics_daily_trend
-- Written by: historical_analytics (batch hourly)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_daily_trend (
    project_id          TEXT,
    feedback_type       TEXT,
    submitted_date      DATE,
    submitted_count     BIGINT,
    resolved_count      BIGINT,
    computed_at         TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (project_id, feedback_type, submitted_date)
);
