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
