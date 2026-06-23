import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "data" / "session11_service_area_first_wave.py"
PLAN_PATH = ROOT / "data" / "service_area_plan.py"


@pytest.fixture(scope="module")
def rollout():
    spec = importlib.util.spec_from_file_location(
        "session11_service_area_first_wave", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def service_area_plan():
    spec = importlib.util.spec_from_file_location("service_area_plan", PLAN_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_first_wave_targets_match_service_area_plan(rollout, service_area_plan):
    target_handles = [target.handle for target in rollout.FIRST_WAVE_TARGETS]

    assert target_handles == service_area_plan.FIRST_WAVE_HANDLES
    rollout.validate_targets()


def test_target_metadata_stays_within_search_snippet_limits(rollout):
    for target in rollout.FIRST_WAVE_TARGETS:
        assert len(target.seo_title) <= 65, target.handle
        assert len(target.meta_description) <= 160, target.handle


def test_body_block_is_theme_safe_and_contains_required_elements(rollout):
    target = rollout.FIRST_WAVE_TARGETS[0]
    body = rollout.build_body_block(target)

    assert rollout.marker_for(target.handle) in body
    assert "<h1" not in body.lower()
    assert 'href="tel:+17275426028"' in body
    assert 'href="/pages/contact-us"' in body
    assert '<script type="application/ld+json">' in body
    assert f"{rollout.SITE}/pages/{target.handle}" in body


def test_schema_json_is_parseable_service_schema(rollout):
    target = rollout.FIRST_WAVE_TARGETS[-1]
    schema = rollout.build_schema(target)
    raw_json = schema.removeprefix(
        '<script type="application/ld+json">'
    ).removesuffix("</script>")

    parsed = json.loads(raw_json)
    assert parsed["@type"] == "Service"
    assert parsed["provider"]["@type"] == "LocalBusiness"
    assert parsed["provider"]["name"] == rollout.ORG_NAME
    assert parsed["url"] == f"{rollout.SITE}/pages/{target.handle}"
    assert {"@type": "City", "name": target.location_label} in parsed["areaServed"]


def test_plan_target_marks_missing_page_as_create(rollout):
    target = rollout.FIRST_WAVE_TARGETS[0]

    result = rollout.plan_target(target, existing_page=None, metafields={})

    assert result["page_exists"] is False
    assert result["body_status"] == "create_body"
    assert result["title_status"] == "create_page_title"
    assert result["needs_page_write"] is True
    assert result["needs_meta_write"] is True
    assert result["body_before_chars"] == 0
    assert result["body_after_chars"] > 0


def test_plan_target_is_idempotent_when_marker_title_and_metafields_match(rollout):
    target = rollout.FIRST_WAVE_TARGETS[1]
    existing_body = f"<p>Existing copy</p>\n{rollout.build_body_block(target)}"
    existing_page = {
        "id": 123,
        "handle": target.handle,
        "title": target.page_title,
        "body_html": existing_body,
    }
    metafields = {
        "title_tag": {"id": 1, "key": "title_tag", "value": target.seo_title},
        "description_tag": {
            "id": 2,
            "key": "description_tag",
            "value": target.meta_description,
        },
    }

    result = rollout.plan_target(target, existing_page, metafields)

    assert result["page_exists"] is True
    assert result["body_status"] == "unchanged"
    assert result["title_status"] == "unchanged"
    assert result["needs_page_write"] is False
    assert result["needs_meta_write"] is False
    assert all(item["status"] == "unchanged" for item in result["metafields"])


def test_plan_target_appends_without_overwriting_existing_body(rollout):
    target = rollout.FIRST_WAVE_TARGETS[2]
    existing_body = "<p>Keep this human-written page body.</p>"
    existing_page = {
        "id": 456,
        "handle": target.handle,
        "title": "Old title",
        "body_html": existing_body,
    }

    result = rollout.plan_target(target, existing_page, metafields={})

    assert result["body_status"] == "append_block"
    assert result["title_status"] == "update_page_title"
    assert result["needs_page_write"] is True
    assert result["body_after_chars"] > len(existing_body)
    assert result["body_added_chars"] == result["body_after_chars"] - len(existing_body)


def test_legacy_source_pages_are_report_only_followups(rollout):
    target = next(t for t in rollout.FIRST_WAVE_TARGETS if t.source_handle)

    result = rollout.plan_target(target, existing_page=None, metafields={})

    assert result["source_handle"] == target.source_handle
    assert "does not redirect/noindex" in result["legacy_note"]
