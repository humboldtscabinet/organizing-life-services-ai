#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/infra/backup/out}"

TEMP_PLAIN_BACKUP=""
TEMP_LIST=""

cleanup() {
  if [[ -n "$TEMP_PLAIN_BACKUP" && -f "$TEMP_PLAIN_BACKUP" ]]; then
    rm -f "$TEMP_PLAIN_BACKUP"
  fi
  if [[ -n "$TEMP_LIST" && -f "$TEMP_LIST" ]]; then
    rm -f "$TEMP_LIST"
  fi
}

latest_backup() {
  find "$BACKUP_DIR" -type f \
    \( -name "ols_n8n_*.tar.gz" -o -name "ols_n8n_*.tar.gz.enc" \) \
    -print 2>/dev/null | sort | tail -n 1
}

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" ]]; then
  BACKUP_FILE="$(latest_backup)"
fi

if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "ERROR: n8n backup file not found. Pass a path or create one in $BACKUP_DIR." >&2
  exit 1
fi

trap cleanup EXIT

plain_backup="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.enc ]]; then
  if [[ -z "${BACKUP_ENCRYPTION_PASSWORD:-}" ]]; then
    echo "ERROR: BACKUP_ENCRYPTION_PASSWORD is required to verify encrypted backups." >&2
    exit 1
  fi

  TEMP_PLAIN_BACKUP="$(mktemp "${TMPDIR:-/tmp}/ols_n8n_verify.XXXXXX.tar.gz")"
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
    -in "$BACKUP_FILE" \
    -out "$TEMP_PLAIN_BACKUP" \
    -pass env:BACKUP_ENCRYPTION_PASSWORD
  plain_backup="$TEMP_PLAIN_BACKUP"
fi

echo "Checking n8n backup archive..."
TEMP_LIST="$(mktemp "${TMPDIR:-/tmp}/ols_n8n_verify.XXXXXX.list")"
tar -tzf "$plain_backup" > "$TEMP_LIST"

entry_count="$(wc -l < "$TEMP_LIST" | tr -d ' ')"
if [[ "$entry_count" -eq 0 ]]; then
  echo "ERROR: n8n backup archive is empty." >&2
  exit 1
fi

echo "n8n backup verification succeeded for $BACKUP_FILE"
echo "Archive entries: $entry_count"

if grep -qx "./database.sqlite" "$TEMP_LIST"; then
  echo "Found n8n SQLite database in archive."
else
  echo "WARNING: ./database.sqlite was not found; this may be expected if n8n uses an external DB."
fi
