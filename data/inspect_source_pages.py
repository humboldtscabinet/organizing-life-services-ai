"""Inspect candidate Shopify pages/articles for internal-link placement."""
import json
import httpx
from app.services.shopify_service import _shopify_headers, _shopify_url


def g(p):
    return httpx.get(_shopify_url(p), headers=_shopify_headers(), timeout=30).json()


def main():
    pages = g("pages.json?limit=250")["pages"]
    out = {}
    for h in ["personal-property-appraisal", "what-is-an-estate-sale",
              "estate-liquidation", "estate-cleanout-services"]:
        p = next((x for x in pages if x["handle"] == h), None)
        if p:
            out[h] = {"kind": "page", "id": p["id"], "body_len": len(p["body_html"]),
                      "body_html": p["body_html"]}

    blogs = g("blogs.json?limit=50")["blogs"]
    for b in blogs:
        bid = b["id"]
        arts = g(f"blogs/{bid}/articles.json?limit=250")["articles"]
        for h in ["pros-and-cons-of-estate-sales",
                  "estate-sale-vs-garage-sale-know-the-differences",
                  "estate-sales-near-me-your-ultimate-guide-to-local-finds"]:
            a = next((x for x in arts if x["handle"] == h), None)
            if a:
                out[h] = {"kind": "article", "blog_id": bid, "id": a["id"],
                          "body_len": len(a["body_html"]), "body_html": a["body_html"]}

    with open("/tmp/source_pages.json", "w") as f:
        json.dump(out, f)
    for k, v in out.items():
        print(f"{k:60s} {v['kind']:8s} id={v['id']} body_len={v['body_len']}")


if __name__ == "__main__":
    main()
