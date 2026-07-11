#!/usr/bin/env python3
"""
Scheduled platform sync for the Mac mini / server runtime.

Pulls GSC, GA4, Google Ads, GBP, and Shopify orders into Postgres, then
optionally generates dashboard tasks and schedules content opportunities.

Usage:
  python scripts/scheduled_platform_sync.py
  python scripts/scheduled_platform_sync.py --full-cycle
  python scripts/scheduled_platform_sync.py --days-back 14 --no-sheets

Designed for launchd/cron on the always-on server. Requires DATABASE_URL and
Google/Shopify credentials in the environment or .env file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.database import SessionLocal  # noqa: E402
from app.services.dashboard_service import generate_tasks  # noqa: E402
from app.services.ga4_service import pull_ga4_data  # noqa: E402
from app.services.gbp_service import pull_gbp_data  # noqa: E402
from app.services.google_ads_service import pull_google_ads_data  # noqa: E402
from app.services.gsc_service import pull_gsc_data  # noqa: E402
from app.services.phase1_automation_service import run_phase1_cycle  # noqa: E402
from app.services.sheets_service import (  # noqa: E402
    push_ga4_to_sheets,
    push_google_ads_to_sheets,
    push_gsc_to_sheets,
)
from app.services.shopify_service import pull_shopify_orders  # noqa: E402


def _capture(action, *args, **kwargs):
    try:
        return action(*args, **kwargs)
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def run_sync(
    *,
    days_back: int,
    push_to_sheets: bool,
    generate_task_recommendations: bool,
    full_cycle: bool,
    schedule_content_count: int,
) -> dict:
    db = SessionLocal()
    try:
        if full_cycle:
            return run_phase1_cycle(
                db,
                days_back=days_back,
                schedule_content_count=schedule_content_count,
                push_to_sheets=push_to_sheets,
            )

        result = {
            "status": "success",
            "mode": "pull_only",
            "pulls": {},
            "pushes": {},
            "tasks_generated": {},
            "failed_steps": 0,
        }

        result["pulls"]["gsc"] = _capture(pull_gsc_data, db, days_back=days_back)
        result["pulls"]["ga4"] = _capture(pull_ga4_data, db, days_back=days_back)
        result["pulls"]["google_ads"] = _capture(pull_google_ads_data, db, days_back=days_back)
        result["pulls"]["gbp"] = _capture(pull_gbp_data, db, days_back=28)
        result["pulls"]["shopify_orders"] = _capture(pull_shopify_orders, db, days_back=days_back)

        if push_to_sheets:
            result["pushes"]["gsc"] = _capture(push_gsc_to_sheets, db)
            result["pushes"]["ga4"] = _capture(push_ga4_to_sheets, db)
            result["pushes"]["google_ads"] = _capture(push_google_ads_to_sheets, db)

        if generate_task_recommendations:
            result["tasks_generated"] = _capture(generate_tasks, db, days_back=days_back)

        nested = [
            *result["pulls"].values(),
            *result.get("pushes", {}).values(),
            result.get("tasks_generated", {}),
        ]
        failed_steps = sum(
            1 for item in nested if item.get("status") in {"error", "unavailable"}
        )
        result["failed_steps"] = failed_steps
        if failed_steps:
            result["status"] = "partial"
        return result
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheduled OLS platform data sync")
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--no-sheets", action="store_true")
    parser.add_argument("--generate-tasks", action="store_true")
    parser.add_argument(
        "--full-cycle",
        action="store_true",
        help="Run the full Phase 1 gated cycle (pulls, tasks, content scheduling, alert)",
    )
    parser.add_argument(
        "--schedule-content-count",
        type=int,
        default=1,
        help="Content tasks to schedule when --full-cycle is set",
    )
    args = parser.parse_args()

    result = run_sync(
        days_back=args.days_back,
        push_to_sheets=not args.no_sheets,
        generate_task_recommendations=args.generate_tasks,
        full_cycle=args.full_cycle,
        schedule_content_count=args.schedule_content_count,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in {"success", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
