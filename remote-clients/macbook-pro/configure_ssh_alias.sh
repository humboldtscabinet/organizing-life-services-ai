#!/usr/bin/env bash
set -euo pipefail

TAILNET_NAME="${1:-${TAILNET_NAME:-}}"
MINI_USER="${MINI_USER:-aiagentecosystem}"
MINI_HOST="${MINI_HOST:-agent-eco-mini}"
IDENTITY_FILE="${IDENTITY_FILE:-$HOME/.ssh/id_ed25519}"
SSH_CONFIG="${SSH_CONFIG:-$HOME/.ssh/config}"
MARKER_BEGIN="# BEGIN OLS MINI REMOTE CLIENT"
MARKER_END="# END OLS MINI REMOTE CLIENT"

if [[ "$TAILNET_NAME" == "--lan-only" ]]; then
  TAILNET_NAME=""
fi

if [[ "$TAILNET_NAME" == *"<"* || "$TAILNET_NAME" == *">"* ]]; then
  echo "Replace the placeholder with the real Tailscale MagicDNS tailnet name." >&2
  exit 1
fi

mkdir -p "$(dirname "$SSH_CONFIG")"
touch "$SSH_CONFIG"
chmod 700 "$(dirname "$SSH_CONFIG")"
chmod 600 "$SSH_CONFIG"

if [[ -f "$SSH_CONFIG" ]]; then
  cp "$SSH_CONFIG" "${SSH_CONFIG}.bak.$(date +%Y%m%d%H%M%S)"
fi

tmp_file="$(mktemp)"
awk -v begin="$MARKER_BEGIN" -v end="$MARKER_END" '
  $0 == begin {skip=1; next}
  $0 == end {skip=0; next}
  skip != 1 {print}
' "$SSH_CONFIG" > "$tmp_file"

cat >> "$tmp_file" <<EOF
$MARKER_BEGIN
Host ols-mini-lan
  HostName ${MINI_HOST}.local
  User ${MINI_USER}
  IdentityFile ${IDENTITY_FILE}
  IdentitiesOnly yes
  ServerAliveInterval 30
  ServerAliveCountMax 3
  LocalForward 3000 127.0.0.1:3000
  LocalForward 8000 127.0.0.1:8000
  LocalForward 5678 127.0.0.1:5678
EOF

if [[ -n "$TAILNET_NAME" ]]; then
  cat >> "$tmp_file" <<EOF

Host ols-mini
  HostName ${MINI_HOST}.${TAILNET_NAME}
  User ${MINI_USER}
  IdentityFile ${IDENTITY_FILE}
  IdentitiesOnly yes
  ServerAliveInterval 30
  ServerAliveCountMax 3
  LocalForward 3000 127.0.0.1:3000
  LocalForward 8000 127.0.0.1:8000
  LocalForward 5678 127.0.0.1:5678
EOF
fi

cat >> "$tmp_file" <<EOF
$MARKER_END
EOF

mv "$tmp_file" "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

echo "Updated $SSH_CONFIG"
echo "Test LAN:       ssh ols-mini-lan"
if [[ -n "$TAILNET_NAME" ]]; then
  echo "Test Tailscale: ssh ols-mini"
else
  echo "Tailscale alias skipped. Add it later with: $0 <tailnet-name>"
fi
