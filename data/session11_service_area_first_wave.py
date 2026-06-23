"""Session 11: first-wave service-area rollout for OLS local SEO.

This script prepares the first set of permanent service-area pages from
`data/service_area_plan.py`:

- Pinellas County hub
- Pasco County hub
- Tampa / Hillsborough hub
- Palm Harbor
- Clearwater
- New Port Richey
- Tarpon Springs permanent page

Safety:
- Default mode is dry-run.
- Live writes require `--apply` plus the data mutation guard env:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

- Existing page bodies are snapshotted before live body writes.
- Existing pages are not destructively rewritten. They receive an idempotent
  marked section: `SERVICE-AREA-FIRST-WAVE-V1:{handle}`.
- Legacy event pages are reported, not redirected/noindexed automatically.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from _mutation_guard import (
        CONFIRM_ENV,
        CONFIRM_PHRASE,
        activate as activate_data_mutation_guard,
    )
except ModuleNotFoundError:  # pragma: no cover - supports module-style imports.
    from data._mutation_guard import (
        CONFIRM_ENV,
        CONFIRM_PHRASE,
        activate as activate_data_mutation_guard,
    )

activate_data_mutation_guard()

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.service_area_plan import FIRST_WAVE_HANDLES  # noqa: E402

OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SITE = "https://organizinglifeservices.com"
ORG_NAME = "Organizing Life Services"
PHONE = "(727) 542-6028"
PHONE_E164 = "+17275426028"
CONTACT_PATH = "/pages/contact-us"
MARKER_PREFIX = "SERVICE-AREA-FIRST-WAVE-V1"


@dataclass(frozen=True)
class FirstWaveTarget:
    handle: str
    page_title: str
    seo_title: str
    meta_description: str
    location_label: str
    county_label: str
    page_kind: str
    action: str
    intro: str
    local_details: tuple[str, ...]
    nearby_links: tuple[tuple[str, str], ...]
    faq_pairs: tuple[tuple[str, str], ...]
    source_handle: str | None = None


FIRST_WAVE_TARGETS: tuple[FirstWaveTarget, ...] = (
    FirstWaveTarget(
        handle="estate-sale-pinellas-county",
        page_title="Estate Sales in Pinellas County, FL",
        seo_title="Estate Sales Pinellas County, FL | Full-Service OLS",
        meta_description=(
            "Estate sales in Pinellas County, FL by OLS. Estate sale planning, "
            "appraisals, downsizing, and cleanouts. Call (727) 542-6028."
        ),
        location_label="Pinellas County",
        county_label="Pinellas County",
        page_kind="county_hub",
        action="create",
        intro=(
            "Organizing Life Services helps Pinellas County families handle estate "
            "sales, downsizing, appraisals, liquidation, and cleanouts with one "
            "coordinated local team."
        ),
        local_details=(
            "Pinellas homes often need careful sale planning around condo rules, "
            "HOA access, parking limits, waterfront-property logistics, and tight "
            "real-estate timelines.",
            "This hub connects Palm Harbor, Clearwater, Tarpon Springs, Dunedin, "
            "Largo, St. Petersburg, Safety Harbor, Seminole, and Pinellas Park "
            "service pages.",
        ),
        nearby_links=(
            ("estate-sale-palm-harbor-pinellas-county", "Palm Harbor estate sales"),
            ("estate-sale-clearwater-florida", "Clearwater estate sales"),
            ("estate-sale-tarpon-springs-florida", "Tarpon Springs estate sales"),
            ("estate-sale-dunedin-florida", "Dunedin estate sales"),
            ("estate-sale-largo-florida", "Largo estate sales"),
            ("estate-sale-st-petersburg-florida", "St. Petersburg estate sales"),
        ),
        faq_pairs=(
            (
                "Do you serve all of Pinellas County?",
                "Yes. OLS serves north, central, and south Pinellas communities, "
                "including Palm Harbor, Clearwater, Dunedin, Largo, St. Petersburg, "
                "Tarpon Springs, Safety Harbor, Seminole, and Pinellas Park.",
            ),
            (
                "Can you handle condo or HOA estate sales?",
                "Yes. We plan around community access rules, parking, elevators, "
                "security gates, and sale-day buyer flow before publishing the sale.",
            ),
            (
                "Do you also handle cleanouts after a Pinellas estate sale?",
                "Yes. Estate cleanout, donation coordination, and broom-clean turnover "
                "can be included when the family or realtor needs the property cleared.",
            ),
        ),
    ),
    FirstWaveTarget(
        handle="estate-sale-pasco-county",
        page_title="Estate Sales in Pasco County, FL",
        seo_title="Estate Sales Pasco County, FL | Appraisals & Cleanouts",
        meta_description=(
            "Estate sales in Pasco County, FL by OLS. Full-service estate sale "
            "planning, appraisals, downsizing, and cleanouts. Call (727) 542-6028."
        ),
        location_label="Pasco County",
        county_label="Pasco County",
        page_kind="county_hub",
        action="refresh",
        intro=(
            "OLS supports Pasco County estate sale clients with pricing, staging, "
            "marketing, sale-day staffing, downsizing support, appraisals, and "
            "post-sale cleanout coordination."
        ),
        local_details=(
            "Pasco projects often involve family homes, retirement communities, "
            "gated neighborhoods, and move-out deadlines that need a calm plan.",
            "This hub should stay focused on Pasco. Hernando may be mentioned as "
            "secondary coverage, but Pasco should be the headline service area.",
        ),
        nearby_links=(
            ("estate-sale-new-port-richey-florida", "New Port Richey estate sales"),
            ("estate-sale-wesley-chapel-florida", "Wesley Chapel estate sales"),
            ("estate-sale-trinity-florida", "Trinity estate sales"),
            ("estate-sale-holiday-florida", "Holiday estate sales"),
            ("estate-sale-hudson-florida", "Hudson estate sales"),
        ),
        faq_pairs=(
            (
                "Which Pasco communities do you serve?",
                "OLS serves New Port Richey, Wesley Chapel, Trinity, Holiday, "
                "Hudson, Port Richey, Land O' Lakes, and nearby Pasco communities.",
            ),
            (
                "Can you help if the estate is small?",
                "Yes. If a public estate sale is not the right fit, we can discuss "
                "downsizing support, cleanout options, or appraisal services.",
            ),
            (
                "Do you coordinate cleanout after the sale?",
                "Yes. We can help with donation pickup, hauling, and cleanout so the "
                "property is ready for the family, realtor, or closing timeline.",
            ),
        ),
    ),
    FirstWaveTarget(
        handle="estate-sale-tampa-hillsborough-county",
        page_title="Estate Sales in Tampa & Hillsborough County, FL",
        seo_title="Estate Sales Tampa & Hillsborough County | OLS",
        meta_description=(
            "Estate sales in Tampa and Hillsborough County by OLS. Planning, "
            "pricing, appraisals, downsizing, and cleanouts. Call (727) 542-6028."
        ),
        location_label="Tampa and Hillsborough County",
        county_label="Hillsborough County",
        page_kind="county_hub",
        action="refresh",
        intro=(
            "OLS helps Tampa and Hillsborough County families plan estate sales, "
            "downsizing moves, appraisals, liquidation, and cleanouts without "
            "turning a stressful transition into a DIY project."
        ),
        local_details=(
            "Hillsborough work often includes larger homes, gated communities, "
            "busy streets, and sale-day parking plans that need to be handled early.",
            "This hub should support Tampa plus future Brandon, Riverview, "
            "Carrollwood, Lutz, Westchase, Plant City, and Valrico pages.",
        ),
        nearby_links=(
            ("estate-sale-brandon-florida", "Brandon estate sales"),
            ("estate-sale-riverview-florida", "Riverview estate sales"),
            ("estate-sale-carrollwood-florida", "Carrollwood estate sales"),
            ("estate-sale-lutz-florida", "Lutz estate sales"),
            ("estate-sale-westchase-florida", "Westchase estate sales"),
        ),
        faq_pairs=(
            (
                "Do you serve Tampa and surrounding Hillsborough neighborhoods?",
                "Yes. OLS serves Tampa plus surrounding Hillsborough communities "
                "including Brandon, Riverview, Carrollwood, Lutz, Westchase, Plant "
                "City, and Valrico when the project fits our service area.",
            ),
            (
                "Can you help with estate sale planning before a home listing?",
                "Yes. We can coordinate sale timing, cleanout, and appraisals around "
                "a realtor's listing or closing schedule.",
            ),
            (
                "Do you handle appraisals in Hillsborough County?",
                "Yes. Personal property appraisal support is available for estate, "
                "probate, downsizing, insurance, and planning needs.",
            ),
        ),
    ),
    FirstWaveTarget(
        handle="estate-sale-palm-harbor-pinellas-county",
        page_title="Estate Sales in Palm Harbor, FL",
        seo_title="Estate Sales Palm Harbor, FL | Pinellas County OLS",
        meta_description=(
            "Estate sales in Palm Harbor, FL by OLS. Full-service sale planning, "
            "appraisals, downsizing, and cleanouts. Call (727) 542-6028."
        ),
        location_label="Palm Harbor",
        county_label="Pinellas County",
        page_kind="city",
        action="refresh",
        intro=(
            "OLS helps Palm Harbor families organize estate sales, downsizing moves, "
            "personal property appraisals, and estate cleanouts across north Pinellas."
        ),
        local_details=(
            "Palm Harbor projects often involve 55+ communities, villas, waterfront "
            "homes, and inherited family properties where timing and access matter.",
            "Nearby service areas include Tarpon Springs, Dunedin, Clearwater, "
            "Safety Harbor, and the broader Pinellas County hub.",
        ),
        nearby_links=(
            ("estate-sale-pinellas-county", "Pinellas County estate sales"),
            ("estate-sale-tarpon-springs-florida", "Tarpon Springs estate sales"),
            ("estate-sale-dunedin-florida", "Dunedin estate sales"),
            ("estate-sale-clearwater-florida", "Clearwater estate sales"),
        ),
        faq_pairs=(
            (
                "Do you handle estate sales in Palm Harbor retirement communities?",
                "Yes. We can plan around community access, parking rules, elevators, "
                "and buyer flow before the sale is publicly listed.",
            ),
            (
                "Can you help before a Palm Harbor home goes on the market?",
                "Yes. We can coordinate estate sale timing, cleanout, and donation "
                "pickup so the home is ready for listing or closing.",
            ),
            (
                "Do you serve nearby north Pinellas cities?",
                "Yes. OLS also serves Tarpon Springs, Dunedin, Clearwater, Safety "
                "Harbor, and surrounding Pinellas communities.",
            ),
        ),
    ),
    FirstWaveTarget(
        handle="estate-sale-clearwater-florida",
        page_title="Estate Sales in Clearwater, FL",
        seo_title="Estate Sales Clearwater, FL | Pinellas County OLS",
        meta_description=(
            "Estate sales in Clearwater, FL by OLS. Pricing, staging, appraisals, "
            "downsizing, and estate cleanouts. Call (727) 542-6028."
        ),
        location_label="Clearwater",
        county_label="Pinellas County",
        page_kind="city",
        action="refresh",
        intro=(
            "OLS provides Clearwater estate sale planning, appraisal support, "
            "downsizing help, and cleanout coordination for families across central "
            "Pinellas County."
        ),
        local_details=(
            "Clearwater projects may involve condos, beach-area access, older family "
            "homes, and parking constraints that need thoughtful sale-day planning.",
            "Nearby service areas include Palm Harbor, Dunedin, Largo, Safety Harbor, "
            "and the Pinellas County hub.",
        ),
        nearby_links=(
            ("estate-sale-pinellas-county", "Pinellas County estate sales"),
            ("estate-sale-palm-harbor-pinellas-county", "Palm Harbor estate sales"),
            ("estate-sale-dunedin-florida", "Dunedin estate sales"),
            ("estate-sale-largo-florida", "Largo estate sales"),
        ),
        faq_pairs=(
            (
                "Can you run estate sales in Clearwater condos?",
                "Yes. We review access, elevator use, parking, and association rules "
                "before deciding the best sale format.",
            ),
            (
                "Do you provide Clearwater estate cleanout services?",
                "Yes. Cleanout, donation coordination, and post-sale hauling can be "
                "planned with the estate sale.",
            ),
            (
                "Do you help with appraisals in Clearwater?",
                "Yes. OLS provides personal property appraisal support for estate, "
                "probate, downsizing, and insurance needs.",
            ),
        ),
    ),
    FirstWaveTarget(
        handle="estate-sale-new-port-richey-florida",
        page_title="Estate Sales in New Port Richey, FL",
        seo_title="Estate Sales New Port Richey, FL | Pasco County OLS",
        meta_description=(
            "Estate sales in New Port Richey, FL by OLS. Sale planning, pricing, "
            "appraisals, downsizing, and cleanouts. Call (727) 542-6028."
        ),
        location_label="New Port Richey",
        county_label="Pasco County",
        page_kind="city",
        action="refresh",
        intro=(
            "OLS helps New Port Richey families plan estate sales, downsizing moves, "
            "personal property appraisals, and cleanouts throughout west Pasco."
        ),
        local_details=(
            "New Port Richey estate projects often involve retirement communities, "
            "family homes, waterfront neighborhoods, and inherited properties.",
            "Nearby service areas include Trinity, Holiday, Port Richey, Hudson, "
            "Wesley Chapel, and the Pasco County hub.",
        ),
        nearby_links=(
            ("estate-sale-pasco-county", "Pasco County estate sales"),
            ("estate-sale-wesley-chapel-florida", "Wesley Chapel estate sales"),
            ("estate-sale-trinity-florida", "Trinity estate sales"),
            ("estate-sale-holiday-florida", "Holiday estate sales"),
        ),
        faq_pairs=(
            (
                "Do you serve west Pasco homes outside New Port Richey?",
                "Yes. OLS also serves Port Richey, Holiday, Trinity, Hudson, and "
                "nearby Pasco communities when the project fits our service area.",
            ),
            (
                "Can you help if the family is out of town?",
                "Yes. We can coordinate consultation, planning, sale preparation, "
                "and post-sale cleanout with remote family decision-makers.",
            ),
            (
                "Do you handle cleanout after a New Port Richey estate sale?",
                "Yes. Donation pickup and cleanout can be planned as part of the "
                "sale process.",
            ),
        ),
    ),
    FirstWaveTarget(
        handle="estate-sale-tarpon-springs-florida",
        page_title="Estate Sales in Tarpon Springs, FL",
        seo_title="Estate Sales Tarpon Springs, FL | Pinellas County OLS",
        meta_description=(
            "Estate sales in Tarpon Springs, FL by OLS. Sale planning, appraisals, "
            "downsizing, and estate cleanouts. Call (727) 542-6028."
        ),
        location_label="Tarpon Springs",
        county_label="Pinellas County",
        page_kind="city",
        action="create",
        intro=(
            "OLS helps Tarpon Springs families plan estate sales, appraisals, "
            "downsizing moves, liquidation, and cleanouts with a permanent service "
            "page separate from one-time event-sale pages."
        ),
        local_details=(
            "Tarpon Springs projects may involve waterfront homes, historic homes, "
            "condos, villas, and neighborhoods near the Sponge Docks or Lake Tarpon.",
            "This page should become the permanent Tarpon Springs service page while "
            "legacy event pages remain separate.",
        ),
        nearby_links=(
            ("estate-sale-pinellas-county", "Pinellas County estate sales"),
            ("estate-sale-palm-harbor-pinellas-county", "Palm Harbor estate sales"),
            ("estate-sale-dunedin-florida", "Dunedin estate sales"),
            ("estate-sale-clearwater-florida", "Clearwater estate sales"),
        ),
        faq_pairs=(
            (
                "Why create a permanent Tarpon Springs page?",
                "The current Tarpon Springs search demand should point to a durable "
                "service page, not a past sale event page tied to one neighborhood.",
            ),
            (
                "Do you serve Tarpon Springs neighborhoods near the Sponge Docks?",
                "Yes. OLS serves Tarpon Springs and nearby north Pinellas communities "
                "when estate sale or cleanout logistics are a good fit.",
            ),
            (
                "Can you combine appraisal and estate sale services?",
                "Yes. Personal property appraisal support can be paired with estate "
                "sale planning, downsizing, or cleanout needs.",
            ),
        ),
        source_handle="tarpon-springs-estate-sale-in-woodfield",
    ),
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def marker_for(handle: str) -> str:
    return f"{MARKER_PREFIX}:{handle}"


def tel_link() -> str:
    return f'<a href="tel:{PHONE_E164}">{PHONE}</a>'


def service_links() -> str:
    return (
        '<ul>'
        '<li><a href="/pages/estate-sale-planning">Estate sale planning</a></li>'
        '<li><a href="/pages/personal-property-appraisal">Personal property appraisals</a></li>'
        '<li><a href="/pages/downsizing-moving-sales">Downsizing and moving sales</a></li>'
        '<li><a href="/pages/estate-cleanout-services">Estate cleanout services</a></li>'
        '</ul>'
    )


def build_schema(target: FirstWaveTarget) -> str:
    area_served: list[dict[str, str]] = [
        {"@type": "AdministrativeArea", "name": target.county_label},
    ]
    if target.page_kind == "city":
        area_served.insert(0, {"@type": "City", "name": target.location_label})

    data = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": f"{target.location_label} estate sale services",
        "serviceType": [
            "Estate sales",
            "Estate liquidation",
            "Personal property appraisal",
            "Downsizing",
            "Estate cleanout",
        ],
        "provider": {
            "@type": "LocalBusiness",
            "name": ORG_NAME,
            "telephone": PHONE_E164,
            "url": SITE,
        },
        "areaServed": area_served,
        "url": f"{SITE}/pages/{target.handle}",
    }
    return (
        '<script type="application/ld+json">'
        + json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        + "</script>"
    )


def build_body_block(target: FirstWaveTarget) -> str:
    marker = marker_for(target.handle)
    local_detail_html = "\n".join(f"<p>{detail}</p>" for detail in target.local_details)
    nearby_html = "\n".join(
        f'<li><a href="/pages/{handle}">{label}</a></li>'
        for handle, label in target.nearby_links
    )
    faq_html = "\n".join(
        f"<h3>{question}</h3>\n<p>{answer}</p>"
        for question, answer in target.faq_pairs
    )
    schema = build_schema(target)

    return f"""<!-- {marker} -->
