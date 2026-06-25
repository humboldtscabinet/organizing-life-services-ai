#!/usr/bin/env python3
"""High-confidence secret scanner for tracked repository files."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SecretPattern:
    name: str
    regex: re.Pattern[str]


PATTERNS = [
    SecretPattern("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    SecretPattern("github-token", re.compile(r"\bgh[pousr]_[0-9A-Za-z_]{36,}\b")),
    SecretPattern("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    SecretPattern("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    SecretPattern("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{32,}\b")),
    SecretPattern("shopify-client-secret", re.compile(r"\bshpss_[0-9a-fA-F]{32,}\b")),
    SecretPattern("shopify-access-token", re.compile(r"\bshpat_[0-9a-fA-F]{32,}\b")),
    SecretPattern("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b")),
    SecretPattern("private-key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
]


SKIP_DIRS = {
    ".git",
    ".venv",
    ".venv-audit",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}

SKIP_FILES = {
    Path("tests/test_security_tools.py"),
}


def git_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return [Path(p.decode()) for p in result.stdout.split(b"\0") if p]


def should_skip(path: Path) -> bool:
    return path in SKIP_FILES or any(part in SKIP_DIRS for part in path.parts)


def read_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if should_skip(path) or not path.is_file():
            continue
        text = read_text(path)
        if text is None:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in PATTERNS:
                if pattern.regex.search(line):
                    findings.append(f"{path}:{line_number}: {pattern.name}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional paths to scan. Defaults to tracked git files.",
    )
    args = parser.parse_args()

    paths = args.paths or git_files()
    findings = scan(paths)
    if findings:
        print("Potential secrets found:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1

    print("No high-confidence secrets found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
