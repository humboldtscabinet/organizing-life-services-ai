"""Session-7: boost crawl-priority on 6 unindexed geo pages.

Plan:
  1. Append idempotent "Service Areas We Cover" block (marker SERVICE-AREAS-V1)
     to bottom of high-authority indexed pages: estate-cleanout-services + faqs.
     Each block links to all 11 geo pages.
  2. Append idempotent "Related Service Areas" cross-link block
     (marker GEO-CROSSLINKS-V1) to the body of ALL 11 geo pages. Each page links
     to the other 10. This (a) creates inbound links from indexed siblings to the
     6 unknown pages, (b) bumps `updated_at` so the sitemap lastmod refreshes.
  3. Resubmit sitemap to GSC + re-inspect the 6 previously-unknown URLs.

Idempotent — skips pages whose body already contains the marker.
"""
import os
import sys
import time
from pathlib import Path

import httpx
from google.oauth2 import service_account
from googleapiclient.discovery import build

STORE = os.getenv('SHOPIFY_STORE'); CID = os.getenv('SHOPIFY_CLIENT_ID')
CS = os.getenv('SHOPIFY_CLIENT_SECRET'); API = os.getenv('SHOPIFY_API_VERSION', '2024-10')
SA = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'credentials/google-service-account.json')
SITE = 'https://organizinglifeservices.com/'
SITEMAP = 'https://organizinglifeservices.com/sitemap.xml'

# (handle, anchor text)
GEO_ANCHORS = [
    ('estate-sale-palm-harbor-pinellas-county',  'Palm Harbor'),
    ('tarpon-springs-estate-sale-in-woodfield',  'Tarpon Springs'),
    ('estate-sale-clearwater-florida',           'Clearwater'),
    ('estate-sale-dunedin-florida',              'Dunedin'),
    ('estate-sale-st-petersburg-florida',        'St. Petersburg'),
    ('estate-sale-largo-florida',                'Largo'),
    ('estate-sale-tampa-hillsborough-county',    'Tampa'),
    ('estate-sale-new-port-richey-florida',      'New Port Richey'),
    ('estate-sale-wesley-chapel-florida',        'Wesley Chapel'),
    ('estate-sale-pasco-county',                 'Pasco & Hernando County'),
    ('estate-sale-citrus-county',                'Citrus County'),
]

# Pages that previously came back as "URL is unknown to Google" — confirm they get inbound
UNKNOWN_GEO = {
    'estate-sale-clearwater-florida',
    'estate-sale-dunedin-florida',
    'estate-sale-st-petersburg-florida',
    'estate-sale-largo-florida',
    'estate-sale-new-port-richey-florida',
    'estate-sale-wesley-chapel-florida',
}

URLS_TO_REINSPECT = [f'https://organizinglifeservices.com/pages/{h}' for h in UNKNOWN_GEO]


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


def make_service_areas_block(intro):
    """Used on estate-cleanout-services + faqs — links to ALL 11 geo pages."""
    items = ''.join(
        f'<li><a href="/pages/{h}">Estate sales in {anchor}</a></li>'
        for h, anchor in GEO_ANCHORS
    )
    return (
        '\n<!-- SERVICE-AREAS-V1 -->\n'
        '<section class="ols-service-areas" style="margin:32px 0;padding:24px;border-top:1px solid #eee;">\n'
        f'  <h2 style="font-size:20px;margin:0 0 12px;">Service Areas We Cover</h2>\n'
        f'  <p style="margin:0 0 12px;">{intro}</p>\n'
        f'  <ul style="columns:2;column-gap:32px;margin:0;padding-left:20px;line-height:1.8;">{items}</ul>\n'
        '</section>\n<!-- /SERVICE-AREAS-V1 -->\n'
    )


