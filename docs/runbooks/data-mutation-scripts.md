# Runbook: Historical Data Mutation Scripts

The `data/` directory contains historical one-off SEO scripts from earlier
optimization sessions. Some are read-only audit helpers; others can write to
Shopify Admin API or IndexNow.

## Default Rule

Prefer guarded API routes over direct `data/` mutator scripts:

```text
human_confirmed=true
judge_verdict=PASS
```

Use direct scripts only when there is no maintained API path and the exact
target list/output has been reviewed.

## Direct Script Write Confirmation

Direct production writes from `data/` are blocked unless both values are set:

```bash
OLS_ALLOW_DATA_MUTATION=1 \
OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
python data/some_historical_script.py
```

This applies to Shopify Admin API mutations and IndexNow submissions. Read-only
scripts and Shopify OAuth token exchange are allowed.

## Before Running A Mutator

1. Read the script top-to-bottom.
2. Confirm it uses the intended target list, URL, theme, blog, or page IDs.
3. Run its dry-run mode first if available.
4. Save the before/after output or audit artifact.
5. Update `docs/seo-audits/CHANGELOG.md` after a live site change.

## Cleanup Policy

Do not add new one-off mutator scripts unless they are genuinely temporary.
Recurring operations should become one of:

- a guarded FastAPI route,
- a documented runbook with dry-run and typed confirmation,
- or a read-only audit script that writes only local review artifacts.
