#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/infra/backup/out}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
N8N_CONTAINER="${N8N_CONTAINER:-ols-n8n}"
N8N_VOLUME_DEST="${N8N_VOLUME_DEST:-/home/node/.n8n}"

STOPPED_N8N=""

cleanup() {
  if [[ "$STOPPED_N8N" == "true" ]]; then
    docker start "$N8N_CONTAINER" >/dev/null 2>&1 || true
  fi
}

n8n_volume_name() {
  docker inspect -f "{{range .Mounts}}{{if eq .Destination \"$N8N_VOLUME_DEST\"}}{{.Name}}{{end}}{{end}}" \
    "$N8N_CONTAINER" 2>/dev/null
}

sha256_string() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum | awk '{print $1}'
  else
    openssl dgst -sha256 -r | awk '{print $1}'
  fi
}

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${N8N_ENCRYPTION_KEY:-}" ]]; then
  echo "ERROR: N8N_ENCRYPTION_KEY is required; n8n backups are not useful without it." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is not available." >&2
  exit 1
fi

trap cleanup EXIT

if ! docker inspect "$N8N_CONTAINER" >/dev/null 2>&1; then
  echo "ERROR: n8n container $N8N_CONTAINER does not exist. Start the stack first." >&2
  exit 1
fi

n8n_volume="$(n8n_volume_name)"
if [[ -z "$n8n_volume" ]]; then
  echo "ERROR: could not find n8n volume mounted at $N8N_VOLUME_DEST." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive_name="ols_n8n_${timestamp}.tar.gz"
plain_backup="$BACKUP_DIR/$archive_name"
encrypted_backup="${plain_backup}.enc"
manifest="$BACKUP_DIR/ols_n8n_${timestamp}.manifest.txt"

if [[ "$(docker inspect -f '{{.State.Running}}' "$N8N_CONTAINER")" == "true" ]]; then
  echo "Stopping n8n briefly for a consistent volume backup..."
  STOPPED_N8N="true"
  docker stop "$N8N_CONTAINER" >/dev/null
fi

echo "Creating n8n volume backup from Docker volume $n8n_volume..."
docker run --rm \
  -v "$n8n_volume:/data:ro" \
  -v "$BACKUP_DIR:/backup" \
  alpine:3.20 \
  sh -c "cd /data && tar -czf /backup/$archive_name ."

key_fingerprint="$(printf '%s' "$N8N_ENCRYPTION_KEY" | sha256_string)"
{
  echo "created_at=$timestamp"
  echo "container=$N8N_CONTAINER"
  echo "volume=$n8n_volume"
  echo "volume_dest=$N8N_VOLUME_DEST"
  echo "n8n_encryption_key_sha256=$key_fingerprint"
  echo "note=N8N_ENCRYPTION_KEY itself is not stored here; preserve it separately."
} > "$manifest"

if [[ -n "${BACKUP_ENCRYPTION_PASSWORD:-}" ]]; then
  openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 \
    -in "$plain_backup" \
    -out "$encrypted_backup" \
    -pass env:BACKUP_ENCRYPTION_PASSWORD
  rm "$plain_backup"
  echo "Encrypted n8n backup written to $encrypted_backup"
else
  echo "WARNING: BACKUP_ENCRYPTION_PASSWORD is not set; n8n backup is unencrypted."
  echo "Unencrypted n8n backup written to $plain_backup"
fi

echo "n8n backup manifest written to $manifest"
find "$BACKUP_DIR" -type f -name "ols_n8n_*.tar.gz*" -mtime "+$BACKUP_RETENTION_DAYS" -delete
find "$BACKUP_DIR" -type f -name "ols_n8n_*.manifest.txt" -mtime "+$BACKUP_RETENTION_DAYS" -delete
