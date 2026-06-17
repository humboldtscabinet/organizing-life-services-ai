# Mac Mini Agent Server — Step-by-Step Implementation Guide

> Companion to [mac-mini-agent-server-plan.md](mac-mini-agent-server-plan.md).
> Each step is tagged by who performs it and has an explicit gate.
> Last updated: 2026-06-17.

## Legend

- **HUMAN** — physical setup, passwords, accounts, secrets, GUI toggles.
- **AI** — assistant can run/edit over SSH once Remote Login works.
- **BOTH** — assistant can drive, but the human must authorize or provide a
  secret/value.

## Section 0 — Pre-flight

Do this before unboxing if possible.

| # | Step | Who | Notes |
|---|------|-----|-------|
| 0.1 | Prepare `.env` values | HUMAN | Generate fresh `OLS_API_KEY`, `SECRET_KEY`, `POSTGRES_PASSWORD`, and `N8N_ENCRYPTION_KEY`. |
| 0.2 | Gather Google/Shopify credentials | HUMAN | `.env` plus `credentials/google-service-account.json`. Never commit them. |
| 0.3 | Rotate any previously exposed `OLS_API_KEY` | HUMAN | The old dashboard source contained a key; treat it as burned if it was live. |
| 0.4 | Confirm GitHub auth method | HUMAN | New SSH key for the mini is preferred. |
| 0.5 | Decide remote access style | HUMAN | Recommended: LAN/SSH first, Tailscale later before off-network use. |

**Gate:** secrets exist outside git, and the mini has a planned GitHub auth path.

## Section 1 — Mac Foundation

Must start physically at the mini.

| # | Step | Who | Notes |
|---|------|-----|-------|
| 1.1 | Complete macOS first boot and updates | HUMAN | Run updates before installing server tooling. |
| 1.2 | Connect Ethernet and reserve LAN IP | HUMAN | Prefer router DHCP reservation over manual IP on the mini. |
| 1.3 | Install Xcode Command Line Tools | BOTH | `xcode-select --install`; human handles GUI/password. |
| 1.4 | Install Homebrew | BOTH | Use the official Homebrew command. |
| 1.5 | Install Git, OrbStack, and Ollama | AI | `brew install git ollama && brew install --cask orbstack`. |
| 1.6 | Enable OrbStack start-on-login | HUMAN | GUI toggle. |
| 1.7 | Enable Remote Login / SSH | HUMAN | Handoff gate for AI-driven terminal work. |
| 1.8 | Disable sleep | BOTH | `sudo pmset -a sleep 0`; human enters password. |
| 1.9 | Decide FileVault mode | HUMAN | Keep on for physical security; off only for unattended reboot priority. |

**Gate:** `ssh <mini-user>@mini.local` works from the workstation.

## Section 2 — Secure OLS Deploy

Run remotely over SSH.

| # | Step | Who | Notes |
|---|------|-----|-------|
| 2.1 | Clone repo | AI | Recommended path: `~/services/ols`. |
| 2.2 | Transfer `.env` and credentials | HUMAN | AirDrop or `scp`; never GitHub. |
| 2.3 | Create local dirs | AI | Ensure `data/` and `credentials/` exist. |
| 2.4 | Run deploy script | AI | `infra/server/deploy_server.sh`; runs preflight, compose up, migrations, and stack verification. |
| 2.5 | Fix deploy failures if any | BOTH | Preflight failures are usually missing secrets, credentials, or Docker/OrbStack not running. |
| 2.6 | Unlock dashboard | HUMAN | Visit `http://localhost:3000` on the mini or through SSH tunnel and enter `OLS_API_KEY`. |
| 2.7 | Verify services | AI | `infra/server/verify_stack.sh`; checks health, localhost port binding, and Postgres exposure. |
| 2.8 | Reboot test | BOTH | Confirm OrbStack and containers recover after reboot/login. |

**Gate:** API health is OK, dashboard/n8n load through approved access, and
Postgres is not published to the LAN.

## Section 3 — Backups Before Data

Do this before re-pulling fresh analytics data.

