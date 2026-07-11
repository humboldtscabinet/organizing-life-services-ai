# Phase 1 Automation Runbook

This runbook covers the gated automation loop for improving rankings and leads
on organizinglifeservices.com using Google Marketing Platform and Shopify data.

## What Phase 1 automation does

1. Pull GSC, GA4, Google Ads, GBP, and Shopify order data into Postgres
2. Generate dashboard tasks from measured gaps
3. Schedule the next content opportunity(s)
4. Raise an operator alert summarizing the run

It does **not** auto-publish blogs or mutate customer-facing Shopify state.

## Operator surfaces

| Surface | Use |
|---|---|
| Dashboard `Run Phase 1 Cycle` | Manual one-click cycle from the operator console |
| `POST /api/dashboard/phase1-cycle` | API trigger for n8n or scripts |
| `POST /api/dashboard/refresh` | Daily data pull + task generation only |
| `scripts/scheduled_platform_sync.py` | Server cron/launchd entry point |
| GitHub Actions `Daily Platform Snapshot` | Repo-visible GSC + GA4 JSON artifacts |
| GitHub Actions `Weekly SEO Audit` | Deep audit + measurement baseline |

## Server schedule (recommended)

### Daily data refresh

```bash
cd /Users/aiagentecosystem/services/ols
docker exec ols-api python /app/scripts/scheduled_platform_sync.py --generate-tasks
```

### Weekly gated cycle (Monday)

```bash
docker exec ols-api python /app/scripts/scheduled_platform_sync.py --full-cycle --schedule-content-count 1
```

Or import `workflows/n8n/weekly_phase1_cycle.json` into n8n and activate it on
the Mac mini.

## Content publish flow (dashboard)

1. Run Phase 1 cycle or `POST /api/content/schedule-next`
2. Approve a pending `content` task in the dashboard
3. Click `Preview Draft` to generate a Claude draft without publishing
4. Click `Publish`, confirm human review, and set judge verdict to `PASS`
5. The route `POST /api/content/generate-and-publish` writes to Shopify only
   after both gates pass

## Manual blockers still requiring operator action

These cannot be automated from this repo alone:

1. **GA4 key-event cleanup** — follow [ga4-key-event-cleanup.md](ga4-key-event-cleanup.md)
2. **GBP remediation deploy** — run `session9_strip_street_address.py` and
   `fix_contact_page.py` with production `.env`
3. **Service-area first wave** — review and execute
   `data/session11_service_area_first_wave.py`
4. **Google Ads direct API** — configure OAuth + developer token per
   [../google_ads_api_design_doc.md](../google_ads_api_design_doc.md)

## Secrets required

### GitHub Actions daily snapshot

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GA4_PROPERTY_ID`
- `GSC_SITE_URL`

### Server runtime

- All values in `.env.example`
- `OLS_API_KEY` for n8n HTTP calls

## Verification

```bash
pytest -q tests/test_phase1_automation.py tests/test_gsc_service.py tests/test_gbp_service.py
curl -H "X-API-Key: $OLS_API_KEY" -X POST http://127.0.0.1:8000/api/dashboard/phase1-cycle
```

Review dashboard alerts after each cycle. Pending tasks should appear before any
publish action is taken.
