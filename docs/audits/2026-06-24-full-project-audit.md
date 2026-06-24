# Full OLS Project Audit - 2026-06-24

## Overall Status

**Pass with warnings for infrastructure and security; fail for conversion KPI trust.**

The Mac mini server foundation is healthy: source is synced, API/dashboard/n8n/Postgres are running, ports are localhost-only, Ollama/Gemma works, backups restore, iCloud offsite sync works, and the major June 17 security failures have been remediated.

The project is not yet "hands-off production mature" because GA4 is still counting passive page-load behavior as conversions, the first-wave service-area SEO rollout is dry-run-ready but not live, n8n has no active workflows, the mini has no pytest environment, and old `data/` mutator scripts remain the main complexity surface.

## Evidence Summary

| Area | Status | Evidence |
|---|---|---|
| iMac source state | Pass | Local repo is clean on `main` at `657bf768e7391b160a7496f22dc6b6b74f27b1a7`, matching `origin/main`. |
| Mac mini source state | Pass | Live repo is `/Users/aiagentecosystem/services/ols`, clean on `main`, same commit as GitHub. `git fetch origin main` succeeds. |
| Local tests | Pass | `.venv/bin/python -m pytest`: 80 passed, 2 BeautifulSoup/lxml deprecation warnings. |
| Dashboard build | Pass with warning | `npm --prefix dashboard run build` passes; Vite warns the main JS chunk is over 500 kB. |
| Secret scan | Pass | `scripts/scan_secrets.py` found no high-confidence secrets in tracked files. |
| Shell syntax | Pass | All tracked shell scripts parse with `bash -n`. |
| Ruff/static lint | Warning | CI lint scope passes, but `ruff check app tests scripts` flags `scripts/get_google_ads_refresh_token.py` import order. |
| Server preflight | Pass | Mini `infra/server/preflight.sh`: 0 failures, 0 warnings. |
| Runtime stack | Pass with expected warnings | Mini `verify_stack.sh`: 0 failures, 2 expected warnings because dashboard/n8n have no Docker healthcheck. |
| Network exposure | Pass | Postgres has no host port; API/dashboard/n8n bind to `127.0.0.1`; `/health` returns DB ok and auth enabled. |
| Static exposure remediation | Pass | Live `/static/image_analysis_export.csv` returns 404. |
| Vision schema/remediation | Pass | Live `/api/vision/results` returns 200; `image_analysis` and `llm_audit` tables exist. |
| Vision debug tools | Pass | Live `/api/vision/get-token` returns 404 in production. |
| Ollama/Gemma | Pass | `gemma4:12b` and `gemma4:31b` are installed; generation check passes; API container reports local LLM status ok. |
| Backups | Pass | Fresh encrypted Postgres and n8n backups created, restore-verified, and synced to iCloud Drive `OLS Backups`. |
| launchd backups | Pass with note | `com.ols.backups` is loaded for 03:15 local runs. Manual backup succeeded during this audit. |
| n8n | Warning | Service is reachable and backed up, but export reports no workflows. n8n also warns `N8N_RUNNERS_ENABLED` should be set. |
| iMac server parity | Warning | iMac `.env` lacks server-only values: `N8N_ENCRYPTION_KEY`, `BACKUP_ENCRYPTION_PASSWORD`, `OFFSITE_BACKUP_DIR`, `N8N_IMAGE`, and CORS pinning. Mini `.env` is correct. |
| Config split | Warning | iMac has GTM IDs; mini does not. Mini has backup/n8n server keys; iMac does not. Decide which machine owns which integrations. |
| Mini Python test env | Warning | Mini has no repo `.venv`, so pytest currently runs on iMac and CI only. |
| Host access | Warning | Mini currently resolves as `agent-eco-mini.local`, but numeric IP is `192.168.1.19`, not the old `192.168.1.73`. |
| macOS recovery posture | Warning | Sleep is disabled, FileVault is on, firewall is disabled, and `autorestart` is 0. Localhost bindings reduce firewall risk; unattended power-loss recovery is unresolved. |
| GA4 conversion trust | Fail | Fresh baseline still counts `page_view` and `ads_conversion_Contact_Page_load_https_1` as key events. |
| GBP API | Warning | On-site GBP readiness passes; API access remains blocked/rate-limited/pending. |
| Google Ads direct API | Deferred | Direct Ads developer token/refresh token are not set; GA4-derived Ads fallback remains the available path. |
| Service-area SEO rollout | Ready, not live | Guarded first-wave Shopify script exists and dry-run report is clean; no live writes yet. |

