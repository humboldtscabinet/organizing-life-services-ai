# Full OLS Project Production-Readiness Audit - 2026-06-17

## Overall Status

**Fail for full production readiness.**

The Mac mini server runtime is healthy: the API, dashboard, n8n container,
Postgres, backups, Ollama, and both Gemma models are running from the expected
server path. Local tests also pass. However, the whole project is not yet
production-ready because the audit found high-risk repository/privacy exposure,
unauthenticated static serving of `data/`, and live schema drift that breaks the
vision workflow.

This is not a "tear it all down" result. The server foundation is good. The next
work should be a focused hardening and simplification pass.

## Evidence Summary

| Area | Status | Evidence |
| --- | --- | --- |
| iMac repo baseline | Pass with caveat | Local repo is on `main` at `007ca48`, matching local `origin/main`. Existing untracked files remain in `data/audit_output/` plus `data/verify_session3.py`; they were not touched. |
| Mac mini live repo | Pass with caveat | Live path is `/Users/aiagentecosystem/services/ols`; branch `main`; `HEAD=007ca48`; working tree clean. Mini `origin/main` ref is stale at `2d11556` because GitHub HTTPS auth still fails noninteractively. |
| Server preflight | Pass | With server PATH set, `infra/server/preflight.sh` completed with `0 failure(s), 0 warning(s)`. Non-login SSH shells still lack Homebrew/OrbStack/Ollama PATH. |
| Runtime stack | Pass with expected warnings | `infra/server/verify_stack.sh` completed with 0 failures and 2 expected warnings: dashboard and n8n have no healthcheck. API/dashboard/n8n bind to `127.0.0.1`; Postgres has no host port. |
| API health | Pass | `/health` returned `status=ok`, `database=ok`, `auth=enabled`. |
| Ollama / Gemma | Pass | `gemma4:12b` and `gemma4:31b` are installed; both generated responses; `/api/llm/local-status` returned `status=ok`. |
| Backups | Pass | Fresh Postgres/n8n backups were created and verified. Postgres restore verified 10 tables; n8n archive had 12 entries and `database.sqlite`. launchd backup job is loaded with last exit code 0. |
| Local Python tests | Pass | `.venv/bin/python -m pytest` completed: `37 passed`, 2 BeautifulSoup/lxml deprecation warnings. |
| Dashboard build | Pass with warning | `npm run build` completed. Vite warned that the main JS chunk is larger than 500 kB. |
| Lint/static checks | Warning | `ruff check app tests` found 2 import-order issues: `app/services/llm_router.py` and `tests/test_shell_scripts.py`. Shell syntax checks passed. |
| Compose config | Mixed | Local dev `docker-compose config --quiet` passed with obsolete `version` warning. Server compose renders on the mini, but fails on the iMac because the iMac `.env` lacks server-only values. |
| Secrets permissions | Mixed | Mini `.env` and Google credentials are `600`; iMac `.env` is `644`. Mini `.env` has required server secrets, but relies on Compose defaults for local LLM model names. |
| Secret scan | Fail | Tracked conversation markdown contains sensitive browser/session material. Redacted scan found sensitive URL/token/cookie-like hits in 13 conversation markdown files, including QuickBooks URL tokens. |
| Static file exposure | Fail | The API mounts all of `data/` at unauthenticated `/static`. On the mini, `/static/audit_output/deep_seo_audit_20260525_181655.md` and `/static/image_analysis_export.csv` returned HTTP 200. |
| High-stakes gates | Pass with caveat | Live negative tests for Shopify redirect, destructive cleanup, and bulk vision push returned `409` without `human_confirmed=true` and `judge_verdict=PASS`. `generate-and-publish` uses dashboard approval plus LLM judge, but not the shared human-confirmation gate. |
| Google ingestion | Pass with caveats | 1-day live pulls succeeded: GSC inserted 348 rows, GA4 inserted 40 rows, Ads fallback inserted 8 rows. GBP pull returned Google 404; direct Google Ads API and GTM are not configured. |
| Dashboard workflow | Pass | Dashboard metrics/tasks endpoints returned 200. Task generation created 4 pending SEO tasks from fresh data. |
| n8n | Warning | n8n is reachable and backed up, but the live n8n database has 0 workflows. The versioned workflow JSON is a template with `active=false`. |
| Vision workflow | Fail | `/api/vision/results` returned `relation "image_analysis" does not exist`. ORM model exists, but `infra/postgres/init.sql` and migrations do not create the table. |
| Agent layer | Warning | `app/agents` and `app/skills/*` are only `.gitkeep` placeholders. Actual safety behavior is in `app/services/llm_router.py`, `app/safety.py`, and guarded routes. |

