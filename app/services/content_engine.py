"""
Content Engine — Blog content generation and publishing service for OLS.

Capabilities:
  - Analyze content gaps from GSC data (high-impression, low-click keywords)
  - Generate blog posts using Claude API with SEO optimization
  - Create dashboard tasks for approved content
  - Publish to Shopify (admin API)

All content is Tampa Bay focused, with geographic references to Pinellas, Pasco,
Hillsborough, Hernando, Citrus, and Manatee counties.

Manual-approval mode: generates tasks, waits for human approval before publishing.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import anthropic
import httpx
import openai
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import DashboardTask, GSCData

logger = logging.getLogger(__name__)

# Anthropic client (uses ANTHROPIC_API_KEY env var)
anthropic_client = anthropic.Anthropic()

# Geographic focus for OLS
FLORIDA_COUNTIES = [
    "Pinellas",
    "Pasco",
    "Hillsborough",
    "Hernando",
    "Citrus",
    "Manatee",
]

FLORIDA_CITIES = [
    "Tampa",
    "St. Petersburg",
    "Clearwater",
    "Largo",
    "Sarasota",
    "Bradenton",
    "Dunedin",
    "Palm Harbor",
    "Safety Harbor",
    "Tarpon Springs",
    "Holiday",
    "Hudson",
    "New Port Richey",
    "Brooksville",
]

# Shopify configuration
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "ols-online")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")
SHOPIFY_BLOG_ID = "52179501100"  # "news" blog

_shopify_token_cache = {"token": None, "expires_at": None}

# Token TTL: refresh every 23 hours (Shopify tokens last 24h)
_TOKEN_TTL_SECONDS = 23 * 60 * 60


def _get_shopify_token() -> str:
    """
    Get a Shopify access token using Client Credentials grant.

    Caches the token with a 23-hour TTL to handle expiration.
    """
    now = datetime.utcnow()
    if (
        _shopify_token_cache["token"]
        and _shopify_token_cache["expires_at"]
        and now < _shopify_token_cache["expires_at"]
    ):
        return _shopify_token_cache["token"]

    if not all([SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET]):
        raise ValueError(
            "Missing Shopify credentials. Set SHOPIFY_CLIENT_ID "
            "and SHOPIFY_CLIENT_SECRET in .env."
        )

    resp = httpx.post(
        f"https://{SHOPIFY_STORE}.myshopify.com/admin/oauth/access_token",
        json={
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    _shopify_token_cache["token"] = token
    _shopify_token_cache["expires_at"] = now + timedelta(seconds=_TOKEN_TTL_SECONDS)
    return token


def _shopify_headers() -> dict:
    """Build request headers for Shopify Admin API calls."""
    token = _get_shopify_token()
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }


def _shopify_url(endpoint: str) -> str:
    """Build a full Shopify Admin API URL."""
    return (
        f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/{endpoint}"
    )


def _generate_blog_image(topic: str, target_keyword: str) -> Optional[Dict]:
    """
    Generate a unique blog thumbnail image using DALL-E 3.

    Creates a professional, photorealistic image tailored to the blog topic.
    Returns a dict with the image URL and SEO alt text, or None on failure.

    Shopify accepts image URLs directly — it downloads and hosts the image.

    Returns:
        {
            "src": "https://oaidalleapiprodscus.blob...",  # temporary URL
            "alt": "SEO-optimized alt text for the image"
        }
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "YOUR_OPENAI_API_KEY_HERE":
        logger.warning("OPENAI_API_KEY not set — skipping image generation")
        return None

    try:
        client = openai.OpenAI(api_key=api_key)

        # Build a prompt for a professional, photorealistic estate sale image
        image_prompt = (
            f"Professional real estate photography style image for a blog post about "
            f"'{topic}' in the Tampa Bay, Florida area. "
            f"The image should feel warm, inviting, and professional. "
            f"Show a well-organized, bright interior space appropriate for "
            f"estate sale or home organization services. "
            f"Natural lighting, clean composition, no text or watermarks. "
            f"Photorealistic, high quality, editorial style."
        )

        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1792x1024",  # landscape ratio, ideal for blog headers
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url

        # Generate SEO-optimized alt text using the target keyword
        alt_text = (
            f"{target_keyword.title()} - Professional estate sale and "
            f"home organization services in Tampa Bay, Florida"
        )

        logger.info(f"Generated blog image for '{topic}'")
        return {"src": image_url, "alt": alt_text}

    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return None


