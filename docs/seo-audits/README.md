# SEO Audits

Human-readable, point-in-time SEO audits for **organizinglifeservices.com**.

Each file is a snapshot — it captures what the site looked like, what changed since the prior audit, and what worked or didn't. New audits are appended; old ones are kept for trend analysis.

## Naming convention

```
YYYY-MM-DD-<short-slug>.md
```

Example: `2026-05-25-post-april-changes-audit.md`

## How audits are generated

1. Run the deep audit script (writes raw JSON + MD to `data/audit_output/`):
   ```bash
   source .venv-audit/bin/activate
   python data/deep_seo_audit.py
   ```
2. Synthesize the raw output into a human-readable summary in this folder.
3. Update [CHANGELOG.md](CHANGELOG.md) with the new audit entry.
4. Commit and push so the team has the full history.

See [docs/runbooks/run-deep-seo-audit.md](../runbooks/run-deep-seo-audit.md) for the full procedure.

## Raw outputs

`data/audit_output/` is tracked in git (both `.md` and `.json`) so contributors and the weekly GitHub Actions cron can diff audits across time. The curated summaries in *this* folder are the human-readable interpretation; the raw files are the machine-readable source.

## Cadence

- After every significant SEO change (meta rewrites, schema deploys, new content batches)
- Otherwise, every 28 days, so windows line up with GSC comparison periods
