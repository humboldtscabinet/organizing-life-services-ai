"""Tests for GSC pagination behavior."""

from datetime import datetime

from app.services import gsc_service


class _FakeQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None


class _FakeDb:
    def __init__(self):
        self.added = []
        self.commit_count = 0

    def query(self, *_args, **_kwargs):
        return _FakeQuery()

    def add(self, record):
        self.added.append(record)

    def commit(self):
        self.commit_count += 1


class _FakeSearchAnalytics:
    def __init__(self, batches):
        self._batches = batches
        self.calls = 0

    def query(self, siteUrl, body):
        self.last_body = body
        self.site_url = siteUrl
        return self

    def execute(self):
        batch = self._batches[self.calls]
        self.calls += 1
        return {"rows": batch}


class _FakeService:
    def __init__(self, batches):
        self._search = _FakeSearchAnalytics(batches)

    def searchanalytics(self):
        return self._search


def test_pull_gsc_data_paginates_until_short_batch(monkeypatch):
    batches = [
        [
            {"keys": ["query a", "/a", "2026-06-01"], "clicks": 1, "impressions": 10, "ctr": 0.1, "position": 5.0},
        ]
        * 1000,
        [
            {"keys": ["query b", "/b", "2026-06-02"], "clicks": 2, "impressions": 20, "ctr": 0.1, "position": 6.0},
        ],
    ]

    fake_service = _FakeService(batches)
    monkeypatch.setattr(gsc_service, "_get_gsc_service", lambda: fake_service)
    monkeypatch.setenv("GSC_SITE_URL", "https://www.organizinglifeservices.com")

    db = _FakeDb()
    result = gsc_service.pull_gsc_data(db=db, days_back=7)

    assert result["status"] == "success"
    assert result["rows_fetched"] == 1001
    assert result["rows_inserted"] == 1001
    assert fake_service._search.calls == 2
    assert fake_service._search.last_body["startRow"] == 1000
    assert db.commit_count == 1

    inserted_dates = {record.date for record in db.added if hasattr(record, "date")}
    assert datetime.fromisoformat("2026-06-02") in inserted_dates
