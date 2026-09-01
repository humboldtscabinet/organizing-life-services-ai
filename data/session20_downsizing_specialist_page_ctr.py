"""Session 20: page CTR pass for the "downsizing-moving-sales" Shopify page.

Why
---
GSC 2026-08-01→08-28 (deep audit
``data/audit_output/deep_seo_audit_20260831_120737.json``) shows a classic
rank-with-no-CTR snippet mismatch on an EXISTING Shopify page (not a blog
article):

- query ``downsizing specialist`` on this URL: 62 impressions, 0 clicks,
  CTR 0, position 3.7.
- page totals: 179 impressions, 2 clicks, position 22.2.

The page already ranks in the top ~4 for ``downsizing specialist``, but the
live SERP snippet does not name that job. This pass rewrites THIS page's
Shopify SEO metafields (``global.title_tag`` / ``global.description_tag``, the
same page SEO fields used by Session 10 / Session 11) so the snippet states the
searcher's intent in one sentence and adds Tampa Bay service-area context plus
the approved phone, without keyword stuffing, competitor names, invented
prices, testimonials, street addresses, or GTM tags.

Live title (2026-08-31 crawl): ``Downsizing & Moving Sales in Greater Tampa Bay Area`` (50)
Live H1    (2026-08-31 crawl): ``Downsizing Help & Moving Sales | Organizing Life Services``
Live meta  (2026-08-31 crawl): ``Simplify downsizing and moving with our efficient services. Transform your space and embrace a more organized life. Contact us today!``

H1 is deliberately left unchanged (this pass edits only the SEO title/meta
metafields, exactly like Session 19). The page body, H1, GTM container
``GTM-KQ76X4NR``, and phone ``(727) 542-6028`` are not touched.

Scope (deliberately narrow)
---------------------------
- Updates ONLY the page whose handle is ``downsizing-moving-sales`` (see
  :data:`TARGET_HANDLE`). The script selects exactly one matching handle and
  errors if zero or more than one match, so it can never write a different
  page by accident.
- Writes the Shopify SEO metafields ``global.title_tag`` and
  ``global.description_tag`` only (same page SEO fields as Session 10 / 11).
- Does NOT touch the page body/H1, Shopify products, product SEO fields, fee
  collections, the homepage theme, GTM tags, ads, GBP, ``app/agents/``, the
  dashboard Apply path, or any other page.
- Deliberately does NOT target the Tampa hub
  ``/pages/estate-sale-tampa-hillsborough-county`` (a rank-position job, not a
  snippet job) and does NOT create any new Palm Harbor URL.

Safety
------
- Default mode is dry-run.
- Live writes require ``--apply`` plus mutation confirmation:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

- Snapshots the page's existing metafields (JSON) before any live write.
- Idempotent once the proposed ``title_tag`` / ``description_tag`` are present.

Usage
-----
    set -a && source .env && set +a
    .venv/bin/python data/session20_downsizing_specialist_page_ctr.py

    OLS_ALLOW_DATA_MUTATION=1 \\
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \\
    .venv/bin/python data/session20_downsizing_specialist_page_ctr.py --apply
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
    from _mutation_guard import activate as activate_data_mutation_guard
except ModuleNotFoundError:  # pragma: no cover
    from data._mutation_guard import activate as activate_data_mutation_guard

activate_data_mutation_guard()

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HOST = "organizinglifeservices.com"

# --- Target (single page only) -------------------------------------------
TARGET_HANDLE = "downsizing-moving-sales"
TARGET_URL = f"https://{HOST}/pages/{TARGET_HANDLE}"

# Page SEO metafields live in the ``global`` namespace as single-line text,
# same as Session 10 / Session 11 (see data/session11_service_area_first_wave.py).
METAFIELD_NAMESPACE = "global"
TITLE_KEY = "title_tag"
DESCRIPTION_KEY = "description_tag"
METAFIELD_TYPE = "single_line_text_field"

# --- Proposed copy -------------------------------------------------------
# Title ≤60 (live is 50 and generic); description ≤160. Serves the query
# ``downsizing specialist`` (GSC pos 3.7, 62 impr, 0 clicks) by naming that job
# in the title and answering it in one sentence, while staying true to OLS as a
# downsizing / estate-sale / personal-property company. Tampa Bay service-area
# context and the approved phone (727) 542-6028 are allowed. No keyword
# stuffing, no "near me", no competitor names, no invented prices/testimonials,
# no street addresses, no GTM tags. H1 is left unchanged.
PAGE_TITLE = "Downsizing Specialist in Tampa Bay | Moving Sales | OLS"
PAGE_DESCRIPTION = (
    "Need a downsizing specialist in Tampa Bay? OLS handles sorting, "
    "moving sales, and cleanouts. Call (727) 542-6028."
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


# --- Pure helpers (unit-tested; no network) ------------------------------


def select_target_page(pages: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the single page whose handle == :data:`TARGET_HANDLE`.

    Refuses to proceed unless exactly one page matches, so this pass can never
    write a different page by accident.
    """
    matches = [p for p in pages if p.get("handle") == TARGET_HANDLE]
    if not matches:
        raise RuntimeError(
            f"Target page handle {TARGET_HANDLE!r} not found among "
            f"{len(pages)} pages"
        )
    if len(matches) > 1:
        raise RuntimeError(
            f"Refusing to write: {len(matches)} pages match handle "
            f"{TARGET_HANDLE!r}; expected exactly one"
        )
    return matches[0]