## High Risks

1. **Committed conversation archive contains sensitive session material.**
   - Evidence: redacted scan found URL token, bearer token, and session/cookie-like hits across 13 tracked `conversations/markdown/*.md` files.
   - Impact: exposed browser-session or accounting URLs may remain recoverable from Git history even if current sessions expire.
   - Remediation: remove or encrypt sensitive conversation archives, rewrite Git history if this repo is not already considered compromised, and rotate/revoke any affected app/account sessions.

2. **Unauthenticated `/static` serves the entire `data/` directory.**
   - Evidence: mini served audit markdown and `image_analysis_export.csv` from `/static` without API auth.
   - Impact: if API access is ever exposed beyond localhost, any file under `data/` may become retrievable, including future ignored token/cookie files or private audit outputs.
   - Remediation: remove the broad static mount or replace it with a small allowlist behind API-key auth.

3. **Vision workflow schema is missing on the live server.**
   - Evidence: `/api/vision/results` fails because `image_analysis` does not exist; live Postgres has 10 tables and lacks that ORM table.
   - Impact: image analysis, result export, and downstream alt-text workflows are not fully functional.
   - Remediation: add an idempotent migration for `image_analysis`, apply it on the mini, and add a schema/test check.

4. **Vision debug/token/proxy endpoints are too powerful for the current boundary.**
   - Evidence: `app/routes/vision.py` includes endpoints that store/return XO session tokens, save arbitrary files under `data/`, run a diagnostic Shopify mutation, and proxy caller-supplied URLs.
   - Impact: acceptable as temporary localhost-only tools, but dangerous if dashboard/API access is widened or the API key leaks.
   - Remediation: remove them, disable behind an explicit local-debug env flag, or split them into a separate non-production tool.

## Medium Risks

- **One-off scripts bypass the high-stakes gate.** `data/` contains 42 Python scripts; many directly mutate Shopify/theme/blog state and several do not default to dry-run or explicit confirmation.
- **Mini GitHub auth is still not fixed.** Live `HEAD` is correct, but the mini cannot fetch GitHub and its local `origin/main` ref is stale.
- **n8n is installed but functionally empty.** No live workflows are present; the checked-in weekly workflow is inactive template JSON.
- **GBP, direct Google Ads, and GTM are not fully configured.** GSC/GA4/Ads fallback work, but GBP returns 404, direct Ads is unavailable, and GTM IDs are missing.
- **iMac dev config is not server-equivalent.** Local preflight fails due missing server secrets, wildcard CORS, missing pinned n8n image, and missing backup password. Local `.env` is also `644`.
- **Content publishing has a parallel approval path.** `generate-and-publish` requires an approved dashboard task and an LLM judge pass, but not the shared `human_confirmed` route gate used elsewhere.
- **No mini-side test environment.** The mini has no repo `.venv`; the API container has pytest installed but does not copy `/tests`.
- **Unattended recovery remains unresolved.** FileVault is on and `autorestart` is 0, so power-loss recovery likely needs human action.

## Low Risks / Cleanup

- Dashboard and n8n lack Docker healthchecks; current reachability checks pass.
- macOS firewall is disabled; current service ports are localhost-only.
- Vite build warns about a large dashboard bundle.
- Ruff found two import-order issues.
- `docker-compose.yml` uses obsolete `version: "3.9"`.
- Docs are partly stale: README still says "Laptop Only"; architecture says "No reverse proxy yet" and names a future CrewAI layer that is not implemented.
- `app/agents` / `app/skills` scaffolding may be fine, but should not be described as an active agent ecosystem yet.
- Router DHCP reservation, off-machine backups, and dashboard access strategy remain human/operator decisions.

