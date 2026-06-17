def test_shopify_write_requires_high_stakes_confirmation(client, auth_headers, monkeypatch):
    called = False

    def fake_create_redirect(from_path, to_path):
        nonlocal called
        called = True
        return {"status": "created", "from": from_path, "to": to_path}

    monkeypatch.setattr("app.routes.shopify.create_redirect", fake_create_redirect)

    response = client.post(
        "/api/shopify/redirects/create",
        params={"from_path": "/old", "to_path": "/new"},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert called is False


def test_shopify_write_runs_after_pass_and_human_confirmation(
    client, auth_headers, monkeypatch
):
    def fake_create_redirect(from_path, to_path):
        return {"status": "created", "from": from_path, "to": to_path}

    monkeypatch.setattr("app.routes.shopify.create_redirect", fake_create_redirect)

    response = client.post(
        "/api/shopify/redirects/create",
        params={
            "from_path": "/old",
            "to_path": "/new",
            "human_confirmed": "true",
            "judge_verdict": "PASS",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "created", "from": "/old", "to": "/new"}


def test_destructive_cleanup_dry_run_does_not_require_confirmation(
    client, auth_headers, monkeypatch
):
    def fake_cleanup(redirect_map, dry_run=True):
        return {"status": "dry_run", "count": len(redirect_map), "dry_run": dry_run}

    monkeypatch.setattr("app.routes.shopify.consolidate_thin_pages", fake_cleanup)

    response = client.post(
        "/api/shopify/cleanup/thin-pages",
        params={"dry_run": "true"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "dry_run"
    assert response.json()["dry_run"] is True


def test_destructive_cleanup_execution_requires_confirmation(
    client, auth_headers, monkeypatch
):
    called = False

    def fake_cleanup(redirect_map, dry_run=True):
        nonlocal called
        called = True
        return {"status": "completed"}

    monkeypatch.setattr("app.routes.shopify.consolidate_thin_pages", fake_cleanup)

    response = client.post(
        "/api/shopify/cleanup/thin-pages",
        params={"dry_run": "false"},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert called is False


def test_bulk_alt_push_requires_confirmation(client, auth_headers, monkeypatch):
    called = False

    def fake_background(force):
        nonlocal called
        called = True

    monkeypatch.setattr("app.routes.vision._run_alt_push_background", fake_background)

    response = client.post(
        "/api/vision/push-alt-text",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert called is False
