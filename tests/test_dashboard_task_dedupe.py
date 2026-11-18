"""De-duplication of recurring dashboard tasks (e.g. 'Create targeted content').

The recommendation detector runs daily and re-proposes the same advisory task
(same kind + query/target) every run. These tasks carry a stable ``dedupe_key``
so repeats collapse: a new task is skipped while a pending/approved task exists
for the key, or while a recently dismissed one is still inside the configurable
window (default 30 days). A task dismissed outside the window — or a different
query — is created.

Uses an in-memory SQLite session so the real ORM query path is exercised.
"""

from datetime import timedelta

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
    """Let the Postgres JSONB column type build on SQLite for tests."""
    return "JSON"


@pytest.fixture
def db():
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


QUERY = "estate sale tampa"
DEDUPE_KEY = dashboard_service.make_dedupe_key("seo", "content_ranking", QUERY)


def _task_data(query: str = QUERY, *, avg_pos: float = 12.3) -> dict:
    """A 'Create targeted content' task dict as the GSC detector builds it."""
    return {
        "task_type": "seo",
        "category": "content_ranking",
        "priority": "MEDIUM",
        "dedupe_key": dashboard_service.make_dedupe_key("seo", "content_ranking", query),
        "title": f"Create targeted content for '{query}' (position {avg_pos})",
        "description": "Create or optimize content to push to page 1.",
        "finding": f"Query near page 2: {query} at position {avg_pos}",
        "action_endpoint": None,
        "action_payload": None,
        "status": "pending",
    }


def _insert(db, *, status, dedupe_key=DEDUPE_KEY, title="existing", dismissed_at=None):
    task = DashboardTask(
        task_type="seo",
        category="content_ranking",
        priority="MEDIUM",
        title=title,
        dedupe_key=dedupe_key,
        status=status,
        dismissed_at=dismissed_at,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def test_pending_duplicate_is_skipped(db):
    """A pending task with the same dedupe key blocks a new one."""
    existing = _insert(db, status="pending")

    blocker = dashboard_service._existing_blocking_task(db, _task_data())

    assert blocker is not None
    assert blocker.id == existing.id


def test_approved_duplicate_is_skipped(db):
    """An approved task with the same dedupe key blocks a new one."""
    existing = _insert(db, status="approved")

    blocker = dashboard_service._existing_blocking_task(db, _task_data())

    assert blocker is not None
    assert blocker.id == existing.id


def test_dismissed_duplicate_inside_window_is_skipped(db):
    """A task dismissed inside the window still blocks a new one."""
    now = utcnow()
    existing = _insert(
        db,
        status="dismissed",
        dismissed_at=now - timedelta(days=10),
    )

    blocker = dashboard_service._existing_blocking_task(
        db, _task_data(), window_days=30, now=now
    )

    assert blocker is not None
    assert blocker.id == existing.id


def test_dismissed_duplicate_outside_window_is_created(db):
    """A task dismissed before the window no longer blocks; the new one is made."""
    now = utcnow()
    _insert(db, status="dismissed", dismissed_at=now - timedelta(days=45))

    blocker = dashboard_service._existing_blocking_task(
        db, _task_data(), window_days=30, now=now
    )

    assert blocker is None


def test_different_query_is_created(db):
    """A different query has a different dedupe key and is not blocked."""
    _insert(db, status="pending")

    other = _task_data(query="probate cleanout clearwater")

    blocker = dashboard_service._existing_blocking_task(db, other)

    assert blocker is None


def test_window_default_is_thirty_days(monkeypatch):
    monkeypatch.delenv("OLS_DEDUPE_DISMISSED_WINDOW_DAYS", raising=False)
    assert dashboard_service._dismissed_dedupe_window_days() == 30


def test_window_is_configurable_via_env(monkeypatch):
    monkeypatch.setenv("OLS_DEDUPE_DISMISSED_WINDOW_DAYS", "7")
    assert dashboard_service._dismissed_dedupe_window_days() == 7


def test_window_env_invalid_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("OLS_DEDUPE_DISMISSED_WINDOW_DAYS", "not-a-number")
    assert dashboard_service._dismissed_dedupe_window_days() == 30


def test_configured_window_applies_when_env_set(db, monkeypatch):
    """With a 7-day window, a task dismissed 10 days ago no longer blocks."""
    now = utcnow()
    _insert(db, status="dismissed", dismissed_at=now - timedelta(days=10))
    monkeypatch.setenv("OLS_DEDUPE_DISMISSED_WINDOW_DAYS", "7")

    # window_days omitted so the env-configured window is used.
    blocker = dashboard_service._existing_blocking_task(db, _task_data(), now=now)

    assert blocker is None
