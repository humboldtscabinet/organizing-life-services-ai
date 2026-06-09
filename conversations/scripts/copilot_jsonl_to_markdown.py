#!/usr/bin/env python3
"""
Convert a GitHub Copilot Chat transcript (.jsonl) into a readable Markdown file.

Usage:
    python3 copilot_jsonl_to_markdown.py INPUT.jsonl[.gz] OUTPUT.md

Copilot stores one event-based JSONL transcript per chat session under:
    ~/Library/Application Support/Code/User/workspaceStorage/<hash>/
        GitHub.copilot-chat/transcripts/<session-uuid>.jsonl

Each line is an event: {type, data, id, timestamp, parentId}. Event types seen:
  - session.start          → metadata (versions, start time)
  - user.message           → data.content, data.attachments
  - assistant.message      → data.content, data.reasoningText, data.toolRequests
  - assistant.turn_start/end → boundaries (skipped)
  - tool.execution_start   → data.toolName, data.arguments, data.toolCallId
  - tool.execution_complete→ data.toolCallId, data.success

Design goals (mirror the sibling Claude converter):
- Lossy-but-readable. Preserves user/assistant text, tool calls (name + inputs),
  and tool success status. Full tool OUTPUTS are not stored by Copilot in the
  transcript, so they cannot be reproduced here (the raw .jsonl.gz is the
  lossless record).
- Deterministic: same input → same output.
- Self-contained: stdlib only. Handles plain or gzipped input.
"""
from __future__ import annotations

import gzip
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def fmt_ts(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return raw


def truncate(text: str, limit: int) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n… [truncated {len(text) - limit:,} chars] …"


def _open(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _arguments_to_str(args: Any) -> str:
    """tool arguments may be a JSON string or a dict."""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            return args
    try:
        return json.dumps(args, indent=2)
    except Exception:
        return str(args)


def convert(jsonl_path: Path, md_path: Path) -> dict:
    stats = {"messages": 0, "user": 0, "assistant": 0, "tool_calls": 0, "skipped": 0}

    meta = {
        "sessionId": "",
        "startTime": "",
        "lastTime": "",
        "copilotVersion": "",
        "vscodeVersion": "",
        "producer": "",
    }

    rows: list[dict] = []
    with _open(jsonl_path) as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                stats["skipped"] += 1

    # Pre-pass: map toolCallId → success so we can annotate each call.
    tool_success: dict[str, bool] = {}
    for row in rows:
        if row.get("type") == "tool.execution_complete":
            d = row.get("data", {}) or {}
            tcid = d.get("toolCallId")
            if tcid is not None:
                tool_success[tcid] = bool(d.get("success"))

    lines: list[str] = []
    for row in rows:
        rtype = row.get("type")
        data = row.get("data", {}) or {}
        ts = row.get("timestamp", "")
        if ts:
            meta["lastTime"] = ts

        if rtype == "session.start":
            meta["sessionId"] = data.get("sessionId", "")
            meta["startTime"] = data.get("startTime", "") or ts
            meta["copilotVersion"] = data.get("copilotVersion", "")
            meta["vscodeVersion"] = data.get("vscodeVersion", "")
            meta["producer"] = data.get("producer", "")
            continue

        if rtype == "user.message":
            content = (data.get("content") or "").strip()
            if not content:
                continue
            stats["messages"] += 1
            stats["user"] += 1
            atts = data.get("attachments") or []
            att_note = f"\n\n_attachments: {len(atts)}_" if atts else ""
            lines.append(f"## 👤 User — {fmt_ts(ts)}\n\n{truncate(content, 16000)}{att_note}\n")
            continue

        if rtype == "assistant.message":
            content = (data.get("content") or "").strip()
            reasoning = (data.get("reasoningText") or "").strip()
            parts: list[str] = []
            if reasoning:
                parts.append(
                    "<details><summary>💭 reasoning</summary>\n\n"
                    f"{truncate(reasoning, 6000)}\n\n</details>"
                )
            if content:
                parts.append(truncate(content, 16000))
            if not parts:
                continue
            stats["messages"] += 1
            stats["assistant"] += 1
            lines.append(f"## 🤖 Assistant — {fmt_ts(ts)}\n\n" + "\n\n".join(parts) + "\n")
            continue

        if rtype == "tool.execution_start":
            name = data.get("toolName", "?")
            tcid = data.get("toolCallId", "")
            args = _arguments_to_str(data.get("arguments", {}))
            ok = tool_success.get(tcid)
            marker = "" if ok is None else ("  ✅" if ok else "  ❌")
            stats["tool_calls"] += 1
            lines.append(
                f"**🔧 Tool: `{name}`{marker}**\n\n"
                f"```json\n{truncate(args, 2500)}\n```\n"
            )
            continue

        # assistant.turn_start / assistant.turn_end / tool.execution_complete: skip
        stats["skipped"] += 1

    header = [
        f"# Copilot Chat: `{meta['sessionId']}`",
        "",
        f"- **Started:** {fmt_ts(meta['startTime'])}",
        f"- **Last activity:** {fmt_ts(meta['lastTime'])}",
        f"- **Producer:** `{meta['producer']}`",
        f"- **Copilot version:** `{meta['copilotVersion']}`  ·  **VS Code:** `{meta['vscodeVersion']}`",
        f"- **Messages:** {stats['messages']} "
        f"(user: {stats['user']}, assistant: {stats['assistant']}, tool calls: {stats['tool_calls']})",
        "",
        "> Note: Copilot transcripts do not store full tool OUTPUTS — tool calls"
        " show name, inputs, and success only. The raw `.jsonl.gz` is the lossless record.",
        "",
        "---",
        "",
    ]

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(header) + "\n".join(lines), encoding="utf-8")
    return stats


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    src = Path(argv[1])
    dst = Path(argv[2])
    if not src.exists():
        print(f"ERROR: input not found: {src}", file=sys.stderr)
        return 1
    stats = convert(src, dst)
    print(
        f"Converted {src.name} → {dst.name} "
        f"(user {stats['user']}, assistant {stats['assistant']}, tools {stats['tool_calls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
