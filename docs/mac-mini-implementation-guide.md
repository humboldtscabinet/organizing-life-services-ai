# Mac Mini Agent Server — Step-by-Step Implementation Guide

> Companion to [mac-mini-agent-server-plan.md](mac-mini-agent-server-plan.md).
> Each step is tagged with who performs it and an estimated time.
> Last updated: 2026-06-09.

## Legend

- 👤 **HUMAN** — only you can do this (physical access, GUI toggles, secrets,
  accounts, passwords, purchases). The AI assistant cannot.
- 🤖 **AI** — the assistant can do this for you in an edit/agent mode (write files,
  run terminal commands, edit code), with your approval.
- 🤝 **BOTH** — AI drafts/runs it, but you must supply a value or confirm a prompt.

> Note: All 🤖 steps require the assistant to be in an **edit/agent mode** with
> terminal access **on the Mac mini** (or over SSH to it). In plan/ask mode the
> assistant can only advise.

---

## Section 1 — Server foundation
**Estimated time: ~20–30 min** (mostly downloads). Must be done physically at the
mini (or via Screen Sharing) until SSH is enabled.

| # | Step | Who | Notes |
|---|------|-----|-------|
| 1.1 | Sign into macOS, connect mini to the router (10 GbE if available) | 👤 HUMAN | Physical setup. |
| 1.2 | Install Xcode Command Line Tools (`xcode-select --install`) | 👤 HUMAN | GUI dialog appears; takes ~5–10 min. |
| 1.3 | Install Homebrew (paste official install script) | 🤝 BOTH | AI provides the command; you authorize with your password. |
| 1.4 | `brew install --cask orbstack` and `brew install git` | 🤖 AI | AI runs once a terminal is available. ~5 min. |
| 1.5 | OrbStack → enable **Start on login** | 👤 HUMAN | GUI toggle in OrbStack settings. |
| 1.6 | Enable **Remote Login / SSH** (Settings → General → Sharing) | 👤 HUMAN | GUI toggle. Enables all remote work after this. |
| 1.7 | Disable sleep: `sudo pmset -a sleep 0` | 🤝 BOTH | AI provides command; you enter your password. |
| 1.8 | Note LAN IP / `mini.local` | 🤝 BOTH | AI can run `ipconfig getifaddr en0`; you record it. |

**Gate:** you can `ssh you@mini.local` from the MacBook Pro. ✅

---

## Section 2 — Deploy OLS
**Estimated time: ~20–40 min** (image builds + first boot). Done remotely over SSH.

| # | Step | Who | Notes |
|---|------|-----|-------|
| 2.1 | `git clone` repo → `/opt/ols` | 🤖 AI | AI runs it. May prompt for GitHub auth → 👤 you. |
| 2.2 | Create the GitHub auth (PAT or SSH key) if clone prompts | 👤 HUMAN | Account-level secret; only you. |
| 2.3 | Copy `.env` to repo root (`scp`/AirDrop) | 👤 HUMAN | Contains live secrets — must be you. |
| 2.4 | Copy `credentials/google-service-account.json` | 👤 HUMAN | Secret file — must be you. |
| 2.5 | Confirm `credentials/` and `data/` dirs exist | 🤖 AI | AI verifies (compose bind-mounts both). |
| 2.6 | `docker compose up -d --build` | 🤖 AI | AI runs. First build ~10–20 min. |
| 2.7 | Verify `/health`, `:3000`, `:5678`, `/docs` | 🤖 AI | AI curls + reports. |
| 2.8 | Re-pull fresh data (`/api/seo/gsc/pull`, `/ga4/pull`) | 🤖 AI | AI runs with the `X-API-Key` you set in `.env`. |

**Gate:** `/health` returns 200, all 4 containers healthy, dashboard loads. ✅

---

## Section 3 — Local agent brain (Ollama + Gemma)
**Estimated time: ~15–30 min** (model download dominates; ~16 GB for 27b).

