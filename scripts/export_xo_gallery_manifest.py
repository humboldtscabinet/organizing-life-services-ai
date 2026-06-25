#!/usr/bin/env python3
"""
Convert a local XO gallery manifest JSON file into a flat CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _gallery_items(payload: dict) -> list[tuple[str, dict]]:
    galleries = payload.get("galleries", payload)
    if not isinstance(galleries, dict):
        raise ValueError("Expected a top-level 'galleries' object in the manifest JSON.")

    def sort_key(item: tuple[str, dict]) -> tuple[int, str]:
        gallery_id = str(item[0])
        if gallery_id.isdigit():
            return (0, f"{int(gallery_id):012d}")
        return (1, gallery_id)

    return sorted(galleries.items(), key=sort_key)


def export_manifest(input_path: Path, output_path: Path, base_url: str) -> int:
    with input_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    rows_written = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["gallery_id", "gallery_name", "image_number", "filename", "image_url"])

        for gallery_id, gallery in _gallery_items(payload):
            gallery_name = gallery.get("name", f"Gallery {gallery_id}")
            filenames = gallery.get("filenames") or []

            for index, filename in enumerate(filenames, start=1):
                writer.writerow([
                    gallery_id,
                    gallery_name,
                    index,
                    filename,
                    f"{base_url}{filename}" if base_url else "",
                ])
                rows_written += 1

    return rows_written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Flatten a local XO gallery manifest into CSV for spreadsheet review."
    )
    parser.add_argument(
        "--input",
        default="data/xo_gallery_images.json",
        help="Path to the local XO gallery manifest JSON file.",
    )
    parser.add_argument(
        "--output",
        default="data/xo_gallery_manifest.csv",
        help="Where to write the flattened CSV output.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Optional image base URL to prepend to each filename.",
    )
    args = parser.parse_args()

    rows_written = export_manifest(
        input_path=Path(args.input),
        output_path=Path(args.output),
        base_url=args.base_url,
    )
    print(f"Wrote {rows_written} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
