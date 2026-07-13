# Post-Deploy Measurement Baseline - organizinglifeservices.com
_Generated 2026-07-13 12:49 UTC_

## Overall Read
**Status: Pass with SEO warnings, fail on conversion-tracking trust.**

The live SEO changes are rendering, but GA4 is currently counting passive/page-load behavior as key events. Do not treat the current conversion total as a business KPI until GA4 key events are cleaned up.

## 1. GA4 Conversion Tracking
**Window:** `2026-06-15 -> 2026-07-12`

| Metric | Prior | Current | Delta |
|---|---:|---:|---:|
| Sessions | 1,013 | 790 | -22.0% |
| keyEvents | 1,557 | 1,356 | -12.9% |
| Key events/session | - | 1.72 | - |

**Trust assessment:** `fail`
- **HIGH**: Passive events such as page views or page-load events are counted as key events.
- **MEDIUM**: Key events per session is unusually high for real lead tracking.

**GA4 Admin key-event config access:** `unavailable`
- Use the GA4 UI cleanup runbook now, or enable Google Analytics Admin API in GCP if you want this repo to inspect key-event configuration directly.
- Reason: `Google Analytics Admin API is disabled in the service-account GCP project.`

Top key-event rows:
| Event | Class | Key events | Event count |
|---|---|---:|---:|
| `page_view` | passive_or_pageview | 1,262 | 1,262 |
| `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 79 | 79 |
| `form_submit` | lead_intent | 15 | 15 |
| `session_start` | passive_or_pageview | 0 | 796 |
| `user_engagement` | passive_or_pageview | 0 | 710 |
| `first_visit` | passive_or_pageview | 0 | 694 |
| `scroll` | passive_or_pageview | 0 | 144 |
| `form_start` | other | 0 | 40 |
| `search` | other | 0 | 26 |
| `view_search_results` | passive_or_pageview | 0 | 4 |
| `click` | other | 0 | 3 |
| `view_item` | other | 0 | 1 |

Top organic landing-page key-event rows:
| Landing page | Event | Class | Key events | Sessions |
|---|---|---|---:|---:|
| `/` | `page_view` | passive_or_pageview | 272 | 101 |
| `/` | `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 23 | 14 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `page_view` | passive_or_pageview | 15 | 10 |
| `/pages/estate-sale-new-port-richey-florida` | `page_view` | passive_or_pageview | 12 | 7 |
| `/pages/estate-liquidation` | `page_view` | passive_or_pageview | 11 | 6 |
| `/pages/estate-sale-pasco-county` | `page_view` | passive_or_pageview | 11 | 5 |
| `/pages/contact-us` | `page_view` | passive_or_pageview | 8 | 5 |
| `/pages/estate-sale-tampa-hillsborough-county` | `page_view` | passive_or_pageview | 8 | 4 |
| `/blogs/news/find-the-best-jewelry-buyer-in-tampa-florida` | `page_view` | passive_or_pageview | 7 | 2 |
| `/blogs/news/yard-sale-vs-estate-sale-key-differences` | `page_view` | passive_or_pageview | 6 | 5 |
| `/pages/personal-property-appraisal` | `page_view` | passive_or_pageview | 6 | 4 |
| `/pages/estate-sale-dunedin-florida` | `page_view` | passive_or_pageview | 6 | 3 |

## 2. Post-Deploy Live SEO Verification
**Status:** `pass`

| Page | Status | Title len | Meta len | H1s | Robots | Issues |
|---|---|---:|---:|---:|---|---|
| Homepage | pass | 58 | 148 | 1 | `` | low_alt_text_coverage |
| Personal Property Appraisal | pass | 58 | 151 | 1 | `` | none |
| Contact | pass | 54 | 156 | 1 | `` | none |
| About | pass | 35 | 147 | 1 | `` | none |
| Testimonials | pass | 53 | 147 | 1 | `` | none |
| Senior Services | pass | 31 | 160 | 1 | `` | none |
| All Collections | pass | 57 |  | 2 | `noindex,follow` | missing_meta_description, multiple_h1, noindex |
| Fees Products | pass | 62 |  | 2 | `noindex,follow` | missing_meta_description, multiple_h1, noindex |

## 3. Next Content Targets
**GSC window:** `2026-06-13 -> 2026-07-10`

| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `estate sale organizers` | `/` | 299 | 1 | 12.0 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 2 | `estate sale organizers` | `/pages/estate-sale-tampa-hillsborough-county` | 101 | 0 | 18.0 | HIGH (90) | Create or improve a service-area page/section |
| 3 | `estate sales` | `/pages/estate-sale-new-port-richey-florida` | 176 | 1 | 7.8 | HIGH (70) | Review existing page intent and title/meta alignment |
| 4 | `estate sales palm harbor` | `/pages/estate-sale-palm-harbor-pinellas-county` | 213 | 3 | 9.8 | HIGH (70) | Create or improve a service-area page/section |
| 5 | `estate sale organizer` | `/pages/estate-sale-tampa-hillsborough-county` | 72 | 0 | 16.0 | HIGH (90) | Create or improve a service-area page/section |
| 6 | `estate sales new port richey` | `/pages/estate-sale-new-port-richey-florida` | 76 | 0 | 11.0 | HIGH (70) | Review existing page intent and title/meta alignment |
| 7 | `estate sales tarpon springs` | `/pages/tarpon-springs-estate-sale-in-woodfield` | 108 | 0 | 7.4 | HIGH (70) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 8 | `how to increase home value for appraisal` | `/blogs/news/how-to-increase-your-home-appraisal-value` | 77 | 0 | 29.2 | MEDIUM (50) | Create or refresh an educational guide |
| 9 | `estate sale organizers` | `/pages/13925-pathfinder-drive-tampa-florida` | 87 | 0 | 8.9 | HIGH (90) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 10 | `estate sales near me` | `/pages/estate-sale-new-port-richey-florida` | 116 | 0 | 9.3 | MEDIUM (55) | Review existing page intent and title/meta alignment |
| 11 | `estate sales palm harbor` | `/` | 114 | 1 | 6.5 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 12 | `estate sale organizer` | `/` | 91 | 0 | 4.7 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 13 | `estate sale organizers` | `/pages/estate-sale-planning` | 87 | 0 | 8.9 | HIGH (70) | Review existing page intent and title/meta alignment |
| 14 | `estate sale organizers` | `/pages/senior-services` | 87 | 0 | 8.9 | HIGH (70) | Review existing page intent and title/meta alignment |
| 15 | `estate cleanout services` | `/pages/estate-cleanout-services` | 46 | 0 | 17.6 | HIGH (70) | Expand matching service page with FAQs, process, and CTA |

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

Raw JSON: `data/audit_output/post_deploy_measurement_baseline_20260713T124920Z.json`