def _get_existing_blog_urls() -> List[Dict]:
    """
    Fetch existing blog post titles and URLs from Shopify.

    Returns a list of dicts: [{"title": "...", "url": "/blogs/news/handle"}]
    Used to provide real internal link targets to the blog generation prompt.
    """
    try:
        response = httpx.get(
            _shopify_url(f"blogs/{SHOPIFY_BLOG_ID}/articles.json?limit=50&fields=title,handle"),
            headers=_shopify_headers(),
            timeout=15,
        )
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return [
            {"title": a["title"], "url": f"/blogs/news/{a['handle']}"}
            for a in articles
            if a.get("handle")
        ]
    except Exception as e:
        logger.warning(f"Could not fetch existing blog URLs: {e}")
        return []


def analyze_content_gaps(db: Session, days_back: int = 90) -> List[Dict]:
    """
    Identify content gaps from GSC data of the last N days.

    Content gaps are queries where the site gets impressions but few/no clicks,
    indicating an opportunity for new or improved content.

    Three categories of opportunities:
    1. Zero-click high-impression queries (biggest gaps)
    2. Low-CTR queries at positions 5-20 (easy wins with better content)
    3. Location queries without dedicated pages

    Returns sorted list of top 30 opportunities by estimated value.
    """
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    # Group by query, aggregate metrics over the period
    query_stats = (
        db.query(
            GSCData.query,
            func.sum(GSCData.clicks).label("total_clicks"),
            func.sum(GSCData.impressions).label("total_impressions"),
            func.avg(GSCData.position).label("avg_position"),
            func.avg(GSCData.ctr).label("avg_ctr"),
        )
        .filter(GSCData.date >= cutoff)
        .group_by(GSCData.query)
        .having(func.sum(GSCData.impressions) >= 20)
        .all()
    )

    logger.info(f"Content gap analysis: {len(query_stats)} queries with 20+ impressions in {days_back} days")

    # Get existing content tasks to avoid duplicates
    existing_tasks = (
        db.query(DashboardTask.title)
        .filter(
            DashboardTask.task_type == "content",
            DashboardTask.status.in_(["pending", "approved", "completed"]),
        )
        .all()
    )
    existing_titles = {t.title.lower() for t in existing_tasks}

    opportunities = []

    for query_text, clicks, impressions, position, ctr in query_stats:
        if not query_text or not impressions:
            continue

        clicks = int(clicks or 0)
        impressions = int(impressions)
        position = float(position or 0)
        ctr_val = float(ctr or 0)

        # Skip branded queries
        if "organizing life" in query_text.lower():
            continue

        # Skip out-of-territory queries (Virginia, other states, etc.)
        if _is_out_of_territory(query_text):
            continue

        # Skip off-topic queries that won't drive estate sale leads
        if _is_off_topic(query_text):
            continue

        # Skip if we already have a content task for this
        if any(query_text.lower() in title for title in existing_titles):
            continue

        # Category 1: Zero/low click, any position with decent impressions
        # These are queries where Google shows us but nobody clicks
        if clicks <= 2 and impressions >= 30:
            # Estimate: if we create dedicated content and reach position 3,
            # we could get ~8% CTR
            estimated_new_ctr = 0.08 if position > 10 else 0.05
            estimated_value = impressions * estimated_new_ctr

            post_type = "service_area" if _is_location_query(query_text) else "seo_blog"

            opportunities.append({
                "query": query_text,
                "impressions": impressions,
                "clicks": clicks,
                "current_position": round(position, 1),
                "current_ctr": round(ctr_val, 4),
                "estimated_monthly_clicks": round(estimated_value / 3, 0),
                "estimated_value": round(estimated_value, 1),
                "gap_type": "zero_click",
                "suggested_post_type": post_type,
            })

        # Category 2: Position 5-20 with low CTR (easy wins)
        # Already ranking but CTR is below potential
        elif 5 <= position <= 20 and ctr_val < 0.03 and impressions >= 40:
            # Better title/meta could push CTR from <3% to 5-8%
            estimated_improvement = 0.05 - ctr_val
            estimated_value = impressions * max(estimated_improvement, 0.02)

            post_type = "service_area" if _is_location_query(query_text) else "seo_blog"

            opportunities.append({
                "query": query_text,
                "impressions": impressions,
                "clicks": clicks,
                "current_position": round(position, 1),
                "current_ctr": round(ctr_val, 4),
                "estimated_monthly_clicks": round(estimated_value / 3, 0),
                "estimated_value": round(estimated_value, 1),
                "gap_type": "low_ctr",
                "suggested_post_type": post_type,
            })

    # Sort by estimated value (highest potential first)
    opportunities.sort(key=lambda x: x["estimated_value"], reverse=True)

    # Deduplicate similar-intent queries (keep the higher-value version)
    # e.g. "difference between yard sale and garage sale" vs
    #      "difference between garage sale and yard sale"
    deduped = []
    seen_word_sets = []
    for opp in opportunities:
        # Create a normalized word set (order-independent)
        words = frozenset(opp["query"].lower().split())
        # Check if we already have a query with the same words
        if words not in seen_word_sets:
            seen_word_sets.append(words)
            deduped.append(opp)
    opportunities = deduped

    logger.info(f"Content gap analysis complete: {len(opportunities)} opportunities found")
    return opportunities[:30]


