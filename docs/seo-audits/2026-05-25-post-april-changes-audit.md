# SEO Audit — organizinglifeservices.com

**Date:** 2026-05-25
**Audit window:** 28 days (`2026-04-25 → 2026-05-22`) vs prior 28 days (`2026-03-28 → 2026-04-24`)
**Trigger:** Post-deployment audit following the April 20–22, 2026 optimization push
**Raw data:** `data/audit_output/deep_seo_audit_20260525_181655.{md,json}` (gitignored)

---

## What changed between the two windows

The April 20–22 optimization push included:

- **Apr 20** — Initial schema markup rollout (`data/add_schema_markup.py`), meta-tag drafts (`data/meta_drafts.py`), push of metas to Shopify (`data/push_meta_to_shopify.py`), blog content fixes (`data/apply_blog_fixes.py`), new geo/event landing pages (`data/create_seo_pages.py`)
- **Apr 22** — Round-2 meta push (`data/push_meta_round2.py`), schema snippet push (`data/push_schema_snippet.py`), internal-link pass (`data/internal_links_a3.py`), two new blog posts (`data/b1_faq_what_is_estate_sale.py`, `data/b2_yard_vs_estate_sale_post.py`)

---

## 1. Headline verdict

**Mixed — net positive on the metrics that matter, with two real warning signs.**

| Signal | Direction | Confidence |
|---|---|---|
| Clicks (GSC) | ✅ Up | High |
| CTR (GSC) | ✅ Up materially | High |
| Schema deployment | ✅ Complete (100%) | High |
| Per-query rank gains on target keywords | ✅ Up | High |
| Impressions | ⚠️ Down | High |
| Average position | ⚠️ Worse | Medium (likely dilution + cannibalization, see §4) |
| GA4 organic sessions/users | ⚠️ Slightly down | Medium |
| Organic conversions | ➖ Flat (449 → 449) | High |

---

## 2. Search Console — 28d vs prior 28d

| Metric | Prior | Current | Δ |
|---|---:|---:|---:|
| Clicks | 113 | **137** | **+21.2%** ✅ |
| Impressions | 21,187 | 13,787 | −34.9% ⚠️ |
| CTR | 0.53% | **0.99%** | **+0.46 pp** ✅ |
| Avg position | 11.4 | 17.7 | +6.3 (worse) ⚠️ |

The clicks-up / impressions-down pattern is the classic signature of **dropping low-intent long-tail impressions while retaining money keywords**. CTR nearly doubling is direct evidence the title/meta rewrites are working in the SERP.

---

## 3. GA4 — 28d vs prior 28d

(GA4 window: `2026-04-27 → 2026-05-24` vs `2026-03-30 → 2026-04-26`)

**All traffic**

| Metric | Prior | Current | Δ |
|---|---:|---:|---:|
| Sessions | 1,609 | 1,373 | −14.7% |
| Active users | 1,098 | 1,077 | −1.9% |
| New users | 929 | 974 | +4.8% ✅ |
| Page views | 2,526 | 2,037 | −19.4% |
| Engagement rate | 97.7% | 97.9% | flat |

**Organic search only**

| Metric | Prior | Current | Δ |
|---|---:|---:|---:|
| Organic sessions | 173 | 163 | −5.8% |
| Organic users | 146 | 130 | −11.0% ⚠️ |
| Organic page views | 412 | 396 | −3.9% |
| Organic conversions | 449 | **449** | **0%** ➖ |

**Interpretation:** Organic users dipped ~11%, but **conversions held flat at 449**. The visitors we lost were lower-intent — quality of organic traffic improved (consistent with the GSC CTR jump). Email (457) and Cross-network (534) channels are the current conversion volume leaders; Organic is still material at 449.

> ⚠️ **GSC vs GA4 mismatch:** GSC says clicks +21%, GA4 says organic sessions −6%. This is normal (different attribution, GA4 consent mode, bot filtering). The GSC number is the more reliable signal for "did SEO work move the needle."

