# Workflows

## Current Status

The project has two automation surfaces:

- GitHub Actions for repo-side checks and weekly audit generation.
- launchd on the Mac mini for Postgres refresh and the weekly Phase 1 cycle.

Do not run duplicate weekly SEO automations from both surfaces unless their
roles are clearly separated.

## launchd (Mac mini)

Installer: `infra/server/install_launchd_platform_sync.sh`

| Job | When | Command |
|---|---|---|
| `com.ols.platform-sync.daily` | 06:00 | `scheduled_platform_sync.py --generate-tasks` |
| `com.ols.platform-sync.weekly` | Monday 07:00 | `scheduled_platform_sync.py --full-cycle --schedule-content-count 1` |

Wrapper: `infra/server/run_platform_sync.sh` (waits for API health, then
`docker exec ols-api`). Logs: `infra/server/out/`.

See [runbooks/mini-deploy-apply-loop.md](runbooks/mini-deploy-apply-loop.md)
and [runbooks/phase1-automation.md](runbooks/phase1-automation.md).

## n8n

Versioned workflow templates live in `workflows/n8n/`. They stay **inactive**.
Do not import `daily_platform_sync.json`, `weekly_phase1_cycle.json`, or
`weekly_seo_audit.json` while launchd owns mini sync. Leave the `ols-n8n`
container running so encrypted n8n backups keep working.

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
  produces repo-visible artifacts and PR review.
- Daily platform snapshot: GitHub Actions (`daily-platform-snapshot.yml`) archives
  GSC + GA4 JSON under `data/audit_output/`. These files are **not** the live
  ops store.
- Daily Postgres refresh + task generation: Mac mini launchd
  `com.ols.platform-sync.daily`.
- Weekly gated Phase 1 cycle: Mac mini launchd `com.ols.platform-sync.weekly`.
- Public Shopify writes: manual approval through guarded API Apply routes.
- Direct `data/` scripts: historical/manual fallback only; see
  [runbooks/data-mutation-scripts.md](runbooks/data-mutation-scripts.md).

## Off-Machine Backup Status

The Mac mini backup runner supports `OFFSITE_BACKUP_DIR`, but the off-machine
destination is an operator decision. Until the external G-Drive or iCloud path
is mounted and configured, backups should be treated as local-only.
