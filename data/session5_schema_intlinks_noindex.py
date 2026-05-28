"""Session-5: enrich LocalBusiness JSON-LD, add A5 homepage intlinks to new
geo pages, and implement noindex via per-page metafield for 16 dead past-sale
pages.

Three changes:
  1. Theme: replace the existing static LocalBusiness JSON-LD block with an
     enriched version (marker SCHEMA-LB-V2) — adds @id, image/logo, priceRange,
     sameAs (FB + IG), areaServed (multiple cities), openingHoursSpecification.
  2. Theme: append a second homepage intlinks block (marker SEO-INTLINKS-A5-V1)
     with exact-match anchors to all 6 new/expanded geo pages.
  3. Theme: add a per-page robots meta override (marker SEO-ROBOTS-V1) reading
     page.metafields.seo.robots. Then push `seo.robots="noindex,follow"` to the
     16 empty past-event pages (body < 100 chars, no inbound conversion value).

Idempotent — each insertion skips itself if its marker is already present.
Snapshots existing theme.liquid before mutation.
"""
import os
import sys
import time
from pathlib import Path

import httpx

STORE = os.getenv('SHOPIFY_STORE'); CID = os.getenv('SHOPIFY_CLIENT_ID')
CS = os.getenv('SHOPIFY_CLIENT_SECRET'); API = os.getenv('SHOPIFY_API_VERSION', '2024-10')
THEME = 153690210458
SNAPSHOT = Path('data/audit_output/theme_layout_snapshot_pre_session5.liquid')

# 16 empty past-event pages to noindex,follow (body <100 chars based on prior audit)
NOINDEX_HANDLES = [
    "13925-pathfinder-drive-tampa-florida",
    "613-severs-landing-palm-harbor-fl-estate-sale-part-1",
    "613-severs-landing-palm-harbor-fl-estate-sale-part-2",
    "estate-sale-safety-harbor-florida-pinellas-county-34695",
    "estate-sale-westchase-tampa-fl-33626-hillsborough-county",
    "highland-lakes-estate-sale",
    "lansbrook-myrtle-point-estate-sale-part-two",
    "myrtle-point-estate-sale",
    "moon-lake-estate-sale",
    "new-port-richey-appointment-only-sale-april-2024",
    "new-port-richey-sale-huge-do-not-miss-this-one",
    "odessa-estate-sale-june-2024",
    "organizing-life-estate-sale-company-successful-sales",
    "pimberton-drive-hudson",
    "pinellas-park-estate-sale-in-the-mainlands-9841-41st-street-north",
    "successful-high-quality-estate-sale-ridge-lane-palm-harbor-pinellas-county-florida",
    "vintage-coca-cola-estate-sale-in-dunedin-florida-march-2023",
    "vintage-palm-harbor-coming-up-soon",
]

ENRICHED_LB = """<!-- SCHEMA-LB-V2 -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "@id": "https://organizinglifeservices.com/#organization",
  "name": "Organizing Life Services",
  "alternateName": "OLS Estate Sales",
  "description": "Tampa Bay's most trusted full-service estate sale company since 2010. Pricing, staging, marketing, sale-day staffing, appraisals, downsizing, and post-sale cleanout across Pinellas, Pasco, Hillsborough, Hernando, and Citrus counties.",
  "url": "https://organizinglifeservices.com/",
  "logo": "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_LOGO_PNG.png",
  "image": "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_LOGO_PNG.png",
  "telephone": "+17275426028",
  "email": "OrganizingLife@Hotmail.Com",
  "priceRange": "$$",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "E LAKE RD S",
    "addressLocality": "Palm Harbor",
    "addressRegion": "FL",
    "postalCode": "34685",
    "addressCountry": "US"
  },
  "areaServed": [
    {"@type": "City", "name": "Palm Harbor"},
    {"@type": "City", "name": "Tarpon Springs"},
    {"@type": "City", "name": "Clearwater"},
    {"@type": "City", "name": "Dunedin"},
    {"@type": "City", "name": "St. Petersburg"},
    {"@type": "City", "name": "Largo"},
    {"@type": "City", "name": "Tampa"},
    {"@type": "City", "name": "New Port Richey"},
    {"@type": "City", "name": "Wesley Chapel"},
    {"@type": "AdministrativeArea", "name": "Pinellas County"},
    {"@type": "AdministrativeArea", "name": "Pasco County"},
    {"@type": "AdministrativeArea", "name": "Hillsborough County"},
    {"@type": "AdministrativeArea", "name": "Hernando County"},
    {"@type": "AdministrativeArea", "name": "Citrus County"}
  ],
  "sameAs": [
    "https://www.facebook.com/profile.php?id=100063703233651",
    "https://www.instagram.com/organizing_life_services"
  ],
  "openingHoursSpecification": [
    {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "opens": "09:00", "closes": "17:00"},
    {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Saturday"], "opens": "09:00", "closes": "15:00"}
  ],
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "Estate Sale & Liquidation Services",
    "itemListElement": [
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Estate Sales"}},
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Estate Cleanout & Liquidation"}},
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Personal Property Appraisals"}},
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Downsizing & Moving Sales"}},
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Senior Transition Services"}}
    ]
  }
}
</script>
<!-- /SCHEMA-LB-V2 -->"""

