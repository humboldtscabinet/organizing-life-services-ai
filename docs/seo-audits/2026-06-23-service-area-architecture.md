# Service-Area SEO Architecture - Organizing Life Services

**Date:** 2026-06-23
**Scope:** Pinellas, Pasco, and Hillsborough as the primary service footprint, with secondary coverage for Hernando, Citrus, and Manatee when practical.
**Status:** Architecture and implementation blueprint. No live Shopify writes in this pass.

---

## Executive Read

Yes, OLS should have more service-area pages, but the structure needs to be deliberate. The current site already has several strong geo pages, a few hybrid county/city pages, and many old event-sale shells that should not become canonical SEO landing pages.

The correct architecture is:

1. County hubs for the real core counties: Pinellas, Pasco, Hillsborough.
2. City pages under those hubs where OLS has meaningful local relevance.
3. Permanent city/service pages, not one-off estate-sale event pages.
4. Internal links from homepage, service pages, county hubs, and sibling city pages.
5. Unique city/county value on each page so the rollout does not become doorway-page spam.

This should happen after GA4 key-event cleanup, or at least with the understanding that lead measurement is currently noisy.

---

## Guardrails

Google warns against doorway pages created only to rank for similar location queries. That is the risk with city pages if each page is just the same copy with the city swapped.

Every OLS service-area page needs:

- A real local purpose: city/county logistics, nearby communities, property types, buyer behavior, parking/access notes, senior communities, or cleanout timing.
- Clear service scope: estate sales, appraisals, downsizing, estate cleanouts, and liquidation.
- A unique FAQ section.
- Links to the county hub, nearby city pages, the appraisal page, estate cleanout page, downsizing page, and contact page.
- LocalBusiness or Service schema that keeps OLS as a service-area business, not a fake storefront.
- A strong CTA with `(727) 542-6028` and `/pages/contact-us`.

References:

- Google Search Central spam policies, doorway abuse: https://developers.google.com/search/docs/essentials/spam-policies
- Google LocalBusiness structured data: https://developers.google.com/search/docs/appearance/structured-data/local-business

---

## Current Live Inventory

Read-only Shopify inventory on 2026-06-23 found these relevant existing pages.

### Strong/usable service pages

| Handle | Current role | Read |
|---|---|---|
| `estate-cleanout-services` | Estate cleanout service page | Strong page; expand into service-area crosslinks and FAQs after GA4 cleanup. |
| `downsizing-moving-sales` | Downsizing/moving sales page | Strong page; should link into county/city architecture. |
| `personal-property-appraisal` | Appraisal service page | Title/meta fixed; needs full landing-page expansion. |
| `estate-liquidation` | Liquidation service page | Useful supporting page. |
| `estate-sale-planning` | Planning/hire page | Useful supporting page for organizer/planner queries. |
| `estate-sale-companies-near-me` | Local-intent page | Useful, but should not compete with county/city hubs. |

### Existing geo pages to keep and refresh

| Handle | County | Role |
|---|---|---|
| `estate-sale-palm-harbor-pinellas-county` | Pinellas | Keep as Palm Harbor page; decide whether to split out a pure Pinellas hub. |
| `estate-sale-clearwater-florida` | Pinellas | Keep and refresh. |
| `estate-sale-dunedin-florida` | Pinellas | Keep and refresh in wave 2. |
| `estate-sale-largo-florida` | Pinellas | Keep and refresh in wave 2. |
| `estate-sale-st-petersburg-florida` | Pinellas | Keep and refresh in wave 2. |
| `estate-sale-tampa-hillsborough-county` | Hillsborough | Keep as Tampa/Hillsborough hub, refresh first. |
| `estate-sale-new-port-richey-florida` | Pasco | Keep and refresh first. |
| `estate-sale-wesley-chapel-florida` | Pasco | Keep and refresh in wave 2. |
| `estate-sale-pasco-county` | Pasco | Refresh as pure Pasco hub; do not keep merging Pasco and Hernando as one primary page. |
| `estate-sale-citrus-county` | Citrus | Keep as secondary coverage, not core first wave. |

### Legacy event pages not to use as canonical city pages

These are thin event shells or sale-specific pages. They may show GSC demand, but they should not be the long-term page for that city.

