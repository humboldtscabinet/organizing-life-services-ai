"""
Organizing Life Services — FastAPI Application Entry Point
"""

from fastapi import FastAPI

from app.routes.seo import router as seo_router
from app.routes.shopify import router as shopify_router
from app.routes.vision import router as vision_router

app = FastAPI(
    title="Organizing Life Services — Operations API",
    description="Internal API for SEO data, audits, and business operations.",
    version="0.3.0",
)

# Register routers
app.include_router(seo_router)
app.include_router(shopify_router)
app.include_router(vision_router)


@app.get("/health")
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": "ols-api", "version": "0.3.0"}
