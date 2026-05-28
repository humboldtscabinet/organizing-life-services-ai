# SEO Changelog — organizinglifeservices.com

A running log of every SEO change deployed to the live site, the scripts that did it, and the hypothesis being tested. Read top-to-bottom for newest-first.

Each entry should answer:
- **What** changed (pages, fields, schema, links, content)
- **Why** (hypothesis: "we expect X to improve")
- **How** (script(s) run, commit SHA)
- **Result** (link to the audit that measured the outcome, once available)

---

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
