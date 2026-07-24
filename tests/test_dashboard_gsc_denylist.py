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


def test_generate_gsc_tasks_excludes_denylist_rows_from_query_stats():
    """Denylist impressions must not inflate thresholds for mixed queries."""
    rows = [
        _row(
            page="https://organizinglifeservices.com/products/product-cc-2-7-fee",
            query="tampa estate sale",
            impressions=100,
            clicks=0,
            ctr=0.0,
            position=10.0,
        ),
        _row(
            page="https://organizinglifeservices.com/pages/estate-sale-services",
            query="tampa estate sale",
            impressions=10,
            clicks=1,
            ctr=0.1,
            position=5.0,
        ),
    ]
    db = _FakeDb(rows)
    cutoff = datetime.utcnow() - timedelta(days=7)

    tasks = dashboard_service._generate_gsc_tasks(db, cutoff)

    # Without excluding denylist rows, impressions=110 would trigger Rule 1.
    assert not any("tampa estate sale" in t["title"] for t in tasks)


def test_generate_cross_channel_tasks_skips_denylist_pages():
    product = "https://organizinglifeservices.com/products/product-cc-2-7-fee"
    service = "https://organizinglifeservices.com/pages/estate-cleanout-services"

    class _DistinctQuery:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *_args, **_kwargs):
            return self

        def distinct(self):
            return self

        def all(self):
            return self._rows

    class _SumQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def scalar(self):
            return 3

    class _Db:
        def __init__(self):
            self._phase = 0

        def query(self, *_cols):
            self._phase += 1
            if self._phase <= 2:
                return _DistinctQuery([(product,), (service,)])
            return _SumQuery()

    cutoff = datetime.utcnow() - timedelta(days=7)
    tasks = dashboard_service._generate_cross_channel_tasks(_Db(), cutoff)

    titles = [t["title"] for t in tasks]
    assert all("/products/" not in t for t in titles)
    assert any("estate-cleanout-services" in t for t in titles)
