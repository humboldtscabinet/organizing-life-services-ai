"""Enqueue-time filters keep obvious junk out of the dashboard queue.

Covers the real payloads the operator mass-dismissed on 2026-08-31 and
2026-09-03 (frozen-meta rewrites worse than live copy, duplicate rows for one
URL, and a LOW-intent "near me" blog already covered by live pages), plus a
would-enqueue good CTR snippet that must still get through.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services import dashboard_service
from app.services.task_enqueue_filters import (
    RANK_HOLE_POSITION,
    copy_quality_reason,
    frozen_meta_rejection_reason,
    frozen_meta_url_key,
    keyword_already_covered,
    should_skip_low_lead_near_me,
)


def _page_payload(*, page_id, path, current_title, query, new_title, new_meta):
    return {
        "resource": "page",
        "page_id": page_id,
        "handle": path.split("/pages/", 1)[1],
        "path": path,
        "query": query,
        "current_title": current_title,
        "current_meta_description": "",
        "new_title": new_title,
        "new_meta_description": new_meta,
    }


def _article_payload(*, article_id, path, current_title, query, new_title, new_meta):
    return {
        "resource": "article",
        "article_id": article_id,
        "blog_id": 999,
        "handle": path.rsplit("/", 1)[-1],
        "path": path,
        "query": query,
        "current_title": current_title,
        "current_meta_description": "",
        "new_title": new_title,
        "new_meta_description": new_meta,
    }


# --- Frozen meta: would-NOT-enqueue (the dismissed rows) ---------------------


def test_211_230_estate_buyers_near_me_drops_city_and_service():
    """211/230 /pages/estate-sale-new-port-richey-florida (duplicate rows)."""
    payload = _page_payload(
        page_id=211,
        path="/pages/estate-sale-new-port-richey-florida",
        current_title="Estate Sales in New Port Richey, FL",
        query="estate buyers near me",
        new_title="Estate Buyers Near Me | Organizing Life Services",
        new_meta="Need help with estate buyers near me? Call OLS today.",
    )
    reason = frozen_meta_rejection_reason(payload, avg_position=11.0)
    assert reason is not None


def test_212_229_estate_clean_out_zephyrhills_drops_city():
    """212/229 /pages/estate-cleanout-services — Zephyrhills is not served."""
    payload = _page_payload(
        page_id=212,
        path="/pages/estate-cleanout-services",
        current_title="Estate Cleanout Services Tampa Bay | Same-Week Help",
        query="estate clean out in zephyrhills",
        new_title="Estate Clean Out In Zephyrhills | Organizing Life Services",
        new_meta="Need help with estate clean out in zephyrhills? Call OLS today.",
    )
    assert frozen_meta_rejection_reason(payload, avg_position=12.0) is not None


def test_229_deceased_estate_clean_up_drops_service():
    payload = _page_payload(
        page_id=229,
        path="/pages/estate-cleanout-services",
        current_title="Estate Cleanout Services Tampa Bay | Same-Week Help",
        query="deceased estate clean up",
        new_title="Deceased Estate Clean Up | Organizing Life Services",
        new_meta="Need help with deceased estate clean up? Call OLS today.",
    )
    assert frozen_meta_rejection_reason(payload, avg_position=12.0) is not None


def test_220_estate_moves_drops_service_term():
    """220 /pages/estate-liquidation — 'estate moves' is not a service term."""
    payload = _page_payload(
        page_id=220,
        path="/pages/estate-liquidation",
        current_title="Estate Liquidation Services | Tampa Bay Downsizing",
        query="estate moves",
        new_title="Estate Moves | Organizing Life Services",
        new_meta="Need help with estate moves? Call OLS today.",
    )
    assert frozen_meta_rejection_reason(payload, avg_position=13.0) is not None


def test_221_222_blog_retitled_to_query_string():
    """221/222 blog posts retitled to the raw triggering query."""
    payload = _article_payload(
        article_id=221,
        path="/blogs/news/how-to-run-an-estate-sale",
        current_title="How to Run an Estate Sale: A Complete Guide",
        query="estate liquidators near me",
        new_title="Estate Liquidators Near Me | Organizing Life Services",
        new_meta="Need help with estate liquidators near me? Call OLS today.",
    )
    assert frozen_meta_rejection_reason(payload, avg_position=10.0) is not None


def test_rank_hole_is_not_a_snippet_job():
    """On-brand copy, but page 2 ranking — a rank hole, not a CTR job."""
    payload = _page_payload(
        page_id=300,
        path="/pages/estate-sale-clearwater",
        current_title="Estate Sales in Clearwater, FL",
        query="estate sales clearwater",
        new_title="Estate Sales in Clearwater, FL",
        new_meta="Clearwater estate sales by Organizing Life Services. Call OLS today.",
    )
    reason = frozen_meta_rejection_reason(payload, avg_position=RANK_HOLE_POSITION + 1)
    assert reason is not None
    assert "rank hole" in reason


def test_query_echo_shopper_title_without_service():
    payload = _page_payload(
        page_id=301,
        path="/pages/some-page",
        current_title="",
        query="stuff near me",
        new_title="Stuff Near Me | Organizing Life Services",
        new_meta="Need help with stuff near me? Call OLS today.",
    )
    assert frozen_meta_rejection_reason(payload) is not None


def test_competitor_name_rejected():
    assert copy_quality_reason(
        "Estate Sales Tampa | OLS", "Better than MaxSold estate sales. Call OLS."
    )


def test_truncated_title_rejected():
    assert copy_quality_reason("Estate Sale Services In", "Tampa Bay estate sales.")


def test_stuffed_title_rejected():
    assert copy_quality_reason(
        "Estate Sale Estate Sale Estate Sale Tampa", "Tampa estate sales."
    )


# --- Frozen meta: would-ENQUEUE (real CTR snippet job) -----------------------


def test_good_ctr_snippet_on_city_page_enqueues():
    """Existing city page, title keeps city + estate sales, position ~5."""
    payload = _page_payload(
        page_id=400,
        path="/pages/estate-sale-new-port-richey-florida",
        current_title="Estate Sales in New Port Richey, FL",
        query="estate sales new port richey",
        new_title="Estate Sales in New Port Richey, FL",
        new_meta=(
            "New Port Richey estate sales by Organizing Life Services. "
            "Call (727) 542-6028 today."
        ),
    )
    assert frozen_meta_rejection_reason(payload, avg_position=5.0) is None


# --- Dedup by URL / handle, not by query -------------------------------------


def test_frozen_meta_url_key_ignores_copy():
    a = _page_payload(
        page_id=211,
        path="/pages/estate-sale-new-port-richey-florida",
        current_title="Estate Sales in New Port Richey, FL",
        query="estate buyers near me",
        new_title="Estate Buyers Near Me | OLS",
        new_meta="a",
    )
    b = _page_payload(
        page_id=211,
        path="/pages/estate-sale-new-port-richey-florida",
        current_title="Estate Sales in New Port Richey, FL",
        query="estate sale near me",
        new_title="Estate Sale Near Me | OLS",
        new_meta="b",
    )
    assert frozen_meta_url_key(a) == frozen_meta_url_key(b) == "page:211"


# --- Content: LOW-intent near-me blog already covered ------------------------


def test_208_low_lead_near_me_already_covered_is_skipped():
    existing = [
        "/blogs/news/estate-sales-near-me-your-ultimate-guide-to-local-finds",
        "/pages/estate-sale-companies-near-me",
    ]
    assert should_skip_low_lead_near_me("estate sales near me", "LOW", existing) is True


def test_seller_intent_high_content_still_enqueues():
    existing = ["/pages/estate-sale-companies-near-me"]
    assert (
        should_skip_low_lead_near_me("estate sale company clearwater", "HIGH", existing)
        is False
    )


def test_low_lead_near_me_not_yet_covered_still_enqueues():
    assert should_skip_low_lead_near_me("estate sales near me palm harbor", "LOW", []) is False


def test_keyword_already_covered_matches_slug_substring():
    assert keyword_already_covered(
        "estate sales near me",
        ["/blogs/news/estate-sales-near-me-your-ultimate-guide-to-local-finds"],
    )
    assert not keyword_already_covered("downsizing checklist tampa", ["/pages/contact"])


# --- Integration: generators drop rejected frozen-meta rows ------------------


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_a, **_k):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows

    def query(self, _model):
        return _FakeQuery(self._rows)


def _row(*, page, query, clicks=0, impressions=80, ctr=0.0, position=6.0):
    return SimpleNamespace(
        page=page,
        query=query,
        clicks=clicks,
        impressions=impressions,
        ctr=ctr,
        position=position,
        date=datetime.utcnow() - timedelta(days=1),
    )


def test_generate_gsc_tasks_drops_rejected_frozen_meta(monkeypatch):
    page = "https://organizinglifeservices.com/pages/estate-sale-new-port-richey-florida"
    rows = [_row(page=page, query="estate buyers near me", impressions=120, position=6.0)]

    def _bad_draft(page_url, query, **_kwargs):
        return {
            "action_kind": "shopify.apply_frozen_meta",
            "fingerprint": "shopify.apply_frozen_meta:page:211:deadbeef",
            "action_payload": _page_payload(
                page_id=211,
                path="/pages/estate-sale-new-port-richey-florida",
                current_title="Estate Sales in New Port Richey, FL",
                query=query,
                new_title="Estate Buyers Near Me | Organizing Life Services",
                new_meta="Need help with estate buyers near me? Call OLS today.",
            ),
        }

    monkeypatch.setattr(
        "app.services.frozen_meta_service.resolve_and_draft", _bad_draft
    )
    cutoff = datetime.utcnow() - timedelta(days=7)
    tasks = dashboard_service._generate_gsc_tasks(_FakeDb(rows), cutoff)
    assert not any(t.get("action_kind") == "shopify.apply_frozen_meta" for t in tasks)
    assert not any(t["category"] == "zero_click_investigation" for t in tasks)


def test_generate_gsc_tasks_keeps_good_frozen_meta(monkeypatch):
    page = "https://organizinglifeservices.com/pages/estate-sale-new-port-richey-florida"
    rows = [_row(page=page, query="estate sales new port richey", impressions=120, position=5.0)]

    def _good_draft(page_url, query, **_kwargs):
        return {
            "action_kind": "shopify.apply_frozen_meta",
            "fingerprint": "shopify.apply_frozen_meta:page:400:cafef00d",
            "action_payload": _page_payload(
                page_id=400,
                path="/pages/estate-sale-new-port-richey-florida",
                current_title="Estate Sales in New Port Richey, FL",
                query=query,
                new_title="Estate Sales in New Port Richey, FL",
                new_meta="New Port Richey estate sales by OLS. Call (727) 542-6028.",
            ),
        }

    monkeypatch.setattr(
        "app.services.frozen_meta_service.resolve_and_draft", _good_draft
    )
    cutoff = datetime.utcnow() - timedelta(days=7)
    tasks = dashboard_service._generate_gsc_tasks(_FakeDb(rows), cutoff)
    frozen = [t for t in tasks if t.get("action_kind") == "shopify.apply_frozen_meta"]
    assert frozen, "expected a good CTR frozen-meta task to enqueue"


def test_generate_gsc_tasks_dedupes_same_url(monkeypatch):
    page = "https://organizinglifeservices.com/pages/estate-sale-new-port-richey-florida"
    # Two different queries for the SAME url -> one page, one frozen-meta task.
    rows = [
        _row(page=page, query="estate sales new port richey", impressions=120, position=5.0),
        _row(page=page, query="estate sale new port richey fl", impressions=110, position=6.0),
    ]

    def _good_draft(page_url, query, **_kwargs):
        return {
            "action_kind": "shopify.apply_frozen_meta",
            "fingerprint": f"shopify.apply_frozen_meta:page:400:{abs(hash(query)) % 10**8}",
            "action_payload": _page_payload(
                page_id=400,
                path="/pages/estate-sale-new-port-richey-florida",
                current_title="Estate Sales in New Port Richey, FL",
                query=query,
                new_title="Estate Sales in New Port Richey, FL",
                new_meta="New Port Richey estate sales by OLS. Call (727) 542-6028.",
            ),
        }

    monkeypatch.setattr(
        "app.services.frozen_meta_service.resolve_and_draft", _good_draft
    )
    cutoff = datetime.utcnow() - timedelta(days=7)
    tasks = dashboard_service._generate_gsc_tasks(_FakeDb(rows), cutoff)
    frozen = [t for t in tasks if t.get("action_kind") == "shopify.apply_frozen_meta"]
    assert len(frozen) == 1, "one page must yield at most one frozen-meta task"