INTLINKS_A5 = """    {%- if template.name == 'index' -%}
    {%- comment -%} SEO-INTLINKS-A5-V1: geo + service anchors {%- endcomment -%}
    <section class="ols-home-geo-intlinks" aria-label="Estate sale locations" style="max-width:1200px;margin:30px auto;padding:24px 16px;border-top:1px solid #eee;font-size:15px;line-height:1.6;color:#333;">
      <h2 style="font-size:18px;margin:0 0 12px;font-weight:600;">Estate Sales Near You — Tampa Bay &amp; Beyond</h2>
      <p style="margin:0 0 8px;">Organizing Life Services produces professionally managed estate sales across the Greater Tampa Bay Area, including <a href="/pages/estate-sale-palm-harbor-pinellas-county">estate sales Palm Harbor</a>, <a href="/pages/tarpon-springs-estate-sale-in-woodfield">estate sales Tarpon Springs</a>, <a href="/pages/estate-sale-clearwater-florida">estate sales Clearwater</a>, <a href="/pages/estate-sale-dunedin-florida">estate sales Dunedin</a>, <a href="/pages/estate-sale-st-petersburg-florida">estate sales St. Petersburg</a>, <a href="/pages/estate-sale-largo-florida">estate sales Largo</a>, <a href="/pages/estate-sale-tampa-hillsborough-county">estate sales Tampa</a>, <a href="/pages/estate-sale-new-port-richey-florida">estate sales New Port Richey</a>, <a href="/pages/estate-sale-wesley-chapel-florida">estate sales Wesley Chapel</a>, <a href="/pages/estate-sale-pasco-county">Pasco &amp; Hernando County</a>, and <a href="/pages/estate-sale-citrus-county">Citrus County</a>.</p>
      <p style="margin:0;">We also offer Tampa Bay <a href="/pages/personal-property-appraisal">personal property appraisers</a>, <a href="/pages/downsizing-moving-sales">downsizing specialist services</a>, and full-service <a href="/pages/estate-cleanout-services">estate cleanout</a> &mdash; see our <a href="/pages/faqs">frequently asked questions</a> to learn more.</p>
    </section>
    {%- endif -%}"""

ROBOTS_SNIPPET = """    {%- comment -%} SEO-ROBOTS-V1: per-page noindex override via page.metafields.seo.robots {%- endcomment -%}
    {%- if page and page.metafields.seo.robots != blank -%}
    <meta name="robots" content="{{ page.metafields.seo.robots | escape }}">
    {%- endif -%}"""


def _retry(fn, *a, **k):
    for i in range(6):
        try:
            r = fn(*a, **k)
            if hasattr(r, 'status_code') and r.status_code == 429:
                time.sleep(float(r.headers.get('Retry-After', 2 ** i))); continue
            return r
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            time.sleep(2 ** i)
    raise RuntimeError('retries exhausted')