def make_crosslink_block(self_handle):
    """Used on each geo page — links to all 10 OTHER geo pages."""
    others = [(h, a) for h, a in GEO_ANCHORS if h != self_handle]
    items = ''.join(
        f'<li><a href="/pages/{h}">Estate sales in {anchor}</a></li>'
        for h, anchor in others
    )
    return (
        '\n<!-- GEO-CROSSLINKS-V1 -->\n'
        '<section class="ols-geo-crosslinks" style="margin:32px 0;padding:24px;border-top:1px solid #eee;">\n'
        '  <h2 style="font-size:20px;margin:0 0 12px;">Estate Sales in Nearby Areas</h2>\n'
        '  <p style="margin:0 0 12px;">Organizing Life Services produces full-service estate sales across the Greater Tampa Bay Area. Explore our coverage in other nearby cities and counties:</p>\n'
        f'  <ul style="columns:2;column-gap:32px;margin:0;padding-left:20px;line-height:1.8;">{items}</ul>\n'
        '</section>\n<!-- /GEO-CROSSLINKS-V1 -->\n'
    )


def patch_page(B, H, p, marker, block):
    if marker in (p.get('body_html') or ''):
        print(f'  [skip] {p["handle"]} already has {marker}')
        return False
    new_body = (p.get('body_html') or '') + block
    r = _retry(httpx.put, f'{B}/pages/{p["id"]}.json', headers=H, timeout=30,
               json={'page': {'id': p['id'], 'body_html': new_body}})
    r.raise_for_status()
    print(f'  [ok] {p["handle"]}: +{len(block)}c')
    time.sleep(0.4)
    return True


def section_a_b_intlinks():
    print('=== A+B) Crosslink + service-areas blocks ===')
    tok = httpx.post(f'https://{STORE}.myshopify.com/admin/oauth/access_token',
        json={'client_id': CID, 'client_secret': CS, 'grant_type': 'client_credentials'},
        timeout=30).json()['access_token']
    H = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    B = f'https://{STORE}.myshopify.com/admin/api/{API}'

    pages = _retry(httpx.get, f'{B}/pages.json?limit=250', headers=H, timeout=30).json()['pages']
    bh = {p['handle']: p for p in pages}

    # 1) Service-areas block on estate-cleanout-services + faqs
    print('\n[hub pages] inserting SERVICE-AREAS-V1')
    for h, intro in [
        ('estate-cleanout-services',
         'We serve homeowners, executors, attorneys, and senior-living facilities across the Greater Tampa Bay Area:'),
        ('faqs',
         'Have questions about our process in your area? Browse our city-specific service pages:'),
    ]:
        p = bh.get(h)
        if not p:
            print(f'  [miss] {h}'); continue
        patch_page(B, H, p, 'SERVICE-AREAS-V1', make_service_areas_block(intro))

    # 2) Crosslink block on ALL 11 geo pages
    print('\n[geo pages] inserting GEO-CROSSLINKS-V1')
    for h, _ in GEO_ANCHORS:
        p = bh.get(h)
        if not p:
            print(f'  [miss] {h}'); continue
        patch_page(B, H, p, 'GEO-CROSSLINKS-V1', make_crosslink_block(h))


def section_c_recrawl():
    print('\n=== C) Sitemap resubmit + re-inspect 6 unknown geo URLs ===')
    creds = service_account.Credentials.from_service_account_file(
        SA, scopes=['https://www.googleapis.com/auth/webmasters'])
    gsc = build('searchconsole', 'v1', credentials=creds, cache_discovery=False)
    try:
        gsc.sitemaps().submit(siteUrl=SITE, feedpath=SITEMAP).execute()
        print(f'  [ok] sitemap resubmitted')
    except Exception as e:
        print(f'  [warn] sitemap: {e}')

    print(f'  re-inspecting {len(URLS_TO_REINSPECT)} URLs (this also queues for crawl)...')
    for u in URLS_TO_REINSPECT:
        try:
            r = gsc.urlInspection().index().inspect(body={
                'inspectionUrl': u, 'siteUrl': SITE}).execute()
            idx = r.get('inspectionResult', {}).get('indexStatusResult', {})
            print(f'  {idx.get("verdict","?"):8} {idx.get("coverageState","?")[:40]:40} {u}')
        except Exception as e:
            print(f'  [err] {u}: {e}')
        time.sleep(0.6)


def main():
    section_a_b_intlinks()
    section_c_recrawl()


if __name__ == '__main__':
    main()
