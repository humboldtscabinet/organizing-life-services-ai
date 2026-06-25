#!/usr/bin/env bash
set -euo pipefail

MINI_HOST="${MINI_HOST:-agent-eco-mini.local}"
MINI_USER="${MINI_USER:-aiagentecosystem}"

ssh -t "${MINI_USER}@${MINI_HOST}" 'zsh -lc '\''
set -euo pipefail
echo "Applying headless power settings. macOS may ask for the mini admin password."
sudo pmset -a sleep 0 displaysleep 0 disksleep 0
sudo pmset autorestart 1
echo
echo "Updated pmset state:"
pmset -g custom | sed -n "1,120p"
'\'''

