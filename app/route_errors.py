"""Small helpers for route-level error semantics."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status


def raise_route_error(
    logger: logging.Logger,
    operation: str,
    exc: Exception,
    *,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> None:
    """Log a route failure and surface it as a real HTTP error."""
    logger.exception("%s failed", operation)
    raise HTTPException(status_code=status_code, detail=f"{operation} failed: {exc}") from exc


def raise_unavailable(detail: str) -> None:
    """Surface unconfigured optional integrations as HTTP 503."""
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


def raise_if_service_error(result: dict, *, default_status: int = 400) -> None:
    """Turn legacy service-level {'status': 'error'} payloads into HTTP errors."""
    if not isinstance(result, dict) or result.get("status") != "error":
        return

    detail = result.get("detail") or result.get("message") or "Operation failed"
    lowered = str(detail).lower()
    status_code = status.HTTP_404_NOT_FOUND if "not found" in lowered else default_status
    raise HTTPException(status_code=status_code, detail=detail)
