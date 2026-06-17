#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.server.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/infra/backup/out}"
KEEP_RESTORE_VERIFY_DB="${KEEP_RESTORE_VERIFY_DB:-false}"

COMPOSE_CMD=()
TEMP_PLAIN_BACKUP=""
VERIFY_DB_CREATED=""

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

cleanup() {
  if [[ -n "$TEMP_PLAIN_BACKUP" && -f "$TEMP_PLAIN_BACKUP" ]]; then
    rm -f "$TEMP_PLAIN_BACKUP"
  fi

  if [[ -n "$VERIFY_DB_CREATED" && "$KEEP_RESTORE_VERIFY_DB" != "true" ]]; then
    "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T postgres \
      dropdb --if-exists --force -U "$POSTGRES_USER" "$VERIFY_DB" >/dev/null 2>&1 || true
  fi
}

latest_backup() {
  find "$BACKUP_DIR" -type f \
    \( -name "ols_postgres_*.sql.gz" -o -name "ols_postgres_*.sql.gz.enc" \) \
    -print 2>/dev/null | sort | tail -n 1
}

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-ols_user}"
POSTGRES_DB="${POSTGRES_DB:-ols_db}"
VERIFY_DB="${VERIFY_DB:-ols_restore_verify_$(date -u +%Y%m%dT%H%M%SZ)_$$}"
BACKUP_FILE="${1:-}"

if [[ -z "$BACKUP_FILE" ]]; then
  BACKUP_FILE="$(latest_backup)"
fi

if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "ERROR: backup file not found. Pass a path or create one in $BACKUP_DIR." >&2
  exit 1
fi

compose_cmd
trap cleanup EXIT

plain_backup="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.enc ]]; then
  if [[ -z "${BACKUP_ENCRYPTION_PASSWORD:-}" ]]; then
    echo "ERROR: BACKUP_ENCRYPTION_PASSWORD is required to verify encrypted backups." >&2
    exit 1
  fi

  TEMP_PLAIN_BACKUP="$(mktemp "${TMPDIR:-/tmp}/ols_restore_verify.XXXXXX.sql.gz")"
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
    -in "$BACKUP_FILE" \
    -out "$TEMP_PLAIN_BACKUP" \
    -pass env:BACKUP_ENCRYPTION_PASSWORD
  plain_backup="$TEMP_PLAIN_BACKUP"
fi

echo "Checking backup archive..."
gzip -t "$plain_backup"

echo "Creating disposable restore database $VERIFY_DB..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T postgres \
  dropdb --if-exists --force -U "$POSTGRES_USER" "$VERIFY_DB" >/dev/null 2>&1 || true
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T postgres \
  createdb -U "$POSTGRES_USER" "$VERIFY_DB"
VERIFY_DB_CREATED="true"

echo "Restoring backup into $VERIFY_DB..."
gzip -dc "$plain_backup" | "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$VERIFY_DB" >/dev/null

table_count="$("${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T postgres \
  psql -Atqc "select count(*) from information_schema.tables where table_schema not in ('pg_catalog','information_schema');" \
    -U "$POSTGRES_USER" -d "$VERIFY_DB")"

echo "Restore verification succeeded for $BACKUP_FILE"
echo "Restored schema table count: $table_count"

if [[ "$KEEP_RESTORE_VERIFY_DB" == "true" ]]; then
  echo "Keeping disposable database for inspection: $VERIFY_DB"
fi
