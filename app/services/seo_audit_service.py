"""
SEO Audit Service — Analyzes data from all pipelines and generates
actionable recommendations for the operator dashboard.

Manual-approval mode: produces recommendations only.
No automated changes — human reviews everything in Google Sheets.

Reads from: gsc_data, ga4_data, google_ads_data
Writes to: seo_reports (Postgres) → Google Sheets "SEO Audit" tabs
"""

import os
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    GA4Data,
    GoogleAdsData,
    GSCData,
    SEOReport,
    WorkflowLog,
)


# ===================== Core Audit Runner =====================


def run_seo_audit(db: Session, days_back: int = 7) -> dict:
    """
    Run a full SEO audit across all data sources.

    Returns a dict with audit results and recommendations.
    Each section is stored as a separate SEOReport row.
    """
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    reports_created = 0
    all_findings = {}

    # --- 1. GSC Audit ---
    gsc_findings = _audit_gsc(db, cutoff, days_back)
    if gsc_findings:
        report = SEOReport(
            report_type="gsc_audit",
            report_date=datetime.utcnow(),
            summary=gsc_findings["summary"],
            data=gsc_findings,
        )
        db.add(report)
        reports_created += 1
        all_findings["gsc"] = gsc_findings

    # --- 2. GA4 Audit ---
    ga4_findings = _audit_ga4(db, cutoff, days_back)
    if ga4_findings:
        report = SEOReport(
            report_type="ga4_audit",
            report_date=datetime.utcnow(),
            summary=ga4_findings["summary"],
            data=ga4_findings,
        )
        db.add(report)
        reports_created += 1
        all_findings["ga4"] = ga4_findings

    # --- 3. Google Ads Audit ---
    ads_findings = _audit_google_ads(db, cutoff, days_back)
    if ads_findings:
        report = SEOReport(
            report_type="google_ads_audit",
            report_date=datetime.utcnow(),
            summary=ads_findings["summary"],
            data=ads_findings,
        )
        db.add(report)
        reports_created += 1
        all_findings["google_ads"] = ads_findings

    # --- 4. Cross-channel recommendations ---
    recommendations = _generate_recommendations(all_findings)
    if recommendations:
        report = SEOReport(
            report_type="seo_recommendations",
            report_date=datetime.utcnow(),
            summary=f"{len(recommendations)} actionable recommendations generated",
            data={"recommendations": recommendations},
        )
        db.add(report)
        reports_created += 1
        all_findings["recommendations"] = recommendations

    db.commit()

    # Log the workflow
    log_entry = WorkflowLog(
        workflow_name="seo_audit",
        status="success",
        payload={
            "days_back": days_back,
            "reports_created": reports_created,
            "sections": list(all_findings.keys()),
        },
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "days_back": days_back,
        "reports_created": reports_created,
        "findings": all_findings,
    }


# ===================== GSC Audit =====================


