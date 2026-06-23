import pytest

from app import runtime_config


def test_cors_defaults_to_pinned_local_origins(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.setenv("FASTAPI_ENV", "development")

    origins = runtime_config.cors_allow_origins()

    assert "http://localhost:3000" in origins
    assert "*" not in origins


def test_cors_wildcard_is_rejected_in_production(monkeypatch):
    monkeypatch.setenv("FASTAPI_ENV", "production")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")

    with pytest.raises(RuntimeError, match="not allowed in production"):
        runtime_config.cors_allow_origins()


def test_missing_api_key_is_rejected_in_production(monkeypatch):
    monkeypatch.setenv("FASTAPI_ENV", "production")
    monkeypatch.delenv("OLS_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OLS_API_KEY"):
        runtime_config.configured_api_key()


def test_development_generated_api_key_is_not_logged(monkeypatch, caplog):
    monkeypatch.setenv("FASTAPI_ENV", "development")
    monkeypatch.delenv("OLS_API_KEY", raising=False)

    key = runtime_config.configured_api_key()

    assert key
    assert key not in caplog.text

