# Full OLS Project Remediation Plan - 2026-06-17

## Summary

This plan turns the full project production-readiness audit into a sequenced
fix path. The goal is to make the broader repo safe for daily use and future
controlled exposure without over-engineering the agent ecosystem before the
core system is stable.

Default operating rule: **do not expose API, dashboard, n8n, or Ollama beyond
localhost until Phase 1 is complete and verified.**

Current baseline:

- Mac mini runtime is healthy: stack, backups, Ollama/Gemma, and API health pass.
- Local tests pass: `42 passed`.
- Full repo readiness failed because of sensitive tracked conversations,
  unauthenticated static `data/` exposure, missing `image_analysis` schema,
  risky vision debug/proxy endpoints, and one-off Shopify mutator sprawl.

Implementation status after the first hardening pass:

- Completed: removed the broad unauthenticated `/static` data mount.
- Completed: added and applied an idempotent `image_analysis` migration.
- Completed: disabled vision debug/token/proxy/file-write tools by default.
- Completed: aligned content publish with the shared high-stakes confirmation gate.
- Completed: removed transcript artifacts from the current tree, moved the
  local copy to a private archive, and changed backup scripts to write outside
  the repo.
- Completed: moved the local IndexNow key out of repo data and tightened local
  `.env` permissions.
- Completed: configured Mac mini GitHub pull access with a read-only deploy key
  and SSH remote.
- Completed: added a history-rewrite runbook for optional old-commit transcript
  purging.
- Completed: Git history rewrite removed legacy conversation transcript paths
  from reachable history.
- Completed: added high-confidence secret scanning and repo hygiene tests.
- Completed: added default runtime blocking for direct `data/` script
  production mutations.
- Completed: added optional off-machine backup sync support.
- Still open: session rotation for any exposed legacy transcript material,
  deeper one-off mutator consolidation into guarded API routes, and choosing
  the actual off-machine backup destination.

## Phase 0 - Containment And Access Freeze

Objective: prevent the known risky surfaces from becoming externally reachable
while the repo is being repaired.

Changes:

- Keep API, dashboard, and n8n bound to `127.0.0.1` in `docker-compose.server.yml`.
- Do not add LAN/Tailscale/public bindings yet.
- Do not enable a reverse proxy yet.
- Do not import/activate n8n workflows yet unless they only call localhost.
- Do not run public-facing Shopify write scripts from `data/`.
- Preserve current working backup state before every high-risk change.

Acceptance gates:

- `infra/server/verify_stack.sh` still reports localhost-only bindings.
- `lsof` on the mini still shows Ollama on `127.0.0.1:11434`.
- `infra/backup/run_all_backups.sh` succeeds before Phase 1 begins.

## Phase 1 - Critical Security And Privacy Hardening

Objective: remove the two highest-risk data exposure paths: committed sensitive
conversation material and unauthenticated serving of `data/`.

### 1.1 Conversation Archive Decision

Problem:

- The audit found token/cookie/session-like material in tracked conversation
  markdown, including QuickBooks URL tokens.
- Even if current sessions expired, Git history can preserve sensitive URLs.

Decision:

- Treat `conversations/raw/` and `conversations/markdown/` as private data,
  not application source.
- Move future conversation backup artifacts out of the app repo.
- Keep only a small sanitized `conversations/README.md` and optional index that
  contains no transcript content.

Implementation:

- Add ignore rules for future transcript material:
  - `conversations/raw/*`
  - `conversations/markdown/*`
  - allow only `.gitkeep`, `README.md`, and sanitized index files if needed.
- Remove tracked transcript artifacts from the current tree using `git rm`.
- If repo privacy requirements demand history cleanup, use a separate,
  deliberate history-rewrite operation with backups:
  - recommended tool: `git filter-repo`
  - target paths: `conversations/raw/`, `conversations/markdown/`
  - coordinate forced push and fresh clones afterward.
- Rotate/revoke any still-relevant sessions that may have appeared in archived
  transcripts: QuickBooks/browser sessions first, then Shopify/XO/GitHub if
  evidence suggests exposure.

Acceptance gates:

- `git ls-files conversations/raw conversations/markdown` returns no transcript
  files.
