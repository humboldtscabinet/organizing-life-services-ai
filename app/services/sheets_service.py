"""
Google Sheets — Operator Dashboard Service

Pushes data from Postgres to Google Sheets for human review.
This is the operator's primary dashboard surface.
"""

import os

import gspread
from google.oauth2 import service_account
from sqlalchemy.orm import Session

from app.db.models import GA4Data, GBPInsight, GoogleAdsData, GSCData

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_sheets_client() -> gspread.Client:
    """Build an authenticated gspread client using the service account."""
    credentials_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/credentials/google-service-account.json",
    )
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SHEETS_SCOPES
    )
    return gspread.authorize(credentials)


def push_gsc_to_sheets(
    db: Session,
    spreadsheet_id: str = None,
    worksheet_name: str = "GSC Data",
    limit: int = 500,
) -> dict:
    """
    Push the latest GSC data from Postgres to Google Sheets.

    Creates or clears the worksheet, writes headers + rows.
    Returns a summary dict.
    """
    spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID is not set")

    # Query latest GSC data from Postgres
    records = (
        db.query(GSCData)
        .order_by(GSCData.date.desc(), GSCData.clicks.desc())
        .limit(limit)
        .all()
    )

    if not records:
        return {"status": "no_data", "rows_pushed": 0}

    # Build the data for Sheets
    headers = [
        "Date",
        "Query",
        "Page",
        "Clicks",
        "Impressions",
        "CTR",
        "Avg Position",
    ]

    rows = []
    for r in records:
        rows.append([
            r.date.strftime("%Y-%m-%d") if r.date else "",
            r.query or "",
            r.page or "",
            r.clicks or 0,
            r.impressions or 0,
            round(r.ctr * 100, 2) if r.ctr else 0,  # Display as percentage
            round(r.position, 1) if r.position else 0,
        ])

    # Connect to Sheets and write
    client = _get_sheets_client()
    spreadsheet = client.open_by_key(spreadsheet_id)

    # Get or create the worksheet
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name, rows=len(rows) + 1, cols=len(headers)
        )

    # Write headers + data in one batch
    all_data = [headers] + rows
    worksheet.update(range_name="A1", values=all_data)

    # Auto-format: bold headers, freeze top row
    worksheet.format("A1:G1", {"textFormat": {"bold": True}})
    worksheet.freeze(rows=1)

    return {
        "status": "success",
        "spreadsheet_id": spreadsheet_id,
        "worksheet": worksheet_name,
        "rows_pushed": len(rows),
    }


def push_ga4_to_sheets(
    db: Session,
    spreadsheet_id: str = None,
    limit: int = 500,
) -> dict:
    """
    Push GA4 data from Postgres to Google Sheets.

    Creates three tabs:
    - GA4 Daily Overview: daily metrics (sessions, users, page views, etc.)
    - GA4 Top Pages: page-level performance
    - GA4 Traffic Sources: source/medium breakdown
    """
    spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID is not set")

    client = _get_sheets_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    total_pushed = 0

    # --- Tab 1: Daily Overview ---
    overview_records = (
        db.query(GA4Data)
        .filter(GA4Data.data["report"].as_string() == "daily_overview")
        .order_by(GA4Data.date.desc())
        .limit(limit)
        .all()
    )

    if overview_records:
        # Pivot: one row per date with all metrics as columns
        date_metrics = {}
        for r in overview_records:
            date_key = r.dimension_value
            if date_key not in date_metrics:
                date_metrics[date_key] = {}
            date_metrics[date_key][r.metric_name] = r.metric_value

        headers = [
            "Date",
            "Sessions",
            "Active Users",
            "New Users",
            "Page Views",
            "Bounce Rate %",
            "Avg Session Duration (s)",
        ]
        rows = []
        for date_key in sorted(date_metrics.keys(), reverse=True):
            m = date_metrics[date_key]
            rows.append([
                f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:]}",
                int(m.get("sessions", 0)),
                int(m.get("activeUsers", 0)),
                int(m.get("newUsers", 0)),
                int(m.get("screenPageViews", 0)),
                round(m.get("bounceRate", 0) * 100, 1),
                round(m.get("averageSessionDuration", 0), 1),
            ])

        _write_sheet_tab(spreadsheet, "GA4 Daily Overview", headers, rows)
        total_pushed += len(rows)

    # --- Tab 2: Top Pages ---
    pages_records = (
        db.query(GA4Data)
        .filter(GA4Data.data["report"].as_string() == "top_pages")
        .order_by(GA4Data.metric_value.desc())
        .limit(limit)
        .all()
    )

    if pages_records:
        headers = ["Date", "Page Path", "Page Views", "Active Users", "Avg Duration (s)"]
        rows = []
        for r in pages_records:
            rows.append([
                r.date.strftime("%Y-%m-%d") if r.date else "",
                r.dimension_value or "",
                int(r.metric_value or 0),
                int(r.data.get("activeUsers", 0)) if r.data else 0,
                round(r.data.get("avgSessionDuration", 0), 1) if r.data else 0,
            ])
        _write_sheet_tab(spreadsheet, "GA4 Top Pages", headers, rows)
        total_pushed += len(rows)

    # --- Tab 3: Traffic Sources ---
    sources_records = (
        db.query(GA4Data)
        .filter(GA4Data.data["report"].as_string() == "traffic_sources")
        .order_by(GA4Data.metric_value.desc())
        .limit(limit)
        .all()
    )

    if sources_records:
        headers = ["Date", "Source / Medium", "Sessions", "Active Users"]
        rows = []
        for r in sources_records:
            rows.append([
                r.date.strftime("%Y-%m-%d") if r.date else "",
                r.dimension_value or "",
                int(r.metric_value or 0),
                int(r.data.get("activeUsers", 0)) if r.data else 0,
            ])
        _write_sheet_tab(spreadsheet, "GA4 Traffic Sources", headers, rows)
        total_pushed += len(rows)

    if total_pushed == 0:
        return {"status": "no_data", "rows_pushed": 0}

    return {
        "status": "success",
        "spreadsheet_id": spreadsheet_id,
        "rows_pushed": total_pushed,
    }


