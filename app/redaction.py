"""Utilities for keeping secrets out of stored payloads and API errors."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[redacted]"

SENSITIVE_KEY_PARTS = (
    "authorization",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "id_token",
    "client_secret",
    "private_key",
    "password",
    "secret",
    "session",
    "token",
)

SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(authorization\s*:\s*bearer\s+)([^\s,;]+)",
    ),
    re.compile(
        r"(?i)\b((?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|"
        r"client[_-]?secret|private[_-]?key|password|secret|token)\s*[:=]\s*)"
        r"([\"']?)[^\s,;&\"']+(\2)",
    ),
    re.compile(r"\bgh[pousr]_[0-9A-Za-z_]{36,}\b"),
    re.compile(r"\bshpat_[0-9a-fA-F]{32,}\b"),
    re.compile(r"\bshpss_[0-9a-fA-F]{32,}\b"),
    re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)


def is_sensitive_key(key: object) -> bool:
    """Return true when a JSON/object key is likely to contain a secret."""
    normalized = str(key).strip().lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def truncate_text(value: str, max_length: int) -> str:
    """Bound user-supplied text while leaving a clear truncation marker."""
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 15]}...[truncated]"


def redact_sensitive_text(value: object, *, max_length: int | None = None) -> str:
    """Redact common secret shapes from a string-like value."""
    text = str(value)
    for pattern in SECRET_PATTERNS:
        if pattern.groups >= 3:
            text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}{m.group(3)}", text)
        elif pattern.groups >= 2:
            text = pattern.sub(lambda m: f"{m.group(1)}{REDACTED}", text)
        else:
            text = pattern.sub(REDACTED, text)
    if max_length is not None:
        text = truncate_text(text, max_length)
    return text


def sanitize_jsonish(
    value: Any,
    *,
    max_string_length: int = 1000,
    max_depth: int = 4,
    max_items: int = 50,
) -> Any:
    """
    Return a JSON-serializable, size-bounded, secret-redacted copy of value.

    This is intentionally conservative: it favors preserving enough context to
    debug an alert while preventing raw command output or credentials from being
    stored in Postgres and shown in the dashboard.
    """
    if max_depth < 0:
        return "[max-depth-exceeded]"

    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                sanitized["_truncated_items"] = True
                break
            key_text = truncate_text(str(key), 120)
            if is_sensitive_key(key_text):
                sanitized[key_text] = REDACTED
            else:
                sanitized[key_text] = sanitize_jsonish(
                    item,
                    max_string_length=max_string_length,
                    max_depth=max_depth - 1,
                    max_items=max_items,
                )
        return sanitized

    if isinstance(value, str):
        return redact_sensitive_text(value, max_length=max_string_length)

    if isinstance(value, bool | int | float) or value is None:
        return value

    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        items = [
            sanitize_jsonish(
                item,
                max_string_length=max_string_length,
                max_depth=max_depth - 1,
                max_items=max_items,
            )
            for item in list(value)[:max_items]
        ]
        if len(value) > max_items:
            items.append("[truncated-items]")
        return items

    return redact_sensitive_text(repr(value), max_length=max_string_length)


def bounded_json_object(value: Any, *, max_bytes: int = 12_000) -> dict[str, Any] | None:
    """Sanitize a mapping and cap its serialized size."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return {"value": sanitize_jsonish(value)}

    sanitized = sanitize_jsonish(value)
    encoded = json.dumps(sanitized, sort_keys=True, default=str)
    if len(encoded.encode("utf-8")) <= max_bytes:
        return sanitized

    return {
        "_truncated": True,
        "_reason": f"details exceeded {max_bytes} bytes after sanitization",
    }
