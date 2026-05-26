"""B2 — Generate full blog post for "difference between yard sale and estate sale" and publish.

Target query currently ranks #8 with no dedicated page (ambient ranking from generic content).
A targeted post should jump to top 5.

Run: docker exec ols-api sh -c 'cd /app && PYTHONPATH=/app python3 data/b2_yard_vs_estate_sale_post.py [--dry-run]'
"""
import json
import sys
import httpx
from anthropic import Anthropic

from app.services.shopify_service import _shopify_headers, _shopify_url

ARTICLE_HANDLE = "yard-sale-vs-estate-sale-key-differences"  # NEW handle

PROMPT = """You are a senior SEO content writer for Organizing Life Services, a Florida estate sale company serving Pinellas, Pasco & Hillsborough counties (primary) and Hernando, Citrus & Manatee (secondary).

Phone: (727) 542-6028
Website: https://organizinglifeservices.com

Write a comprehensive blog post (~1200 words) targeting the search query: "difference between yard sale and estate sale"

REQUIREMENTS:
- Authoritative but warm tone. Helpful, not pushy.
- Use H2 and H3 headings to structure. Include at least one comparison table.
- Cover: definitions, who runs each, typical inventory, pricing, duration, audience, profit potential, when to choose which, Florida-specific notes.
- Include 2 contextual internal links using Markdown-style HTML:
    * <a href="/pages/what-is-an-estate-sale">what an estate sale is</a>
    * <a href="/pages/estate-cleanout-services">estate cleanout services</a>
- End with a soft CTA section directing readers to call (727) 542-6028 for a free consultation.
- Use natural keyword variations: "yard sale vs estate sale", "garage sale", "estate liquidation", "Tampa Bay", "Pinellas County", etc.
- DO NOT use the word "delve". Avoid AI clichés ("In today's fast-paced world...", "Look no further", etc.).

ALSO PROVIDE:
- An SEO meta title (55-60 chars) including the target query
- An SEO meta description (140-155 chars) including the target query
- A short article excerpt/summary (~30 words) for the blog index
- A suggested featured-image alt text

RETURN STRICT JSON ONLY (no markdown fence):
{
  "title": "Display title for the article (60-70 chars, can differ from meta title)",
  "meta_title": "...",
  "meta_description": "...",
  "excerpt": "...",
  "image_alt": "...",
  "body_html": "Full HTML body. Use <h2>, <h3>, <p>, <ul>, <li>, <table>, <strong>, <a> tags. NO <html>/<body>/<head> wrappers."
}"""


def _get(p):
    r = httpx.get(_shopify_url(p), headers=_shopify_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def _post(p, body):
    r = httpx.post(_shopify_url(p), headers=_shopify_headers(), json=body, timeout=60)
    r.raise_for_status()
    return r.json()


def _put(p, body):
    r = httpx.put(_shopify_url(p), headers=_shopify_headers(), json=body, timeout=60)
    r.raise_for_status()
    return r.json()


def upsert_metafield(owner_resource, owner_id, key, value):
    list_path = f"{owner_resource}/{owner_id}/metafields.json"
    data = _get(list_path)
    existing = next(
        (m for m in data["metafields"]
         if m["namespace"] == "global" and m["key"] == key),
        None,
    )
    if existing:
        url = f"metafields/{existing['id']}.json"
        body = {"metafield": {"id": existing["id"], "value": value, "type": "single_line_text_field"}}
        return _put(url, body)["metafield"]
    body = {"metafield": {"namespace": "global", "key": key, "value": value,
                          "type": "single_line_text_field"}}
    return _post(list_path, body)["metafield"]


def generate_post():
    client = Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{"role": "user", "content": PROMPT}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
        text = text.strip().rstrip("`").strip()
    return json.loads(text)


def main(dry_run=False):
    blogs = _get("blogs.json?limit=50")["blogs"]
    blog = next((b for b in blogs if b["handle"] == "news"), blogs[0])
    print(f"Target blog: {blog['title']} (id={blog['id']}, handle={blog['handle']})")

    # Check if article already exists
    existing = _get(f"blogs/{blog['id']}/articles.json?limit=250&handle={ARTICLE_HANDLE}")
    if existing.get("articles"):
        print(f"Article with handle '{ARTICLE_HANDLE}' already exists — aborting.")
        sys.exit(0)

    post = generate_post()
    print("=== GENERATED POST ===")
    print(f"Title: {post['title']}")
    print(f"Meta title: {post['meta_title']} ({len(post['meta_title'])} chars)")
    print(f"Meta desc: {post['meta_description']} ({len(post['meta_description'])} chars)")
    print(f"Excerpt: {post['excerpt']}")
    print(f"Image alt: {post['image_alt']}")
    print(f"Body HTML length: {len(post['body_html'])} bytes")
    word_count = len(post['body_html'].split())
    print(f"~Word count: {word_count}")

    if dry_run:
        print("[dry-run] not pushing")
        with open("/tmp/b2_draft.json", "w") as f:
            json.dump(post, f, indent=2)
        print("Draft saved to /tmp/b2_draft.json")
        return

    # Create article
    body = {
        "article": {
            "title": post["title"],
            "handle": ARTICLE_HANDLE,
            "author": "Organizing Life Services",
            "tags": "estate sales, yard sales, garage sales, Tampa Bay, Florida",
            "body_html": post["body_html"],
            "summary_html": f"<p>{post['excerpt']}</p>",
            "published": True,
        }
    }
    created = _post(f"blogs/{blog['id']}/articles.json", body)["article"]
    article_id = created["id"]
    print(f"\nCreated article id={article_id} handle={created['handle']}")
    print(f"URL: https://organizinglifeservices.com/blogs/{blog['handle']}/{created['handle']}")

    # Push SEO metafields
    upsert_metafield("articles", article_id, "title_tag", post["meta_title"])
    upsert_metafield("articles", article_id, "description_tag", post["meta_description"])
    print("SEO metafields pushed.")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