## Functional Workflow Status

| Workflow | Status | Notes |
| --- | --- | --- |
| API + database health | Working | Live `/health` is OK. |
| Dashboard metrics/tasks | Working | Endpoints return 200; task generation created 4 pending SEO tasks. |
| GSC pull | Working | 1-day pull inserted 348 rows. |
| GA4 pull | Working | 1-day pull inserted 40 rows. |
| Ads pull | Working with fallback | 1-day fallback inserted 8 rows; direct Google Ads API unavailable. |
| GBP pull | Broken / config issue | Returned Google 404. |
| GTM overview/audit | Not configured | Missing GTM account/container IDs. |
| Shopify cleanup dry-run | Working | Dry-run returned 200 and did not require high-stakes confirmation. |
| High-stakes write blocking | Working | Live negative tests returned 409 before mutation. |
| Vision result workflow | Broken | Missing `image_analysis` table. |
| n8n runtime | Installed but empty | Service reachable, backup verified, 0 live workflows. |
| Local LLM | Working | Ollama, Gemma models, generation checks, and API container status all pass. |
| Backups/restore | Working | Manual and launchd-backed verification pass. |

## Missing Tests

- Migration/schema parity test that compares ORM tables to init/migration SQL.
- API test for `/static` exposure policy.
- Tests around the vision debug/token/proxy endpoints, if they remain.
- Test proving `generate-and-publish` cannot publish from approval alone without the intended human/LLM gate policy.
- Tests for n8n workflow import/activation expectations.
- Mini-side test setup or CI that runs the same pytest suite against the deployed commit.
- Tests or lint policy for one-off mutation scripts in `data/`.

## Remediation Checklist

### Immediate

1. Treat the tracked conversation archive as sensitive. Decide whether to remove it from the repo, encrypt it, or rewrite history; rotate/revoke any still-valid sessions/tokens represented there.
2. Remove or protect the broad `/static` mount. Do not expose API/dashboard over LAN/Tailscale until this is fixed.
3. Move `data/audit_output/indexnow_key.txt` out of repo-adjacent data or add a specific ignore/secret-management path before committing anything in `data/audit_output/`.
4. Add and apply an `image_analysis` migration; verify `/api/vision/results` returns success afterward.
5. Disable or remove the vision debug/token/proxy/file-save endpoints unless they are intentionally kept as local-only diagnostics.

### Next

6. Convert recurring `data/` mutators into guarded API workflows or archive old one-off scripts outside the runtime repo.
7. Decide the content publishing gate policy, then make `generate-and-publish` match it explicitly.
8. Configure GitHub SSH auth on the mini and refresh its `origin/main` ref.
9. Import/activate the n8n workflow only if it is meant to run; otherwise document n8n as installed but unused.
10. Fix GBP/GTM/direct Ads config or mark those integrations as intentionally deferred.
11. Add mini-side test setup or CI and include schema/static/security checks.
12. Tighten iMac `.env` permissions and either keep it dev-only by design or sync it with `.env.example` server keys.
13. Decide off-machine backup destination, DHCP reservation, FileVault/autorestart policy, and dashboard access path.

## Commands / Checks Run

```bash
.venv/bin/python -m pytest
npm run build
ruff check app tests
docker-compose config --quiet
docker-compose -f docker-compose.server.yml config --quiet
find infra conversations -name '*.sh' -print0 | xargs -0 -n1 bash -n
infra/server/preflight.sh
infra/server/verify_stack.sh
infra/server/verify_local_llm.sh
RUN_GENERATE_CHECK=true infra/server/verify_local_llm.sh
infra/backup/run_all_backups.sh
infra/backup/verify_postgres_backup.sh
infra/backup/verify_n8n_backup.sh
curl http://127.0.0.1:8000/health
```

Additional redacted checks queried repo state, file permissions, secret-pattern
locations, live API smoke endpoints, database table names/counts, n8n workflow
count, launchd state, and network listeners. Secret values were not printed.

