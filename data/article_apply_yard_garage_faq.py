"""Append FAQ + FAQPage JSON-LD to the yard-vs-garage article.

Target: /blogs/news/estate-sale-vs-garage-sale-know-the-differences
GSC opportunity: query "difference between yard sale and garage sale"
  — 92 impressions, 0% CTR, avg position 15.2.

Idempotent via marker FAQ-YGE-V1.
"""
import os
import sys
import httpx

STORE = os.getenv("SHOPIFY_STORE")
CID = os.getenv("SHOPIFY_CLIENT_ID")
CS = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")

BLOG_ID = 52179501100
ARTICLE_ID = 560955195546
MARKER = "FAQ-YGE-V1"

FAQ_HTML = """
<!-- FAQ-YGE-V1 -->
<h3><strong>Frequently Asked Questions</strong></h3>
<h4><strong>What is the difference between a yard sale and a garage sale?</strong></h4>
<p>A yard sale and a garage sale are essentially the same thing — both are small, informal sales held at a private home where the seller displays unwanted household items for neighbors and passersby to buy. The only practical difference is location: a yard sale is set up outside in the front yard or driveway, while a garage sale is staged inside or just outside the garage. Sellers use the terms interchangeably, and shoppers treat them the same way. Pricing, advertising (signs and Facebook Marketplace), and the type of merchandise (clothing, toys, kitchenware, tools) are identical. If weather is a concern or you have a large garage, the "garage sale" label may be more accurate; if you want curb-side visibility, "yard sale" works better. Either way, expect a one- or two-day event with most items priced from $0.50 to $20.</p>
<h4><strong>Is a yard sale or garage sale better than an estate sale?</strong></h4>
<p>It depends on what you are selling and how much of it. Yard/garage sales are best for clearing 50–200 everyday items and earning a few hundred dollars. Estate sales are better when you are liquidating an entire household (often 1,000+ items), need to handle antiques, jewelry, or collectibles, and want professional pricing, marketing, and crowd management. A typical Tampa Bay estate sale grosses several thousand dollars over a weekend — far more than a yard sale could ever produce.</p>
<h4><strong>Do I need a permit for a yard sale or garage sale in Florida?</strong></h4>
<p>Most Florida cities and counties allow homeowners to hold 2–4 yard or garage sales per year without a permit, but rules vary. Pinellas County, Hillsborough County, and many municipalities (St. Petersburg, Tampa, Clearwater) require sales to be limited in duration (usually 1–3 days) and may restrict signage placement. Always check your local code-enforcement office before posting signs on public right-of-way.</p>
<script type=\"application/ld+json\">
{
  \"@context\": \"https://schema.org\",
  \"@type\": \"FAQPage\",
  \"mainEntity\": [
    {
      \"@type\": \"Question\",
      \"name\": \"What is the difference between a yard sale and a garage sale?\",
      \"acceptedAnswer\": {
        \"@type\": \"Answer\",
        \"text\": \"A yard sale and a garage sale are essentially the same thing — both are small, informal sales held at a private home where the seller displays unwanted household items for neighbors and passersby to buy. The only practical difference is location: a yard sale is set up outside in the front yard or driveway, while a garage sale is staged inside or just outside the garage. Sellers use the terms interchangeably, and shoppers treat them the same way.\"
      }
    },
    {
      \"@type\": \"Question\",
      \"name\": \"Is a yard sale or garage sale better than an estate sale?\",
      \"acceptedAnswer\": {
        \"@type\": \"Answer\",
        \"text\": \"It depends on what you are selling. Yard/garage sales are best for clearing 50–200 everyday items and earning a few hundred dollars. Estate sales are better when you are liquidating an entire household, need to handle antiques or collectibles, and want professional pricing, marketing, and crowd management.\"
      }
    },
    {
      \"@type\": \"Question\",
      \"name\": \"Do I need a permit for a yard sale or garage sale in Florida?\",
      \"acceptedAnswer\": {
        \"@type\": \"Answer\",
        \"text\": \"Most Florida cities and counties allow homeowners to hold 2–4 yard or garage sales per year without a permit, but rules vary. Always check your local code-enforcement office for duration limits and signage rules.\"
      }
    }
  ]
}
</script>
<!-- /FAQ-YGE-V1 -->
"""


def main():
    if not all([STORE, CID, CS]):
        sys.exit("Missing SHOPIFY creds")
    tok = httpx.post(f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CID, "client_secret": CS, "grant_type": "client_credentials"},
        timeout=30).json()["access_token"]
    H = {"X-Shopify-Access-Token": tok, "Content-Type": "application/json"}
    BASE = f"https://{STORE}.myshopify.com/admin/api/{API_VER}"

    art = httpx.get(f"{BASE}/blogs/{BLOG_ID}/articles/{ARTICLE_ID}.json",
                    headers=H, timeout=30).json()["article"]
    body = art["body_html"]
    if MARKER in body:
        print(f"[faq] marker {MARKER} already present — nothing to do")
        return

    new_body = body.rstrip() + "\n" + FAQ_HTML.strip() + "\n"
    print(f"[faq] {len(body)} -> {len(new_body)} chars (+{len(new_body) - len(body)})")

    r = httpx.put(f"{BASE}/blogs/{BLOG_ID}/articles/{ARTICLE_ID}.json",
                  headers=H, timeout=60,
                  json={"article": {"id": ARTICLE_ID, "body_html": new_body}})
    r.raise_for_status()
    print("[faq] article updated.")


if __name__ == "__main__":
    main()
