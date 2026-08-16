"""Read-only WorkflowLog and LLMAudit listings for the operator dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import LLMAudit, WorkflowLog
from app.redaction import redact_sensitive_text, sanitize_jsonish

DEFAULT_DAYS = 7
MAX_ROWS = 200


def list_workflow_logs(
    db: Session,
    *,
    days: int = DEFAULT_DAYS,
    limit: int = MAX_ROWS,
    workflow_name: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    days = max(1, min(days, 30))
    limit = max(1, min(limit, MAX_ROWS))
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = db.query(WorkflowLog).filter(WorkflowLog.created_at >= cutoff)
    if workflow_name:
        query = query.filter(WorkflowLog.workflow_name == workflow_name)
    if status:
        query = query.filter(WorkflowLog.status == status)
    rows = query.order_by(WorkflowLog.created_at.desc()).limit(limit).all()
    return [serialize_workflow_log(row) for row in rows]


def serialize_workflow_log(row: WorkflowLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "workflow_name": row.workflow_name,
        "status": row.status,
        "payload": sanitize_jsonish(row.payload),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_llm_audits(
    db: Session,
    *,
    days: int = DEFAULT_DAYS,
    limit: int = MAX_ROWS,
    task_type: str | None = None,
    status: str | None = None,
    include_bodies: bool = False,
) -> list[dict[str, Any]]:
    days = max(1, min(days, 30))
    limit = max(1, min(limit, MAX_ROWS))
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = db.query(LLMAudit).filter(LLMAudit.created_at >= cutoff)
    if task_type:
        query = query.filter(LLMAudit.task_type == task_type)
    if status:
        query = query.filter(LLMAudit.status == status)
    rows = query.order_by(LLMAudit.created_at.desc()).limit(limit).all()
    return [serialize_llm_audit(row, include_bodies=include_bodies) for row in rows]


def serialize_llm_audit(row: LLMAudit, *, include_bodies: bool = False) -> dict[str, Any]:
    payload = {
        "id": row.id,
        "task_type": row.task_type,
        "risk_level": row.risk_level,
        "model_role": row.model_role,
        "provider": row.provider,
        "model": row.model,
        "status": row.status,
        "verdict": row.verdict,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "total_tokens": row.total_tokens,
        "estimated_cost_usd": row.estimated_cost_usd,
        "input_refs": sanitize_jsonish(row.input_refs),
        "error": redact_sensitive_text(row.error) if row.error else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    if include_bodies:
        payload["request"] = sanitize_jsonish(row.request)
        payload["response"] = sanitize_jsonish(row.response)
    return payload
