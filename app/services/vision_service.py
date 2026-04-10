"""
Vision Service — AI Image Recognition for Estate Sale Photos

Uses Claude's vision API to analyze estate sale gallery images and generate:
  - SEO alt text
  - Item titles
  - Item tags (searchable keywords)
  - Descriptions

Pipeline:
  1. Pull image URLs from Shopify Files API (CDN-hosted images)
  2. Send each image to Claude Vision for analysis
  3. Store results in image_analysis table
  4. Export as CSV for XO Gallery bulk upload

Manual-approval mode: all operations require explicit trigger.
"""

import base64
import csv
import io
import os
import re
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.db.models import ImageAnalysis, WorkflowLog


# ===================== Shopify Files API =====================


def _shopify_graphql(query: str, variables: dict = None) -> dict:
    """Execute a GraphQL query against the Shopify Admin API."""
    from app.services.shopify_service import _get_access_token

    store = os.getenv("SHOPIFY_STORE")
    version = os.getenv("SHOPIFY_API_VERSION", "2024-10")
    token = _get_access_token()

    url = f"https://{store}.myshopify.com/admin/api/{version}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    timeout = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)
    resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def pull_image_urls(query_filter: str = "media_type:IMAGE", limit: int = 50) -> list:
    """
    Pull image file URLs from Shopify's Files API via GraphQL.

    Returns list of dicts: {url, filename, alt, created_at}
    """
    graphql_query = """
    query($first: Int!, $query: String) {
        files(first: $first, query: $query) {
            edges {
                node {
                    ... on MediaImage {
                        id
                        alt
                        image {
                            url
                            altText
                            width
                            height
                        }
                        createdAt
                    }
                }
            }
        }
    }
    """

    result = _shopify_graphql(
        graphql_query,
        variables={"first": limit, "query": query_filter},
    )

    images = []
    edges = result.get("data", {}).get("files", {}).get("edges", [])

    for edge in edges:
        node = edge.get("node", {})
        image_data = node.get("image", {})
        if not image_data or not image_data.get("url"):
            continue

        url = image_data["url"]
        # Extract filename from URL
        filename = url.split("/")[-1].split("?")[0] if "/" in url else ""

        images.append({
            "url": url,
            "filename": filename,
            "alt": image_data.get("altText", "") or node.get("alt", ""),
            "width": image_data.get("width"),
            "height": image_data.get("height"),
            "shopify_id": node.get("id", ""),
            "created_at": node.get("createdAt", ""),
        })

    return images


def pull_theme_assets(filter_prefix: str = "photo", limit: int = 250) -> list:
    """
    Pull image URLs from Shopify Theme Assets API.

    XO Gallery stores images as theme assets on Shopify's CDN.
    These appear under /t/{theme_id}/assets/ in the URL.

    filter_prefix: filter asset keys that start with this string
    """
    from app.services.shopify_service import _shopify_headers, _shopify_url

    headers = _shopify_headers()

    # First, get the active theme ID
    themes_url = _shopify_url("themes.json")
    resp = httpx.get(themes_url, headers=headers, timeout=30)
    resp.raise_for_status()
    themes = resp.json().get("themes", [])

    # Find the published/main theme
    active_theme = None
    for theme in themes:
        if theme.get("role") == "main":
            active_theme = theme
            break

    if not active_theme:
        return []

    theme_id = active_theme["id"]

    # Pull all assets from the theme
    assets_url = _shopify_url(f"themes/{theme_id}/assets.json")
    resp = httpx.get(assets_url, headers=headers, timeout=60)
    resp.raise_for_status()
    assets = resp.json().get("assets", [])

    # Filter for image assets (XO Gallery photos)
    store = os.getenv("SHOPIFY_STORE")
    images = []
    image_extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif")

    for asset in assets:
        key = asset.get("key", "")
        # Filter for images in assets that match our prefix or are photos
        if not key.lower().endswith(image_extensions):
            continue
        if filter_prefix and not key.lower().split("/")[-1].startswith(filter_prefix.lower()):
            continue

        # Build the CDN URL
        filename = key.split("/")[-1]
        # The public URL uses the theme's CDN path
        public_url = asset.get("public_url", "")
        if not public_url:
            public_url = f"https://cdn.shopify.com/s/files/1/0294/7966/5708/{key}"

        images.append({
            "url": public_url,
            "filename": filename,
            "key": key,
            "content_type": asset.get("content_type", ""),
            "created_at": asset.get("created_at", ""),
            "updated_at": asset.get("updated_at", ""),
        })

        if len(images) >= limit:
            break

    return images


