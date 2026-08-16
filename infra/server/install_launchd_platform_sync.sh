#!/usr/bin/env bash
# Install launchd jobs for daily generate-tasks and weekly Phase 1.
# Do not import n8n workflow templates; leave ols-n8n running unused.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WRAPPER="${ROOT_DIR}/infra/server/run_platform_sync.sh"
LAUNCHD_PATH="${LAUNCHD_PATH:-/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$HOME/.orbstack/bin:/usr/bin:/bin:/usr/sbin:/sbin}"
LOG_DIR="${PLATFORM_SYNC_LOG_DIR:-$ROOT_DIR/infra/server/out}"
LOAD_NOW="${LOAD_NOW:-true}"
DAILY_LABEL="${DAILY_LABEL:-com.ols.platform-sync.daily}"
WEEKLY_LABEL="${WEEKLY_LABEL:-com.ols.platform-sync.weekly}"
DAILY_HOUR="${DAILY_HOUR:-6}"
DAILY_MINUTE="${DAILY_MINUTE:-0}"
WEEKLY_HOUR="${WEEKLY_HOUR:-7}"
WEEKLY_MINUTE="${WEEKLY_MINUTE:-0}"
# launchd: 0 and 7 = Sunday, 1 = Monday
WEEKLY_WEEKDAY="${WEEKLY_WEEKDAY:-1}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: launchd platform-sync installation is only supported on macOS." >&2
  exit 1
fi

if [[ ! -x "$WRAPPER" ]]; then
  chmod +x "$WRAPPER"
fi

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

write_plist() {
  local label="$1"
  local plist_path="$2"
  local hour="$3"
  local minute="$4"
  local weekday="${5:-}"
  shift 5 || true
  local args=("$@")

  local weekday_xml=""
  if [[ -n "$weekday" ]]; then
    weekday_xml="    <key>Weekday</key>
    <integer>${weekday}</integer>"
  fi

  local args_xml=""
  local arg
  for arg in "${args[@]}"; do
    args_xml="${args_xml}      <string>${arg}</string>
"
  done

  cat > "$plist_path" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$label</string>

  <key>ProgramArguments</key>
  <array>
    <string>$WRAPPER</string>
${args_xml}  </array>

  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>$LAUNCHD_PATH</string>
  </dict>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$hour</integer>
    <key>Minute</key>
    <integer>$minute</integer>
${weekday_xml}
  </dict>

  <key>StandardOutPath</key>
  <string>$LOG_DIR/${label}.log</string>

  <key>StandardErrorPath</key>
  <string>$LOG_DIR/${label}.err.log</string>
</dict>
</plist>
PLIST

  echo "Installed launchd plist at $plist_path"

  if [[ "$LOAD_NOW" == "true" ]]; then
    launchctl bootout "gui/$(id -u)" "$plist_path" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$(id -u)" "$plist_path"
    launchctl enable "gui/$(id -u)/$label"
    echo "Loaded launchd job $label"
  else
    echo "LOAD_NOW=false; plist written but not loaded: $label"
  fi
}

write_plist \
  "$DAILY_LABEL" \
  "$HOME/Library/LaunchAgents/${DAILY_LABEL}.plist" \
  "$DAILY_HOUR" \
  "$DAILY_MINUTE" \
  "" \
  --generate-tasks

write_plist \
  "$WEEKLY_LABEL" \
  "$HOME/Library/LaunchAgents/${WEEKLY_LABEL}.plist" \
  "$WEEKLY_HOUR" \
  "$WEEKLY_MINUTE" \
  "$WEEKLY_WEEKDAY" \
  --full-cycle --schedule-content-count 1

echo "Daily: ${DAILY_HOUR}:$(printf '%02d' "$DAILY_MINUTE") --generate-tasks"
echo "Weekly: weekday ${WEEKLY_WEEKDAY} ${WEEKLY_HOUR}:$(printf '%02d' "$WEEKLY_MINUTE") --full-cycle"
echo "Do not import workflows/n8n/*.json. Kick once with:"
echo "  launchctl kickstart -k gui/\$(id -u)/${DAILY_LABEL}"
