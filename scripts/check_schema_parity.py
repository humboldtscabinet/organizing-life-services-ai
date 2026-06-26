#!/usr/bin/env python3
"""
Check that infra/postgres/init.sql covers every ORM table and index.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.models import Base  # noqa: E402

INIT_SQL_PATH = Path("infra/postgres/init.sql")
TABLE_PATTERN = re.compile(r"CREATE TABLE IF NOT EXISTS\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
INDEX_PATTERN = re.compile(r"CREATE INDEX IF NOT EXISTS\s+([a-zA-Z0-9_]+)", re.IGNORECASE)


def main() -> int:
    init_sql = INIT_SQL_PATH.read_text(encoding="utf-8")
    defined_tables = {match.group(1) for match in TABLE_PATTERN.finditer(init_sql)}
    defined_indexes = {match.group(1) for match in INDEX_PATTERN.finditer(init_sql)}

    expected_tables = set(Base.metadata.tables.keys())
    expected_indexes = {
        index.name
        for table in Base.metadata.tables.values()
        for index in table.indexes
        if index.name
        and not all(column.primary_key for column in index.columns)
    }

    missing_tables = sorted(expected_tables - defined_tables)
    missing_indexes = sorted(expected_indexes - defined_indexes)

    if not missing_tables and not missing_indexes:
        print("Schema parity OK")
        return 0

    if missing_tables:
        print("Missing tables in init.sql:")
        for table in missing_tables:
            print(f"  - {table}")

    if missing_indexes:
        print("Missing indexes in init.sql:")
        for index in missing_indexes:
            print(f"  - {index}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
