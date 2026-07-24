"""Session 12: homepage CTR refinement for estate sale organizers queries.

Scope
-----
Homepage ``/`` SEO title/description are theme-controlled via the existing
``HOMEPAGE-SEO-META-V1`` block in ``layout/theme.liquid`` (Session 10).
This script replaces that copy with stronger CTR text for organizer intent
and adds a light above-fold/internal-link reinforcement for organizer +
service-area pages.

Does NOT touch Shopify products or product SEO fields.

Safety
------
- Default mode is dry-run.
- Live writes require ``--apply`` plus mutation confirmation:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

- Snapshots theme assets before live writes.
- Idempotent once the new title/description and intlinks marker are present.

Usage
-----
    set -a && source .env && set +a
    .venv/bin/python data/session12_homepage_organizers_ctr.py

    OLS_ALLOW_DATA_MUTATION=1 \\
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \\
    .venv/bin/python data/session12_homepage_organizers_ctr.py --apply
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from _mutation_guard import activate as activate_data_mutation_guard
except ModuleNotFoundError:  # pragma: no cover
    from data._mutation_guard import activate as activate_data_mutation_guard

activate_data_mutation_guard()

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HOST = "organizinglifeservices.com"
ORG_URL = f"https://{HOST}/"

HOMEPAGE_META_MARKER = "HOMEPAGE-SEO-META-V1"
INTLINKS_MARKER = "SEO-INTLINKS-ORGANIZERS-V1"

# Keep title ≤60 and description ~120–160 for SERP CTR.
HOMEPAGE_TITLE = "Estate Sale Organizers Tampa Bay | Call OLS Today"
HOMEPAGE_DESCRIPTION = (
    "Need estate sale organizers in Tampa Bay? OLS runs estate sales, "
    "appraisals, and downsizing across Pinellas to Citrus. Call (727) 542-6028."
)

LEGACY_TITLES = (
    "Estate Sale Organizers Tampa Bay | Appraisals & Downsizing",
)
LEGACY_DESCRIPTIONS = (
    (
        "Tampa Bay estate sale organizers for estate sales, appraisals, "
        "downsizing, and cleanouts across Pinellas, Pasco, Hillsborough, "
        "Hernando, and Citrus."
    ),
)

INTLINKS_BLOCK = f"""    {{%- if template.name == 'index' -%}}
    {{%- comment -%}} {INTLINKS_MARKER}: organizer + service-area anchors {{%- endcomment -%}}
    <section class="ols-home-organizers-intlinks" aria-label="Estate sale organizer services" style="max-width:1200px;margin:24px auto;padding:20px 16px 8px;border-top:1px solid #eee;font-size:15px;line-height:1.6;color:#333;">
      <h2 style="font-size:18px;margin:0 0 10px;font-weight:600;">Estate Sale Organizers Serving Tampa Bay</h2>
      <p style="margin:0 0 8px;">Families hire our <a href="/pages/contact-us">estate sale organizers</a> for full-service sales, appraisals, and downsizing help. Start with <a href="/pages/estate-sale-palm-harbor-pinellas-county">estate sales in Palm Harbor / Pinellas County</a> or <a href="/pages/estate-sale-pasco-county">Pasco County estate sale services</a>.</p>
      <p style="margin:0;">Need a cleanout after the sale? See our <a href="/pages/estate-cleanout-services">estate cleanout services</a> across Tampa Bay.</p>
    </section>
    {{%- endif -%}}