def _audit_gsc(db: Session, cutoff: datetime, days_back: int) -> dict | None:
    """Analyze GSC data for search performance insights."""
    records = (
        db.query(GSCData)
        .filter(GSCData.date >= cutoff)
        .all()
    )

    if not records:
        return None

    # Aggregate by query
    query_stats = {}
    for r in records:
        q = r.query or "(unknown)"
        if q not in query_stats:
            query_stats[q] = {
                "clicks": 0,
                "impressions": 0,
                "ctr_sum": 0.0,
                "position_sum": 0.0,
                "count": 0,
            }
        query_stats[q]["clicks"] += r.clicks or 0
        query_stats[q]["impressions"] += r.impressions or 0
        query_stats[q]["ctr_sum"] += r.ctr or 0
        query_stats[q]["position_sum"] += r.position or 0
        query_stats[q]["count"] += 1

    # Top queries by clicks
    top_queries = sorted(
        query_stats.items(),
        key=lambda x: x[1]["clicks"],
        reverse=True,
    )[:10]

    # High-impression, low-click queries (opportunity keywords)
    opportunity_keywords = []
    for q, stats in query_stats.items():
        avg_ctr = stats["ctr_sum"] / stats["count"] if stats["count"] else 0
        avg_pos = stats["position_sum"] / stats["count"] if stats["count"] else 0
        if stats["impressions"] >= 10 and avg_ctr < 0.03 and avg_pos <= 20:
            opportunity_keywords.append({
                "query": q,
                "impressions": stats["impressions"],
                "clicks": stats["clicks"],
                "avg_ctr": round(avg_ctr, 4),
                "avg_position": round(avg_pos, 1),
                "action": "Improve title/meta description to boost CTR",
            })

    opportunity_keywords.sort(key=lambda x: x["impressions"], reverse=True)
    opportunity_keywords = opportunity_keywords[:15]

    # Queries ranking on page 2 (positions 11-20) — close to page 1
    almost_page_one = []
    for q, stats in query_stats.items():
        avg_pos = stats["position_sum"] / stats["count"] if stats["count"] else 0
        if 8 <= avg_pos <= 20 and stats["impressions"] >= 5:
            almost_page_one.append({
                "query": q,
                "impressions": stats["impressions"],
                "clicks": stats["clicks"],
                "avg_position": round(avg_pos, 1),
                "action": "Optimize content to push to page 1",
            })

    almost_page_one.sort(key=lambda x: x["impressions"], reverse=True)
    almost_page_one = almost_page_one[:10]

    # Aggregate by page
    page_stats = {}
    for r in records:
        p = r.page or "(unknown)"
        if p not in page_stats:
            page_stats[p] = {"clicks": 0, "impressions": 0}
        page_stats[p]["clicks"] += r.clicks or 0
        page_stats[p]["impressions"] += r.impressions or 0

    top_pages = sorted(
        page_stats.items(),
        key=lambda x: x[1]["clicks"],
        reverse=True,
    )[:10]

    total_clicks = sum(s["clicks"] for s in query_stats.values())
    total_impressions = sum(s["impressions"] for s in query_stats.values())

    return {
        "summary": (
            f"{total_clicks} clicks, {total_impressions} impressions "
            f"over {days_back} days. "
            f"{len(opportunity_keywords)} opportunity keywords found, "
            f"{len(almost_page_one)} queries near page 1."
        ),
        "totals": {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "unique_queries": len(query_stats),
            "unique_pages": len(page_stats),
        },
        "top_queries": [
            {"query": q, **s} for q, s in top_queries
        ],
        "top_pages": [
            {"page": p, **s} for p, s in top_pages
        ],
        "opportunity_keywords": opportunity_keywords,
        "almost_page_one": almost_page_one,
    }


# ===================== GA4 Audit =====================


def _audit_ga4(db: Session, cutoff: datetime, days_back: int) -> dict | None:
    """Analyze GA4 data for traffic and engagement insights."""

    # Daily overview data
    overview_records = (
        db.query(GA4Data)
        .filter(
            GA4Data.data["report"].as_string() == "daily_overview",
            GA4Data.date >= cutoff,
        )
        .all()
    )

    if not overview_records:
        return None

    # Pivot by date
    date_metrics = {}
    for r in overview_records:
        date_key = r.dimension_value
        if date_key not in date_metrics:
            date_metrics[date_key] = {}
        date_metrics[date_key][r.metric_name] = r.metric_value or 0

    # Calculate period totals
    total_sessions = sum(m.get("sessions", 0) for m in date_metrics.values())
    total_users = sum(m.get("activeUsers", 0) for m in date_metrics.values())
    total_new_users = sum(m.get("newUsers", 0) for m in date_metrics.values())
    total_pageviews = sum(m.get("screenPageViews", 0) for m in date_metrics.values())

    avg_bounce = 0
    avg_duration = 0
    num_days = len(date_metrics)
    if num_days > 0:
        avg_bounce = sum(
            m.get("bounceRate", 0) for m in date_metrics.values()
        ) / num_days
        avg_duration = sum(
            m.get("averageSessionDuration", 0) for m in date_metrics.values()
        ) / num_days

    # Daily trend (sorted)
    daily_trend = []
    for date_key in sorted(date_metrics.keys()):
        m = date_metrics[date_key]
        daily_trend.append({
            "date": f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:]}",
            "sessions": int(m.get("sessions", 0)),
            "users": int(m.get("activeUsers", 0)),
            "pageviews": int(m.get("screenPageViews", 0)),
        })

    # Detect traffic drops (day-over-day)
    traffic_alerts = []
    for i in range(1, len(daily_trend)):
        prev = daily_trend[i - 1]["sessions"]
        curr = daily_trend[i]["sessions"]
        if prev > 0 and curr < prev * 0.5:
            traffic_alerts.append({
                "date": daily_trend[i]["date"],
                "sessions": curr,
                "previous_day_sessions": prev,
                "drop_pct": round((1 - curr / prev) * 100, 1),
                "alert": "Sessions dropped >50% day-over-day",
            })

    # Top pages
    top_pages_records = (
        db.query(GA4Data)
        .filter(
            GA4Data.data["report"].as_string() == "top_pages",
            GA4Data.date >= cutoff,
        )
        .order_by(GA4Data.metric_value.desc())
        .limit(10)
        .all()
    )

    top_pages = []
    for r in top_pages_records:
        top_pages.append({
            "page": r.dimension_value,
            "pageviews": int(r.metric_value or 0),
            "users": int(r.data.get("activeUsers", 0)) if r.data else 0,
        })

    # Top traffic sources
    sources_records = (
        db.query(GA4Data)
        .filter(
            GA4Data.data["report"].as_string() == "traffic_sources",
            GA4Data.date >= cutoff,
        )
        .order_by(GA4Data.metric_value.desc())
        .limit(10)
        .all()
    )

    top_sources = []
    for r in sources_records:
        top_sources.append({
            "source_medium": r.dimension_value,
            "sessions": int(r.metric_value or 0),
        })

    return {
        "summary": (
            f"{int(total_sessions)} sessions, {int(total_users)} users, "
            f"{int(total_pageviews)} pageviews over {days_back} days. "
            f"Avg bounce rate: {round(avg_bounce * 100, 1)}%. "
            f"{len(traffic_alerts)} traffic alerts."
        ),
        "totals": {
            "sessions": int(total_sessions),
            "active_users": int(total_users),
            "new_users": int(total_new_users),
            "pageviews": int(total_pageviews),
            "avg_bounce_rate_pct": round(avg_bounce * 100, 1),
            "avg_session_duration_s": round(avg_duration, 1),
        },
        "daily_trend": daily_trend,
        "traffic_alerts": traffic_alerts,
        "top_pages": top_pages,
        "top_sources": top_sources,
    }


