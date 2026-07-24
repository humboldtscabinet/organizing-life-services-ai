"""Tests for SEO denylist filtering in GSC keyword task generation."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.dashboard_service import (
    _generate_gsc_tasks,
    _is_seo_denylisted_page,
)


def test_products_paths_are_denylisted():
    assert _is_seo_denylisted_page(
        "https://organizinglifeservices.com/products/processing-fee"
    )
    assert _is_seo_denylisted_page("/products/product-cc-2-7-fee")
    assert _is_seo_denylisted_page("https://organizinglifeservices.com/products")


def test_actionable_pages_are_not_denylisted():
    assert not _is_seo_denylisted_page(
        "https://organizinglifeservices.com/pages/estate-cleanout-services"
    )
    assert not _is_seo_denylisted_page("https://organizinglifeservices.com/")
    assert not _is_seo_denylisted_page(None)
    assert not _is_seo_denylisted_page("")


def test_utility_collections_are_denylisted():
    assert _is_seo_denylisted_page(
        "https://organizinglifeservices.com/collections/all"
    )
    assert _is_seo_denylisted_page(
        "https://organizinglifeservices.com/collections/fees-products"
    )


def _gsc_row(*, query, page, impressions, clicks=0, ctr=0.01, position=12.0):
    return SimpleNamespace(
        query=query,
        page=page,
        impressions=impressions,
        clicks=clicks,
        ctr=ctr,
        position=position,
    )


def _mock_db(records):
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = records
    return db


def test_rule1_ignores_product_impressions_when_threshold_only_met_via_denylist():
    """
    A query with mostly /products/* traffic plus a thin actionable page must
    not pass Rule 1 using denylisted impressions.
    """
    cutoff = datetime.utcnow()
    records = [
        _gsc_row(
            query="estate sale organizers",
            page="https://organizinglifeservices.com/products/processing-fee",
            impressions=80,
            clicks=1,
            ctr=0.01,
            position=10.0,
        ),
        _gsc_row(
            query="estate sale organizers",
            page="https://organizinglifeservices.com/pages/fees-products",
            impressions=10,
            clicks=0,
            ctr=0.0,
            position=14.0,
        ),
    ]

    tasks = _generate_gsc_tasks(_mock_db(records), cutoff)

    assert not any(
        t["category"] == "keyword_optimization" and "estate sale organizers" in t["title"]
        for t in tasks
    )


def test_rule1_uses_only_actionable_page_metrics():
    """Actionable-page traffic alone can still create a Rule 1 task."""
    cutoff = datetime.utcnow()
    records = [
        _gsc_row(
            query="estate sale company palm harbor",
            page="https://organizinglifeservices.com/products/processing-fee",
            impressions=200,
            clicks=0,
            ctr=0.0,
            position=5.0,
        ),
        _gsc_row(
            query="estate sale company palm harbor",
            page="https://organizinglifeservices.com/pages/estate-sale-palm-harbor-pinellas-county",
            impressions=60,
            clicks=1,
            ctr=0.01,
            position=9.0,
        ),
    ]

    tasks = _generate_gsc_tasks(_mock_db(records), cutoff)
    rule1 = [
        t for t in tasks
        if t["category"] == "keyword_optimization"
        and "estate sale company palm harbor" in t["title"]
    ]

    assert len(rule1) == 1
    assert "60 impressions" in rule1[0]["description"]
    assert "200" not in rule1[0]["description"]


def test_rule2_skips_query_only_seen_on_products():
    """Queries that only appear on denylisted pages must not spawn Rule 2 tasks."""
    cutoff = datetime.utcnow()
    records = [
        _gsc_row(
            query="processing fee estate sale",
            page="https://organizinglifeservices.com/products/processing-fee",
            impressions=40,
            clicks=0,
            ctr=0.0,
            position=12.0,
        ),
    ]

    tasks = _generate_gsc_tasks(_mock_db(records), cutoff)

    assert not any(t["category"] == "content_ranking" for t in tasks)


def test_rule3_skips_denylisted_zero_click_pages():
    cutoff = datetime.utcnow()
    records = [
        _gsc_row(
            query="processing fee",
            page="https://organizinglifeservices.com/products/processing-fee",
            impressions=100,
            clicks=0,
            ctr=0.0,
            position=8.0,
        ),
    ]

    tasks = _generate_gsc_tasks(_mock_db(records), cutoff)

    assert not any(t["category"] == "zero_click_investigation" for t in tasks)
