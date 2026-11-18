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

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

CLOUDFLARED="$(command -v cloudflared || true)"
if [ -z "${CLOUDFLARED}" ]; then
  echo "$(ts) ERROR cloudflared not found on PATH" >>"${LOG_FILE}"
  exit 127
fi

echo "$(ts) starting quick tunnel -> ${LOCAL_URL}" >>"${LOG_FILE}"

# Run cloudflared in the foreground so launchd owns its lifecycle (KeepAlive
# restarts it on exit or reboot). Stream its output into the shared log and, as
# soon as the assigned *.trycloudflare.com hostname appears, publish it to
# URL_FILE so the operator can look up the current address.
"${CLOUDFLARED}" tunnel --no-autoupdate --url "${LOCAL_URL}" 2>&1 \
  | while IFS= read -r line; do
      printf '%s\n' "${line}" >>"${LOG_FILE}"
      url="$(printf '%s\n' "${line}" \
        | grep -Eo 'https://[A-Za-z0-9.-]+\.trycloudflare\.com' \
        | head -n1 || true)"
      if [ -n "${url}" ]; then
        printf '%s\n' "${url}" >"${URL_FILE}"
        echo "$(ts) public URL ${url}" >>"${LOG_FILE}"
      fi
    done
