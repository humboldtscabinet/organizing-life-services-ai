"""Unit coverage for Session 20 page CTR (downsizing specialist) patch.

These tests exercise the pure selection / planning logic only; no Shopify or
network calls are made. The mutation guard activates on import, which is fine.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def s20():
    return _load(
        "session20_downsizing_specialist_page_ctr",
        ROOT / "data" / "session20_downsizing_specialist_page_ctr.py",
    )


def _mf(s20, key: str, value: str, mf_id: int = 1) -> dict:
    return {
        "id": mf_id,
        "namespace": s20.METAFIELD_NAMESPACE,
        "key": key,
        "value": value,
        "type": s20.METAFIELD_TYPE,
    }


# --- Proposed copy contract ------------------------------------------------


def test_copy_lengths(s20):
    assert len(s20.PAGE_TITLE) <= 60
    assert 100 <= len(s20.PAGE_DESCRIPTION) <= 160


def test_copy_speaks_to_downsizing_specialist_without_stuffing(s20):
    title = s20.PAGE_TITLE.lower()
    desc = s20.PAGE_DESCRIPTION.lower()
    # Serves the query "downsizing specialist" in both fields.
    assert "downsizing specialist" in title
    assert "downsizing specialist" in desc
    # Region context + approved phone; no "near me" stuffing.
    assert "Tampa Bay" in s20.PAGE_TITLE
    assert "Tampa Bay" in s20.PAGE_DESCRIPTION
    assert "(727) 542-6028" in s20.PAGE_DESCRIPTION
    assert "near me" not in title
    assert "near me" not in desc


def test_copy_stays_on_brand(s20):
    """OLS is a downsizing / estate-sale company; no invented claims, prices, or GTM tags."""
    blob = (s20.PAGE_TITLE + " " + s20.PAGE_DESCRIPTION).lower()
    assert "pawn" not in blob
    # No invented price figures / testimonials / guarantees / GTM tags / addresses.
    assert "$" not in blob
    assert "gtm-" not in blob
    for banned in (
        "guarantee",
        "guaranteed",
        "best price",
        "highest price",
        "5-star",
        "reviews say",
    ):
        assert banned not in blob


# --- Handle targeting (must not write other pages) ------------------------


def test_targets_the_downsizing_page_only(s20):
    """Session 20 targets the downsizing-moving-sales page, not the Tampa hub."""
    assert s20.TARGET_HANDLE == "downsizing-moving-sales"
    # Deliberately not the Tampa hub (rank job, not a snippet job).
    assert "tampa-hillsborough" not in s20.TARGET_HANDLE


def test_selects_only_target_handle(s20):
    pages = [
        {"id": 101, "handle": "some-other-page", "title": "Other"},
        {"id": 202, "handle": s20.TARGET_HANDLE, "title": "Downsizing & Moving Sales"},
        # The Tampa hub must NOT be selected.
        {"id": 303, "handle": "estate-sale-tampa-hillsborough-county", "title": "Tampa"},
    ]
    target = s20.select_target_page(pages)
    assert target["id"] == 202
    assert target["handle"] == s20.TARGET_HANDLE


def test_select_raises_when_target_absent(s20):
    pages = [
        {"id": 1, "handle": "not-the-one", "title": "Nope"},
        {"id": 2, "handle": "estate-sale-tampa-hillsborough-county", "title": "Nope"},
    ]
    with pytest.raises(RuntimeError):
        s20.select_target_page(pages)


def test_select_raises_on_duplicate_handles(s20):
    pages = [
        {"id": 1, "handle": s20.TARGET_HANDLE, "title": "A"},
        {"id": 2, "handle": s20.TARGET_HANDLE, "title": "B"},
    ]
    with pytest.raises(RuntimeError):
        s20.select_target_page(pages)


# --- Metafield planning + idempotency -------------------------------------


def test_plan_create_when_absent(s20):
    assert s20.plan_metafield(None, s20.PAGE_TITLE) == "create"


def test_plan_update_when_value_differs(s20):
    existing = _mf(s20, s20.TITLE_KEY, "Downsizing & Moving Sales in Greater Tampa Bay Area")
    assert s20.plan_metafield(existing, s20.PAGE_TITLE) == "update"


def test_plan_unchanged_when_value_matches(s20):
    title_existing = _mf(s20, s20.TITLE_KEY, s20.PAGE_TITLE)
    desc_existing = _mf(s20, s20.DESCRIPTION_KEY, s20.PAGE_DESCRIPTION)
    assert s20.plan_metafield(title_existing, s20.PAGE_TITLE) == "unchanged"
    assert s20.plan_metafield(desc_existing, s20.PAGE_DESCRIPTION) == "unchanged"


def test_find_metafield_respects_namespace_and_key(s20):
    metafields = [
        {"id": 9, "namespace": "custom", "key": s20.TITLE_KEY, "value": "wrong ns"},
        _mf(s20, s20.TITLE_KEY, "right one", mf_id=10),
        _mf(s20, s20.DESCRIPTION_KEY, "desc", mf_id=11),
    ]
    found = s20.find_metafield(metafields, s20.TITLE_KEY)
    assert found is not None
    assert found["id"] == 10
    assert s20.find_metafield(metafields, "no_such_key") is None


def test_idempotency_matching_values_yield_no_change(s20):
    """When both metafields already hold the proposed copy, nothing changes."""
    metafields = [
        _mf(s20, s20.TITLE_KEY, s20.PAGE_TITLE, mf_id=1),
        _mf(s20, s20.DESCRIPTION_KEY, s20.PAGE_DESCRIPTION, mf_id=2),
    ]
    title_mf = s20.find_metafield(metafields, s20.TITLE_KEY)
    desc_mf = s20.find_metafield(metafields, s20.DESCRIPTION_KEY)
    title_status = s20.plan_metafield(title_mf, s20.PAGE_TITLE)
    desc_status = s20.plan_metafield(desc_mf, s20.PAGE_DESCRIPTION)
    changed = title_status != "unchanged" or desc_status != "unchanged"
    assert not changed
