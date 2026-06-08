"""
Dashboard Routes — Marketing Dashboard task generation and management endpoints.

All endpoints are in manual-approval mode:
- Generate tasks from threshold analysis of GSC, GA4, Google Ads data
- List and filter tasks
- Approve/dismiss tasks
- Get dashboard metrics and insights
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

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
from app.services.sheets_service import (
    push_ga4_to_sheets,
    push_google_ads_to_sheets,
    push_gsc_to_sheets,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


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
    try:
        result = generate_tasks(db=db, days_back=days_back)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


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
    try:
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
                    "status": t.status,
                    "created_at": t.created_at.isoformat(),
                    "approved_at": t.approved_at.isoformat() if t.approved_at else None,
                }
                for t in tasks
            ],
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/tasks/{task_id}")
def get_task_detail(task_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a single task.
    """
    try:
        task = get_task_by_id(db, task_id)
        if not task:
            return {"status": "error", "detail": "Task not found"}

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
    except Exception as e:
        return {"status": "error", "detail": str(e)}


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
    try:
        result = approve_task(db, task_id)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/tasks/{task_id}/dismiss")
def trigger_dismiss_task(task_id: int, db: Session = Depends(get_db)):
    """
    Dismiss a pending task (mark as dismissed).

    Returns:
    - status: 'success' or 'error'
    - task_id: the dismissed task's ID
    - message: confirmation message
    """
    try:
        result = dismiss_task(db, task_id)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


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
    try:
        result = delay_task(db, task_id, hours=hours)
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


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
    try:
        metrics = get_dashboard_metrics(db)
        return {
            "status": "success",
            "metrics": metrics,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/metrics/channels")
def get_channel_metrics_endpoint(db: Session = Depends(get_db)):
    """
    Get per-channel metrics for the last 7 days.

    Returns aggregated data from:
    - GSC: record count, clicks, impressions, avg position
    - GA4: record count, sessions, pageviews
    - Google Ads: record count, spend, conversions, clicks
    """
    try:
        metrics = get_channel_metrics(db)
        return {
            "status": "success",
            "metrics": metrics,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


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

    # Step 1: Pull data from all channels
    try:
        gsc_result = pull_gsc_data(db)
        result["pulls"]["gsc"] = gsc_result
    except Exception as e:
        result["pulls"]["gsc"] = {"status": "error", "detail": str(e)}

    try:
        ga4_result = pull_ga4_data(db)
        result["pulls"]["ga4"] = ga4_result
    except Exception as e:
        result["pulls"]["ga4"] = {"status": "error", "detail": str(e)}

    try:
        ads_result = pull_google_ads_data(db)
        result["pulls"]["google_ads"] = ads_result
    except Exception as e:
        result["pulls"]["google_ads"] = {"status": "error", "detail": str(e)}

    # Step 2: Push data to sheets
    try:
        push_gsc = push_gsc_to_sheets(db)
        result["pushes"]["gsc"] = push_gsc
    except Exception as e:
        result["pushes"]["gsc"] = {"status": "error", "detail": str(e)}

    try:
        push_ga4 = push_ga4_to_sheets(db)
        result["pushes"]["ga4"] = push_ga4
    except Exception as e:
        result["pushes"]["ga4"] = {"status": "error", "detail": str(e)}

    try:
        push_ads = push_google_ads_to_sheets(db)
        result["pushes"]["google_ads"] = push_ads
    except Exception as e:
        result["pushes"]["google_ads"] = {"status": "error", "detail": str(e)}

    # Step 3: Generate tasks
    try:
        tasks_result = generate_tasks(db)
        result["tasks_generated"] = tasks_result
    except Exception as e:
        result["tasks_generated"] = {"status": "error", "detail": str(e)}

    return result
