"""Session-9: strip the public street address from the live LocalBusiness JSON-LD
(Option A — service-area business, no public storefront).

Context
-------
`session5_schema_intlinks_noindex.py` injected an enriched LocalBusiness block
(marker SCHEMA-LB-V2) that hard-codes a public street address:

    "streetAddress": "E LAKE RD S",
    "addressLocality": "Palm Harbor",
    "addressRegion": "FL",
    "postalCode": "34685"

Organizing Life Services has no public storefront — every estate sale is run
on-site at the client's property — so a pinned street address is both inaccurate
and a likely contributor to the GBP API "internal quality checks" denial
(2026-04-21). Google explicitly supports service-area businesses publishing only
`areaServed` with a region-level address.

This script replaces the SCHEMA-LB-V2 block with SCHEMA-LB-V3, identical in every
respect EXCEPT the address object is reduced to region + country only:

    "address": { "@type": "PostalAddress", "addressRegion": "FL", "addressCountry": "US" }

The rich `areaServed` (9 cities + 5 counties) is retained, so geographic
targeting is unaffected. The Tampa PMB mailbox is used ONLY as a mailing address
on the contact page (see fix_contact_page.py) — never as a schema street address.

Idempotency / safety
--------------------
- Skips if SCHEMA-LB-V3 is already present.
- Replaces the exact span from `<!-- SCHEMA-LB-V2 -->` to `<!-- /SCHEMA-LB-V2 -->`.
- The V3 block intentionally keeps the literal token "SCHEMA-LB-V2" inside an
  HTML comment. This is deliberate: session5's idempotency guard is
  `if 'SCHEMA-LB-V2' in theme`. Keeping the token means a later re-run of
  session5 still no-ops instead of appending a fresh street-address block.
- Snapshots theme.liquid before mutating.
- Supports --dry-run.

Run inside Docker:
  docker exec ols-api python /app/data/session9_strip_street_address.py --dry-run
  docker exec ols-api python /app/data/session9_strip_street_address.py
"""
import os
import sys
import time
from pathlib import Path

import httpx

STORE = os.getenv("SHOPIFY_STORE")
CID = os.getenv("SHOPIFY_CLIENT_ID")
CS = os.getenv("SHOPIFY_CLIENT_SECRET")
API = os.getenv("SHOPIFY_API_VERSION", "2024-10")

SNAPSHOT = Path("data/audit_output/theme_layout_snapshot_pre_session9.liquid")

V2_START = "<!-- SCHEMA-LB-V2 -->"
V2_END = "<!-- /SCHEMA-LB-V2 -->"

# Identical to session5's ENRICHED_LB EXCEPT:
#   - markers bumped to V3 (the opening comment keeps the literal "SCHEMA-LB-V2"
#     token so session5's idempotency guard still trips on re-run)
#   - address reduced to addressRegion + addressCountry (no street/locality/postal)
ENRICHED_LB_V3 = """<!-- SCHEMA-LB-V3 (supersedes SCHEMA-LB-V2; street address removed for service-area business) -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "@id": "https://organizinglifeservices.com/#organization",
  "name": "Organizing Life Services",
  "alternateName": "OLS Estate Sales",
  "description": "Tampa Bay's most trusted full-service estate sale company since 2010. Pricing, staging, marketing, sale-day staffing, appraisals, downsizing, and post-sale cleanout across Pinellas, Pasco, Hillsborough, Hernando, and Citrus counties.",
  "url": "https://organizinglifeservices.com/",
  "logo": "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_LOGO_PNG.png",
  "image": "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_LOGO_PNG.png",
  "telephone": "+17275426028",
  "email": "OrganizingLife@Hotmail.Com",
  "priceRange": "$$",
  "address": {
    "@type": "PostalAddress",
    "addressRegion": "FL",
    "addressCountry": "US"
  },
  "areaServed": [
    {"@type": "City", "name": "Palm Harbor"},
    {"@type": "City", "name": "Tarpon Springs"},
    {"@type": "City", "name": "Clearwater"},
    {"@type": "City", "name": "Dunedin"},
    {"@type": "City", "name": "St. Petersburg"},
    {"@type": "City", "name": "Largo"},
    {"@type": "City", "name": "Tampa"},
    {"@type": "City", "name": "New Port Richey"},
    {"@type": "City", "name": "Wesley Chapel"},
    {"@type": "AdministrativeArea", "name": "Pinellas County"},
    {"@type": "AdministrativeArea", "name": "Pasco County"},
    {"@type": "AdministrativeArea", "name": "Hillsborough County"},
    {"@type": "AdministrativeArea", "name": "Hernando County"},
    {"@type": "AdministrativeArea", "name": "Citrus County"}
  ],
  "sameAs": [
    "https://www.facebook.com/profile.php?id=100063703233651",
    "https://www.instagram.com/organizing_life_services"
  ],
  "openingHoursSpecification": [
    {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "opens": "09:00", "closes": "17:00"},
    {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Saturday"], "opens": "09:00", "closes": "15:00"}
  ],
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "Estate Sale & Liquidation Services",
    "itemListElement": [
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Estate Sales"}},
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Estate Cleanout & Liquidation"}},
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Personal Property Appraisals"}},
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Downsizing & Moving Sales"}},
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Senior Transition Services"}}
    ]
  }
}
</script>
<!-- /SCHEMA-LB-V3 -->"""


