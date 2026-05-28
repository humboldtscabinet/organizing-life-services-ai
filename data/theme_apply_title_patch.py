"""Apply the round-3 title-tag patch to a Shopify theme.

The patch modifies layout/theme.liquid so that when a `global.title_tag`
metafield is set on the current resource (article/page/product/collection/blog),
the theme renders the metafield value verbatim WITHOUT appending the
shop.name brand suffix. Pages without a title_tag metafield continue to
get the existing brand append.

Usage (recommended workflow):
  1. In Shopify admin: Online Store -> Themes -> click "..." on
     "Vt-kitchor-home-3" -> Duplicate. Wait for the new theme to appear.
  2. Find the duplicate's numeric ID (or just let this script list themes
     and pick interactively).
  3. Preview / verify the patch:
        python data/theme_apply_title_patch.py --theme-id <ID> --dry-run
  4. Apply:
        python data/theme_apply_title_patch.py --theme-id <ID>
  5. In Shopify admin, click "Preview" on the duplicate theme and open
     several articles/pages. Confirm the <title> is now ~40-60 chars and
     no longer ends with "Organizing Life Services - Estate Sale Company".
  6. When satisfied, click "Publish" on the duplicate in Shopify admin.

Idempotent: if the theme is already patched the script reports it and exits 0.
"""
import argparse
import difflib
import os
import sys
import re

import httpx

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


PATCH_MARKER = "assign has_custom_title_tag = false"

PATCH_BLOCK = (
    "  {%- liquid\n"
    "    assign has_custom_title_tag = false\n"
    "    if article.metafields.global.title_tag != blank\n"
    "      assign has_custom_title_tag = true\n"
    "    elsif page.metafields.global.title_tag != blank\n"
    "      assign has_custom_title_tag = true\n"
    "    elsif product.metafields.global.title_tag != blank\n"
    "      assign has_custom_title_tag = true\n"
    "    elsif collection.metafields.global.title_tag != blank\n"
    "      assign has_custom_title_tag = true\n"
    "    elsif blog.metafields.global.title_tag != blank\n"
    "      assign has_custom_title_tag = true\n"
    "    endif\n"
    "  -%}\n"
)


def list_themes():
    return httpx.get(f"{BASE}/themes.json", headers=H, timeout=30).json()["themes"]


def get_asset(theme_id, key):
    r = httpx.get(f"{BASE}/themes/{theme_id}/assets.json", headers=H,
                  params={"asset[key]": key}, timeout=30)
    r.raise_for_status()
    return r.json()["asset"]


def put_asset(theme_id, key, value):
    body = {"asset": {"key": key, "value": value}}
    r = httpx.put(f"{BASE}/themes/{theme_id}/assets.json", headers=H,
                  json=body, timeout=60)
    r.raise_for_status()
    return r.json()["asset"]


def apply_patch(source: str) -> tuple[str, str]:
    """Return (new_source, action) where action is 'patched' or 'noop'."""
    if PATCH_MARKER in source:
        return source, "noop"

    # The target line we modify (line 14 in the audited theme):
    # locate the exact `<title>` block opening
    title_open_re = re.compile(r"(?m)^(\s*)<title>\s*$")
    match = title_open_re.search(source)
    if not match:
        raise RuntimeError(
            "Could not locate `<title>` open tag in layout/theme.liquid; "
            "theme may have an unexpected structure — abort."
        )
    insert_at = match.end() + 1  # position just past the newline after <title>

    # The brand-append clause we widen
    brand_append_re = re.compile(
        r"\{%\s*unless\s+page_title\s+contains\s+shop\.name\s*%\}"
    )
    if not brand_append_re.search(source):
        raise RuntimeError(
            "Could not locate `{% unless page_title contains shop.name %}` — "
            "theme may have already been customised; abort."
        )

    # Step 1: insert the liquid assign block right after <title>
    new_source = source[:insert_at] + PATCH_BLOCK + source[insert_at:]

    # Step 2: widen the brand-append condition
    new_source = brand_append_re.sub(
        "{% unless has_custom_title_tag or page_title contains shop.name %}",
        new_source,
        count=1,
    )
    return new_source, "patched"


def show_diff(before: str, after: str, key: str):
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{key}",
        tofile=f"b/{key}",
        n=4,
    )
    sys.stdout.writelines(diff)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme-id", type=int, help="Target theme ID (unpublished duplicate)")
    ap.add_argument("--dry-run", action="store_true", help="Print diff but don't push")
    ap.add_argument("--list", action="store_true", help="Just list themes and exit")
    args = ap.parse_args()

    themes = list_themes()
    if args.list or not args.theme_id:
        print("Themes in store:")
        for t in themes:
            print(f"  id={t['id']:>14}  role={t['role']:<12} name={t['name']!r}")
        if args.list:
            return
        sys.exit("\nPass --theme-id <ID> for the duplicate you want to patch.")

    target = next((t for t in themes if t["id"] == args.theme_id), None)
    if not target:
        sys.exit(f"Theme {args.theme_id} not found in store.")
    if target["role"] == "main":
        sys.exit(
            "REFUSING to patch the LIVE theme (role=main). "
            "Duplicate it in Shopify admin first, then pass the duplicate's --theme-id."
        )
    print(f"[patch] target theme: id={target['id']}  role={target['role']}  name={target['name']!r}")

    asset = get_asset(target["id"], "layout/theme.liquid")
    before = asset["value"]
    after, action = apply_patch(before)

    if action == "noop":
        print("[patch] theme already contains the patch marker — nothing to do. Exit.")
        return

    print(f"\n[patch] diff for layout/theme.liquid:\n")
    show_diff(before, after, "layout/theme.liquid")

    if args.dry_run:
        print("\n[patch] --dry-run set, no changes pushed.")
        return

    print("\n[patch] pushing patched layout/theme.liquid ...")
    put_asset(target["id"], "layout/theme.liquid", after)
    print("[patch] done.")
    print("\nNext: open Shopify admin -> Online Store -> Themes,")
    print(f"      click 'Preview' on theme id={target['id']}, then open a few articles to confirm titles are short.")


if __name__ == "__main__":
    main()
