"""Verify quick-wins session: SD page markers, top-4 FAQ markers, A4 intlinks markers."""
import os
import time
import httpx

STORE = os.getenv("SHOPIFY_STORE"); CID = os.getenv("SHOPIFY_CLIENT_ID")
CS = os.getenv("SHOPIFY_CLIENT_SECRET"); API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")
BLOG_ID = 52179501100

SD_PAGES = [
    ("estate-sale-citrus-county", "SD-ESNM-V1"),
    ("tarpon-springs-estate-sale-in-woodfield", "SD-ESTS-V1"),
    ("personal-property-appraisal", "SD-TPPA-V1"),
    ("downsizing-moving-sales", "SD-DSPC-V1"),
]
FAQ_ARTICLES = [
    ("pros-and-cons-of-estate-sales", "FAQ-PCES-V1"),
    ("how-to-increase-your-home-appraisal-value", "FAQ-HIAV-V1"),
    ("estate-auction-vs-estate-sale-pros-and-cons", "FAQ-EAES-V1"),
    ("the-ultimate-guide-for-barbie-collector-buyers", "FAQ-BARB-V1"),
]
A4_ARTICLES = [
    "estate-sale-vs-garage-sale-know-the-differences",
    "pros-and-cons-of-estate-sales",
    "how-to-increase-your-home-appraisal-value",
    "estate-auction-vs-estate-sale-pros-and-cons",
    "the-ultimate-guide-for-barbie-collector-buyers",
    "how-to-plan-estate-sale",
]
A4_MARKER = "INTLINKS-A4-V1"


def main():
    tok = httpx.post(f"https://{STORE}.myshopify.com/admin/oauth/access_token",
        json={"client_id": CID, "client_secret": CS, "grant_type": "client_credentials"},
        timeout=30).json()["access_token"]
    H = {"X-Shopify-Access-Token": tok}
    BASE = f"https://{STORE}.myshopify.com/admin/api/{API_VER}"

    pages = httpx.get(f"{BASE}/pages.json?limit=250", headers=H, timeout=30).json()["pages"]
    pmap = {p["handle"]: p for p in pages}
    print("=== SD PAGE MARKERS ===")
    ok = 0
    for h, m in SD_PAGES:
        body = (pmap.get(h) or {}).get("body_html", "") or ""
        present = m in body
        ok += int(present)
        print(f"  {'OK ' if present else 'MISS'} {h}: {m} -> {present} ({len(body)} chars)")
    print(f"  ==> {ok}/{len(SD_PAGES)} SD markers present")

    by_handle = {}
    next_url = f"{BASE}/blogs/{BLOG_ID}/articles.json?limit=250&fields=id,handle"
    while next_url:
        r = httpx.get(next_url, headers=H, timeout=30)
        for a in r.json().get("articles", []):
            by_handle[a["handle"]] = a["id"]
        next_url = None
        for part in r.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
        time.sleep(0.3)

    print("\n=== FAQ ARTICLE MARKERS + FAQPage schema ===")
    ok = 0
    for h, m in FAQ_ARTICLES:
        aid = by_handle.get(h)
        body = httpx.get(f"{BASE}/blogs/{BLOG_ID}/articles/{aid}.json", headers=H,
                         timeout=30).json()["article"]["body_html"] or ""
        m_ok = m in body
        s_ok = '"FAQPage"' in body
        ok += int(m_ok and s_ok)
        print(f"  {'OK ' if (m_ok and s_ok) else 'MISS'} {h}: marker={m_ok} schema={s_ok}")
        time.sleep(0.3)
    print(f"  ==> {ok}/{len(FAQ_ARTICLES)} FAQ articles fully present")

    print("\n=== A4 INTLINK MARKERS ===")
    ok = 0
    for h in A4_ARTICLES:
        aid = by_handle.get(h)
        body = httpx.get(f"{BASE}/blogs/{BLOG_ID}/articles/{aid}.json", headers=H,
                         timeout=30).json()["article"]["body_html"] or ""
        present = A4_MARKER in body
        ok += int(present)
        print(f"  {'OK ' if present else 'MISS'} {h}: {present}")
        time.sleep(0.3)
    print(f"  ==> {ok}/{len(A4_ARTICLES)} A4 markers present")


if __name__ == "__main__":
    main()
