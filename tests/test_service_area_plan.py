import importlib.util
from pathlib import Path

import pytest

_PLAN_PATH = Path(__file__).resolve().parent.parent / "data" / "service_area_plan.py"


@pytest.fixture(scope="module")
def plan():
    spec = importlib.util.spec_from_file_location("service_area_plan", _PLAN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_primary_counties_match_real_core_service_area(plan):
    assert set(plan.PRIMARY_COUNTIES) == {"pinellas", "pasco", "hillsborough"}


def test_each_primary_county_has_city_pages(plan):
    for county_key in plan.PRIMARY_COUNTIES:
        assert plan.city_pages_by_county(county_key), county_key


def test_planned_handles_are_unique(plan):
    handles = plan.all_planned_handles()
    assert len(handles) == len(set(handles))


def test_first_wave_covers_hubs_and_highest_signal_city_pages(plan):
    first_wave = set(plan.FIRST_WAVE_HANDLES)

    assert "estate-sale-pinellas-county" in first_wave
    assert "estate-sale-pasco-county" in first_wave
    assert "estate-sale-tampa-hillsborough-county" in first_wave
    assert "estate-sale-palm-harbor-pinellas-county" in first_wave
    assert "estate-sale-clearwater-florida" in first_wave
    assert "estate-sale-new-port-richey-florida" in first_wave
    assert "estate-sale-tarpon-springs-florida" in first_wave


def test_legacy_event_pages_have_permanent_target_handles(plan):
    legacy_migrations = [
        page for page in plan.CITY_PAGES
        if page["status"] == "create_permanent_or_migrate_legacy"
    ]

    assert legacy_migrations
    for page in legacy_migrations:
        assert page.get("current_handle")
        assert page["handle"] != page["current_handle"]