- Redacted token scan across tracked files finds no sensitive conversation hits.
- Conversation backup scripts write outside this repo or to an ignored private
  path.
- Decision recorded: current tree is cleaned; Git history rewrite remains a
  separate private-risk debt until explicitly approved.

### 1.2 Remove Broad Static Data Mount

Problem:

- `app/main.py` mounts the whole `data/` directory at `/static` without API key.
- On the mini, audit markdown and `image_analysis_export.csv` were served with
  HTTP 200.

Decision:

- Remove the broad `/static` mount entirely for server use.
- Reintroduce file access later only through explicit authenticated endpoints.

Implementation:

- Delete the `StaticFiles` import and `/static` mount from `app/main.py`.
- If any workflow truly needs a file, add a narrow API-key-protected route under
  the relevant router, with an allowlist of safe filenames and no path traversal.
- Add tests:
  - `/static/image_analysis_export.csv` returns 404.
  - `/health` remains unauthenticated.
  - `/api/*` routes still require `X-API-Key`.

Acceptance gates:

- `curl http://127.0.0.1:8000/static/image_analysis_export.csv` returns 404.
- `pytest` includes and passes a static exposure regression test.
- Server stack still verifies after rebuild.

### 1.3 Local Secret Hygiene

Problem:

- iMac `.env` is mode `644`.
- Untracked `data/audit_output/indexnow_key.txt` exists in the dev clone.

Implementation:

- Set local `.env` to `600`.
- Move `data/audit_output/indexnow_key.txt` to a private credentials location
  or delete it after preserving the value in a password manager.
- Add an ignore rule for that exact file pattern if IndexNow key material must
  ever exist locally again.

Acceptance gates:

- `stat -f '%Sp %N' .env` returns `-rw-------`.
- `git status --short` does not show `data/audit_output/indexnow_key.txt`.
- `git check-ignore` confirms future token/key output paths are ignored.

## Phase 2 - Schema And Runtime Correctness

Objective: make deployed database schema match the ORM and restore broken vision
read paths without risking production data.

### 2.1 Add `image_analysis` Migration

Problem:

- `ImageAnalysis` exists in `app/db/models.py`.
- `infra/postgres/init.sql` and migrations do not create `image_analysis`.
- Live `/api/vision/results` fails with `relation "image_analysis" does not exist`.

Implementation:

- Add `infra/postgres/migrations/002_image_analysis.sql`.
- Add matching `CREATE TABLE IF NOT EXISTS image_analysis` block to
  `infra/postgres/init.sql` for fresh installs.
- Include indexes aligned to usage:
  - `status`
  - `gallery_name`
  - `image_url`
  - optionally `(status, gallery_name)`
- Keep migration idempotent.
- Apply migration on mini with `infra/postgres/apply_migrations.sh`.

Acceptance gates:

- Live Postgres returns `image_analysis` from `to_regclass`.
- `/api/vision/results` returns `status=success` rather than schema error.
- Backup verification still restores successfully after migration.
- Add a test or script check that all ORM table names exist in init/migration SQL.

### 2.2 Migration Discipline

Problem:

- `init.sql` only runs on new volumes; existing servers depend on migrations.
- There is no automated parity check.

Implementation:

- Add a lightweight test that extracts ORM `__tablename__` values and checks
  each has a migration or init SQL definition.
- Document migration process in `docs/deployment.md`.
- Keep SQL migrations idempotent and ordered.

Acceptance gates:

- `pytest` fails if a future ORM table lacks a migration/init definition.
- `infra/postgres/apply_migrations.sh` remains safe to rerun.

## Phase 3 - Risky Route Surface Cleanup

Objective: keep useful vision functionality while removing temporary debug,
token, file-write, and open-proxy behavior from the production API.

### 3.1 Remove Or Gate Vision Debug Tools

Problem endpoints:

- `GET /api/vision/debug/test-mutation`
- `GET /api/vision/debug/alt-text-audit`
- `POST /api/vision/save-file`
- `GET /api/vision/store-token`
- `GET /api/vision/get-token`
- `POST /api/vision/xo-proxy`

Decision:

