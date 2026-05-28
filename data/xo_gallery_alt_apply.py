"""XO Gallery alt-text audit + apply.

XO Gallery images live in shop metafields `xo_gallery.gallery_NN` (JSON arrays
of {img, alt:{en: ...}, w, h}). This script:

  1. Pulls all xo_gallery.gallery_NN shop metafields (paginated)
  2. Parses each, scans every image for missing/empty `alt.en`
  3. Looks up the alt text from data/image_analysis_export.csv by filename
  4. Writes back updated gallery JSON (atomic per metafield)

Idempotent: only fills empty/missing alts; never overwrites existing alt text.

Run with --dry-run first to see what would change.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

import httpx

STORE = os.getenv('SHOPIFY_STORE'); CID = os.getenv('SHOPIFY_CLIENT_ID')
CS = os.getenv('SHOPIFY_CLIENT_SECRET'); API = os.getenv('SHOPIFY_API_VERSION', '2024-10')
CSV_PATH = 'data/image_analysis_export.csv'

# size-suffix patterns Shopify CDN appends, e.g. _500x, _600x600, _1024x1024
SIZE_SUFFIX = re.compile(r'_(?:\d+x\d+|\d+x|x\d+)(?=\.[a-zA-Z]+$)')


def normalize_filename(url_or_filename):
    """Strip path, query, and Shopify size suffix to get a base filename for matching."""
    name = os.path.basename(urlparse(url_or_filename).path or url_or_filename)
    # strip ?v=... query if present in basename
    name = name.split('?', 1)[0]
    # strip _500x type suffix
    name = SIZE_SUFFIX.sub('', name)
    return name.lower()


def load_csv_lookup():
    lookup = {}
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            alt = (row.get('alt_text') or '').strip()
            if not alt:
                continue
            for k in (row.get('filename'), row.get('image_url')):
                if k:
                    nk = normalize_filename(k)
                    lookup.setdefault(nk, alt)
    return lookup


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


def get_alt(img):
    """Return current alt text (en) from an XO image dict, '' if missing/empty."""
    a = img.get('alt')
    if isinstance(a, dict):
        return (a.get('en') or '').strip()
    if isinstance(a, str):
        return a.strip()
    return ''


def set_alt(img, value):
    """Set alt text preserving existing schema (dict-with-locales preferred)."""
    a = img.get('alt')
    if isinstance(a, dict):
        a['en'] = value
        img['alt'] = a
    else:
        img['alt'] = {'en': value}
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--fallback', action='store_true',
                    help='For images not found in CSV, generate a templated alt from the gallery title')
    args = ap.parse_args()

    if not all([STORE, CID, CS]): sys.exit('Missing SHOPIFY creds')
    lookup = load_csv_lookup()
    print(f'[csv] loaded {len(lookup)} unique alt entries from {CSV_PATH}')

    tok = httpx.post(f'https://{STORE}.myshopify.com/admin/oauth/access_token',
        json={'client_id': CID, 'client_secret': CS, 'grant_type': 'client_credentials'},
        timeout=30).json()['access_token']
    H = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    B = f'https://{STORE}.myshopify.com/admin/api/{API}'

    all_mfs = []
    url = f'{B}/metafields.json?limit=250&namespace=xo_gallery'
    while url:
        r = _retry(httpx.get, url, headers=H, timeout=30)
        all_mfs += r.json()['metafields']
        url = None
        for p in r.headers.get('Link', '').split(','):
            if 'rel="next"' in p: url = p.split(';')[0].strip().strip('<>')
        time.sleep(0.3)
    galleries = [m for m in all_mfs if m['key'].startswith('gallery_')]
    print(f'[xo] {len(galleries)} gallery metafields')

    grand_total = grand_missing = grand_filled = grand_unmatched = grand_fallback = 0
    galleries_updated = 0
    unmatched_samples = []

    for m in galleries:
        try:
            data = json.loads(m['value'])
        except Exception as e:
            print(f'  [skip] {m["key"]} parse error: {e}'); continue
        # Some galleries store {"images": [...]}; others store the list directly.
        if isinstance(data, list):
            imgs = data
            top_is_list = True
        elif isinstance(data, dict):
            imgs = data.get('images') or []
            top_is_list = False
        else:
            continue
        if not imgs: continue

        # Pull a clean title for fallback alts (only valid when top is dict)
        gtitle = ''
        if not top_is_list:
            t = data.get('title')
            if isinstance(t, dict):
                gtitle = (t.get('en') or '').strip()
            elif isinstance(t, str):
                gtitle = t.strip()
        # Strip pipes & extra whitespace
        gtitle_clean = re.sub(r'\s*\|\s*', ' ', gtitle).strip() if gtitle else ''

        missing = filled = unmatched = fb = 0
        changed = False
        idx = 0
        for img in imgs:
            idx += 1
            grand_total += 1
            if get_alt(img):
                continue
            missing += 1; grand_missing += 1
            src = img.get('img') or ''
            key = normalize_filename(src)
            alt = lookup.get(key)
            if alt:
                set_alt(img, alt)
                filled += 1; grand_filled += 1
                changed = True
            elif args.fallback and gtitle_clean:
                fb_alt = f'{gtitle_clean} — Organizing Life Services Tampa Bay estate sale, photo {idx}'
                # Trim to reasonable length
                if len(fb_alt) > 125:
                    fb_alt = fb_alt[:122].rstrip() + '...'
                set_alt(img, fb_alt)
                fb += 1; grand_fallback += 1
                changed = True
            else:
                unmatched += 1; grand_unmatched += 1
                if len(unmatched_samples) < 10:
                    unmatched_samples.append(src)

        if changed and not args.dry_run:
            new_val = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            r = _retry(httpx.put, f'{B}/metafields/{m["id"]}.json', headers=H, timeout=60,
                       json={'metafield': {'id': m['id'], 'value': new_val, 'type': 'json'}})
            r.raise_for_status()
            galleries_updated += 1
            time.sleep(0.6)
        if missing:
            print(f'  {m["key"]:14s} imgs={len(imgs):4d} missing={missing:3d} filled={filled:3d} fb={fb:3d} unmatched={unmatched:3d}{"  [DRY]" if args.dry_run and changed else ""}')

    print('\n=== SUMMARY ===')
    print(f'  total images        : {grand_total}')
    print(f'  with existing alt   : {grand_total - grand_missing}')
    print(f'  missing alt         : {grand_missing}')
    print(f'  filled from CSV     : {grand_filled}')
    print(f'  fallback templated  : {grand_fallback}')
    print(f'  unmatched (no fix)  : {grand_unmatched}')
    print(f'  galleries updated   : {galleries_updated}{" (DRY-RUN — nothing written)" if args.dry_run else ""}')
    if unmatched_samples:
        print('\n  Unmatched samples (first 10):')
        for s in unmatched_samples: print(f'    {s}')


if __name__ == '__main__':
    main()