| # | Step | Who | Notes |
|---|------|-----|-------|
| 3.1 | `brew install ollama` | 🤖 AI | ~2 min. |
| 3.2 | `ollama pull gemma2:27b` | 🤖 AI | Large download; time depends on bandwidth. |
| 3.3 | Verify `ollama run gemma2:27b` responds | 🤖 AI | AI sends a test prompt. |
| 3.4 | Confirm container reaches `host.docker.internal:11434` | 🤖 AI | AI runs a curl from inside `ols-api`. |
| 3.5 | Add `LOCAL_LLM_BASE_URL` / `LOCAL_LLM_MODEL` to `.env` | 🤝 BOTH | AI edits `.env`; you confirm values. |

**Gate:** Gemma responds locally; the API container can reach Ollama. ✅

---

## Section 4 — Multi-LLM "government" (orchestration)
**Estimated time: ~1–3 days of iterative dev** (real engineering, not a one-shot).

| # | Step | Who | Notes |
|---|------|-----|-------|
| 4.1 | Decide router location + audit storage (open decisions) | 👤 HUMAN | Two quick choices; AI recommends. |
| 4.2 | Provide API keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, Grok key | 👤 HUMAN | Account secrets — only you. |
| 4.3 | Write `app/services/llm_router.py` (clerk→executive→judiciary) | 🤖 AI | AI implements the tiered router. |
| 4.4 | Add `llm_audit` table or wire into `workflow_logs` | 🤖 AI | AI edits models/init.sql. |
| 4.5 | Route `vision_service.py` / `content_engine.py` through router | 🤖 AI | AI refactors existing calls. |
| 4.6 | Write tests for routing + judge FLAG behavior | 🤖 AI | AI adds pytest cases. |
| 4.7 | Review behavior + tune escalation thresholds | 🤝 BOTH | AI proposes; you judge real outputs. |

**Gate:** router logs model/cost/verdict; judge FLAGs an intentionally wrong output. ✅

---

## Section 5 — Harden for always-on
**Estimated time: ~1–2 hours, spread out** (add only when justified).

| # | Step | Who | Notes |
|---|------|-----|-------|
| 5.1 | Install + configure Tailscale | 🤝 BOTH | AI installs; you log into your Tailscale account. |
| 5.2 | `infra/backup/backup.sh` daily `pg_dump` + rotation | 🤖 AI | AI writes script + cron/launchd. |
| 5.3 | `bootstrap.command` one-clicker | 🤖 AI | AI writes the wrapper. |
| 5.4 | (Optional) host `python@3.11` for local pytest/ruff | 🤖 AI | Only if you want host-side testing. |

**Gate:** reachable via Tailscale off-network; a backup file is produced. ✅

---

## Timeline summary

| Section | Est. time | Bottleneck |
|---------|-----------|------------|
| 1 — Server foundation | 20–30 min | Downloads + GUI toggles (human) |
| 2 — Deploy OLS | 20–40 min | First Docker image build |
| 3 — Local agent brain | 15–30 min | Gemma model download |
| 4 — Multi-LLM government | 1–3 days | Iterative coding + tuning |
| 5 — Harden | 1–2 hours | Spread out, as needed |

**To a running server (Sections 1–2): ~1 hour.**
**To a working local agent brain (through Section 3): ~1.5 hours.**
Sections 4–5 are ongoing development, not one-time setup.

---

## What the AI assistant cannot do (always 👤 you)

- Physical setup, plugging in cables, signing into macOS.
- GUI toggles: OrbStack "Start on login", Remote Login/SSH, Tailscale login.
- Entering your macOS/sudo password.
- Supplying secrets: `.env` values, the Google service-account JSON, API keys
  (Anthropic, OpenAI, Grok), GitHub auth.
- Purchasing/creating accounts or API plans.

## What the AI assistant can do (🤖, in edit/agent mode with terminal on the mini)

- Run `brew`, `git`, `docker compose`, `ollama`, `curl` commands.
- Write and edit code: `llm_router.py`, backup scripts, `bootstrap.command`,
  model/schema changes, tests.
- Verify health checks and report results.
- Edit `.env` once you provide the secret values.