- Production default: disabled.
- Keep only if explicitly enabled by `ENABLE_VISION_DEBUG_TOOLS=true`.
- The open proxy and token-return endpoint should be removed unless there is a
  current, documented workflow that cannot be replaced.

Implementation:

- Add a helper dependency such as `require_debug_tools_enabled()`.
- Gate diagnostic read endpoints behind the helper.
- Remove `get-token` token-return behavior; replace with status-only metadata
  if absolutely needed: present/expired, never raw token.
- Remove arbitrary URL proxying or restrict to a fixed allowlist of XO Gallery
  hosts and methods.
- Remove arbitrary file writes; if export is needed, return the generated file
  as a response instead of writing caller-chosen names under `data/`.
- Ensure all real Shopify mutations still call `require_high_stakes_confirmation`.

Acceptance gates:

- With default env, each debug/token/proxy endpoint returns 404 or 403.
- No endpoint returns raw session tokens, bearer tokens, cookies, or token
  previews.
- Tests cover disabled-by-default behavior.
- Live negative tests still show high-stakes mutations return 409 without
  `human_confirmed=true` and `judge_verdict=PASS`.

### 3.2 Content Publish Gate Alignment

Problem:

- `generate-and-publish` has a parallel policy: dashboard task approval plus LLM
  judge pass, but no shared `human_confirmed` gate parameter.

Decision:

- Publishing generated content is high-stakes.
- It must require:
  - task status `approved`
  - independent LLM judge `PASS`
  - explicit human confirmation at execution time

Implementation:

- Add `human_confirmed: bool = False` and `judge_verdict: str | None = None`
  to `/api/content/generate-and-publish`.
- Call `require_high_stakes_confirmation(task_type="content_publish", ...)`
  before `publish_to_shopify`.
- Decide whether the route-level `judge_verdict` should be:
  - the result of a prior review step, or
  - reserved for a future two-step preview/review flow.
- Conservative v1: require route-level `judge_verdict=PASS`, then still run the
  internal LLM judge immediately before publication.

Acceptance gates:

- Calling `/api/content/generate-and-publish` without confirmation returns 409
  before Shopify calls.
- Approved task alone is insufficient.
- Existing content judge tests still pass.
- A route test proves confirmation plus judge pass reaches the publish function
  when it is monkeypatched.

## Phase 4 - One-Off Script Governance And Simplification

Objective: stop direct one-off scripts from being the default way to mutate
Shopify and reduce repo sprawl without losing historical context.

Findings:

- `data/` contains 42 Python scripts.
- Many directly call Shopify write endpoints.
- Many do not have `--dry-run`, confirmation prompts, or shared high-stakes
  gates.

Decision:

- `data/` should become historical/reference material plus read-only analysis.
- Recurring mutation workflows should move into guarded API routes or documented
  runbooks.
- Old one-off mutators should be archived, not casually run.

Implementation:

- Classify scripts into four groups:
  - `keep_readonly`: audits, fetches, report generation
  - `keep_guarded`: still useful but must default to dry-run and require explicit `--apply`
  - `convert_to_api`: recurring business workflow should become an authenticated route/service
  - `archive`: one-off historical patch no longer used
- Add `data/README.md` with the classification table and warning banner.
- For any retained mutator:
  - add `argparse`
  - default to dry-run
  - require `--apply`
  - require a typed confirmation string for public Shopify changes
  - print target store, IDs, and count before execution
- Move historical one-offs under `data/archive/YYYY-MM/` or `docs/seo-audits/`
  if preserving context matters.
- Add a static test that flags direct mutator scripts without dry-run/apply
  controls.

Acceptance gates:

- No top-level `data/*.py` direct mutator can execute writes by default.
- Static test fails on a new mutator missing dry-run/apply controls.
- Runbooks point to guarded API routes where possible.

Current status:

- `data/` scripts now get a runtime mutation guard through `sitecustomize.py`.
- Direct Shopify Admin API and IndexNow writes require
  `OLS_ALLOW_DATA_MUTATION=1`.
- The detailed inventory is recorded in
  `docs/audits/2026-06-17-data-script-safety-audit.md`.

## Phase 5 - Secrets, GitHub, And Repo Hygiene

