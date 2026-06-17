#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.server.yml}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"

COMPOSE_CMD=()
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

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
  else
    fail "Docker Compose is not available"
    return 1
  fi
}

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  else
    warn ".env not found at $ENV_FILE; using compose defaults where possible"
  fi
}

container_for_service() {
  local service="$1"
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null || true
}

check_container() {
  local service="$1"
  local container="$2"
  local id
  local running
  local health

  id="$(container_for_service "$service")"
  if [[ -z "$id" ]]; then
    fail "$service container is missing"
    return
  fi

  running="$(docker inspect -f '{{.State.Running}}' "$id" 2>/dev/null || true)"
  if [[ "$running" == "true" ]]; then
    pass "$service container is running"
  else
    fail "$service container is not running"
  fi

  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id" 2>/dev/null || true)"
  case "$health" in
    healthy) pass "$service healthcheck is healthy" ;;
    none) warn "$service has no healthcheck" ;;
    *) fail "$service healthcheck is $health" ;;
  esac

  if [[ -n "$container" ]]; then
    local named_id
    named_id="$(docker inspect -f '{{.Id}}' "$container" 2>/dev/null || true)"
    if [[ -n "$named_id" && "$id" == "$named_id" ]]; then
      pass "$service uses expected container name $container"
    else
      warn "$service is running but container name differs from $container"
    fi
  fi
}

check_localhost_binding() {
  local container="$1"
  local port="$2"
  local binding

  binding="$(docker port "$container" "$port/tcp" 2>/dev/null || true)"
  if [[ -z "$binding" ]]; then
    fail "$container does not publish $port/tcp"
    return
  fi

  if printf '%s\n' "$binding" | grep -qv '^127\.0\.0\.1:'; then
    fail "$container publishes $port/tcp outside localhost: $binding"
  else
    pass "$container publishes $port/tcp on localhost only"
  fi
}

check_not_published() {
  local container="$1"
  local binding

  binding="$(docker port "$container" 2>/dev/null || true)"
  if [[ -z "$binding" ]]; then
    pass "$container has no published host ports"
  else
    fail "$container unexpectedly publishes host ports: $binding"
  fi
}

wait_for_http_codes() {
  local name="$1"
  local url="$2"
  local allowed_codes="$3"
  local code
  local deadline=$((SECONDS + TIMEOUT_SECONDS))

  while [[ "$SECONDS" -lt "$deadline" ]]; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$url" 2>/dev/null || true)"
    case " $allowed_codes " in
      *" $code "*)
      pass "$name reachable at $url with HTTP $code"
      return
      ;;
    esac
    sleep 3
  done

  fail "$name was not reachable at $url within ${TIMEOUT_SECONDS}s; last HTTP code: ${code:-none}"
}

load_env
compose_cmd || true

if [[ ${#COMPOSE_CMD[@]} -gt 0 ]]; then
  check_container postgres ols-postgres
  check_container api ols-api
  check_container dashboard ols-dashboard
  check_container n8n ols-n8n

  check_not_published ols-postgres
  check_localhost_binding ols-api 8000
  check_localhost_binding ols-dashboard 80
  check_localhost_binding ols-n8n 5678

  wait_for_http_codes "API health" "http://127.0.0.1:${FASTAPI_PORT:-8000}/health" "200"
  wait_for_http_codes "dashboard" "http://127.0.0.1:${DASHBOARD_PORT:-3000}" "200 301 302"
  wait_for_http_codes "n8n" "http://127.0.0.1:${N8N_PORT:-5678}" "200 301 302 401"
fi

printf '\nStack verification complete: %s failure(s), %s warning(s).\n' "$failures" "$warnings"
if [[ "$failures" -gt 0 ]]; then
  exit 1
fi
