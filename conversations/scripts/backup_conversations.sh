#!/usr/bin/env bash
# Backup Claude conversation transcripts to the OLS repo.
#
# What it does (idempotent):
#   1. Finds all .jsonl transcripts under ~/.claude/projects/
#   2. For each, copies the raw JSONL into conversations/raw/
#   3. Runs jsonl_to_markdown.py to produce a human-readable .md in conversations/markdown/
#   4. Regenerates conversations/INDEX.md with a sortable list
#   5. If anything changed, git add + commit + push
#
# Safe to run repeatedly. Existing files get overwritten with the latest copy
# (transcripts are append-only, so older content is preserved).
#
# Exit codes:
#   0 - success (with or without changes)
#   1 - setup error (missing binary, bad repo state)
#   2 - git push failed

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────
REPO_ROOT="${REPO_ROOT:-$HOME/Documents/Claude/Projects/Ai Agent Ecosystem - OLS/organizing-life-services-ai}"
# Cowork/Claude desktop stores transcripts under Library/Application Support.
# Override with CLAUDE_PROJECTS_DIR env var if yours lives elsewhere.
CLAUDE_PROJECTS_DIR="${CLAUDE_PROJECTS_DIR:-$HOME/Library/Application Support/Claude/local-agent-mode-sessions}"
BRANCH="${BRANCH:-main}"
LOG_FILE="${LOG_FILE:-$REPO_ROOT/conversations/scripts/backup.log}"

# ── Logging ────────────────────────────────────────────────────────
log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

# ── Preflight ──────────────────────────────────────────────────────
mkdir -p "$(dirname "$LOG_FILE")"
log "── Backup run starting ──"

if [[ ! -d "$REPO_ROOT" ]]; then
  log "ERROR: repo root not found: $REPO_ROOT"
  exit 1
fi

if [[ ! -d "$CLAUDE_PROJECTS_DIR" ]]; then
  log "ERROR: Claude projects dir not found: $CLAUDE_PROJECTS_DIR"
  log "       Set CLAUDE_PROJECTS_DIR env var if your transcripts live elsewhere."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  log "ERROR: python3 not on PATH"
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  log "ERROR: git not on PATH"
  exit 1
fi

cd "$REPO_ROOT"

# Make sure we're on the expected branch and clean-ish (stash uncommitted local work)
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  log "WARNING: on branch $CURRENT_BRANCH, expected $BRANCH. Skipping push."
  PUSH_ENABLED=false
else
  PUSH_ENABLED=true
fi

# Pull latest first to minimize merge conflicts on shared repos
if $PUSH_ENABLED; then
  log "Pulling latest from origin/$BRANCH..."
  git pull --rebase --autostash origin "$BRANCH" >> "$LOG_FILE" 2>&1 || {
    log "WARNING: git pull failed; continuing with local state"
  }
fi

# ── Sync transcripts ───────────────────────────────────────────────
RAW_DIR="$REPO_ROOT/conversations/raw"
MD_DIR="$REPO_ROOT/conversations/markdown"
SCRIPTS_DIR="$REPO_ROOT/conversations/scripts"
mkdir -p "$RAW_DIR" "$MD_DIR"

COUNT=0
NEW_OR_UPDATED=0

