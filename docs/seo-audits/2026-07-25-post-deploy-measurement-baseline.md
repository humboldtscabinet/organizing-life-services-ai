# Post-Deploy Measurement Baseline - organizinglifeservices.com
_Generated 2026-07-25 15:17 UTC_

## Overall Read
**Status: Pass with SEO warnings, fail on conversion-tracking trust.**

The live SEO changes are rendering, but GA4 is currently counting passive/page-load behavior as key events. Do not treat the current conversion total as a business KPI until GA4 key events are cleaned up.

## 1. GA4 Conversion Tracking
**Window:** `2026-06-27 -> 2026-07-24`

| Metric | Prior | Current | Delta |
|---|---:|---:|---:|
| Sessions | 566 | 1,243 | +119.6% |
| keyEvents | 1,012 | 1,981 | +95.8% |
| Key events/session | - | 1.59 | - |

**Trust assessment:** `fail`
- **HIGH**: Passive events such as page views or page-load events are counted as key events.
- **MEDIUM**: Key events per session is unusually high for real lead tracking.

**GA4 Admin key-event config access:** `unavailable`
- Use the GA4 UI cleanup runbook now, or enable Google Analytics Admin API in GCP if you want this repo to inspect key-event configuration directly.
- Reason: `Google Analytics Admin API is disabled in the service-account GCP project.`

Top key-event rows:
| Event | Class | Key events | Event count |
|---|---|---:|---:|
| `page_view` | passive_or_pageview | 1,870 | 1,898 |
| `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 94 | 97 |
| `form_submit` | lead_intent | 17 | 17 |
| `session_start` | passive_or_pageview | 0 | 1,242 |
| `user_engagement` | passive_or_pageview | 0 | 1,101 |
| `first_visit` | passive_or_pageview | 0 | 1,087 |
| `scroll` | passive_or_pageview | 0 | 214 |
| `form_start` | other | 0 | 52 |
| `search` | other | 0 | 29 |
| `click` | other | 0 | 12 |
| `view_search_results` | passive_or_pageview | 0 | 8 |
| `view_item` | other | 0 | 1 |

Top organic landing-page key-event rows:
| Landing page | Event | Class | Key events | Sessions |
|---|---|---|---:|---:|
| `/` | `page_view` | passive_or_pageview | 282 | 115 |
| `/pages/estate-sale-dunedin-florida` | `page_view` | passive_or_pageview | 19 | 11 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `page_view` | passive_or_pageview | 18 | 12 |
| `/pages/organizing-life-estate-sale-company-successful-sales` | `page_view` | passive_or_pageview | 17 | 10 |
| `/` | `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 15 | 11 |
| `/pages/estate-liquidation` | `page_view` | passive_or_pageview | 15 | 9 |
| `/pages/estate-sale-tampa-hillsborough-county` | `page_view` | passive_or_pageview | 14 | 6 |
| `/pages/estate-sale-new-port-richey-florida` | `page_view` | passive_or_pageview | 13 | 8 |
| `/pages/estate-sale-pasco-county` | `page_view` | passive_or_pageview | 13 | 6 |
| `/blogs/news/estate-auction-vs-estate-sale-pros-and-cons` | `page_view` | passive_or_pageview | 11 | 10 |
| `/pages/about-us` | `page_view` | passive_or_pageview | 9 | 7 |
| `/pages/sell-your-house-florida` | `page_view` | passive_or_pageview | 9 | 5 |

## 2. Post-Deploy Live SEO Verification
**Status:** `warning`

| Page | Status | Title len | Meta len | H1s | Robots | Issues |
|---|---|---:|---:|---:|---|---|
| Homepage | warning | 49 | 139 | 1 | `` | low_alt_text_coverage, slow_response |
| Personal Property Appraisal | warning | 58 | 151 | 1 | `` | slow_response |
| Contact | warning | 54 | 156 | 1 | `` | slow_response |
| About | warning | 35 | 147 | 1 | `` | slow_response |
| Testimonials | warning | 53 | 147 | 1 | `` | slow_response |
| Senior Services | warning | 31 | 160 | 1 | `` | slow_response |
| All Collections | warning | 57 |  | 2 | `noindex,follow` | missing_meta_description, multiple_h1, noindex, slow_response |
| Fees Products | warning | 62 |  | 2 | `noindex,follow` | missing_meta_description, multiple_h1, noindex, slow_response |
| Fee Product CC 2.7 | warning | 68 |  | 1 | `noindex,follow` | title_too_long, missing_meta_description, noindex, low_alt_text_coverage, slow_response |
| Fee Product CC 2.7 Duplicate | warning | 68 | 87 | 1 | `noindex,follow` | title_too_long, noindex, low_alt_text_coverage, slow_response |
| Processing Fee Product | warning | 63 |  | 1 | `noindex,follow` | missing_meta_description, noindex, low_alt_text_coverage, slow_response |

