"""
Vision Routes — AI image recognition endpoints for estate sale photos.

All endpoints are manual-trigger:
- Pull image URLs from Shopify
- Analyze images with Claude Vision
- Export results as CSV for XO Gallery bulk upload
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.vision_service import (
    analyze_gallery_images,
    export_analysis_csv,
    get_analysis_summary,
    pull_gallery_images_from_page,
    pull_image_urls,
)

router = APIRouter(prefix="/api/vision", tags=["Vision AI"])


@router.get("/images")
def list_shopify_images(limit: int = 50):
    """
    Pull image URLs from Shopify Files API.

    Returns image URLs, filenames, and existing alt text.
    """
    try:
        images = pull_image_urls(limit=limit)
        return {
            "status": "success",
            "count": len(images),
            "images": images,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/images/page/{page_handle}")
def list_page_images(page_handle: str):
    """
    Pull image URLs embedded in a specific Shopify page.

    Useful for finding XO Gallery images on a particular estate sale page.
    """
    try:
        images = pull_gallery_images_from_page(page_handle)
        return {
            "status": "success",
            "page_handle": page_handle,
            "count": len(images),
            "images": images,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/analyze")
def analyze_images(
    gallery_name: str = "",
    source: str = "files",
    page_handle: str = "",
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    Analyze estate sale images with Claude Vision AI.

    source options:
      - "files": Pull from Shopify Files API (default)
      - "page": Pull from a specific page's body HTML

    gallery_name: estate sale name for context (e.g. "2829 Tangelo Way, Palm Harbor")
    limit: max images to analyze (controls API cost, default 10)

    This is a WRITE operation that calls the Anthropic API.
    Each image costs ~$0.01-0.05 depending on size.
    """
    try:
        if source == "page" and page_handle:
            images = pull_gallery_images_from_page(page_handle)
        else:
            images = pull_image_urls(limit=limit)

        if not images:
            return {
                "status": "warning",
                "detail": "No images found to analyze.",
            }

        result = analyze_gallery_images(
            db=db,
            image_urls=images,
            gallery_name=gallery_name,
            batch_size=limit,
        )
        return result

    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/results")
def get_results(db: Session = Depends(get_db)):
    """Get a summary of all image analysis results."""
    try:
        summary = get_analysis_summary(db)
        return {"status": "success", **summary}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/export/csv")
def export_csv(
    gallery_name: str = None,
    db: Session = Depends(get_db),
):
    """
    Export image analysis results as CSV.

    Columns: filename, image_url, title, alt_text, tags, description, confidence

    The CSV can be used for:
    - XO Gallery bulk SEO field updates
    - Google Sheets import for review
    - Bulk alt text updates via Shopify
    """
    try:
        csv_content = export_analysis_csv(db, gallery_name=gallery_name)
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=image_analysis.csv"
            },
        )
    except Exception as e:
        return {"status": "error", "detail": str(e)}
