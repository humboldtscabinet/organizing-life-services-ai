"""Internal links A4 pass — append a 'Related Tampa Bay Estate Services' link
block to the top 6 articles by GSC impressions, using exact-match anchor text
drawn from striking-distance GSC queries.

Idempotent: marker INTLINKS-A4-V1 per article. Skips if already present.

Targets:
  - estate-sale-vs-garage-sale-know-the-differences (1574 imp)
  - pros-and-cons-of-estate-sales (722 imp)
  - how-to-increase-your-home-appraisal-value (677 imp)
  - estate-auction-vs-estate-sale-pros-and-cons (579 imp)
  - the-ultimate-guide-for-barbie-collector-buyers (563 imp)
  - how-to-plan-estate-sale (also high authority)

Each link uses the exact wording that surfaces in GSC striking-distance data,
so the anchor text reinforces the target page for those queries.
"""
import os
import sys
import time
import httpx

STORE = os.getenv("SHOPIFY_STORE"); CID = os.getenv("SHOPIFY_CLIENT_ID")
CS = os.getenv("SHOPIFY_CLIENT_SECRET"); API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")
BLOG_ID = 52179501100
MARKER = "INTLINKS-A4-V1"

TARGETS = [
    "estate-sale-vs-garage-sale-know-the-differences",
    "pros-and-cons-of-estate-sales",
    "how-to-increase-your-home-appraisal-value",
    "estate-auction-vs-estate-sale-pros-and-cons",
    "the-ultimate-guide-for-barbie-collector-buyers",
    "how-to-plan-estate-sale",
]

LINK_BLOCK = f"""<!-- {MARKER} -->
<h3><strong>Related Tampa Bay Estate Services</strong></h3>
<ul>
  <li><a href="/pages/estate-cleanout-services">Estate sale organizer &amp; full-service estate cleanout</a></li>
  <li><a href="/pages/personal-property-appraisal">Tampa personal property appraisers</a></li>
  <li><a href="/pages/downsizing-moving-sales">Tampa Bay downsizing specialist services</a></li>
  <li><a href="/pages/estate-sale-palm-harbor-pinellas-county">Estate sales Palm Harbor &amp; Pinellas County</a></li>
  <li><a href="/pages/tarpon-springs-estate-sale-in-woodfield">Estate sales in Tarpon Springs</a></li>
  <li><a href="/pages/estate-sale-citrus-county">Estate sales near me — Citrus County</a></li>
  <li><a href="/pages/fees-products">Estate sale fees &amp; pricing</a></li>
  <li><a href="/pages/faqs">Estate sale FAQs</a></li>
</ul>
<!-- /{MARKER} -->"""


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

    by_handle = {}
    next_url = f"{BASE}/blogs/{BLOG_ID}/articles.json?limit=250&fields=id,handle"
    while next_url:
        r = _retry(httpx.get, next_url, headers=H, timeout=30)
        for a in r.json().get("articles", []):
            by_handle[a["handle"]] = a["id"]
        next_url = None
        for part in r.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
        time.sleep(0.3)
    print(f"[a4] resolved {len(by_handle)} article handles")

    for handle in TARGETS:
        aid = by_handle.get(handle)
        if not aid:
            print(f"  [skip] {handle} not found"); continue
        art = _retry(httpx.get, f"{BASE}/blogs/{BLOG_ID}/articles/{aid}.json",
                     headers=H, timeout=30).json()["article"]
        body = art["body_html"] or ""
        if MARKER in body:
            print(f"  [skip] {handle} already has {MARKER}"); continue
        new_body = body.rstrip() + "\n" + LINK_BLOCK + "\n"
        r = _retry(httpx.put, f"{BASE}/blogs/{BLOG_ID}/articles/{aid}.json",
                   headers=H, timeout=60,
                   json={"article": {"id": aid, "body_html": new_body}})
        r.raise_for_status()
        print(f"  [ok] {handle}: +{len(new_body)-len(body)} chars")
        time.sleep(0.6)


if __name__ == "__main__":
    main()
