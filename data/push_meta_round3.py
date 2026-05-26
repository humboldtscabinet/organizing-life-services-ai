"""Round 3 — push approved meta rewrites to Shopify.

Reads `data/audit_output/round3_meta_drafts.json` and pushes ONLY the
entries with `"approved": true` to Shopify Admin API as metafields
(`global.title_tag`, `global.description_tag`).

Workflow:
  1. Run `python data/round3_draft_metas.py` to generate the drafts file.
  2. Human review: open the JSON, set `approved: true` on each entry to deploy
     (and optionally hand-edit the draft.new_title / draft.new_meta_description
     fields). Leave `approved: false` to skip.
  3. Run this script inside the API container:
        docker exec ols-api python3 /app/data/push_meta_round3.py

  Or with DRY_RUN to preview without pushing:
        DRY_RUN=1 docker exec -e DRY_RUN=1 ols-api python3 /app/data/push_meta_round3.py

Entries with `kind == "special"` (blog index, collections, etc. that don't
support per-resource SEO metafields) are skipped with a status note even if
approved.

After a successful push, add an entry to docs/seo-audits/CHANGELOG.md.
"""
import json
import os
import sys
from pathlib import Path

import httpx

from app.services.shopify_service import _shopify_headers, _shopify_url

DRAFTS_PATH = Path(__file__).parent / "audit_output" / "round3_meta_drafts.json"
DRY_RUN = bool(os.environ.get("DRY_RUN"))


def _get(path):
    r = httpx.get(_shopify_url(path), headers=_shopify_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def upsert_metafield(owner_resource, owner_id, key, value):
    list_path = f"{owner_resource}/{owner_id}/metafields.json"
    data = _get(list_path)
    existing = next(
        (m for m in data["metafields"]
         if m["namespace"] == "global" and m["key"] == key),
        None,
    )
    headers = _shopify_headers()
    if existing:
        url = _shopify_url(f"metafields/{existing['id']}.json")
        body = {"metafield": {"id": existing["id"], "value": value, "type": "single_line_text_field"}}
        r = httpx.put(url, headers=headers, json=body, timeout=30)
    else:
        url = _shopify_url(list_path)
        body = {"metafield": {
            "namespace": "global", "key": key, "value": value,
            "type": "single_line_text_field",
        }}
        r = httpx.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return r.json()["metafield"]


def main():
    if not DRAFTS_PATH.exists():
        print(f"[round3-push] ERROR: {DRAFTS_PATH} not found. Run round3_draft_metas.py first.", file=sys.stderr)
        sys.exit(1)

    with open(DRAFTS_PATH) as f:
        doc = json.load(f)
    drafts = doc.get("drafts", [])

    approved = [d for d in drafts if d.get("approved") is True]
    print(f"[round3-push] {len(approved)} of {len(drafts)} drafts marked approved")
    if DRY_RUN:
        print("[round3-push] DRY_RUN=1 — no changes will be pushed")
    if not approved:
        print("[round3-push] nothing to push. Set `approved: true` on entries in the JSON.")
        return

    # Build lookup maps once
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
            results.append({"handle": handle, "kind": kind, "status": "skipped_special",
                            "note": d.get("special_note") or "cannot set per-resource metafield"})
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

        if DRY_RUN:
            results.append({
                "handle": handle, "kind": kind, "owner_id": owner_id,
                "status": "dry_run",
                "new_title": new_title,
                "new_meta": new_meta,
            })
            continue

        title_mf = upsert_metafield(owner_resource, owner_id, "title_tag", new_title)
        desc_mf = upsert_metafield(owner_resource, owner_id, "description_tag", new_meta)
        results.append({
            "handle": handle, "kind": kind, "owner_id": owner_id,
            "status": "updated",
            "title_metafield_id": title_mf["id"],
            "desc_metafield_id": desc_mf["id"],
        })

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
