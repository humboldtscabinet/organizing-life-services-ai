"""
Content Scheduler — Content calendar generation and scheduling service for OLS.

Capabilities:
  - Generate a 12-week content calendar from GSC data
  - Pick the next high-value content opportunity weekly
  - Track publishing status and content gaps

This service drives the weekly n8n automation that schedules new blog content.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.db.models import GSCData, DashboardTask
from app.services.content_engine import (
    analyze_content_gaps,
    create_content_task,
)

logger = logging.getLogger(__name__)


def get_content_calendar(db: Session, weeks: int = 12) -> List[Dict]:
    """
    Generate a prioritized content calendar for the next N weeks.

    Uses GSC data to identify high-value topics, distributes them across
    the calendar, and checks which ones are already scheduled.

    Returns:
        [
            {
                "week": 1,
                "date": "2024-04-15",
                "topic": "Estate Sales in Clearwater",
                "target_keyword": "estate sale clearwater",
                "post_type": "seo_blog",
                "impressions": 150,
                "priority": "HIGH",
                "status": "pending" | "scheduled" | "published" | "gap"
            },
            ...
        ]
    """
    # Get content opportunities from GSC
    opportunities = analyze_content_gaps(db, days_back=90)

    calendar = []
    today = datetime.utcnow().date()

    for week_num in range(1, weeks + 1):
        # Calculate week start date
        week_date = today + timedelta(weeks=week_num)

        if week_num <= len(opportunities):
            opp = opportunities[week_num - 1]
            query = opp["query"]

            # Check if a task already exists for this query
            existing_task = (
                db.query(DashboardTask)
                .filter(
                    and_(
                        DashboardTask.task_type == "content",
                        DashboardTask.action_payload["target_keyword"].astext == query,
                    )
                )
                .first()
            )

            status = "gap"
            if existing_task:
                status = "scheduled" if existing_task.status == "pending" else existing_task.status

            calendar.append(
                {
                    "week": week_num,
                    "date": week_date.isoformat(),
                    "topic": query.title(),
                    "target_keyword": query,
                    "post_type": "seo_blog",
                    "impressions": opp["impressions"],
                    "estimated_value": opp["estimated_value"],
                    "priority": "HIGH" if opp["impressions"] >= 200 else "MEDIUM",
                    "status": status,
                }
            )
        else:
            # Fill remaining weeks with "gap"
            calendar.append(
                {
                    "week": week_num,
                    "date": week_date.isoformat(),
                    "topic": None,
                    "target_keyword": None,
                    "post_type": None,
                    "impressions": 0,
                    "estimated_value": 0,
                    "priority": None,
                    "status": "gap",
                }
            )

    return calendar


def schedule_weekly_content(db: Session, count: int = 1) -> Dict:
    """
    Pick the top N content opportunities and schedule them for this week.

    Called by n8n automation weekly. Finds the highest-value content gaps
    that haven't been scheduled yet, creates dashboard tasks, and returns
    the list of tasks created.

    Args:
        db: Database session
        count: Number of tasks to create this run (default 1; used for
               aggressive-but-controlled ramp — e.g., 3 tasks/week in
               ramp-up weeks, 1/week at steady state).

    Returns:
        {
            "status": "success" | "no_content" | "all_scheduled" | "partial" | "error",
            "tasks_created": int,
            "tasks_requested": int,
            "tasks": [
                {
                    "task_id": int,
                    "topic": "...",
                    "target_keyword": "...",
                    "impressions": int,
                    "priority": "HIGH" | "MEDIUM" | "LOW",
                    "post_type": "seo_blog" | "service_area",
                },
                ...
            ],
            "message": "..."
        }
    """
    try:
        # Clamp count to sane bounds (1-10) to prevent accidental bulk drops
        count = max(1, min(10, int(count)))

        # Get all content opportunities
        opportunities = analyze_content_gaps(db, days_back=90)

        if not opportunities:
            return {
                "status": "no_content",
                "tasks_created": 0,
                "tasks_requested": count,
                "tasks": [],
                "message": "No content gaps identified in GSC data",
            }

        created_tasks = []

        # Walk opportunities in priority order, creating tasks for ones that
        # don't already have a pending/approved/executing task.
        for opp in opportunities:
            if len(created_tasks) >= count:
                break

            target_keyword = opp["query"]

            # Check if a task already exists for this keyword
            existing = (
                db.query(DashboardTask)
                .filter(
                    and_(
                        DashboardTask.task_type == "content",
                        DashboardTask.action_payload["target_keyword"].astext == target_keyword,
                        DashboardTask.status.in_(["pending", "approved", "executing"]),
                    )
                )
                .first()
            )

            if existing:
                continue

            # Create a new task for this opportunity
            # Use the post type suggested by gap analysis (seo_blog or service_area)
            suggested_type = opp.get("suggested_post_type", "seo_blog")
            task = create_content_task(
                db=db,
                opportunity=opp,
                post_type=suggested_type,
            )

            created_tasks.append(
                {
                    "task_id": task.id,
                    "topic": opp["query"],
                    "target_keyword": target_keyword,
                    "impressions": opp["impressions"],
                    "priority": task.priority,
                    "post_type": suggested_type,
                }
            )

        if not created_tasks:
            return {
                "status": "all_scheduled",
                "tasks_created": 0,
                "tasks_requested": count,
                "tasks": [],
                "message": "All top opportunities are already scheduled as pending tasks",
            }

        status = "success" if len(created_tasks) == count else "partial"
        return {
            "status": status,
            "tasks_created": len(created_tasks),
            "tasks_requested": count,
            "tasks": created_tasks,
            "message": f"Scheduled {len(created_tasks)} of {count} requested content tasks",
        }

    except Exception as e:
        logger.error(f"Error in schedule_weekly_content: {e}")
        return {
            "status": "error",
            "tasks_created": 0,
            "tasks_requested": count,
            "tasks": [],
            "detail": str(e),
        }


def get_content_status(db: Session) -> Dict:
    """
    Get an overview of the content pipeline status.

    Returns:
        {
            "total_published": int,
            "pending_tasks": int,
            "approved_tasks": int,
            "content_gaps_remaining": int,
            "next_scheduled_topic": str or None,
            "last_published": {
                "title": "...",
                "date": "2024-04-09",
                "url": "..."
            }
        }
    """
    try:
        # Count published articles
        published_count = (
            db.query(DashboardTask)
            .filter(
                and_(
                    DashboardTask.task_type == "content",
                    DashboardTask.status == "completed",
                )
            )
            .count()
        )

        # Count pending tasks
        pending_count = (
            db.query(DashboardTask)
            .filter(
                and_(
                    DashboardTask.task_type == "content",
                    DashboardTask.status == "pending",
                )
            )
            .count()
        )

        # Count approved tasks
        approved_count = (
            db.query(DashboardTask)
            .filter(
                and_(
                    DashboardTask.task_type == "content",
                    DashboardTask.status == "approved",
                )
            )
            .count()
        )

        # Count remaining gaps
        gaps = analyze_content_gaps(db, days_back=90)
        remaining_gaps = len(gaps)

        # Get next scheduled topic
        next_task = (
            db.query(DashboardTask)
            .filter(
                and_(
                    DashboardTask.task_type == "content",
                    DashboardTask.status == "pending",
                )
            )
            .order_by(DashboardTask.created_at)
            .first()
        )

        next_topic = None
        if next_task and next_task.action_payload:
            next_topic = next_task.action_payload.get("target_keyword", "")

        # Get last published article
        last_published = (
            db.query(DashboardTask)
            .filter(
                and_(
                    DashboardTask.task_type == "content",
                    DashboardTask.status == "completed",
                )
            )
            .order_by(DashboardTask.completed_at.desc())
            .first()
        )

        last_pub_info = None
        if last_published and last_published.result:
            last_pub_info = {
                "title": last_published.result.get("title", "Unknown"),
                "date": last_published.completed_at.isoformat() if last_published.completed_at else None,
                "url": last_published.result.get("shopify_article_url", ""),
            }

        return {
            "status": "success",
            "total_published": published_count,
            "pending_tasks": pending_count,
            "approved_tasks": approved_count,
            "content_gaps_remaining": remaining_gaps,
            "next_scheduled_topic": next_topic,
            "last_published": last_pub_info,
        }

    except Exception as e:
        logger.error(f"Error in get_content_status: {e}")
        return {"status": "error", "detail": str(e)}