def _is_location_query(query: str) -> bool:
    """Check if a query contains location terms that suggest a service area page."""
    location_terms = [
        "palm harbor", "dunedin", "tarpon springs", "clearwater", "largo",
        "st pete", "petersburg", "safety harbor", "tampa", "brandon",
        "new port richey", "trinity", "wesley chapel", "brooksville",
        "spring hill", "crystal river", "inverness", "bradenton",
        "pinellas", "pasco", "hillsborough", "hernando", "citrus", "manatee",
        "seminole", "lakewood ranch",
    ]
    q_lower = query.lower()
    return any(loc in q_lower for loc in location_terms)


def _is_out_of_territory(query: str) -> bool:
    """
    Detect queries targeting locations outside OLS service area (Greater Tampa Bay).

    OLS serves Pinellas, Pasco, Hillsborough, Hernando, Citrus, and Manatee counties.
    Queries mentioning Virginia, other states, or non-FL cities should be skipped.
    """
    q_lower = query.lower()

    # Full state/region names — simple substring match
    out_of_territory_full = [
        "virginia", "maryland", "washington dc", "new york", "california",
        "texas", "chicago", "atlanta", "north carolina", "south carolina",
        "georgia", "alabama", "mississippi", "louisiana", "tennessee",
        "kentucky", "ohio", "michigan", "pennsylvania", "new jersey",
        "connecticut", "massachusetts", "oregon", "colorado", "arizona",
        "nevada", "utah", "hawaii", "indiana", "minnesota", "wisconsin",
        "missouri", "iowa", "arkansas", "oklahoma", "kansas", "nebraska",
        "idaho", "montana", "wyoming", "new mexico", "maine", "vermont",
        "new hampshire", "rhode island", "delaware", "west virginia",
        "south dakota", "north dakota",
    ]

    for term in out_of_territory_full:
        if term in q_lower:
            return True

    # 2-letter state abbreviations — need word boundary matching
    # Excludes FL (our state) and ambiguous abbreviations that are common
    # English words: "me" (Maine), "in" (Indiana), "or" (Oregon),
    # "oh" (Ohio), "hi" (Hawaii), "la" (Louisiana), "de" (Delaware),
    # "al" (Alabama — could match names). These states are covered by
    # their full names above.
    state_abbrevs = [
        "va", "ga", "md", "dc", "ny", "ca", "tx", "nc", "sc",
        "ms", "tn", "ky", "mi", "pa", "nj",
        "ct", "ma", "co", "az", "nv", "ut",
        "mn", "wi", "mo", "ia", "ar", "ok", "ks", "ne", "id",
        "mt", "wy", "nm", "vt", "nh", "ri", "wv",
        "sd", "nd", "il",
    ]

    for abbrev in state_abbrevs:
        if re.search(rf'\b{abbrev}\b', q_lower):
            return True

    return False


def _is_off_topic(query: str) -> bool:
    """
    Skip queries unrelated to OLS core services.

    OLS offers: estate sales, estate cleanouts, downsizing help,
    organizing, liquidation, appraisals, and probate services.
    Queries about collectibles (barbie, etc.) without estate/sale context
    are off-topic and won't convert to leads.
    """
    q_lower = query.lower()

    # Core service terms — if present, always keep the query
    service_terms = [
        "estate", "cleanout", "clean out", "downsiz", "liquidat",
        "apprais", "probate", "organiz", "hoard", "declutter",
        "moving sale", "yard sale", "garage sale", "tag sale",
        "antique", "auction",
    ]
    if any(term in q_lower for term in service_terms):
        return False

    # Off-topic categories that won't drive leads
    off_topic_terms = [
        "barbie", "pokemon", "hot wheels", "lego",
        "recipe", "weather", "movie", "netflix",
        "sports", "nfl", "nba",
    ]
    if any(term in q_lower for term in off_topic_terms):
        return True

    return False


