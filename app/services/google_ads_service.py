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
from sqlalchemy.orm import Session

from app.db.models import GoogleAdsData, WorkflowLog


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

        record = GoogleAdsData(
            campaign_name=campaign_name,
            ad_group=None,  # Campaign-level row
            clicks=clicks,
            impressions=impressions,
            cost=cost,
            conversions=conversions,
            date=date_obj,
            data={
                "report": "campaign",
                "ctr": round(ctr, 4),
                "average_cpc": cpc,
                "customer_id": customer_id,
                "source": "ga4_api",
            },
        )
        db.add(record)
        rows_inserted += 1
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

        record = GoogleAdsData(
            campaign_name=campaign_name,
            ad_group=ad_group_name,
            clicks=clicks,
            impressions=impressions,
            cost=cost,
            conversions=conversions,
            date=date_obj,
            data={
                "report": "ad_group",
                "customer_id": customer_id,
                "source": "ga4_api",
            },
        )
        db.add(record)
        rows_inserted += 1
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

        record = GoogleAdsData(
            campaign_name=campaign_name,
            ad_group=keyword,  # Store keyword in ad_group field
            clicks=clicks,
            impressions=impressions,
            cost=cost,
            conversions=0,
            date=date_obj,
            data={
                "report": "keyword",
                "customer_id": customer_id,
                "source": "ga4_api",
            },
        )
        db.add(record)
        rows_inserted += 1
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
