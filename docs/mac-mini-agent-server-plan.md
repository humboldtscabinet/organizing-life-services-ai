# Mac Mini AI Agent Ecosystem Server — Migration Plan

> Reference plan for migrating Organizing Life Services AI to a dedicated
> Mac mini server, and building a tiered multi-LLM "government" on top of it.
> Status: planning. Last updated: 2026-06-09.

## Vision

A dedicated, always-on Mac mini (M4 Pro, 14-core CPU / 20-core GPU / 16-core
Neural Engine, 64 GB unified memory, 1 TB SSD, 10 GbE) whose **sole purpose is
running AI agent ecosystems**. The OLS SEO platform is tenant #1; the box is set
up so additional agent projects can be hosted later.

### Confirmed decisions

- **Data:** fresh start — no Postgres migration. `infra/postgres/init.sql`
  auto-creates the empty schema; GSC/GA4 data is re-pulled from Google.
- **Deploy:** manual — SSH into the mini, `git pull`, rebuild. GitHub is the
  code middleman (MacBook Pro / iMac → `git push` → GitHub → mini `git pull`).
- **Access:** LAN now (mini → router, ideally 10 GbE); add Tailscale later for
  secure remote dashboard/API without public exposure.
- **Container runtime:** OrbStack (lighter than Docker Desktop on Apple Silicon).
- **Local LLM runtime:** Ollama (OpenAI-compatible API) serving Gemma.
- **Secrets:** never committed. `.env` + `credentials/google-service-account.json`
  moved once via `scp`/AirDrop.

---

## Stage 1 — Server foundation (hands-on the mini, ~15 min)

1. Install Xcode Command Line Tools + Homebrew.
2. `brew install --cask orbstack` and `brew install git`.
3. OrbStack: enable **Start on login**.
4. Enable **Remote Login / SSH** (System Settings → General → Sharing). Everything
   after this is done remotely from the MacBook Pro.
5. Disable sleep so it behaves like a server: `sudo pmset -a sleep 0`.
6. Note the LAN IP / `mini.local` hostname.

## Stage 2 — Deploy OLS (remote via SSH) — depends on Stage 1

1. `git clone` the repo to `/opt/ols`.
2. `scp`/AirDrop `.env` + `credentials/google-service-account.json` (never via
   git). Ensure `credentials/` and `data/` directories exist — the compose file
   bind-mounts both.
3. `docker compose up -d --build`.
4. Verify: `curl http://localhost:8000/health` → 200; dashboard `:3000`; n8n
   `:5678`; OpenAPI `/docs`.
   - Reboot survival is automatic: every service has `restart: unless-stopped`
     and OrbStack starts on login — **no launchd plist needed**.
5. Re-pull fresh data (fresh-start DB): `POST /api/seo/gsc/pull` and
   `POST /api/seo/ga4/pull` (with the `X-API-Key` header).

## Stage 3 — Local agent brain — depends on Stage 2

1. `brew install ollama` then `ollama pull gemma2:27b`; verify it responds.
2. Ollama listens on host `:11434`; containers reach it via
   `host.docker.internal:11434`.
3. Add env vars: `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`.

## Stage 4 — Multi-LLM "government" — depends on Stage 3

New module `app/services/llm_router.py` — the accountable orchestration layer.

Tiers use **escalation, not parallelism** — roughly 90% of tasks stop at the clerk:

| Branch | Role | Model(s) | When |
| --- | --- | --- | --- |
| **Clerk** (local) | Classify, route, draft, summarize, read local files (PII-safe) | Gemma via Ollama | Default / every task entry |
| **Executive** | Hard reasoning, planning, coding | Claude Opus 4.8 / GPT‑5 Codex | Only when the clerk escalates |
| **Judiciary** | Independent grounding/fact audit | Grok (different model family) | Only before high-stakes writes |

- High-stakes writes = Shopify writes, money-spend (Vision/Ads budgets), content
  publish.
- The judge runs a **structured grounding checklist** → `PASS` / `FLAG` + reason
  (not vibes).
- **Audit trail:** log model, tokens, cost, and verdict per task (new `llm_audit`
  table or reuse `workflow_logs`).
- Route existing `app/services/vision_service.py` and
  `app/services/content_engine.py` LLM calls through the router.

## Stage 5 — Harden for always-on (add only when justified)

1. **Tailscale** for secure remote dashboard/API (no public exposure).
2. `infra/backup/backup.sh`: daily `pg_dump` + rotation (once real data
   accumulates).
3. `bootstrap.command` one-clicker wrapping Stage 2 steps 3–4 (after the first
   manual success).
4. (Optional) host `python@3.11` for running `pytest`/`ruff` directly on the box.

---

## Verification gates

- **Stage 2:** `/health` 200, all 4 containers healthy, dashboard + n8n + `/docs`
  reachable, reboot survives.
- **Stage 3:** `ollama run gemma2:27b` responds; a container reaches
  `host.docker.internal:11434`.
- **Stage 4:** router logs model/cost/verdict; the judge correctly FLAGs an
  intentionally wrong output.

## Cut after audit (redundant / premature)

- **launchd plist** — redundant with `restart: unless-stopped` + OrbStack start-on-login.
- **Host Python + `gh`** in the base install — containers run everything.
- **Backup cron + `bootstrap.command`** up front — deferred to Stage 5.

## Open decisions (non-blocking)

1. **Gemma variant:** `gemma2:27b` (quality) vs. smaller (throughput) vs. `gemma3` (newer).
2. **Router location:** `app/services/` vs. `app/agents/` (matches the planned agent layer).
3. **Audit storage:** new `llm_audit` table vs. reuse `workflow_logs`.

## Dev-time AI workflow (separate — not app code)

- Copilot / Claude in VS Code → in-editor coding.
- Codex → large refactors.
- ChatGPT / Grok → research + independent second opinion.
