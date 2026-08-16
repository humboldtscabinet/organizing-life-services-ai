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
    Filter,
    FilterExpression,
    Metric,
    RunReportRequest,
)
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import GA4Data, WorkflowLog

# Weekly lead KPI = these two. Never treat page_view as a lead.
LEAD_EVENT_NAMES = ("form_submit", "phone_call_clicks")


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

    named_inserted, named_updated = _pull_named_events(
        db,
        client=client,
        property_id=property_id,
        start_date=start_date,
        end_date=end_date,
    )
    inserted += named_inserted
    updated += named_updated

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


def _pull_named_events(
    db: Session,
    *,
    client,
    property_id: str,
    start_date,
    end_date,
) -> tuple[int, int]:
    """Store daily eventCount (and keyEvents when available) for lead events.

    Uses data.report=named_events so session/pageview charts stay untouched.
    """
    inserted = 0
    updated = 0
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="eventName"),
            Dimension(name="date"),
        ],
        metrics=[Metric(name="eventCount"), Metric(name="keyEvents")],
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                in_list_filter=Filter.InListFilter(values=list(LEAD_EVENT_NAMES)),
            )
        ),
    )
    try:
        response = client.run_report(request)
        include_key_events = True
    except Exception:
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[
                Dimension(name="eventName"),
                Dimension(name="date"),
            ],
            metrics=[Metric(name="eventCount")],
            date_ranges=[
                DateRange(
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                )
            ],
            dimension_filter=FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    in_list_filter=Filter.InListFilter(values=list(LEAD_EVENT_NAMES)),
                )
            ),
        )
        response = client.run_report(request)
        include_key_events = False

    for row in response.rows:
        event_name = row.dimension_values[0].value
        date_str = row.dimension_values[1].value
        date_obj = datetime.strptime(date_str, "%Y%m%d")
        event_count = float(row.metric_values[0].value or 0)
        result = _upsert_ga4(
            db,
            metric_name="eventCount",
            dimension_name="eventName",
            dimension_value=event_name,
            date=date_obj,
            metric_value=event_count,
            data={"report": "named_events"},
        )
        if result == "inserted":
            inserted += 1
        else:
            updated += 1
        if include_key_events and len(row.metric_values) > 1:
            key_events = float(row.metric_values[1].value or 0)
            result = _upsert_ga4(
                db,
                metric_name="keyEvents",
                dimension_name="eventName",
                dimension_value=event_name,
                date=date_obj,
                metric_value=key_events,
                data={"report": "named_events"},
            )
            if result == "inserted":
                inserted += 1
            else:
                updated += 1
    return inserted, updated


def count_named_events(event_name: str, days_back: int = 7) -> int | None:
    """Return GA4 eventCount for one event over the last N days, or None.

    Read-only. Used by the GTM ensure detector to no-op when
    ``phone_call_clicks`` is already firing.
    """
    if not event_name:
        return None
    property_id = os.getenv("GA4_PROPERTY_ID")
    creds_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/credentials/google-service-account.json",
    )
    if not property_id or not os.path.exists(creds_path):
        return None

    client = _get_ga4_client()
    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back)
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(
                    value=event_name,
                    match_type=Filter.StringFilter.MatchType.EXACT,
                ),
            )
        ),
    )
    response = client.run_report(request)
    total = 0
    for row in response.rows:
        total += int(float(row.metric_values[0].value or 0))
    return total


def sum_stored_lead_events(db: Session, days_back: int = 7) -> dict:
    """Sum form_submit + phone_call_clicks from Postgres named_events rows.

    KPI is those two eventCounts. Never include page_view.
    """
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    totals = {name: 0.0 for name in LEAD_EVENT_NAMES}
    last_date = None
    rows = (
        db.query(GA4Data)
        .filter(
            GA4Data.date >= cutoff,
            GA4Data.metric_name == "eventCount",
            GA4Data.dimension_name == "eventName",
            GA4Data.dimension_value.in_(LEAD_EVENT_NAMES),
        )
        .all()
    )
    for row in rows:
        payload = row.data or {}
        if payload.get("report") not in (None, "named_events"):
            continue
        name = row.dimension_value
        if name in totals:
            totals[name] += float(row.metric_value or 0)
        if row.date and (last_date is None or row.date > last_date):
            last_date = row.date
    form_submit = int(totals["form_submit"])
    phone = int(totals["phone_call_clicks"])
    return {
        "form_submit": form_submit,
        "phone_call_clicks": phone,
        "total_leads": form_submit + phone,
        "last_date": last_date.isoformat() if last_date else None,
        "kpi": "form_submit + phone_call_clicks (never page_view)",
        "period_days": days_back,
    }
