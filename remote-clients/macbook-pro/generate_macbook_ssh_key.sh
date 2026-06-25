#!/usr/bin/env bash
set -euo pipefail

KEY_FILE="${KEY_FILE:-$HOME/.ssh/id_ed25519}"
KEY_COMMENT="${KEY_COMMENT:-macbook-pro-to-agent-eco-mini}"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [[ -f "$KEY_FILE" ]]; then
  echo "PASS: SSH private key already exists: $KEY_FILE"
else
  echo "Creating SSH key: $KEY_FILE"
  ssh-keygen -t ed25519 -C "$KEY_COMMENT" -f "$KEY_FILE"
fi

chmod 600 "$KEY_FILE"
chmod 644 "${KEY_FILE}.pub"

echo
echo "Public key:"
cat "${KEY_FILE}.pub"
echo
echo "Next: ./install_public_key_on_mini.sh"

