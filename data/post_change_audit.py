"""Post-change SEO audit — measures impact of Phases 4-8 (May 28, 2026).

Compares:
  POST window: 2026-05-28 -> 2026-06-03  (7 days, post-change)
  PRE  window: 2026-05-21 -> 2026-05-27  (7 days, pre-change)
  BASE window: 2026-04-30 -> 2026-05-27  (28 days, deeper baseline)

For each priority URL group: geo (11), top-6 articles, hub (4), homepage.
Measures GSC clicks/impressions/CTR/position + GA4 sessions.
Plus: URL inspection on 6 previously-unknown geo pages.
Plus: live schema verification (FAQ/Article/Breadcrumb/LocalBusiness).
Plus: noindex enforcement check (18 dead pages).
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest, Filter, FilterExpression,
)

SITE = 'https://organizinglifeservices.com/'
HOST = 'organizinglifeservices.com'
SA = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'credentials/google-service-account.json')
GA4 = '396184354'
OUT = Path('data/audit_output')
TODAY = datetime(2026, 6, 4).date()

# 7-day post-change window (2026-05-28 to 2026-06-03)
POST_END = TODAY - timedelta(days=1)
POST_START = TODAY - timedelta(days=7)
# 7-day pre-change window (2026-05-21 to 2026-05-27)
PRE_END = POST_START - timedelta(days=1)
PRE_START = POST_START - timedelta(days=7)
# 28-day baseline ending right before changes
BASE_END = POST_START - timedelta(days=1)
BASE_START = POST_START - timedelta(days=28)

UA = 'Mozilla/5.0 (compatible; OLS-Audit/1.0; +https://organizinglifeservices.com)'
HDR = {'User-Agent': UA}

GEO = [
    'estate-sale-palm-harbor-pinellas-county', 'tarpon-springs-estate-sale-in-woodfield',
    'estate-sale-clearwater-florida', 'estate-sale-dunedin-florida',
    'estate-sale-st-petersburg-florida', 'estate-sale-largo-florida',
    'estate-sale-tampa-hillsborough-county', 'estate-sale-new-port-richey-florida',
    'estate-sale-wesley-chapel-florida', 'estate-sale-pasco-county', 'estate-sale-citrus-county',
]
ARTICLES = [
    'estate-sale-vs-garage-sale-know-the-differences', 'pros-and-cons-of-estate-sales',
    'how-to-increase-your-home-appraisal-value', 'estate-auction-vs-estate-sale-pros-and-cons',
    'the-ultimate-guide-for-barbie-collector-buyers', 'how-to-plan-estate-sale',
]
HUBS = ['estate-cleanout-services', 'faqs', 'personal-property-appraisal', 'downsizing-moving-sales']

NOINDEX_18 = [
    "13925-pathfinder-drive-tampa-florida",
    "613-severs-landing-palm-harbor-fl-estate-sale-part-1",
    "613-severs-landing-palm-harbor-fl-estate-sale-part-2",
    "estate-sale-safety-harbor-florida-pinellas-county-34695",
    "estate-sale-westchase-tampa-fl-33626-hillsborough-county",
    "highland-lakes-estate-sale", "lansbrook-myrtle-point-estate-sale-part-two",
    "myrtle-point-estate-sale", "moon-lake-estate-sale",
    "new-port-richey-appointment-only-sale-april-2024",
    "new-port-richey-sale-huge-do-not-miss-this-one",
    "odessa-estate-sale-june-2024", "organizing-life-estate-sale-company-successful-sales",
    "pimberton-drive-hudson",
    "pinellas-park-estate-sale-in-the-mainlands-9841-41st-street-north",
    "successful-high-quality-estate-sale-ridge-lane-palm-harbor-pinellas-county-florida",
    "vintage-coca-cola-estate-sale-in-dunedin-florida-march-2023",
    "vintage-palm-harbor-coming-up-soon",
]


def all_priority_urls():
    urls = [SITE]
    for h in GEO: urls.append(f'{SITE}pages/{h}')
    for h in ARTICLES: urls.append(f'{SITE}blogs/news/{h}')
    for h in HUBS: urls.append(f'{SITE}pages/{h}')
    return urls


# ---------- GSC pull ----------
def gsc_window(gsc, start, end, page_filter=None):
    """Aggregate clicks/impressions/CTR/position per page for a date window."""
    rows = []
    start_row = 0
    while True:
        body = {
            'startDate': start.isoformat(),
            'endDate': end.isoformat(),
            'dimensions': ['page'],
            'rowLimit': 25000,
            'startRow': start_row,
        }
        r = gsc.searchanalytics().query(siteUrl=SITE, body=body).execute()
        rs = r.get('rows', [])
        rows.extend(rs)
        if len(rs) < 25000: break
        start_row += 25000
    page_data = {}
    for row in rows:
        page = row['keys'][0]
        page_data[page] = {
            'clicks': row.get('clicks', 0),
            'impressions': row.get('impressions', 0),
            'ctr': row.get('ctr', 0),
            'position': row.get('position', 0),
        }
    return page_data


def gsc_queries_window(gsc, start, end):
    """Aggregate by (page, query)."""
    rows = []
    start_row = 0
    while True:
        body = {
            'startDate': start.isoformat(),
            'endDate': end.isoformat(),
            'dimensions': ['query', 'page'],
            'rowLimit': 25000,
            'startRow': start_row,
        }
        r = gsc.searchanalytics().query(siteUrl=SITE, body=body).execute()
        rs = r.get('rows', [])
        rows.extend(rs)
        if len(rs) < 25000: break
        start_row += 25000
    out = []
    for row in rows:
        q, p = row['keys']
        out.append({'query': q, 'page': p, 'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr': row.get('ctr', 0), 'position': row.get('position', 0)})
    return out


def section_gsc(creds):
    gsc = build('searchconsole', 'v1', credentials=creds, cache_discovery=False)
    print('[GSC] pulling 7d post, 7d pre, 28d base...')
    post = gsc_window(gsc, POST_START, POST_END)
    pre  = gsc_window(gsc, PRE_START,  PRE_END)
    base = gsc_window(gsc, BASE_START, BASE_END)
    print(f'  post  pages={len(post):4} clicks={sum(p["clicks"] for p in post.values()):4} '
          f'impr={sum(p["impressions"] for p in post.values())}')
    print(f'  pre   pages={len(pre):4}  clicks={sum(p["clicks"] for p in pre.values()):4} '
          f'impr={sum(p["impressions"] for p in pre.values())}')
    print(f'  base  pages={len(base):4} clicks={sum(p["clicks"] for p in base.values()):4} '
          f'impr={sum(p["impressions"] for p in base.values())}')

    # Per-priority-URL comparison
    rows = []
    for url in all_priority_urls():
        ph = post.get(url, {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0})
        pr = pre.get(url,  {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0})
        bs = base.get(url, {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0})
        rows.append({
            'url': url,
            'post_clicks': ph['clicks'], 'pre_clicks': pr['clicks'], 'base_clicks_28d': bs['clicks'],
            'post_impr': ph['impressions'], 'pre_impr': pr['impressions'], 'base_impr_28d': bs['impressions'],
            'post_ctr': ph['ctr'], 'pre_ctr': pr['ctr'],
            'post_pos': ph['position'], 'pre_pos': pr['position'],
        })

    # Query-level: new wins (queries present in post but not in pre) - filter to priority URLs
    print('[GSC] pulling query-level deltas...')
    qpost = gsc_queries_window(gsc, POST_START, POST_END)
    qpre  = gsc_queries_window(gsc, PRE_START,  PRE_END)
    pre_keys = {(q['query'], q['page']) for q in qpre}
    priority = set(all_priority_urls())
    new_wins = [q for q in qpost if (q['query'], q['page']) not in pre_keys and q['page'] in priority]
    new_wins.sort(key=lambda x: -x['impressions'])
    return {'per_url': rows, 'new_wins_top30': new_wins[:30]}


# ---------- URL inspection ----------
def section_inspect(creds):
    gsc = build('searchconsole', 'v1', credentials=creds, cache_discovery=False)
    targets = [f'{SITE}pages/{h}' for h in GEO] + [f'{SITE}blogs/news/{h}' for h in ARTICLES] + [SITE]
    out = []
    print(f'[INSPECT] checking {len(targets)} priority URLs...')
    for u in targets:
        try:
            r = gsc.urlInspection().index().inspect(body={
                'inspectionUrl': u, 'siteUrl': SITE}).execute()
            idx = r.get('inspectionResult', {}).get('indexStatusResult', {})
            mob = r.get('inspectionResult', {}).get('mobileUsabilityResult', {})
            rch = r.get('inspectionResult', {}).get('richResultsResult', {})
            row = {
                'url': u,
                'verdict': idx.get('verdict', '?'),
                'coverage': idx.get('coverageState', '?'),
                'last_crawl': idx.get('lastCrawlTime', '?'),
                'indexing_state': idx.get('indexingState', '?'),
                'rich_results_verdict': rch.get('verdict', '?'),
                'rich_results_items': [it.get('richResultType') for it in rch.get('detectedItems', [])],
            }
            out.append(row)
            print(f'  {row["verdict"]:8} {row["coverage"][:36]:36}  rich={row["rich_results_verdict"]:8} '
                  f'{",".join(row["rich_results_items"])[:40]:40} {u}')
        except Exception as e:
            out.append({'url': u, 'error': str(e)})
            print(f'  [ERR] {u}: {str(e)[:80]}')
        time.sleep(0.6)
    return out


# ---------- Inspect noindexed pages ----------
def section_noindex_check(creds):
    gsc = build('searchconsole', 'v1', credentials=creds, cache_discovery=False)
    targets = [f'{SITE}pages/{h}' for h in NOINDEX_18[:8]]  # sample 8 of 18 to stay under quota
    out = []
    print(f'[NOINDEX] checking {len(targets)} dead pages (verifying removal)...')
    for u in targets:
        try:
            r = gsc.urlInspection().index().inspect(body={
                'inspectionUrl': u, 'siteUrl': SITE}).execute()
            idx = r.get('inspectionResult', {}).get('indexStatusResult', {})
            row = {'url': u, 'verdict': idx.get('verdict', '?'),
                   'coverage': idx.get('coverageState', '?'),
                   'indexing_state': idx.get('indexingState', '?'),
                   'last_crawl': idx.get('lastCrawlTime', '?'),
                   'robots_txt_state': idx.get('robotsTxtState', '?'),
                   'page_fetch_state': idx.get('pageFetchState', '?')}
            out.append(row)
            print(f'  {row["verdict"]:8} {row["coverage"][:36]:36} state={row["indexing_state"][:30]:30} {u}')
        except Exception as e:
            out.append({'url': u, 'error': str(e)})
            print(f'  [ERR] {u}: {str(e)[:80]}')
        time.sleep(0.6)
    return out


# ---------- Live schema verification ----------
def section_schema():
    print('[SCHEMA] fetching & parsing JSON-LD from live URLs...')
    out = []
    checks = (
        [(f'{SITE}', 'homepage', ['LocalBusiness', 'SCHEMA-LB-V2', 'SEO-INTLINKS-A5-V1'])] +
        [(f'{SITE}pages/{h}', f'geo:{h[:30]}',
          ['FAQ-SCHEMA-V1', 'FAQPage', 'BreadcrumbList', 'GEO-CROSSLINKS-V1']) for h in GEO[:6]] +
        [(f'{SITE}blogs/news/{h}', f'article:{h[:30]}',
          ['ARTICLE-SCHEMA-V1', '"@type":"Article"', 'BreadcrumbList']) for h in ARTICLES] +
        [(f'{SITE}pages/{h}', f'hub:{h}', ['SERVICE-AREAS-V1']) for h in ('estate-cleanout-services', 'faqs')]
    )
    for url, label, markers in checks:
        try:
            r = httpx.get(url, timeout=20, headers=HDR, follow_redirects=True)
            html = r.text
            found = {m: (m in html) for m in markers}
            all_ok = all(found.values())
            out.append({'url': url, 'label': label, 'status': r.status_code,
                        'markers': found, 'all_ok': all_ok})
            badge = 'OK ' if all_ok else 'MISS'
            print(f'  [{badge}] {label:40} {url}  missing={[m for m,v in found.items() if not v]}')
        except Exception as e:
            out.append({'url': url, 'label': label, 'error': str(e)})
            print(f'  [ERR] {label}: {e}')
        time.sleep(0.3)
    return out


# ---------- Noindex header verification ----------
def section_noindex_live():
    print('[NOINDEX-LIVE] verifying meta robots on 18 dead pages...')
    out = []
    for h in NOINDEX_18:
        url = f'{SITE}pages/{h}'
        try:
            r = httpx.get(url, timeout=15, headers=HDR, follow_redirects=True)
            m = re.search(r'<meta\s+name="robots"\s+content="([^"]+)"', r.text)
            content = m.group(1) if m else None
            ok = content and 'noindex' in content.lower()
            out.append({'url': url, 'status': r.status_code, 'robots': content, 'ok': bool(ok)})
            if not ok:
                print(f'  [MISS] {h}: robots={content}')
        except Exception as e:
            out.append({'url': url, 'error': str(e)})
    ok_count = sum(1 for x in out if x.get('ok'))
    print(f'  [summary] {ok_count}/{len(NOINDEX_18)} pages have noindex meta tag live')
    return out


# ---------- GA4 organic sessions ----------
def section_ga4(creds):
    print('[GA4] pulling organic sessions per landing page...')
    client = BetaAnalyticsDataClient(credentials=creds)
    out = {}
    for label, start, end in (('post', POST_START, POST_END), ('pre', PRE_START, PRE_END),
                              ('base_28d', BASE_START, BASE_END)):
        req = RunReportRequest(
            property=f'properties/{GA4}',
            date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
            dimensions=[Dimension(name='landingPagePlusQueryString'),
                        Dimension(name='sessionDefaultChannelGroup')],
            metrics=[Metric(name='sessions'), Metric(name='conversions')],
        )
        rows = client.run_report(req).rows
        out[label] = []
        for row in rows:
            page, channel = row.dimension_values[0].value, row.dimension_values[1].value
            sessions = int(row.metric_values[0].value); conv = float(row.metric_values[1].value)
            if channel == 'Organic Search':
                out[label].append({'page': page, 'sessions': sessions, 'conversions': conv})
    print(f'  post organic landing pages: {len(out["post"])}')
    print(f'  pre  organic landing pages: {len(out["pre"])}')
    return out


def main():
    creds = service_account.Credentials.from_service_account_file(
        SA, scopes=['https://www.googleapis.com/auth/webmasters',
                    'https://www.googleapis.com/auth/analytics.readonly'])

    print(f'\nWindows:')
    print(f'  POST (post-change 7d):  {POST_START} -> {POST_END}')
    print(f'  PRE  (pre-change 7d):   {PRE_START} -> {PRE_END}')
    print(f'  BASE (28d baseline):    {BASE_START} -> {BASE_END}')

    result = {}
    result['windows'] = {'post': [str(POST_START), str(POST_END)],
                         'pre':  [str(PRE_START),  str(PRE_END)],
                         'base': [str(BASE_START), str(BASE_END)]}
    print('\n--- 1) GSC per-URL + new query wins ---')
    result['gsc'] = section_gsc(creds)
    print('\n--- 2) URL Inspection ---')
    result['inspection'] = section_inspect(creds)
    print('\n--- 3) Noindex-18 inspection ---')
    result['noindex_inspection'] = section_noindex_check(creds)
    print('\n--- 4) Live schema verification ---')
    result['schema'] = section_schema()
    print('\n--- 5) Live noindex meta verification ---')
    result['noindex_live'] = section_noindex_live()
    print('\n--- 6) GA4 organic sessions ---')
    result['ga4'] = section_ga4(creds)

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f'post_change_audit_{TODAY.strftime("%Y%m%d")}.json'
    p.write_text(json.dumps(result, indent=2, default=str))
    print(f'\n[done] saved {p}')


if __name__ == '__main__':
    main()
