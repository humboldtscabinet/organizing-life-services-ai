# Conversation Archive Policy

This repo no longer stores raw or rendered AI conversation transcripts.
Transcripts can contain session URLs, tokens, cookies, customer details, store
configuration, and other operational material that should not live in source
control.

## Current Layout

```text
conversations/
├── README.md
└── scripts/
    ├── backup_conversations.sh
    ├── backup_copilot_conversations.sh
    ├── jsonl_to_markdown.py
    ├── copilot_jsonl_to_markdown.py
    └── launchd plist templates
```

The actual private archive defaults to:

```text
~/.ols/private/conversations/
├── raw/
├── markdown/
├── logs/
└── INDEX.md
```

Override that path with `OLS_CONVERSATION_ARCHIVE_DIR` if needed.

## Backing Up Conversations

Claude/local-agent transcript backup:

```bash
bash conversations/scripts/backup_conversations.sh
```

GitHub Copilot transcript backup:

```bash
bash conversations/scripts/backup_copilot_conversations.sh
```

Both scripts write to the private archive and set restrictive permissions. They
do not `git add`, commit, or push transcript contents.

## Using Past Context

When past context is needed, reference the private archive from the local
machine instead of adding transcript files to this repo. For example:

```bash
rg "XO Gallery" ~/.ols/private/conversations/markdown
```

If a conversation contains a decision worth preserving in source control, turn
that decision into a short sanitized note under `docs/`, not a transcript dump.

## Legacy History Note

Older commits in this private repository contained transcript files under
`conversations/raw/` and `conversations/markdown/`. The current tree removes
those files and ignores future transcript artifacts. A full Git history rewrite
with `git filter-repo` remains a separate, coordinated operation if the repo
ever needs stronger historical purging.
