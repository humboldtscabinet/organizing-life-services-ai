"""
API Key Authentication for OLS Operations API.

All endpoints (except /health) require a valid API key
passed via the X-API-Key header.

Usage in routes:
    from app.auth import require_api_key

    @router.get("/endpoint")
    def my_endpoint(api_key: str = Depends(require_api_key)):
        ...
"""

import logging
import os
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# Header name for API key
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _get_api_key() -> str:
    """
    Get the configured API key from environment.

    If OLS_API_KEY is not set, generates one on first startup
    and logs it so the operator can save it.
    """
    key = os.getenv("OLS_API_KEY", "").strip()
    if not key:
        # Generate a secure random key and warn
        key = secrets.token_urlsafe(32)
        os.environ["OLS_API_KEY"] = key
        logger.warning(
            "============================================\n"
            "  NO OLS_API_KEY SET — auto-generated key:\n"
            f"  {key}\n"
            "  Add OLS_API_KEY to your .env file!\n"
            "============================================"
        )
    return key


# Resolve once at import time
_VALID_API_KEY = _get_api_key()


async def require_api_key(
    api_key: str = Security(API_KEY_HEADER),
) -> str:
    """
    FastAPI dependency that validates the X-API-Key header.

    Returns the API key if valid, raises 401/403 otherwise.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, _VALID_API_KEY):
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
