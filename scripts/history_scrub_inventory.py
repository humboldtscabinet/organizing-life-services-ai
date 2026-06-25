#!/usr/bin/env python3
"""
Scan likely high-risk text areas for secret material and write a hashed report.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TARGETS = ("dashboard", "docs", "conversations")
SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}
SKIP_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".pdf",
    ".pyc",
    ".sqlite",
    ".db",
    ".woff",
    ".woff2",
}

SECRET_PATTERNS = {
    "openai_api_key": re.compile(r"sk-(?:proj-|live-|test-)?[A-Za-z0-9_-]{20,}"),
    "anthropic_api_key": re.compile(r"sk-ant-[A-Za-z0-9_-]{16,}"),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
    "google_service_account": re.compile(
        r'"client_email"\s*:\s*"[^"]+\.iam\.gserviceaccount\.com"'
    ),
    "api_key_assignment": re.compile(
        r"(?im)^(?:OLS_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|SHOPIFY_ACCESS_TOKEN)\s*=\s*.+$"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a hashed history-scrub inventory report."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional paths to scan. Defaults to dashboard docs conversations.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("security/history-scrub/history-scan.local.json"),
        help="Path to the JSON report. Defaults to a gitignored local file.",
    )
    return parser.parse_args()


def _iter_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        if not target.exists():
            continue
        if target.is_file():
            files.append(target)
            continue
        for path in target.rglob("*"):
            if path.is_dir():
                if path.name in SKIP_DIRS:
                    continue
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            if path.name.endswith(".local.tsv") or path.name.endswith(".local.txt") or path.name.endswith(".local.json"):
                continue
            files.append(path)
    return sorted(set(files))


def _read_text(path: Path) -> str | None:
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
                return handle.read()

        sample = path.read_bytes()[:1024]
        if b"\0" in sample:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _hash_match(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def scan_paths(paths: list[Path]) -> dict:
    files = _iter_files(paths)
    counts = Counter()
    findings = []

    for path in files:
        text = _read_text(path)
        if text is None:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule_name, pattern in SECRET_PATTERNS.items():
                for match in pattern.finditer(line):
                    matched_text = match.group(0)
                    counts[rule_name] += 1
                    findings.append(
                        {
                            "path": str(path),
                            "line": line_number,
                            "rule": rule_name,
                            "match_length": len(matched_text),
                            "match_sha256_prefix": _hash_match(matched_text),
                        }
                    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": [str(path) for path in paths],
        "files_scanned": len(files),
        "total_findings": len(findings),
        "counts_by_rule": dict(sorted(counts.items())),
        "findings": findings,
    }


def main() -> int:
    args = parse_args()
    target_paths = [Path(path) for path in args.paths] if args.paths else [
        Path(name) for name in DEFAULT_TARGETS
    ]
    report = scan_paths(target_paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "Scanned "
        f"{report['files_scanned']} files across {len(target_paths)} target roots; "
        f"found {report['total_findings']} possible matches."
    )
    print(f"Report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
