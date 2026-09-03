"""Enqueue-time filters that keep obvious junk out of the dashboard queue.

These are pure, side-effect-free predicates applied at DashboardTask
*creation* time. They exist so the operator stops mass-dismissing the same
kinds of low-value rows on every weekday audit (frozen-meta rewrites that are
worse than the live copy, duplicate rows for one URL, and LOW-intent
"near me" blog tasks for keywords a live page/post already covers).

Scope guardrails (see AGENTS.md):
  * This module never touches the high-stakes gate, Apply, or the allowlisted
    ``action_kind`` values. It only decides whether a task row is worth
    creating in the first place.
  * It adds no new Apply verbs and does not change how any existing verb runs.

The two entry points are:
  * :func:`frozen_meta_rejection_reason` — should this ``shopify.apply_frozen``
    ``_meta`` draft be enqueued? Returns ``None`` to allow, or a short reason
    string to reject.
  * :func:`should_skip_low_lead_near_me` — should this ``content.generate_and``
    ``_publish`` opportunity be skipped because it is a LOW-intent "near me"
    blog for a keyword that a live page/post already covers?
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Avg GSC position at or above this is a ranking problem (page 2+), not a
# snippet/CTR job that a title/meta rewrite can fix. Frozen-meta tasks are only
# worthwhile when the page already ranks well enough for the snippet to matter.
RANK_HOLE_POSITION = 15.0

# Core OLS service phrases. Order matters only for readability. "clean out" and
# "cleanout" are treated as the same term via normalization below.
SERVICE_TERMS: tuple[str, ...] = (
    "estate sale",
    "estate liquidation",
    "estate cleanout",
    "home cleanout",
    "house cleanout",
    "cleanout",
    "liquidation",
    "downsizing",
    "downsize",
    "organizing",
    "declutter",
    "appraisal",
    "probate",
    "moving sale",
    "tag sale",
    "estate clearing",
)

# Cities / counties OLS actually serves (Tampa Bay: Pinellas, Pasco,
# Hillsborough, Hernando, Citrus). Used to detect when a rewrite drops the
# live page's geography.
CITY_TERMS: tuple[str, ...] = (
    "tampa bay",
    "tampa",
    "st petersburg",
    "saint petersburg",
    "st pete",
    "petersburg",
    "clearwater",
    "largo",
    "dunedin",
    "palm harbor",
    "safety harbor",
    "tarpon springs",
    "oldsmar",
    "seminole",
    "pinellas",
    "new port richey",
    "port richey",
    "trinity",
    "holiday",
    "hudson",
    "wesley chapel",
    "land o lakes",
    "zephyrhills",
    "dade city",
    "pasco",
    "brandon",
    "riverview",
    "plant city",
    "hillsborough",
    "brooksville",
    "spring hill",
    "hernando",
    "crystal river",
    "inverness",
    "citrus",
)

# Competitor brand names that must never appear in OLS meta copy.
COMPETITOR_TERMS: tuple[str, ...] = (
    "estatesales.net",
    "estatesale.com",
    "everything but the house",
    "ebth",
    "caring transitions",
    "maxsold",
    "max sold",
    "blue moon estate",
    "blue moon",
    "two men and a truck",
    "junk king",
    "1800 got junk",
    "1-800-got-junk",
    "college hunks",
)

# Shopper / research intent signals that make a bare query-echo title junk.
SHOPPER_TERMS: tuple[str, ...] = (
    "near me",
    "buyers",
    "buyer",
    "buy",
    "today",
    "this weekend",
    "tomorrow",
    "pictures",
    "photos",
    "hours",
    "address",
    "craigslist",
    "facebook",
)

# Trailing connector words that indicate a title was cut mid-thought.
_DANGLING_CONNECTORS: frozenset[str] = frozenset(
    {
        "in",
        "the",
        "and",
        "for",
        "with",
        "to",
        "a",
        "of",
        "at",
        "on",
        "or",
        "near",
        "your",
        "our",
        "&",
        "-",
        "|",
    }
)

_BRAND_SUFFIXES: tuple[str, ...] = (
    "organizing life services",
    "ols",
)


def _norm(text: str | None) -> str:
    """Lowercase, drop punctuation, collapse whitespace, unify clean out."""
    value = (text or "").lower()
    value = value.replace("clean out", "cleanout").replace("clean-out", "cleanout")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _service_terms_in(text: str) -> set[str]:
    normalized = _norm(text)
    return {term for term in (_norm(t) for t in SERVICE_TERMS) if term and term in normalized}


def _city_terms_in(text: str) -> set[str]:
    normalized = _norm(text)
    return {term for term in (_norm(t) for t in CITY_TERMS) if term and term in normalized}


def _strip_brand(title: str) -> str:
    """Return the meaningful part of a title with the OLS brand suffix removed."""
    normalized = _norm(title)
    for brand in _BRAND_SUFFIXES:
        if normalized.endswith(brand):
            normalized = normalized[: -len(brand)].strip()
    return normalized


def title_is_query_echo(new_title: str, query: str) -> bool:
    """True when the title is essentially the raw GSC query.

    Only flags shopper/research or non-service query echoes; a query that
    itself carries a real OLS service term (e.g. "estate sales new port
    richey") is a legitimate on-brand title and is left alone.
    """
    stripped = _strip_brand(new_title)
    q = _norm(query)
    if not q or not stripped:
        return False
    if stripped != q:
        return False
    # Title == query. Junk only when the query is shopper/research intent or
    # carries no core service term of its own.
    if _service_terms_in(q) and not _has_shopper_intent(q):
        return False
    return True


def _has_shopper_intent(text: str) -> bool:
    normalized = _norm(text)
    return any(_norm(term) in normalized for term in SHOPPER_TERMS)


def drops_city_or_service(new_title: str, live_title: str) -> str | None:
    """Reject when the rewrite drops the live page's city or core service term.

    Returns a reason string, or ``None`` when the rewrite keeps the live
    page's geography and service focus. When there is no live title to compare
    against, this check abstains (returns ``None``).
    """
    if not (live_title or "").strip():
        return None

    live_services = _service_terms_in(live_title)
    new_services = _service_terms_in(new_title)
    if live_services and not (live_services & new_services):
        return "proposed title drops the live page's core service term"

    live_cities = _city_terms_in(live_title)
    new_cities = _city_terms_in(new_title)
    if live_cities and not (live_cities & new_cities):
        return "proposed title drops the live page's city/geography"

    return None


def is_rank_hole(avg_position: float | None) -> bool:
    """True when the page ranks too low for a snippet rewrite to matter."""
    if avg_position is None:
        return False
    try:
        return float(avg_position) >= RANK_HOLE_POSITION
    except (TypeError, ValueError):
        return False


def _looks_truncated(text: str) -> bool:
    normalized = _norm(text)
    if not normalized:
        return False
    return normalized.split()[-1] in _DANGLING_CONNECTORS


def _looks_stuffed(text: str) -> bool:
    words = [w for w in _norm(text).split() if len(w) > 3]
    for word in set(words):
        if words.count(word) >= 3:
            return True
    return False


def _has_competitor(text: str) -> bool:
    normalized = _norm(text)
    return any(_norm(term) in normalized for term in COMPETITOR_TERMS)


def copy_quality_reason(new_title: str, new_meta: str) -> str | None:
    """Reject truncated / keyword-stuffed / competitor-mentioning copy."""
    blob_title = new_title or ""
    both = f"{new_title or ''} {new_meta or ''}"
    if _has_competitor(both):
        return "proposed copy mentions a competitor brand"
    if _looks_truncated(blob_title):
        return "proposed title looks truncated"
    if _looks_stuffed(blob_title):
        return "proposed title looks keyword-stuffed"
    return None


def frozen_meta_rejection_reason(
    payload: dict[str, Any] | None,
    *,
    avg_position: float | None = None,
) -> str | None:
    """Return a reason to *not* enqueue this frozen-meta draft, or ``None``.

    ``payload`` is the ``action_payload`` produced by
    ``frozen_meta_service.resolve_and_draft`` (contains ``new_title``,
    ``new_meta_description``, ``current_title``, ``query``). Deduplication by
    URL/handle is handled separately by :func:`frozen_meta_url_key`.
    """
    if not isinstance(payload, dict):
        return "missing frozen payload"

    new_title = str(payload.get("new_title") or "").strip()
    new_meta = str(payload.get("new_meta_description") or "").strip()
    live_title = str(payload.get("current_title") or "").strip()
    query = str(payload.get("query") or "").strip()

    if not new_title or not new_meta:
        return "missing proposed title/meta"

    if is_rank_hole(avg_position):
        return (
            f"page is a rank hole (avg position {round(float(avg_position), 1)}"
            f" >= {RANK_HOLE_POSITION}), not a snippet/CTR job"
        )

    drop_reason = drops_city_or_service(new_title, live_title)
    if drop_reason:
        return drop_reason

    if title_is_query_echo(new_title, query):
        return "proposed title is essentially the raw GSC query"

    quality_reason = copy_quality_reason(new_title, new_meta)
    if quality_reason:
        return quality_reason

    return None


def frozen_meta_url_key(payload: dict[str, Any] | None) -> str | None:
    """Stable per-URL/handle key so one page yields at most one frozen task.

    Unlike the copy-hash fingerprint, this ignores the proposed title/meta so
    two different rewrites for the same URL collapse to one task.
    """
    if not isinstance(payload, dict):
        return None
    resource = payload.get("resource")
    if resource == "page":
        rid = payload.get("page_id") or payload.get("handle")
        if rid:
            return f"page:{rid}"
    if resource == "article":
        rid = payload.get("article_id") or payload.get("handle")
        if rid:
            return f"article:{rid}"
    path = payload.get("path")
    if path:
        return f"path:{path}"
    return None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def keyword_already_covered(query: str, existing_urls: Iterable[str]) -> bool:
    """True when a live page/post URL already covers this keyword.

    Matches when the slugified query is a substring of an existing URL slug, or
    when every significant word of the query appears in an existing URL slug.
    """
    q_slug = _slug(query)
    if not q_slug:
        return False
    q_words = [w for w in q_slug.split("-") if len(w) > 2]
    for url in existing_urls or []:
        u_slug = _slug(url)
        if not u_slug:
            continue
        if q_slug in u_slug:
            return True
        u_words = set(u_slug.split("-"))
        if q_words and all(w in u_words for w in q_words):
            return True
    return False


def should_skip_low_lead_near_me(
    query: str,
    lead_tier: str | None,
    existing_urls: Iterable[str],
) -> bool:
    """Skip LOW-lead shopper "near me" blog tasks already covered by a live URL.

    Seller-intent HIGH/MEDIUM opportunities are never skipped here.
    """
    if (lead_tier or "").upper() != "LOW":
        return False
    if "near me" not in (query or "").lower():
        return False
    return keyword_already_covered(query, existing_urls)
