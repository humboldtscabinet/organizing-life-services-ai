#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
OLLAMA_VERIFY_URL="${OLLAMA_VERIFY_URL:-http://127.0.0.1:11434}"
FASTAPI_PORT="${FASTAPI_PORT:-8000}"
RUN_GENERATE_CHECK="${RUN_GENERATE_CHECK:-false}"

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
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  else
    warn ".env not found at $ENV_FILE; using local defaults"
  fi
}

check_model_listed() {
  local model="$1"
  if ollama list 2>/dev/null | awk 'NR > 1 {print $1}' | grep -qx "$model"; then
    pass "Ollama model is pulled: $model"
  else
    fail "Ollama model is missing: $model"
  fi
}

check_generate() {
  local model="$1"
  local body

  body="$(printf '{"model":"%s","prompt":"Reply with exactly: ok","stream":false}' "$model" \
    | curl -sS --max-time 120 -H 'Content-Type: application/json' \
      -d @- "${OLLAMA_VERIFY_URL%/}/api/generate" 2>/dev/null || true)"

  if printf '%s' "$body" | grep -q '"response"'; then
    pass "Ollama generated a response with $model"
  else
    fail "Ollama did not generate a response with $model"
  fi
}

check_api_container_status() {
  local body
  local code

  if [[ -z "${OLS_API_KEY:-}" || "${OLS_API_KEY:-}" == "CHANGE_ME" ]]; then
    warn "OLS_API_KEY is not set; skipping API /api/llm/local-status check"
    return
  fi

  body="$(mktemp "${TMPDIR:-/tmp}/ols_llm_status.XXXXXX")"
  code="$(curl -sS -o "$body" -w '%{http_code}' --max-time 10 \
    -H "X-API-Key: $OLS_API_KEY" \
    "http://127.0.0.1:${FASTAPI_PORT}/api/llm/local-status" 2>/dev/null || true)"

  if [[ "$code" != "200" ]]; then
    warn "API /api/llm/local-status not reachable or unauthorized; HTTP ${code:-none}"
    rm -f "$body"
    return
  fi

  if grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' "$body"; then
    pass "API container reports local LLM status ok"
  else
    fail "API container reached Ollama but local LLM status is not ok: $(cat "$body")"
  fi
  rm -f "$body"
}

load_env
LOCAL_LLM_MODEL="${LOCAL_LLM_MODEL:-gemma4:12b}"
LOCAL_LLM_LARGE_MODEL="${LOCAL_LLM_LARGE_MODEL:-gemma4:31b}"
OLLAMA_VERIFY_URL="${OLLAMA_VERIFY_URL:-http://127.0.0.1:11434}"

if ! command -v ollama >/dev/null 2>&1; then
  fail "ollama is not installed"
else
  pass "ollama command is installed"
  if curl -sS --max-time 5 "${OLLAMA_VERIFY_URL%/}/api/tags" >/dev/null 2>&1; then
    pass "Ollama API is reachable at $OLLAMA_VERIFY_URL"
  else
    fail "Ollama API is not reachable at $OLLAMA_VERIFY_URL"
  fi

  check_model_listed "$LOCAL_LLM_MODEL"
  check_model_listed "$LOCAL_LLM_LARGE_MODEL"

  if [[ "$RUN_GENERATE_CHECK" == "true" ]]; then
    check_generate "$LOCAL_LLM_MODEL"
    check_generate "$LOCAL_LLM_LARGE_MODEL"
  else
    warn "generation test skipped; set RUN_GENERATE_CHECK=true to force a prompt response check"
  fi
fi

check_api_container_status

printf '\nLocal LLM verification complete: %s failure(s), %s warning(s).\n' "$failures" "$warnings"
if [[ "$failures" -gt 0 ]]; then
  exit 1
fi
