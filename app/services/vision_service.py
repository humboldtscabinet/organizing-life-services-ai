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

    resp = httpx.post(url, headers=headers, json=payload, timeout=30)
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
