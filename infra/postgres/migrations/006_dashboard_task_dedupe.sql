-- Recurring-task de-duplication: stable dedupe_key + dismissal timestamp.
-- Idempotent for existing volumes (init.sql covers fresh installs).
-- Adds nullable columns only; existing rows are left untouched (NULL).

ALTER TABLE dashboard_tasks
    ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(300);

ALTER TABLE dashboard_tasks
    ADD COLUMN IF NOT EXISTS dismissed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_dashboard_tasks_dedupe_key
    ON dashboard_tasks (dedupe_key);

-- Backfill dedupe_key for legacy content_ranking rows so the first run after
-- deploy does not re-create every open/dismissed recommendation (their keys
-- would otherwise be NULL and never match the keyed lookup). The query is
-- recovered from the stable title pattern
--   Create targeted content for '<query>' (position <n>)
-- and normalized exactly like app.services.dashboard_service.make_dedupe_key:
-- lowercased with internal whitespace collapsed to single spaces and trimmed.
--
-- Idempotent and non-destructive: only rows with a NULL dedupe_key and a
-- matching title are touched, and ONLY the dedupe_key column is written. status
-- and every other column (including dismissed_at) are left unchanged. Re-running
-- is a no-op once keys are filled. dismissed_at is intentionally NOT backfilled;
-- the service treats a legacy dismissed row as dismissed at its created_at.
UPDATE dashboard_tasks
SET dedupe_key = 'seo:content_ranking:' || btrim(
        regexp_replace(
            lower(
                substring(
                    title FROM '^Create targeted content for ''(.+)'' \(position [0-9.]+\)$'
                )
            ),
            '\s+', ' ', 'g'
        )
    )
WHERE dedupe_key IS NULL
  AND task_type = 'seo'
  AND category = 'content_ranking'
  AND title ~ '^Create targeted content for ''(.+)'' \(position [0-9.]+\)$';
