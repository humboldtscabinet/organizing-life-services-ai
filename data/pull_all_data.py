"""
Pull data from GSC, GA4, and Google Ads for blog strategy analysis.
Run via: docker exec ols-api python /app/data/pull_all_data.py
"""
import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, "/app")

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, OrderBy, FilterExpression, Filter
)

CREDENTIALS_PATH = "/app/credentials/google-service-account.json"
GA4_PROPERTY_ID = "396184354"
DAYS_BACK = 90  # 3 months of data for trend analysis

# Date range
end_date = datetime.now() - timedelta(days=1)  # Yesterday (data lag)
start_date = end_date - timedelta(days=DAYS_BACK)
start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

print(f"Date range: {start_str} to {end_str} ({DAYS_BACK} days)")
print("=" * 60)

results = {}

# ============================================================
# 1. GOOGLE SEARCH CONSOLE
# ============================================================
print("\n[GSC] Pulling Search Console data...")
try:
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    gsc = build("searchconsole", "v1", credentials=creds)

    # Top queries (all)
    gsc_queries = gsc.searchanalytics().query(
        siteUrl="https://organizinglifeservices.com/",
        body={
            "startDate": start_str,
            "endDate": end_str,
            "dimensions": ["query"],
            "rowLimit": 1000,
            "dataState": "all"
        }
    ).execute()

    queries = []
    for row in gsc_queries.get("rows", []):
        queries.append({
            "query": row["keys"][0],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": round(row["ctr"] * 100, 2),
            "position": round(row["position"], 1)
        })

    results["gsc_queries"] = sorted(queries, key=lambda x: x["impressions"], reverse=True)
    print(f"  OK  {len(queries)} queries retrieved")

    # Top pages
    gsc_pages = gsc.searchanalytics().query(
        siteUrl="https://organizinglifeservices.com/",
        body={
            "startDate": start_str,
            "endDate": end_str,
            "dimensions": ["page"],
            "rowLimit": 500,
            "dataState": "all"
        }
    ).execute()

    pages = []
    for row in gsc_pages.get("rows", []):
        pages.append({
            "page": row["keys"][0],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": round(row["ctr"] * 100, 2),
            "position": round(row["position"], 1)
        })

    results["gsc_pages"] = sorted(pages, key=lambda x: x["clicks"], reverse=True)
    print(f"  OK  {len(pages)} pages retrieved")

    # Queries where position is 5-20 (easy win opportunities)
    easy_wins = [q for q in queries if 5 <= q["position"] <= 20 and q["impressions"] >= 10]
    results["gsc_easy_wins"] = sorted(easy_wins, key=lambda x: x["impressions"], reverse=True)
    print(f"  OK  {len(easy_wins)} easy-win queries (position 5-20, 10+ impressions)")

    # High impressions, low CTR (title/meta optimization opportunities)
    low_ctr = [q for q in queries if q["impressions"] >= 50 and q["ctr"] < 3.0]
    results["gsc_low_ctr"] = sorted(low_ctr, key=lambda x: x["impressions"], reverse=True)
    print(f"  OK  {len(low_ctr)} low-CTR queries (50+ impressions, <3% CTR)")

except Exception as e:
    print(f"  FAIL  GSC: {e}")
    results["gsc_error"] = str(e)

# ============================================================
# 2. GOOGLE ANALYTICS 4
# ============================================================
print("\n[GA4] Pulling Analytics data...")
try:
    creds_ga4 = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    ga4_client = BetaAnalyticsDataClient(credentials=creds_ga4)

    # Top blog pages
    blog_report = ga4_client.run_report(RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="activeUsers"),
            Metric(name="averageSessionDuration"),
            Metric(name="bounceRate"),
        ],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(
                    match_type=Filter.StringFilter.MatchType.CONTAINS,
                    value="/blogs/"
                )
            )
        ),
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=100
    ))

    blog_pages = []
    for row in blog_report.rows:
        blog_pages.append({
            "page": row.dimension_values[0].value,
            "pageviews": int(row.metric_values[0].value),
            "users": int(row.metric_values[1].value),
            "avg_duration": round(float(row.metric_values[2].value), 1),
            "bounce_rate": round(float(row.metric_values[3].value) * 100, 1)
        })

    results["ga4_blog_pages"] = blog_pages
    print(f"  OK  {len(blog_pages)} blog pages with traffic data")

    # Overall site metrics
    site_report = ga4_client.run_report(RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
        dimensions=[],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="newUsers"),
        ],
    ))

    if site_report.rows:
        row = site_report.rows[0]
        results["ga4_site_summary"] = {
            "sessions": int(row.metric_values[0].value),
            "active_users": int(row.metric_values[1].value),
            "pageviews": int(row.metric_values[2].value),
            "bounce_rate": round(float(row.metric_values[3].value) * 100, 1),
            "avg_duration": round(float(row.metric_values[4].value), 1),
            "new_users": int(row.metric_values[5].value),
        }
        print(f"  OK  Site summary: {results['ga4_site_summary']['sessions']} sessions, {results['ga4_site_summary']['active_users']} users")

    # Traffic sources
    source_report = ga4_client.run_report(RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
        dimensions=[Dimension(name="sessionSourceMedium")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="conversions"),
        ],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=30
    ))

    sources = []
    for row in source_report.rows:
        sources.append({
            "source_medium": row.dimension_values[0].value,
            "sessions": int(row.metric_values[0].value),
            "users": int(row.metric_values[1].value),
            "conversions": int(row.metric_values[2].value),
        })

    results["ga4_traffic_sources"] = sources
    print(f"  OK  {len(sources)} traffic sources")

    # Top landing pages (all, not just blogs)
    landing_report = ga4_client.run_report(RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
        dimensions=[Dimension(name="landingPage")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=50
    ))

    landings = []
    for row in landing_report.rows:
        landings.append({
            "page": row.dimension_values[0].value,
            "sessions": int(row.metric_values[0].value),
            "users": int(row.metric_values[1].value),
            "bounce_rate": round(float(row.metric_values[2].value) * 100, 1),
            "avg_duration": round(float(row.metric_values[3].value), 1),
        })

    results["ga4_landing_pages"] = landings
    print(f"  OK  {len(landings)} landing pages")