def generate_blog_post(
    db: Session,
    topic: str,
    target_keyword: str,
    post_type: str = "seo_blog",
    related_keywords: Optional[List[str]] = None,
) -> Dict:
    """
    Generate a complete blog post using Claude API.

    Args:
        db: Database session
        topic: Blog post topic (e.g., "Estate Sales in Clearwater")
        target_keyword: Primary SEO keyword (e.g., "estate sale clearwater")
        post_type: "seo_blog" (800-1200 words), "service_area" (800-1000 words),
                   or "educational_guide" (1500+ words)
        related_keywords: List of secondary keywords to naturally include

    Returns:
        {
            "title": "SEO-optimized title under 60 chars",
            "body_html": "<h2>...</h2><p>...</p>",
            "summary_html": "Short summary for post preview",
            "handle": "url-slug",
            "tags": ["estate sales", "clearwater"],
            "meta_description": "150-160 char SEO description"
        }
    """
    if post_type not in ["seo_blog", "service_area", "educational_guide"]:
        raise ValueError(f"Invalid post_type: {post_type}")

    # Word count and tone by type
    word_counts = {
        "seo_blog": "800-1200 words",
        "service_area": "800-1000 words",
        "educational_guide": "1500+ words",
    }

    tone_hints = {
        "seo_blog": "informative and actionable, with strong SEO optimization",
        "service_area": "local, community-focused, highlighting service areas in Greater Tampa Bay",
        "educational_guide": "comprehensive and authoritative, a go-to resource for the topic",
    }

    related_kw_str = ""
    if related_keywords:
        related_kw_str = f"\n- Related keywords to naturally include: {', '.join(related_keywords)}"

    counties_str = ", ".join(FLORIDA_COUNTIES)
    cities_str = ", ".join(FLORIDA_CITIES)

    # Fetch real existing blog URLs for internal linking
    existing_posts = _get_existing_blog_urls()
    if existing_posts:
        links_section = "EXISTING BLOG POSTS (use these EXACT URLs for internal links — pick 2-3 relevant ones):\n"
        for post in existing_posts[:20]:
            links_section += f'  - "{post["title"]}": {post["url"]}\n'
    else:
        links_section = "Internal links: Link to /blogs/news/ and /pages/contact for CTA."

    # CTA intent varies by post type, but the phone number and contact URL are MANDATORY for all types
    cta_intent = {
        "seo_blog": "Frame as scheduling a free consultation",
        "service_area": "Frame as requesting a free in-home estimate, mention serving the specific area",
        "educational_guide": "Frame as getting personalized expert guidance, position OLS as the trusted resource",
    }
    cta_framing = cta_intent.get(post_type, cta_intent["seo_blog"])

    prompt = f"""Write a professional blog post for Organizing Life Services (OLS),
an estate sale and downsizing company based in Tampa Bay, Florida.

Topic: {topic}
Primary keyword: {target_keyword}
Post type: {post_type}
Target length: {word_counts[post_type]}
Tone: {tone_hints[post_type]}{related_kw_str}

=============================================================
BUSINESS DETAILS (ALL REQUIRED — must appear in the post):
  - Business name: Organizing Life Services (OLS)
  - Phone: (727) 542-6028   <-- MUST appear in body_html, verbatim
  - Phone link: tel:7275426028   <-- MUST be used as href on the phone number
  - Contact page URL: /pages/contact-us   <-- MUST be linked from the CTA
  - Location: Greater Tampa Bay, Florida
=============================================================

NON-NEGOTIABLE FINAL SECTION (the post MUST end with this):
Write a final <h2>Call</h2>-style section (heading text can vary — e.g., "Ready to Get Started?", "Schedule Your Free Consultation", "Talk to a Tampa Bay Estate Sale Expert") followed by ONE paragraph that:
  (a) Contains the EXACT phone number (727) 542-6028 as a clickable tel: link: <a href="tel:7275426028">(727) 542-6028</a>
  (b) Contains a link to /pages/contact-us with natural anchor text
  (c) {cta_framing}
  (d) Is 40-80 words long

If you omit the phone number, the tel: link, or the /pages/contact-us link from this closing section, the post is invalid and will be rejected.

CONTENT REQUIREMENTS:
1. Write {word_counts[post_type]} of original, human-sounding content
2. Target audience: homeowners in Greater Tampa Bay dealing with estate sales, downsizing, or estate cleanouts
3. Geographic focus: Reference {counties_str} counties and cities like {cities_str}
4. CRITICAL: NEVER reference locations or services outside Florida
5. Avoid generic AI phrases like "in today's world", "navigating the complexities", "it's important to note", "whether you're looking to"
6. Write in a warm, knowledgeable, helpful tone — like a trusted neighbor who happens to be an expert

SEO REQUIREMENTS:
7. Include the primary keyword "{target_keyword}" in the FIRST paragraph (within first 100 words)
8. Use the primary keyword naturally 3-5 times throughout (no keyword stuffing)
9. Use proper heading hierarchy: ONE h2 for the intro, then h2 for each major section, h3 for subsections
10. Write an SEO meta description (150-160 characters) that includes the keyword and a compelling reason to click
11. Title must be under 60 characters, include the keyword, and be compelling to click

LINKING:
{links_section}
12. Include 2-3 internal links to the most relevant existing posts above (in the body, not the CTA)
13. The final CTA section described above is REQUIRED and must contain (727) 542-6028 verbatim

FORMATTING:
14. Use clean HTML: h2, h3, p, ul/li, a tags only (Shopify compatible)
15. No inline styles, no divs, no classes
16. Handle/slug must be lowercase, hyphens only, under 60 characters, no special characters

Format your response as JSON with these exact keys:
{{
    "title": "Your SEO Title Here",
    "meta_description": "Your meta description here (150-160 chars)",
    "body_html": "<h2>Intro heading</h2><p>Content with keyword in first paragraph...</p>",
    "summary_html": "<p>A 2-3 sentence summary</p>",
    "handle": "url-slug-here",
    "tags": ["estate sales", "tampa bay", "relevant tag 3", "relevant tag 4"]
}}

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no text outside the JSON object."""

    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the response
        response_text = message.content[0].text

        # Remove markdown code block if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        post_data = json.loads(response_text.strip())

        # Validate required fields
        required_fields = ["title", "meta_description", "body_html", "summary_html", "handle"]
        for field in required_fields:
            if field not in post_data:
                raise ValueError(f"Missing required field in Claude response: {field}")

        # -------------------------------------------------------------
        # Content validation: reject posts missing required CTA elements
        # -------------------------------------------------------------
        # These checks catch cases where Claude ignores the prompt's CTA
        # requirement. A post without a phone number or contact link is
        # broken for conversion purposes — we fail loudly instead of
        # silently publishing it to Shopify.
        body = post_data.get("body_html", "") or ""
        body_lower = body.lower()

        # Accept any of these phone number formats
        phone_formats = [
            "(727) 542-6028",
            "727-542-6028",
            "727.542.6028",
            "7275426028",  # covers tel:7275426028 and raw
        ]
        has_phone = any(fmt in body for fmt in phone_formats)

        has_tel_link = "tel:7275426028" in body_lower or 'href="tel:7275426028"' in body_lower
        has_contact_link = "/pages/contact-us" in body_lower

        validation_errors = []
        if not has_phone:
            validation_errors.append(
                "Post body missing required phone number (727) 542-6028"
            )
        if not has_tel_link:
            validation_errors.append(
                "Post body missing required tel:7275426028 clickable link"
            )
        if not has_contact_link:
            validation_errors.append(
                "Post body missing required /pages/contact-us link"
            )

        if validation_errors:
            error_msg = "Content validation failed: " + "; ".join(validation_errors)
            logger.error(f"{error_msg}. Generated title was: {post_data.get('title', '?')}")
            raise ValueError(error_msg)

        # Use Claude-generated tags if present, otherwise fallback
        if "tags" not in post_data or not post_data["tags"]:
            post_data["tags"] = [
                "estate sales",
                "tampa bay",
                target_keyword.replace(" ", "-").lower(),
            ]

        # Sanitize handle: lowercase, hyphens only, max 60 chars
        handle = post_data.get("handle", "")
        handle = re.sub(r'[^a-z0-9-]', '-', handle.lower())
        handle = re.sub(r'-+', '-', handle).strip('-')[:60]
        post_data["handle"] = handle

        logger.info(
            f"Generated blog post: {post_data['title']} "
            f"(phone+tel+contact CTA all verified)"
        )
        return post_data

    except Exception as e:
        logger.error(f"Error generating blog post: {e}")
        raise


