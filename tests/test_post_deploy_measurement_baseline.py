import importlib.util
from pathlib import Path

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "post_deploy_measurement_baseline.py"
)


@pytest.fixture(scope="module")
def baseline():
    spec = importlib.util.spec_from_file_location("post_deploy_measurement_baseline", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_classify_event_name_flags_passive_pageviews(baseline):
    assert baseline.classify_event_name("page_view") == "passive_or_pageview"
    assert (
        baseline.classify_event_name("ads_conversion_Contact_Page_load_https_1")
        == "passive_or_pageview"
    )


def test_classify_event_name_flags_lead_intent(baseline):
    assert baseline.classify_event_name("form_submit") == "lead_intent"
    assert baseline.classify_event_name("phone_click_header") == "lead_intent"
    assert baseline.classify_event_name("generate_lead") == "lead_intent"


def test_assess_conversion_tracking_fails_on_passive_key_events(baseline):
    result = baseline.assess_conversion_tracking(
        sessions=100,
        key_events=160,
        event_rows=[
            {"event_name": "page_view", "key_events": 150},
            {"event_name": "form_submit", "key_events": 10},
        ],
    )

    assert result["status"] == "fail"
    assert result["passive_key_events"] == 150
    assert any("Passive events" in issue["issue"] for issue in result["issues"])


def test_assess_conversion_tracking_passes_real_lead_events(baseline):
    result = baseline.assess_conversion_tracking(
        sessions=100,
        key_events=5,
        event_rows=[
            {"event_name": "form_submit", "key_events": 3},
            {"event_name": "phone_click", "key_events": 2},
        ],
    )

    assert result["status"] == "pass"
    assert result["lead_key_events"] == 5
    assert result["passive_key_events"] == 0


def test_content_action_routes_known_service_pages(baseline):
    assert "appraisal page" in baseline.content_action(
        "tampa personal property appraisers",
        "https://organizinglifeservices.com/pages/personal-property-appraisal",
    )
    assert "homepage" in baseline.content_action(
        "estate sales clearwater fl",
        "https://organizinglifeservices.com/",
    )
    assert "service-area" in baseline.content_action(
        "estate sales clearwater fl",
        "https://organizinglifeservices.com/pages/estate-sale-clearwater-pinellas-county",
    )
    assert "educational guide" in baseline.content_action(
        "what is an estate sale",
        "https://organizinglifeservices.com/blogs/news/estate-sales",
    )


def test_legacy_event_pages_are_not_recommended_as_primary_targets(baseline):
    assert baseline.looks_legacy_event_page(
        "https://organizinglifeservices.com/pages/13925-pathfinder-drive-tampa-florida"
    )
    assert "legacy event shell" in baseline.content_action(
        "estate sale organizers",
        "https://organizinglifeservices.com/pages/13925-pathfinder-drive-tampa-florida",
    )
