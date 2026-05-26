# SEO Audits

Human-readable, point-in-time SEO audits for **organizinglifeservices.com**.

Each file is a snapshot — it captures what the site looked like, what changed since the prior audit, and what worked or didn't. New audits are appended; old ones are kept for trend analysis.

## Naming convention

```
YYYY-MM-DD-<short-slug>.md
```

Example: `2026-05-25-post-april-changes-audit.md`

## How audits are generated

1. Run the deep audit script (writes raw JSON + MD to the gitignored `data/audit_output/`):
   ```bash
   source .venv-audit/bin/activate
   python data/deep_seo_audit.py
   ```
2. Synthesize the raw output into a human-readable summary in this folder.
3. Commit and push so the team has the full history.

## Why not commit the raw output?

`data/audit_output/` is intentionally gitignored — the raw JSON can contain large query/page lists and changes every run. The curated summaries in this folder are the canonical record.

## Cadence

- After every significant SEO change (meta rewrites, schema deploys, new content batches)
- Otherwise, every 28 days, so windows line up with GSC comparison periods
