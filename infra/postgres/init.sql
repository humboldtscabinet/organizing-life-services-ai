-- =============================================================
-- Organizing Life Services AI — Postgres Init (MVP Tables)
-- Runs automatically on first docker compose up
-- =============================================================

-- ---------- Core tables ----------

CREATE TABLE IF NOT EXISTS contacts (
    id              SERIAL PRIMARY KEY,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    phone           VARCHAR(30),
    email           VARCHAR(255),
    source          VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_logs (
    id              SERIAL PRIMARY KEY,
    workflow_name   VARCHAR(200) NOT NULL,
    status          VARCHAR(50) NOT NULL,
    payload         JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_audit (
    id                  SERIAL PRIMARY KEY,
    task_type           VARCHAR(100) NOT NULL,
    risk_level          VARCHAR(30) NOT NULL,
    model_role          VARCHAR(50) NOT NULL,
    provider            VARCHAR(50) NOT NULL,
    model               VARCHAR(200) NOT NULL,
    status              VARCHAR(50) NOT NULL,
    verdict             VARCHAR(30),
    prompt_tokens       INTEGER,
    completion_tokens   INTEGER,
    total_tokens        INTEGER,
    estimated_cost_usd  DOUBLE PRECISION,
    input_refs          JSONB,
    request             JSONB,
    response            JSONB,
    error               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_llm_audit_task_created
    ON llm_audit (task_type, created_at);
CREATE INDEX IF NOT EXISTS ix_llm_audit_risk_status
    ON llm_audit (risk_level, status);

-- ---------- SEO tables (Phase 1) ----------

CREATE TABLE IF NOT EXISTS seo_reports (
    id              SERIAL PRIMARY KEY,
    report_type     VARCHAR(100) NOT NULL,
    report_date     TIMESTAMPTZ NOT NULL,
    summary         TEXT,
    data            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gsc_data (
    id              SERIAL PRIMARY KEY,
    query           VARCHAR(500),
    page            VARCHAR(500),
    clicks          INTEGER DEFAULT 0,
    impressions     INTEGER DEFAULT 0,
    ctr             DOUBLE PRECISION DEFAULT 0.0,
    position        DOUBLE PRECISION DEFAULT 0.0,
    date            TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ga4_data (
    id              SERIAL PRIMARY KEY,
    metric_name     VARCHAR(200) NOT NULL,
    metric_value    DOUBLE PRECISION,
    dimension_name  VARCHAR(200),
    dimension_value VARCHAR(500),
    date            TIMESTAMPTZ NOT NULL,
    data            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gbp_insights (
    id              SERIAL PRIMARY KEY,
    metric_name     VARCHAR(200) NOT NULL,
    metric_value    DOUBLE PRECISION,
    period_start    TIMESTAMPTZ,
    period_end      TIMESTAMPTZ,
    data            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS google_ads_data (
    id              SERIAL PRIMARY KEY,
    campaign_name   VARCHAR(300),
    ad_group        VARCHAR(300),
    clicks          INTEGER DEFAULT 0,
    impressions     INTEGER DEFAULT 0,
    cost            DOUBLE PRECISION DEFAULT 0.0,
    conversions     DOUBLE PRECISION DEFAULT 0.0,
    date            TIMESTAMPTZ NOT NULL,
    data            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS image_analysis (
    id              SERIAL PRIMARY KEY,
    image_url       VARCHAR(1000) NOT NULL,
    filename        VARCHAR(500),
    gallery_name    VARCHAR(300),
    alt_text        TEXT,
    title           VARCHAR(500),
    item_tags       JSONB,
    description     TEXT,
    confidence      DOUBLE PRECISION,
    status          VARCHAR(50) DEFAULT 'pending',
    data            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_image_analysis_status
    ON image_analysis (status);
CREATE INDEX IF NOT EXISTS ix_image_analysis_gallery_name
    ON image_analysis (gallery_name);
CREATE INDEX IF NOT EXISTS ix_image_analysis_image_url
    ON image_analysis (image_url);
CREATE INDEX IF NOT EXISTS ix_image_analysis_status_gallery
    ON image_analysis (status, gallery_name);

CREATE TABLE IF NOT EXISTS shopify_orders (
    id              SERIAL PRIMARY KEY,
    shopify_order_id VARCHAR(100) UNIQUE NOT NULL,
    order_number    VARCHAR(50),
    customer_email  VARCHAR(255),
    total_price     DOUBLE PRECISION,
    status          VARCHAR(50),
    order_date      TIMESTAMPTZ,
    data            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ---------- Dashboard tables ----------

CREATE TABLE IF NOT EXISTS dashboard_tasks (
    id              SERIAL PRIMARY KEY,
    task_type       VARCHAR(50) NOT NULL,
    category        VARCHAR(100) NOT NULL,
    priority        VARCHAR(20) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    finding         TEXT,
    action_endpoint VARCHAR(500),
    action_payload  JSONB,
    status          VARCHAR(50) DEFAULT 'pending',
    result          JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    approved_at     TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    delayed_until   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ops_alerts (
    id                  SERIAL PRIMARY KEY,
    source              VARCHAR(100) NOT NULL,
    severity            VARCHAR(20) NOT NULL,
    status              VARCHAR(30) DEFAULT 'open',
    title               VARCHAR(300) NOT NULL,
    message             TEXT,
    fingerprint         VARCHAR(300),
    details             JSONB,
    occurrence_count    INTEGER DEFAULT 1,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at     TIMESTAMPTZ,
    dismissed_at        TIMESTAMPTZ,
    resolved_at         TIMESTAMPTZ,
    CONSTRAINT ck_ops_alerts_severity
        CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    CONSTRAINT ck_ops_alerts_status
        CHECK (status IN ('open', 'acknowledged', 'dismissed', 'resolved')),
    CONSTRAINT ck_ops_alerts_occurrence_count
        CHECK (occurrence_count >= 1)
);

CREATE INDEX IF NOT EXISTS ix_ops_alerts_status
    ON ops_alerts (status);
CREATE INDEX IF NOT EXISTS ix_ops_alerts_severity_status
    ON ops_alerts (severity, status);
CREATE INDEX IF NOT EXISTS ix_ops_alerts_source_status
    ON ops_alerts (source, status);
CREATE INDEX IF NOT EXISTS ix_ops_alerts_fingerprint_status
    ON ops_alerts (fingerprint, status);
CREATE INDEX IF NOT EXISTS ix_ops_alerts_created_at
    ON ops_alerts (created_at);
CREATE INDEX IF NOT EXISTS ix_ops_alerts_last_seen_at
    ON ops_alerts (last_seen_at);
