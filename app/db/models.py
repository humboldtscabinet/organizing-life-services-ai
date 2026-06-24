"""
SQLAlchemy ORM models — MVP tables per MASTER_PLAN_V2.1
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.database import Base

# ---------- Core tables ----------

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(30))
    email = Column(String(255))
    source = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowLog(Base):
    __tablename__ = "workflow_logs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_name = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False)
    payload = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class LLMAudit(Base):
    __tablename__ = "llm_audit"
    __table_args__ = (
        Index("ix_llm_audit_task_created", "task_type", "created_at"),
        Index("ix_llm_audit_risk_status", "risk_level", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(100), nullable=False)
    risk_level = Column(String(30), nullable=False)
    model_role = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False)
    verdict = Column(String(30))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    estimated_cost_usd = Column(Float)
    input_refs = Column(JSONB)
    request = Column(JSONB)
    response = Column(JSONB)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------- SEO tables (Phase 1) ----------

class SEOReport(Base):
    __tablename__ = "seo_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(100), nullable=False)
    report_date = Column(DateTime, nullable=False)
    summary = Column(Text)
    data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class GSCData(Base):
    __tablename__ = "gsc_data"
    __table_args__ = (
        Index("ix_gsc_data_date", "date"),
        Index("ix_gsc_data_query", "query"),
        Index("ix_gsc_data_query_date", "query", "date"),
        Index("ix_gsc_data_query_page_date", "query", "page", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(500))
    page = Column(String(500))
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    position = Column(Float, default=0.0)
    date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GA4Data(Base):
    __tablename__ = "ga4_data"
    __table_args__ = (
        Index("ix_ga4_data_date", "date"),
        Index("ix_ga4_data_metric_date", "metric_name", "date"),
        Index("ix_ga4_data_metric_dim_date", "metric_name", "dimension_value", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(200), nullable=False)
    metric_value = Column(Float)
    dimension_name = Column(String(200))
    dimension_value = Column(String(500))
    date = Column(DateTime, nullable=False)
    data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class GBPInsight(Base):
    __tablename__ = "gbp_insights"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(200), nullable=False)
    metric_value = Column(Float)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class GoogleAdsData(Base):
    __tablename__ = "google_ads_data"
    __table_args__ = (
        Index("ix_google_ads_data_date", "date"),
        Index("ix_google_ads_data_campaign_date", "campaign_name", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    campaign_name = Column(String(300))
    ad_group = Column(String(300))
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    conversions = Column(Float, default=0.0)
    date = Column(DateTime, nullable=False)
    data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class ImageAnalysis(Base):
    __tablename__ = "image_analysis"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(1000), nullable=False)
    filename = Column(String(500))
    gallery_name = Column(String(300))
    alt_text = Column(Text)
    title = Column(String(500))
    item_tags = Column(JSONB)       # ["furniture", "antique desk", "oak"]
    description = Column(Text)       # longer description for SEO
    confidence = Column(Float)       # 0.0–1.0 from the vision model
    status = Column(String(50), default="pending")  # pending, analyzed, error
    data = Column(JSONB)             # full API response for debugging
    created_at = Column(DateTime, default=datetime.utcnow)


class ShopifyOrder(Base):
    __tablename__ = "shopify_orders"

    id = Column(Integer, primary_key=True, index=True)
    shopify_order_id = Column(String(100), unique=True, nullable=False)
    order_number = Column(String(50))
    customer_email = Column(String(255))
    total_price = Column(Float)
    status = Column(String(50))
    order_date = Column(DateTime)
    data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------- Dashboard Task Management ----------

class DashboardTask(Base):
    __tablename__ = "dashboard_tasks"
    __table_args__ = (
        Index("ix_dashboard_tasks_status", "status"),
        Index("ix_dashboard_tasks_type_status", "task_type", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), nullable=False)  # seo, ads, shopify, content
    category = Column(String(100), nullable=False)   # e.g. "keyword_optimization", "ad_spend", "meta_fix"
    priority = Column(String(20), nullable=False)     # HIGH, MEDIUM, LOW
    title = Column(String(500), nullable=False)
    description = Column(Text)
    finding = Column(Text)                            # The data that triggered this task
    action_endpoint = Column(String(500))             # API endpoint to call when approved
    action_payload = Column(JSONB)                    # JSON payload for the API call
    status = Column(String(50), default="pending")    # pending, approved, executing, completed, failed, dismissed, delayed
    result = Column(JSONB)                            # Result from execution
    delayed_until = Column(DateTime, nullable=True)   # When to show the task again if delayed
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class OpsAlert(Base):
    __tablename__ = "ops_alerts"
    __table_args__ = (
        Index("ix_ops_alerts_status", "status"),
        Index("ix_ops_alerts_severity_status", "severity", "status"),
        Index("ix_ops_alerts_source_status", "source", "status"),
        Index("ix_ops_alerts_fingerprint_status", "fingerprint", "status"),
        Index("ix_ops_alerts_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)        # INFO, WARNING, CRITICAL
    status = Column(String(30), default="open")          # open, acknowledged, dismissed, resolved
    title = Column(String(300), nullable=False)
    message = Column(Text)
    fingerprint = Column(String(300))
    details = Column(JSONB)
    occurrence_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
