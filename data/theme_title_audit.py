"""Audit the active Shopify theme to find the <title> generation logic.

Read-only. Lists themes, picks the live one, fetches layout/theme.liquid
and any snippet that mentions page_title or shop.name, prints them with
line numbers so we can craft a precise patch.

Usage:
    python data/theme_title_audit.py
"""
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

STORE = os.getenv("SHOPIFY_STORE")
CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")

if not all([STORE, CLIENT_ID, CLIENT_SECRET]):
    sys.exit("Missing SHOPIFY_STORE / SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET in .env")


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


def get(path):
    r = httpx.get(f"{BASE}/{path}", headers=H, timeout=30)
    r.raise_for_status()
    return r.json()


def list_themes():
    return get("themes.json")["themes"]


def list_assets(theme_id):
    return get(f"themes/{theme_id}/assets.json")["assets"]


def get_asset(theme_id, key):
    r = httpx.get(f"{BASE}/themes/{theme_id}/assets.json",
                  headers=H, params={"asset[key]": key}, timeout=30)
    r.raise_for_status()
    return r.json()["asset"]


def main():
    themes = list_themes()
    live = next((t for t in themes if t.get("role") == "main"), None)
    if not live:
        sys.exit("No live (role=main) theme found")
    print(f"[theme] live theme: id={live['id']}  name={live['name']!r}  role={live['role']}")

    assets = list_assets(live["id"])
    # Find candidates: layout/theme.liquid, anything with 'meta' or 'head' in name
    candidates = [a["key"] for a in assets
                  if a["key"] in ("layout/theme.liquid",)
                  or "meta-tag" in a["key"].lower()
                  or "head" in a["key"].lower()
                  or a["key"].startswith("snippets/seo")]
    print(f"[theme] {len(candidates)} candidate files to inspect:")
    for k in candidates:
        print(f"  - {k}")

    hits = []
    for key in candidates:
        try:
            asset = get_asset(live["id"], key)
        except Exception as e:
            print(f"  ! skip {key}: {e}")
            continue
        body = asset.get("value") or asset.get("attachment") or ""
        if not isinstance(body, str):
            continue
        lines = body.splitlines()
        for i, ln in enumerate(lines, 1):
            low = ln.lower()
            if "page_title" in low or "<title" in low or "shop.name" in low:
                hits.append((key, i, ln))

    print(f"\n[theme] {len(hits)} relevant lines found:\n")
    last_key = None
    for key, lineno, ln in hits:
        if key != last_key:
            print(f"\n--- {key} ---")
            last_key = key
        print(f"  L{lineno:>4}  {ln.rstrip()}")

    # Save the full layout/theme.liquid locally for reference
    try:
        layout = get_asset(live["id"], "layout/theme.liquid")
        out_path = "data/audit_output/theme_layout_snapshot.liquid"
        with open(out_path, "w") as f:
            f.write(layout.get("value") or "")
        print(f"\n[theme] saved snapshot: {out_path}")
    except Exception as e:
        print(f"[theme] could not snapshot layout: {e}")


if __name__ == "__main__":
    main()