def list_all_themes() -> list:
    """
    List all Shopify themes (including unpublished ones).

    XO Gallery stores images under an older theme (e.g., theme 7)
    while the active storefront uses a newer theme (e.g., theme 16).
    """
    from app.services.shopify_service import _shopify_headers, _shopify_url

    headers = _shopify_headers()
    themes_url = _shopify_url("themes.json")
    resp = httpx.get(themes_url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("themes", [])


def pull_xo_gallery_assets(
    theme_id: int = None,
    filter_prefix: str = "photo",
    limit: int = 10000,
) -> list:
    """
    Pull XO Gallery image URLs from a specific Shopify theme.

    XO Gallery stores estate sale photos as theme assets under an older
    theme version (typically /t/7/assets/). The active theme (/t/16/)
    does NOT contain these images.

    If theme_id is not provided, searches ALL themes for photo assets.

    Returns list of dicts: {url, filename, key, theme_id}
    """
    from app.services.shopify_service import _shopify_headers, _shopify_url

    headers = _shopify_headers()
    image_extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif")

    # If no theme_id specified, get all themes and search each
    if theme_id is None:
        themes = list_all_themes()
        theme_ids = [t["id"] for t in themes]
    else:
        theme_ids = [theme_id]

    all_images = []

    for tid in theme_ids:
        try:
            assets_url = _shopify_url(f"themes/{tid}/assets.json")
            resp = httpx.get(assets_url, headers=headers, timeout=120)
            resp.raise_for_status()
            assets = resp.json().get("assets", [])
        except Exception:
            continue

        for asset in assets:
            key = asset.get("key", "")
            if not key.lower().endswith(image_extensions):
                continue
            filename = key.split("/")[-1]
            if filter_prefix and not filename.lower().startswith(
                filter_prefix.lower()
            ):
                continue

            public_url = asset.get("public_url", "")
            if not public_url:
                public_url = (
                    f"https://cdn.shopify.com/s/files/1/0294/7966/5708/{key}"
                )

            all_images.append(
                {
                    "url": public_url,
                    "filename": filename,
                    "key": key,
                    "theme_id": tid,
                    "content_type": asset.get("content_type", ""),
                    "created_at": asset.get("created_at", ""),
                    "updated_at": asset.get("updated_at", ""),
                }
            )

            if len(all_images) >= limit:
                return all_images

    return all_images


def pull_gallery_images_from_page(page_handle: str) -> list:
    """
    Pull image URLs from a specific Shopify page's body HTML.

    Useful for finding XO Gallery embedded images.
    Parses img tags from the page body to extract CDN URLs.
    """
    from app.services.shopify_service import get_pages

    pages = get_pages(limit=250)
    target_page = None
    for p in pages:
        if p.get("handle") == page_handle:
            target_page = p
            break

    if not target_page:
        return []

    body_html = target_page.get("body_html", "") or ""

    # Extract image URLs from body HTML
    img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
    urls = img_pattern.findall(body_html)

    images = []
    for url in urls:
        filename = url.split("/")[-1].split("?")[0] if "/" in url else ""
        images.append({
            "url": url,
            "filename": filename,
            "source": f"page:{page_handle}",
        })

    return images


# ===================== Claude Vision API =====================


def _get_anthropic_client():
    """Get an Anthropic client for Claude Vision API."""
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing ANTHROPIC_API_KEY. Set it in .env to use AI image recognition."
        )
    return anthropic.Anthropic(api_key=api_key)


