"""
Organizing Life Services — FastAPI Application Entry Point
"""

import logging

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api_errors import (
    APIError,
    api_error_handler,
    http_exception_handler,
    normalize_api_responses,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.auth import require_api_key
from app.db.database import SessionLocal
from app.routes.content import router as content_router
from app.routes.dashboard import router as dashboard_router
from app.routes.lifecycle import router as lifecycle_router
from app.routes.llm import router as llm_router
from app.routes.seo import router as seo_router
from app.routes.shopify import router as shopify_router
from app.routes.vision import router as vision_router
from app.settings import validate_runtime_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = validate_runtime_settings()


def _database_check() -> tuple[str, str]:
    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        return "ok", ""
    except Exception as exc:
        logger.error("Database readiness check failed: %s", exc)
        return "error", str(exc)
    finally:
        if db is not None:
            db.close()


def _readiness_payload() -> tuple[dict, int]:
    issues = settings.readiness_issues()
    db_status, db_error = _database_check()

    if db_status != "ok":
        issues.append("Database connection failed")

    payload = {
        "service": "ols-api",
        "version": settings.app_version,
        "auth": "enabled",
        "checks": {
            "config": "ok" if not settings.readiness_issues() else "error",
            "database": db_status,
        },
    }

    if issues:
        payload["status"] = "not_ready"
        payload["issues"] = issues
        if db_error:
            payload["checks"]["database_detail"] = "Database connection failed"
        return payload, status.HTTP_503_SERVICE_UNAVAILABLE

    payload["status"] = "ready"
    return payload, status.HTTP_200_OK

app = FastAPI(
    title="Organizing Life Services — Operations API",
    description="Internal API for SEO data, audits, and business operations.",
    version=settings.app_version,
)
app.middleware("http")(normalize_api_responses)
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
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


@app.get("/health/live")
def live_health_check():
    """Liveness probe: if this responds, the process is up."""
    return {
        "status": "ok",
        "service": "ols-api",
        "version": settings.app_version,
        "auth": "enabled",
    }


@app.get("/health/ready")
def readiness_health_check():
    """Readiness probe for Docker and other automated dependents."""
    payload, status_code = _readiness_payload()
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/health")
def compatibility_health_check():
    """
    Compatibility health endpoint for humans.

    This stays readable in browsers and CLI tools, while automated checks should
    use `/health/live` and `/health/ready`.
    """
    readiness_payload, readiness_status = _readiness_payload()
    return {
        "status": "ok" if readiness_status == status.HTTP_200_OK else "degraded",
        "service": "ols-api",
        "version": settings.app_version,
        "auth": "enabled",
        "liveness": "/health/live",
        "readiness": "/health/ready",
        "checks": readiness_payload["checks"],
        "issues": readiness_payload.get("issues", []),
    }
