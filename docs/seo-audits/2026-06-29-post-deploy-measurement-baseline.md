# Post-Deploy Measurement Baseline - organizinglifeservices.com
_Generated 2026-06-29 13:26 UTC_

## Overall Read
**Status: Pass with SEO warnings, fail on conversion-tracking trust.**

The live SEO changes are rendering, but GA4 is currently counting passive/page-load behavior as key events. Do not treat the current conversion total as a business KPI until GA4 key events are cleaned up.

## 1. GA4 Conversion Tracking
**Window:** `2026-06-01 -> 2026-06-28`

| Metric | Prior | Current | Delta |
|---|---:|---:|---:|
| Sessions | 1,183 | 545 | -53.9% |
| keyEvents | 1,888 | 945 | -49.9% |
| Key events/session | - | 1.73 | - |

**Trust assessment:** `fail`
- **HIGH**: Passive events such as page views or page-load events are counted as key events.
- **MEDIUM**: Key events per session is unusually high for real lead tracking.

**GA4 Admin key-event config access:** `unavailable`
- Use the GA4 UI cleanup runbook now, or enable Google Analytics Admin API in GCP if you want this repo to inspect key-event configuration directly.
- Reason: `Google Analytics Admin API is disabled in the service-account GCP project.`

Top key-event rows:
| Event | Class | Key events | Event count |
|---|---|---:|---:|
| `page_view` | passive_or_pageview | 871 | 871 |
| `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 66 | 66 |
| `form_submit` | lead_intent | 8 | 8 |
| `session_start` | passive_or_pageview | 0 | 550 |
| `user_engagement` | passive_or_pageview | 0 | 477 |
| `first_visit` | passive_or_pageview | 0 | 449 |
| `scroll` | passive_or_pageview | 0 | 94 |
| `form_start` | other | 0 | 23 |
| `click` | other | 0 | 2 |
| `view_item` | other | 0 | 1 |

Top organic landing-page key-event rows:
| Landing page | Event | Class | Key events | Sessions |
|---|---|---|---:|---:|
| `/` | `page_view` | passive_or_pageview | 212 | 77 |
| `/` | `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 17 | 11 |
| `/pages/estate-liquidation` | `page_view` | passive_or_pageview | 14 | 7 |
| `/pages/estate-sale-new-port-richey-florida` | `page_view` | passive_or_pageview | 11 | 6 |
| `/blogs/news/yard-sale-vs-estate-sale-key-differences` | `page_view` | passive_or_pageview | 10 | 9 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `page_view` | passive_or_pageview | 10 | 5 |
| `/pages/contact-us` | `page_view` | passive_or_pageview | 8 | 3 |
| `/pages/testimonials` | `page_view` | passive_or_pageview | 8 | 3 |
| `/pages/estate-sale-pasco-county` | `page_view` | passive_or_pageview | 8 | 2 |
| `/pages/personal-property-appraisal` | `page_view` | passive_or_pageview | 7 | 3 |
| `/pages/contact-us` | `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 6 | 3 |
| `/pages/fees-products` | `page_view` | passive_or_pageview | 6 | 1 |

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
**GSC window:** `2026-05-30 -> 2026-06-26`

| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `estate sale organizers` | `/` | 260 | 0 | 14.1 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 2 | `estate sale companies near me` | `/` | 94 | 0 | 15.1 | MEDIUM (55) | Expand homepage service-intent copy or refine homepage internal links |
| 3 | `estate sale organizers` | `/pages/estate-sale-tampa-hillsborough-county` | 63 | 0 | 15.0 | HIGH (90) | Create or improve a service-area page/section |
| 4 | `how to increase home value for appraisal` | `/blogs/news/how-to-increase-your-home-appraisal-value` | 73 | 0 | 27.8 | MEDIUM (50) | Create or refresh an educational guide |
| 5 | `estate sales palm harbor` | `/` | 114 | 1 | 8.9 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 6 | `estate sales palm harbor` | `/pages/estate-sale-palm-harbor-pinellas-county` | 51 | 0 | 10.7 | HIGH (70) | Create or improve a service-area page/section |
| 7 | `estate sales tarpon springs` | `/pages/tarpon-springs-estate-sale-in-woodfield` | 80 | 0 | 7.0 | HIGH (70) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 8 | `estate organization service` | `/` | 59 | 0 | 12.3 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 9 | `estate sale and appraisal services` | `/` | 93 | 0 | 6.9 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 10 | `estate cleanout services` | `/pages/estate-cleanout-services` | 48 | 0 | 15.1 | HIGH (70) | Expand matching service page with FAQs, process, and CTA |
| 11 | `estate sale organizer` | `/pages/estate-sale-tampa-hillsborough-county` | 41 | 0 | 19.6 | HIGH (90) | Create or improve a service-area page/section |
| 12 | `estate sale organizers` | `/pages/13925-pathfinder-drive-tampa-florida` | 57 | 0 | 9.1 | HIGH (90) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 13 | `tampa personal property appraisers` | `/pages/personal-property-appraisal` | 64 | 0 | 8.2 | HIGH (70) | Expand appraisal page into a stronger service landing page |
| 14 | `estate sale planners` | `/` | 45 | 0 | 15.8 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 15 | `estate sale organizer` | `/` | 57 | 0 | 5.7 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |

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

Raw JSON: `data/audit_output/post_deploy_measurement_baseline_20260629T132631Z.json`