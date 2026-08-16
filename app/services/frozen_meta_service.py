"""Frozen Shopify title/meta drafts for DashboardTask Apply.

Apply never invents copy. The payload must already contain new_title and
new_meta_description. v1 supports pages and blog articles only.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

TITLE_MAX = 60
META_MAX = 155
ACTION_KIND = "shopify.apply_frozen_meta"

_PRODUCT_PREFIXES = ("/products/",)
_COLLECTION_PREFIXES = ("/collections/",)
_HOMEPAGE_PATHS = {"/", ""}


def normalize_path(page_url: str) -> str:
    if not page_url:
        return ""
    value = page_url.strip()
    parsed = urlparse(value if "://" in value else f"https://example.invalid{value if value.startswith('/') else '/' + value}")
    path = parsed.path or "/"
    return path.rstrip("/") or "/"


def classify_gsc_url(page_url: str) -> dict[str, Any]:
    """Map a GSC page URL to a Shopify resource kind (no network)."""
    path = normalize_path(page_url)
    if path in _HOMEPAGE_PATHS:
        return {"kind": "homepage", "path": path}
    if path.startswith(_PRODUCT_PREFIXES):
        return {"kind": "blocked", "reason": "product", "path": path}
    if path.startswith(_COLLECTION_PREFIXES):
        return {"kind": "blocked", "reason": "collection", "path": path}
    if path.startswith("/pages/"):
        handle = path.split("/pages/", 1)[1].split("/")[0]
        if not handle:
            return {"kind": "unknown", "path": path}
        return {"kind": "page", "path": path, "handle": handle}
    if path.startswith("/blogs/"):
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 3:
            return {
                "kind": "article",
                "path": path,
                "blog_handle": parts[1],
                "article_handle": parts[2],
            }
        return {"kind": "unknown", "path": path}
    return {"kind": "unknown", "path": path}


def clip_title(value: str) -> str:
    text = " ".join((value or "").split())
    return text[:TITLE_MAX]


def clip_meta(value: str) -> str:
    text = " ".join((value or "").split())
    return text[:META_MAX]


def draft_title(query: str, current_title: str = "") -> str:
    current = (current_title or "").strip()
    q = (query or "").strip()
    if q and q.lower() in current.lower() and current:
        return clip_title(current)
    if q:
        return clip_title(f"{q.title()} | Organizing Life Services")
    return clip_title(current or "Organizing Life Services | Tampa Bay")


def draft_meta(query: str, current_meta: str = "") -> str:
    current = (current_meta or "").strip()
    q = (query or "").strip()
    if current and q.lower() in current.lower():
        return clip_meta(current)
    if q:
        return clip_meta(
            f"Need help with {q}? Organizing Life Services serves Tampa Bay "
            "estate sales and related services. Call OLS today."
        )
    return clip_meta(
        current
        or "Organizing Life Services helps Tampa Bay families with estate sales "
        "and related services. Call OLS today."
    )


def frozen_meta_fingerprint(
    resource: str,
    resource_id: int | str,
    new_title: str,
    new_meta: str,
) -> str:
    digest = hashlib.sha256(f"{new_title}|{new_meta}".encode("utf-8")).hexdigest()[:12]
    return f"{ACTION_KIND}:{resource}:{resource_id}:{digest}"


def payload_has_frozen_copy(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    title = (payload.get("new_title") or "").strip()
    meta = (payload.get("new_meta_description") or "").strip()
    return bool(title and meta)


def _find_page(handle: str) -> dict[str, Any] | None:
    from app.services.shopify_service import get_pages

    for page in get_pages(limit=250):
        if (page.get("handle") or "") == handle:
            return page
    return None


def _find_article(blog_handle: str, article_handle: str) -> dict[str, Any] | None:
    from app.services.shopify_service import get_blog_articles, get_blogs

    for blog in get_blogs():
        if (blog.get("handle") or "") != blog_handle:
            continue
        blog_id = blog.get("id")
        if not blog_id:
            continue
        for article in get_blog_articles(blog_id, limit=250):
            if (article.get("handle") or "") == article_handle:
                return {**article, "blog_id": blog_id, "blog_handle": blog_handle}
    return None


def resolve_and_draft(
    page_url: str,
    query: str,
    *,
    lookup: bool = True,
) -> dict[str, Any] | None:
    """Return a frozen payload, or None if this URL is not an applyable v1 target."""
    classified = classify_gsc_url(page_url)
    kind = classified.get("kind")
    if kind in {"homepage", "blocked", "unknown"}:
        return None
    if not lookup:
        return None

    try:
        if kind == "page":
            page = _find_page(classified["handle"])
            if not page or not page.get("id"):
                return None
            current_title = page.get("title") or ""
            new_title = draft_title(query, current_title)
            new_meta = draft_meta(query, "")
            resource_id = int(page["id"])
            payload = {
                "resource": "page",
                "page_id": resource_id,
                "handle": classified["handle"],
                "path": classified["path"],
                "query": query,
                "current_title": current_title,
                "current_meta_description": "",
                "new_title": new_title,
                "new_meta_description": new_meta,
                "preview": {
                    "resource": "page",
                    "handle": classified["handle"],
                    "new_title": new_title,
                    "new_meta_description": new_meta,
                },
            }
            return {
                "action_kind": ACTION_KIND,
                "fingerprint": frozen_meta_fingerprint(
                    "page", resource_id, new_title, new_meta
                ),
                "action_payload": payload,
            }

        if kind == "article":
            article = _find_article(
                classified["blog_handle"], classified["article_handle"]
            )
            if not article or not article.get("id") or not article.get("blog_id"):
                return None
            current_title = article.get("title") or ""
            new_title = draft_title(query, current_title)
            new_meta = draft_meta(query, article.get("summary_html") or "")
            resource_id = int(article["id"])
            blog_id = int(article["blog_id"])
            payload = {
                "resource": "article",
                "article_id": resource_id,
                "blog_id": blog_id,
                "handle": classified["article_handle"],
                "blog_handle": classified["blog_handle"],
                "path": classified["path"],
                "query": query,
                "current_title": current_title,
                "current_meta_description": "",
                "new_title": new_title,
                "new_meta_description": new_meta,
                "preview": {
                    "resource": "article",
                    "handle": classified["article_handle"],
                    "new_title": new_title,
                    "new_meta_description": new_meta,
                },
            }
            return {
                "action_kind": ACTION_KIND,
                "fingerprint": frozen_meta_fingerprint(
                    "article", resource_id, new_title, new_meta
                ),
                "action_payload": payload,
            }
    except Exception:
        logger.exception("Shopify lookup failed for frozen meta on %s", page_url)
        return None
    return None


def validate_frozen_payload(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return (resource, write_fields). Raises ValueError on refuse."""
    resource = payload.get("resource")
    new_title = clip_title(str(payload.get("new_title") or ""))
    new_meta = clip_meta(str(payload.get("new_meta_description") or ""))
    if not new_title or not new_meta:
        raise ValueError("Frozen payload requires new_title and new_meta_description")
    if len(new_title) > TITLE_MAX or len(new_meta) > META_MAX:
        raise ValueError("Frozen title/meta exceeds length caps")
    path = payload.get("path") or ""
    classified = classify_gsc_url(path) if path else {"kind": resource}
    if classified.get("kind") in {"homepage", "blocked"}:
        raise ValueError("Frozen meta refuses homepage, products, and collections")
    if resource == "page":
        page_id = payload.get("page_id")
        if not page_id:
            raise ValueError("page_id is required")
        return "page", {
            "page_id": int(page_id),
            "title": new_title,
            "meta_description": new_meta,
        }
    if resource == "article":
        article_id = payload.get("article_id")
        blog_id = payload.get("blog_id")
        if not article_id or not blog_id:
            raise ValueError("blog_id and article_id are required")
        return "article", {
            "blog_id": int(blog_id),
            "article_id": int(article_id),
            "title": new_title,
            "meta_description": new_meta,
        }
    raise ValueError(f"Unsupported frozen meta resource: {resource}")
