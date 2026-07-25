"""Session 16: Install GTM container snippet on the live Shopify theme.

Root cause: GA4 loads via Shopify Google & YouTube channel, but GTM-KQ76X4NR
was never on the storefront — so published GTM tags (including
phone_call_clicks) never ran.

This script:
1. Injects standard GTM head + noscript snippets into ``layout/theme.liquid``
   (idempotent marker ``OLS-GTM-INSTALL-V1``).
2. Optionally (``--apply`` default with GTM writes): pause GTM tag
   ``GA4-Config-G-4HSTXZKG9E`` so Shopify keeps base page_view and GTM does
   not double-count; set ``waitForTags=true`` on ``OLS - tel link click``;
   create a container version (does not publish unless ``--publish``).

Safety
------
- Default mode is dry-run.
- Live writes require ``--apply`` plus:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

Usage
-----
    docker exec --env-file .env ols-api python3 /app/data/session16_install_gtm.py
    docker exec -e OLS_ALLOW_DATA_MUTATION=1 \\
      -e OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \\
      --env-file .env ols-api python3 /app/data/session16_install_gtm.py --apply
    # after review, publish the new version:
    ... --publish --version-path accounts/.../versions/N
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from _mutation_guard import (
        CONFIRM_ENV,
        CONFIRM_PHRASE,
        activate as activate_data_mutation_guard,
    )
except ModuleNotFoundError:  # pragma: no cover
    from data._mutation_guard import (
        CONFIRM_ENV,
        CONFIRM_PHRASE,
        activate as activate_data_mutation_guard,
    )

activate_data_mutation_guard()

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LAYOUT_KEY = "layout/theme.liquid"
GTM_PUBLIC_ID = os.getenv("GTM_PUBLIC_ID", "GTM-KQ76X4NR").strip() or "GTM-KQ76X4NR"
MARKER = "OLS-GTM-INSTALL-V1"
GA4_CONFIG_TAG_NAME = "GA4-Config-G-4HSTXZKG9E"
OLS_TEL_TRIGGER_NAME = "OLS - tel link click"

GTM_HEAD = f"""{{%- comment -%}} {MARKER} head {{%- endcomment -%}}
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','{GTM_PUBLIC_ID}');</script>
<!-- End Google Tag Manager -->
{{%- comment -%}} /{MARKER} head {{%- endcomment -%}}
"""

GTM_BODY = f"""{{%- comment -%}} {MARKER} body {{%- endcomment -%}}
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={GTM_PUBLIC_ID}"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager -->
{{%- comment -%}} /{MARKER} body {{%- endcomment -%}}
"""


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
            time.sleep(2**attempt)
    if last:
        raise last
    raise RuntimeError("retries exhausted")


def require_apply_confirmation() -> None:
    allow = os.getenv("OLS_ALLOW_DATA_MUTATION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }
    confirm = os.getenv(CONFIRM_ENV, "").strip()
    if not allow or confirm != CONFIRM_PHRASE:
        sys.exit(
            "Live apply requires OLS_ALLOW_DATA_MUTATION=1 and "
            f"{CONFIRM_ENV}={CONFIRM_PHRASE}."
        )


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


def main_theme(headers: dict[str, str], base_url: str) -> dict:
    themes = _retry(httpx.get, f"{base_url}/themes.json", headers=headers, timeout=60).json().get(
        "themes", []
    )
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


def inject_gtm(liquid: str) -> tuple[str, dict[str, Any]]:
    info: dict[str, Any] = {
        "marker": MARKER,
        "public_id": GTM_PUBLIC_ID,
        "head": "unchanged",
        "body": "unchanged",
    }
    out = liquid
    if MARKER in out and GTM_PUBLIC_ID in out:
        info["status"] = "unchanged"
        return out, info

    if "googletagmanager.com/gtm.js" in out and GTM_PUBLIC_ID in out:
        info["status"] = "unchanged"
        info["reason"] = "gtm_already_installed"
        return out, info

    # Head: insert before </head>
    if MARKER + " head" not in out:
        if re.search(r"</head>", out, flags=re.I):
            out = re.sub(
                r"</head>",
                GTM_HEAD + "\n</head>",
                out,
                count=1,
                flags=re.I,
            )
            info["head"] = "insert"
        else:
            info["head"] = "missing_head_tag"
            info["status"] = "error"
            return liquid, info

    # Body: insert immediately after <body ...>
    if MARKER + " body" not in out:
        m = re.search(r"<body[^>]*>", out, flags=re.I)
        if not m:
            info["body"] = "missing_body_tag"
            info["status"] = "error"
            return liquid, info
        insert_at = m.end()
        out = out[:insert_at] + "\n" + GTM_BODY + out[insert_at:]
        info["body"] = "insert"

    info["status"] = "would_update" if info["head"] == "insert" or info["body"] == "insert" else "unchanged"
    return out, info


def patch_theme(*, dry_run: bool) -> dict[str, Any]:
    headers, base_url = shopify_context()
    theme = main_theme(headers, base_url)
    before = get_theme_asset(headers, base_url, theme["id"], LAYOUT_KEY)
    after, info = inject_gtm(before)
    result = {
        "theme_id": theme["id"],
        "asset": LAYOUT_KEY,
        **info,
        "changed": info.get("status") in {"would_update", "updated"},
    }
    if info.get("status") == "error":
        return result
    if info.get("status") == "unchanged":
        return result
    if dry_run:
        result["status"] = "would_update"
        return result
    put_theme_asset(headers, base_url, theme["id"], LAYOUT_KEY, after)
    result["status"] = "updated"
    result["changed"] = True
    return result


def patch_gtm_workspace(*, dry_run: bool, create_version: bool) -> dict[str, Any]:
    from app.services import gtm_service as gs

    out: dict[str, Any] = {"dry_run": dry_run}
    if not gs.direct_api_available():
        return {"status": "skipped", "reason": "gtm_not_configured"}

    # Pause GA4 config in GTM (Shopify channel already sends page_view)
    tag = gs.get_tag_by_name(GA4_CONFIG_TAG_NAME)
    if not tag:
        out["ga4_config"] = {"status": "not_found", "name": GA4_CONFIG_TAG_NAME}
    elif tag.get("paused"):
        out["ga4_config"] = {"status": "unchanged", "already_paused": True}
    else:
        body = {
            "name": tag["name"],
            "type": tag["type"],
            "parameter": tag.get("parameter") or [],
            "firingTriggerId": tag.get("firing_trigger_ids") or [],
            "paused": True,
        }
        if dry_run:
            out["ga4_config"] = {"status": "would_pause", "tag_id": tag.get("tag_id")}
        else:
            updated = gs.update_tag(
                tag["path"], body, fingerprint=tag.get("fingerprint")
            )
            out["ga4_config"] = {
                "status": "paused",
                "tag_id": updated.get("tag_id"),
            }

    # Prefer waitForTags=true on tel trigger so dialer navigation does not drop hits
    trigger = gs.get_trigger_by_name(OLS_TEL_TRIGGER_NAME)
    if not trigger:
        out["tel_trigger"] = {"status": "not_found", "name": OLS_TEL_TRIGGER_NAME}
    else:
        # Rebuild body from known good shape with waitForTags true
        from app.services.gtm_service import _tel_link_trigger_body

        body = _tel_link_trigger_body()
        body["waitForTags"] = {"type": "boolean", "value": "true"}
        # Detect if already true
        existing_wait = None
        # list_triggers summary may not include waitForTags; fetch via update compare
        if dry_run:
            out["tel_trigger"] = {
                "status": "would_set_waitForTags_true",
                "trigger_id": trigger.get("trigger_id"),
            }
        else:
            updated = gs.update_trigger(
                trigger["path"], body, fingerprint=trigger.get("fingerprint")
            )
            out["tel_trigger"] = {
                "status": "updated_waitForTags_true",
                "trigger_id": updated.get("trigger_id"),
            }

    if create_version and not dry_run:
        out["version"] = gs.create_version(
            name="OLS install GTM + pause GA4 config; waitForTags tel",
            notes=(
                "Pause GTM GA4 Config to avoid double page_view with Shopify "
                "Google channel; waitForTags=true on OLS tel trigger."
            ),
        )
    elif create_version and dry_run:
        out["version"] = {"action": "would_create_version"}

    return out


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--skip-gtm-workspace",
        action="store_true",
        help="Only install theme snippet; do not pause GA4 config / update trigger.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish a version_path (requires --version-path).",
    )
    parser.add_argument("--version-path", default="")
    parser.add_argument(
        "--no-version",
        action="store_true",
        help="With --apply, skip create_version after GTM workspace edits.",
    )
    args = parser.parse_args()

    if args.publish:
        require_apply_confirmation()
        from app.services import gtm_service as gs

        path = (args.version_path or "").strip()
        if not path:
            sys.exit("--publish requires --version-path")
        result = gs.publish_version(path)
        print(json.dumps(result, indent=2, default=str))
        return 0

    dry_run = not args.apply
    if args.apply:
        require_apply_confirmation()

    print("Session 16 install GTM" + (" (DRY RUN)" if dry_run else ""))
    report: dict[str, Any] = {
        "script": "session16_install_gtm",
        "dry_run": dry_run,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gtm_public_id": GTM_PUBLIC_ID,
        "theme": patch_theme(dry_run=dry_run),
    }
    if not args.skip_gtm_workspace:
        report["gtm_workspace"] = patch_gtm_workspace(
            dry_run=dry_run,
            create_version=args.apply and not args.no_version,
        )
    else:
        report["gtm_workspace"] = {"status": "skipped"}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"session16_install_gtm_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    print(f"\nWrote report: {path.relative_to(PROJECT_ROOT)}")
    if not dry_run and report.get("gtm_workspace", {}).get("version", {}).get("version_path"):
        vp = report["gtm_workspace"]["version"]["version_path"]
        print(
            "\nNext: publish after review:\n"
            f"  ... session16_install_gtm.py --publish --version-path {vp}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
