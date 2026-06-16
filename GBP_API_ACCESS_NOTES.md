# Google Business Profile API Access Request

- **Case ID:** 7-8753000040474
- **Date submitted:** April 7, 2026
- **APIs requested:** Account Management API, Performance API, Business Information API
- **GCP Project:** ols-marketing-agent (Project Number: 330992031618)
- **Service Account:** ols-operations@ols-marketing-agent.iam.gserviceaccount.com

## Status
- **DENIED — April 21, 2026**
- Google email: "your account did not pass our internal quality checks"
- Root causes identified and remediation underway (see below)

## Root Causes & Fixes

| Issue | Fix | Status |
|---|---|---|
| Live `LocalBusiness` schema published a public street address (`E LAKE RD S`, Palm Harbor 34685) — but OLS is a service-area business with no public storefront (estate sales run on-site) | `session9_strip_street_address.py` reduces the schema address to region only (`addressRegion: FL`, `addressCountry: US`) and keeps the rich `areaServed` (9 cities + 5 counties). Logic validated offline (13/13 checks). | ⏳ Code ready — **deploy pending `.env`** |
| `/pages/contact` returned 404 | Shopify redirect `/pages/contact` → `/pages/contact-us` via `fix_contact_page.py` | ⏳ Code ready — deploy pending `.env` |
| Contact page was a bare Maps iframe with no readable NAP | `fix_contact_page.py` writes full NAP HTML — phone, email, **mailing address** (Tampa PMB, clearly labeled), hours, and a regional service-area map | ⏳ Code ready — deploy pending `.env` |

**Address strategy (Option A — no public street address):** OLS has no public storefront, so no `streetAddress` appears anywhere in structured data. The Tampa PMB — `5005 W Laurel St, Suite 100 PMB1048, Tampa, FL 33607` — is used **only** as a labeled mailing address on the contact page, never as a schema `streetAddress`. This matches Google's guidance for service-area businesses and is the cleanest posture for GBP reapproval. The live homepage schema is owned by `session5_schema_intlinks_noindex.py` (`SCHEMA-LB-V2`) → superseded by `session9` (`SCHEMA-LB-V3`).

## Deploy Steps (Run Before Reapplying)

> Requires the gitignored `.env` (Shopify credentials) in the repo root and Colima/Docker running. `.env` is **not** in this checkout — copy it from the machine where the SEO sessions ran, or recreate it from `.env.example`.

```bash
# 0. Start runtime (if not already up)
colima start && docker compose up -d api

# 1. Strip the public street address from the live schema (dry-run first)
docker exec ols-api python /app/data/session9_strip_street_address.py --dry-run
docker exec ols-api python /app/data/session9_strip_street_address.py

# 2. Fix the contact page + create the /pages/contact redirect
docker exec ols-api python /app/data/fix_contact_page.py
```

## Reapplication Checklist
- [ ] Add `.env` with Shopify creds, then run the Deploy Steps above
- [ ] Verify schema at https://search.google.com/test/rich-results — confirm **no** `streetAddress` and `areaServed` intact
- [ ] Verify /pages/contact no longer 404s (301 → /pages/contact-us)
- [ ] Verify /pages/contact-us shows the labeled mailing address (not just a map iframe)
- [ ] In reapplication, use this use case statement:
  > "Internal operations dashboard to monitor performance metrics for a single
  > owned-and-operated Google Business Profile listing. No third-party access.
  > The application is a self-hosted FastAPI service used exclusively by the
  > business owner to pull GBP performance data into a private Google Sheet
  > for review and planning."
- [ ] Wait ~30 days before reapplying (Google recommends this)

## GBP Listing Info
- **Business Name:** Organizing Life Services Estate Sale Company
- **GBP Location ID:** locations/8085786647786125239
- **GBP Business ID:** 8085786647786125239
- **Mailing Address:** 5005 W Laurel St, Suite 100 PMB1048, Tampa, FL 33607
- **Phone:** (727) 542-6028
- **Website:** https://organizinglifeservices.com

## Once API Access Is Granted
1. Run discover script to accept service account invitation and confirm location ID
2. Test `/api/seo/gbp/pull` endpoint
3. Test `/api/seo/gbp/push-to-sheets` endpoint
