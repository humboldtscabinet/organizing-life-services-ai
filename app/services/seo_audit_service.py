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


# =========================================================================
# Deep SEO Audit — period-over-period from live GSC + GA4 APIs
# =========================================================================
#
# This is the canonical implementation. The standalone CLI script
# `data/deep_seo_audit.py` calls into this same code path so the report
# stays consistent whether run from Docker (`POST /api/seo/audit/deep`)
# or from a developer laptop.

from app.services import seo_crawler  # noqa: E402


# ---------- Math helpers ----------------------------------------------------

def weighted_avg_position(rows: list[dict]) -> float:
    """
    Impression-weighted average position.

    GSC's raw "average position" is unweighted — a single long-tail
    impression at position 99 distorts the number as much as a money
    keyword at position 3. This weights every position by the number of
    impressions it produced, which is what humans actually mean when
    they say "where do we rank on average".
    """
    total_imp = sum(r.get("impressions", 0) for r in rows)
    if total_imp <= 0:
        return 0.0
    return (
        sum(r.get("position", 0) * r.get("impressions", 0) for r in rows)
        / total_imp
    )


def _pct_change(curr: float, prev: float) -> float | None:
    if not prev:
        return None
    return (curr - prev) / prev * 100.0


def _totals(rows: list[dict]) -> dict:
    clicks = sum(r.get("clicks", 0) for r in rows)
    imps = sum(r.get("impressions", 0) for r in rows)
    ctr = clicks / imps if imps else 0.0
    return {
        "clicks": clicks,
        "impressions": imps,
        "ctr": ctr,
        "avg_position_unweighted": (
            sum(r.get("position", 0) for r in rows) / len(rows) if rows else 0.0
        ),
        "avg_position_weighted": weighted_avg_position(rows),
    }


# ---------- GSC live pull (period comparison) -------------------------------

def _gsc_client():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/credentials/google-service-account.json",
    )
    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def _gsc_query(svc, site_url: str, start, end, dims: list[str],
               row_limit: int = 25000) -> list[dict]:
    rows: list[dict] = []
    start_row = 0
    while True:
        body = {
            "startDate": str(start),
            "endDate": str(end),
            "dimensions": dims,
            "rowLimit": row_limit,
            "startRow": start_row,
        }
        resp = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
        batch = resp.get("rows", [])
        rows.extend(batch)
        if len(batch) < row_limit:
            break
        start_row += row_limit
        if start_row > 100000:
            break
    # Flatten keys
    out = []
    for r in rows:
        item = {
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr": r.get("ctr", 0.0),
            "position": r.get("position", 0.0),
        }
        for i, dim in enumerate(dims):
            item[dim] = r["keys"][i] if i < len(r["keys"]) else ""
        out.append(item)
    return out


