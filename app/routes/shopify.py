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
    consolidate_thin_pages,
    create_page,
    create_redirect,
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


# ===================== Page Management Endpoints =====================


@router.post("/pages/create")
def create_new_page(
    title: str,
    body_html: str,
    handle: str = None,
    meta_description: str = None,
    published: bool = True,
):
    """
    Create a new page in the Shopify store.

    Used for creating portfolio pages, landing pages, etc.
    This is a WRITE operation — use only after human review.
    """
    try:
        result = create_page(
            title=title,
            body_html=body_html,
            handle=handle,
            meta_description=meta_description,
            published=published,
        )
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/redirects/create")
def create_url_redirect(from_path: str, to_path: str):
    """
    Create a 301 URL redirect.

    from_path: e.g. "/pages/old-estate-sale-address"
    to_path: e.g. "/pages/estate-sale-palm-harbor-pinellas-county"
    """
    try:
        result = create_redirect(from_path=from_path, to_path=to_path)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/cleanup/thin-pages")
def cleanup_thin_pages(dry_run: bool = True):
    """
    Consolidate thin estate sale pages by redirecting them to area portfolio pages.

    dry_run=True (default): shows the plan without executing.
    dry_run=False: creates 301 redirects and deletes old pages.

    This is a DESTRUCTIVE operation — always run dry_run=True first.
    """
    # Complete redirect mapping: thin page → target area page
    redirect_map = [
        # ─── Pinellas County (Palm Harbor, Clearwater, Largo, Dunedin, St Pete, etc.) ───
        {"page_id": 117608349850, "from_handle": "1071-donegan-road-lot-123-largo-estate-sale", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 109048266906, "from_handle": "1661-grove-street-clearwater-fl-33755", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 110219952282, "from_handle": "1956-sandra-drive-clearwater-florida", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 97837121690, "from_handle": "2274-13th-ave-sw-largo-florida-33770", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 122438844570, "from_handle": "2829-tangelo-way-palm-harbor-estate-sale", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 112757342362, "from_handle": "2836-highlands-blvd-a-palm-harbor-florida", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 106818371738, "from_handle": "3006-bolt-drive-palm-harbor-fl", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 98212216986, "from_handle": "3131-6th-ave-n-saint-petersburg-florida-grand-estate-sale-in-historic-kenwood-st-petersburg", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 103417675930, "from_handle": "4399-brooker-creek-drive-estate-sale", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 97930018970, "from_handle": "677-monte-cristo-blvd-tierra-verde-33715", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 105978888346, "from_handle": "8445-calais-pinellas-park-florida-33781", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 97086472346, "from_handle": "bel-air-sale-3165-renatta-drive-bellair-bluffs-33710", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 100800037018, "from_handle": "clearwater-haines-sale", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 98641543322, "from_handle": "dunedin-eisenhower-drive-estate-sale", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 105704456346, "from_handle": "dunedin-estate-sale-on-oak-hill-drive", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 97745567898, "from_handle": "estate-sale-1183-lindenwood-drive-tarpon-springs-34688", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 98728935578, "from_handle": "estate-sale-3254-masters-drive-clearwater-fl-33761", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 119268573338, "from_handle": "estate-sale-3494-primrose-way-palm-harbor-fl-34683", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 97241432218, "from_handle": "1018-egret-court-dunedin-florida-34698", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 96485179546, "from_handle": "clean-out-sale-saint-petersburg-florida-33710-pinellas-county", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 96484851866, "from_handle": "estate-sale-tampa-bay-area-pinellas-county-dunedin-florida-34698", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 96484655258, "from_handle": "estate-sale-tampa-bay-pinellas-county-largo-florida-33770", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 96484917402, "from_handle": "estate-sale-clearwater-florida-33759-pinellas-county", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 96484950170, "from_handle": "estate-sale-east-lake-woodlands-community-oldsmar-florida-pinellas-county", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        {"page_id": 96485146778, "from_handle": "estate-sale-palm-harbor-florida-highland-lakes-community-34685", "to_handle": "estate-sale-palm-harbor-pinellas-county"},
        # ─── Hillsborough County (Tampa) ───
        {"page_id": 96484819098, "from_handle": "estate-sale-hillsborough-county-tampa-florida-33614", "to_handle": "estate-sale-tampa-hillsborough-county"},
        # ─── Pasco County (New Port Richey, Holiday, Hudson) ───
        {"page_id": 102268666010, "from_handle": "4819-prince-george-circle-new-port-richey-estate-sale", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 97984217242, "from_handle": "6916-alken-court-new-port-richey", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 98448965786, "from_handle": "18356-autumn-lake-blvd", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 98838216858, "from_handle": "estate-sale-in-new-port-richey-florida-4809-portland-manor-drive", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 99034792090, "from_handle": "estate-sale-in-new-port-richey-florida-4809-portland-manor-drive-phase-2", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 99629662362, "from_handle": "estate-sale-at-1840-palmer-court-palm-harbor-florida-34685", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 96484786330, "from_handle": "estate-sale-holiday-florida-34691-pasco-county", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 96484982938, "from_handle": "estate-sale-holiday-florida-34691-pasco-county-1", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 96485015706, "from_handle": "estate-sale-holiday-florida-34691-pasco-county-may-20th-21st", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 96485212314, "from_handle": "estate-sale-new-port-richey-florida-34655-pasco-county", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 96485081242, "from_handle": "estate-sale-new-port-richey-florida-pasco-county", "to_handle": "estate-sale-pasco-county"},
        {"page_id": 96484884634, "from_handle": "estate-sale-pasco-county-new-port-richey-florida-34653-summer-lakes-community", "to_handle": "estate-sale-pasco-county"},
        # ─── Citrus County (Brooksville) ───
        {"page_id": 97526186138, "from_handle": "estate-sale-brooksville-fl", "to_handle": "estate-sale-citrus-county"},
        {"page_id": 104616755354, "from_handle": "brooksville-estate-sale-on-peruvian-lily-court", "to_handle": "estate-sale-citrus-county"},
    ]

    try:
        result = consolidate_thin_pages(
            redirect_map=redirect_map, dry_run=dry_run
        )
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}
