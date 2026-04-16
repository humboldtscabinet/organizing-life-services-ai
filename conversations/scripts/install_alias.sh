#!/usr/bin/env bash
# Install a 'cowork-backup' alias into ~/.zshrc so you can trigger the
# conversation backup from any Terminal window by typing one word.
#
# Idempotent: re-running just leaves the existing alias in place.

set -euo pipefail

ZSHRC="$HOME/.zshrc"
REPO_ROOT="$HOME/Developer/organizing-life-services-ai"
SCRIPT_PATH="$REPO_ROOT/conversations/scripts/backup_conversations.sh"
MARKER="# cowork-backup alias (managed by install_alias.sh)"

if ! [[ -f "$SCRIPT_PATH" ]]; then
  echo "ERROR: backup script not found at $SCRIPT_PATH" >&2
  exit 1
fi

touch "$ZSHRC"

if grep -qF "$MARKER" "$ZSHRC"; then
  echo "Alias already installed in $ZSHRC — nothing to do."
  echo "Run: source ~/.zshrc  (or open a new Terminal) to activate it."
  exit 0
fi

{
  echo ""
  echo "$MARKER"
  echo "alias cowork-backup='bash \"$SCRIPT_PATH\"'"
} >> "$ZSHRC"

echo "Added 'cowork-backup' alias to $ZSHRC."
echo ""
echo "To use it in this terminal right now:"
echo "    source ~/.zshrc"
echo ""
echo "Or open a new Terminal tab. Then just type:"
echo "    cowork-backup"
