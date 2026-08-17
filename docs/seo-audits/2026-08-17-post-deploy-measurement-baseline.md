# Post-Deploy Measurement Baseline - organizinglifeservices.com
_Generated 2026-08-17 12:07 UTC_

## Overall Read
**Status: Pass with SEO warnings, fail on conversion-tracking trust.**

The live SEO changes are rendering, but GA4 is currently counting passive/page-load behavior as key events. Do not treat the current conversion total as a business KPI until GA4 key events are cleaned up.

## 1. GA4 Conversion Tracking
**Window:** `2026-07-20 -> 2026-08-16`

| Metric | Prior | Current | Delta |
|---|---:|---:|---:|
| Sessions | 1,101 | 1,476 | +34.1% |
| keyEvents | 1,778 | 393 | -77.9% |
| Key events/session | - | 0.27 | - |

**Trust assessment:** `fail`
- **HIGH**: Passive events such as page views or page-load events are counted as key events.

**GA4 Admin key-event config access:** `ok`
- No passive/page-view key events found in Admin API config.

Top key-event rows:
| Event | Class | Key events | Event count |
|---|---|---:|---:|
| `page_view` | passive_or_pageview | 338 | 2,115 |
| `form_submit` | lead_intent | 19 | 19 |
| `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 18 | 99 |
| `phone_call_clicks` | lead_intent | 18 | 18 |
| `session_start` | passive_or_pageview | 0 | 1,484 |
| `user_engagement` | passive_or_pageview | 0 | 1,253 |
| `first_visit` | passive_or_pageview | 0 | 1,173 |
| `scroll` | passive_or_pageview | 0 | 426 |
| `form_start` | other | 0 | 46 |
| `click` | other | 0 | 21 |
| `search` | other | 0 | 4 |
| `view_search_results` | passive_or_pageview | 0 | 3 |

Top organic landing-page key-event rows:
| Landing page | Event | Class | Key events | Sessions |
|---|---|---|---:|---:|
| `/` | `page_view` | passive_or_pageview | 50 | 57 |
| `/pages/organizing-life-estate-sale-company-successful-sales` | `page_view` | passive_or_pageview | 10 | 3 |
| `/pages/sell-your-house-florida?msclkid=955bb0622c8d17400a8fda3c7dc2f78d` | `page_view` | passive_or_pageview | 5 | 1 |
| `/` | `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 4 | 12 |
| `/` | `phone_call_clicks` | lead_intent | 4 | 3 |
| `/?msclkid=d9f85f506d101f5c766e350e1cc0b42d` | `page_view` | passive_or_pageview | 4 | 1 |
| `/pages/what-is-an-estate-sale?msclkid=4407afb905ca1cbfeb4ac5e759ecb6f2` | `page_view` | passive_or_pageview | 4 | 1 |
| `/pages/about-us` | `page_view` | passive_or_pageview | 3 | 3 |
| `/?msclkid=0f03b251326e15468151d830b9b0126d` | `page_view` | passive_or_pageview | 3 | 1 |
| `/?msclkid=75d7226edc991eeaf5fb483168e949a3` | `page_view` | passive_or_pageview | 3 | 1 |
| `/blogs/news/pros-and-cons-of-estate-sales` | `page_view` | passive_or_pageview | 2 | 4 |
| `/` | `form_submit` | lead_intent | 2 | 2 |

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
**GSC window:** `2026-07-18 -> 2026-08-14`

| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `estate sale organizers` | `/` | 257 | 0 | 14.6 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 2 | `estate sales near me` | `/pages/estate-sale-new-port-richey-florida` | 352 | 5 | 9.2 | MEDIUM (55) | Review existing page intent and title/meta alignment |
| 3 | `estate sale organizers` | `/pages/estate-sale-tampa-hillsborough-county` | 115 | 0 | 20.6 | HIGH (90) | Create or improve a service-area page/section |
| 4 | `estate sales palm harbor` | `/pages/estate-sale-palm-harbor-pinellas-county` | 156 | 0 | 8.9 | HIGH (70) | Create or improve a service-area page/section |
| 5 | `how to increase home value for appraisal` | `/blogs/news/how-to-increase-your-home-appraisal-value` | 106 | 0 | 24.4 | MEDIUM (50) | Create or refresh an educational guide |
| 6 | `estate sales new port richey` | `/pages/estate-sale-new-port-richey-florida` | 81 | 0 | 10.7 | HIGH (70) | Review existing page intent and title/meta alignment |
| 7 | `estate sales near me` | `/pages/estate-sale-citrus-county` | 152 | 1 | 8.9 | MEDIUM (55) | Create or improve a service-area page/section |
| 8 | `estate sales citrus county` | `/pages/estate-sale-citrus-county` | 63 | 0 | 10.9 | HIGH (70) | Create or improve a service-area page/section |
| 9 | `estate sale organizers` | `/pages/13925-pathfinder-drive-tampa-florida` | 78 | 0 | 5.6 | HIGH (90) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 10 | `estate sale organizers` | `/pages/estate-sale-planning` | 92 | 0 | 5.7 | HIGH (70) | Review existing page intent and title/meta alignment |
| 11 | `estate sale organizers` | `/pages/senior-services` | 92 | 0 | 5.7 | HIGH (70) | Review existing page intent and title/meta alignment |
| 12 | `estate sales` | `/pages/estate-sale-new-port-richey-florida` | 129 | 2 | 5.3 | HIGH (70) | Review existing page intent and title/meta alignment |
| 13 | `estate sale helpers` | `/` | 66 | 0 | 14.7 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 14 | `professional tag sale organizers` | `/` | 62 | 0 | 10.8 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 15 | `estate sale organizer` | `/pages/estate-sale-tampa-hillsborough-county` | 68 | 0 | 6.6 | HIGH (90) | Create or improve a service-area page/section |

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

Raw JSON: `data/audit_output/post_deploy_measurement_baseline_20260817T120738Z.json`