def _gsc_period_block(
    site_url: str, cur_start, cur_end, prv_start, prv_end
) -> dict:
    svc = _gsc_client()

    cur_all = _gsc_query(svc, site_url, cur_start, cur_end, [])
    prv_all = _gsc_query(svc, site_url, prv_start, prv_end, [])

    cur_tot = _totals(cur_all)
    prv_tot = _totals(prv_all)

    deltas = {
        "clicks_delta_pct": _pct_change(cur_tot["clicks"], prv_tot["clicks"]),
        "impressions_delta_pct": _pct_change(
            cur_tot["impressions"], prv_tot["impressions"]
        ),
        "ctr_delta_pp": (
            (cur_tot["ctr"] - prv_tot["ctr"]) * 100
            if prv_tot["impressions"] else None
        ),
        "position_delta_unweighted": (
            cur_tot["avg_position_unweighted"]
            - prv_tot["avg_position_unweighted"]
            if prv_tot["impressions"] else None
        ),
        "position_delta_weighted": (
            cur_tot["avg_position_weighted"]
            - prv_tot["avg_position_weighted"]
            if prv_tot["impressions"] else None
        ),
    }

    # Queries
    cur_q = _gsc_query(svc, site_url, cur_start, cur_end, ["query"])
    prv_q = _gsc_query(svc, site_url, prv_start, prv_end, ["query"])
    cur_q_map = {r["query"]: r for r in cur_q}
    prv_q_map = {r["query"]: r for r in prv_q}

    movers = []
    for q, c in cur_q_map.items():
        p = prv_q_map.get(q)
        prev_clicks = p["clicks"] if p else 0
        prev_pos = p["position"] if p else None
        prev_imp = p["impressions"] if p else 0
        movers.append({
            "query": q,
            "clicks": c["clicks"],
            "prev_clicks": prev_clicks,
            "clicks_delta": c["clicks"] - prev_clicks,
            "impressions": c["impressions"],
            "prev_impressions": prev_imp,
            "position": round(c["position"], 1),
            "prev_position": round(prev_pos, 1) if prev_pos else None,
            "position_delta": (
                round(c["position"] - prev_pos, 1) if prev_pos else None
            ),
            "ctr": round(c["ctr"], 4),
        })

    top_winners = sorted(movers, key=lambda x: x["clicks_delta"], reverse=True)[:20]
    top_losers = sorted(
        [m for m in movers if m["prev_clicks"] > 0],
        key=lambda x: x["clicks_delta"],
    )[:20]
    rank_gains = sorted(
        [m for m in movers if m["position_delta"] is not None
         and m["prev_impressions"] >= 5],
        key=lambda x: x["position_delta"],
    )[:20]
    rank_losses = sorted(
        [m for m in movers if m["position_delta"] is not None
         and m["prev_impressions"] >= 5],
        key=lambda x: x["position_delta"],
        reverse=True,
    )[:20]

    # Pages
    cur_p = _gsc_query(svc, site_url, cur_start, cur_end, ["page"])
    prv_p = _gsc_query(svc, site_url, prv_start, prv_end, ["page"])
    cur_p_map = {r["page"]: r for r in cur_p}
    prv_p_map = {r["page"]: r for r in prv_p}

    page_changes = []
    for url, c in cur_p_map.items():
        p = prv_p_map.get(url)
        prev_clicks = p["clicks"] if p else 0
        prev_imp = p["impressions"] if p else 0
        prev_pos = p["position"] if p else None
        page_changes.append({
            "page": url,
            "clicks": c["clicks"],
            "prev_clicks": prev_clicks,
            "clicks_delta": c["clicks"] - prev_clicks,
            "impressions": c["impressions"],
            "prev_impressions": prev_imp,
            "impressions_delta": c["impressions"] - prev_imp,
            "position": round(c["position"], 1),
            "prev_position": round(prev_pos, 1) if prev_pos else None,
            "position_delta": (
                round(c["position"] - prev_pos, 1) if prev_pos else None
            ),
            "ctr": round(c["ctr"], 4),
        })

    page_winners = sorted(
        page_changes, key=lambda x: x["clicks_delta"], reverse=True
    )[:15]
    page_losers = sorted(
        [p for p in page_changes if p["prev_clicks"] > 0],
        key=lambda x: x["clicks_delta"],
    )[:15]

    # Query × page for striking distance + CTR opps
    cur_qp = _gsc_query(svc, site_url, cur_start, cur_end, ["query", "page"])

    ctr_opportunities = [
        {
            "query": r["query"],
            "page": r["page"],
            "impressions": r["impressions"],
            "ctr": round(r["ctr"], 4),
            "position": round(r["position"], 1),
        }
        for r in cur_qp
        if r["impressions"] >= 30
        and 1 <= r["position"] <= 20
        and r["ctr"] < 0.03
    ]
    ctr_opportunities.sort(key=lambda x: x["impressions"], reverse=True)

    striking_distance = [
        {
            "query": r["query"],
            "page": r["page"],
            "impressions": r["impressions"],
            "clicks": r["clicks"],
            "position": round(r["position"], 1),
        }
        for r in cur_qp
        if 8 <= r["position"] <= 20 and r["impressions"] >= 10
    ]
    striking_distance.sort(key=lambda x: x["impressions"], reverse=True)

    return {
        "windows": {
            "current": {"start": str(cur_start), "end": str(cur_end)},
            "prior":   {"start": str(prv_start), "end": str(prv_end)},
        },
        "totals_current": cur_tot,
        "totals_prior": prv_tot,
        "deltas": deltas,
        "top_query_winners": top_winners,
        "top_query_losers": top_losers,
        "biggest_rank_gains": rank_gains,
        "biggest_rank_losses": rank_losses,
        "page_winners": page_winners,
        "page_losers": page_losers,
        "ctr_opportunities": ctr_opportunities[:30],
        "striking_distance": striking_distance[:30],
    }


