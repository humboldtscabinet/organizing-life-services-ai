"""
SEO Crawler — single-UA storefront technical crawler.

Crawls every URL discovered from the Shopify sitemap with a normal
browser user-agent and extracts on-page SEO signals.

**Why not a "Googlebot" pass?** We used to crawl twice — once as a
browser, once spoofing the Googlebot UA — and diff the two to detect
cloaking. That comparison is worthless from any IP we control:
Shopify (and Google) verify Googlebot by *reverse DNS*, not by the
User-Agent string, so a spoofed Googlebot UA from a non-Google IP is
always served Shopify's 429 "Verifying your connection…" bot-challenge.
The result was a 100%-false-positive "blocked to Googlebot, CRITICAL"
signal. The authoritative "what does Google see" answer now comes from
the Google URL Inspection API (see `app/services/gsc_url_inspection.py`),
which reports Google's own crawl/index verdict per URL. Do NOT
reintroduce a spoofed-Googlebot crawl.

Per-page checks:
  - HTTP status, response time, page size
  - <title>, meta description, canonical, robots
  - H1 count, H1 text
  - JSON-LD schema @types
  - Image alt-text coverage
  - Open Graph + Twitter card coverage
"""

from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

UA_BROWSER = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
UA_GOOGLEBOT = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
)
UA_AUDITOR = (
    "Mozilla/5.0 (compatible; OLS-SEO-Auditor/1.0; "
    "+https://organizinglifeservices.com)"
)

CRAWL_TIMEOUT = 20
CRAWL_WORKERS = 8
MAX_URLS_DEFAULT = 250

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def discover_urls_verbose(
    site_url: str, ua: str = UA_BROWSER
) -> tuple[list[str], dict]:
    """
    Walk the sitemap index and return (urls, diagnostics).

    Diagnostics surface failures that would otherwise be silently swallowed
    (e.g. Shopify's 429 "Verifying your connection" bot-challenge), so an
    empty crawl never looks identical to a real empty sitemap.
    """
    seeds = [urljoin(site_url.rstrip("/") + "/", "sitemap.xml")]
    seen_sitemaps: set[str] = set()
    urls: list[str] = []
    sitemap_errors: list[dict] = []
    bot_challenge_detected = False

    def fetch(u: str) -> tuple[str, dict | None]:
        try:
            r = requests.get(
                u, timeout=CRAWL_TIMEOUT, headers={"User-Agent": ua}
            )
        except Exception as e:
            return "", {"url": u, "status": None, "reason": f"exception: {e}"}
        if not r.ok:
            return "", {
                "url": u,
                "status": r.status_code,
                "reason": f"http {r.status_code}",
            }
        return r.text, None

    queue = list(seeds)
    while queue:
        sm = queue.pop()
        if sm in seen_sitemaps:
            continue
        seen_sitemaps.add(sm)
        text, err = fetch(sm)
        if err:
            sitemap_errors.append(err)
            continue
        try:
            root = ET.fromstring(text.encode())
        except ET.ParseError as e:
            # Most common cause here is Shopify returning an HTML
            # bot-challenge page (status 200 with HTML body) instead of XML.
            snippet = text[:120].replace("\n", " ")
            looks_html = "<html" in text[:200].lower() or "doctype html" in text[:200].lower()
            if looks_html:
                bot_challenge_detected = True
            sitemap_errors.append({
                "url": sm,
                "status": 200,
                "reason": f"xml parse error ({e}); body starts: {snippet!r}",
            })
            continue
        tag = root.tag.split("}", 1)[-1]
        if tag == "sitemapindex":
            for loc in root.findall(".//sm:loc", _NS):
                if loc.text:
                    queue.append(loc.text.strip())
        elif tag == "urlset":
            for loc in root.findall(".//sm:loc", _NS):
                if loc.text:
                    urls.append(loc.text.strip())

    seen = set()
    out = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)

    diagnostics = {
        "sitemaps_fetched": sorted(seen_sitemaps),
        "sitemap_errors": sitemap_errors,
        "bot_challenge_detected": bot_challenge_detected,
        "urls_found": len(out),
    }
    return out, diagnostics