Objective: make the repo and both machines predictable for development and
deployment.

Implementation:

- Configure GitHub SSH auth on the mini: **completed**
  - create a dedicated deploy/dev SSH key
  - add it to GitHub with least privilege available
  - switch mini remote to SSH or configure credential helper deliberately
  - run `git fetch origin` and verify `origin/main` updates
- Decide whether to run the optional history rewrite:
  - follow `docs/runbooks/git-history-secret-purge.md`
  - requires explicit approval and a force-push window
- Clean dev clone state:
  - decide whether to commit or discard untracked audit outputs
  - do not commit `indexnow_key.txt`
  - decide whether `data/verify_session3.py` is historical, useful, or should be archived
- Tighten `.gitignore`:
  - explicitly ignore local token/key/cookie files
  - keep only intentional audit outputs tracked
- Add a recommended local setup note:
  - `.env` must be `600`
  - server profile requires `.env.example` server keys
  - iMac `.env` may intentionally be dev-only

Acceptance gates:

- Mini `git fetch origin` succeeds.
- Mini `git rev-parse origin/main` matches GitHub.
- `git status --short` contains only intentional changes.
- Secret scan across tracked files is clean after conversation/archive decisions.

## Phase 6 - Integration Completion Or Explicit Deferral

Objective: stop half-configured integrations from being mistaken for working
systems.

### GBP

- Current state: pull returns Google 404.
- Action:
  - verify `GBP_ACCOUNT_ID` and `GBP_LOCATION_ID`
  - confirm the API endpoint path in `app/services/gbp_service.py`
  - add an integration status endpoint or clearer error detail
- Acceptance:
  - GBP pull succeeds, or docs mark GBP as deferred with the exact blocker.

### GTM

- Current state: IDs missing.
- Action:
  - run discover endpoints
  - set `GTM_ACCOUNT_ID` and `GTM_CONTAINER_ID`
  - confirm service account/user access
- Acceptance:
  - `/api/seo/gtm/overview` returns available data, or docs mark GTM deferred.

### Direct Google Ads API

- Current state: GA4-derived Ads fallback works; direct API unavailable.
- Action:
  - decide whether direct Google Ads API is necessary now
  - if yes, configure developer token and OAuth refresh token
  - if no, label fallback as the supported v1
- Acceptance:
  - direct Ads endpoints work, or the dashboard/docs distinguish fallback vs direct API clearly.

### n8n

- Current state: service running, backups verified, 0 workflows installed.
- Action:
  - decide whether n8n should be active now
  - if yes, import `workflows/n8n/weekly_seo_audit.json`, configure env, activate intentionally
  - if no, document n8n as installed for future use
- Acceptance:
  - live workflow count and active state match docs.

## Phase 7 - Test, CI, And Operational Verification

Objective: make future regressions visible before they reach the mini.

Implementation:

- Add tests for:
  - static exposure disabled
  - schema/migration parity
  - debug tools disabled by default
  - content publish confirmation gate
  - high-stakes route matrix
  - data mutator safety controls
- Add or document a mini-side test mode:
  - option A: create `.venv` on mini and run pytest from repo
  - option B: copy tests into a test image/stage
  - option C: rely on iMac/CI tests and keep mini as runtime-only
- Add a single verification script for post-remediation release:
  - local `pytest`
  - dashboard build
  - shell syntax
  - server preflight
  - stack verify
  - LLM verify
  - backup verify
  - selected read-only API smoke checks

Acceptance gates:

- Full local verification passes.
- Mini runtime verification passes after deploy.
- Audit report can be updated from Fail to Pass with warnings or Pass.

## Phase 8 - Documentation And Architecture Reset

Objective: make the repo describe reality instead of the hoped-for future.

Implementation:

- Update `README.md`:
  - current phase is Mac mini internal operations server, not laptop-only
  - clarify local dev vs server deploy
  - link to latest audit and remediation plan
- Update `docs/architecture.md`:
  - current deployed services: FastAPI, Postgres, dashboard, n8n, Ollama
  - current bindings: localhost-only
  - agent layer is not implemented yet