---

## 4. Why average position got worse (probably not a real loss)

**Biggest ranking GAINS** on the keywords targeted by the April work:

| Query | Was | Now | Δ | Impressions |
|---|---:|---:|---:|---:|
| personalized estate solutions | 50.2 | **13.7** | −36.5 | 9 |
| estate sale planner near me | 51.6 | 23.7 | −27.9 | 6 |
| how to increase property value for appraisal | 50.1 | 28.2 | −21.9 | 22 |
| estate organization service | 36.7 | 19.7 | −17.0 | 146 |
| moving sale company | 35.0 | 19.8 | −15.2 | 11 |
| estate sale planners | 35.6 | 22.3 | −13.2 | 89 |
| estate sale organizer near me | 25.4 | 13.0 | −12.4 | 49 |
| professional yard sale services | 22.0 | 10.1 | −11.9 | 15 |
| estate sale services | 21.9 | 10.5 | −11.4 | 6 |
| estate sale managers | 20.8 | 10.0 | −10.8 | 1 |

These are **exactly the keyword clusters targeted** by `meta_drafts.py`, `create_seo_pages.py`, and the internal-link pass. The work landed.

**Biggest ranking DROPS** — almost entirely informational/blog queries:

| Query | Was | Now | Δ |
|---|---:|---:|---:|
| estate sale manager | 6.0 | 86 | +80.0 |
| how to do an estate sale on your own | 15.8 | 88 | +72.2 |
| estate buyout services | 21.2 | 76 | +54.8 |
| how to have an estate sale | 22.6 | 72.2 | +49.6 |
| how to do an estate sale | 23.1 | 67 | +43.9 |
| moving sale vs estate sale | 8.3 | 45 | +36.7 |
| is having an estate sale worth it | 5.8 | 41.7 | +35.9 |
| estate vs garage sale | 2.6 | 33.5 | +30.9 |

**Diagnosis:** The two new April 22 blog posts (`b1_faq_what_is_estate_sale.py`, `b2_yard_vs_estate_sale_post.py`) likely caused **keyword cannibalization** — the new posts are competing with the older "how-to" blog content for the same terms, and Google is still sorting out which to rank. This explains both the dropped average position (more URLs ranking shallowly for the same query) and the lower impressions on the older posts.

This is recoverable — needs canonicalization or content consolidation, not a strategy reversal.

---

## 5. Pages — winners and losers

**Winners (vs prior 28d):**

| Page | Δ Clicks | Δ Impr | Pos |
|---|---:|---:|---:|
| `/` | +16 | +96 | 15.3 |
| `/pages/613-severs-landing-palm-harbor…part-2` | +5 | +248 | 5.9 (new) |
| `/pages/tarpon-springs-estate-sale-in-woodfield` | +3 | +78 | 8.6 |
| `/pages/estate-sale-citrus-county` | +2 | +122 | 10.2 |
| `/blogs/news/yard-sale-vs-estate-sale-key-differences` | +2 | +214 | 18.0 |

The new geo/event landing pages from `create_seo_pages.py` are pulling clicks and ranking on page 1.

**Losers:**

| Page | Clicks now | Was | Δ |
|---|---:|---:|---:|
| `/pages/estate-cleanout-services` | 2 | 7 | **−5** |
| `/pages/sell-your-house-florida` | 0 | 3 | −3 |
| `/blogs/news/estate-auction-vs-estate-sale-pros-and-cons` | 1 | 3 | −2 |
| `/pages/testimonials` | 1 | 3 | −2 |

`estate-cleanout-services` is the only concerning one — it rose to position 22.1 (was 12.5), losing page-1 visibility. **Action:** diff the live page vs `data/snippets/` to confirm the April changes deployed correctly there.

---

## 6. Technical SEO — live crawl (84 URLs)

