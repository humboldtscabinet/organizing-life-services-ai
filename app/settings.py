"""
Runtime settings for the OLS API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_DATABASE_URL = "postgresql://ols_user:CHANGE_ME@localhost:5432/ols_db"
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


@dataclass(frozen=True)
class Settings:
    api_key: str
    database_url: str
    allowed_origins: tuple[str, ...]
    app_version: str = "0.5.0"

    def readiness_issues(self) -> list[str]:
        issues: list[str] = []

        if not self.api_key.strip():
            issues.append("OLS_API_KEY is not configured")

        if not self.database_url.strip():
            issues.append("DATABASE_URL is not configured")

        return issues


def _parse_allowed_origins(raw_value: str) -> tuple[str, ...]:
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    if "*" in origins:
        raise RuntimeError("Wildcard CORS origins are not allowed; pin explicit origins.")
    return tuple(origins) if origins else DEFAULT_ALLOWED_ORIGINS


@lru_cache
def get_settings() -> Settings:
    api_key = os.getenv("OLS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OLS_API_KEY is required. Set it in your environment or .env before starting the API."
        )

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
    allowed_origins_raw = os.getenv("OLS_ALLOWED_ORIGINS") or os.getenv("CORS_ALLOW_ORIGINS", "")
    allowed_origins = _parse_allowed_origins(allowed_origins_raw)

    return Settings(
        api_key=api_key,
        database_url=database_url,
        allowed_origins=allowed_origins,
    )


def validate_runtime_settings() -> Settings:
    """Fail fast during startup if required settings are missing."""
    return get_settings()
