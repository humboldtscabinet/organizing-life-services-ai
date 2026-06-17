#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.server.yml}"
SKIP_PREFLIGHT="${SKIP_PREFLIGHT:-false}"
SKIP_MIGRATIONS="${SKIP_MIGRATIONS:-false}"
SKIP_VERIFY="${SKIP_VERIFY:-false}"

COMPOSE_CMD=()

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
  else
    echo "ERROR: Docker Compose is not available." >&2
    exit 1
  fi
}

cd "$ROOT_DIR"
mkdir -p data credentials
compose_cmd

if [[ "$SKIP_PREFLIGHT" != "true" ]]; then
  infra/server/preflight.sh
fi

echo "Building and starting OLS server stack..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d --build

if [[ "$SKIP_MIGRATIONS" != "true" ]]; then
  infra/postgres/apply_migrations.sh
fi

if [[ "$SKIP_VERIFY" != "true" ]]; then
  infra/server/verify_stack.sh
fi

cat <<'MSG'

Deploy complete.

Next setup-day gates:
1. Run infra/backup/backup_postgres.sh and infra/backup/verify_postgres_backup.sh.
2. Run infra/backup/backup_n8n.sh and infra/backup/verify_n8n_backup.sh.
3. Pull local Gemma models, then run infra/server/verify_local_llm.sh.
4. Reboot the mini and run infra/server/verify_stack.sh again.
MSG
