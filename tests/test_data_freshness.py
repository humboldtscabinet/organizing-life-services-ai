from datetime import datetime, timedelta

from app.services.ga4_service import LEAD_EVENT_NAMES, _pull_named_events, sum_stored_lead_events
from app.services.ops_alert_service import classify_ingest_freshness


class _Row:
    def __init__(self, event_name, date_str, event_count, key_events=None):
        self.dimension_values = [
            type("V", (), {"value": event_name})(),
            type("V", (), {"value": date_str})(),
        ]
        metrics = [type("V", (), {"value": str(event_count)})()]
        if key_events is not None:
            metrics.append(type("V", (), {"value": str(key_events)})())
        self.metric_values = metrics


class _Response:
    def __init__(self, rows):
        self.rows = rows


class _Client:
    def __init__(self, rows, fail_key_events=False):
        self.rows = rows
        self.fail_key_events = fail_key_events
        self.calls = 0

    def run_report(self, request):
        self.calls += 1
        metric_names = [m.name for m in request.metrics]
        if self.fail_key_events and "keyEvents" in metric_names:
            raise RuntimeError("keyEvents not available")
        return _Response(self.rows)


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows


class _FakeDb:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.upserts = []

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self.rows)

    def add(self, obj):
        self.rows.append(obj)


def test_classify_ingest_freshness_empty_is_critical():
    now = datetime(2026, 8, 16, 18, 0, 0)
    result = classify_ingest_freshness(None, now=now)
    assert result["stale"] is True
    assert result["severity"] == "CRITICAL"
    assert result["age_hours"] is None


def test_classify_ingest_freshness_warning_and_fresh():
    now = datetime(2026, 8, 16, 18, 0, 0)
    stale = classify_ingest_freshness(now - timedelta(hours=40), now=now)
    assert stale["stale"] is True
    assert stale["severity"] == "WARNING"
    critical = classify_ingest_freshness(now - timedelta(hours=80), now=now)
    assert critical["severity"] == "CRITICAL"
    fresh = classify_ingest_freshness(now - timedelta(hours=10), now=now)
    assert fresh["stale"] is False
    assert fresh["severity"] is None


def test_pull_named_events_stores_eventcount_under_named_events_report(monkeypatch):
    from app.services import ga4_service

    captured = []

    def fake_upsert(db, **kwargs):
        captured.append(kwargs)
        return "inserted"

    monkeypatch.setattr(ga4_service, "_upsert_ga4", fake_upsert)
    client = _Client(
        [
            _Row("form_submit", "20260815", 3, 3),
            _Row("phone_call_clicks", "20260815", 5, 5),
        ]
    )
    inserted, updated = _pull_named_events(
        object(),
        client=client,
        property_id="396184354",
        start_date=datetime(2026, 8, 9).date(),
        end_date=datetime(2026, 8, 15).date(),
    )
    assert inserted == 4
    assert updated == 0
    reports = {row["data"]["report"] for row in captured}
    assert reports == {"named_events"}
    names = {(row["metric_name"], row["dimension_value"]) for row in captured}
    assert ("eventCount", "form_submit") in names
    assert ("eventCount", "phone_call_clicks") in names
    assert ("keyEvents", "form_submit") in names


def test_sum_stored_lead_events_ignores_page_view():
    class _Rec:
        def __init__(self, name, value, date, report="named_events"):
            self.metric_name = "eventCount"
            self.dimension_name = "eventName"
            self.dimension_value = name
            self.metric_value = value
            self.date = date
            self.data = {"report": report}

    now = datetime(2026, 8, 16)
    db = _FakeDb(
        [
            _Rec("form_submit", 2, now),
            _Rec("phone_call_clicks", 5, now),
            _Rec("page_view", 99, now),
        ]
    )
    result = sum_stored_lead_events(db, days_back=7)
    assert result["form_submit"] == 2
    assert result["phone_call_clicks"] == 5
    assert result["total_leads"] == 7
    assert "page_view" not in result
    assert set(LEAD_EVENT_NAMES) == {"form_submit", "phone_call_clicks"}
