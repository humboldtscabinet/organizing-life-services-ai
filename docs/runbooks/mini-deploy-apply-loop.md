# Runbook: Mini deploy of the allowlisted Apply loop

Deploy GitHub `main` (PR #61 / `4102027` or later) onto the Mac mini so
`POST /api/dashboard/tasks/{id}/apply` exists, then install launchd platform
sync. Full stack deploy is documented in [deployment.md](../deployment.md).

This is **operator work on the mini**. Do not flip the mini GitHub deploy key
to write. Push from the laptop.

## Prerequisites

- SSH as `aiagentecosystem` (LAN `agent-eco-mini.local` or Tailscale MagicDNS)
- Repo at `/Users/aiagentecosystem/services/ols`
- Production `.env` and `credentials/google-service-account.json` already present

## 1. Pull and confirm HEAD

```bash
cd /Users/aiagentecosystem/services/ols
git fetch origin
git checkout main
git pull origin main
git log -1 --oneline
# Expect 4102027 or a later commit that includes app/services/task_apply_service.py
test -f app/services/task_apply_service.py && echo HAS_APPLY
```

## 2. Server `.env` — GTM detector will no-op without these

June 2026 audit found GTM IDs on the iMac, not the mini. Confirm **server**
`.env` (numeric GTM IDs, not the public `GTM-XXXX` string):

```bash
grep -E '^(GTM_ACCOUNT_ID|GTM_CONTAINER_ID|GA4_MEASUREMENT_ID|GA4_PROPERTY_ID|GSC_SITE_URL)=' .env
```

| Key | Shape |
|---|---|
| `GTM_ACCOUNT_ID` | numeric account id |
| `GTM_CONTAINER_ID` | numeric internal container id (not `GTM-KQ76X4NR`) |
| `GA4_MEASUREMENT_ID` | `G-…` |
| `GA4_PROPERTY_ID` | numeric property id (`396184354`) |

Do not commit `.env`.

## 3. Deploy (builds, migrations, verify)

```bash
infra/server/deploy_server.sh
```

`deploy_server.sh` already runs `infra/postgres/apply_migrations.sh`, including
`005_dashboard_task_apply.sql` (`action_kind`, `fingerprint`).

## 4. Smoke

```bash
docker exec ols-api printenv GTM_ACCOUNT_ID GTM_CONTAINER_ID GA4_MEASUREMENT_ID
set -a && source .env && set +a
curl -sS -H "X-API-Key: ${OLS_API_KEY}" http://127.0.0.1:8000/health/ready
curl -sS -H "X-API-Key: ${OLS_API_KEY}" http://127.0.0.1:8000/api/dashboard/tasks | head
```

Dashboard: Apply appears on GTM / content cards only. Advisory GSC cards stay
Approve / Dismiss. **Do not** Apply GTM publish unless you intend a live
container publish.

## 5. Install the one scheduler (after this PR is on the mini)

Do **not** import `workflows/n8n/*.json`. Leave `ols-n8n` running so n8n
backups keep working.

```bash
chmod +x infra/server/run_platform_sync.sh infra/server/install_launchd_platform_sync.sh
infra/server/install_launchd_platform_sync.sh
launchctl kickstart -k gui/$(id -u)/com.ols.platform-sync.daily
ls -l infra/server/out/
```

Daily 06:00 `--generate-tasks`. Monday 07:00 `--full-cycle`.

## 6. FileVault / power (operator decision)

No script will turn FileVault off. Pick one posture and record it:

1. **Keep FileVault.** Accept a site visit after power loss. Still run
   `sudo pmset autorestart 1` so the Mac powers on to the unlock screen.
2. **Physically secure headless.** FileVault off, auto-login
   `aiagentecosystem`, OrbStack login item, `sudo pmset autorestart 1`.

See [mac-mini-implementation-guide.md](../mac-mini-implementation-guide.md) §0.6
and §1.9–1.11.

## If something goes wrong

- Migration already applied: `apply_migrations.sh` is idempotent for `005`.
- Apply 404: image is stale — confirm `docker exec ols-api ls /app/app/services/task_apply_service.py`.
- GTM detector silent: printenv GTM_* inside `ols-api`.
- launchd never runs: `launchctl print gui/$(id -u)/com.ols.platform-sync.daily`
  and OrbStack PATH in the plist (installer bakes Homebrew + OrbStack).
