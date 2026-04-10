"""Fetch the full body_html of a specific blog article."""
import os, sys, json
sys.path.insert(0, "/app")
import httpx

STORE = os.getenv("SHOPIFY_STORE", "ols-online")
CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

def get_token():
    resp = httpx.post(
        f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("access_token")

token = get_token()
blog_id = 52179501100
article_id = 561529389210

url = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}/blogs/{blog_id}/articles/{article_id}.json"
resp = httpx.get(url, headers={"X-Shopify-Access-Token": token}, timeout=30)
resp.raise_for_status()
article = resp.json().get("article", {})

# Save full article to JSON
with open("/tmp/article_full.json", "w") as f:
    json.dump({
        "title": article.get("title"),
        "handle": article.get("handle"),
        "tags": article.get("tags"),
        "body_html": article.get("body_html"),
        "summary_html": article.get("summary_html"),
    }, f, indent=2)

print(f"Title: {article.get('title')}")
print(f"Handle: {article.get('handle')}")
print(f"Tags: {article.get('tags')}")
print(f"Body length: {len(article.get('body_html', ''))} chars")
print(f"Saved to /tmp/article_full.json")
