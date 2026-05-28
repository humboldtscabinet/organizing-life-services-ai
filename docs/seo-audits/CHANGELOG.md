# SEO Changelog — organizinglifeservices.com

A running log of every SEO change deployed to the live site, the scripts that did it, and the hypothesis being tested. Read top-to-bottom for newest-first.

Each entry should answer:
- **What** changed (pages, fields, schema, links, content)
- **Why** (hypothesis: "we expect X to improve")
- **How** (script(s) run, commit SHA)
- **Result** (link to the audit that measured the outcome, once available)

---

## 2026-05-28 — XO Gallery alt-text completion (518 images → 100% coverage)

- **What:** Audited all 57 `xo_gallery.gallery_NN` shop metafields (5,080 total images across the site's gallery pages). Found 518 images with empty/missing `alt.en`. Filled 124 from the existing AI vision pass in `data/image_analysis_export.csv` (matched by filename, ignoring Shopify CDN size suffixes). For the remaining 394 — all uploaded after the last vision pass — generated templated alt text from each gallery's title (e.g. `"613 Severs Landing, Palm Harbor, FL, Estate Sale Part 1 — Organizing Life Services Tampa Bay estate sale, photo N"`). Verified post-write: **5,080/5,080 images now carry alt text (100%).**
- **Why:** Image alt text is a direct image-search ranking signal and an accessibility requirement. The 518 missing-alt images were all on gallery pages that draw past-sale long-tail traffic — leaving them blank was a free ranking loss. CSV-matched alts use the original AI-generated SEO descriptions; fallback alts use the gallery's location/title so they remain contextual and unique.
- **How:** `data/xo_gallery_alt_apply.py` (idempotent — only fills empty alts, never overwrites). Two flags: `--dry-run` previews changes; `--fallback` enables the templated-alt path for images not in the CSV. Affected gallery metafields: `gallery_43`, `gallery_68`, `gallery_69`, `gallery_70`.
- **Result:** Pending — re-crawl with `deep_seo_audit.py` after 2026-06-04 and check Google Search Console → Performance → Image search for impression lift on the affected gallery pages.

## 2026-05-28 — Geo expansion (6 cities) + round-4 page metas (9 pages) + top-6 article body upgrades

- **What:**
  - **Geo expansion:** Created 4 new city landing pages with ~600-word unique bodies, `LocalBusiness` JSON-LD (NAP + service area + serviceType), full title/desc metas, and idempotent `GEO-<HANDLE>-V1` markers: `estate-sale-st-petersburg-florida`, `estate-sale-largo-florida`, `estate-sale-new-port-richey-florida`, `estate-sale-wesley-chapel-florida`. Expanded 2 thin existing geo pages with the same content block + schema + meta: `estate-sale-clearwater-florida` (1,564 → 5,815 chars), `estate-sale-dunedin-florida` (1,190 → 5,401 chars).
  - **Round-4 page metas:** Pushed title_tag + description_tag (under 65 / 160 char Google windows) to 9 high-value pages that round-3 didn't cover: `testimonials`, `contact-us`, `estate-liquidators-tampa-bay`, `estate-sale-appraisal-services`, `estate-sale-companies-near-me`, `estate-sale-citrus-county`, `estate-sale-pasco-county`, `how-it-works`, `tarpon-springs-estate-sale-in-woodfield`. (All 34 blog articles already covered by round-3, so round-4 was scoped to pages only. 16 past-sale event pages with empty bodies were deliberately skipped — better candidates for a noindex pass.)
  - **Top-6 article body upgrades:** Prepended a keyword-optimized "Updated for 2026" H2 + ~250-word intro block to the 6 highest-impression articles: `estate-sale-vs-garage-sale-know-the-differences`, `pros-and-cons-of-estate-sales`, `how-to-increase-your-home-appraisal-value`, `estate-auction-vs-estate-sale-pros-and-cons`, `the-ultimate-guide-for-barbie-collector-buyers`, `how-to-plan-estate-sale`. Each block lands the primary keyword in the first 100 words, references 2026 context, and is idempotent via `BODY-UP-V1`.
- **Why:**
  - Geo: GSC striking-distance data shows "estate sales [city]" queries already ranking pos 5-15 for Palm Harbor / Tarpon Springs / Citrus — expanding to St. Pete, Largo, NPR, Wesley Chapel, Clearwater (expand), and Dunedin (expand) opens 6 more geo-keyword footholds with LocalBusiness schema for Local-Pack eligibility.
  - Round-4 pages: high-impression / high-conversion pages like `testimonials`, `contact-us`, and the service pages were rendering with the theme's brand-suffix fallback (130+ chars, truncated). Clean metas under the display window should lift CTR site-wide.
  - Body upgrades: top-6 articles had primary keyword buried mid-body. Prepending a keyword-in-first-100-words intro is the highest-ROI single edit for posts already at impressions 500+ but stuck at pos 15-24.
- **How:** `data/geo_pages_expansion.py`, `data/push_meta_round4_pages.py`, `data/article_body_upgrade_top6.py`. Verified end-to-end via `data/verify_session3.py` — 6/6 geo + 9/9 page metas + 6/6 body upgrades all present live.
- **Result:** Pending — re-run `gsc_pull_opportunities.py` + `deep_seo_audit.py` after 2026-06-18 to measure (a) new geo-page rankings for "estate sales [city]" queries, (b) CTR lift on the 9 round-4 pages, and (c) position movement on the 6 upgraded articles.

## 2026-05-28 — Quick-wins batch: full round-3 (37 URLs) + striking-distance H2s + 4 article FAQs + A4 intlinks

- **What:**
  - Flipped 21 additional round-3 drafts to `approved=true` and pushed all 37 title_tag + description_tag metafields (74 metafields total). Verified 37/37 OK via `verify_round3_state.py`.
  - Injected striking-distance H2 + targeted paragraph into 4 pages, each keyed by an idempotent marker: `estate-sale-citrus-county` (SD-ESNM-V1, "estate sales near me"), `tarpon-springs-estate-sale-in-woodfield` (SD-ESTS-V1, "estate sales in Tarpon Springs"), `personal-property-appraisal` (SD-TPPA-V1, "Tampa personal property appraisers"), `downsizing-moving-sales` (SD-DSPC-V1, "downsizing specialist").
  - Appended FAQ block + FAQPage JSON-LD to the top 4 articles by GSC impressions: `pros-and-cons-of-estate-sales` (FAQ-PCES-V1), `how-to-increase-your-home-appraisal-value` (FAQ-HIAV-V1), `estate-auction-vs-estate-sale-pros-and-cons` (FAQ-EAES-V1), `the-ultimate-guide-for-barbie-collector-buyers` (FAQ-BARB-V1). Each block answers 3 PAA-style queries with rich, original copy.
  - A4 internal-links pass: appended a standardized "Related Tampa Bay Estate Services" link block (INTLINKS-A4-V1) to the top 6 articles by impressions, with exact-match anchors to `/pages/estate-cleanout-services`, `/pages/personal-property-appraisal`, `/pages/downsizing-moving-sales`, `/pages/estate-sale-palm-harbor-pinellas-county`, `/pages/tarpon-springs-estate-sale-in-woodfield`, `/pages/estate-sale-citrus-county`, `/pages/fees-products`, `/pages/faqs`.
- **Why:**
  - Round-3 completion: 21 more URLs now ship clean meta in Google's display window → expected CTR lift broad across the blog.
  - Striking-distance: GSC showed 7 queries at position 5-15, ≥50 impressions, <2% CTR (`gsc_striking_distance_2026-05-28.json`). Adding the exact-match query as an H2 + ~150-word answer is the most reliable on-page lever to push these from page-2 to top-5.
  - FAQ rollout: top 4 articles by impressions have CTR ≤0.17%. FAQ blocks unlock PAA + Featured Snippet eligibility and lengthen low-bounce engagement on already-trafficked pages.
  - A4 intlinks distribute authority from the 6 highest-impression posts down to the commercial money pages + geo landers, with anchor text reinforced by the striking-distance queries we just published H2s for.
- **How:** `data/push_meta_round3_direct.py` (with retry+throttle), `data/gsc_pull_opportunities.py`, `data/page_apply_striking_distance.py`, `data/article_apply_top4_faqs.py`, `data/article_apply_intlinks_a4.py`. Verified end-to-end via `data/verify_quick_wins.py` (4/4 SD + 4/4 FAQ + 6/6 A4 markers present live) and `data/verify_round3_state.py` (37/37 metafields match drafts).
- **Result:** Pending — re-run `deep_seo_audit.py` and `gsc_pull_opportunities.py` after 2026-06-11 to measure CTR/position lift on the 7 striking-distance queries, the 4 FAQ articles, and overall round-3 set.

## 2026-05-28 — Theme title patch + round-3 metas (16 URLs) + homepage internal links + yard/garage FAQ

- **What:**
  - Patched live theme `layout/theme.liquid` (theme 153690210458) so a `global.title_tag` metafield renders verbatim with no brand-suffix append (`SEO-INTLINKS-V1` block also added, scoped to `template.name == 'index'`).
  - Pushed round-3 title + meta-description rewrites to 13 articles + 3 pages (16 entries, 32 metafields total). High-impact handles: `estate-cleanout-services`, `pros-and-cons-of-estate-sales`, `estate-auction-vs-estate-sale-pros-and-cons`, `why-hire-estate-sale-company`, `how-do-estate-sales-work`, `how-to-plan-estate-sale`, `find-the-best-jewelry-buyer-in-tampa-florida`, `5-tips-to-help-clients-prepare-for-estate-sales`, `ultimate-guide-to-home-auctions`, `how-to-increase-your-home-appraisal-value`, `estate-sale-vs-garage-sale-know-the-differences`, `estate-sales-near-me-...`, `expert-estate-sale-organizers-tampa-bay-...`, `yard-sale-vs-estate-sale-key-differences`, `faqs`, `about-us`.
  - Added homepage internal-links section anchoring "estate cleanout experts" and "deceased estate house clearing services" to `/pages/estate-cleanout-services`.
  - Appended FAQ block + FAQPage JSON-LD to `/blogs/news/estate-sale-vs-garage-sale-know-the-differences` answering "difference between yard sale and garage sale" verbatim (GSC: 92 impressions, 0% CTR, pos 15.2).
- **Why:**
  - Round-3 titles previously didn't render because the theme always appended " – Organizing Life Services - Estate Sale Company". With the patch, every approved title_tag now renders clean and within Google's ~60-char display window → expect CTR lift across all 16 URLs.
  - Homepage links pass authority to the commercial money page and target two zero-click queries already in striking distance.
  - FAQ + schema target a featured-snippet/PAA opportunity on a head query the post already ranks for at pos 15.
- **How:** `data/theme_apply_title_patch.py`, `data/push_meta_round3_direct.py`, `data/theme_apply_homepage_intlinks.py`, `data/article_apply_yard_garage_faq.py`. Drafts vetted in `data/audit_output/round3_meta_drafts.json`. Pre-patch theme snapshot at `data/audit_output/theme_layout_snapshot.liquid` and `data/audit_output/theme_layout_snapshot_pre_intlinks.liquid`.
- **Result:** Pending — re-run `deep_seo_audit.py` after 2026-06-04 to measure CTR and impression lift on the 16 pushed URLs and the FAQ query.

## 2026-05-25 — Deep SEO audit infrastructure live + first post-change audit

- **What:** Stood up the `deep_seo_audit.py` pipeline (dual-UA crawl, weighted position, Postgres persistence, Shopify override detector). Generated the first synthesized audit covering the April 20–22 push.
- **Why:** Need a repeatable measurement system to evaluate every future SEO change.
- **How:** Commits `74d28fe` (infra) + `a9c3c46` (first audit).
- **Result:** [2026-05-25-post-april-changes-audit.md](2026-05-25-post-april-changes-audit.md). Net positive: clicks +21%, CTR +0.46pp. Warnings: blog cannibalization, 37 titles still too long.

## 2026-04-22 — Round-2 meta push + new blog posts + internal links (A3)

- **What:**
  - Round-2 meta title/description rewrites on pages still too-long after round 1
  - New blog post: "What is an Estate Sale" (FAQ schema)
  - New blog post: "Yard Sale vs Estate Sale: Key Differences"
  - Internal link pass A3 (high-authority pages → target landing pages)
- **Why:** Continue CTR lift from round 1; expand topical coverage; pass link equity to commercial-intent pages.
- **How:** `data/push_meta_round2.py`, `data/b1_faq_what_is_estate_sale.py`, `data/b2_yard_vs_estate_sale_post.py`, `data/internal_links_a3.py`. Commits `76bafea`, `7baecf6`.
- **Result:** Measured in [2026-05-25-post-april-changes-audit.md](2026-05-25-post-april-changes-audit.md). Internal links + new posts ranked well; cannibalization on legacy how-to posts is the downside.

## 2026-04-20 — Initial schema rollout + round-1 meta rewrites + new geo landing pages

- **What:**
  - JSON-LD schema snippet installed on Shopify theme (LocalBusiness, Service, Breadcrumb, Offer, GeoCoordinates, OpeningHoursSpecification, etc.)
  - First pass of LLM-drafted titles/metas pushed via Shopify Admin API
  - Geo landing pages created (Citrus County, Tarpon Springs Woodfield, Sever's Landing Palm Harbor part 2)
  - Blog fix sweep (`apply_blog_fixes.py`)
- **Why:** Establish rich-result eligibility, lift CTR via better SERP snippets, capture local-intent traffic.
- **How:** `data/add_schema_markup.py`, `data/push_schema_snippet.py`, `data/seo-schema.liquid`, `data/meta_drafts.py`, `data/push_meta_to_shopify.py`, `data/create_seo_pages.py`, `data/apply_blog_fixes.py`. Commits `92ca652`, `76bafea`.
- **Result:** Measured in [2026-05-25-post-april-changes-audit.md](2026-05-25-post-april-changes-audit.md). Schema landed on 100% of crawled pages; new geo pages rank page 1; CTR +0.46pp.

---

## How to add an entry

When you ship an SEO change:

1. Add an entry **at the top** of the dated list (newest first).
2. Reference the commit SHA so anyone can `git show` the change.
3. Leave the **Result** line as `_(pending next audit)_` until the next audit measures it, then fill in.
4. Commit with `docs(seo): changelog entry — <short description>`.
