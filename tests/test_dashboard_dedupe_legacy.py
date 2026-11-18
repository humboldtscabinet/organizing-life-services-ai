"""Legacy-row + timezone-safety coverage for recommendation de-duplication.

Two bugs are pinned here:

1. **Unkeyed/legacy rows.** Rows created before the ``dedupe_key`` column
   existed carry ``dedupe_key = NULL``. The keyed lookup can never match them,
   so the first run after deploy would re-create every open/dismissed
   recommendation. The runtime now recovers the key from the stored title and a
   new idempotent migration (007) backfills the column.

2. **Timezone mismatch (HIGH).** Postgres ``TIMESTAMPTZ`` columns read back
   timezone-aware, while ``utcnow()`` is naive. The dismissed-window comparison
   used to raise ``TypeError: can't compare offset-naive and offset-aware
   datetimes``, crashing ``generate_tasks`` after the first keyed task was
   dismissed. SQLite returns naive values, which is why CI missed it — so the
   fake-db tests below deliberately use timezone-AWARE datetimes, and a
   Postgres-backed test exercises the real driver read path.

Documented rule under test: a ``completed`` or ``executing`` task blocks a
re-created recommendation (see ``DEDUPE_OPEN_STATUSES``).
"""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import DashboardTask
from app.services import dashboard_service
from app.time_utils import utcnow


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # pragma: no cover - test shim
    return "JSON"


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeDb:
    """Stand-in session: ignores opaque SQL filters, returns stored rows.

    The dedupe helpers re-check keys/windows in Python, so returning the full
    set faithfully exercises their decision logic. (It cannot model the SQL
    ``category``+``title`` fallback, so end-to-end ``_existing_blocking_task``
    fall-through is covered by the SQLite/Postgres tests instead.)
    """

    def __init__(self, rows=None):
        self._rows = list(rows or [])

    def query(self, *_args):
        return _FakeQuery(self._rows)


def _aware_days_ago(days: int) -> datetime:
    """A timezone-AWARE UTC datetime, as Postgres TIMESTAMPTZ reads back."""
    return datetime.now(timezone.utc) - timedelta(days=days)


def _legacy_row(
    *, status, query="estate sale tampa", position="12.3", dismissed_at=None,
    created_at=None,
):
    """A legacy row: NULL dedupe_key, real content_ranking title pattern."""
    return SimpleNamespace(
        dedupe_key=None,
        task_type="seo",
        category="content_ranking",
        title=f"Create targeted content for '{query}' (position {position})",
        status=status,
        dismissed_at=dismissed_at,
        created_at=created_at if created_at is not None else _aware_days_ago(0),
        fingerprint=None,
    )


def _keyed_row(*, status, key, dismissed_at=None, created_at=None):
    return SimpleNamespace(
        dedupe_key=key,
        task_type="seo",
        category="content_ranking",
        title="Create targeted content for 'estate sale tampa' (position 12.0)",
        status=status,
        dismissed_at=dismissed_at,
        created_at=created_at if created_at is not None else _aware_days_ago(0),
        fingerprint=None,
    )


def _key(query="estate sale tampa"):
    return dashboard_service._dedupe_key("seo", "content_ranking", query)


def _task_data(query="estate sale tampa"):
    return {
        "task_type": "seo",
        "category": "content_ranking",
        "title": f"Create targeted content for '{query}' (position 12.0)",
        "dedupe_key": _key(query),
        "status": "pending",
    }


# --------------------------------------------------------------------------- #
# Timezone safety (these would raise TypeError on the pre-fix code)
# --------------------------------------------------------------------------- #


def test_as_naive_utc_strips_tzinfo():
    aware = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    naive = dashboard_service._as_naive_utc(aware)
    assert naive.tzinfo is None
    assert naive == datetime(2026, 1, 1, 12, 0)
    assert dashboard_service._as_naive_utc(None) is None


def test_keyed_dismissed_aware_inside_window_blocks():
    db = _FakeDb([_keyed_row(status="dismissed", key=_key(), dismissed_at=_aware_days_ago(5))])
    assert dashboard_service._existing_by_dedupe_key(db, _key()) is not None


def test_keyed_dismissed_aware_outside_window_does_not_block():
    db = _FakeDb([_keyed_row(status="dismissed", key=_key(), dismissed_at=_aware_days_ago(45))])
    assert dashboard_service._existing_by_dedupe_key(db, _key()) is None


def test_unkeyed_dismissed_aware_inside_window_blocks():
    db = _FakeDb([_legacy_row(status="dismissed", dismissed_at=_aware_days_ago(10))])
    assert (
        dashboard_service._existing_unkeyed_dedupe_task(db, _task_data(), _key())
        is not None
    )


