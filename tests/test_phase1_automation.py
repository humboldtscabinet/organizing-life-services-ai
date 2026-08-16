"""Tests for Phase 1 automation service."""

from types import SimpleNamespace

from app.services import phase1_automation_service as phase1


class _FakeAlert:
    id = 42


def test_run_phase1_cycle_reports_partial_when_pull_fails(monkeypatch):
    db = object()

    monkeypatch.setattr(phase1, "pull_gsc_data", lambda *_args, **_kwargs: {"status": "error", "detail": "boom"})
    monkeypatch.setattr(phase1, "pull_ga4_data", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "pull_google_ads_data", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "pull_gbp_data", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "pull_shopify_orders", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "push_gsc_to_sheets", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "push_ga4_to_sheets", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "push_google_ads_to_sheets", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "generate_tasks", lambda *_args, **_kwargs: {"status": "success", "tasks_created": 2})
    monkeypatch.setattr(
        phase1,
        "schedule_weekly_content",
        lambda *_args, **_kwargs: {"status": "success", "tasks_created": 1},
    )
    monkeypatch.setattr(phase1, "create_alert", lambda *_args, **_kwargs: _FakeAlert())
    monkeypatch.setattr(
        phase1,
        "check_data_freshness",
        lambda *_args, **_kwargs: {"status": "success", "stale_channels": []},
    )

    result = phase1.run_phase1_cycle(db, days_back=7, schedule_content_count=1)

    assert result["status"] == "partial"
    assert result["failed_steps"] == 1
    assert result["alert_id"] == 42
    assert result["tasks_generated"]["tasks_created"] == 2
    assert result["content_scheduled"]["tasks_created"] == 1


def test_run_phase1_cycle_success(monkeypatch):
    db = object()

    monkeypatch.setattr(phase1, "pull_gsc_data", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "pull_ga4_data", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "pull_google_ads_data", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "pull_gbp_data", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "pull_shopify_orders", lambda *_args, **_kwargs: {"status": "success"})
    monkeypatch.setattr(phase1, "generate_tasks", lambda *_args, **_kwargs: {"status": "success", "tasks_created": 0})
    monkeypatch.setattr(
        phase1,
        "schedule_weekly_content",
        lambda *_args, **_kwargs: {"status": "all_scheduled", "tasks_created": 0},
    )
    monkeypatch.setattr(phase1, "create_alert", lambda *_args, **_kwargs: SimpleNamespace(id=7))
    monkeypatch.setattr(
        phase1,
        "check_data_freshness",
        lambda *_args, **_kwargs: {"status": "success", "stale_channels": []},
    )

    result = phase1.run_phase1_cycle(db, push_to_sheets=False)

    assert result["status"] == "success"
    assert result["failed_steps"] == 0
    assert "pushes" not in result or result["pushes"] == {}
