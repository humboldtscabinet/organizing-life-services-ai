"""Dashboard GSC task generation must skip internal Shopify utilities."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services import dashboard_service


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows

    def query(self, _model):
        return _FakeQuery(self._rows)


def _row(*, page, query, clicks=0, impressions=80, ctr=0.0, position=12.0, days_ago=1):
    return SimpleNamespace(
        page=page,
        query=query,
        clicks=clicks,
        impressions=impressions,
        ctr=ctr,
        position=position,
        date=datetime.utcnow() - timedelta(days=days_ago),
    )


def test_is_seo_denylist_page_covers_products_and_utility_collections():
    assert dashboard_service._is_seo_denylist_page(
        "https://organizinglifeservices.com/products/product-cc-2-7-fee"
    )
    assert dashboard_service._is_seo_denylist_page("/products/processing-fee")
    assert dashboard_service._is_seo_denylist_page(
        "https://organizinglifeservices.com/collections/all"
    )
    assert dashboard_service._is_seo_denylist_page("/collections/fees-products")
    assert not dashboard_service._is_seo_denylist_page(
        "https://organizinglifeservices.com/pages/fees-products"
    )
    assert not dashboard_service._is_seo_denylist_page("/")


def test_generate_gsc_tasks_skips_product_and_utility_collection_pages():
    rows = [
        _row(
            page="https://organizinglifeservices.com/products/product-cc-2-7-fee",
            query="credit card fee estate sale",
            impressions=120,
            clicks=0,
            ctr=0.0,
            position=10.0,
        ),
        _row(
            page="https://organizinglifeservices.com/collections/fees-products",
            query="estate sale fees",
            impressions=90,
            clicks=0,
            ctr=0.0,
            position=11.0,
        ),
        _row(
            page="https://organizinglifeservices.com/pages/estate-cleanout-services",
            query="estate cleanout tampa",
            impressions=100,
            clicks=0,
            ctr=0.0,
            position=9.0,
        ),
    ]
    db = _FakeDb(rows)
    cutoff = datetime.utcnow() - timedelta(days=7)

    tasks = dashboard_service._generate_gsc_tasks(db, cutoff)

    titles = [t["title"] for t in tasks]
    joined = " | ".join(titles)
    assert "/products/" not in joined
    assert "collections/fees-products" not in joined
    assert "collections/all" not in joined
    assert any("estate-cleanout-services" in t or "estate cleanout tampa" in t for t in titles)
