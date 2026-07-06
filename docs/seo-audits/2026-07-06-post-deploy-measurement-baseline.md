# Post-Deploy Measurement Baseline - organizinglifeservices.com
_Generated 2026-07-06 13:14 UTC_

## Overall Read
**Status: Pass with SEO warnings, fail on conversion-tracking trust.**

The live SEO changes are rendering, but GA4 is currently counting passive/page-load behavior as key events. Do not treat the current conversion total as a business KPI until GA4 key events are cleaned up.

## 1. GA4 Conversion Tracking
**Window:** `2026-06-08 -> 2026-07-05`

| Metric | Prior | Current | Delta |
|---|---:|---:|---:|
| Sessions | 1,126 | 545 | -51.6% |
| keyEvents | 1,750 | 954 | -45.5% |
| Key events/session | - | 1.75 | - |

**Trust assessment:** `fail`
- **HIGH**: Passive events such as page views or page-load events are counted as key events.
- **MEDIUM**: Key events per session is unusually high for real lead tracking.

**GA4 Admin key-event config access:** `unavailable`
- Use the GA4 UI cleanup runbook now, or enable Google Analytics Admin API in GCP if you want this repo to inspect key-event configuration directly.
- Reason: `Google Analytics Admin API is disabled in the service-account GCP project.`

Top key-event rows:
| Event | Class | Key events | Event count |
|---|---|---:|---:|
| `page_view` | passive_or_pageview | 880 | 880 |
| `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 66 | 66 |
| `form_submit` | lead_intent | 8 | 8 |
| `session_start` | passive_or_pageview | 0 | 549 |
| `user_engagement` | passive_or_pageview | 0 | 472 |
| `first_visit` | passive_or_pageview | 0 | 450 |
| `scroll` | passive_or_pageview | 0 | 91 |
| `form_start` | other | 0 | 20 |
| `click` | other | 0 | 2 |
| `search` | other | 0 | 2 |
| `view_search_results` | passive_or_pageview | 0 | 2 |
| `view_item` | other | 0 | 1 |

Top organic landing-page key-event rows:
| Landing page | Event | Class | Key events | Sessions |
|---|---|---|---:|---:|
| `/` | `page_view` | passive_or_pageview | 227 | 80 |
| `/` | `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 18 | 12 |
| `/pages/estate-sale-new-port-richey-florida` | `page_view` | passive_or_pageview | 11 | 6 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `page_view` | passive_or_pageview | 10 | 5 |
| `/blogs/news/yard-sale-vs-estate-sale-key-differences` | `page_view` | passive_or_pageview | 9 | 8 |
| `/pages/contact-us` | `page_view` | passive_or_pageview | 9 | 5 |
| `/pages/personal-property-appraisal` | `page_view` | passive_or_pageview | 8 | 4 |
| `/pages/estate-sale-pasco-county` | `page_view` | passive_or_pageview | 8 | 2 |
| `/pages/contact-us` | `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 7 | 5 |
| `/pages/testimonials` | `page_view` | passive_or_pageview | 6 | 2 |
| `/pages/fees-products` | `page_view` | passive_or_pageview | 6 | 1 |
| `/pages/estate-sale-citrus-county` | `page_view` | passive_or_pageview | 4 | 4 |

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
**GSC window:** `2026-06-06 -> 2026-07-03`

| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `estate sale organizers` | `/` | 263 | 0 | 12.5 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 2 | `estate sales palm harbor` | `/pages/estate-sale-palm-harbor-pinellas-county` | 136 | 0 | 9.9 | HIGH (70) | Create or improve a service-area page/section |
| 3 | `estate sale organizers` | `/pages/estate-sale-tampa-hillsborough-county` | 69 | 0 | 12.7 | HIGH (90) | Create or improve a service-area page/section |
| 4 | `estate sales` | `/pages/estate-sale-new-port-richey-florida` | 125 | 1 | 7.5 | HIGH (70) | Review existing page intent and title/meta alignment |
| 5 | `estate sale organizer` | `/pages/estate-sale-tampa-hillsborough-county` | 55 | 0 | 18.8 | HIGH (90) | Create or improve a service-area page/section |
| 6 | `estate sale companies near me` | `/` | 73 | 0 | 14.6 | MEDIUM (55) | Expand homepage service-intent copy or refine homepage internal links |
| 7 | `estate sales tarpon springs` | `/pages/tarpon-springs-estate-sale-in-woodfield` | 102 | 0 | 7.3 | HIGH (70) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 8 | `how to increase home value for appraisal` | `/blogs/news/how-to-increase-your-home-appraisal-value` | 74 | 0 | 28.7 | MEDIUM (50) | Create or refresh an educational guide |
| 9 | `estate sales palm harbor` | `/` | 113 | 1 | 7.8 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 10 | `estate cleanout services` | `/pages/estate-cleanout-services` | 48 | 0 | 16.2 | HIGH (70) | Expand matching service page with FAQs, process, and CTA |
| 11 | `estate sale organizers` | `/pages/13925-pathfinder-drive-tampa-florida` | 65 | 0 | 8.9 | HIGH (90) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 12 | `estate sale organizer` | `/` | 71 | 0 | 4.8 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 13 | `estate sale and appraisal services` | `/` | 84 | 0 | 6.4 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 14 | `estate sale planners` | `/` | 53 | 0 | 15.8 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 15 | `estate organization service` | `/` | 50 | 0 | 17.1 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |

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

Raw JSON: `data/audit_output/post_deploy_measurement_baseline_20260706T131433Z.json`