# ===================== Google Ads Audit =====================


def _audit_google_ads(
    db: Session, cutoff: datetime, days_back: int
) -> dict | None:
    """Analyze Google Ads data for spend efficiency and performance."""

    campaign_records = (
        db.query(GoogleAdsData)
        .filter(
            GoogleAdsData.data["report"].as_string() == "campaign",
            GoogleAdsData.date >= cutoff,
        )
        .all()
    )

    if not campaign_records:
        return None

    # Aggregate by campaign
    campaign_totals = {}
    for r in campaign_records:
        name = r.campaign_name or "(unknown)"
        if name not in campaign_totals:
            campaign_totals[name] = {
                "clicks": 0,
                "impressions": 0,
                "cost": 0.0,
                "conversions": 0.0,
            }
        campaign_totals[name]["clicks"] += r.clicks or 0
        campaign_totals[name]["impressions"] += r.impressions or 0
        campaign_totals[name]["cost"] += r.cost or 0
        campaign_totals[name]["conversions"] += r.conversions or 0

    # Calculate derived metrics per campaign
    campaign_performance = []
    for name, totals in campaign_totals.items():
        ctr = (
            totals["clicks"] / totals["impressions"]
            if totals["impressions"] > 0
            else 0
        )
        cpc = (
            totals["cost"] / totals["clicks"]
            if totals["clicks"] > 0
            else 0
        )
        cost_per_conv = (
            totals["cost"] / totals["conversions"]
            if totals["conversions"] > 0
            else 0
        )

        campaign_performance.append({
            "campaign": name,
            "clicks": totals["clicks"],
            "impressions": totals["impressions"],
            "ctr_pct": round(ctr * 100, 2),
            "total_cost": round(totals["cost"], 2),
            "avg_cpc": round(cpc, 2),
            "conversions": round(totals["conversions"], 1),
            "cost_per_conversion": round(cost_per_conv, 2),
        })

    campaign_performance.sort(key=lambda x: x["total_cost"], reverse=True)

    total_spend = sum(c["total_cost"] for c in campaign_performance)
    total_clicks = sum(c["clicks"] for c in campaign_performance)
    total_conversions = sum(c["conversions"] for c in campaign_performance)

    # Flag inefficient campaigns (high spend, low conversions)
    inefficient = []
    for c in campaign_performance:
        if c["total_cost"] > 0 and c["conversions"] == 0:
            inefficient.append({
                **c,
                "alert": "Spending with zero conversions",
            })
        elif c["ctr_pct"] < 1.0 and c["impressions"] > 100:
            inefficient.append({
                **c,
                "alert": "CTR below 1% — review ad copy and targeting",
            })

    return {
        "summary": (
            f"${round(total_spend, 2)} total spend, "
            f"{total_clicks} clicks, "
            f"{round(total_conversions, 1)} conversions over {days_back} days. "
            f"{len(inefficient)} campaigns flagged for review."
        ),
        "totals": {
            "total_spend": round(total_spend, 2),
            "total_clicks": total_clicks,
            "total_conversions": round(total_conversions, 1),
            "campaigns_active": len(campaign_totals),
        },
        "campaign_performance": campaign_performance,
        "inefficient_campaigns": inefficient,
    }


