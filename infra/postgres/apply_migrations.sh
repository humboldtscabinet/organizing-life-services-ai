#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.server.yml}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-$ROOT_DIR/infra/postgres/migrations}"

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

if [[ ! -d "$MIGRATIONS_DIR" ]]; then
  echo "No migrations directory found at $MIGRATIONS_DIR"
  exit 0
fi

shopt -s nullglob
migrations=("$MIGRATIONS_DIR"/*.sql)
if [[ ${#migrations[@]} -eq 0 ]]; then
  echo "No SQL migrations found."
  exit 0
fi

compose_cmd

for migration in "${migrations[@]}"; do
  echo "Applying $(basename "$migration")..."
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T postgres \
    psql -v ON_ERROR_STOP=1 \
      -U "${POSTGRES_USER:-ols_user}" \
      -d "${POSTGRES_DB:-ols_db}" < "$migration"
done

echo "Migrations complete."
