# Post-Deploy Measurement Baseline - organizinglifeservices.com
_Generated 2026-07-20 12:43 UTC_

## Overall Read
**Status: Pass with SEO warnings, fail on conversion-tracking trust.**

The live SEO changes are rendering, but GA4 is currently counting passive/page-load behavior as key events. Do not treat the current conversion total as a business KPI until GA4 key events are cleaned up.

## 1. GA4 Conversion Tracking
**Window:** `2026-06-22 -> 2026-07-19`

| Metric | Prior | Current | Delta |
|---|---:|---:|---:|
| Sessions | 1,009 | 1,101 | +9.1% |
| keyEvents | 1,549 | 1,778 | +14.8% |
| Key events/session | - | 1.61 | - |

**Trust assessment:** `fail`
- **HIGH**: Passive events such as page views or page-load events are counted as key events.
- **MEDIUM**: Key events per session is unusually high for real lead tracking.

**GA4 Admin key-event config access:** `unavailable`
- Use the GA4 UI cleanup runbook now, or enable Google Analytics Admin API in GCP if you want this repo to inspect key-event configuration directly.
- Reason: `Google Analytics Admin API is disabled in the service-account GCP project.`

Top key-event rows:
| Event | Class | Key events | Event count |
|---|---|---:|---:|
| `page_view` | passive_or_pageview | 1,673 | 1,673 |
| `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 87 | 87 |
| `form_submit` | lead_intent | 18 | 18 |
| `session_start` | passive_or_pageview | 0 | 1,101 |
| `first_visit` | passive_or_pageview | 0 | 962 |
| `user_engagement` | passive_or_pageview | 0 | 958 |
| `scroll` | passive_or_pageview | 0 | 202 |
| `form_start` | other | 0 | 52 |
| `search` | other | 0 | 29 |
| `click` | other | 0 | 10 |
| `view_search_results` | passive_or_pageview | 0 | 8 |
| `view_item` | other | 0 | 1 |

Top organic landing-page key-event rows:
| Landing page | Event | Class | Key events | Sessions |
|---|---|---|---:|---:|
| `/` | `page_view` | passive_or_pageview | 277 | 114 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `page_view` | passive_or_pageview | 19 | 13 |
| `/pages/estate-sale-dunedin-florida` | `page_view` | passive_or_pageview | 19 | 11 |
| `/pages/estate-sale-new-port-richey-florida` | `page_view` | passive_or_pageview | 18 | 12 |
| `/` | `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 17 | 11 |
| `/pages/estate-sale-tampa-hillsborough-county` | `page_view` | passive_or_pageview | 16 | 7 |
| `/blogs/news/estate-auction-vs-estate-sale-pros-and-cons` | `page_view` | passive_or_pageview | 14 | 11 |
| `/pages/estate-liquidation` | `page_view` | passive_or_pageview | 14 | 9 |
| `/pages/estate-sale-pasco-county` | `page_view` | passive_or_pageview | 13 | 6 |
| `/pages/sell-your-house-florida` | `page_view` | passive_or_pageview | 9 | 5 |
| `/pages/what-is-an-estate-sale` | `page_view` | passive_or_pageview | 8 | 6 |
| `/blogs/news/a-comprehensive-guide-to-wills-and-estate-planning` | `page_view` | passive_or_pageview | 8 | 5 |

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
**GSC window:** `2026-06-20 -> 2026-07-17`

| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `estate sale organizers` | `/` | 293 | 1 | 11.1 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 2 | `estate sale organizers` | `/pages/estate-sale-tampa-hillsborough-county` | 119 | 0 | 24.9 | HIGH (90) | Create or improve a service-area page/section |
| 3 | `estate sales palm harbor` | `/pages/estate-sale-palm-harbor-pinellas-county` | 293 | 4 | 9.5 | HIGH (70) | Create or improve a service-area page/section |
| 4 | `estate sales near me` | `/pages/estate-sale-new-port-richey-florida` | 186 | 0 | 9.2 | MEDIUM (55) | Review existing page intent and title/meta alignment |
| 5 | `estate sales` | `/pages/estate-sale-new-port-richey-florida` | 201 | 2 | 7.9 | HIGH (70) | Review existing page intent and title/meta alignment |
| 6 | `estate sales new port richey` | `/pages/estate-sale-new-port-richey-florida` | 105 | 1 | 10.9 | HIGH (70) | Review existing page intent and title/meta alignment |
| 7 | `how to increase home value for appraisal` | `/blogs/news/how-to-increase-your-home-appraisal-value` | 87 | 0 | 28.2 | MEDIUM (50) | Create or refresh an educational guide |
| 8 | `estate sales tarpon springs` | `/pages/tarpon-springs-estate-sale-in-woodfield` | 106 | 0 | 7.1 | HIGH (70) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 9 | `estate sale organizers` | `/pages/13925-pathfinder-drive-tampa-florida` | 90 | 0 | 8.7 | HIGH (90) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 10 | `estate sales near me` | `/pages/estate-sale-palm-harbor-pinellas-county` | 154 | 2 | 7.9 | MEDIUM (55) | Create or improve a service-area page/section |
| 11 | `estate sale organizer` | `/` | 98 | 0 | 5.1 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 12 | `estate sales near me` | `/pages/estate-sale-citrus-county` | 128 | 1 | 8.9 | MEDIUM (55) | Create or improve a service-area page/section |
| 13 | `estate sale organizer` | `/pages/estate-sale-tampa-hillsborough-county` | 81 | 0 | 8.0 | HIGH (90) | Create or improve a service-area page/section |
| 14 | `estate sale organizer` | `/pages/13925-pathfinder-drive-tampa-florida` | 78 | 0 | 5.5 | HIGH (90) | Use this demand to build/strengthen a permanent service-area page; leave legacy event shell noindexed |
| 15 | `estate sale organizers` | `/pages/estate-sale-planning` | 90 | 0 | 8.7 | HIGH (70) | Review existing page intent and title/meta alignment |

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

Raw JSON: `data/audit_output/post_deploy_measurement_baseline_20260720T124337Z.json`