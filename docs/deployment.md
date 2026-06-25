# Deployment

## Canonical Checkout

Run local Docker commands from:

```bash
/Users/robertporter/organizing-life-services-ai
```

This is the git-tracked source of truth for the laptop stack. Keep runtime
secrets in the git-ignored local files below:

```text
.env
credentials/google-service-account.json
```

## Laptop Development

For normal local development:

```bash
cd /Users/robertporter/organizing-life-services-ai
docker compose up -d --build
```

When only the API or dashboard changed:

```bash
docker compose up -d --build api dashboard
```

Verify:

```bash
curl -sf http://localhost:8000/health/ready
docker ps --format '{{.Names}}\t{{.Status}}'
```

The current Compose project name resolves to `organizing-life-services-ai`, so
the Postgres volume is reused as:

```text
organizing-life-services-ai_postgres_data
```

If the checkout path ever changes, keep the same folder basename or set
`COMPOSE_PROJECT_NAME=organizing-life-services-ai` to avoid creating a new
empty volume by accident.

## Runtime Notes

- Automated health checks should use `GET /health/live` and `GET /health/ready`.
- The dashboard container reads `OLS_API_KEY` from `.env` and injects it at the
  nginx proxy layer. Do not hardcode the key in frontend source files.
- To run the backend test suite without modifying the runtime image, use
  `./scripts/run_tests_in_docker.sh`.

## Secret Hygiene

- Rotate any credential found in tracked files before rewriting history.
- Current-tree docs and dashboard source are scrubbed; archived raw
  conversation exports remain excluded from automated secret scanning until the
  coordinated history cleanup is complete.
- Use the prep kit in `security/history-scrub/` before any `git filter-repo`
  rewrite. Keep the replacement manifest in the gitignored `*.local.*` files
  there, and run the actual rewrite in a fresh mirror clone.
- Existing clones will need to re-clone or hard-reset after a history rewrite.

## Mac Mini Server

Use the server compose file on the always-on Mac mini:

```bash
docker compose -f docker-compose.server.yml up -d --build
```

Prefer connecting to the mini by mDNS name instead of a changing DHCP address:

```bash
ssh aiagentecosystem@agent-eco-mini.local
```

The preferred setup-day command is:

```bash
infra/server/deploy_server.sh
```

It creates required local directories, runs preflight, starts the server stack,
applies SQL migrations, and runs the stack verifier.

Server behavior:

- FastAPI runs without the development reloader by default.
- Postgres is not published to the host network.
- API, dashboard, and n8n bind to `127.0.0.1` by default.
- n8n expects a stable `N8N_ENCRYPTION_KEY`.

## Server Preflight

Before first server deploy, set unique values in `.env`:

```text
POSTGRES_PASSWORD
SECRET_KEY
OLS_API_KEY
N8N_ENCRYPTION_KEY
BACKUP_ENCRYPTION_PASSWORD
FASTAPI_ENV=production
CORS_ALLOW_ORIGINS
```

Then run:

```bash
infra/server/preflight.sh
infra/server/verify_stack.sh
```

## Backups

For a full manual backup run, including Postgres and n8n verification:

```bash
infra/backup/run_all_backups.sh
```

Useful individual commands:

```bash
infra/backup/backup_postgres.sh
infra/backup/verify_postgres_backup.sh
infra/backup/backup_n8n.sh
infra/backup/verify_n8n_backup.sh
infra/backup/sync_offsite_backups.sh
```

Install the recurring launchd job on the mini with:

```bash
infra/backup/install_launchd_backups.sh
```

## Existing Volume Migrations

`infra/postgres/init.sql` only runs on brand-new Postgres volumes. For existing
volumes, apply idempotent SQL migrations explicitly:

```bash
infra/postgres/apply_migrations.sh
```

## High-Stakes Mutations

Public/business-facing write routes fail closed by default. After independent
review, call them with both confirmation parameters:

```text
human_confirmed=true
judge_verdict=PASS
```

This applies to direct Shopify/content/lifecycle writes and bulk vision
alt-text pushes.
