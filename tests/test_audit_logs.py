from datetime import datetime

from app.db.models import LLMAudit, WorkflowLog
from app.services.audit_log_service import serialize_llm_audit, serialize_workflow_log


def test_workflow_log_payload_is_redacted():
    row = WorkflowLog(
        id=1,
        workflow_name="dashboard_task_apply",
        status="success",
        payload={"api_key": "super-secret", "task_id": 9},
        created_at=datetime.utcnow(),
    )
    serialized = serialize_workflow_log(row)
    assert serialized["payload"]["api_key"] == "[redacted]"
    assert serialized["payload"]["task_id"] == 9


def test_llm_audit_omits_bodies_by_default():
    row = LLMAudit(
        id=2,
        task_type="shopify_update",
        risk_level="high",
        model_role="judiciary",
        provider="anthropic",
        model="claude",
        status="success",
        verdict="PASS",
        request={"prompt": "secret OLS_API_KEY=abc", "api_key": "nope"},
        response={"text": "ok"},
        created_at=datetime.utcnow(),
    )
    listed = serialize_llm_audit(row, include_bodies=False)
    assert "request" not in listed
    assert "response" not in listed
    with_bodies = serialize_llm_audit(row, include_bodies=True)
    assert with_bodies["request"]["api_key"] == "[redacted]"
    assert "OLS_API_KEY=" not in str(with_bodies["request"]) or "[redacted]" in str(
        with_bodies["request"]
    )


def test_logs_and_audit_routes_require_api_key(client):
    assert client.get("/api/dashboard/logs").status_code == 401
    assert client.get("/api/llm/audit").status_code == 401
