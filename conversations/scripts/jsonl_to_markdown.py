#!/usr/bin/env python3
"""
Convert a Claude Code JSONL session transcript into a readable Markdown file.

Usage:
    python3 jsonl_to_markdown.py INPUT.jsonl OUTPUT.md

Design goals:
- Lossy-but-readable. Preserves user messages, assistant text, tool calls
  (with inputs), and tool results. Drops low-signal metadata like deferred
  tool schema deltas, queue-operation rows, and raw attachment byte dumps.
- Deterministic: same input produces same output.
- Self-contained: only stdlib.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SKIP_TYPES = {"queue-operation"}
# These attachment types are high-volume and low-signal for human review
SKIP_ATTACHMENT_TYPES = {
    "deferred_tools_delta",
    "skills_delta",
    "available_mcp_servers_delta",
}


def fmt_ts(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return raw


def truncate(text: str, limit: int = 8000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n… [truncated {len(text) - limit:,} chars] …"


def render_content(content: Any) -> str:
    """Render message.content which may be str or list of blocks."""
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return json.dumps(content, indent=2)

    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            parts.append(str(block))
            continue
        btype = block.get("type")
        if btype == "text":
            parts.append(block.get("text", "").strip())
        elif btype == "tool_use":
            name = block.get("name", "?")
            tool_input = block.get("input", {})
            try:
                input_str = json.dumps(tool_input, indent=2)
            except Exception:
                input_str = str(tool_input)
            parts.append(
                f"**🔧 Tool call: `{name}`**\n\n"
                f"```json\n{truncate(input_str, 4000)}\n```"
            )
        elif btype == "tool_result":
            tool_id = block.get("tool_use_id", "?")
            result = block.get("content", "")
            if isinstance(result, list):
                result_text = "\n\n".join(
                    render_content([b]) if isinstance(b, dict) else str(b)
                    for b in result
                )
            else:
                result_text = str(result)
            is_error = block.get("is_error", False)
            marker = "❌ Error" if is_error else "✅ Result"
            parts.append(
                f"**{marker} from tool `{tool_id[:8]}…`**\n\n"
                f"```\n{truncate(result_text, 6000)}\n```"
            )
        elif btype == "thinking":
            thinking = block.get("thinking", "").strip()
            if thinking:
                parts.append(f"<details><summary>💭 thinking</summary>\n\n{thinking}\n\n</details>")
        elif btype == "image":
            parts.append("*[image omitted]*")
        else:
            parts.append(f"*[unknown block type: {btype}]*")

    return "\n\n".join(p for p in parts if p)


def convert(jsonl_path: Path, md_path: Path) -> dict:
    """Convert a JSONL file to markdown. Returns stats dict."""
    stats = {"messages": 0, "user": 0, "assistant": 0, "tool_calls": 0, "skipped": 0}

    session_id = ""
    first_ts = ""
    last_ts = ""
    cwd = ""
    version = ""

    lines: list[str] = []

    # Transparently handle gzipped (.jsonl.gz) or plain (.jsonl) inputs
    if jsonl_path.suffix == ".gz":
        opener = lambda: gzip.open(jsonl_path, "rt", encoding="utf-8")
    else:
        opener = lambda: jsonl_path.open("r", encoding="utf-8")

    with opener() as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                stats["skipped"] += 1
                continue

            rtype = row.get("type")

            # Skip noisy / infrastructure rows
            if rtype in SKIP_TYPES:
                stats["skipped"] += 1
                continue

            # Attachment rows: skip most, but keep e.g. file uploads
            if "attachment" in row:
                att = row.get("attachment", {})
                if att.get("type") in SKIP_ATTACHMENT_TYPES:
                    stats["skipped"] += 1
                    continue

            ts = row.get("timestamp", "")
            if ts:
                if not first_ts:
                    first_ts = ts
                last_ts = ts

            session_id = session_id or row.get("sessionId", "")
            cwd = cwd or row.get("cwd", "")
            version = version or row.get("version", "")

            msg = row.get("message")
            if not msg:
                continue

            role = msg.get("role", rtype or "?")
            content = msg.get("content", "")

            rendered = render_content(content)
            if not rendered:
                continue

            stats["messages"] += 1
            if role == "user":
                stats["user"] += 1
                lines.append(f"## 👤 User — {fmt_ts(ts)}\n\n{rendered}\n")
            elif role == "assistant":
                stats["assistant"] += 1
                # Count tool calls inside
                if isinstance(content, list):
                    stats["tool_calls"] += sum(
                        1 for b in content if isinstance(b, dict) and b.get("type") == "tool_use"
                    )
                lines.append(f"## 🤖 Assistant — {fmt_ts(ts)}\n\n{rendered}\n")
            else:
                lines.append(f"## ℹ️  {role} — {fmt_ts(ts)}\n\n{rendered}\n")

    header = [
        f"# Conversation: `{session_id}`",
        "",
        f"- **Started:** {fmt_ts(first_ts)}",
        f"- **Last activity:** {fmt_ts(last_ts)}",
        f"- **Working dir:** `{cwd}`",
        f"- **Claude Code version:** `{version}`",
        f"- **Messages:** {stats['messages']} (user: {stats['user']}, assistant: {stats['assistant']}, tool calls: {stats['tool_calls']})",
        "",
        "---",
        "",
    ]

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(header) + "\n".join(lines), encoding="utf-8")

    return {
        **stats,
        "session_id": session_id,
        "first_ts": first_ts,
        "last_ts": last_ts,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: jsonl_to_markdown.py INPUT.jsonl OUTPUT.md", file=sys.stderr)
        return 1
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    if not src.exists():
        print(f"Input not found: {src}", file=sys.stderr)
        return 1
    stats = convert(src, dst)
    print(f"Wrote {dst} ({stats['messages']} msgs, {stats['tool_calls']} tool calls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