| # | Step | Who | Notes |
|---|------|-----|-------|
| 3.1 | Add encrypted Postgres backup script | AI | Daily `pg_dump` with retention. |
| 3.2 | Back up n8n data | AI | `infra/backup/backup_n8n.sh`; preserve `N8N_ENCRYPTION_KEY` outside git. |
| 3.3 | Run first backups manually | AI | Run both Postgres and n8n backup scripts; confirm artifacts exist. |
| 3.4 | Test restore path | AI | `infra/backup/verify_postgres_backup.sh`; restores into a disposable DB only. |
| 3.5 | Verify n8n archive | AI | `infra/backup/verify_n8n_backup.sh`; confirms archive readability. |
| 3.6 | Install daily backup schedule | AI | `infra/backup/install_launchd_backups.sh`; logs to `infra/backup/out/`. |
| 3.7 | Apply SQL migrations | AI | `infra/postgres/apply_migrations.sh`; needed for `llm_audit` on existing volumes. |
| 3.8 | Re-pull GSC/GA4 | AI | Use authenticated API calls only after backup proof. |

**Gate:** Postgres and n8n backups exist,
`infra/backup/verify_postgres_backup.sh` passes, and
`infra/backup/verify_n8n_backup.sh` passes. On the mini, the daily launchd
backup job is installed.

## Section 4 — Local Gemma Brain

This proves local model availability; it does not yet route app logic.

| # | Step | Who | Notes |
|---|------|-----|-------|
| 4.1 | Start Ollama | AI | Use host Ollama for Apple Silicon acceleration. |
| 4.2 | Pull clerk model | AI | `ollama pull gemma4:12b`. |
| 4.3 | Pull heavyweight model | AI | `ollama pull gemma4:31b`. |
| 4.4 | Verify local prompts | AI | Run a small deterministic prompt against both models. |
| 4.5 | Configure container access | AI | Use `host.docker.internal:11434`; only expose Ollama after firewall/Tailscale decision. |
| 4.6 | Add local LLM vars | BOTH | Confirm `.env` has `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, and `LOCAL_LLM_LARGE_MODEL`. |
| 4.7 | Verify API-to-Ollama status | AI | `infra/server/verify_local_llm.sh`; `GET /api/llm/local-status` should return `status: ok`. |

**Gate:** both Gemma 4 models respond and the API container reaches Ollama
through the intended boundary.

## Section 5 — Accountable LLM Router

This is real engineering, not setup-day work. The first implementation now
exists: `app/services/llm_router.py`, `llm_audit`, audited content drafting, and
a pre-publish content judge.

| # | Step | Who | Notes |
|---|------|-----|-------|
| 5.1 | Add `llm_audit` migration | AI | Done in `infra/postgres/migrations/001_llm_audit.sql`; apply with `infra/postgres/apply_migrations.sh`. |
| 5.2 | Implement `app/services/llm_router.py` | AI | Done for Ollama clerk, Anthropic executive/judiciary, audit writes, and fail-closed gate helper. |
| 5.3 | Route existing LLM calls | AI | Content drafting now routes through the router; vision remains direct Claude Vision for multimodal calls. |
| 5.4 | Add high-stakes gates | AI | Content publish has judge review; direct Shopify/content/lifecycle writes and bulk vision/alt pushes require `human_confirmed=true&judge_verdict=PASS`. |
| 5.5 | Add tests | AI | Router, gate, content draft audit, publish judge, and route-level high-stakes tests are in place. |
| 5.6 | Tune with real examples | BOTH | Review outputs before allowing broader automation. |

**Gate:** an intentionally wrong public-content recommendation is `FLAG`ged,
and no high-stakes write can bypass audit + human approval.

## Section 6 — OpenClaw and Parallel Web Sidecars

Add only after Sections 2-5 are stable.

| # | Step | Who | Notes |
|---|------|-----|-------|
| 6.1 | Install OpenClaw in sandboxed mode | AI | No production secrets, no unrestricted host tools. |
| 6.2 | Expose only bounded OLS actions | AI | Prefer internal API endpoints over filesystem/credential access. |
| 6.3 | Add parallel web workers | AI | Evidence collection only: URL, timestamp, extracted text, source type, confidence. |
| 6.4 | Add judge comparison step | AI | Detect contradictions and fail closed. |
| 6.5 | Review sidecar permissions | BOTH | Remove anything that can mutate production without approval. |

**Gate:** sidecars can collect and summarize evidence, but cannot write to
Shopify/ads/content without a bounded API path, audit record, and human approval.

## First-Sitting Target

For a fresh Mac mini, the practical first sitting is Sections 1, 2, and 4, with
Section 3 added before real data is considered durable. Sections 5 and 6 are
multi-day development work.
