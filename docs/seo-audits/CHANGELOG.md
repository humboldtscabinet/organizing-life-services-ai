# SEO Changelog — organizinglifeservices.com

A running log of every SEO change deployed to the live site, the scripts that did it, and the hypothesis being tested. Read top-to-bottom for newest-first.

Each entry should answer:
- **What** changed (pages, fields, schema, links, content)
- **Why** (hypothesis: "we expect X to improve")
- **How** (script(s) run, commit SHA)
- **Result** (link to the audit that measured the outcome, once available)

---

## 2026-08-31 — Session 20: page CTR pass for "downsizing-moving-sales" (`downsizing specialist`) (live applied)

**Status: LIVE applied.** Applied **2026-08-31 ~8:19 PM ET** (after PRs #89/#90 merged) via the guarded [`data/session20_downsizing_specialist_page_ctr.py`](../../data/session20_downsizing_specialist_page_ctr.py) script with `--apply` under the mutation guard (after a read-only dry-run) — Shopify page id **99735568538**, handle `downsizing-moving-sales` ([live URL](https://organizinglifeservices.com/pages/downsizing-moving-sales)). The metafield title/description below (`Downsizing Specialist in Tampa Bay | Moving Sales | OLS` / the Tampa Bay + phone meta) are now the live `global.title_tag` / `global.description_tag`; the H1 (`Downsizing Help & Moving Sales | Organizing Life Services`) is unchanged. Operator verified the live HTML afterward (see Result below).

**What**
- New guarded, idempotent session script [`data/session20_downsizing_specialist_page_ctr.py`](../../data/session20_downsizing_specialist_page_ctr.py) that updates the Shopify SEO metafields (`global.title_tag` / `global.description_tag`, the same page SEO fields used by Session 10 / Session 11) for **one** EXISTING page — handle `downsizing-moving-sales` ([live URL](https://organizinglifeservices.com/pages/downsizing-moving-sales)):
  - Title (55 chars): `Downsizing Specialist in Tampa Bay | Moving Sales | OLS`
  - Description (113 chars): `Need a downsizing specialist in Tampa Bay? OLS handles sorting, moving sales, and cleanouts. Call (727) 542-6028.`
- Edits the SEO title/meta metafields only. H1 (`Downsizing Help & Moving Sales | Organizing Life Services`) is left unchanged, exactly like Session 19. Does **not** touch the page body, Shopify products, product SEO fields, fee collections, the homepage theme, GTM (`GTM-KQ76X4NR`), ads, GBP, `app/agents/`, the dashboard Apply path, or any other page.
- The script selects exactly one page by handle and refuses to run if zero or more than one match, so it can never write a different page.

**Why (hypothesis)**
- GSC 2026-08-01→08-28 (deep audit [`data/audit_output/deep_seo_audit_20260831_120737.json`](../../data/audit_output/deep_seo_audit_20260831_120737.json)): query `downsizing specialist` → this URL earns 62 impressions, 0 clicks, position 3.7 — a classic rank-with-no-CTR snippet mismatch (page totals: 179 impressions, 2 clicks, position 22.2). The live title (`Downsizing & Moving Sales in Greater Tampa Bay Area`, 50 chars) and generic live meta do not name the searcher's job. Naming `downsizing specialist` in the title and answering it in one sentence, with Tampa Bay service-area context plus the approved phone `(727) 542-6028`, should let the same top-4 ranking finally earn clicks — without keyword stuffing, `near me`, competitor names, invented prices, testimonials, street addresses, or GTM tags.
- **Not addressed here:** the Tampa hub `/pages/estate-sale-tampa-hillsborough-county` (rank pos ~27 — a ranking job, not a snippet job) is deliberately out of scope; no new Palm Harbor URL is created; organizer queries (just published) are untouched.

**How**
- Script: dry-run default; live writes require `--apply` + `OLS_ALLOW_DATA_MUTATION=1` / `OLS_DATA_MUTATION_CONFIRM=...`; snapshots the page's existing metafields (JSON) before any write; idempotent once the proposed `title_tag` / `description_tag` are present.
- Tests: [`tests/test_session20_downsizing_specialist_page_ctr.py`](../../tests/test_session20_downsizing_specialist_page_ctr.py) cover copy length + downsizing-specialist-intent/on-brand contract (no `$`, no `gtm-`), handle targeting (selects only the downsizing page, never the Tampa hub; raises when absent or duplicated), and metafield planning + idempotency (create / update / unchanged).

**Result / next watch**
- **Live applied 2026-08-31 ~8:19 PM ET** on the Mac mini (page id 99735568538, handle `downsizing-moving-sales`). Live HTML verified after apply: GTM container `GTM-KQ76X4NR` present; phone `(727) 542-6028` present; no `noindex`; no `streetAddress` in schema; the Tampa hub `/pages/estate-sale-tampa-hillsborough-county` is unchanged.
- **Next:** re-measure `downsizing specialist` → this URL CTR at **2026-09-14 (14d)** and **2026-09-28 (28d)**.

---

## 2026-08-31 — Task 207: new blog "Estate Sale Organizers in Tampa Bay: What to Know" (live applied)

**Status: LIVE applied.** Applied **2026-08-31 ~5:10 PM ET** via the dashboard `content.generate_and_publish` Apply verb with `human_confirmed=true` (and judge `PASS` — both gate flags required). This is the first live blog publish; the last live apply is no longer 2026-07-25.

**What**
- Published a new Shopify blog article (news blog), Shopify `article_id` **565700591770**, handle `estate-sale-organizers-tampa-bay-guide` ([live URL](https://organizinglifeservices.com/blogs/news/estate-sale-organizers-tampa-bay-guide)):
  - Title / H1: `Estate Sale Organizers in Tampa Bay: What to Know`
  - Meta description: `Hiring estate sale organizers in Tampa Bay? Learn what they do, how to choose one, and what to prepare for a smoother, more profitable sale.`
- Did **not** touch Shopify products, product SEO fields, fee collections, the homepage theme, GTM tags, GBP, Ads, or `app/agents/`.

**Why (hypothesis)**
- GSC 2026-08-01→08-28 (weekly audit [`deep_seo_audit_20260831_120737.json`](../../data/audit_output/deep_seo_audit_20260831_120737.json)): query `estate sale organizers` aggregates **276 impressions, 0 clicks, position 16.9** — the homepage `/` alone carries **272 impressions, 0 clicks, position 15.9**. A dedicated informational guide targeting `estate sale organizers` gives the query a purpose-built landing page instead of leaning on the homepage snippet. (A remembered baseline of 1,241 impressions / 0 clicks / pos 19.2 was **not** confirmed in the repo audit files and is not used here.)

**How**
- Dashboard Apply: `content.generate_and_publish` (gate `content_publish`), `human_confirmed=true`, judge `PASS`. No guarded session script — this was a human-confirmed dashboard publish, not a `data/session*.py` run.
- Live HTML verified after publish: GTM container `GTM-KQ76X4NR` present; phone `(727) 542-6028` / `tel:7275426028`; links `/pages/contact-us`; no `noindex`; no `streetAddress` in schema.

**Result / next watch**
- Live and verified (see live-HTML checks above). No live metrics yet — measurement pending the next GSC window.
- **Next:** re-measure GSC query `estate sale organizers` and the URL `estate-sale-organizers-tampa-bay-guide` at **14 days (2026-09-14)** and **28 days (2026-09-28)**.

---

## 2026-08-31 — Session 19: article CTR pass for "estate-sale-vs-garage-sale-know-the-differences" (live applied)

**Status: LIVE applied.** Applied **2026-08-31 ~1:40 PM ET** — Shopify `article_id` **560955195546**, handle `estate-sale-vs-garage-sale-know-the-differences`. The metafield title/description below (`Estate Sale vs Garage Sale in Tampa Bay | OLS` / the Tampa Bay + phone meta) are now the live `global.title_tag` / `global.description_tag`; the H1 is unchanged. Deliberately did **not** touch `/blogs/news/yard-sale-vs-estate-sale-key-differences`.

**What (proposed)**
- New guarded, idempotent session script [`data/session19_estate_sale_vs_garage_sale_article_ctr.py`](../../data/session19_estate_sale_vs_garage_sale_article_ctr.py) that updates the Shopify SEO metafields (`global.title_tag` / `global.description_tag`, same article fields as Session 10 round 3 / [`data/push_meta_round3_direct.py`](../../data/push_meta_round3_direct.py)) for **one** article — handle `estate-sale-vs-garage-sale-know-the-differences` ([live URL](https://organizinglifeservices.com/blogs/news/estate-sale-vs-garage-sale-know-the-differences)):
  - Title (45 chars): `Estate Sale vs Garage Sale in Tampa Bay | OLS`
  - Description (147 chars): `Estate sale vs garage sale? Estate sales are professionally run whole-home sales; garage sales are DIY. Serving Tampa Bay, FL. Call (727) 542-6028.`
- The script selects exactly one article by handle and refuses to run if zero or more than one match, so it can never write a different article.
- Does **not** touch Shopify products, product SEO fields, fee collections, the homepage theme, GTM tags, `app/agents/`, or any other article.

**Why (hypothesis)**
- GSC 2026-08-01→08-28 (weekly audit, PR #82): this URL (the garage-sale-vs-estate-sale comparison) earned ~1,531 impressions and 0 clicks — a classic rank-with-no-CTR mismatch. The live title (`Estate Sale vs Garage Sale: Key Differences Explained`, 53 chars) already names the query, but the live meta (`Learn the key differences between estate sales vs garage sales, including pricing, scope, and which option works best for your situation.`, 137 chars) is generic — no Tampa Bay, no OLS, no phone — so the snippet does not earn the click. Restating the difference in one sentence and adding Tampa Bay / Florida service-area context plus the approved phone `(727) 542-6028` should let the same ranking finally earn clicks — without keyword stuffing, `near me`, competitor names, invented prices, or fake testimonials. OLS is an estate-sale / personal-property company (not a pawn shop, not a weekend garage-sale operator); the copy stays a homeowner comparison and does not pretend OLS runs garage sales.

**Cannibalization (hypothesis — not addressed here)**
- A second post exists at [`/blogs/news/yard-sale-vs-estate-sale-key-differences`](https://organizinglifeservices.com/blogs/news/yard-sale-vs-estate-sale-key-differences). Session 19 updates **only** the garage-sale handle above and deliberately does not touch, write, or "merge" the yard-sale post.

**How**
- Script: dry-run default; live writes require `--apply` + `OLS_ALLOW_DATA_MUTATION=1` / `OLS_DATA_MUTATION_CONFIRM=...`; snapshots the article's existing metafields (JSON) before any write; idempotent once the proposed `title_tag` / `description_tag` are present.
- Tests: [`tests/test_session19_estate_sale_vs_garage_sale_article_ctr.py`](../../tests/test_session19_estate_sale_vs_garage_sale_article_ctr.py) cover copy length + comparison-intent/on-brand contract, handle targeting (selects only the garage-sale handle, never the yard-sale cannibal; raises when absent or duplicated), and metafield planning + idempotency (create / update / unchanged).

**Result / next watch**
- **Live applied 2026-08-31 ~1:40 PM ET** (article 560955195546). Re-measure this URL's `estate sale vs garage sale` CTR at 14/28d.

---

## 2026-08-31 — Session 18: article CTR pass for "how-to-find-the-best-antique-buyer" (live applied)

**Status: LIVE applied.** Applied **2026-08-31 ~1:25 PM ET** — Shopify `article_id` **560540614810**, handle `how-to-find-the-best-antique-buyer`. The metafield title/description below (`Where to Sell Antiques Locally in Tampa Bay | OLS` + the seller-local-intent meta) are now the live `global.title_tag` / `global.description_tag`.

**What (proposed)**
- New guarded, idempotent session script [`data/session18_antique_buyer_article_ctr.py`](../../data/session18_antique_buyer_article_ctr.py) that updates the Shopify SEO metafields (`global.title_tag` / `global.description_tag`, same article fields as Session 10 round 3 / [`data/push_meta_round3_direct.py`](../../data/push_meta_round3_direct.py)) for **one** article — handle `how-to-find-the-best-antique-buyer` ([live URL](https://organizinglifeservices.com/blogs/news/how-to-find-the-best-antique-buyer)):
  - Title (49 chars): `Where to Sell Antiques Locally in Tampa Bay | OLS`
  - Description (152 chars): `Where to sell antiques locally? Find a trusted antique buyer in Tampa Bay, FL, or let our estate sale team handle the sale for you. Call (727) 542-6028.`
- The script selects exactly one article by handle and refuses to run if zero or more than one match, so it can never write a different article.
- Does **not** touch Shopify products, product SEO fields, fee collections, the homepage theme, GTM tags, or `app/agents/`.

**Why (hypothesis)**
- GSC 2026-08-01→08-28: query `where to sell antiques locally` → this URL earns 190 impressions, 0 clicks, position 1.0 — a classic rank-#1, 0% CTR snippet mismatch. The live title (`How to Find the Best Antique Buyer | Organizing Life Services`, 61 chars) is buyer-framed and long enough to truncate, while the searcher's job is to *sell* antiques locally. Reframing the title/meta to seller-local intent should let the same #1 ranking finally earn clicks — without keyword stuffing, competitor names, invented prices, or fake testimonials. OLS is an estate-sale / personal-property company (not a pawn shop); Tampa Bay / Florida service-area context and the approved phone `(727) 542-6028` are allowed.

**How**
- Script: dry-run default; live writes require `--apply` + `OLS_ALLOW_DATA_MUTATION=1` / `OLS_DATA_MUTATION_CONFIRM=...`; snapshots the article's existing metafields (JSON) before any write; idempotent once the proposed `title_tag` / `description_tag` are present.
- Tests: [`tests/test_session18_antique_buyer_article_ctr.py`](../../tests/test_session18_antique_buyer_article_ctr.py) cover copy length + seller-intent/on-brand contract, handle targeting (selects only the target handle; raises when absent or duplicated), and metafield planning + idempotency (create / update / unchanged).

**Result / next watch**
- **Live applied 2026-08-31 ~1:25 PM ET** (article 560540614810). Re-measure `where to sell antiques locally` → this URL CTR at 14/28d.

---

## 2026-08-31 — Session 17: homepage CTR pass for organizers + estate-cleanout-near-me (NOT live applied)

**Status: NOT live applied.** Docs + guarded script only. No Shopify write has run; this entry documents the proposed change and its dry-run brakes. The last CHANGELOG live apply remains **2026-07-25**.

**What (proposed)**
- New guarded, idempotent session script [`data/session17_homepage_ctr_cleanout.py`](../../data/session17_homepage_ctr_cleanout.py) that upgrades the homepage theme meta block `HOMEPAGE-SEO-META-V1` → `HOMEPAGE-SEO-META-V2` with dual-intent SERP copy:
  - Title (50 chars): `Estate Sale Organizers & Cleanouts | Tampa Bay OLS`
  - Description (156 chars): `Tampa Bay estate sale organizers and estate cleanout services. OLS runs full sales, appraisals, and downsizing from Pinellas to Citrus. Call (727) 542-6028.`
- The organizer intlinks block `SEO-INTLINKS-ORGANIZERS-V1` already links estate cleanout services, so the script does **not** duplicate that copy; a single cleanout sentence is inserted only if that block is missing any cleanout mention.
- One H1 story is preserved (heading stays `Estate Sale Organizers Serving Tampa Bay`); the `OLS-GTM-INSTALL-V1` GTM snippet is guarded against regression.

**Why (hypothesis)**
- GSC 2026-08-01→08-28: `estate sale organizers` → `/` (272 impr, 0 clicks, pos 15.9) and `estate cleanout near me` → `/` (264 impr, 0 clicks, pos 1.2). Cleanout ranks #1 with 0% CTR — a snippet mismatch, since the live title is organizer-only. Folding cleanout into the title/meta should let the same page earn clicks for both intents without keyword stuffing, competitor names, or invented prices/testimonials.

**How**
- Script: dry-run default; live writes require `--apply` + `OLS_ALLOW_DATA_MUTATION=1` / `OLS_DATA_MUTATION_CONFIRM=...`; snapshots `layout/theme.liquid` before any write; idempotent once V2 copy is present.
- Tests: [`tests/test_session17_homepage_ctr_cleanout.py`](../../tests/test_session17_homepage_ctr_cleanout.py) cover copy-length/dual-intent contract, V1→V2 marker upgrade + idempotency, legacy-copy handling, no-duplicate cleanout, and the GTM regression guard.

**Result / next watch**
- _(pending)_ — no live apply yet. Operator: run a read-only dry-run on the Mac mini, review the diff, then `--apply` under the mutation guard. Re-measure `estate sale organizers` and `estate cleanout near me` CTR on `/` 14/28d after any real Apply.

---

## 2026-08-31 — Weekly SEO audit: full 28d read on the Jul 25 applies (measurement only)

**What**
- Ran the weekly deep audit + post-deploy measurement baseline over 2026-08-01→08-28 vs 2026-07-04→07-31.
- **No new live Shopify write this week.** This is a measurement pass; the last CHANGELOG live apply remains **2026-07-25**.
- Crawl health: 80/80 pages returned 200; Google URL Inspection 20/20 PASS.

**Why**
- Measure the 2026-07-25 GTM install + `phone_call_clicks` and organic-hub applies over a full 28-day window, now that they have been live long enough to show in search stats.

**How**
- Workflow: GitHub Actions `weekly-seo-audit`, PR #82, merge `ef55604`.
- Raw: [`data/audit_output/deep_seo_audit_20260831_120737.{md,json}`](../../data/audit_output/deep_seo_audit_20260831_120737.md), [`data/audit_output/post_deploy_measurement_baseline_20260831T121003Z.json`](../../data/audit_output/post_deploy_measurement_baseline_20260831T121003Z.json).
- Baseline summary: [`docs/seo-audits/2026-08-31-post-deploy-measurement-baseline.md`](2026-08-31-post-deploy-measurement-baseline.md).

**Result / next watch**
- **GSC:** clicks 117 → 97 (−17.1%); impressions 14,690 → 13,425; weighted avg position 15.8 → 16.9.
- **GA4:** all-traffic sessions +24.4%; organic sessions −61.5%; conversion tracking still fails trust checks.
- **Real lead-intent key events:** `form_submit` 19, `phone_call_clicks` 8. Junk still in the mix: `page_view` (2 key events) and `ads_conversion_Contact_Page_load_https_1` (1 key event / 91 events).
- **CTR holes (homepage still 0 clicks):** `estate sale organizers` → `/` (272 impr, 0 clicks, pos 15.9); `estate cleanout near me` → `/` (264 impr, 0 clicks, pos 1.2).
- **Gainer:** `estate sales near me` +6 clicks.
- **Next:** (1) unmark `page_view` as a key event in the GA4 UI; (2) `ads.disable_bogus_conversions` for `Contact_Page_load`; (3) then homepage content for the `estate sale organizers` and `estate cleanout near me` intents. Re-measure 14/28d after any real Apply.

---

## 2026-07-25 — Session 16: install GTM on theme (live applied)

**What**
- Injected public container `GTM-KQ76X4NR` into Shopify `theme.liquid` (`OLS-GTM-INSTALL-V1`).
- Paused GTM `GA4-Config-G-4HSTXZKG9E` so page_view stays on Shopify Google channel only (avoids double-count).
- Set `waitForTags=true` on OLS tel click trigger; created GTM container **version 9**.

**Why**
- Storefront had GA4 via Shopify channel (`G-4HSTXZKG9E`) but no GTM snippet, so published phone-click tags never fired.

**How**
- Script: [`data/session16_install_gtm.py`](../../data/session16_install_gtm.py)
- Mac mini apply + GTM version create; publish version 9 (UI or `--publish`)
- Runbook: [`docs/runbooks/gtm-write-and-publish.md`](../runbooks/gtm-write-and-publish.md)

**Result / next watch**
- Live HTML includes `GTM-KQ76X4NR`. GA4 Realtime showed `phone_call_clicks` as a key event after a test call click.
- Standard Reports → Events may lag Realtime; keep Shopify channel + paused GTM config as the single page_view path.

---

## 2026-07-25 — Session 14: GTM `phone_call_clicks` (live applied)

**What**
- Gated GTM write path: tag/trigger CRUD, version create/publish, `ensure_phone_call_clicks_tracking()`.
- Created OLS tel-click trigger + GA4 event tag for measurement ID `G-4HSTXZKG9E` (prefer `G-` over Ads `AW-`).
- Operator paused legacy duplicate **Event - Phone Call**; published container version 8 in UI before Session 16 theme install.

**Why**
- Need a durable, gated operator path for phone lead events instead of one-off UI edits; Ads IDs must not bind as GA4 measurement IDs.

**How**
- Code: `app/services/gtm_service.py`, gated routes in `app/routes/seo.py`, tests `tests/test_gtm_write_control.py`
- Script: [`data/session14_gtm_phone_clicks.py`](../../data/session14_gtm_phone_clicks.py)
- Env on mini: `GTM_ACCOUNT_ID=6201388805`, `GTM_CONTAINER_ID=168770630`, `GA4_MEASUREMENT_ID=G-4HSTXZKG9E`

**Result / next watch**
- Workspace objects + versions created; events only after Session 16 installed GTM on the theme.
- Still: unmark noisy GA4 key events in UI (property 396184354) per [`2026-07-25-ga4-key-event-cleanup-checklist.md`](2026-07-25-ga4-key-event-cleanup-checklist.md).

---

## 2026-07-25 — Session 15 organic growth hubs (live applied)

**What**
- Appraisal deepen (`SD-APPRAISAL-V2` on `personal-property-appraisal`).
- Tampa/Hillsborough deepen (`SD-TAMPA-V2`) with neighborhood proof + soft organizer cannibalization note.
- Pinellas hub intlink on homepage theme (`SEO-INTLINKS-PINELLAS-V1`); Clearwater/Tarpon/Palm Harbor already had hub links.
- Operator checklist: [`2026-07-25-organic-growth-next-steps.md`](2026-07-25-organic-growth-next-steps.md).

**Why**
- Audit: appraisal near-me striking distance; Tampa ~600 impr / 0 clicks; Pinellas hub needs stronger internal links; organizers demand should not center on the Tampa hub.

**How**
- Script: [`data/session15_organic_growth_hubs.py`](../../data/session15_organic_growth_hubs.py)
- Mac mini apply on `cursor/gtm-gated-write-control`: report `data/audit_output/session15_organic_growth_hubs_20260725T174221Z.json`
- Live verified via curl: `SD-APPRAISAL-V2`, `SD-TAMPA-V2`, homepage `estate-sale-pinellas-county`
- IndexNow skipped (no key in container)

**Result / next watch**
- Track A (GTM install + `phone_call_clicks`) completed in Sessions 14–16; measurement baseline when site 429 cools.
- GSC: Tampa clicks + appraisal near-me ~14–28 days; organizers CTR Aug 8 / Aug 22.

---

## 2026-07-25 — P0 follow-through: Tarpon intlinks + Palm Harbor SD + watch docs

**What**
- Retargeted service-intent Woodfield gallery hrefs → permanent `/pages/estate-sale-tarpon-springs-florida` in homepage theme intlinks + 6 A4 blog articles.
- Confirmed Palm Harbor title/meta; appended striking-distance block `SD-ESPH-V1` (“Estate Sales Palm Harbor”).
- Added GA4 operator checklist and homepage organizers CTR watch checklist.
- Source scripts updated so re-runs do not restore Woodfield service links: [`data/article_apply_intlinks_a4.py`](../../data/article_apply_intlinks_a4.py), [`data/session5_schema_intlinks_noindex.py`](../../data/session5_schema_intlinks_noindex.py).

**Why**
- Audit showed Tarpon Springs demand still routing through the noindexed gallery URL via internal links; Palm Harbor sits at pos ~9.3 with weak CTR; organizer homepage copy needs a timed CTR watch; GA4 key events still inflate lead metrics.

**How**
- Guarded script: [`data/session13_woodfield_tarpon_palm_harbor.py`](../../data/session13_woodfield_tarpon_palm_harbor.py)
- Report: [`data/audit_output/session13_woodfield_tarpon_palm_harbor_20260725T153205Z.json`](../../data/audit_output/session13_woodfield_tarpon_palm_harbor_20260725T153205Z.json)
- Checklists: [`2026-07-25-ga4-key-event-cleanup-checklist.md`](2026-07-25-ga4-key-event-cleanup-checklist.md), [`2026-07-25-homepage-organizers-ctr-watch.md`](2026-07-25-homepage-organizers-ctr-watch.md)

**Result / next watch**
- Live verified: homepage + sample article link to permanent Tarpon page; Palm Harbor title + `SD-ESPH-V1` H2 present; organizers homepage title/intlinks still live.
- **Operator:** complete GA4 key-event unmarks in UI (property 396184354), then re-run measurement baseline ~2026-07-27 and ~2026-08-22.
- Organizers CTR GSC check-ins: **2026-08-08** and **2026-08-22**.

---

## 2026-07-25 — Comprehensive SEO audit (post Session 11/12)

**What**
- Ran [`data/deep_seo_audit.py`](../../data/deep_seo_audit.py) and [`data/post_deploy_measurement_baseline.py`](../../data/post_deploy_measurement_baseline.py).
- Synthesized recommendations in [`docs/seo-audits/2026-07-25-comprehensive-seo-audit.md`](2026-07-25-comprehensive-seo-audit.md).

**Why**
- Need a fresh 28-day baseline after service-guardrails, homepage organizers CTR, first-wave service-area pages, and Woodfield noindex.

**How**
- Raw: [`data/audit_output/deep_seo_audit_20260725_150718.{md,json}`](../../data/audit_output/deep_seo_audit_20260725_150718.md), [`docs/seo-audits/2026-07-25-post-deploy-measurement-baseline.md`](2026-07-25-post-deploy-measurement-baseline.md).

**Result / next watch**
- Impressions up, clicks/CTR down; organic sessions up strongly. Top levers: GA4 key-event cleanup, Palm Harbor striking distance, Tampa hub rescue, organizer cannibalization cleanup, Tarpon intlink retarget.
- GSC window ends 2026-07-22 — Jul 24 live applies not yet in search stats.

---

## 2026-07-24 — Service-only Shopify guardrails + homepage organizers CTR prep

**What**
- Documented hard policy: Shopify products/utility collections are internal-only and never SEO/ads/content targets.
- API product SEO writes fail closed by policy.
- Fee/internal product URLs get noindex treatment via guarded script.
- Dashboard GSC task generation skips `/products/*` and utility collections.
- Homepage CTR script prepared to refine `HOMEPAGE-SEO-META-V1` + service-intent reinforcement for `estate sale organizers`.

**Why**
- OLS is a service business; fee “products” previously caused bad SEO/ads assumptions.
- Homepage still has high impressions / near-zero clicks for organizer queries (Jul 20 baseline).

**How**
- Code/docs in the service-guardrails + homepage CTR PR.
- Guarded scripts: [`data/session12_noindex_fee_products.py`](../../data/session12_noindex_fee_products.py), [`data/session12_homepage_organizers_ctr.py`](../../data/session12_homepage_organizers_ctr.py).
- Operator runbook: [`docs/runbooks/service-guardrails-homepage-ctr.md`](../runbooks/service-guardrails-homepage-ctr.md).
- Live Shopify apply is operator-gated on the Mac mini (dry-run → mutation confirm).

**Result / next watch**
- **Live applied (Mac mini) 2026-07-24 ~23:02Z:** upgraded fee-product theme block `SEO-ROBOTS-PRODUCTS-V1` → `SEO-ROBOTS-PRODUCTS-V2` (`request.path`). Report: `data/audit_output/session12_noindex_fee_products_20260724T230219Z.json`. Snapshot: `data/audit_output/theme_layout_snapshot_pre_session12_products_20260724T230219Z.liquid`.
- Verified live `noindex,follow` on `/products/product-cc-2-7-fee`, `/products/product-cc-2-7-fee-2`, `/products/processing-fee` (fee URL needed a theme comment cache-bust after Shopify `page_cache` lag).
- Homepage CTR/intlinks were already applied earlier the same day (see `session12_homepage_organizers_ctr_20260724T221500Z.json`).
- Watch GSC CTR for `estate sale organizers` / `estate sale organizer` over 14–28 days; confirm fee URLs drop from index coverage.

---

## 2026-06-23 — First-wave service-area Shopify dry-run scaffold

**What**
- Added [`data/session11_service_area_first_wave.py`](../../data/session11_service_area_first_wave.py), a guarded Shopify implementation script for the first wave of Pinellas, Pasco, and Hillsborough service-area pages.
- Added unit coverage in [`tests/test_session11_service_area_first_wave.py`](../../tests/test_session11_service_area_first_wave.py) for target alignment, metadata lengths, schema parsing, idempotency, append-only behavior, and legacy-page handling.
- Ran a read-only Shopify dry-run and saved the report at [`data/audit_output/session11_service_area_first_wave_20260623T230329Z.json`](../../data/audit_output/session11_service_area_first_wave_20260623T230329Z.json).

**Why**
- The site needs more durable local-service landing pages for the real core counties: Pinellas, Pasco, and Hillsborough.
- The implementation needs production brakes before any live Shopify writes: dry-run by default, snapshots before writes, idempotent markers, and explicit mutation confirmation.

**How**
- Dry-run authenticated to Shopify and read current page/metafield state only.
- Planned 2 new permanent pages: `estate-sale-pinellas-county` and `estate-sale-tarpon-springs-florida`.
- Planned append-only refreshes for 5 existing pages: Pasco County, Tampa/Hillsborough County, Palm Harbor, Clearwater, and New Port Richey.
- Legacy event page `tarpon-springs-estate-sale-in-woodfield` is report-only in this script; it is not redirected or noindexed automatically.

**Result / next watch**
- **Live applied (confirmed 2026-07-24):** all 7 first-wave pages are live with `SERVICE-AREA-FIRST-WAVE-V1` markers, including new hubs/pages `estate-sale-pinellas-county` and `estate-sale-tarpon-springs-florida`.
- Idempotent re-dry-run 2026-07-24: `would_or_did_page_writes=0`, `would_or_did_meta_writes=0` (report `data/audit_output/session11_service_area_first_wave_20260724T233506Z.json`).
- **IndexNow submitted 2026-07-24 ~23:37Z** for all 7 first-wave URLs: api.indexnow.org=200, bing.com/indexnow=200, yandex.com/indexnow=202 (report `data/audit_output/session11_indexnow_20260724T233704Z.json`).
- **Legacy gallery noindexed 2026-07-24 ~23:42Z:** `tarpon-springs-estate-sale-in-woodfield` (past sale photo gallery, not a service page) now has `seo.robots=noindex,follow` and live HTML verified after a page-body cache-bust (report `data/audit_output/woodfield_noindex_20260724T234157Z.json`). Permanent service URL remains `/pages/estate-sale-tarpon-springs-florida`.
- Optional later: retarget internal links that still use Woodfield as the “Tarpon Springs estate sales” anchor (e.g. homepage/article intlinks) to the permanent service page.
- Watch GSC indexing for the two new URLs and engagement on refreshed county/city hubs over 14–28 days; confirm Woodfield drops from index coverage.

---

## 2026-06-23 — Service-area architecture for Pinellas, Pasco, and Hillsborough

**What**
- Added [`data/service_area_plan.py`](../../data/service_area_plan.py), a machine-readable service-area plan for OLS local SEO.
- Added [`docs/seo-audits/2026-06-23-service-area-architecture.md`](2026-06-23-service-area-architecture.md), covering current live inventory, primary county hubs, city page waves, legacy event-page migration targets, page template, and measurement plan.

**Why**
- OLS primarily serves Pinellas, Pasco, and Hillsborough, so the geo strategy needs more than the initial handful of priority pages.
- The current live site has a mix of strong permanent pages and thin legacy event pages. Using old event pages as canonical city SEO pages would be messy and could create doorway-page risk.

**How**
- Primary hubs: Pinellas County, Pasco County, Hillsborough/Tampa.
- First-wave city pages: Palm Harbor, Clearwater, Tarpon Springs, Tampa/Hillsborough, and New Port Richey.
- Later waves: Dunedin, Largo, St. Petersburg, Safety Harbor, Seminole, Wesley Chapel, Brandon, Riverview, and remaining Pasco/Hillsborough cities.

**Result / next watch**
- No live Shopify writes in this pass.
- Next implementation should be a guarded first-wave Shopify script with `--dry-run`, snapshots, and explicit human confirmation.
- GA4 key-event cleanup should still happen before relying on lead/conversion impact.

---

## 2026-06-23 — Post-deploy measurement baseline: conversion trust, live verification, content targets

**What**
- Added [`data/post_deploy_measurement_baseline.py`](../../data/post_deploy_measurement_baseline.py), a read-only measurement script that audits GA4 key events, verifies the changed live URLs, builds a business-weighted GSC content target list, checks GBP on-site readiness, and summarizes GTM audit availability.
- Added the generated report at [`docs/seo-audits/2026-06-23-post-deploy-measurement-baseline.md`](2026-06-23-post-deploy-measurement-baseline.md) and raw JSON at [`data/audit_output/post_deploy_measurement_baseline_20260623T222711Z.json`](../../data/audit_output/post_deploy_measurement_baseline_20260623T222711Z.json).
- Updated the weekly SEO audit workflow to run the measurement baseline after the deep audit and include `docs/seo-audits/` in the automated PR.

**Why**
- The weekly audit showed organic conversions were too high relative to organic sessions, so the next risk was measurement quality rather than more page edits.
- The site needs a repeatable way to connect SEO work to real lead intent: form submits, phone clicks, email clicks, contact CTA clicks, and high-intent landing pages.

**How**
- GA4 Data API: key events by event name, channel, and organic landing page.
- Live storefront crawl: homepage, appraisal, contact, trust pages, senior services, and noindexed utility collections.
- GSC query/page data: business-weighted content targets using lead-relevance scoring.
- GBP readiness: LocalBusiness schema, service-area posture, no public street address, contact-page mailing-address labeling.

**Result / next watch**
- Live SEO verification passed for the June changes.
- GBP on-site readiness passed; GBP API access remains blocked/unavailable in this run.
- GTM audit was available and reported 5 tags, 1 trigger, 0 flagged findings.
- GA4 conversion tracking failed trust checks: `page_view` and `ads_conversion_Contact_Page_load_https_1` are counted as key events. The GA4 Admin API is disabled in the service-account GCP project, so cleanup should be done in the GA4 UI using [`docs/runbooks/ga4-key-event-cleanup.md`](../runbooks/ga4-key-event-cleanup.md).
- Top content priorities remain service-intent work: homepage service-intent copy/internal links, Tampa/Hillsborough service-area page, estate cleanout page, Tarpon Springs permanent service-area handling, and appraisal page expansion.

---

## 2026-06-23 — Targeted weekly-audit fixes: homepage CTR, appraisal page, H1 cleanup

**What**
- Added [`data/session10_weekly_seo_fixes.py`](../../data/session10_weekly_seo_fixes.py), a guarded/idempotent live Shopify patch script with `--dry-run`.
- Updated the homepage theme title/meta description to target the highest-impression service-intent queries found in the weekly audit:
  - Title: `Estate Sale Organizers Tampa Bay | Appraisals & Downsizing`
  - Description: `Tampa Bay estate sale organizers for estate sales, appraisals, downsizing, and cleanouts across Pinellas, Pasco, Hillsborough, Hernando, and Citrus.`
- Updated `/pages/personal-property-appraisal` SEO metafields:
  - Title: `Personal Property Appraisers Tampa Bay | Estate Appraisals`
  - Description: `Need Tampa personal property appraisers? OLS provides estate sale, probate, insurance, and downsizing appraisals across Tampa Bay. Call (727) 542-6028.`
- Demoted body-level H1 tags to H2 on `/pages/contact-us`, `/pages/about-us`, `/pages/testimonials`, and `/pages/senior-services`.
- Demoted the contact template's form-section H1 to H2 so `/pages/contact-us` now has a single rendered H1.
- Added theme-level `noindex,follow` for thin Shopify utility collections:
  - `/collections/all`
  - `/collections/fees-products`
- Restored IndexNow submission without reintroducing the local key file: the script now recovers the existing key from the Shopify IndexNow page, verifies the public root key URL, and redacts the key from reports.

**Why**
- The 2026-06-23 weekly audit showed the homepage earning impressions for high-intent phrases (`estate sale organizers`, `estate sale companies near me`, `estate sale and appraisal services`) but receiving weak CTR. The old homepage title was 90 characters and generic.
- The appraisal page had strong business-intent impressions (`tampa personal property appraisers`) but the title was only `Personal Property Appraisal`.
- Contact/trust pages were showing multiple rendered H1s, mostly from a mix of theme page-title output and body/section content.
- Shopify utility collections were thin, had no meta descriptions, and were not meaningful search landing pages.

**How**
- Live script reports:
  - [`data/audit_output/session10_weekly_seo_fixes_20260623T214401Z.json`](../../data/audit_output/session10_weekly_seo_fixes_20260623T214401Z.json)
  - [`data/audit_output/session10_weekly_seo_fixes_20260623T214801Z.json`](../../data/audit_output/session10_weekly_seo_fixes_20260623T214801Z.json)
  - [`data/audit_output/session10_weekly_seo_fixes_20260623T215925Z.json`](../../data/audit_output/session10_weekly_seo_fixes_20260623T215925Z.json)
- Theme snapshots:
  - [`data/audit_output/theme_layout_snapshot_pre_session10_20260623T214400Z.liquid`](../../data/audit_output/theme_layout_snapshot_pre_session10_20260623T214400Z.liquid)
  - [`data/audit_output/theme_page_contact_snapshot_pre_session10_20260623T214800Z.liquid`](../../data/audit_output/theme_page_contact_snapshot_pre_session10_20260623T214800Z.liquid)
- Live verification after patch:
  - Homepage title length: 58; meta description length: 148.
  - Personal Property Appraisal title length: 58; meta description length: 151.
  - Contact, About, Testimonials, Senior Services, and Personal Property Appraisal each render one H1.
  - `/collections/all` and `/collections/fees-products` render `noindex,follow`.
  - IndexNow key recovered from Shopify page; public root key URL verified; 8 URLs submitted with api.indexnow.org=200, bing.com/indexnow=200, yandex.com/indexnow=202.

**Result / next watch**
- Re-run the weekly audit after 7-14 days and compare CTR/clicks for:
  - homepage queries: `estate sale organizers`, `estate sale companies near me`, `estate sale and appraisal services`
  - appraisal queries: `tampa personal property appraisers`, `estate sale and appraisal services`
- IndexNow was submitted successfully on 2026-06-23. Keep `data/audit_output/indexnow_key.txt` absent; the key source of truth is the Shopify IndexNow page and root redirect.

---

## 2026-06-23 — Weekly SEO audit automation baseline

**What**
- Ran the first successful GitHub Actions weekly SEO audit end to end.
- Added raw output under [`data/audit_output/deep_seo_audit_20260623_213027.md`](../../data/audit_output/deep_seo_audit_20260623_213027.md) and [`data/audit_output/deep_seo_audit_20260623_213027.json`](../../data/audit_output/deep_seo_audit_20260623_213027.json).
- Added the curated human-readable summary at [`docs/seo-audits/2026-06-23-weekly-seo-audit.md`](2026-06-23-weekly-seo-audit.md).

**Headline results**
- GSC clicks: 135 -> 131 (-3.0%); impressions: 13,747 -> 13,078 (-4.9%); CTR: 0.98% -> 1.00%.
- Weighted average position improved from 18.0 -> 17.4.
- GA4 all-traffic sessions dropped 38.3%, but organic sessions held flat at 164 -> 164 and organic users improved slightly from 132 -> 133.
- Google URL Inspection returned PASS / Submitted and indexed for all 20 top-impression pages inspected.

**Recommendation**
- Do not run a broad rewrite. Prioritize targeted CTR and on-page cleanup:
  1. Personal Property Appraisal title/meta.
  2. H1 cleanup on contact/about/testimonials/senior-services.
  3. Homepage metadata around `estate sale organizers`, `estate sale companies near me`, and appraisal/downsizing intent.
  4. Decide whether Shopify collection pages should be optimized or intentionally noindexed.
  5. Confirm GA4 conversion definitions before treating conversion deltas as business KPIs.

**Result**
- Automation is now producing reviewable audit PRs. Next site changes should be human-reviewed and limited to high-intent pages.

---

## 2026-06-15 — Strip public street address from LocalBusiness schema (Option A)

**What**
- Built [`data/session9_strip_street_address.py`](../../data/session9_strip_street_address.py): replaces the live `SCHEMA-LB-V2` homepage JSON-LD block (injected by [session5](../../data/session5_schema_intlinks_noindex.py)) with `SCHEMA-LB-V3` — identical except the `address` object is reduced from a full street address (`E LAKE RD S`, Palm Harbor, FL 34685) to **region only** (`addressRegion: FL`, `addressCountry: US`). The rich `areaServed` (9 cities + 5 counties) is unchanged.
- Updated [`data/fix_contact_page.py`](../../data/fix_contact_page.py): writes a real NAP block to `/pages/contact-us` (phone, email, **labeled mailing address** = Tampa PMB, hours, regional service-area map) and creates a `/pages/contact → /pages/contact-us` redirect (the bare URL was 404ing).

**Why**
- Google denied GBP API access on 2026-04-21 ("did not pass our internal quality checks"). Root-cause audit found the live schema pinned a public street address even though OLS is a **service-area business** with no public storefront (every sale runs on-site). Google's structured-data guidance says service-area businesses should omit the street address and rely on `areaServed` — which we already publish richly.
- The Tampa PMB (`5005 W Laurel St, Suite 100 PMB1048, Tampa, FL 33607`) is retained **only** as a labeled mailing address on the contact page, never as a schema `streetAddress`.

**How**
- Scripts: `data/session9_strip_street_address.py` (idempotent: skips if `SCHEMA-LB-V3` present; snapshots theme to `data/audit_output/theme_layout_snapshot_pre_session9.liquid`; `--dry-run` supported), `data/fix_contact_page.py`.
- **Re-run guard:** the V3 block deliberately keeps the literal `SCHEMA-LB-V2` token in an HTML comment so session5's `if 'SCHEMA-LB-V2' in theme` idempotency check still no-ops and cannot re-append the old street-address block.
- Logic validated offline against the real session5 block — **13/13 assertions pass** (no `streetAddress`, region kept, `areaServed` kept, single ld+json block, idempotent re-run).
- **Deploy status:** code ready & validated; **deployment pending** the gitignored `.env` (Shopify creds), which is absent from this checkout.

**Result**
- Pending deploy + follow-up audit. Recheck schema with the Rich Results test after deploy; reapply for GBP API access ~30 days after the listing + site are confirmed consistent.

---

## 2026-06-04 — Post-change impact audit (Phases 4–8)

**What**
- Built [`data/post_change_audit.py`](../../data/post_change_audit.py): 6-section measurement script comparing 7-day post-change window (May 28 → Jun 3) vs 7-day pre-change window (May 21 → May 27) across the 22 priority URLs touched in Phases 4–8.
- Ran [`data/deep_seo_audit.py`](../../data/deep_seo_audit.py) for a fresh site-wide 28-day baseline.
- Compiled the comprehensive report at [`docs/seo-audits/2026-06-04_post-change_impact_audit.md`](2026-06-04_post-change_impact_audit.md).

**Headline results (22 priority URLs, 7d POST vs 7d PRE)**
- **Clicks: 19 → 31 (+63.2%)**
- **CTR: 0.70% → 1.45% (+0.75pp, more than doubled)**
- **Organic sessions (GA4): 34 → 45 (+32.4%)**
- **Organic conversions (GA4): 91 → 114 (+25.3%)**
- **12 of 18 priority URLs indexed** (PASS verdict); **11 of 18 with FAQ + Breadcrumb rich results** (was 0 pre-change)
- **6 net new geo pages progressed** from "URL is unknown to Google" → either indexed (1: New Port Richey) or "Discovered – currently not indexed" (5: Clearwater, Dunedin, St. Petersburg, Largo, Wesley Chapel)
- **18 of 18 dead pages serve `noindex,follow`** (verified after rate-limit retries)
- **14 of 15 schema markers verified live** (1 false miss = Shopify minification stripped an HTML comment, but the underlying feature — 24 geo-anchor links on homepage — is present)

**Outputs**
- Raw data: [`data/audit_output/post_change_audit_20260604.json`](../../data/audit_output/post_change_audit_20260604.json)
- Fresh site-wide baseline: [`data/audit_output/deep_seo_audit_20260604_195553.{md,json}`](../../data/audit_output/deep_seo_audit_20260604_195553.md)
- Full report: [`docs/seo-audits/2026-06-04_post-change_impact_audit.md`](2026-06-04_post-change_impact_audit.md)

**Recommendation**
- No new SEO push required this week — every Phase 4–8 deliverable is live and producing measurable lift.
- Recheck 2026-06-18 to confirm the 5 pending geo pages have moved from Discovered → Indexed and the 8 noindex pages have dropped from Google's index.
- Phase 9 candidates: Personal Property Appraisal page rebuild, FAQs page expansion, homepage above-the-fold service-area block.

---

## 2026-05-28 — FAQ + Article schema + IndexNow integration

**What**
1. **FAQ + BreadcrumbList JSON-LD on all 11 geo pages** (`FAQ-SCHEMA-V1`). Each block contains a visible 5-Q FAQ `<section>` (cost, duration, leftover/cleanout, service area, scheduling speed) tailored with city + county names, plus matching `FAQPage` and `BreadcrumbList` JSON-LD scripts.
2. **Article + BreadcrumbList JSON-LD on top-6 blog posts** (`ARTICLE-SCHEMA-V1`). Each block adds a visible byline + `Article` JSON-LD (headline, description, datePublished, dateModified=2026-05-28, author=Organization, publisher with logo, image, mainEntityOfPage) + `BreadcrumbList`. Articles: estate-sale-vs-garage-sale, pros-and-cons-of-estate-sales, how-to-increase-home-appraisal-value, estate-auction-vs-estate-sale, barbie-collector-buyers, how-to-plan-estate-sale.
3. **IndexNow integration** — generated UUID-hex key (saved to [data/audit_output/indexnow_key.txt](../../data/audit_output/indexnow_key.txt), gitignored), uploaded `templates/page.indexnow.liquid` (outputs `{{ page.content | strip_html | strip }}` with `{%- layout none -%}`), created Shopify page at handle = key with body = key text + `template_suffix=indexnow`, and created Shopify URL redirect `/{key}.txt -> /pages/{key}` so the key file is served at the **root host** (IndexNow protocol requirement). Submitted all 22 priority URLs (homepage + 11 geo + 6 articles + 4 hub pages) to api.indexnow.org, bing.com/indexnow, and yandex.com/indexnow.

**Why**
- **FAQPage schema** — unlocks rich-result FAQ accordions in SERPs (massive CTR boost for "estate sale {city}" queries). The visible HTML FAQ section also adds 500+ words of city-specific copy per page, addressing real buyer questions (cost, duration, cleanout).
- **BreadcrumbList schema** — gets the blue breadcrumb under the title in SERPs (better visual prominence + click target).
- **Article schema** — required for Top Stories eligibility, sitelinks search box, and E-E-A-T signals. Author/publisher/dateModified are foundational ranking signals for Google's Helpful Content systems.
- **IndexNow** — every future change can now be pushed to Bing and Yandex in seconds (instead of waiting days for organic crawl). Bing represents ~10% of US search; ChatGPT, Copilot, DuckDuckGo, Ecosia all source from Bing's index. Yandex covers Russia + several CIS markets.

**How**
- Script: [data/session8_faq_article_indexnow.py](../../data/session8_faq_article_indexnow.py) — idempotent across all three sections (markers `FAQ-SCHEMA-V1`, `ARTICLE-SCHEMA-V1`; reuses existing IndexNow key + redirect on re-run).
- 11 geo pages patched (~5,300c each), 6 articles patched (~1,900c each), 22 URLs submitted.
- IndexNow submission results: api.indexnow.org=200 OK, bing.com/indexnow=200 OK, yandex.com/indexnow=202 `{"success":true}`.

**Workaround logged — Shopify root key file**
Shopify does not allow arbitrary root-level files. We used a 301 URL redirect from `/{key}.txt` to `/pages/{key}` (which serves clean key text via the new `page.indexnow.liquid` theme template that uses `{%- layout none -%}`). IndexNow's verifier follows the 301 and accepts the response — confirmed by HTTP 202 from api.indexnow.org on test submission.

**Result / next watch**
- 1–7 days: check GSC rich-result reports for new `FAQ` and `Breadcrumbs` eligibility on the 11 geo pages, and `Article` eligibility on the 6 blog posts.
- 24h: check Bing Webmaster Tools (if account exists) for new "URL submitted via IndexNow" entries.
- Future: hook `IndexNow submission` into every Shopify update script (single line addition) so all future content changes propagate instantly.

---

## 2026-05-28 — Geo crosslink boost + 2nd sitemap recrawl for unindexed pages

**What**
1. **Hub pages** (high-authority indexed pages) — appended idempotent `SERVICE-AREAS-V1` block to bottom of `estate-cleanout-services` and `faqs` page bodies. Each block contains a 2-column `<ul>` linking to all 11 geo pages with exact-match anchors ("Estate sales in {City}").
2. **Geo pages** — appended `GEO-CROSSLINKS-V1` block to body of all 11 geo pages. Each page links to the other 10 — creating a fully-connected topical cluster. Block size ~1.4KB per page; bumps Shopify `updated_at` so sitemap lastmod refreshes.
3. **GSC** — resubmitted `sitemap.xml` and re-inspected the 6 previously-unknown URLs.

**Why**
- The 6 new geo pages from Phase 2 came back as `URL is unknown to Google` despite being in the sitemap. Internal links from already-indexed pages are the single fastest way to signal crawl-priority. We added inbound links from 12 indexed pages (estate-cleanout-services + faqs + 10 sibling geo pages) into each previously-unknown page.
- Cross-linking all 11 geo pages also strengthens the topical cluster signal (Google understands them as a coordinated set of related local-service pages).

**How**
- Script: [data/session7_geo_crosslinks_recrawl.py](../../data/session7_geo_crosslinks_recrawl.py) — idempotent (skips pages whose body already contains the marker). 13 pages patched total (2 hub + 11 geo).

**Result**
- Post-inspection status of the 6 previously-unknown URLs:
  - `Discovered - currently not indexed`: clearwater, dunedin, st-petersburg, largo, wesley-chapel (5/6 — **upgraded from unknown**)
  - `URL is unknown to Google`: new-port-richey (1/6 — likely a sample-timing artifact; re-inspect in 48h)
- Re-run [data/session6_recrawl_nap_geo_metas.py](../../data/session6_recrawl_nap_geo_metas.py) `section_a` in 7–14 days to confirm `PASS / Submitted and indexed`.

---

## 2026-05-28 — Sitemap recrawl + robots/NAP audit + round-5 geo metafield standardization

**What**
1. **GSC**: resubmitted `sitemap.xml` and inspected 7 URLs (homepage + 6 new geo pages from Phase 2). Inspection output saved to [data/audit_output/session6_url_inspection.json](../../data/audit_output/session6_url_inspection.json).
2. **robots.txt audit**: parsed 44 `Disallow:` rules under `User-agent: *`. Confirmed **none** of the 18 noindexed pages or 11 geo pages are accidentally blocked from crawl — link equity flows through `noindex,follow` cleanly.
3. **NAP verification**: printed live homepage `LocalBusiness` JSON-LD (name/phone/address/email/url) for manual cross-check against GBP listing.
4. **Round-5 geo metafields**: standardized `global.title_tag` + `global.description_tag` across all 11 geo pages — plural "Estate Sales", city + region + FL, phone CTA `(727) 542-6028`, 50-60c titles, 145-160c descriptions. **9 field updates** applied (script skips fields already matching target).

**Why**
- **Sitemap resubmit + URL inspection** — tells Google the sitemap freshness has changed and queues the 6 new geo pages for crawl review (they were `URL is unknown to Google` at inspection time despite being in the sitemap — typical for brand-new low-authority pages).
- **robots.txt audit** — confirms our `noindex` pages still pass link equity (a `Disallow` would have made `noindex,follow` useless).
- **NAP audit** — Knowledge Panel eligibility requires perfect name/address/phone consistency between site JSON-LD and Google Business Profile. Manual user verification step gated on GBP API quota grant (still pending per `/memories/repo/google_apis_status.md`).
- **Round-5 metas** — consistent format across the geo cluster increases SERP CTR and lets Google understand them as a topical cluster. Phone CTA in meta description drives direct call conversions.

**How**
- Script: [data/session6_recrawl_nap_geo_metas.py](../../data/session6_recrawl_nap_geo_metas.py) — single idempotent script with three sections (`section_a`, `section_b`, `section_c`). GSC auth via service account `ols-operations@ols-marketing-agent`.
- Field updates: `palm-harbor` (title+desc), `tarpon-springs` (title), `st-petersburg` (desc), `tampa-hillsborough` (title+desc), `new-port-richey` (desc), `wesley-chapel` (desc), `citrus-county` (desc). Clearwater, Dunedin, Largo, Pasco already matched target.

**Result / next watch**
- Recheck inspection in 7 days: re-run `section_a` and look for `verdict: PASS` on the 6 geo pages.
- Once GBP API quota lands (~Apr 29), automate NAP diff via `gbp_service.py` instead of manual.
- Re-run [data/deep_seo_audit.py](../../data/deep_seo_audit.py) in 2 weeks for impression/CTR lift on standardized metas.

---

## 2026-05-28 — Enriched LocalBusiness schema + A5 homepage geo intlinks + noindex 18 dead pages

**What**
1. **Theme** `layout/theme.liquid` (live theme `153690210458`): replaced the legacy hand-written `LocalBusiness` JSON-LD with an enriched, idempotent-keyed block `SCHEMA-LB-V2`. New fields added: `@id`, `logo`, `image`, `priceRange`, `sameAs` (Facebook + Instagram), `areaServed` (9 cities + 5 counties), `openingHoursSpecification` (Mon-Fri 9-5, Sat 9-3), expanded `hasOfferCatalog` (5 services). Telephone normalized to `+17275426028`.
2. **Theme**: added a second homepage intlinks block (`SEO-INTLINKS-A5-V1`) — scoped `template.name == 'index'`, contains exact-match anchors to all 11 geo pages (9 cities + Pasco/Hernando + Citrus county) plus 4 service-area anchors (appraisal, downsizing, cleanout, FAQs).
3. **Theme**: added a per-page robots-meta override (`SEO-ROBOTS-V1`) — reads `page.metafields.seo.robots` and emits `<meta name="robots" content="...">` when set.
4. **Pages**: pushed `seo.robots = "noindex,follow"` metafield to 18 empty past-event pages (single-line image gallery shells with no descriptive copy or active offer). Handles: `13925-pathfinder-drive-tampa-florida`, `613-severs-landing-palm-harbor-fl-estate-sale-part-{1,2}`, `estate-sale-safety-harbor-florida-pinellas-county-34695`, `estate-sale-westchase-tampa-fl-33626-hillsborough-county`, `highland-lakes-estate-sale`, `lansbrook-myrtle-point-estate-sale-part-two`, `myrtle-point-estate-sale`, `moon-lake-estate-sale`, `new-port-richey-appointment-only-sale-april-2024`, `new-port-richey-sale-huge-do-not-miss-this-one`, `odessa-estate-sale-june-2024`, `organizing-life-estate-sale-company-successful-sales`, `pimberton-drive-hudson`, `pinellas-park-estate-sale-in-the-mainlands-9841-41st-street-north`, `successful-high-quality-estate-sale-ridge-lane-palm-harbor-pinellas-county-florida`, `vintage-coca-cola-estate-sale-in-dunedin-florida-march-2023`, `vintage-palm-harbor-coming-up-soon`.

**Why**
- **Schema** — Knowledge Panel eligibility requires `image`, `priceRange`, `areaServed`, `sameAs`. Stronger entity identity (`@id` + sameAs) helps Google reconcile the brand across GBP/social and unlocks rich result eligibility (LocalBusiness card, sitelinks search box).
- **A5 intlinks** — distribute homepage PageRank to the 6 new/expanded geo pages from session 2 and the existing palm-harbor/tarpon-springs pages with exact-match city anchors. Strong internal linking from the highest-authority page in the site is the fastest known lever for local pack visibility.
- **Noindex 18 dead pages** — these pages add nothing for users (no copy, no active sale, no conversion path) and dilute crawl budget + topical authority. `noindex,follow` keeps link equity flowing while removing them from the index; we choose `follow` (not `nofollow`) because they still link to active gallery pages.

**How**
- Script: [data/session5_schema_intlinks_noindex.py](../../data/session5_schema_intlinks_noindex.py) — single idempotent script that (a) snapshots `layout/theme.liquid` to `data/audit_output/theme_layout_snapshot_pre_session5.liquid`, (b) replaces the legacy LocalBusiness JSON-LD, (c) inserts the A5 intlinks block after the existing `SEO-INTLINKS-V1` close-`endif`, (d) inserts the robots-meta conditional before `</head>`, (e) upserts the `seo.robots` metafield on the 18 dead pages.
- Theme size: 6,636 → 10,707 chars.
- Live verification: homepage HTML contains `SCHEMA-LB-V2`, `areaServed`, `sameAs`, `priceRange`, `openingHours`, all 11 geo anchor `<a>` tags, and 4 service-area anchors. `/pages/highland-lakes-estate-sale` emits `<meta name="robots" content="noindex,follow">`. Homepage emits no robots meta (regression check passed).

**Result** — Watch GSC over 2-3 weeks for: (a) "Estate Sale - Palm Harbor" / "Estate Sale - Tampa" Knowledge Panel candidates, (b) impression lift on the 11 city-keyed queries, (c) coverage report removing the 18 noindexed pages from the indexed set. Re-run [data/deep_seo_audit.py](../../data/deep_seo_audit.py) in 2 weeks.

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