def discover_urls(site_url: str, ua: str = UA_BROWSER) -> list[str]:
    """Walk the sitemap index and return every URL listed."""
    urls, _ = discover_urls_verbose(site_url, ua=ua)
    return urls


def audit_page(url: str, ua: str = UA_BROWSER) -> dict:
    """Fetch a single URL and extract SEO signals."""
    t0 = time.time()
    try:
        r = requests.get(
            url,
            timeout=CRAWL_TIMEOUT,
            headers={"User-Agent": ua},
            allow_redirects=True,
        )
        elapsed = time.time() - t0
    except Exception as e:
        return {"url": url, "ua": ua, "error": str(e), "ok": False}

    info: dict = {
        "url": url,
        "ua": ua,
        "final_url": r.url,
        "status": r.status_code,
        "response_ms": round(elapsed * 1000, 0),
        "size_kb": round(len(r.content) / 1024, 1),
        "ok": r.ok,
    }
    ctype = r.headers.get("Content-Type") or ""
    if not r.ok or "text/html" not in ctype:
        return info

    soup = BeautifulSoup(r.content, "lxml")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    meta_desc_tag = soup.find(
        "meta", attrs={"name": re.compile(r"^description$", re.I)}
    )
    meta_desc = (meta_desc_tag.get("content", "") if meta_desc_tag else "").strip()
    canonical_tag = soup.find(
        "link", rel=lambda v: bool(v) and "canonical" in v
    )
    canonical = canonical_tag.get("href") if canonical_tag else ""
    robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    robots = robots_tag.get("content", "") if robots_tag else ""

    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2_count = len(soup.find_all("h2"))
    h3_count = len(soup.find_all("h3"))

    imgs = soup.find_all("img")
    img_total = len(imgs)
    img_no_alt = sum(1 for i in imgs if not (i.get("alt") or "").strip())

    og_present = bool(soup.find("meta", property=re.compile(r"^og:")))
    twitter_present = bool(
        soup.find("meta", attrs={"name": re.compile(r"^twitter:", re.I)})
    )
    hreflang_count = len(
        soup.find_all(
            "link",
            rel=lambda v: bool(v) and "alternate" in v,
            hreflang=True,
        )
    )

    schema_types: list[str] = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        def walk(d):
            if isinstance(d, dict):
                t = d.get("@type")
                if t:
                    if isinstance(t, list):
                        schema_types.extend(t)
                    else:
                        schema_types.append(t)
                for v in d.values():
                    walk(v)
            elif isinstance(d, list):
                for v in d:
                    walk(v)

        walk(data)

    text = soup.get_text(" ", strip=True)
    word_count = len(text.split())

    issues = []
    if not title:
        issues.append("missing_title")
    elif len(title) < 30:
        issues.append("title_too_short")
    elif len(title) > 65:
        issues.append("title_too_long")
    if not meta_desc:
        issues.append("missing_meta_description")
    elif len(meta_desc) < 70:
        issues.append("meta_description_too_short")
    elif len(meta_desc) > 165:
        issues.append("meta_description_too_long")
    if len(h1s) == 0:
        issues.append("missing_h1")
    elif len(h1s) > 1:
        issues.append("multiple_h1")
    if not canonical:
        issues.append("missing_canonical")
    if "noindex" in (robots or "").lower():
        issues.append("noindex")
    if img_total and img_no_alt / img_total > 0.2:
        issues.append("low_alt_text_coverage")
    if not og_present:
        issues.append("missing_open_graph")
    if not schema_types:
        issues.append("missing_schema")
    if word_count < 200:
        issues.append("thin_content")
    if info["size_kb"] > 1500:
        issues.append("page_too_heavy")
    if info["response_ms"] > 2000:
        issues.append("slow_response")

    info.update({
        "title": title,
        "title_len": len(title),
        "meta_description": meta_desc,
        "meta_description_len": len(meta_desc),
        "canonical": canonical,
        "robots": robots,
        "h1_count": len(h1s),
        "h1_first": h1s[0] if h1s else "",
        "h2_count": h2_count,
        "h3_count": h3_count,
        "img_total": img_total,
        "img_no_alt": img_no_alt,
        "alt_coverage_pct": (
            round((1 - img_no_alt / img_total) * 100, 1) if img_total else 100
        ),
        "og_present": og_present,
        "twitter_card": twitter_present,
        "hreflang_count": hreflang_count,
        "schema_types": sorted(set(schema_types)),
        "word_count": word_count,
        "issues": issues,
    })
    return info


