"""Session-8: three SEO upgrades.

  1. FAQ + BreadcrumbList JSON-LD on all 11 geo pages.
     Appends an idempotent <!-- FAQ-SCHEMA-V1 --> block to each geo page body
     containing both schemas (Google supports multiple JSON-LD per page). The
     block ALSO renders an HTML FAQ <section> with the same Q&A as visible
     content (required by Google to be eligible for FAQ rich results).

  2. Article + BreadcrumbList JSON-LD on top-6 blog posts.
     Appends idempotent <!-- ARTICLE-SCHEMA-V1 --> block to each article body
     with @type=Article (headline, datePublished, dateModified, author,
     publisher, image, mainEntityOfPage) + BreadcrumbList.

  3. IndexNow setup + bulk submission to Bing/Yandex.
     - Generates UUID hex key
     - Uploads templates/page.indexnow.liquid to theme (outputs JUST page
       content, no theme chrome) so the key file URL serves as plain text
     - Creates a Shopify page at handle = key, body = key text, template_suffix
       = "indexnow"
     - Submits all 11 geo pages + 6 blog posts + homepage + 4 hub pages to
       https://api.indexnow.org/IndexNow

Idempotent throughout. Persists IndexNow key to data/audit_output/indexnow_key.txt
so future re-runs reuse it.
"""
import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

STORE = os.getenv('SHOPIFY_STORE'); CID = os.getenv('SHOPIFY_CLIENT_ID')
CS = os.getenv('SHOPIFY_CLIENT_SECRET'); API = os.getenv('SHOPIFY_API_VERSION', '2024-10')
THEME = 153690210458
BLOG = 52179501100
HOST = 'organizinglifeservices.com'
ORG_NAME = 'Organizing Life Services'
ORG_URL = f'https://{HOST}/'
ORG_LOGO = 'https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_LOGO_PNG.png'
PHONE = '(727) 542-6028'
OUT = Path('data/audit_output'); OUT.mkdir(parents=True, exist_ok=True)
INDEXNOW_KEY_FILE = OUT / 'indexnow_key.txt'

# (handle, city, county, region/area-served-suffix)
GEO_PAGES = [
    ('estate-sale-palm-harbor-pinellas-county',  'Palm Harbor',     'Pinellas County',                'Pinellas County, FL'),
    ('tarpon-springs-estate-sale-in-woodfield',  'Tarpon Springs',  'Pinellas County',                'Pinellas County, FL'),
    ('estate-sale-clearwater-florida',           'Clearwater',      'Pinellas County',                'Pinellas County, FL'),
    ('estate-sale-dunedin-florida',              'Dunedin',         'Pinellas County',                'Pinellas County, FL'),
    ('estate-sale-st-petersburg-florida',        'St. Petersburg',  'Pinellas County',                'Pinellas County, FL'),
    ('estate-sale-largo-florida',                'Largo',           'Pinellas County',                'Pinellas County, FL'),
    ('estate-sale-tampa-hillsborough-county',    'Tampa',           'Hillsborough County',            'Hillsborough County, FL'),
    ('estate-sale-new-port-richey-florida',      'New Port Richey', 'Pasco County',                   'Pasco County, FL'),
    ('estate-sale-wesley-chapel-florida',        'Wesley Chapel',   'Pasco County',                   'Pasco County, FL'),
    ('estate-sale-pasco-county',                 'Pasco County',    'Pasco & Hernando County',        'Pasco and Hernando County, FL'),
    ('estate-sale-citrus-county',                'Citrus County',   'Citrus County',                  'Citrus County, FL'),
]

# (handle, headline, primary_kw, published_iso, description)
TOP6_ARTICLES = [
    ('estate-sale-vs-garage-sale-know-the-differences',
     'Estate Sale vs Garage Sale: 2026 Quick Guide',
     'estate sale vs garage sale',
     '2024-06-15T10:00:00-04:00',
     'Compare estate sales and garage sales side-by-side: proceeds, time, effort, and which format fits your Tampa Bay inventory.'),
    ('pros-and-cons-of-estate-sales',
     'Pros and Cons of Estate Sales: 2026 Guide',
     'pros and cons of estate sales',
     '2024-07-20T10:00:00-04:00',
     'Every pro and con of running an estate sale in 2026, including real Tampa Bay commission ranges and when an estate sale is NOT the right choice.'),
    ('how-to-increase-your-home-appraisal-value',
     'How to Increase Your Home Appraisal Value: 2026 Tips',
     'how to increase home appraisal value',
     '2024-09-10T10:00:00-04:00',
     'Highest-ROI upgrades to boost your home appraisal value in 2026, plus how a pre-listing estate sale moves the number $5,000–$15,000.'),
    ('estate-auction-vs-estate-sale-pros-and-cons',
     'Estate Auction vs Estate Sale: 2026 Comparison',
     'estate auction vs estate sale',
     '2024-08-12T10:00:00-04:00',
     'Estate auction vs estate sale — which format nets more for your inventory in 2026? Full Tampa Bay economics, hybrid strategies, and decision matrix.'),
    ('the-ultimate-guide-for-barbie-collector-buyers',
     'Ultimate Guide for Barbie Collector Buyers in 2026',
     'Barbie collector buyers',
     '2024-10-05T10:00:00-04:00',
     'Identify, value, and sell vintage Barbie collections in 2026 — top buyers, condition grading, current market prices, and how to connect with serious buyers.'),
    ('how-to-plan-estate-sale',
     'How to Plan an Estate Sale: 2026 Step-by-Step',
     'how to plan an estate sale',
     '2024-05-30T10:00:00-04:00',
     'Step-by-step 2026 guide to planning an estate sale — timeline, sorting, pricing, marketing, sale-day staffing, and post-sale cleanout.'),
]

