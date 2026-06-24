import stat


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


def test_vision_debug_tools_disabled_by_default(client, auth_headers):
    endpoints = [
        ("GET", "/api/vision/debug/test-mutation"),
        ("GET", "/api/vision/debug/alt-text-audit"),
        ("POST", "/api/vision/save-file"),
        ("GET", "/api/vision/store-token?t=example"),
        ("GET", "/api/vision/get-token"),
        ("POST", "/api/vision/xo-proxy"),
    ]

    for method, path in endpoints:
        response = client.request(method, path, headers=auth_headers)
        assert response.status_code == 404, (method, path, response.text)


def test_vision_debug_tools_stay_disabled_in_production(
    client, auth_headers, monkeypatch
):
    monkeypatch.setenv("FASTAPI_ENV", "production")
    monkeypatch.setenv("ENABLE_VISION_DEBUG_TOOLS", "true")

    response = client.get("/api/vision/get-token", headers=auth_headers)

    assert response.status_code == 404


def test_vision_debug_save_file_rejects_path_traversal(
    client,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("ENABLE_VISION_DEBUG_TOOLS", "true")
    monkeypatch.setattr("app.routes.vision.DATA_DIR", tmp_path)

    response = client.post(
        "/api/vision/save-file",
        headers=auth_headers,
        json={"filename": "../evil.txt", "data": "aGVsbG8="},
    )

    assert response.status_code == 400
    assert not (tmp_path.parent / "evil.txt").exists()


def test_vision_debug_save_file_writes_private_file(
    client,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("ENABLE_VISION_DEBUG_TOOLS", "true")
    monkeypatch.setattr("app.routes.vision.DATA_DIR", tmp_path)

    response = client.post(
        "/api/vision/save-file",
        headers=auth_headers,
        json={"filename": "debug-output.txt", "data": "aGVsbG8="},
    )

    assert response.status_code == 200
    output = tmp_path / "debug-output.txt"
    assert output.read_bytes() == b"hello"
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_content_publish_requires_high_stakes_confirmation(
    client, auth_headers, monkeypatch
):
    from app.db.database import get_db
    from app.main import app

    class _FakeTask:
        id = 123
        status = "approved"

    class _FakeQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return _FakeTask()

    class _FakeDb:
        def query(self, _model):
            return _FakeQuery()

    called = False

    def fake_publish_to_shopify(db, task_id):
        nonlocal called
        called = True
        return {"status": "success", "task_id": task_id, "article_id": "1"}

    app.dependency_overrides[get_db] = lambda: _FakeDb()
    monkeypatch.setattr("app.routes.content.publish_to_shopify", fake_publish_to_shopify)
    try:
        response = client.post(
            "/api/content/generate-and-publish",
            params={"task_id": "123"},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 409
    assert called is False


def test_content_publish_runs_after_gate_pass(client, auth_headers, monkeypatch):
    from app.db.database import get_db
    from app.main import app

    class _FakeTask:
        id = 123
        status = "approved"

    class _FakeQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return _FakeTask()

    class _FakeDb:
        def query(self, _model):
            return _FakeQuery()

    def fake_publish_to_shopify(db, task_id):
        return {"status": "success", "task_id": task_id, "article_id": "1"}

    app.dependency_overrides[get_db] = lambda: _FakeDb()
    monkeypatch.setattr("app.routes.content.publish_to_shopify", fake_publish_to_shopify)
    try:
        response = client.post(
            "/api/content/generate-and-publish",
            params={
                "task_id": "123",
                "human_confirmed": "true",
                "judge_verdict": "PASS",
            },
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "task_id": 123, "article_id": "1"}
