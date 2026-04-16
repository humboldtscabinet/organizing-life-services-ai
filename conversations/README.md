# Conversation Archive

This folder is an append-only archive of Claude conversations related to the OLS project. The goal is simple: because Claude has no native cross-session memory, we keep every session's transcript here so Claude (or you, or a future collaborator) can look back at what was discussed, decided, or debugged.

## Layout

```
conversations/
├── README.md              ← you are here
├── INDEX.md               ← auto-generated list of every archived session
├── raw/                   ← verbatim .jsonl transcripts (lossless, machine-readable)
├── markdown/              ← human-readable .md version of each transcript
└── scripts/
    ├── backup_conversations.sh       ← sync + commit + push
    ├── jsonl_to_markdown.py          ← converter used by the sync script
    ├── com.humboldtscabinet.claude-conversation-backup.plist  ← launchd daily job
    └── SETUP.md                      ← one-time setup instructions
```

Filename convention: `YYYY-MM-DD_<session-id-prefix>.{jsonl,md}`. The date is the file's last-modified date; the session ID prefix is the first 8 chars of the full session UUID.

## How to use the archive

### To remind Claude of past context in a new conversation

Paste or reference the relevant file, for example:

> "Here's the session where we set up the XO Gallery automation: `conversations/markdown/2026-04-15_ece7d054.md`. Pick up from where we left off with filling alt text."

Claude can read these files directly from the workspace folder.

### To find something specific

```bash
# Search every markdown transcript for a keyword
grep -l "XO Gallery" conversations/markdown/*.md

# Show just the user messages from a session
grep "^## 👤 User" conversations/markdown/2026-04-15_ece7d054.md
```

### To re-process a transcript (e.g. better markdown formatting)

```bash
python3 conversations/scripts/jsonl_to_markdown.py \
    conversations/raw/2026-04-15_ece7d054.jsonl \
    conversations/markdown/2026-04-15_ece7d054.md
```

## Privacy

This repository is **private**. Transcripts contain references to API keys, store configuration, and other operational details, and are not safe to make public without scrubbing. If the repo is ever considered for open-sourcing, `conversations/` would need to be purged from history first (e.g., via `git filter-repo`).

## What gets synced

The backup script mirrors every `.jsonl` file it finds under `~/.claude/projects/` on the Mac that runs it. Transcripts are append-only within a session, so re-running the backup is always safe and idempotent.

Sessions from multiple projects (not just OLS) will be picked up if they exist. If you want to filter by project, add a path filter inside `backup_conversations.sh`.

## Automation

The launchd job `com.humboldtscabinet.claude-conversation-backup` runs the backup script daily at 2:15am local time. See `scripts/SETUP.md` for how to install it.

You can also run the backup on demand any time:

```bash
bash conversations/scripts/backup_conversations.sh
```