DATE_MODIFIED = '2026-05-28T10:00:00-04:00'

INDEXNOW_URLS = (
    [ORG_URL] +
    [f'{ORG_URL}pages/{h}' for h, *_ in GEO_PAGES] +
    [f'{ORG_URL}blogs/news/{h}' for h, *_ in TOP6_ARTICLES] +
    [f'{ORG_URL}pages/{h}' for h in ('estate-cleanout-services', 'faqs',
                                      'personal-property-appraisal', 'downsizing-moving-sales')]
)


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


def shopify_auth():
    tok = httpx.post(f'https://{STORE}.myshopify.com/admin/oauth/access_token',
        json={'client_id': CID, 'client_secret': CS, 'grant_type': 'client_credentials'},
        timeout=30).json()['access_token']
    return ({'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'},
            f'https://{STORE}.myshopify.com/admin/api/{API}')


def patch_page_body(B, H, page, marker, block):
    if marker in (page.get('body_html') or ''):
        print(f'  [skip] {page["handle"]} already has {marker}')
        return False
    new_body = (page.get('body_html') or '') + block
    r = _retry(httpx.put, f'{B}/pages/{page["id"]}.json', headers=H, timeout=30,
               json={'page': {'id': page['id'], 'body_html': new_body}})
    r.raise_for_status()
    print(f'  [ok] {page["handle"]}: +{len(block)}c')
    time.sleep(0.4)
    return True


def patch_article_body(B, H, blog_id, article, marker, block):
    if marker in (article.get('body_html') or ''):
        print(f'  [skip] {article["handle"]} already has {marker}')
        return False
    new_body = (article.get('body_html') or '') + block
    r = _retry(httpx.put, f'{B}/blogs/{blog_id}/articles/{article["id"]}.json',
               headers=H, timeout=30,
               json={'article': {'id': article['id'], 'body_html': new_body}})
    r.raise_for_status()
    print(f'  [ok] {article["handle"]}: +{len(block)}c')
    time.sleep(0.4)
    return True


