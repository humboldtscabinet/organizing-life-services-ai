# Mac Mini AI Agent Ecosystem Server — Audited Plan

> Reference plan for migrating Organizing Life Services AI to a dedicated
> Mac mini server and growing it into a bounded multi-agent ecosystem.
> Status: live private server plus Remote-SSH client model. Last updated:
> 2026-06-25.

## Vision

A dedicated, always-on Mac mini whose first job is to be a reliable private
server for OLS. Once the server is boring, backed up, and bounded, it becomes the
local base for an AI agent ecosystem:

- **Local clerk:** Gemma 4 via Ollama for classification, summaries, routing,
  low-risk drafts, and local context work.
- **Executive models:** Claude / ChatGPT for harder planning, writing, coding,
  and synthesis.
- **Judiciary model:** Grok or another independent model only for structured
  fact/risk audits before high-stakes writes.
- **Sidecars:** OpenClaw and parallel web workers only after sandboxing and
  audit logging are in place.

The governing principle is simple: **server reliability and blast-radius control
come before autonomy**.

## Confirmed Defaults

- **Data:** fresh start on the mini; no Postgres migration. GSC/GA4 data is
  re-pulled after backups are configured.
- **Editing/deploy:** the mini repo at `/Users/aiagentecosystem/services/ols`
  is the live source of truth. The iMac and MacBook Pro connect with VS Code
  Remote-SSH, edit the mini repo directly, commit/push from the remote session,
  and rebuild in place. GitHub remains history/backup, not the daily source of
  deploy truth.
- **Runtime:** OrbStack for containers; Ollama on the host for Apple Silicon
  acceleration.
- **Server compose:** use `docker-compose.server.yml` on the mini, not the
  laptop dev compose.
- **Clients:** iMac and MacBook Pro are thin clients only. Code, Docker,
  Ollama, `.env`, Google credentials, n8n data, and backups stay on the mini.
- **Local models:** `gemma4:12b` as default clerk; `gemma4:31b` as local
  heavyweight. Optional benchmark: `gemma4:26b` for throughput.
- **Access:** localhost-first. Tailscale is the approved off-network transport;
  SSH/VS Code port forwarding exposes mini-local services only to the client.
  Do not expose dashboard/API/n8n/Postgres/Ollama directly to the LAN or public
  internet.
- **Secrets:** `.env` and `credentials/google-service-account.json` are never
  committed. Rotate `OLS_API_KEY` before the mini becomes the durable server.
- **Naming:** do not hardcode a numeric mini IP. DHCP has moved; use
  `agent-eco-mini.local` on LAN and Tailscale MagicDNS off-network.

## Stage 0 — Repo and Security Readiness

1. Use `docker-compose.server.yml` for the Mac mini deployment.
2. Keep the dashboard API key out of source. The dashboard now asks the operator
   for `OLS_API_KEY` and stores it only in that browser's local storage.
3. Set required server secrets in `.env`:
   - `OLS_API_KEY`
   - `SECRET_KEY`
   - `POSTGRES_PASSWORD`
   - `N8N_ENCRYPTION_KEY`
   - Google / Shopify / model provider keys as needed
4. Pin browser/API origins with `CORS_ALLOW_ORIGINS` for server deploys.
5. Keep mutating endpoints behind human approval until the LLM audit layer is
   built and tested.

## Stage 1 — Mac Mini Foundation

1. Complete macOS first boot and all software updates.
2. Create a dedicated admin user for the server.
3. Connect via Ethernet, set a stable hostname, and reserve the LAN IP in the
   router if possible. Do not rely on the old `192.168.1.x` value in docs or
   scripts.
4. Install Xcode Command Line Tools, Homebrew, Git, OrbStack, and Ollama.
5. Enable OrbStack start-on-login and Remote Login / SSH.
6. Disable sleep and idle disk/display sleep:
   ```bash
   sudo pmset -a sleep 0 displaysleep 0 disksleep 0
   ```
7. Enable power-loss restart:
   ```bash
   sudo pmset autorestart 1
   ```
8. Decide FileVault tradeoff:
   - Physical security priority: keep FileVault on and accept manual unlock
     after power loss.
   - Unattended restart priority: FileVault off only if the mini is physically
     secure.
