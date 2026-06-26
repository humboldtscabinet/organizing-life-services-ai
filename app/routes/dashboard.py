"""
Dashboard Routes — Marketing Dashboard task generation and management endpoints.

All endpoints are in manual-approval mode:
- Generate tasks from threshold analysis of GSC, GA4, Google Ads data
- List and filter tasks
- Approve/dismiss tasks
- Get dashboard metrics and insights
"""

from typing import Any, Callable

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api_errors import APIError, build_error_payload, service_result_or_raise
from app.db.database import get_db
from app.services.dashboard_service import (
    approve_task,
    delay_task,
    dismiss_task,
    generate_tasks,
    get_channel_metrics,
    get_dashboard_metrics,
    get_task_by_id,
    get_tasks,
)
from app.services.ga4_service import pull_ga4_data
from app.services.google_ads_service import pull_google_ads_data
from app.services.gsc_service import pull_gsc_data
from app.services.ops_alert_service import (
    acknowledge_alert,
    alert_to_dict,
    create_alert,
    get_alert_metrics,
    list_alerts,
    resolve_alert,
)
from app.services.ops_alert_service import (
    dismiss_alert as dismiss_ops_alert_service,
)
from app.services.sheets_service import (
    push_ga4_to_sheets,
    push_google_ads_to_sheets,
    push_gsc_to_sheets,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


class AlertCreateRequest(BaseModel):
    source: str = Field(..., min_length=1, max_length=100)
    severity: str = Field(..., description="INFO, WARNING, or CRITICAL")
    title: str = Field(..., min_length=1, max_length=300)
    message: str | None = None
    fingerprint: str | None = Field(
        None,
        max_length=300,
        description="Stable key for deduplicating repeated health checks",
    )
    details: dict[str, Any] | None = None


def _has_error(result: dict) -> bool:
    return result.get("status") in {"error", "unavailable"}


def _capture_step(action: Callable[..., dict[str, Any]], *args, **kwargs) -> dict[str, Any]:
    try:
        return service_result_or_raise(action(*args, **kwargs))
    except APIError as exc:
        return build_error_payload(
            status_code=exc.status_code,
            detail=exc.detail,
            code=exc.code,
            extra=exc.extra,
        )
    except Exception as exc:
        return build_error_payload(
            status_code=500,
            detail=str(exc),
            code="internal_server_error",
        )


@router.post("/generate-tasks")
def trigger_generate_tasks(
    days_back: int = 7,
    db: Session = Depends(get_db),
):
    """
    Manually trigger task generation from all data sources.

    Analyzes GSCData, GA4Data, GoogleAdsData from the last N days
    and generates actionable DashboardTask records.

    Returns:
    - status: 'success' or 'error'
    - tasks_created: count of new tasks added
    - tasks_by_type: breakdown by task_type (seo, ads, shopify)
    """
    return service_result_or_raise(generate_tasks(db=db, days_back=days_back))


@router.get("/tasks")
def list_tasks(
    status: str = Query(None, description="Filter by status: pending, approved, completed, dismissed"),
    task_type: str = Query(None, description="Filter by task_type: seo, ads, shopify"),
    priority: str = Query(None, description="Filter by priority: HIGH, MEDIUM, LOW"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    List dashboard tasks with optional filters.

    Returns tasks sorted by priority (HIGH first) then by created_at (newest first).
    """
    tasks = get_tasks(
        db=db,
        status=status,
        task_type=task_type,
        priority=priority,
        limit=limit,
    )

    return {
        "status": "success",
        "count": len(tasks),
        "tasks": [
            {
                "id": t.id,
                "task_type": t.task_type,
                "category": t.category,
                "priority": t.priority,
                "title": t.title,
                "description": t.description,
                "finding": t.finding,
                "action_payload": t.action_payload,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "approved_at": t.approved_at.isoformat() if t.approved_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ],
    }


@router.get("/tasks/{task_id}")
def get_task_detail(task_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a single task.
    """
    task = get_task_by_id(db, task_id)
    if not task:
        raise APIError(status_code=404, detail="Task not found")

    return {
        "status": "success",
        "task": {
            "id": task.id,
            "task_type": task.task_type,
            "category": task.category,
            "priority": task.priority,
            "title": task.title,
            "description": task.description,
            "finding": task.finding,
            "action_endpoint": task.action_endpoint,
            "action_payload": task.action_payload,
            "status": task.status,
            "result": task.result,
            "created_at": task.created_at.isoformat(),
            "approved_at": task.approved_at.isoformat() if task.approved_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
    }


@router.post("/tasks/{task_id}/approve")
def trigger_approve_task(task_id: int, db: Session = Depends(get_db)):
    """
    Approve a pending task.

    Sets status to 'approved' and approved_at timestamp.
    If action_endpoint is configured, the endpoint will be called
    in a future implementation for automated task execution.

    Returns:
    - status: 'success' or 'error'
    - task_id: the approved task's ID
    - message: confirmation message
    """
    return service_result_or_raise(approve_task(db, task_id))


@router.post("/tasks/{task_id}/dismiss")
def trigger_dismiss_task(task_id: int, db: Session = Depends(get_db)):
    """
    Dismiss a pending task (mark as dismissed).

    Returns:
    - status: 'success' or 'error'
    - task_id: the dismissed task's ID
    - message: confirmation message
    """
    return service_result_or_raise(dismiss_task(db, task_id))


@router.post("/tasks/{task_id}/delay")
def trigger_delay_task(
    task_id: int,
    hours: int = Query(24, description="Hours to delay the task (default 24)"),
    db: Session = Depends(get_db),
):
    """
    Delay (snooze) a pending task.

    Sets status to "delayed" and hides from pending tasks until the delay expires.
    After the delay, the task automatically returns to "pending" status.

    Query Parameters:
    - hours: Number of hours to delay (default 24)

    Returns:
    - status: 'success' or 'error'
    - task_id: the delayed task's ID
    - delayed_until: ISO timestamp when task will reappear
    - message: confirmation message
    """
    return service_result_or_raise(delay_task(db, task_id, hours=hours))


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """
    Get dashboard summary metrics.

    Returns:
    - total_tasks: count of all tasks
    - status_breakdown: {pending, approved, completed, dismissed, failed}
    - type_breakdown: {seo, ads, shopify}
    - priority_breakdown: {HIGH, MEDIUM, LOW}
    - recent_completions_7d: tasks completed in last 7 days
    """
    metrics = get_dashboard_metrics(db)
    return {
        "status": "success",
        "metrics": metrics,
    }


@router.get("/metrics/channels")
def get_channel_metrics_endpoint(db: Session = Depends(get_db)):
    """
    Get per-channel metrics for the last 7 days.

    Returns aggregated data from:
    - GSC: record count, clicks, impressions, avg position
    - GA4: record count, sessions, pageviews
    - Google Ads: record count, spend, conversions, clicks
    """
    metrics = get_channel_metrics(db)
    return {
        "status": "success",
        "metrics": metrics,
    }


@router.post("/refresh")
def trigger_full_refresh(db: Session = Depends(get_db)):
    """
    Full refresh: pull fresh data from all channels, push to sheets, and generate tasks.

    This endpoint:
    1. Pulls fresh data from GSC, GA4, and Google Ads
    2. Pushes data to Google Sheets
    3. Generates new tasks based on the data
    4. Returns combined results showing what was pulled and tasks created

    Each step is wrapped in try/except so one failure doesn't block the rest.

    Returns:
    - status: 'success' if all steps complete (even with some errors)
    - pulls: results from pulling data from each service
    - pushes: results from pushing data to sheets
    - tasks_generated: result from task generation
    """
    result = {
        "status": "success",
        "pulls": {},
        "pushes": {},
        "tasks_generated": {},
    }
    failed_steps = 0

    # Step 1: Pull data from all channels
    result["pulls"]["gsc"] = _capture_step(pull_gsc_data, db)
    result["pulls"]["ga4"] = _capture_step(pull_ga4_data, db)
    result["pulls"]["google_ads"] = _capture_step(pull_google_ads_data, db)

    # Step 2: Push data to sheets
    result["pushes"]["gsc"] = _capture_step(push_gsc_to_sheets, db)
    result["pushes"]["ga4"] = _capture_step(push_ga4_to_sheets, db)
    result["pushes"]["google_ads"] = _capture_step(push_google_ads_to_sheets, db)

    # Step 3: Generate tasks
    result["tasks_generated"] = _capture_step(generate_tasks, db)

    nested_results = [
        *result["pulls"].values(),
        *result["pushes"].values(),
        result["tasks_generated"],
    ]
    failed_steps = sum(1 for item in nested_results if _has_error(item))
    if failed_steps:
        result["status"] = "partial"
        result["failed_steps"] = failed_steps

    return result


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
def create_ops_alert(payload: AlertCreateRequest, db: Session = Depends(get_db)):
    """
    Create or update an operational alert.

    Intended first for n8n/private health checks. Use `fingerprint` to update
    the active alert for a recurring problem instead of creating duplicates.
    """
    try:
        alert = create_alert(db=db, **payload.model_dump())
    except ValueError as exc:
        raise APIError(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "alert": alert}


@router.get("/alerts")
def list_ops_alerts(
    status_filter: str | None = Query("open", alias="status"),
    severity: str | None = Query(None, description="INFO, WARNING, or CRITICAL"),
    source: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List operational alerts for the private dashboard."""
    try:
        alerts = list_alerts(
            db=db,
            status=status_filter,
            severity=severity,
            source=source,
            limit=limit,
        )
    except ValueError as exc:
        raise APIError(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "count": len(alerts),
        "alerts": [alert_to_dict(alert) for alert in alerts],
    }


@router.get("/alerts/metrics")
def get_ops_alert_metrics(db: Session = Depends(get_db)):
    """Return operational alert counts for dashboard KPI cards."""
    return {"status": "success", "metrics": get_alert_metrics(db)}


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_ops_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark an alert as acknowledged."""
    return service_result_or_raise(acknowledge_alert(db, alert_id))


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_ops_alert(alert_id: int, db: Session = Depends(get_db)):
    """Dismiss an alert."""
    return service_result_or_raise(dismiss_ops_alert_service(db, alert_id))


@router.post("/alerts/{alert_id}/resolve")
def resolve_ops_alert(alert_id: int, db: Session = Depends(get_db)):
    """Resolve an alert after the underlying condition is fixed."""
    return service_result_or_raise(resolve_alert(db, alert_id))
