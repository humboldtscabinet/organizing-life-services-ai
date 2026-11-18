-- Recommendation de-duplication for dashboard tasks: a stable dedupe_key
-- (kind + query/target) plus a dismissed_at anchor for the configurable
-- "recently dismissed" window. Idempotent for existing volumes (init.sql
-- covers fresh installs). Existing rows are left untouched: new columns
-- default to NULL and the dedupe path falls back to created_at when a
-- dismissed row predates this migration.

ALTER TABLE dashboard_tasks
    ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(300);

ALTER TABLE dashboard_tasks
    ADD COLUMN IF NOT EXISTS dismissed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_dashboard_tasks_dedupe_key
    ON dashboard_tasks (dedupe_key);