| Existing handle | Better permanent target |
|---|---|
| `tarpon-springs-estate-sale-in-woodfield` | `estate-sale-tarpon-springs-florida` |
| `estate-sale-safety-harbor-florida-pinellas-county-34695` | `estate-sale-safety-harbor-florida` |
| `pinellas-park-estate-sale-in-the-mainlands-9841-41st-street-north` | `estate-sale-pinellas-park-florida` |
| `estate-sale-westchase-tampa-fl-33626-hillsborough-county` | `estate-sale-westchase-florida` |
| `13925-pathfinder-drive-tampa-florida` | Strengthen Tampa/Hillsborough hub, do not use this event page. |
| `pimberton-drive-hudson` | `estate-sale-hudson-florida` |

---

## Target Architecture

### Primary county hubs

| County | Target handle | Action |
|---|---|---|
| Pinellas County | `estate-sale-pinellas-county` | Create new pure county hub, or carefully split from Palm Harbor page. |
| Pasco County | `estate-sale-pasco-county` | Refresh existing page as pure Pasco hub. Move Hernando language to secondary support. |
| Hillsborough County | `estate-sale-tampa-hillsborough-county` | Refresh existing page as Tampa + Hillsborough hub. |

County hub purpose:

- Explain full county coverage.
- Link to all relevant city pages in that county.
- Link to core services: estate sales, appraisals, downsizing, cleanouts.
- Rank for county-level queries.
- Support city pages with internal authority.

### Pinellas city pages

| City | Target handle | Status | Wave |
|---|---|---|---:|
| Palm Harbor | `estate-sale-palm-harbor-pinellas-county` | Refresh existing | 1 |
| Clearwater | `estate-sale-clearwater-florida` | Refresh existing | 1 |
| Tarpon Springs | `estate-sale-tarpon-springs-florida` | Create/migrate from legacy event | 1 |
| Dunedin | `estate-sale-dunedin-florida` | Refresh existing | 2 |
| Largo | `estate-sale-largo-florida` | Refresh existing | 2 |
| St. Petersburg | `estate-sale-st-petersburg-florida` | Refresh existing | 2 |
| Safety Harbor | `estate-sale-safety-harbor-florida` | Create/migrate from legacy event | 2 |
| Seminole | `estate-sale-seminole-florida` | Create new | 2 |
| Pinellas Park | `estate-sale-pinellas-park-florida` | Create/migrate from legacy event | 3 |

### Pasco city pages

| City | Target handle | Status | Wave |
|---|---|---|---:|
| New Port Richey | `estate-sale-new-port-richey-florida` | Refresh existing | 1 |
| Wesley Chapel | `estate-sale-wesley-chapel-florida` | Refresh existing | 2 |
| Trinity | `estate-sale-trinity-florida` | Create new | 3 |
| Holiday | `estate-sale-holiday-florida` | Create new | 3 |
| Hudson | `estate-sale-hudson-florida` | Create/migrate from legacy event | 3 |
| Port Richey | `estate-sale-port-richey-florida` | Create new | 3 |
| Land O' Lakes | `estate-sale-land-o-lakes-florida` | Create new | 3 |

### Hillsborough city pages

| City | Target handle | Status | Wave |
|---|---|---|---:|
| Tampa | `estate-sale-tampa-florida` | Covered by existing Tampa/Hillsborough hub for now; migrate later only if needed | 1 |
| Brandon | `estate-sale-brandon-florida` | Create new | 2 |
| Riverview | `estate-sale-riverview-florida` | Create new | 2 |
| Carrollwood | `estate-sale-carrollwood-florida` | Create new | 3 |
| Lutz | `estate-sale-lutz-florida` | Create new | 3 |
| Westchase | `estate-sale-westchase-florida` | Create/migrate from legacy event | 3 |
| Plant City | `estate-sale-plant-city-florida` | Create new | 3 |
| Valrico | `estate-sale-valrico-florida` | Create new | 3 |

---

## First-Wave Implementation

The first wave should be small enough to quality-control by hand.

Implementation status on 2026-06-23:

