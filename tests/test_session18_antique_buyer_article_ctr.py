"""Unit coverage for Session 18 article CTR (antique buyer) metafield patch.

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
def s18():
    return _load(
        "session18_antique_buyer_article_ctr",
        ROOT / "data" / "session18_antique_buyer_article_ctr.py",
    )


def _mf(s18, key: str, value: str, mf_id: int = 1) -> dict:
    return {
        "id": mf_id,
        "namespace": s18.METAFIELD_NAMESPACE,
        "key": key,
        "value": value,
        "type": s18.METAFIELD_TYPE,
    }


# --- Proposed copy contract ------------------------------------------------


def test_copy_lengths(s18):
    assert len(s18.ARTICLE_TITLE) <= 60
    assert 120 <= len(s18.ARTICLE_DESCRIPTION) <= 160


def test_copy_speaks_to_seller_intent_without_stuffing(s18):
    title = s18.ARTICLE_TITLE.lower()
    desc = s18.ARTICLE_DESCRIPTION.lower()
    # Serves "where to sell antiques locally".
    assert "sell antiques" in desc
    assert "locally" in desc
    assert "antique" in title
    # Region context + approved phone; no "near me" stuffing.
    assert "Tampa Bay" in s18.ARTICLE_DESCRIPTION
    assert "(727) 542-6028" in s18.ARTICLE_DESCRIPTION
    assert "near me" not in title
    assert "near me" not in desc


def test_copy_stays_on_brand(s18):
    """OLS is estate-sale / personal-property, not a pawn shop; no invented claims."""
    blob = (s18.ARTICLE_TITLE + " " + s18.ARTICLE_DESCRIPTION).lower()
    assert "pawn" not in blob
    # No invented price figures / testimonials.
    assert "$" not in blob
    for banned in ("guarantee", "guaranteed", "best price", "highest price", "5-star", "reviews say"):
        assert banned not in blob


# --- Handle targeting (must not write other articles) ---------------------


def test_selects_only_target_handle(s18):
    articles = [
        {"id": 101, "handle": "some-other-post", "title": "Other"},
        {"id": 202, "handle": s18.TARGET_HANDLE, "title": "Antique Buyer"},
        {"id": 303, "handle": "yet-another", "title": "Another"},
    ]
    target = s18.select_target_article(articles)
    assert target["id"] == 202
    assert target["handle"] == s18.TARGET_HANDLE


def test_select_raises_when_target_absent(s18):
    articles = [
        {"id": 1, "handle": "not-the-one", "title": "Nope"},
        {"id": 2, "handle": "also-not", "title": "Nope"},
    ]
    with pytest.raises(RuntimeError):
        s18.select_target_article(articles)


def test_select_raises_on_duplicate_handles(s18):
    articles = [
        {"id": 1, "handle": s18.TARGET_HANDLE, "title": "A"},
        {"id": 2, "handle": s18.TARGET_HANDLE, "title": "B"},
    ]
    with pytest.raises(RuntimeError):
        s18.select_target_article(articles)


# --- Metafield planning + idempotency -------------------------------------


def test_plan_create_when_absent(s18):
    assert s18.plan_metafield(None, s18.ARTICLE_TITLE) == "create"


def test_plan_update_when_value_differs(s18):
    existing = _mf(s18, s18.TITLE_KEY, "How to Find the Best Antique Buyer | Organizing Life Services")
    assert s18.plan_metafield(existing, s18.ARTICLE_TITLE) == "update"


def test_plan_unchanged_when_value_matches(s18):
    title_existing = _mf(s18, s18.TITLE_KEY, s18.ARTICLE_TITLE)
    desc_existing = _mf(s18, s18.DESCRIPTION_KEY, s18.ARTICLE_DESCRIPTION)
    assert s18.plan_metafield(title_existing, s18.ARTICLE_TITLE) == "unchanged"
    assert s18.plan_metafield(desc_existing, s18.ARTICLE_DESCRIPTION) == "unchanged"


def test_find_metafield_respects_namespace_and_key(s18):
    metafields = [
        {"id": 9, "namespace": "custom", "key": s18.TITLE_KEY, "value": "wrong ns"},
        _mf(s18, s18.TITLE_KEY, "right one", mf_id=10),
        _mf(s18, s18.DESCRIPTION_KEY, "desc", mf_id=11),
    ]
    found = s18.find_metafield(metafields, s18.TITLE_KEY)
    assert found is not None
    assert found["id"] == 10
    assert s18.find_metafield(metafields, "no_such_key") is None


def test_idempotency_matching_values_yield_no_change(s18):
    """When both metafields already hold the proposed copy, nothing changes."""
    metafields = [
        _mf(s18, s18.TITLE_KEY, s18.ARTICLE_TITLE, mf_id=1),
        _mf(s18, s18.DESCRIPTION_KEY, s18.ARTICLE_DESCRIPTION, mf_id=2),
    ]
    title_mf = s18.find_metafield(metafields, s18.TITLE_KEY)
    desc_mf = s18.find_metafield(metafields, s18.DESCRIPTION_KEY)
    title_status = s18.plan_metafield(title_mf, s18.ARTICLE_TITLE)
    desc_status = s18.plan_metafield(desc_mf, s18.ARTICLE_DESCRIPTION)
    changed = title_status != "unchanged" or desc_status != "unchanged"
    assert not changed
