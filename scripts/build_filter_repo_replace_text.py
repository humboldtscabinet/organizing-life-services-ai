#!/usr/bin/env python3
"""
Build a git-filter-repo --replace-text file from a local TSV manifest.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

VALID_MATCH_TYPES = {"literal", "regex"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a git-filter-repo replace-text expressions file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the local TSV manifest with label/match_type/find/replace columns.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to the generated git-filter-repo expressions file.",
    )
    return parser.parse_args()


def _normalize_value(value: str, *, field_name: str, row_number: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"Row {row_number}: {field_name} cannot be blank.")
    if "\n" in normalized or "\r" in normalized:
        raise ValueError(f"Row {row_number}: {field_name} cannot contain newlines.")
    if "==>" in normalized:
        raise ValueError(
            f"Row {row_number}: {field_name} cannot contain '==>' because "
            "git-filter-repo uses it as the separator."
        )
    return normalized


def build_expressions(input_path: Path) -> list[str]:
    if not input_path.exists():
        raise FileNotFoundError(f"Manifest not found: {input_path}")

    with input_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        expected_columns = {"label", "match_type", "find", "replace"}
        if reader.fieldnames is None or set(reader.fieldnames) != expected_columns:
            raise ValueError(
                "Manifest must be a tab-separated file with exactly these "
                "columns: label, match_type, find, replace"
            )

        expressions: list[str] = []
        for row_number, row in enumerate(reader, start=2):
            label = (row.get("label") or "").strip()
            match_type = (row.get("match_type") or "").strip().lower()
            find_value = row.get("find") or ""
            replace_value = row.get("replace") or ""

            if not any((label, match_type, find_value, replace_value)):
                continue

            if match_type not in VALID_MATCH_TYPES:
                raise ValueError(
                    f"Row {row_number}: match_type must be one of "
                    f"{sorted(VALID_MATCH_TYPES)}."
                )

            find_value = _normalize_value(
                find_value,
                field_name="find",
                row_number=row_number,
            )
            replace_value = _normalize_value(
                replace_value,
                field_name="replace",
                row_number=row_number,
            )

            prefix = "" if match_type == "literal" else f"{match_type}:"
            expressions.append(f"{prefix}{find_value}==>{replace_value}")

        return expressions


def main() -> int:
    args = parse_args()
    expressions = build_expressions(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(expressions) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(expressions)} git-filter-repo expressions to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