# Find main-session .jsonl files only.
# Structure: .../local_<uuid>/.claude/projects/-sessions-<name>/<session-uuid>.jsonl
# Exclude:
#   - subagents/agent-*.jsonl (low-signal, work delegated from main sessions)
#   - audit.jsonl (infrastructure/permission log, not a conversation)
while IFS= read -r -d '' jsonl_file; do
  COUNT=$((COUNT + 1))

  session_id="$(basename "$jsonl_file" .jsonl)"
  # Extract the parent "-sessions-<name>" folder so we can preserve a readable label
  parent_dir="$(basename "$(dirname "$jsonl_file")")"
  # Strip the leading "-sessions-" prefix if present
  label="${parent_dir#-sessions-}"
  # Date-prefix from the file's mtime (YYYY-MM-DD)
  mtime_date="$(date -r "$jsonl_file" '+%Y-%m-%d')"
  prefix="${mtime_date}_${label}_${session_id:0:8}"

  # Raw transcripts are stored gzipped so GitHub's 100MB-per-file limit
  # doesn't block pushes. JSONL compresses ~10x.
  raw_dst="$RAW_DIR/${prefix}.jsonl.gz"
  md_dst="$MD_DIR/${prefix}.md"

  # Only re-copy + re-convert if source is newer than current raw copy
  needs_update=false
  if [[ ! -f "$raw_dst" ]]; then
    needs_update=true
  elif [[ "$jsonl_file" -nt "$raw_dst" ]]; then
    needs_update=true
  fi

  if $needs_update; then
    # gzip into the destination; -n omits filename+mtime for reproducibility
    gzip -n -c "$jsonl_file" > "$raw_dst" || {
      log "WARNING: gzip failed for $jsonl_file"
      continue
    }
    python3 "$SCRIPTS_DIR/jsonl_to_markdown.py" "$raw_dst" "$md_dst" >> "$LOG_FILE" 2>&1 || {
      log "WARNING: conversion failed for $jsonl_file"
      continue
    }
    NEW_OR_UPDATED=$((NEW_OR_UPDATED + 1))
    log "Synced: $prefix"
  fi
done < <(find "$CLAUDE_PROJECTS_DIR" -type f -name '*.jsonl' \
    -path '*/.claude/projects/-sessions-*' \
    ! -path '*/subagents/*' \
    ! -name 'audit.jsonl' \
    -print0)

log "Found $COUNT total transcript(s), $NEW_OR_UPDATED new or updated."

# ── Regenerate INDEX.md ─────────────────────────────────────────────
INDEX="$REPO_ROOT/conversations/INDEX.md"
{
  echo "# Conversation Archive Index"
  echo ""
  echo "_Auto-generated by \`backup_conversations.sh\`. Last updated: $(date '+%Y-%m-%d %H:%M:%S %Z')_"
  echo ""
  echo "| Date | Session | Size | Markdown | Raw JSONL |"
  echo "|------|---------|------|----------|-----------|"
  # List by filename (date-prefixed = chronological, newest first)
  find "$MD_DIR" -maxdepth 1 -name '*.md' -print0 2>/dev/null \
    | xargs -0 -I{} basename {} .md \
    | sort -r \
    | while IFS= read -r base; do
        md_file="$MD_DIR/${base}.md"
        date_part="${base%%_*}"
        sess_part="${base#*_}"
        size_bytes=$(wc -c < "$md_file" 2>/dev/null || echo 0)
        if [[ "$size_bytes" -gt 1048576 ]]; then
          size=$(awk "BEGIN {printf \"%.1fM\", $size_bytes/1048576}")
        elif [[ "$size_bytes" -gt 1024 ]]; then
          size=$(awk "BEGIN {printf \"%.0fK\", $size_bytes/1024}")
        else
          size="${size_bytes}B"
        fi
        raw_rel="raw/${base}.jsonl.gz"
        md_rel="markdown/${base}.md"
        echo "| $date_part | \`$sess_part\` | $size | [view]($md_rel) | [view]($raw_rel) |"
      done
} > "$INDEX"

# ── Commit + push if changed ────────────────────────────────────────
git add conversations/ >> "$LOG_FILE" 2>&1

if git diff --cached --quiet; then
  log "No changes to commit."
  log "── Backup run complete (no-op) ──"
  exit 0
fi

COMMIT_MSG="archive: sync $NEW_OR_UPDATED conversation(s) $(date '+%Y-%m-%d %H:%M')"
git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1 || {
  log "ERROR: git commit failed"
  exit 1
}
log "Committed: $COMMIT_MSG"

if $PUSH_ENABLED; then
  if git push origin "$BRANCH" >> "$LOG_FILE" 2>&1; then
    log "Pushed to origin/$BRANCH"
  else
    log "ERROR: git push failed. Commit is local only."
    exit 2
  fi
fi

log "── Backup run complete ──"