# -------- #1 FAQ + Breadcrumb per geo page --------
def faq_block_for(handle, city, county, area):
    page_url = f'{ORG_URL}pages/{handle}'
    faqs = [
        (f'How much does an estate sale cost in {city}, FL?',
         f'There is no upfront cost for a {city} estate sale with Organizing Life Services. We work on commission — typically 30–40% of gross sales depending on inventory size, scope, and condition. This covers pricing, staging, marketing, sale-day staffing, credit-card processing, and basic post-sale cleanout. You receive a written contract and a net-proceeds estimate before we schedule the sale.'),
        (f'How long does an estate sale take in {city}?',
         f'A typical {city} estate sale runs 1–3 sale days (Friday–Sunday is most common) preceded by 5–10 days of in-home setup: sorting, pricing, staging, and photography. From signed contract to final payout, most {area} estate sales complete in 2–4 weeks.'),
        ('What happens to the items that do not sell?',
         f'After the sale, Organizing Life Services handles the entire cleanout: donations to local Tampa Bay charities (with itemized receipts for your tax records), consignment of higher-value leftovers, and removal of remaining items. The home is left broom-clean and ready for listing, closing, or family handoff.'),
        (f'What areas around {city} do you serve?',
         f'In addition to {city}, we run estate sales throughout {area} — including all surrounding neighborhoods, gated communities, and 55+ developments. We also cover the broader Greater Tampa Bay Area: Pinellas, Pasco, Hillsborough, Hernando, and Citrus counties.'),
        (f'How quickly can you schedule an estate sale in {city}?',
         f'Most {city} estate sales can be scheduled within 2–4 weeks of the initial consultation. For probate, time-sensitive relocations, or expedited closings, we offer rush scheduling (1–2 weeks) when our calendar allows. Call {PHONE} to check current availability.'),
    ]
    breadcrumb = {
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home',         'item': ORG_URL},
            {'@type': 'ListItem', 'position': 2, 'name': 'Estate Sales', 'item': f'{ORG_URL}pages/estate-cleanout-services'},
            {'@type': 'ListItem', 'position': 3, 'name': f'{city}',      'item': page_url},
        ],
    }
    faq_jsonld = {
        '@context': 'https://schema.org', '@type': 'FAQPage',
        'mainEntity': [
            {'@type': 'Question', 'name': q,
             'acceptedAnswer': {'@type': 'Answer', 'text': a}}
            for q, a in faqs
        ],
    }
    visible_html = (
        f'<section class="ols-faq" style="margin:32px 0;padding:24px;border-top:1px solid #eee;">\n'
        f'  <h2 style="font-size:22px;margin:0 0 16px;">Frequently Asked Questions — Estate Sales in {city}</h2>\n'
        + ''.join(
            f'  <div style="margin:16px 0;"><h3 style="font-size:17px;margin:0 0 6px;">{q}</h3><p style="margin:0;">{a}</p></div>\n'
            for q, a in faqs
        )
        + '</section>'
    )
    return (
        '\n<!-- FAQ-SCHEMA-V1 -->\n'
        + visible_html
        + '\n<script type="application/ld+json">'
        + json.dumps(faq_jsonld, separators=(',', ':'))
        + '</script>'
        + '\n<script type="application/ld+json">'
        + json.dumps(breadcrumb, separators=(',', ':'))
        + '</script>\n<!-- /FAQ-SCHEMA-V1 -->\n'
    )


def section_1_faq_breadcrumbs(B, H):
    print('=== #1 FAQ + Breadcrumb schema on 11 geo pages ===')
    pages = _retry(httpx.get, f'{B}/pages.json?limit=250', headers=H, timeout=30).json()['pages']
    bh = {p['handle']: p for p in pages}
    for h, city, county, area in GEO_PAGES:
        p = bh.get(h)
        if not p: print(f'  [miss] {h}'); continue
        patch_page_body(B, H, p, 'FAQ-SCHEMA-V1', faq_block_for(h, city, county, area))


# -------- #2 Article + Breadcrumb per top-6 blog --------
def article_block_for(handle, headline, kw, published, description, image_url):
    article_url = f'{ORG_URL}blogs/news/{handle}'
    article_jsonld = {
        '@context': 'https://schema.org', '@type': 'Article',
        'headline': headline,
        'description': description,
        'image': [image_url] if image_url else [ORG_LOGO],
        'datePublished': published,
        'dateModified': DATE_MODIFIED,
        'author': {'@type': 'Organization', 'name': ORG_NAME, 'url': ORG_URL},
        'publisher': {
            '@type': 'Organization', 'name': ORG_NAME,
            'logo': {'@type': 'ImageObject', 'url': ORG_LOGO},
        },
        'mainEntityOfPage': {'@type': 'WebPage', '@id': article_url},
        'keywords': kw,
    }
    breadcrumb = {
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home',  'item': ORG_URL},
            {'@type': 'ListItem', 'position': 2, 'name': 'Blog',  'item': f'{ORG_URL}blogs/news'},
            {'@type': 'ListItem', 'position': 3, 'name': headline, 'item': article_url},
        ],
    }
    byline = (
        f'<p class="ols-byline" style="font-size:14px;color:#666;margin:16px 0;border-top:1px solid #eee;padding-top:12px;">'
        f'<strong>By {ORG_NAME}</strong> &mdash; Tampa Bay\'s trusted estate-sale specialists since 2010. '
        f'<em>Updated for 2026. Questions? Call {PHONE} or '
        f'<a href="/pages/contact">request a free consultation</a>.</em></p>'
    )
    return (
        '\n<!-- ARTICLE-SCHEMA-V1 -->\n'
        + byline
        + '\n<script type="application/ld+json">'
        + json.dumps(article_jsonld, separators=(',', ':'))
        + '</script>'
        + '\n<script type="application/ld+json">'
        + json.dumps(breadcrumb, separators=(',', ':'))
        + '</script>\n<!-- /ARTICLE-SCHEMA-V1 -->\n'
    )


def section_2_article_schema(B, H):
    print('\n=== #2 Article + Breadcrumb schema on top-6 articles ===')
    articles = _retry(httpx.get, f'{B}/blogs/{BLOG}/articles.json?limit=250',
                      headers=H, timeout=30).json()['articles']
    bh = {a['handle']: a for a in articles}
    for h, headline, kw, published, description in TOP6_ARTICLES:
        a = bh.get(h)
        if not a: print(f'  [miss] {h}'); continue
        img = a.get('image', {}).get('src') if a.get('image') else None
        patch_article_body(B, H, BLOG, a, 'ARTICLE-SCHEMA-V1',
                           article_block_for(h, headline, kw, published, description, img))