"""

COOKIE_ANCHOR = "{%- include 'cookie-policy' -%}"

INDEXNOW_KEY_PATH = PROJECT_ROOT / "credentials" / "indexnow_key.txt"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _retry(fn: Any, *args: Any, **kwargs: Any) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(8):
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


def main_theme(headers: dict[str, str], base_url: str) -> dict:
    themes = get_json(f"{base_url}/themes.json", headers).get("themes", [])
    theme = next((t for t in themes if t.get("role") == "main"), None)
    if not theme:
        sys.exit("No main Shopify theme found")
    return theme


def get_theme_asset(headers: dict[str, str], base_url: str, theme_id: int, key: str) -> str:
    resp = _retry(
        httpx.get,
        f"{base_url}/themes/{theme_id}/assets.json",
        headers=headers,
        params={"asset[key]": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["asset"]["value"]


def put_theme_asset(
    headers: dict[str, str], base_url: str, theme_id: int, key: str, value: str
) -> None:
    resp = _retry(
        httpx.put,
        f"{base_url}/themes/{theme_id}/assets.json",
        headers=headers,
        json={"asset": {"key": key, "value": value}},
        timeout=60,
    )
    resp.raise_for_status()


def replace_homepage_meta(source: str) -> tuple[str, str]:
    """Replace HOMEPAGE-SEO-META-V1 title/description copy. Returns (after, status)."""
    if HOMEPAGE_META_MARKER not in source:
        raise RuntimeError(
            f"Marker {HOMEPAGE_META_MARKER} not found — run Session 10 homepage patch first"
        )

    if HOMEPAGE_TITLE in source and HOMEPAGE_DESCRIPTION in source:
        return source, "unchanged"

    after = source
    replaced_title = False
    for legacy in LEGACY_TITLES:
        if legacy in after:
            after = after.replace(legacy, HOMEPAGE_TITLE, 1)
            replaced_title = True
            break

    # Fallback: replace first index-title line after the V1 title comment.
    if not replaced_title:
        title_re = re.compile(
            rf"({{%- comment -%}} {re.escape(HOMEPAGE_META_MARKER)}: title "
            r"{{%- endcomment -%}}\s*"
            r"{%- if template\.name == 'index' -%}\s*)"
            r"([^\n]+)",
            re.MULTILINE,
        )
        after, n = title_re.subn(rf"\g<1>{HOMEPAGE_TITLE}", after, count=1)
        replaced_title = n == 1

    replaced_desc = False
    for legacy in LEGACY_DESCRIPTIONS:
        needle = f'content="{legacy}"'
        replacement = f'content="{HOMEPAGE_DESCRIPTION}"'
        if needle in after:
            after = after.replace(needle, replacement, 1)
            replaced_desc = True
            break

    if not replaced_desc:
        desc_re = re.compile(
            rf'({{%- comment -%}} {re.escape(HOMEPAGE_META_MARKER)}: description '
            r'{{%- endcomment -%}}\s*'
            r'{%- if template\.name == \'index\' -%}\s*'
            r'<meta name="description" content=")([^"]+)(">)',
            re.MULTILINE,
        )
        after, n = desc_re.subn(rf"\g<1>{HOMEPAGE_DESCRIPTION}\g<3>", after, count=1)
        replaced_desc = n == 1

    if not replaced_title or not replaced_desc:
        raise RuntimeError(
            "Could not replace homepage title/description inside HOMEPAGE-SEO-META-V1"
        )
    if HOMEPAGE_TITLE not in after or HOMEPAGE_DESCRIPTION not in after:
        raise RuntimeError("Homepage meta replace did not land new copy")
    return after, "replaced"


def patch_organizer_intlinks(source: str) -> tuple[str, str]:
    if INTLINKS_MARKER in source:
        return source, "unchanged"
    if COOKIE_ANCHOR not in source:
        raise RuntimeError(f"Could not locate intlinks anchor: {COOKIE_ANCHOR!r}")
    after = source.replace(COOKIE_ANCHOR, INTLINKS_BLOCK + "    " + COOKIE_ANCHOR, 1)
    if INTLINKS_MARKER not in after:
        raise RuntimeError("Organizer intlinks insertion failed")
    return after, "inserted"


def submit_indexnow(url: str) -> dict[str, Any]:
    key = ""
    if INDEXNOW_KEY_PATH.exists():
        key = INDEXNOW_KEY_PATH.read_text().strip()
    key = key or os.getenv("INDEXNOW_KEY", "").strip()
    if not key:
        return {"status": "skipped", "reason": "no_indexnow_key"}
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"{ORG_URL}{key}.txt",
        "urlList": [url],
    }
    resp = _retry(
        httpx.post,
        "https://api.indexnow.org/indexnow",
        json=payload,
        timeout=30,
    )
    return {"status_code": resp.status_code, "url": url}


def run(*, apply: bool, skip_indexnow: bool = False) -> dict[str, Any]:
    dry_run = not apply
    assert len(HOMEPAGE_TITLE) <= 60
    assert 120 <= len(HOMEPAGE_DESCRIPTION) <= 160

    headers, base_url = shopify_context()
    theme = main_theme(headers, base_url)
    layout_key = "layout/theme.liquid"
    before = get_theme_asset(headers, base_url, theme["id"], layout_key)

    after, meta_status = replace_homepage_meta(before)
    after, intlinks_status = patch_organizer_intlinks(after)
    changed = after != before

    result: dict[str, Any] = {
        "mode": "apply" if apply else "dry_run",
        "theme_id": theme["id"],
        "theme_name": theme.get("name"),
        "homepage_title": HOMEPAGE_TITLE,
        "homepage_title_len": len(HOMEPAGE_TITLE),
        "homepage_description": HOMEPAGE_DESCRIPTION,
        "homepage_description_len": len(HOMEPAGE_DESCRIPTION),
        "meta_status": (
            f"would_{meta_status}" if dry_run and meta_status != "unchanged" else meta_status
        ),
        "intlinks_status": (
            f"would_{intlinks_status}"
            if dry_run and intlinks_status != "unchanged"
            else intlinks_status
        ),
        "changed": changed,
    }

    if changed:
        result["diff_preview"] = "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile="before/layout/theme.liquid",
                tofile="after/layout/theme.liquid",
                n=3,
            )
        )[:8000]

    if dry_run or not changed:
        result["indexnow"] = {"status": "skipped", "reason": "dry_run_or_unchanged"}
        return result

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = OUT_DIR / f"theme_layout_snapshot_pre_session12_homepage_{timestamp}.liquid"
    snapshot.write_text(before)
    put_theme_asset(headers, base_url, theme["id"], layout_key, after)
    result["snapshot"] = str(snapshot.relative_to(PROJECT_ROOT))

    if skip_indexnow:
        result["indexnow"] = {"status": "skipped", "reason": "flag"}
    else:
        # Brief pause so storefront can pick up theme asset.
        time.sleep(2)
        result["indexnow"] = submit_indexnow(ORG_URL)

    result["verify"] = {
        "live_url": ORG_URL,
        "expect_title": HOMEPAGE_TITLE,
        "expect_meta": HOMEPAGE_DESCRIPTION,
        "expect_intlinks_marker": INTLINKS_MARKER,
    }
    return result


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform live Shopify theme writes (requires mutation guard env).",
    )
    parser.add_argument(
        "--skip-indexnow",
        action="store_true",
        help="Skip IndexNow homepage ping after apply.",
    )
    args = parser.parse_args()
    result = run(apply=args.apply, skip_indexnow=args.skip_indexnow)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_DIR / f"session12_homepage_organizers_ctr_{timestamp}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nWrote report: {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