def create_content_task(
    db: Session, opportunity: Dict, post_type: str = "seo_blog"
) -> DashboardTask:
    """
    Create a dashboard task for content generation.

    Args:
        db: Database session
        opportunity: Result from analyze_content_gaps()
        post_type: Type of content to generate

    Returns:
        DashboardTask record (not yet committed)
    """
    query = opportunity["query"]
    impressions = opportunity["impressions"]

    # Determine priority
    if impressions >= 200:
        priority = "HIGH"
    elif impressions >= 50:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    # Generate category based on query
    category = "blog_post"
    if any(
        term in query.lower()
        for term in ["service area", "estate sale", "downsizing", "liquidation"]
    ):
        category = "service_area"

    task = DashboardTask(
        task_type="content",
        category=category,
        priority=priority,
        title=f"Blog Post: {query.title()}",
        description=f"Create a {post_type} targeting '{query}' based on {impressions} search impressions with low click-through rate.",
        finding=f"GSC Data: {impressions} impressions, {opportunity['clicks']} clicks, position {opportunity['current_position']}",
        action_endpoint="/api/content/generate-and-publish",
        action_payload={
            "topic": query.title(),
            "target_keyword": query,
            "post_type": post_type,
        },
        status="pending",
    )

    db.add(task)
    db.commit()

    logger.info(f"Created content task #{task.id}: {task.title}")
    return task


