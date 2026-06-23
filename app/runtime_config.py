"""Runtime configuration helpers with production-safe defaults."""

from __future__ import annotations

import logging
import os
import secrets

logger = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes", "y", "on"}
PRODUCTION_ENVS = {"production", "prod", "server"}
PLACEHOLDER_VALUES = {"", "CHANGE_ME", "YOUR_API_KEY_HERE"}
DEFAULT_DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]


def fastapi_env() -> str:
    """Return the normalized deployment environment name."""
    return os.getenv("FASTAPI_ENV", os.getenv("OLS_ENV", "development")).strip().lower()


def is_production_env() -> bool:
    """True when the process should refuse dev-only insecure fallbacks."""
    return (
        fastapi_env() in PRODUCTION_ENVS
        or os.getenv("OLS_PRODUCTION", "").strip().lower() in TRUE_VALUES
    )


def _is_placeholder(value: str) -> bool:
    stripped = value.strip()
    return stripped in PLACEHOLDER_VALUES or stripped.startswith("YOUR_")


def configured_api_key() -> str:
    """
    Return the configured API key.

    Development can still boot with a process-local generated key, but the key
    is no longer printed to logs. Production/server mode fails fast instead.
    """
    key = os.getenv("OLS_API_KEY", "").strip()
    if key and not _is_placeholder(key):
        return key

    if is_production_env() or os.getenv("OLS_REQUIRE_EXPLICIT_API_KEY", "").lower() in TRUE_VALUES:
        raise RuntimeError("OLS_API_KEY must be set to a non-placeholder value")

    generated = secrets.token_urlsafe(32)
    os.environ["OLS_API_KEY"] = generated
    logger.warning(
        "OLS_API_KEY is not set; generated a process-local development key. "
        "Set OLS_API_KEY in .env before using the dashboard or server deploy."
    )
    return generated


def cors_allow_origins() -> list[str]:
    """Read comma-separated CORS origins, refusing wildcard in production."""
    raw = os.getenv("CORS_ALLOW_ORIGINS", ",".join(DEFAULT_DEV_CORS_ORIGINS)).strip()
    if raw == "*":
        if is_production_env():
            raise RuntimeError("CORS_ALLOW_ORIGINS='*' is not allowed in production")
        return ["*"]

    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        if is_production_env():
            raise RuntimeError("CORS_ALLOW_ORIGINS must be set in production")
        return DEFAULT_DEV_CORS_ORIGINS
    return origins
