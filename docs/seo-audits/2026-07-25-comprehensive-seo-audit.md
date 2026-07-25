# Comprehensive SEO Audit — organizinglifeservices.com
_Generated 2026-07-25 · synthesized from deep crawl + GSC/GA4_

**Raw inputs**
- [`data/audit_output/deep_seo_audit_20260725_150718.md`](../../data/audit_output/deep_seo_audit_20260725_150718.md)
- [`docs/seo-audits/2026-07-25-post-deploy-measurement-baseline.md`](2026-07-25-post-deploy-measurement-baseline.md)

**GSC window:** current `2026-06-25 → 2026-07-22` vs prior `2026-05-28 → 2026-06-24`  
**Important:** Session 11/12 live applies (2026-07-24) are **not yet reflected** in this GSC window.

---

## Executive summary

Search **visibility is up** (impressions +6.8%, organic sessions +85%) but **search CTR and clicks are down** (CTR 1.08% → 0.83%, clicks −18%). Weighted average position improved slightly (16.6 → 16.0).

The site is not invisible — it is **earning impressions on weak snippets and wrong URLs** (archive/gallery pages, thin blogs, city pages with soft titles). Ranking growth will come from consolidating commercial intent onto permanent service hubs and improving CTR at positions 4–12, not from broad new indexing alone.

Index health is strong: **48/50** top-impression URLs are submitted & indexed. GBP on-site schema readiness passes. **GA4 conversion tracking fails trust** (`page_view` marked as a key event) — do not use GA4 “conversions” as a KPI until cleaned up.

---

## Performance snapshot

| Metric | Prior | Current | Δ |
|---|---:|---:|---:|
| GSC clicks | 138 | 113 | −18.1% |
| GSC impressions | 12,725 | 13,591 | +6.8% |
| GSC CTR | 1.08% | 0.83% | −0.25 pp |
| Weighted avg position | 16.6 | 16.0 | −0.5 |
| Organic sessions | 164 | 304 | +85.4% |
| Organic users | 134 | 243 | +81.3% |
| True lead signal (`form_submit`) | — | 17 | — |

---

## What is working

- **Palm Harbor / Citrus / NPR** service pages produce real clicks (12 / 9 / 9).
- **Near-me / estate sale** head terms are moving (several +clicks at positions ~6–8).
- **Index coverage** for money pages is healthy (URL Inspection).
- **Fee products + utility collections** correctly noindex (Session 10/12).
- **Woodfield gallery** noindexed (2026-07-24) — removes a Tarpon Springs cannibal.
- **Homepage organizers meta/intlinks** refreshed (2026-07-24) — too early for GSC read.

---

## Critical problems blocking rankings / clicks

### 1. Organizer demand is fragmented
`estate sale organizers` / `estate sale organizer` earn hundreds of impressions across homepage **and** wrong URLs (Pathfinder noindex gallery, senior-services, planning, Tampa hub). Google is unsure which page to reward.

**Recommendation:** Make homepage + county hubs the only organizer targets. Soften or de-emphasize organizer language on non-service pages; strengthen internal links to hubs.

### 2. Tampa / Hillsborough hub is failing commercially
603 impressions, **0 clicks**, position **30.1**. Session 11 refresh is live but not in this GSC window — still needs deeper local proof, FAQs, and city-child links after re-index.

### 3. Palm Harbor is one step from a breakthrough
`estate sales palm harbor` — 325 impr, pos **9.3**, CTR 1.23%. Classic striking-distance CTR/rank job: exact-match H2, proof block, stronger title within ~60 chars.

### 4. New Port Richey is absorbing generic “near me / estate sales”
NPR ranks for broad queries with weak CTR. Either lean into west-Pasco proof or push generic demand toward homepage / Pinellas / Pasco hubs so NPR stays city-intent.

### 5. Commercial service pages are buried
- Personal property appraisal — pos **21.1**
- Estate cleanout services — pos **41.5**
These are high-lead services with thin SERP presence relative to city pages.

### 6. Blog impression waste
Pros/cons + garage-sale blogs: ~3.2k impr / 6 clicks. Barbie collector guide: 621 impr / 0 clicks. Either upgrade with service CTAs + intlinks or accept as low-priority traffic.

### 7. Measurement is broken for decision-making
GA4 counts `page_view` (1,870) and contact-page-load ads conversion as key events. Only **17** `form_submit` events look like real leads. Follow `docs/runbooks/ga4-key-event-cleanup.md` before judging SEO ROI.

---

## Technical crawl findings (92 URLs)

| Issue | Count | Notes |
|---|---:|---|
| noindex | 24 | Mostly intentional (fees, archives, utilities) |
| title too long | 22 | Trim blog + leftover event titles |
| missing meta description | 22 | Many on noindex/utility — lower priority |
| multiple H1 | 15 | Blog/theme pattern — demote secondary H1s |
| low alt-text coverage | 11 | Especially gallery-heavy pages |

URL Inspection (top 50 by impressions): **48 PASS**, 1 noindex excluded, 1 `/account` robots.txt block (fine).

---

## Prioritized recommendations (ranking impact)

### P0 — This week
1. **GA4 key-event cleanup** — unmark `page_view` and contact-page-load; keep form/phone/email CTAs.
2. **Retarget internal links** that still use Woodfield as “Tarpon Springs estate sales” → `/pages/estate-sale-tarpon-springs-florida`.
3. **Palm Harbor striking-distance pass** — title/H2/proof for `estate sales palm harbor`.
4. **Monitor homepage organizers CTR** after Jul 24 copy (compare in ~14 days).

### P1 — Next 2–4 weeks
5. **Deepen Tampa/Hillsborough hub** — neighborhoods, FAQs, appraisals/cleanouts CTAs, child-city links.
6. **Pinellas hub reinforcement** — ensure new `/pages/estate-sale-pinellas-county` is linked from homepage + Palm Harbor/Clearwater/Tarpon.
7. **NPR / Pasco near-me alignment** — local proof + clarify when to use county hub vs city page.
8. **Appraisal page expansion** for `personal property estate appraisers near me` (pos ~12 striking distance).

### P2 — Next quarter
9. **City wave 2** — Dunedin (already converting), Largo, St. Petersburg, Wesley Chapel.
10. **Cleanout services rebuild** (pos ~41).
11. **Blog triage** — add service CTAs to high-impr educational posts; noindex or consolidate chronic 0-CTR off-topic posts.
12. **Re-run deep audit** after Session 11/12 have a full 28-day GSC window.

---

## Do not do (or deprioritize)

- Chasing more product/collection SEO (already guarded/noindex).
- Treating GA4 “conversions” as SEO success until key events are cleaned.
- Redirecting Woodfield gallery to the service page (keep as noindexed archive).
- Broad new blog volume before fixing hub CTR and cannibalization.

---

## Success criteria (28 days)

- Homepage CTR on `estate sale organizers` / `organizer` materially above 0.33% / 0%.
- Palm Harbor query average position ≤ 7 with CTR ≥ 3%.
- Tampa/Hillsborough hub clicks > 0 with position improving from ~30.
- Tarpon Springs query impressions shifting to `/pages/estate-sale-tarpon-springs-florida`.
- GA4 lead KPI = form_submit (and phone/email clicks), not page_view.
