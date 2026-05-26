"""Push seo-schema.liquid snippet to active Shopify theme + inject include into theme.liquid.

Idempotent: re-running won't double-inject.
"""
import json
import sys
import httpx

from app.services.shopify_service import _shopify_headers, _shopify_url

INCLUDE_LINE = "  {% render 'seo-schema' %}\n"
SNIPPET_KEY = "snippets/seo-schema.liquid"
THEME_KEY = "layout/theme.liquid"


def _get(path):
    r = httpx.get(_shopify_url(path), headers=_shopify_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def _put_asset(theme_id, key, value):
    url = _shopify_url(f"themes/{theme_id}/assets.json")
    body = {"asset": {"key": key, "value": value}}
    r = httpx.put(url, headers=_shopify_headers(), json=body, timeout=60)
    r.raise_for_status()
    return r.json()["asset"]


def _get_asset(theme_id, key):
    url = _shopify_url(f"themes/{theme_id}/assets.json?asset[key]={key}")
    r = httpx.get(url, headers=_shopify_headers(), timeout=30)
    r.raise_for_status()
    return r.json()["asset"]


def main(dry_run=False):
    themes = _get("themes.json")["themes"]
    main_theme = next((t for t in themes if t["role"] == "main"), None)
    if not main_theme:
        print("ERROR: no main theme found"); sys.exit(1)
    theme_id = main_theme["id"]
    print(f"Active theme: {main_theme['name']} (id={theme_id})")

    with open("/app/data/seo-schema.liquid") as f:
        snippet_value = f.read()

    if dry_run:
        print(f"[dry-run] would PUT {SNIPPET_KEY} ({len(snippet_value)} bytes)")
    else:
        asset = _put_asset(theme_id, SNIPPET_KEY, snippet_value)
        print(f"PUT {SNIPPET_KEY} -> updated_at={asset['updated_at']}")

    # Inject include into theme.liquid before </head> if not already present.
    layout = _get_asset(theme_id, THEME_KEY)["value"]
    if "render 'seo-schema'" in layout or 'render "seo-schema"' in layout:
        print("theme.liquid already includes seo-schema — skip injection.")
    else:
        if "</head>" not in layout:
            print("ERROR: </head> not found in theme.liquid — manual inject required")
            sys.exit(2)
        new_layout = layout.replace("</head>", INCLUDE_LINE + "</head>", 1)
        if dry_run:
            print(f"[dry-run] would inject include before </head> (layout {len(layout)} -> {len(new_layout)} bytes)")
        else:
            _put_asset(theme_id, THEME_KEY, new_layout)
            print(f"injected {INCLUDE_LINE.strip()} into theme.liquid before </head>")

    print("\nDone. Verify with:")
    print("  curl -s https://organizinglifeservices.com/ | grep -A1 'application/ld+json' | head -20")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
