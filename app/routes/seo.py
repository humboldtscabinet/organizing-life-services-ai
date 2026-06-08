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
from app.services.gbp_service import discover_gbp_accounts, discover_gbp_locations, pull_gbp_data
from app.services.google_ads_service import pull_google_ads_data
from app.services.gsc_service import pull_gsc_data
from app.services.seo_audit_service import run_deep_seo_audit, run_seo_audit
from app.services.sheets_service import (
    push_audit_to_sheets,
    push_deep_audit_to_sheets,
    push_ga4_to_sheets,
    push_gbp_to_sheets,
    push_google_ads_to_sheets,
    push_gsc_to_sheets,
)

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


# ===================== GBP Endpoints =====================


@router.post("/gbp/discover")
def trigger_gbp_discover(account_name: str = None):
    """
    Discover GBP accounts and locations accessible by the service account.

    Step 1: Call without params to list accounts.
    Step 2: Call with account_name (e.g. "accounts/123456") to list locations.
    """
    try:
        if account_name:
            locations = discover_gbp_locations(account_name)
            return {
                "status": "success",
                "account": account_name,
                "locations": locations,
            }
        else:
            accounts = discover_gbp_accounts()
            return {"status": "success", "accounts": accounts}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/gbp/pull")
def trigger_gbp_pull(
    days_back: int = 28, db: Session = Depends(get_db)
):
    """
    Manually trigger a Google Business Profile performance data pull.

    Pulls the last N days of daily metrics (impressions, clicks,
    direction requests, calls, website clicks) and stores in Postgres.
    Default is 28 days since GBP data is typically reviewed monthly.
    """
    try:
        result = pull_gbp_data(db=db, days_back=days_back)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/gbp/push-to-sheets")
def trigger_gbp_push_to_sheets(
    limit: int = 500, db: Session = Depends(get_db)
):
    """
    Manually push GBP data from Postgres to Google Sheets.

    Creates two tabs: GBP Daily Metrics and GBP Metric Totals.
    """
    try:
        result = push_gbp_to_sheets(db=db, limit=limit)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/gbp/pull-and-push")
