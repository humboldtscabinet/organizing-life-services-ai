import pytest

from app.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_accepts_legacy_cors_env(monkeypatch):
    monkeypatch.setenv("OLS_API_KEY", "test-suite-api-key")
    monkeypatch.delenv("OLS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://dashboard.example")

    settings = get_settings()

    assert settings.allowed_origins == ("https://dashboard.example",)


def test_settings_prefers_new_cors_env(monkeypatch):
    monkeypatch.setenv("OLS_API_KEY", "test-suite-api-key")
    monkeypatch.setenv("OLS_ALLOWED_ORIGINS", "https://new-dashboard.example")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://legacy-dashboard.example")

    settings = get_settings()

    assert settings.allowed_origins == ("https://new-dashboard.example",)


def test_settings_rejects_wildcard_cors(monkeypatch):
    monkeypatch.setenv("OLS_API_KEY", "test-suite-api-key")
    monkeypatch.setenv("OLS_ALLOWED_ORIGINS", "*")

    with pytest.raises(RuntimeError, match="Wildcard CORS"):
        get_settings()
