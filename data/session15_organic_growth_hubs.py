"""Session 15: Organic growth hubs — appraisal, Tampa, Pinellas intlinks.

1. Append ``SD-APPRAISAL-V2`` on ``personal-property-appraisal`` (refresh
   title/meta if drifted from Session 10 targets).
2. Append ``SD-TAMPA-V2`` on ``estate-sale-tampa-hillsborough-county``
   (neighborhoods, service CTAs, soft organizer cannibalization note).
3. Ensure Pinellas hub ``/pages/estate-sale-pinellas-county`` is linked from
   homepage theme + Clearwater + Tarpon (``SEO-INTLINKS-PINELLAS-V1``).
   Palm Harbor is skipped when the hub href already exists (Session 13).

Safety
------
- Default mode is dry-run.
- Live writes require ``--apply`` plus:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

Usage
-----
    .venv/bin/python data/session15_organic_growth_hubs.py
    .venv/bin/python data/session15_organic_growth_hubs.py --apply
    .venv/bin/python data/session15_organic_growth_hubs.py --apply --skip-indexnow

Mac mini (no host .venv)::

    docker exec --env-file .env ols-api python3 /app/data/session15_organic_growth_hubs.py
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
INDEXNOW_KEY_PATH = PROJECT_ROOT / "credentials" / "indexnow_key.txt"

ORG_URL = "https://organizinglifeservices.com/"
LAYOUT_KEY = "layout/theme.liquid"
PINELLAS_HREF = "/pages/estate-sale-pinellas-county"
PINELLAS_MARKER = "SEO-INTLINKS-PINELLAS-V1"

APPRAISAL_HANDLE = "personal-property-appraisal"
APPRAISAL_MARKER = "SD-APPRAISAL-V2"
APPRAISAL_SEO_TITLE = "Personal Property Appraisers Tampa Bay | Estate Appraisals"
APPRAISAL_META = (
    "Need Tampa personal property appraisers? OLS provides estate sale, "
    "probate, insurance, and downsizing appraisals across Tampa Bay. "
    "Call (727) 542-6028."
)
APPRAISAL_BLOCK = f"""<!-- {APPRAISAL_MARKER} -->
<h2><strong>Personal Property Appraisers Near Me</strong></h2>
<p>Looking for <strong>personal property appraisers near me</strong> or Tampa Bay estate appraisals you can trust for probate, insurance, downsizing, or sale planning? Organizing Life Services documents furniture, art, jewelry, collectibles, and household contents with clear values families, attorneys, and insurers can use. We support estate-sale pricing, equitable distribution, and pre-listing decisions across Pinellas, Pasco, Hillsborough, Hernando, and Citrus counties.</p>
<p>Need the home sold and cleared after valuation? Pair appraisal support with our <a href="/pages/estate-sale-tampa-hillsborough-county">Tampa &amp; Hillsborough estate sales</a> hub, <a href="/pages/estate-sale-pinellas-county">Pinellas County estate sales</a>, or <a href="/pages/estate-cleanout-services">estate cleanout services</a>. Call (727) 542-6028 or start on our <a href="/pages/contact-us">contact page</a>.</p>
<!-- /{APPRAISAL_MARKER} -->"""

TAMPA_HANDLE = "estate-sale-tampa-hillsborough-county"
TAMPA_MARKER = "SD-TAMPA-V2"
TAMPA_BLOCK = f"""<!-- {TAMPA_MARKER} -->
<h2><strong>Estate Sales Tampa &amp; Hillsborough County</strong></h2>
<p>OLS runs full-service <strong>estate sales in Tampa</strong> and across Hillsborough County — including South Tampa, Westchase, Carrollwood, Brandon-area homes, Lutz, and nearby communities where parking, HOA access, and realtor timelines matter. We photograph and price the home, list the sale on major directories 5–7 days ahead, staff sale days, and can coordinate donation pickup and cleanout so the property is listing-ready.</p>
<p>Related services: <a href="/pages/personal-property-appraisal">personal property appraisals</a>, <a href="/pages/estate-cleanout-services">estate cleanouts</a>, and <a href="/pages/downsizing-moving-sales">downsizing help</a>. Looking specifically for <em>estate sale organizers</em> company-wide? Start on our <a href="/">homepage</a> or <a href="/pages/contact-us">contact page</a> — this hub focuses on Tampa and Hillsborough estate sale projects.</p>
<p>Call (727) 542-6028 to discuss timing for a Tampa or Hillsborough estate sale.</p>
<!-- /{TAMPA_MARKER} -->"""

CITY_PINELLAS_TARGETS = (
    ("estate-sale-clearwater-florida", "Clearwater"),
    ("estate-sale-tarpon-springs-florida", "Tarpon Springs"),
    ("estate-sale-palm-harbor-pinellas-county", "Palm Harbor"),
)

PINELLAS_PAGE_BLOCK = f"""<!-- {PINELLAS_MARKER} -->
<p>Explore the full <a href="{PINELLAS_HREF}">Pinellas County estate sales</a> hub for nearby cities and county-wide service coverage.</p>
<!-- /{PINELLAS_MARKER} -->"""

PINELLAS_THEME_BLOCK = f"""
{{%- comment -%}} {PINELLAS_MARKER} {{%- endcomment -%}}
{{%- if template.name == 'index' -%}}
<nav aria-label="Pinellas County estate sales">
  <p><a href="{PINELLAS_HREF}">Pinellas County estate sales</a> — Palm Harbor, Clearwater, Tarpon Springs, and more.</p>