def trigger_gbp_full_pipeline(
    days_back: int = 28, limit: int = 500, db: Session = Depends(get_db)
):
    """
    Full pipeline: Pull GBP data → store in Postgres → push to Sheets.
    """
    try:
        pull_result = pull_gbp_data(db=db, days_back=days_back)
        push_result = push_gbp_to_sheets(db=db, limit=limit)
        return {
            "status": "success",
            "pull": pull_result,
            "push": push_result,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ===================== Google Ads Endpoints =====================


@router.post("/ads/pull")
def trigger_ads_pull(
    days_back: int = 30, db: Session = Depends(get_db)
):
    """
    Manually trigger a Google Ads data pull.

    Pulls campaign and ad group performance for the last N days.
    Default is 30 days to match billing cycles.
    """
    try:
        result = pull_google_ads_data(db=db, days_back=days_back)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/ads/push-to-sheets")
def trigger_ads_push_to_sheets(
    limit: int = 500, db: Session = Depends(get_db)
):
    """
    Manually push Google Ads data from Postgres to Google Sheets.

    Creates two tabs: Ads Campaign Performance, Ads Ad Group Performance.
    """
    try:
        result = push_google_ads_to_sheets(db=db, limit=limit)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/ads/pull-and-push")
def trigger_ads_full_pipeline(
    days_back: int = 30, limit: int = 500, db: Session = Depends(get_db)
):
    """
    Full pipeline: Pull Google Ads data → store in Postgres → push to Sheets.
    """
    try:
        pull_result = pull_google_ads_data(db=db, days_back=days_back)
        push_result = push_google_ads_to_sheets(db=db, limit=limit)
        return {
            "status": "success",
            "pull": pull_result,
            "push": push_result,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ----- Direct Google Ads API (Phase A) -----

@router.get("/ads/account-overview")
def ads_account_overview():
    """Customer info, campaign summary, conversion-action audit (direct API)."""
    from app.services.google_ads_service import get_account_overview
    try:
        return get_account_overview()
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/ads/conversion-audit")
def ads_conversion_audit():
    """Flag bogus / misconfigured conversion actions (direct API)."""
    from app.services.google_ads_service import (
        audit_conversion_actions,
        direct_api_available,
    )
    if not direct_api_available():
        return {
            "status": "unavailable",
            "detail": "GOOGLE_ADS_DEVELOPER_TOKEN + OAuth not configured.",
        }
    try:
        return {"status": "success", **audit_conversion_actions()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/ads/campaigns")
def ads_campaigns():
    """List all campaigns with budget + bidding strategy (direct API)."""
    from app.services.google_ads_service import (
        direct_api_available,
        list_campaigns,
    )
    if not direct_api_available():
        return {
            "status": "unavailable",
            "detail": "GOOGLE_ADS_DEVELOPER_TOKEN + OAuth not configured.",
        }
    try:
        return {"status": "success", "campaigns": list_campaigns()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ----- Google Tag Manager (Phase C) -----

@router.get("/gtm/discover")
def gtm_discover(account_id: str | None = None):
    """List GTM accounts (and containers if account_id given) the SA can see."""
    from app.services.gtm_service import (
        direct_api_available,
        discover_gtm_accounts,
        discover_gtm_containers,
    )
    if not direct_api_available():
        return {"status": "unavailable", "detail": "GTM credentials not configured."}
    try:
        if account_id:
            return {"status": "success", "containers": discover_gtm_containers(account_id)}
        return {"status": "success", "accounts": discover_gtm_accounts()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/gtm/overview")
def gtm_overview():
    """Tags, triggers, variables, and audit findings for the configured container."""
    from app.services.gtm_service import get_container_overview
    return get_container_overview()


@router.get("/gtm/audit")
def gtm_audit():
    """Just the audit findings (drift, dead tags, double-fires, page-view conversions)."""
    from app.services.gtm_service import audit_container, direct_api_available
    if not direct_api_available():
        return {"status": "unavailable", "detail": "GTM credentials not configured."}
    try:
        return {"status": "success", **audit_container()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ===================== SEO Audit Endpoints =====================


@router.post("/audit/run")
def trigger_seo_audit(
    days_back: int = 7, db: Session = Depends(get_db)
):
    """
    Run a full SEO audit across GSC, GA4, and Google Ads data.

    Analyzes the last N days of data already in Postgres.
    Generates findings and prioritized recommendations.
    Stores results in seo_reports table.
    """
    try:
        result = run_seo_audit(db=db, days_back=days_back)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/audit/push-to-sheets")
def trigger_audit_push_to_sheets(
    days_back: int = 7, db: Session = Depends(get_db)
):
    """
    Run SEO audit and push results to Google Sheets.

    Creates three tabs:
    - SEO Audit Summary: key metrics from each channel
    - SEO Recommendations: prioritized action items
    - SEO Opportunity Keywords: high-impression, low-CTR queries
    """
    try:
        audit_result = run_seo_audit(db=db, days_back=days_back)
        push_result = push_audit_to_sheets(
            db=db, audit_results=audit_result
        )
        return {
            "status": "success",
            "audit": {
                "reports_created": audit_result.get("reports_created", 0),
            },
            "push": push_result,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ===================== Deep SEO Audit Endpoints =====================

@router.post("/audit/deep")
def trigger_deep_seo_audit(
    period_days: int = 28,
    include_crawl: bool = True,
    include_shopify_overrides: bool = False,
    max_urls: int = 250,
    db: Session = Depends(get_db),
):
    """
    Run a deep SEO audit: live GSC + GA4 period comparison, dual-UA
    technical crawl, impression-weighted position, optional Shopify
    SEO-override check. Persists as SEOReport(report_type='deep_audit').
    """
    try:
        return run_deep_seo_audit(
            db=db,
            period_days=period_days,
            include_crawl=include_crawl,
            include_shopify_overrides=include_shopify_overrides,
            max_urls=max_urls,
        )
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/audit/deep/push-to-sheets")
def trigger_deep_audit_push_to_sheets(
    period_days: int = 28,
    include_crawl: bool = True,
    include_shopify_overrides: bool = False,
    max_urls: int = 250,
    db: Session = Depends(get_db),
):
    """
    Run deep audit and push the executive summary + tables to Sheets.
    Intended for n8n weekly cron.
    """
    try:
        audit = run_deep_seo_audit(
            db=db,
            period_days=period_days,
            include_crawl=include_crawl,
            include_shopify_overrides=include_shopify_overrides,
            max_urls=max_urls,
        )
        push = push_deep_audit_to_sheets(audit_payload=audit)
        return {"status": "success", "report_id": audit.get("report_id"),
                "push": push}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/audit/shopify-overrides")
def trigger_shopify_override_audit(include_products: bool = False):
    """
    Compare Shopify-stored SEO title/meta vs rendered <title> on every
    page + article. Flags theme overrides and length issues at the source.
    """
    from app.services.shopify_seo_audit_service import (
        audit_shopify_seo_overrides,
    )
    try:
        return audit_shopify_seo_overrides(include_products=include_products)
    except Exception as e:
        return {"status": "error", "detail": str(e)}
