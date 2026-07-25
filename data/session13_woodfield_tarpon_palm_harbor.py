"""Session 13 follow-through: Woodfield intlink retarget + Palm Harbor SD block.

1. Replace service-intent hrefs from the legacy Woodfield gallery page to the
   permanent Tarpon Springs service page (theme + articles).
2. Ensure Palm Harbor seo title/meta match Session 11 targets and append an
   idempotent striking-distance H2/proof block (``SD-ESPH-V1``).

Safety
------
- Default mode is dry-run.
- Live writes require ``--apply`` plus:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

Usage
-----
    .venv/bin/python data/session13_woodfield_tarpon_palm_harbor.py
    .venv/bin/python data/session13_woodfield_tarpon_palm_harbor.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from _mutation_guard import (
        CONFIRM_ENV,
        CONFIRM_PHRASE,
        activate as activate_data_mutation_guard,
    )
except ModuleNotFoundError:  # pragma: no cover
    from data._mutation_guard import (
        CONFIRM_ENV,
        CONFIRM_PHRASE,
        activate as activate_data_mutation_guard,
    )

activate_data_mutation_guard()

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OLD_HREF = "/pages/tarpon-springs-estate-sale-in-woodfield"
NEW_HREF = "/pages/estate-sale-tarpon-springs-florida"
LAYOUT_KEY = "layout/theme.liquid"
BLOG_ID = 52179501100

PALM_HANDLE = "estate-sale-palm-harbor-pinellas-county"
PALM_SEO_TITLE = "Estate Sales Palm Harbor, FL | Pinellas County OLS"
PALM_META = (
    "Estate sales in Palm Harbor, FL by OLS. Full-service sale planning, "
    "appraisals, downsizing, and cleanouts. Call (727) 542-6028."
)
PALM_SD_MARKER = "SD-ESPH-V1"
PALM_SD_BLOCK = f"""<!-- {PALM_SD_MARKER} -->
<h2><strong>Estate Sales Palm Harbor</strong></h2>
<p>Looking for <strong>estate sales Palm Harbor</strong> families can trust? Organizing Life Services runs full-service estate sales across north Pinellas — including Palm Harbor villas, 55+ communities, waterfront homes, and inherited family properties near East Lake, Ozona, and Crystal Beach. We plan around HOA and gate access, parking, and realtor timelines; photograph and price every item; and list sales publicly on major estate-sale directories 5–7 days ahead so local buyers show up ready. Need the home broom-clean for listing or closing? We coordinate sale-day staffing, donation pickup, and cleanout. Call (727) 542-6028 or start with our <a href="/pages/estate-sale-pinellas-county">Pinellas County estate sales</a> hub and <a href="/pages/contact-us">contact page</a>.</p>
<!-- /{PALM_SD_MARKER} -->"""

ARTICLE_HANDLES = (
    "estate-sale-vs-garage-sale-know-the-differences",
    "pros-and-cons-of-estate-sales",
    "how-to-increase-your-home-appraisal-value",
    "estate-auction-vs-estate-sale-pros-and-cons",
    "the-ultimate-guide-for-barbie-collector-buyers",
    "how-to-plan-estate-sale",
)


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
            time.sleep(2**attempt)
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


def main_theme(headers: dict[str, str], base_url: str) -> dict:
    themes = _retry(httpx.get, f"{base_url}/themes.json", headers=headers, timeout=60).json().get(
        "themes", []
    )
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


def replace_woodfield_hrefs(html: str) -> tuple[str, int]:
    count = html.count(OLD_HREF)
    if count == 0:
        return html, 0
    return html.replace(OLD_HREF, NEW_HREF), count


def retarget_theme(
    headers: dict[str, str], base_url: str, *, dry_run: bool
) -> dict[str, Any]:
    theme = main_theme(headers, base_url)
    before = get_theme_asset(headers, base_url, theme["id"], LAYOUT_KEY)
    after, n = replace_woodfield_hrefs(before)
    result: dict[str, Any] = {
        "asset": LAYOUT_KEY,
        "theme_id": theme["id"],
        "old_href_count": n,
        "status": "unchanged" if n == 0 else ("would_replace" if dry_run else "replaced"),
    }
    if n and not dry_run:
        put_theme_asset(headers, base_url, theme["id"], LAYOUT_KEY, after)
    return result


def list_articles(headers: dict[str, str], base_url: str) -> dict[str, dict]:
    by_handle: dict[str, dict] = {}
    url = f"{base_url}/blogs/{BLOG_ID}/articles.json?limit=250"
    while url:
        resp = _retry(httpx.get, url, headers=headers, timeout=60)
        resp.raise_for_status()
        for article in resp.json().get("articles", []):
            by_handle[article["handle"]] = article
        next_url = ""
        for part in resp.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
        url = next_url
    return by_handle


def retarget_articles(
    headers: dict[str, str], base_url: str, *, dry_run: bool
) -> list[dict[str, Any]]:
    by_handle = list_articles(headers, base_url)
    results = []
    for handle in ARTICLE_HANDLES:
        article = by_handle.get(handle)
        if not article:
            results.append({"handle": handle, "status": "not_found"})
            continue
        # Need full body
        detail = _retry(
            httpx.get,
            f"{base_url}/blogs/{BLOG_ID}/articles/{article['id']}.json",
            headers=headers,
            timeout=60,
        )
        detail.raise_for_status()
        full = detail.json()["article"]
        body = full.get("body_html") or ""
        after, n = replace_woodfield_hrefs(body)
        entry: dict[str, Any] = {
            "handle": handle,
            "article_id": full["id"],
            "old_href_count": n,
            "status": "unchanged" if n == 0 else ("would_replace" if dry_run else "replaced"),
        }
        if n and not dry_run:
            resp = _retry(
                httpx.put,
                f"{base_url}/blogs/{BLOG_ID}/articles/{full['id']}.json",
                headers=headers,
                json={"article": {"id": full["id"], "body_html": after}},
                timeout=60,
            )
            resp.raise_for_status()
            time.sleep(0.3)
        results.append(entry)
    return results


def list_global_metafields(
    headers: dict[str, str], base_url: str, page_id: int
) -> dict[str, dict]:
    data = _retry(
        httpx.get, f"{base_url}/pages/{page_id}/metafields.json", headers=headers, timeout=60
    ).json()
    return {
        m["key"]: m
        for m in data.get("metafields", [])
        if m.get("namespace") == "global"
    }


def upsert_global_metafield(
    headers: dict[str, str],
    base_url: str,
    page_id: int,
    key: str,
    value: str,
    existing: dict | None,
    *,
    dry_run: bool,
) -> str:
    if existing and existing.get("value") == value:
        return "unchanged"
    if dry_run:
        return "would_update" if existing else "would_create"
    if existing:
        resp = _retry(
            httpx.put,
            f"{base_url}/metafields/{existing['id']}.json",
            headers=headers,
            json={
                "metafield": {
                    "id": existing["id"],
                    "value": value,
                    "type": "single_line_text_field",
                }
            },
            timeout=60,
        )
        resp.raise_for_status()
        return "updated"
    resp = _retry(
        httpx.post,
        f"{base_url}/pages/{page_id}/metafields.json",
        headers=headers,
        json={
            "metafield": {
                "namespace": "global",
                "key": key,
                "value": value,
                "type": "single_line_text_field",
            }
        },
        timeout=60,
    )
    resp.raise_for_status()
    return "created"


def patch_palm_harbor(
    headers: dict[str, str], base_url: str, *, dry_run: bool
) -> dict[str, Any]:
    pages = _retry(httpx.get, f"{base_url}/pages.json?limit=250", headers=headers, timeout=60).json().get(
        "pages", []
    )
    page = next((p for p in pages if p.get("handle") == PALM_HANDLE), None)
    if not page:
        return {"handle": PALM_HANDLE, "status": "not_found"}

    detail = _retry(
        httpx.get, f"{base_url}/pages/{page['id']}.json", headers=headers, timeout=60
    )
    detail.raise_for_status()
    full = detail.json()["page"]
    body = full.get("body_html") or ""
    mfs = list_global_metafields(headers, base_url, full["id"])

    title_status = upsert_global_metafield(
        headers,
        base_url,
        full["id"],
        "title_tag",
        PALM_SEO_TITLE,
        mfs.get("title_tag"),
        dry_run=dry_run,
    )
    meta_status = upsert_global_metafield(
        headers,
        base_url,
        full["id"],
        "description_tag",
        PALM_META,
        mfs.get("description_tag"),
        dry_run=dry_run,
    )

    if PALM_SD_MARKER in body:
        body_status = "unchanged"
    else:
        new_body = body.rstrip() + "\n" + PALM_SD_BLOCK
        body_status = "would_append" if dry_run else "appended"
        if not dry_run:
            resp = _retry(
                httpx.put,
                f"{base_url}/pages/{full['id']}.json",
                headers=headers,
                json={"page": {"id": full["id"], "body_html": new_body}},
                timeout=60,
            )
            resp.raise_for_status()

    return {
        "handle": PALM_HANDLE,
        "page_id": full["id"],
        "title_tag": title_status,
        "description_tag": meta_status,
        "sd_block": body_status,
        "seo_title": PALM_SEO_TITLE,
        "marker": PALM_SD_MARKER,
    }


def require_apply_confirmation() -> None:
    allow = os.getenv("OLS_ALLOW_DATA_MUTATION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }
    confirm = os.getenv(CONFIRM_ENV, "").strip()
    if not allow or confirm != CONFIRM_PHRASE:
        sys.exit(
            "Live apply requires OLS_ALLOW_DATA_MUTATION=1 and "
            f"{CONFIRM_ENV}={CONFIRM_PHRASE}."
        )


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry_run = not args.apply
    if args.apply:
        require_apply_confirmation()

    print("Session 13 Woodfield→Tarpon + Palm Harbor SD" + (" (DRY RUN)" if dry_run else ""))
    headers, base_url = shopify_context()
    report: dict[str, Any] = {
        "dry_run": dry_run,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "woodfield_to_tarpon": {
            "old": OLD_HREF,
            "new": NEW_HREF,
            "theme": retarget_theme(headers, base_url, dry_run=dry_run),
            "articles": retarget_articles(headers, base_url, dry_run=dry_run),
        },
        "palm_harbor": patch_palm_harbor(headers, base_url, dry_run=dry_run),
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"session13_woodfield_tarpon_palm_harbor_{stamp}.json"
    path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\nWrote report: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