def analyze_image(image_url: str, gallery_name: str = "") -> dict:
    """
    Analyze a single image using Claude's vision API.

    Returns:
        {
            "alt_text": "Short SEO-friendly alt text",
            "title": "Item title for XO Gallery",
            "tags": ["tag1", "tag2", ...],
            "description": "Longer description for SEO",
            "confidence": 0.95,
        }
    """
    client = _get_anthropic_client()

    location_context = ""
    if gallery_name:
        # Parse location from gallery name (e.g. "2829 Tangelo Way, Palm Harbor")
        location_context = f" This photo is from an estate sale at {gallery_name}."

    prompt = f"""Analyze this estate sale photo and provide the following in JSON format:

1. "alt_text": A concise, SEO-friendly alt text (under 125 characters) describing the item(s) shown. Include the item type, notable brand/style if visible, and condition. Example: "Vintage mahogany writing desk with brass hardware, estate sale Palm Harbor FL"

2. "title": A short title for the item (under 60 characters). Example: "Vintage Mahogany Writing Desk"

3. "tags": An array of 3-8 searchable keyword tags for this item. Include: item category, brand (if visible), material, style/era, color. Example: ["furniture", "desk", "writing desk", "mahogany", "vintage", "brass hardware"]

4. "description": A 1-2 sentence description suitable for SEO. Mention the item, its condition, and that it was found at an Organizing Life Services estate sale in Tampa Bay, FL.

5. "confidence": Your confidence level (0.0-1.0) that you correctly identified the item(s).
{location_context}

Respond ONLY with valid JSON, no markdown formatting or code blocks."""

    # Fetch the image and convert to base64
    try:
        img_resp = httpx.get(image_url, timeout=30, follow_redirects=True)
        img_resp.raise_for_status()
        image_data = base64.b64encode(img_resp.content).decode("utf-8")

        # Detect media type
        content_type = img_resp.headers.get("content-type", "image/jpeg")
        if "png" in content_type:
            media_type = "image/png"
        elif "webp" in content_type:
            media_type = "image/webp"
        elif "gif" in content_type:
            media_type = "image/gif"
        else:
            media_type = "image/jpeg"
    except Exception as e:
        return {
            "error": f"Failed to fetch image: {str(e)}",
            "alt_text": "",
            "title": "",
            "tags": [],
            "description": "",
            "confidence": 0.0,
        }

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        import json

        response_text = message.content[0].text.strip()
        # Clean up potential markdown formatting
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[-1]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        result = json.loads(response_text)

        # Include token usage for cost tracking
        if hasattr(message, "usage"):
            result["_input_tokens"] = message.usage.input_tokens
            result["_output_tokens"] = message.usage.output_tokens

        return result

    except Exception as e:
        return {
            "error": f"Vision API error: {str(e)}",
            "alt_text": "",
            "title": "",
            "tags": [],
            "description": "",
            "confidence": 0.0,
        }


# ===================== Pipeline Orchestrator =====================


def analyze_gallery_images(
    db: Session,
    image_urls: list[dict],
    gallery_name: str = "",
    batch_size: int = 10,
) -> dict:
    """
    Analyze a batch of images and store results in the database.

    image_urls: list of dicts with at least 'url' and optionally 'filename'
    gallery_name: name/address of the estate sale for context
    batch_size: max images to process in one call (controls API costs)

    Returns summary of results.
    """
    results = []
    processed = 0
    errors = 0

    for img in image_urls[:batch_size]:
        url = img.get("url", "")
        filename = img.get("filename", "")

        if not url:
            continue

        # Check if already analyzed
        existing = (
            db.query(ImageAnalysis)
            .filter(ImageAnalysis.image_url == url)
            .first()
        )
        if existing:
            results.append({
                "filename": filename,
                "status": "skipped",
                "reason": "already analyzed",
            })
            continue

        # Analyze with Claude Vision
        analysis = analyze_image(url, gallery_name=gallery_name)

        # Store result
        record = ImageAnalysis(
            image_url=url,
            filename=filename,
            gallery_name=gallery_name,
            alt_text=analysis.get("alt_text", ""),
            title=analysis.get("title", ""),
            item_tags=analysis.get("tags", []),
            description=analysis.get("description", ""),
            confidence=analysis.get("confidence", 0.0),
            status="analyzed" if "error" not in analysis else "error",
            data=analysis,
        )
        db.add(record)
        processed += 1

        if "error" in analysis:
            errors += 1
            results.append({
                "filename": filename,
                "status": "error",
                "error": analysis["error"],
            })
        else:
            results.append({
                "filename": filename,
                "status": "analyzed",
                "alt_text": analysis.get("alt_text", ""),
                "title": analysis.get("title", ""),
                "tags": analysis.get("tags", []),
            })

    db.commit()

    # Log workflow
    log_entry = WorkflowLog(
        workflow_name="image_analysis",
        status="success" if errors == 0 else "partial",
        payload={
            "gallery_name": gallery_name,
            "images_submitted": len(image_urls[:batch_size]),
            "processed": processed,
            "errors": errors,
        },
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "gallery_name": gallery_name,
        "images_submitted": len(image_urls[:batch_size]),
        "processed": processed,
        "errors": errors,
        "results": results,
    }


