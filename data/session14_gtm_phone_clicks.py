"""Session 14: Ensure GTM phone_call_clicks tracking (tel: link clicks).

Idempotently creates/updates:
  - Trigger: ``OLS - tel link click`` (Click URL contains tel:)
  - Tag: ``OLS - phone_call_clicks`` (GA4 Event)

Default: dry-run. Does not publish live unless ``--publish`` is passed
(after a version exists from ``--apply`` or ``--version-path``).

Safety
------
- Default mode is dry-run.
- Live workspace writes require ``--apply`` plus:

    OLS_ALLOW_DATA_MUTATION=1
    OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE

- Live publish additionally requires ``--publish`` (and the same env vars).

Usage
-----
    .venv/bin/python data/session14_gtm_phone_clicks.py
    .venv/bin/python data/session14_gtm_phone_clicks.py --apply
    .venv/bin/python data/session14_gtm_phone_clicks.py --apply --publish
    .venv/bin/python data/session14_gtm_phone_clicks.py --publish \\
        --version-path accounts/.../versions/N
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUT_DIR = PROJECT_ROOT / "data" / "audit_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)


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
        raise SystemExit(
            "Live apply requires OLS_ALLOW_DATA_MUTATION=1 and "
            f"{CONFIRM_ENV}={CONFIRM_PHRASE}."
        )


def write_report(payload: dict[str, Any]) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"session14_gtm_phone_clicks_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ensure OLS GTM phone_call_clicks tracking (dry-run by default)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write workspace trigger/tag and create a container version.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish a version live (requires --apply result or --version-path).",
    )
    parser.add_argument(
        "--version-path",
        default="",
        help="Container version path to publish (skips ensure when used alone).",
    )
    parser.add_argument(
        "--no-version",
        action="store_true",
        help="With --apply, skip create_version (workspace only).",
    )
    parser.add_argument(
        "--version-name",
        default="",
        help="Optional container version name.",
    )
    args = parser.parse_args()

    from app.services import gtm_service as gs

    if not gs.direct_api_available():
        raise SystemExit(
            "GTM not configured. Set GOOGLE_APPLICATION_CREDENTIALS and "
            "GTM_ACCOUNT_ID / GTM_CONTAINER_ID."
        )

    report: dict[str, Any] = {
        "script": "session14_gtm_phone_clicks",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "apply": bool(args.apply),
        "publish": bool(args.publish),
    }

    ensure_result: dict[str, Any] | None = None
    version_path = (args.version_path or "").strip()
    only_publish_existing = bool(args.publish and version_path and not args.apply)

    if not only_publish_existing:
        dry_run = not args.apply
        if args.apply:
            require_apply_confirmation()
        ensure_result = gs.ensure_phone_call_clicks_tracking(
            dry_run=dry_run,
            create_version_after=args.apply and not args.no_version,
            version_name=args.version_name or None,
        )
        report["ensure"] = ensure_result
        if (
            not dry_run
            and ensure_result.get("version")
            and ensure_result["version"].get("version_path")
        ):
            version_path = ensure_result["version"]["version_path"]

    if args.publish:
        require_apply_confirmation()
        if not version_path:
            raise SystemExit(
                "Publish requested but no version_path available. "
                "Re-run with --apply (creates a version) or pass --version-path."
            )
        publish_result = gs.publish_version(version_path)
        report["publish_result"] = publish_result
        print(json.dumps({"publish": publish_result}, indent=2, default=str))
    elif ensure_result is not None:
        summary = {
            "status": ensure_result.get("status"),
            "dry_run": ensure_result.get("dry_run"),
            "would_create": ensure_result.get("would_create"),
            "unchanged": ensure_result.get("unchanged"),
            "updated": ensure_result.get("updated"),
            "created": ensure_result.get("created"),
            "trigger": ensure_result.get("trigger"),
            "tag": ensure_result.get("tag"),
            "version": ensure_result.get("version"),
            "note": ensure_result.get("note"),
        }
        print(json.dumps(summary, indent=2, default=str))

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    out = write_report(report)
    print(f"Wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
