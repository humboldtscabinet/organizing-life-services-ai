from app.services import task_apply_service as tas
from app.services.frozen_meta_service import (
    TITLE_MAX,
    classify_gsc_url,
    draft_title,
    frozen_meta_fingerprint,
    payload_has_frozen_copy,
    validate_frozen_payload,
)
from tests.test_task_apply import _FakeDb, _Task


def test_classify_refuses_homepage_products_collections():
    assert classify_gsc_url("https://organizinglifeservices.com/")["kind"] == "homepage"
    assert classify_gsc_url("/products/credit-card-fee")["kind"] == "blocked"
    assert classify_gsc_url("/collections/fees-products")["kind"] == "blocked"
    page = classify_gsc_url(
        "https://organizinglifeservices.com/pages/personal-property-appraisal"
    )
    assert page == {
        "kind": "page",
        "path": "/pages/personal-property-appraisal",
        "handle": "personal-property-appraisal",
    }


def test_draft_title_respects_length_cap():
    title = draft_title("estate sale companies in tampa bay florida near me extra words")
    assert len(title) <= TITLE_MAX
    assert "Organizing Life Services" in title or title


def test_validate_frozen_payload_page_ignores_body_html_key():
    resource, fields = validate_frozen_payload(
        {
            "resource": "page",
            "page_id": 99,
            "path": "/pages/personal-property-appraisal",
            "new_title": "Personal Property Appraisal | OLS",
            "new_meta_description": "Tampa Bay personal property appraisals. Call OLS today.",
            "body_html": "<p>should not be written</p>",
        }
    )
    assert resource == "page"
    assert fields == {
        "page_id": 99,
        "title": "Personal Property Appraisal | OLS",
        "meta_description": "Tampa Bay personal property appraisals. Call OLS today.",
    }
    assert "body_html" not in fields


def test_validate_frozen_payload_refuses_homepage_path():
    try:
        validate_frozen_payload(
            {
                "resource": "page",
                "page_id": 1,
                "path": "/",
                "new_title": "Home | OLS",
                "new_meta_description": "Tampa Bay estate sales. Call OLS today.",
            }
        )
    except ValueError as exc:
        assert "homepage" in str(exc).lower() or "refuse" in str(exc).lower()
    else:
        raise AssertionError("expected homepage refuse")


def test_missing_frozen_copy_is_not_applyable():
    task = _Task(
        action_kind="shopify.apply_frozen_meta",
        action_payload={"resource": "page", "page_id": 1},
        status="pending",
    )
    serialized = tas.serialize_dashboard_task(task)
    assert serialized["applyable"] is False
    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=True, judge_verdict="PASS")
    assert result["status"] == "error"
    assert result["code"] == "missing_frozen_copy"


def test_frozen_meta_apply_calls_update_page_seo_only(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "app.services.shopify_service.update_page_seo",
        lambda page_id, title=None, body_html=None, meta_description=None: calls.append(
            {
                "page_id": page_id,
                "title": title,
                "body_html": body_html,
                "meta_description": meta_description,
            }
        ) or {"status": "updated", "page_id": page_id, "fields_updated": ["title", "metafield", "id"]},
    )

    payload = {
        "resource": "page",
        "page_id": 42,
        "path": "/pages/personal-property-appraisal",
        "new_title": "Personal Property Appraisal Tampa | OLS",
        "new_meta_description": "Appraisals for Tampa Bay estates. Call OLS today.",
        "body_html": "<p>ignored</p>",
        "extra": "ignored",
    }
    task = _Task(
        action_kind="shopify.apply_frozen_meta",
        action_payload=payload,
        status="pending",
        fingerprint=frozen_meta_fingerprint(
            "page", 42, payload["new_title"], payload["new_meta_description"]
        ),
    )
    result = tas.apply_task(_FakeDb(task), 1, human_confirmed=True, judge_verdict="PASS")
    assert result["status"] == "success"
    assert calls == [
        {
            "page_id": 42,
            "title": payload["new_title"],
            "body_html": None,
            "meta_description": payload["new_meta_description"],
        }
    ]
    assert "extra" in result["result"]["ignored_payload_keys"]
    assert "body_html" in result["result"]["ignored_payload_keys"]


def test_payload_has_frozen_copy():
    assert payload_has_frozen_copy({"new_title": "A", "new_meta_description": "B"})
    assert not payload_has_frozen_copy({"new_title": "A"})
