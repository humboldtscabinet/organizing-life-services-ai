"""
Blog Audit Script — Pull all blog posts from Shopify and analyze for:
1. Out-of-territory state references
2. SEO quality (title length, meta descriptions, content length, headings, links, images)

Run inside Docker:
  docker exec ols-api python /app/data/blog_audit.py
"""

import os
import sys
import json
import re

sys.path.insert(0, "/app")

import httpx

STORE = os.getenv("SHOPIFY_STORE", "ols-online")
CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

OUT_OF_TERRITORY_STATES = [
    'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
    'connecticut', 'delaware', 'georgia', 'hawaii', 'idaho', 'illinois',
    'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine', 'maryland',
    'massachusetts', 'michigan', 'minnesota', 'mississippi', 'missouri',
    'montana', 'nebraska', 'nevada', 'new hampshire', 'new jersey',
    'new mexico', 'new york', 'north carolina', 'north dakota', 'ohio',
    'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina',
    'south dakota', 'tennessee', 'texas', 'utah', 'vermont', 'virginia',
    'washington', 'west virginia', 'wisconsin', 'wyoming'
]

OUT_OF_TERRITORY_CITIES = [
    'new york city', 'los angeles', 'chicago', 'houston', 'phoenix',
    'philadelphia', 'san antonio', 'san diego', 'dallas', 'san jose',
    'austin', 'seattle', 'denver', 'boston', 'nashville', 'detroit',
    'portland', 'las vegas', 'atlanta', 'san francisco', 'pittsburgh',
    'charlotte', 'minneapolis', 'baltimore', 'milwaukee', 'richmond'
]


def get_token():
    resp = httpx.post(
        f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("access_token")


def shopify_get(endpoint, token):
    url = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}/{endpoint}"
    resp = httpx.get(url, headers={"X-Shopify-Access-Token": token}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def strip_html(html):
    if not html:
        return ""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


def find_state_references(text):
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for state in OUT_OF_TERRITORY_STATES:
        if state in text_lower:
            idx = text_lower.index(state)
            start = max(0, idx - 40)
            end = min(len(text), idx + len(state) + 40)
            found.append({"state": state, "context": f"...{text[start:end].strip()}..."})
    for city in OUT_OF_TERRITORY_CITIES:
        if city in text_lower:
            idx = text_lower.index(city)
            start = max(0, idx - 40)
            end = min(len(text), idx + len(city) + 40)
            found.append({"state": f"CITY:{city}", "context": f"...{text[start:end].strip()}..."})
    return found


def audit_seo(article):
    issues = []
    title = article.get("title", "")
    if len(title) > 60:
        issues.append(f"Title too long ({len(title)} chars, ideal < 60)")
    if len(title) < 20:
        issues.append(f"Title too short ({len(title)} chars)")
    body = article.get("body_html", "") or ""
    plain = strip_html(body)
    word_count = len(plain.split())
    if word_count < 300:
        issues.append(f"Thin content ({word_count} words, recommend 500+)")
    if '<h1' not in body.lower() and '<h2' not in body.lower():
        issues.append("No heading tags (H1/H2) found")
    if 'organizinglifeservices.com' not in body and 'href="/' not in body:
        issues.append("No internal links found")
    if '<img' not in body.lower():
        issues.append("No images in content")
    return issues, word_count


def main():
    print("=" * 70)
    print("OLS BLOG AUDIT")
    print("=" * 70)

    token = get_token()
    blogs = shopify_get("blogs.json", token).get("blogs", [])
    print(f"\nFound {len(blogs)} blog(s)")

    all_articles = []
    for blog in blogs:
        blog_id = blog["id"]
        blog_title = blog.get("title", "Unknown")
        arts = shopify_get(f"blogs/{blog_id}/articles.json?limit=250", token).get("articles", [])
        print(f"  Blog: {blog_title} -- {len(arts)} articles")
        for a in arts:
            a["_blog_title"] = blog_title
            a["_blog_id"] = blog_id
        all_articles.extend(arts)

    print(f"\nTotal articles: {len(all_articles)}")
    print("=" * 70)

    results = []
    for art in all_articles:
        title = art.get("title", "Untitled")
        handle = art.get("handle", "")
        body_html = art.get("body_html", "") or ""
        plain_text = strip_html(body_html)
        summary = strip_html(art.get("summary_html", "") or "")
        tags = art.get("tags", "")
        created = art.get("created_at", "")[:10]

        state_refs = find_state_references(title) + find_state_references(plain_text) + find_state_references(summary)
        seo_issues, word_count = audit_seo(art)

        results.append({
            "title": title,
            "handle": handle,
            "url": f"https://organizinglifeservices.com/blogs/news/{handle}",
            "blog": art["_blog_title"],
            "article_id": art["id"],
            "blog_id": art["_blog_id"],
            "created": created,
            "word_count": word_count,
            "tags": tags,
            "state_references": state_refs,
            "seo_issues": seo_issues,
            "has_state_issues": len(state_refs) > 0,
            "has_seo_issues": len(seo_issues) > 0,
        })

    state_posts = [r for r in results if r["has_state_issues"]]
    seo_posts = [r for r in results if r["has_seo_issues"]]

    print(f"\n  Posts with out-of-territory references: {len(state_posts)}")
    print(f"  Posts with SEO issues: {len(seo_posts)}")
    print(f"  Clean posts: {len([r for r in results if not r['has_state_issues'] and not r['has_seo_issues']])}")

    if state_posts:
        print("\n" + "-" * 70)
        print("OUT-OF-TERRITORY STATE REFERENCES")
        print("-" * 70)
        for r in state_posts:
            print(f"\n  [{r['created']}] {r['title']}")
            print(f"    URL: {r['url']}")
            print(f"    Words: {r['word_count']}")
            states_found = sorted(set(ref["state"] for ref in r["state_references"]))
            print(f"    States/cities found: {', '.join(states_found)}")
            for ref in r["state_references"][:5]:
                print(f"      -> {ref['context']}")
            if len(r["state_references"]) > 5:
                print(f"      ... and {len(r['state_references']) - 5} more")

    if seo_posts:
        print("\n" + "-" * 70)
        print("SEO ISSUES")
        print("-" * 70)
        for r in seo_posts:
            print(f"\n  [{r['created']}] {r['title']}")
            print(f"    URL: {r['url']}")
            print(f"    Words: {r['word_count']}")
            for issue in r["seo_issues"]:
                print(f"      ! {issue}")

    print("\n" + "-" * 70)
    print("ALL POSTS SUMMARY")
    print("-" * 70)
    for r in sorted(results, key=lambda x: x["created"], reverse=True):
        flags = []
        if r["has_state_issues"]: flags.append("GEO")
        if r["has_seo_issues"]: flags.append("SEO")
        flag_str = f" [{','.join(flags)}]" if flags else " [OK]"
        print(f"  {r['created']} | {r['word_count']:>5}w | {r['title'][:55]}{flag_str}")

    # Save JSON for further analysis
    with open("/tmp/blog_audit_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull JSON saved to /tmp/blog_audit_results.json")


if __name__ == "__main__":
    main()
