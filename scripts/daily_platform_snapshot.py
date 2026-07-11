#!/usr/bin/env python3
"""
Daily platform snapshot for GitHub Actions or manual runs.

Pulls lightweight GSC and GA4 summaries without Postgres and writes JSON
artifacts under data/audit_output/ for trend review.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from google.analytics.data_v1beta import BetaAnalyticsDataClient  # noqa: E402
from google.analytics.data_v1beta.types import DateRange, Metric, RunReportRequest  # noqa: E402
from google.oauth2 import service_account  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _gsc_service():
    credentials_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=GSC_SCOPES,
    )
    return build("searchconsole", "v1", credentials=credentials)


def _pull_gsc_summary(site_url: str, days_back: int = 7) -> dict:
    service = _gsc_service()
    end_date = datetime.utcnow().date() - timedelta(days=3)
    start_date = end_date - timedelta(days=days_back)

    row_limit = 1000
    start_row = 0
    rows = []
    while True:
        body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": ["query", "page", "date"],
            "rowLimit": row_limit,
            "startRow": start_row,
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        batch = response.get("rows", [])
        rows.extend(batch)
        if len(batch) < row_limit:
            break
        start_row += row_limit

    total_clicks = sum(int(row.get("clicks", 0)) for row in rows)
    total_impressions = sum(int(row.get("impressions", 0)) for row in rows)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows_fetched": len(rows),
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
    }


def _pull_ga4_summary(property_id: str, days_back: int = 7) -> dict:
    credentials_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=credentials)

    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="screenPageViews"),
        ],
    )
    response = client.run_report(request)

    totals = {metric.name: 0 for metric in request.metrics}
    if response.rows:
        for idx, metric in enumerate(request.metrics):
            totals[metric.name] = int(response.rows[0].metric_values[idx].value or 0)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "metrics": totals,
    }


def main() -> int:
    site_url = os.environ.get("GSC_SITE_URL")
    property_id = os.environ.get("GA4_PROPERTY_ID")
    if not site_url or not property_id:
        print("GSC_SITE_URL and GA4_PROPERTY_ID are required", file=sys.stderr)
        return 1

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site_url": site_url,
        "ga4_property_id": property_id,
        "gsc": _pull_gsc_summary(site_url),
        "ga4": _pull_ga4_summary(property_id),
    }

    output_dir = REPO_ROOT / "data" / "audit_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"daily_platform_snapshot_{stamp}.json"
    output_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(json.dumps({"status": "success", "output_path": str(output_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