def _retry(fn, *a, **k):
    for i in range(6):
        try:
            r = fn(*a, **k)
            if hasattr(r, "status_code") and r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2 ** i)))
                continue
            return r
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            time.sleep(2 ** i)
    raise RuntimeError("retries exhausted")


def _token():
    r = _retry(
        httpx.post,
        f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CID, "client_secret": CS, "grant_type": "client_credentials"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _main_theme_id(B, H):
    themes = _retry(httpx.get, f"{B}/themes.json", headers=H, timeout=30).json()["themes"]
    main = next((t for t in themes if t.get("role") == "main"), None)
    if not main:
        sys.exit("ERROR: no main theme found")
    print(f"  active theme: {main['name']} (id={main['id']})")
    return main["id"]


def main(dry_run=False):
    if not all([STORE, CID, CS]):
        sys.exit("Missing SHOPIFY_STORE / SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET")

    H = {"X-Shopify-Access-Token": _token(), "Content-Type": "application/json"}
    B = f"https://{STORE}.myshopify.com/admin/api/{API}"

    theme_id = _main_theme_id(B, H)
    asset = _retry(
        httpx.get,
        f"{B}/themes/{theme_id}/assets.json?asset[key]=layout/theme.liquid",
        headers=H,
        timeout=30,
    ).json()["asset"]
    body = asset["value"]

    if "SCHEMA-LB-V3" in body:
        print("  [skip] SCHEMA-LB-V3 already present — street address already stripped.")
        return

    start = body.find(V2_START)
    if start < 0:
        sys.exit(
            "ERROR: SCHEMA-LB-V2 block not found in theme.liquid. "
            "The live schema is not where expected — inspect manually before proceeding."
        )
    end = body.find(V2_END, start)
    if end < 0:
        sys.exit("ERROR: found V2 start marker but no closing marker — aborting to avoid corruption.")
    end += len(V2_END)

    new = body[:start] + ENRICHED_LB_V3 + body[end:]

    # Snapshot the pre-change theme exactly once.
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    if not SNAPSHOT.exists():
        SNAPSHOT.write_text(body)
        print(f"  [snap] {SNAPSHOT} ({len(body)} chars)")

    print(f"  theme.liquid: {len(body)} -> {len(new)} chars")
    print("  replacing SCHEMA-LB-V2 -> SCHEMA-LB-V3 (address reduced to FL/US region only)")

    if dry_run:
        print("  [dry-run] no write performed. Review the planned change above.")
        # Show the stripped vs retained address for clarity.
        print("  [dry-run] new address object:")
        print('            { "@type": "PostalAddress", "addressRegion": "FL", "addressCountry": "US" }')
        return

    r = _retry(
        httpx.put,
        f"{B}/themes/{theme_id}/assets.json",
        headers=H,
        timeout=60,
        json={"asset": {"key": "layout/theme.liquid", "value": new}},
    )
    r.raise_for_status()
    print("  [ok] theme.liquid updated — public street address removed from schema.")
    print("\nVerify with:")
    print("  curl -s https://organizinglifeservices.com/ | grep -o '\"streetAddress\":[^,]*' || echo 'no streetAddress (correct)'")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