def find_metafield(
    metafields: list[dict[str, Any]], key: str
) -> dict[str, Any] | None:
    return next(
        (
            m
            for m in metafields
            if m.get("namespace") == METAFIELD_NAMESPACE and m.get("key") == key
        ),
        None,
    )


def plan_metafield(existing: dict[str, Any] | None, value: str) -> str:
    """Classify the write for one metafield: ``unchanged`` / ``update`` / ``create``."""
    if existing is None:
        return "create"
    if existing.get("value") == value:
        return "unchanged"
    return "update"


# --- Network reads / writes ----------------------------------------------


def list_pages(headers: dict[str, str], base_url: str) -> list[dict[str, Any]]:
    """Return all Shopify pages (paginated)."""
    pages: list[dict[str, Any]] = []
    url = f"{base_url}/pages.json?limit=250"
    while url:
        resp = _retry(httpx.get, url, headers=headers, timeout=60)
        resp.raise_for_status()
        pages.extend(resp.json().get("pages", []))
        link = resp.headers.get("link", "")
        next_url = ""
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip()[1:-1]
        url = next_url
    return pages


def get_page_metafields(
    headers: dict[str, str], base_url: str, page_id: int
) -> list[dict[str, Any]]:
    data = get_json(f"{base_url}/pages/{page_id}/metafields.json", headers)
    return data.get("metafields", [])


def upsert_metafield(
    headers: dict[str, str],
    base_url: str,
    page_id: int,
    existing: dict[str, Any] | None,
    key: str,
    value: str,
) -> dict[str, Any]:
    if existing is not None:
        url = f"{base_url}/metafields/{existing['id']}.json"
        body = {
            "metafield": {
                "id": existing["id"],
                "value": value,
                "type": METAFIELD_TYPE,
            }
        }
        resp = _retry(httpx.put, url, headers=headers, json=body, timeout=60)
    else:
        url = f"{base_url}/pages/{page_id}/metafields.json"
        body = {
            "metafield": {
                "namespace": METAFIELD_NAMESPACE,
                "key": key,
                "value": value,
                "type": METAFIELD_TYPE,
            }
        }
        resp = _retry(httpx.post, url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()["metafield"]


def run(*, apply: bool) -> dict[str, Any]:
    dry_run = not apply
    assert len(PAGE_TITLE) <= 60, f"title too long: {len(PAGE_TITLE)}"
    assert 100 <= len(PAGE_DESCRIPTION) <= 160, (
        f"description length {len(PAGE_DESCRIPTION)} outside 100–160"
    )

    headers, base_url = shopify_context()
    pages = list_pages(headers, base_url)
    target = select_target_page(pages)
    page_id = target["id"]

    metafields = get_page_metafields(headers, base_url, page_id)
    title_mf = find_metafield(metafields, TITLE_KEY)
    desc_mf = find_metafield(metafields, DESCRIPTION_KEY)

    title_status = plan_metafield(title_mf, PAGE_TITLE)
    desc_status = plan_metafield(desc_mf, PAGE_DESCRIPTION)
    changed = title_status != "unchanged" or desc_status != "unchanged"

    result: dict[str, Any] = {
        "mode": "apply" if apply else "dry_run",
        "target_handle": TARGET_HANDLE,
        "target_url": TARGET_URL,
        "page_id": page_id,
        "page_title": target.get("title"),
        "proposed_title": PAGE_TITLE,
        "proposed_title_len": len(PAGE_TITLE),
        "proposed_description": PAGE_DESCRIPTION,
        "proposed_description_len": len(PAGE_DESCRIPTION),
        "current_title_tag": title_mf.get("value") if title_mf else None,
        "current_description_tag": desc_mf.get("value") if desc_mf else None,
        "title_status": (
            f"would_{title_status}"
            if dry_run and title_status != "unchanged"
            else title_status
        ),
        "description_status": (
            f"would_{desc_status}"
            if dry_run and desc_status != "unchanged"
            else desc_status
        ),
        "changed": changed,
    }

    if dry_run or not changed:
        return result

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = (
        OUT_DIR / f"page_metafields_snapshot_pre_session20_{timestamp}.json"
    )
    snapshot.write_text(
        json.dumps(
            {
                "target_handle": TARGET_HANDLE,
                "page_id": page_id,
                "page_title": target.get("title"),
                "metafields": metafields,
            },
            indent=2,
        )
    )
    result["snapshot"] = str(snapshot.relative_to(PROJECT_ROOT))

    if title_status != "unchanged":
        title_written = upsert_metafield(
            headers, base_url, page_id, title_mf, TITLE_KEY, PAGE_TITLE
        )
        result["title_metafield_id"] = title_written.get("id")
        time.sleep(0.6)
    if desc_status != "unchanged":
        desc_written = upsert_metafield(
            headers,
            base_url,
            page_id,
            desc_mf,
            DESCRIPTION_KEY,
            PAGE_DESCRIPTION,
        )
        result["desc_metafield_id"] = desc_written.get("id")

    result["verify"] = {
        "live_url": TARGET_URL,
        "expect_title": PAGE_TITLE,
        "expect_meta": PAGE_DESCRIPTION,
    }
    return result


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform live Shopify metafield writes (requires mutation guard env).",
    )
    args = parser.parse_args()
    result = run(apply=args.apply)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = (
        OUT_DIR / f"session20_downsizing_specialist_page_ctr_{timestamp}.json"
    )
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nWrote report: {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
