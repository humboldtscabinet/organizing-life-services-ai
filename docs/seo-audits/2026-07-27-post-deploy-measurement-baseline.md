# Post-Deploy Measurement Baseline - organizinglifeservices.com
_Generated 2026-07-27 13:02 UTC_

## Overall Read
**Status: Pass with SEO warnings, fail on conversion-tracking trust.**

The live SEO changes are rendering, but GA4 is currently counting passive/page-load behavior as key events. Do not treat the current conversion total as a business KPI until GA4 key events are cleaned up.

## 1. GA4 Conversion Tracking
**Window:** `2026-06-29 -> 2026-07-26`

| Metric | Prior | Current | Delta |
|---|---:|---:|---:|
| Sessions | 545 | 1,265 | +132.1% |
| keyEvents | 945 | 1,946 | +105.9% |
| Key events/session | - | 1.54 | - |

**Trust assessment:** `fail`
- **HIGH**: Passive events such as page views or page-load events are counted as key events.
- **MEDIUM**: Key events per session is unusually high for real lead tracking.

**GA4 Admin key-event config access:** `ok`
- No passive/page-view key events found in Admin API config.

Top key-event rows:
| Event | Class | Key events | Event count |
|---|---|---:|---:|
| `page_view` | passive_or_pageview | 1,834 | 1,939 |
| `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 92 | 100 |
| `form_submit` | lead_intent | 18 | 18 |
| `phone_call_clicks` | lead_intent | 2 | 2 |
| `session_start` | passive_or_pageview | 0 | 1,264 |
| `user_engagement` | passive_or_pageview | 0 | 1,136 |
| `first_visit` | passive_or_pageview | 0 | 1,102 |
| `scroll` | passive_or_pageview | 0 | 218 |
| `form_start` | other | 0 | 53 |
| `search` | other | 0 | 29 |
| `click` | other | 0 | 12 |
| `view_search_results` | passive_or_pageview | 0 | 8 |

Top organic landing-page key-event rows:
| Landing page | Event | Class | Key events | Sessions |
|---|---|---|---:|---:|
| `/` | `page_view` | passive_or_pageview | 281 | 119 |
| `/pages/estate-sale-dunedin-florida` | `page_view` | passive_or_pageview | 19 | 11 |
| `/pages/organizing-life-estate-sale-company-successful-sales` | `page_view` | passive_or_pageview | 17 | 10 |
| `/` | `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 15 | 12 |
| `/pages/estate-liquidation` | `page_view` | passive_or_pageview | 15 | 9 |
| `/pages/estate-sale-tampa-hillsborough-county` | `page_view` | passive_or_pageview | 14 | 6 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `page_view` | passive_or_pageview | 13 | 11 |
| `/pages/estate-sale-new-port-richey-florida` | `page_view` | passive_or_pageview | 13 | 8 |
| `/blogs/news/estate-auction-vs-estate-sale-pros-and-cons` | `page_view` | passive_or_pageview | 11 | 10 |
| `/pages/about-us` | `page_view` | passive_or_pageview | 9 | 7 |
| `/pages/sell-your-house-florida` | `page_view` | passive_or_pageview | 9 | 5 |
| `/pages/what-is-an-estate-sale` | `page_view` | passive_or_pageview | 8 | 6 |

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
**GSC window:** `2026-06-27 -> 2026-07-24`

| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `estate sale organizers` | `/` | 298 | 1 | 10.6 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 2 | `estate sale organizers` | `/pages/estate-sale-tampa-hillsborough-county` | 148 | 0 | 25.2 | HIGH (90) | Create or improve a service-area page/section |
| 3 | `estate sales palm harbor` | `/pages/estate-sale-palm-harbor-pinellas-county` | 321 | 4 | 9.2 | HIGH (70) | Create or improve a service-area page/section |
| 4 | `estate sales near me` | `/pages/estate-sale-new-port-richey-florida` | 230 | 0 | 9.1 | MEDIUM (55) | Review existing page intent and title/meta alignment |
| 5 | `estate sales new port richey` | `/pages/estate-sale-new-port-richey-florida` | 137 | 1 | 10.7 | HIGH (70) | Review existing page intent and title/meta alignment |
| 6 | `estate sales` | `/pages/estate-sale-new-port-richey-florida` | 182 | 1 | 7.7 | HIGH (70) | Review existing page intent and title/meta alignment |
| 7 | `estate sale organizers` | `/pages/13925-pathfinder-drive-tampa-florida` | 109 | 0 | 7.4 | HIGH (90) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 8 | `how to increase home value for appraisal` | `/blogs/news/how-to-increase-your-home-appraisal-value` | 94 | 0 | 26.0 | MEDIUM (50) | Create or refresh an educational guide |
| 9 | `estate sales near me` | `/pages/estate-sale-citrus-county` | 146 | 1 | 8.8 | MEDIUM (55) | Create or improve a service-area page/section |
| 10 | `estate sale organizers` | `/pages/estate-sale-planning` | 109 | 0 | 7.4 | HIGH (70) | Review existing page intent and title/meta alignment |
| 11 | `estate sale organizers` | `/pages/senior-services` | 109 | 0 | 7.4 | HIGH (70) | Review existing page intent and title/meta alignment |
| 12 | `estate sales near me` | `/pages/estate-sale-palm-harbor-pinellas-county` | 179 | 3 | 8.1 | MEDIUM (55) | Create or improve a service-area page/section |
| 13 | `estate sale organizer` | `/` | 98 | 0 | 5.0 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 14 | `estate sale organizer` | `/pages/estate-sale-tampa-hillsborough-county` | 85 | 0 | 8.4 | HIGH (90) | Create or improve a service-area page/section |
| 15 | `estate sales tarpon springs` | `/pages/tarpon-springs-estate-sale-in-woodfield` | 98 | 0 | 7.2 | HIGH (70) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |

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

Raw JSON: `data/audit_output/post_deploy_measurement_baseline_20260727T130255Z.json`