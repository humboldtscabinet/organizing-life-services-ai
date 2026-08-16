"""Allowlisted DashboardTask apply dispatcher.

Cron/n8n may create tasks. Only a human-confirmed dashboard click may apply
them. The dispatcher calls Python service functions with a frozen payload —
it does not HTTP-to-self, and it does not let the LLM invent verbs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.db.models import DashboardTask, WorkflowLog
from app.services.frozen_meta_service import payload_has_frozen_copy
from app.services.llm_router import HighRiskGateError, assert_high_stakes_gate

logger = logging.getLogger(__name__)

APPLYABLE_STATUSES = frozenset({"pending", "approved"})
BLOCKING_TASK_STATUSES = frozenset(
    {"pending", "delayed", "dismissed", "approved", "executing"}
)

# Explicit refusals — never dispatch even if a task row is poisoned.
NEVER_APPLY_KINDS = frozenset(
    {
        "ads.budget_bid_keyword",
        "gbp.write",
        "gbp.*",
        "gtm.create_arbitrary",
    }
)

# Later verbs are documented but not registered. Apply returns 400, not a write.
DEFERRED_ACTION_KINDS = frozenset(
    {
        "ga4.unmark_junk_key_events",
    }
)


@dataclass(frozen=True)
class ActionKindSpec:
    kind: str
    gate: str
    deterministic: bool
    handler: str


ALLOWLIST: dict[str, ActionKindSpec] = {
    "gtm.ensure_phone_clicks": ActionKindSpec(
        kind="gtm.ensure_phone_clicks",
        gate="gtm_workspace_write",
        deterministic=True,
        handler="gtm_ensure_phone_clicks",
    ),
    "gtm.publish_version": ActionKindSpec(
        kind="gtm.publish_version",
        gate="gtm_publish",
        deterministic=True,
        handler="gtm_publish_version",
    ),
    "content.generate_and_publish": ActionKindSpec(
        kind="content.generate_and_publish",
        gate="content_publish",
        deterministic=False,
        handler="content_generate_and_publish",
    ),
    "shopify.apply_frozen_meta": ActionKindSpec(
        kind="shopify.apply_frozen_meta",
        gate="shopify_update",
        deterministic=False,
        handler="shopify_apply_frozen_meta",
    ),
    "ads.disable_bogus_conversions": ActionKindSpec(
        kind="ads.disable_bogus_conversions",
        gate="ads_conversion_mutate",
        deterministic=True,
        handler="ads_disable_bogus_conversions",
    ),
}


def is_applyable_kind(action_kind: str | None) -> bool:
    return bool(action_kind) and action_kind in ALLOWLIST


def is_applyable_task(task: DashboardTask) -> bool:
    kind = task.action_kind
    if not is_applyable_kind(kind):
        return False
    if task.status not in APPLYABLE_STATUSES:
        return False
    if kind == "shopify.apply_frozen_meta":
        return payload_has_frozen_copy(task.action_payload)
    return True


def is_deterministic_kind(action_kind: str | None) -> bool:
    spec = ALLOWLIST.get(action_kind or "")
    return bool(spec and spec.deterministic)


def serialize_dashboard_task(task: DashboardTask) -> dict[str, Any]:
    kind = task.action_kind
    return {
        "id": task.id,
        "task_type": task.task_type,
        "category": task.category,
        "priority": task.priority,
        "title": task.title,
        "description": task.description,
        "finding": task.finding,
        "action_endpoint": task.action_endpoint,
        "action_kind": kind,
        "action_payload": task.action_payload,
        "fingerprint": task.fingerprint,
        "status": task.status,
        "result": task.result,
        "applyable": is_applyable_task(task),
        "deterministic": is_deterministic_kind(kind),
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "approved_at": task.approved_at.isoformat() if task.approved_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def apply_task(
    db: Session,
    task_id: int,
    *,
    human_confirmed: bool = False,
    judge_verdict: str | None = None,
) -> dict[str, Any]:
    """Execute an allowlisted DashboardTask with a frozen payload.

    n8n must never call this. Deterministic kinds (GTM) require the operator
    checkbox only; the judiciary PASS dropdown stays for Shopify copy.
    """
    task = db.query(DashboardTask).filter(DashboardTask.id == task_id).first()
    if not task:
        return {"status": "error", "detail": "Task not found"}

    kind = task.action_kind
    if not kind:
        return {
            "status": "error",
            "detail": "Task is advisory (no action_kind); Apply is not available",
            "code": "advisory_task",
        }
    if kind in NEVER_APPLY_KINDS or kind.startswith("gbp."):
        return {
            "status": "error",
            "detail": f"action_kind {kind} is permanently refused",
            "code": "never_apply",
        }
    if kind in DEFERRED_ACTION_KINDS:
        return {
            "status": "error",
            "detail": f"action_kind {kind} is not implemented yet",
            "code": "not_implemented",
        }
    spec = ALLOWLIST.get(kind)
    if spec is None:
        return {
            "status": "error",
            "detail": f"action_kind {kind} is not allowlisted",
            "code": "unknown_action_kind",
        }
    if kind == "shopify.apply_frozen_meta" and not payload_has_frozen_copy(
        task.action_payload
    ):
        return {
            "status": "error",
            "detail": "Frozen title and meta description are required before Apply",
            "code": "missing_frozen_copy",
        }
    if task.status not in APPLYABLE_STATUSES:
        return {
            "status": "error",
            "detail": f"Task is {task.status}, not pending or approved",
        }

    resolved_verdict = judge_verdict
    if spec.deterministic:
        if not human_confirmed:
            return {
                "status": "error",
                "detail": (
                    "High-stakes write requires human_confirmed=true after review"
                ),
            }
        resolved_verdict = "PASS"
    try:
        assert_high_stakes_gate(
            task_type=spec.gate,
            risk_level="high",
            judge_verdict=resolved_verdict,
            human_approved=human_confirmed,
        )
    except HighRiskGateError as exc:
        return {"status": "error", "detail": str(exc)}

    if task.status == "pending":
        task.status = "approved"
        task.approved_at = datetime.utcnow()

    task.status = "executing"
    db.commit()

    handler = _HANDLERS[spec.handler]
    try:
        result = handler(db, task)
    except Exception as exc:
        logger.exception("Apply failed for task %s kind %s", task.id, kind)
        task.status = "failed"
        task.result = {"error": str(exc)}
        db.add(
            WorkflowLog(
                workflow_name="dashboard_task_apply",
                status="failed",
                payload={
                    "task_id": task.id,
                    "action_kind": kind,
                    "error": str(exc),
                },
            )
        )
        db.commit()
        return {
            "status": "error",
            "detail": f"Apply failed: {exc}",
            "task_id": task.id,
            "action_kind": kind,
        }

    task.status = "completed"
    task.completed_at = datetime.utcnow()
    task.result = result
    db.add(
        WorkflowLog(
            workflow_name="dashboard_task_apply",
            status="success",
            payload={
                "task_id": task.id,
                "action_kind": kind,
                "result_status": (result or {}).get("status"),
            },
        )
    )
    db.commit()
    return {
        "status": "success",
        "task_id": task.id,
        "action_kind": kind,
        "result": result,
        "task": serialize_dashboard_task(task),
    }


def _frozen_payload(task: DashboardTask) -> dict[str, Any]:
    payload = task.action_payload or {}
    return payload if isinstance(payload, dict) else {}


def _apply_gtm_ensure_phone_clicks(db: Session, task: DashboardTask) -> dict[str, Any]:
    from app.services.gtm_service import (
        direct_api_available,
        ensure_phone_call_clicks_tracking,
    )

    if not direct_api_available():
        raise RuntimeError("GTM credentials not configured.")

    payload = _frozen_payload(task)
    create_version = bool(payload.get("create_version", True))
    ensure_result = ensure_phone_call_clicks_tracking(
        dry_run=False,
        create_version_after=create_version,
    )
    publish_task_id = None
    version = ensure_result.get("version") or {}
    version_path = version.get("version_path")
    compiler_error = bool(version.get("compiler_error"))
    if (
        ensure_result.get("status") == "applied"
        and version_path
        and not compiler_error
    ):
        child = _create_publish_child(
            db,
            parent=task,
            version_path=version_path,
            version_name=version.get("name"),
        )
        publish_task_id = child.id

    return {
        "status": ensure_result.get("status"),
        "ensure": {
            "status": ensure_result.get("status"),
            "trigger": (ensure_result.get("trigger") or {}).get("action"),
            "tag": (ensure_result.get("tag") or {}).get("action"),
            "version_path": version_path,
            "compiler_error": compiler_error,
            "created": ensure_result.get("created"),
            "updated": ensure_result.get("updated"),
            "unchanged": ensure_result.get("unchanged"),
        },
        "publish_task_id": publish_task_id,
        "publish_required": bool(publish_task_id),
    }


def _apply_gtm_publish_version(db: Session, task: DashboardTask) -> dict[str, Any]:
    from app.services.gtm_service import direct_api_available, publish_version

    if not direct_api_available():
        raise RuntimeError("GTM credentials not configured.")

    payload = _frozen_payload(task)
    version_path = payload.get("version_path")
    if not isinstance(version_path, str) or "/versions/" not in version_path:
        raise ValueError(
            "Frozen action_payload.version_path is required and must look like "
            "accounts/{account}/containers/{container}/versions/{version}"
        )
    published = publish_version(version_path)
    return {
        "status": published.get("status"),
        "version_path": published.get("version_path") or version_path,
        "version_id": published.get("version_id"),
        "name": published.get("name"),
    }


def _apply_content_generate_and_publish(
    db: Session, task: DashboardTask
) -> dict[str, Any]:
    from app.services.content_engine import publish_to_shopify

    # publish_to_shopify still requires status == approved.
    task.status = "approved"
    task.approved_at = task.approved_at or datetime.utcnow()
    db.commit()

    result = publish_to_shopify(db, task.id)
    if result.get("status") == "error":
        raise RuntimeError(result.get("detail") or "Content publish failed")
    return result


def _apply_ads_disable_bogus_conversions(
    db: Session, task: DashboardTask
) -> dict[str, Any]:
    from app.services.google_ads_service import pause_conversion_action

    payload = _frozen_payload(task)
    forbidden = {"budget", "bid", "keyword", "campaign_id", "amount_micros"}
    if forbidden.intersection(payload):
        raise ValueError("Payload contains refused Ads mutate fields")
    action_id = payload.get("conversion_action_id")
    if not action_id:
        raise ValueError("Frozen conversion_action_id is required")
    if payload.get("target_status") not in (None, "PAUSED"):
        raise ValueError("Only PAUSED is allowed for conversion actions")
    return pause_conversion_action(int(action_id))


def _apply_shopify_frozen_meta(db: Session, task: DashboardTask) -> dict[str, Any]:
    from app.services.frozen_meta_service import validate_frozen_payload
    from app.services.shopify_service import update_article_seo, update_page_seo

    payload = _frozen_payload(task)
    extra_keys = set(payload) - {
        "resource",
        "page_id",
        "article_id",
        "blog_id",
        "handle",
        "blog_handle",
        "path",
        "query",
        "current_title",
        "current_meta_description",
        "new_title",
        "new_meta_description",
        "preview",
        "lead_score",
        "lead_tier",
        "lead_relevance_reasons",
    }
    resource, fields = validate_frozen_payload(payload)
    if resource == "page":
        result = update_page_seo(
            fields["page_id"],
            title=fields["title"],
            meta_description=fields["meta_description"],
        )
    else:
        result = update_article_seo(
            fields["blog_id"],
            fields["article_id"],
            title=fields["title"],
            meta_description=fields["meta_description"],
        )
    return {
        "status": result.get("status"),
        "resource": resource,
        "ignored_payload_keys": sorted(extra_keys),
        "shopify": result,
    }


def _create_publish_child(
    db: Session,
    *,
    parent: DashboardTask,
    version_path: str,
    version_name: str | None,
) -> DashboardTask:
    fingerprint = f"gtm.publish_version:{version_path}"
    existing = (
        db.query(DashboardTask)
        .filter(
            DashboardTask.fingerprint == fingerprint,
            DashboardTask.status.in_(list(BLOCKING_TASK_STATUSES)),
        )
        .first()
    )
    if existing and existing.action_kind == "gtm.publish_version":
        return existing

    child = DashboardTask(
        task_type="seo",
        category="gtm_publish",
        priority="HIGH",
        title=f"Publish GTM version {version_name or version_path}",
        description=(
            "Publish the frozen GTM container version live. Separate from "
            "workspace ensure — do not bundle. n8n must not call Apply."
        ),
        finding=(
            f"Parent task #{parent.id} created version {version_path} "
            f"with compiler_error=false."
        ),
        action_kind="gtm.publish_version",
        action_endpoint=None,
        action_payload={
            "version_path": version_path,
            "parent_task_id": parent.id,
            "preview": {
                "action": "publish live",
                "version_path": version_path,
            },
        },
        fingerprint=fingerprint,
        status="pending",
    )
    db.add(child)
    db.flush()
    return child


_HANDLERS: dict[str, Callable[[Session, DashboardTask], dict[str, Any]]] = {
    "gtm_ensure_phone_clicks": _apply_gtm_ensure_phone_clicks,
    "gtm_publish_version": _apply_gtm_publish_version,
    "content_generate_and_publish": _apply_content_generate_and_publish,
    "shopify_apply_frozen_meta": _apply_shopify_frozen_meta,
    "ads_disable_bogus_conversions": _apply_ads_disable_bogus_conversions,
}
