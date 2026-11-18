#!/usr/bin/env bash
# ols-dashboard-tunnel.sh — Cloudflare quick tunnel for the OLS dashboard.
#
# Publishes the mini-local dashboard (http://127.0.0.1:3000) over a Cloudflare
# "quick" tunnel so an approved operator can reach it from off-mini without
# exposing a service port on the LAN. Driven by the launchd job
# com.ols.dashboard-tunnel; its plist lives at
# ~/Library/LaunchAgents/com.ols.dashboard-tunnel.plist and is intentionally
# not tracked in this repo.
#
# The quick-tunnel hostname is ephemeral: cloudflared assigns a fresh
# *.trycloudflare.com URL on every (re)start, including after a reboot. The
# current public URL is written to logs/dashboard-public-url.txt and the raw
# cloudflared output is appended to logs/cloudflared-quick.log (both ignored).
set -euo pipefail

# launchd starts jobs with a minimal PATH that omits Homebrew, where cloudflared
# lives on the mini (/opt/homebrew/bin/cloudflared). Prepend the Homebrew bin
# dirs so `command -v cloudflared` resolves under launchd.
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH

LOCAL_URL="http://127.0.0.1:3000"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${REPO_ROOT}/logs"
LOG_FILE="${LOG_DIR}/cloudflared-quick.log"
URL_FILE="${LOG_DIR}/dashboard-public-url.txt"

mkdir -p "${LOG_DIR}"

# The quick-tunnel hostname changes on every (re)start, so clear any address
# left behind by a previous run up front. Until cloudflared prints a fresh
# hostname URL_FILE stays empty rather than advertising a dead URL — including
# when this run exits early without ever publishing one.
: >"${URL_FILE}"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

CLOUDFLARED="$(command -v cloudflared || true)"
if [ -z "${CLOUDFLARED}" ]; then
  echo "$(ts) ERROR cloudflared not found on PATH" >>"${LOG_FILE}"
  exit 127
fi

# Fail closed before exposing anything publicly. A Cloudflare quick tunnel has
# no access control of its own, and the dashboard proxy injects OLS_API_KEY
# into every /api/ request, so publishing it unauthenticated would hand the
# key-gated API (Apply, Shopify publish, ...) to anyone who learns the
# hostname. Only publish once the local dashboard actually demands a credential
# — i.e. answers with an HTTP 401 Basic Auth challenge. Wait briefly for the
# container to come up after a (re)boot before giving up.
for _ in $(seq 1 30); do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "${LOCAL_URL}/" 2>/dev/null || true)"
  if [ "${code}" = "401" ]; then
    break
  fi
  if [ -n "${code}" ] && [ "${code}" != "000" ]; then
    echo "$(ts) ERROR refusing to expose unauthenticated dashboard (HTTP ${code}); enable dashboard HTTP Basic Auth first" >>"${LOG_FILE}"
    exit 1
  fi
  sleep 2
done
if [ "${code:-}" != "401" ]; then
  echo "$(ts) ERROR dashboard did not require authentication on ${LOCAL_URL}; not starting tunnel" >>"${LOG_FILE}"
  exit 1
fi

echo "$(ts) starting quick tunnel -> ${LOCAL_URL}" >>"${LOG_FILE}"

# Run cloudflared in the foreground so launchd owns its lifecycle (KeepAlive
# restarts it on exit or reboot). Stream its output into the shared log and, as
# soon as the assigned *.trycloudflare.com hostname appears, publish it to
# URL_FILE so the operator can look up the current address.
"${CLOUDFLARED}" tunnel --no-autoupdate --url "${LOCAL_URL}" 2>&1 \
  | while IFS= read -r line; do
      printf '%s\n' "${line}" >>"${LOG_FILE}"
      # Capture the assigned quick-tunnel hostname, but skip the cloudflared
      # API host (api.trycloudflare.com) that shows up in failure lines such as
      # a failed POST to https://api.trycloudflare.com/tunnel; it is never the
      # public address and must not overwrite a good one.
      url="$(printf '%s\n' "${line}" \
        | grep -Eo 'https://[A-Za-z0-9.-]+\.trycloudflare\.com' \
        | grep -v '^https://api\.trycloudflare\.com$' \
        | head -n1 || true)"
      if [ -n "${url}" ]; then
        printf '%s\n' "${url}" >"${URL_FILE}"
        echo "$(ts) public URL ${url}" >>"${LOG_FILE}"
      fi
    done
