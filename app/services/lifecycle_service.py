"""
Estate Sale Lifecycle Service — Page & Gallery Management

Manages the full lifecycle of estate sale pages on the Shopify store:

  1. SETUP   — Create a new sale page with SEO-optimized content
  2. LIVE    — Sale is active: page published, gallery linked, SEO monitored
  3. ARCHIVE — Sale concluded: run vision AI on photos, generate tags,
               then redirect page to county service page

This service orchestrates shopify_service + vision_service to automate
the transition between lifecycle stages.

Manual-approval mode: all stage transitions require explicit trigger.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import WorkflowLog

# ===================== County Page Mapping =====================

# Maps Florida counties/areas to their Shopify service page handles
COUNTY_PAGE_MAP = {
    # Pinellas County cities
    "palm harbor": "estate-sale-palm-harbor-pinellas-county",
    "clearwater": "estate-sale-palm-harbor-pinellas-county",
    "largo": "estate-sale-palm-harbor-pinellas-county",
    "dunedin": "estate-sale-palm-harbor-pinellas-county",
    "st petersburg": "estate-sale-palm-harbor-pinellas-county",
    "saint petersburg": "estate-sale-palm-harbor-pinellas-county",
    "st pete": "estate-sale-palm-harbor-pinellas-county",
    "pinellas park": "estate-sale-palm-harbor-pinellas-county",
    "tarpon springs": "estate-sale-palm-harbor-pinellas-county",
    "safety harbor": "estate-sale-palm-harbor-pinellas-county",
    "oldsmar": "estate-sale-palm-harbor-pinellas-county",
    "seminole": "estate-sale-palm-harbor-pinellas-county",
    "belleair": "estate-sale-palm-harbor-pinellas-county",
    "tierra verde": "estate-sale-palm-harbor-pinellas-county",
    "indian rocks": "estate-sale-palm-harbor-pinellas-county",
    "pinellas": "estate-sale-palm-harbor-pinellas-county",
    # Hillsborough County cities
    "tampa": "estate-sale-tampa-hillsborough-county",
    "brandon": "estate-sale-tampa-hillsborough-county",
    "plant city": "estate-sale-tampa-hillsborough-county",
    "riverview": "estate-sale-tampa-hillsborough-county",
    "hillsborough": "estate-sale-tampa-hillsborough-county",
    "valrico": "estate-sale-tampa-hillsborough-county",
    "lutz": "estate-sale-tampa-hillsborough-county",
    # Pasco County cities
    "new port richey": "estate-sale-pasco-county",
    "port richey": "estate-sale-pasco-county",
    "holiday": "estate-sale-pasco-county",
    "hudson": "estate-sale-pasco-county",
    "trinity": "estate-sale-pasco-county",
    "wesley chapel": "estate-sale-pasco-county",
    "zephyrhills": "estate-sale-pasco-county",
    "dade city": "estate-sale-pasco-county",
    "pasco": "estate-sale-pasco-county",
    # Hernando County cities
    "spring hill": "estate-sale-pasco-county",
    "brooksville": "estate-sale-pasco-county",
    "hernando": "estate-sale-pasco-county",
    "weeki wachee": "estate-sale-pasco-county",
    # Citrus County cities
    "inverness": "estate-sale-citrus-county",
    "crystal river": "estate-sale-citrus-county",
    "homosassa": "estate-sale-citrus-county",
    "lecanto": "estate-sale-citrus-county",
    "citrus": "estate-sale-citrus-county",
}

# Default fallback if no county match
DEFAULT_COUNTY_PAGE = "estate-sale-planning"


def _resolve_county_page(address: str) -> str:
    """
    Resolve an address/city to the appropriate county service page handle.

    Searches the address string for known city/county names.
    """
    address_lower = address.lower()
    for city, handle in COUNTY_PAGE_MAP.items():
        if city in address_lower:
            return handle
    return DEFAULT_COUNTY_PAGE


# ===================== Stage 1: SETUP =====================


def create_estate_sale_page(
    address: str,
    city: str,
    state: str = "FL",
    zip_code: str = "",
    sale_dates: str = "",
    description: str = "",
) -> dict:
    """
    Create a new estate sale page with SEO-optimized content.

    Generates:
    - SEO title: "{Address} - Estate Sale | Organizing Life Services"
    - Meta description with city, dates, and CTA
    - Body HTML with sale details and XO Gallery embed placeholder
    - Proper handle for clean URL
    """
    from app.services.shopify_service import create_page

    # Build SEO title
    short_address = address.split(",")[0].strip()
    title = f"{short_address}, {city} - Estate Sale"

    # Build handle (URL slug)
    handle_parts = short_address.lower().replace(",", "").split()
    handle = "-".join(handle_parts) + "-estate-sale"

    # Build meta description
    date_text = f" on {sale_dates}" if sale_dates else ""
    meta_description = (
        f"Estate sale{date_text} at {short_address}, {city}, {state} {zip_code}. "
        f"Professional estate liquidation by Organizing Life Services. "
        f"Furniture, antiques, collectibles, and more. (727) 542-6028."
    )
    # Trim to 160 chars
    if len(meta_description) > 160:
        meta_description = meta_description[:157] + "..."

    # Build body HTML
    date_section = ""
    if sale_dates:
        date_section = f"""
        <div class="sale-dates">
            <h3>Sale Dates</h3>
            <p>{sale_dates}</p>
        </div>
        """

    desc_section = ""
    if description:
        desc_section = f"""
        <div class="sale-description">
            <p>{description}</p>
        </div>
        """

    body_html = f"""
    <div class="estate-sale-page">
        <h2>Estate Sale at {address}</h2>
        <p><strong>{city}, {state} {zip_code}</strong></p>

        {date_section}
        {desc_section}

        <div class="sale-details">
            <h3>About This Sale</h3>
            <p>Organizing Life Services is conducting a professional estate sale
            at this location. Browse our photo gallery below to preview available
            items including furniture, antiques, collectibles, jewelry, appliances,
            and household goods.</p>
        </div>

        <div class="gallery-placeholder">
            <!-- XO Gallery embed will be added here -->
            <p><em>Photo gallery loading... If you don't see images, please refresh the page.</em></p>
        </div>

        <div class="cta-section">
            <h3>Need an Estate Sale Company?</h3>
            <p>Are you a homeowner, attorney, or executor looking for professional
            estate liquidation services in the Tampa Bay area? Organizing Life
            Services has been trusted since 2010.</p>
            <p><strong>Call us today: <a href="tel:7275426028">(727) 542-6028</a></strong></p>
            <p><a href="/pages/contact-us">Request a Free Consultation</a></p>
        </div>
    </div>
    """

    result = create_page(
        title=title,
        body_html=body_html,
        handle=handle,
        meta_description=meta_description,
        published=True,
    )

    result["lifecycle_stage"] = "setup"
    result["county_page"] = _resolve_county_page(f"{address} {city}")
    return result


# ===================== Stage 2: LIVE =====================


def update_sale_status(
    page_id: int,
    sale_dates: str = None,
    additional_info: str = None,
) -> dict:
    """
    Update a live estate sale page with new information.

    Can update sale dates, add notices (e.g., "50% off Saturday"),
    or add additional details.
    """
    from app.services.shopify_service import get_pages, update_page_seo

    # Find the current page
    pages = get_pages(limit=250)
    current_page = None
    for p in pages:
        if p["id"] == page_id:
            current_page = p
            break

    if not current_page:
        return {"status": "error", "detail": f"Page {page_id} not found"}

    updates = {}
    if sale_dates:
        # Update meta description with new dates
        title = current_page.get("title", "")
        updates["meta_description"] = (
            f"Estate sale on {sale_dates} - {title}. "
            f"Professional estate liquidation by Organizing Life Services. "
            f"(727) 542-6028."
        )[:160]

    if additional_info:
        # Append notice to body HTML
        current_body = current_page.get("body_html", "") or ""
        notice_html = f"""
        <div class="sale-notice" style="background: #fff3cd; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <strong>Update:</strong> {additional_info}
        </div>
        """
        updates["body_html"] = notice_html + current_body

    if not updates:
        return {"status": "no_changes", "page_id": page_id}

    result = update_page_seo(page_id=page_id, **updates)
    result["lifecycle_stage"] = "live"
    return result


# ===================== Stage 3: ARCHIVE =====================


def archive_estate_sale(
    db: Session,
    page_id: int,
    page_handle: str,
    address: str = "",
    run_vision: bool = True,
    vision_limit: int = 50,
) -> dict:
    """
    Archive a completed estate sale:

    1. Run AI vision analysis on the gallery photos (if enabled)
    2. Create a 301 redirect from the sale page to the county service page
    3. Delete the old sale page

    This is the key lifecycle transition that turns completed sales
    into SEO value for the service pages.
    """
    from app.services.shopify_service import create_redirect, delete_page
    from app.services.vision_service import (
        analyze_gallery_images,
        pull_image_urls,
    )

    results = {
        "page_id": page_id,
        "page_handle": page_handle,
        "lifecycle_stage": "archived",
        "steps": [],
    }

    # Step 1: Run vision analysis on photos (if enabled)
    if run_vision:
        try:
            images = pull_image_urls(limit=vision_limit)
            # Filter images that might belong to this sale (by filename pattern)
            # For now, analyze all available — in future, filter by gallery
            gallery_name = address or page_handle.replace("-", " ").title()

            vision_result = analyze_gallery_images(
                db=db,
                image_urls=images,
                gallery_name=gallery_name,
                batch_size=vision_limit,
            )
            results["steps"].append({
                "step": "vision_analysis",
                "status": "success",
                "images_processed": vision_result.get("processed", 0),
            })
        except Exception as e:
            results["steps"].append({
                "step": "vision_analysis",
                "status": "error",
                "error": str(e),
            })

    # Step 2: Determine the redirect target
    county_page = _resolve_county_page(address or page_handle)
    from_path = f"/pages/{page_handle}"
    to_path = f"/pages/{county_page}"

    # Step 3: Create 301 redirect
    try:
        redirect_result = create_redirect(from_path, to_path)
        results["steps"].append({
            "step": "redirect",
            "status": "success",
            "from": from_path,
            "to": to_path,
            "redirect_id": redirect_result.get("redirect_id"),
        })
    except Exception as e:
        results["steps"].append({
            "step": "redirect",
            "status": "error",
            "error": str(e),
        })
        # Don't delete the page if redirect failed
        results["status"] = "partial"
        return results

    # Step 4: Delete the old page
    try:
        delete_page(page_id)
        results["steps"].append({
            "step": "delete_page",
            "status": "success",
        })
    except Exception as e:
        results["steps"].append({
            "step": "delete_page",
            "status": "error",
            "error": str(e),
        })

    # Log the lifecycle transition
    log_entry = WorkflowLog(
        workflow_name="estate_sale_lifecycle",
        status="archived",
        payload={
            "page_id": page_id,
            "page_handle": page_handle,
            "redirect_to": county_page,
            "vision_enabled": run_vision,
            "archived_at": datetime.utcnow().isoformat(),
        },
    )
    db.add(log_entry)
    db.commit()

    results["status"] = "success"
    return results


# ===================== Summary / Status =====================


def get_lifecycle_summary(db: Session) -> dict:
    """
    Get a summary of all estate sale lifecycle events.
    """
    from app.services.shopify_service import get_pages

    # Get current pages
    pages = get_pages(limit=250)

    # Categorize pages
    service_pages = []
    sale_pages = []
    other_pages = []

    # Known service page IDs
    service_page_ids = {
        96294600858,   # Estate Sale Planning
        80166289562,   # About Us
        99735601306,   # Estate Cleanout Services
        99735568538,   # Downsizing & Moving Sales
        99768631450,   # Estate Sale Palm Harbor
        99768598682,   # Estate Sale Tampa
        99768664218,   # Estate Sale Pasco & Hernando
        99768729754,   # Estate Sale Citrus County
        96708198554,   # Estate Jewelry Sales
        80166781082,   # Contact Us
    }

    for p in pages:
        page_info = {
            "id": p["id"],
            "title": p.get("title", ""),
            "handle": p.get("handle", ""),
        }
        if p["id"] in service_page_ids:
            service_pages.append(page_info)
        elif "estate sale" in p.get("title", "").lower() or "sale" in p.get("handle", "").lower():
            sale_pages.append(page_info)
        else:
            other_pages.append(page_info)

    # Get archived count from workflow logs
    archived_count = (
        db.query(WorkflowLog)
        .filter(
            WorkflowLog.workflow_name == "estate_sale_lifecycle",
            WorkflowLog.status == "archived",
        )
        .count()
    )

    return {
        "service_pages": len(service_pages),
        "active_sale_pages": len(sale_pages),
        "other_pages": len(other_pages),
        "total_pages": len(pages),
        "archived_sales": archived_count,
        "active_sales": [
            {"id": s["id"], "title": s["title"], "handle": s["handle"]}
            for s in sale_pages
        ],
    }
