"""Session 12: noindex internal Shopify fee/utility product URLs.

Business rule
-------------
OLS is a service business. Shopify “products” such as credit-card fee line
items exist for checkout/admin only. They must never be SEO targets.

This script:
1. Patches the live main theme ``layout/theme.liquid`` so known fee product
   URLs render ``noindex,follow`` (marker ``SEO-ROBOTS-PRODUCTS-V2``, via
   ``request.path`` — ``product.handle`` does not evaluate in this theme's
   layout head).
2. Optionally upserts ``seo.robots=noindex,follow`` on those product
   metafields when present in the store (defense in depth; theme path
   checks are authoritative for rendering).

Does NOT touch:
- Real service pages
- ``/pages/fees-products`` (public pricing/info page)

Safety
------
- Default mode is dry-run.
- Live writes require ``--apply`` plus:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

- Snapshots ``layout/theme.liquid`` before a live theme write.
- Writes a JSON report under ``data/audit_output/``.

Usage
-----
    set -a && source .env && set +a
    .venv/bin/python data/session12_noindex_fee_products.py

    OLS_ALLOW_DATA_MUTATION=1 \\
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \\
    .venv/bin/python data/session12_noindex_fee_products.py --apply
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from _mutation_guard import activate as activate_data_mutation_guard
except ModuleNotFoundError:  # pragma: no cover
    from data._mutation_guard import activate as activate_data_mutation_guard

activate_data_mutation_guard()

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HOST = "organizinglifeservices.com"
ORG_URL = f"https://{HOST}/"

# Known fee/internal product handles seen in GSC / prior crawls.
FEE_PRODUCT_HANDLES = (
    "product-cc-2-7-fee",
    "product-cc-2-7-fee-2",
    "processing-fee",
)

PRODUCT_NOINDEX_MARKER = "SEO-ROBOTS-PRODUCTS-V2"
LEGACY_PRODUCT_NOINDEX_MARKER = "SEO-ROBOTS-PRODUCTS-V1"
# V1 used product.handle; on this theme's layout that drop does not fire for
# product templates, so live HTML never got robots. V2 keys off request.path.
LEGACY_PRODUCT_NOINDEX_RE = re.compile(
    r"\n    \{%- comment -%\} SEO-ROBOTS-PRODUCTS-V1:.*?\{%- endif -%\}",
    re.DOTALL,
)
PAGE_ROBOTS_BLOCK = """    {%- if page and page.metafields.seo.robots != blank -%}
    <meta name="robots" content="{{ page.metafields.seo.robots | escape }}">
    {%- endif -%}"""


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _retry(fn: Any, *args: Any, **kwargs: Any) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(8):
        try:
            resp = fn(*args, **kwargs)
            if getattr(resp, "status_code", None) == 429:
                wait = float(resp.headers.get("Retry-After", 2**attempt))
                print(f"  [429] sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            return resp
        except (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.RemoteProtocolError,
            httpx.ConnectError,
        ) as exc:
            last = exc
            wait = 2**attempt
            print(f"  [retry] {type(exc).__name__}: {exc}; sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
    if last:
        raise last
    raise RuntimeError("retries exhausted")


def shopify_context() -> tuple[dict[str, str], str]:
    store = os.getenv("SHOPIFY_STORE")
    client_id = os.getenv("SHOPIFY_CLIENT_ID")
    client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")
    api_version = os.getenv("SHOPIFY_API_VERSION", "2024-10")
    if not all([store, client_id, client_secret]):
        sys.exit("Missing SHOPIFY_STORE / SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET")

    resp = _retry(
        httpx.post,
        f"https://{store}.myshopify.com/admin/oauth/access_token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    base_url = f"https://{store}.myshopify.com/admin/api/{api_version}"
    return headers, base_url


def get_json(url: str, headers: dict[str, str]) -> dict:
    resp = _retry(httpx.get, url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main_theme(headers: dict[str, str], base_url: str) -> dict:
    themes = get_json(f"{base_url}/themes.json", headers).get("themes", [])
    theme = next((t for t in themes if t.get("role") == "main"), None)
    if not theme:
        sys.exit("No main Shopify theme found")
    return theme


def get_theme_asset(headers: dict[str, str], base_url: str, theme_id: int, key: str) -> str:
    resp = _retry(
        httpx.get,
        f"{base_url}/themes/{theme_id}/assets.json",
        headers=headers,
        params={"asset[key]": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["asset"]["value"]


def put_theme_asset(
    headers: dict[str, str], base_url: str, theme_id: int, key: str, value: str
) -> None:
    resp = _retry(
        httpx.put,
        f"{base_url}/themes/{theme_id}/assets.json",
        headers=headers,
        json={"asset": {"key": key, "value": value}},
        timeout=60,
    )
    resp.raise_for_status()


def build_product_noindex_patch() -> str:
    # Longer paths first so fee-2 is matched before its fee- prefix sibling
    # if conditions are ever switched to `contains`.
    handles = sorted(FEE_PRODUCT_HANDLES, key=len, reverse=True)
    path_checks = []
    for i, handle in enumerate(handles):
        keyword = "if" if i == 0 else "elsif"
        path_checks.append(
            f"    {{%- {keyword} request.path == '/products/{handle}' -%}}\n"
            "      {%- assign ols_noindex_product = true -%}"
        )
    path_block = "\n".join(path_checks) + "\n    {%- endif -%}\n"
    return (
        f"\n    {{%- comment -%}} {PRODUCT_NOINDEX_MARKER}: noindex internal fee products {{%- endcomment -%}}\n"
        "    {%- assign ols_noindex_product = false -%}\n"
        f"{path_block}"
        "    {%- if ols_noindex_product -%}\n"
        '    <meta name="robots" content="noindex,follow">\n'
        "    {%- endif -%}"
    )


def patch_product_noindex(source: str) -> tuple[str, bool]:
    new_patch = build_product_noindex_patch()

    if PRODUCT_NOINDEX_MARKER in source:
        return source, False

    if LEGACY_PRODUCT_NOINDEX_MARKER in source:
        updated, n = LEGACY_PRODUCT_NOINDEX_RE.subn(new_patch, source, count=1)
        if n != 1:
            raise RuntimeError(
                "Found legacy SEO-ROBOTS-PRODUCTS-V1 marker but could not replace block"
            )
        return updated, True

    if PAGE_ROBOTS_BLOCK not in source:
        raise RuntimeError(
            "Could not locate SEO-ROBOTS-V1 page robots block to attach product noindex"
        )
    return source.replace(PAGE_ROBOTS_BLOCK, PAGE_ROBOTS_BLOCK + new_patch, 1), True


def list_products(headers: dict[str, str], base_url: str) -> list[dict]:
    return get_json(f"{base_url}/products.json?limit=250", headers).get("products", [])


def upsert_product_robots(
    headers: dict[str, str],
    base_url: str,
    product: dict,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    product_id = product["id"]
    handle = product["handle"]
    mfs = get_json(
        f"{base_url}/products/{product_id}/metafields.json", headers
    ).get("metafields", [])
    existing = next(
        (
            m
            for m in mfs
            if m.get("namespace") == "seo" and m.get("key") == "robots"
        ),
        None,
    )
    if existing and existing.get("value") == "noindex,follow":
        return {"handle": handle, "product_id": product_id, "status": "unchanged"}

    if dry_run:
        return {
            "handle": handle,
            "product_id": product_id,
            "status": "would_upsert_seo_robots",
            "existing": existing.get("value") if existing else None,
        }

    if existing:
        resp = _retry(
            httpx.put,
            f"{base_url}/metafields/{existing['id']}.json",
            headers=headers,
            json={
                "metafield": {
                    "id": existing["id"],
                    "value": "noindex,follow",
                    "type": "single_line_text_field",
                }
            },
            timeout=60,
        )
    else:
        resp = _retry(
            httpx.post,
            f"{base_url}/products/{product_id}/metafields.json",
            headers=headers,
            json={
                "metafield": {
                    "namespace": "seo",
                    "key": "robots",
                    "value": "noindex,follow",
                    "type": "single_line_text_field",
                }
            },
            timeout=60,
        )
    resp.raise_for_status()
    return {"handle": handle, "product_id": product_id, "status": "upserted_seo_robots"}


def run(*, apply: bool) -> dict[str, Any]:
    dry_run = not apply
    headers, base_url = shopify_context()
    theme = main_theme(headers, base_url)
    layout_key = "layout/theme.liquid"
    before = get_theme_asset(headers, base_url, theme["id"], layout_key)
    after, theme_changed = patch_product_noindex(before)

    products = list_products(headers, base_url)
    by_handle = {p.get("handle"): p for p in products}
    metafield_results = []
    for handle in FEE_PRODUCT_HANDLES:
        product = by_handle.get(handle)
        if not product:
            metafield_results.append({"handle": handle, "status": "not_found_in_store"})
            continue
        metafield_results.append(
            upsert_product_robots(headers, base_url, product, dry_run=dry_run)
        )
        time.sleep(0.2)

    result: dict[str, Any] = {
        "mode": "apply" if apply else "dry_run",
        "theme_id": theme["id"],
        "theme_name": theme.get("name"),
        "product_noindex_theme": (
            "would_patch"
            if theme_changed and dry_run
            else "patched"
            if theme_changed
            else "unchanged"
        ),
        "fee_product_handles": list(FEE_PRODUCT_HANDLES),
        "metafields": metafield_results,
        "verify_urls": [f"{ORG_URL}products/{h}" for h in FEE_PRODUCT_HANDLES],
    }

    if theme_changed:
        result["diff_preview"] = "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile="before/layout/theme.liquid",
                tofile="after/layout/theme.liquid",
                n=3,
            )
        )[:6000]

    if apply and theme_changed:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snapshot = OUT_DIR / f"theme_layout_snapshot_pre_session12_products_{timestamp}.liquid"
        snapshot.write_text(before)
        put_theme_asset(headers, base_url, theme["id"], layout_key, after)
        result["snapshot"] = str(snapshot.relative_to(PROJECT_ROOT))

    return result


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform live Shopify writes (requires mutation guard env).",
    )
    args = parser.parse_args()
    result = run(apply=args.apply)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_DIR / f"session12_noindex_fee_products_{timestamp}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nWrote report: {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
