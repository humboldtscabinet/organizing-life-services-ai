"""
SEO Routes — Manual-trigger endpoints for SEO data operations.

All endpoints are manual-approval mode:
- Pull data from Google APIs → store in Postgres
- Push data from Postgres → Google Sheets for human review
- No automated actions — human must trigger every operation
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.ga4_service import pull_ga4_data
from app.services.gsc_service import pull_gsc_data
from app.services.sheets_service import push_ga4_to_sheets, push_gsc_to_sheets

router = APIRouter(prefix="/api/seo", tags=["SEO"])


@router.post("/gsc/pull")
def trigger_gsc_pull(days_back: int = 7, db: Session = Depends(get_db)):
    """
    Manually trigger a Google Search Console data pull.

    Pulls the last N days of search analytics and stores in Postgres.
    """
    try:
        result = pull_gsc_data(db=db, days_back=days_back)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/gsc/push-to-sheets")
def trigger_gsc_push_to_sheets(
    limit: int = 500, db: Session = Depends(get_db)
):
    """
    Manually push GSC data from Postgres to Google Sheets.

    Writes to the 'GSC Data' tab of the operator dashboard spreadsheet.
    """
    try:
        result = push_gsc_to_sheets(db=db, limit=limit)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/gsc/pull-and-push")
def trigger_gsc_full_pipeline(
    days_back: int = 7, limit: int = 500, db: Session = Depends(get_db)
):
    """
    Full pipeline: Pull GSC data → store in Postgres → push to Sheets.

    Convenience endpoint that runs both steps in sequence.
    Still manual-trigger only.
    """
    try:
        pull_result = pull_gsc_data(db=db, days_back=days_back)
        push_result = push_gsc_to_sheets(db=db, limit=limit)
        return {
            "status": "success",
            "pull": pull_result,
            "push": push_result,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ===================== GA4 Endpoints =====================


@router.post("/ga4/pull")
def trigger_ga4_pull(days_back: int = 7, db: Session = Depends(get_db)):
    """
    Manually trigger a Google Analytics 4 data pull.

    Pulls daily overview, top pages, and traffic sources for the last N days.
    """
    try:
        result = pull_ga4_data(db=db, days_back=days_back)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/ga4/push-to-sheets")
def trigger_ga4_push_to_sheets(
    limit: int = 500, db: Session = Depends(get_db)
):
    """
    Manually push GA4 data from Postgres to Google Sheets.

    Creates three tabs: GA4 Daily Overview, GA4 Top Pages, GA4 Traffic Sources.
    """
    try:
        result = push_ga4_to_sheets(db=db, limit=limit)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/ga4/pull-and-push")
def trigger_ga4_full_pipeline(
    days_back: int = 7, limit: int = 500, db: Session = Depends(get_db)
):
    """
    Full pipeline: Pull GA4 data → store in Postgres → push to Sheets.
    """
    try:
        pull_result = pull_ga4_data(db=db, days_back=days_back)
        push_result = push_ga4_to_sheets(db=db, limit=limit)
        return {
            "status": "success",
            "pull": pull_result,
            "push": push_result,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