def test_unkeyed_dismissed_aware_outside_window_does_not_block():
    db = _FakeDb([_legacy_row(status="dismissed", dismissed_at=_aware_days_ago(45))])
    assert (
        dashboard_service._existing_unkeyed_dedupe_task(db, _task_data(), _key())
        is None
    )


def test_unkeyed_dismissed_without_timestamp_uses_created_at():
    """Legacy dismissed row, no dismissed_at -> anchor on created_at (aware)."""
    db = _FakeDb(
        [_legacy_row(status="dismissed", dismissed_at=None, created_at=_aware_days_ago(3))]
    )
    assert (
        dashboard_service._existing_unkeyed_dedupe_task(db, _task_data(), _key())
        is not None
    )


# --------------------------------------------------------------------------- #
# Legacy / unkeyed key recovery
# --------------------------------------------------------------------------- #


def test_unkeyed_pending_blocks():
    db = _FakeDb([_legacy_row(status="pending")])
    assert (
        dashboard_service._existing_unkeyed_dedupe_task(db, _task_data(), _key())
        is not None
    )


def test_unkeyed_different_query_does_not_block():
    db = _FakeDb([_legacy_row(status="pending", query="estate sale tampa")])
    other = _task_data("probate cleanout clearwater")
    assert (
        dashboard_service._existing_unkeyed_dedupe_task(db, other, _key("probate cleanout clearwater"))
        is None
    )


def test_unkeyed_unparseable_title_does_not_block():
    row = _legacy_row(status="pending")
    row.title = "Investigate zero-click page: /pages/estate-sales"
    db = _FakeDb([row])
    assert (
        dashboard_service._existing_unkeyed_dedupe_task(db, _task_data(), _key())
        is None
    )


def test_computed_key_matches_dedupe_key_normalization():
    row = _legacy_row(status="pending", query="  Estate   SALE  Tampa ")
    assert dashboard_service._computed_dedupe_key_for_row(row) == "seo:content_ranking:estate sale tampa"


# --------------------------------------------------------------------------- #
# Documented completed/executing rule (both keyed and unkeyed)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("status", ["completed", "executing"])
def test_completed_or_executing_keyed_blocks(status):
    db = _FakeDb([_keyed_row(status=status, key=_key())])
    assert dashboard_service._existing_by_dedupe_key(db, _key()) is not None


@pytest.mark.parametrize("status", ["completed", "executing"])
def test_completed_or_executing_unkeyed_blocks(status):
    db = _FakeDb([_legacy_row(status=status)])
    assert (
        dashboard_service._existing_unkeyed_dedupe_task(db, _task_data(), _key())
        is not None
    )


# --------------------------------------------------------------------------- #
# End-to-end _existing_blocking_task over a real (SQLite) ORM session
# --------------------------------------------------------------------------- #


