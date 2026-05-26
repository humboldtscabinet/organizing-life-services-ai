"""B1 — Generate FAQ section + FAQPage JSON-LD for /pages/what-is-an-estate-sale and push to Shopify.

Targets: rich-snippet eligibility for "estate sale meaning" (currently #2 / 0% CTR).
Idempotent: skips if FAQ block already present (marker: data-ols-faq="v1").
Run: docker exec ols-api sh -c 'cd /app && PYTHONPATH=/app python3 data/b1_faq_what_is_estate_sale.py [--dry-run]'
"""
import json
import sys
import httpx
from anthropic import Anthropic

from app.services.shopify_service import _shopify_headers, _shopify_url

PAGE_HANDLE = "what-is-an-estate-sale"
MARKER = 'data-ols-faq="v1"'

PROMPT = """You are an expert SEO copywriter for a Florida estate sale company.

Write 6 FAQ Q&A pairs to append to our "What Is an Estate Sale" page.

CONTEXT:
- Brand: Organizing Life Services (Florida Gulf Coast: Pinellas, Pasco, Hillsborough primary; Hernando, Citrus, Manatee secondary)
- Phone: (727) 542-6028
- Page currently ranks #2 on Google for "estate sale meaning" but gets 0 clicks — we need FAQ rich-snippet eligibility.

TARGET QUESTIONS (use exactly these — they map to real search queries we want to win):
1. What is the meaning of an estate sale?
2. What is the difference between an estate sale and a garage sale?
3. How long does an estate sale last?
4. What happens to items that don't sell at an estate sale?
5. How much does it cost to hire an estate sale company?
6. How do estate sale companies in Florida price items?

RULES:
- Each answer: 40-70 words. Plain English. Helpful, not salesy.
- Naturally mention Florida / Tampa Bay / specific counties where relevant — but don't force it in every answer.
- One answer (the cost or hire one) may end with "Call (727) 542-6028 for a free consultation."
- Return STRICT JSON ONLY, no markdown fence:
{"faqs": [{"q": "...", "a": "..."}, ...]}"""


def _get(p):
    r = httpx.get(_shopify_url(p), headers=_shopify_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def _put_page(page_id, body_html):
    url = _shopify_url(f"pages/{page_id}.json")
    body = {"page": {"id": page_id, "body_html": body_html}}
    r = httpx.put(url, headers=_shopify_headers(), json=body, timeout=30)
    r.raise_for_status()
    return r.json()["page"]


def generate_faqs():
    client = Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": PROMPT}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
        text = text.strip().rstrip("`").strip()
    return json.loads(text)["faqs"]


def build_html_block(faqs):
    items = []
    items.append(f'<section {MARKER} class="ols-faq" style="margin-top:2.5rem">')
    items.append('  <h2>Frequently Asked Questions About Estate Sales</h2>')
    for f in faqs:
        items.append('  <details style="margin:1rem 0;border-bottom:1px solid #e5e5e5;padding-bottom:1rem">')
        items.append(f'    <summary style="font-weight:600;cursor:pointer;font-size:1.05rem">{f["q"]}</summary>')
        items.append(f'    <p style="margin-top:0.75rem">{f["a"]}</p>')
        items.append('  </details>')
    items.append('</section>')

    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in faqs
        ],
    }
    items.append('<script type="application/ld+json">')
    items.append(json.dumps(schema, indent=2))
    items.append('</script>')
    return "\n".join(items)


def main(dry_run=False):
    pages = {p["handle"]: p for p in _get("pages.json?limit=250")["pages"]}
    page = pages.get(PAGE_HANDLE)
    if not page:
        print("ERROR: page not found"); sys.exit(1)
    body = page["body_html"]
    if MARKER in body:
        print("FAQ block already present — skipping."); return

    faqs = generate_faqs()
    print("=== GENERATED FAQs ===")
    for i, f in enumerate(faqs, 1):
        print(f"{i}. {f['q']}\n   {f['a']}\n")
    print(f"Total: {len(faqs)} questions")

    block = build_html_block(faqs)
    new_body = body.rstrip() + "\n\n" + block

    print(f"\nBody size: {len(body)} -> {len(new_body)} bytes (+{len(new_body)-len(body)})")
    if dry_run:
        print("[dry-run] not pushing")
        return

    _put_page(page["id"], new_body)
    print(f"Pushed to page id={page['id']}.")
    print(f"Verify: curl -sL https://organizinglifeservices.com/pages/{PAGE_HANDLE} | grep -c FAQPage")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