# ===================== Recommendations Engine =====================


def _generate_recommendations(findings: dict) -> list:
    """
    Generate cross-channel recommendations based on all audit findings.

    Each recommendation has: priority, category, finding, action.
    """
    recs = []

    # --- GSC-based recommendations ---
    gsc = findings.get("gsc")
    if gsc:
        # Opportunity keywords
        for kw in gsc.get("opportunity_keywords", [])[:5]:
            recs.append({
                "priority": "HIGH",
                "category": "SEO — Content Optimization",
                "finding": (
                    f"'{kw['query']}' has {kw['impressions']} impressions "
                    f"but only {kw['clicks']} clicks "
                    f"(CTR: {round(kw['avg_ctr'] * 100, 1)}%)"
                ),
                "action": (
                    f"Improve title tag and meta description for pages "
                    f"ranking for '{kw['query']}' to increase CTR. "
                    f"Current avg position: {kw['avg_position']}"
                ),
            })

        # Almost page 1 queries
        for kw in gsc.get("almost_page_one", [])[:5]:
            recs.append({
                "priority": "HIGH",
                "category": "SEO — Ranking Improvement",
                "finding": (
                    f"'{kw['query']}' ranks at position {kw['avg_position']} "
                    f"with {kw['impressions']} impressions"
                ),
                "action": (
                    f"Add more relevant content, internal links, and "
                    f"ensure on-page optimization for '{kw['query']}' "
                    f"to push into top 10."
                ),
            })

    # --- GA4-based recommendations ---
    ga4 = findings.get("ga4")
    if ga4:
        totals = ga4.get("totals", {})

        # High bounce rate alert
        if totals.get("avg_bounce_rate_pct", 0) > 70:
            recs.append({
                "priority": "MEDIUM",
                "category": "UX — Engagement",
                "finding": (
                    f"Average bounce rate is "
                    f"{totals['avg_bounce_rate_pct']}% (above 70%)"
                ),
                "action": (
                    "Review landing pages for relevance, load speed, "
                    "mobile-friendliness, and clear calls-to-action. "
                    "Consider adding interior links to keep visitors engaged."
                ),
            })

        # Low session duration
        if totals.get("avg_session_duration_s", 0) < 30:
            recs.append({
                "priority": "MEDIUM",
                "category": "UX — Engagement",
                "finding": (
                    f"Average session duration is only "
                    f"{totals['avg_session_duration_s']}s"
                ),
                "action": (
                    "Add engaging content (photos, testimonials, videos) "
                    "and clear navigation to increase time on site."
                ),
            })

        # Traffic drop alerts
        for alert in ga4.get("traffic_alerts", []):
            recs.append({
                "priority": "HIGH",
                "category": "Traffic — Alert",
                "finding": (
                    f"Traffic dropped {alert['drop_pct']}% on "
                    f"{alert['date']} ({alert['sessions']} sessions "
                    f"vs {alert['previous_day_sessions']} prior day)"
                ),
                "action": (
                    "Investigate: check for site downtime, Google algorithm "
                    "updates, or seasonal patterns. Review GSC for "
                    "indexing issues."
                ),
            })

    # --- Google Ads recommendations ---
    ads = findings.get("google_ads")
    if ads:
        for camp in ads.get("inefficient_campaigns", [])[:3]:
            recs.append({
                "priority": "HIGH",
                "category": "Ads — Spend Efficiency",
                "finding": (
                    f"Campaign '{camp['campaign']}': "
                    f"${camp['total_cost']} spent, "
                    f"{camp['clicks']} clicks, "
                    f"{camp['conversions']} conversions. "
                    f"{camp['alert']}"
                ),
                "action": (
                    "Review ad copy, keywords, and landing page. "
                    "Consider pausing underperforming ad groups or "
                    "adjusting bidding strategy."
                ),
            })

        # Overall ROAS check
        totals = ads.get("totals", {})
        if totals.get("total_spend", 0) > 0 and totals.get("total_conversions", 0) == 0:
            recs.append({
                "priority": "HIGH",
                "category": "Ads — ROI",
                "finding": (
                    f"${totals['total_spend']} spent with zero conversions"
                ),
                "action": (
                    "Audit conversion tracking setup in Google Ads / GA4. "
                    "If tracking is correct, review targeting, ad copy, "
                    "and landing page experience."
                ),
            })

    # Sort by priority
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    recs.sort(key=lambda x: priority_order.get(x["priority"], 3))

    return recs
