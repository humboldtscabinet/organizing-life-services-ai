# Organizing Life Services — AI Operations System

Self-hosted SEO and business-operations system for Organizing Life Services.
Built on FastAPI, Postgres, a React dashboard, n8n, Google integrations,
Shopify workflows, and a conservative local/cloud LLM router.

## Quick Start

```bash
cp .env.example .env
# Fill in .env values
docker compose up -d --build
```

- **API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:3000
- **n8n**: http://localhost:5678

For the always-on Mac mini server, use:

```bash
infra/server/deploy_server.sh
```

See [docs/deployment.md](docs/deployment.md) for server deployment, backups,
local Ollama/Gemma verification, and post-reboot checks.

## Architecture

See `docs/architecture.md` for the full system overview.

## Working with agents

This repo is intentionally **not** a free-running multi-agent system. Two docs
govern how humans and AI agents operate here:

- [`AGENTS.md`](AGENTS.md) — rules Cursor Cloud Agents / Grok Bots must follow
  when changing this codebase (gates, never-apply list, where to look).
- [`docs/grok-bot.md`](docs/grok-bot.md) — the Grok Bot operating contract that
  maps named seats onto existing code paths (SEO measurement, gated Apply,
  Seedance ads, Mac mini ops, coding via Cloud Agents, independent judiciary).

Google Ads video creatives (Seedance / BytePlus ModelArk) live in
[`seedance-ads/`](seedance-ads/README.md). To rebuild that aspect-ratio
pipeline for another company, see
[`seedance-ads/docs/build-for-another-company.md`](seedance-ads/docs/build-for-another-company.md).

## Current Operating Focus

1. Pull and store SEO/business data from GSC, GA4, Shopify, Google Ads, and GBP
   where access is available.
2. Generate evidence-based SEO opportunities from real performance data.
3. Draft changes with strict human and judge gates before public writes.
4. Measure impact through follow-up audits instead of trusting one-off changes.
5. Run the gated Phase 1 automation cycle via dashboard, n8n, or
   `scripts/scheduled_platform_sync.py`.

See [docs/runbooks/phase1-automation.md](docs/runbooks/phase1-automation.md) for
the operator schedule and publish flow.

The broader multi-agent layer is intentionally deferred until the core SEO
workflow is stable and measurable.