## High Priority Findings

### 1. GA4 Conversions Are Still Not Trustworthy

Fresh report: `docs/seo-audits/2026-06-24-post-deploy-measurement-baseline.md`.

GA4 still marks passive events as key events:

- `page_view`: 1,171 key events
- `ads_conversion_Contact_Page_load_https_1`: 68 key events
- true lead signal `form_submit`: 7 key events

Impact: rankings/traffic work can still be measured, but "conversions" are inflated and should not drive business decisions yet.

Action:

1. Follow `docs/runbooks/ga4-key-event-cleanup.md`.
2. In GA4 UI, unmark `page_view` as a key event.
3. Stop counting contact-page load as a conversion.
4. Keep/create real lead events: `form_submit`, phone click, email click, contact CTA click.
5. Rerun `data/post_deploy_measurement_baseline.py` and do not trust lead KPIs until it passes.

### 2. Publish The First-Wave Service-Area Pages, But Only After Review

The main SEO opportunity is still local service intent. The fresh report's top targets include:

- `estate sale organizers` on homepage and Tampa/Hillsborough page
- `estate sales palm harbor`
- `estate cleanout services`
- `estate sales tarpon springs`
- `tampa personal property appraisers`

The guarded script is ready: `data/session11_service_area_first_wave.py`.

Dry-run evidence: `data/audit_output/session11_service_area_first_wave_20260623T230329Z.json`.

Planned live work:

- Create `estate-sale-pinellas-county`
- Create `estate-sale-tarpon-springs-florida`
- Append-refresh Pasco County, Tampa/Hillsborough, Palm Harbor, Clearwater, and New Port Richey
- Update SEO metafields for all seven

Action:

1. Review the dry-run report and page copy.
2. Run the script with explicit mutation confirmation only after approval.
3. Verify rendered title/meta/H1/schema/internal links after apply.
4. Submit changed URLs through IndexNow.
5. Rerun the post-deploy baseline and compare GSC over 7-14 days.

### 3. Stabilize The Mini's Network Identity

The server used to be referenced as `192.168.1.73`, but current LAN IP is `192.168.1.19`.

Impact: `.local` works, but scripts/docs/humans using the numeric IP will drift.

Action:

- Reserve the mini in the router DHCP table, or standardize all docs/scripts on `agent-eco-mini.local`.

## Medium Priority Findings

### 4. Decide What n8n Is For

n8n is healthy, backed up, and reachable locally, but it has no workflows. The checked-in weekly SEO audit workflow is a template, while GitHub Actions is already running weekly audits.

n8n also warns that `N8N_RUNNERS_ENABLED=true` should be set before future n8n behavior changes.

Action:

- Either import/activate a real workflow and set `N8N_RUNNERS_ENABLED=true`, or document n8n as installed-but-unused and avoid treating it as part of the active agent ecosystem.

### 5. Fix Environment Parity

The mini `.env` is correct for server operation. The iMac `.env` is development-only and lacks several server variables, while the mini lacks GTM IDs that the iMac has.

Action:

- Add a short `docs/runbooks/env-parity.md` or update deployment docs with: "mini is production env, iMac is dev env."
- Consider adding `.env.server.example` if we want an explicit checklist for the mini.
- Add GTM IDs to the mini only if GTM audit should run from the server/API.

### 6. Add A Mini-Side Test Environment

The mini can run the stack but not pytest from the repo because no `.venv` exists there.

Action:

- Create a mini-side `.venv`, install `requirements.txt`, and run pytest after deploys; or explicitly rely on CI and document that the mini is runtime-only.

### 7. Keep Taming Historical `data/` Mutators

