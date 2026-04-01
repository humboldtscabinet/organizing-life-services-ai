"""
Shopify Routes — Manual-trigger endpoints for Shopify operations.

All endpoints are manual-approval mode:
- Read: pull products, pages, orders from Shopify
- Write: update SEO fields only when explicitly triggered
- No automated changes — human reviews everything first
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.shopify_service import (
    get_blog_articles,
    get_blogs,
    get_pages,
    get_products,
    get_site_seo_data,
    pull_shopify_orders,
    update_article_seo,
    update_page_seo,
    update_product_seo,
)

router = APIRouter(prefix="/api/shopify", tags=["Shopify"])


# ===================== Read Endpoints =====================


@router.get("/products")
def list_products(limit: int = 50):
    """List products from the Shopify store."""
    try:
        products = get_products(limit=limit)
        return {
            "status": "success",
            "count": len(products),
            "products": [
                {
                    "id": p["id"],
                    "title": p.get("title"),
                    "handle": p.get("handle"),
                    "status": p.get("status"),
                    "product_type": p.get("product_type"),
                }
                for p in products
            ],
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/pages")
def list_pages(limit: int = 50):
    """List pages from the Shopify store."""
    try:
        pages = get_pages(limit=limit)
        return {
            "status": "success",
            "count": len(pages),
            "pages": [
                {
                    "id": p["id"],
                    "title": p.get("title"),
                    "handle": p.get("handle"),
                }
                for p in pages
            ],
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/blogs")
def list_blogs():
    """List all blogs and their articles."""
    try:
        blogs = get_blogs()
        result = []
        for blog in blogs:
            articles = get_blog_articles(blog["id"], limit=10)
            result.append({
                "id": blog["id"],
                "title": blog.get("title"),
                "articles_count": len(articles),
                "articles": [
                    {"id": a["id"], "title": a.get("title")}
                    for a in articles
                ],
            })
        return {"status": "success", "blogs": result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/seo-data")
def get_seo_overview():
    """
    Pull all SEO-relevant data from the Shopify store.

    Returns products, pages, and articles with their titles,
    handles, and content lengths for audit purposes.
    """
    try:
        data = get_site_seo_data()
        return {"status": "success", **data}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ===================== Order Pipeline =====================


@router.post("/orders/pull")
def trigger_orders_pull(
    limit: int = 50,
    status: str = "any",
    db: Session = Depends(get_db),
):
    """
    Pull orders from Shopify into Postgres.

    Skips orders that already exist in the database.
    """
    try:
        result = pull_shopify_orders(db=db, limit=limit, status=status)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ===================== SEO Update Endpoints =====================


@router.put("/products/{product_id}/seo")
def update_product_seo_fields(
    product_id: int,
    title: str = None,
    meta_description: str = None,
    handle: str = None,
):
    """
    Update a product's SEO fields (title, meta description, handle).

    Only updates fields that are provided.
    This is a WRITE operation — use only after human review.
    """
    try:
        result = update_product_seo(
            product_id=product_id,
            title=title,
            meta_description=meta_description,
            handle=handle,
        )
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.put("/pages/{page_id}/seo")
def update_page_seo_fields(
    page_id: int,
    title: str = None,
    body_html: str = None,
    meta_description: str = None,
):
    """
    Update a page's SEO fields (title, content, meta description).

    This is a WRITE operation — use only after human review.
    """
    try:
        result = update_page_seo(
            page_id=page_id,
            title=title,
            body_html=body_html,
            meta_description=meta_description,
        )
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.put("/blogs/{blog_id}/articles/{article_id}/seo")
def update_article_seo_fields(
    blog_id: int,
    article_id: int,
    title: str = None,
    body_html: str = None,
    summary_html: str = None,
    meta_description: str = None,
):
    """
    Update a blog article's SEO fields.

    This is a WRITE operation — use only after human review.
    """
    try:
        result = update_article_seo(
            blog_id=blog_id,
            article_id=article_id,
            title=title,
            body_html=body_html,
            summary_html=summary_html,
            meta_description=meta_description,
        )
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}
