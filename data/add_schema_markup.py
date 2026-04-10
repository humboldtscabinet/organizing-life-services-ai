"""
Add LocalBusiness JSON-LD Schema Markup to the Shopify theme.

Creates a Liquid snippet (snippets/local-business-schema.liquid)
and injects an include tag into the theme's <head> section in theme.liquid.

Run inside Docker:
  docker exec ols-api python /app/data/add_schema_markup.py
"""

import os
import sys
import httpx

sys.path.insert(0, "/app")

STORE = os.getenv("SHOPIFY_STORE", "ols-online")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

# ── JSON-LD Schema for Organizing Life Services ──────────────────────
SCHEMA_SNIPPET = r"""
{%- comment -%}
  LocalBusiness + Service schema for SEO geographic targeting.
  Tells Google that OLS serves the Greater Tampa Bay Area, Florida only.
  Auto-generated — do not edit manually.
{%- endcomment -%}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Organizing Life Services",
  "description": "Professional estate sale company serving the Greater Tampa Bay Area, Florida. Full-service estate sales, liquidation, personal property appraisals, and cleanouts.",
  "url": "https://organizinglifeservices.com",
  "telephone": "+1-727-542-6028",
  "email": "info@organizinglifeservices.com",
  "image": "https://organizinglifeservices.com/cdn/shop/files/OLS-logo.png",
  "priceRange": "$$",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "Palm Harbor",
    "addressRegion": "FL",
    "postalCode": "34683",
    "addressCountry": "US"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 28.0836,
    "longitude": -82.7632
  },
  "areaServed": [
    {
      "@type": "County",
      "name": "Pinellas County",
      "containedInPlace": {
        "@type": "State",
        "name": "Florida"
      }
    },
    {
      "@type": "County",
      "name": "Hillsborough County",
      "containedInPlace": {
        "@type": "State",
        "name": "Florida"
      }
    },
    {
      "@type": "County",
      "name": "Pasco County",
      "containedInPlace": {
        "@type": "State",
        "name": "Florida"
      }
    },
    {
      "@type": "County",
      "name": "Hernando County",
      "containedInPlace": {
        "@type": "State",
        "name": "Florida"
      }
    },
    {
      "@type": "County",
      "name": "Citrus County",
      "containedInPlace": {
        "@type": "State",
        "name": "Florida"
      }
    },
    {
      "@type": "County",
      "name": "Manatee County",
      "containedInPlace": {
        "@type": "State",
        "name": "Florida"
      }
    }
  ],
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "Estate Sale Services",
    "itemListElement": [
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "Estate Sales",
          "description": "Full-service estate sales with professional pricing, staging, marketing, and management."
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "Estate Liquidation",
          "description": "Complete estate liquidation services including buyouts and consignment."
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "Personal Property Appraisals",
          "description": "Certified personal property appraisals for probate, insurance, divorce, and tax purposes."
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "Estate Cleanouts",
          "description": "Post-sale cleanout services including donation coordination and disposal."
        }
      }
    ]
  },
  "openingHoursSpecification": [
    {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
      "opens": "09:00",
      "closes": "17:00"
    }
  ],
  "sameAs": [
    "https://www.facebook.com/OrganizingLifeServices",
    "https://www.instagram.com/organizinglifeservices"
  ]
}
</script>
""".strip()


def get_access_token():
    """Get Shopify access token."""
    client_id = os.getenv("SHOPIFY_CLIENT_ID")
    client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")

    resp = httpx.post(
        f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("access_token")


def shopify_api(method, endpoint, json_data=None):
    """Make a Shopify Admin API call."""
    token = get_access_token()
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }
    url = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}/{endpoint}"

    if method == "GET":
        resp = httpx.get(url, headers=headers, timeout=30)
    elif method == "PUT":
        resp = httpx.put(url, headers=headers, json=json_data, timeout=30)
    else:
        raise ValueError(f"Unsupported method: {method}")

    resp.raise_for_status()
    return resp.json()


def get_main_theme_id():
    """Get the ID of the currently published (main) theme."""
    data = shopify_api("GET", "themes.json")
    themes = data.get("themes", [])
    for theme in themes:
        if theme.get("role") == "main":
            return theme["id"]
    raise RuntimeError("No main theme found!")


def upload_snippet(theme_id):
    """Upload the local-business-schema.liquid snippet."""
    print(f"  Uploading snippet to theme {theme_id}...")
    shopify_api(
        "PUT",
        f"themes/{theme_id}/assets.json",
        {
            "asset": {
                "key": "snippets/local-business-schema.liquid",
                "value": SCHEMA_SNIPPET,
            }
        },
    )
    print("  [OK] snippets/local-business-schema.liquid uploaded")


def inject_include_in_theme(theme_id):
    """
    Add {% render 'local-business-schema' %} to theme.liquid's <head>.

    Only adds it if it's not already present.
    """
    print(f"  Reading theme.liquid from theme {theme_id}...")
    data = shopify_api(
        "GET",
        f"themes/{theme_id}/assets.json?asset[key]=layout/theme.liquid",
    )
    theme_liquid = data.get("asset", {}).get("value", "")

    if not theme_liquid:
        print("  [ERR] Could not read theme.liquid!")
        return False

    # Check if already injected
    if "local-business-schema" in theme_liquid:
        print("  [SKIP] Schema include already present in theme.liquid")
        return True

    # Inject right before </head>
    include_tag = "  {% render 'local-business-schema' %}\n"
    if "</head>" in theme_liquid:
        theme_liquid = theme_liquid.replace(
            "</head>",
            f"{include_tag}</head>",
        )
    elif "</HEAD>" in theme_liquid:
        theme_liquid = theme_liquid.replace(
            "</HEAD>",
            f"{include_tag}</HEAD>",
        )
    else:
        print("  [ERR] Could not find </head> tag in theme.liquid!")
        return False

    # Upload the modified theme.liquid
    print("  Uploading modified theme.liquid...")
    shopify_api(
        "PUT",
        f"themes/{theme_id}/assets.json",
        {
            "asset": {
                "key": "layout/theme.liquid",
                "value": theme_liquid,
            }
        },
    )
    print("  [OK] theme.liquid updated with schema include")
    return True


def main():
    print("=" * 60)
    print("OLS — LocalBusiness Schema Markup Installer")
    print("=" * 60)
    print()

    # Step 1: Get the main theme
    print("[1/3] Finding main theme...")
    theme_id = get_main_theme_id()
    print(f"  Main theme ID: {theme_id}")

    # Step 2: Upload the snippet
    print("[2/3] Uploading schema snippet...")
    upload_snippet(theme_id)

    # Step 3: Inject the include into theme.liquid
    print("[3/3] Injecting include into theme.liquid <head>...")
    success = inject_include_in_theme(theme_id)

    print()
    if success:
        print("SUCCESS! LocalBusiness schema is now live on every page.")
        print("Verify at: https://search.google.com/test/rich-results")
        print("  Enter: https://organizinglifeservices.com")
    else:
        print("PARTIAL: Snippet uploaded but theme.liquid injection failed.")
        print("You may need to manually add this to your theme's <head>:")
        print("  {% render 'local-business-schema' %}")


if __name__ == "__main__":
    main()