def push_google_ads_to_sheets(
    db: Session,
    spreadsheet_id: str = None,
    limit: int = 500,
) -> dict:
    """
    Push Google Ads performance data from Postgres to Google Sheets.

    Creates three tabs:
    - Ads Campaign Performance: daily campaign-level metrics
    - Ads Ad Group Performance: daily ad-group-level metrics
    - Ads Keywords: keyword-level click/cost/impression data
    """
    spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID is not set")

    client = _get_sheets_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    total_pushed = 0

    # --- Tab 1: Campaign Performance ---
    campaign_records = (
        db.query(GoogleAdsData)
        .filter(GoogleAdsData.data["report"].as_string() == "campaign")
        .order_by(GoogleAdsData.date.desc())
        .limit(limit)
        .all()
    )

    if campaign_records:
        headers = [
            "Date",
            "Campaign",
            "Clicks",
            "Impressions",
            "CTR %",
            "Cost ($)",
            "Avg CPC ($)",
            "Conversions",
        ]
        rows = []
        for r in campaign_records:
            rows.append([
                r.date.strftime("%Y-%m-%d") if r.date else "",
                r.campaign_name or "",
                r.clicks or 0,
                r.impressions or 0,
                round(r.data.get("ctr", 0) * 100, 2) if r.data else 0,
                round(r.cost, 2) if r.cost else 0,
                round(r.data.get("average_cpc", 0), 2) if r.data else 0,
                round(r.conversions, 1) if r.conversions else 0,
            ])
        _write_sheet_tab(spreadsheet, "Ads Campaign Performance", headers, rows)
        total_pushed += len(rows)

    # --- Tab 2: Ad Group Performance ---
    adgroup_records = (
        db.query(GoogleAdsData)
        .filter(GoogleAdsData.data["report"].as_string() == "ad_group")
        .order_by(GoogleAdsData.date.desc())
        .limit(limit)
        .all()
    )

    if adgroup_records:
        headers = [
            "Date",
            "Campaign",
            "Ad Group",
            "Clicks",
            "Impressions",
            "Cost ($)",
            "Conversions",
        ]
        rows = []
        for r in adgroup_records:
            rows.append([
                r.date.strftime("%Y-%m-%d") if r.date else "",
                r.campaign_name or "",
                r.ad_group or "",
                r.clicks or 0,
                r.impressions or 0,
                round(r.cost, 2) if r.cost else 0,
                round(r.conversions, 1) if r.conversions else 0,
            ])
        _write_sheet_tab(spreadsheet, "Ads Ad Group Performance", headers, rows)
        total_pushed += len(rows)

    # --- Tab 3: Keywords ---
    keyword_records = (
        db.query(GoogleAdsData)
        .filter(GoogleAdsData.data["report"].as_string() == "keyword")
        .order_by(GoogleAdsData.date.desc())
        .limit(limit)
        .all()
    )

    if keyword_records:
        headers = [
            "Date",
            "Campaign",
            "Keyword",
            "Clicks",
            "Impressions",
            "Cost ($)",
        ]
        rows = []
        for r in keyword_records:
            rows.append([
                r.date.strftime("%Y-%m-%d") if r.date else "",
                r.campaign_name or "",
                r.ad_group or "",  # keyword stored in ad_group field
                r.clicks or 0,
                r.impressions or 0,
                round(r.cost, 2) if r.cost else 0,
            ])
        _write_sheet_tab(spreadsheet, "Ads Keywords", headers, rows)
        total_pushed += len(rows)

    if total_pushed == 0:
        return {"status": "no_data", "rows_pushed": 0}

    return {
        "status": "success",
        "spreadsheet_id": spreadsheet_id,
        "rows_pushed": total_pushed,
    }


