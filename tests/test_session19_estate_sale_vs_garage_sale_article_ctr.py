"""Unit coverage for Session 19 article CTR (estate sale vs garage sale) patch.

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
def s19():
    return _load(
        "session19_estate_sale_vs_garage_sale_article_ctr",
        ROOT / "data" / "session19_estate_sale_vs_garage_sale_article_ctr.py",
    )


def _mf(s19, key: str, value: str, mf_id: int = 1) -> dict:
    return {
        "id": mf_id,
        "namespace": s19.METAFIELD_NAMESPACE,
        "key": key,
        "value": value,
        "type": s19.METAFIELD_TYPE,
    }


# --- Proposed copy contract ------------------------------------------------


def test_copy_lengths(s19):
    assert len(s19.ARTICLE_TITLE) <= 60
    assert 120 <= len(s19.ARTICLE_DESCRIPTION) <= 160


def test_copy_speaks_to_comparison_without_stuffing(s19):
    title = s19.ARTICLE_TITLE.lower()
    desc = s19.ARTICLE_DESCRIPTION.lower()
    # Serves the comparison query "estate sale vs garage sale" in both fields.
    assert "estate sale" in title
    assert "garage sale" in title
    assert "estate sale" in desc
    assert "garage sale" in desc
    # Region context + approved phone; no "near me" stuffing.
    assert "Tampa Bay" in s19.ARTICLE_DESCRIPTION
    assert "(727) 542-6028" in s19.ARTICLE_DESCRIPTION
    assert "near me" not in title
    assert "near me" not in desc


def test_copy_stays_on_brand(s19):
    """OLS is an estate-sale company, not a pawn shop or garage-sale operator; no invented claims."""
    blob = (s19.ARTICLE_TITLE + " " + s19.ARTICLE_DESCRIPTION).lower()
    assert "pawn" not in blob
    # No invented price figures / testimonials / guarantees.
    assert "$" not in blob
    for banned in (
        "guarantee",
        "guaranteed",
        "best price",
        "highest price",
        "5-star",
        "reviews say",
    ):
        assert banned not in blob


# --- Handle targeting (must not write other articles) ---------------------


def test_targets_the_garage_sale_handle_only(s19):
    """Session 19 targets the garage-sale post, never the yard-sale cannibal."""
    assert s19.TARGET_HANDLE == "estate-sale-vs-garage-sale-know-the-differences"
    assert "yard-sale" not in s19.TARGET_HANDLE


def test_selects_only_target_handle(s19):
    articles = [
        {"id": 101, "handle": "some-other-post", "title": "Other"},
        {"id": 202, "handle": s19.TARGET_HANDLE, "title": "Estate vs Garage"},
        # The cannibalization hypothesis post must NOT be selected.
        {"id": 303, "handle": "yard-sale-vs-estate-sale-key-differences", "title": "Yard"},
    ]
    target = s19.select_target_article(articles)
    assert target["id"] == 202
    assert target["handle"] == s19.TARGET_HANDLE


def test_select_raises_when_target_absent(s19):
    articles = [
        {"id": 1, "handle": "not-the-one", "title": "Nope"},
        {"id": 2, "handle": "yard-sale-vs-estate-sale-key-differences", "title": "Nope"},
    ]
    with pytest.raises(RuntimeError):
        s19.select_target_article(articles)


def test_select_raises_on_duplicate_handles(s19):
    articles = [
        {"id": 1, "handle": s19.TARGET_HANDLE, "title": "A"},
        {"id": 2, "handle": s19.TARGET_HANDLE, "title": "B"},
    ]
    with pytest.raises(RuntimeError):
        s19.select_target_article(articles)


# --- Metafield planning + idempotency -------------------------------------


def test_plan_create_when_absent(s19):
    assert s19.plan_metafield(None, s19.ARTICLE_TITLE) == "create"


def test_plan_update_when_value_differs(s19):
    existing = _mf(s19, s19.TITLE_KEY, "Estate Sale vs Garage Sale: Key Differences Explained")
    assert s19.plan_metafield(existing, s19.ARTICLE_TITLE) == "update"


def test_plan_unchanged_when_value_matches(s19):
    title_existing = _mf(s19, s19.TITLE_KEY, s19.ARTICLE_TITLE)
    desc_existing = _mf(s19, s19.DESCRIPTION_KEY, s19.ARTICLE_DESCRIPTION)
    assert s19.plan_metafield(title_existing, s19.ARTICLE_TITLE) == "unchanged"
    assert s19.plan_metafield(desc_existing, s19.ARTICLE_DESCRIPTION) == "unchanged"


def test_find_metafield_respects_namespace_and_key(s19):
    metafields = [
        {"id": 9, "namespace": "custom", "key": s19.TITLE_KEY, "value": "wrong ns"},
        _mf(s19, s19.TITLE_KEY, "right one", mf_id=10),
        _mf(s19, s19.DESCRIPTION_KEY, "desc", mf_id=11),
    ]
    found = s19.find_metafield(metafields, s19.TITLE_KEY)
    assert found is not None
    assert found["id"] == 10
    assert s19.find_metafield(metafields, "no_such_key") is None


def test_idempotency_matching_values_yield_no_change(s19):
    """When both metafields already hold the proposed copy, nothing changes."""
    metafields = [
        _mf(s19, s19.TITLE_KEY, s19.ARTICLE_TITLE, mf_id=1),
        _mf(s19, s19.DESCRIPTION_KEY, s19.ARTICLE_DESCRIPTION, mf_id=2),
    ]
    title_mf = s19.find_metafield(metafields, s19.TITLE_KEY)
    desc_mf = s19.find_metafield(metafields, s19.DESCRIPTION_KEY)
    title_status = s19.plan_metafield(title_mf, s19.ARTICLE_TITLE)
    desc_status = s19.plan_metafield(desc_mf, s19.ARTICLE_DESCRIPTION)
    changed = title_status != "unchanged" or desc_status != "unchanged"
    assert not changed
