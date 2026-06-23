"""Session 10: targeted fixes from the 2026-06-23 weekly SEO audit.

Scope
-----
This script deliberately implements only the high-signal recommendations from
`docs/seo-audits/2026-06-23-weekly-seo-audit.md`:

1. Rewrite the Personal Property Appraisal page SEO title/description.
2. Demote body-level H1 tags to H2 on conversion/trust pages where the Shopify
   theme already emits the page H1.
3. Patch the live theme's homepage `<title>` and meta description to match
   service-intent queries already earning impressions.
4. Add a theme-level `noindex,follow` meta for thin Shopify utility collections
   (`/collections/all` and `/collections/fees-products`).
5. Demote the contact template's form-section H1 to H2 so `/pages/contact-us`
   has one canonical page H1.

It does NOT touch the 18 intentionally noindexed old event pages.

Safety
------
- Supports `--dry-run`.
- Idempotent: repeated runs no-op once the intended values are present.
- Snapshots `layout/theme.liquid` before a live theme write.
- Writes a JSON report to `data/audit_output/`.
- Live writes are blocked by `data/_mutation_guard.py` unless the operator sets:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

Usage
-----
    set -a && source .env && set +a
    .venv/bin/python data/session10_weekly_seo_fixes.py --dry-run

    OLS_ALLOW_DATA_MUTATION=1 \
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
    .venv/bin/python data/session10_weekly_seo_fixes.py
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from _mutation_guard import activate as activate_data_mutation_guard
except ModuleNotFoundError:  # pragma: no cover - supports module-style imports.
    from data._mutation_guard import activate as activate_data_mutation_guard

activate_data_mutation_guard()

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HOST = "organizinglifeservices.com"
ORG_URL = f"https://{HOST}/"

HOMEPAGE_TITLE = "Estate Sale Organizers Tampa Bay | Appraisals & Downsizing"
HOMEPAGE_DESCRIPTION = (
    "Tampa Bay estate sale organizers for estate sales, appraisals, downsizing, "
    "and cleanouts across Pinellas, Pasco, Hillsborough, Hernando, and Citrus."
)

APPRAISAL_META = {
    "handle": "personal-property-appraisal",
    "title_tag": "Personal Property Appraisers Tampa Bay | Estate Appraisals",
    "description_tag": (
        "Need Tampa personal property appraisers? OLS provides estate sale, "
        "probate, insurance, and downsizing appraisals across Tampa Bay. "
        "Call (727) 542-6028."
    ),
}

H1_DEMOTE_PAGE_HANDLES = [
    "contact-us",
    "about-us",
    "testimonials",
    "senior-services",
]

UTILITY_COLLECTION_HANDLES = ["all", "fees-products"]

INDEXNOW_URLS = [
    ORG_URL,
    f"{ORG_URL}pages/personal-property-appraisal",
    f"{ORG_URL}pages/contact-us",
    f"{ORG_URL}pages/about-us",
    f"{ORG_URL}pages/testimonials",
    f"{ORG_URL}pages/senior-services",
    f"{ORG_URL}collections/all",
    f"{ORG_URL}collections/fees-products",
]

HOMEPAGE_META_MARKER = "HOMEPAGE-SEO-META-V1"
COLLECTION_NOINDEX_MARKER = "SEO-ROBOTS-COLLECTIONS-V1"
CONTACT_H1_MARKER = "CONTACT-H1-DEMOTE-V1"

PAGE_TITLE_LINE_RE = re.compile(r"(?m)^(\s*)\{\{\s*page_title\s*\}\}.*shop\.name.*$")
DESCRIPTION_BLOCK = """    {%- if page_description -%}
    <meta name="description" content="{{ page_description | escape }}">
    {%- endif -%}"""
PAGE_ROBOTS_BLOCK = """    {%- if page and page.metafields.seo.robots != blank -%}
    <meta name="robots" content="{{ page.metafields.seo.robots | escape }}">
    {%- endif -%}"""
CONTACT_H1_LINE = '  <h1 class="h3 mb-3">{{ section.settings.title_page }}</h1>'
CONTACT_H2_PATCH = (
    f"  {{%- comment -%}} {CONTACT_H1_MARKER}: page title already emits the H1 {{%- endcomment -%}}\n"
    '  <h2 class="h3 mb-3">{{ section.settings.title_page }}</h2>'
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


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


def get_pages(headers: dict[str, str], base_url: str) -> dict[str, dict]:
    pages = get_json(f"{base_url}/pages.json?limit=250", headers).get("pages", [])
    return {page["handle"]: page for page in pages}


def list_metafields(headers: dict[str, str], base_url: str, resource: str, owner_id: int) -> list[dict]:
    data = get_json(f"{base_url}/{resource}/{owner_id}/metafields.json", headers)
    return data.get("metafields", [])


def upsert_global_metafield(
    headers: dict[str, str],
    base_url: str,
    resource: str,
    owner_id: int,
    key: str,
    value: str,
    dry_run: bool,
) -> dict[str, Any]:
    metafields = list_metafields(headers, base_url, resource, owner_id)
    existing = next(
        (m for m in metafields if m.get("namespace") == "global" and m.get("key") == key),
        None,
    )
    current = existing.get("value") if existing else None
    if current == value:
        return {"status": "unchanged", "key": key, "existing_id": existing.get("id")}

    if dry_run:
        return {
            "status": "would_update" if existing else "would_create",
            "key": key,
            "before": current,
            "after": value,
        }

    if existing:
        resp = _retry(
            httpx.put,
            f"{base_url}/metafields/{existing['id']}.json",
            headers=headers,
            json={"metafield": {"id": existing["id"], "value": value, "type": "single_line_text_field"}},
            timeout=60,
        )
        action = "updated"
    else:
        resp = _retry(
            httpx.post,
            f"{base_url}/{resource}/{owner_id}/metafields.json",
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
        action = "created"
    resp.raise_for_status()
    return {"status": action, "key": key, "metafield_id": resp.json()["metafield"]["id"]}


def update_appraisal_meta(
    headers: dict[str, str], base_url: str, pages: dict[str, dict], dry_run: bool
) -> dict[str, Any]:
    title = APPRAISAL_META["title_tag"]
    desc = APPRAISAL_META["description_tag"]
    assert len(title) <= 65, f"appraisal title too long: {len(title)}"
    assert len(desc) <= 160, f"appraisal description too long: {len(desc)}"

    page = pages.get(APPRAISAL_META["handle"])
    if not page:
        return {"handle": APPRAISAL_META["handle"], "status": "not_found"}

    results = [
        upsert_global_metafield(headers, base_url, "pages", page["id"], "title_tag", title, dry_run),
        upsert_global_metafield(
            headers, base_url, "pages", page["id"], "description_tag", desc, dry_run
        ),
    ]
    return {
        "handle": APPRAISAL_META["handle"],
        "page_id": page["id"],
        "status": "dry_run" if dry_run else "checked",
        "title_len": len(title),
        "description_len": len(desc),
        "metafields": results,
    }


def demote_body_h1(html: str) -> tuple[str, int]:
    open_count = len(re.findall(r"<\s*h1(?=[\s>])", html, flags=re.IGNORECASE))
    if open_count == 0:
        return html, 0
    updated = re.sub(r"<\s*h1(?=[\s>])", "<h2", html, flags=re.IGNORECASE)
    updated = re.sub(r"</\s*h1\s*>", "</h2>", updated, flags=re.IGNORECASE)
    return updated, open_count


def update_page_h1s(
    headers: dict[str, str], base_url: str, pages: dict[str, dict], dry_run: bool
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for handle in H1_DEMOTE_PAGE_HANDLES:
        page = pages.get(handle)
        if not page:
            results.append({"handle": handle, "status": "not_found"})
            continue
        before = page.get("body_html") or ""
        after, count = demote_body_h1(before)
        if count == 0:
            results.append({"handle": handle, "page_id": page["id"], "status": "unchanged", "h1s": 0})
            continue
        if before == after:
            results.append({"handle": handle, "page_id": page["id"], "status": "unchanged", "h1s": count})
            continue
        if dry_run:
            results.append({
                "handle": handle,
                "page_id": page["id"],
                "status": "would_demote_body_h1",
                "body_h1_count": count,
            })
            continue
        resp = _retry(
            httpx.put,
            f"{base_url}/pages/{page['id']}.json",
            headers=headers,
            json={"page": {"id": page["id"], "body_html": after}},
            timeout=60,
        )
        resp.raise_for_status()
        results.append({
            "handle": handle,
            "page_id": page["id"],
            "status": "demoted_body_h1",
            "body_h1_count": count,
        })
        time.sleep(0.4)
    return results


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


def patch_homepage_meta(source: str) -> tuple[str, bool]:
    if HOMEPAGE_META_MARKER in source:
        return source, False

    title_line = (
        f"      {{%- comment -%}} {HOMEPAGE_META_MARKER}: title {{%- endcomment -%}}\n"
        "      {%- if template.name == 'index' -%}\n"
        f"      {HOMEPAGE_TITLE}\n"
        "      {%- else -%}\n"
        r"\g<0>"
        "\n      {%- endif -%}"
    )
    patched, count = PAGE_TITLE_LINE_RE.subn(title_line, source, count=1)
    if count != 1:
        raise RuntimeError("Could not locate Shopify theme title line for homepage patch")

    description_patch = (
        f"    {{%- comment -%}} {HOMEPAGE_META_MARKER}: description {{%- endcomment -%}}\n"
        "    {%- if template.name == 'index' -%}\n"
        f'    <meta name="description" content="{HOMEPAGE_DESCRIPTION}">\n'
        "    {%- elsif page_description -%}\n"
        '    <meta name="description" content="{{ page_description | escape }}">\n'
        "    {%- endif -%}"
    )
    if DESCRIPTION_BLOCK not in patched:
        raise RuntimeError("Could not locate Shopify theme description block for homepage patch")
    patched = patched.replace(DESCRIPTION_BLOCK, description_patch, 1)
    return patched, True


def patch_collection_noindex(source: str) -> tuple[str, bool]:
    if COLLECTION_NOINDEX_MARKER in source:
        return source, False

    robots_patch = (
        PAGE_ROBOTS_BLOCK
        + f"\n    {{%- comment -%}} {COLLECTION_NOINDEX_MARKER}: noindex thin Shopify utility collections {{%- endcomment -%}}\n"
        "    {%- assign ols_noindex_collection = false -%}\n"
        "    {%- if collection and collection.handle == 'all' -%}\n"
        "      {%- assign ols_noindex_collection = true -%}\n"
        "    {%- elsif collection and collection.handle == 'fees-products' -%}\n"
        "      {%- assign ols_noindex_collection = true -%}\n"
        "    {%- endif -%}\n"
        "    {%- if ols_noindex_collection -%}\n"
        '    <meta name="robots" content="noindex,follow">\n'
        "    {%- endif -%}"
    )
    if PAGE_ROBOTS_BLOCK not in source:
        raise RuntimeError("Could not locate existing SEO-ROBOTS-V1 block for collection noindex patch")
    return source.replace(PAGE_ROBOTS_BLOCK, robots_patch, 1), True


def patch_contact_section_h1(source: str) -> tuple[str, bool]:
    if CONTACT_H1_MARKER in source:
        return source, False
    if CONTACT_H1_LINE not in source:
        raise RuntimeError("Could not locate contact template section H1")
    return source.replace(CONTACT_H1_LINE, CONTACT_H2_PATCH, 1), True


def update_theme(
    headers: dict[str, str], base_url: str, dry_run: bool
) -> dict[str, Any]:
    theme = main_theme(headers, base_url)
    layout_key = "layout/theme.liquid"
    contact_key = "sections/page-contact.liquid"

    before = get_theme_asset(headers, base_url, theme["id"], layout_key)
    after, homepage_changed = patch_homepage_meta(before)
    after, collection_changed = patch_collection_noindex(after)

    contact_before = get_theme_asset(headers, base_url, theme["id"], contact_key)
    contact_after, contact_changed = patch_contact_section_h1(contact_before)

    changed = before != after
    contact_asset_changed = contact_before != contact_after
    result: dict[str, Any] = {
        "theme_id": theme["id"],
        "theme_name": theme.get("name"),
        "homepage_meta": "would_patch" if homepage_changed and dry_run else "patched" if homepage_changed else "unchanged",
        "collection_noindex": (
            "would_patch" if collection_changed and dry_run else "patched" if collection_changed else "unchanged"
        ),
        "contact_section_h1": (
            "would_patch" if contact_changed and dry_run else "patched" if contact_changed else "unchanged"
        ),
        "changed": changed or contact_asset_changed,
    }

    if changed:
        diff = "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile="before/layout/theme.liquid",
                tofile="after/layout/theme.liquid",
                n=3,
            )
        )
        result["diff_preview"] = diff[:6000]

    if contact_asset_changed:
        contact_diff = "\n".join(
            difflib.unified_diff(
                contact_before.splitlines(),
                contact_after.splitlines(),
                fromfile=f"before/{contact_key}",
                tofile=f"after/{contact_key}",
                n=3,
            )
        )
        result["contact_diff_preview"] = contact_diff[:3000]

    if dry_run or not (changed or contact_asset_changed):
        return result

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshots = []
    if changed:
        snapshot_path = OUT_DIR / f"theme_layout_snapshot_pre_session10_{timestamp}.liquid"
        snapshot_path.write_text(before)
        put_theme_asset(headers, base_url, theme["id"], layout_key, after)
        snapshots.append(str(snapshot_path.relative_to(PROJECT_ROOT)))
    if contact_asset_changed:
        snapshot_path = OUT_DIR / f"theme_page_contact_snapshot_pre_session10_{timestamp}.liquid"
        snapshot_path.write_text(contact_before)
        put_theme_asset(headers, base_url, theme["id"], contact_key, contact_after)
        snapshots.append(str(snapshot_path.relative_to(PROJECT_ROOT)))
    result["snapshot_paths"] = snapshots
    return result


def _is_indexnow_key(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{32}", value.strip()))


def recover_indexnow_key(headers: dict[str, str], base_url: str) -> dict[str, Any]:
    env_key = (os.getenv("INDEXNOW_KEY") or os.getenv("OLS_INDEXNOW_KEY") or "").strip()
    if _is_indexnow_key(env_key):
        return {"status": "found", "source": "environment", "key": env_key}

    key_file = OUT_DIR / "indexnow_key.txt"
    if key_file.exists():
        file_key = key_file.read_text().strip()
        if _is_indexnow_key(file_key):
            return {"status": "found", "source": str(key_file.relative_to(PROJECT_ROOT)), "key": file_key}

    pages = get_json(f"{base_url}/pages.json?limit=250", headers).get("pages", [])
    for page in pages:
        handle = (page.get("handle") or "").strip()
        body = (page.get("body_html") or "").strip()
        if (
            _is_indexnow_key(handle)
            and body == handle
            and page.get("template_suffix") == "indexnow"
        ):
            return {
                "status": "found",
                "source": "shopify_page",
                "key": handle,
                "page_id": page.get("id"),
            }

    return {"status": "missing", "key": ""}


def create_indexnow_key_in_shopify(
    headers: dict[str, str], base_url: str, dry_run: bool
) -> dict[str, Any]:
    key = uuid.uuid4().hex
    if dry_run:
        return {"status": "would_create", "key": key}

    page_resp = _retry(
        httpx.post,
        f"{base_url}/pages.json",
        headers=headers,
        timeout=30,
        json={
            "page": {
                "title": "IndexNow Key",
                "handle": key,
                "body_html": key,
                "template_suffix": "indexnow",
                "published": True,
            }
        },
    )
    page_resp.raise_for_status()
    return {"status": "created", "key": key, "page_id": page_resp.json()["page"]["id"]}


def ensure_indexnow_template_and_redirect(
    headers: dict[str, str],
    base_url: str,
    key: str,
    dry_run: bool,
) -> dict[str, Any]:
    theme = main_theme(headers, base_url)
    template_key = "templates/page.indexnow.liquid"
    template_value = "{%- layout none -%}{{ page.content | strip_html | strip }}"

    template_status = "unchanged"
    try:
        current = get_theme_asset(headers, base_url, theme["id"], template_key)
    except httpx.HTTPStatusError:
        current = ""
    if current != template_value:
        template_status = "would_update" if dry_run else "updated"
        if not dry_run:
            put_theme_asset(headers, base_url, theme["id"], template_key, template_value)

    redirects = get_json(f"{base_url}/redirects.json?path=/{key}.txt&limit=5", headers).get(
        "redirects", []
    )
    redirect_exists = any(
        item.get("path") == f"/{key}.txt" and item.get("target") == f"/pages/{key}"
        for item in redirects
    )
    redirect_status = "unchanged"
    if not redirect_exists:
        redirect_status = "would_create" if dry_run else "created"
        if not dry_run:
            resp = _retry(
                httpx.post,
                f"{base_url}/redirects.json",
                headers=headers,
                timeout=30,
                json={"redirect": {"path": f"/{key}.txt", "target": f"/pages/{key}"}},
            )
            resp.raise_for_status()

    public_url = f"{ORG_URL}{key}.txt"
    verify_status = "skipped_dry_run"
    if not dry_run:
        resp = _retry(httpx.get, public_url, follow_redirects=True, timeout=30)
        verify_status = "ok" if resp.status_code == 200 and resp.text.strip() == key else "failed"

    return {
        "template": template_status,
        "redirect": redirect_status,
        "public_key_url": f"{ORG_URL}[redacted-key].txt",
        "public_key_verification": verify_status,
    }


def submit_indexnow(
    headers: dict[str, str],
    base_url: str,
    dry_run: bool,
) -> dict[str, Any]:
    recovered = recover_indexnow_key(headers, base_url)
    if recovered.get("status") == "missing":
        recovered = create_indexnow_key_in_shopify(headers, base_url, dry_run)

    key = recovered.get("key", "")
    if not _is_indexnow_key(key):
        return {"status": "skipped", "reason": "no valid IndexNow key", "key_source": recovered}

    setup = ensure_indexnow_template_and_redirect(headers, base_url, key, dry_run)
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"{ORG_URL}{key}.txt",
        "urlList": INDEXNOW_URLS,
    }
    endpoints = [
        "https://api.indexnow.org/IndexNow",
        "https://www.bing.com/indexnow",
        "https://yandex.com/indexnow",
    ]
    if dry_run:
        return {
            "status": "would_submit",
            "url_count": len(INDEXNOW_URLS),
            "endpoints": endpoints,
            "key_source": {k: v for k, v in recovered.items() if k != "key"},
            "setup": setup,
        }

    results = []
    for endpoint in endpoints:
        resp = _retry(httpx.post, endpoint, json=payload, timeout=30)
        results.append({"endpoint": endpoint, "status_code": resp.status_code, "body": resp.text[:300]})
    return {
        "status": "submitted",
        "url_count": len(INDEXNOW_URLS),
        "key_source": {k: v for k, v in recovered.items() if k != "key"},
        "setup": setup,
        "results": results,
    }


def write_report(report: dict[str, Any]) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"session10_weekly_seo_fixes_{timestamp}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True))
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-indexnow", action="store_true")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")

    if len(HOMEPAGE_TITLE) > 65:
        sys.exit(f"Homepage title too long: {len(HOMEPAGE_TITLE)}")
    if len(HOMEPAGE_DESCRIPTION) > 160:
        sys.exit(f"Homepage description too long: {len(HOMEPAGE_DESCRIPTION)}")

    print("Session 10 weekly SEO fixes" + (" (DRY RUN)" if args.dry_run else ""))
    headers, base_url = shopify_context()
    pages = get_pages(headers, base_url)

    report: dict[str, Any] = {
        "dry_run": args.dry_run,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": {
            "appraisal_page": APPRAISAL_META["handle"],
            "h1_demote_pages": H1_DEMOTE_PAGE_HANDLES,
            "utility_collections_noindex": UTILITY_COLLECTION_HANDLES,
            "indexnow_urls": INDEXNOW_URLS,
        },
        "appraisal_meta": update_appraisal_meta(headers, base_url, pages, args.dry_run),
        "h1_demotions": update_page_h1s(headers, base_url, pages, args.dry_run),
        "theme": update_theme(headers, base_url, args.dry_run),
    }

    if args.skip_indexnow:
        report["indexnow"] = {"status": "skipped", "reason": "--skip-indexnow"}
    else:
        report["indexnow"] = submit_indexnow(headers, base_url, args.dry_run)

    report_path = write_report(report)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"\nReport written to {report_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
