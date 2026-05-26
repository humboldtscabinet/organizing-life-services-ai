"""One-off: draft meta titles + descriptions for top CTR-fix pages via Claude."""
import json
from anthropic import Anthropic

PAGES = [
    {"query": "estate sales near me", "url": "https://organizinglifeservices.com/", "page_role": "Homepage of Organizing Life Services — local estate sale & senior downsizing company serving Pinellas, Pasco & Hillsborough counties (primary) plus Hernando, Citrus & Manatee (secondary), FL.", "current_pos": 5.4, "impressions": 48},
    {"query": "estate sale meaning", "url": "https://organizinglifeservices.com/pages/what-is-an-estate-sale", "page_role": "Educational page defining what an estate sale is, how it differs from other sales, and how the process works.", "current_pos": 1.7, "impressions": 96},
    {"query": "estate sales / estate sale (informational)", "url": "https://organizinglifeservices.com/blogs/news/pros-and-cons-of-estate-sales", "page_role": "Blog post weighing the pros and cons of holding an estate sale.", "current_pos": 4.4, "impressions": 135},
    {"query": "estate sale vs garage sale", "url": "https://organizinglifeservices.com/blogs/news/estate-sale-vs-garage-sale-know-the-differences", "page_role": "Blog post comparing estate sales and garage sales — key differences, when to use each.", "current_pos": 1.8, "impressions": 36},
]

PROMPT = """You are an SEO copywriter. Draft an SEO meta title and meta description for the following page.

PAGE URL: {url}
TARGET QUERY: {query}
PAGE PURPOSE: {page_role}
CURRENT GOOGLE POSITION: {current_pos} (avg)
RECENT IMPRESSIONS: {impressions} in last 30 days, but ZERO clicks — so the snippet is not enticing searchers.

Rules:
- Title: 50-60 characters, includes the target query naturally, leads with benefit/intent, no clickbait.
- Description: 140-155 characters, includes target query, gives a clear reason to click, includes a soft CTA.
- The brand is "Organizing Life Services" (Florida Gulf Coast — primary counties: Pinellas, Pasco, Hillsborough; also serves Hernando, Citrus, Manatee).
- Return STRICT JSON only: {{"title": "...", "description": "...", "title_chars": N, "desc_chars": N}}"""

client = Anthropic()
results = []
for p in PAGES:
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{"role": "user", "content": PROMPT.format(**p)}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
        text = text.strip().rstrip("`").strip()
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {"raw": text}
    results.append({"url": p["url"], "query": p["query"], **parsed})

print(json.dumps(results, indent=2))
