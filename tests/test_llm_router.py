import json
from types import SimpleNamespace

import pytest

from app.services import content_engine
from app.services.llm_router import (
    HighRiskGateError,
    LLMProviderUnavailable,
    LLMRequest,
    LLMResult,
    assert_high_stakes_gate,
    is_high_stakes,
    route_llm,
)


class _FakeOllamaResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "response": '{"ok": true}',
            "prompt_eval_count": 7,
            "eval_count": 3,
            "done": True,
        }


def test_low_risk_request_routes_to_local_clerk(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeOllamaResponse()

    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://ollama.test:11434")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "gemma4:12b")
    monkeypatch.setattr("app.services.llm_router.httpx.post", fake_post)

    result = route_llm(
        LLMRequest(
            task_type="classification",
            risk_level="low",
            response_format="json",
            prompt="Classify this task.",
        )
    )

    assert result.provider == "ollama"
    assert result.model == "gemma4:12b"
    assert result.model_role == "clerk"
    assert result.text == '{"ok": true}'
    assert result.total_tokens == 10
    assert calls[0]["url"] == "http://ollama.test:11434/api/generate"
    assert calls[0]["json"]["format"] == "json"


def test_executive_request_requires_anthropic_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(LLMProviderUnavailable):
        route_llm(
            LLMRequest(
                task_type="content_draft",
                risk_level="medium",
                preferred_role="executive",
                prompt="Draft content.",
            )
        )


def test_high_stakes_gate_fails_closed_until_judge_and_human_pass():
    assert is_high_stakes("content_publish", "medium")

    with pytest.raises(HighRiskGateError):
        assert_high_stakes_gate(
            task_type="content_publish",
            risk_level="medium",
            judge_verdict=None,
            human_approved=True,
        )

    with pytest.raises(HighRiskGateError):
        assert_high_stakes_gate(
            task_type="content_publish",
            risk_level="medium",
            judge_verdict="PASS",
            human_approved=False,
        )

    assert_high_stakes_gate(
        task_type="content_publish",
        risk_level="medium",
        judge_verdict="PASS",
        human_approved=True,
    )


def test_generate_blog_post_uses_router_and_keeps_audit_id(monkeypatch):
    body = (
        '<h2>Intro</h2><p>estate sale clearwater appears in the first paragraph.</p>'
        '<h2>Ready to Get Started?</h2><p>Call '
        '<a href="tel:7275426028">(727) 542-6028</a> or visit '
        '<a href="/pages/contact-us">our contact page</a> to schedule help.</p>'
    )
    payload = {
        "title": "Estate Sale Clearwater Guide",
        "meta_description": "Estate sale Clearwater help from local Tampa Bay experts for downsizing and cleanout planning.",
        "body_html": body,
        "summary_html": "<p>Helpful local guide.</p>",
        "handle": "Estate Sale Clearwater Guide!!!",
        "tags": ["estate sales", "clearwater"],
    }

    def fake_route(request, db=None):
        assert request.task_type == "content_draft"
        assert request.risk_level == "medium"
        assert request.preferred_role == "executive"
        return LLMResult(
            text=json.dumps(payload),
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            model_role="executive",
            status="success",
            audit_id=42,
        )

    monkeypatch.setattr(content_engine, "_get_existing_blog_urls", lambda: [])
    monkeypatch.setattr(content_engine, "route_llm", fake_route)

    post = content_engine.generate_blog_post(
        db=None,
        topic="Estate Sale Clearwater",
        target_keyword="estate sale clearwater",
    )

    assert post["_llm_audit_id"] == 42
    assert post["handle"] == "estate-sale-clearwater-guide"


def test_publish_judge_pass_returns_audit_metadata(monkeypatch):
    def fake_route(request, db=None):
        assert request.task_type == "content_publish_review"
        assert request.risk_level == "high"
        assert request.preferred_role == "judiciary"
        return LLMResult(
            text=json.dumps({"verdict": "PASS", "reasons": [], "blocking_issue": ""}),
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            model_role="judiciary",
            status="success",
            audit_id=77,
        )

    monkeypatch.setattr(content_engine, "route_llm", fake_route)
    task = SimpleNamespace(
        id=123,
        title="Approved content task",
        action_payload={"target_keyword": "estate sale clearwater"},
    )

    review = content_engine._judge_blog_post_for_publish(
        db=None,
        post_data={
            "_llm_audit_id": 42,
            "title": "Estate Sale Clearwater",
            "meta_description": "Estate sale Clearwater help.",
            "handle": "estate-sale-clearwater",
            "tags": ["estate sales"],
            "body_html": '<h2>Ready?</h2><p><a href="tel:7275426028">(727) 542-6028</a> <a href="/pages/contact-us">Contact</a></p>',
            "summary_html": "<p>Summary</p>",
        },
        task=task,
    )

    assert review == {"verdict": "PASS", "reasons": [], "audit_id": 77}


def test_publish_judge_flag_blocks_publish(monkeypatch):
    def fake_route(request, db=None):
        return LLMResult(
            text=json.dumps(
                {
                    "verdict": "FLAG",
                    "reasons": ["Missing contact link"],
                    "blocking_issue": "CTA is incomplete",
                }
            ),
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            model_role="judiciary",
            status="success",
            audit_id=78,
        )

    monkeypatch.setattr(content_engine, "route_llm", fake_route)
    task = SimpleNamespace(id=123, title="Approved content task", action_payload={})

    with pytest.raises(ValueError, match="Content judge FLAG"):
        content_engine._judge_blog_post_for_publish(
            db=None,
            post_data={"title": "Bad draft", "body_html": "<p>No CTA</p>"},
            task=task,
        )