# ---------- GA4 period block (live) -----------------------------------------

def _ga4_period_block(cur_start, cur_end, prv_start, prv_end) -> dict | None:
    prop_id = os.getenv("GA4_PROPERTY_ID")
    if not prop_id:
        return None
    try:
        from google.oauth2 import service_account
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest, FilterExpression,
            Filter,
        )
    except ImportError:
        return {"error": "google-analytics-data not installed"}

    creds_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/credentials/google-service-account.json",
    )
    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{prop_id}"

    def run(start, end, dims, mets, filt=None, limit=10000):
        req = RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
            dimensions=[Dimension(name=d) for d in dims],
            metrics=[Metric(name=m) for m in mets],
            limit=limit,
        )
        if filt is not None:
            req.dimension_filter = filt
        return client.run_report(req)

    def sum_metrics(resp) -> dict:
        out: dict[str, float] = {}
        for row in resp.rows:
            for i, mv in enumerate(row.metric_values):
                k = resp.metric_headers[i].name
                out[k] = out.get(k, 0.0) + float(mv.value or 0)
        return out

    overall = ["sessions", "activeUsers", "newUsers", "screenPageViews",
               "engagementRate", "averageSessionDuration", "bounceRate"]

    cur_all = run(cur_start, cur_end, [], overall)
    prv_all = run(prv_start, prv_end, [], overall)

    organic_filter = FilterExpression(
        filter=Filter(
            field_name="sessionDefaultChannelGroup",
            string_filter=Filter.StringFilter(
                value="Organic Search", case_sensitive=False
            ),
        )
    )
    org_mets = ["sessions", "activeUsers", "screenPageViews",
                "engagementRate", "conversions"]
    cur_org = run(cur_start, cur_end, [], org_mets, filt=organic_filter)
    prv_org = run(prv_start, prv_end, [], org_mets, filt=organic_filter)

    channels_resp = run(
        cur_start, cur_end,
        ["sessionDefaultChannelGroup"],
        ["sessions", "activeUsers", "conversions"],
        limit=20,
    )
    channels = [
        {
            "channel": r.dimension_values[0].value,
            "sessions": float(r.metric_values[0].value or 0),
            "users": float(r.metric_values[1].value or 0),
            "conversions": float(r.metric_values[2].value or 0),
        }
        for r in channels_resp.rows
    ]

    lp_resp = run(
        cur_start, cur_end,
        ["landingPagePlusQueryString"],
        ["sessions", "activeUsers", "engagementRate", "conversions"],
        filt=organic_filter,
        limit=25,
    )
    landing = [
        {
            "page": r.dimension_values[0].value,
            "sessions": float(r.metric_values[0].value or 0),
            "users": float(r.metric_values[1].value or 0),
            "engagement_rate": float(r.metric_values[2].value or 0),
            "conversions": float(r.metric_values[3].value or 0),
        }
        for r in lp_resp.rows
    ]

    return {
        "windows": {
            "current": {"start": str(cur_start), "end": str(cur_end)},
            "prior":   {"start": str(prv_start), "end": str(prv_end)},
        },
        "all_traffic_current": sum_metrics(cur_all),
        "all_traffic_prior":   sum_metrics(prv_all),
        "organic_current":     sum_metrics(cur_org),
        "organic_prior":       sum_metrics(prv_org),
        "channels_current": channels,
        "top_organic_landing_pages": landing,
    }


