"""Runtime guard for one-off scripts under data/.

The data folder contains historical SEO scripts, including direct Shopify
mutators. When those scripts are run directly, this guard blocks external write
requests unless the operator explicitly opts in with both a boolean env var and
a typed confirmation phrase.
"""

from __future__ import annotations

import os
from functools import wraps
from typing import Any
from urllib.parse import urlparse

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TRUE_VALUES = {"1", "true", "yes", "y", "on"}
CONFIRM_ENV = "OLS_DATA_MUTATION_CONFIRM"
CONFIRM_PHRASE = "I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE"
INDEXNOW_HOSTS = {
    "api.indexnow.org",
    "www.bing.com",
    "bing.com",
    "yandex.com",
    "www.yandex.com",
}

_ACTIVE = False


class DataMutationBlocked(RuntimeError):
    """Raised when a data script attempts an unapproved production mutation."""


def _enabled() -> bool:
    allow_flag = os.getenv("OLS_ALLOW_DATA_MUTATION", "").strip().lower() in TRUE_VALUES
    confirmation = os.getenv(CONFIRM_ENV, "").strip()
    return allow_flag and confirmation == CONFIRM_PHRASE


def _safe_url(url: Any) -> str:
    parsed = urlparse(str(url))
    if not parsed.scheme or not parsed.netloc:
        return str(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def is_guarded_mutation(method: str, url: Any) -> bool:
    method = method.upper()
    if method not in MUTATING_METHODS:
        return False

    parsed = urlparse(str(url))
    host = (parsed.hostname or "").lower()
    path = parsed.path

    if host.endswith(".myshopify.com"):
        if path.endswith("/admin/oauth/access_token"):
            return False
        return "/admin/api/" in path

    if host in INDEXNOW_HOSTS:
        return True

    return False


def guard_request(method: str, url: Any) -> None:
    if _enabled() or not is_guarded_mutation(method, url):
        return

    raise DataMutationBlocked(
        "Blocked direct production mutation from data/ script: "
        f"{method.upper()} {_safe_url(url)}. "
        "Prefer a guarded API route with human_confirmed=true and "
        "judge_verdict=PASS. If this historical script is truly required, set "
        f"OLS_ALLOW_DATA_MUTATION=1 and {CONFIRM_ENV}={CONFIRM_PHRASE} only "
        "after human review."
    )


def _patch_httpx() -> None:
    try:
        import httpx
    except ImportError:
        return

    original_request = httpx.request

    @wraps(original_request)
    def request(method: str, url: Any, *args: Any, **kwargs: Any) -> Any:
        guard_request(method, url)
        return original_request(method, url, *args, **kwargs)

    httpx.request = request

    for method_name in ("post", "put", "patch", "delete"):
        original = getattr(httpx, method_name)

        @wraps(original)
        def method_wrapper(
            url: Any,
            *args: Any,
            _method: str = method_name.upper(),
            _original: Any = original,
            **kwargs: Any,
        ) -> Any:
            guard_request(_method, url)
            return _original(url, *args, **kwargs)

        setattr(httpx, method_name, method_wrapper)

    original_client_request = httpx.Client.request

    @wraps(original_client_request)
    def client_request(self: Any, method: str, url: Any, *args: Any, **kwargs: Any) -> Any:
        guard_request(method, url)
        return original_client_request(self, method, url, *args, **kwargs)

    httpx.Client.request = client_request

    original_async_client_request = httpx.AsyncClient.request

    @wraps(original_async_client_request)
    async def async_client_request(
        self: Any,
        method: str,
        url: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        guard_request(method, url)
        return await original_async_client_request(self, method, url, *args, **kwargs)

    httpx.AsyncClient.request = async_client_request


def _patch_requests() -> None:
    try:
        import requests
    except ImportError:
        return

    original_request = requests.request

    @wraps(original_request)
    def request(method: str, url: Any, *args: Any, **kwargs: Any) -> Any:
        guard_request(method, url)
        return original_request(method, url, *args, **kwargs)

    requests.request = request

    for method_name in ("post", "put", "patch", "delete"):
        original = getattr(requests, method_name)

        @wraps(original)
        def method_wrapper(
            url: Any,
            *args: Any,
            _method: str = method_name.upper(),
            _original: Any = original,
            **kwargs: Any,
        ) -> Any:
            guard_request(_method, url)
            return _original(url, *args, **kwargs)

        setattr(requests, method_name, method_wrapper)


def activate() -> None:
    global _ACTIVE
    if _ACTIVE:
        return
    _patch_httpx()
    _patch_requests()
    _ACTIVE = True
