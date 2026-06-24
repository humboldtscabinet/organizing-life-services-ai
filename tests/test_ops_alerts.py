import pytest

from app.services.ops_alert_service import create_alert, normalize_severity


class _FakeDb:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    def query(self, *_args):
        return _FakeQuery()

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        if obj.id is None:
            obj.id = 1


class _FakeQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return None


def test_create_alert_validates_and_serializes_without_external_services():
    db = _FakeDb()

    alert = create_alert(
        db,
        source="n8n",
        severity="warning",
        title="Backup verification failed",
        message="Postgres restore verifier returned non-zero.",
        fingerprint="backup:postgres",
        details={"script": "verify_postgres_backup.sh"},
    )

    assert db.committed is True
    assert alert["id"] == 1
    assert alert["source"] == "n8n"
    assert alert["severity"] == "WARNING"
    assert alert["status"] == "open"
    assert alert["fingerprint"] == "backup:postgres"
    assert alert["occurrence_count"] == 1
    assert alert["details"] == {"script": "verify_postgres_backup.sh"}


def test_invalid_alert_severity_is_rejected():
    with pytest.raises(ValueError, match="Invalid alert severity"):
        normalize_severity("urgent")


def test_create_alert_route_requires_auth(client):
    response = client.post(
        "/api/dashboard/alerts",
        json={
            "source": "n8n",
            "severity": "INFO",
            "title": "Daily check passed",
        },
    )

    assert response.status_code == 401


def test_create_alert_route_accepts_authenticated_alert(client, auth_headers):
    from app.db.database import get_db
    from app.main import app

    db = _FakeDb()
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = client.post(
            "/api/dashboard/alerts",
            json={
                "source": "n8n",
                "severity": "CRITICAL",
                "title": "Ollama is unreachable",
                "message": "GET /api/tags failed",
                "fingerprint": "llm:ollama:unreachable",
            },
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["alert"]["severity"] == "CRITICAL"
    assert body["alert"]["title"] == "Ollama is unreachable"


def test_acknowledge_missing_alert_returns_404(client, auth_headers, monkeypatch):
    from app.db.database import get_db
    from app.main import app

    monkeypatch.setattr(
        "app.routes.dashboard.acknowledge_alert",
        lambda _db, _alert_id: {"status": "error", "detail": "Alert not found"},
    )
    app.dependency_overrides[get_db] = lambda: object()
    try:
        response = client.post(
            "/api/dashboard/alerts/999/acknowledge",
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"
