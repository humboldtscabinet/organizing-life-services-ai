"""Session-6: A) sitemap resubmit + URL inspection recrawl pings,
B) robots.txt + GBP NAP audit, C) round-5 geo metafield standardization.

Idempotent — each section detects no-op and skips.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from google.oauth2 import service_account
from googleapiclient.discovery import build

SITE = 'https://organizinglifeservices.com/'
SITEMAP = 'https://organizinglifeservices.com/sitemap.xml'
STORE = os.getenv('SHOPIFY_STORE'); CID = os.getenv('SHOPIFY_CLIENT_ID')
CS = os.getenv('SHOPIFY_CLIENT_SECRET'); API = os.getenv('SHOPIFY_API_VERSION', '2024-10')
SA = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'credentials/google-service-account.json')

OUT = Path('data/audit_output'); OUT.mkdir(parents=True, exist_ok=True)

URLS_TO_INSPECT = [
    'https://organizinglifeservices.com/',
    'https://organizinglifeservices.com/pages/estate-sale-clearwater-florida',
    'https://organizinglifeservices.com/pages/estate-sale-dunedin-florida',
    'https://organizinglifeservices.com/pages/estate-sale-st-petersburg-florida',
    'https://organizinglifeservices.com/pages/estate-sale-largo-florida',
    'https://organizinglifeservices.com/pages/estate-sale-new-port-richey-florida',
    'https://organizinglifeservices.com/pages/estate-sale-wesley-chapel-florida',
]

# Round-5 geo metas — standardized: plural "Estate Sales", city+region+FL, phone CTA where length permits
# Format: (handle, page_id, title_tag, description_tag)
GEO_METAS = {
    'estate-sale-palm-harbor-pinellas-county':  ('Estate Sales Palm Harbor, FL | Pinellas County Liquidators',
                                                  'Estate sales in Palm Harbor, FL by Organizing Life Services. Pricing, staging, marketing & cleanout for Pinellas County homes. Call (727) 542-6028.'),
    'tarpon-springs-estate-sale-in-woodfield':  ('Estate Sales Tarpon Springs, FL | Woodfield & Sponge Docks',
                                                  'Estate sales across Tarpon Springs FL — Woodfield, Sponge Docks, Whitcomb Bayou & Riverside Drive. Full-service liquidation. Call (727) 542-6028.'),
    'estate-sale-clearwater-florida':           ('Estate Sales Clearwater, FL | Pinellas County Pros',
                                                  'Estate sales in Clearwater, FL by Organizing Life Services. Full-service pricing, staging, marketing, sale-day staffing & cleanout. Call (727) 542-6028.'),
    'estate-sale-dunedin-florida':              ('Estate Sales Dunedin, FL | Pinellas County Liquidators',
                                                  'Professional estate sales in Dunedin, FL. Organizing Life Services manages pricing, staging, marketing & cleanout. Call (727) 542-6028 for a free quote.'),
    'estate-sale-st-petersburg-florida':        ('Estate Sales St. Petersburg, FL | Full-Service Liquidators',
                                                  'Estate sales in St. Petersburg, FL by Organizing Life Services. Pricing, staging, marketing & sale-day staffing for Pinellas County. Call (727) 542-6028.'),
    'estate-sale-largo-florida':                ('Estate Sales Largo, FL | Pinellas County Liquidators',
                                                  'Professional estate sales in Largo, FL. Organizing Life Services manages pricing, staging, marketing, sale-day staffing & cleanout. Call (727) 542-6028.'),
    'estate-sale-tampa-hillsborough-county':    ('Estate Sales Tampa, FL | Hillsborough County Liquidators',
                                                  'Estate sales in Tampa, FL by Organizing Life Services. Full-service pricing, staging, marketing & cleanout across Hillsborough County. Call (727) 542-6028.'),
    'estate-sale-new-port-richey-florida':      ('Estate Sales New Port Richey, FL | Pasco County Pros',
                                                  'Estate sales in New Port Richey, FL by Organizing Life Services. Full-service pricing, staging, marketing & cleanout for Pasco County. Call (727) 542-6028.'),
    'estate-sale-wesley-chapel-florida':        ('Estate Sales Wesley Chapel, FL | Pasco County Liquidators',
                                                  'Estate sales in Wesley Chapel, FL by Organizing Life Services. Pricing, staging, marketing & cleanout for Pasco County homes. Call (727) 542-6028.'),
    'estate-sale-pasco-county':                 ('Estate Sales Pasco & Hernando County, FL | Free Quote',
                                                  'Professional estate sales across Pasco & Hernando County, FL. Pricing, staging, marketing & cleanout by Organizing Life Services. Call (727) 542-6028.'),
    'estate-sale-citrus-county':                ('Estate Sales Citrus County, FL | Inverness & Crystal River',
                                                  'Estate sales across Citrus County — Inverness, Crystal River, Homosassa, Beverly Hills & Lecanto. Full-service liquidation. Call (727) 542-6028.'),
}


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


# ---------- A) Sitemap resubmit + URL inspection ----------
def section_a():
    print('\n=== A) GSC sitemap resubmit + URL inspection ===')
    creds = service_account.Credentials.from_service_account_file(
        SA, scopes=['https://www.googleapis.com/auth/webmasters'])
    gsc = build('searchconsole', 'v1', credentials=creds, cache_discovery=False)

    # Resubmit sitemap
    try:
        gsc.sitemaps().submit(siteUrl=SITE, feedpath=SITEMAP).execute()
        print(f'  [ok] sitemap resubmitted: {SITEMAP}')
    except Exception as e:
        print(f'  [warn] sitemap submit: {e}')

    # Inspect URLs (queues for recrawl indirectly + reports current status)
    print(f'  inspecting {len(URLS_TO_INSPECT)} URLs...')
    rows = []
    for u in URLS_TO_INSPECT:
        try:
            r = gsc.urlInspection().index().inspect(body={
                'inspectionUrl': u, 'siteUrl': SITE,
            }).execute()
            ir = r.get('inspectionResult', {})
            idx = ir.get('indexStatusResult', {})
            verdict = idx.get('verdict', '?')
            cov = idx.get('coverageState', '?')
            last_crawl = idx.get('lastCrawlTime', '?')
            print(f'  {verdict:8} {cov[:40]:40} {last_crawl[:10]} {u}')
            rows.append({'url': u, 'verdict': verdict, 'coverage': cov, 'lastCrawl': last_crawl})
        except Exception as e:
            print(f'  [err] {u}: {e}')
            rows.append({'url': u, 'error': str(e)})
        time.sleep(0.5)

    (OUT / 'session6_url_inspection.json').write_text(json.dumps(rows, indent=2))


# ---------- B) robots.txt + NAP audit ----------
def section_b():
    print('\n=== B) robots.txt + NAP audit ===')
    # Fetch robots.txt
    r = httpx.get('https://organizinglifeservices.com/robots.txt', timeout=15)
    robots = r.text
    print(f'  robots.txt: {len(robots)} chars, HTTP {r.status_code}')

    # Parse Disallow rules under User-agent: *
    in_star = False
    disallows = []
    for line in robots.splitlines():
        s = line.strip()
        if s.lower().startswith('user-agent:'):
            in_star = (s.split(':', 1)[1].strip() == '*')
        elif in_star and s.lower().startswith('disallow:'):
            d = s.split(':', 1)[1].strip()
            if d: disallows.append(d)

    # Check our noindexed pages aren't accidentally disallowed
    noindex_paths = [
        '/pages/highland-lakes-estate-sale',
        '/pages/13925-pathfinder-drive-tampa-florida',
        '/pages/myrtle-point-estate-sale',
        '/pages/estate-sale-clearwater-florida',
        '/pages/estate-sale-palm-harbor-pinellas-county',
    ]
    print(f'  Disallow rules under *: {len(disallows)} total')
    bad = []
    for p in noindex_paths:
        for d in disallows:
            # naive prefix match
            if d.endswith('*'): pat = d[:-1]
            else: pat = d
            if pat and p.startswith(pat):
                bad.append((p, d))
    if bad:
        print('  [WARN] noindexed pages also Disallowed (link equity loss):')
        for p, d in bad: print(f'    {p}  vs  Disallow: {d}')
    else:
        print('  [ok] none of the noindexed pages are Disallow-blocked')

    # NAP — pull schema from homepage and print for user verification vs GBP
    print('\n  NAP from live homepage JSON-LD (for GBP verification):')
    hp = httpx.get(SITE, timeout=15).text
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', hp, re.S):
        try:
            j = json.loads(block.strip())
        except Exception:
            continue
        if (isinstance(j, dict) and 'LocalBusiness' in str(j.get('@type', ''))):
            print(f'    name:      {j.get("name")}')
            print(f'    phone:     {j.get("telephone")}')
            print(f'    email:     {j.get("email")}')
            addr = j.get('address', {})
            print(f'    address:   {addr.get("streetAddress")}, {addr.get("addressLocality")}, '
                  f'{addr.get("addressRegion")} {addr.get("postalCode")}')
            print(f'    url:       {j.get("url")}')
            print(f'    sameAs:    {j.get("sameAs")}')
            print(f'    priceRange:{j.get("priceRange")}')
    print('  ACTION: manually cross-check NAP above against your GBP listing at')
    print('         https://business.google.com/ — phone/address must match EXACTLY.')


# ---------- C) Round-5 geo metafield standardization ----------
def section_c():
    print('\n=== C) Round-5 geo metafields ===')
    tok = httpx.post(f'https://{STORE}.myshopify.com/admin/oauth/access_token',
        json={'client_id': CID, 'client_secret': CS, 'grant_type': 'client_credentials'},
        timeout=30).json()['access_token']
    H = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    B = f'https://{STORE}.myshopify.com/admin/api/{API}'

    pages = _retry(httpx.get, f'{B}/pages.json?limit=250', headers=H, timeout=30).json()['pages']
    bh = {p['handle']: p for p in pages}

    changed = 0
    for h, (new_t, new_d) in GEO_METAS.items():
        p = bh.get(h)
        if not p:
            print(f'  [miss] {h}'); continue
        mfs = _retry(httpx.get, f'{B}/pages/{p["id"]}/metafields.json',
                     headers=H, timeout=30).json().get('metafields', [])
        cur = {m['key']: m for m in mfs if m.get('namespace') == 'global'}

        for key, val in (('title_tag', new_t), ('description_tag', new_d)):
            existing = cur.get(key)
            if existing and existing.get('value') == val:
                continue
            if existing:
                r = _retry(httpx.put, f'{B}/metafields/{existing["id"]}.json',
                           headers=H, timeout=30,
                           json={'metafield': {'id': existing['id'], 'value': val,
                                                'type': 'single_line_text_field'}})
            else:
                r = _retry(httpx.post, f'{B}/pages/{p["id"]}/metafields.json',
                           headers=H, timeout=30,
                           json={'metafield': {'namespace': 'global', 'key': key,
                                                'value': val, 'type': 'single_line_text_field'}})
            r.raise_for_status()
            changed += 1
            print(f'  [{key:>15}] {h}: {len(val)}c')
            time.sleep(0.4)
    print(f'  total field updates: {changed}')


def main():
    section_a()
    section_b()
    section_c()


if __name__ == '__main__':
    main()
