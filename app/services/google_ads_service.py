"""
Google Ads — Data Pull Service (via GA4 API)

Pulls Google Ads campaign performance data through the GA4 Data API.
This avoids the need for a separate Google Ads developer token and
OAuth2 setup — uses the same service account as GA4.

Requires:
  - Google Ads linked to GA4 in the GA4 property settings
  - Service account with Viewer access on GA4 (already set up)

Manual-approval mode: read-only.
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

from app.db.models import GoogleAdsData, WorkflowLog


def _upsert_ads(db: Session, campaign_name: str, ad_group: str,
                date: datetime, clicks: int, impressions: int,
                cost: float, conversions: float, data: dict) -> str:
    """Insert or update a Google Ads record. Returns 'inserted' or 'updated'."""
    existing = (
        db.query(GoogleAdsData)
        .filter(
            and_(
                GoogleAdsData.campaign_name == campaign_name,
                GoogleAdsData.ad_group == ad_group if ad_group else GoogleAdsData.ad_group.is_(None),
                GoogleAdsData.date == date,
                GoogleAdsData.data["report"].astext == data.get("report", ""),
            )
        )
        .first()
    )
    if existing:
        existing.clicks = clicks
        existing.impressions = impressions
        existing.cost = cost
        existing.conversions = conversions
        existing.data = data
        return "updated"
    else:
        record = GoogleAdsData(
            campaign_name=campaign_name,
            ad_group=ad_group,
            clicks=clicks,
            impressions=impressions,
            cost=cost,
            conversions=conversions,
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


def pull_google_ads_data(
    db: Session,
    property_id: str = None,
    customer_id: str = None,
    days_back: int = 30,
) -> dict:
    """
    Pull Google Ads performance data via the GA4 Data API.

    Runs two reports:
    1. Campaign-level: daily clicks, cost, impressions by campaign
    2. Keyword-level: top search terms driving ad clicks

    All data stored in google_ads_data table.
    """
    property_id = property_id or os.getenv("GA4_PROPERTY_ID")
    if not property_id:
        raise ValueError("GA4_PROPERTY_ID is not set")

    customer_id = customer_id or os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")

    client = _get_ga4_client()

    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back)

    rows_inserted = 0
    rows_updated = 0

    # --- Report 1: Campaign performance (daily) ---
    campaign_request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionGoogleAdsCampaignName"),
            Dimension(name="date"),
        ],
        metrics=[
            Metric(name="advertiserAdClicks"),
            Metric(name="advertiserAdCost"),
            Metric(name="advertiserAdCostPerClick"),
            Metric(name="advertiserAdImpressions"),
            Metric(name="conversions"),
        ],
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        limit=500,
    )

    campaign_response = client.run_report(campaign_request)
    campaign_count = 0

    for row in campaign_response.rows:
        campaign_name = row.dimension_values[0].value
        date_str = row.dimension_values[1].value  # YYYYMMDD
        date_obj = datetime.strptime(date_str, "%Y%m%d")

        clicks = int(float(row.metric_values[0].value))
        cost = round(float(row.metric_values[1].value), 2)
        cpc = round(float(row.metric_values[2].value), 2)
        impressions = int(float(row.metric_values[3].value))
        conversions = float(row.metric_values[4].value)

        # Calculate CTR
        ctr = (clicks / impressions) if impressions > 0 else 0.0

        result = _upsert_ads(
            db, campaign_name=campaign_name, ad_group=None,
            date=date_obj, clicks=clicks, impressions=impressions,
            cost=cost, conversions=conversions,
            data={
                "report": "campaign",
                "ctr": round(ctr, 4),
                "average_cpc": cpc,
                "customer_id": customer_id,
                "source": "ga4_api",
            },
        )
        if result == "inserted":
            rows_inserted += 1
        else:
            rows_updated += 1
        campaign_count += 1

    # --- Report 2: Ad Group performance (daily) ---
    adgroup_request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionGoogleAdsCampaignName"),
            Dimension(name="sessionGoogleAdsAdGroupName"),
            Dimension(name="date"),
        ],
        metrics=[
            Metric(name="advertiserAdClicks"),
            Metric(name="advertiserAdCost"),
            Metric(name="advertiserAdImpressions"),
            Metric(name="conversions"),
        ],
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        limit=500,
    )

    adgroup_response = client.run_report(adgroup_request)
    adgroup_count = 0

    for row in adgroup_response.rows:
        campaign_name = row.dimension_values[0].value
        ad_group_name = row.dimension_values[1].value
        date_str = row.dimension_values[2].value
        date_obj = datetime.strptime(date_str, "%Y%m%d")

        clicks = int(float(row.metric_values[0].value))
        cost = round(float(row.metric_values[1].value), 2)
        impressions = int(float(row.metric_values[2].value))
        conversions = float(row.metric_values[3].value)

        result = _upsert_ads(
            db, campaign_name=campaign_name, ad_group=ad_group_name,
            date=date_obj, clicks=clicks, impressions=impressions,
            cost=cost, conversions=conversions,
            data={
                "report": "ad_group",
                "customer_id": customer_id,
                "source": "ga4_api",
            },
        )
        if result == "inserted":
            rows_inserted += 1
        else:
            rows_updated += 1
        adgroup_count += 1

    # --- Report 3: Ad keywords / search terms ---
    keyword_request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionGoogleAdsKeyword"),
            Dimension(name="sessionGoogleAdsCampaignName"),
            Dimension(name="date"),
        ],
        metrics=[
            Metric(name="advertiserAdClicks"),
            Metric(name="advertiserAdCost"),
            Metric(name="advertiserAdImpressions"),
        ],
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        limit=500,
    )

    keyword_response = client.run_report(keyword_request)
    keyword_count = 0

    for row in keyword_response.rows:
        keyword = row.dimension_values[0].value
        campaign_name = row.dimension_values[1].value
        date_str = row.dimension_values[2].value
        date_obj = datetime.strptime(date_str, "%Y%m%d")

        clicks = int(float(row.metric_values[0].value))
        cost = round(float(row.metric_values[1].value), 2)
        impressions = int(float(row.metric_values[2].value))

        result = _upsert_ads(
            db, campaign_name=campaign_name,
            ad_group=keyword,  # Store keyword in ad_group field (model lacks keyword column)
            date=date_obj, clicks=clicks, impressions=impressions,
            cost=cost, conversions=0,
            data={
                "report": "keyword",
                "keyword": keyword,  # Store actual keyword name in data JSON
                "customer_id": customer_id,
                "source": "ga4_api",
            },
        )
        if result == "inserted":
            rows_inserted += 1
        else:
            rows_updated += 1
        keyword_count += 1

    db.commit()

    # Log the workflow
    log_entry = WorkflowLog(
        workflow_name="google_ads_data_pull",
        status="success",
        payload={
            "property_id": property_id,
            "customer_id": customer_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "campaign_rows": campaign_count,
            "adgroup_rows": adgroup_count,
            "keyword_rows": keyword_count,
            "rows_inserted": rows_inserted,
        },
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "property_id": property_id,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "campaign_rows": campaign_count,
        "adgroup_rows": adgroup_count,
        "keyword_rows": keyword_count,
        "rows_inserted": rows_inserted,
    }


# =============================================================
# Direct Google Ads API (Phase A)
# -------------------------------------------------------------
# These functions use the official google-ads SDK and require:
#   GOOGLE_ADS_DEVELOPER_TOKEN, _CLIENT_ID, _CLIENT_SECRET,
#   _REFRESH_TOKEN, _CUSTOMER_ID
#
# When the developer token is missing, ``direct_api_available()``
# returns False and callers should fall back to the GA4-derived
# data path above.
# =============================================================


def direct_api_available() -> bool:
    """True if the direct Google Ads API is fully configured."""
    from app.services.google_oauth import google_ads_client
    return google_ads_client() is not None


def _customer_id() -> str:
    cid = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "").strip()
    if not cid:
        raise ValueError("GOOGLE_ADS_CUSTOMER_ID is not set")
    return cid


def list_conversion_actions() -> list[dict]:
    """Return every conversion action on the account, with config flags.

    This is the audit that would have caught the page_view / Contact Page
    Load bogus conversions automatically.
    """
    from app.services.google_oauth import google_ads_client
    client = google_ads_client()
    if client is None:
        raise RuntimeError(
            "Google Ads direct API is not configured. "
            "Set GOOGLE_ADS_DEVELOPER_TOKEN + OAuth credentials in .env."
        )

    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            conversion_action.id,
            conversion_action.name,
            conversion_action.status,
            conversion_action.type,
            conversion_action.category,
            conversion_action.primary_for_goal,
            conversion_action.counting_type,
            conversion_action.click_through_lookback_window_days,
            conversion_action.value_settings.default_value,
            conversion_action.value_settings.always_use_default_value
        FROM conversion_action
        ORDER BY conversion_action.name
    """
    response = ga_service.search(customer_id=_customer_id(), query=query)
    out: list[dict] = []
    for row in response:
        ca = row.conversion_action
        out.append({
            "id": ca.id,
            "name": ca.name,
            "status": ca.status.name,
            "type": ca.type_.name,
            "category": ca.category.name,
            "primary_for_goal": ca.primary_for_goal,
            "counting_type": ca.counting_type.name,
            "click_lookback_days": ca.click_through_lookback_window_days,
            "default_value": ca.value_settings.default_value,
        })
    return out


