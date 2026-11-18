"""De-duplication of recommendation tasks (e.g. 'Create targeted content').

The daily job used to mint a new content_ranking task every run because the
task title embeds the current average position, which drifts day to day. These
tests pin the dedupe-key behaviour: pending/approved duplicates and recently
dismissed duplicates are suppressed, while dismissals outside the configurable
window and genuinely different queries are allowed through.
"""

from datetime import timedelta
from types import SimpleNamespace

from app.services import dashboard_service
from app.time_utils import utcnow


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
    """Minimal stand-in: ignores opaque SQL filters and returns stored rows.

    ``_existing_by_dedupe_key`` re-checks the key in Python, so returning the
    full set here faithfully exercises the production decision logic.
    """

    def __init__(self, rows=None):
        self._rows = list(rows or [])
        self.committed = False

    def query(self, *_args):
        return _FakeQuery(self._rows)

    def add(self, obj):
        self._rows.append(obj)

    def commit(self):
        self.committed = True


def _stored(dedupe_key, status, *, created_days_ago=0, dismissed_days_ago=None):
    now = utcnow()
    dismissed_at = (
        now - timedelta(days=dismissed_days_ago)
        if dismissed_days_ago is not None
        else None
    )
    return SimpleNamespace(
        dedupe_key=dedupe_key,
        status=status,
        created_at=now - timedelta(days=created_days_ago),
        dismissed_at=dismissed_at,
        title="Create targeted content for 'estate sale tampa' (position 12.0)",
        category="content_ranking",
        fingerprint=None,
    )


def _task_data(query):
    return {
        "task_type": "seo",
        "category": "content_ranking",
        "title": f"Create targeted content for '{query}' (position 12.0)",
        "dedupe_key": dashboard_service._dedupe_key("seo", "content_ranking", query),
        "status": "pending",
    }


def test_dedupe_key_is_stable_across_position_and_casing():
    key_lo = dashboard_service._dedupe_key("seo", "content_ranking", "Estate Sale Tampa")
    key_hi = dashboard_service._dedupe_key("seo", "content_ranking", "estate   sale tampa")
    assert key_lo == key_hi == "seo:content_ranking:estate sale tampa"


def test_pending_duplicate_is_skipped():
    query = "estate sale tampa"
    key = dashboard_service._dedupe_key("seo", "content_ranking", query)
    db = _FakeDb([_stored(key, "pending")])

    assert dashboard_service._existing_blocking_task(db, _task_data(query)) is not None


def test_approved_duplicate_is_skipped():
    query = "estate sale tampa"
    key = dashboard_service._dedupe_key("seo", "content_ranking", query)
    db = _FakeDb([_stored(key, "approved")])

    assert dashboard_service._existing_blocking_task(db, _task_data(query)) is not None


def test_dismissed_duplicate_inside_window_is_skipped():
    query = "estate sale tampa"
    key = dashboard_service._dedupe_key("seo", "content_ranking", query)
    db = _FakeDb([_stored(key, "dismissed", dismissed_days_ago=5)])

    assert dashboard_service._existing_blocking_task(db, _task_data(query)) is not None


def test_dismissed_duplicate_outside_window_is_created():
    query = "estate sale tampa"
    key = dashboard_service._dedupe_key("seo", "content_ranking", query)
    db = _FakeDb([_stored(key, "dismissed", dismissed_days_ago=45)])

    assert dashboard_service._existing_blocking_task(db, _task_data(query)) is None


def test_different_query_is_created():
    key = dashboard_service._dedupe_key("seo", "content_ranking", "estate sale tampa")
    db = _FakeDb([_stored(key, "pending")])

    other = _task_data("estate cleanout clearwater")
    assert dashboard_service._existing_blocking_task(db, other) is None


def test_dismissed_window_is_configurable(monkeypatch):
    query = "estate sale tampa"
    key = dashboard_service._dedupe_key("seo", "content_ranking", query)
    # A task dismissed 10 days ago is outside a 7-day window -> re-created.
    monkeypatch.setenv("OLS_DEDUPE_DISMISSED_WINDOW_DAYS", "7")
    db = _FakeDb([_stored(key, "dismissed", dismissed_days_ago=10)])
    assert dashboard_service._existing_blocking_task(db, _task_data(query)) is None

    # Same row is inside a 90-day window -> suppressed.
    monkeypatch.setenv("OLS_DEDUPE_DISMISSED_WINDOW_DAYS", "90")
    assert dashboard_service._existing_blocking_task(db, _task_data(query)) is not None


def test_invalid_window_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("OLS_DEDUPE_DISMISSED_WINDOW_DAYS", "not-a-number")
    assert (
        dashboard_service._dismissed_dedupe_window_days()
        == dashboard_service.DEFAULT_DISMISSED_DEDUPE_WINDOW_DAYS
    )


def test_dismissed_without_timestamp_falls_back_to_created_at():
    """Legacy dismissed rows (no dismissed_at) use created_at for the window."""
    query = "estate sale tampa"
    key = dashboard_service._dedupe_key("seo", "content_ranking", query)
    recent = SimpleNamespace(
        dedupe_key=key,
        status="dismissed",
        created_at=utcnow() - timedelta(days=3),
        dismissed_at=None,
        title="",
        category="content_ranking",
        fingerprint=None,
    )
    assert dashboard_service._existing_blocking_task(_FakeDb([recent]), _task_data(query)) is not None


def test_dismiss_task_records_dismissed_at():
    task = SimpleNamespace(
        id=1,
        status="pending",
        title="Create targeted content for 'estate sale tampa' (position 12.0)",
        dismissed_at=None,
    )
    db = _FakeDb([task])

    result = dashboard_service.dismiss_task(db, 1)

    assert result["status"] == "success"
    assert task.status == "dismissed"
    assert task.dismissed_at is not None
    assert db.committed is True


def test_generate_gsc_tasks_attaches_stable_dedupe_key():
    """The content_ranking task carries a position-independent dedupe key."""
    rows = [
        SimpleNamespace(
            page="https://organizinglifeservices.com/pages/estate-sales",
            query="estate sale tampa",
            clicks=6,
            impressions=120,
            ctr=0.05,  # >= 3% so Rule 1 (low-CTR) does not fire; isolates Rule 2
            position=12.0,
            date=utcnow() - timedelta(days=1),
        )
    ]

    class _GscDb:
        def query(self, _model):
            return _FakeQuery(rows)

    tasks = dashboard_service._generate_gsc_tasks(_GscDb(), utcnow() - timedelta(days=7))
    content_tasks = [t for t in tasks if t["category"] == "content_ranking"]
    assert content_tasks, "expected a content_ranking task"
    assert (
        content_tasks[0]["dedupe_key"]
        == "seo:content_ranking:estate sale tampa"
    )
