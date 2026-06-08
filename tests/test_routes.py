"""
Route smoke tests.

The single most valuable safety net for this app: assert that the app boots,
the health endpoint works, and the auth boundary is enforced on every
registered API route. This catches broken imports (like a missing dependency)
and accidental removal of the API-key guard.
"""

from starlette.routing import Route


def test_health_ok(client):
    """Health endpoint requires no auth and always returns 200."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "ols-api"
    # DB may be down in CI/local (no Postgres) — both states are valid.
    assert body["status"] in {"ok", "degraded"}
    assert body["auth"] == "enabled"


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
    Every parameter-free /api route must reject an unauthenticated request
    with 401 (missing key). This proves the auth dependency is wired on all
    routers, not a hand-picked few.
    """
    routes = _api_routes(client)
    assert routes, "expected to discover /api routes"

    failures = []
    for route in routes:
        method = next(iter(route.methods - {"HEAD", "OPTIONS"}))
        resp = client.request(method, route.path)  # no API key
        if resp.status_code != 401:
            failures.append((method, route.path, resp.status_code))

    assert not failures, f"routes not enforcing auth (expected 401): {failures}"


def test_bad_key_is_forbidden(client):
    """A present-but-wrong key returns 403 (not 401, not 200)."""
    r = client.get("/api/dashboard/metrics", headers={"X-API-Key": "wrong"})
    assert r.status_code == 403


def test_valid_key_passes_auth(client, auth_headers):
    """
    A valid key gets PAST auth. The endpoint may still 500 (no DB/creds in
    test env) or 200, but it must NOT be 401/403 — that proves the key works.
    """
    r = client.get("/api/dashboard/metrics", headers=auth_headers)
    assert r.status_code not in (401, 403)