</nav>
{{%- endif -%}}
{{%- comment -%}} /{PINELLAS_MARKER} {{%- endcomment -%}}
"""


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


def list_pages(headers: dict[str, str], base_url: str) -> dict[str, dict]:
    by_handle: dict[str, dict] = {}
    url = f"{base_url}/pages.json?limit=250"
    while url:
        resp = _retry(httpx.get, url, headers=headers, timeout=60)
        resp.raise_for_status()
        for page in resp.json().get("pages", []):
            by_handle[page["handle"]] = page
        next_url = ""
        for part in resp.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
        url = next_url
    return by_handle


def get_page(headers: dict[str, str], base_url: str, page_id: int) -> dict:
    resp = _retry(httpx.get, f"{base_url}/pages/{page_id}.json", headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()["page"]


def put_page_body(
    headers: dict[str, str], base_url: str, page_id: int, body_html: str
) -> None:
    resp = _retry(
        httpx.put,
        f"{base_url}/pages/{page_id}.json",
        headers=headers,
        json={"page": {"id": page_id, "body_html": body_html}},
        timeout=60,
    )
    resp.raise_for_status()


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


def append_marker_block(body: str, marker: str, block: str) -> tuple[str, str]:
    if marker in body:
        return body, "unchanged"
    return body.rstrip() + "\n" + block, "append"


def patch_appraisal(
    headers: dict[str, str], base_url: str, pages: dict[str, dict], *, dry_run: bool
) -> dict[str, Any]:
    page = pages.get(APPRAISAL_HANDLE)
    if not page:
        return {"handle": APPRAISAL_HANDLE, "status": "not_found"}
    full = get_page(headers, base_url, page["id"])
    body = full.get("body_html") or ""
    mfs = list_global_metafields(headers, base_url, full["id"])

    title_status = upsert_global_metafield(
        headers,
        base_url,
        full["id"],
        "title_tag",
        APPRAISAL_SEO_TITLE,
        mfs.get("title_tag"),
        dry_run=dry_run,
    )
    meta_status = upsert_global_metafield(
        headers,
        base_url,
        full["id"],
        "description_tag",
        APPRAISAL_META,
        mfs.get("description_tag"),
        dry_run=dry_run,
    )

    new_body, action = append_marker_block(body, APPRAISAL_MARKER, APPRAISAL_BLOCK)
    if action == "unchanged":
        body_status = "unchanged"
    elif dry_run:
        body_status = "would_append"
    else:
        put_page_body(headers, base_url, full["id"], new_body)
        body_status = "appended"
        time.sleep(0.3)

    return {
        "handle": APPRAISAL_HANDLE,
        "page_id": full["id"],
        "title_tag": title_status,
        "description_tag": meta_status,
        "sd_block": body_status,
        "marker": APPRAISAL_MARKER,
        "url": f"{ORG_URL}pages/{APPRAISAL_HANDLE}",
        "changed": body_status != "unchanged"
        or title_status not in {"unchanged"}
        or meta_status not in {"unchanged"},
    }


def patch_tampa(
    headers: dict[str, str], base_url: str, pages: dict[str, dict], *, dry_run: bool
) -> dict[str, Any]:
    page = pages.get(TAMPA_HANDLE)
    if not page:
        return {"handle": TAMPA_HANDLE, "status": "not_found"}
    full = get_page(headers, base_url, page["id"])
    body = full.get("body_html") or ""
    new_body, action = append_marker_block(body, TAMPA_MARKER, TAMPA_BLOCK)
    if action == "unchanged":
        body_status = "unchanged"
    elif dry_run:
        body_status = "would_append"
    else:
        put_page_body(headers, base_url, full["id"], new_body)
        body_status = "appended"
        time.sleep(0.3)

    return {
        "handle": TAMPA_HANDLE,
        "page_id": full["id"],
        "sd_block": body_status,
        "marker": TAMPA_MARKER,
        "url": f"{ORG_URL}pages/{TAMPA_HANDLE}",
        "changed": body_status != "unchanged",
    }


def ensure_pinellas_on_page(
    headers: dict[str, str],
    base_url: str,
    pages: dict[str, dict],
    handle: str,
    label: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    page = pages.get(handle)
    if not page:
        return {"handle": handle, "label": label, "status": "not_found"}
    full = get_page(headers, base_url, page["id"])
    body = full.get("body_html") or ""
    if PINELLAS_HREF in body or PINELLAS_MARKER in body:
        return {
            "handle": handle,
            "label": label,
            "status": "unchanged",
            "reason": "pinellas_href_or_marker_present",
            "changed": False,
        }
    new_body = body.rstrip() + "\n" + PINELLAS_PAGE_BLOCK
    if dry_run:
        status = "would_append"
    else:
        put_page_body(headers, base_url, full["id"], new_body)
        status = "appended"
        time.sleep(0.3)
    return {
        "handle": handle,
        "label": label,
        "page_id": full["id"],
        "status": status,
        "marker": PINELLAS_MARKER,
        "url": f"{ORG_URL}pages/{handle}",
        "changed": status != "unchanged",
    }


def ensure_pinellas_on_theme(
    headers: dict[str, str], base_url: str, *, dry_run: bool
) -> dict[str, Any]:
    theme = main_theme(headers, base_url)
    before = get_theme_asset(headers, base_url, theme["id"], LAYOUT_KEY)
    if PINELLAS_MARKER in before or (
        PINELLAS_HREF in before and "SEO-INTLINKS" in before
    ):
        # Hub already referenced from an intlinks block — still add marker only if
        # href completely absent from theme.
        if PINELLAS_HREF in before:
            return {
                "asset": LAYOUT_KEY,
                "theme_id": theme["id"],
                "status": "unchanged",
                "reason": "pinellas_href_present",
                "changed": False,
            }
    if PINELLAS_MARKER in before:
        return {
            "asset": LAYOUT_KEY,
            "theme_id": theme["id"],
            "status": "unchanged",
            "reason": "marker_present",
            "changed": False,
        }
    after = before.rstrip() + "\n" + PINELLAS_THEME_BLOCK
    if dry_run:
        status = "would_append"
    else:
        put_theme_asset(headers, base_url, theme["id"], LAYOUT_KEY, after)
        status = "appended"
    return {
        "asset": LAYOUT_KEY,
        "theme_id": theme["id"],
        "status": status,
        "marker": PINELLAS_MARKER,
        "changed": status != "unchanged",
    }


def submit_indexnow(urls: list[str]) -> dict[str, Any]:
    key = ""
    if INDEXNOW_KEY_PATH.exists():
        key = INDEXNOW_KEY_PATH.read_text().strip()
    key = key or os.getenv("INDEXNOW_KEY", "").strip() or os.getenv("OLS_INDEXNOW_KEY", "").strip()
    if not key:
        return {"status": "skipped", "reason": "no_indexnow_key"}
    if not urls:
        return {"status": "skipped", "reason": "no_urls"}
    host = "organizinglifeservices.com"
    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"https://{host}/{key}.txt",
        "urlList": urls,
    }
    results = {}
    for endpoint in (
        "https://api.indexnow.org/indexnow",
        "https://www.bing.com/indexnow",
    ):
        try:
            resp = _retry(httpx.post, endpoint, json=payload, timeout=30)
            results[endpoint] = {"status_code": resp.status_code}
        except Exception as exc:  # noqa: BLE001
            results[endpoint] = {"error": str(exc)[:200]}
    return {"status": "submitted", "urls": urls, "endpoints": results}


def changed_public_urls(report: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("appraisal", "tampa"):
        block = report.get(key) or {}
        if block.get("changed") and block.get("url"):
            urls.append(block["url"])
    for item in report.get("pinellas_pages") or []:
        if item.get("changed") and item.get("url"):
            urls.append(item["url"])
    theme = report.get("pinellas_theme") or {}
    if theme.get("changed"):
        urls.append(ORG_URL)
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--skip-indexnow",
        action="store_true",
        help="Skip IndexNow after a successful apply.",
    )
    args = parser.parse_args()
    dry_run = not args.apply
    if args.apply:
        require_apply_confirmation()

    print("Session 15 organic growth hubs" + (" (DRY RUN)" if dry_run else ""))
    headers, base_url = shopify_context()
    pages = list_pages(headers, base_url)

    report: dict[str, Any] = {
        "script": "session15_organic_growth_hubs",
        "dry_run": dry_run,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "appraisal": patch_appraisal(headers, base_url, pages, dry_run=dry_run),
        "tampa": patch_tampa(headers, base_url, pages, dry_run=dry_run),
        "pinellas_theme": ensure_pinellas_on_theme(headers, base_url, dry_run=dry_run),
        "pinellas_pages": [
            ensure_pinellas_on_page(
                headers, base_url, pages, handle, label, dry_run=dry_run
            )
            for handle, label in CITY_PINELLAS_TARGETS
        ],
    }

    if dry_run or args.skip_indexnow:
        report["indexnow"] = {
            "status": "skipped",
            "reason": "dry_run" if dry_run else "flag",
        }
    else:
        urls = changed_public_urls(report)
        report["indexnow"] = submit_indexnow(urls)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"session15_organic_growth_hubs_{stamp}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote report: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
