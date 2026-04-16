# One-Time Setup

Run these commands **on your Mac** (Terminal app) once. The whole setup takes about 3 minutes.

## 1. Install GitHub CLI

```bash
brew install gh
```

Then authenticate with your GitHub account (this is what lets the backup script push without typing a password every time):

```bash
gh auth login
```

When prompted:
- **Where do you use GitHub?** → `GitHub.com`
- **Preferred protocol for Git operations?** → `HTTPS`
- **Authenticate Git with your GitHub credentials?** → `Y`
- **How would you like to authenticate?** → `Login with a web browser`

Follow the browser prompt, then verify:

```bash
gh auth status
```

You should see `Logged in to github.com as humboldtscabinet`.

## 2. Test the backup script manually

```bash
cd "$HOME/Documents/Claude/Projects/Ai Agent Ecosystem - OLS/organizing-life-services-ai"
bash conversations/scripts/backup_conversations.sh
```

You should see output like:

```
[2026-04-15 23:35:00] ── Backup run starting ──
[2026-04-15 23:35:00] Pulling latest from origin/main...
[2026-04-15 23:35:02] Synced: 2026-04-15_ece7d054
[2026-04-15 23:35:02] Found 1 total transcript(s), 1 new or updated.
[2026-04-15 23:35:03] Committed: archive: sync 1 conversation(s) 2026-04-15 23:35
[2026-04-15 23:35:05] Pushed to origin/main
[2026-04-15 23:35:05] ── Backup run complete ──
```

If it succeeded, visit https://github.com/humboldtscabinet/organizing-life-services-ai/tree/main/conversations — you should see the archive live on GitHub.

## 3. Install the daily launchd job

This is what makes it run automatically every morning at 2:15am.

Copy the plist into the system location launchd expects:

```bash
cp "$HOME/Documents/Claude/Projects/Ai Agent Ecosystem - OLS/organizing-life-services-ai/conversations/scripts/com.humboldtscabinet.claude-conversation-backup.plist" \
   "$HOME/Library/LaunchAgents/"
```

Load it:

```bash
launchctl load -w "$HOME/Library/LaunchAgents/com.humboldtscabinet.claude-conversation-backup.plist"
```

Verify it's registered:

```bash
launchctl list | grep claude-conversation-backup
```

You should see a line with the label and exit status `0`.

## Manual triggers

There are three ways to run a backup on demand. Pick whichever feels natural.

### Option A — Shell alias `cowork-backup` (easiest)

One-time install:

```bash
bash "$HOME/Documents/Claude/Projects/Ai Agent Ecosystem - OLS/organizing-life-services-ai/conversations/scripts/install_alias.sh"
source ~/.zshrc
```

After that, from **any** Terminal window, from **any** directory:

```bash
cowork-backup
```

### Option B — Invoke the launchd job directly

```bash
launchctl start com.humboldtscabinet.claude-conversation-backup
tail -f /tmp/claude-conversation-backup.stdout.log
```

Works the same as the daily 2:15am run, just fires immediately.

### Option C — Touch the trigger file (works from Claude mid-conversation)

The launchd job watches `conversations/.trigger`. Any modification to it fires a backup. From a shell:

```bash
touch "$HOME/Documents/Claude/Projects/Ai Agent Ecosystem - OLS/organizing-life-services-ai/conversations/.trigger"
```

Or just ask Claude: *"Back up our conversations."* Claude can touch that file directly from the sandbox — no shell needed.

## Troubleshooting

### "I want to change the run time"

Edit the plist's `Hour` and `Minute` values, then reload:

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.humboldtscabinet.claude-conversation-backup.plist"
# (edit the file)
launchctl load -w "$HOME/Library/LaunchAgents/com.humboldtscabinet.claude-conversation-backup.plist"
```

### "I want to disable the auto-run"

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.humboldtscabinet.claude-conversation-backup.plist"
```

### "The script ran but the push failed"

Check the log:

```bash
tail -50 conversations/scripts/backup.log
```

Common causes:
- `gh auth status` expired — re-run `gh auth login`
- You have uncommitted local work on `main` — commit or stash it, then re-run
- Network was down at 2:15am — the next run will pick up the backlog

### "Transcripts aren't in `~/.claude/projects/` on my Mac — where are they?"

Find them:

```bash
find ~ -name "*.jsonl" -path "*claude*" 2>/dev/null | head -5
```

If they're elsewhere, set the env var in the plist:

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>CLAUDE_PROJECTS_DIR</key>
    <string>/actual/path/here</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
</dict>
```

Then reload the job.
