"""
Shopify — Store Data & Content Service

Reads and writes store data via the Shopify Admin API.
Uses Client Credentials auth (Dev Dashboard custom app).

Capabilities:
  - Read products, pages, blog posts, orders
  - Update meta titles, descriptions, page content
  - Pull order data for the shopify_orders pipeline
  - Create URL redirects (301) for thin/archived pages
  - Create new pages (portfolio pages, etc.)
  - Delete pages (after redirect is in place)

Manual-approval mode: all write operations require explicit trigger.
"""

import os

import httpx
from sqlalchemy.orm import Session

from app.db.models import ShopifyOrder, WorkflowLog

_access_token_cache = {"token": None}


def _get_access_token() -> str:
    """
    Get a Shopify access token using Client Credentials grant.

    Caches the token for reuse within the same process.
    """
    if _access_token_cache["token"]:
        return _access_token_cache["token"]

    store = os.getenv("SHOPIFY_STORE")
    client_id = os.getenv("SHOPIFY_CLIENT_ID")
    client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")

    if not all([store, client_id, client_secret]):
        raise ValueError(
            "Missing Shopify credentials. Set SHOPIFY_STORE, "
            "SHOPIFY_CLIENT_ID, and SHOPIFY_CLIENT_SECRET in .env."
        )

    resp = httpx.post(
        f"https://{store}.myshopify.com/admin/oauth/access_token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    _access_token_cache["token"] = token
    return token


def _shopify_headers() -> dict:
    """Build request headers for Shopify Admin API calls."""
    token = _get_access_token()
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }


def _shopify_url(endpoint: str) -> str:
    """Build a full Shopify Admin API URL."""
    store = os.getenv("SHOPIFY_STORE")
    version = os.getenv("SHOPIFY_API_VERSION", "2024-10")
    return f"https://{store}.myshopify.com/admin/api/{version}/{endpoint}"


# ===================== Read Operations =====================


def get_products(limit: int = 50) -> list:
    """Fetch products from the store."""
    headers = _shopify_headers()
    url = _shopify_url(f"products.json?limit={limit}")

    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("products", [])


def get_pages(limit: int = 50) -> list:
    """Fetch pages (About, Contact, etc.) from the store."""
    headers = _shopify_headers()
    url = _shopify_url(f"pages.json?limit={limit}")

    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("pages", [])


def get_blogs() -> list:
    """Fetch all blogs from the store."""
    headers = _shopify_headers()
    url = _shopify_url("blogs.json")

    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("blogs", [])


def get_blog_articles(blog_id: int, limit: int = 50) -> list:
    """Fetch articles from a specific blog."""
    headers = _shopify_headers()
    url = _shopify_url(f"blogs/{blog_id}/articles.json?limit={limit}")

    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("articles", [])


def get_orders(limit: int = 50, status: str = "any") -> list:
    """Fetch orders from the store."""
    headers = _shopify_headers()
    url = _shopify_url(f"orders.json?limit={limit}&status={status}")

    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("orders", [])


def get_store_metafields() -> list:
    """Fetch store-level metafields (SEO settings, etc.)."""
    headers = _shopify_headers()
    url = _shopify_url("metafields.json")

    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("metafields", [])


# ===================== Write Operations (SEO) =====================


def update_product_seo(
    product_id: int,
    title: str = None,
    meta_description: str = None,
    handle: str = None,
) -> dict:
    """
    Update a product's SEO fields.

    Only updates fields that are provided (non-None).
    """
    headers = _shopify_headers()
    url = _shopify_url(f"products/{product_id}.json")

    product_data = {}
    if title is not None:
        product_data["title"] = title
    if meta_description is not None:
        product_data["metafields_global_description_tag"] = meta_description
    if handle is not None:
        product_data["handle"] = handle

    if not product_data:
        return {"status": "no_changes", "product_id": product_id}

    product_data["id"] = product_id

    resp = httpx.put(
        url,
        headers=headers,
        json={"product": product_data},
        timeout=30,
    )
    resp.raise_for_status()
    return {
        "status": "updated",
        "product_id": product_id,
        "fields_updated": list(product_data.keys()),
    }


