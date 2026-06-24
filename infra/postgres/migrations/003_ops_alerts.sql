-- Ops alert inbox for private dashboard/n8n health notifications.

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
    resolved_at         TIMESTAMPTZ
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
