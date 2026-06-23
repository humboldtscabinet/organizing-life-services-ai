# Deployment

## Laptop Development

Use the dev compose file when working locally:

```bash
docker compose up -d --build
```

This profile bind-mounts the app source and runs FastAPI with reload enabled.

## Mac Mini Server

Use the server compose file on the always-on Mac mini:

```bash
docker compose -f docker-compose.server.yml up -d --build
```

Prefer connecting to the mini by mDNS name instead of a changing DHCP address:

```bash
ssh aiagentecosystem@agent-eco-mini.local
```

The mini has previously moved between `192.168.1.73` and `192.168.1.19`.
Reserve a DHCP lease in the router before documenting or automating a numeric
LAN IP.

Server behavior:

- FastAPI runs without the development reloader.
- Postgres is not published to the host network.
- API, dashboard, and n8n bind to `127.0.0.1` by default.
- Dashboard users enter `OLS_API_KEY` in the browser unlock screen.
- n8n is pinned and expects a stable `N8N_ENCRYPTION_KEY`.

The preferred setup-day command is:

```bash
infra/server/deploy_server.sh
```

It creates required local directories, runs preflight, starts the server compose
stack, applies SQL migrations, and runs the stack verifier.

## Server Pre-flight

Before first server deploy, set unique values in `.env`:

```text
POSTGRES_PASSWORD
SECRET_KEY
OLS_API_KEY
N8N_ENCRYPTION_KEY
BACKUP_ENCRYPTION_PASSWORD
CORS_ALLOW_ORIGINS
```

Generate examples:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
openssl rand -hex 32
```

Then run the preflight checker:

```bash
infra/server/preflight.sh
```

The checker fails on missing server secrets, wildcard CORS, unpinned n8n,
missing Google credentials, broken server compose rendering, or missing
backup/migration tooling. Ollama/model availability is reported as a warning so
the script can run before the local model stage.

After deploys or reboots, verify the running stack:

```bash
infra/server/verify_stack.sh
```

## Backups

For a full manual backup run, including Postgres and n8n verification:

```bash
infra/backup/run_all_backups.sh
```

The backup runner also supports an optional off-machine sync step. Set
`OFFSITE_BACKUP_DIR` in `.env` to copy encrypted backup artifacts and n8n
manifests after each successful local backup run.

External drive example:

```bash
OFFSITE_BACKUP_DIR="/Volumes/G-DRIVE/OLS Backups"
```

iCloud Drive example:

```bash
OFFSITE_BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/OLS Backups"
```

If neither path is configured, the off-machine sync step no-ops and local
encrypted backups still run normally. Use one destination first; add a private
target-list file with `OFFSITE_BACKUP_TARGETS_FILE` later if you want both the
external drive and iCloud in the same run.

Individual backup commands are also available:

```bash
infra/backup/backup_postgres.sh
infra/backup/verify_postgres_backup.sh
infra/backup/backup_n8n.sh
infra/backup/verify_n8n_backup.sh
infra/backup/sync_offsite_backups.sh
```

For recurring backups on the Mac mini, install the launchd job:

```bash
infra/backup/install_launchd_backups.sh
```

The launchd job runs `infra/backup/run_all_backups.sh` daily at 03:15 by
default. Override with `START_HOUR` and `START_MINUTE` when installing. Keep
`BACKUP_ENCRYPTION_PASSWORD` in `.env` or a private password-manager-backed
wrapper. Do not commit backup artifacts or passphrases.

The Postgres verifier restores into a disposable verification database:

```bash
infra/backup/verify_postgres_backup.sh infra/backup/out/ols_postgres_YYYYMMDDTHHMMSSZ.sql.gz.enc
```

If no path is passed, the verifier uses the newest backup in
`infra/backup/out/`. It never restores over the production database. Set
`KEEP_RESTORE_VERIFY_DB=true` only when you want to inspect the temporary
database manually.

The n8n backup stops n8n briefly, archives the `n8n_data` Docker volume, then
starts n8n again. It writes a manifest with an `N8N_ENCRYPTION_KEY` fingerprint
but never stores the key itself. Preserve `N8N_ENCRYPTION_KEY` in your password
manager; without it, restored n8n credentials cannot be decrypted.

Verify the archive can be read:

```bash
infra/backup/verify_n8n_backup.sh infra/backup/out/ols_n8n_YYYYMMDDTHHMMSSZ.tar.gz.enc
```

If no path is passed, the verifier uses the newest n8n backup in
`infra/backup/out/`.

## Existing Volume Migrations

`infra/postgres/init.sql` only runs on brand-new Postgres volumes. For existing
volumes, apply idempotent SQL migrations explicitly:

```bash
infra/postgres/apply_migrations.sh
```

The current migration set adds the `llm_audit` table used by the LLM router.

## High-Stakes Mutations

Public/business-facing write routes fail closed by default. After independent
review, call them with both confirmation parameters:

```text
human_confirmed=true
judge_verdict=PASS
```

This applies to direct Shopify/content/lifecycle writes and bulk vision alt-text
pushes. Dry-run endpoints remain available without confirmation.

Historical direct-write scripts under `data/` are a fallback, not the preferred
path. If one must be used, it also requires:

```text
OLS_ALLOW_DATA_MUTATION=1
OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE
```

See [runbooks/data-mutation-scripts.md](runbooks/data-mutation-scripts.md).

## Local LLM Verification

After Ollama and Gemma are installed on the Mac mini, verify the API container
can see the local model host:

```bash
infra/server/verify_local_llm.sh

curl -H "X-API-Key: $OLS_API_KEY" \
  http://localhost:8000/api/llm/local-status
```

Expected `status` is `ok` once both `LOCAL_LLM_MODEL` and
`LOCAL_LLM_LARGE_MODEL` are pulled. `degraded` means Ollama is reachable but one
or more configured models is missing. Set `RUN_GENERATE_CHECK=true` when you
want the verifier to force a real prompt response from both local models. If the
host-side Ollama URL is not `http://127.0.0.1:11434`, set `OLLAMA_VERIFY_URL`.
