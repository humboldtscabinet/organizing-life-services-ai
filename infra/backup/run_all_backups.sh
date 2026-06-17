#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERIFY_BACKUPS_AFTER_CREATE="${VERIFY_BACKUPS_AFTER_CREATE:-true}"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$HOME/.orbstack/bin:$PATH"

cd "$ROOT_DIR"

echo "Starting OLS backup run..."
infra/backup/backup_postgres.sh

if [[ "$VERIFY_BACKUPS_AFTER_CREATE" == "true" ]]; then
  infra/backup/verify_postgres_backup.sh
fi

infra/backup/backup_n8n.sh

if [[ "$VERIFY_BACKUPS_AFTER_CREATE" == "true" ]]; then
  infra/backup/verify_n8n_backup.sh
fi

echo "OLS backup run complete."
