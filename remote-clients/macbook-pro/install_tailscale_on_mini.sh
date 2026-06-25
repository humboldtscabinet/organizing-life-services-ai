#!/usr/bin/env bash
set -euo pipefail

MINI_HOST="${MINI_HOST:-agent-eco-mini.local}"
MINI_USER="${MINI_USER:-aiagentecosystem}"

ssh -t "${MINI_USER}@${MINI_HOST}" 'zsh -lc '\''
set -euo pipefail
if command -v tailscale >/dev/null 2>&1; then
  echo "Tailscale CLI is already installed at $(command -v tailscale)"
else
  echo "Installing Tailscale. macOS may ask for the mini admin password."
  brew install --cask tailscale-app
fi

open -a Tailscale || true
echo
echo "Next on the mini:"
echo "1. Finish Tailscale sign-in."
echo "2. Approve any System Settings > Privacy & Security prompt."
echo "3. Enable MagicDNS in the Tailscale admin console."
echo
echo "Then verify from a client with:"
echo "  HOST_ALIAS=ols-mini ./verify_mini_headless_state.sh"
'\'''

