"""
Organizing Life Services — FastAPI Application Entry Point
"""

from fastapi import FastAPI

app = FastAPI(
    title="Organizing Life Services — Operations API",
    description="Internal API for SEO data, audits, and business operations.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": "ols-api", "version": "0.1.0"}