# ===================== Budget-Aware Bulk Processing =====================

# Claude Sonnet 4 pricing (per million tokens)
_INPUT_PRICE_PER_M = 3.0   # $3 per 1M input tokens
_OUTPUT_PRICE_PER_M = 15.0  # $15 per 1M output tokens


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in dollars from token counts."""
    return (input_tokens * _INPUT_PRICE_PER_M / 1_000_000) + (
        output_tokens * _OUTPUT_PRICE_PER_M / 1_000_000
    )


def bulk_analyze_with_budget(
    db: Session,
    budget_dollars: float = 90.0,
    commit_every: int = 25,
    max_workers: int = 5,
) -> dict:
    """
    Analyze ALL XO Gallery images from the local JSON file, respecting a budget cap.

    Processes images with concurrent API calls (max_workers threads),
    commits to DB in batches, tracks cost, stops when budget is exhausted.

    Returns a summary with cost tracking.
    """
    import json as _json
    import logging
    from concurrent.futures import ThreadPoolExecutor, as_completed

    logger = logging.getLogger("vision_bulk")
    logging.basicConfig(level=logging.INFO)

    xo_data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "xo_gallery_images.json",
    )
    if not os.path.exists(xo_data_path):
        return {"status": "error", "message": "xo_gallery_images.json not found"}

    with open(xo_data_path) as f:
        data = _json.load(f)

    # Theme assets base URL (for photo-* lowercase files)
    theme_base_url = data.get("base_url", "")
    # Shopify Files base URL (for Photo_*, long-name files uploaded via XO Gallery)
    files_base_url = "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/"
    galleries = data.get("galleries", {})

    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    total_processed = 0
    total_skipped = 0
    total_errors = 0
    galleries_completed = 0
    budget_hit = False

    # Only skip successfully analyzed images — retry errors
    all_existing_urls = set(
        row[0] for row in db.query(ImageAnalysis.image_url).filter(
            ImageAnalysis.status == "analyzed"
        ).all()
    )
    logger.info(f"Found {len(all_existing_urls)} successfully analyzed images in DB")

    # Delete old error rows so they can be retried (avoids duplicate inserts)
    error_count = db.query(ImageAnalysis).filter(
        ImageAnalysis.status == "error"
    ).delete()
    db.commit()
    if error_count:
        logger.info(f"Deleted {error_count} previous error rows for retry")

    for gid, gallery in galleries.items():
        if budget_hit:
            break

        gallery_name = gallery.get("name", "")
        filenames = gallery.get("filenames", [])

        # Filter out already-analyzed images
        to_process = []
        for fname in filenames:
            # Use correct base URL: theme assets for photo-* files,
            # Shopify Files for everything else (Photo_*, long names, etc.)
            if fname.startswith("photo-"):
                url = theme_base_url + fname
            else:
                url = files_base_url + fname
            if url in all_existing_urls:
                total_skipped += 1
            else:
                to_process.append((fname, url))

        if not to_process:
            galleries_completed += 1
            logger.info(
                f"Gallery {gid}: {gallery_name} — all {len(filenames)} "
                f"already analyzed, skipping"
            )
            continue

        logger.info(
            f"Gallery {gid}: {gallery_name} ({len(to_process)} new / "
            f"{len(filenames)} total) [cost so far: ${total_cost:.2f}]"
        )

        # Process in parallel batches
        batch_count = 0
        batch_start = 0

        while batch_start < len(to_process) and not budget_hit:
            # Take next chunk of max_workers images
            chunk = to_process[batch_start:batch_start + max_workers]
            batch_start += max_workers

            # Submit all images in chunk to thread pool
            futures = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for fname, url in chunk:
                    future = executor.submit(
                        analyze_image, url, gallery_name=gallery_name
                    )
                    futures[future] = (fname, url)

                for future in as_completed(futures):
                    fname, url = futures[future]
                    try:
                        analysis = future.result()
                    except Exception as e:
                        analysis = {
                            "error": f"Thread error: {str(e)}",
                            "alt_text": "", "title": "",
                            "tags": [], "description": "",
                            "confidence": 0.0,
                        }

                    # Track tokens/cost
                    img_input = analysis.pop("_input_tokens", 0)
                    img_output = analysis.pop("_output_tokens", 0)
                    img_cost = _estimate_cost(img_input, img_output)
                    total_input_tokens += img_input
                    total_output_tokens += img_output
                    total_cost += img_cost

                    # Store result
                    record = ImageAnalysis(
                        image_url=url,
                        filename=fname,
                        gallery_name=gallery_name,
                        alt_text=analysis.get("alt_text", ""),
                        title=analysis.get("title", ""),
                        item_tags=analysis.get("tags", []),
                        description=analysis.get("description", ""),
                        confidence=analysis.get("confidence", 0.0),
                        status="analyzed" if "error" not in analysis else "error",
                        data=analysis,
                    )
                    db.add(record)
                    all_existing_urls.add(url)
                    total_processed += 1
                    batch_count += 1

                    if "error" in analysis:
                        total_errors += 1

            # Commit after each parallel chunk
            db.commit()
            logger.info(
                f"  Chunk done: {total_processed} processed, "
                f"${total_cost:.2f} spent, {total_errors} errors"
            )

            # Check budget after each chunk
            if total_cost >= budget_dollars:
                budget_hit = True
                logger.info(
                    f"BUDGET HIT: ${total_cost:.2f} >= ${budget_dollars:.2f}. "
                    f"Stopping after {total_processed} images."
                )

        # Commit at end of each gallery
        db.commit()
        if not budget_hit:
            galleries_completed += 1

    # Final log entry
    log_entry = WorkflowLog(
        workflow_name="bulk_image_analysis",
        status="budget_hit" if budget_hit else "success",
        payload={
            "total_processed": total_processed,
            "total_skipped": total_skipped,
            "total_errors": total_errors,
            "galleries_completed": galleries_completed,
            "total_cost_usd": round(total_cost, 4),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "budget_dollars": budget_dollars,
        },
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "budget_hit" if budget_hit else "success",
        "total_processed": total_processed,
        "total_skipped": total_skipped,
        "total_errors": total_errors,
        "galleries_completed": galleries_completed,
        "total_galleries": len(galleries),
        "total_cost_usd": round(total_cost, 4),
        "avg_cost_per_image": round(total_cost / max(total_processed, 1), 6),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "budget_dollars": budget_dollars,
        "budget_remaining": round(budget_dollars - total_cost, 2),
    }


# ===================== Export =====================


def export_analysis_csv(db: Session, gallery_name: str = None) -> str:
    """
    Export image analysis results as CSV string.

    CSV columns match XO Gallery bulk edit fields:
    filename, title, alt_text, tags, description

    Returns CSV as a string (caller can write to file or return as response).
    """
    query = db.query(ImageAnalysis).filter(
        ImageAnalysis.status == "analyzed"
    )
    if gallery_name:
        query = query.filter(ImageAnalysis.gallery_name == gallery_name)

    records = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "filename",
        "image_url",
        "title",
        "alt_text",
        "tags",
        "description",
        "confidence",
    ])

    for r in records:
        tags_str = ", ".join(r.item_tags) if r.item_tags else ""
        writer.writerow([
            r.filename,
            r.image_url,
            r.title,
            r.alt_text,
            tags_str,
            r.description,
            r.confidence,
        ])

    return output.getvalue()


# ===================== Bulk Alt Text Push to Shopify =====================


def _fetch_shopify_file_ids(cursor: str = None, limit: int = 250) -> dict:
    """
    Fetch a page of Shopify Files with their GIDs and filenames.

    Returns {files: [{id, filename, alt, url}, ...], has_next, cursor}
    """
    after_clause = f', after: "{cursor}"' if cursor else ""
    query = f"""
    query {{
        files(first: {limit}, query: "media_type:IMAGE"{after_clause}) {{
            edges {{
                node {{
                    ... on MediaImage {{
                        id
                        alt
                        image {{
                            url
                            altText
                        }}
                    }}
                }}
                cursor
            }}
            pageInfo {{
                hasNextPage
            }}
        }}
    }}
    """
    result = _shopify_graphql(query)
    edges = result.get("data", {}).get("files", {}).get("edges", [])
    has_next = result.get("data", {}).get("files", {}).get("pageInfo", {}).get("hasNextPage", False)

    files = []
    last_cursor = None
    for edge in edges:
        node = edge.get("node", {})
        image = node.get("image", {})
        if not node.get("id"):
            continue
        url = image.get("url", "")
        filename = url.split("/")[-1].split("?")[0] if url else ""
        files.append({
            "id": node["id"],
            "filename": filename,
            "current_alt": image.get("altText", "") or node.get("alt", ""),
            "url": url,
        })
        last_cursor = edge.get("cursor")

    return {"files": files, "has_next": has_next, "cursor": last_cursor}


def _update_file_alt_text(file_id: str, alt_text: str) -> dict:
    """
    Update the alt text on a single Shopify File via GraphQL.

    Uses the fileUpdate mutation.
    """
    query = """
    mutation fileUpdate($input: [FileUpdateInput!]!) {
        fileUpdate(files: $input) {
            files {
                ... on MediaImage {
                    id
                    alt
                    image {
                        altText
                    }
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    variables = {
        "input": [{
            "id": file_id,
            "alt": alt_text,
        }]
    }
    result = _shopify_graphql(query, variables)
    errors = result.get("data", {}).get("fileUpdate", {}).get("userErrors", [])
    if errors:
        return {"status": "error", "errors": errors}
    return {"status": "updated", "id": file_id}


def bulk_push_alt_text(db: Session, batch_size: int = 50, force: bool = False, progress_callback=None) -> dict:
    """
    Push AI-generated alt text to Shopify Files in bulk.

    1. Fetches all Shopify Files via GraphQL (paginated)
    2. Matches filenames to analyzed images in our database
    3. Updates alt text on each matched file

    force: If True, overwrite existing alt text (e.g. Webrex filename-based alt).

    Only updates files that:
    - Have a match in our image_analysis table with status='analyzed'
    - Currently have empty or missing alt text on Shopify

    Returns summary of updates.
    """
    import logging
    import time

    logger = logging.getLogger("vision_alt_push")

    # Load all analyzed images keyed by filename
    analyzed = db.query(ImageAnalysis).filter(
        ImageAnalysis.status == "analyzed",
        ImageAnalysis.alt_text.isnot(None),
        ImageAnalysis.alt_text != "",
    ).all()

    # Build lookup by filename (without _500x suffix and with it)
    alt_lookup = {}
    for record in analyzed:
        fname = record.filename or ""
        if fname:
            alt_lookup[fname] = record.alt_text
            # Also try without _500x suffix
            clean = fname.replace("_500x", "")
            alt_lookup[clean] = record.alt_text

    logger.info(f"Loaded {len(analyzed)} analyzed images, {len(alt_lookup)} lookup entries")

    total_shopify_files = 0
    total_matched = 0
    total_updated = 0
    total_skipped_has_alt = 0
    total_no_match = 0
    total_errors = 0
    cursor = None

    while True:
        # Retry pagination fetch up to 3 times (SSL timeouts are transient)
        page = None
        for attempt in range(3):
            try:
                page = _fetch_shopify_file_ids(cursor=cursor)
                break
            except Exception as e:
                logger.warning(f"Fetch page failed (attempt {attempt+1}/3): {e}")
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))  # Backoff: 5s, 10s
                else:
                    logger.error(f"Fetch page failed after 3 attempts, stopping.")
                    return {
                        "status": "partial",
                        "detail": f"Stopped after fetch error: {e}",
                        "total_shopify_files": total_shopify_files,
                        "total_matched": total_matched,
                        "total_updated": total_updated,
                        "total_skipped_has_alt": total_skipped_has_alt,
                        "total_no_match": total_no_match,
                        "total_errors": total_errors,
                    }

        files = page["files"]
        total_shopify_files += len(files)

        for f in files:
            fname = f["filename"]

            # Try to match by filename
            alt_text = alt_lookup.get(fname)
            if not alt_text:
                # Try without _500x
                clean = fname.replace("_500x", "")
                alt_text = alt_lookup.get(clean)

            if not alt_text:
                total_no_match += 1
                continue

            total_matched += 1

            # Skip if already has the exact alt text we'd push (idempotent)
            current = f["current_alt"] or ""
            if current == alt_text:
                total_skipped_has_alt += 1
                continue

            # Skip if already has GOOD alt text (not just a filename)
            # Webrex sets alt text to the raw filename — that's not real alt text
            is_filename_alt = current.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))
            if not force and current and len(current) > 5 and not is_filename_alt:
                total_skipped_has_alt += 1
                continue

            # Update alt text on Shopify (with retry for transient errors)
            last_error = ""
            update_success = False
            for attempt in range(3):
                try:
                    result = _update_file_alt_text(f["id"], alt_text)
                    if result["status"] == "updated":
                        total_updated += 1
                        update_success = True
                    else:
                        last_error = str(result)
                        logger.warning(f"Error updating {fname}: {result}")
                    break  # Don't retry on API-level errors (permissions etc)
                except Exception as e:
                    last_error = str(e)
                    if attempt < 2:
                        logger.warning(f"Retry {attempt+1} for {fname}: {e}")
                        time.sleep(3 * (attempt + 1))
                    else:
                        logger.error(f"Failed after 3 attempts for {fname}: {e}")

            if not update_success and last_error:
                total_errors += 1

            if last_error and progress_callback:
                progress_callback({
                    "files_scanned": total_shopify_files,
                    "matched": total_matched,
                    "updated": total_updated,
                    "skipped": total_skipped_has_alt,
                    "errors": total_errors,
                    "no_match": total_no_match,
                    "last_error": last_error[:500],
                    "last_error_file": fname,
                })

            # Rate limit: Shopify allows ~2 requests/sec for GraphQL mutations
            time.sleep(0.5)

        logger.info(
            f"Page done: {total_shopify_files} files scanned, "
            f"{total_matched} matched, {total_updated} updated"
        )

        if progress_callback:
            progress_callback({
                "files_scanned": total_shopify_files,
                "matched": total_matched,
                "updated": total_updated,
                "skipped": total_skipped_has_alt,
                "errors": total_errors,
                "no_match": total_no_match,
            })

        if not page["has_next"]:
            break
        cursor = page["cursor"]

    return {
        "status": "success",
        "total_shopify_files": total_shopify_files,
        "total_matched": total_matched,
        "total_updated": total_updated,
        "total_skipped_has_alt": total_skipped_has_alt,
        "total_no_match": total_no_match,
        "total_errors": total_errors,
    }


