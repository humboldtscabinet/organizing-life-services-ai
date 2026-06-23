# Workflows

## Current Status

The project has two automation surfaces:

- GitHub Actions for repo-side checks and weekly audit generation.
- n8n for local/server-side scheduled operations.

Do not run duplicate weekly SEO automations from both surfaces unless their
roles are clearly separated.

## n8n

Versioned workflow templates live in `workflows/n8n/`.

The weekly SEO audit workflow is intentionally a template until imported,
configured, and activated inside the Mac mini n8n instance. It should call only
localhost-bound OLS API endpoints and must use `OLS_API_KEY` from n8n
credentials or environment.

## GitHub Actions

Use GitHub Actions for:

- tests and lint checks,
- secret scanning,
- repo-visible audit artifacts,
- PR-based review of generated SEO reports.

Avoid putting Shopify write credentials in GitHub Actions unless the workflow is
explicitly designed, reviewed, and protected for production writes.

## Recommended Ownership

- Weekly measurement audit: GitHub Actions is the current owner because it
  produces repo-visible artifacts and PR review. Keep the n8n weekly audit
  workflow inactive unless you deliberately move ownership to the Mac mini.
- Public Shopify writes: manual approval through guarded API routes.
- Direct `data/` scripts: historical/manual fallback only; see
  [runbooks/data-mutation-scripts.md](runbooks/data-mutation-scripts.md).

## Off-Machine Backup Status

The Mac mini backup runner supports `OFFSITE_BACKUP_DIR`, but the off-machine
destination is an operator decision. Until the external G-Drive or iCloud path
is mounted and configured, backups should be treated as local-only.
