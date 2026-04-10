"""
Google Search Console — Data Pull Service

Pulls search analytics data from GSC and stores it in Postgres.
Manual-approval mode: this service only READS data. No writes to GSC.
"""

import os
from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.db.models import GSCData, WorkflowLog

# Scopes required for read-only GSC access
GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _get_gsc_service():
    """Build an authenticated GSC API client using the service account."""
    credentials_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/credentials/google-service-account.json",
    )
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=GSC_SCOPES
    )
    return build("searchconsole", "v1", credentials=credentials)


def pull_gsc_data(
    db: Session,
    site_url: str = None,
    days_back: int = 7,
) -> dict:
    """
    Pull search analytics from GSC for the last N days.

    Returns a summary dict with row count and date range.
    All data is stored in the gsc_data table.
    """
    site_url = site_url or os.getenv("GSC_SITE_URL")
    if not site_url:
        raise ValueError("GSC_SITE_URL is not set")

    service = _get_gsc_service()

    end_date = datetime.utcnow().date() - timedelta(days=3)  # GSC data lags ~3 days
    start_date = end_date - timedelta(days=days_back)

    request_body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["query", "page", "date"],
        "rowLimit": 1000,
    }

    response = (
        service.searchanalytics()
        .query(siteUrl=site_url, body=request_body)
        .execute()
    )

    rows = response.get("rows", [])
    inserted = 0
    updated = 0

    for row in rows:
        keys = row.get("keys", [])
        query_text = keys[0] if len(keys) > 0 else ""
        page_url = keys[1] if len(keys) > 1 else ""
        date_str = keys[2] if len(keys) > 2 else start_date.isoformat()
        row_date = datetime.fromisoformat(date_str)

        # Upsert: check if this query+page+date combo already exists
        existing = (
            db.query(GSCData)
            .filter(
                GSCData.query == query_text,
                GSCData.page == page_url,
                GSCData.date == row_date,
            )
            .first()
        )

        if existing:
            # Update with latest data (GSC can revise numbers)
            existing.clicks = int(row.get("clicks", 0))
            existing.impressions = int(row.get("impressions", 0))
            existing.ctr = round(row.get("ctr", 0.0), 4)
            existing.position = round(row.get("position", 0.0), 2)
            updated += 1
        else:
            record = GSCData(
                query=query_text,
                page=page_url,
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=round(row.get("ctr", 0.0), 4),
                position=round(row.get("position", 0.0), 2),
                date=row_date,
            )
            db.add(record)
            inserted += 1

    # Log the workflow execution
    log_entry = WorkflowLog(
        workflow_name="gsc_data_pull",
        status="success",
        payload={
            "site_url": site_url,
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
        "site_url": site_url,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows_inserted": inserted,
    }
