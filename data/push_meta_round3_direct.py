"""Round 3 push — direct OAuth variant (no sqlalchemy / no Docker).

Same logic as data/push_meta_round3.py but uses Shopify Client Credentials
OAuth directly so it can run inside the lightweight .venv-audit env.

Usage:
  set -a && source .env && set +a
  source .venv-audit/bin/activate
  python data/push_meta_round3_direct.py [--dry-run]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx


def _retry(fn, *args, **kwargs):
    last = None
    for attempt in range(5):
        try:
            return fn(*args, **kwargs)
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.ConnectError) as e:
            last = e
            wait = 2 ** attempt
            print(f"  [retry] {type(e).__name__}: {e}; sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise last

STORE = os.getenv("SHOPIFY_STORE")
CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")

if not all([STORE, CLIENT_ID, CLIENT_SECRET]):
    sys.exit("Missing SHOPIFY_STORE / SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET in .env")

DRAFTS_PATH = Path(__file__).parent / "audit_output" / "round3_meta_drafts.json"


def _token():
    r = httpx.post(
        f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
              "grant_type": "client_credentials"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


TOKEN = _token()
H = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
BASE = f"https://{STORE}.myshopify.com/admin/api/{API_VER}"


def _get(path):
    r = _retry(httpx.get, f"{BASE}/{path}", headers=H, timeout=60)
    r.raise_for_status()
    return r.json()


def upsert_metafield(owner_resource, owner_id, key, value, dry_run=False):
    list_path = f"{owner_resource}/{owner_id}/metafields.json"
    data = _get(list_path)
    existing = next(
        (m for m in data["metafields"]
         if m["namespace"] == "global" and m["key"] == key),
        None,
    )
    if dry_run:
        return {"id": existing["id"] if existing else None, "dry_run": True}
    if existing:
        url = f"{BASE}/metafields/{existing['id']}.json"
        body = {"metafield": {"id": existing["id"], "value": value, "type": "single_line_text_field"}}
        r = _retry(httpx.put, url, headers=H, json=body, timeout=60)
    else:
        url = f"{BASE}/{list_path}"
        body = {"metafield": {
            "namespace": "global", "key": key, "value": value,
            "type": "single_line_text_field",
        }}
        r = _retry(httpx.post, url, headers=H, json=body, timeout=60)
    r.raise_for_status()
    return r.json()["metafield"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry_run = args.dry_run or bool(os.environ.get("DRY_RUN"))

    if not DRAFTS_PATH.exists():
        sys.exit(f"ERROR: {DRAFTS_PATH} not found.")

    with open(DRAFTS_PATH) as f:
        doc = json.load(f)
    drafts = doc.get("drafts", [])

    approved = [d for d in drafts if d.get("approved") is True]
    print(f"[round3-push] {len(approved)} of {len(drafts)} approved" + (" (DRY RUN)" if dry_run else ""))
    if not approved:
        return

    pages = {p["handle"]: p for p in _get("pages.json?limit=250")["pages"]}
    blogs = _get("blogs.json?limit=50")["blogs"]
    article_map = {}
    for b in blogs:
        for a in _get(f"blogs/{b['id']}/articles.json?limit=250")["articles"]:
            article_map[a["handle"]] = (b["id"], a["id"])

    results = []
    for d in approved:
        kind = d.get("kind")
        handle = d.get("handle")
        draft = d.get("draft") or {}
        new_title = draft.get("new_title")
        new_meta = draft.get("new_meta_description")

        if not new_title or not new_meta:
            results.append({"handle": handle, "status": "missing_draft_fields"})
            continue
        if kind == "special":
            results.append({"handle": handle, "kind": kind, "status": "skipped_special"})
            continue
        if kind == "page":
            page = pages.get(handle)
            if not page:
                results.append({"handle": handle, "kind": kind, "status": "not_found"})
                continue
            owner_resource, owner_id = "pages", page["id"]
        elif kind == "article":
            mapping = article_map.get(handle)
            if not mapping:
                results.append({"handle": handle, "kind": kind, "status": "not_found"})
                continue
            owner_resource, owner_id = "articles", mapping[1]
        else:
            results.append({"handle": handle, "kind": kind, "status": "unknown_kind"})
            continue

        title_mf = upsert_metafield(owner_resource, owner_id, "title_tag", new_title, dry_run=dry_run)
        desc_mf = upsert_metafield(owner_resource, owner_id, "description_tag", new_meta, dry_run=dry_run)
        results.append({
            "handle": handle, "kind": kind, "owner_id": owner_id,
            "status": "dry_run" if dry_run else "updated",
            "title_metafield_id": title_mf.get("id"),
            "desc_metafield_id": desc_mf.get("id"),
            "new_title": new_title,
            "new_meta_chars": len(new_meta),
        })

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