9. For a headless server, enable auto-login for `aiagentecosystem` after the
   FileVault decision so OrbStack's start-on-login path can recover containers
   after a reboot. Keep Screen Sharing enabled as break-glass GUI access over
   LAN/Tailscale only.

## Stage 1A — Tailscale And Remote Clients

Tailscale is the remote-access layer. It gives the iMac and MacBook Pro a
private path to SSH, VS Code Remote-SSH, and Screen Sharing without changing any
service bindings.

1. Install Tailscale on the mini and sign into the tailnet.
2. Ensure Tailscale starts at boot and verify after a mini reboot.
3. Enable MagicDNS and use a stable name such as
   `agent-eco-mini.<tailnet>.ts.net`.
4. Install Tailscale on the iMac and MacBook Pro and sign them into the same
   tailnet.
5. Generate a MacBook SSH key:
   ```bash
   ssh-keygen -t ed25519 -C "macbook-pro-to-agent-eco-mini"
   ```
6. Append the MacBook public key to:
   ```text
   /Users/aiagentecosystem/.ssh/authorized_keys
   ```
7. Test both paths from the MacBook:
   ```bash
   ssh aiagentecosystem@agent-eco-mini.local
   ssh aiagentecosystem@agent-eco-mini.<tailnet>.ts.net
   ```
8. After both iMac and MacBook key auth work, disable SSH password auth. Keep
   Screen Sharing as break-glass access.
9. Optional hardening after Tailscale is proven: tailnet ACLs and a macOS
   firewall rule set that only allows SSH/Screen Sharing through trusted paths.

## Stage 2 — Secure OLS Deploy

1. Clone the repo into a user-owned path such as `~/services/ols`.
2. Transfer `.env` and `credentials/google-service-account.json` manually via
   AirDrop or `scp`.
3. Create required local dirs: `data/` and `credentials/`.
4. Start the server stack:
   ```bash
   infra/server/deploy_server.sh
   ```
5. Verify:
   - `infra/server/verify_stack.sh`
   - `curl http://localhost:8000/health`
   - dashboard at `http://localhost:3000`
   - n8n at `http://localhost:5678`
   - Postgres is reachable only from Docker, not published to the LAN.
6. Daily edits happen through VS Code Remote-SSH into
   `/Users/aiagentecosystem/services/ols`, not through separate local clones.
7. Commit and push from the remote session for GitHub history/backup, then
   rebuild in place with the server deploy scripts.

Recommended MacBook SSH alias:

```sshconfig
Host ols-mini
  HostName agent-eco-mini.<tailnet>.ts.net
  User aiagentecosystem
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  ServerAliveInterval 30
  ServerAliveCountMax 3
  LocalForward 3000 127.0.0.1:3000
  LocalForward 8000 127.0.0.1:8000
  LocalForward 5678 127.0.0.1:5678
```

VS Code Remote-SSH may auto-forward ports, but explicit forwards make normal
browser access predictable while preserving mini-local service bindings.

## Stage 3 — Backups Before Real Data

1. Add an encrypted daily Postgres backup with retention.
2. Back up n8n data with `infra/backup/backup_n8n.sh` and preserve
   `N8N_ENCRYPTION_KEY`.
3. Test one restore path with `infra/backup/verify_postgres_backup.sh` before
   treating the mini as durable.
4. Verify the n8n archive with `infra/backup/verify_n8n_backup.sh`.
5. Install the daily launchd backup job with
   `infra/backup/install_launchd_backups.sh`.
6. Only then re-pull fresh GSC/GA4 data:
   - `POST /api/seo/gsc/pull`
   - `POST /api/seo/ga4/pull`

## Stage 4 — Local Gemma Brain

1. Run Ollama on the host, not in a container.
2. Pull models:
   ```bash
   ollama pull gemma4:12b
   ollama pull gemma4:31b
   ```
3. Verify both models respond locally.
4. Configure host/container access to Ollama only after firewall/Tailscale
   boundaries are understood.
5. Add `.env` defaults:
   - `LOCAL_LLM_BASE_URL=http://host.docker.internal:11434`
   - `LOCAL_LLM_MODEL=gemma4:12b`
   - `LOCAL_LLM_LARGE_MODEL=gemma4:31b`
