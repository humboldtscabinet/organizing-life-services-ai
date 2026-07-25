# Organic growth next steps (2026-07-25) — Session 15

Parallel tracks after the Jul 25 audit: **measurement (human)** and **hub content (Session 15 script)**.

Palm Harbor SD + homepage organizers are already live — **watch only** (no rewrite this session).

## Track A — Operator measurement

1. **GA4 key events** (property `396184354`)  
   Confirm junk events unmarked; keep `form_submit` and `phone_call_clicks` (once firing).  
   → [`docs/runbooks/ga4-key-event-cleanup.md`](../runbooks/ga4-key-event-cleanup.md)  
   → [`2026-07-25-ga4-key-event-cleanup-checklist.md`](2026-07-25-ga4-key-event-cleanup-checklist.md)

2. **GTM phone clicks** (after GTM write-control is on the mini)  
   Dry-run → workspace apply → gated publish.  
   → [`docs/runbooks/gtm-write-and-publish.md`](../runbooks/gtm-write-and-publish.md)  
   → `data/session14_gtm_phone_clicks.py`

3. **Measurement baseline** (when Shopify/`429` cools)

```bash
cd /Users/aiagentecosystem/services/ols
docker exec --env-file .env ols-api python3 /app/data/post_deploy_measurement_baseline.py
```

4. **Scheduled watches**
   - Organizers CTR: **2026-08-08** and **2026-08-22** — [`2026-07-25-homepage-organizers-ctr-watch.md`](2026-07-25-homepage-organizers-ctr-watch.md)
   - Palm Harbor `estate sales palm harbor` CTR/position ~14–28 days after `SD-ESPH-V1`
   - Tampa clicks + appraisal near-me ~14–28 days after Session 15 apply

## Track B — Session 15 content (Shopify)

Script: [`data/session15_organic_growth_hubs.py`](../../data/session15_organic_growth_hubs.py)

| Target | Marker / action |
|---|---|
| `personal-property-appraisal` | Append `SD-APPRAISAL-V2`; refresh title/meta if drifted |
| `estate-sale-tampa-hillsborough-county` | Append `SD-TAMPA-V2` (neighborhoods + soft organizer note) |
| Homepage theme + Clearwater + Tarpon | `SEO-INTLINKS-PINELLAS-V1` if Pinellas hub href missing |
| Palm Harbor | Skip if Pinellas hub already linked (Session 13) |

### Dry-run / apply / IndexNow (Mac mini)

No host `.venv` — use the API container (`./data` is mounted):

```bash
cd /Users/aiagentecosystem/services/ols
git pull   # once Session 15 is on the deploy branch

# Dry-run (default)
docker exec --env-file .env ols-api python3 /app/data/session15_organic_growth_hubs.py

# Apply (workspace Shopify writes + IndexNow for changed URLs)
docker exec \
  -e OLS_ALLOW_DATA_MUTATION=1 \
  -e OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
  --env-file .env \
  ols-api python3 /app/data/session15_organic_growth_hubs.py --apply

# Apply without IndexNow
docker exec \
  -e OLS_ALLOW_DATA_MUTATION=1 \
  -e OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
  --env-file .env \
  ols-api python3 /app/data/session15_organic_growth_hubs.py --apply --skip-indexnow
```

On a laptop with a local venv:

```bash
set -a && source .env && set +a
.venv/bin/python data/session15_organic_growth_hubs.py
OLS_ALLOW_DATA_MUTATION=1 \
OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
.venv/bin/python data/session15_organic_growth_hubs.py --apply
```

### Verify after apply

```bash
curl -sL https://organizinglifeservices.com/pages/personal-property-appraisal | grep -o 'SD-APPRAISAL-V2' | head
curl -sL https://organizinglifeservices.com/pages/estate-sale-tampa-hillsborough-county | grep -o 'SD-TAMPA-V2' | head
curl -sL https://organizinglifeservices.com/pages/estate-sale-clearwater-florida | grep -o 'estate-sale-pinellas-county' | head
curl -sL https://organizinglifeservices.com/ | grep -o 'estate-sale-pinellas-county' | head
```

Report JSON: `data/audit_output/session15_organic_growth_hubs_<timestamp>.json`

## Out of scope (do later)

- Blog triage / Barbie noindex  
- Cleanout page rebuild  
- City wave 2  
- Homepage organizers title rewrite (wait for Aug 8)

## Related

- [`2026-07-25-comprehensive-seo-audit.md`](2026-07-25-comprehensive-seo-audit.md)
- [`CHANGELOG.md`](CHANGELOG.md)
