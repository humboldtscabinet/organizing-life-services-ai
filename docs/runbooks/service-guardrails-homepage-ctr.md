# Runbook: Service Guardrails + Homepage Organizers CTR

Apply after the service-guardrails / homepage CTR PR is merged to `main`.

OLS is a **service business**. Shopify fee/utility products are internal-only.
This runbook noindexes those product URLs and refreshes homepage SERP copy for
`estate sale organizers` queries.

## Prerequisites

- SSH to the Mac mini production host
- Repo at `/Users/aiagentecosystem/services/ols` (or current deploy path)
- `.env` loaded with Shopify credentials
- Mutation confirmation env ready (only for `--apply`)

## 1) Pull and deploy

```bash
cd /Users/aiagentecosystem/services/ols
git pull origin main
# use the site's normal docker rebuild/restart path
```

Confirm API is healthy, then continue from the host (or `docker exec ols-api`
if scripts are run inside the API container). Prefer the host venv if that is
how Session 10/11 scripts were applied.

```bash
set -a && source .env && set +a
```

## 2) Dry-run homepage CTR meta + intlinks first

Apply homepage **before** product noindex. Back-to-back theme PUTs can race;
running products last avoids overwriting a fresh product block.

On the Mac mini there is no repo `.venv` — use the API container:

```bash
docker exec ols-api python3 /app/data/session12_homepage_organizers_ctr.py
```

Confirm:

- Title ≤ 60 chars, description ~120–160
- Diff only touches `HOMEPAGE-SEO-META-V1` copy and adds `SEO-INTLINKS-ORGANIZERS-V1`
- No product/collection SEO fields are modified

## 3) Dry-run fee product noindex

```bash
docker exec ols-api python3 /app/data/session12_noindex_fee_products.py
```

Review the JSON report under `data/audit_output/session12_noindex_fee_products_*.json`:

- Theme patch status should be `would_patch` or `unchanged`
- Marker should be `SEO-ROBOTS-PRODUCTS-V2` (uses `request.path`)
- Handles: `product-cc-2-7-fee`, `product-cc-2-7-fee-2`, `processing-fee`
- Missing handles are OK to note; do not invent new product SEO

## 4) Apply (mutation guard required)

Only after dry-run review — **homepage first, then products**:

```bash
docker exec \
  -e OLS_ALLOW_DATA_MUTATION=1 \
  -e OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
  ols-api python3 /app/data/session12_homepage_organizers_ctr.py --apply

sleep 5

docker exec \
  -e OLS_ALLOW_DATA_MUTATION=1 \
  -e OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
  ols-api python3 /app/data/session12_noindex_fee_products.py --apply
```

## 5) Verify live

```bash
curl -sL https://organizinglifeservices.com/ | tr '\n' ' ' | grep -o '<title>[^<]*</title>'
curl -sL https://organizinglifeservices.com/ | tr '\n' ' ' | grep -o 'Estate Sale Organizers Serving Tampa Bay'
curl -sL 'https://organizinglifeservices.com/products/product-cc-2-7-fee' | grep -i robots | head
curl -sL 'https://organizinglifeservices.com/products/processing-fee' | grep -i robots | head
```

Expect:

- Homepage title: `Estate Sale Organizers Tampa Bay | Call OLS Today`
- Homepage visible intlinks heading: `Estate Sale Organizers Serving Tampa Bay`
- Fee product pages: `noindex,follow`
- (Liquid comment markers like `SEO-INTLINKS-ORGANIZERS-V1` do not appear in HTML)

## 6) Measurement baseline

```bash
.venv/bin/python data/post_deploy_measurement_baseline.py
```

Confirm checks pass for:

- Homepage title/meta
- `/collections/all`, `/collections/fees-products` still noindex
- Fee product URLs now noindex

## 7) Changelog

Append a short “live applied” note under the 2026-07-24 service-guardrails entry
in `docs/seo-audits/CHANGELOG.md` with the apply timestamp and report filenames.

## If something goes wrong

- Theme snapshots are written under `data/audit_output/theme_layout_snapshot_pre_session12_*.liquid`
- Restore by uploading the snapshot to `layout/theme.liquid` on the main theme
- Product SEO write API remains policy-blocked (`PUT /api/shopify/products/{id}/seo` → 403); do not bypass via Admin SEO fields for ranking
