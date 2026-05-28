"""Pull GSC striking-distance + top-pages data for SEO action planning.

Outputs:
  data/audit_output/gsc_striking_distance_<DATE>.json
    - queries at positions 5-15 with >=50 impressions and <2% CTR
  data/audit_output/gsc_top_pages_<DATE>.json
    - top 20 pages by impressions (for FAQ rollout + intlinks targeting)

Read-only. Uses service account.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials/google-service-account.json")
SITE = os.getenv("GSC_SITE_URL", "https://organizinglifeservices.com/")
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

OUT = Path("data/audit_output")
OUT.mkdir(parents=True, exist_ok=True)
TODAY = datetime.now(timezone.utc).date().isoformat()


def svc():
    creds = service_account.Credentials.from_service_account_file(CREDS, scopes=SCOPES)
    return build("searchconsole", "v1", credentials=creds)


def fetch_all(s, body):
    """Paginate through all rows."""
    rows = []
    start = 0
    while True:
        b = dict(body); b["startRow"] = start; b["rowLimit"] = 25000
        r = s.searchanalytics().query(siteUrl=SITE, body=b).execute()
        chunk = r.get("rows", [])
        rows.extend(chunk)
        if len(chunk) < 25000:
            break
        start += 25000
    return rows


def main():
    s = svc()
    end = datetime.now(timezone.utc).date() - timedelta(days=3)
    start = end - timedelta(days=28)
    base = {"startDate": start.isoformat(), "endDate": end.isoformat()}

    # 1. Query + page combinations
    qp_rows = fetch_all(s, dict(base, dimensions=["query", "page"]))
    print(f"[gsc] {len(qp_rows)} query+page rows")

    striking = []
    for r in qp_rows:
        q, p = r["keys"]
        imp = int(r.get("impressions", 0))
        clk = int(r.get("clicks", 0))
        pos = float(r.get("position", 0))
        ctr = float(r.get("ctr", 0))
        if imp >= 50 and 5.0 <= pos <= 15.0 and ctr < 0.02:
            striking.append({
                "query": q, "page": p,
                "impressions": imp, "clicks": clk,
                "ctr": round(ctr, 4), "position": round(pos, 2),
            })
    striking.sort(key=lambda x: x["impressions"], reverse=True)
    sd_path = OUT / f"gsc_striking_distance_{TODAY}.json"
    sd_path.write_text(json.dumps({
        "site_url": SITE, "date_range": [start.isoformat(), end.isoformat()],
        "filters": {"min_impressions": 50, "position_range": [5, 15], "max_ctr": 0.02},
        "count": len(striking), "rows": striking,
    }, indent=2))
    print(f"[gsc] {len(striking)} striking-distance queries -> {sd_path}")

    # 2. Top pages by impressions
    p_rows = fetch_all(s, dict(base, dimensions=["page"]))
    p_rows.sort(key=lambda r: int(r.get("impressions", 0)), reverse=True)
    top_pages = [{
        "page": r["keys"][0],
        "impressions": int(r["impressions"]),
        "clicks": int(r["clicks"]),
        "ctr": round(float(r.get("ctr", 0)), 4),
        "position": round(float(r.get("position", 0)), 2),
    } for r in p_rows[:30]]
    tp_path = OUT / f"gsc_top_pages_{TODAY}.json"
    tp_path.write_text(json.dumps({
        "site_url": SITE, "date_range": [start.isoformat(), end.isoformat()],
        "count": len(top_pages), "rows": top_pages,
    }, indent=2))
    print(f"[gsc] top {len(top_pages)} pages -> {tp_path}")

    # Console summary
    print("\n--- TOP 10 STRIKING-DISTANCE QUERIES ---")
    for r in striking[:10]:
        print(f"  pos {r['position']:>5.1f} | {r['impressions']:>4} imp | CTR {r['ctr']*100:>4.2f}% | {r['query']!r:50s} -> {r['page']}")

    print("\n--- TOP 10 PAGES BY IMPRESSIONS ---")
    for r in top_pages[:10]:
        print(f"  {r['impressions']:>5} imp | {r['clicks']:>3} clk | CTR {r['ctr']*100:>5.2f}% | pos {r['position']:>5.1f} | {r['page']}")


if __name__ == "__main__":
    main()
