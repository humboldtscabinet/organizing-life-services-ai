"""
Shopify SEO Override Auditor

For every Shopify page, blog article, and product, compare:
  - The SEO title (`metafields_global_title_tag`) stored in Shopify
  - vs. the rendered <title> from the live HTML

When these differ, the storefront theme (or a Shopify-level append like
" – Organizing Life Services") is overriding our optimization. This is
what caused 37 pages to flag `title_too_long` even after the meta
rewrite passes shipped.

Also flags Shopify-side length issues (title >60 chars stored,
meta description >155 chars stored).
"""

from __future__ import annotations

import os

import httpx

from app.services import seo_crawler, shopify_service


TITLE_LIMIT = 60
META_LIMIT = 155


def _build_url(handle: str, kind: str, blog_handle: str | None = None) -> str:
    """Translate a Shopify resource handle into its public URL."""
    store_url = os.getenv(
        "SHOPIFY_PUBLIC_URL", "https://organizinglifeservices.com"
    ).rstrip("/")
    if kind == "page":
        return f"{store_url}/pages/{handle}"
    if kind == "product":
        return f"{store_url}/products/{handle}"
    if kind == "article" and blog_handle:
        return f"{store_url}/blogs/{blog_handle}/{handle}"
    return ""


def _read_seo_metafields(kind: str, resource_id: int) -> dict:
    """
    Read SEO title + description from the resource's metafields
    (`global.title_tag`, `global.description_tag`).
    """
    headers = shopify_service._shopify_headers()
    endpoint = {
        "page": f"pages/{resource_id}/metafields.json",
        "product": f"products/{resource_id}/metafields.json",
        "article": f"articles/{resource_id}/metafields.json",
    }.get(kind)
    if not endpoint:
        return {}

    url = shopify_service._shopify_url(endpoint)
    try:
        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError:
        return {}

    out = {}
    for mf in resp.json().get("metafields", []):
        if mf.get("namespace") == "global":
            if mf.get("key") == "title_tag":
                out["seo_title"] = mf.get("value", "")
            elif mf.get("key") == "description_tag":
                out["seo_description"] = mf.get("value", "")
    return out


def _compare(resource: dict, kind: str, blog_handle: str | None = None) -> dict:
    """Compare a single resource's stored SEO fields vs the live HTML."""
    handle = resource.get("handle", "")
    url = _build_url(handle, kind, blog_handle)
    if not url:
        return {}

    seo = _read_seo_metafields(kind, resource["id"])
    stored_title = seo.get("seo_title") or resource.get("title", "")
    stored_meta = seo.get("seo_description", "")

    live = seo_crawler.audit_page(url, ua=seo_crawler.UA_BROWSER)
    live_title = (live.get("title") or "").strip()
    live_meta = (live.get("meta_description") or "").strip()

    flags = []
    if stored_title and live_title and stored_title.strip() != live_title:
        flags.append("title_overridden_by_theme")
    if stored_meta and live_meta and stored_meta.strip() != live_meta:
        flags.append("meta_overridden_by_theme")
    if stored_title and len(stored_title) > TITLE_LIMIT:
        flags.append("stored_title_too_long")
    if stored_meta and len(stored_meta) > META_LIMIT:
        flags.append("stored_meta_too_long")
    if not stored_title:
        flags.append("missing_stored_title")
    if not stored_meta:
        flags.append("missing_stored_meta")
    if live.get("title_len", 0) > 65:
        flags.append("live_title_too_long")

    return {
        "kind": kind,
        "id": resource["id"],
        "handle": handle,
        "url": url,
        "stored_title": stored_title,
        "stored_title_len": len(stored_title or ""),
        "live_title": live_title,
        "live_title_len": len(live_title or ""),
        "stored_meta": stored_meta,
        "stored_meta_len": len(stored_meta or ""),
        "live_meta": live_meta,
        "live_meta_len": len(live_meta or ""),
        "live_status": live.get("status"),
        "flags": flags,
    }


def audit_shopify_seo_overrides(
    include_products: bool = False,
    max_articles_per_blog: int = 100,
) -> dict:
    """
    Walk Shopify pages + articles (and optionally products) and report
    every resource whose stored SEO title/meta differs from the live HTML
    rendering, or whose stored values exceed length limits.
    """
    results: list[dict] = []

    # Pages
    for p in shopify_service.get_pages(limit=250):
        cmp = _compare(p, "page")
        if cmp:
            results.append(cmp)

    # Articles (per blog)
    for blog in shopify_service.get_blogs():
        articles = shopify_service.get_blog_articles(
            blog_id=blog["id"], limit=max_articles_per_blog
        )
        for a in articles:
            cmp = _compare(a, "article", blog_handle=blog.get("handle"))
            if cmp:
                results.append(cmp)

    # Products (optional)
    if include_products:
        for prod in shopify_service.get_products(limit=250):
            cmp = _compare(prod, "product")
            if cmp:
                results.append(cmp)

    flagged = [r for r in results if r["flags"]]
    flag_counts: dict[str, int] = {}
    for r in flagged:
        for f in r["flags"]:
            flag_counts[f] = flag_counts.get(f, 0) + 1

    overridden = [
        r for r in flagged
        if "title_overridden_by_theme" in r["flags"]
        or "meta_overridden_by_theme" in r["flags"]
    ]

    return {
        "resources_audited": len(results),
        "resources_flagged": len(flagged),
        "flag_counts": dict(sorted(flag_counts.items(), key=lambda x: -x[1])),
        "theme_overrides": overridden,
        "all_flagged": flagged,
    }
