"""Append FAQ + FAQPage JSON-LD schema to top 4 articles by GSC impressions.

Targets (chosen from gsc_top_pages_2026-05-28.json — excluding already-FAQ'd
yard/garage article and skipping any with low SEO value):

  1. pros-and-cons-of-estate-sales         (722 imp, 0.14% CTR, pos 23.6)
  2. how-to-increase-your-home-appraisal-value (677 imp, 0% CTR, pos 24.4)
  3. estate-auction-vs-estate-sale-pros-and-cons (579 imp, 0.17% CTR, pos 22.7)
  4. the-ultimate-guide-for-barbie-collector-buyers (563 imp, 0% CTR, pos 17.1)

Each FAQ block uses an idempotent marker so reruns are safe.
"""
import os
import sys
import time
import httpx

STORE = os.getenv("SHOPIFY_STORE"); CID = os.getenv("SHOPIFY_CLIENT_ID")
CS = os.getenv("SHOPIFY_CLIENT_SECRET"); API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")
BLOG_ID = 52179501100

# Per-article (handle, marker, [(question, answer), ...])
ARTICLES = [
    (
        "pros-and-cons-of-estate-sales", "FAQ-PCES-V1",
        [
            ("What are the main pros and cons of an estate sale?",
             "The main pros of an estate sale are that it converts an entire household of belongings into cash quickly (typically over one weekend), the professional company handles all pricing, staging, marketing, and sale-day staffing, and unsold items can usually be donated or hauled away as part of the service. The main cons are that you generally net 60–70% of gross sales after a 30–40% commission, the home must be open to the public for 1–3 days, items occasionally sell below sentimental value, and you forfeit some control over final pricing because the company prices to actually sell. For most Tampa Bay families liquidating a full home, the time savings and net proceeds still beat any DIY alternative."),
            ("Is an estate sale worth it financially?",
             "For homes with $5,000+ in total contents, yes — an estate sale almost always produces more net cash than a yard sale, auction, or consignment shop, even after the 30–40% commission. A professionally run estate sale draws hundreds of buyers in a weekend, prices items at fair market value rather than yard-sale prices, and clears the home so the realtor can list immediately. For very small estates (under $2,000 in contents), a buyout, online listing, or donation may net more after commission."),
            ("What are the biggest disadvantages of holding an estate sale?",
             "The biggest disadvantages are: (1) the company keeps 30–40% of gross sales as commission, (2) the home must be staged and open to the public for 1–3 days, (3) some sentimental items may sell for less than the family expected, and (4) Florida law requires a Bill of Sale for firearms and other regulated items, which adds paperwork. A reputable estate sale company will walk through these issues during the free consultation so there are no surprises on sale day."),
        ],
    ),
    (
        "how-to-increase-your-home-appraisal-value", "FAQ-HIAV-V1",
        [
            ("What hurts a home appraisal the most?",
             "The biggest negatives are deferred maintenance (roof age, HVAC condition, water stains, peeling paint), outdated kitchens and bathrooms, cluttered or dirty interiors, and obvious damage like cracked tile, broken fixtures, or pet odors. Curb-appeal issues — overgrown landscaping, faded paint, cracked driveways — also lower the appraiser's first impression. Decluttering and a thorough deep clean are the cheapest, fastest fixes and can move an appraisal by several thousand dollars."),
            ("Does decluttering before an appraisal help?",
             "Yes — decluttering helps significantly because it allows the appraiser to see room dimensions, finishes, and storage clearly, and it signals that the home has been well-maintained. Empty or lightly furnished homes also photograph better, which matters because the appraiser includes interior photos in the report. Organizing Life Services regularly handles pre-appraisal estate sales and cleanouts in Tampa Bay so homeowners can present a clean, well-staged property."),
            ("How much can a home appraisal increase with simple upgrades?",
             "Simple upgrades under $5,000 — fresh interior paint in neutral colors, professional carpet cleaning or replacement, new light fixtures, modern cabinet hardware, fresh landscaping, and pressure-washing — can add $5,000–$20,000 to a Tampa Bay home appraisal. Bigger ROI projects include kitchen and bathroom refreshes (new countertops, refaced cabinets, updated faucets), which can return 70–90% of cost in appraised value."),
        ],
    ),
    (
        "estate-auction-vs-estate-sale-pros-and-cons", "FAQ-EAES-V1",
        [
            ("What is the difference between an estate auction and an estate sale?",
             "An estate sale is a 1–3 day, fixed-price event held inside the home, where the public walks through and buys items off marked price tags. An estate auction is a competitive-bidding event — held either on-site, at an auction house, or online — where each item or lot sells to the highest bidder. Estate sales are faster, less paperwork, and better for liquidating a full household of mid-range items. Auctions typically yield higher prices on rare, high-value, or collectible pieces because competitive bidding drives prices up. Many Tampa Bay families use a hybrid approach: auction the top 10–20 items, then estate-sale the rest."),
            ("Which makes more money — an estate sale or an estate auction?",
             "It depends on the inventory. An estate sale typically grosses more total dollars because every item is for sale, including everyday household goods. An auction usually grosses higher per-item prices on premium pieces (fine art, antiques, jewelry, sterling, mid-century modern, Asian art) but skips the lower-value contents. For a household with mostly everyday items plus 5–10 valuable pieces, the highest-net strategy is to auction the premium items separately and then run an estate sale for the rest."),
            ("Which has a higher commission — an estate sale or an estate auction?",
             "Estate sale commissions in Tampa Bay typically run 30–40% of gross sales. Auction commissions vary more: live regional auction houses charge 20–35% seller commission plus a 15–25% buyer's premium, while online auction platforms (e.g., Everything But The House, LiveAuctioneers consignors) charge 35–50% all-in. The total cost is usually similar; the better choice is the format that produces the highest gross for your specific inventory."),
        ],
    ),
    (
        "the-ultimate-guide-for-barbie-collector-buyers", "FAQ-BARB-V1",
        [
            ("What Barbie dolls are worth the most money?",
             "The most valuable Barbies are the 1959 #1 Ponytail Barbie (mint, boxed: $20,000–$27,000), the 1959–1965 Bubblecut and Swirl Ponytail variants ($300–$3,000 boxed), De Beers 40th Anniversary Barbie with real diamonds ($85,000+), the Pink Splendor 1996 ($900–$1,500), and rare designer collaborations (Bob Mackie originals, Lorraine Schwartz). Condition is everything — mint in original box doubles or triples value. Estate sales in Tampa Bay regularly turn up unboxed 1960s–1980s Barbies in the $50–$500 range."),
            ("How do I find a Barbie collector or buyer near me?",
             "The best routes are (1) reputable estate sale and appraisal companies that maintain a network of vintage doll collectors, (2) verified eBay buyers with 1,000+ feedback scores in vintage dolls, (3) specialty auction houses like Theriault's or Morphy Auctions, and (4) local doll-collector club meetups (the Tampa Bay Doll Collectors Club meets monthly). Organizing Life Services in Tampa Bay regularly appraises and brokers vintage Barbie collections during estate liquidations."),
            ("How can I tell if my Barbie is valuable?",
             "Check four things: (1) head and body markings (date stamp on lower back, country of manufacture — pre-1972 Japan-made are most valuable), (2) hair condition (original, never-played-with hair adds 50–200% value), (3) original outfit, shoes, and accessories present and intact, and (4) original box, stand, and paperwork. A 1960s Barbie with original box, intact hair, and full accessories can be worth 5–10× the same doll loose."),
        ],
    ),
]