# ---------- Executive summary -----------------------------------------------

def build_executive_summary(gsc: dict, ga4: dict | None,
                            crawl: dict | None,
                            shopify_overrides: dict | None = None) -> dict:
    """Headline numbers + verdict bullets, suitable for the dashboard."""
    cur = gsc["totals_current"]
    prv = gsc["totals_prior"]
    d = gsc["deltas"]

    verdict = []
    if (d["clicks_delta_pct"] or 0) > 5:
        verdict.append(
            f"Clicks up {d['clicks_delta_pct']:.1f}% — optimizations driving traffic."
        )
    elif (d["clicks_delta_pct"] or 0) < -5:
        verdict.append(
            f"Clicks down {abs(d['clicks_delta_pct']):.1f}% — recent changes not lifting traffic."
        )
    if d["ctr_delta_pp"] is not None and abs(d["ctr_delta_pp"]) > 0.2:
        direction = "up" if d["ctr_delta_pp"] > 0 else "down"
        verdict.append(
            f"CTR {direction} {abs(d['ctr_delta_pp']):.2f} pp — meta/title work {'paying off' if direction=='up' else 'needs another pass'}."
        )
    if d["position_delta_weighted"] is not None:
        if d["position_delta_weighted"] < -0.3:
            verdict.append(
                f"Weighted position improved by {abs(d['position_delta_weighted']):.1f} — money keywords moving up."
            )
        elif d["position_delta_weighted"] > 0.3:
            verdict.append(
                f"Weighted position dropped by {d['position_delta_weighted']:.1f} — investigate top queries."
            )

    summary = {
        "windows": gsc["windows"],
        "headline": {
            "clicks_current": cur["clicks"],
            "clicks_prior": prv["clicks"],
            "clicks_delta_pct": d["clicks_delta_pct"],
            "impressions_current": cur["impressions"],
            "impressions_prior": prv["impressions"],
            "impressions_delta_pct": d["impressions_delta_pct"],
            "ctr_current_pct": round(cur["ctr"] * 100, 2),
            "ctr_prior_pct": round(prv["ctr"] * 100, 2),
            "ctr_delta_pp": d["ctr_delta_pp"],
            "weighted_position_current": round(cur["avg_position_weighted"], 2),
            "weighted_position_prior": round(prv["avg_position_weighted"], 2),
            "weighted_position_delta": d["position_delta_weighted"],
            "raw_position_current": round(cur["avg_position_unweighted"], 2),
            "raw_position_prior": round(prv["avg_position_unweighted"], 2),
        },
        "verdict": verdict,
    }

    if ga4 and "error" not in (ga4 or {}):
        org_c = ga4.get("organic_current", {})
        org_p = ga4.get("organic_prior", {})
        summary["ga4"] = {
            "organic_sessions_current": int(org_c.get("sessions", 0)),
            "organic_sessions_prior": int(org_p.get("sessions", 0)),
            "organic_conversions_current": int(org_c.get("conversions", 0)),
            "organic_conversions_prior": int(org_p.get("conversions", 0)),
        }

    if crawl:
        diff = crawl.get("diff", {})
        summary["crawl"] = {
            "urls_crawled": crawl.get("browser", {}).get("urls_crawled", 0),
            "urls_ok_browser": crawl.get("browser", {}).get("urls_ok", 0),
            "urls_ok_googlebot": crawl.get("googlebot", {}).get("urls_ok", 0),
            "status_mismatches": diff.get("status_mismatch_count", 0),
            "browser_blocked_googlebot_ok": len(
                diff.get("browser_blocked_but_googlebot_ok", [])
            ),
            "googlebot_blocked_browser_ok": len(
                diff.get("googlebot_blocked_but_browser_ok", [])
            ),
        }

    if shopify_overrides:
        summary["shopify_overrides"] = {
            "resources_audited": shopify_overrides.get("resources_audited", 0),
            "resources_flagged": shopify_overrides.get("resources_flagged", 0),
            "theme_overrides": len(
                shopify_overrides.get("theme_overrides", [])
            ),
            "flag_counts": shopify_overrides.get("flag_counts", {}),
        }

    return summary


