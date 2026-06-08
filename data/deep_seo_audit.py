"""
Deep SEO Audit — CLI runner (laptop-friendly, no Docker required)
=================================================================

Mirrors `app/services/seo_audit_service.run_deep_seo_audit` but runs
standalone without the API/Postgres dependency. Useful for ad-hoc audits
from a developer laptop.

What it does:
  1. GSC live pull: current 28d vs prior 28d (with impression-weighted
     position in addition to the raw "avg position").
  2. GA4 live pull: all-traffic + organic-only, current vs prior.
  3. **Dual-UA technical crawl** — every sitemap URL is fetched both as a
     normal browser and as Googlebot, then the responses are diffed to
     expose Shopify bot-blocking / cloaking.
  4. Markdown + JSON report under `data/audit_output/`.

For the canonical, persistent version that writes to Postgres + Sheets,
hit `POST /api/seo/audit/deep` instead.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services import seo_crawler  # noqa: E402
from app.services import gsc_url_inspection  # noqa: E402

from google.oauth2 import service_account  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402


ENV_PATH = PROJECT_ROOT / ".env"
OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env(ENV_PATH)


def _cfg(key: str, default: str = "") -> str:
    """Prefer a real environment variable (CI), fall back to .env (laptop)."""
    return os.getenv(key) or ENV.get(key, default)


SITE_URL = _cfg("GSC_SITE_URL", "https://organizinglifeservices.com/").rstrip("/") + "/"
GA4_PROPERTY_ID = _cfg("GA4_PROPERTY_ID", "")
CREDS_PATH = PROJECT_ROOT / "credentials" / "google-service-account.json"

GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
GA4_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

MAX_URLS = int(os.getenv("DEEP_AUDIT_MAX_URLS", "250"))
INSPECT_TOP_N = int(os.getenv("DEEP_AUDIT_INSPECT_TOP_N", "50"))

TODAY = datetime.now(timezone.utc).date()
GSC_END = TODAY - timedelta(days=3)
GSC_CUR_START = GSC_END - timedelta(days=27)
GSC_PRV_END = GSC_CUR_START - timedelta(days=1)
GSC_PRV_START = GSC_PRV_END - timedelta(days=27)


# ---- GSC -------------------------------------------------------------------
def gsc_client():
    creds = service_account.Credentials.from_service_account_file(
        str(CREDS_PATH), scopes=GSC_SCOPES
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def gsc_query(svc, start, end, dimensions, row_limit=25000):
    rows = []
    start_row = 0
    while True:
        body = {
            "startDate": str(start),
            "endDate": str(end),
            "dimensions": dimensions,
            "rowLimit": row_limit,
            "startRow": start_row,
        }
        resp = svc.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
        batch = resp.get("rows", [])
        rows.extend(batch)
        if len(batch) < row_limit:
            break
        start_row += row_limit
        if start_row > 100000:
            break
    return rows


def gsc_totals(rows):
    c = sum(r.get("clicks", 0) for r in rows)
    i = sum(r.get("impressions", 0) for r in rows)
    if i > 0:
        ctr = c / i
        weighted_pos = (
            sum(r.get("position", 0) * r.get("impressions", 0) for r in rows) / i
        )
    else:
        ctr, weighted_pos = 0.0, 0.0
    raw_pos = (
        sum(r.get("position", 0) for r in rows) / len(rows) if rows else 0.0
    )
    return {
        "clicks": c,
        "impressions": i,
        "ctr": ctr,
        "avg_position_weighted": weighted_pos,
        "avg_position_unweighted": raw_pos,
    }


def pct_change(curr, prev):
    if prev in (0, None):
        return None
    return (curr - prev) / prev * 100.0


def run_gsc_block() -> dict:
    print(f"[GSC] Pulling current ({GSC_CUR_START} → {GSC_END}) vs prior "
          f"({GSC_PRV_START} → {GSC_PRV_END})…", file=sys.stderr)
    svc = gsc_client()

    cur_rows = gsc_query(svc, GSC_CUR_START, GSC_END, [])
    prv_rows = gsc_query(svc, GSC_PRV_START, GSC_PRV_END, [])

    cur_tot = gsc_totals(cur_rows)
    prv_tot = gsc_totals(prv_rows)

    deltas = {
        "clicks_delta_pct": pct_change(cur_tot["clicks"], prv_tot["clicks"]),
        "impressions_delta_pct": pct_change(cur_tot["impressions"],
                                            prv_tot["impressions"]),
        "ctr_delta_pp": (
            (cur_tot["ctr"] - prv_tot["ctr"]) * 100
            if prv_tot["impressions"] else None
        ),
        "position_delta_weighted": (
            cur_tot["avg_position_weighted"] - prv_tot["avg_position_weighted"]
            if prv_tot["impressions"] else None
        ),
        "position_delta_unweighted": (
            cur_tot["avg_position_unweighted"] - prv_tot["avg_position_unweighted"]
            if prv_tot["impressions"] else None
        ),
    }

    cur_q = gsc_query(svc, GSC_CUR_START, GSC_END, ["query"])
    prv_q = gsc_query(svc, GSC_PRV_START, GSC_PRV_END, ["query"])

    def by_key(rows, idx=0):
        return {r["keys"][idx]: r for r in rows}

    cur_q_map = by_key(cur_q); prv_q_map = by_key(prv_q)

    movers = []
    for q, c in cur_q_map.items():
        p = prv_q_map.get(q)
        prev_pos = p.get("position", 0) if p else None
        prev_clicks = p.get("clicks", 0) if p else 0
        prev_imp = p.get("impressions", 0) if p else 0
        movers.append({
            "query": q,
            "clicks": c.get("clicks", 0),
            "prev_clicks": prev_clicks,
            "clicks_delta": c.get("clicks", 0) - prev_clicks,
            "impressions": c.get("impressions", 0),
            "prev_impressions": prev_imp,
            "position": round(c.get("position", 0), 1),
            "prev_position": round(prev_pos, 1) if prev_pos else None,
            "position_delta": (
                round(c.get("position", 0) - prev_pos, 1) if prev_pos else None
            ),
        })

    top_winners = sorted(movers, key=lambda x: x["clicks_delta"], reverse=True)[:20]
    top_losers = sorted(
        [m for m in movers if m["prev_clicks"] > 0],
        key=lambda x: x["clicks_delta"],
    )[:20]

    cur_qp = gsc_query(svc, GSC_CUR_START, GSC_END, ["query", "page"])
    opp = sorted([
        {
            "query": r["keys"][0],
            "page": r["keys"][1],
            "impressions": r.get("impressions", 0),
            "ctr": round(r.get("ctr", 0), 4),
            "position": round(r.get("position", 0), 1),
        }
        for r in cur_qp
        if r.get("impressions", 0) >= 30
        and 1 <= r.get("position", 0) <= 20
        and r.get("ctr", 0) < 0.03
    ], key=lambda x: x["impressions"], reverse=True)

    striking = sorted([
        {
            "query": r["keys"][0],
            "page": r["keys"][1],
            "impressions": r.get("impressions", 0),
            "clicks": r.get("clicks", 0),
            "position": round(r.get("position", 0), 1),
        }
        for r in cur_qp
        if 8 <= r.get("position", 0) <= 20 and r.get("impressions", 0) >= 10
    ], key=lambda x: x["impressions"], reverse=True)

    cur_p = gsc_query(svc, GSC_CUR_START, GSC_END, ["page"])
    top_pages = sorted([
        {
            "page": r["keys"][0],
            "impressions": r.get("impressions", 0),
            "clicks": r.get("clicks", 0),
            "position": round(r.get("position", 0), 1),
        }
        for r in cur_p
    ], key=lambda x: x["impressions"], reverse=True)

    return {
        "windows": {
            "current": {"start": str(GSC_CUR_START), "end": str(GSC_END)},
            "prior":   {"start": str(GSC_PRV_START), "end": str(GSC_PRV_END)},
        },
        "totals_current": cur_tot,
        "totals_prior": prv_tot,
        "deltas": deltas,
        "top_query_winners": top_winners,
        "top_query_losers": top_losers,
        "ctr_opportunities": opp[:30],
        "striking_distance": striking[:30],
        "top_pages": top_pages,
    }


# ---- GA4 -------------------------------------------------------------------
def run_ga4_block() -> dict | None:
    if not GA4_PROPERTY_ID:
        return None
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest, FilterExpression, Filter,
        )
    except ImportError:
        return {"error": "google-analytics-data not installed"}

    creds = service_account.Credentials.from_service_account_file(
        str(CREDS_PATH), scopes=GA4_SCOPES
    )
    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{GA4_PROPERTY_ID}"

    def run(start, end, dims, mets, filt=None, limit=10000):
        req = RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
            dimensions=[Dimension(name=d) for d in dims],
            metrics=[Metric(name=m) for m in mets],
            limit=limit,
        )
        if filt is not None:
            req.dimension_filter = filt
        return client.run_report(req)

    cur_start = TODAY - timedelta(days=28)
    cur_end = TODAY - timedelta(days=1)
    prv_start = cur_start - timedelta(days=28)
    prv_end = cur_start - timedelta(days=1)

    def totals(resp):
        out = defaultdict(float)
        for row in resp.rows:
            for i, mv in enumerate(row.metric_values):
                out[resp.metric_headers[i].name] += float(mv.value or 0)
        return dict(out)

    overall = ["sessions", "activeUsers", "newUsers", "screenPageViews",
               "engagementRate", "averageSessionDuration", "bounceRate"]
    cur_all = run(cur_start, cur_end, [], overall)
    prv_all = run(prv_start, prv_end, [], overall)

    organic_filter = FilterExpression(
        filter=Filter(
            field_name="sessionDefaultChannelGroup",
            string_filter=Filter.StringFilter(
                value="Organic Search", case_sensitive=False
            ),
        )
    )
    org_mets = ["sessions", "activeUsers", "screenPageViews",
                "engagementRate", "conversions"]
    cur_org = run(cur_start, cur_end, [], org_mets, filt=organic_filter)
    prv_org = run(prv_start, prv_end, [], org_mets, filt=organic_filter)

    return {
        "windows": {
            "current": {"start": str(cur_start), "end": str(cur_end)},
            "prior":   {"start": str(prv_start), "end": str(prv_end)},
        },
        "all_traffic_current": totals(cur_all),
        "all_traffic_prior":   totals(prv_all),
        "organic_current":     totals(cur_org),
        "organic_prior":       totals(prv_org),
    }


# ---- Dual-UA crawl (delegated to shared module) ----------------------------
def run_dual_crawl() -> dict:
    print(f"[CRAWL] Storefront crawl (browser UA), cap {MAX_URLS}…",
          file=sys.stderr)
    return seo_crawler.storefront_crawl(SITE_URL, max_urls=MAX_URLS)


# ---- URL Inspection (authoritative Googlebot view) -------------------------
def run_inspection_block(gsc: dict) -> dict | None:
    """
    Inspect the top-N pages by impressions through the Google URL Inspection
    API — the authoritative "what does Google see" signal that replaces the
    old (false-positive) spoofed-Googlebot crawl.
    """
    top_pages = (gsc or {}).get("top_pages") or []
    urls = [p["page"] for p in top_pages if p.get("page")][:INSPECT_TOP_N]
    if not urls:
        return None

    print(f"[INSPECT] Google URL Inspection on top {len(urls)} pages "
          f"by impressions…", file=sys.stderr)
    try:
        svc = gsc_url_inspection.build_inspection_service(str(CREDS_PATH))
        results = gsc_url_inspection.inspect_urls(
            svc, SITE_URL, urls, max_calls=INSPECT_TOP_N
        )
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "requested": len(urls)}

    summary = gsc_url_inspection.summarize(results)
    summary["results"] = results
    return summary


# ---- Report renderer -------------------------------------------------------
def fmt_pct(v):
    return "n/a" if v is None else f"{v:+.1f}%"


def fmt_int(v):
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return str(v)


def render_md(gsc, ga4, crawl, inspection) -> str:
    L = []
    add = L.append
    add("# Deep SEO Audit — organizinglifeservices.com")
    add(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")

    add("## 1. Executive Summary\n")
    cw, pw = gsc["windows"]["current"], gsc["windows"]["prior"]
    add(f"**Windows:** current `{cw['start']} → {cw['end']}` vs prior "
        f"`{pw['start']} → {pw['end']}`\n")
    cur, prv, d = gsc["totals_current"], gsc["totals_prior"], gsc["deltas"]
    add("| Metric | Prior | Current | Δ |")
    add("|---|---:|---:|---:|")
    add(f"| Clicks | {fmt_int(prv['clicks'])} | {fmt_int(cur['clicks'])} | "
        f"{fmt_pct(d['clicks_delta_pct'])} |")
    add(f"| Impressions | {fmt_int(prv['impressions'])} | "
        f"{fmt_int(cur['impressions'])} | {fmt_pct(d['impressions_delta_pct'])} |")
    add(f"| CTR | {prv['ctr']*100:.2f}% | {cur['ctr']*100:.2f}% | "
        f"{(d['ctr_delta_pp'] or 0):+.2f} pp |")
    add(f"| **Weighted avg position** | {prv['avg_position_weighted']:.1f} | "
        f"{cur['avg_position_weighted']:.1f} | "
        f"{(d['position_delta_weighted'] or 0):+.1f} |")
    add(f"| Raw avg position | {prv['avg_position_unweighted']:.1f} | "
        f"{cur['avg_position_unweighted']:.1f} | "
        f"{(d['position_delta_unweighted'] or 0):+.1f} |")
    add("")
    add("_The **weighted** position weights each ranking by its impression "
        "volume — much more meaningful than the raw GSC average._\n")

    if ga4 and "error" not in ga4:
        add("## 2. GA4 (28-day comparison)\n")
        all_c, all_p = ga4["all_traffic_current"], ga4["all_traffic_prior"]
        org_c, org_p = ga4["organic_current"], ga4["organic_prior"]
        add("| Metric | Prior | Current | Δ |")
        add("|---|---:|---:|---:|")
        for label, key in [("Sessions", "sessions"), ("Users", "activeUsers"),
                           ("Page views", "screenPageViews")]:
            add(f"| {label} | {fmt_int(all_p.get(key,0))} | "
                f"{fmt_int(all_c.get(key,0))} | "
                f"{fmt_pct(pct_change(all_c.get(key,0), all_p.get(key,0)))} |")
        add("")
        add("**Organic only**")
        add("| Metric | Prior | Current | Δ |")
        add("|---|---:|---:|---:|")
        for label, key in [("Organic sessions", "sessions"),
                           ("Organic users", "activeUsers"),
                           ("Organic conversions", "conversions")]:
            add(f"| {label} | {fmt_int(org_p.get(key,0))} | "
                f"{fmt_int(org_c.get(key,0))} | "
                f"{fmt_pct(pct_change(org_c.get(key,0), org_p.get(key,0)))} |")
        add("")

    add("## 3. Storefront SEO Crawl\n")
    b = crawl["browser"]
    sm_diag = crawl.get("sitemap_diagnostics") or {}
    if b["urls_crawled"] == 0:
        add("> ⚠️ **No URLs were crawled.** Sitemap discovery returned an "
            "empty list — this is almost always an infrastructure issue "
            "(Shopify bot-challenge / IP rate-limit), not a real SEO finding.")
        if sm_diag.get("bot_challenge_detected"):
            add("> ")
            add("> Detected: Shopify served an HTML bot-challenge page "
                "(\"Verifying your connection…\") instead of `sitemap.xml`. "
                "Re-run from a different IP, or wait ~15 min for the rate-limit "
                "to clear.")
        errs = sm_diag.get("sitemap_errors") or []
        if errs:
            add("> ")
            add("> Sitemap fetch errors:")
            for e in errs[:10]:
                add(f"> - `{e.get('url')}` → {e.get('reason')}")
        add("")
    add("_Crawled with a browser user-agent. This reflects what a normal "
        "visitor (and our auditor) sees on the storefront. For Google's own "
        "crawl/index verdict, see Section 3a._\n")
    add(f"- URLs crawled: {b['urls_crawled']}")
    add(f"- 200 OK: {b['urls_ok']}")
    add(f"- Status counts: {b['status_counts']}")
    add(f"- Avg response: {b['avg_response_ms']} ms — Avg size: "
        f"{b['avg_size_kb']} KB\n")

    add("### Issue counts (browser view)")
    add("| Issue | # pages |")
    add("|---|---:|")
    for iss, n in b["issue_counts"].items():
        add(f"| {iss} | {n} |")
    add("")

    add("## 3a. Google URL Inspection — authoritative index status\n")
    if not inspection:
        add("_No URL inspection data this run (no top pages available)._\n")
    elif inspection.get("error"):
        add(f"> ⚠️ URL Inspection failed: `{inspection['error']}` "
            f"(requested {inspection.get('requested', 0)} URLs).\n")
    else:
        add(f"_Inspected the top {inspection['inspected']} pages by "
            f"impressions via the Google Search Console URL Inspection API — "
            f"this is Google's own verdict, not a spoofed crawl._\n")
        add(f"- Verdicts: {inspection['verdict_counts']}")
        if inspection.get("errors"):
            add(f"- Inspection errors: {inspection['errors']}")
        add("")
        add("**Coverage states**")
        add("| State | # pages |")
        add("|---|---:|")
        for state, n in sorted(
            inspection["coverage_counts"].items(), key=lambda x: -x[1]
        ):
            add(f"| {state} | {n} |")
        add("")
        problems = inspection.get("problems") or []
        if problems:
            add(f"### ⚠️ Pages needing attention ({len(problems)})")
            add("| Page | Verdict | Coverage | Canonical mismatch | "
                "Last crawl |")
            add("|---|---|---|:--:|---|")
            for p in problems[:30]:
                if p.get("error"):
                    add(f"| `{p['url']}` | ERROR | {p['error']} | | |")
                    continue
                mismatch = "⚠️" if p.get("canonical_mismatch") else ""
                add(f"| `{p['url']}` | {p.get('verdict','')} | "
                    f"{p.get('coverage_state','')} | {mismatch} | "
                    f"{p.get('last_crawl_time','')} |")
            add("")
        else:
            add("✅ All inspected pages are indexed with no canonical "
                "mismatches.\n")

    add("## 4. Top Click Gainers (current vs prior 28d)")
    add("| Query | Clicks | Δ | Position |")
    add("|---|---:|---:|---:|")
    for m in gsc["top_query_winners"][:15]:
        add(f"| {m['query']} | {m['clicks']} | +{m['clicks_delta']} | "
            f"{m['position']} |")
    add("")

    add("## 5. CTR Opportunities (free clicks waiting)")
    add("| Query | Page | Impr. | CTR | Pos |")
    add("|---|---|---:|---:|---:|")
    for o in gsc["ctr_opportunities"][:20]:
        add(f"| {o['query']} | `{o['page']}` | {o['impressions']} | "
            f"{o['ctr']*100:.2f}% | {o['position']} |")
    add("")

    add("## 6. Striking-Distance Queries")
    add("| Query | Page | Impr. | Clicks | Pos |")
    add("|---|---|---:|---:|---:|")
    for s in gsc["striking_distance"][:20]:
        add(f"| {s['query']} | `{s['page']}` | {s['impressions']} | "
            f"{s['clicks']} | {s['position']} |")
    add("")

    add("---")
    add("_Full per-page crawl data in the companion `.json` file._")
    return "\n".join(L)


def main():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_md = OUT_DIR / f"deep_seo_audit_{ts}.md"
    out_json = OUT_DIR / f"deep_seo_audit_{ts}.json"

    print("=" * 60, file=sys.stderr)
    print("Deep SEO Audit (CLI) starting", file=sys.stderr)
    print(f"Site: {SITE_URL}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    gsc = run_gsc_block()
    ga4 = run_ga4_block()
    crawl = run_dual_crawl()
    inspection = run_inspection_block(gsc)

    md = render_md(gsc, ga4, crawl, inspection)
    out_md.write_text(md)
    out_json.write_text(
        json.dumps({"gsc": gsc, "ga4": ga4, "crawl": crawl,
                    "inspection": inspection},
                   indent=2, default=str)
    )

    print(f"\nReport:   {out_md}", file=sys.stderr)
    print(f"Raw JSON: {out_json}", file=sys.stderr)
    print(out_md)


if __name__ == "__main__":
    main()
