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
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.runtime_config import configured_api_key

logger = logging.getLogger(__name__)

# Header name for API key
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _get_api_key() -> str:
    """
    Get the configured API key from environment.

    Production/server mode fails fast when OLS_API_KEY is absent. Development
    may generate a process-local key, but never prints it to logs.
    """
    return configured_api_key()


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
