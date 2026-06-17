#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LABEL="${LABEL:-com.ols.backups}"
PLIST_PATH="${PLIST_PATH:-$HOME/Library/LaunchAgents/$LABEL.plist}"
START_HOUR="${START_HOUR:-3}"
START_MINUTE="${START_MINUTE:-15}"
BACKUP_LOG_DIR="${BACKUP_LOG_DIR:-$ROOT_DIR/infra/backup/out}"
LOAD_NOW="${LOAD_NOW:-true}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: launchd backup installation is only supported on macOS." >&2
  exit 1
fi

mkdir -p "$(dirname "$PLIST_PATH")" "$BACKUP_LOG_DIR"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>$ROOT_DIR/infra/backup/run_all_backups.sh</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$START_HOUR</integer>
    <key>Minute</key>
    <integer>$START_MINUTE</integer>
  </dict>

  <key>StandardOutPath</key>
  <string>$BACKUP_LOG_DIR/launchd-backup.log</string>

  <key>StandardErrorPath</key>
  <string>$BACKUP_LOG_DIR/launchd-backup.err.log</string>
</dict>
</plist>
PLIST

echo "Installed launchd plist at $PLIST_PATH"
echo "Daily backup time: ${START_HOUR}:${START_MINUTE}"

if [[ "$LOAD_NOW" == "true" ]]; then
  launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
  launchctl enable "gui/$(id -u)/$LABEL"
  echo "Loaded launchd job $LABEL"
else
  echo "LOAD_NOW=false; plist written but not loaded."
fi
