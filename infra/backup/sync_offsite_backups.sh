#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/infra/backup/out}"
OFFSITE_BACKUP_TARGETS_FILE="${OFFSITE_BACKUP_TARGETS_FILE:-}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

targets=()
if [[ -n "${OFFSITE_BACKUP_DIR:-}" ]]; then
  targets+=("$OFFSITE_BACKUP_DIR")
fi

if [[ -n "$OFFSITE_BACKUP_TARGETS_FILE" && -f "$OFFSITE_BACKUP_TARGETS_FILE" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    targets+=("$line")
  done < "$OFFSITE_BACKUP_TARGETS_FILE"
fi

if [[ "${#targets[@]}" -eq 0 ]]; then
  echo "No off-machine backup target configured; set OFFSITE_BACKUP_DIR to enable sync."
  exit 0
fi

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "ERROR: backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "ERROR: rsync is required for off-machine backup sync." >&2
  exit 1
fi

for target in "${targets[@]}"; do
  mkdir -p "$target"
  if [[ ! -w "$target" ]]; then
    echo "ERROR: off-machine backup target is not writable: $target" >&2
    exit 1
  fi

  echo "Syncing encrypted backup artifacts to $target..."
  rsync -a \
    --include='*/' \
    --include='*.enc' \
    --include='*.manifest.txt' \
    --exclude='*' \
    "$BACKUP_DIR"/ "$target"/
done

echo "Off-machine backup sync complete."
