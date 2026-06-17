#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.server.yml}"
CREDENTIALS_FILE="${GOOGLE_CREDENTIALS_FILE:-$ROOT_DIR/credentials/google-service-account.json}"

failures=0
warnings=0

fail() {
  failures=$((failures + 1))
  printf 'FAIL: %s\n' "$1"
}

warn() {
  warnings=$((warnings + 1))
  printf 'WARN: %s\n' "$1"
}

pass() {
  printf 'PASS: %s\n' "$1"
}

load_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    fail ".env not found at $ENV_FILE"
    return
  fi

  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  pass "loaded .env"
}

value_is_placeholder() {
  local value="${1:-}"
  [[ -z "$value" || "$value" == "CHANGE_ME" || "$value" == "YOUR_"*"_HERE" ]]
}

require_secret() {
  local name="$1"
  local value="${!name:-}"
  if value_is_placeholder "$value"; then
    fail "$name is missing or still a placeholder"
  else
    pass "$name is set"
  fi
}

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    printf 'docker compose'
  elif command -v docker-compose >/dev/null 2>&1; then
    printf 'docker-compose'
  else
    return 1
  fi
}

check_compose_config() {
  local cmd
  if ! cmd="$(compose_cmd)"; then
    fail "Docker Compose is not available"
    return
  fi

  # shellcheck disable=SC2086
  if $cmd -f "$COMPOSE_FILE" config --quiet >/dev/null 2>&1; then
    pass "server compose renders"
  else
    fail "server compose does not render"
  fi
}

check_ollama_model() {
  local model="$1"
  if [[ -z "$model" ]]; then
    warn "local model variable is empty"
    return
  fi
  if ! command -v ollama >/dev/null 2>&1; then
    warn "ollama is not installed yet; skip model check for $model"
    return
  fi
  if ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$model"; then
    pass "ollama model available: $model"
  else
    warn "ollama model not pulled yet: $model"
  fi
}

load_env

if [[ -f "$ENV_FILE" ]]; then
  require_secret POSTGRES_PASSWORD
  require_secret SECRET_KEY
  require_secret OLS_API_KEY
  require_secret N8N_BASIC_AUTH_PASSWORD
  require_secret N8N_ENCRYPTION_KEY
  require_secret BACKUP_ENCRYPTION_PASSWORD

  if [[ "${CORS_ALLOW_ORIGINS:-*}" == "*" ]]; then
    fail "CORS_ALLOW_ORIGINS is wildcard; pin it for server deploy"
  else
    pass "CORS_ALLOW_ORIGINS is pinned"
  fi

  if [[ "${N8N_IMAGE:-}" == *":latest" || -z "${N8N_IMAGE:-}" ]]; then
    fail "N8N_IMAGE must be pinned, not latest/empty"
  else
    pass "N8N_IMAGE is pinned to ${N8N_IMAGE}"
  fi

  check_ollama_model "${LOCAL_LLM_MODEL:-gemma4:12b}"
  check_ollama_model "${LOCAL_LLM_LARGE_MODEL:-gemma4:31b}"
fi

if [[ -f "$CREDENTIALS_FILE" ]]; then
  pass "Google service-account credential file exists"
else
  fail "Google service-account credential file missing at $CREDENTIALS_FILE"
fi

if [[ -x "$ROOT_DIR/infra/backup/backup_postgres.sh" ]]; then
  pass "Postgres backup script is executable"
else
  fail "Postgres backup script missing or not executable"
fi

if [[ -x "$ROOT_DIR/infra/backup/verify_postgres_backup.sh" ]]; then
  pass "Postgres backup restore verifier is executable"
else
  fail "Postgres backup restore verifier missing or not executable"
fi

if [[ -x "$ROOT_DIR/infra/backup/backup_n8n.sh" ]]; then
  pass "n8n backup script is executable"
else
  fail "n8n backup script missing or not executable"
fi

if [[ -x "$ROOT_DIR/infra/backup/verify_n8n_backup.sh" ]]; then
  pass "n8n backup verifier is executable"
else
  fail "n8n backup verifier missing or not executable"
fi

if [[ -x "$ROOT_DIR/infra/backup/run_all_backups.sh" ]]; then
  pass "combined backup runner is executable"
else
  fail "combined backup runner missing or not executable"
fi

if [[ -x "$ROOT_DIR/infra/backup/install_launchd_backups.sh" ]]; then
  pass "launchd backup installer is executable"
else
  fail "launchd backup installer missing or not executable"
fi

if [[ -x "$ROOT_DIR/infra/postgres/apply_migrations.sh" ]]; then
  pass "migration runner is executable"
else
  fail "migration runner missing or not executable"
fi

if [[ -x "$ROOT_DIR/infra/server/deploy_server.sh" ]]; then
  pass "server deploy script is executable"
else
  fail "server deploy script missing or not executable"
fi

if [[ -x "$ROOT_DIR/infra/server/verify_stack.sh" ]]; then
  pass "server stack verifier is executable"
else
  fail "server stack verifier missing or not executable"
fi

if [[ -x "$ROOT_DIR/infra/server/verify_local_llm.sh" ]]; then
  pass "local LLM verifier is executable"
else
  fail "local LLM verifier missing or not executable"
fi

if compgen -G "$ROOT_DIR/infra/postgres/migrations/*.sql" >/dev/null; then
  pass "SQL migrations are present"
else
  warn "no SQL migrations found"
fi

check_compose_config

printf '\nPreflight complete: %s failure(s), %s warning(s).\n' "$failures" "$warnings"
if [[ "$failures" -gt 0 ]]; then
  exit 1
fi
