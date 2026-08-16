from datetime import date, datetime

from app.services.gsc_watches import generate_gsc_watch_tasks


class _Rec:
    def __init__(self, query, page, clicks, impressions, ctr, position, dt):
        self.query = query
        self.page = page
        self.clicks = clicks
        self.impressions = impressions
        self.ctr = ctr
        self.position = position
        self.date = dt


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self.rows)


def test_gsc_watch_skips_until_due(monkeypatch):
    monkeypatch.setattr(
        "app.services.gsc_watches._aggregate_watch",
        lambda *_args, **_kwargs: {
            "impressions": 100,
            "clicks": 0,
            "ctr": 0.0,
            "position": 10.0,
            "row_count": 1,
        },
    )
    tasks = generate_gsc_watch_tasks(
        _FakeDb([]), today=date(2026, 8, 1), days_back=28
    )
    assert tasks == []


def test_gsc_watch_emits_fingerprint_after_due(monkeypatch):
    monkeypatch.setattr(
        "app.services.gsc_watches._aggregate_watch",
        lambda *_args, **_kwargs: {
            "impressions": 302,
            "clicks": 1,
            "ctr": 0.0033,
            "position": 10.6,
            "row_count": 1,
        },
    )
    monkeypatch.setattr(
        "app.services.dashboard_service._maybe_attach_frozen_meta",
        lambda task, *_args, **_kwargs: task,
    )
    tasks = generate_gsc_watch_tasks(
        _FakeDb([]), today=date(2026, 8, 16), days_back=28
    )
    fingerprints = {t["fingerprint"] for t in tasks}
    assert "gsc.watch:organizers-plural-14d:2026-08-08" in fingerprints
    assert "gsc.watch:tampa-hub-14d:2026-08-08" in fingerprints
    homepage = [t for t in tasks if t["action_payload"]["homepage"]]
    assert all(t.get("action_kind") is None for t in homepage)
