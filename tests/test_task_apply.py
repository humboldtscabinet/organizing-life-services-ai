"""Allowlisted DashboardTask apply loop."""

from __future__ import annotations

from datetime import datetime

from app.services import dashboard_service
from app.services import task_apply_service as tas
from app.services.gtm_service import PHONE_EVENT_NAME


class _Task:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.task_type = kwargs.get("task_type", "seo")
        self.category = kwargs.get("category", "gtm_phone_clicks")
        self.priority = kwargs.get("priority", "HIGH")
        self.title = kwargs.get("title", "Restore GTM phone_call_clicks tracking")
        self.description = kwargs.get("description", "desc")
        self.finding = kwargs.get("finding", "finding")
        self.action_endpoint = kwargs.get("action_endpoint")
        self.action_kind = kwargs.get("action_kind")
        self.action_payload = kwargs.get("action_payload") or {}
        self.fingerprint = kwargs.get("fingerprint")
        self.status = kwargs.get("status", "pending")
        self.result = None
        self.created_at = datetime.utcnow()
        self.approved_at = None
        self.completed_at = None


class _FakeDb:
    def __init__(self, task):
        self.task = task
        self.added = []
        self.commits = 0

    def query(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.task

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = 100 + index

    def commit(self):
        self.commits += 1


def test_advisory_task_cannot_apply():
    task = _Task(action_kind=None)
    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=True, judge_verdict="PASS")
    assert result["status"] == "error"
    assert result["code"] == "advisory_task"


def test_never_apply_kinds_are_refused():
    task = _Task(action_kind="ads.budget_bid_keyword")
    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=True, judge_verdict="PASS")
    assert result["status"] == "error"
    assert result["code"] == "never_apply"


def test_deferred_kind_is_not_implemented():
    task = _Task(action_kind="ga4.unmark_junk_key_events")
    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=True, judge_verdict="PASS")
    assert result["status"] == "error"
    assert result["code"] == "not_implemented"


def test_gtm_apply_requires_human_confirmation():
    task = _Task(action_kind="gtm.ensure_phone_clicks")
    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=False)
    assert result["status"] == "error"
    assert "human_confirmed" in result["detail"]
    assert task.status == "pending"


def test_gtm_ensure_apply_creates_separate_publish_child(monkeypatch):
    task = _Task(
        action_kind="gtm.ensure_phone_clicks",
        action_payload={"create_version": True, "preview": {"tag": "would_create"}},
    )
    db = _FakeDb(task)

    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )

    def fake_ensure(**kwargs):
        assert kwargs["dry_run"] is False
        assert kwargs["create_version_after"] is True
        return {
            "status": "applied",
            "trigger": {"action": "created"},
            "tag": {"action": "created"},
            "version": {
                "version_path": "accounts/1/containers/2/versions/9",
                "name": "v9",
                "compiler_error": False,
            },
            "created": ["tag:OLS - phone_call_clicks"],
            "updated": [],
            "unchanged": [],
        }

    monkeypatch.setattr(
        "app.services.gtm_service.ensure_phone_call_clicks_tracking",
        fake_ensure,
    )

    result = tas.apply_task(db, 1, human_confirmed=True)

    assert result["status"] == "success"
    assert task.status == "completed"
    assert result["result"]["publish_task_id"]
    child = next(
        obj for obj in db.added if getattr(obj, "action_kind", None) == "gtm.publish_version"
    )
    assert child.action_payload["version_path"] == "accounts/1/containers/2/versions/9"
    assert child.status == "pending"


def test_gtm_ensure_unchanged_does_not_create_publish_child(monkeypatch):
    task = _Task(action_kind="gtm.ensure_phone_clicks")
    db = _FakeDb(task)
    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr(
        "app.services.gtm_service.ensure_phone_call_clicks_tracking",
        lambda **_k: {
            "status": "unchanged",
            "trigger": {"action": "unchanged"},
            "tag": {"action": "unchanged"},
            "version": None,
            "created": [],
            "updated": [],
            "unchanged": ["tag:OLS - phone_call_clicks"],
        },
    )

    result = tas.apply_task(db, 1, human_confirmed=True)
    assert result["status"] == "success"
    assert result["result"]["publish_task_id"] is None
    assert not any(
        getattr(obj, "action_kind", None) == "gtm.publish_version" for obj in db.added
    )


def test_gtm_publish_uses_frozen_version_path_only(monkeypatch):
    frozen = "accounts/1/containers/2/versions/9"
    task = _Task(
        action_kind="gtm.publish_version",
        action_payload={"version_path": frozen, "preview": {"action": "publish live"}},
    )
    published = {}

    def fake_publish(version_path):
        published["path"] = version_path
        return {
            "status": "published",
            "version_path": version_path,
            "version_id": "9",
            "name": "v9",
        }

    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr("app.services.gtm_service.publish_version", fake_publish)

    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=True)
    assert result["status"] == "success"
    assert published["path"] == frozen