## 3. Next Content Targets
**GSC window:** `2026-06-25 -> 2026-07-22`

| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `estate sale organizers` | `/` | 302 | 1 | 10.6 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 2 | `estate sale organizers` | `/pages/estate-sale-tampa-hillsborough-county` | 145 | 0 | 24.6 | HIGH (90) | Create or improve a service-area page/section |
| 3 | `estate sales palm harbor` | `/pages/estate-sale-palm-harbor-pinellas-county` | 325 | 4 | 9.3 | HIGH (70) | Create or improve a service-area page/section |
| 4 | `estate sales new port richey` | `/pages/estate-sale-new-port-richey-florida` | 128 | 1 | 10.8 | HIGH (70) | Review existing page intent and title/meta alignment |
| 5 | `estate sales near me` | `/pages/estate-sale-new-port-richey-florida` | 193 | 0 | 9.2 | MEDIUM (55) | Review existing page intent and title/meta alignment |
| 6 | `estate sales` | `/pages/estate-sale-new-port-richey-florida` | 188 | 2 | 7.8 | HIGH (70) | Review existing page intent and title/meta alignment |
| 7 | `estate sale organizers` | `/pages/13925-pathfinder-drive-tampa-florida` | 108 | 0 | 7.7 | HIGH (90) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 8 | `how to increase home value for appraisal` | `/blogs/news/how-to-increase-your-home-appraisal-value` | 91 | 0 | 26.6 | MEDIUM (50) | Create or refresh an educational guide |
| 9 | `estate sale organizers` | `/pages/estate-sale-planning` | 108 | 0 | 7.7 | HIGH (70) | Review existing page intent and title/meta alignment |
| 10 | `estate sale organizers` | `/pages/senior-services` | 108 | 0 | 7.7 | HIGH (70) | Review existing page intent and title/meta alignment |
| 11 | `estate sales near me` | `/pages/estate-sale-citrus-county` | 138 | 1 | 8.8 | MEDIUM (55) | Create or improve a service-area page/section |
| 12 | `estate sales tarpon springs` | `/pages/tarpon-springs-estate-sale-in-woodfield` | 104 | 0 | 7.2 | HIGH (70) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 13 | `estate sales near me` | `/pages/estate-sale-palm-harbor-pinellas-county` | 176 | 3 | 8.0 | MEDIUM (55) | Create or improve a service-area page/section |
| 14 | `estate sale organizer` | `/` | 98 | 0 | 4.9 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 15 | `estate sale organizer` | `/pages/estate-sale-tampa-hillsborough-county` | 84 | 0 | 8.3 | HIGH (90) | Create or improve a service-area page/section |

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

**GBP API:** `blocked_or_unavailable` - Client error '429 Too Many Requests' for url 'https://mybusinessaccountmanagement.googleapis.com/v1/accounts'

## 5. Ongoing Reporting
- This report is generated by `data/post_deploy_measurement_baseline.py`.
- Weekly automation now runs both the deep SEO audit and this measurement baseline.
- GTM audit available: 5 tags, 1 triggers, 0 flagged findings.

## Remediation Checklist
1. Follow `docs/runbooks/ga4-key-event-cleanup.md`.
2. In GA4 Admin, unmark `page_view` as a key event.
3. Stop counting `ads_conversion_Contact_Page_load_https_1` as a conversion; a contact-page view is not a lead.
4. Keep or create true lead key events: form submit, phone click, email click, and contact CTA click.
5. If API inspection is desired, enable Google Analytics Admin API in GCP; UI cleanup works now.
6. After the GA4 change, rerun this report and use lead-intent key events as the business KPI.
7. Expand the highest-priority content targets only after the tracking baseline is clean.

Raw JSON: `data/audit_output/post_deploy_measurement_baseline_20260725T151707Z.json`