"""
Dashboard Service — Task recommendation engine for OLS Marketing Dashboard.

Generates actionable tasks based on threshold analysis of:
- Google Search Console data (GSCData)
- Google Analytics 4 data (GA4Data)
- Google Ads data (GoogleAdsData)
- SEO audit recommendations (SEOReport)

Manual-approval mode: generates tasks, waits for human approval before execution.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.db.models import (
    DashboardTask,
    GA4Data,
    GoogleAdsData,
    GSCData,
    SEOReport,
)

# Geographic service area terms for Organizing Life Services
# Based in Greater Tampa Bay Area, Florida
FLORIDA_SERVICE_AREA_TERMS = {
    'florida', 'fl', 'tampa', 'clearwater', 'largo', 'dunedin', 'palm harbor',
    'st pete', 'saint petersburg', 'pinellas', 'pasco', 'hillsborough',
    'hernando', 'citrus', 'manatee', 'new port richey', 'tarpon springs',
    'holiday', 'hudson', 'brooksville', 'bradenton', 'sarasota', 'oldsmar',
    'safety harbor'
}

# US state names (excluding Florida) indicating out-of-territory
OUT_OF_TERRITORY_STATES = {
    'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
    'connecticut', 'delaware', 'georgia', 'hawaii', 'idaho', 'illinois',
    'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine', 'maryland',
    'massachusetts', 'michigan', 'minnesota', 'mississippi', 'missouri',
    'montana', 'nebraska', 'nevada', 'new hampshire', 'new jersey',
    'new mexico', 'new york', 'north carolina', 'north dakota', 'ohio',
    'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina',
    'south dakota', 'tennessee', 'texas', 'utah', 'vermont', 'virginia',
    'washington', 'west virginia', 'wisconsin', 'wyoming'
}


def _is_out_of_territory(query: str) -> bool:
    """
    Check if a GSC query is from outside OLS service area.

    Filters out keywords containing state names outside Florida unless they
    also contain Florida service area terms. This prevents generating tasks
    for out-of-territory search volume that OLS cannot serve.

    Args:
        query: Search query string from Google Search Console

    Returns:
        True if query is clearly out-of-territory, False otherwise
    """
    if not query:
        return False

    query_lower = query.lower()

    # Check if any out-of-territory state name is in the query
    contains_out_of_territory_state = any(
        state in query_lower for state in OUT_OF_TERRITORY_STATES
    )

    # Check if any service area term is in the query
    contains_service_area = any(
        term in query_lower for term in FLORIDA_SERVICE_AREA_TERMS
    )

    # Mark as out-of-territory only if it has an out-of-state reference
    # AND does NOT have any service area reference
    return contains_out_of_territory_state and not contains_service_area


def generate_tasks(db: Session, days_back: int = 7) -> dict:
    """
    Scan all data sources and generate actionable dashboard tasks.

    Returns a dict with:
    - status: 'success' or 'error'
    - tasks_created: count of new tasks added
    - tasks_by_type: breakdown by task_type
    """
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    new_tasks = []

    # --- 1. GSC Tasks ---
    gsc_tasks = _generate_gsc_tasks(db, cutoff)
    new_tasks.extend(gsc_tasks)

    # --- 2. Google Ads Tasks ---
    ads_tasks = _generate_ads_tasks(db, cutoff)
    new_tasks.extend(ads_tasks)

    # --- 3. SEO Audit Tasks (from SEOReport) ---
    audit_tasks = _generate_audit_tasks(db)
    new_tasks.extend(audit_tasks)

    # --- 4. Cross-channel Tasks ---
    cross_tasks = _generate_cross_channel_tasks(db, cutoff)
    new_tasks.extend(cross_tasks)

    # Deduplicate and save
    saved_count = 0
    for task_data in new_tasks:
        # Check if similar task already exists in any active state
        # (prevents re-creating dismissed, approved, or completed tasks)
        existing = (
            db.query(DashboardTask)
            .filter(
                and_(
                    DashboardTask.category == task_data["category"],
                    DashboardTask.title == task_data["title"],
                    DashboardTask.status.in_(["pending", "delayed", "dismissed", "approved", "completed"]),
                )
            )
            .first()
        )

        if not existing:
            task = DashboardTask(**task_data)
            db.add(task)
            saved_count += 1

    db.commit()

    # Count by type
    tasks_by_type = {}
    for task in new_tasks:
        task_type = task["task_type"]
        tasks_by_type[task_type] = tasks_by_type.get(task_type, 0) + 1

    return {
        "status": "success",
        "tasks_created": saved_count,
        "tasks_by_type": tasks_by_type,
    }


def _generate_gsc_tasks(db: Session, cutoff: datetime) -> list[dict]:
    """Generate SEO tasks from Google Search Console data."""
    tasks = []

    # Fetch GSC data for the period
    records = (
        db.query(GSCData)
        .filter(GSCData.date >= cutoff)
        .all()
    )

    if not records:
        return tasks

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
                "pages": [],
            }
        query_stats[q]["clicks"] += r.clicks or 0
        query_stats[q]["impressions"] += r.impressions or 0
        query_stats[q]["ctr_sum"] += r.ctr or 0
        query_stats[q]["position_sum"] += r.position or 0
        query_stats[q]["count"] += 1
        if r.page and r.page not in query_stats[q]["pages"]:
            query_stats[q]["pages"].append(r.page)

    # Rule 1: High-impression, low-CTR queries (impressions >= 50, CTR < 3%)
    for q, stats in query_stats.items():
        if stats["count"] == 0:
            continue
        # Skip out-of-territory queries
        if _is_out_of_territory(q):
            continue
        avg_ctr = (stats["ctr_sum"] / stats["count"]) if stats["count"] else 0
        if stats["impressions"] >= 50 and avg_ctr < 0.03:
            tasks.append({
                "task_type": "seo",
                "category": "keyword_optimization",
                "priority": "HIGH",
                "title": f"Optimize meta title/description for '{q}'",
                "description": (
                    f"Query '{q}' has {stats['impressions']} impressions "
                    f"but only {stats['clicks']} clicks (CTR: {round(avg_ctr * 100, 2)}%). "
                    f"Improve title tag and meta description to increase CTR."
                ),
                "finding": (
                    f"High impressions ({stats['impressions']}), low CTR "
                    f"({round(avg_ctr * 100, 2)}%) for query: {q}"
                ),
                "action_endpoint": None,
                "action_payload": None,
                "status": "pending",
            })

    # Rule 2: Queries ranking position 8-20 with decent impressions (>= 20)
    for q, stats in query_stats.items():
        if stats["count"] == 0:
            continue
        # Skip out-of-territory queries
        if _is_out_of_territory(q):
            continue
        avg_pos = (stats["position_sum"] / stats["count"]) if stats["count"] else 0
        if 8 <= avg_pos <= 20 and stats["impressions"] >= 20:
            tasks.append({
                "task_type": "seo",
                "category": "content_ranking",
                "priority": "MEDIUM",
                "title": f"Create targeted content for '{q}' (position {round(avg_pos, 1)})",
                "description": (
                    f"Query '{q}' is ranking at position {round(avg_pos, 1)} "
                    f"with {stats['impressions']} impressions. "
                    f"Create or optimize content to push to page 1."
                ),
                "finding": (
                    f"Query near page 2: {q} at position {round(avg_pos, 1)} "
                    f"with {stats['impressions']} impressions"
                ),
                "action_endpoint": None,
                "action_payload": None,
                "status": "pending",
            })

    # Rule 3: Pages with high impressions but zero clicks
    page_stats = {}
    page_queries = {}  # Track queries per page to check geography
    for r in records:
        p = r.page or "(unknown)"
        q = r.query or "(unknown)"
        if p not in page_stats:
            page_stats[p] = {"clicks": 0, "impressions": 0}
            page_queries[p] = []
        page_stats[p]["clicks"] += r.clicks or 0
        page_stats[p]["impressions"] += r.impressions or 0
        if q not in page_queries[p]:
            page_queries[p].append(q)

    for page, stats in page_stats.items():
        if stats["impressions"] >= 50 and stats["clicks"] == 0:
            # Skip if all queries for this page are out-of-territory
            page_queries_all_out_of_territory = all(
                _is_out_of_territory(q) for q in page_queries[page]
            )
            if page_queries_all_out_of_territory:
                continue

            tasks.append({
                "task_type": "seo",
                "category": "zero_click_investigation",
                "priority": "HIGH",
                "title": f"Investigate zero-click page: {page}",
                "description": (
                    f"Page {page} has {stats['impressions']} impressions "
                    f"but zero clicks. Investigate content relevance and meta tags."
                ),
                "finding": (
                    f"Zero-click page detected: {page} with "
                    f"{stats['impressions']} impressions"
                ),
                "action_endpoint": None,
                "action_payload": None,
                "status": "pending",
            })

    return tasks


def _generate_ads_tasks(db: Session, cutoff: datetime) -> list[dict]:
    """Generate Google Ads tasks."""
    tasks = []

    records = (
        db.query(GoogleAdsData)
        .filter(GoogleAdsData.date >= cutoff)
        .all()
    )

    if not records:
        return tasks

    # Aggregate by campaign
    campaign_stats = {}
    for r in records:
        name = r.campaign_name or "(unknown)"
        if name not in campaign_stats:
            campaign_stats[name] = {
                "clicks": 0,
                "impressions": 0,
                "cost": 0.0,
                "conversions": 0.0,
                "count": 0,
            }
        campaign_stats[name]["clicks"] += r.clicks or 0
        campaign_stats[name]["impressions"] += r.impressions or 0
        campaign_stats[name]["cost"] += r.cost or 0
        campaign_stats[name]["conversions"] += r.conversions or 0
        campaign_stats[name]["count"] += 1

    # Aggregate by ad group
    adgroup_stats = {}
    for r in records:
        ag = r.ad_group or "(unknown)"
        if ag not in adgroup_stats:
            adgroup_stats[ag] = {
                "clicks": 0,
                "cost": 0.0,
                "conversions": 0.0,
                "count": 0,
            }
        adgroup_stats[ag]["clicks"] += r.clicks or 0
        adgroup_stats[ag]["cost"] += r.cost or 0
        adgroup_stats[ag]["conversions"] += r.conversions or 0
        adgroup_stats[ag]["count"] += 1

    # Rule 1: Campaigns with spend > $10 and zero conversions
    for name, stats in campaign_stats.items():
        if stats["cost"] > 10 and stats["conversions"] == 0:
            tasks.append({
                "task_type": "ads",
                "category": "ad_spend",
                "priority": "HIGH",
                "title": f"Review campaign '{name}' — ${stats['cost']:.2f} spent, 0 conversions",
                "description": (
                    f"Campaign '{name}' has spent ${stats['cost']:.2f} "
                    f"with {stats['clicks']} clicks but zero conversions. "
                    f"Review targeting, keywords, and landing page."
                ),
                "finding": (
                    f"Campaign: {name} | Spend: ${stats['cost']:.2f} | "
                    f"Clicks: {stats['clicks']} | Conversions: {stats['conversions']}"
                ),
                "action_endpoint": None,
                "action_payload": None,
                "status": "pending",
            })

    # Rule 2: Campaigns with CTR < 1% and impressions > 100
    for name, stats in campaign_stats.items():
        if stats["impressions"] > 100 and stats["count"] > 0:
            ctr = stats["clicks"] / stats["impressions"] if stats["impressions"] > 0 else 0
            if ctr < 0.01:
                tasks.append({
                    "task_type": "ads",
                    "category": "ad_copy",
                    "priority": "MEDIUM",
                    "title": f"Improve ad copy for '{name}' — CTR only {round(ctr * 100, 2)}%",
                    "description": (
                        f"Campaign '{name}' has a CTR of {round(ctr * 100, 2)}% "
                        f"({stats['clicks']} clicks / {stats['impressions']} impressions). "
                        f"Review and improve ad copy and targeting."
                    ),
                    "finding": (
                        f"Campaign: {name} | CTR: {round(ctr * 100, 2)}% | "
                        f"Impressions: {stats['impressions']}"
                    ),
                    "action_endpoint": None,
                    "action_payload": None,
                    "status": "pending",
                })

    # Rule 3: Ad groups with cost_per_conversion > $50
    for ag, stats in adgroup_stats.items():
        if stats["conversions"] > 0 and stats["count"] > 0:
            cpc = stats["cost"] / stats["clicks"] if stats["clicks"] > 0 else 0
            cost_per_conv = stats["cost"] / stats["conversions"]
            if cost_per_conv > 50:
                tasks.append({
                    "task_type": "ads",
                    "category": "ad_targeting",
                    "priority": "MEDIUM",
                    "title": f"Optimize targeting for '{ag}' — CPC ${cpc:.2f}",
                    "description": (
                        f"Ad group '{ag}' has a cost per conversion of ${cost_per_conv:.2f} "
                        f"(${stats['cost']:.2f} spend / {stats['conversions']:.1f} conversions). "
                        f"Review targeting and keywords to reduce acquisition cost."
                    ),
                    "finding": (
                        f"Ad group: {ag} | Cost/Conv: ${cost_per_conv:.2f} | "
                        f"CPC: ${cpc:.2f}"
                    ),
                    "action_endpoint": None,
                    "action_payload": None,
                    "status": "pending",
                })

    return tasks


def _generate_audit_tasks(db: Session) -> list[dict]:
    """Generate tasks from latest SEO audit recommendations."""
    tasks = []

    # Get the most recent SEO recommendations report
    latest_audit = (
        db.query(SEOReport)
        .filter(SEOReport.report_type == "seo_recommendations")
        .order_by(SEOReport.report_date.desc())
        .first()
    )

    if not latest_audit or not latest_audit.data:
        return tasks

    recommendations = latest_audit.data.get("recommendations", [])
    for rec in recommendations:
        priority = rec.get("priority", "MEDIUM")
        category = rec.get("category", "seo_audit")

        tasks.append({
            "task_type": "seo",
            "category": category.lower().replace(" — ", "_").replace(" ", "_"),
            "priority": priority,
            "title": rec.get("finding", "SEO Recommendation")[:500],
            "description": rec.get("action", ""),
            "finding": rec.get("finding", ""),
            "action_endpoint": None,
            "action_payload": None,
            "status": "pending",
        })

    return tasks


def _generate_cross_channel_tasks(db: Session, cutoff: datetime) -> list[dict]:
    """Generate cross-channel tasks based on data correlation."""
    tasks = []

    # Detect GA4 traffic drops on pages that appear in GSC
    ga4_pages = (
        db.query(GA4Data.dimension_value)
        .filter(
            GA4Data.date >= cutoff,
            GA4Data.data["report"].as_string() == "top_pages",
        )
        .distinct()
        .all()
    )

    gsc_pages = (
        db.query(GSCData.page)
        .filter(GSCData.date >= cutoff)
        .distinct()
        .all()
    )

    ga4_page_set = {p[0] for p in ga4_pages if p[0]}
    gsc_page_set = {p[0] for p in gsc_pages if p[0]}
    shared_pages = ga4_page_set & gsc_page_set

    # Simple heuristic: if traffic is low on a page that has GSC data, flag it
    if shared_pages:
        for page in list(shared_pages)[:5]:  # Limit to 5 tasks
            # Check if page has low views in GA4
            page_views = (
                db.query(func.sum(GA4Data.metric_value))
                .filter(
                    GA4Data.dimension_value == page,
                    GA4Data.date >= cutoff,
                    GA4Data.data["report"].as_string() == "top_pages",
                )
                .scalar()
            )

            if page_views and page_views < 10:
                tasks.append({
                    "task_type": "seo",
                    "category": "traffic_investigation",
                    "priority": "MEDIUM",
                    "title": f"Investigate low traffic on GSC page: {page}",
                    "description": (
                        f"Page {page} appears in Search Console data "
                        f"but has only {int(page_views) if page_views else 0} views in GA4. "
                        f"Check content quality, indexing, and mobile usability."
                    ),
                    "finding": (
                        f"Cross-channel anomaly: {page} has GSC impressions "
                        f"but low GA4 traffic ({int(page_views) if page_views else 0} views)"
                    ),
                    "action_endpoint": None,
                    "action_payload": None,
                    "status": "pending",
                })

    return tasks


def get_tasks(
    db: Session,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
) -> list[DashboardTask]:
    """
    Query dashboard tasks with optional filters.

    Handles delayed tasks:
    - Excludes tasks with status "delayed" where delayed_until is in the future
    - Auto-resets tasks with status "delayed" where delayed_until is in the past back to "pending"

    Sorted by priority (HIGH first) then by created_at (newest first).
    """
    now = datetime.utcnow()

    # First, auto-reset expired delayed tasks back to pending
    expired_delayed = (
        db.query(DashboardTask)
        .filter(
            DashboardTask.status == "delayed",
            DashboardTask.delayed_until <= now,
        )
        .all()
    )
    for task in expired_delayed:
        task.status = "pending"
    if expired_delayed:
        db.commit()

    # Build the query
    query = db.query(DashboardTask)

    # If not explicitly filtering for delayed status, exclude future-delayed tasks
    if status != "delayed":
        query = query.filter(
            ~(
                (DashboardTask.status == "delayed") &
                (DashboardTask.delayed_until > now)
            )
        )

    if status:
        query = query.filter(DashboardTask.status == status)
    if task_type:
        query = query.filter(DashboardTask.task_type == task_type)
    if priority:
        query = query.filter(DashboardTask.priority == priority)

    # Sort: priority (HIGH first), then created_at (newest first)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    tasks = query.limit(limit).all()

    tasks.sort(
        key=lambda t: (
            priority_order.get(t.priority, 3),
            -t.created_at.timestamp(),
        )
    )

    return tasks


def get_task_by_id(db: Session, task_id: int) -> Optional[DashboardTask]:
    """Retrieve a single task by ID."""
    return db.query(DashboardTask).filter(DashboardTask.id == task_id).first()


def approve_task(db: Session, task_id: int) -> dict:
    """
    Approve a task and optionally execute it.

    Sets status to 'approved' and approved_at timestamp.
    If action_endpoint is set, calls the endpoint (for future implementation).
    """
    task = get_task_by_id(db, task_id)
    if not task:
        return {"status": "error", "detail": "Task not found"}

    if task.status != "pending":
        return {"status": "error", "detail": f"Task is {task.status}, not pending"}

    task.status = "approved"
    task.approved_at = datetime.utcnow()

    db.commit()

    return {
        "status": "success",
        "task_id": task.id,
        "message": f"Task approved: {task.title}",
    }


def dismiss_task(db: Session, task_id: int) -> dict:
    """Dismiss a pending task."""
    task = get_task_by_id(db, task_id)
    if not task:
        return {"status": "error", "detail": "Task not found"}

    if task.status != "pending":
        return {"status": "error", "detail": f"Task is {task.status}, not pending"}

    task.status = "dismissed"
    db.commit()

    return {
        "status": "success",
        "task_id": task.id,
        "message": f"Task dismissed: {task.title}",
    }


def delay_task(db: Session, task_id: int, hours: int = 24) -> dict:
    """
    Delay (snooze) a pending task.

    Sets status to "delayed" and delayed_until to now + hours.
    The task will automatically return to "pending" when the delay expires.
    """
    task = get_task_by_id(db, task_id)
    if not task:
        return {"status": "error", "detail": "Task not found"}

    if task.status != "pending":
        return {"status": "error", "detail": f"Task is {task.status}, not pending"}

    task.status = "delayed"
    task.delayed_until = datetime.utcnow() + timedelta(hours=hours)
    db.commit()

    return {
        "status": "success",
        "task_id": task.id,
        "delayed_until": task.delayed_until.isoformat(),
        "message": f"Task delayed for {hours} hours: {task.title}",
    }


def get_dashboard_metrics(db: Session) -> dict:
    """
    Return summary metrics for the dashboard.

    Includes:
    - Total tasks by status (including delayed)
    - Tasks by type
    - Tasks by priority
    - Recent completions
    """
    now = datetime.utcnow()

    # Auto-reset expired delayed tasks first
    expired_delayed = (
        db.query(DashboardTask)
        .filter(
            DashboardTask.status == "delayed",
            DashboardTask.delayed_until <= now,
        )
        .all()
    )
    for task in expired_delayed:
        task.status = "pending"
    if expired_delayed:
        db.commit()

    all_tasks = db.query(DashboardTask).all()

    # Count by status
    status_counts = {}
    for task in all_tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1

    # Count by type
    type_counts = {}
    for task in all_tasks:
        type_counts[task.task_type] = type_counts.get(task.task_type, 0) + 1

    # Count by priority
    priority_counts = {}
    for task in all_tasks:
        priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1

    # Recent completions (last 7 days)
    cutoff = datetime.utcnow() - timedelta(days=7)
    recent_completions = (
        db.query(DashboardTask)
        .filter(
            DashboardTask.status == "completed",
            DashboardTask.completed_at >= cutoff,
        )
        .count()
    )

    return {
        "total_tasks": len(all_tasks),
        "status_breakdown": status_counts,
        "type_breakdown": type_counts,
        "priority_breakdown": priority_counts,
        "recent_completions_7d": recent_completions,
    }


def get_channel_metrics(db: Session) -> dict:
    """
    Return per-channel metrics:
    - GSC: total records, avg metrics
    - GA4: total sessions, pageviews
    - Google Ads: total spend, conversions
    """
    cutoff = datetime.utcnow() - timedelta(days=7)

    # GSC metrics
    gsc_records = db.query(GSCData).filter(GSCData.date >= cutoff).all()
    gsc_metrics = {
        "record_count": len(gsc_records),
        "total_clicks": sum(r.clicks or 0 for r in gsc_records),
        "total_impressions": sum(r.impressions or 0 for r in gsc_records),
        "avg_position": (
            sum(r.position or 0 for r in gsc_records) / len(gsc_records)
            if gsc_records
            else 0
        ),
    }

    # GA4 metrics (from daily_overview)
    ga4_records = (
        db.query(GA4Data)
        .filter(
            GA4Data.date >= cutoff,
            GA4Data.data["report"].as_string() == "daily_overview",
        )
        .all()
    )
    ga4_metrics = {
        "record_count": len(ga4_records),
        "total_sessions": sum(
            r.metric_value or 0 for r in ga4_records
            if r.metric_name == "sessions"
        ),
        "total_pageviews": sum(
            r.metric_value or 0 for r in ga4_records
            if r.metric_name == "screenPageViews"
        ),
    }

    # Google Ads metrics
    ads_records = db.query(GoogleAdsData).filter(GoogleAdsData.date >= cutoff).all()
    ads_metrics = {
        "record_count": len(ads_records),
        "total_spend": sum(r.cost or 0.0 for r in ads_records),
        "total_conversions": sum(r.conversions or 0.0 for r in ads_records),
        "total_clicks": sum(r.clicks or 0 for r in ads_records),
    }

    return {
        "period_days": 7,
        "gsc": gsc_metrics,
        "ga4": ga4_metrics,
        "google_ads": ads_metrics,
    }