def fix_empty_alt_text(progress_callback=None) -> dict:
    """
    Find all Shopify files with empty alt text, analyze them with Claude Vision,
    and push AI-generated alt text directly.

    This handles the ~189 files that weren't in the original analysis DB.
    """
    import logging
    import time

    logger = logging.getLogger("vision_fix_empty")

    total_scanned = 0
    total_empty = 0
    total_analyzed = 0
    total_pushed = 0
    total_errors = 0
    cursor = None

    while True:
        # Fetch page with retry
        page = None
        for attempt in range(3):
            try:
                page = _fetch_shopify_file_ids(cursor=cursor)
                break
            except Exception as e:
                logger.warning(f"Fetch page failed (attempt {attempt+1}/3): {e}")
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                else:
                    return {
                        "status": "partial",
                        "detail": f"Stopped after fetch error: {e}",
                        "total_scanned": total_scanned,
                        "total_empty": total_empty,
                        "total_analyzed": total_analyzed,
                        "total_pushed": total_pushed,
                        "total_errors": total_errors,
                    }

        for f in page["files"]:
            total_scanned += 1
            current_alt = (f.get("current_alt") or "").strip()

            if current_alt:
                continue  # Already has alt text, skip

            total_empty += 1
            url = f.get("url", "")
            filename = f.get("filename", "")
            file_id = f.get("id", "")

            if not url:
                total_errors += 1
                logger.warning(f"No URL for empty-alt file: {filename}")
                continue

            # Analyze with Claude Vision
            try:
                result = analyze_image(url, gallery_name="Organizing Life Services")
                alt_text = result.get("alt_text", "")
                if not alt_text:
                    total_errors += 1
                    logger.warning(f"No alt text generated for {filename}: {result}")
                    continue
                total_analyzed += 1
            except Exception as e:
                total_errors += 1
                logger.error(f"Vision analysis failed for {filename}: {e}")
                continue

            # Push to Shopify with retry
            push_success = False
            for attempt in range(3):
                try:
                    push_result = _update_file_alt_text(file_id, alt_text)
                    if push_result["status"] == "updated":
                        total_pushed += 1
                        push_success = True
                    else:
                        logger.warning(f"Push error for {filename}: {push_result}")
                    break
                except Exception as e:
                    if attempt < 2:
                        logger.warning(f"Push retry {attempt+1} for {filename}: {e}")
                        time.sleep(3 * (attempt + 1))
                    else:
                        logger.error(f"Push failed after 3 attempts for {filename}: {e}")

            if not push_success:
                total_errors += 1

            # Rate limit
            time.sleep(1.0)  # Slower rate for Vision API + Shopify mutation combo

            if progress_callback:
                progress_callback({
                    "scanned": total_scanned,
                    "empty_found": total_empty,
                    "analyzed": total_analyzed,
                    "pushed": total_pushed,
                    "errors": total_errors,
                    "last_file": filename,
                    "last_alt": alt_text[:100] if alt_text else "",
                })

        if progress_callback:
            progress_callback({
                "scanned": total_scanned,
                "empty_found": total_empty,
                "analyzed": total_analyzed,
                "pushed": total_pushed,
                "errors": total_errors,
            })

        if not page["has_next"]:
            break
        cursor = page["cursor"]

    return {
        "status": "success",
        "total_scanned": total_scanned,
        "total_empty": total_empty,
        "total_analyzed": total_analyzed,
        "total_pushed": total_pushed,
        "total_errors": total_errors,
    }


