# Private Conversation Backup Setup

Conversation transcripts are private local artifacts. Do not commit them to this
repo.

## Default Destination

Backups write to:

```text
~/.ols/private/conversations/
```

To use a different destination:

```bash
export OLS_CONVERSATION_ARCHIVE_DIR="/path/to/private/conversation-archive"
```

## Manual Backups

Claude/local-agent sessions:

```bash
bash conversations/scripts/backup_conversations.sh
```

GitHub Copilot Chat sessions for this repo:

```bash
bash conversations/scripts/backup_copilot_conversations.sh
```

Both scripts create:

```text
raw/
markdown/
logs/
INDEX.md
```

under the private archive path.

## Automation

The plist templates in this folder may still be used with launchd, but they
should be reviewed before loading because local clone paths differ by machine.
The backup scripts themselves no longer commit or push transcript files.

Recommended checks after any launchd install:

```bash
launchctl list | rg "conversation-backup"
tail -50 ~/.ols/private/conversations/logs/claude-backup.log
tail -50 ~/.ols/private/conversations/logs/copilot-backup.log
```

## Restoring Old Local Context

A private copy of the previously tracked archive may exist at:

```text
~/.ols/private/conversations/legacy-git-archive-2026-06-17/
```

Use it locally only. If a decision from a transcript matters to the project,
write a short sanitized note under `docs/` instead of recommitting transcript
content.
