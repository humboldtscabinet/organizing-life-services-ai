# Changelog

Engineering changelog for the OLS stack (code/config changes). Live-site SEO
changes are tracked separately in
[`docs/seo-audits/CHANGELOG.md`](docs/seo-audits/CHANGELOG.md). Newest first.

## Unreleased

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
