"""
Google URL Inspection API helper.

This is the authoritative "what does Google actually see?" signal. Unlike a
spoofed-Googlebot HTTP crawl (which Shopify blocks from any non-Google IP),
the URL Inspection API reports Google's own crawl/index verdict for a URL,
fetched from Search Console's index.

Auth: reuses the existing GSC service account. The read-only Search Console
scope (`webmasters.readonly`) is sufficient for URL inspection.

Quota (per Search Console property): 2,000 inspections/day, 600/min — far
more than a weekly audit needs.

Docs: https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
"""

from __future__ import annotations

import time

GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def build_inspection_service(creds_path: str):
    """Build a Search Console v1 service client from a service-account file."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        str(creds_path), scopes=GSC_SCOPES
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def inspect_url(svc, site_url: str, url: str, language_code: str = "en-US") -> dict:
    """
    Inspect a single URL. Returns a flattened dict of the signals we care
    about (never raises — failures are captured in the returned dict).
    """
    body = {
        "inspectionUrl": url,
        "siteUrl": site_url,
        "languageCode": language_code,
    }
    try:
        resp = (
            svc.urlInspection()
            .index()
            .inspect(body=body)
            .execute()
        )
    except Exception as e:  # noqa: BLE001 - report, don't crash the audit
        return {"url": url, "error": str(e)}

    result = resp.get("inspectionResult", {}) or {}
    idx = result.get("indexStatusResult", {}) or {}
    mob = result.get("mobileUsabilityResult", {}) or {}
    rich = result.get("richResultsResult", {}) or {}

    user_canonical = idx.get("userCanonical", "")
    google_canonical = idx.get("googleCanonical", "")

    return {
        "url": url,
        "verdict": idx.get("verdict", ""),                # PASS/PARTIAL/FAIL/NEUTRAL
        "coverage_state": idx.get("coverageState", ""),
        "robots_txt_state": idx.get("robotsTxtState", ""),
        "indexing_state": idx.get("indexingState", ""),
        "page_fetch_state": idx.get("pageFetchState", ""),
        "last_crawl_time": idx.get("lastCrawlTime", ""),
        "crawled_as": idx.get("crawledAs", ""),
        "user_canonical": user_canonical,
        "google_canonical": google_canonical,
        "canonical_mismatch": bool(
            user_canonical
            and google_canonical
            and user_canonical != google_canonical
        ),
        "mobile_verdict": mob.get("verdict", ""),
        "rich_results_verdict": rich.get("verdict", ""),
        "inspection_link": result.get("inspectionResultLink", ""),
    }


def inspect_urls(
    svc,
    site_url: str,
    urls: list[str],
    max_calls: int = 50,
    pause_s: float = 0.12,
) -> list[str] | list[dict]:
    """
    Inspect up to `max_calls` URLs sequentially. A small pause keeps us well
    under the 600/min per-minute quota. Returns a list of per-URL dicts.
    """
    out: list[dict] = []
    for url in urls[:max_calls]:
        out.append(inspect_url(svc, site_url, url))
        if pause_s:
            time.sleep(pause_s)
    return out


def summarize(results: list[dict]) -> dict:
    """Aggregate inspection results into headline counts + the problem rows."""
    verdict_counts: dict[str, int] = {}
    coverage_counts: dict[str, int] = {}
    errors = 0
    problems: list[dict] = []

    for r in results:
        if r.get("error"):
            errors += 1
            problems.append(r)
            continue
        v = r.get("verdict") or "UNKNOWN"
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
        cov = r.get("coverage_state") or "UNKNOWN"
        coverage_counts[cov] = coverage_counts.get(cov, 0) + 1

        not_indexed = "indexed" not in cov.lower()
        if v != "PASS" or not_indexed or r.get("canonical_mismatch"):
            problems.append(r)

    return {
        "inspected": len(results),
        "errors": errors,
        "verdict_counts": verdict_counts,
        "coverage_counts": coverage_counts,
        "problems": problems,
    }
