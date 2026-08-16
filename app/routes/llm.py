"""LLM operations and health endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.audit_log_service import list_llm_audits
from app.services.llm_router import local_llm_status

router = APIRouter(prefix="/api/llm", tags=["LLM"])


@router.get("/local-status")
def get_local_llm_status():
    """
    Verify the API container can reach host Ollama and see configured Gemma models.
    """
    return local_llm_status()


@router.get("/audit")
def list_llm_audit(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(100, ge=1, le=200),
    task_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    include_bodies: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Read-only LLMAudit list. Bodies omitted unless include_bodies=1."""
    audits = list_llm_audits(
        db,
        days=days,
        limit=limit,
        task_type=task_type,
        status=status_filter,
        include_bodies=include_bodies,
    )
    return {"status": "success", "count": len(audits), "audits": audits}
