#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.server.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/infra/backup/out}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

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

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-ols_user}"
POSTGRES_DB="${POSTGRES_DB:-ols_db}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
plain_backup="$BACKUP_DIR/ols_postgres_${timestamp}.sql.gz"
encrypted_backup="${plain_backup}.enc"

mkdir -p "$BACKUP_DIR"
compose_cmd

echo "Creating Postgres backup from $POSTGRES_DB..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "$plain_backup"

if [[ -n "${BACKUP_ENCRYPTION_PASSWORD:-}" ]]; then
  openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 \
    -in "$plain_backup" \
    -out "$encrypted_backup" \
    -pass env:BACKUP_ENCRYPTION_PASSWORD
  rm "$plain_backup"
  echo "Encrypted backup written to $encrypted_backup"
else
  echo "WARNING: BACKUP_ENCRYPTION_PASSWORD is not set; backup is unencrypted."
  echo "Unencrypted backup written to $plain_backup"
fi

find "$BACKUP_DIR" -type f -name "ols_postgres_*.sql.gz*" -mtime "+$BACKUP_RETENTION_DAYS" -delete
