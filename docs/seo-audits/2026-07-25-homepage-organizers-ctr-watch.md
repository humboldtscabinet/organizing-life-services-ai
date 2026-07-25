# Homepage organizers CTR watch (post 2026-07-24)

Session 12 refreshed homepage SERP copy and organizer intlinks. This checklist tracks whether CTR improves for organizer queries.

## Live expectations (already applied)

- Title: `Estate Sale Organizers Tampa Bay | Call OLS Today`
- Intlinks marker: `SEO-INTLINKS-ORGANIZERS-V1`
- Visible heading includes: `Estate Sale Organizers Serving Tampa Bay`

Quick live check:

```bash
curl -sL https://organizinglifeservices.com/ | tr '\n' ' ' \
  | grep -oE '<title>[^<]+</title>|Estate Sale Organizers Serving Tampa Bay' | head
```

## GSC baseline (window ended 2026-07-22 — pre / early change)

| Query | Page | Impressions | CTR | Position |
|---|---|---:|---:|---:|
| `estate sale organizers` | `/` | 302 | 0.33% | 10.6 |
| `estate sale organizer` | `/` | 98 | 0.00% | 4.9 |

Source: [`deep_seo_audit_20260725_150718.md`](../../data/audit_output/deep_seo_audit_20260725_150718.md).

## Check-in dates

| Date | What to do |
|---|---|
| **2026-08-08** (~14 days) | Curl title/intlinks; GSC Performance → filter queries above + page `/` |
| **2026-08-22** (~28 days) | Same; decide if title/description iteration is needed |

## Success criteria

- CTR on `estate sale organizers` clearly above **0.33%**
- CTR on `estate sale organizer` clearly above **0%**
- Position stable or improving (do not chase position at the expense of CTR)

## If flat after 28 days

Iterate **title/description only** via [`data/session12_homepage_organizers_ctr.py`](../../data/session12_homepage_organizers_ctr.py). Do not expand scope into new pages for this experiment.