There are 47 top-level Python files under `data/`. Many are historical Shopify/theme/blog mutators. Runtime guard coverage is in place through `data/sitecustomize.py`, and newer scripts self-guard, but many old files do not advertise dry-run or confirmation behavior clearly.

Action:

- Keep current policy: recurring work should become guarded API routes or guarded scripts with dry-run and typed confirmation.
- Archive old one-off scripts by month/session once they are no longer useful as references.
- Do not treat the `data/` script collection as a clean product surface.

### 8. Resolve Deferred Integrations

Current state:

- GBP: on-site readiness passes, API access still blocked/rate-limited/pending.
- GTM: available from iMac baseline run, missing on mini.
- Google Ads direct API: not configured and likely not needed immediately.
- Shopify: configured and working for guarded dry-runs.
- XO Gallery: still specialized and should remain controlled/limited.

Action:

- Focus on GBP API access and Shopify/service-area SEO first.
- Leave Google Ads direct API deferred unless campaign/config audits become a real business need.

## Low Priority / Cleanup

- Dashboard bundle is over 500 kB after minification; code-split later if dashboard grows.
- Fix `scripts/get_google_ads_refresh_token.py` import ordering if we decide to lint `scripts/` broadly.
- Add Docker Compose CLI notes for the iMac: this machine has `docker-compose` v5, not `docker compose`.
- Add dashboard/n8n healthchecks only if the current external verifier scripts become insufficient.
- Decide FileVault/autorestart tradeoff for unattended power-loss recovery.
- macOS firewall is disabled; acceptable while services are localhost-only, but revisit before LAN/Tailscale exposure.

## Over-Engineering Read

The useful spine is now clear:

1. GSC/GA4/Shopify/GBP data collection.
2. A measured SEO opportunity list.
3. Guarded content/site changes.
4. Post-change measurement.
5. Backups and restore verification.

The risky over-engineering is mostly outside that spine:

- calling the placeholder "agent government" production-ready too early,
- keeping n8n installed without a clear workflow owner,
- accumulating one-off mutator scripts,
- adding more model hierarchy before GA4/GBP/service-area execution is boring and measured.

Recommendation: keep Gemma/Ollama as the local clerk, cloud models as draft/judge helpers, and avoid adding more orchestration until the SEO loop is stable for several weeks.

## Recommended Next Moves

1. **Fix GA4 key events in the UI.**
2. **Review and apply the first-wave service-area Shopify script.**
3. **Verify the live pages and submit IndexNow.**
4. **Reserve the mini's DHCP IP or standardize on `agent-eco-mini.local`.**
5. **Decide n8n's role and set `N8N_RUNNERS_ENABLED=true` if keeping it active.**
6. **Create a mini-side pytest environment or document CI-only testing.**
7. **Continue archiving/labeling historical `data/` mutators.**

## Commands Run

Local/iMac:

```bash
.venv/bin/python -m pytest
.venv/bin/python scripts/scan_secrets.py
npm --prefix dashboard run build
find . -name '*.sh' -type f -print0 | xargs -0 -n1 bash -n
.venv/bin/python -m ruff check app tests scripts
docker-compose --env-file .env -f docker-compose.server.yml config --quiet
.venv/bin/python data/post_deploy_measurement_baseline.py
```

Mac mini:

```bash
infra/server/preflight.sh
infra/server/verify_stack.sh
infra/server/verify_local_llm.sh
RUN_GENERATE_CHECK=true infra/server/verify_local_llm.sh
curl http://127.0.0.1:8000/health
infra/backup/verify_postgres_backup.sh
infra/backup/verify_n8n_backup.sh
infra/backup/run_all_backups.sh
docker compose -f docker-compose.server.yml config --quiet
```

Live smoke checks confirmed:

- `/health`: 200, database ok, auth enabled
- `/static/image_analysis_export.csv`: 404
- `/api/vision/results`: 200 with empty result set
- `/api/vision/get-token`: 404 in production
- Postgres tables include `image_analysis` and `llm_audit`
- Fresh backups synced to iCloud Drive
