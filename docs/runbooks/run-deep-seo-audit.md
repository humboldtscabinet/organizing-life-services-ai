# Runbook: Run a Deep SEO Audit

Generates a full SEO audit comparing the last 28 days vs the prior 28 days, using live Google Search Console + GA4 data plus a fresh crawl of the site.

## Prerequisites

- Service-account credentials at `credentials/google-service-account.json` (must have GSC + GA4 + Sheets API access — see [`/memories/repo/google_apis_status.md`](../../memories/repo/google_apis_status.md) for the canonical list of granted APIs).
- Python audit venv at `.venv-audit/` (gitignored). If missing:
  ```bash
  python3 -m venv .venv-audit
  source .venv-audit/bin/activate
  pip install -r requirements.txt
  ```

## Procedure

1. **Activate the audit venv:**
   ```bash
   source .venv-audit/bin/activate
   ```

2. **Run the audit:**
   ```bash
   python data/deep_seo_audit.py
   ```
   This writes two files to `data/audit_output/`:
   - `deep_seo_audit_YYYYMMDD_HHMMSS.json` — machine-readable raw dump
   - `deep_seo_audit_YYYYMMDD_HHMMSS.md` — auto-generated markdown report

3. **Run the post-deploy measurement baseline:**
   ```bash
   python data/post_deploy_measurement_baseline.py
   ```
   This writes:
   - `data/audit_output/post_deploy_measurement_baseline_YYYYMMDDTHHMMSSZ.json`
   - `docs/seo-audits/YYYY-MM-DD-post-deploy-measurement-baseline.md`

4. **Synthesize the human-readable audit.** Copy the auto-generated MD into `docs/seo-audits/YYYY-MM-DD-<short-slug>.md` and edit it down to:
   - Executive summary (1 paragraph)
   - GSC + GA4 numbers (28d vs prior 28d)
   - Per-query / per-page winners and losers
   - Technical SEO findings
   - "What worked / what didn't" assessment
   - Next-step recommendations (do **not** implement; just record)

5. **Update the changelog** at [docs/seo-audits/CHANGELOG.md](../seo-audits/CHANGELOG.md) — add a new entry at the top.

6. **Commit and push:**
   ```bash
   git add data/audit_output/ docs/seo-audits/
   git commit -m "docs(seo): YYYY-MM-DD audit — <one-line summary>"
   git push origin main
   ```

## What the audit measures

| Section | Data source | Window |
|---|---|---|
| GSC clicks/impressions/CTR/position | Search Console API | last 28d vs prior 28d |
| GA4 sessions/users/conversions | GA4 Data API (property 396184354) | last 28d vs prior 28d |
| Top organic landing pages | GA4 | last 28d |
| Query gains / losses | GSC | last 28d vs prior 28d |
| Page gains / losses | GSC | last 28d vs prior 28d |
| Technical crawl (status, schema, on-page issues) | live crawl of sitemap | point-in-time |

The post-deploy measurement baseline adds:

| Section | Data source | Why it matters |
|---|---|---|
| GA4 key events by event name | GA4 Data API | Detects inflated conversions such as `page_view` or contact-page-load events |
| Organic landing-page key events | GA4 Data API | Shows which SEO pages create real lead intent |
| Changed-page render checks | Live Shopify storefront | Confirms title/meta/H1/noindex changes survived cache/theme behavior |
| Business-weighted content targets | GSC + lead-relevance scoring | Prioritizes queries likely to create estate sale/appraisal/cleanout leads |
| GBP readiness | Live schema/contact page + optional GBP API | Keeps service-area business posture aligned while API access is pending |

## If something goes wrong

- **GSC returns 403:** service account isn't added as a User on the Search Console property. Re-invite at search.google.com/search-console/users.
- **GA4 returns "no permission":** add the service account as a Viewer on the GA4 property.
- **Measurement baseline reports conversion-tracking `fail`:** fix GA4 key-event definitions before using conversion totals as a business KPI. `page_view`, contact-page-load events, and passive engagement events should not count as leads.
- **GTM audit unavailable:** add the service account as read-only in GTM and set `GTM_ACCOUNT_ID` / `GTM_CONTAINER_ID`.
- **Audit script can't find credentials:** check `GOOGLE_APPLICATION_CREDENTIALS` env var or that `credentials/google-service-account.json` exists.
- **Crawler returns mostly 403s:** Shopify bot protection. Verify in GSC's Coverage report that Googlebot itself isn't being blocked.

## Cadence

Run after every significant SEO change and otherwise every 28 days so comparison windows line up cleanly with GSC's standard period.