def update_page_seo(
    page_id: int,
    title: str = None,
    body_html: str = None,
    meta_description: str = None,
) -> dict:
    """
    Update a page's title, content, or meta description.
    """
    headers = _shopify_headers()
    url = _shopify_url(f"pages/{page_id}.json")

    page_data = {}
    if title is not None:
        page_data["title"] = title
    if body_html is not None:
        page_data["body_html"] = body_html
    if meta_description is not None:
        page_data["metafield"] = {
            "namespace": "global",
            "key": "description_tag",
            "value": meta_description,
            "type": "single_line_text_field",
        }

    if not page_data:
        return {"status": "no_changes", "page_id": page_id}

    page_data["id"] = page_id

    resp = httpx.put(
        url,
        headers=headers,
        json={"page": page_data},
        timeout=30,
    )
    resp.raise_for_status()
    return {
        "status": "updated",
        "page_id": page_id,
        "fields_updated": list(page_data.keys()),
    }


def update_article_seo(
    blog_id: int,
    article_id: int,
    title: str = None,
    body_html: str = None,
    summary_html: str = None,
    meta_description: str = None,
) -> dict:
    """
    Update a blog article's SEO fields.
    """
    headers = _shopify_headers()
    url = _shopify_url(f"blogs/{blog_id}/articles/{article_id}.json")

    article_data = {}
    if title is not None:
        article_data["title"] = title
    if body_html is not None:
        article_data["body_html"] = body_html
    if summary_html is not None:
        article_data["summary_html"] = summary_html
    if meta_description is not None:
        article_data["metafield"] = {
            "namespace": "global",
            "key": "description_tag",
            "value": meta_description,
            "type": "single_line_text_field",
        }

    if not article_data:
        return {"status": "no_changes", "article_id": article_id}

    article_data["id"] = article_id

    resp = httpx.put(
        url,
        headers=headers,
        json={"article": article_data},
        timeout=30,
    )
    resp.raise_for_status()
    return {
        "status": "updated",
        "article_id": article_id,
        "fields_updated": list(article_data.keys()),
    }


# ===================== Order Pipeline =====================


