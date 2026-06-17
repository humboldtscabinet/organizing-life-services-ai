"""Safety gates for high-stakes business mutations."""

from fastapi import HTTPException, status

from app.services.llm_router import HighRiskGateError, RiskLevel, assert_high_stakes_gate


def require_high_stakes_confirmation(
    *,
    task_type: str,
    risk_level: RiskLevel = "high",
    human_confirmed: bool = False,
    judge_verdict: str | None = None,
) -> None:
    """
    FastAPI-facing wrapper for high-stakes mutation gates.

    Direct write endpoints should call this before touching Shopify, ads,
    public content, or other customer-facing state.
    """
    try:
        assert_high_stakes_gate(
            task_type=task_type,
            risk_level=risk_level,
            judge_verdict=judge_verdict,
            human_approved=human_confirmed,
        )
    except HighRiskGateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{exc}. Pass human_confirmed=true and judge_verdict=PASS "
                "after review to execute this mutation."
            ),
        ) from exc
