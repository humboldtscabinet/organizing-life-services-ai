"""Inject striking-distance H2 + targeted paragraph into 4 pages.

Each insertion is keyed by an idempotent HTML comment marker so reruns are safe.
Source data: data/audit_output/gsc_striking_distance_2026-05-28.json
"""
import os
import sys
import time
import httpx

STORE = os.getenv("SHOPIFY_STORE"); CID = os.getenv("SHOPIFY_CLIENT_ID")
CS = os.getenv("SHOPIFY_CLIENT_SECRET"); API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")

# (page handle, marker, html_block)
INSERTIONS = [
    (
        "estate-sale-citrus-county",
        "SD-ESNM-V1",
        """<!-- SD-ESNM-V1 -->
<h2><strong>Estate Sales Near Me in Citrus County</strong></h2>
<p>Looking for <strong>estate sales near me</strong> in Citrus County? Organizing Life Services hosts professionally managed estate sales in Inverness, Crystal River, Homosassa, Beverly Hills, and Lecanto. Each sale is publicly listed on EstateSales.net and EstateSales.org with full photo galleries 5-7 days in advance, so local buyers can preview inventory and plan their visit. Sales typically run Friday-Sunday, 9am-3pm, with discounted pricing on day three. Whether you're searching for antiques, mid-century furniture, tools, or estate jewelry, our Citrus County sales are the largest in the area — and you'll find current upcoming dates linked from our homepage every week.</p>
<!-- /SD-ESNM-V1 -->""",
    ),
    (
        "tarpon-springs-estate-sale-in-woodfield",
        "SD-ESTS-V1",
        """<!-- SD-ESTS-V1 -->
<h2><strong>Estate Sales in Tarpon Springs &amp; Pinellas County</strong></h2>
<p>Searching for <strong>estate sales in Tarpon Springs</strong>? Organizing Life Services produces estate sales across Tarpon Springs neighborhoods including Woodfield, Whitcomb Bayou, the Sponge Docks district, Riverside Drive waterfront homes, and East Lake. Our Tarpon Springs estate sales draw buyers from Pinellas, Pasco, and Hillsborough counties because we price competitively, photograph every item, and list publicly 5-7 days ahead. If you have a Tarpon Springs home to liquidate — whether a small condo or a 4,000-sq-ft estate — we handle sorting, staging, pricing, marketing, sale-day staffing, and post-sale donation pickup, so the home is ready for the realtor with one phone call.</p>
<!-- /SD-ESTS-V1 -->""",
    ),
    (
        "personal-property-appraisal",
        "SD-TPPA-V1",
        """<!-- SD-TPPA-V1 -->
<h2><strong>Tampa Personal Property Appraisers</strong></h2>
<p>Need <strong>Tampa personal property appraisers</strong> you can trust for insurance, estate, divorce, or IRS purposes? Organizing Life Services has appraised over 2,000 Tampa Bay estates since 2010. Our written appraisal reports include item-by-item fair market value, replacement cost, photographs, and provenance notes — and are accepted by all major insurance carriers and Florida probate courts. We appraise antiques, fine art, jewelry, sterling silver, Asian art, mid-century modern furniture, collectibles, firearms, coins, and full household contents. On-site appraisals across Hillsborough, Pinellas, Pasco, Hernando, and Citrus counties typically completed within 5 business days of inspection. Call for a quote or to schedule.</p>
<!-- /SD-TPPA-V1 -->""",
    ),
    (
        "downsizing-moving-sales",
        "SD-DSPC-V1",
        """<!-- SD-DSPC-V1 -->
<h2><strong>Tampa Bay Downsizing Specialist Services</strong></h2>
<p>As a Tampa Bay <strong>downsizing specialist</strong> serving Pinellas, Pasco, Hillsborough, Hernando, and Citrus counties since 2010, Organizing Life Services helps seniors and families transition from larger homes to smaller residences with minimal stress. Our downsizing services include in-home consultations, room-by-room sorting, "keep / sell / donate / discard" decision support, packing of keepsakes, hands-on estate sale or buyout liquidation of remaining items, charitable donation pickups, and broom-clean home turnover for the realtor. Whether you're moving to assisted living, a 55+ community, or a smaller family home, our downsizing specialist team handles every step on your timeline.</p>
<!-- /SD-DSPC-V1 -->""",
    ),
]


def _retry(fn, *a, **k):
    for i in range(6):
        try:
            r = fn(*a, **k)
            if hasattr(r, "status_code") and r.status_code == 429:
                w = float(r.headers.get("Retry-After", 2 ** i))
                time.sleep(w); continue
            return r
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            time.sleep(2 ** i)
    raise RuntimeError("retries exhausted")


def main():
    tok = httpx.post(f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CID, "client_secret": CS, "grant_type": "client_credentials"},
        timeout=30).json()["access_token"]
    H = {"X-Shopify-Access-Token": tok, "Content-Type": "application/json"}
    BASE = f"https://{STORE}.myshopify.com/admin/api/{API_VER}"

    pages = _retry(httpx.get, f"{BASE}/pages.json?limit=250", headers=H, timeout=30).json()["pages"]
    by_handle = {p["handle"]: p for p in pages}

    for handle, marker, block in INSERTIONS:
        page = by_handle.get(handle)
        if not page:
            print(f"  [skip] {handle} not found"); continue
        body = page.get("body_html") or ""
        if marker in body:
            print(f"  [skip] {handle} already has {marker}"); continue
        new_body = body.rstrip() + "\n" + block.strip() + "\n"
        r = _retry(httpx.put, f"{BASE}/pages/{page['id']}.json", headers=H, timeout=60,
                   json={"page": {"id": page["id"], "body_html": new_body}})
        r.raise_for_status()
        print(f"  [ok] {handle}: {len(body)} -> {len(new_body)} chars (+{len(new_body)-len(body)})")
        time.sleep(0.6)


if __name__ == "__main__":
    main()