def pull_shopify_orders(
    db: Session,
    limit: int = 50,
    status: str = "any",
) -> dict:
    """
    Pull orders from Shopify and store in Postgres.

    Populates the shopify_orders table for business analytics.
    """
    orders = get_orders(limit=limit, status=status)
    rows_inserted = 0

    for order in orders:
        from datetime import datetime

        # Check if order already exists
        existing = (
            db.query(ShopifyOrder)
            .filter(ShopifyOrder.shopify_order_id == str(order["id"]))
            .first()
        )
        if existing:
            continue

        order_date = None
        if order.get("created_at"):
            try:
                order_date = datetime.fromisoformat(
                    order["created_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                order_date = datetime.utcnow()

        record = ShopifyOrder(
            shopify_order_id=str(order["id"]),
            order_number=str(order.get("order_number", "")),
            customer_email=order.get("email", ""),
            total_price=float(order.get("total_price", 0)),
            status=order.get("financial_status", ""),
            order_date=order_date,
            data={
                "name": order.get("name"),
                "currency": order.get("currency"),
                "fulfillment_status": order.get("fulfillment_status"),
                "line_items_count": len(order.get("line_items", [])),
            },
        )
        db.add(record)
        rows_inserted += 1

    db.commit()

    # Log the workflow
    log_entry = WorkflowLog(
        workflow_name="shopify_orders_pull",
        status="success",
        payload={
            "orders_fetched": len(orders),
            "rows_inserted": rows_inserted,
        },
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "orders_fetched": len(orders),
        "rows_inserted": rows_inserted,
    }


# ===================== Site Audit Helper =====================


def get_site_seo_data() -> dict:
    """
    Pull all SEO-relevant data from the Shopify store.

    Returns products, pages, and blog articles with their
    titles, meta descriptions, handles, and content.
    Used by the SEO audit to generate content recommendations.
    """
    products = get_products(limit=250)
    pages = get_pages(limit=50)

    blogs = get_blogs()
    articles = []
    for blog in blogs:
        arts = get_blog_articles(blog["id"], limit=50)
        for art in arts:
            art["blog_id"] = blog["id"]
            art["blog_title"] = blog.get("title", "")
        articles.extend(arts)

# ===================== Redirect & Page Management =====================


def create_redirect(from_path: str, to_path: str) -> dict:
    """
    Create a 301 URL redirect in Shopify.

    from_path: e.g. "/pages/old-estate-sale-address"
    to_path:   e.g. "/pages/estate-sale-palm-harbor-pinellas-county"
    """
    headers = _shopify_headers()
    url = _shopify_url("redirects.json")

    resp = httpx.post(
        url,
        headers=headers,
        json={"redirect": {"path": from_path, "target": to_path}},
        timeout=30,
    )
    resp.raise_for_status()
    redirect = resp.json().get("redirect", {})
    return {
        "status": "created",
        "redirect_id": redirect.get("id"),
        "from": from_path,
        "to": to_path,
    }


def delete_page(page_id: int) -> dict:
    """
    Delete a page from the Shopify store.

    WARNING: Only call after a 301 redirect is in place for the page URL.
    """
    headers = _shopify_headers()
    url = _shopify_url(f"pages/{page_id}.json")

    resp = httpx.delete(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return {"status": "deleted", "page_id": page_id}


def create_page(
    title: str,
    body_html: str,
    handle: str = None,
    meta_description: str = None,
    published: bool = True,
) -> dict:
    """
    Create a new page in the Shopify store.

    Used for portfolio pages, landing pages, etc.
    """
    headers = _shopify_headers()
    url = _shopify_url("pages.json")

    page_data = {
        "title": title,
        "body_html": body_html,
        "published": published,
    }
    if handle:
        page_data["handle"] = handle
    if meta_description:
        page_data["metafield"] = {
            "namespace": "global",
            "key": "description_tag",
            "value": meta_description,
            "type": "single_line_text_field",
        }

    resp = httpx.post(
        url,
        headers=headers,
        json={"page": page_data},
        timeout=30,
    )
    resp.raise_for_status()
    page = resp.json().get("page", {})
    return {
        "status": "created",
        "page_id": page.get("id"),
        "handle": page.get("handle"),
        "title": page.get("title"),
    }


def consolidate_thin_pages(redirect_map: list[dict], dry_run: bool = True) -> dict:
    """
    Consolidate thin pages by creating 301 redirects and deleting the old pages.

    redirect_map: list of dicts with keys:
      - page_id: int (Shopify page ID)
      - from_handle: str (old page handle, e.g. "old-estate-sale-address")
      - to_handle: str (target page handle, e.g. "estate-sale-palm-harbor-pinellas-county")

    dry_run: if True, returns the plan without executing.
    """
    results = []

    for item in redirect_map:
        page_id = item["page_id"]
        from_path = f"/pages/{item['from_handle']}"
        to_path = f"/pages/{item['to_handle']}"

        if dry_run:
            results.append({
                "action": "dry_run",
                "page_id": page_id,
                "redirect": f"{from_path} → {to_path}",
            })
            continue

        try:
            # Step 1: Delete the old page FIRST
            # (Shopify returns 422 if you try to redirect from an active page)
            delete_result = delete_page(page_id)

            # Step 2: Create the 301 redirect now that the path is free
            redirect_result = create_redirect(from_path, to_path)

            results.append({
                "action": "completed",
                "page_id": page_id,
                "redirect_id": redirect_result.get("redirect_id"),
                "redirect": f"{from_path} → {to_path}",
            })
        except Exception as e:
            results.append({
                "action": "error",
                "page_id": page_id,
                "redirect": f"{from_path} → {to_path}",
                "error": str(e),
            })

    return {
        "status": "dry_run" if dry_run else "executed",
        "total": len(results),
        "results": results,
    }


    return {
        "products": [
            {
                "id": p["id"],
                "title": p.get("title", ""),
                "handle": p.get("handle", ""),
                "body_html_length": len(p.get("body_html", "") or ""),
                "tags": p.get("tags", ""),
                "product_type": p.get("product_type", ""),
                "status": p.get("status", ""),
                "meta_title": p.get("metafields_global_title_tag", ""),
                "meta_description": p.get(
                    "metafields_global_description_tag", ""
                ),
            }
            for p in products
        ],
        "pages": [
            {
                "id": pg["id"],
                "title": pg.get("title", ""),
                "handle": pg.get("handle", ""),
                "body_html_length": len(pg.get("body_html", "") or ""),
            }
            for pg in pages
        ],
        "articles": [
            {
                "id": a["id"],
                "blog_id": a.get("blog_id"),
                "blog_title": a.get("blog_title", ""),
                "title": a.get("title", ""),
                "handle": a.get("handle", ""),
                "body_html_length": len(a.get("body_html", "") or ""),
                "summary_html_length": len(
                    a.get("summary_html", "") or ""
                ),
                "tags": a.get("tags", ""),
            }
            for a in articles
        ],
        "totals": {
            "products": len(products),
            "pages": len(pages),
            "articles": len(articles),
            "blogs": len(blogs),
        },
    }
