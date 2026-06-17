from app.services.llm_router import local_llm_status


class _FakeTagsResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_local_llm_status_ok(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://ollama.test:11434")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "gemma4:12b")
    monkeypatch.setenv("LOCAL_LLM_LARGE_MODEL", "gemma4:31b")

    def fake_get(url, timeout):
        assert url == "http://ollama.test:11434/api/tags"
        assert timeout == 5.0
        return _FakeTagsResponse(
            {
                "models": [
                    {"name": "gemma4:12b"},
                    {"name": "gemma4:31b"},
                ]
            }
        )

    monkeypatch.setattr("app.services.llm_router.httpx.get", fake_get)

    status = local_llm_status()

    assert status["status"] == "ok"
    assert status["reachable"] is True
    assert status["missing_models"] == []


def test_local_llm_status_degraded_when_model_missing(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_MODEL", "gemma4:12b")
    monkeypatch.setenv("LOCAL_LLM_LARGE_MODEL", "gemma4:31b")
    monkeypatch.setattr(
        "app.services.llm_router.httpx.get",
        lambda url, timeout: _FakeTagsResponse({"models": [{"name": "gemma4:12b"}]}),
    )

    status = local_llm_status()

    assert status["status"] == "degraded"
    assert status["missing_models"] == ["gemma4:31b"]


def test_local_llm_status_error_when_ollama_unreachable(monkeypatch):
    def fake_get(url, timeout):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("app.services.llm_router.httpx.get", fake_get)

    status = local_llm_status()

    assert status["status"] == "error"
    assert status["reachable"] is False
    assert "connection refused" in status["detail"]


def test_local_llm_status_route_requires_auth_and_returns_status(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        "app.routes.llm.local_llm_status",
        lambda: {"status": "ok", "reachable": True},
    )

    unauthenticated = client.get("/api/llm/local-status")
    assert unauthenticated.status_code == 401

    authenticated = client.get("/api/llm/local-status", headers=auth_headers)
    assert authenticated.status_code == 200
    assert authenticated.json() == {"status": "ok", "reachable": True}