# ---------- Public entry point ---------------------------------------------

def run_deep_seo_audit(
    db: Session,
    period_days: int = 28,
    include_crawl: bool = True,
    include_shopify_overrides: bool = False,
    max_urls: int = 250,
) -> dict:
    """
    Run a full deep SEO audit:
      - GSC live pull, current period vs prior period
      - GA4 live pull, same windows
      - Optional dual-UA crawl (browser + Googlebot) + diff
      - Optional Shopify SEO-override detection
      - Impression-weighted position score
      - Persist as SEOReport(report_type='deep_audit')
    """
    site_url = os.getenv("GSC_SITE_URL")
    if not site_url:
        raise ValueError("GSC_SITE_URL is not set")

    today = datetime.utcnow().date()
    gsc_end = today - timedelta(days=3)  # GSC lag
    cur_start = gsc_end - timedelta(days=period_days - 1)
    prv_end = cur_start - timedelta(days=1)
    prv_start = prv_end - timedelta(days=period_days - 1)

    gsc = _gsc_period_block(site_url, cur_start, gsc_end, prv_start, prv_end)
    ga4 = _ga4_period_block(
        today - timedelta(days=period_days),
        today - timedelta(days=1),
        today - timedelta(days=period_days * 2),
        today - timedelta(days=period_days + 1),
    )

    crawl = None
    if include_crawl:
        try:
            crawl = seo_crawler.dual_ua_crawl(site_url, max_urls=max_urls)
        except Exception as e:
            crawl = {"error": str(e)}

    shopify_overrides = None
    if include_shopify_overrides:
        try:
            from app.services import shopify_seo_audit_service
            shopify_overrides = (
                shopify_seo_audit_service.audit_shopify_seo_overrides()
            )
        except Exception as e:
            shopify_overrides = {"error": str(e)}

    exec_summary = build_executive_summary(
        gsc, ga4, crawl, shopify_overrides
    )

    payload = {
        "executive_summary": exec_summary,
        "gsc": gsc,
        "ga4": ga4,
        "crawl": crawl,
        "shopify_overrides": shopify_overrides,
    }

    headline = exec_summary["headline"]
    summary_text = (
        f"Clicks {headline['clicks_prior']} → {headline['clicks_current']} "
        f"({headline['clicks_delta_pct']:.1f}% Δ); "
        f"CTR {headline['ctr_prior_pct']}% → {headline['ctr_current_pct']}%; "
        f"weighted position "
        f"{headline['weighted_position_prior']} → "
        f"{headline['weighted_position_current']}."
    )

    report = SEOReport(
        report_type="deep_audit",
        report_date=datetime.utcnow(),
        summary=summary_text,
        data=payload,
    )
    db.add(report)

    db.add(WorkflowLog(
        workflow_name="deep_seo_audit",
        status="success",
        payload={
            "period_days": period_days,
            "include_crawl": include_crawl,
            "include_shopify_overrides": include_shopify_overrides,
            "report_id": None,  # filled below after flush
        },
    ))
    db.commit()
    db.refresh(report)

    return {
        "status": "success",
        "report_id": report.id,
        "summary": summary_text,
        "data": payload,
    }