<section class="ols-service-area-first-wave">
<p>{target.intro}</p>

<h2>Estate Sale Services in {target.location_label}</h2>
<p>Our work in {target.location_label} can include estate sale planning, sorting, pricing, staging, marketing, sale-day staffing, personal property appraisal support, downsizing help, and estate cleanout coordination. The goal is simple: make the transition manageable for the family while presenting the home and contents clearly to qualified Tampa Bay buyers.</p>

<h2>Local Planning Notes</h2>
{local_detail_html}

<h2>Services Available in {target.location_label}</h2>
{service_links()}

<h2>Nearby Service Areas</h2>
<p>OLS primarily serves Pinellas, Pasco, and Hillsborough counties. These nearby pages help families compare the closest service area for their property:</p>
<ul>
{nearby_html}
</ul>

<h2>{target.location_label} Estate Sale FAQs</h2>
{faq_html}

<h2>Schedule a Free Consultation</h2>
<p>Call {tel_link()} or use our <a href="{CONTACT_PATH}">contact form</a> to talk through the property, timeline, and best next step. OLS can help determine whether a public estate sale, appraisal, downsizing plan, cleanout, or a mix of services is the right fit.</p>

{schema}
</section>
<!-- /{marker} -->"""


def validate_target(target: FirstWaveTarget) -> None:
    if target.handle not in FIRST_WAVE_HANDLES:
        raise ValueError(f"{target.handle} is not in service_area_plan.FIRST_WAVE_HANDLES")
    if len(target.seo_title) > 65:
        raise ValueError(f"{target.handle} SEO title too long: {len(target.seo_title)}")
    if len(target.meta_description) > 160:
        raise ValueError(
            f"{target.handle} meta description too long: {len(target.meta_description)}"
        )
    if "<h1" in build_body_block(target).lower():
        raise ValueError(f"{target.handle} body block must not emit an H1")


def validate_targets(targets: tuple[FirstWaveTarget, ...] = FIRST_WAVE_TARGETS) -> None:
    handles = [target.handle for target in targets]
    if len(handles) != len(set(handles)):
        raise ValueError("Duplicate first-wave target handles")
    if set(handles) != set(FIRST_WAVE_HANDLES):
        raise ValueError(
            "Script target handles do not match data.service_area_plan.FIRST_WAVE_HANDLES"
        )
    for target in targets:
        validate_target(target)


def _retry(fn: Any, *args: Any, **kwargs: Any) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(7):
        try:
            resp = fn(*args, **kwargs)
            if getattr(resp, "status_code", None) == 429:
                wait = float(resp.headers.get("Retry-After", 2**attempt))
                print(f"  [429] sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            return resp
        except (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.RemoteProtocolError,
            httpx.ConnectError,
        ) as exc:
            last = exc
            wait = 2**attempt
            print(f"  [retry] {type(exc).__name__}: {exc}; sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
    if last:
        raise last
    raise RuntimeError("retries exhausted")


def shopify_context() -> tuple[dict[str, str], str]:
    store = os.getenv("SHOPIFY_STORE")
    client_id = os.getenv("SHOPIFY_CLIENT_ID")
    client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")
    api_version = os.getenv("SHOPIFY_API_VERSION", "2024-10")

    if not all([store, client_id, client_secret]):
        sys.exit("Missing SHOPIFY_STORE / SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET")

    resp = _retry(
        httpx.post,
        f"https://{store}.myshopify.com/admin/oauth/access_token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    base_url = f"https://{store}.myshopify.com/admin/api/{api_version}"
    return headers, base_url


def get_json(url: str, headers: dict[str, str]) -> dict:
    resp = _retry(httpx.get, url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def get_pages(headers: dict[str, str], base_url: str) -> dict[str, dict]:
    pages: list[dict] = []
    url = f"{base_url}/pages.json?limit=250"
    while url:
        resp = _retry(httpx.get, url, headers=headers, timeout=60)
        resp.raise_for_status()
        pages.extend(resp.json().get("pages", []))
        link = resp.headers.get("link", "")
        next_url = ""
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip()[1:-1]
        url = next_url
    return {page["handle"]: page for page in pages}


def list_global_metafields(headers: dict[str, str], base_url: str, page_id: int) -> dict[str, dict]:
    data = get_json(f"{base_url}/pages/{page_id}/metafields.json", headers)
    return {
        metafield["key"]: metafield
        for metafield in data.get("metafields", [])
        if metafield.get("namespace") == "global"
    }


def plan_target(target: FirstWaveTarget, existing_page: dict | None, metafields: dict[str, dict]) -> dict:
    block = build_body_block(target)
    marker = marker_for(target.handle)
    page_exists = existing_page is not None
    current_body = (existing_page or {}).get("body_html") or ""
    marker_exists = marker in current_body
    body_after = block if not page_exists else current_body.rstrip() + "\n\n" + block
    body_status = "unchanged" if marker_exists else "create_body" if not page_exists else "append_block"

    current_title = (existing_page or {}).get("title") or ""
    title_status = "unchanged" if current_title == target.page_title else "update_page_title"
    if not page_exists:
        title_status = "create_page_title"

    meta_results = []
    for key, desired in (
        ("title_tag", target.seo_title),
        ("description_tag", target.meta_description),
    ):
        existing = metafields.get(key)
        current = existing.get("value") if existing else None
        if current == desired:
            status = "unchanged"
        elif existing:
            status = "update"
        else:
            status = "create"
        meta_results.append({
            "key": key,
            "status": status,
            "before_len": len(current or ""),
            "after_len": len(desired),
        })

    needs_page_write = not page_exists or body_status != "unchanged" or title_status != "unchanged"
    needs_meta_write = any(item["status"] != "unchanged" for item in meta_results)

    return {
        "handle": target.handle,
        "page_id": existing_page.get("id") if existing_page else None,
        "page_exists": page_exists,
        "action": target.action,
        "page_kind": target.page_kind,
        "body_status": body_status,
        "title_status": title_status,
        "needs_page_write": needs_page_write,
        "needs_meta_write": needs_meta_write,
        "metafields": meta_results,
        "body_before_chars": len(current_body),
        "body_after_chars": len(body_after),
        "body_added_chars": 0 if marker_exists else len(body_after) - len(current_body),
        "source_handle": target.source_handle,
        "legacy_note": (
            f"Review legacy source page {target.source_handle}; this script does not redirect/noindex it."
            if target.source_handle
            else None
        ),
        "url": f"{SITE}/pages/{target.handle}",
    }


def write_snapshot(timestamp: str, target: FirstWaveTarget, page: dict, metafields: dict[str, dict]) -> str:
    safe_handle = re.sub(r"[^a-z0-9-]+", "-", target.handle.lower()).strip("-")
    path = OUT_DIR / f"service_area_snapshot_pre_session11_{timestamp}_{safe_handle}.json"
    payload = {
        "target": asdict(target),
        "page": {
            "id": page.get("id"),
            "handle": page.get("handle"),
            "title": page.get("title"),
            "body_html": page.get("body_html"),
            "published_at": page.get("published_at"),
            "updated_at": page.get("updated_at"),
        },
        "global_metafields": {
            key: {
                "id": value.get("id"),
                "key": value.get("key"),
                "namespace": value.get("namespace"),
                "value": value.get("value"),
                "type": value.get("type"),
            }
            for key, value in metafields.items()
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return str(path.relative_to(PROJECT_ROOT))


def put_page(
    headers: dict[str, str],
    base_url: str,
    page_id: int,
    *,
    title: str,
    body_html: str,
) -> dict:
    resp = _retry(
        httpx.put,
        f"{base_url}/pages/{page_id}.json",
        headers=headers,
        json={"page": {"id": page_id, "title": title, "body_html": body_html}},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["page"]


def create_page(headers: dict[str, str], base_url: str, target: FirstWaveTarget) -> dict:
    resp = _retry(
        httpx.post,
        f"{base_url}/pages.json",
        headers=headers,
        json={
            "page": {
                "title": target.page_title,
                "handle": target.handle,
                "body_html": build_body_block(target),
                "published": True,
            }
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["page"]


def upsert_global_metafield(
    headers: dict[str, str],
    base_url: str,
    page_id: int,
    existing: dict | None,
    key: str,
    value: str,
) -> dict:
    if existing and existing.get("value") == value:
        return {"key": key, "status": "unchanged", "id": existing.get("id")}

    if existing:
        resp = _retry(
            httpx.put,
            f"{base_url}/metafields/{existing['id']}.json",
            headers=headers,
            json={
                "metafield": {
                    "id": existing["id"],
                    "value": value,
                    "type": "single_line_text_field",
                }
            },
            timeout=60,
        )
        action = "updated"
    else:
        resp = _retry(
            httpx.post,
            f"{base_url}/pages/{page_id}/metafields.json",
            headers=headers,
            json={
                "metafield": {
                    "namespace": "global",
                    "key": key,
                    "value": value,
                    "type": "single_line_text_field",
                }
            },
            timeout=60,
        )
        action = "created"
    resp.raise_for_status()
    return {"key": key, "status": action, "id": resp.json()["metafield"]["id"]}


def apply_target(
    headers: dict[str, str],
    base_url: str,
    target: FirstWaveTarget,
    existing_page: dict | None,
    metafields: dict[str, dict],
    timestamp: str,
) -> dict:
    result = plan_target(target, existing_page, metafields)
    snapshots: list[str] = []

    if existing_page and (result["needs_page_write"] or result["needs_meta_write"]):
        snapshots.append(write_snapshot(timestamp, target, existing_page, metafields))

    if not existing_page:
        page = create_page(headers, base_url, target)
        result["page_id"] = page["id"]
        result["page_write_status"] = "created"
        metafields = {}
    else:
        body = existing_page.get("body_html") or ""
        marker = marker_for(target.handle)
        if marker in body and existing_page.get("title") == target.page_title:
            page = existing_page
            result["page_write_status"] = "unchanged"
        else:
            new_body = body if marker in body else body.rstrip() + "\n\n" + build_body_block(target)
            page = put_page(
                headers,
                base_url,
                existing_page["id"],
                title=target.page_title,
                body_html=new_body,
            )
            result["page_write_status"] = "updated"

    meta_writes = []
    for key, value in (
        ("title_tag", target.seo_title),
        ("description_tag", target.meta_description),
    ):
        meta_writes.append(
            upsert_global_metafield(
                headers,
                base_url,
                page["id"],
                metafields.get(key),
                key,
                value,
            )
        )
        time.sleep(0.4)

    result["metafield_writes"] = meta_writes
    result["snapshot_paths"] = snapshots
    return result


def write_report(report: dict[str, Any]) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"session11_service_area_first_wave_{timestamp}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str))
    return path


def require_apply_confirmation() -> None:
    allow_flag = os.getenv("OLS_ALLOW_DATA_MUTATION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }
    confirm = os.getenv(CONFIRM_ENV, "").strip()
    if not (allow_flag and confirm == CONFIRM_PHRASE):
        sys.exit(
            "Live apply requires OLS_ALLOW_DATA_MUTATION=1 and "
            f"{CONFIRM_ENV}={CONFIRM_PHRASE}. Run dry-run first and review the report."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform live Shopify writes. Default is dry-run.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    validate_targets()

    dry_run = not args.apply
    if args.apply:
        require_apply_confirmation()

    print("Session 11 first-wave service-area rollout" + (" (DRY RUN)" if dry_run else ""))

    headers, base_url = shopify_context()
    pages = get_pages(headers, base_url)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    target_results: list[dict] = []
    for target in FIRST_WAVE_TARGETS:
        existing_page = pages.get(target.handle)
        metafields = (
            list_global_metafields(headers, base_url, existing_page["id"])
            if existing_page
            else {}
        )
        if dry_run:
            result = plan_target(target, existing_page, metafields)
        else:
            result = apply_target(headers, base_url, target, existing_page, metafields, timestamp)
        if target.source_handle:
            result["source_page_exists"] = target.source_handle in pages
        target_results.append(result)

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": target_results,
        "summary": {
            "target_count": len(target_results),
            "would_or_did_page_writes": sum(1 for r in target_results if r["needs_page_write"]),
            "would_or_did_meta_writes": sum(1 for r in target_results if r["needs_meta_write"]),
            "new_pages": [
                r["handle"] for r in target_results if not r["page_exists"]
            ],
            "existing_pages": [
                r["handle"] for r in target_results if r["page_exists"]
            ],
            "legacy_followups": [
                r["legacy_note"] for r in target_results if r.get("legacy_note")
            ],
        },
    }

    report_path = write_report(report)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"\nReport written to {report_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
