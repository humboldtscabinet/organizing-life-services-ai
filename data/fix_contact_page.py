"""
Fix Contact Page & Add /pages/contact Redirect

This script does three things:
  1. Replaces the /pages/contact-us body with proper NAP HTML content
     (Name, Address, Phone) so Google can read it — not just a Maps iframe.
  2. Creates a /pages/contact page that redirects to /pages/contact-us
     so the 404 is resolved.
  3. Updates the Shopify redirect list so /pages/contact → /pages/contact-us.

Run inside Docker:
  docker exec ols-api python /app/data/fix_contact_page.py
"""

import os
import sys
import httpx

sys.path.insert(0, "/app")

STORE = os.getenv("SHOPIFY_STORE", "ols-online")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

# ── Contact Page HTML Content ─────────────────────────────────────────
# Visible NAP (Name, Address, Phone) content + embedded map.
# This replaces the bare iframe that had no readable content.
CONTACT_PAGE_BODY = """
<div class="ols-contact-page" style="max-width:800px;margin:0 auto;padding:2rem 1rem;font-family:inherit;">

  <h1 style="font-size:2rem;margin-bottom:0.5rem;">Contact Organizing Life Services</h1>
  <p style="font-size:1.1rem;color:#555;margin-bottom:2rem;">
    We serve clients throughout the Greater Tampa Bay Area. Estate sales are conducted
    on-site at our clients' properties. Reach out to schedule a free consultation.
  </p>

  <div style="display:flex;flex-wrap:wrap;gap:2rem;margin-bottom:2.5rem;">

    <div style="flex:1;min-width:220px;">
      <h2 style="font-size:1.2rem;margin-bottom:0.75rem;">📞 Phone</h2>
      <p style="font-size:1.1rem;">
        <a href="tel:+17275426028" style="color:inherit;text-decoration:none;">
          (727) 542-6028
        </a>
      </p>
      <p style="color:#555;font-size:0.95rem;">Available 7 days a week, 9am–5pm</p>
    </div>

    <div style="flex:1;min-width:220px;">
      <h2 style="font-size:1.2rem;margin-bottom:0.75rem;">✉️ Email</h2>
      <p style="font-size:1.1rem;">
        <a href="mailto:info@organizinglifeservices.com" style="color:inherit;text-decoration:none;">
          info@organizinglifeservices.com
        </a>
      </p>
    </div>

    <div style="flex:1;min-width:220px;">
      <h2 style="font-size:1.2rem;margin-bottom:0.75rem;">📬 Mailing Address</h2>
      <address style="font-style:normal;line-height:1.6;">
        Organizing Life Services<br>
        5005 W Laurel St, Suite 100 PMB1048<br>
        Tampa, FL 33607
      </address>
      <p style="color:#555;font-size:0.9rem;margin-top:0.5rem;">
        Estate sales are conducted on-site at client properties throughout Tampa Bay.
      </p>
    </div>

  </div>

  <div style="margin-bottom:2.5rem;">
    <h2 style="font-size:1.2rem;margin-bottom:0.75rem;">🗺️ Service Area</h2>
    <p style="color:#444;">
      We provide estate sale services across <strong>Pinellas</strong>,
      <strong>Hillsborough</strong>, <strong>Pasco</strong>, <strong>Hernando</strong>,
      and <strong>Citrus</strong> counties in Florida.
      Out-of-state clients welcome — we can plan your sale entirely by phone.
    </p>
  </div>

  <div style="margin-bottom:2.5rem;">
    <h2 style="font-size:1.2rem;margin-bottom:1rem;">📍 Tampa Bay Service Area</h2>
    <iframe
      title="Organizing Life Services — Tampa Bay Service Area"
      src="https://www.google.com/maps/embed?api=1&q=Tampa+Bay,+Florida"
      width="100%"
      height="350"
      style="border:0;border-radius:8px;"
      allowfullscreen=""
      loading="lazy"
      referrerpolicy="no-referrer-when-downgrade">
    </iframe>
  </div>

  <div>
    <h2 style="font-size:1.2rem;margin-bottom:0.75rem;">📅 Schedule a Free Consultation</h2>
    <p>
      Call us at <a href="tel:+17275426028">(727) 542-6028</a> or email
      <a href="mailto:info@organizinglifeservices.com">info@organizinglifeservices.com</a>
      to get started. We're happy to walk through your situation and explain exactly
      how the process works — with no obligation.
    </p>
  </div>

</div>
""".strip()


def get_access_token():
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
    elif method == "POST":
        resp = httpx.post(url, headers=headers, json=json_data, timeout=30)
    else:
        raise ValueError(f"Unsupported method: {method}")
    resp.raise_for_status()
    return resp.json()


def get_page_by_handle(handle):
    """Find a Shopify page by its URL handle. Returns the page dict or None."""
    data = shopify_api("GET", f"pages.json?handle={handle}&limit=1")
    pages = data.get("pages", [])
    return pages[0] if pages else None


def update_contact_us_page():
    """Replace the /pages/contact-us body with proper NAP content."""
    print("[1/2] Updating /pages/contact-us with NAP content...")
    page = get_page_by_handle("contact-us")
    if not page:
        print("  [ERR] Could not find contact-us page. Creating it...")
        data = shopify_api(
            "POST",
            "pages.json",
            {
                "page": {
                    "title": "Contact Us",
                    "handle": "contact-us",
                    "body_html": CONTACT_PAGE_BODY,
                    "published": True,
                }
            },
        )
        print(f"  [OK] Created contact-us page (ID: {data['page']['id']})")
        return

    page_id = page["id"]
    shopify_api(
        "PUT",
        f"pages/{page_id}.json",
        {
            "page": {
                "id": page_id,
                "body_html": CONTACT_PAGE_BODY,
            }
        },
    )
    print(f"  [OK] Updated contact-us page (ID: {page_id}) with NAP content")


def create_contact_redirect():
    """
    Create a Shopify URL redirect: /pages/contact → /pages/contact-us
    If the redirect already exists, skip it.
    """
    print("[2/2] Creating /pages/contact → /pages/contact-us redirect...")

    # Check if redirect already exists
    data = shopify_api("GET", "redirects.json?path=%2Fpages%2Fcontact&limit=5")
    existing = data.get("redirects", [])
    for r in existing:
        if r.get("path") == "/pages/contact":
            print(f"  [SKIP] Redirect already exists (ID: {r['id']})")
            return

    # Create it
    result = shopify_api(
        "POST",
        "redirects.json",
        {
            "redirect": {
                "path": "/pages/contact",
                "target": "/pages/contact-us",
            }
        },
    )
    print(f"  [OK] Redirect created (ID: {result['redirect']['id']})")


def main():
    print("=" * 60)
    print("OLS — Contact Page Fix & /pages/contact Redirect")
    print("=" * 60)
    print()

    update_contact_us_page()
    print()
    create_contact_redirect()

    print()
    print("Done.")
    print("  Contact page: https://organizinglifeservices.com/pages/contact-us")
    print("  Redirect:     https://organizinglifeservices.com/pages/contact")
    print()
    print("Next: Run add_schema_markup.py to push the updated schema with the")
    print("      corrected mailing address to the live theme.")


if __name__ == "__main__":
    main()
