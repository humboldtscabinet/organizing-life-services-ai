-- Recurring-task de-duplication: stable dedupe_key + dismissal timestamp.
-- Idempotent for existing volumes (init.sql covers fresh installs).
-- Adds nullable columns only; existing rows are left untouched (NULL).

ALTER TABLE dashboard_tasks
    ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(300);

ALTER TABLE dashboard_tasks
    ADD COLUMN IF NOT EXISTS dismissed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_dashboard_tasks_dedupe_key
    ON dashboard_tasks (dedupe_key);