def patch_theme(B, H):
    r = _retry(httpx.get, f'{B}/themes/{THEME}/assets.json?asset[key]=layout/theme.liquid',
               headers=H, timeout=30)
    body = r.json()['asset']['value']

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    if not SNAPSHOT.exists():
        SNAPSHOT.write_text(body)
        print(f'  [snap] {SNAPSHOT} ({len(body)} chars)')

    new = body
    changes = []

    # 1. Replace LocalBusiness block (matches the existing static one)
    if 'SCHEMA-LB-V2' in new:
        print('  [skip] SCHEMA-LB-V2 already present')
    else:
        marker_start = '<script type="application/ld+json">\n{\n  "@context": "http://schema.org",\n  "@type": "LocalBusiness",'
        idx = new.find(marker_start)
        if idx < 0:
            print('  [warn] could not locate existing LocalBusiness JSON-LD — appending new one in head')
            head_end = new.find('</head>')
            new = new[:head_end] + ENRICHED_LB + '\n  ' + new[head_end:]
            changes.append('SCHEMA-LB-V2 (appended)')
        else:
            end_marker = '</script>'
            end_idx = new.find(end_marker, idx) + len(end_marker)
            new = new[:idx] + ENRICHED_LB + new[end_idx:]
            changes.append('SCHEMA-LB-V2 (replaced legacy LocalBusiness)')

    # 2. Add A5 intlinks block — insert before existing SEO-INTLINKS-V1 if exists, else before {%- endif -%} of index
    if 'SEO-INTLINKS-A5-V1' in new:
        print('  [skip] SEO-INTLINKS-A5-V1 already present')
    else:
        anchor = "{%- comment -%} SEO-INTLINKS-V1: estate-cleanout-services anchors {%- endcomment -%}"
        # Find the wrapping {%- if template.name == 'index' -%} BEFORE the anchor — insert our A5 block after that opening tag's matching {%- endif -%}
        # Simpler: find the {%- endif -%} that closes the V1 section and insert immediately after it
        v1_idx = new.find(anchor)
        if v1_idx < 0:
            print('  [warn] SEO-INTLINKS-V1 anchor not found, inserting before {{ content_for_layout }} fallback')
            # fallback: insert before closing </body>
            insert_at = new.find('</body>')
            new = new[:insert_at] + INTLINKS_A5 + '\n    ' + new[insert_at:]
        else:
            # walk forward to first '{%- endif -%}' AFTER v1_idx
            end_if = new.find('{%- endif -%}', v1_idx)
            insert_at = end_if + len('{%- endif -%}')
            new = new[:insert_at] + '\n' + INTLINKS_A5 + new[insert_at:]
        changes.append('SEO-INTLINKS-A5-V1 (homepage geo block)')

    # 3. Add robots snippet in head (before </head>)
    if 'SEO-ROBOTS-V1' in new:
        print('  [skip] SEO-ROBOTS-V1 already present')
    else:
        head_end = new.find('</head>')
        new = new[:head_end] + ROBOTS_SNIPPET + '\n  ' + new[head_end:]
        changes.append('SEO-ROBOTS-V1 (per-page robots meta override)')

    if not changes:
        print('  [noop] no theme changes needed')
        return

    print(f'  changes: {changes}')
    print(f'  theme.liquid: {len(body)} -> {len(new)} chars')
    r = _retry(httpx.put, f'{B}/themes/{THEME}/assets.json', headers=H, timeout=60,
               json={'asset': {'key': 'layout/theme.liquid', 'value': new}})
    r.raise_for_status()
    print('  [ok] theme.liquid updated')


def push_noindex(B, H):
    pages = _retry(httpx.get, f'{B}/pages.json?limit=250', headers=H, timeout=30).json()['pages']
    bh = {p['handle']: p for p in pages}
    print(f'\n[noindex] pushing seo.robots=noindex,follow to {len(NOINDEX_HANDLES)} pages')
    for h in NOINDEX_HANDLES:
        p = bh.get(h)
        if not p:
            print(f'  [skip] {h} not found'); continue
        # Check existing
        mfs = _retry(httpx.get, f'{B}/pages/{p["id"]}/metafields.json',
                     headers=H, timeout=30).json().get('metafields', [])
        existing = next((m for m in mfs if m.get('namespace') == 'seo' and m.get('key') == 'robots'), None)
        if existing and existing.get('value') == 'noindex,follow':
            print(f'  [skip] {h} already noindex'); continue
        payload = {'metafield': {'namespace': 'seo', 'key': 'robots',
                                  'value': 'noindex,follow', 'type': 'single_line_text_field'}}
        if existing:
            r = _retry(httpx.put, f'{B}/metafields/{existing["id"]}.json', headers=H, timeout=30,
                       json={'metafield': {'id': existing['id'], 'value': 'noindex,follow',
                                            'type': 'single_line_text_field'}})
        else:
            r = _retry(httpx.post, f'{B}/pages/{p["id"]}/metafields.json',
                       headers=H, timeout=30, json=payload)
        r.raise_for_status()
        print(f'  [ok] {h}')
        time.sleep(0.4)


def main():
    if not all([STORE, CID, CS]): sys.exit('Missing SHOPIFY creds')
    tok = httpx.post(f'https://{STORE}.myshopify.com/admin/oauth/access_token',
        json={'client_id': CID, 'client_secret': CS, 'grant_type': 'client_credentials'},
        timeout=30).json()['access_token']
    H = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    B = f'https://{STORE}.myshopify.com/admin/api/{API}'
    patch_theme(B, H)
    push_noindex(B, H)


if __name__ == '__main__':
    main()
