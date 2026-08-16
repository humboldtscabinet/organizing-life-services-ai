"""
Phase 1 automation — gated weekly cycle for SEO operations.

Pulls platform data, generates dashboard tasks, schedules content opportunities,
and raises operator alerts. Does not auto-publish or mutate customer-facing state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.services.content_scheduler import schedule_weekly_content
from app.services.dashboard_service import generate_tasks
from app.services.ga4_service import pull_ga4_data
from app.services.gbp_service import pull_gbp_data
from app.services.google_ads_service import pull_google_ads_data
from app.services.gsc_service import pull_gsc_data
from app.services.ops_alert_service import check_data_freshness, create_alert
from app.services.sheets_service import (
    push_ga4_to_sheets,
    push_google_ads_to_sheets,
    push_gsc_to_sheets,
)
from app.services.shopify_service import pull_shopify_orders


def _capture_step(action: Callable[..., dict[str, Any]], *args, **kwargs) -> dict[str, Any]:
    try:
        result = action(*args, **kwargs)
        if not isinstance(result, dict):
            return {"status": "error", "detail": "Unexpected result type"}
        return result
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _has_error(result: dict[str, Any]) -> bool:
    return result.get("status") in {"error", "unavailable"}


def run_phase1_cycle(
    db: Session,
    *,
    days_back: int = 7,
    schedule_content_count: int = 1,
    push_to_sheets: bool = True,
) -> dict[str, Any]:
    """
    Run the Phase 1 gated automation cycle.

    Steps:
      1. Pull GSC, GA4, Google Ads, GBP (if configured), and Shopify orders
      2. Optionally push channel data to Google Sheets
      3. Generate dashboard tasks from fresh data
      4. Schedule the next content opportunity(s)
      5. Create an operator alert summarizing the run

    No customer-facing writes occur in this cycle.
    """
    result: dict[str, Any] = {
        "status": "success",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "pulls": {},
        "pushes": {},
        "tasks_generated": {},
        "content_scheduled": {},
        "failed_steps": 0,
    }

    result["pulls"]["gsc"] = _capture_step(pull_gsc_data, db, days_back=days_back)
    result["pulls"]["ga4"] = _capture_step(pull_ga4_data, db, days_back=days_back)
    result["pulls"]["google_ads"] = _capture_step(pull_google_ads_data, db, days_back=days_back)
    result["pulls"]["gbp"] = _capture_step(pull_gbp_data, db, days_back=28)
    # Shopify order pull uses limit/status, not a date window.
    result["pulls"]["shopify_orders"] = _capture_step(pull_shopify_orders, db, limit=50)

    if push_to_sheets:
        result["pushes"]["gsc"] = _capture_step(push_gsc_to_sheets, db)
        result["pushes"]["ga4"] = _capture_step(push_ga4_to_sheets, db)
        result["pushes"]["google_ads"] = _capture_step(push_google_ads_to_sheets, db)

    result["tasks_generated"] = _capture_step(generate_tasks, db, days_back=days_back)
    result["content_scheduled"] = _capture_step(
        schedule_weekly_content,
        db,
        count=schedule_content_count,
    )

    nested_results = [
        *result["pulls"].values(),
        *result.get("pushes", {}).values(),
        result["tasks_generated"],
        result["content_scheduled"],
    ]
    failed_steps = sum(1 for item in nested_results if _has_error(item))
    result["failed_steps"] = failed_steps
    if failed_steps:
        result["status"] = "partial"

    tasks_created = int(result["tasks_generated"].get("tasks_created", 0) or 0)
    content_created = int(result["content_scheduled"].get("tasks_created", 0) or 0)
    severity = "WARNING" if failed_steps else "INFO"
    title = (
        "Phase 1 cycle completed with follow-up needed"
        if failed_steps
        else "Phase 1 cycle completed"
    )
    message = (
        f"Generated {tasks_created} dashboard task(s) and scheduled "
        f"{content_created} content task(s). Review pending tasks before publish."
    )

    alert = create_alert(
        db=db,
        source="phase1_automation",
        severity=severity,
        title=title,
        message=message,
        fingerprint="phase1-weekly-cycle",
        details={
            "failed_steps": failed_steps,
            "tasks_created": tasks_created,
            "content_tasks_created": content_created,
            "pull_statuses": {
                key: value.get("status")
                for key, value in result["pulls"].items()
            },
        },
    )
    result["alert_id"] = alert["id"] if isinstance(alert, dict) else alert.id
    result["freshness"] = _capture_step(check_data_freshness, db)
    if _has_error(result["freshness"]):
        result["failed_steps"] = int(result["failed_steps"]) + 1
        result["status"] = "partial"
    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    return result
