"""
Content Routes — Blog content generation and publishing endpoints.

All endpoints are in manual-approval mode:
- Generate content tasks from GSC analysis
- View content calendar and status
- Generate post previews
- Publish approved content to Shopify

All routes require X-API-Key authentication.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DashboardTask
from app.services.content_engine import (
    SHOPIFY_BLOG_ID,
    _generate_blog_image,
    _shopify_headers,
    _shopify_url,
    analyze_content_gaps,
    generate_blog_post,
    publish_to_shopify,
)
from app.services.content_scheduler import (
    get_content_calendar,
    get_content_status,
    schedule_weekly_content,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content", tags=["Content"])


@router.post("/analyze-gaps")
def analyze_gaps(
    days_back: int = Query(90, ge=7, le=180, description="Days of GSC data to analyze"),
    db: Session = Depends(get_db),
):
    """
    Analyze Google Search Console data to identify content gaps.

    Content gaps are high-impression queries with low click-through rates
    that indicate ranking position is poor but search volume exists.

    Returns:
        {
            "status": "success",
            "gap_count": int,
            "opportunities": [
                {
                    "query": "estate sale clearwater",
                    "impressions": 150,
                    "clicks": 2,
                    "current_position": 22.5,
                    "estimated_value": 6.75,
                    ...
                },
                ...
            ]
        }
    """
    try:
        opportunities = analyze_content_gaps(db=db, days_back=days_back)

        return {
            "status": "success",
            "gap_count": len(opportunities),
            "opportunities": opportunities,
        }

    except Exception as e:
        logger.error(f"Error analyzing content gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/schedule-next")
def schedule_next(
    count: int = Query(
        1,
        ge=1,
        le=10,
        description="Number of content tasks to schedule this run (default 1, max 10)",
    ),
    db: Session = Depends(get_db),
):
    """
    Schedule the next N high-value content opportunities.

    Picks the top GSC gaps that haven't been scheduled yet, creates
    dashboard tasks for each, and returns the list of tasks created.

    The `count` parameter supports the aggressive-but-controlled ramp:
      - Ramp-up weeks 1-2: count=3
      - Ramp-up weeks 3-4: count=2
      - Steady state:      count=1

    Returns:
        {
            "status": "success" | "partial" | "no_content" | "all_scheduled" | "error",
            "tasks_created": int,
            "tasks_requested": int,
            "tasks": [
                {
                    "task_id": int,
                    "topic": "...",
                    "target_keyword": "...",
                    "impressions": int,
                    "priority": "HIGH" | "MEDIUM" | "LOW",
                    "post_type": "seo_blog" | "service_area",
                },
                ...
            ],
            "message": "..."
        }
    """
    try:
        result = schedule_weekly_content(db=db, count=count)
        return result

    except Exception as e:
        logger.error(f"Error scheduling weekly content: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/generate-and-publish")
def generate_and_publish(
    task_id: int = Query(..., description="DashboardTask ID to publish"),
    db: Session = Depends(get_db),
):
    """
    Generate blog post content and publish to Shopify.

    Takes an approved dashboard task, generates the blog post via Claude,
    and publishes it to the Shopify news blog. Only works if task status
    is "approved".

    Returns:
        {
            "status": "success" | "error",
            "article_id": str,
            "article_url": str,
            "task_id": int,
            "detail": str (on error)
        }
    """
    try:
        task = db.query(DashboardTask).filter(DashboardTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task #{task_id} not found")

        if task.status != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Task status is '{task.status}', must be 'approved'",
            )

        result = publish_to_shopify(db=db, task_id=task_id)

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("detail", "Unknown error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing task: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/calendar")
def calendar(
    weeks: int = Query(12, ge=4, le=26, description="Number of weeks to forecast"),
    db: Session = Depends(get_db),
):
    """
    Get content calendar for the next N weeks.

    Identifies top content opportunities and distributes them across
    a calendar. Shows which topics are scheduled, published, or gaps.

    Returns:
        {
            "status": "success",
            "weeks": 12,
            "calendar": [
                {
                    "week": 1,
                    "date": "2024-04-15",
                    "topic": "Estate Sales in Clearwater",
                    "target_keyword": "estate sale clearwater",
                    "priority": "HIGH",
                    "status": "gap" | "scheduled" | "published"
                },
                ...
            ]
        }
    """
    try:
        calendar = get_content_calendar(db=db, weeks=weeks)

        return {
            "status": "success",
            "weeks": weeks,
            "calendar": calendar,
        }

    except Exception as e:
        logger.error(f"Error getting content calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """
    Get content pipeline status overview.

    Returns metrics on published posts, pending tasks, and remaining gaps.

    Returns:
        {
            "status": "success" | "error",
            "total_published": int,
            "pending_tasks": int,
            "approved_tasks": int,
            "content_gaps_remaining": int,
            "next_scheduled_topic": str,
            "last_published": {
                "title": "...",
                "date": "2024-04-09T12:30:45",
                "url": "https://ols-online.myshopify.com/blogs/news/..."
            }
        }
    """
    try:
        result = get_content_status(db=db)
        return result

    except Exception as e:
        logger.error(f"Error getting content status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/generate-preview")
def generate_preview(
    topic: str = Query(..., description="Blog post topic"),
    target_keyword: str = Query(..., description="Primary SEO keyword"),
    post_type: str = Query(
        "seo_blog",
        description="Post type: seo_blog, service_area, or educational_guide",
    ),
    db: Session = Depends(get_db),
):
    """
    Generate a blog post preview without publishing to Shopify.

    Generates the full blog post content using Claude and returns it
    for review/approval before publishing. No database changes.

    Returns:
        {
            "status": "success" | "error",
            "title": "...",
            "meta_description": "...",
            "body_html": "<h2>...</h2>...",
            "summary_html": "<p>...</p>",
            "handle": "url-slug",
            "tags": ["estate sales", "clearwater"],
            "character_count": int,
            "word_count": int
        }
    """
    try:
        if post_type not in ["seo_blog", "service_area", "educational_guide"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid post_type: {post_type}",
            )

        post_data = generate_blog_post(
            db=db,
            topic=topic,
            target_keyword=target_keyword,
            post_type=post_type,
        )

        # Calculate word and character counts
        body_text = post_data["body_html"].replace("<h2>", " ").replace("</h2>", " ")
        body_text = body_text.replace("<h3>", " ").replace("</h3>", " ")
        body_text = body_text.replace("<p>", " ").replace("</p>", " ")
        body_text = body_text.replace("<a href=", "").replace("</a>", " ")
        body_text = body_text.replace(">", " ")

        words = len(body_text.split())
        chars = len(post_data["body_html"])

        return {
            "status": "success",
            "title": post_data["title"],
            "meta_description": post_data["meta_description"],
            "body_html": post_data["body_html"],
            "summary_html": post_data["summary_html"],
            "handle": post_data["handle"],
            "tags": post_data["tags"],
            "character_count": chars,
            "word_count": words,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/add-image")
def add_image_to_article(
    article_id: int = Query(..., description="Shopify article ID"),
    topic: str = Query(..., description="Blog topic for image prompt"),
    target_keyword: str = Query(..., description="SEO keyword for alt text"),
):
    """
    Generate and attach a featured image to an existing Shopify article.

    Use this to backfill images on articles published without thumbnails.
    """
    import httpx as _httpx

    try:
        image_data = _generate_blog_image(topic=topic, target_keyword=target_keyword)
        if not image_data:
            raise HTTPException(
                status_code=500,
                detail="Image generation failed — check OPENAI_API_KEY",
            )

        # Update the existing article with the image
        update_body = {
            "article": {
                "id": article_id,
                "image": {
                    "src": image_data["src"],
                    "alt": image_data["alt"],
                },
            }
        }

        response = _httpx.put(
            _shopify_url(f"blogs/{SHOPIFY_BLOG_ID}/articles/{article_id}.json"),
            headers=_shopify_headers(),
            json=update_body,
            timeout=60,
        )
        response.raise_for_status()

        return {
            "status": "success",
            "article_id": article_id,
            "image_alt": image_data["alt"],
            "message": "Featured image added successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding image to article: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/fix-article-content")
def fix_article_content(
    article_id: int = Query(..., description="Shopify article ID to inspect/fix"),
    find: Optional[str] = Query(None, description="Exact string to find in article body_html (required unless append_html is used)"),
    replace: Optional[str] = Query(None, description="Replacement string (required unless append_html is used)"),
    append_html: Optional[str] = Query(None, description="HTML to append to the end of body_html (alternative to find/replace mode)"),
    dry_run: bool = Query(
        True,
        description="If true, returns a preview of changes without writing to Shopify (default true for safety)",
    ),
    db: Session = Depends(get_db),
):
    """
    Find-and-replace on a published Shopify article body.

    Useful for retroactively correcting mistakes in published content
    (e.g., a wrong phone number, broken link, or outdated claim).
    Dry-run mode is the default — you must explicitly pass dry_run=false
    to commit the change to Shopify.

    Also updates the article title if the find string appears there.

    Returns:
        {
            "status": "success",
            "article_id": int,
            "dry_run": bool,
            "title": "...",
            "body_occurrences": int,
            "title_occurrences": int,
            "preview_snippets": ["...snippet around each match..."],
            "updated": bool,
        }
    """
    import httpx as _httpx

    # Validate mode: must be either find/replace or append_html
    if append_html is None and (find is None or replace is None):
        raise HTTPException(
            status_code=400,
            detail="Must provide either (find + replace) for find/replace mode OR append_html for append mode",
        )
    if append_html is not None and (find is not None or replace is not None):
        raise HTTPException(
            status_code=400,
            detail="Cannot mix append_html with find/replace — use one mode at a time",
        )

    try:
        # 1. Fetch the current article
        get_resp = _httpx.get(
            _shopify_url(f"blogs/{SHOPIFY_BLOG_ID}/articles/{article_id}.json"),
            headers=_shopify_headers(),
            timeout=30,
        )
        get_resp.raise_for_status()
        article = get_resp.json().get("article", {})

        current_title = article.get("title", "") or ""
        current_body = article.get("body_html", "") or ""

        # -----------------------------------------------------------
        # Mode 2: append_html — append the given HTML to body_html
        # -----------------------------------------------------------
        if append_html is not None:
            new_body = current_body + append_html
            preview_snippet = (
                "..." + current_body[-120:].replace("\n", " ") +
                " [APPEND>] " + append_html[:200].replace("\n", " ") + "..."
            )

            if dry_run:
                return {
                    "status": "dry_run",
                    "article_id": article_id,
                    "dry_run": True,
                    "mode": "append_html",
                    "title": current_title,
                    "current_body_length": len(current_body),
                    "append_length": len(append_html),
                    "new_body_length": len(new_body),
                    "preview_snippets": [preview_snippet],
                    "updated": False,
                    "message": (
                        f"DRY RUN: would append {len(append_html)} chars of HTML "
                        f"to end of article {article_id}. Re-run with dry_run=false to commit."
                    ),
                }

            # Commit the append
            update_body = {
                "article": {
                    "id": article_id,
                    "body_html": new_body,
                }
            }
            put_resp = _httpx.put(
                _shopify_url(f"blogs/{SHOPIFY_BLOG_ID}/articles/{article_id}.json"),
                headers=_shopify_headers(),
                json=update_body,
                timeout=60,
            )
            put_resp.raise_for_status()

            return {
                "status": "success",
                "article_id": article_id,
                "dry_run": False,
                "mode": "append_html",
                "title": current_title,
                "current_body_length": len(current_body),
                "append_length": len(append_html),
                "new_body_length": len(new_body),
                "preview_snippets": [preview_snippet],
                "updated": True,
                "message": f"Appended {len(append_html)} chars of HTML to article {article_id}",
            }

        # -----------------------------------------------------------
        # Mode 1: find/replace (original behavior)
        # -----------------------------------------------------------
        body_occurrences = current_body.count(find)
        title_occurrences = current_title.count(find)
        total = body_occurrences + title_occurrences

        # 2. Build preview snippets (±60 chars around each match)
        preview_snippets = []
        idx = 0
        search_from = 0
        while True:
            pos = current_body.find(find, search_from)
            if pos == -1 or len(preview_snippets) >= 5:
                break
            start = max(0, pos - 60)
            end = min(len(current_body), pos + len(find) + 60)
            snippet = current_body[start:end].replace("\n", " ")
            preview_snippets.append(f"...{snippet}...")
            search_from = pos + len(find)
            idx += 1

        if total == 0:
            return {
                "status": "no_matches",
                "article_id": article_id,
                "dry_run": dry_run,
                "title": current_title,
                "body_occurrences": 0,
                "title_occurrences": 0,
                "preview_snippets": [],
                "updated": False,
                "message": f"String not found in article {article_id}",
            }

        # 3. Dry-run short-circuit
        if dry_run:
            return {
                "status": "dry_run",
                "article_id": article_id,
                "dry_run": True,
                "title": current_title,
                "body_occurrences": body_occurrences,
                "title_occurrences": title_occurrences,
                "preview_snippets": preview_snippets,
                "updated": False,
                "message": (
                    f"DRY RUN: would replace {total} occurrence(s) of "
                    f"'{find}' with '{replace}'. Re-run with dry_run=false to commit."
                ),
            }

        # 4. Commit the change
        new_body = current_body.replace(find, replace)
        new_title = current_title.replace(find, replace)

        update_body = {
            "article": {
                "id": article_id,
                "body_html": new_body,
            }
        }
        if title_occurrences > 0:
            update_body["article"]["title"] = new_title

        put_resp = _httpx.put(
            _shopify_url(f"blogs/{SHOPIFY_BLOG_ID}/articles/{article_id}.json"),
            headers=_shopify_headers(),
            json=update_body,
            timeout=60,
        )
        put_resp.raise_for_status()

        return {
            "status": "success",
            "article_id": article_id,
            "dry_run": False,
            "title": new_title,
            "body_occurrences": body_occurrences,
            "title_occurrences": title_occurrences,
            "preview_snippets": preview_snippets,
            "updated": True,
            "message": f"Replaced {total} occurrence(s) of '{find}' with '{replace}'",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fixing article content: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