def publish_to_shopify(db: Session, task_id: int) -> Dict:
    """
    Generate blog post content and publish to Shopify.

    Args:
        db: Database session
        task_id: DashboardTask ID

    Returns:
        {
            "status": "success" or "error",
            "article_url": "https://ols-online.myshopify.com/blogs/...",
            "article_id": "...",
            "task_id": task_id
        }
    """
    # Fetch the task
    task = db.query(DashboardTask).filter(DashboardTask.id == task_id).first()
    if not task:
        return {"status": "error", "detail": f"Task #{task_id} not found"}

    if task.status != "approved":
        return {
            "status": "error",
            "detail": f"Task status is '{task.status}', must be 'approved'",
        }

    try:
        # Mark as executing immediately to prevent duplicate runs
        task.status = "executing"
        db.commit()

        payload = task.action_payload
        topic = payload.get("topic", "Blog Post")
        target_keyword = payload.get("target_keyword", "")
        post_type = payload.get("post_type", "seo_blog")

        # Generate the blog post
        post_data = generate_blog_post(
            db=db,
            topic=topic,
            target_keyword=target_keyword,
            post_type=post_type,
        )

        # Generate featured image
        image_data = _generate_blog_image(topic=topic, target_keyword=target_keyword)

        # Publish to Shopify
        article_body = {
            "article": {
                "title": post_data["title"],
                "body_html": post_data["body_html"],
                "summary_html": post_data["summary_html"],
                "handle": post_data["handle"],
                "tags": ",".join(post_data["tags"]),
                "metafields": [
                    {
                        "namespace": "global",
                        "key": "description_tag",
                        "value": post_data["meta_description"],
                        "type": "string",
                    }
                ],
            }
        }

        # Attach featured image if generated successfully
        if image_data:
            article_body["article"]["image"] = {
                "src": image_data["src"],
                "alt": image_data["alt"],
            }

        response = httpx.post(
            _shopify_url(f"blogs/{SHOPIFY_BLOG_ID}/articles.json"),
            headers=_shopify_headers(),
            json=article_body,
            timeout=60,  # longer timeout for image download
        )
        response.raise_for_status()

        article_response = response.json().get("article", {})
        article_id = article_response.get("id")
        article_handle = article_response.get("handle")

        # Build the article URL
        article_url = f"https://{SHOPIFY_STORE}.myshopify.com/blogs/news/{article_handle}"

        # Update task status
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.result = {
            "shopify_article_id": article_id,
            "shopify_article_url": article_url,
            "title": post_data["title"],
        }
        db.commit()

        logger.info(f"Published article #{article_id} to Shopify: {article_url}")

        return {
            "status": "success",
            "article_id": article_id,
            "article_url": article_url,
            "task_id": task_id,
        }

    except httpx.HTTPError as e:
        logger.error(f"Shopify API error: {e}")
        task.status = "failed"
        task.result = {"error": str(e)}
        db.commit()
        return {
            "status": "error",
            "detail": f"Shopify API error: {str(e)}",
        }

    except Exception as e:
        logger.error(f"Error publishing to Shopify: {e}")
        task.status = "failed"
        task.result = {"error": str(e)}
        db.commit()
        return {"status": "error", "detail": str(e)}
