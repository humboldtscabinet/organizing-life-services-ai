import re
from pathlib import Path

import app.db.models  # noqa: F401
from app.db.database import Base

ROOT = Path(__file__).resolve().parents[1]


def test_orm_tables_have_sql_bootstrap_or_migration_coverage():
    """Every ORM table should exist in init SQL or an idempotent migration."""
    sql_files = [ROOT / "infra" / "postgres" / "init.sql"]
    sql_files.extend(sorted((ROOT / "infra" / "postgres" / "migrations").glob("*.sql")))
    sql = "\n".join(path.read_text() for path in sql_files)

    missing = []
    for table_name in sorted(Base.metadata.tables):
        pattern = rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table_name)}\b"
        if not re.search(pattern, sql, flags=re.IGNORECASE):
            missing.append(table_name)

    assert not missing, f"ORM tables missing SQL bootstrap/migration coverage: {missing}"
