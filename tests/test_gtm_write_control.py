"""Unit tests for GTM ensure_phone_call_clicks and gated SEO routes."""

from __future__ import annotations

import pytest


@pytest.fixture
def gtm_env(monkeypatch):
    monkeypatch.setenv("GTM_ACCOUNT_ID", "111")
    monkeypatch.setenv("GTM_CONTAINER_ID", "222")
    monkeypatch.setenv("GA4_MEASUREMENT_ID", "G-TEST123")


def _tel_trigger(*, trigger_id="10", path=None):
    return {
        "trigger_id": trigger_id,
        "name": "OLS - tel link click",
        "type": "linkClick",
        "path": path or f"accounts/111/containers/222/workspaces/1/triggers/{trigger_id}",
        "fingerprint": "fp-trigger",
        "filter": [
            {
                "type": "contains",
                "parameter": [
                    {"type": "template", "key": "arg0", "value": "{{Click URL}}"},
                    {"type": "template", "key": "arg1", "value": "tel:"},
                ],
            }
        ],
    }


def _phone_tag(*, tag_id="20", trigger_id="10", path=None):
    return {
        "tag_id": tag_id,
        "name": "OLS - phone_call_clicks",
        "type": "gaawe",
        "path": path or f"accounts/111/containers/222/workspaces/1/tags/{tag_id}",
        "fingerprint": "fp-tag",
        "firing_trigger_ids": [trigger_id],
        "blocking_trigger_ids": [],
        "paused": False,
        "parameter": [
            {"type": "boolean", "key": "sendEcommerceData", "value": "false"},
            {"type": "template", "key": "eventName", "value": "phone_call_clicks"},
            {
                "type": "template",
                "key": "measurementIdOverride",
                "value": "G-TEST123",
            },
        ],
    }


def test_ensure_phone_clicks_dry_run_would_create(gtm_env, monkeypatch):
    from app.services import gtm_service as gs

    monkeypatch.setattr(gs, "list_triggers", lambda **_: [])
    monkeypatch.setattr(gs, "list_tags", lambda **_: [])
    monkeypatch.setattr(
        gs, "_default_workspace", lambda: "accounts/111/containers/222/workspaces/1"
    )

    plan = gs.ensure_phone_call_clicks_tracking(dry_run=True, create_version_after=True)

    assert plan["dry_run"] is True
    assert plan["trigger"]["action"] == "would_create"
    assert plan["tag"]["action"] == "would_create"
    assert plan["version"]["action"] == "would_create_version"
    assert "trigger:OLS - tel link click" in plan["would_create"]
    assert "tag:OLS - phone_call_clicks" in plan["would_create"]


def test_ensure_phone_clicks_idempotent_unchanged(gtm_env, monkeypatch):
    from app.services import gtm_service as gs

    trigger = _tel_trigger()
    tag = _phone_tag()
    monkeypatch.setattr(gs, "list_triggers", lambda **_: [trigger])
    monkeypatch.setattr(gs, "list_tags", lambda **_: [tag])
    monkeypatch.setattr(
        gs, "_default_workspace", lambda: "accounts/111/containers/222/workspaces/1"
    )

    created = False

    def boom(*_a, **_k):
        nonlocal created
        created = True
        raise AssertionError("should not create when unchanged")

    monkeypatch.setattr(gs, "create_trigger", boom)
    monkeypatch.setattr(gs, "create_tag", boom)
    monkeypatch.setattr(gs, "update_trigger", boom)
    monkeypatch.setattr(gs, "update_tag", boom)

    plan = gs.ensure_phone_call_clicks_tracking(dry_run=False, create_version_after=False)

    assert plan["status"] == "unchanged"
    assert plan["trigger"]["action"] == "unchanged"
    assert plan["tag"]["action"] == "unchanged"
    assert created is False


