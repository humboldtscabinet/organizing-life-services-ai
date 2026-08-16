"""Explicit GSC measurement watches as fingerprinted dashboard tasks.

Homepage watches stay advisory (frozen-meta v1 does not write theme SEO).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import GSCData
from app.services.frozen_meta_service import normalize_path


@dataclass(frozen=True)
class GscWatch:
    slug: str
    query: str
    page_path: str
    baseline_ctr: float
    baseline_position: float
    success_ctr: float
    due_on: date
    homepage: bool
    notes: str
    session_script: str | None = None


# Session 12 organizers CTR: 2026-07-25-homepage-organizers-ctr-watch.md
# Session 15 Tampa hub + appraisal: 2026-07-25-organic-growth-next-steps.md
WATCHES: tuple[GscWatch, ...] = (
    GscWatch(
        slug="organizers-plural-14d",
        query="estate sale organizers",
        page_path="/",
        baseline_ctr=0.0033,
        baseline_position=10.6,
        success_ctr=0.0033,
        due_on=date(2026, 8, 8),
        homepage=True,
        notes="CTR must be clearly above 0.33%. Homepage watch stays advisory.",
        session_script="data/session12_homepage_organizers_ctr.py",
    ),
    GscWatch(
        slug="organizers-plural-28d",
        query="estate sale organizers",
        page_path="/",
        baseline_ctr=0.0033,
        baseline_position=10.6,
        success_ctr=0.0033,
        due_on=date(2026, 8, 22),
        homepage=True,
        notes="28-day check. Iterate title/description only if still flat.",
        session_script="data/session12_homepage_organizers_ctr.py",
    ),
    GscWatch(
        slug="organizers-singular-14d",
        query="estate sale organizer",
        page_path="/",
        baseline_ctr=0.0,
        baseline_position=4.9,
        success_ctr=0.0,
        due_on=date(2026, 8, 8),
        homepage=True,
        notes="CTR must be clearly above 0%. Homepage watch stays advisory.",
        session_script="data/session12_homepage_organizers_ctr.py",
    ),
    GscWatch(
        slug="organizers-singular-28d",
        query="estate sale organizer",
        page_path="/",
        baseline_ctr=0.0,
        baseline_position=4.9,
        success_ctr=0.0,
        due_on=date(2026, 8, 22),
        homepage=True,
        notes="28-day check. Homepage watch stays advisory.",
        session_script="data/session12_homepage_organizers_ctr.py",
    ),
    GscWatch(
        slug="tampa-hub-14d",
        query="estate sale tampa",
        page_path="/pages/estate-sale-tampa-hillsborough-county",
        baseline_ctr=0.0,
        baseline_position=0.0,
        success_ctr=0.0,
        due_on=date(2026, 8, 8),
        homepage=False,
        notes="Session 15 SD-TAMPA-V2. Compare clicks/CTR vs pre-apply window.",
        session_script="data/session15_organic_growth_hubs.py",
    ),
    GscWatch(
        slug="appraisal-near-me-14d",
        query="personal property appraisers near me",
        page_path="/pages/personal-property-appraisal",
        baseline_ctr=0.0,
        baseline_position=0.0,
        success_ctr=0.0,
        due_on=date(2026, 8, 8),
        homepage=False,
        notes="Session 15 SD-APPRAISAL-V2. Appraisal near-me check-in.",
        session_script="data/session15_organic_growth_hubs.py",
    ),
)


def _path_matches(page: str | None, expected_path: str) -> bool:
    return normalize_path(page or "") == expected_path


def _is_denylist(page: str | None) -> bool:
    path = normalize_path(page or "")
    return path.startswith("/products/") or path in {
        "/collections/all",
        "/collections/fees-products",
    }


def _aggregate_watch(db: Session, watch: GscWatch, cutoff: datetime) -> dict[str, Any]:
    records = (
        db.query(GSCData)
        .filter(GSCData.date >= cutoff, GSCData.query == watch.query)
        .all()
    )
    matched = [
        r
        for r in records
        if _path_matches(r.page, watch.page_path) and not _is_denylist(r.page)
    ]
    impressions = sum(r.impressions or 0 for r in matched)
    clicks = sum(r.clicks or 0 for r in matched)
    ctr = (clicks / impressions) if impressions else 0.0
    positions = [r.position for r in matched if r.position]
    avg_pos = sum(positions) / len(positions) if positions else 0.0
    return {
        "impressions": impressions,
        "clicks": clicks,
        "ctr": ctr,
        "position": avg_pos,
        "row_count": len(matched),
    }


def generate_gsc_watch_tasks(
    db: Session,
    *,
    today: date | None = None,
    days_back: int = 28,
) -> list[dict[str, Any]]:
    today = today or date.today()
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days_back)
    tasks: list[dict[str, Any]] = []
    for watch in WATCHES:
        if today < watch.due_on:
            continue
        stats = _aggregate_watch(db, watch, cutoff)
        ctr_pct = round(stats["ctr"] * 100, 2)
        baseline_pct = round(watch.baseline_ctr * 100, 2)
        met = stats["ctr"] > watch.success_ctr if watch.success_ctr > 0 else stats["ctr"] > watch.baseline_ctr
        if watch.success_ctr == 0:
            met = stats["ctr"] > 0
        fingerprint = f"gsc.watch:{watch.slug}:{watch.due_on.isoformat()}"
        finding = (
            f"{watch.query} on {watch.page_path}: "
            f"CTR {ctr_pct}% (baseline {baseline_pct}%), "
            f"position {round(stats['position'], 1)}, "
            f"clicks {stats['clicks']}, impressions {stats['impressions']}. "
            f"{'Success threshold met.' if met else 'Still flat vs baseline.'} {watch.notes}"
        )
        description = watch.notes
        if watch.homepage and watch.session_script:
            description += (
                f" Do not auto-rewrite. If still flat, iterate via {watch.session_script}."
            )
        payload: dict[str, Any] = {
            "watch_slug": watch.slug,
            "query": watch.query,
            "page_path": watch.page_path,
            "baseline_ctr": watch.baseline_ctr,
            "baseline_position": watch.baseline_position,
            "current": stats,
            "success_met": met,
            "homepage": watch.homepage,
            "session_script": watch.session_script,
        }
        task: dict[str, Any] = {
            "task_type": "seo",
            "category": "gsc_watch",
            "priority": "HIGH",
            "title": f"GSC watch: {watch.query} ({watch.slug})",
            "description": description,
            "finding": finding,
            "action_endpoint": None,
            "action_kind": None,
            "action_payload": payload,
            "fingerprint": fingerprint,
            "status": "pending",
        }
        if not watch.homepage and not met:
            from app.services.dashboard_service import _maybe_attach_frozen_meta

            page_url = f"https://organizinglifeservices.com{watch.page_path}"
            task = _maybe_attach_frozen_meta(task, page_url, watch.query)
            # Watches stay notes unless a draft actually attached.
            if not task.get("action_kind"):
                task["action_kind"] = None
        tasks.append(task)
    return tasks