def push_gbp_to_sheets(
    db: Session,
    spreadsheet_id: str = None,
    limit: int = 500,
) -> dict:
    """
    Push GBP performance data from Postgres to Google Sheets.

    Creates two tabs:
    - GBP Daily Metrics: one row per date with all metrics as columns
    - GBP Metric Totals: aggregate totals per metric over the date range
    """
    spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID is not set")

    client = _get_sheets_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    total_pushed = 0

    # Query all GBP records, most recent first
    records = (
        db.query(GBPInsight)
        .order_by(GBPInsight.period_start.desc())
        .limit(limit)
        .all()
    )

    if not records:
        return {"status": "no_data", "rows_pushed": 0}

    # --- Tab 1: GBP Daily Metrics (pivoted: one row per date) ---
    date_metrics = {}
    all_metric_names = set()

    for r in records:
        date_key = r.period_start.strftime("%Y-%m-%d") if r.period_start else "unknown"
        if date_key not in date_metrics:
            date_metrics[date_key] = {}
        date_metrics[date_key][r.metric_name] = int(r.metric_value or 0)
        all_metric_names.add(r.metric_name)

    # Sort metric names for consistent column order
    sorted_metrics = sorted(all_metric_names)

    # Friendly column names
    friendly_names = {
        "BUSINESS_IMPRESSIONS_DESKTOP_MAPS": "Desktop Maps",
        "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH": "Desktop Search",
        "BUSINESS_IMPRESSIONS_MOBILE_MAPS": "Mobile Maps",
        "BUSINESS_IMPRESSIONS_MOBILE_SEARCH": "Mobile Search",
        "BUSINESS_DIRECTION_REQUESTS": "Direction Requests",
        "CALL_CLICKS": "Call Clicks",
        "WEBSITE_CLICKS": "Website Clicks",
    }

    headers = ["Date"] + [friendly_names.get(m, m) for m in sorted_metrics]
    rows = []
    for date_key in sorted(date_metrics.keys(), reverse=True):
        m = date_metrics[date_key]
        row = [date_key]
        for metric in sorted_metrics:
            row.append(m.get(metric, 0))
        rows.append(row)

    _write_sheet_tab(spreadsheet, "GBP Daily Metrics", headers, rows)
    total_pushed += len(rows)

    # --- Tab 2: GBP Metric Totals ---
    metric_totals = {}
    for r in records:
        name = r.metric_name
        metric_totals[name] = metric_totals.get(name, 0) + int(r.metric_value or 0)

    totals_headers = ["Metric", "Total"]
    totals_rows = []
    for metric in sorted_metrics:
        totals_rows.append([
            friendly_names.get(metric, metric),
            metric_totals.get(metric, 0),
        ])

    _write_sheet_tab(spreadsheet, "GBP Metric Totals", totals_headers, totals_rows)
    total_pushed += len(totals_rows)

    return {
        "status": "success",
        "spreadsheet_id": spreadsheet_id,
        "rows_pushed": total_pushed,
    }


def _write_sheet_tab(spreadsheet, tab_name: str, headers: list, rows: list):
    """Helper: write headers + rows to a named tab, creating it if needed."""
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        worksheet.clear()
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=tab_name, rows=len(rows) + 1, cols=len(headers)
        )

    all_data = [headers] + rows
    worksheet.update(range_name="A1", values=all_data)
    worksheet.format(f"A1:{chr(64 + len(headers))}1", {"textFormat": {"bold": True}})
    worksheet.freeze(rows=1)
