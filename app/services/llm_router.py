"""
Accountable LLM routing for OLS agent workflows.

This module is intentionally small and conservative. It centralizes model
selection, audit logging, and high-stakes gating before broader agent behavior
is introduced.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import logging
import os
from typing import Any, Literal

import httpx
from sqlalchemy.orm import Session

from app.db.models import LLMAudit

logger = logging.getLogger(__name__)

RiskLevel = Literal["low", "medium", "high"]
ModelRole = Literal["clerk", "executive", "judiciary"]
ResponseFormat = Literal["text", "json"]

HIGH_STAKES_TASK_TYPES = {
    "shopify_publish",
    "shopify_update",
    "shopify_delete",
    "content_publish",
    "bulk_alt_text_push",
    "ads_budget_change",
}


class LLMRouterError(RuntimeError):
    """Base router error."""


class LLMProviderUnavailable(LLMRouterError):
    """Raised when the selected provider is not configured or reachable."""


class HighRiskGateError(LLMRouterError):
    """Raised when a high-stakes write lacks required approvals."""


@dataclass(frozen=True)
class LLMRequest:
    task_type: str
    prompt: str
    risk_level: RiskLevel = "low"
    response_format: ResponseFormat = "text"
    system_prompt: str | None = None
    preferred_role: ModelRole | None = None
    allowed_tools: tuple[str, ...] = ()
    input_refs: dict[str, Any] = field(default_factory=dict)
    max_tokens: int = 1024
    temperature: float = 0.2
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    model_role: ModelRole
    status: str
    audit_id: int | None = None
    verdict: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


def is_high_stakes(task_type: str, risk_level: RiskLevel = "low") -> bool:
    return risk_level == "high" or task_type in HIGH_STAKES_TASK_TYPES


def assert_high_stakes_gate(
    *,
    task_type: str,
    risk_level: RiskLevel,
    judge_verdict: str | None,
    human_approved: bool,
) -> None:
    """
    Fail closed for production writes that require independent review.

    This is separate from model generation so services can call it immediately
    before mutating Shopify, ads budgets, or other customer-facing state.
    """
    if not is_high_stakes(task_type, risk_level):
        return

    if judge_verdict != "PASS" or not human_approved:
        raise HighRiskGateError(
            "High-stakes write requires judge_verdict='PASS' and human_approved=True"
        )


def route_llm(request: LLMRequest, db: Session | None = None) -> LLMResult:
    role = request.preferred_role or _default_role_for(request)
    provider, model = _provider_for(role)
    audit_id = None

    try:
        if provider == "ollama":
            result = _call_ollama(request=request, role=role, model=model)
        elif provider == "anthropic":
            result = _call_anthropic(request=request, role=role, model=model)
        else:
            raise LLMProviderUnavailable(f"Unsupported LLM provider: {provider}")

        audit_id = _write_audit(
            db=db,
            request=request,
            result=result,
            error=None,
        )
        if audit_id:
            return _replace_audit_id(result, audit_id)
        return result

    except Exception as exc:
        _write_audit(
            db=db,
            request=request,
            result=LLMResult(
                text="",
                provider=provider,
                model=model,
                model_role=role,
                status="error",
            ),
            error=str(exc),
        )
        raise


def local_llm_status(timeout: float = 5.0) -> dict[str, Any]:
    """Return Ollama reachability and configured Gemma model availability."""
    base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://host.docker.internal:11434")
    configured_models = [
        os.getenv("LOCAL_LLM_MODEL", "gemma4:12b"),
        os.getenv("LOCAL_LLM_LARGE_MODEL", "gemma4:31b"),
    ]
    configured_models = [model for model in configured_models if model]

    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return {
            "status": "error",
            "reachable": False,
            "base_url": base_url,
            "configured_models": configured_models,
            "available_models": [],
            "missing_models": configured_models,
            "detail": str(exc),
        }

    available_models = sorted(
        {
            model.get("name") or model.get("model")
            for model in data.get("models", [])
            if model.get("name") or model.get("model")
        }
    )
    missing_models = [
        model for model in configured_models if model not in available_models
    ]

    return {
        "status": "ok" if not missing_models else "degraded",
        "reachable": True,
        "base_url": base_url,
        "configured_models": configured_models,
        "available_models": available_models,
        "missing_models": missing_models,
    }


def _default_role_for(request: LLMRequest) -> ModelRole:
    if request.risk_level == "low":
        return "clerk"
    return "executive"


def _provider_for(role: ModelRole) -> tuple[str, str]:
    if role == "clerk":
        return "ollama", os.getenv("LOCAL_LLM_MODEL", "gemma4:12b")
    if role == "executive":
        return "anthropic", os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    if role == "judiciary":
        return "anthropic", os.getenv("ANTHROPIC_JUDGE_MODEL", "claude-sonnet-4-20250514")
    raise LLMProviderUnavailable(f"No provider configured for role: {role}")


def _call_ollama(request: LLMRequest, role: ModelRole, model: str) -> LLMResult:
    base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://host.docker.internal:11434")
    payload: dict[str, Any] = {
        "model": model,
        "prompt": request.prompt,
        "stream": False,
        "options": {
            "temperature": request.temperature,
            "num_predict": request.max_tokens,
        },
    }
    if request.system_prompt:
        payload["system"] = request.system_prompt
    if request.response_format == "json":
        payload["format"] = "json"

    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/api/generate",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LLMProviderUnavailable(f"Ollama request failed: {exc}") from exc

    data = response.json()
    text = data.get("response", "")
    prompt_tokens = data.get("prompt_eval_count")
    completion_tokens = data.get("eval_count")
    total_tokens = (
        prompt_tokens + completion_tokens
        if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int)
        else None
    )
    return LLMResult(
        text=text,
        provider="ollama",
        model=model,
        model_role=role,
        status="success",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        raw_response=_safe_raw_response(data),
    )


def _call_anthropic(request: LLMRequest, role: ModelRole, model: str) -> LLMResult:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMProviderUnavailable("ANTHROPIC_API_KEY is not configured")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "messages": [{"role": "user", "content": request.prompt}],
    }
    if request.system_prompt:
        kwargs["system"] = request.system_prompt

    message = client.messages.create(**kwargs)
    text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    ).strip()
    prompt_tokens = getattr(message.usage, "input_tokens", None)
    completion_tokens = getattr(message.usage, "output_tokens", None)
    total_tokens = (
        prompt_tokens + completion_tokens
        if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int)
        else None
    )
    return LLMResult(
        text=text,
        provider="anthropic",
        model=model,
        model_role=role,
        status="success",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        raw_response={"id": getattr(message, "id", None)},
    )


def _write_audit(
    *,
    db: Session | None,
    request: LLMRequest,
    result: LLMResult,
    error: str | None,
) -> int | None:
    if db is None:
        return None

    record = LLMAudit(
        task_type=request.task_type,
        risk_level=request.risk_level,
        model_role=result.model_role,
        provider=result.provider,
        model=result.model,
        status="error" if error else result.status,
        verdict=result.verdict,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        estimated_cost_usd=None,
        input_refs=request.input_refs,
        request=_safe_request(request),
        response=_safe_result(result),
        error=error,
        created_at=datetime.utcnow(),
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        return int(record.id)
    except Exception:
        db.rollback()
        logger.exception("Failed to write LLM audit record")
        return None


def _replace_audit_id(result: LLMResult, audit_id: int) -> LLMResult:
    return LLMResult(
        text=result.text,
        provider=result.provider,
        model=result.model,
        model_role=result.model_role,
        status=result.status,
        audit_id=audit_id,
        verdict=result.verdict,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        raw_response=result.raw_response,
    )


def _safe_request(request: LLMRequest) -> dict[str, Any]:
    data = asdict(request)
    data["prompt"] = _truncate(data.get("prompt", ""))
    if data.get("system_prompt"):
        data["system_prompt"] = _truncate(data["system_prompt"])
    return data


def _safe_result(result: LLMResult) -> dict[str, Any]:
    data = asdict(result)
    data["text"] = _truncate(data.get("text", ""))
    return data


def _safe_raw_response(data: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "model",
        "created_at",
        "done",
        "total_duration",
        "load_duration",
        "prompt_eval_count",
        "eval_count",
    }
    return {key: data.get(key) for key in allowed_keys if key in data}


def _truncate(value: str, limit: int = 6000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]"
