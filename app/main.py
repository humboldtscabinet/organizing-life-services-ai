"""
Organizing Life Services — FastAPI Application Entry Point
"""
# reload-trigger: cors-enabled-v4

import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth import require_api_key
from app.db.database import SessionLocal
from app.routes.content import router as content_router
from app.routes.dashboard import router as dashboard_router
from app.routes.lifecycle import router as lifecycle_router
from app.routes.llm import router as llm_router
from app.routes.seo import router as seo_router
from app.routes.shopify import router as shopify_router
from app.routes.vision import router as vision_router
from app.runtime_config import cors_allow_origins

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Organizing Life Services — Operations API",
    description="Internal API for SEO data, audits, and business operations.",
    version="0.5.0",
)

# Enable CORS so Shopify admin pages can call our proxy endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers — all require API key authentication
app.include_router(seo_router, dependencies=[Depends(require_api_key)])
app.include_router(shopify_router, dependencies=[Depends(require_api_key)])
app.include_router(vision_router, dependencies=[Depends(require_api_key)])
app.include_router(lifecycle_router, dependencies=[Depends(require_api_key)])
app.include_router(dashboard_router, dependencies=[Depends(require_api_key)])
app.include_router(content_router, dependencies=[Depends(require_api_key)])
app.include_router(llm_router, dependencies=[Depends(require_api_key)])

@app.get("/health")
def health_check():
    """
    Health check endpoint (no auth required).

    Verifies the API is running and the database is reachable.
    """
    # Check database connectivity
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Health check DB failure: {e}")

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "ols-api",
        "version": "0.5.0",
        "database": db_status,
        "auth": "enabled",
    }
