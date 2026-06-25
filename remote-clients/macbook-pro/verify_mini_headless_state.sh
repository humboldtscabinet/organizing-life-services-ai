#!/usr/bin/env bash
set -euo pipefail

HOST_ALIAS="${HOST_ALIAS:-ols-mini}"

ssh "$HOST_ALIAS" 'zsh -lc '\''
echo "computer_name=$(scutil --get ComputerName 2>/dev/null || true)"
echo "hostname=$(hostname)"
echo "tailscale_bin=$(command -v tailscale || true)"
if command -v tailscale >/dev/null 2>&1; then
  tailscale status 2>/dev/null | sed -n "1,12p" || true
fi
fdesetup status 2>/dev/null || true
pmset -g custom 2>/dev/null | sed -n "1,120p" || true
echo "remote_login=$(systemsetup -getremotelogin 2>/dev/null || true)"
cd /Users/aiagentecosystem/services/ols
./infra/server/verify_stack.sh
'\'''

