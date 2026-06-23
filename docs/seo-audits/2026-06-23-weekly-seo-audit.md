# Weekly SEO Audit - organizinglifeservices.com

**Generated:** 2026-06-23
**Audit window:** 28 days (`2026-05-24 -> 2026-06-20`) vs prior 28 days (`2026-04-26 -> 2026-05-23`)
**Trigger:** First successful GitHub Actions weekly SEO audit run
**Raw data:** [`data/audit_output/deep_seo_audit_20260623_213027.md`](../../data/audit_output/deep_seo_audit_20260623_213027.md) and [`data/audit_output/deep_seo_audit_20260623_213027.json`](../../data/audit_output/deep_seo_audit_20260623_213027.json)

---

## Headline Verdict

**Mixed, but not alarming.** Search visibility dipped slightly, overall GA4 traffic fell sharply, but organic sessions held flat and all top inspected pages are indexed. The next useful work is not another broad push; it is targeted SERP CTR cleanup and technical hygiene on pages that already have impressions.

| Signal | Prior | Current | Delta | Read |
|---|---:|---:|---:|---|
| GSC clicks | 135 | 131 | -3.0% | Slightly down |
| GSC impressions | 13,747 | 13,078 | -4.9% | Slightly down |
| GSC CTR | 0.98% | 1.00% | +0.02 pp | Flat/slightly better |
| Weighted avg position | 18.0 | 17.4 | -0.6 | Slightly better |
| GA4 sessions | 1,421 | 877 | -38.3% | Broad traffic drop |
| Organic sessions | 164 | 164 | 0.0% | Stable |
| Organic users | 132 | 133 | +0.8% | Stable |
| Organic conversions | 471 | 380 | -19.3% | Needs review |

The GA4 all-traffic decline is larger than the organic decline, so this audit does not point to SEO as the main source of the traffic drop. Organic is flat on sessions/users, while GSC average position improved a bit. The conversion drop should be checked against GA4 event definitions before treating it as a business-loss number.

---

## Indexing And Crawl Health

The strongest positive signal: Google URL Inspection returned `PASS` for all 20 inspected top-impression pages.

| URL Inspection signal | Count |
|---|---:|
| PASS verdict | 20 |
| Submitted and indexed | 20 |
| Canonical mismatches | 0 |

Browser crawl health was also good at the transport level:

| Crawl signal | Value |
|---|---:|
| URLs crawled | 80 |
| 200 OK | 80 |
| Average response | 348 ms |
| Average page size | 646 KB |

Interpretation: the site is reachable, indexable, and not showing the old false-positive Googlebot blocking issue. The remaining crawl issues are on-page cleanup problems, not server availability problems.

---

## Main Issues Found

| Issue | Pages | Read |
|---|---:|---|
| `title_too_long` | 20 | Mostly portfolio/event pages plus blog index |
| `multiple_h1` | 19 | Theme/content structure cleanup |
| `missing_meta_description` | 19 | Mostly old event/collection pages |
| `noindex` | 18 | Expected for intentionally noindexed dead event pages |
| `low_alt_text_coverage` | 7 | Blog image cleanup |
| `meta_description_too_long` | 3 | Easy rewrite candidates |
| `title_too_short` | 1 | Personal property appraisal page |

The `noindex` count appears expected because prior work deliberately marked 18 thin past-event pages `noindex,follow`. Do not "fix" those unless the page is being rebuilt into a real landing page.

Examples worth addressing:

- `/pages/personal-property-appraisal`: title is only 27 characters despite 300 impressions and page-position room to improve.
- `/pages/contact-us`: 3 H1s on a conversion-critical page.
- `/pages/about-us`, `/pages/testimonials`, `/pages/senior-services`: multiple H1s on trust/support pages.
- `/collections/all` and `/collections/fees-products`: missing meta descriptions and multiple H1s.
- `/blogs/news`: title and meta description are both too long.
- Several older event pages have very long titles and no meta descriptions, but many are intentionally noindexed.

---

## Highest-Value SEO Opportunities

These are the best next targets because they already have impressions, decent ranking, and low CTR.

| Query | Page | Impressions | CTR | Position |
|---|---|---:|---:|---:|
| estate sale organizers | homepage | 245 | 0.00% | 14.6 |
| estate sales palm harbor | homepage | 115 | 0.00% | 8.6 |
| estate sale companies near me | homepage | 99 | 0.00% | 19.1 |
| estate sale and appraisal services | homepage | 95 | 0.00% | 6.5 |
| estate organization service | homepage | 70 | 0.00% | 11.4 |
| estate sales tarpon springs | Tarpon Springs event/page | 69 | 0.00% | 7.3 |
| downsizing specialist | downsizing page | 64 | 0.00% | 4.8 |
| tampa personal property appraisers | appraisal page | 61 | 0.00% | 7.9 |

The biggest pattern is homepage query mismatch: Google is showing the homepage for many service-intent searches, but searchers are not clicking. The homepage snippet likely needs clearer "Estate Sale Organizers / Estate Sale Company / Appraisal / Downsizing" language above the fold and in metadata, without stuffing.

---

## Recommended Next Actions

1. **Rewrite the Personal Property Appraisal title/meta first.**
   This page has strong business intent and appears in striking-distance searches like `tampa personal property appraisers` and `estate sale and appraisal services`.

2. **Fix H1 structure on conversion/trust pages.**
   Start with contact, about, testimonials, and senior services. Keep one clear page H1; demote decorative section headings to H2/H3.

3. **Update homepage metadata around the highest-impression service phrases.**
   Target the homepage terms already appearing in GSC: `estate sale organizers`, `estate sale companies near me`, `estate sale organizer near me`, and `estate sale and appraisal services`.

4. **Clean collection pages or noindex them intentionally.**
   `/collections/all` and `/collections/fees-products` look like Shopify utility pages. Either give them proper metadata and one H1, or intentionally remove them from search if they are not conversion pages.

5. **Treat old noindexed event pages as a backlog, not an emergency.**
   Leave the intentional `noindex,follow` pages alone unless rebuilding selected examples into polished case-study pages.

6. **Audit GA4 conversion definitions.**
   The reported organic conversion count is high relative to sessions. Confirm which events are counted as conversions before using the -19.3% delta as a business KPI.

---

## Decision

Merge the raw audit output and this summary. The automation is now useful, but the next site work should be targeted and human-reviewed, not a broad automated rewrite.
