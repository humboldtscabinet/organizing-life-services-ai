-- Backfill dedupe_key for legacy content_ranking rows created before the
-- dedupe_key column existed (migration 006 added the column but intentionally
-- left existing rows NULL). Without a key, the keyed dedupe lookup can never
-- match these rows, so the first run after deploy would re-create every open
-- or dismissed recommendation. The runtime also recovers the key at read time
-- (dashboard_service._existing_unkeyed_dedupe_task); this backfill makes the
-- fast keyed path catch them too.
--
-- The query is recovered from the stable title pattern
--   Create targeted content for '<query>' (position <n>)
-- and normalized exactly like app.services.dashboard_service._dedupe_key:
-- lowercased, internal whitespace collapsed to single spaces, trimmed.
--
-- apply_migrations.sh re-runs every migration file on each invocation, so this
-- MUST be safe to run repeatedly. It is: only rows with a NULL dedupe_key and a
-- matching title are touched, and ONLY the dedupe_key column is written. status,
-- dismissed_at, and every other column are left unchanged. Once keys are filled
-- a re-run matches nothing (UPDATE 0). dismissed_at is intentionally NOT
-- backfilled; the service treats a legacy dismissed row as dismissed at its
-- created_at for the recently-dismissed window.

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
