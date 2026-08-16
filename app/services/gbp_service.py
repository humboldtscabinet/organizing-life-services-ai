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
import time
from datetime import datetime, timedelta
from typing import Any

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
    return {"Authorization": f"Bearer {creds.token}"}


def _fetch_multi_daily_metrics_params(start_date, end_date) -> list[tuple[str, Any]]:
    """
    Build GBP Performance API query params.

    Google documents fetchMultiDailyMetricsTimeSeries as GET with repeated
    dailyMetrics query params and an empty request body.
    """
    params: list[tuple[str, Any]] = []
    params.extend(("dailyMetrics", metric) for metric in DAILY_METRICS)
    params.extend(
        [
            ("dailyRange.start_date.year", start_date.year),
            ("dailyRange.start_date.month", start_date.month),
            ("dailyRange.start_date.day", start_date.day),
            ("dailyRange.end_date.year", end_date.year),
            ("dailyRange.end_date.month", end_date.month),
            ("dailyRange.end_date.day", end_date.day),
        ]
    )
    return params


def _iter_daily_metric_series(data: dict) -> list[dict]:
    """Flatten the GBP multi-daily response into daily metric series records."""
    flattened = []
    for multi_series in data.get("multiDailyMetricTimeSeries", []):
        daily_series = multi_series.get("dailyMetricTimeSeries", [])
        if isinstance(daily_series, dict):
            daily_series = [daily_series]
        flattened.extend(daily_series)
    return flattened


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

    params = _fetch_multi_daily_metrics_params(start_date, end_date)
    resp = None
    for attempt in range(3):
        resp = httpx.get(
            url,
            headers=headers,
            params=params,
            timeout=60,
        )
        if resp.status_code == 429 and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        break

    if resp is not None and resp.status_code in {401, 403, 429}:
        return _gbp_access_unavailable(db, location_id, resp.status_code, resp.text)

    resp.raise_for_status()
    data = resp.json()

    rows_inserted = 0
    rows_updated = 0
    for daily_ts in _iter_daily_metric_series(data):
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

            existing = (
                db.query(GBPInsight)
                .filter(
                    GBPInsight.metric_name == metric_name,
                    GBPInsight.period_start == date_obj,
                    GBPInsight.data["location_id"].astext == location_id,
                )
                .first()
            )

            if existing:
                existing.metric_value = value
                existing.period_end = date_obj
                existing.data = {
                    "location_id": location_id,
                    "source": "performance_api",
                }
                rows_updated += 1
            else:
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
            "rows_updated": rows_updated,
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
        "rows_updated": rows_updated,
    }


def _gbp_access_unavailable(
    db: Session,
    location_id: str,
    status_code: int,
    body: str,
) -> dict[str, Any]:
    """Record a gbp:access OpsAlert and skip the rest of the pull.

    Never writes to GBP. 403 = access denied; 429 = retry later.
    """
    from app.services.ops_alert_service import create_alert

    snippet = (body or "").replace("\n", " ")[:300]
    severity = "WARNING" if status_code == 429 else "CRITICAL"
    try:
        create_alert(
            db,
            source="gbp",
            severity=severity,
            title="GBP Performance API access blocked",
            message=(
                f"HTTP {status_code} pulling {location_id}. "
                "Keep NAP/schema in Shopify; do not invent GBP writes."
            ),
            fingerprint="gbp:access",
            details={"http_status": status_code, "location_id": location_id, "body": snippet},
        )
    except Exception:
        pass
    db.add(
        WorkflowLog(
            workflow_name="gbp_performance_pull",
            status="unavailable",
            payload={
                "location_id": location_id,
                "http_status": status_code,
            },
        )
    )
    db.commit()
    return {
        "status": "unavailable",
        "location_id": location_id,
        "http_status": status_code,
        "detail": f"GBP Performance API HTTP {status_code}",
    }