def audit_conversion_actions() -> dict:
    """Flag conversion actions that look bogus or misconfigured.

    Heuristics:
        * Type == ``WEBPAGE`` + name contains 'page view' / 'page load'
          → almost certainly a vanity metric, not a real conversion.
        * Counting type == ``MANY_PER_CLICK`` for phone/form actions
          → inflates conversion counts; should be ONE_PER_CLICK.
        * Status == ``ENABLED`` + ``primary_for_goal`` True with category
          ``PAGE_VIEW`` → these are the ones that destroy Smart Bidding.
    """
    actions = list_conversion_actions()
    findings: list[dict] = []
    for a in actions:
        issues: list[str] = []
        name_lc = a["name"].lower()
        if a["category"] == "PAGE_VIEW":
            issues.append("category=PAGE_VIEW (not a real conversion)")
        if any(s in name_lc for s in ("page view", "page load", "pageview")):
            issues.append("name suggests page-view tracking")
        if a["counting_type"] == "MANY_PER_CLICK" and any(
            s in name_lc for s in ("call", "phone", "form", "submit", "lead")
        ):
            issues.append("counting=MANY_PER_CLICK (should be ONE for leads)")
        if a["status"] == "ENABLED" and a["primary_for_goal"] and issues:
            issues.append("ENABLED + primary_for_goal — actively biasing bids")
        if issues:
            findings.append({**a, "issues": issues})
    return {
        "total_actions": len(actions),
        "flagged": len(findings),
        "actions": actions,
        "findings": findings,
    }