def test_ensure_phone_clicks_apply_creates(gtm_env, monkeypatch):
    from app.services import gtm_service as gs

    monkeypatch.setattr(gs, "list_triggers", lambda **_: [])
    monkeypatch.setattr(
        gs,
        "list_tags",
        lambda **_: [
            {
                "tag_id": "1",
                "name": "GA4 Config",
                "type": "gaawc",
                "path": "…/tags/1",
                "fingerprint": "x",
                "firing_trigger_ids": ["2147479553"],
                "blocking_trigger_ids": [],
                "paused": False,
                "parameter": [],
            }
        ],
    )
    monkeypatch.setattr(
        gs, "_default_workspace", lambda: "accounts/111/containers/222/workspaces/1"
    )

    def fake_create_trigger(body, *, workspace_path=None):
        return _tel_trigger(trigger_id="99")

    def fake_create_tag(body, *, workspace_path=None):
        assert body["type"] == "gaawe"
        assert any(
            p.get("key") == "eventName" and p.get("value") == "phone_call_clicks"
            for p in body["parameter"]
        )
        assert body["firingTriggerId"] == ["99"]
        return _phone_tag(tag_id="88", trigger_id="99")

    version_called = {}

    def fake_create_version(name, notes="", *, workspace_path=None):
        version_called["name"] = name
        return {
            "version_id": "7",
            "version_path": "accounts/111/containers/222/versions/7",
            "name": name,
            "notes": notes,
            "compiler_error": False,
            "new_workspace_path": "accounts/111/containers/222/workspaces/2",
            "sync_status": None,
            "raw": {},
        }

    monkeypatch.setattr(gs, "create_trigger", fake_create_trigger)
    monkeypatch.setattr(gs, "create_tag", fake_create_tag)
    monkeypatch.setattr(gs, "create_version", fake_create_version)

    plan = gs.ensure_phone_call_clicks_tracking(dry_run=False, create_version_after=True)

    assert plan["status"] == "applied"
    assert plan["trigger"]["action"] == "created"
    assert plan["tag"]["action"] == "created"
    assert plan["version"]["action"] == "created_version"
    assert plan["version"]["version_path"] == "accounts/111/containers/222/versions/7"
    assert version_called["name"]


def test_gtm_ensure_requires_high_stakes(client, auth_headers, monkeypatch):
    called = False

    def fake_ensure(**_kwargs):
        nonlocal called
        called = True
        return {"status": "applied"}

    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr(
        "app.services.gtm_service.ensure_phone_call_clicks_tracking",
        fake_ensure,
    )

    response = client.post(
        "/api/seo/gtm/ensure-phone-clicks",
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert called is False


def test_gtm_ensure_dry_run_skips_gate(client, auth_headers, monkeypatch):
    def fake_ensure(**kwargs):
        assert kwargs.get("dry_run") is True
        return {
            "status": "dry_run",
            "dry_run": True,
            "would_create": ["trigger:OLS - tel link click"],
            "unchanged": [],
            "updated": [],
            "created": [],
            "trigger": {"action": "would_create"},
            "tag": {"action": "would_create"},
            "version": {"action": "would_create_version"},
        }

    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr(
        "app.services.gtm_service.ensure_phone_call_clicks_tracking",
        fake_ensure,
    )

    response = client.post(
        "/api/seo/gtm/ensure-phone-clicks",
        params={"dry_run": "true"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["result"]["dry_run"] is True


def test_gtm_ensure_runs_after_pass(client, auth_headers, monkeypatch):
    def fake_ensure(**kwargs):
        assert kwargs.get("dry_run") is False
        return {
            "status": "applied",
            "dry_run": False,
            "would_create": [],
            "unchanged": [],
            "updated": [],
            "created": ["tag:OLS - phone_call_clicks"],
            "trigger": {"action": "created"},
            "tag": {"action": "created"},
            "version": {
                "action": "created_version",
                "version_path": "accounts/1/containers/2/versions/3",
            },
        }

    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr(
        "app.services.gtm_service.ensure_phone_call_clicks_tracking",
        fake_ensure,
    )

    response = client.post(
        "/api/seo/gtm/ensure-phone-clicks",
        params={
            "human_confirmed": "true",
            "judge_verdict": "PASS",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["result"]["status"] == "applied"


def test_gtm_publish_requires_high_stakes(client, auth_headers, monkeypatch):
    called = False

    def fake_publish(version_path):
        nonlocal called
        called = True
        return {"status": "published", "version_path": version_path}

    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr("app.services.gtm_service.publish_version", fake_publish)

    response = client.post(
        "/api/seo/gtm/publish",
        params={"version_path": "accounts/1/containers/2/versions/3"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert called is False


def test_gtm_publish_runs_after_pass(client, auth_headers, monkeypatch):
    def fake_publish(version_path):
        return {
            "status": "published",
            "version_path": version_path,
            "version_id": "3",
            "name": "v3",
            "raw": {},
        }

    monkeypatch.setattr(
        "app.services.gtm_service.direct_api_available", lambda: True
    )
    monkeypatch.setattr("app.services.gtm_service.publish_version", fake_publish)

    response = client.post(
        "/api/seo/gtm/publish",
        params={
            "version_path": "accounts/1/containers/2/versions/3",
            "human_confirmed": "true",
            "judge_verdict": "PASS",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["result"]["version_path"] == "accounts/1/containers/2/versions/3"
