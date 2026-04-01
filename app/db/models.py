"""
SQLAlchemy ORM models — MVP tables per MASTER_PLAN_V2.1
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
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