- Update `docs/agents.md`:
  - state that agent government is future work
  - document current LLM router roles: clerk/executive/judiciary
  - document high-stakes gate policy
- Update `docs/deployment.md`:
  - add explicit server PATH note for SSH/launchd
  - add migration discipline
  - add external exposure prerequisites
- Add `docs/runbooks/remediation-release-check.md` with the final verification command sequence.

Acceptance gates:

- Docs no longer describe the system as laptop-only.
- Docs clearly distinguish implemented, installed-unused, and future-agent pieces.
- A new contributor can identify the safe deploy path and the high-stakes write policy.

## Phase 9 - Controlled Exposure Decision

Objective: decide how the dashboard/API should be accessed after hardening.

Do this only after Phases 1-8 are complete.

Options:

- SSH tunnel only:
  - safest and simplest
  - no LAN/Tailscale bind
- Tailscale:
  - good for remote operator access
  - requires firewall/access policy
- LAN bind:
  - simplest inside home network
  - highest accidental exposure risk

Recommended default:

- Use SSH tunnel first.
- Consider Tailscale only after static/data exposure and debug tools are fixed.
- Avoid broad LAN binding unless there is a clear operator need.

Acceptance gates before any exposure:

- `/static` broad mount removed.
- Debug/proxy/token endpoints disabled or removed.
- CORS pinned to exact access origin.
- API key rotated after cleanup.
- macOS firewall policy reviewed.
- Router DHCP reservation confirmed.
- Off-machine backup destination configured.

## Implementation Order

1. Phase 0 containment.
2. Phase 1.2 static mount removal.
3. Phase 2.1 `image_analysis` migration.
4. Phase 3.1 vision debug/proxy cleanup.
5. Phase 3.2 content publish gate alignment.
6. Phase 1.1 conversation archive decision and cleanup.
7. Phase 4 one-off script governance.
8. Phase 5 GitHub/repo hygiene.
9. Phase 6 integration/n8n decisions.
10. Phase 7 tests and release verification.
11. Phase 8 docs reset.
12. Phase 9 controlled exposure decision.

Reason for this order:

- Static exposure and schema drift are quick, high-leverage code fixes.
- Vision route cleanup reduces the blast radius before any broader access.
- Conversation history cleanup may require coordination/history rewrite, so it
  should begin early but may complete after the first code hardening pass.
- Script governance and docs are important, but less urgent than live API
  exposure and broken runtime paths.

## Final Release Verification

Run locally on the iMac:

```bash
.venv/bin/python -m pytest
npm --prefix dashboard run build
ruff check app tests
find infra conversations -name '*.sh' -print0 | xargs -0 -n1 bash -n
docker-compose config --quiet
```

Run on the Mac mini from `/Users/aiagentecosystem/services/ols` with server PATH:

```bash
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
infra/server/preflight.sh
docker-compose -f docker-compose.server.yml config --quiet
infra/postgres/apply_migrations.sh
infra/server/verify_stack.sh
infra/server/verify_local_llm.sh
RUN_GENERATE_CHECK=true infra/server/verify_local_llm.sh
infra/backup/run_all_backups.sh
infra/backup/verify_postgres_backup.sh
infra/backup/verify_n8n_backup.sh
curl http://127.0.0.1:8000/health
```

Required live smoke checks:

- `/static/image_analysis_export.csv` returns 404.
- `/api/vision/results` returns success.
- high-stakes write without confirmation returns 409.
- `/api/llm/local-status` returns `status=ok`.
- dashboard root returns 200.
- n8n access state matches the documented decision.

## Done Definition

The broader repo is ready for daily internal reliance when:

- No tracked sensitive transcript artifacts remain, or the repo is explicitly
  treated as private with a documented risk acceptance and rotated sessions.
- Broad unauthenticated static serving of `data/` is gone.
- Vision schema drift is fixed and tested.
- Temporary vision debug/proxy/token tools are removed or disabled by default.
- Content publishing uses a single explicit high-stakes gate policy.
- One-off mutator scripts cannot write by accident.
- Mini GitHub auth works.
- Backups, stack, local LLM, and API health survive deploy/reboot checks.
- Docs accurately describe current reality.
- Full local and live verification commands pass.
