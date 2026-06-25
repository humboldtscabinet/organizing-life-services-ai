"""
Route smoke tests.

The single most valuable safety net for this app: assert that the app boots,
the health endpoint works, and the auth boundary is enforced on every
registered API route. This catches broken imports (like a missing dependency)
and accidental removal of the API-key guard.
"""

import subprocess
import sys

import pytest
from starlette.routing import Route


def test_health_ok(client):
    """Compatibility health stays human-readable without auth."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "ols-api"
    assert body["status"] in {"ok", "degraded"}
    assert body["auth"] == "enabled"


def test_health_live_stays_up_when_db_is_down(client, monkeypatch):
    """Liveness must stay green even if readiness dependencies fail."""
    import app.main as main

    monkeypatch.setattr(main, "_database_check", lambda: ("error", "db down"))

    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_ready_reports_dependency_failures(client, monkeypatch):
    """Readiness must fail closed when the database is unavailable."""
    import app.main as main

    monkeypatch.setattr(main, "_database_check", lambda: ("error", "db down"))

    r = client.get("/health/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "error"
    assert "Database connection failed" in body["issues"]


def test_openapi_schema_builds(client):
    """If the OpenAPI schema renders, every router imported cleanly."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "paths" in r.json()


def _api_routes(client) -> list[Route]:
    app = client.app
    return [
        r
        for r in app.routes
        if isinstance(r, Route)
        and r.path.startswith("/api")
        and "{" not in r.path  # skip path-param routes for the generic sweep
    ]


def test_all_api_routes_require_key(client):
    """
    Every registered /api route should include the auth dependency, even when
    the route has additional validation requirements.
    """
    routes = _api_routes(client)
    assert routes, "expected to discover /api routes"

    failures = []
    for route in routes:
        dependency_calls = {
            getattr(getattr(dependency, "call", None), "__name__", "")
            for dependency in route.dependant.dependencies
        }
        if "require_api_key" not in dependency_calls:
            failures.append(route.path)

    assert not failures, f"routes missing auth dependency: {failures}"


def test_representative_route_without_key_is_unauthorized(client):
    """Representative authenticated routes should reject missing keys at runtime."""
    routes = [
        "/api/dashboard/metrics",
        "/api/vision/gallery-structure",
        "/api/seo/ads/conversion-audit",
    ]
    for path in routes:
        response = client.get(path)
        assert response.status_code == 401, path


def test_bad_key_is_forbidden(client):
    """A present-but-wrong key returns 403 (not 401, not 200)."""
    r = client.get("/api/dashboard/metrics", headers={"X-API-Key": "wrong"})
    assert r.status_code == 403


def test_method_not_allowed_uses_specific_error_code(client, auth_headers):
    response = client.get("/api/vision/analyze", headers=auth_headers)
    assert response.status_code == 405
    body = response.json()
    assert body["status"] == "error"
    assert body["code"] == "method_not_allowed"


def test_valid_key_passes_auth(client, auth_headers):
    """
    A valid key gets past auth and reaches the endpoint implementation.
    """
    r = client.get("/api/vision/gallery-structure", headers=auth_headers)
    assert r.status_code == 410


def test_cors_allows_only_configured_dev_origins(client):
    allowed = client.options(
        "/api/dashboard/metrics",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-credentials" not in allowed.headers

    blocked = client.options(
        "/api/dashboard/metrics",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    assert blocked.headers.get("access-control-allow-origin") is None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/vision/gallery-structure"),
    ],
)
def test_retired_vision_helper_endpoints_return_gone(client, auth_headers, method, path):
    response = client.request(method, path, headers=auth_headers, json={})
    assert response.status_code == 410
    body = response.json()
    assert body["status"] == "error"
    assert body["code"] == "endpoint_retired"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/vision/save-file"),
        ("GET", "/api/vision/store-token"),
        ("GET", "/api/vision/get-token"),
        ("POST", "/api/vision/xo-proxy"),
    ],
)
def test_vision_debug_helpers_are_disabled_by_default(
    client,
    auth_headers,
    method,
    path,
):
    response = client.request(method, path, headers=auth_headers, json={})
    assert response.status_code == 404
    assert response.json()["status"] == "error"


def test_static_data_directory_is_not_public(client):
    response = client.get("/static/xo_gallery_images.json")
    assert response.status_code == 404


def test_unavailable_dependencies_are_reported_as_503(client, auth_headers, monkeypatch):
    import app.services.google_ads_service as google_ads_service

    monkeypatch.setattr(google_ads_service, "direct_api_available", lambda: False)

    response = client.get("/api/seo/ads/conversion-audit", headers=auth_headers)
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["code"] == "service_unavailable"


def test_vision_analyze_rejects_unsupported_source(client, auth_headers):
    response = client.post(
        "/api/vision/analyze",
        headers=auth_headers,
        params={"source": "mystery"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["code"] == "bad_request"


def test_vision_analyze_local_requires_imported_manifest(
    client,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    import app.routes.vision as vision_routes

    missing_manifest = tmp_path / "missing-xo-gallery.json"
    monkeypatch.setattr(
        vision_routes,
        "XO_GALLERY_DATA_FILE",
        str(missing_manifest),
    )

    response = client.post(
        "/api/vision/analyze",
        headers=auth_headers,
        params={"source": "local"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert body["code"] == "not_found"


def test_seo_pipeline_skips_push_when_audit_fails(client, auth_headers, monkeypatch):
    import app.routes.seo as seo_routes

    push_called = {"value": False}

    monkeypatch.setattr(
        seo_routes,
        "run_seo_audit",
        lambda db, days_back: {"status": "error", "detail": "GSC upstream timeout"},
    )

    def _unexpected_push(*args, **kwargs):
        push_called["value"] = True
        return {"status": "success"}

    monkeypatch.setattr(seo_routes, "push_audit_to_sheets", _unexpected_push)

    response = client.post("/api/seo/audit/push-to-sheets", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["push"]["status"] == "skipped"
    assert not push_called["value"]


def test_missing_api_key_configuration_fails_fast(monkeypatch):
    from app.settings import get_settings, validate_runtime_settings

    get_settings.cache_clear()
    monkeypatch.delenv("OLS_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        validate_runtime_settings()
    monkeypatch.setenv("OLS_API_KEY", "test-suite-api-key")
    get_settings.cache_clear()


def test_schema_parity_script_passes():
    result = subprocess.run(
        [sys.executable, "scripts/check_schema_parity.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