- [`data/session11_service_area_first_wave.py`](../../data/session11_service_area_first_wave.py) now implements the first-wave plan with dry-run by default.
- The dry-run report is [`data/audit_output/session11_service_area_first_wave_20260623T230329Z.json`](../../data/audit_output/session11_service_area_first_wave_20260623T230329Z.json).
- No live Shopify writes have been performed by this script yet.
- The script appends a marked body section that starts at `h2`; the Shopify page title should remain responsible for the rendered page-level `h1`.

1. `estate-sale-pinellas-county`
   - Create pure Pinellas hub.
   - Link to Palm Harbor, Clearwater, Tarpon Springs, Dunedin, Largo, St. Petersburg, Safety Harbor, Seminole, Pinellas Park.

2. `estate-sale-pasco-county`
   - Refresh existing page as pure Pasco hub.
   - Keep Hernando as a secondary note, not the headline.
   - Link to New Port Richey, Wesley Chapel, Trinity, Holiday, Hudson, Port Richey, Land O' Lakes.

3. `estate-sale-tampa-hillsborough-county`
   - Refresh existing page as Tampa/Hillsborough hub.
   - Link to Brandon, Riverview, Carrollwood, Lutz, Westchase, Plant City, Valrico as pages are created.

4. `estate-sale-palm-harbor-pinellas-county`
   - Refresh as Palm Harbor city page.
   - Add links back to Pinellas hub and nearby Pinellas city pages.

5. `estate-sale-clearwater-florida`
   - Refresh as Clearwater city page.
   - Add more unique Clearwater-specific copy and FAQs.

6. `estate-sale-new-port-richey-florida`
   - Refresh as New Port Richey/Pasco page.
   - Link to Pasco hub and Wesley Chapel.

7. `estate-sale-tarpon-springs-florida`
   - Create permanent page or migrate from `tarpon-springs-estate-sale-in-woodfield`.
   - Keep the old Woodfield event page noindexed or redirect only if the content is retired.

---

## Page Template

Each county/city page should use this structure.

1. One rendered H1:
   - `Estate Sales in {City}, FL`
   - `Estate Sales in {County} County, FL`
   - For Shopify implementation scripts, this should come from the page title/theme output, not an appended body-level H1.

2. Intro:
   - Who OLS helps in that area.
   - Estate sales, downsizing, cleanouts, appraisals.
   - Phone and service-area language.

3. Local logistics:
   - Property types.
   - Neighborhoods/nearby communities.
   - Parking/gated community/HOA/senior community considerations where relevant.

4. Process:
   - Consultation.
   - Sorting/staging.
   - Pricing/research.
   - Marketing.
   - Sale-day staffing.
   - Cleanout/donation.

5. Services:
   - Estate sales.
   - Estate cleanouts.
   - Downsizing/moving sales.
   - Personal property appraisals.

6. FAQs:
   - How quickly can a sale happen?
   - What if the home is in a gated community?
   - Do you handle cleanouts?
   - Do you appraise personal property?
   - What nearby areas do you serve?

7. Internal links:
   - County hub.
   - Nearby city pages.
   - Appraisal page.
   - Estate cleanout page.
   - Downsizing page.
   - Contact page.

8. CTA:
   - Call `(727) 542-6028`.
   - Link to `/pages/contact-us`.

---

## Measurement Plan

Before live publishing:

- Finish GA4 key-event cleanup so conversions represent real lead intent.
- Keep the current measurement baseline as the pre-rollout checkpoint.

After each first-wave page goes live:

- Verify title, meta description, canonical, one H1, schema, and internal links.
- Submit changed URLs through IndexNow.
- Re-run `data/post_deploy_measurement_baseline.py`.
- Re-run the weekly deep SEO audit after 7-14 days for crawl/indexing signals.
- Use 28-day windows for business conclusions.

Primary KPIs:

- GSC impressions/clicks for `{city} estate sale company`, `estate sale organizers`, `estate sale companies near me`, `{county} estate sales`, `estate cleanout services`, and appraisal terms.
- Organic landing-page sessions.
- Clean lead key events only: `form_submit`, `phone_click`, `email_click`, `contact_cta_click`.

---

## Decision

Proceed with a first-wave service-area rollout after GA4 key-event cleanup. The immediate next implementation should be a guarded Shopify script for the first wave, but the script should support `--dry-run`, page snapshots, and explicit human confirmation before live writes.