def compare_alt_text(db: Session, sample_size: int = 10) -> dict:
    """
    Compare existing Shopify Files alt text (e.g. from Webrex) with our AI-generated alt text.

    Returns side-by-side comparison for matched files.
    """
    import logging

    logger = logging.getLogger("vision_alt_compare")

    # Load analyzed images keyed by filename
    analyzed = db.query(ImageAnalysis).filter(
        ImageAnalysis.status == "analyzed",
        ImageAnalysis.alt_text.isnot(None),
        ImageAnalysis.alt_text != "",
    ).all()

    alt_lookup = {}
    for record in analyzed:
        fname = record.filename or ""
        if fname:
            alt_lookup[fname] = record.alt_text
            clean = fname.replace("_500x", "")
            alt_lookup[clean] = record.alt_text

    comparisons = []
    cursor = None

    while len(comparisons) < sample_size:
        page = _fetch_shopify_file_ids(cursor=cursor)
        files = page["files"]

        for f in files:
            fname = f["filename"]
            our_alt = alt_lookup.get(fname)
            if not our_alt:
                clean = fname.replace("_500x", "")
                our_alt = alt_lookup.get(clean)

            if not our_alt:
                continue

            shopify_alt = f["current_alt"] or ""

            comparisons.append({
                "filename": fname,
                "shopify_current_alt": shopify_alt,
                "our_ai_alt": our_alt,
                "shopify_length": len(shopify_alt),
                "our_length": len(our_alt),
            })

            if len(comparisons) >= sample_size:
                break

        if not page["has_next"]:
            break
        cursor = page["cursor"]

    return {
        "status": "success",
        "sample_size": len(comparisons),
        "comparisons": comparisons,
    }


def get_analysis_summary(db: Session) -> dict:
    """Get a summary of all image analysis results."""
    total = db.query(ImageAnalysis).count()
    analyzed = db.query(ImageAnalysis).filter(
        ImageAnalysis.status == "analyzed"
    ).count()
    errors = db.query(ImageAnalysis).filter(
        ImageAnalysis.status == "error"
    ).count()
    pending = db.query(ImageAnalysis).filter(
        ImageAnalysis.status == "pending"
    ).count()

    # Get unique galleries
    galleries = (
        db.query(ImageAnalysis.gallery_name)
        .distinct()
        .all()
    )
    gallery_names = [g[0] for g in galleries if g[0]]

    # Get all unique tags
    all_tags = set()
    records = db.query(ImageAnalysis).filter(
        ImageAnalysis.status == "analyzed"
    ).all()
    for r in records:
        if r.item_tags:
            all_tags.update(r.item_tags)

    return {
        "total_images": total,
        "analyzed": analyzed,
        "errors": errors,
        "pending": pending,
        "galleries": gallery_names,
        "unique_tags": sorted(list(all_tags)),
        "tag_count": len(all_tags),
    }
