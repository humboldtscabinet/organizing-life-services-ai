import os
import subprocess
import sys
from pathlib import Path

from data._mutation_guard import DataMutationBlocked, guard_request, is_guarded_mutation

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

    try:
        guard_request("DELETE", "https://ols-online.myshopify.com/admin/api/2024-10/pages/123.json")
    except DataMutationBlocked as exc:
        assert "OLS_ALLOW_DATA_MUTATION=1" in str(exc)
    else:
        raise AssertionError("expected data mutation guard to block")


def test_data_sitecustomize_blocks_direct_httpx_mutation_before_network():
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "data"),
    }
    env.pop("OLS_ALLOW_DATA_MUTATION", None)

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