def build_faq_html(marker, qa_pairs):
    visible = "\n".join(
        f"<h4><strong>{q}</strong></h4>\n<p>{a}</p>" for q, a in qa_pairs
    )
    schema_entities = ",\n    ".join(
        '{"@type":"Question","name":' + _jstr(q) + ',"acceptedAnswer":{"@type":"Answer","text":' + _jstr(a) + "}}"
        for q, a in qa_pairs
    )
    return (
        f"<!-- {marker} -->\n"
        f"<h3><strong>Frequently Asked Questions</strong></h3>\n"
        f"{visible}\n"
        '<script type="application/ld+json">\n'
        '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[\n    '
        + schema_entities
        + "\n]}\n</script>\n"
        f"<!-- /{marker} -->"
    )


def _jstr(s):
    import json
    return json.dumps(s, ensure_ascii=False)


def _retry(fn, *a, **k):
    for i in range(6):
        try:
            r = fn(*a, **k)
            if hasattr(r, "status_code") and r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2 ** i))); continue
            return r
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            time.sleep(2 ** i)
    raise RuntimeError("retries exhausted")


def main():
    if not all([STORE, CID, CS]): sys.exit("Missing SHOPIFY creds")
    tok = httpx.post(f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CID, "client_secret": CS, "grant_type": "client_credentials"},
        timeout=30).json()["access_token"]
    H = {"X-Shopify-Access-Token": tok, "Content-Type": "application/json"}
    BASE = f"https://{STORE}.myshopify.com/admin/api/{API_VER}"

    # Resolve handle -> article ID (paginate articles in blog)
    by_handle = {}
    next_url = f"{BASE}/blogs/{BLOG_ID}/articles.json?limit=250&fields=id,handle,title"
    while next_url:
        r = _retry(httpx.get, next_url, headers=H, timeout=30)
        for a in r.json().get("articles", []):
            by_handle[a["handle"]] = a["id"]
        link = r.headers.get("Link", "")
        # crude rel=next parse
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
        time.sleep(0.3)
    print(f"[faq] resolved {len(by_handle)} article handles")

    for handle, marker, qa in ARTICLES:
        aid = by_handle.get(handle)
        if not aid:
            print(f"  [skip] {handle} not found"); continue
        art = _retry(httpx.get, f"{BASE}/blogs/{BLOG_ID}/articles/{aid}.json",
                     headers=H, timeout=30).json()["article"]
        body = art["body_html"] or ""
        if marker in body:
            print(f"  [skip] {handle} already has {marker}"); continue
        block = build_faq_html(marker, qa)
        new_body = body.rstrip() + "\n" + block + "\n"
        r = _retry(httpx.put, f"{BASE}/blogs/{BLOG_ID}/articles/{aid}.json",
                   headers=H, timeout=60,
                   json={"article": {"id": aid, "body_html": new_body}})
        r.raise_for_status()
        print(f"  [ok] {handle}: {len(body)} -> {len(new_body)} chars (+{len(new_body)-len(body)})")
        time.sleep(0.6)


if __name__ == "__main__":
    main()