def test_gtm_publish_rejects_missing_frozen_path(monkeypatch):
    task = _Task(action_kind="gtm.publish_version", action_payload={})
    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    called = {"value": False}

    def boom(_path):
        called["value"] = True
        raise AssertionError("must not publish without frozen path")

    monkeypatch.setattr("app.services.gtm_service.publish_version", boom)

    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=True)
    assert result["status"] == "error"
    assert called["value"] is False
    assert task.status == "failed"


def test_detector_noops_when_phone_clicks_already_firing(monkeypatch):
    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr(
        "app.services.ga4_service.count_named_events",
        lambda *_a, **_k: 5,
    )
    monkeypatch.setattr(
        "app.services.gtm_service.phone_click_ensure_needed",
        lambda: (_ for _ in ()).throw(AssertionError("must not dry-run GTM when events > 0")),
    )

    assert dashboard_service._generate_gtm_apply_tasks(days_back=7) == []


def test_detector_creates_ensure_task_on_drift_when_events_are_zero(monkeypatch):
    monkeypatch.setenv("GTM_CONTAINER_ID", "168770630")
    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr(
        "app.services.ga4_service.count_named_events",
        lambda *_a, **_k: 0,
    )
    monkeypatch.setattr(
        "app.services.gtm_service.phone_click_ensure_needed",
        lambda: {
            "needed": True,
            "plan": {
                "trigger": {"action": "would_create"},
                "tag": {"action": "would_create"},
            },
        },
    )

    tasks = dashboard_service._generate_gtm_apply_tasks(days_back=7)
    assert len(tasks) == 1
    assert tasks[0]["action_kind"] == "gtm.ensure_phone_clicks"
    assert tasks[0]["fingerprint"] == "gtm.ensure_phone_clicks:168770630"
    assert tasks[0]["action_payload"]["create_version"] is True


def test_detector_skips_when_workspace_already_correct(monkeypatch):
    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr(
        "app.services.ga4_service.count_named_events",
        lambda *_a, **_k: 0,
    )
    monkeypatch.setattr(
        "app.services.gtm_service.phone_click_ensure_needed",
        lambda: {
            "needed": False,
            "plan": {
                "trigger": {"action": "unchanged"},
                "tag": {"action": "unchanged"},
            },
        },
    )
    assert dashboard_service._generate_gtm_apply_tasks() == []


def test_detector_skips_when_gtm_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: False
    )
    assert dashboard_service._generate_gtm_apply_tasks() == []


def test_apply_route_requires_auth(client):
    response = client.post("/api/dashboard/tasks/1/apply")
    assert response.status_code == 401


def test_apply_route_dispatches_after_confirmation(client, auth_headers, monkeypatch):
    from app.db.database import get_db
    from app.main import app

    def fake_apply(_db, task_id, *, human_confirmed, judge_verdict):
        assert task_id == 7
        assert human_confirmed is True
        return {
            "status": "success",
            "task_id": 7,
            "action_kind": "gtm.ensure_phone_clicks",
            "result": {"status": "applied", "publish_task_id": 8},
        }

    monkeypatch.setattr("app.routes.dashboard.apply_task", fake_apply)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        response = client.post(
            "/api/dashboard/tasks/7/apply",
            params={"human_confirmed": "true"},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["result"]["publish_task_id"] == 8


def test_count_named_events_returns_none_without_config(monkeypatch):
    from app.services.ga4_service import count_named_events

    monkeypatch.delenv("GA4_PROPERTY_ID", raising=False)
    assert count_named_events(PHONE_EVENT_NAME) is None


def test_serialize_marks_applyable_pending_kinds():
    task = _Task(action_kind="gtm.publish_version", status="pending")
    payload = tas.serialize_dashboard_task(task)
    assert payload["applyable"] is True
    assert payload["deterministic"] is True

    advisory = _Task(action_kind=None, status="pending")
    assert tas.serialize_dashboard_task(advisory)["applyable"] is False


def test_ads_disable_bogus_pauses_frozen_id_only(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.google_ads_service.pause_conversion_action",
        lambda action_id: calls.append(action_id) or {"status": "paused", "conversion_action_id": action_id},
    )
    task = _Task(
        action_kind="ads.disable_bogus_conversions",
        action_payload={
            "conversion_action_id": 123,
            "name": "Page view",
            "target_status": "PAUSED",
        },
        status="pending",
    )
    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=True)
    assert result["status"] == "success"
    assert calls == [123]


def test_ads_disable_refuses_budget_fields():
    task = _Task(
        action_kind="ads.disable_bogus_conversions",
        action_payload={"conversion_action_id": 1, "budget": 50},
        status="pending",
    )
    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=True)
    assert result["status"] == "error"
    assert "budget" in result["detail"].lower() or "failed" in result["detail"].lower()
