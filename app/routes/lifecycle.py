"""
Lifecycle Routes — Estate sale page management endpoints.

Three lifecycle stages:
  POST /setup    — Create a new estate sale page
  PUT  /live     — Update an active sale page
  POST /archive  — Archive a completed sale (vision AI + redirect + delete)
  GET  /summary  — View current lifecycle status
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.route_errors import raise_route_error
from app.safety import require_high_stakes_confirmation
from app.services.lifecycle_service import (
    archive_estate_sale,
    create_estate_sale_page,
    get_lifecycle_summary,
    update_sale_status,
)

router = APIRouter(prefix="/api/lifecycle", tags=["Estate Sale Lifecycle"])
logger = logging.getLogger(__name__)


@router.post("/setup")
def setup_new_sale(
    address: str,
    city: str,
    state: str = "FL",
    zip_code: str = "",
    sale_dates: str = "",
    description: str = "",
    human_confirmed: bool = False,
    judge_verdict: str | None = None,
):
    """
    Stage 1: Create a new estate sale page.

    Creates a Shopify page with SEO-optimized title, meta description,
    body content, and a placeholder for the XO Gallery embed.

    After creating, you'll need to:
    1. Create an XO Gallery album for this sale
    2. Upload photos to the gallery
    3. Link the gallery to the page via XO Gallery's "Publish" feature
    """
    require_high_stakes_confirmation(
        task_type="shopify_publish",
        human_confirmed=human_confirmed,
        judge_verdict=judge_verdict,
    )
    try:
        result = create_estate_sale_page(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            sale_dates=sale_dates,
            description=description,
        )
        return result
    except Exception as e:
        raise_route_error(logger, "Set up estate sale page", e)


@router.put("/live/{page_id}")
def update_live_sale(
    page_id: int,
    sale_dates: str = None,
    additional_info: str = None,
    human_confirmed: bool = False,
    judge_verdict: str | None = None,
):
    """
    Stage 2: Update a live estate sale page.

    Add sale dates, discount notices, or other updates.
    Example: additional_info="50% off all remaining items on Saturday!"
    """
    require_high_stakes_confirmation(
        task_type="shopify_update",
        human_confirmed=human_confirmed,
        judge_verdict=judge_verdict,
    )
    try:
        result = update_sale_status(
            page_id=page_id,
            sale_dates=sale_dates,
            additional_info=additional_info,
        )
        return result
    except Exception as e:
        raise_route_error(logger, "Update live estate sale page", e)


@router.post("/archive")
def archive_sale(
    page_id: int,
    page_handle: str,
    address: str = "",
    run_vision: bool = True,
    vision_limit: int = 50,
    human_confirmed: bool = False,
    judge_verdict: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Stage 3: Archive a completed estate sale.

    This performs three actions in sequence:
    1. Runs AI vision analysis on gallery photos (generates alt text + tags)
    2. Creates a 301 redirect from the sale page to the county service page
    3. Deletes the old sale page

    The county service page is auto-detected from the address.

    run_vision: Set to False to skip AI analysis (saves API cost)
    vision_limit: Max images to analyze (default 50, controls cost)
    """
    require_high_stakes_confirmation(
        task_type="shopify_delete",
        human_confirmed=human_confirmed,
        judge_verdict=judge_verdict,
    )
    try:
        result = archive_estate_sale(
            db=db,
            page_id=page_id,
            page_handle=page_handle,
            address=address,
            run_vision=run_vision,
            vision_limit=vision_limit,
        )
        return result
    except Exception as e:
        raise_route_error(logger, "Archive estate sale", e)


@router.get("/summary")
def lifecycle_summary(db: Session = Depends(get_db)):
    """
    Get current lifecycle status.

    Shows service pages, active sale pages, and archived count.
    """
    try:
        summary = get_lifecycle_summary(db)
        return {"status": "success", **summary}
    except Exception as e:
        raise_route_error(logger, "Lifecycle summary", e)
