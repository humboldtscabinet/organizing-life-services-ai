import os
import subprocess
import sys
from pathlib import Path

from data._mutation_guard import (
    CONFIRM_ENV,
    CONFIRM_PHRASE,
    DataMutationBlocked,
    guard_request,
    is_guarded_mutation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_guard_classifies_shopify_admin_writes_but_allows_reads_and_oauth():
    admin_url = "https://ols-online.myshopify.com/admin/api/2024-10/pages/123.json"
    oauth_url = "https://ols-online.myshopify.com/admin/oauth/access_token"

    assert is_guarded_mutation("PUT", admin_url) is True
    assert is_guarded_mutation("GET", admin_url) is False
    assert is_guarded_mutation("POST", oauth_url) is False
    assert is_guarded_mutation("POST", "https://api.indexnow.org/indexnow") is True


def test_guard_blocks_without_explicit_mutation_env(monkeypatch):
    monkeypatch.delenv("OLS_ALLOW_DATA_MUTATION", raising=False)
    monkeypatch.delenv(CONFIRM_ENV, raising=False)

    try:
        guard_request("DELETE", "https://ols-online.myshopify.com/admin/api/2024-10/pages/123.json")
    except DataMutationBlocked as exc:
        assert "OLS_ALLOW_DATA_MUTATION=1" in str(exc)
        assert CONFIRM_PHRASE in str(exc)
    else:
        raise AssertionError("expected data mutation guard to block")


def test_guard_requires_typed_confirmation_even_when_allow_flag_is_set(monkeypatch):
    monkeypatch.setenv("OLS_ALLOW_DATA_MUTATION", "1")
    monkeypatch.delenv(CONFIRM_ENV, raising=False)

    try:
        guard_request("POST", "https://api.indexnow.org/indexnow")
    except DataMutationBlocked as exc:
        assert CONFIRM_ENV in str(exc)
    else:
        raise AssertionError("expected data mutation guard to block")


def test_guard_allows_mutation_with_boolean_flag_and_typed_confirmation(monkeypatch):
    monkeypatch.setenv("OLS_ALLOW_DATA_MUTATION", "1")
    monkeypatch.setenv(CONFIRM_ENV, CONFIRM_PHRASE)

    guard_request("POST", "https://api.indexnow.org/indexnow")


def test_data_sitecustomize_blocks_direct_httpx_mutation_before_network():
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "data"),
    }
    env.pop("OLS_ALLOW_DATA_MUTATION", None)
    env.pop(CONFIRM_ENV, None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import httpx; "
                "httpx.put('https://ols-online.myshopify.com/admin/api/2024-10/pages/123.json')"
            ),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Blocked direct production mutation" in result.stderr
