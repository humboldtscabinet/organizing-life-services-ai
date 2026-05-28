"""Apply homepage internal-links block to live Shopify theme.

Adds a small SEO links section, conditional on `template.name == 'index'`,
just before `{%- include 'cookie-policy' -%}` in layout/theme.liquid.

Anchors point to /pages/estate-cleanout-services using:
  - "estate cleanout experts"
  - "deceased estate house clearing services"

Idempotent via marker SEO-INTLINKS-V1.
"""
import argparse
import os
import sys
import time
import httpx

STORE = os.getenv("SHOPIFY_STORE")
CID = os.getenv("SHOPIFY_CLIENT_ID")
CS = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")

MARKER = "SEO-INTLINKS-V1"

BLOCK = """    {%- if template.name == 'index' -%}
    {%- comment -%} SEO-INTLINKS-V1: estate-cleanout-services anchors {%- endcomment -%}
    <section class=\"ols-home-intlinks\" aria-label=\"Estate cleanout resources\" style=\"max-width:1200px;margin:30px auto;padding:24px 16px;border-top:1px solid #eee;font-size:15px;line-height:1.6;color:#333;\">
      <h2 style=\"font-size:18px;margin:0 0 12px;font-weight:600;\">Estate Cleanout Resources for Tampa Bay</h2>
      <p style=\"margin:0;\">Looking for full-service help? Our team of <a href=\"/pages/estate-cleanout-services\">estate cleanout experts</a> handles same-week house clearings across Pinellas, Pasco, Hillsborough, Hernando, and Citrus counties. We also offer compassionate <a href=\"/pages/estate-cleanout-services\">deceased estate house clearing services</a> for families managing a loved one's belongings.</p>
    </section>
    {%- endif -%}
"""

ANCHOR = "{%- include 'cookie-policy' -%}"


def _token():
    r = httpx.post(f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CID, "client_secret": CS, "grant_type": "client_credentials"},
        timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme-id", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not all([STORE, CID, CS]):
        sys.exit("Missing SHOPIFY creds")

    tok = _token()
    H = {"X-Shopify-Access-Token": tok, "Content-Type": "application/json"}
    BASE = f"https://{STORE}.myshopify.com/admin/api/{API_VER}"

    # refuse live theme unless explicit; here we WANT the live one since user already published patched theme
    themes = httpx.get(f"{BASE}/themes.json", headers=H, timeout=30).json()["themes"]
    target = next(t for t in themes if t["id"] == args.theme_id)
    print(f"[intlinks] target theme {target['id']} ({target['name']}) role={target['role']}")

    r = httpx.get(f"{BASE}/themes/{args.theme_id}/assets.json", headers=H,
                  params={"asset[key]": "layout/theme.liquid"}, timeout=60)
    r.raise_for_status()
    src = r.json()["asset"]["value"]

    if MARKER in src:
        print(f"[intlinks] marker {MARKER} already present — nothing to do")
        return

    if ANCHOR not in src:
        sys.exit(f"[intlinks] anchor not found: {ANCHOR!r}")

    new_src = src.replace(ANCHOR, BLOCK + "    " + ANCHOR, 1)
    if MARKER not in new_src:
        sys.exit("[intlinks] insertion failed — marker not present after patch")

    print(f"[intlinks] {len(src)} -> {len(new_src)} chars (+{len(new_src) - len(src)})")

    if args.dry_run:
        print("[intlinks] DRY RUN — not writing")
        return

    put = httpx.put(f"{BASE}/themes/{args.theme_id}/assets.json", headers=H,
                    json={"asset": {"key": "layout/theme.liquid", "value": new_src}},
                    timeout=60)
    put.raise_for_status()
    print("[intlinks] live theme updated.")


if __name__ == "__main__":
    main()
