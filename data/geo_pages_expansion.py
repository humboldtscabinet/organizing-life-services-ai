"""Geo-landing page expansion — create/expand 6 city pages with unique
~600-word body, title/meta, and LocalBusiness JSON-LD.

Strategy:
  - CREATE 4 new pages: estate-sale-st-petersburg-florida, estate-sale-largo-florida,
    estate-sale-new-port-richey-florida, estate-sale-wesley-chapel-florida
  - EXPAND 2 thin existing pages: estate-sale-clearwater-florida (1564 chars),
    estate-sale-dunedin-florida (1190 chars) by appending a content block.

All edits are idempotent via marker GEO-<SHORT>-V1.
"""
import os
import sys
import time
import httpx

STORE = os.getenv("SHOPIFY_STORE"); CID = os.getenv("SHOPIFY_CLIENT_ID")
CS = os.getenv("SHOPIFY_CLIENT_SECRET"); API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")

PHONE = "(727) 542-6028"
PHONE_E164 = "+17275426028"
ORG_NAME = "Organizing Life Services"
SITE = "https://organizinglifeservices.com"

# Each city: (handle, action, title_tag, desc_tag, h1, city_label, county,
#             unique_intro, neighborhoods)
CITIES = [
    {
        "handle": "estate-sale-st-petersburg-florida",
        "action": "create",
        "title": "Estate Sales St. Petersburg, FL | Full-Service Liquidators",
        "desc": "Estate sales in St. Petersburg, FL run by Organizing Life Services. Pricing, staging, marketing, and sale-day staffing for Pinellas County homes. Call (727) 542-6028.",
        "h1": "Estate Sales in St. Petersburg, Florida",
        "city": "St. Petersburg",
        "county": "Pinellas County",
        "neighborhoods": ["Snell Isle", "Old Northeast", "Coquina Key", "Tyrone", "Tierra Verde", "Pinellas Point", "Crescent Lake", "Shore Acres"],
    },
    {
        "handle": "estate-sale-largo-florida",
        "action": "create",
        "title": "Estate Sales Largo, FL | Pinellas County Liquidators",
        "desc": "Professional estate sales in Largo, FL. Organizing Life Services manages pricing, staging, marketing, sale-day staffing & cleanout. Call (727) 542-6028.",
        "h1": "Estate Sales in Largo, Florida",
        "city": "Largo",
        "county": "Pinellas County",
        "neighborhoods": ["Belleair Bluffs", "Indian Rocks Beach", "Seminole", "Imperial Park", "East Bay", "Harbor Bluffs"],
    },
    {
        "handle": "estate-sale-new-port-richey-florida",
        "action": "create",
        "title": "Estate Sales New Port Richey, FL | Pasco County Pros",
        "desc": "Estate sales in New Port Richey, FL by Organizing Life Services. Full-service pricing, staging, marketing & cleanout for Pasco County homes. (727) 542-6028.",
        "h1": "Estate Sales in New Port Richey, Florida",
        "city": "New Port Richey",
        "county": "Pasco County",
        "neighborhoods": ["Gulf Harbors", "Jasmine Lakes", "Trinity", "Seven Springs", "Heritage Lake", "Bear Creek"],
    },
    {
        "handle": "estate-sale-wesley-chapel-florida",
        "action": "create",
        "title": "Estate Sales Wesley Chapel, FL | Pasco County Liquidators",
        "desc": "Estate sales in Wesley Chapel, FL run by Organizing Life Services. Pricing, staging, marketing & cleanout for Pasco County homes. Call (727) 542-6028.",
        "h1": "Estate Sales in Wesley Chapel, Florida",
        "city": "Wesley Chapel",
        "county": "Pasco County",
        "neighborhoods": ["Seven Oaks", "Meadow Pointe", "Lexington Oaks", "Bridgewater", "Saddlebrook", "Watergrass"],
    },
    {
        "handle": "estate-sale-clearwater-florida",
        "action": "expand",
        "title": "Estate Sales Clearwater, FL | Pinellas County Pros",
        "desc": "Estate sales in Clearwater, FL by Organizing Life Services. Full-service pricing, staging, marketing, sale-day staffing & cleanout. Call (727) 542-6028.",
        "h1": None,
        "city": "Clearwater",
        "county": "Pinellas County",
        "neighborhoods": ["Clearwater Beach", "Island Estates", "Belleair", "Sand Key", "Countryside", "Morningside", "Harbor Oaks"],
    },
    {
        "handle": "estate-sale-dunedin-florida",
        "action": "expand",
        "title": "Estate Sales Dunedin, FL | Pinellas County Liquidators",
        "desc": "Professional estate sales in Dunedin, FL. Organizing Life Services manages pricing, staging, marketing & cleanout. Call (727) 542-6028 for a free quote.",
        "h1": None,
        "city": "Dunedin",
        "county": "Pinellas County",
        "neighborhoods": ["Honeymoon Island area", "Curlew Landings", "Spanish Trails", "Highland Woods", "Brae Moor", "Patricia Estates"],
    },
]


