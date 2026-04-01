"""
Google Sheets — Operator Dashboard Service

Pushes data from Postgres to Google Sheets for human review.
This is the operator's primary dashboard surface.
"""

import os

import gspread
from google.oauth2 import service_account
from sqlalchemy.orm import Session

from app.db.models import GSCData

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
