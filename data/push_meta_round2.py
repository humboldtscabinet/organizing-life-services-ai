"""Round 2 — push 3 approved meta rewrites to Shopify.

Run inside the API container:
    docker exec ols-api python3 /app/data/push_meta_round2.py
"""
import json
import httpx

from app.services.shopify_service import _shopify_headers, _shopify_url

TARGETS = [
    {
        "kind": "article",
        "handle": "pros-and-cons-of-estate-sales",
        "title_tag": "Estate Sale Pros & Cons | Florida Estate Sale Company Guide",
        "description_tag": "Weighing an estate sale? Get the pros, cons & costs from Tampa Bay's estate sale pros — Pinellas, Pasco & Hillsborough. Free consult. Call today.",
    },
    {
        "kind": "article",
        "handle": "estate-sales-near-me-your-ultimate-guide-to-local-finds",
        "title_tag": "Estate Sales Near Me: Tampa Bay Local Finds Guide 2026",
        "description_tag": "Find estate sales near you in Pinellas, Pasco & Hillsborough. Local finds, schedules & insider tips from Florida's trusted estate sale company.",
    },
    {
        "kind": "page",
        "handle": "estate-cleanout-services",
        "title_tag": "Estate Cleanout Services Tampa Bay | Same-Week Service",
        "description_tag": "Full-service estate cleanouts in Pinellas, Pasco & Hillsborough. Sort, donate, dispose, sell. Insured & local. Free on-site estimate — call today.",
    },
]


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
                results.append({"handle": t["handle"], "status": "not_found"}); continue
            owner_resource, owner_id = "pages", page["id"]
        else:
            mapping = article_map.get(t["handle"])
            if not mapping:
                results.append({"handle": t["handle"], "status": "not_found"}); continue
            owner_resource, owner_id = "articles", mapping[1]

        title_mf = upsert_metafield(owner_resource, owner_id, "title_tag", t["title_tag"])
        desc_mf = upsert_metafield(owner_resource, owner_id, "description_tag", t["description_tag"])
        results.append({
            "handle": t["handle"], "kind": t["kind"], "owner_id": owner_id,
            "status": "updated",
            "title_metafield_id": title_mf["id"],
            "desc_metafield_id": desc_mf["id"],
        })

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
