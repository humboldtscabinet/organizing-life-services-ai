-- Allowlisted apply loop: frozen action_kind + fingerprint on dashboard tasks.
-- Idempotent for existing volumes (init.sql covers fresh installs).

ALTER TABLE dashboard_tasks
    ADD COLUMN IF NOT EXISTS action_kind VARCHAR(100);

ALTER TABLE dashboard_tasks
    ADD COLUMN IF NOT EXISTS fingerprint VARCHAR(300);

CREATE INDEX IF NOT EXISTS ix_dashboard_tasks_fingerprint
    ON dashboard_tasks (fingerprint);

CREATE INDEX IF NOT EXISTS ix_dashboard_tasks_action_kind
    ON dashboard_tasks (action_kind);
