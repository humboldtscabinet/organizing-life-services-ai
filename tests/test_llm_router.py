import json
from types import SimpleNamespace

import pytest

from app.services import content_engine
from app.services import llm_router
from app.services.llm_router import (
    HighRiskGateError,
    LLMProviderUnavailable,
    LLMRequest,
    LLMResult,
    _provider_for,
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


def test_clerk_and_executive_provider_selection(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_MODEL", "gemma4:12b")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    assert _provider_for("clerk") == ("ollama", "gemma4:12b")
    assert _provider_for("executive") == ("anthropic", "claude-sonnet-4-20250514")


def test_judiciary_defaults_to_anthropic_when_no_xai_key(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_JUDGE_MODEL", "claude-sonnet-4-20250514")

    provider, model = _provider_for("judiciary")

    assert provider == "anthropic"
    assert model == "claude-sonnet-4-20250514"


def test_judiciary_uses_xai_grok_when_key_present(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-test-key")
    monkeypatch.delenv("XAI_JUDGE_MODEL", raising=False)

    provider, model = _provider_for("judiciary")

    assert provider == "xai"
    assert model == "grok-4"


def test_judiciary_is_independent_of_executive_when_xai_key_present(monkeypatch):
    """The whole point of the xAI judge: judge provider != executive provider."""
    monkeypatch.setenv("XAI_API_KEY", "xai-test-key")

    executive_provider, _ = _provider_for("executive")
    judiciary_provider, _ = _provider_for("judiciary")

    assert executive_provider == "anthropic"
    assert judiciary_provider == "xai"
    assert judiciary_provider != executive_provider


def test_xai_judge_model_is_configurable(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-test-key")
    monkeypatch.setenv("XAI_JUDGE_MODEL", "grok-4-fast")

    provider, model = _provider_for("judiciary")

    assert provider == "xai"
    assert model == "grok-4-fast"


def test_route_llm_routes_judiciary_to_xai(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-test-key")

    captured = {}

    class _FakeMessage:
        content = '{"verdict": "PASS", "reasons": [], "blocking_issue": ""}'

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeUsage:
        prompt_tokens = 11
        completion_tokens = 5

    class _FakeCompletion:
        id = "xai-cmpl-1"
        choices = [_FakeChoice()]
        usage = _FakeUsage()

    class _FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _FakeCompletion()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeOpenAI:
        def __init__(self, api_key, base_url):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            self.chat = _FakeChat()

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeOpenAI)

    result = route_llm(
        LLMRequest(
            task_type="content_publish_review",
            risk_level="high",
            preferred_role="judiciary",
            response_format="json",
            prompt="Review this draft.",
        )
    )

    assert result.provider == "xai"
    assert result.model == "grok-4"
    assert result.model_role == "judiciary"
    assert result.total_tokens == 16
    assert captured["base_url"] == "https://api.x.ai/v1"
    assert captured["response_format"] == {"type": "json_object"}


def test_xai_call_requires_key(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    with pytest.raises(LLMProviderUnavailable):
        llm_router._call_xai(
            LLMRequest(task_type="content_publish_review", prompt="x"),
            role="judiciary",
            model="grok-4",
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
        '<h2>Intro</h2><p>estate sale clearwater appears in the first paragraph. '
        'Organizing Life Services helps homeowners across Tampa Bay, Florida.</p>'
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


def test_generate_blog_post_rejects_generic_or_unsupported_claims(monkeypatch):
    payload = {
        "title": "Estate Sale Clearwater Guide",
        "meta_description": "Estate sale Clearwater help from local Tampa Bay experts for downsizing and cleanout planning.",
        "body_html": (
            '<h2>Intro</h2><p>estate sale clearwater help from Organizing Life '
            'Services in Tampa Bay, Florida. In today\'s world, our guaranteed '
            'service makes everything simple.</p>'
            '<h2>Ready?</h2><p><a href="tel:7275426028">(727) 542-6028</a> '
            '<a href="/pages/contact-us">Contact</a></p>'
        ),
        "summary_html": "<p>Summary.</p>",
        "handle": "estate-sale-clearwater",
        "tags": ["estate sales"],
    }

    def fake_route(request, db=None):
        return LLMResult(
            text=json.dumps(payload),
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            model_role="executive",
            status="success",
        )

    monkeypatch.setattr(content_engine, "_get_existing_blog_urls", lambda: [])
    monkeypatch.setattr(content_engine, "route_llm", fake_route)

    with pytest.raises(ValueError, match="generic AI phrase"):
        content_engine.generate_blog_post(
            db=None,
            topic="Estate Sale Clearwater",
            target_keyword="estate sale clearwater",
        )


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
            "body_html": (
                '<h2>Ready?</h2><p>Organizing Life Services helps Tampa Bay, '
                'Florida families. <a href="tel:7275426028">(727) 542-6028</a> '
                '<a href="/pages/contact-us">Contact</a></p>'
            ),
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
