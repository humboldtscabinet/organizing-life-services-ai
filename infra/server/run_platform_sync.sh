#!/usr/bin/env bash
# Wait for ols-api, then run scheduled_platform_sync.py inside the container.
# Intended for launchd: com.ols.platform-sync.daily / .weekly
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
LOG_DIR="${PLATFORM_SYNC_LOG_DIR:-$ROOT_DIR/infra/server/out}"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:${FASTAPI_PORT:-8000}/health/ready}"
WAIT_SECONDS="${WAIT_SECONDS:-60}"
CONTAINER="${OLS_API_CONTAINER:-ols-api}"

mkdir -p "$LOG_DIR"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:${FASTAPI_PORT:-8000}/health/ready}"
fi

deadline=$((SECONDS + WAIT_SECONDS))
until curl -sf --max-time 5 "$API_HEALTH_URL" >/dev/null 2>&1; do
  if [[ "$SECONDS" -ge "$deadline" ]]; then
    echo "ERROR: $CONTAINER was not ready at $API_HEALTH_URL within ${WAIT_SECONDS}s" >&2
    exit 1
  fi
  sleep 2
done

exec docker exec "$CONTAINER" python /app/scripts/scheduled_platform_sync.py "$@"
