"""
Google Analytics 4 — Data Pull Service

Pulls analytics data from GA4 and stores it in Postgres.
Manual-approval mode: this service only READS data. No writes to GA4.
"""

import os
from datetime import datetime, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import GA4Data, WorkflowLog


def _upsert_ga4(db: Session, metric_name: str, dimension_name: str,
                dimension_value: str, date: datetime, metric_value: float,
                data: dict) -> str:
    """Insert or update a GA4 record. Returns 'inserted' or 'updated'."""
    existing = (
        db.query(GA4Data)
        .filter(
            and_(
                GA4Data.metric_name == metric_name,
                GA4Data.dimension_name == dimension_name,
                GA4Data.dimension_value == dimension_value,
                GA4Data.date == date,
            )
        )
        .first()
    )
    if existing:
        existing.metric_value = metric_value
        existing.data = data
        return "updated"
    else:
        record = GA4Data(
            metric_name=metric_name,
            metric_value=metric_value,
            dimension_name=dimension_name,
            dimension_value=dimension_value,
            date=date,
            data=data,
        )
        db.add(record)
        return "inserted"


def _get_ga4_client():
    """Build an authenticated GA4 API client using the service account."""
    credentials_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/credentials/google-service-account.json",
    )
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    return BetaAnalyticsDataClient()


def pull_ga4_data(
    db: Session,
    property_id: str = None,
    days_back: int = 7,
) -> dict:
    """
    Pull key metrics from GA4 for the last N days.

    Pulls: sessions, active users, page views, bounce rate, avg session duration
    Dimensions: date, page path, session source/medium

    All data is stored in the ga4_data table.
    """
    property_id = property_id or os.getenv("GA4_PROPERTY_ID")
    if not property_id:
        raise ValueError("GA4_PROPERTY_ID is not set")

    client = _get_ga4_client()

    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back)

    # --- Report 1: Daily overview metrics ---
    overview_request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="newUsers"),
        ],
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
    )

    overview_response = client.run_report(overview_request)
    inserted = 0
    updated = 0

    for row in overview_response.rows:
        date_str = row.dimension_values[0].value  # YYYYMMDD format
        date_obj = datetime.strptime(date_str, "%Y%m%d")

        metric_names = [
            "sessions",
            "activeUsers",
            "screenPageViews",
            "bounceRate",
            "averageSessionDuration",
            "newUsers",
        ]

        for i, metric_name in enumerate(metric_names):
            value = float(row.metric_values[i].value)
            result = _upsert_ga4(
                db, metric_name=metric_name, dimension_name="date",
                dimension_value=date_str, date=date_obj,
                metric_value=value, data={"report": "daily_overview"},
            )
            if result == "inserted":
                inserted += 1
            else:
                updated += 1

    # --- Report 2: Top pages ---
    pages_request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="pagePath"),
            Dimension(name="date"),
        ],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="activeUsers"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        limit=200,
    )

    pages_response = client.run_report(pages_request)

    for row in pages_response.rows:
        page_path = row.dimension_values[0].value
        date_str = row.dimension_values[1].value
        date_obj = datetime.strptime(date_str, "%Y%m%d")

        result = _upsert_ga4(
            db, metric_name="pageViews", dimension_name="pagePath",
            dimension_value=page_path, date=date_obj,
            metric_value=float(row.metric_values[0].value),
            data={
                "report": "top_pages",
                "activeUsers": float(row.metric_values[1].value),
                "avgSessionDuration": float(row.metric_values[2].value),
            },
        )
        if result == "inserted":
            inserted += 1
        else:
            updated += 1

    # --- Report 3: Traffic sources ---
    sources_request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionSourceMedium"),
            Dimension(name="date"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
        ],
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        limit=200,
    )

    sources_response = client.run_report(sources_request)

    for row in sources_response.rows:
        source_medium = row.dimension_values[0].value
        date_str = row.dimension_values[1].value
        date_obj = datetime.strptime(date_str, "%Y%m%d")

        result = _upsert_ga4(
            db, metric_name="sessions", dimension_name="sessionSourceMedium",
            dimension_value=source_medium, date=date_obj,
            metric_value=float(row.metric_values[0].value),
            data={
                "report": "traffic_sources",
                "activeUsers": float(row.metric_values[1].value),
            },
        )
        if result == "inserted":
            inserted += 1
        else:
            updated += 1

    # Log the workflow execution
    log_entry = WorkflowLog(
        workflow_name="ga4_data_pull",
        status="success",
        payload={
            "property_id": property_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "rows_inserted": inserted,
            "rows_updated": updated,
        },
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "property_id": property_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows_inserted": inserted,
            "rows_updated": updated,
    }
