#!/usr/bin/env bash
set -euo pipefail

MINI_HOST="${MINI_HOST:-agent-eco-mini.local}"
MINI_USER="${MINI_USER:-aiagentecosystem}"
PUBLIC_KEY_FILE="${PUBLIC_KEY_FILE:-$HOME/.ssh/id_ed25519.pub}"

if [[ ! -f "$PUBLIC_KEY_FILE" ]]; then
  echo "Missing public key: $PUBLIC_KEY_FILE" >&2
  echo "Create one with: ssh-keygen -t ed25519 -C \"macbook-pro-to-agent-eco-mini\"" >&2
  exit 1
fi

public_key="$(tr -d '\r\n' < "$PUBLIC_KEY_FILE")"

if [[ -z "$public_key" ]]; then
  echo "Public key file is empty: $PUBLIC_KEY_FILE" >&2
  exit 1
fi

printf '%s\n' "$public_key" | ssh "${MINI_USER}@${MINI_HOST}" 'zsh -lc '\''
read -r public_key
umask 077
mkdir -p ~/.ssh
touch ~/.ssh/authorized_keys
if ! grep -qxF "$public_key" ~/.ssh/authorized_keys; then
  printf "%s\n" "$public_key" >> ~/.ssh/authorized_keys
fi
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
'\'''

echo "Installed public key on ${MINI_USER}@${MINI_HOST}"
