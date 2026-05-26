"""Internal-linking pass — Task A3.

Adds 5 contextual internal links across 4 source pages, boosting 2 target pages.
Idempotent: skips edits where target href already present.
Run: docker exec ols-api sh -c 'cd /app && PYTHONPATH=/app python3 data/internal_links_a3.py [--dry-run]'
"""
import json
import sys
import httpx

from app.services.shopify_service import _shopify_headers, _shopify_url

# Each edit: (kind, handle, old_substring, new_substring, expected_target_in_new)
EDITS = [
    # --- Boost: /pages/personal-property-appraisal ---
    {
        "kind": "article",
        "handle": "pros-and-cons-of-estate-sales",
        "old": "the appraisal and pricing of the items",
        "new": 'the <a href="/pages/personal-property-appraisal">appraisal</a> and pricing of the items',
        "target": "/pages/personal-property-appraisal",
    },
    {
        "kind": "page",
        "handle": "estate-liquidation",
        "old": "<span>Appraisal Services:</span>",
        "new": '<span><a href="/pages/personal-property-appraisal">Appraisal Services</a>:</span>',
        "target": "/pages/personal-property-appraisal",
    },
    {
        "kind": "article",
        "handle": "estate-sale-vs-garage-sale-know-the-differences",
        "old": "Estate sale items are appraised and priced based on their market value",
        "new": 'Estate sale items are <a href="/pages/personal-property-appraisal">appraised and priced</a> based on their market value',
        "target": "/pages/personal-property-appraisal",
    },
    # --- Boost: /pages/what-is-an-estate-sale ---
    {
        "kind": "article",
        "handle": "pros-and-cons-of-estate-sales",
        "old": "The concept of an estate sale is simple",
        "new": 'The concept of <a href="/pages/what-is-an-estate-sale">an estate sale</a> is simple',
        "target": "/pages/what-is-an-estate-sale",
    },
    {
        "kind": "page",
        "handle": "estate-cleanout-services",
        "old": "houses that don't qualify for an estate sale",
        "new": 'houses that don\'t qualify for <a href="/pages/what-is-an-estate-sale">an estate sale</a>',
        "target": "/pages/what-is-an-estate-sale",
    },
]


def _get(p):
    r = httpx.get(_shopify_url(p), headers=_shopify_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def _put_page(page_id, body_html):
    url = _shopify_url(f"pages/{page_id}.json")
    body = {"page": {"id": page_id, "body_html": body_html}}
    r = httpx.put(url, headers=_shopify_headers(), json=body, timeout=30)
    r.raise_for_status()
    return r.json()["page"]


def _put_article(blog_id, article_id, body_html):
    url = _shopify_url(f"blogs/{blog_id}/articles/{article_id}.json")
    body = {"article": {"id": article_id, "body_html": body_html}}
    r = httpx.put(url, headers=_shopify_headers(), json=body, timeout=30)
    r.raise_for_status()
    return r.json()["article"]


def main(dry_run=False):
    pages = {p["handle"]: p for p in _get("pages.json?limit=250")["pages"]}
    blogs = _get("blogs.json?limit=50")["blogs"]
    article_map = {}
    for b in blogs:
        for a in _get(f"blogs/{b['id']}/articles.json?limit=250")["articles"]:
            article_map[a["handle"]] = (b["id"], a)

    # Group edits by (kind, handle) so we apply all to same body in one PUT
    grouped = {}
    for e in EDITS:
        grouped.setdefault((e["kind"], e["handle"]), []).append(e)

    results = []
    for (kind, handle), edits in grouped.items():
        if kind == "page":
            obj = pages.get(handle)
            if not obj:
                results.append({"handle": handle, "status": "not_found"}); continue
            body = obj["body_html"]
        else:
            mapping = article_map.get(handle)
            if not mapping:
                results.append({"handle": handle, "status": "not_found"}); continue
            blog_id, obj = mapping
            body = obj["body_html"]

        applied = []
        skipped = []
        new_body = body
        for e in edits:
            if e["target"] in new_body and 'href="' + e["target"] + '"' in new_body:
                # already linked somewhere — only skip if old substring already contains the link
                if e["new"] in new_body:
                    skipped.append({"target": e["target"], "reason": "already_applied"})
                    continue
            count = new_body.count(e["old"])
            if count == 0:
                skipped.append({"target": e["target"], "reason": "old_not_found",
                                "old_preview": e["old"][:80]})
                continue
            # Replace only first occurrence
            new_body = new_body.replace(e["old"], e["new"], 1)
            applied.append({"target": e["target"], "occurrences_before": count})

        if not applied:
            results.append({"handle": handle, "kind": kind, "status": "no_changes",
                            "skipped": skipped})
            continue

        if dry_run:
            results.append({"handle": handle, "kind": kind, "status": "DRY_RUN",
                            "applied": applied, "skipped": skipped,
                            "body_delta_bytes": len(new_body) - len(body)})
        else:
            if kind == "page":
                _put_page(obj["id"], new_body)
            else:
                _put_article(blog_id, obj["id"], new_body)
            results.append({"handle": handle, "kind": kind, "status": "updated",
                            "applied": applied, "skipped": skipped,
                            "body_delta_bytes": len(new_body) - len(body)})

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
