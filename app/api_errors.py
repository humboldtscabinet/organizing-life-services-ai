"""
Shared API error formatting and response normalization.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from json import JSONDecodeError
from typing import Any

import httpx
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

JSON_CONTENT_TYPES = ("application/json", "application/problem+json")


class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str,
        *,
        code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code or infer_error_code(status_code, detail)
        self.extra = extra or {}
        super().__init__(detail)


def service_result_or_raise(
    result: dict[str, Any],
    *,
    default_error_status: int = 500,
) -> dict[str, Any]:
    """
    Convert legacy service return dicts into explicit API errors.

    This lets routes remove broad `try/except` wrappers while still working
    with service functions that return `{"status": "error"}` or
    `{"status": "unavailable"}` payloads.
    """
    status = result.get("status")

    if status == "error":
        detail = str(result.get("detail") or result.get("message") or "Request failed")
        raise APIError(
            status_code=infer_error_status_code(detail, default=default_error_status),
            detail=detail,
            code=result.get("code"),
            extra={
                key: value
                for key, value in result.items()
                if key not in {"status", "detail", "message", "code"}
            },
        )

    if status == "unavailable":
        raise APIError(
            status_code=503,
            detail=str(result.get("detail") or "Service unavailable"),
            code=result.get("code") or "service_unavailable",
        )

    return result


def infer_error_status_code(detail: str, default: int = 500) -> int:
    text = (detail or "").strip().lower()

    if not text:
        return default

    if "not found" in text:
        return 404

    if any(
        phrase in text
        for phrase in (
            "not pending",
            "must be",
            "already scheduled",
            "already exists",
            "already approved",
            "already dismissed",
        )
    ):
        return 409

    if any(
        phrase in text
        for phrase in (
            "missing",
            "unsupported",
            "invalid",
            "required",
            "no data provided",
            "no files found",
        )
    ):
        return 400

    if any(
        phrase in text
        for phrase in (
            "timed out",
            "timeout",
            "connection",
            "shopify api error",
            "google api",
            "http error",
            "upstream",
        )
    ):
        return 502

    return default


def infer_error_code(status_code: int, detail: str = "") -> str:
    text = (detail or "").strip().lower()

    if status_code == 400:
        return "bad_request"
    if status_code == 401:
        return "missing_api_key"
    if status_code == 403:
        return "invalid_api_key"
    if status_code == 404:
        return "not_found"
    if status_code == 405:
        return "method_not_allowed"
    if status_code == 409:
        return "invalid_state"
    if status_code == 410:
        return "endpoint_retired"
    if status_code == 422:
        return "validation_error"
    if status_code == 502:
        return "upstream_dependency_error"
    if status_code == 503:
        return "service_unavailable"
    if "database" in text:
        return "database_error"
    return "internal_server_error"


def sanitize_error_detail(status_code: int, detail: str) -> str:
    if status_code < 500:
        return detail

    if status_code == 502:
        return "Upstream service error"

    if status_code == 503:
        return "Service unavailable"

    return "Internal server error"


def build_error_payload(
    *,
    status_code: int,
    detail: str,
    code: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "status": "error",
        "detail": sanitize_error_detail(status_code, detail),
        "code": code or infer_error_code(status_code, detail),
    }
    if extra and status_code < 500:
        payload.update(extra)
    return payload


def json_error_response(
    *,
    status_code: int,
    detail: str,
    code: str | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error_payload(
            status_code=status_code,
            detail=detail,
            code=code,
            extra=extra,
        ),
    )


async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return json_error_response(
        status_code=exc.status_code,
        detail=exc.detail,
        code=exc.code,
        extra=exc.extra,
    )


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        detail = str(exc.detail.get("detail") or exc.detail.get("message") or "Request failed")
        code = exc.detail.get("code")
        extra = {
            key: value
            for key, value in exc.detail.items()
            if key not in {"status", "detail", "message", "code"}
        }
    else:
        detail = str(exc.detail)
        code = None
        extra = None

    return json_error_response(
        status_code=exc.status_code,
        detail=detail,
        code=code,
        extra=extra,
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return json_error_response(
        status_code=422,
        detail="Request validation failed",
        code="validation_error",
        extra={"errors": exc.errors()},
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API exception", exc_info=exc)

    if isinstance(exc, httpx.HTTPError):
        return json_error_response(
            status_code=502,
            detail=str(exc),
            code="upstream_dependency_error",
        )

    if isinstance(exc, SQLAlchemyError):
        return json_error_response(
            status_code=503,
            detail="Database operation failed",
            code="database_error",
        )

    return json_error_response(
        status_code=500,
        detail=str(exc),
        code="internal_server_error",
    )


def _json_content_type(response: Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    return any(media_type in content_type for media_type in JSON_CONTENT_TYPES)


def _normalized_payload(payload: dict[str, Any], status_code: int) -> tuple[dict[str, Any], int]:
    status = payload.get("status")

    if status == "error":
        raw_detail = str(payload.get("detail") or payload.get("message") or "Request failed")
        normalized_status = (
            status_code
            if status_code >= 400
            else infer_error_status_code(raw_detail, default=500)
        )
        normalized_payload = build_error_payload(
            status_code=normalized_status,
            detail=raw_detail,
            code=payload.get("code"),
            extra={
                key: value
                for key, value in payload.items()
                if key not in {"status", "detail", "message", "code"}
            },
        )
        return normalized_payload, normalized_status

    if status == "unavailable":
        detail = str(payload.get("detail") or "Service unavailable")
        return (
            {
                "status": "error",
                "detail": sanitize_error_detail(503, detail),
                "code": "service_unavailable",
            },
            503,
        )

    if status == "partial":
        updated = dict(payload)
        updated.setdefault("code", "partial_success")
        return updated, status_code

    return payload, status_code


def _build_response_from_bytes(
    *,
    response: Response,
    body: bytes,
    status_code: int,
) -> Response:
    headers = dict(response.headers)
    headers.pop("content-length", None)
    return Response(
        content=body,
        status_code=status_code,
        headers=headers,
        media_type=response.media_type,
        background=response.background,
    )


async def normalize_api_responses(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)

    if not request.url.path.startswith("/api/") or not _json_content_type(response):
        return response

    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    if not body:
        return _build_response_from_bytes(
            response=response,
            body=body,
            status_code=response.status_code,
        )

    try:
        payload = json.loads(body)
    except JSONDecodeError:
        return _build_response_from_bytes(
            response=response,
            body=body,
            status_code=response.status_code,
        )

    if not isinstance(payload, dict):
        return _build_response_from_bytes(
            response=response,
            body=body,
            status_code=response.status_code,
        )

    normalized_payload, normalized_status = _normalized_payload(payload, response.status_code)
    normalized_body = json.dumps(normalized_payload).encode("utf-8")

    return _build_response_from_bytes(
        response=response,
        body=normalized_body,
        status_code=normalized_status,
    )
