"""Post-deploy measurement baseline for OLS SEO work.

This read-only runner answers the practical questions that should follow a
site SEO change:

1. Can GA4 conversions be trusted as lead/business intent?
2. Do the changed pages still render the intended title/meta/H1/noindex state?
3. Which GSC opportunities should become the next content targets?
4. Is GBP/local-SEO readiness aligned while API access is pending?
5. What should the weekly operator report highlight?

Outputs:
  - data/audit_output/post_deploy_measurement_baseline_<timestamp>.json
  - docs/seo-audits/YYYY-MM-DD-post-deploy-measurement-baseline.md

No live writes are performed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services import seo_crawler  # noqa: E402
from app.services.lead_relevance import score_lead_relevance  # noqa: E402

ENV_PATH = PROJECT_ROOT / ".env"
CREDS_PATH = PROJECT_ROOT / "credentials" / "google-service-account.json"
OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
DOCS_DIR = PROJECT_ROOT / "docs" / "seo-audits"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

HOST = "organizinglifeservices.com"
SITE_URL_DEFAULT = f"https://{HOST}/"

GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
GA4_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

PASSIVE_EVENT_NAMES = {
    "page_view",
    "session_start",
    "first_visit",
    "user_engagement",
    "scroll",
    "view_search_results",
}
LEAD_EVENT_PATTERNS = (
    "form_submit",
    "generate_lead",
    "lead",
    "phone",
    "call",
    "tel",
    "email",
    "contact_click",
    "submit_lead",
)

CHANGED_URLS = [
    {
        "label": "Homepage",
        "url": SITE_URL_DEFAULT,
        "expected_title": "Estate Sale Organizers Tampa Bay | Appraisals & Downsizing",
        "expected_meta": (
            "Tampa Bay estate sale organizers for estate sales, appraisals, "
            "downsizing, and cleanouts across Pinellas, Pasco, Hillsborough, "
            "Hernando, and Citrus."
        ),
        "expected_h1_count": 1,
        "allowed_issues": {"low_alt_text_coverage"},
    },
    {
        "label": "Personal Property Appraisal",
        "url": f"{SITE_URL_DEFAULT}pages/personal-property-appraisal",
        "expected_title": "Personal Property Appraisers Tampa Bay | Estate Appraisals",
        "expected_meta": (
            "Need Tampa personal property appraisers? OLS provides estate sale, "
            "probate, insurance, and downsizing appraisals across Tampa Bay. "
            "Call (727) 542-6028."
        ),
        "expected_h1_count": 1,
        "allowed_issues": set(),
    },
    {
        "label": "Contact",
        "url": f"{SITE_URL_DEFAULT}pages/contact-us",
        "expected_h1_count": 1,
        "allowed_issues": set(),
    },
    {
        "label": "About",
        "url": f"{SITE_URL_DEFAULT}pages/about-us",
        "expected_h1_count": 1,
        "allowed_issues": set(),
    },
    {
        "label": "Testimonials",
        "url": f"{SITE_URL_DEFAULT}pages/testimonials",
        "expected_h1_count": 1,
        "allowed_issues": set(),
    },
    {
        "label": "Senior Services",
        "url": f"{SITE_URL_DEFAULT}pages/senior-services",
        "expected_h1_count": 1,
        "allowed_issues": set(),
    },
    {
        "label": "All Collections",
        "url": f"{SITE_URL_DEFAULT}collections/all",
        "expected_robots_contains": "noindex",
        "allowed_issues": {"noindex", "missing_meta_description", "multiple_h1"},
    },
    {
        "label": "Fees Products",
        "url": f"{SITE_URL_DEFAULT}collections/fees-products",
        "expected_robots_contains": "noindex",
        "allowed_issues": {"noindex", "missing_meta_description", "multiple_h1"},
    },
]


def load_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def ensure_local_credentials() -> str:
    configured = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    configured_path = Path(configured) if configured else None
    if configured_path and configured_path.exists():
        return str(configured_path)
    if CREDS_PATH.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CREDS_PATH)
        return str(CREDS_PATH)
    raise FileNotFoundError(
        "Google service-account credentials not found. Expected "
        "GOOGLE_APPLICATION_CREDENTIALS or credentials/google-service-account.json."
    )


def site_url() -> str:
    value = os.getenv("GSC_SITE_URL", SITE_URL_DEFAULT).strip() or SITE_URL_DEFAULT
    return value.rstrip("/") + "/"


def pct_change(curr: float, prev: float) -> float | None:
    if prev in (0, None):
        return None
    return (curr - prev) / prev * 100.0


def fmt_int(value: Any) -> str:
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.1f}%"


def fmt_ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def is_lead_event(event_name: str) -> bool:
    name = event_name.lower()
    return any(pattern in name for pattern in LEAD_EVENT_PATTERNS)


def is_passive_event(event_name: str) -> bool:
    name = event_name.lower()
    if name in PASSIVE_EVENT_NAMES:
        return True
    return "page_load" in name or "contact_page_load" in name


def classify_event_name(event_name: str) -> str:
    if is_lead_event(event_name):
        return "lead_intent"
    if is_passive_event(event_name):
        return "passive_or_pageview"
    return "other"


def assess_conversion_tracking(
    *,
    sessions: float,
    key_events: float,
    event_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    lead_key_events = sum(
        row["key_events"] for row in event_rows if classify_event_name(row["event_name"]) == "lead_intent"
    )
    passive_key_events = sum(
        row["key_events"]
        for row in event_rows
        if classify_event_name(row["event_name"]) == "passive_or_pageview"
    )
    ratio = key_events / sessions if sessions else None
    issues: list[dict[str, str]] = []

    if key_events <= 0:
        issues.append({
            "severity": "high",
            "issue": "GA4 reports zero key events/conversions in the audit window.",
        })
    if passive_key_events > 0:
        issues.append({
            "severity": "high",
            "issue": "Passive events such as page views or page-load events are counted as key events.",
        })
    if lead_key_events <= 0:
        issues.append({
            "severity": "high",
            "issue": "No lead-intent key events were detected.",
        })
    if ratio is not None and ratio > 0.5:
        issues.append({
            "severity": "medium",
            "issue": "Key events per session is unusually high for real lead tracking.",
        })

    status = "pass"
    if any(i["severity"] == "high" for i in issues):
        status = "fail"
    elif issues:
        status = "warning"

    return {
        "status": status,
        "sessions": sessions,
        "key_events": key_events,
        "key_events_per_session": ratio,
        "lead_key_events": lead_key_events,
        "passive_key_events": passive_key_events,
        "issues": issues,
    }


def _ga4_types():
    from google.analytics.data_v1beta.types import (  # noqa: PLC0415
        DateRange,
        Dimension,
        Filter,
        FilterExpression,
        Metric,
        RunReportRequest,
    )

    return DateRange, Dimension, Filter, FilterExpression, Metric, RunReportRequest


def _ga4_client(credentials_path: str):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient  # noqa: PLC0415

    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=GA4_SCOPES
    )
    return BetaAnalyticsDataClient(credentials=creds)


def _run_ga4_report(
    client: Any,
    property_id: str,
    *,
    start_date: str,
    end_date: str,
    dimensions: list[str],
    metrics: list[str],
    dimension_filter: Any = None,
    limit: int = 10000,
) -> list[dict[str, Any]]:
    DateRange, Dimension, _Filter, _FilterExpression, Metric, RunReportRequest = _ga4_types()
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        limit=limit,
    )
    if dimension_filter is not None:
        request.dimension_filter = dimension_filter
    response = client.run_report(request)

    rows = []
    for row in response.rows:
        item: dict[str, Any] = {}
        for i, header in enumerate(response.dimension_headers):
            item[header.name] = row.dimension_values[i].value
        for i, header in enumerate(response.metric_headers):
            raw = row.metric_values[i].value
            try:
                item[header.name] = float(raw)
            except ValueError:
                item[header.name] = raw
        rows.append(item)
    return rows


def _ga4_string_filter(field_name: str, value: str):
    _DateRange, _Dimension, Filter, FilterExpression, _Metric, _RunReportRequest = _ga4_types()
    return FilterExpression(
        filter=Filter(
            field_name=field_name,
            string_filter=Filter.StringFilter(value=value, case_sensitive=False),
        )
    )


def _choose_key_event_metric(client: Any, property_id: str, start_date: str, end_date: str) -> str:
    for metric in ("keyEvents", "conversions"):
        try:
            _run_ga4_report(
                client,
                property_id,
                start_date=start_date,
                end_date=end_date,
                dimensions=["eventName"],
                metrics=[metric],
                limit=1,
            )
            return metric
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError("Neither GA4 keyEvents nor conversions metric is available.")


def run_ga4_conversion_audit(credentials_path: str) -> dict[str, Any]:
    property_id = os.getenv("GA4_PROPERTY_ID", "").strip()
    if not property_id:
        return {"available": False, "reason": "GA4_PROPERTY_ID is not configured."}

    client = _ga4_client(credentials_path)
    today = datetime.now(timezone.utc).date()
    end = today - timedelta(days=1)
    start = end - timedelta(days=27)
    prior_end = start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=27)

    metric = _choose_key_event_metric(client, property_id, start.isoformat(), end.isoformat())

    current_totals = _run_ga4_report(
        client,
        property_id,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        dimensions=[],
        metrics=["sessions", "activeUsers", metric],
        limit=1,
    )[0]
    prior_totals = _run_ga4_report(
        client,
        property_id,
        start_date=prior_start.isoformat(),
        end_date=prior_end.isoformat(),
        dimensions=[],
        metrics=["sessions", "activeUsers", metric],
        limit=1,
    )[0]

    event_rows_raw = _run_ga4_report(
        client,
        property_id,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        dimensions=["eventName"],
        metrics=[metric, "eventCount"],
        limit=100,
    )
    event_rows = sorted(
        [
            {
                "event_name": row["eventName"],
                "key_events": row.get(metric, 0.0),
                "event_count": row.get("eventCount", 0.0),
                "classification": classify_event_name(row["eventName"]),
            }
            for row in event_rows_raw
        ],
        key=lambda r: (r["key_events"], r["event_count"]),
        reverse=True,
    )

    organic_filter = _ga4_string_filter("sessionDefaultChannelGroup", "Organic Search")
    organic_landing_rows = _run_ga4_report(
        client,
        property_id,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        dimensions=["landingPagePlusQueryString", "eventName"],
        metrics=[metric, "sessions", "eventCount"],
        dimension_filter=organic_filter,
        limit=100,
    )
    organic_landing_rows = sorted(
        [
            {
                "landing_page": row["landingPagePlusQueryString"],
                "event_name": row["eventName"],
                "key_events": row.get(metric, 0.0),
                "sessions": row.get("sessions", 0.0),
                "event_count": row.get("eventCount", 0.0),
                "classification": classify_event_name(row["eventName"]),
            }
            for row in organic_landing_rows
        ],
        key=lambda r: (r["key_events"], r["sessions"]),
        reverse=True,
    )

    channel_rows = _run_ga4_report(
        client,
        property_id,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        dimensions=["sessionDefaultChannelGroup", "eventName"],
        metrics=[metric, "sessions", "eventCount"],
        limit=100,
    )
    channel_rows = sorted(
        [
            {
                "channel": row["sessionDefaultChannelGroup"],
                "event_name": row["eventName"],
                "key_events": row.get(metric, 0.0),
                "sessions": row.get("sessions", 0.0),
                "event_count": row.get("eventCount", 0.0),
                "classification": classify_event_name(row["eventName"]),
            }
            for row in channel_rows
        ],
        key=lambda r: (r["key_events"], r["sessions"]),
        reverse=True,
    )

    assessment = assess_conversion_tracking(
        sessions=current_totals.get("sessions", 0.0),
        key_events=current_totals.get(metric, 0.0),
        event_rows=event_rows,
    )

    return {
        "available": True,
        "property_id": property_id,
        "key_event_metric": metric,
        "windows": {
            "current": {"start": start.isoformat(), "end": end.isoformat()},
            "prior": {"start": prior_start.isoformat(), "end": prior_end.isoformat()},
        },
        "totals_current": current_totals,
        "totals_prior": prior_totals,
        "deltas": {
            "sessions_delta_pct": pct_change(
                current_totals.get("sessions", 0.0), prior_totals.get("sessions", 0.0)
            ),
            "key_events_delta_pct": pct_change(
                current_totals.get(metric, 0.0), prior_totals.get(metric, 0.0)
            ),
        },
        "event_rows": event_rows[:30],
        "organic_landing_rows": organic_landing_rows[:30],
        "channel_rows": channel_rows[:30],
        "assessment": assessment,
    }


def gsc_client(credentials_path: str):
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=GSC_SCOPES
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def gsc_query(
    service: Any,
    *,
    start_date: str,
    end_date: str,
    dimensions: list[str],
    row_limit: int = 25000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start_row = 0
    while True:
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions,
            "rowLimit": row_limit,
            "startRow": start_row,
        }
        response = service.searchanalytics().query(siteUrl=site_url(), body=body).execute()
        batch = response.get("rows", [])
        rows.extend(batch)
        if len(batch) < row_limit:
            break
        start_row += row_limit
    return rows


def content_action(query: str, page: str) -> str:
    query_lc = query.lower()
    path = urlparse(page).path.rstrip("/")
    path_lc = path.lower()
    if path in {"", "/"}:
        return "Expand homepage service-intent copy or refine homepage internal links"
    if "personal-property-appraisal" in path:
        return "Expand appraisal page into a stronger service landing page"
    if any(term in query_lc for term in ("cleanout", "clean out", "downsizing")):
        return "Expand matching service page with FAQs, process, and CTA"
    if looks_legacy_event_page(page):
        return "Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed"
    if any(
        term in query_lc
        or term.replace(" ", "-") in path_lc
        for term in (
            "tampa",
            "clearwater",
            "dunedin",
            "palm harbor",
            "tarpon springs",
            "st petersburg",
            "largo",
            "pasco",
            "hernando",
            "citrus",
            "pinellas",
        )
    ):
        return "Create or improve a service-area page/section"
    if path.startswith("/blogs/") or query_lc.startswith(("what ", "how ", "why ")):
        return "Create or refresh an educational guide"
    return "Review existing page intent and title/meta alignment"


def looks_legacy_event_page(page: str) -> bool:
    path = urlparse(page).path.lower()
    if not path.startswith("/pages/"):
        return False
    protected_service_paths = (
        "personal-property-appraisal",
        "estate-cleanout-services",
        "estate-sale-planning",
        "estate-liquidation",
        "senior-services",
        "downsizing",
        "contact-us",
        "about-us",
        "testimonials",
        "faqs",
    )
    if any(token in path for token in protected_service_paths):
        return False
    legacy_terms = (
        "appointment-only",
        "coming-up",
        "part-one",
        "part-two",
        "huge-do-not-miss",
        "vintage-",
        "-drive-",
        "-lane-",
        "-street-",
        "-sale-in-",
    )
    return bool(re.search(r"/pages/\d", path) or any(term in path for term in legacy_terms))


def run_content_target_audit(credentials_path: str) -> dict[str, Any]:
    service = gsc_client(credentials_path)
    today = datetime.now(timezone.utc).date()
    end = today - timedelta(days=3)
    start = end - timedelta(days=27)

    rows = gsc_query(
        service,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        dimensions=["query", "page"],
    )

    targets: list[dict[str, Any]] = []
    for row in rows:
        query, page = row["keys"]
        impressions = float(row.get("impressions", 0))
        clicks = float(row.get("clicks", 0))
        ctr = float(row.get("ctr", 0))
        position = float(row.get("position", 0))
        if impressions < 30 or position > 30:
            continue
        if not (clicks <= 2 or (5 <= position <= 20 and ctr < 0.03)):
            continue
        lead = score_lead_relevance(query, page=page)
        if lead.tier == "LOW":
            continue
        potential_ctr = 0.08 if position > 10 else 0.05
        click_gap = max((potential_ctr - ctr) * impressions, impressions * 0.015)
        business_score = click_gap * (0.5 + lead.score / 100)
        targets.append({
            "query": query,
            "page": page,
            "impressions": int(impressions),
            "clicks": int(clicks),
            "ctr": ctr,
            "position": round(position, 1),
            "lead_score": lead.score,
            "lead_tier": lead.tier,
            "lead_relevance_reasons": list(lead.reasons),
            "estimated_click_gap": round(click_gap, 1),
            "business_score": round(business_score, 1),
            "recommended_action": content_action(query, page),
        })

    targets.sort(key=lambda item: item["business_score"], reverse=True)
    return {
        "available": True,
        "windows": {"current": {"start": start.isoformat(), "end": end.isoformat()}},
        "targets": targets[:25],
    }


def verify_changed_urls() -> dict[str, Any]:
    pages = []
    for target in CHANGED_URLS:
        info = seo_crawler.audit_page(target["url"])
        checks: list[dict[str, Any]] = []

        def add_check(name: str, passed: bool, detail: str = "") -> None:
            checks.append({"check": name, "passed": passed, "detail": detail})

        if expected := target.get("expected_title"):
            add_check("title", info.get("title") == expected, info.get("title", ""))
        if expected := target.get("expected_meta"):
            add_check(
                "meta_description",
                info.get("meta_description") == expected,
                info.get("meta_description", ""),
            )
        if "expected_h1_count" in target:
            add_check(
                "h1_count",
                info.get("h1_count") == target["expected_h1_count"],
                str(info.get("h1_count")),
            )
        if expected := target.get("expected_robots_contains"):
            robots = (info.get("robots") or "").lower()
            add_check("robots", expected in robots, info.get("robots", ""))
        add_check("http_ok", bool(info.get("ok")), str(info.get("status") or info.get("error", "")))
        add_check("canonical_present", bool(info.get("canonical")), info.get("canonical", ""))

        allowed = set(target.get("allowed_issues", set()))
        unexpected_issues = [
            issue for issue in info.get("issues", []) if issue not in allowed
        ]
        add_check(
            "unexpected_issues",
            not unexpected_issues,
            ", ".join(unexpected_issues) if unexpected_issues else "none",
        )

        pages.append({
            "label": target["label"],
            "url": target["url"],
            "status": "pass" if all(c["passed"] for c in checks) else "warning",
            "title_len": info.get("title_len"),
            "meta_description_len": info.get("meta_description_len"),
            "h1_count": info.get("h1_count"),
            "robots": info.get("robots", ""),
            "issues": info.get("issues", []),
            "checks": checks,
        })

    return {
        "status": "pass" if all(p["status"] == "pass" for p in pages) else "warning",
        "pages": pages,
    }


def _extract_json_ld_objects(soup: BeautifulSoup) -> list[Any]:
    out = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            out.append(json.loads(script.string or ""))
        except (TypeError, json.JSONDecodeError):
            continue
    return out


def _walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)


def _find_local_business(json_ld: list[Any]) -> dict[str, Any] | None:
    for item in json_ld:
        for node in _walk_json(item):
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if "LocalBusiness" in types:
                return node
    return None


def run_gbp_readiness(credentials_path: str, *, skip_api: bool = False) -> dict[str, Any]:
    homepage = requests.get(SITE_URL_DEFAULT, timeout=30, headers={"User-Agent": seo_crawler.UA_BROWSER})
    contact = requests.get(
        f"{SITE_URL_DEFAULT}pages/contact-us",
        timeout=30,
        headers={"User-Agent": seo_crawler.UA_BROWSER},
    )
    homepage.raise_for_status()
    contact.raise_for_status()

    soup = BeautifulSoup(homepage.content, "lxml")
    contact_soup = BeautifulSoup(contact.content, "lxml")
    local_business = _find_local_business(_extract_json_ld_objects(soup)) or {}
    address = local_business.get("address") or {}
    contact_text = contact_soup.get_text(" ", strip=True)

    checks = [
        {
            "check": "LocalBusiness schema present",
            "passed": bool(local_business),
            "detail": local_business.get("name", ""),
        },
        {
            "check": "No public streetAddress in schema",
            "passed": "streetAddress" not in address,
            "detail": "streetAddress absent" if "streetAddress" not in address else "streetAddress present",
        },
        {
            "check": "Schema keeps region/country",
            "passed": address.get("addressRegion") == "FL" and address.get("addressCountry") == "US",
            "detail": f"{address.get('addressRegion', '')}/{address.get('addressCountry', '')}",
        },
        {
            "check": "Schema has service area",
            "passed": bool(local_business.get("areaServed")),
            "detail": f"{len(local_business.get('areaServed') or [])} area entries",
        },
        {
            "check": "Schema has phone",
            "passed": bool(local_business.get("telephone")),
            "detail": local_business.get("telephone", ""),
        },
        {
            "check": "Contact page labels mailing address",
            "passed": "mailing address" in contact_text.lower() and "PMB" in contact_text,
            "detail": "mailing address label and PMB present" if "PMB" in contact_text else "PMB missing",
        },
    ]

    api_status: dict[str, Any] = {
        "attempted": False,
        "status": "skipped",
        "reason": "skip_api requested" if skip_api else "not attempted",
    }
    if not skip_api and os.getenv("GBP_LOCATION_ID"):
        try:
            from app.services.gbp_service import discover_gbp_accounts  # noqa: PLC0415

            accounts = discover_gbp_accounts()
            api_status = {
                "attempted": True,
                "status": "ok",
                "account_count": len(accounts),
            }
        except Exception as exc:  # noqa: BLE001
            api_status = {
                "attempted": True,
                "status": "blocked_or_unavailable",
                "reason": str(exc).splitlines()[0][:240],
            }

    return {
        "status": "pass" if all(c["passed"] for c in checks) else "warning",
        "checks": checks,
        "api_status": api_status,
    }


def run_gtm_audit() -> dict[str, Any]:
    if not (os.getenv("GTM_ACCOUNT_ID") and os.getenv("GTM_CONTAINER_ID")):
        return {"available": False, "reason": "GTM_ACCOUNT_ID/GTM_CONTAINER_ID not configured."}
    try:
        from app.services.gtm_service import get_container_overview  # noqa: PLC0415

        overview = get_container_overview()
        if not overview.get("available"):
            return overview
        audit = overview.get("audit", {})
        return {
            "available": True,
            "tag_count": len(overview.get("tags", [])),
            "trigger_count": len(overview.get("triggers", [])),
            "variable_count": len(overview.get("variables", [])),
            "flagged": audit.get("flagged", 0),
            "findings": audit.get("findings", [])[:15],
        }
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "reason": str(exc).splitlines()[0][:240]}


def render_md(report: dict[str, Any]) -> str:
    ga4 = report["ga4_conversion_tracking"]
    seo = report["post_deploy_seo_verification"]
    content = report["content_targets"]
    gbp = report["gbp_readiness"]
    gtm = report["gtm_audit"]

    lines: list[str] = []
    add = lines.append
    add("# Post-Deploy Measurement Baseline - organizinglifeservices.com")
    add(f"_Generated {report['generated_at']}_")
    add("")
    add("## Overall Read")
    if ga4.get("available") and ga4["assessment"]["status"] == "fail":
        add("**Status: Pass with SEO warnings, fail on conversion-tracking trust.**")
        add("")
        add(
            "The live SEO changes are rendering, but GA4 is currently counting "
            "passive/page-load behavior as key events. Do not treat the current "
            "conversion total as a business KPI until GA4 key events are cleaned up."
        )
    else:
        add("**Status: Pass with warnings.**")
    add("")

    add("## 1. GA4 Conversion Tracking")
    if not ga4.get("available"):
        add(f"> GA4 unavailable: {ga4.get('reason')}")
    else:
        metric = ga4["key_event_metric"]
        assessment = ga4["assessment"]
        add(f"**Window:** `{ga4['windows']['current']['start']} -> {ga4['windows']['current']['end']}`")
        add("")
        add("| Metric | Prior | Current | Delta |")
        add("|---|---:|---:|---:|")
        add(
            f"| Sessions | {fmt_int(ga4['totals_prior'].get('sessions', 0))} | "
            f"{fmt_int(ga4['totals_current'].get('sessions', 0))} | "
            f"{fmt_pct(ga4['deltas'].get('sessions_delta_pct'))} |"
        )
        add(
            f"| {metric} | {fmt_int(ga4['totals_prior'].get(metric, 0))} | "
            f"{fmt_int(ga4['totals_current'].get(metric, 0))} | "
            f"{fmt_pct(ga4['deltas'].get('key_events_delta_pct'))} |"
        )
        add(
            f"| Key events/session | - | {fmt_ratio(assessment['key_events_per_session'])} | - |"
        )
        add("")
        add("**Trust assessment:** `" + assessment["status"] + "`")
        for issue in assessment.get("issues", []):
            add(f"- **{issue['severity'].upper()}**: {issue['issue']}")
        add("")
        add("Top key-event rows:")
        add("| Event | Class | Key events | Event count |")
        add("|---|---|---:|---:|")
        for row in ga4["event_rows"][:12]:
            add(
                f"| `{row['event_name']}` | {row['classification']} | "
                f"{fmt_int(row['key_events'])} | {fmt_int(row['event_count'])} |"
            )
        add("")
        add("Top organic landing-page key-event rows:")
        add("| Landing page | Event | Class | Key events | Sessions |")
        add("|---|---|---|---:|---:|")
        for row in ga4["organic_landing_rows"][:12]:
            add(
                f"| `{row['landing_page']}` | `{row['event_name']}` | "
                f"{row['classification']} | {fmt_int(row['key_events'])} | "
                f"{fmt_int(row['sessions'])} |"
            )
        add("")

    add("## 2. Post-Deploy Live SEO Verification")
    add(f"**Status:** `{seo['status']}`")
    add("")
    add("| Page | Status | Title len | Meta len | H1s | Robots | Issues |")
    add("|---|---|---:|---:|---:|---|---|")
    for page in seo["pages"]:
        add(
            f"| {page['label']} | {page['status']} | "
            f"{page.get('title_len') or ''} | {page.get('meta_description_len') or ''} | "
            f"{page.get('h1_count') or ''} | `{page.get('robots') or ''}` | "
            f"{', '.join(page.get('issues') or []) or 'none'} |"
        )
    add("")

    add("## 3. Next Content Targets")
    add(f"**GSC window:** `{content['windows']['current']['start']} -> {content['windows']['current']['end']}`")
    add("")
    add("| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |")
    add("|---:|---|---|---:|---:|---:|---|---|")
    for idx, target in enumerate(content.get("targets", [])[:15], start=1):
        page_path = urlparse(target["page"]).path or "/"
        add(
            f"| {idx} | `{target['query']}` | `{page_path}` | "
            f"{target['impressions']} | {target['clicks']} | {target['position']} | "
            f"{target['lead_tier']} ({target['lead_score']}) | "
            f"{target['recommended_action']} |"
        )
    if not content.get("targets"):
        add("_No high/medium lead-relevance targets matched the current thresholds._")
    add("")

    add("## 4. GBP Readiness")
    add(f"**On-site readiness:** `{gbp['status']}`")
    add("")
    add("| Check | Status | Detail |")
    add("|---|---|---|")
    for check in gbp["checks"]:
        add(
            f"| {check['check']} | {'PASS' if check['passed'] else 'WARN'} | "
            f"{check.get('detail', '')} |"
        )
    api = gbp.get("api_status", {})
    add("")
    add(
        f"**GBP API:** `{api.get('status')}`"
        + (f" - {api.get('reason')}" if api.get("reason") else "")
    )
    add("")

    add("## 5. Ongoing Reporting")
    add("- This report is generated by `data/post_deploy_measurement_baseline.py`.")
    add("- Weekly automation now runs both the deep SEO audit and this measurement baseline.")
    if gtm.get("available"):
        add(
            f"- GTM audit available: {gtm.get('tag_count', 0)} tags, "
            f"{gtm.get('trigger_count', 0)} triggers, {gtm.get('flagged', 0)} flagged findings."
        )
    else:
        add(f"- GTM audit unavailable: {gtm.get('reason')}")
    add("")

    add("## Remediation Checklist")
    add("1. In GA4 Admin, unmark `page_view` as a key event.")
    add("2. Stop counting `ads_conversion_Contact_Page_load_https_1` as a conversion; a contact-page view is not a lead.")
    add("3. Keep or create true lead key events: form submit, phone click, email click, and contact CTA click.")
    add("4. After the GA4 change, rerun this report and use lead-intent key events as the business KPI.")
    add("5. Expand the highest-priority content targets only after the tracking baseline is clean.")
    add("")
    add(f"Raw JSON: `{report['raw_json_path']}`")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-gbp-api", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    load_env()
    credentials_path = ensure_local_credentials()

    generated_at = datetime.now(timezone.utc)
    timestamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    raw_path = OUT_DIR / f"post_deploy_measurement_baseline_{timestamp}.json"
    doc_path = DOCS_DIR / f"{generated_at.date().isoformat()}-post-deploy-measurement-baseline.md"

    report: dict[str, Any] = {
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "site_url": site_url(),
        "ga4_conversion_tracking": run_ga4_conversion_audit(credentials_path),
        "post_deploy_seo_verification": verify_changed_urls(),
        "content_targets": run_content_target_audit(credentials_path),
        "gbp_readiness": run_gbp_readiness(credentials_path, skip_api=args.skip_gbp_api),
        "gtm_audit": run_gtm_audit(),
        "raw_json_path": str(raw_path.relative_to(PROJECT_ROOT)),
    }

    raw_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str))
    if not args.json_only:
        doc_path.write_text(render_md(report))
        report["markdown_path"] = str(doc_path.relative_to(PROJECT_ROOT))
        raw_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str))

    print(json.dumps({
        "status": "ok",
        "raw_json": str(raw_path.relative_to(PROJECT_ROOT)),
        "markdown": None if args.json_only else str(doc_path.relative_to(PROJECT_ROOT)),
        "ga4_tracking_status": report["ga4_conversion_tracking"].get("assessment", {}).get("status"),
        "seo_verification_status": report["post_deploy_seo_verification"]["status"],
        "content_targets": len(report["content_targets"].get("targets", [])),
        "gbp_status": report["gbp_readiness"]["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
