# Post-Deploy Measurement Baseline - organizinglifeservices.com
_Generated 2026-08-31 12:10 UTC_

## Overall Read
**Status: Pass with SEO warnings, fail on conversion-tracking trust.**

The live SEO changes are rendering, but GA4 is currently counting passive/page-load behavior as key events. Do not treat the current conversion total as a business KPI until GA4 key events are cleaned up.

## 1. GA4 Conversion Tracking
**Window:** `2026-08-03 -> 2026-08-30`

| Metric | Prior | Current | Delta |
|---|---:|---:|---:|
| Sessions | 1,289 | 1,604 | +24.4% |
| keyEvents | 1,685 | 30 | -98.2% |
| Key events/session | - | 0.02 | - |

**Trust assessment:** `fail`
- **HIGH**: Passive events such as page views or page-load events are counted as key events.

**GA4 Admin key-event config access:** `ok`
- No passive/page-view key events found in Admin API config.

Top key-event rows:
| Event | Class | Key events | Event count |
|---|---|---:|---:|
| `form_submit` | lead_intent | 19 | 19 |
| `phone_call_clicks` | lead_intent | 8 | 8 |
| `page_view` | passive_or_pageview | 2 | 2,239 |
| `ads_conversion_Contact_Page_load_https_1` | passive_or_pageview | 1 | 91 |
| `session_start` | passive_or_pageview | 0 | 1,611 |
| `user_engagement` | passive_or_pageview | 0 | 1,220 |
| `first_visit` | passive_or_pageview | 0 | 1,214 |
| `scroll` | passive_or_pageview | 0 | 499 |
| `form_start` | other | 0 | 60 |
| `click` | other | 0 | 20 |
| `view_item` | other | 0 | 3 |
| `search` | other | 0 | 2 |

Top organic landing-page key-event rows:
| Landing page | Event | Class | Key events | Sessions |
|---|---|---|---:|---:|
| `/` | `form_submit` | lead_intent | 2 | 2 |
| `/` | `phone_call_clicks` | lead_intent | 2 | 2 |
| `/pages/13925-pathfinder-drive-tampa-florida` | `page_view` | passive_or_pageview | 1 | 1 |
| `/` | `page_view` | passive_or_pageview | 0 | 52 |
| `/` | `session_start` | passive_or_pageview | 0 | 52 |
| `/` | `user_engagement` | passive_or_pageview | 0 | 44 |
| `/` | `first_visit` | passive_or_pageview | 0 | 39 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `page_view` | passive_or_pageview | 0 | 11 |
| `/pages/estate-sale-palm-harbor-pinellas-county` | `session_start` | passive_or_pageview | 0 | 11 |
| `/pages/estate-sale-new-port-richey-florida` | `page_view` | passive_or_pageview | 0 | 10 |
| `/pages/estate-sale-new-port-richey-florida` | `session_start` | passive_or_pageview | 0 | 10 |
| `/` | `scroll` | passive_or_pageview | 0 | 9 |

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
**GSC window:** `2026-08-01 -> 2026-08-28`

| Priority | Query | Page | Impr. | Clicks | Pos. | Lead | Action |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `estate sale organizers` | `/` | 272 | 0 | 15.9 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |
| 2 | `estate sales near me` | `/pages/estate-sale-new-port-richey-florida` | 386 | 6 | 9.3 | MEDIUM (55) | Review existing page intent and title/meta alignment |
| 3 | `estate cleanout near me` | `/` | 264 | 0 | 1.2 | MEDIUM (55) | Expand homepage service-intent copy or refine homepage internal links |
| 4 | `estate sale organizers` | `/pages/estate-sale-tampa-hillsborough-county` | 101 | 0 | 24.6 | HIGH (90) | Create or improve a service-area page/section |
| 5 | `estate sale planners` | `/` | 108 | 0 | 15.2 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 6 | `estate sales near me` | `/pages/estate-sale-citrus-county` | 180 | 1 | 8.8 | MEDIUM (55) | Create or improve a service-area page/section |
| 7 | `how to increase home value for appraisal` | `/blogs/news/how-to-increase-your-home-appraisal-value` | 101 | 0 | 27.8 | MEDIUM (50) | Create or refresh an educational guide |
| 8 | `estate sales near me` | `/pages/estate-sale-dunedin-florida` | 81 | 0 | 10.6 | MEDIUM (55) | Create or improve a service-area page/section |
| 9 | `estate sales near me` | `/pages/estate-sale-palm-harbor-pinellas-county` | 161 | 2 | 8.5 | MEDIUM (55) | Create or improve a service-area page/section |
| 10 | `estate sale helpers` | `/` | 76 | 0 | 14.2 | MEDIUM (50) | Expand homepage service-intent copy or refine homepage internal links |
| 11 | `estate sales new port richey` | `/pages/estate-sale-new-port-richey-florida` | 62 | 0 | 10.7 | HIGH (70) | Review existing page intent and title/meta alignment |
| 12 | `estate sales citrus county` | `/pages/estate-sale-citrus-county` | 60 | 0 | 11.2 | HIGH (70) | Create or improve a service-area page/section |
| 13 | `estate sales palm harbor` | `/pages/estate-sale-palm-harbor-pinellas-county` | 85 | 0 | 9.5 | HIGH (70) | Create or improve a service-area page/section |
| 14 | `estate sale organizer` | `/pages/estate-sale-tampa-hillsborough-county` | 72 | 0 | 7.6 | HIGH (90) | Create or improve a service-area page/section |
| 15 | `downsizing sales services bradenton fl` | `/` | 51 | 0 | 19.3 | HIGH (70) | Expand homepage service-intent copy or refine homepage internal links |

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

Raw JSON: `data/audit_output/post_deploy_measurement_baseline_20260831T121003Z.json`