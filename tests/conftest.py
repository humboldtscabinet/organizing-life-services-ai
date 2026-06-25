"""
Shared pytest fixtures.

These tests are designed to run WITHOUT external services (no Postgres, no
Google APIs, no Shopify). Anything that needs the database is exercised only
through the /health endpoint, which degrades gracefully when the DB is down.
"""

import os

import pytest

# A deterministic API key for the whole test session. Must be set before the
# FastAPI app imports runtime settings.
TEST_API_KEY = "test-suite-api-key"
os.environ.setdefault("OLS_API_KEY", TEST_API_KEY)


@pytest.fixture(scope="session")
def api_key() -> str:
    return os.environ["OLS_API_KEY"]


@pytest.fixture(scope="session")
def client():
    """A FastAPI TestClient bound to the real app object."""
    from fastapi.testclient import TestClient

    import app.main as main

    with TestClient(main.app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(api_key):
    return {"X-API-Key": api_key}