def build_body(spec, is_new=True):
    """Build idempotent content block (full body for new pages, append block for expand)."""
    city = spec["city"]; county = spec["county"]
    neighborhoods = spec["neighborhoods"]; h1 = spec["h1"]
    marker = f"GEO-{spec['handle'].upper().replace('-', '_')[:40]}-V1"
    hood_list = "".join(f"<li>{n}</li>" for n in neighborhoods)
    hood_inline = ", ".join(neighborhoods[:-1]) + f", and {neighborhoods[-1]}"

    h1_html = f"<h1><strong>{h1}</strong></h1>\n" if h1 else ""

    schema = (
        '<script type="application/ld+json">{'
        f'"@context":"https://schema.org","@type":"LocalBusiness",'
        f'"name":"{ORG_NAME} — {city} Estate Sales",'
        f'"telephone":"{PHONE_E164}",'
        f'"url":"{SITE}/pages/{spec["handle"]}",'
        f'"areaServed":[{{"@type":"City","name":"{city}"}},{{"@type":"AdministrativeArea","name":"{county}"}}],'
        f'"serviceType":["Estate Sale","Estate Liquidation","Estate Cleanout","Personal Property Appraisal","Downsizing"],'
        '"priceRange":"$$"'
        '}</script>'
    )

    block = f"""<!-- {marker} -->
{h1_html}<p>Looking for a trusted <strong>estate sale company in {city}, Florida</strong>? Organizing Life Services has been producing professionally managed estate sales across {county} since 2010. We handle the full process — sorting, pricing, staging, photography, public marketing, sale-day staffing, payment processing, and post-sale donation pickup — so families in {city} can liquidate a home in one weekend without the stress of doing it themselves.</p>

<h2>Why {city} Families Choose Organizing Life Services</h2>
<p>Every {city} estate sale we produce is publicly listed on EstateSales.net and EstateSales.org 5–7 days before opening day, with a full photo gallery so local buyers can plan their visit. Our pricing comes from 14+ years of {county} comparable-sales data, fine-art and antiques expertise from a former New York City auction house, and ongoing reference to live auction results — so your items sell at the right number on the right day. Sale weekends typically gross several thousand dollars more than a DIY yard sale, and unsold items are donated and hauled off as part of the service.</p>

<h2>{city} Neighborhoods We Serve</h2>
<p>We routinely produce estate sales in {hood_inline}, and every other {city} neighborhood. Whether the home is a waterfront estate, a 55+ community villa, a townhome, or a small condo, our team scales staffing up or down to match the inventory and pace expected.</p>
<ul>{hood_list}</ul>

<h2>What We Handle for Every {city} Estate Sale</h2>
<ul>
<li><strong>Free in-home consultation</strong> — we walk the property, review inventory, and quote commission terms in writing.</li>
<li><strong>Sorting &amp; staging</strong> — every room is set up for buyer flow, with clear sight lines and grouped categories.</li>
<li><strong>Pricing &amp; research</strong> — antiques, fine art, jewelry, sterling silver, coins, firearms, mid-century modern furniture, and collectibles each get specialist attention.</li>
<li><strong>Public marketing</strong> — EstateSales.net and EstateSales.org listings, social posts, and our buyer email list of 5,000+ Tampa Bay collectors.</li>
<li><strong>Sale-day staffing</strong> — cashiers, floor staff, security, and parking management on premises.</li>
<li><strong>Post-sale cleanout</strong> — donation pickup, hauling, and broom-clean turnover for the realtor.</li>
</ul>

<h2>Beyond Estate Sales — Full {city} Estate Services</h2>
<p>If a traditional estate sale is not the right fit (small home, gated community without public-sale access, or a tight timeline) we also offer <a href="/pages/estate-cleanout-services">full-service estate cleanout</a>, <a href="/pages/personal-property-appraisal">written personal property appraisals</a>, and <a href="/pages/downsizing-moving-sales">downsizing and moving sale services</a> across {city} and surrounding {county} communities.</p>

<h2>Get a Free {city} Estate Sale Quote</h2>
<p>Call <a href="tel:{PHONE_E164}"><strong>{PHONE}</strong></a> or use our <a href="/pages/contact-us">contact form</a> to schedule a free in-home consultation. Most {city} estate sales can be staged, marketed, and conducted within 3–4 weeks of the first call. We also serve nearby Pinellas, Pasco, Hillsborough, Hernando, and Citrus county communities — see our <a href="/pages/estate-sale-companies-near-me">full service-area page</a>.</p>

{schema}
<!-- /{marker} -->"""
    return block, marker


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


