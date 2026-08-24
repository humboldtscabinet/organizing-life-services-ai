# Post-Deploy Measurement Baseline - organizinglifeservices.com
_Generated 2026-08-24 12:09 UTC_

## Overall Read
**Status: Pass with SEO warnings, fail on conversion-tracking trust.**

The live SEO changes are rendering, but GA4 is currently counting passive/page-load behavior as key events. Do not treat the current conversion total as a business KPI until GA4 key events are cleaned up.

## 1. GA4 Conversion Tracking
**Window:** `2026-07-27 -> 2026-08-23`

| Metric | Prior | Current | Delta |
|---|---:|---:|---:|
| Sessions | 1,265 | 1,445 | +14.2% |
| keyEvents | 1,946 | 43 | -97.8% |
| Key events/session | - | 0.03 | - |

**Trust assessment:** `fail`
- **HIGH**: Passive events such as page views or page-load events are counted as key events.

**GA4 Admin key-event config access:** `ok`
- No passive/page-view key events found in Admin API config.

Top key-event rows:
| Event | Class | Key events | Event count |
|---|---|---:|---:|
| `form_submit` | lead_intent | 21 | 21 |
| `phone_call_clicks` | lead_intent | 17 | 17 |
| `page_view` | passive_or_pageview | 4 | 2,016 |
| `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 1 | 97 |
| `session_start` | passive_or_pageview | 0 | 1,453 |
| `first_visit` | passive_or_pageview | 0 | 1,132 |
| `user_engagement` | passive_or_pageview | 0 | 1,119 |
| `scroll` | passive_or_pageview | 0 | 423 |
| `form_start` | other | 0 | 55 |
| `click` | other | 0 | 20 |
| `search` | other | 0 | 4 |
| `view_search_results` | passive_or_pageview | 0 | 3 |

Top organic landing-page key-event rows:
| Landing page | Event | Class | Key events | Sessions |
|---|---|---|---:|---:|
| `/` | `phone_call_clicks` | lead_intent | 4 | 3 |
| `/` | `form_submit` | lead_intent | 2 | 2 |
| `/pages/13925-pathfinder-drive-tampa-florida` | `page_view` | passive_or_pageview | 1 | 1 |
| `/` | `page_view` | passive_or_pageview | 0 | 51 |
| `/` | `session_start` | passive_or_pageview | 0 | 51 |
| `/` | `user_engagement` | passive_or_pageview | 0 | 42 |
| `/` | `first_visit` | passive_or_pageview | 0 | 40 |
| `/pages/estate-sale-new-port-richey-florida` | `page_view` | passive_or_pageview | 0 | 13 |
| `/pages/estate-sale-new-port-richey-florida` | `session_start` | passive_or_pageview | 0 | 13 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `page_view` | passive_or_pageview | 0 | 12 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `session_start` | passive_or_pageview | 0 | 12 |
| `/` | `scroll` | passive_or_pageview | 0 | 11 |

## 2. Post-Deploy Live SEO Verification
**Status:** `pass`

| Page | Status | Title len | Meta len | H1s | Robots | Issues |
|---|---|---:|---:|---:|---|---|
| Homepage | pass | 49 | 139 | 1 | `` | low_alt_text_coverage |
| Personal Property Appraisal | pass | 58 | 151 | 1 | `` | none |
| Contact | pass | 54 | 156 | 1 | `` | none |
| About | pass | 35 | 147 | 1 | `` | none |
| Testimonials | pass | 53 | 147 | 1 | `` | none |
| Senior Services | pass | 31 | 160 | 1 | `` | none |
| All Collections | pass | 57 |  | 2 | `noindex,follow` | missing_meta_description, multiple_h1, noindex |
| Fees Products | pass | 62 |  | 2 | `noindex,follow` | missing_meta_description, multiple_h1, noindex |
| Fee Product CC 2.7 | pass | 68 |  | 1 | `noindex,follow` | title_too_long, missing_meta_description, noindex, low_alt_text_coverage |
| Fee Product CC 2.7 Duplicate | pass | 68 | 87 | 1 | `noindex,follow` | title_too_long, noindex, low_alt_text_coverage |
| Processing Fee Product | pass | 63 |  | 1 | `noindex,follow` | missing_meta_description, noindex, low_alt_text_coverage |

## 3. Next Content Targets
**GSC window:** `2026-07-25 -> 2026-08-21`

| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `estate sale organizers` | `/` | 262 | 0 | 15.5 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 2 | `estate sales near me` | `/pages/estate-sale-new-port-richey-florida` | 397 | 5 | 9.2 | MEDIUM (55) | Review existing page intent and title/meta alignment |
| 3 | `estate cleanout near me` | `/` | 262 | 0 | 1.0 | MEDIUM (55) | Expand homepage service-intent copy or refine homepage internal links |
| 4 | `estate sale organizers` | `/pages/estate-sale-tampa-hillsborough-county` | 100 | 0 | 22.5 | HIGH (90) | Create or improve a service-area page/section |
| 5 | `how to increase home value for appraisal` | `/blogs/news/how-to-increase-your-home-appraisal-value` | 104 | 0 | 26.3 | MEDIUM (50) | Create or refresh an educational guide |
| 6 | `estate sales near me` | `/pages/estate-sale-citrus-county` | 169 | 1 | 8.8 | MEDIUM (55) | Create or improve a service-area page/section |
| 7 | `estate sales palm harbor` | `/pages/estate-sale-palm-harbor-pinellas-county` | 121 | 0 | 9.3 | HIGH (70) | Create or improve a service-area page/section |
| 8 | `estate sales near me` | `/pages/estate-sale-palm-harbor-pinellas-county` | 197 | 3 | 8.5 | MEDIUM (55) | Create or improve a service-area page/section |
| 9 | `estate sale planners` | `/` | 83 | 0 | 14.8 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 10 | `estate sales new port richey` | `/pages/estate-sale-new-port-richey-florida` | 62 | 0 | 10.6 | HIGH (70) | Review existing page intent and title/meta alignment |
| 11 | `estate sales citrus county` | `/pages/estate-sale-citrus-county` | 60 | 0 | 11.2 | HIGH (70) | Create or improve a service-area page/section |
| 12 | `estate sales near me` | `/pages/estate-sale-dunedin-florida` | 69 | 0 | 10.3 | MEDIUM (55) | Create or improve a service-area page/section |
| 13 | `estate sale helpers` | `/` | 67 | 0 | 14.1 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 14 | `estate sales` | `/pages/estate-sale-new-port-richey-florida` | 143 | 3 | 5.0 | HIGH (70) | Review existing page intent and title/meta alignment |
| 15 | `professional tag sale organizers` | `/` | 63 | 0 | 10.8 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |

## 4. GBP Readiness
**On-site readiness:** `pass`

| Check | Status | Detail |
|---|---|---|
| LocalBusiness schema present | PASS | Organizing Life Services |
| No public streetAddress in schema | PASS | streetAddress absent |
| Schema keeps region/country | PASS | FL/US |
| Schema has service area | PASS | 14 area entries |
| Schema has phone | PASS | +17275426028 |
| Contact page labels mailing address | PASS | mailing address label and PMB present |

**GBP API:** `skipped` - not attempted

## 5. Ongoing Reporting
- This report is generated by `data/post_deploy_measurement_baseline.py`.
- Weekly automation now runs both the deep SEO audit and this measurement baseline.
- GTM audit unavailable: GTM_ACCOUNT_ID/GTM_CONTAINER_ID not configured.

## Remediation Checklist
1. Follow `docs/runbooks/ga4-key-event-cleanup.md`.
2. In GA4 Admin, unmark `page_view` as a key event.
3. Stop counting `ads_conversion_Contact_Page_load_https_1` as a conversion; a contact-page view is not a lead.
4. Keep or create true lead key events: form submit, phone click, email click, and contact CTA click.
5. If API inspection is desired, enable Google Analytics Admin API in GCP; UI cleanup works now.
6. After the GA4 change, rerun this report and use lead-intent key events as the business KPI.
7. Expand the highest-priority content targets only after the tracking baseline is clean.

Raw JSON: `data/audit_output/post_deploy_measurement_baseline_20260824T120922Z.json`