except Exception as e:
    print(f"  FAIL  GA4: {e}")
    results["ga4_error"] = str(e)

# ============================================================
# 3. GOOGLE ADS (via GA4 API)
# ============================================================
print("\n[ADS] Pulling Google Ads data...")
try:
    # Campaign performance
    campaign_report = ga4_client.run_report(RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
        dimensions=[Dimension(name="sessionGoogleAdsCampaignName")],
        metrics=[
            Metric(name="advertiserAdClicks"),
            Metric(name="advertiserAdCost"),
            Metric(name="advertiserAdCostPerClick"),
            Metric(name="advertiserAdImpressions"),
            Metric(name="conversions"),
        ],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="advertiserAdClicks"), desc=True)],
        limit=100
    ))

    campaigns = []
    for row in campaign_report.rows:
        name = row.dimension_values[0].value
        if name and name != "(not set)":
            clicks = int(row.metric_values[0].value)
            impressions = int(row.metric_values[3].value)
            campaigns.append({
                "campaign": name,
                "clicks": clicks,
                "cost": round(float(row.metric_values[1].value), 2),
                "cpc": round(float(row.metric_values[2].value), 2),
                "impressions": impressions,
                "conversions": int(row.metric_values[4].value),
                "ctr": round((clicks / impressions * 100) if impressions > 0 else 0, 2),
            })

    results["ads_campaigns"] = campaigns
    print(f"  OK  {len(campaigns)} campaigns")

    # Keyword performance
    keyword_report = ga4_client.run_report(RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
        dimensions=[
            Dimension(name="sessionGoogleAdsKeyword"),
            Dimension(name="sessionGoogleAdsCampaignName"),
        ],
        metrics=[
            Metric(name="advertiserAdClicks"),
            Metric(name="advertiserAdCost"),
            Metric(name="advertiserAdImpressions"),
            Metric(name="conversions"),
        ],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="advertiserAdClicks"), desc=True)],
        limit=500
    ))

    keywords = []
    for row in keyword_report.rows:
        kw = row.dimension_values[0].value
        if kw and kw != "(not set)":
            clicks = int(row.metric_values[0].value)
            impressions = int(row.metric_values[2].value)
            keywords.append({
                "keyword": kw,
                "campaign": row.dimension_values[1].value,
                "clicks": clicks,
                "cost": round(float(row.metric_values[1].value), 2),
                "impressions": impressions,
                "conversions": int(row.metric_values[3].value),
                "ctr": round((clicks / impressions * 100) if impressions > 0 else 0, 2),
            })

    results["ads_keywords"] = sorted(keywords, key=lambda x: x["clicks"], reverse=True)
    print(f"  OK  {len(keywords)} keywords")

except Exception as e:
    print(f"  FAIL  Ads: {e}")
    results["ads_error"] = str(e)

# ============================================================
# SAVE ALL DATA
# ============================================================
output_path = "/tmp/strategy_data.json"
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"\n{'=' * 60}")
print(f"All data saved to {output_path}")
print(f"{'=' * 60}")

# Quick summary
print("\n--- QUICK SUMMARY ---")
if "gsc_queries" in results:
    top5 = results["gsc_queries"][:5]
    print(f"\nTop 5 GSC queries by impressions:")
    for q in top5:
        print(f"  {q['query']:50s} | imp: {q['impressions']:>6} | clicks: {q['clicks']:>4} | pos: {q['position']:>5}")

if "gsc_easy_wins" in results:
    print(f"\nTop 5 easy-win queries (position 5-20):")
    for q in results["gsc_easy_wins"][:5]:
        print(f"  {q['query']:50s} | imp: {q['impressions']:>6} | pos: {q['position']:>5}")

if "ga4_blog_pages" in results:
    print(f"\nTop 5 blog pages by pageviews:")
    for p in results["ga4_blog_pages"][:5]:
        print(f"  {p['page']:60s} | views: {p['pageviews']:>6} | users: {p['users']:>5}")

if "ads_keywords" in results:
    print(f"\nTop 5 Google Ads keywords by clicks:")
    for k in results["ads_keywords"][:5]:
        print(f"  {k['keyword']:50s} | clicks: {k['clicks']:>4} | cost: ${k['cost']:>8}")
