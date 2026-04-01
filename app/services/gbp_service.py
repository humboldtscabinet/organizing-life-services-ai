"""
Google Business Profile — Data Pull Service

Pulls performance metrics from GBP Performance API into Postgres.
Manual-approval mode: this service only READS data. No writes to GBP.

Requires:
  - My Business Account Management API (enabled in GCP)
  - My Business Business Information API (enabled in GCP)
  - Business Profile Performance API (enabled in GCP)
  - Service account added as a Manager on the GBP listing
"""

import os
from datetime import datetime, timedelta

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from sqlalchemy.orm import Session

from app.db.models import GBPInsight, WorkflowLog

GBP_SCOPES = ["https://www.googleapis.com/auth/business.manage"]

# Metrics available from the Business Profile Performance API
DAILY_METRICS = [
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
    "BUSINESS_DIRECTION_REQUESTS",
    "CALL_CLICKS",
    "WEBSITE_CLICKS",
]


def _get_gbp_credentials():
    """Build authenticated credentials for GBP APIs."""
    creds_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/credentials/google-service-account.json",
    )
    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=GBP_SCOPES
    )
    credentials.refresh(Request())
    return credentials


def _auth_headers() -> dict:
    """Return Authorization header dict with a fresh token."""
    creds = _get_gbp_credentials()
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }


# ===================== Discovery =====================


def discover_gbp_accounts() -> list:
    """
    List all GBP accounts accessible by the service account.

    Use this to find your account ID. The service account must be
    added as a Manager on the GBP account first.
    """
    headers = _auth_headers()
    url = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"

    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    accounts = []
    for acct in data.get("accounts", []):
        accounts.append({
            "name": acct.get("name"),           # e.g. "accounts/123456"
            "accountName": acct.get("accountName"),
            "type": acct.get("type"),
        })
    return accounts


def discover_gbp_locations(account_name: str) -> list:
    """
    List all locations under a GBP account.

    account_name: full resource name, e.g. "accounts/123456"
    """
    headers = _auth_headers()
    url = (
        f"https://mybusinessbusinessinformation.googleapis.com/v1/"
        f"{account_name}/locations"
        f"?readMask=name,title,storefrontAddress"
    )

    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    locations = []
    for loc in data.get("locations", []):
        locations.append({
            "name": loc.get("name"),             # e.g. "locations/789012"
            "title": loc.get("title"),
            "address": loc.get("storefrontAddress", {}),
        })
    return locations


# ===================== Data Pull =====================


def pull_gbp_data(
    db: Session,
    location_id: str = None,
    days_back: int = 28,
) -> dict:
    """
    Pull GBP performance metrics for the last N days.

    Uses the Business Profile Performance API
    fetchMultiDailyMetricsTimeSeries endpoint.

    location_id: full resource name, e.g. "locations/789012"
    """
    location_id = location_id or os.getenv("GBP_LOCATION_ID")
    if not location_id:
        raise ValueError(
            "GBP_LOCATION_ID is not set. "
            "Run /api/seo/gbp/discover first to find your location ID."
        )

    headers = _auth_headers()

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days_back)

    url = (
        f"https://businessprofileperformance.googleapis.com/v1/"
        f"{location_id}:fetchMultiDailyMetricsTimeSeries"
    )

    payload = {
        "dailyMetrics": DAILY_METRICS,
        "dailyRange": {
            "startDate": {
                "year": start_date.year,
                "month": start_date.month,
                "day": start_date.day,
            },
            "endDate": {
                "year": end_date.year,
                "month": end_date.month,
                "day": end_date.day,
            },
        },
    }

    resp = httpx.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    rows_inserted = 0
    time_series_list = data.get("multiDailyMetricTimeSeries", [])

    for series in time_series_list:
        daily_ts = series.get("dailyMetricTimeSeries", {})
        metric_name = daily_ts.get("dailyMetric", "UNKNOWN")

        dated_values = (
            daily_ts.get("timeSeries", {}).get("datedValues", [])
        )

        for point in dated_values:
            date_info = point.get("date", {})
            date_obj = datetime(
                year=date_info.get("year", 2026),
                month=date_info.get("month", 1),
                day=date_info.get("day", 1),
            )
            value = int(point.get("value", 0))

            record = GBPInsight(
                metric_name=metric_name,
                metric_value=value,
                period_start=date_obj,
                period_end=date_obj,
                data={
                    "location_id": location_id,
                    "source": "performance_api",
                },
            )
            db.add(record)
            rows_inserted += 1

    db.commit()

    # Log the workflow execution
    log_entry = WorkflowLog(
        workflow_name="gbp_performance_pull",
        status="success",
        payload={
            "location_id": location_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "rows_inserted": rows_inserted,
            "metrics_requested": DAILY_METRICS,
        },
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "location_id": location_id,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "rows_inserted": rows_inserted,
    }