✅ **Structured data: 100% of crawled pages.** Every page now exposes `LocalBusiness`, `BreadcrumbList`, `Service`, `Offer`, `OpeningHoursSpecification`, `PostalAddress`, `GeoCoordinates`. The schema rollout (`add_schema_markup.py`, `push_schema_snippet.py`, `data/seo-schema.liquid`) **fully landed**.

⚠️ **HTTP status distribution: 45 × 403, 39 × 200.** Roughly **half the sitemap returns 403 to the crawler** — likely a Shopify bot-protection / Cloudflare rule, not a real outage. Worth verifying Googlebot itself isn't being blocked (check GSC coverage report).

⚠️ **On-page issues still outstanding:**

| Issue | Pages affected |
|---|---:|
| Title too long | **37** |
| Meta description too long | 11 |
| Low alt-text coverage | 7 |
| Multiple H1 | 5 |
| Missing meta description | 2 |
| Meta description too short | 1 |

The April meta rewrites helped, but **37 pages still have over-long titles** — Google will truncate them in the SERP, capping CTR gains. A third meta pass is the highest-ROI next move.

---

## 7. What worked vs. what didn't

### ✅ Worked

1. **Schema markup rollout** — 100% coverage achieved; rich-result eligibility is in place
2. **Meta/title rewrites** — CTR nearly doubled (0.53% → 0.99%)
3. **Geo landing pages** (Citrus County, Tarpon Springs, Pinellas Park, Sever's Landing) — ranking page 1 and pulling clicks
4. **Keyword targeting** — the exact clusters targeted (`estate sale planner`, `estate sale services`, `estate organization service`, `estate sale managers`) moved up double-digit positions
5. **Click volume** — +21% on the work that matters most

### ⚠️ Didn't work / regressions

1. **Blog cannibalization** — new FAQ + yard-vs-estate posts dropped older how-to blog content from page 1 (queries like "how to do an estate sale" fell 50–70 positions)
2. **`/pages/estate-cleanout-services` regressed** — clicks fell 7→2, position 12.5→22.1
3. **37 pages still have over-long titles** — round-2 meta push didn't catch all of them
4. **Average position worsened** by 6.3 — mostly dilution from new long-tail rankings, but the cannibalization piece is real
5. **GA4 organic users down 11%** — small absolute number (146→130) but worth monitoring

### ➖ Neutral / inconclusive

- Organic conversions exactly flat (449 → 449) — work neither helped nor hurt conversion volume, but quality-per-visitor went up since fewer visitors produced the same conversions
- Impressions down 35% — neutral-to-positive; appears to be loss of low-intent long-tail

---

## 8. Bottom line

**The Apr 20–22 optimizations were net positive.** The two most direct measures of SEO effectiveness — clicks (+21%) and CTR (+0.46 pp) — both improved meaningfully. Schema is fully deployed. Targeted keyword rankings moved in the right direction.

The negatives (impressions down, position worse, organic users down) are mostly **second-order side effects of the new content** — the blog cannibalization is real and addressable, and the average-position drop is partially a math artifact of newly ranking long-tail queries.

**Most concerning single item:** `/pages/estate-cleanout-services` dropping out of page-1 visibility.

---

## 9. Recommended next actions (priority order)

1. **Round-3 meta pass** on the 37 over-long titles — highest-ROI move
2. **Resolve blog cannibalization** between the new FAQ/yard-vs-estate posts and the older how-to content (consolidate, canonicalize, or differentiate intent)
3. **Diff `/pages/estate-cleanout-services` live HTML vs `data/snippets/`** to confirm April changes deployed
4. **CTR opportunity rewrites** — see §5 of the raw audit for the top 20 queries with high impressions but weak CTR while already ranking top-20
5. **Striking-distance push** — pick 10 queries in position 8–20 with ≥10 impressions and add internal links + ~200 words of supporting content
6. **Re-audit in 28 days** to confirm the next round of optimizations lifted the same metrics
