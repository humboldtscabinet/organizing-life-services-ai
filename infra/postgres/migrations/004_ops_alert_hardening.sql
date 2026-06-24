-- Hardening for operational alerts after the initial inbox rollout.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_ops_alerts_severity'
    ) THEN
        ALTER TABLE ops_alerts
            ADD CONSTRAINT ck_ops_alerts_severity
            CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_ops_alerts_status'
    ) THEN
        ALTER TABLE ops_alerts
            ADD CONSTRAINT ck_ops_alerts_status
            CHECK (status IN ('open', 'acknowledged', 'dismissed', 'resolved'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_ops_alerts_occurrence_count'
    ) THEN
        ALTER TABLE ops_alerts
            ADD CONSTRAINT ck_ops_alerts_occurrence_count
            CHECK (occurrence_count >= 1);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_ops_alerts_last_seen_at
    ON ops_alerts (last_seen_at);