def crawl_site(
    site_url: str,
    ua: str = UA_BROWSER,
    max_urls: int = MAX_URLS_DEFAULT,
    workers: int = CRAWL_WORKERS,
    urls: list[str] | None = None,
) -> dict:
    """
    Crawl every URL with one UA, return per-page + aggregate results.
    """
    if urls is None:
        urls = discover_urls(site_url, ua=ua)
    urls = urls[:max_urls]

    pages: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(audit_page, u, ua): u for u in urls}
        for fut in as_completed(futs):
            pages.append(fut.result())

    ok = [p for p in pages if p.get("ok")]
    issue_counts: dict[str, int] = defaultdict(int)
    schema_counts: dict[str, int] = defaultdict(int)
    status_counts: dict[str, int] = defaultdict(int)

    for p in ok:
        for iss in p.get("issues", []):
            issue_counts[iss] += 1
        for t in p.get("schema_types", []):
            schema_counts[t] += 1
    for p in pages:
        status_counts[str(p.get("status", "ERR"))] += 1

    avg_resp = sum(p.get("response_ms", 0) for p in ok) / len(ok) if ok else 0
    avg_size = sum(p.get("size_kb", 0) for p in ok) / len(ok) if ok else 0

    return {
        "ua": ua,
        "urls_discovered": len(urls),
        "urls_crawled": len(pages),
        "urls_ok": len(ok),
        "status_counts": dict(status_counts),
        "avg_response_ms": round(avg_resp, 0),
        "avg_size_kb": round(avg_size, 1),
        "issue_counts": dict(sorted(issue_counts.items(), key=lambda x: -x[1])),
        "schema_type_coverage": dict(
            sorted(schema_counts.items(), key=lambda x: -x[1])
        ),
        "pages": pages,
    }


def storefront_crawl(
    site_url: str, max_urls: int = MAX_URLS_DEFAULT
) -> dict:
    """
    Crawl every sitemap URL once with a browser UA and return the
    per-page + aggregate results plus sitemap-discovery diagnostics.

    Returns:
        {
          "browser": <crawl_site result>,   # primary crawl payload
          "sitemap_diagnostics": {...},     # surfaces 429 / bot-challenge
        }

    NOTE: the key is named "browser" (not "crawl") for backward
    compatibility with downstream consumers that previously read the
    browser arm of the old dual-UA result.
    """
    urls, sitemap_diagnostics = discover_urls_verbose(site_url, ua=UA_BROWSER)
    urls = urls[:max_urls]

    browser = crawl_site(site_url, ua=UA_BROWSER, urls=urls)

    return {
        "browser": browser,
        "sitemap_diagnostics": sitemap_diagnostics,
    }


def dual_ua_crawl(
    site_url: str, max_urls: int = MAX_URLS_DEFAULT
) -> dict:
    """Deprecated alias for `storefront_crawl`.

    Kept so existing callers keep working. The Googlebot pass was removed
    (it produced only false positives — see the module docstring), so this
    now performs a single browser-UA crawl.
    """
    return storefront_crawl(site_url, max_urls=max_urls)
