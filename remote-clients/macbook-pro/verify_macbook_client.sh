#!/usr/bin/env bash
set -euo pipefail

HOST_ALIAS="${HOST_ALIAS:-ols-mini}"
REMOTE_REPO="${REMOTE_REPO:-/Users/aiagentecosystem/services/ols}"

pass() {
  printf 'PASS: %s\n' "$1"
}

warn() {
  printf 'WARN: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

if command -v tailscale >/dev/null 2>&1; then
  pass "tailscale command is installed"
  if tailscale status >/dev/null 2>&1; then
    pass "tailscale status is available"
  else
    warn "tailscale is installed but status failed; sign in or start Tailscale"
  fi
else
  warn "tailscale command not found; install/sign into Tailscale before off-network use"
fi

if [[ -f "$HOME/.ssh/id_ed25519" && -f "$HOME/.ssh/id_ed25519.pub" ]]; then
  pass "default ed25519 SSH key exists"
else
  warn "default ed25519 SSH key not found; run ssh-keygen before connecting"
fi

ssh -o BatchMode=yes "$HOST_ALIAS" "cd '$REMOTE_REPO' && printf 'host=%s\n' \"\$(hostname)\" && printf 'pwd=%s\n' \"\$(pwd)\" && printf 'branch=%s\n' \"\$(git branch --show-current)\" && printf 'head=%s\n' \"\$(git rev-parse HEAD)\" && git status --short" \
  || fail "SSH to $HOST_ALIAS failed. Check Tailscale/MagicDNS, ~/.ssh/config, and authorized_keys."

pass "SSH reached mini live repo"

ssh -o BatchMode=yes "$HOST_ALIAS" "cd '$REMOTE_REPO' && ./infra/server/verify_stack.sh" \
  || fail "remote stack verification failed"

pass "remote stack verification passed"

echo
echo "If your SSH config has LocalForward entries and this script was run through that alias,"
echo "open these MacBook URLs:"
echo "  dashboard: http://localhost:3000"
echo "  API docs:  http://localhost:8000/docs"
echo "  n8n:       http://localhost:5678"