# -------- #3 IndexNow setup + submission --------
INDEXNOW_TEMPLATE = '''{%- layout none -%}{{ page.content | strip_html | strip }}'''


def section_3_indexnow(B, H):
    print('\n=== #3 IndexNow key setup + bulk URL submission ===')
    # 1) Reuse or generate key
    if INDEXNOW_KEY_FILE.exists():
        key = INDEXNOW_KEY_FILE.read_text().strip()
        print(f'  reusing key: {key[:8]}...')
    else:
        key = uuid.uuid4().hex
        INDEXNOW_KEY_FILE.write_text(key)
        print(f'  generated key: {key[:8]}... (saved to {INDEXNOW_KEY_FILE})')

    # 2) Upload templates/page.indexnow.liquid theme asset
    asset_key = 'templates/page.indexnow.liquid'
    r = _retry(httpx.put, f'{B}/themes/{THEME}/assets.json', headers=H, timeout=60,
               json={'asset': {'key': asset_key, 'value': INDEXNOW_TEMPLATE}})
    if r.status_code in (200, 201):
        print(f'  [ok] theme asset uploaded: {asset_key}')
    else:
        print(f'  [warn] asset upload {r.status_code}: {r.text[:300]}')

    # 3) Upsert page with handle=key, body=key, template_suffix=indexnow
    pages = _retry(httpx.get, f'{B}/pages.json?handle={key}', headers=H, timeout=30).json()['pages']
    if pages:
        page = pages[0]
        r = _retry(httpx.put, f'{B}/pages/{page["id"]}.json', headers=H, timeout=30,
                   json={'page': {'id': page['id'], 'body_html': key,
                                   'template_suffix': 'indexnow', 'published': True}})
        print(f'  [ok] key page updated (id={page["id"]})')
    else:
        r = _retry(httpx.post, f'{B}/pages.json', headers=H, timeout=30,
                   json={'page': {'title': 'IndexNow Key', 'handle': key, 'body_html': key,
                                   'template_suffix': 'indexnow', 'published': True}})
        page = r.json()['page']
        print(f'  [ok] key page created (id={page["id"]})')

    key_url_redirect = f'{ORG_URL}{key}.txt'
    page_url = f'{ORG_URL}pages/{key}'
    print(f'  key page URL : {page_url}')
    print(f'  key file URL : {key_url_redirect}  (root-level, required by IndexNow)')

    # 4) Ensure URL redirect /{key}.txt -> /pages/{key} exists
    rd = _retry(httpx.get, f'{B}/redirects.json?path=/{key}.txt', headers=H, timeout=30).json()['redirects']
    if rd:
        print(f'  [skip] redirect /{key}.txt already exists')
    else:
        r = _retry(httpx.post, f'{B}/redirects.json', headers=H, timeout=30,
                   json={'redirect': {'path': f'/{key}.txt', 'target': f'/pages/{key}'}})
        r.raise_for_status()
        print(f'  [ok] created redirect /{key}.txt -> /pages/{key}')

    # 5) Verify the root-level key URL resolves to clean key text (via 301 to /pages/{key})
    time.sleep(2)
    vr = httpx.get(key_url_redirect, timeout=15, follow_redirects=True)
    body_clean = vr.text.strip()
    if body_clean == key:
        print(f'  [ok] {key_url_redirect} returns clean key (HTTP {vr.status_code} after {len(vr.history)} redirects)')
    else:
        print(f'  [ERR] key file mismatch — IndexNow will reject. Got: {body_clean[:120]!r}')
        return

    # 6) Submit URL list to IndexNow via api.indexnow.org (fans out to Bing/Yandex/Seznam)
    payload = {
        'host': HOST,
        'key': key,
        'keyLocation': key_url_redirect,
        'urlList': INDEXNOW_URLS,
    }
    for endpoint in ('https://api.indexnow.org/IndexNow',
                     'https://www.bing.com/indexnow',
                     'https://yandex.com/indexnow'):
        r = httpx.post(endpoint, json=payload,
                       headers={'Content-Type': 'application/json; charset=utf-8'},
                       timeout=30)
        ok = 'OK ' if r.status_code in (200, 202) else 'ERR'
        print(f'  [{ok}] {endpoint}: HTTP {r.status_code} {r.text[:120]!r}')


def main():
    H, B = shopify_auth()
    section_1_faq_breadcrumbs(B, H)
    section_2_article_schema(B, H)
    section_3_indexnow(B, H)


if __name__ == '__main__':
    main()
