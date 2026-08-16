"""Operational alert inbox for the private dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import GA4Data, GoogleAdsData, GSCData, OpsAlert
from app.redaction import bounded_json_object, redact_sensitive_text, truncate_text

VALID_SEVERITIES = {"INFO", "WARNING", "CRITICAL"}
VALID_STATUSES = {"open", "acknowledged", "dismissed", "resolved"}
ACTIVE_STATUSES = {"open", "acknowledged"}
MAX_SOURCE_CHARS = 100
MAX_TITLE_CHARS = 300
MAX_FINGERPRINT_CHARS = 300
MAX_MESSAGE_CHARS = 4000


def _clean_short_text(value: str | None, *, max_chars: int) -> str:
    return truncate_text(redact_sensitive_text((value or "").strip()), max_chars)


def _clean_optional_text(value: str | None, *, max_chars: int) -> str | None:
    if value is None:
        return None
    cleaned = truncate_text(redact_sensitive_text(value.strip()), max_chars)
    return cleaned or None


def normalize_severity(value: str) -> str:
    severity = (value or "").strip().upper()
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"Invalid alert severity: {value}")
    return severity


def normalize_status(value: str) -> str:
    status = (value or "").strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid alert status: {value}")
    return status


def alert_to_dict(alert: OpsAlert) -> dict[str, Any]:
    return {
        "id": alert.id,
        "source": alert.source,
        "severity": alert.severity,
        "status": alert.status,
        "title": alert.title,
        "message": alert.message,
        "fingerprint": alert.fingerprint,
        "details": alert.details,
        "occurrence_count": alert.occurrence_count or 1,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "updated_at": alert.updated_at.isoformat() if alert.updated_at else None,
        "last_seen_at": alert.last_seen_at.isoformat() if alert.last_seen_at else None,
        "acknowledged_at": (
            alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
        ),
        "dismissed_at": alert.dismissed_at.isoformat() if alert.dismissed_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
    }


def create_alert(
    db: Session,
    *,
    source: str,
    severity: str,
    title: str,
    message: str | None = None,
    fingerprint: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create an alert, or update the active alert with the same fingerprint.

    Repeated n8n checks should send a stable fingerprint so the dashboard shows
    one alert with an occurrence count instead of one alert per run.
    """
    now = datetime.utcnow()
    normalized_source = _clean_short_text(source, max_chars=MAX_SOURCE_CHARS)
    normalized_title = _clean_short_text(title, max_chars=MAX_TITLE_CHARS)
    normalized_fingerprint = _clean_optional_text(
        fingerprint,
        max_chars=MAX_FINGERPRINT_CHARS,
    )
    sanitized_message = _clean_optional_text(message, max_chars=MAX_MESSAGE_CHARS)
    sanitized_details = bounded_json_object(details)

    if not normalized_source:
        raise ValueError("Alert source is required")
    if not normalized_title:
        raise ValueError("Alert title is required")

    normalized_severity = normalize_severity(severity)
    existing: OpsAlert | None = None

    if normalized_fingerprint:
        existing = (
            db.query(OpsAlert)
            .filter(
                OpsAlert.fingerprint == normalized_fingerprint,
                OpsAlert.status.in_(ACTIVE_STATUSES),
            )
            .order_by(OpsAlert.created_at.desc())
            .first()
        )

    if existing:
        existing.source = normalized_source
        existing.severity = normalized_severity
        existing.status = "open"
        existing.title = normalized_title
        existing.message = sanitized_message
        existing.details = sanitized_details
        existing.occurrence_count = (existing.occurrence_count or 1) + 1
        existing.updated_at = now
        existing.last_seen_at = now
        existing.acknowledged_at = None
        existing.dismissed_at = None
        existing.resolved_at = None
        alert = existing
    else:
        alert = OpsAlert(
            source=normalized_source,
            severity=normalized_severity,
            status="open",
            title=normalized_title,
            message=sanitized_message,
            fingerprint=normalized_fingerprint,
            details=sanitized_details,
            occurrence_count=1,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        db.add(alert)

    db.commit()
    db.refresh(alert)
    return alert_to_dict(alert)


def list_alerts(
    db: Session,
    *,
    status: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    limit: int = 50,
) -> list[OpsAlert]:
    query = db.query(OpsAlert)

    if status:
        query = query.filter(OpsAlert.status == normalize_status(status))
    if severity:
        query = query.filter(OpsAlert.severity == normalize_severity(severity))
    if source:
        query = query.filter(OpsAlert.source == source.strip())

    return (
        query.order_by(OpsAlert.last_seen_at.desc(), OpsAlert.created_at.desc())
        .limit(limit)
        .all()
    )


def get_alert(db: Session, alert_id: int) -> OpsAlert | None:
    return db.query(OpsAlert).filter(OpsAlert.id == alert_id).first()


def acknowledge_alert(db: Session, alert_id: int) -> dict[str, Any]:
    alert = get_alert(db, alert_id)
    if not alert:
        return {"status": "error", "detail": "Alert not found"}

    now = datetime.utcnow()
    alert.status = "acknowledged"
    alert.acknowledged_at = now
    alert.updated_at = now
    db.commit()
    db.refresh(alert)
    return {"status": "success", "alert": alert_to_dict(alert)}


def dismiss_alert(db: Session, alert_id: int) -> dict[str, Any]:
    alert = get_alert(db, alert_id)
    if not alert:
        return {"status": "error", "detail": "Alert not found"}

    now = datetime.utcnow()
    alert.status = "dismissed"
    alert.dismissed_at = now
    alert.updated_at = now
    db.commit()
    db.refresh(alert)
    return {"status": "success", "alert": alert_to_dict(alert)}


def resolve_alert(db: Session, alert_id: int) -> dict[str, Any]:
    alert = get_alert(db, alert_id)
    if not alert:
        return {"status": "error", "detail": "Alert not found"}

    now = datetime.utcnow()
    alert.status = "resolved"
    alert.resolved_at = now
    alert.updated_at = now
    db.commit()
    db.refresh(alert)
    return {"status": "success", "alert": alert_to_dict(alert)}


def get_alert_metrics(db: Session) -> dict[str, Any]:
    by_status = {
        status: count
        for status, count in db.query(OpsAlert.status, func.count(OpsAlert.id))
        .group_by(OpsAlert.status)
        .all()
    }
    by_severity = {
        severity: count
        for severity, count in db.query(OpsAlert.severity, func.count(OpsAlert.id))
        .filter(OpsAlert.status.in_(ACTIVE_STATUSES))
        .group_by(OpsAlert.severity)
        .all()
    }
    latest_open = (
        db.query(OpsAlert)
        .filter(OpsAlert.status == "open")
        .order_by(OpsAlert.created_at.desc())
        .first()
    )

    return {
        "status_breakdown": by_status,
        "active_severity_breakdown": by_severity,
        "open_count": by_status.get("open", 0),
        "acknowledged_count": by_status.get("acknowledged", 0),
        "critical_open_count": (
            db.query(OpsAlert)
            .filter(OpsAlert.status == "open", OpsAlert.severity == "CRITICAL")
            .count()
        ),
        "warning_open_count": (
            db.query(OpsAlert)
            .filter(OpsAlert.status == "open", OpsAlert.severity == "WARNING")
            .count()
        ),
        "latest_open_at": latest_open.created_at.isoformat() if latest_open else None,
    }


FRESHNESS_CHANNELS = {
    "gsc": GSCData,
    "ga4": GA4Data,
    "google_ads": GoogleAdsData,
}

FRESHNESS_WARNING_HOURS = 36
FRESHNESS_CRITICAL_HOURS = 72


def classify_ingest_freshness(
    last_ingested: datetime | None,
    *,
    now: datetime | None = None,
    warning_hours: int = FRESHNESS_WARNING_HOURS,
    critical_hours: int = FRESHNESS_CRITICAL_HOURS,
) -> dict[str, Any]:
    """Classify freshness from ingest time (created_at), not Google's metric date.

    GSC Search Analytics often lags 2–3 days, so max(date) would always look
    stale. The 36h SLA is “did the mini pull run,” not “is Google’s report
    current.”
    """
    now = now or datetime.utcnow()
    if last_ingested is None:
        return {
            "stale": True,
            "severity": "CRITICAL",
            "age_hours": None,
        }
    age_hours = (now - last_ingested).total_seconds() / 3600.0
    if age_hours > critical_hours:
        return {"stale": True, "severity": "CRITICAL", "age_hours": age_hours}
    if age_hours > warning_hours:
        return {"stale": True, "severity": "WARNING", "age_hours": age_hours}
    return {"stale": False, "severity": None, "age_hours": age_hours}


def check_data_freshness(
    db: Session,
    *,
    max_age_hours: int = FRESHNESS_WARNING_HOURS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Open or resolve data:freshness:{channel} alerts from ingest timestamps."""
    now = now or datetime.utcnow()
    channels: list[dict[str, Any]] = []
    stale: list[str] = []

    for channel, model in FRESHNESS_CHANNELS.items():
        last_ingested = db.query(func.max(model.created_at)).scalar()
        last_date = db.query(func.max(model.date)).scalar()
        classified = classify_ingest_freshness(
            last_ingested,
            now=now,
            warning_hours=max_age_hours,
        )
        fingerprint = f"data:freshness:{channel}"
        last_ingested_iso = last_ingested.isoformat() if last_ingested else None
        last_date_iso = last_date.isoformat() if last_date else None
        entry = {
            "channel": channel,
            "last_ingested_at": last_ingested_iso,
            "last_date": last_date_iso,
            **classified,
        }
        if classified["stale"]:
            stale.append(channel)
            age = classified["age_hours"]
            age_label = "no rows" if age is None else f"{age:.1f}h since ingest"
            create_alert(
                db,
                source="platform_sync",
                severity=classified["severity"],
                title=f"{channel.upper()} data is stale",
                message=(
                    f"{channel} last ingest {age_label}. "
                    "Mini Postgres is the ops source of truth."
                ),
                fingerprint=fingerprint,
                details={
                    "channel": channel,
                    "last_ingested_at": last_ingested_iso,
                    "last_date": last_date_iso,
                    "age_hours": classified["age_hours"],
                },
            )
        else:
            existing = (
                db.query(OpsAlert)
                .filter(
                    OpsAlert.fingerprint == fingerprint,
                    OpsAlert.status.in_(ACTIVE_STATUSES),
                )
                .order_by(OpsAlert.created_at.desc())
                .first()
            )
            if existing:
                resolve_alert(db, existing.id)
        channels.append(entry)

    return {
        "status": "success",
        "stale_channels": stale,
        "channels": channels,
        "checked_at": now.isoformat(),
    }