def list_campaigns() -> list[dict]:
    """Return every campaign with status, channel type, budget, and bidding."""
    from app.services.google_oauth import google_ads_client
    client = google_ads_client()
    if client is None:
        raise RuntimeError("Google Ads direct API is not configured.")

    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign_budget.amount_micros,
            campaign.start_date,
            campaign.end_date
        FROM campaign
        ORDER BY campaign.name
    """
    response = ga_service.search(customer_id=_customer_id(), query=query)
    out: list[dict] = []
    for row in response:
        c = row.campaign
        out.append({
            "id": c.id,
            "name": c.name,
            "status": c.status.name,
            "channel": c.advertising_channel_type.name,
            "bidding_strategy": c.bidding_strategy_type.name,
            "daily_budget_usd": round(row.campaign_budget.amount_micros / 1_000_000, 2),
            "start_date": c.start_date,
            "end_date": c.end_date,
        })
    return out


def get_account_overview() -> dict:
    """One-call summary: customer info + campaign count + conversion-action audit."""
    from app.services.google_oauth import google_ads_client
    client = google_ads_client()
    if client is None:
        return {"available": False, "reason": "developer token / OAuth not configured"}

    ga_service = client.get_service("GoogleAdsService")
    customer_query = """
        SELECT
            customer.id,
            customer.descriptive_name,
            customer.currency_code,
            customer.time_zone,
            customer.manager,
            customer.test_account
        FROM customer LIMIT 1
    """
    customer_row = next(iter(ga_service.search(
        customer_id=_customer_id(), query=customer_query
    )))
    cust = customer_row.customer
    campaigns = list_campaigns()
    audit = audit_conversion_actions()
    return {
        "available": True,
        "customer": {
            "id": cust.id,
            "name": cust.descriptive_name,
            "currency": cust.currency_code,
            "time_zone": cust.time_zone,
            "is_manager": cust.manager,
            "is_test": cust.test_account,
        },
        "campaign_count": len(campaigns),
        "active_campaigns": [c for c in campaigns if c["status"] == "ENABLED"],
        "conversion_audit": audit,
    }

