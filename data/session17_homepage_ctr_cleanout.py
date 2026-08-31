"""Session 17: homepage CTR pass for organizers + estate-cleanout-near-me.

Why
---
GSC 2026-08-01→08-28 shows the homepage ``/`` earning impressions but 0 clicks
for two distinct intents:

- ``estate sale organizers`` → ``/`` : 272 impr, 0 clicks, pos 15.9
- ``estate cleanout near me``  → ``/`` : 264 impr, 0 clicks, pos 1.2

The cleanout query ranks #1 with a 0% CTR, which is the classic sign of a SERP
snippet mismatch: the live title (Session 12, ``HOMEPAGE-SEO-META-V1``) reads
``Estate Sale Organizers Tampa Bay | Call OLS Today`` — pure organizer intent —
so a searcher on ``estate cleanout near me`` sees an organizers headline and
scrolls past. This pass refreshes the homepage title + meta description so the
snippet speaks to *both* organizer and cleanout intent, without keyword
stuffing, competitor names, invented prices, or fake testimonials.

Scope (deliberately narrow)
---------------------------
- Upgrades the theme ``HOMEPAGE-SEO-META-V1`` block to ``HOMEPAGE-SEO-META-V2``
  with new title/description copy (region stays Tampa Bay / Pinellas→Citrus,
  approved phone ``(727) 542-6028``).
- Cleanout is folded into the **title** (it fits under 60 chars) and reinforced
  in the meta; the H1 story on the page is unchanged (one H1).
- The organizer intlinks block ``SEO-INTLINKS-ORGANIZERS-V1`` already mentions
  estate cleanout services, so this script does **not** duplicate that copy. A
  single cleanout-facing sentence is only inserted if that block somehow lacks
  any cleanout mention.
- Refuses to regress the ``OLS-GTM-INSTALL-V1`` GTM snippet (Session 16): if the
  container is present before the edit it must still be present after.

Does NOT touch Shopify products or product SEO fields, fee collections, or
``app/agents/``.

Safety
------
- Default mode is dry-run.
- Live writes require ``--apply`` plus mutation confirmation:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

- Snapshots ``layout/theme.liquid`` before any live write.
- Idempotent once the ``HOMEPAGE-SEO-META-V2`` copy is present.

Usage
-----
    set -a && source .env && set +a
    .venv/bin/python data/session17_homepage_ctr_cleanout.py

    OLS_ALLOW_DATA_MUTATION=1 \\
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \\
    .venv/bin/python data/session17_homepage_ctr_cleanout.py --apply
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

# Marker upgrade: Session 10 introduced V1, Session 12 refreshed the copy in
# place (still V1). This pass changes the copy AND bumps the marker to V2 so the
# new dual-intent snippet is the idempotency signal.
HOMEPAGE_META_MARKER_V2 = "HOMEPAGE-SEO-META-V2"
HOMEPAGE_META_MARKER_V1 = "HOMEPAGE-SEO-META-V1"

INTLINKS_MARKER = "SEO-INTLINKS-ORGANIZERS-V1"

# GTM install (Session 16). This pass must not drop it.
GTM_MARKER = "OLS-GTM-INSTALL-V1"
GTM_PUBLIC_ID = "GTM-KQ76X4NR"

# --- Proposed copy -------------------------------------------------------
# Title ≤60, description ~120–160. Serves organizer intent (kept as the lead)
# and estate-cleanout-near-me intent (the #1-ranked, 0-CTR query) without
# stuffing "near me" literally — region + service words carry local intent.
HOMEPAGE_TITLE = "Estate Sale Organizers & Cleanouts | Tampa Bay OLS"
HOMEPAGE_DESCRIPTION = (
    "Tampa Bay estate sale organizers and estate cleanout services. OLS runs "
    "full sales, appraisals, and downsizing from Pinellas to Citrus. "
    "Call (727) 542-6028."
)

# Copy this pass replaces (Session 12 live copy first, then the Session 10
# copy, in case an older theme is encountered).
LEGACY_TITLES = (
    "Estate Sale Organizers Tampa Bay | Call OLS Today",
    "Estate Sale Organizers Tampa Bay | Appraisals & Downsizing",
)
LEGACY_DESCRIPTIONS = (
    (
        "Need estate sale organizers in Tampa Bay? OLS runs estate sales, "
        "appraisals, and downsizing across Pinellas to Citrus. "
        "Call (727) 542-6028."
    ),
    (
        "Tampa Bay estate sale organizers for estate sales, appraisals, "
        "downsizing, and cleanouts across Pinellas, Pasco, Hillsborough, "
        "Hernando, and Citrus."
    ),
)

# Single cleanout-near-me-facing sentence, only inserted if the organizer
# intlinks block is missing any cleanout mention (defensive; live already has
# one, so this normally no-ops).
CLEANOUT_SENTENCE = (
    '      <p style="margin:8px 0 0;">Need an estate cleanout near you? Our '
    '<a href="/pages/estate-cleanout-services">estate cleanout services</a> '
    "clear full estates across Tampa Bay, from Pinellas to Citrus.</p>\n"
)

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


def upgrade_homepage_meta(source: str) -> tuple[str, str]:
    """Upgrade HOMEPAGE-SEO-META-V1 → V2 with dual-intent copy.

    Returns ``(after, status)`` where status is ``unchanged`` or ``upgraded``.
    """
    if (
        HOMEPAGE_META_MARKER_V2 in source
        and HOMEPAGE_TITLE in source
        and HOMEPAGE_DESCRIPTION in source
    ):
        return source, "unchanged"

    if HOMEPAGE_META_MARKER_V1 not in source:
        raise RuntimeError(
            f"Marker {HOMEPAGE_META_MARKER_V1} not found — run the Session 10/12 "
            "homepage patch first"
        )

    after = source

    replaced_title = False
    for legacy in LEGACY_TITLES:
        if legacy in after:
            after = after.replace(legacy, HOMEPAGE_TITLE, 1)
            replaced_title = True
            break
    if not replaced_title:
        # Fallback: first index-title line after the V1 title comment.
        title_re = re.compile(
            rf"({{%- comment -%}} {re.escape(HOMEPAGE_META_MARKER_V1)}: title "
            r"{%- endcomment -%}\s*"
            r"{%- if template\.name == 'index' -%}\s*)"
            r"([^\n]+)",
            re.MULTILINE,
        )
        after, n = title_re.subn(rf"\g<1>{HOMEPAGE_TITLE}", after, count=1)
        replaced_title = n == 1

    replaced_desc = False
    for legacy in LEGACY_DESCRIPTIONS:
        needle = f'content="{legacy}"'
        if needle in after:
            after = after.replace(needle, f'content="{HOMEPAGE_DESCRIPTION}"', 1)
            replaced_desc = True
            break
    if not replaced_desc:
        desc_re = re.compile(
            rf'({{%- comment -%}} {re.escape(HOMEPAGE_META_MARKER_V1)}: description '
            r'{%- endcomment -%}\s*'
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

    # Bump the marker last so the copy-replacement regexes above still key off V1.
    after = after.replace(HOMEPAGE_META_MARKER_V1, HOMEPAGE_META_MARKER_V2)

    if (
        HOMEPAGE_TITLE not in after
        or HOMEPAGE_DESCRIPTION not in after
        or HOMEPAGE_META_MARKER_V2 not in after
        or HOMEPAGE_META_MARKER_V1 in after
    ):
        raise RuntimeError("Homepage meta upgrade did not land V2 copy cleanly")
    return after, "upgraded"


def ensure_cleanout_sentence(source: str) -> tuple[str, str]:
    """Add one cleanout sentence to the organizer intlinks block iff missing.

    Statuses: ``intlinks_absent`` (block not present — not this pass's job),
    ``present`` (already mentions cleanout — do not duplicate), ``inserted``.
    """
    if INTLINKS_MARKER not in source:
        return source, "intlinks_absent"

    start = source.index(INTLINKS_MARKER)
    close_idx = source.find("</section>", start)
    if close_idx == -1:
        # No section boundary found; be conservative and do nothing.
        return source, "present"

    block = source[start:close_idx]
    if re.search(r"cleanout", block, re.IGNORECASE):
        return source, "present"

    after = source[:close_idx] + CLEANOUT_SENTENCE + "    " + source[close_idx:]
    if "estate-cleanout-services" not in after:
        raise RuntimeError("Cleanout sentence insertion failed")
    return after, "inserted"


def assert_gtm_preserved(before: str, after: str) -> None:
    for token in (GTM_MARKER, GTM_PUBLIC_ID):
        if token in before and token not in after:
            raise RuntimeError(
                f"Refusing to regress GTM: {token} present before edit but missing after"
            )


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
    assert len(HOMEPAGE_TITLE) <= 60, f"title too long: {len(HOMEPAGE_TITLE)}"
    assert 120 <= len(HOMEPAGE_DESCRIPTION) <= 160, (
        f"description length {len(HOMEPAGE_DESCRIPTION)} outside 120–160"
    )

    headers, base_url = shopify_context()
    theme = main_theme(headers, base_url)
    layout_key = "layout/theme.liquid"
    before = get_theme_asset(headers, base_url, theme["id"], layout_key)

    after, meta_status = upgrade_homepage_meta(before)
    after, cleanout_status = ensure_cleanout_sentence(after)
    assert_gtm_preserved(before, after)
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
        "cleanout_sentence_status": (
            f"would_{cleanout_status}"
            if dry_run and cleanout_status == "inserted"
            else cleanout_status
        ),
        "gtm_snippet_present": GTM_MARKER in before,
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
    snapshot = OUT_DIR / f"theme_layout_snapshot_pre_session17_homepage_{timestamp}.liquid"
    snapshot.write_text(before)
    put_theme_asset(headers, base_url, theme["id"], layout_key, after)
    result["snapshot"] = str(snapshot.relative_to(PROJECT_ROOT))

    if skip_indexnow:
        result["indexnow"] = {"status": "skipped", "reason": "flag"}
    else:
        time.sleep(2)
        result["indexnow"] = submit_indexnow(ORG_URL)

    result["verify"] = {
        "live_url": ORG_URL,
        "expect_title": HOMEPAGE_TITLE,
        "expect_meta": HOMEPAGE_DESCRIPTION,
        "expect_meta_marker": HOMEPAGE_META_MARKER_V2,
        "expect_gtm": GTM_PUBLIC_ID,
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
    out_path = OUT_DIR / f"session17_homepage_ctr_cleanout_{timestamp}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nWrote report: {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
