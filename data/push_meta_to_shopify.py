"""One-off: push approved meta title/description rewrites to Shopify.

Updates SEO metafields ONLY (global.title_tag + global.description_tag).
Leaves visible page/article titles untouched.

Homepage (/) is NOT pushable via Admin API — set manually in
Online Store -> Preferences.

Run inside the API container:
    docker exec ols-api python3 /app/data/push_meta_to_shopify.py
"""
import json
import httpx

from app.services.shopify_service import _shopify_headers, _shopify_url

TARGETS = [
    {
        "kind": "page",
        "handle": "what-is-an-estate-sale",
        "title_tag": "Estate Sale Meaning: Complete Guide to Estate Sales",
        "description_tag": "Learn estate sale meaning, process & how they differ from garage sales. Get expert insights from Florida's estate sale professionals.",
    },
    {
        "kind": "article",
        "handle": "pros-and-cons-of-estate-sales",
        "title_tag": "Estate Sale Pros and Cons: Complete Guide for Families",
        "description_tag": "Discover the key advantages and drawbacks of estate sales. Get expert insights to help you decide if an estate sale is right for you.",
    },
    {
        "kind": "article",
        "handle": "estate-sale-vs-garage-sale-know-the-differences",
        "title_tag": "Estate Sale vs Garage Sale: Key Differences & When to Choose",
        "description_tag": "Estate sale vs garage sale: Learn the key differences, pricing, and when to use each option. Make the right choice for your needs.",
    },
]


def _get(path):
    r = httpx.get(_shopify_url(path), headers=_shopify_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def upsert_metafield(owner_resource, owner_id, key, value):
    """Create or update a metafield in the global namespace."""
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
            "namespace": "global",
            "key": key,
            "value": value,
            "type": "single_line_text_field",
        }}
        r = httpx.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return r.json()["metafield"]


def main():
    pages = {p["handle"]: p for p in _get("pages.json?limit=250")["pages"]}
    blogs = _get("blogs.json?limit=50")["blogs"]
    article_map = {}
    for b in blogs:
        for a in _get(f"blogs/{b['id']}/articles.json?limit=250")["articles"]:
            article_map[a["handle"]] = (b["id"], a["id"])

    results = []
    for t in TARGETS:
        if t["kind"] == "page":
            page = pages.get(t["handle"])
            if not page:
                results.append({"handle": t["handle"], "status": "not_found"})
                continue
            owner_resource, owner_id = "pages", page["id"]
        else:
            mapping = article_map.get(t["handle"])
            if not mapping:
                results.append({"handle": t["handle"], "status": "not_found"})
                continue
            owner_resource, owner_id = "articles", mapping[1]

        title_mf = upsert_metafield(owner_resource, owner_id, "title_tag", t["title_tag"])
        desc_mf = upsert_metafield(owner_resource, owner_id, "description_tag", t["description_tag"])
        results.append({
            "handle": t["handle"],
            "kind": t["kind"],
            "owner_id": owner_id,
            "status": "updated",
            "title_metafield_id": title_mf["id"],
            "desc_metafield_id": desc_mf["id"],
        })

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
