# Changelog

Engineering changelog for the OLS stack (code/config changes). Live-site SEO
changes are tracked separately in
[`docs/seo-audits/CHANGELOG.md`](docs/seo-audits/CHANGELOG.md). Newest first.

## Unreleased

- **Enqueue-time task filters keep obvious junk out of the dashboard queue.**
  New pure-predicate module `app/services/task_enqueue_filters.py` (no Apply,
  gate, or `action_kind` changes) is wired into task *creation*:
  - `shopify.apply_frozen_meta` drafts are **not enqueued** when the rewrite
    (a) is essentially the raw GSC query, (b) drops the live page's city or
    core service term, (c) targets a rank hole (avg position ≥ 15, i.e. a
    ranking job not a snippet/CTR job), (d) duplicates a URL/handle that
    already has an open frozen-meta task, or (e) is truncated / keyword-stuffed
    / mentions a competitor. Real CTR snippet jobs on existing URLs that keep
    the city + service on-brand still enqueue.
  - Frozen-meta tasks now **dedupe by URL/handle, not by query** — one page,
    one frozen-meta task (`_generate_gsc_tasks` in
    `app/services/dashboard_service.py`; GSC watches stay advisory notes).
  - `content.generate_and_publish` skips **LOW-lead shopper "near me" blogs**
    when a live location/near-me page or post already covers the keyword
    (`schedule_weekly_content` in `app/services/content_scheduler.py` +
    `get_existing_content_coverage` in `app/services/content_engine.py`).
    Seller-intent HIGH/MEDIUM content tasks still enqueue.
  - No historical rows are backfilled or auto-dismissed (queue cleanup stays an
    operator action). Covered by `tests/test_task_enqueue_filters.py`.
- **Executive blog writer now uses Claude Sonnet 5** (`claude-sonnet-5`). The
  executive default in `app/services/llm_router.py` and the
  `ANTHROPIC_MODEL` / `ANTHROPIC_JUDGE_MODEL` defaults in
  `docker-compose.server.yml` and `.env.example` move off the retired
  `claude-sonnet-4-20250514` snapshot.
- **Sampling params are omitted for models that reject them.** `_call_anthropic`
  no longer sends `temperature` (nor `top_p`/`top_k`) for Claude Sonnet 5 or
  Claude Opus 4.7/4.8, which 400 on non-default sampling and run adaptive
  thinking by default. Older Anthropic snapshots (e.g. `claude-sonnet-4-*`)
  still receive `temperature`, so fallback routing is unaffected. This fixes the
  `POST /api/content/preview-for-task` 500 (`temperature is deprecated for this
  model`). `content_draft` `max_tokens` was raised so adaptive thinking does not
  truncate the article JSON.
- **Judiciary remains Grok when `XAI_API_KEY` is set.** Independent-reviewer
  routing is unchanged: xAI/Grok is still the judge whenever the key is present,
  and the Anthropic judge is only a fallback when it is absent.