@pytest.fixture
def sqlite_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DashboardTask.__table__.create(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _insert(sqlite_db, *, status, dedupe_key=None, query="estate sale tampa",
            position="12.3", dismissed_at=None):
    task = DashboardTask(
        task_type="seo",
        category="content_ranking",
        priority="MEDIUM",
        title=f"Create targeted content for '{query}' (position {position})",
        dedupe_key=dedupe_key,
        status=status,
        dismissed_at=dismissed_at,
    )
    sqlite_db.add(task)
    sqlite_db.commit()
    sqlite_db.refresh(task)
    return task


def test_end_to_end_unkeyed_pending_is_skipped(sqlite_db):
    existing = _insert(sqlite_db, status="pending", dedupe_key=None)
    assert existing.dedupe_key is None
    blocker = dashboard_service._existing_blocking_task(sqlite_db, _task_data())
    assert blocker is not None and blocker.id == existing.id


def test_end_to_end_unkeyed_dismissed_inside_window_is_skipped(sqlite_db):
    existing = _insert(
        sqlite_db, status="dismissed", dedupe_key=None,
        dismissed_at=utcnow() - timedelta(days=10),
    )
    blocker = dashboard_service._existing_blocking_task(sqlite_db, _task_data())
    assert blocker is not None and blocker.id == existing.id


def test_end_to_end_different_query_is_created(sqlite_db):
    """No keyed or unkeyed match for this query -> allowed through."""
    _insert(sqlite_db, status="pending", dedupe_key=None, query="estate sale tampa")
    other = _task_data("probate cleanout clearwater")
    assert dashboard_service._existing_blocking_task(sqlite_db, other) is None


def test_end_to_end_keyed_pending_is_skipped(sqlite_db):
    existing = _insert(sqlite_db, status="pending", dedupe_key=_key())
    blocker = dashboard_service._existing_blocking_task(sqlite_db, _task_data())
    assert blocker is not None and blocker.id == existing.id


# --------------------------------------------------------------------------- #
# Postgres-backed test: real TIMESTAMPTZ driver path + backfill migration 007
# --------------------------------------------------------------------------- #

_PG_DSN = os.getenv("OLS_TEST_PG_DSN", "").strip()


def _pg_available():
    if not _PG_DSN:
        return False
    try:
        import psycopg2

        conn = psycopg2.connect(_PG_DSN, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


pg_backed = pytest.mark.skipif(
    not _pg_available(),
    reason="set OLS_TEST_PG_DSN to a reachable Postgres to run the TIMESTAMPTZ test",
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_DASHBOARD_TASKS_TIMESTAMPTZ_DDL = """
CREATE TABLE dashboard_tasks (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    finding TEXT,
    action_endpoint VARCHAR(500),
    action_kind VARCHAR(100),
    action_payload JSONB,
    fingerprint VARCHAR(300),
    dedupe_key VARCHAR(300),
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    delayed_until TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ
);
"""


def _run_sql_file(cur, rel_path):
    with open(os.path.join(_REPO_ROOT, rel_path), encoding="utf-8") as fh:
        cur.execute(fh.read())


@pg_backed
def test_postgres_timestamptz_and_backfill():
    import psycopg2
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm

    conn = psycopg2.connect(_PG_DSN)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS dashboard_tasks CASCADE;")
            cur.execute(_DASHBOARD_TASKS_TIMESTAMPTZ_DDL)
            # 198 legacy rows (30 open, 168 dismissed), NULL dedupe_key.
            cur.execute(
                """
                INSERT INTO dashboard_tasks (task_type, category, priority, title, status)
                SELECT 'seo', 'content_ranking', 'MEDIUM',
                       'Create targeted content for ''query ' || g ||
                       ''' (position 12.3)', 'pending'
                FROM generate_series(1, 30) g;
                """
            )
            cur.execute(
                """
                INSERT INTO dashboard_tasks
                    (task_type, category, priority, title, status, dismissed_at)
                SELECT 'seo', 'content_ranking', 'MEDIUM',
                       'Create targeted content for ''dismissed ' || g ||
                       ''' (position 9.0)', 'dismissed', NOW()
                FROM generate_series(1, 168) g;
                """
            )
            cur.execute("SELECT count(*) FROM dashboard_tasks WHERE dedupe_key IS NULL;")
            assert cur.fetchone()[0] == 198

            # Idempotent backfill: run twice; second run changes nothing.
            _run_sql_file(cur, "infra/postgres/migrations/007_dashboard_task_dedupe_backfill.sql")
            _run_sql_file(cur, "infra/postgres/migrations/007_dashboard_task_dedupe_backfill.sql")

            cur.execute("SELECT count(*) FROM dashboard_tasks WHERE dedupe_key IS NOT NULL;")
            assert cur.fetchone()[0] == 198
            cur.execute("SELECT count(*) FROM dashboard_tasks WHERE status = 'dismissed';")
            assert cur.fetchone()[0] == 168  # status untouched
            cur.execute(
                "SELECT dedupe_key FROM dashboard_tasks WHERE title LIKE '%%query 1''%%' LIMIT 1;"
            )
            assert cur.fetchone()[0] == "seo:content_ranking:query 1"

        engine = _ce(_PG_DSN)
        session = _sm(bind=engine)()
        try:
            row = (
                session.query(DashboardTask)
                .filter(DashboardTask.status == "dismissed")
                .first()
            )
            assert row.dismissed_at is not None
            assert row.dismissed_at.tzinfo is not None  # aware, as TIMESTAMPTZ reads
            # Keyed match after backfill, no TypeError on the aware comparison.
            assert (
                dashboard_service._existing_blocking_task(session, _task_data("dismissed 1"))
                is not None
            )
            # A genuinely new query still falls through and is allowed.
            assert (
                dashboard_service._existing_blocking_task(session, _task_data("brand new query"))
                is None
            )
        finally:
            session.close()
            engine.dispose()
    finally:
        conn.close()


@pg_backed
def test_postgres_unkeyed_fallback_without_backfill():
    """Before any backfill, an aware dismissed legacy row still blocks at runtime."""
    import psycopg2
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm

    conn = psycopg2.connect(_PG_DSN)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS dashboard_tasks CASCADE;")
            cur.execute(_DASHBOARD_TASKS_TIMESTAMPTZ_DDL)
            cur.execute(
                """
                INSERT INTO dashboard_tasks
                    (task_type, category, priority, title, status, dismissed_at)
                VALUES ('seo', 'content_ranking', 'MEDIUM',
                        'Create targeted content for ''estate sale tampa'' (position 12.3)',
                        'dismissed', NOW());
                """
            )
        engine = _ce(_PG_DSN)
        session = _sm(bind=engine)()
        try:
            blocker = dashboard_service._existing_blocking_task(
                session, _task_data("estate sale tampa")
            )
            assert blocker is not None
            assert blocker.dedupe_key is None  # matched via unkeyed fallback
        finally:
            session.close()
            engine.dispose()
    finally:
        conn.close()