def upsert_metafield(BASE, H, page_id, key, value):
    payload = {"metafield": {"namespace": "global", "key": key, "value": value,
                             "type": "single_line_text_field"}}
    r = _retry(httpx.post, f"{BASE}/pages/{page_id}/metafields.json",
               headers=H, json=payload, timeout=30)
    if r.status_code in (200, 201):
        return "created"
    # try existing
    existing = _retry(httpx.get, f"{BASE}/pages/{page_id}/metafields.json",
                      headers=H, timeout=30).json().get("metafields", [])
    for m in existing:
        if m.get("namespace") == "global" and m.get("key") == key:
            r2 = _retry(httpx.put, f"{BASE}/metafields/{m['id']}.json",
                        headers=H, json={"metafield": {"id": m["id"], "value": value,
                                                       "type": "single_line_text_field"}},
                        timeout=30)
            r2.raise_for_status()
            return "updated"
    raise RuntimeError(f"meta upsert failed: {r.status_code} {r.text}")


def main():
    if not all([STORE, CID, CS]): sys.exit("Missing SHOPIFY creds")
    tok = httpx.post(f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CID, "client_secret": CS, "grant_type": "client_credentials"},
        timeout=30).json()["access_token"]
    H = {"X-Shopify-Access-Token": tok, "Content-Type": "application/json"}
    BASE = f"https://{STORE}.myshopify.com/admin/api/{API_VER}"

    existing = _retry(httpx.get, f"{BASE}/pages.json?limit=250", headers=H, timeout=30).json()["pages"]
    by_handle = {p["handle"]: p for p in existing}

    for spec in CITIES:
        h = spec["handle"]; action = spec["action"]
        block, marker = build_body(spec)
        page = by_handle.get(h)

        if action == "create":
            if page:
                # already exists — switch to expand
                body = page.get("body_html") or ""
                if marker in body:
                    print(f"  [skip] {h} already has {marker}"); 
                else:
                    new_body = body.rstrip() + "\n" + block + "\n"
                    r = _retry(httpx.put, f"{BASE}/pages/{page['id']}.json", headers=H,
                               timeout=60, json={"page": {"id": page["id"], "body_html": new_body}})
                    r.raise_for_status()
                    print(f"  [upd] {h}: +{len(new_body)-len(body)} chars")
                pid = page["id"]
            else:
                r = _retry(httpx.post, f"{BASE}/pages.json", headers=H, timeout=60,
                           json={"page": {"title": spec["h1"], "handle": h,
                                          "body_html": block, "published": True}})
                if r.status_code not in (200, 201):
                    print(f"  [FAIL CREATE] {h}: {r.status_code} {r.text[:200]}"); continue
                pid = r.json()["page"]["id"]
                print(f"  [new] {h}: created id={pid} ({len(block)} chars)")
                time.sleep(0.6)
        else:  # expand
            if not page:
                print(f"  [skip] {h} doesn't exist — can't expand"); continue
            body = page.get("body_html") or ""
            if marker in body:
                print(f"  [skip] {h} already has {marker}")
            else:
                new_body = body.rstrip() + "\n" + block + "\n"
                r = _retry(httpx.put, f"{BASE}/pages/{page['id']}.json", headers=H,
                           timeout=60, json={"page": {"id": page["id"], "body_html": new_body}})
                r.raise_for_status()
                print(f"  [exp] {h}: +{len(new_body)-len(body)} chars (now {len(new_body)})")
            pid = page["id"]

        # metafields
        s1 = upsert_metafield(BASE, H, pid, "title_tag", spec["title"])
        time.sleep(0.6)
        s2 = upsert_metafield(BASE, H, pid, "description_tag", spec["desc"])
        time.sleep(0.6)
        print(f"        title_tag: {s1} | description_tag: {s2}")


if __name__ == "__main__":
    main()
