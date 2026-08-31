"""Session 18: article CTR pass for "how-to-find-the-best-antique-buyer".

Why
---
GSC 2026-08-01→08-28 shows a classic rank-#1, 0-CTR snippet mismatch on a
single blog article:

- query ``where to sell antiques locally`` → this URL: 190 impressions,
  0 clicks, position 1.0.

The article ranks first for a seller-intent query, but the live SERP snippet is
framed entirely around *finding a buyer* rather than the searcher's actual job
("where can I sell my antiques locally?"), and the live title is already 61
chars — long enough to be truncated. This pass rewrites THIS article's Shopify
SEO metafields so the snippet speaks to the seller-local intent without keyword
stuffing, competitor names, invented prices, or fake testimonials.

Live title  (2026-08-31 crawl): ``How to Find the Best Antique Buyer | Organizing Life Services`` (61)
Live meta   (2026-08-31 crawl): ``Learn how to find the best antique buyer for your valuable items with expert tips on research, evaluation, and negotiation strategies.``

Scope (deliberately narrow)
---------------------------
- Updates ONLY the article whose handle is
  ``how-to-find-the-best-antique-buyer`` (see :data:`TARGET_HANDLE`). The
  script refuses to write any other article — it selects exactly one matching
  handle and errors if zero or more than one match.
- Writes the Shopify SEO metafields ``global.title_tag`` and
  ``global.description_tag`` (the same article SEO fields used by
  ``data/push_meta_round3_direct.py`` / Session 10 round 3).
- Does NOT touch Shopify products, product SEO fields, fee collections, the
  homepage theme, GTM tags, or ``app/agents/``.

Safety
------
- Default mode is dry-run.
- Live writes require ``--apply`` plus mutation confirmation:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

- Snapshots the article's existing metafields (JSON) before any live write.
- Idempotent once the proposed ``title_tag`` / ``description_tag`` are present.

Usage
-----
    set -a && source .env && set +a
    .venv/bin/python data/session18_antique_buyer_article_ctr.py

    OLS_ALLOW_DATA_MUTATION=1 \\
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \\
    .venv/bin/python data/session18_antique_buyer_article_ctr.py --apply
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

# --- Target (single article only) ----------------------------------------
TARGET_HANDLE = "how-to-find-the-best-antique-buyer"
TARGET_URL = f"https://{HOST}/blogs/news/{TARGET_HANDLE}"

# Article SEO metafields live in the ``global`` namespace as single-line text,
# same as Session 10 round 3 (see data/push_meta_round3_direct.py).
METAFIELD_NAMESPACE = "global"
TITLE_KEY = "title_tag"
DESCRIPTION_KEY = "description_tag"
METAFIELD_TYPE = "single_line_text_field"

# --- Proposed copy -------------------------------------------------------
# Title ≤60 (live is 61 and organizer/buyer-framed); description ~120–160.
# Serves the seller-local intent ``where to sell antiques locally`` while
# staying true to OLS as an estate-sale / personal-property company (NOT a pawn
# shop). Tampa Bay / Florida service-area context and the approved phone number
# (727) 542-6028 are allowed. No competitor names, no invented prices, no fake
# testimonials, no "near me" stuffing.
ARTICLE_TITLE = "Where to Sell Antiques Locally in Tampa Bay | OLS"
ARTICLE_DESCRIPTION = (
    "Where to sell antiques locally? Find a trusted antique buyer in Tampa Bay, "
    "FL, or let our estate sale team handle the sale for you. Call (727) 542-6028."
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


def select_target_article(articles: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the single article whose handle == :data:`TARGET_HANDLE`.

    Refuses to proceed unless exactly one article matches, so this pass can
    never write a different article by accident.
    """
    matches = [a for a in articles if a.get("handle") == TARGET_HANDLE]
    if not matches:
        raise RuntimeError(
            f"Target article handle {TARGET_HANDLE!r} not found among "
            f"{len(articles)} articles"
        )
    if len(matches) > 1:
        raise RuntimeError(
            f"Refusing to write: {len(matches)} articles match handle "
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


# --- Network writes -------------------------------------------------------


def list_articles(headers: dict[str, str], base_url: str) -> list[dict[str, Any]]:
    """Return all blog articles with their owning blog id attached."""
    articles: list[dict[str, Any]] = []
    blogs = get_json(f"{base_url}/blogs.json?limit=250", headers).get("blogs", [])
    for blog in blogs:
        page = get_json(
            f"{base_url}/blogs/{blog['id']}/articles.json?limit=250", headers
        )
        for art in page.get("articles", []):
            art = dict(art)
            art["_blog_id"] = blog["id"]
            articles.append(art)
    return articles


def get_article_metafields(
    headers: dict[str, str], base_url: str, article_id: int
) -> list[dict[str, Any]]:
    data = get_json(
        f"{base_url}/articles/{article_id}/metafields.json", headers
    )
    return data.get("metafields", [])


def upsert_metafield(
    headers: dict[str, str],
    base_url: str,
    article_id: int,
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
        url = f"{base_url}/articles/{article_id}/metafields.json"
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
    assert len(ARTICLE_TITLE) <= 60, f"title too long: {len(ARTICLE_TITLE)}"
    assert 120 <= len(ARTICLE_DESCRIPTION) <= 160, (
        f"description length {len(ARTICLE_DESCRIPTION)} outside 120–160"
    )

    headers, base_url = shopify_context()
    articles = list_articles(headers, base_url)
    target = select_target_article(articles)
    article_id = target["id"]
    blog_id = target.get("_blog_id")

    metafields = get_article_metafields(headers, base_url, article_id)
    title_mf = find_metafield(metafields, TITLE_KEY)
    desc_mf = find_metafield(metafields, DESCRIPTION_KEY)

    title_status = plan_metafield(title_mf, ARTICLE_TITLE)
    desc_status = plan_metafield(desc_mf, ARTICLE_DESCRIPTION)
    changed = title_status != "unchanged" or desc_status != "unchanged"

    result: dict[str, Any] = {
        "mode": "apply" if apply else "dry_run",
        "target_handle": TARGET_HANDLE,
        "target_url": TARGET_URL,
        "blog_id": blog_id,
        "article_id": article_id,
        "article_title": target.get("title"),
        "proposed_title": ARTICLE_TITLE,
        "proposed_title_len": len(ARTICLE_TITLE),
        "proposed_description": ARTICLE_DESCRIPTION,
        "proposed_description_len": len(ARTICLE_DESCRIPTION),
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
        OUT_DIR / f"article_metafields_snapshot_pre_session18_{timestamp}.json"
    )
    snapshot.write_text(
        json.dumps(
            {
                "target_handle": TARGET_HANDLE,
                "article_id": article_id,
                "blog_id": blog_id,
                "article_title": target.get("title"),
                "metafields": metafields,
            },
            indent=2,
        )
    )
    result["snapshot"] = str(snapshot.relative_to(PROJECT_ROOT))

    if title_status != "unchanged":
        title_written = upsert_metafield(
            headers, base_url, article_id, title_mf, TITLE_KEY, ARTICLE_TITLE
        )
        result["title_metafield_id"] = title_written.get("id")
        time.sleep(0.6)
    if desc_status != "unchanged":
        desc_written = upsert_metafield(
            headers,
            base_url,
            article_id,
            desc_mf,
            DESCRIPTION_KEY,
            ARTICLE_DESCRIPTION,
        )
        result["desc_metafield_id"] = desc_written.get("id")

    result["verify"] = {
        "live_url": TARGET_URL,
        "expect_title": ARTICLE_TITLE,
        "expect_meta": ARTICLE_DESCRIPTION,
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
    out_path = OUT_DIR / f"session18_antique_buyer_article_ctr_{timestamp}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nWrote report: {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