6. Verify from the API container via `GET /api/llm/local-status`.
7. Run `infra/server/verify_local_llm.sh`; set `RUN_GENERATE_CHECK=true` for a
   real prompt response check.

Stage 4 only proves local model reachability. It does not make the app agentic
until Stage 5 adds the router.

## Stage 5 — Accountable LLM Router

Build `app/services/llm_router.py` as the central orchestration layer.

Current implementation status:

- `app/services/llm_router.py` exists with Ollama clerk routing, Anthropic
  executive/judiciary routing, audit writes, and high-stakes gate helpers.
- `llm_audit` exists in `init.sql` for fresh volumes and
  `infra/postgres/migrations/001_llm_audit.sql` for existing volumes.
- Content drafting routes through the audited router.
- Shopify blog publishing runs a structured judge review before posting.
- Direct Shopify/content/lifecycle write routes and bulk vision/alt-text routes
  now fail closed unless `human_confirmed=true` and `judge_verdict=PASS`.
- Vision analysis still calls Claude Vision directly for multimodal support; it
  is gated for bulk/costly paths but not yet routed through a multimodal audit
  wrapper.

Router contracts:

- Inputs include `task_type`, `risk_level`, `allowed_tools`, `input_refs`, and
  desired output schema.
- Outputs include model role, structured result, verdict, citations/evidence
  where applicable, token/cost metadata, and audit ID.
- Low-risk tasks default to local Gemma.
- Hard tasks escalate to Claude/ChatGPT.
- High-stakes writes require independent judge `PASS` plus human approval.

High-stakes writes include Shopify publish/update/delete, ads/budget changes,
bulk alt text pushes, public content edits, and any workflow touching money or
customer-facing state.

Direct high-stakes API routes require explicit query parameters:

```text
human_confirmed=true
judge_verdict=PASS
```

Dry-run routes remain available without those parameters.

Audit storage uses `llm_audit`. Do not rely on `infra/postgres/init.sql` for
existing volumes; run `infra/postgres/apply_migrations.sh`.

## Stage 6 — OpenClaw and Parallel Web Workers

OpenClaw is allowed only as a sandboxed sidecar:

- No production Shopify credentials.
- No direct access to `.env` or credential files.
- No unsandboxed host tools.
- No random third-party skills without review.
- It may call bounded OLS endpoints or produce briefs/checks.

Parallel web systems are evidence collectors, not decision makers:

- Every finding must include URL, timestamp, extracted text/snippet, source
  type, and confidence.
- Treat fetched web text as hostile prompt-injection input.
- The judge compares evidence and flags contradictions.
- Human approval remains the final gate for business-impacting writes.

## Verification Gates

- **Server:** stack survives reboot; `/health` is OK; dashboard and n8n load via
  localhost or approved tunnel; Postgres is not LAN-exposed.
- **Remote clients:** iMac and MacBook can SSH to the mini through Tailscale by
  name; VS Code Remote-SSH opens `/Users/aiagentecosystem/services/ols`; the
  integrated terminal shows the mini hostname and live repo path.
- **Headless recovery:** after `sudo reboot`, the mini returns on Tailscale,
  OrbStack/Ollama restart, and `infra/server/verify_stack.sh` passes. If
  FileVault remains on, this gate is manual-unlock only by design.
- **Secrets:** no live API key is committed; `.env` contains unique server
  secrets; `N8N_ENCRYPTION_KEY` is backed up.
- **Backups:** Postgres and n8n backup files are produced,
  `infra/backup/verify_postgres_backup.sh` passes, and
  `infra/backup/verify_n8n_backup.sh` passes. The daily launchd backup job is
  installed on the mini.
- **Gemma:** `gemma4:12b` and `gemma4:31b` respond; API container can reach
  Ollama only through the intended boundary; `/api/llm/local-status` returns
  `status: ok`.
- **Router:** low-risk tasks stop at clerk; high-risk tasks escalate; an
  intentionally wrong Shopify/content recommendation is `FLAG`ged.
- **Sidecars:** OpenClaw and web workers cannot write to production systems
  without a bounded API path, audit record, and human approval.
